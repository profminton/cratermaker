import numpy as np
import os
from pathlib import Path
from _binding import Simulation_binding

class Simulation(Simulation_binding):
    """
    This is a class that defines the basic Cratermaker surface object. It initializes a dictionary of user and reads
    it in from a file (default name is cratermaker.in). It also creates the directory structure needed to store surface
    files if necessary.
    """
    #def __init__(self, param_file="cratermaker.in", isnew=True):
    #    currentdir = os.getcwd()