"""
LAMMPS data / trajectory parser.

Supports:
- LAMMPS data files (orthogonal and triclinic boxes, any file suffix).
- LAMMPS text dump trajectories (``lammpstrj`` / ``dump`` / custom columns).

Files are read strictly as UTF-8. A dedicated exception is raised when the
file cannot be decoded so the GUI can show an explicit error dialog.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional, Set, Tuple

from .box_math import SimulationBox
from .periodic_table import (
    ELEMENTS_DB,
    ElementInfo,
    UNKNOWN_ELEMENT,
    guess_element_from_mass,
)


class LammpsFileError(ValueError):
    """Raised when a file cannot be interpreted as LAMMPS input."""


class InvalidEncodingError(LammpsFileError):
    """Raised when the file is not valid UTF-8 text."""


# Fallback palette for atom types whose element cannot be inferred.
TYPE_COLOR_PALETTE = [
    "#E15759",
    "#4E79A7",
    "#59A14F",
    "#F28E2B",
    "#B07AA1",
    "#76B7B2",
    "#EDC948",
    "#FF9DA7",
    "#9C755F",
    "#BAB0AC",
]

# Atom styles accepted by TopoTools / topo readlammpsdata.
STYLE_FALLBACKS = ("full", "molecular", "bond", "angle", "charge", "atomic", "dipole")


@dataclass
class AtomTypeData:
    type_id: int
    mass: float = 0.0
    comment: str = ""
    element: str = "X"
    element_info: ElementInfo = field(default_factory=lambda: UNKNOWN_ELEMENT)
    radius: float = 1.5
    color: str = "#BAB0AC"  # Hex color used by the GUI and the Tcl generator


@dataclass
class LammpsDataInfo:
    filepath: str
    file_type: str = "data"  # "data" or "dump"
    title: str = ""
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

    @property
    def is_trajectory(self) -> bool:
        return self.file_type == "dump"

    def style_candidates(self) -> List[str]:
        """Styles to try in TopoTools, detected style first."""
        styles: List[str] = []
        if self.atom_style_detected:
            styles.append(self.atom_style)
        for style in STYLE_FALLBACKS:
            if style not in styles:
                styles.append(style)
        return styles


class LammpsDataParser:
    """Parses LAMMPS data files and dump trajectories."""

    KNOWN_STYLES = ["full", "molecular", "atomic", "charge", "dipole", "metal", "bond", "angle"]

    SECTION_NAMES = (
        "masses",
        "atoms",
        "velocities",
        "bonds",
        "angles",
        "dihedrals",
        "impropers",
        "pair coeffs",
        "bond coeffs",
        "angle coeffs",
        "dihedral coeffs",
        "improper coeffs",
    )

    MAX_ATOM_SAMPLE = 60_000

    @classmethod
    def parse(cls, filepath: str) -> LammpsDataInfo:
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"文件不存在: {filepath}")

        if cls._detect_kind(filepath) == "dump":
            return cls._parse_dump(filepath)
        return cls._parse_data(filepath)

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------
    @classmethod
    def _iter_lines(cls, filepath: str) -> Iterator[str]:
        """Yields text lines, raising InvalidEncodingError for non-UTF-8 files."""
        try:
            with open(filepath, "r", encoding="utf-8-sig") as handle:
                for line in handle:
                    yield line
        except UnicodeDecodeError as exc:
            raise InvalidEncodingError(
                "文件不是有效的 UTF-8 编码，无法读取。请将其转换为 UTF-8 后重试。"
            ) from exc
        except OSError as exc:
            raise LammpsFileError(f"无法读取文件: {exc}") from exc

    @classmethod
    def _detect_kind(cls, filepath: str) -> str:
        for index, line in enumerate(cls._iter_lines(filepath)):
            if index >= 60:
                break
            text = line.strip()
            if text.upper().startswith("ITEM:"):
                return "dump"
        return "data"

    @staticmethod
    def _palette_color(type_id: int) -> str:
        return TYPE_COLOR_PALETTE[(max(type_id, 1) - 1) % len(TYPE_COLOR_PALETTE)]

    @classmethod
    def _make_type(cls, type_id: int, mass: float, comment: str) -> AtomTypeData:
        element, element_info = guess_element_from_mass(mass, comment)
        if element == "X" or element_info is UNKNOWN_ELEMENT:
            color = cls._palette_color(type_id)
        else:
            color = element_info.hex_color
        return AtomTypeData(
            type_id=type_id,
            mass=mass,
            comment=comment,
            element=element,
            element_info=element_info,
            radius=element_info.vdw_radius,
            color=color,
        )

    @staticmethod
    def _parse_bounds_block(rows: List[List[float]]) -> Optional[SimulationBox]:
        """Converts the three dump BOX BOUNDS rows into a SimulationBox."""
        if len(rows) != 3 or any(len(row) < 2 for row in rows):
            return None

        is_triclinic = any(len(row) >= 3 for row in rows)
        if is_triclinic:
            xlo_bound, xhi_bound, xy = (rows[0] + [0.0, 0.0, 0.0])[:3]
            ylo_bound, yhi_bound, xz = (rows[1] + [0.0, 0.0, 0.0])[:3]
            zlo_bound, zhi_bound, yz = (rows[2] + [0.0, 0.0, 0.0])[:3]

            xlo = xlo_bound - min(0.0, xy, xz, xy + xz)
            xhi = xhi_bound - max(0.0, xy, xz, xy + xz)
            ylo = ylo_bound - min(0.0, yz)
            yhi = yhi_bound - max(0.0, yz)
            zlo, zhi = zlo_bound, zhi_bound

            return SimulationBox(
                xlo=xlo,
                xhi=xhi,
                ylo=ylo,
                yhi=yhi,
                zlo=zlo,
                zhi=zhi,
                xy=xy,
                xz=xz,
                yz=yz,
                is_triclinic=True,
            )

        return SimulationBox(
            xlo=rows[0][0],
            xhi=rows[0][1],
            ylo=rows[1][0],
            yhi=rows[1][1],
            zlo=rows[2][0],
            zhi=rows[2][1],
        )

    # ------------------------------------------------------------------
    # Data file
    # ------------------------------------------------------------------
    @classmethod
    def _parse_data(cls, filepath: str) -> LammpsDataInfo:
        info = LammpsDataInfo(filepath=os.path.abspath(filepath), file_type="data")

        num_lines = 0
        masses: Dict[int, Tuple[float, str]] = {}
        atom_sample: List[str] = []
        current_section: Optional[str] = None

        xlo = xhi = ylo = yhi = zlo = zhi = 0.0
        xy = xz = yz = 0.0
        is_triclinic = False
        box_parsed = False

        for index, raw_line in enumerate(cls._iter_lines(filepath)):
            num_lines += 1
            if index == 0:
                info.title = raw_line.strip()
                continue

            clean_line = raw_line.split("#", 1)[0].strip()
            lower_clean = clean_line.lower()

            # Section headers
            matched_section = None
            for section in cls.SECTION_NAMES:
                if lower_clean == section or lower_clean.startswith(section + " "):
                    matched_section = section
                    break
            if matched_section:
                current_section = matched_section
                if matched_section == "atoms":
                    hint = cls._style_from_line(raw_line)
                    if hint:
                        info.atom_style = hint
                        info.atom_style_detected = True
                continue

            if not clean_line:
                continue

            # Header counts
            match = re.match(r"^(\d+)\s+atoms\b", clean_line, re.I)
            if match:
                info.num_atoms = int(match.group(1))
                continue
            match = re.match(r"^(\d+)\s+atom\s+types\b", clean_line, re.I)
            if match:
                info.num_atom_types = int(match.group(1))
                continue
            match = re.match(r"^(\d+)\s+bonds\b", clean_line, re.I)
            if match:
                info.num_bonds = int(match.group(1))
                continue
            match = re.match(r"^(\d+)\s+bond\s+types\b", clean_line, re.I)
            if match:
                info.num_bond_types = int(match.group(1))
                continue
            match = re.match(r"^(\d+)\s+angles\b", clean_line, re.I)
            if match:
                info.num_angles = int(match.group(1))
                continue
            match = re.match(r"^(\d+)\s+angle\s+types\b", clean_line, re.I)
            if match:
                info.num_angle_types = int(match.group(1))
                continue
            match = re.match(r"^(\d+)\s+dihedrals\b", clean_line, re.I)
            if match:
                info.num_dihedrals = int(match.group(1))
                continue
            match = re.match(r"^(\d+)\s+impropers\b", clean_line, re.I)
            if match:
                info.num_impropers = int(match.group(1))
                continue

            # Box bounds
            match = re.match(r"^([-\d.eE+]+)\s+([-\d.eE+]+)\s+xlo\s+xhi\b", clean_line, re.I)
            if match:
                xlo, xhi = float(match.group(1)), float(match.group(2))
                box_parsed = True
                continue
            match = re.match(r"^([-\d.eE+]+)\s+([-\d.eE+]+)\s+ylo\s+yhi\b", clean_line, re.I)
            if match:
                ylo, yhi = float(match.group(1)), float(match.group(2))
                box_parsed = True
                continue
            match = re.match(r"^([-\d.eE+]+)\s+([-\d.eE+]+)\s+zlo\s+zhi\b", clean_line, re.I)
            if match:
                zlo, zhi = float(match.group(1)), float(match.group(2))
                box_parsed = True
                continue
            match = re.match(
                r"^([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s+xy\s+xz\s+yz\b",
                clean_line,
                re.I,
            )
            if match:
                xy, xz, yz = float(match.group(1)), float(match.group(2)), float(match.group(3))
                is_triclinic = True
                continue

            if current_section == "masses":
                tokens = clean_line.split()
                if len(tokens) >= 2 and tokens[0].isdigit():
                    try:
                        mass = float(tokens[1])
                    except ValueError:
                        continue
                    comment = ""
                    if "#" in raw_line:
                        comment = raw_line.split("#", 1)[1].strip()
                    masses[int(tokens[0])] = (mass, comment)

            elif current_section == "atoms":
                if not raw_line.lstrip().startswith("#"):
                    atom_sample.append(clean_line)

            # Masses precede Atoms in conventional data files; stop after a
            # small atom sample so very large files load instantly.
            if len(atom_sample) >= 20 and current_section == "atoms":
                break

        if num_lines == 0:
            raise LammpsFileError("文件为空。")
        if not info.num_atoms and not masses and not box_parsed:
            raise LammpsFileError(
                "无法识别该文件：既不是 LAMMPS data 文件，也不是 LAMMPS dump 轨迹文件。"
            )

        if box_parsed:
            info.box = SimulationBox(
                xlo=xlo,
                xhi=xhi,
                ylo=ylo,
                yhi=yhi,
                zlo=zlo,
                zhi=zhi,
                xy=xy,
                xz=xz,
                yz=yz,
                is_triclinic=is_triclinic,
            )

        if not info.atom_style_detected and atom_sample:
            info.atom_style = cls._detect_atom_style(atom_sample, info.num_bonds)
            info.atom_style_detected = True

        type_count = info.num_atom_types or (max(masses) if masses else 0)
        for type_id in range(1, type_count + 1):
            mass, comment = masses.get(type_id, (0.0, ""))
            info.atom_types[type_id] = cls._make_type(type_id, mass, comment)
        info.num_atom_types = len(info.atom_types)

        return info

    @classmethod
    def _style_from_line(cls, raw_line: str) -> Optional[str]:
        if "#" not in raw_line:
            return None
        comment = raw_line.split("#", 1)[1].strip().lower()
        for style in cls.KNOWN_STYLES:
            if re.search(rf"\b{re.escape(style)}\b", comment):
                return style
        return None

    @classmethod
    def _detect_atom_style(cls, sample_lines: List[str], num_bonds: int) -> str:
        """
        Detects atom_style from the column count:
        - atomic: id type x y z (5 / 8 cols)
        - full: id mol type q x y z (7 / 10 cols)
        - charge: id type q x y z (6 / 9 cols)
        - molecular / bond / angle: id mol type x y z (6 / 9 cols)
        """
        if not sample_lines:
            return "full"

        tokens = sample_lines[0].split("#", 1)[0].split()
        ncols = len(tokens)

        if ncols in (5, 8):
            return "atomic"
        if ncols in (7, 10):
            return "full"
        if ncols in (6, 9):
            try:
                value = float(tokens[2])
                if ("." in tokens[2] and not tokens[2].endswith(".0")) or value < 0:
                    return "charge"
            except ValueError:
                pass
            return "molecular"

        return "full" if num_bonds > 0 else "atomic"

    # ------------------------------------------------------------------
    # Dump trajectory
    # ------------------------------------------------------------------
    @classmethod
    def _parse_dump(cls, filepath: str) -> LammpsDataInfo:
        info = LammpsDataInfo(filepath=os.path.abspath(filepath), file_type="dump")

        pending: Optional[str] = None
        num_atoms: Optional[int] = None
        box_rows: List[List[float]] = []
        columns: List[str] = []
        type_index: Optional[int] = None
        element_index: Optional[int] = None
        remaining_atoms = 0
        sampled = 0
        type_elements: Dict[int, str] = {}
        seen_types: Set[int] = set()

        for raw_line in cls._iter_lines(filepath):
            text = raw_line.strip()
            if not text:
                continue

            if text.upper().startswith("ITEM:"):
                item = text[5:].strip()
                upper_item = item.upper()

                if upper_item.startswith("TIMESTEP"):
                    pending = "timestep"
                elif upper_item.startswith("NUMBER OF ATOMS"):
                    pending = "natoms"
                elif upper_item.startswith("BOX BOUNDS"):
                    pending = "box"
                    box_rows = []
                elif upper_item.startswith("ATOMS"):
                    pending = "atoms"
                    parts = item.split()
                    columns = [part.strip().lower() for part in parts[1:]]
                    type_index = columns.index("type") if "type" in columns else None
                    element_index = columns.index("element") if "element" in columns else None
                    remaining_atoms = num_atoms or 0
                    sampled = 0
                else:
                    pending = None
                continue

            if pending == "timestep":
                if not info.title:
                    info.title = f"起始步 {text}"
                pending = None
                continue

            if pending == "natoms":
                try:
                    info.num_atoms = int(text.split()[0])
                except (ValueError, IndexError):
                    pass
                num_atoms = info.num_atoms
                pending = None
                continue

            if pending == "box":
                try:
                    values = [float(value) for value in text.split()[:3]]
                except ValueError:
                    continue
                if values:
                    box_rows.append(values)
                if len(box_rows) == 3:
                    info.box = cls._parse_bounds_block(box_rows)
                    pending = None
                continue

            if pending == "atoms":
                if remaining_atoms <= 0 and num_atoms:
                    break
                tokens = text.split()
                if type_index is not None and type_index < len(tokens):
                    try:
                        type_id = int(tokens[type_index])
                    except ValueError:
                        type_id = None
                    if type_id is not None and type_id > 0:
                        seen_types.add(type_id)
                        if element_index is not None and element_index < len(tokens):
                            symbol = tokens[element_index].strip().capitalize()
                            if symbol in ELEMENTS_DB and type_id not in type_elements:
                                type_elements[type_id] = symbol

                remaining_atoms -= 1
                sampled += 1
                if num_atoms and remaining_atoms <= 0:
                    break
                if sampled >= cls.MAX_ATOM_SAMPLE:
                    break

        if not info.num_atoms and not seen_types:
            raise LammpsFileError(
                "无法识别该文件：既不是 LAMMPS data 文件，也不是 LAMMPS dump 轨迹文件。"
            )

        for type_id in sorted(seen_types):
            element = type_elements.get(type_id, "")
            if element:
                element_info = ELEMENTS_DB[element]
                atom_type = AtomTypeData(
                    type_id=type_id,
                    mass=element_info.mass,
                    comment="",
                    element=element,
                    element_info=element_info,
                    radius=element_info.vdw_radius,
                    color=element_info.hex_color,
                )
            else:
                atom_type = AtomTypeData(
                    type_id=type_id,
                    mass=0.0,
                    comment="",
                    element="X",
                    element_info=UNKNOWN_ELEMENT,
                    radius=UNKNOWN_ELEMENT.vdw_radius,
                    color=cls._palette_color(type_id),
                )
            info.atom_types[type_id] = atom_type

        info.num_atom_types = len(info.atom_types)
        info.num_bonds = 0
        info.atom_style_detected = False
        return info
