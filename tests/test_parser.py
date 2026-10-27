"""Unit tests for LAMMPS data and trajectory parsing."""

import os
import tempfile
import unittest

from lammps_vmd_tool.core.parser import (
    InvalidEncodingError,
    LammpsDataParser,
    LammpsFileError,
)


class TestParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.examples_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "examples"
        )

    def test_parse_water_full(self):
        filepath = os.path.join(self.examples_dir, "water_full.data")
        info = LammpsDataParser.parse(filepath)

        self.assertEqual(info.file_type, "data")
        self.assertEqual(info.num_atoms, 6)
        self.assertEqual(info.num_atom_types, 2)
        self.assertEqual(info.num_bonds, 4)
        self.assertEqual(info.num_angles, 2)
        self.assertEqual(info.atom_style, "full")
        self.assertIsNotNone(info.box)
        self.assertFalse(info.box.is_triclinic)

        self.assertEqual(info.atom_types[1].element, "O")
        self.assertEqual(info.atom_types[2].element, "H")
        self.assertAlmostEqual(info.atom_types[1].mass, 15.9994, places=3)
        self.assertAlmostEqual(info.atom_types[2].mass, 1.0080, places=3)
        self.assertEqual(info.atom_types[1].comment, "Oxygen")
        self.assertTrue(info.atom_types[1].color.startswith("#"))

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

    def test_any_file_suffix(self):
        source = os.path.join(self.examples_dir, "water_full.data")
        with open(source, encoding="utf-8") as handle:
            content = handle.read()
        with tempfile.NamedTemporaryFile(
            "w", suffix=".lammps_system", delete=False, encoding="utf-8"
        ) as handle:
            handle.write(content)
            temp_path = handle.name
        try:
            info = LammpsDataParser.parse(temp_path)
            self.assertEqual(info.num_atoms, 6)
        finally:
            os.unlink(temp_path)

    def test_parse_orthogonal_dump(self):
        content = """ITEM: TIMESTEP
0
ITEM: NUMBER OF ATOMS
3
ITEM: BOX BOUNDS pp pp pp
0.0 10.0
0.0 20.0
0.0 30.0
ITEM: ATOMS id type element x y z
1 1 O 1.0 2.0 3.0
2 1 O 2.0 3.0 4.0
3 2 H 3.0 4.0 5.0
ITEM: TIMESTEP
100
"""
        with tempfile.NamedTemporaryFile(
            "w", suffix=".dump", delete=False, encoding="utf-8"
        ) as handle:
            handle.write(content)
            temp_path = handle.name
        try:
            info = LammpsDataParser.parse(temp_path)
            self.assertEqual(info.file_type, "dump")
            self.assertTrue(info.is_trajectory)
            self.assertEqual(info.num_atoms, 3)
            self.assertEqual(info.num_atom_types, 2)
            self.assertEqual(info.atom_types[1].element, "O")
            self.assertEqual(info.atom_types[2].element, "H")
            self.assertAlmostEqual(info.box.lx, 10.0)
            self.assertAlmostEqual(info.box.ly, 20.0)
            self.assertAlmostEqual(info.box.lz, 30.0)
            self.assertFalse(info.box.is_triclinic)
        finally:
            os.unlink(temp_path)

    def test_parse_triclinic_dump_bounds(self):
        content = """ITEM: TIMESTEP
0
ITEM: NUMBER OF ATOMS
2
ITEM: BOX BOUNDS xy xz yz pp pp pp
0.0 10.0 1.0
0.0 10.0 0.5
0.0 10.0 0.0
ITEM: ATOMS id type x y z
1 1 1.0 2.0 3.0
2 1 2.0 3.0 4.0
"""
        with tempfile.NamedTemporaryFile(
            "w", suffix=".lammpstrj", delete=False, encoding="utf-8"
        ) as handle:
            handle.write(content)
            temp_path = handle.name
        try:
            info = LammpsDataParser.parse(temp_path)
            self.assertTrue(info.box.is_triclinic)
            self.assertAlmostEqual(info.box.xy, 1.0)
            self.assertAlmostEqual(info.box.xz, 0.5)
            self.assertAlmostEqual(info.box.xlo, 0.0)
            self.assertAlmostEqual(info.box.xhi, 8.5)
        finally:
            os.unlink(temp_path)

    def test_invalid_encoding_raises(self):
        with tempfile.NamedTemporaryFile("wb", suffix=".data", delete=False) as handle:
            handle.write("测试数据\n6 atoms\n".encode("gbk"))
            temp_path = handle.name
        try:
            with self.assertRaises(InvalidEncodingError):
                LammpsDataParser.parse(temp_path)
        finally:
            os.unlink(temp_path)

    def test_unknown_content_raises(self):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".txt", delete=False, encoding="utf-8"
        ) as handle:
            handle.write("this is not a lammps file\n")
            temp_path = handle.name
        try:
            with self.assertRaises(LammpsFileError):
                LammpsDataParser.parse(temp_path)
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    unittest.main()
