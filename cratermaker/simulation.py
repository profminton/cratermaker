from ._bind import _BodyBind
from dataclasses import dataclass, field
import numpy as np
from numpy.typing import NDArray
from numpy.random import default_rng
import jigsawpy
import os
import trimesh
import json


def to_config(obj):
    # Check if the object has the attribute 'config_ignore'
    ignores = getattr(obj, 'config_ignore', [])
        
    # Generate a dictionary of serializable attributes, excluding those in 'ignores'
    return {
        k: v for k, v in obj.__dict__.items()
        if isinstance(v, (int, float, str, list, dict, bool, type(None))) and k not in ignores
    }
   
def set_properties(obj,**kwargs):
    """
    Sets properties of configurable Simulation objects (e.g. Simulation, Target, Material). How properties are set depends on what arguments are passed to the function in the following way: 
    
    1) filename : path-like
        Properties are read in from JSON file.
    2) catalogue: str
        Properties are read in from a catalogue of pre-defined properties. Properties set by `catalogue` override any set by `filename`. 
    3) kwargs: Any
        Properties are set based on values keyword:value pairs passed to the function. Properties set by `kwarg` override any set by either `catalogue` or `filename 
    """
    
    def set_properties_from_arguments(obj, **kwargs):
        for key, value in kwargs.items():
            if hasattr(obj, key):
                setattr(obj, key, value)   
            
    def set_properties_from_catalogue(obj, catalogue, key):
        # Look up material in the catalogue
            
        properties = catalogue.get(key) 
        if properties: # A match was found to the catalogue 
            set_properties_from_arguments(obj, **properties)
            
    def set_properties_from_file(obj, filename):
        with open(filename, 'r') as f:
            properties =  json.load(f)
            n = obj.__class__.__name__.lower()
            if n in properties:
                set_properties_from_arguments(obj,**properties[n])
        
    if 'filename' in kwargs:
        set_properties_from_file(obj,filename=kwargs['filename'])
    
    if 'catalogue' in kwargs and 'key' in kwargs:
        set_properties_from_catalogue(obj,kwargs['catalogue'],kwargs['key'])
        
    set_properties_from_arguments(obj,**kwargs)
    
    # Check for any unset properties
    for property_name, value in obj.__dict__.items():
        if value is None:
            raise ValueError(f"The property {property_name} has not been set!")    
    
    return
    
    
            
def create_catalogue(header,values):
    # Create the catalogue dictionary using the class variables
    catalogue = {
        tab[0]: dict(zip(header, tab))
        for tab in values
    }

    # Remove the first key from each dictionary in the catalogue
    for k in list(catalogue):
        del catalogue[k][header[0]]

    return catalogue 


@dataclass
class Material:
    # Define all valid properties for the Target object
    name: str = None
    K1: float = None
    mu: float = None
    Ybar: float = None
    density: float = None    

    config_ignore = ['catalogue']  # Instance variables to ignore when saving to file
    def __post_init__(self):
        # Define some default crater scaling relationship terms (see Richardson 2009, Table 1) 
        material_properties = [
            "name",       "K1",     "mu",   "Ybar",     "density" 
        ]
        material_values = [
            ("Water",     2.30,     0.55,   0.0,        1000.0),
            ("Sand",      0.24,     0.41,   0.0,        1750.0),
            ("Dry Soil",  0.24,     0.41,   0.18,       1500.0),
            ("Wet Soil",  0.20,     0.55,   1.14,       2000.0),
            ("Soft Rock", 0.20,     0.55,   7.60,       2250.0),
            ("Hard Rock", 0.20,     0.55,   18.0,       2500.0),
            ("Ice",       2.30,     0.39,   0.0,        900.0), # TODO: Update these based on Kraus, Senft, and Stewart (2011) 
        ]        
        
        self.catalogue = create_catalogue(material_properties, material_values)
        
        # Set properties for the Material object based on the catalogue value)
        if self.name:
            set_properties(self,catalogue=self.catalogue, key=self.name)
        else:
            raise ValueError('No material defined!')    
        
        return    
    
    def set_properties(self, **kwargs):
        set_properties(self,**kwargs)
        return


@dataclass
class Target:
    # Set up instance variables
    name: str = None
    radius: float = None
    gravity: float = None
    material: Material = field(default_factory=Material)
    
    config_ignore = ['catalogue','material']  # Instance variables to ignore when saving to file
    def __post_init__(self):
        # Define some built-in catalogue values for known solar system targets of interest
        gEarth = 9.80665 # 1 g in SI units

        body_properties = [
            "name",    "radius",   "gravity",      "material_name"
        ]
        body_values = [
            ("Mercury", 2440.0e3,  0.377 * gEarth, "Soft Rock"),
            ("Venus",   6051.84e3, 0.905 * gEarth, "Hard Rock"),
            ("Earth",   6371.01e3, 1.0   * gEarth, "Wet Soil" ),
            ("Moon",    1737.53e3, 0.1657* gEarth, "Soft Rock"),
            ("Mars",    3389.92e3, 0.379 * gEarth, "Soft Rock"),
            ("Ceres",   469.7e3,   0.29  * gEarth, "Ice"      ),
            ("Vesta",   262.7e3,   0.25  * gEarth, "Soft Rock"),
        ]      
        
        self.catalogue = create_catalogue(body_properties, body_values)
        
        # Set properties for the Target object based on the arguments passed to the function
        if self.name:
            set_properties(self,catalogue=self.catalogue, key=self.name)
        else: 
            raise ValueError('No target defined!')    
                
        
        return
   
    
    def set_properties(self, **kwargs):
        set_properties(self,**kwargs)
        return
    
    
