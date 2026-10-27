"""
LAMMPS Data to VMD Visualization Tool
"""

from .core.parser import (
    AtomTypeData,
    InvalidEncodingError,
    LammpsDataInfo,
    LammpsDataParser,
    LammpsFileError,
)
from .core.box_math import SimulationBox
from .core.periodic_table import guess_element_from_mass, get_element_info
from .core.vmd_generator import VmdScriptGenerator, VisualSettings
from .core.launcher import find_vmd_executable, launch_vmd

__version__ = "0.0.2"
__all__ = [
    "LammpsDataParser",
    "LammpsDataInfo",
    "LammpsFileError",
    "InvalidEncodingError",
    "AtomTypeData",
    "SimulationBox",
    "guess_element_from_mass",
    "get_element_info",
    "VmdScriptGenerator",
    "VisualSettings",
    "find_vmd_executable",
    "launch_vmd",
]
