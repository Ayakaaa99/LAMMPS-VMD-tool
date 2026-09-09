"""
Unit tests for simulation box geometry calculations (orthogonal and triclinic).
"""

import math
import unittest
from lammps_vmd_tool.core.box_math import SimulationBox


class TestBoxMath(unittest.TestCase):
    def test_orthogonal_box(self):
        box = SimulationBox(
            xlo=0.0, xhi=10.0,
            ylo=0.0, yhi=20.0,
            zlo=-5.0, zhi=15.0,
            is_triclinic=False
        )
        self.assertAlmostEqual(box.lx, 10.0)
        self.assertAlmostEqual(box.ly, 20.0)
        self.assertAlmostEqual(box.lz, 20.0)
        self.assertAlmostEqual(box.volume, 4000.0)

        a, b, c, alpha, beta, gamma = box.to_vmd_unitcell()
        self.assertAlmostEqual(a, 10.0)
        self.assertAlmostEqual(b, 20.0)
        self.assertAlmostEqual(c, 20.0)
        self.assertAlmostEqual(alpha, 90.0)
        self.assertAlmostEqual(beta, 90.0)
        self.assertAlmostEqual(gamma, 90.0)

    def test_triclinic_box(self):
        # Tilted box: a = 10, b = 10, c = 10 with xy = 5.0
        # b vector is (5.0, 10.0, 0), length = sqrt(25+100) = sqrt(125) approx 11.1803
        # cos(gamma) = 5.0 / sqrt(125) = 1/sqrt(5) -> gamma approx 63.435 deg
        box = SimulationBox(
            xlo=0.0, xhi=10.0,
            ylo=0.0, yhi=10.0,
            zlo=0.0, zhi=10.0,
            xy=5.0, xz=0.0, yz=0.0,
            is_triclinic=True
        )
        a, b, c, alpha, beta, gamma = box.to_vmd_unitcell()
        self.assertAlmostEqual(a, 10.0)
        self.assertAlmostEqual(b, math.sqrt(125), places=3)
        self.assertAlmostEqual(c, 10.0)
        self.assertAlmostEqual(alpha, 90.0)
        self.assertAlmostEqual(beta, 90.0)
        self.assertAlmostEqual(gamma, math.degrees(math.acos(5.0 / math.sqrt(125))), places=2)


if __name__ == "__main__":
    unittest.main()

