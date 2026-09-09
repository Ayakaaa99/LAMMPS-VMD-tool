"""
Unit tests for LAMMPS data parser.
"""

import os
import unittest
from lammps_vmd_tool.core.parser import LammpsDataParser


class TestParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.examples_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "examples")

    def test_parse_water_full(self):
        filepath = os.path.join(self.examples_dir, "water_full.data")
        info = LammpsDataParser.parse(filepath)

        self.assertEqual(info.num_atoms, 6)
        self.assertEqual(info.num_atom_types, 2)
        self.assertEqual(info.num_bonds, 4)
        self.assertEqual(info.num_angles, 2)
        self.assertEqual(info.atom_style, "full")
        self.assertIsNotNone(info.box)
        self.assertFalse(info.box.is_triclinic)

        # Check atom types
        self.assertEqual(info.atom_types[1].element, "O")
        self.assertEqual(info.atom_types[2].element, "H")
        self.assertAlmostEqual(info.atom_types[1].mass, 15.9994, places=3)
        self.assertAlmostEqual(info.atom_types[2].mass, 1.0080, places=3)

    def test_parse_graphene_atomic(self):
        filepath = os.path.join(self.examples_dir, "graphene_atomic.data")
        info = LammpsDataParser.parse(filepath)

        self.assertEqual(info.num_atoms, 8)
        self.assertEqual(info.num_atom_types, 1)
        self.assertEqual(info.num_bonds, 0)
        self.assertEqual(info.atom_style, "atomic")
        self.assertEqual(info.atom_types[1].element, "C")

    def test_parse_quartz_triclinic(self):
        filepath = os.path.join(self.examples_dir, "quartz_triclinic.data")
        info = LammpsDataParser.parse(filepath)

        self.assertEqual(info.num_atoms, 6)
        self.assertEqual(info.num_atom_types, 2)
        self.assertTrue(info.box.is_triclinic)
        self.assertAlmostEqual(info.box.xy, -2.4565)
        self.assertEqual(info.atom_types[1].element, "Si")
        self.assertEqual(info.atom_types[2].element, "O")


if __name__ == "__main__":
    unittest.main()

