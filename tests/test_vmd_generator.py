"""Unit tests for the VMD Tcl script generator."""

import os
import tempfile
import unittest

from lammps_vmd_tool.core.parser import LammpsDataParser
from lammps_vmd_tool.core.vmd_generator import VmdScriptGenerator, VisualSettings


class TestVmdGenerator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.examples_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "examples"
        )

    def test_data_script(self):
        filepath = os.path.join(self.examples_dir, "water_full.data")
        info = LammpsDataParser.parse(filepath)
        script = VmdScriptGenerator.generate(
            info, settings=VmdScriptGenerator.PRESETS["publication"]
        )

        self.assertIn("package require topotools", script)
        self.assertIn("topo readlammpsdata", script)
        self.assertIn("color change rgb", script)
        self.assertIn("color Type 1", script)
        self.assertIn("pbc box", script)
        self.assertIn("mol modstyle 0 $lvMolid CPK", script)
        self.assertIn("color Display Background", script)
        self.assertIn("menu tkcon on", script)
        self.assertIn("$sel set element \"O\"", script)
        # Script must stay ASCII-only so Chinese Windows encodings cannot
        # corrupt Tcl source files.
        script.encode("ascii")

    def test_triclinic_script(self):
        filepath = os.path.join(self.examples_dir, "quartz_triclinic.data")
        info = LammpsDataParser.parse(filepath)
        script = VmdScriptGenerator.generate(
            info, settings=VmdScriptGenerator.PRESETS["dark"]
        )
        self.assertIn("molinfo $lvMolid set a", script)
        self.assertIn("molinfo $lvMolid set alpha", script)
        self.assertIn("color Display Background", script)
        self.assertIn('$sel set element "Si"', script)

    def test_dump_script(self):
        content = """ITEM: TIMESTEP
0
ITEM: NUMBER OF ATOMS
2
ITEM: BOX BOUNDS pp pp pp
0.0 10.0
0.0 10.0
0.0 10.0
ITEM: ATOMS id type x y z
1 1 1.0 2.0 3.0
2 2 2.0 3.0 4.0
"""
        with tempfile.NamedTemporaryFile(
            "w", suffix=".lammpstrj", delete=False, encoding="utf-8"
        ) as handle:
            handle.write(content)
            temp_path = handle.name
        try:
            info = LammpsDataParser.parse(temp_path)
            script = VmdScriptGenerator.generate(info)
            self.assertIn("type lammpstrj", script)
            self.assertIn("waitfor all", script)
            self.assertNotIn("topo readlammpsdata $lvPath", script)
            self.assertIn("DynamicBonds", script)
        finally:
            os.unlink(temp_path)

    def test_chinese_path_is_escaped(self):
        info = LammpsDataParser.parse(
            os.path.join(self.examples_dir, "water_full.data")
        )
        info.filepath = r"E:\数据\水分子.data"
        script = VmdScriptGenerator.generate(info)
        script.encode("ascii")
        self.assertIn("\\u6570\\u636e", script)

    def test_custom_settings(self):
        info = LammpsDataParser.parse(
            os.path.join(self.examples_dir, "water_full.data")
        )
        settings = VisualSettings(
            rep_style="VDW",
            sphere_scale=0.9,
            bg_color="#102030",
            box_color="#AABBCC",
            projection="Perspective",
            show_axes=True,
            show_box=True,
        )
        script = VmdScriptGenerator.generate(info, settings=settings)
        self.assertIn("VDW 0.90", script)
        self.assertIn("display projection Perspective", script)
        self.assertIn("axes location lowerleft", script)
        self.assertIn("0.0627 0.1255 0.1882", script)


if __name__ == "__main__":
    unittest.main()
