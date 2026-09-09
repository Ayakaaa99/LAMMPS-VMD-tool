"""
Simulation box geometry calculations for LAMMPS and VMD.
Supports both orthogonal and triclinic (tilted) simulation boxes.
"""

from dataclasses import dataclass
import math
from typing import Tuple, Optional


@dataclass
class SimulationBox:
    xlo: float
    xhi: float
    ylo: float
    yhi: float
    zlo: float
    zhi: float
    xy: float = 0.0
    xz: float = 0.0
    yz: float = 0.0
    is_triclinic: bool = False

    @property
    def lx(self) -> float:
        return self.xhi - self.xlo

    @property
    def ly(self) -> float:
        return self.yhi - self.ylo

    @property
    def lz(self) -> float:
        return self.zhi - self.zlo

    @property
    def volume(self) -> float:
        """Volume of simulation cell."""
        return self.lx * self.ly * self.lz

    @property
    def origin(self) -> Tuple[float, float, float]:
        return (self.xlo, self.ylo, self.zlo)

    @property
    def center(self) -> Tuple[float, float, float]:
        """Center of the unit cell."""
        cx = self.xlo + 0.5 * (self.lx + self.xy + self.xz)
        cy = self.ylo + 0.5 * (self.ly + self.yz)
        cz = self.zlo + 0.5 * self.lz
        return (cx, cy, cz)

    def to_vmd_unitcell(self) -> Tuple[float, float, float, float, float, float]:
        """
        Converts LAMMPS box parameters to VMD unit cell parameters:
        (a, b, c, alpha, beta, gamma)
        Angles are in degrees.
        """
        lx, ly, lz = self.lx, self.ly, self.lz
        xy, xz, yz = self.xy, self.xz, self.yz

        if not self.is_triclinic or (xy == 0.0 and xz == 0.0 and yz == 0.0):
            return (lx, ly, lz, 90.0, 90.0, 90.0)

        # Cell vector lengths
        a = lx
        b = math.sqrt(xy**2 + ly**2)
        c = math.sqrt(xz**2 + yz**2 + lz**2)

        # Angles
        cos_alpha = (xy * xz + ly * yz) / (b * c)
        cos_beta = xz / c
        cos_gamma = xy / b

        # Clamp values to [-1.0, 1.0] to avoid floating point precision issues with acos
        cos_alpha = max(-1.0, min(1.0, cos_alpha))
        cos_beta = max(-1.0, min(1.0, cos_beta))
        cos_gamma = max(-1.0, min(1.0, cos_gamma))

        alpha = math.degrees(math.acos(cos_alpha))
        beta = math.degrees(math.acos(cos_beta))
        gamma = math.degrees(math.acos(cos_gamma))

        return (a, b, c, alpha, beta, gamma)