@dataclass    
class Projectile:
    radius: float = None
    diameter: float = None
    velocity: float = None
    sin_impact_angle: float = None
    vertical_velocity: float = None
        

@dataclass
class Crater:
    diameter: float = None
    radius: float = None
    morphotype: float = None


class Simulation():
    """
    This is a class that defines the basic Cratermaker body object. 
    """
    def __init__(self, target_name="Moon", material_name=None, **kwargs):
        if material_name:
            material = Material(name=material_name)
            self.target = Target(name=target_name, material=material, **kwargs) 
        else: 
            self.target = Target(name=target_name, **kwargs)
       
        # Set some default values for the simulation parameters
        self.pix = kwargs.get('pix', self.target.radius / 1e3)
        self.time_function = kwargs.get('time_function', None)
        self.tstart = kwargs.get('tstart', 0.0)  # Simulation start time (in y)
        self.tstop = kwargs.get('tstop', 4.31e9)    # Simulation stop time (in y)
        
        # Set some default values for the production function population
        self.impactor_sfd  = kwargs.get('impactor_sfd', None)
        self.impactor_velocity = kwargs.gt('impactor_velocity', None)
        
        # Set the random number generator seed
        self.seed = kwargs.get('seed', 235029385) 
        self.rng = default_rng(seed=self.seed)
        
        
        self.cachedir = os.path.join(os.getcwd(),'.cache')
        self.mesh_file = kwargs.get('mesh_file', os.path.join(self.cachedir,"target_mesh.glb") )
        if not os.path.exists(self.cachedir):
            os.mkdir(self.cachedir)
       
        self.mesh = None 
        # Check if a mesh exists, and if so, load it up
        if os.path.exists(self.mesh_file):
            self.load_body_mesh()
            
    def populate(self):
        """
        Populate the surface with craters
        """
        
        if not self.mesh:
            print("Generating new mesh. Please be patient.")
            self.make_target_mesh
            
         

    
        
    config_ignore = ['target', 'projectile', 'crater']  # Instance variables to ignore when saving to file
    def to_json(self, filename):
        
        # Get the simulation configuration into the correct structure
        material_config = to_config(self.target.material)
        target_config = {**to_config(self.target), 'material' : material_config}
        sim_config = {**to_config(self),'target' : target_config} 
        
        # Write the combined configuration to a JSON file
        with open(filename, 'w') as f:
            json.dump(sim_config, f, indent=4)
        
    @property
    def elevation(self):
        return self._body.fobj.elevation
    
    @property
    def name(self):
        return self._body.fobj.name

    def get_elevation(self):
        return self._body.get_elevation()
    
    def set_elevation(self, elevation_array):
        self._body.set_elevation(elevation_array)

    def make_target_mesh(self):
        '''
            This will use jigsawpy to tesselate a sphere to make our intial mesh. This will then be converted to a GLB format
        '''
        
        # This will get updated evantually after we're done testing
        # Set up jigsaw objects
        opts = jigsawpy.jigsaw_jig_t()
        geom = jigsawpy.jigsaw_msh_t()
        mesh = jigsawpy.jigsaw_msh_t()
        
        # Set up Jigsaw mesh files and mesh body if a file doesn't already exist
        opts.mesh_file = self.mesh_file.replace(".glb",".msh")
        opts.jcfg_file = self.mesh_file.replace(".glb",".jig")
        opts.geom_file = self.mesh_file.replace(".glb","_geom.msh")
        
        # Define basic sphere using the built-in ellipsoid mesh model
        geom.mshID = "ellipsoid-mesh"
        geom.radii = np.full(3, self.target.radius, dtype=geom.REALS_t)
        jigsawpy.savemsh(opts.geom_file,geom)

        # Set mesh options
        opts.hfun_scal = "absolute"  #scaling type for mesh-size function, either "relative" or "absolute." For "relative" mesh-size values as percentages of the (mean) length of the axis-aligned bounding-box (AABB) associated with the geometry. "absolute" interprets mesh-size values as absolute measures.
        opts.hfun_hmax = np.sqrt(2.0) * self.pix       # mesh-size function value. The "pix" value is adjusted to keep it scaled  to roughly the same as the older CTEM pix
        opts.mesh_dims = +2          # Number of mesh dimensions (2 for body mesh, 3 for volume)
        opts.optm_qlim = +9.5E-01    # threshold on mesh cost function above which gradient-based optimisation is attempted.
        opts.optm_iter = +64         # max. number of mesh optimisation iterations. 
        opts.optm_qtol = +1.0E-05    # tolerance on mesh cost function for convergence. Iteration on a given node is terminated if adjacent element cost-functions are improved by less than QTOL.
        opts.mesh_kern = "delfront"  # meshing kernel, choice of the standard Delaunay-refinement algorithm ('delaunay') or the Frontal-Delaunay method ('delfront').
        
        # Generate tesselated mesh
        jigsawpy.cmd.jigsaw(opts, mesh)
        
        # Convert the mesh to trimesh
        # Ensure the vertex and face data is in numpy array format
        vertices = np.array([vert[0] for vert in mesh.vert3])
        faces = np.array([face[0] for face in mesh.tria3])

        # Create a trimesh object
        self.mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
       
        # Save generated mesh 
        export = self.mesh.export(os.path.join(cachedir,f"{meshname}.glb"))
        
        return
    
    
    def load_body_mesh(self):
        # This is not well documented, but trimesh reads the mesh in as a Scene instead of a Trimesh, so we need to extract the actual mesh
        scene = trimesh.load_mesh(self.mesh_file)
        
        # Assuming that the only geometry in the file is the body mesh, this should work
        self.mesh = next(iter(scene.geometry.values()))
        
        return
    
    def set_properties(self, **kwargs):
        set_properties(self,**kwargs)
        return 
      


 