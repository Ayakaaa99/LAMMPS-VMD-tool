"""
Unit tests for periodic table database and smart element inference.
"""

import unittest
from lammps_vmd_tool.core.periodic_table import (
    guess_element_from_mass,
    extract_element_from_comment,
    get_element_info
)


class TestPeriodicTable(unittest.TestCase):
    def test_comment_extraction(self):
        self.assertEqual(extract_element_from_comment("# C"), "C")
        self.assertEqual(extract_element_from_comment("# C_sp2"), "C")
        self.assertEqual(extract_element_from_comment("# OW water oxygen"), "O")
        self.assertEqual(extract_element_from_comment("# HW1 hydrogen"), "H")
        self.assertEqual(extract_element_from_comment("# Fe3+ iron ion"), "Fe")
        self.assertEqual(extract_element_from_comment("# Silicon Si"), "Si")

    def test_mass_matching(self):
        # Without comment, match by mass
        elem, info = guess_element_from_mass(12.011)
        self.assertEqual(elem, "C")
        self.assertEqual(info.name, "Carbon")

        elem, info = guess_element_from_mass(1.008)
        self.assertEqual(elem, "H")

        elem, info = guess_element_from_mass(15.9994)
        self.assertEqual(elem, "O")

        elem, info = guess_element_from_mass(28.085)
        self.assertEqual(elem, "Si")

        elem, info = guess_element_from_mass(55.845)
        self.assertEqual(elem, "Fe")

        elem, info = guess_element_from_mass(63.546)
        self.assertEqual(elem, "Cu")

    def test_element_info(self):
        c_info = get_element_info("C")
        self.assertEqual(c_info.symbol, "C")
        self.assertEqual(c_info.vdw_radius, 1.70)
        self.assertEqual(c_info.vmd_color, "cyan")

        unknown = get_element_info("NonExistent")
        self.assertEqual(unknown.symbol, "X")


if __name__ == "__main__":
    unittest.main()

