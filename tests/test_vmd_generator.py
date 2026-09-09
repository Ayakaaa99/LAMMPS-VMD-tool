"""
Unit tests for VMD script generation.
"""

import os
import unittest
from lammps_vmd_tool.core.parser import LammpsDataParser
from lammps_vmd_tool.core.vmd_generator import VmdScriptGenerator, VisualSettings


class TestVmdGenerator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.examples_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "examples")

    def test_script_generation_water(self):
        filepath = os.path.join(self.examples_dir, "water_full.data")
        info = LammpsDataParser.parse(filepath)

        script = VmdScriptGenerator.generate(info, settings=VmdScriptGenerator.PRESETS["publication"])

        # Check required Tcl commands
        self.assertIn("package require topotools", script)
        self.assertIn("package require pbctools", script)
        self.assertIn("topo readlammpsdata", script)
        self.assertIn("full", script)  # atom style
        self.assertIn('$sel set element "O"', script)
        self.assertIn('$sel set element "H"', script)
        self.assertIn("pbc box", script)
        self.assertIn("mol representation CPK", script)
        self.assertIn("color Display Background white", script)

    def test_script_generation_triclinic(self):
        filepath = os.path.join(self.examples_dir, "quartz_triclinic.data")
        info = LammpsDataParser.parse(filepath)

        script = VmdScriptGenerator.generate(info, settings=VmdScriptGenerator.PRESETS["ball_and_stick"])
        self.assertIn("molinfo $molid set a", script)
        self.assertIn("molinfo $molid set alpha", script)
        self.assertIn('$sel set element "Si"', script)
        self.assertIn("color Display Background black", script)


if __name__ == "__main__":
    unittest.main()

