import numpy as np
from numpy.random import default_rng
import xarray as xr
import json
import os
import tempfile
from typing import Any
from .target import Target, Material
from .crater import Crater, Projectile
from .surface import Surface, initialize_surface, save_surface, elevation_to_cartesian
from ..utils import general_utils as gu
from ..utils.general_utils import float_like
from mpas_tools.viz.paraview_extractor import extract_vtk
from ..fortran_bind import util_perlin

class Simulation():
    """
    This class orchestrates the processes involved in running a crater simulation.

    Attributes
    ----------
    pix : float
        Pixel resolution for the mesh.
    target : Target
        The target body for the impact simulation.
    rng : numpy.random.Generator
        Random number generator instance.

    Methods
    -------
    set_properties(**kwargs):
        Set properties of the current object based on the provided keyword arguments.
    to_json(filename):
        Export the current simulation configuration to a JSON file.
    generate_crater(**kwargs):
        Create a new Crater object and its corresponding Projectile.
    generate_projectile(**kwargs):
        Create a new Projectile object and its corresponding Crater.
    emplace_crater(from_projectile=False, **kwargs):
        Emplace a crater in the simulation, optionally based on a projectile.
    """

    def __init__(self, 
                target: str | Target = "Moon",
                material: str | Material | None = None,
                pix: float_like | None = None,
                reset_surface: bool = True,
                simdir: os.PathLike | None = None, 
                *args: Any,
                **kwargs: Any):
        """
        Initialize the Simulation object.

        Parameters
        ----------
        target: str or Target, optional, default "Moon"
            Name of the target body or Target object for the simulation, default is "Moon".
        material : str or Material, optional
            Name of the material or Material object for the target body, if None is passed, the default material for the target body is used.
        pix : float, optional
            Pixel resolution for the mesh, default is None.
        reset_surface : bool, optional
            Flag to reset the surface elevation, default is True.
        simdir: PathLike, optional
            Path to the simulation directory, default is current working directory.
        **kwargs : Any
            Additional keyword arguments.
        """
      
        if simdir is None:
            simdir = os.getcwd() 
        if not os.path.isabs(simdir):
            simdir = os.path.abspath(simdir)
        if not os.path.exists(simdir):
            os.makedirs(simdir) 
        self.simdir = simdir
        
        if material:
            if isinstance(material, str):
                try:
                    material = Material(material)
                except:
                    raise ValueError(f"Invalid material name {material}")
            elif not isinstance(material, Material):
                raise TypeError("materiat must be an instance of Material or a valid name of a material")        
            
        if not target:
            if material:
                target = Target("Moon", material=material)
            else:
                target = Target("Moon")
        elif isinstance(target, str):
            try:
                if material:
                    target = Target(target, material=material)
                else:
                    target = Target(target)
            except:
                raise ValueError(f"Invalid target name {target}")
        elif isinstance(target, Target):
            if material:
                target.material = material
        elif not isinstance(target, Target):
            raise TypeError("target must be an instance of Target or a valid name of a target body")

        self.target = target

        if pix is not None:
            self.pix = np.float64(pix)
        else:    
            self.pix = np.sqrt(4 * np.pi * self.target.radius**2) * 1e-3  # Default mesh scale that is somewhat comparable to a 1000x1000 CTEM grid

        self.surf = initialize_surface(pix=self.pix, target=self.target, reset_surface=reset_surface, *args, **kwargs)
        
        # Set some default values for the simulation parameters
        self.time_function = kwargs.get('time_function', None)
        self.tstart = kwargs.get('tstart', 0.0)  # Simulation start time (in y)
        self.tstop = kwargs.get('tstop', 4.31e9)    # Simulation stop time (in y)
        
        # Set some default values for the production function population
        self.impactor_sfd  = kwargs.get('impactor_sfd', None)
        self.impactor_velocity = kwargs.get('impactor_velocity', None)
        
        # Set the random number generator seed
        self.seed = kwargs.get('seed', None) 
        self.rng = default_rng(seed=self.seed)
        
        self._crater = None
        self._projectile = None

        return

    
    def set_properties(self, **kwargs):
        """
        Set properties of the current object based on the provided keyword arguments.

        This function is a utility to update the properties of the current object. The actual implementation of the 
        property setting is handled by the `utils.gu.set_properties` method.

        Parameters
        ----------
        **kwargs : dict
            A dictionary of keyword arguments that represent the properties to be set on the current object.

        """        
        gu.set_properties(self,**kwargs)
        return 

    
    def to_json(self, filename):
        """
        Export the current simulation configuration to a JSON file.

        Parameters
        ----------
        filename : str
            The file path where the JSON configuration will be saved.
        """        
        #TODO: Re-do this once the dust settles a bit
        # Get the simulation configuration into the correct structure
        material_config = gu.to_config(self.target.material)
        target_config = {**gu.to_config(self.target), 'material' : material_config}
        sim_config = {**gu.to_config(self),'target' : target_config} 
        
        # Write the combined configuration to a JSON file
        with open(filename, 'w') as f:
            json.dump(sim_config, f, indent=4)
            
        return
    

    def generate_crater(self, **kwargs):
        """
        Create a new Crater object and its corresponding Projectile.

        Parameters
        ----------
        **kwargs : dict
            Keyword arguments for initializing the Crater object.

        Returns
        -------
        (Crater, Projectile)
            A tuple containing the newly created Crater and Projectile objects.
        """        
        # Create a new Crater object with the passed arguments and set it as the crater of this simulation
        crater = Crater(target=self.target, rng=self.rng, **kwargs)
        projectile = crater.scale.crater_to_projectile(crater)
        
        return crater, projectile
    
    
    def generate_projectile(self, **kwargs):
        """
        Create a new Projectile object and its corresponding Crater.

        Parameters
        ----------
        **kwargs : dict
            Keyword arguments for initializing the Projectile object.

        Returns
        -------
        (Projectile, Crater)
            A tuple containing the newly created Projectile and Crater objects.
        """
        projectile = Projectile(target=self.target, rng=self.rng, **kwargs)
        crater = projectile.scale.projectile_to_crater(projectile)
        
        return projectile, crater
   
   
    def emplace_crater(self, from_projectile=False, **kwargs):
        """
        Emplace a crater in the simulation, optionally based on a projectile.

        Parameters
        ----------
        from_projectile : bool, optional
            Flag to create a crater based on a projectile, default is False.
        **kwargs : dict
            Keyword arguments for initializing the Crater or Projectile object.
        """        
        if from_projectile:
            self.projectile, self.crater = self.generate_projectile(**kwargs)
        else:
            self.crater, self.projectile = self.generate_crater(**kwargs)
        self.surf['crater_distance'] = self.surf.get_cell_distance(self.crater.location, self.target.radius)
        self.surf['crater_bearing'] = self.surf.get_cell_initial_bearing(self.crater.location)
        
        self.crater.average_surface_normal_vector = self.surf.get_average_surface(self.crater.location, self.crater.radius)
        
        return  


    def save(self, *args, **kwargs):
        """
        Save the current simulation state to a file.
        """
        save_surface(self.surf, *args, **kwargs)
        
        return
    
    
    def export_vtk(self, 
                   out_dir: os.PathLike | None = None,
                   *args, **kwargs
                   ) -> None:
        """
        Export the surface mesh to a VTK file.

        Parameters
        ----------
        out_dir : str, Default "vtk_files"
            Directory to store the VTK files.
        """
        if out_dir is None:
            out_dir = os.path.join(self.simdir, "vtk_files")
        ignore_time = "time" not in self.surf.dims
        
        # Save the surface data to a combined netCDF file
        with tempfile.TemporaryDirectory() as temp_dir:
            self.save(combine_data_files=True, out_dir=temp_dir)
            
            # Use elevation data to modify the mesh for visualization purposes
            grid = xr.open_dataset(self.grid_file)
           
            vert_vars = ['xVertex', 'yVertex', 'zVertex']
            
            ds_new = elevation_to_cartesian(grid[vert_vars], self.surf['elevation'])
            for var in vert_vars:
                grid[var] = ds_new[var]
                
            face_vars = ['xCell', 'yCell', 'zCell']
            ds_new = elevation_to_cartesian(grid[face_vars], self.surf['elevation'].nodal_average())
            for var in face_vars:
                grid[var] = ds_new[var]
            
            grid.to_netcdf(os.path.join(temp_dir, "surface_mesh.nc"))
            
            # Combine the grid and data into one file
            try:
                extract_vtk(
                    filename_pattern=os.path.join(temp_dir, "*.nc"),
                    mesh_filename=os.path.join(temp_dir, "surface_mesh.nc"),
                    variable_list=['allOnVertices', 'allOnCells'] , 
                    dimension_list=['maxEdges=','vertexDegree='], 
                    combine=True,
                    include_mesh_vars=True,
                    out_dir=out_dir, 
                    ignore_time=ignore_time, 
                    *args, **kwargs)
            except:
                raise RuntimeError("Error in mpas_tools.viz.paraview_extractor.extract_vtk. Cannot export VTK files")
        
        return
    
    def apply_noise(self, 
                    model="turbulence",
                    noise_width=1000e3,
                    noise_height=20e3,
                    **kwargs,
                    ) -> None:
      
        scale = self.target.radius / noise_width
        num_octaves = kwargs.pop("num_octaves", 12)
        anchor = kwargs.pop("anchor", self.rng.uniform(0.0,scale, size=(num_octaves, 3))) 
        
        # Set reasonable default values for the different models
        if model == "turbulence" or model == "billowed" or model == "plaw" or model == "ridged":
            kwargs.setdefault("noise_height", noise_height)
            kwargs.setdefault("freq", 2.00)
            kwargs.setdefault("pers", 0.5)
        if model == "plaw":
            kwargs.setdefault("slope", 2.0)
        if model == "swiss" or model == "jordan":
            kwargs.setdefault("lacunarity", 1.92)
            kwargs.setdefault("gain", 0.5)
            kwargs.setdefault("warp", 0.35)
        if model == "jordan":
            kwargs.setdefault("gain0", 70.0)
            kwargs.setdefault("warp0", 0.4)
            kwargs.setdefault("damp0", 1.0)
            kwargs.setdefault("damp", 0.8)
            kwargs.setdefault("damp_scale", 0.01) 
            
        if "noise_height" in kwargs:
            kwargs["noise_height"] = kwargs["noise_height"] / self.target.radius
            
        vars = ['node_x', 'node_y', 'node_z']
        ds_norm = self.surf.uxgrid._ds[vars] * scale / self.target.radius
        noise_function = lambda x, y, z: util_perlin(model, x, y, z, num_octaves, anchor, **kwargs)
        noise = np.vectorize(noise_function)(ds_norm[vars[0]], ds_norm[vars[1]], ds_norm[vars[2]])
       
        self.surf['elevation'] += noise * self.target.radius 
        
        return
      
    @property
    def data_dir(self):
        return self.surf.data_dir
    
    @property
    def grid_file(self):
        return self.surf.grid_file
    
    @property
    def elevation_file(self):
        return self.surf.elevation_file
    
    # The following are placeholders for if/when we need to pass data back and forth to the Fortran library     
    # @property
    # def elevation(self):
    #     return self._body.fobj.elevation
    
    # @property
    # def name(self):
    #     return self._body.fobj.name


    # def get_elevation(self):
    #     return self._body.get_elevation()

    
    # def set_elevation(self, elevation_array):
    #     self._body.set_elevation(elevation_array)
