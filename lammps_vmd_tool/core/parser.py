"""
LAMMPS Data file parser.
Extracts header information, simulation box, masses, atom types, and auto-detects atom style.
"""

from dataclasses import dataclass, field
import os
import re
from typing import Dict, List, Optional, Tuple, Any

from .box_math import SimulationBox
from .periodic_table import guess_element_from_mass, get_element_info, ElementInfo


@dataclass
class AtomTypeData:
    type_id: int
    mass: float
    comment: str
    element: str
    element_info: ElementInfo
    radius: float
    color: str


@dataclass
class LammpsDataInfo:
    filepath: str
    title: str
    num_atoms: int = 0
    num_atom_types: int = 0
    num_bonds: int = 0
    num_bond_types: int = 0
    num_angles: int = 0
    num_angle_types: int = 0
    num_dihedrals: int = 0
    num_impropers: int = 0
    box: Optional[SimulationBox] = None
    atom_style: str = "full"
    atom_style_detected: bool = False
    atom_types: Dict[int, AtomTypeData] = field(default_factory=dict)
    sample_atoms: List[Dict[str, Any]] = field(default_factory=list)


class LammpsDataParser:
    """Parser for LAMMPS data files."""

    KNOWN_STYLES = ["full", "molecular", "atomic", "charge", "dipole", "metal"]

    @classmethod
    def parse(cls, filepath: str) -> LammpsDataInfo:
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        info = LammpsDataInfo(filepath=os.path.abspath(filepath), title="")
        
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        if not lines:
            raise ValueError("Empty LAMMPS data file")

        # First line is title / description
        info.title = lines[0].strip()

        # Parse header
        line_idx = 1
        num_lines = len(lines)

        xlo = xhi = ylo = yhi = zlo = zhi = 0.0
        xy = xz = yz = 0.0
        is_triclinic = False
        box_parsed = False

        sections: Dict[str, int] = {}  # section name -> line number

        # Section keywords in LAMMPS data files
        section_names = {
            "masses", "atoms", "velocities", "bonds", "angles",
            "dihedrals", "impropers", "pair coeffs", "bond coeffs",
            "angle coeffs", "dihedral coeffs", "improper coeffs"
        }

        while line_idx < num_lines:
            raw_line = lines[line_idx]
            clean_line = raw_line.split("#")[0].strip()
            
            # Check if this line starts a section
            lower_clean = clean_line.lower()
            matched_section = None
            for sec in section_names:
                if lower_clean == sec or lower_clean.startswith(sec + " "):
                    matched_section = sec
                    break
            
            # Also check if raw line has comments like "Atoms # full"
            lower_raw = raw_line.strip().lower()
            for sec in section_names:
                if lower_raw.startswith(sec):
                    matched_section = sec
                    # Check for inline style hint e.g., "Atoms # full"
                    if sec == "atoms" and "#" in raw_line:
                        comment_part = raw_line.split("#", 1)[1].strip().lower()
                        for s in cls.KNOWN_STYLES:
                            if s in comment_part:
                                info.atom_style = s
                                info.atom_style_detected = True
                    break

            if matched_section:
                sections[matched_section] = line_idx
                line_idx += 1
                continue

            if not clean_line:
                line_idx += 1
                continue

            # Header counts
            m = re.match(r"^(\d+)\s+atoms\b", clean_line, re.I)
            if m:
                info.num_atoms = int(m.group(1))
                line_idx += 1
                continue

            m = re.match(r"^(\d+)\s+atom types\b", clean_line, re.I)
            if m:
                info.num_atom_types = int(m.group(1))
                line_idx += 1
                continue

            m = re.match(r"^(\d+)\s+bonds\b", clean_line, re.I)
            if m:
                info.num_bonds = int(m.group(1))
                line_idx += 1
                continue

            m = re.match(r"^(\d+)\s+bond types\b", clean_line, re.I)
            if m:
                info.num_bond_types = int(m.group(1))
                line_idx += 1
                continue

            m = re.match(r"^(\d+)\s+angles\b", clean_line, re.I)
            if m:
                info.num_angles = int(m.group(1))
                line_idx += 1
                continue

            m = re.match(r"^(\d+)\s+angle types\b", clean_line, re.I)
            if m:
                info.num_angle_types = int(m.group(1))
                line_idx += 1
                continue

            m = re.match(r"^(\d+)\s+dihedrals\b", clean_line, re.I)
            if m:
                info.num_dihedrals = int(m.group(1))
                line_idx += 1
                continue

            m = re.match(r"^(\d+)\s+impropers\b", clean_line, re.I)
            if m:
                info.num_impropers = int(m.group(1))
                line_idx += 1
                continue

            # Box bounds
            m = re.match(r"^([-\d\.eE+]+)\s+([-\d\.eE+]+)\s+xlo\s+xhi\b", clean_line, re.I)
            if m:
                xlo, xhi = float(m.group(1)), float(m.group(2))
                box_parsed = True
                line_idx += 1
                continue

            m = re.match(r"^([-\d\.eE+]+)\s+([-\d\.eE+]+)\s+ylo\s+yhi\b", clean_line, re.I)
            if m:
                ylo, yhi = float(m.group(1)), float(m.group(2))
                box_parsed = True
                line_idx += 1
                continue

            m = re.match(r"^([-\d\.eE+]+)\s+([-\d\.eE+]+)\s+zlo\s+zhi\b", clean_line, re.I)
            if m:
                zlo, zhi = float(m.group(1)), float(m.group(2))
                box_parsed = True
                line_idx += 1
                continue

            m = re.match(r"^([-\d\.eE+]+)\s+([-\d\.eE+]+)\s+([-\d\.eE+]+)\s+xy\s+xz\s+yz\b", clean_line, re.I)
            if m:
                xy, xz, yz = float(m.group(1)), float(m.group(2)), float(m.group(3))
                is_triclinic = True
                line_idx += 1
                continue

            line_idx += 1

        if box_parsed:
            info.box = SimulationBox(
                xlo=xlo, xhi=xhi,
                ylo=ylo, yhi=yhi,
                zlo=zlo, zhi=zhi,
                xy=xy, xz=xz, yz=yz,
                is_triclinic=is_triclinic
            )

        # Parse Masses section
        raw_masses: Dict[int, Tuple[float, str]] = {}
        if "masses" in sections:
            m_idx = sections["masses"] + 1
            while m_idx < num_lines:
                line = lines[m_idx].strip()
                m_idx += 1
                if not line:
                    continue
                # If we encounter another section keyword, stop
                first_word = line.split()[0].lower()
                if first_word in section_names:
                    break
                
                comment = ""
                if "#" in line:
                    parts = line.split("#", 1)
                    line_data = parts[0].strip()
                    comment = parts[1].strip()
                else:
                    line_data = line

                tokens = line_data.split()
                if len(tokens) >= 2:
                    try:
                        tid = int(tokens[0])
                        mass = float(tokens[1])
                        raw_masses[tid] = (mass, comment)
                    except ValueError:
                        continue

        # Parse Atoms section to detect style and grab sample atoms
        atom_lines = []
        if "atoms" in sections:
            a_idx = sections["atoms"] + 1
            while a_idx < num_lines:
                line = lines[a_idx].strip()
                a_idx += 1
                if not line:
                    continue
                first_word = line.split()[0].lower()
                if first_word in section_names:
                    break
                
                # Exclude comment-only lines
                if line.startswith("#"):
                    continue

                atom_lines.append(line)
                if len(atom_lines) >= 20:  # Grab first 20 for style detection & sample
                    break

        # Detect atom style if not already detected from section comment
        if not info.atom_style_detected and atom_lines:
            info.atom_style = cls._detect_atom_style(atom_lines, info.num_bonds, info.num_atom_types)
            info.atom_style_detected = True

        # Process atom types (1 to num_atom_types)
        num_types = info.num_atom_types or max(raw_masses.keys(), default=1)
        for tid in range(1, num_types + 1):
            mass, comment = raw_masses.get(tid, (0.0, ""))
            elem, elem_info = guess_element_from_mass(mass, comment)
            info.atom_types[tid] = AtomTypeData(
                type_id=tid,
                mass=mass,
                comment=comment,
                element=elem,
                element_info=elem_info,
                radius=elem_info.vdw_radius,
                color=elem_info.vmd_color
            )

        return info

    @classmethod
    def _detect_atom_style(cls, sample_lines: List[str], num_bonds: int, num_types: int) -> str:
        """
        Detects atom_style from column structure:
        - full: id mol type q x y z (7 cols, or 10 with ix iy iz)
        - molecular: id mol type x y z (6 cols, or 9 with ix iy iz)
        - charge: id type q x y z (6 cols, or 9 with ix iy iz)
        - atomic: id type x y z (5 cols, or 8 with ix iy iz)
        """
        first_line = sample_lines[0].split("#")[0].strip()
        tokens = first_line.split()
        ncols = len(tokens)

        # 5 or 8 columns: atomic
        if ncols in (5, 8):
            return "atomic"

        # 7 or 10 columns: full
        if ncols in (7, 10):
            return "full"

        # 6 or 9 columns: could be molecular or charge
        if ncols in (6, 9):
            # Check if token[2] is likely a float charge vs int type
            try:
                # In 'charge': id type q x y z -> token[1] is type (int), token[2] is charge (float)
                # In 'molecular': id mol type x y z -> token[1] is mol (int), token[2] is type (int)
                val2 = float(tokens[2])
                # If val2 has a decimal part or is negative, it's very likely a charge
                if ("." in tokens[2] and not tokens[2].endswith(".0")) or val2 < 0:
                    return "charge"
                # If num_bonds > 0, molecular is standard
                if num_bonds > 0:
                    return "molecular"
            except ValueError:
                pass
            return "molecular"

        # Fallback default
        if num_bonds > 0:
            return "full"
        return "atomic"
