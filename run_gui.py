#!/usr/bin/env python3
"""
Root entry point to launch the LAMMPS to VMD Visualizer GUI.
Usage:
    python run_gui.py [path_to_lammps_data_file]
"""

import sys
import os

# Ensure package root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from lammps_vmd_tool.gui.app import main

if __name__ == "__main__":
    main()
