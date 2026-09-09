"""
Periodic Table database and smart element inference for LAMMPS data files.
Provides element masses, van der Waals radii, standard colors, and matching logic.
"""

from dataclasses import dataclass
import re
from typing import Optional, Dict, Tuple

@dataclass
class ElementInfo:
    symbol: str
    name: str
    atomic_number: int
    mass: float
    vdw_radius: float  # Angstroms
    vmd_color: str     # VMD predefined color name or index
    hex_color: str     # Hex code for GUI preview


# Standard elements table commonly found in molecular/materials simulations
ELEMENTS_DB: Dict[str, ElementInfo] = {
    "H":  ElementInfo("H",  "Hydrogen",   1,   1.008,  1.20, "white",     "#FFFFFF"),
    "He": ElementInfo("He", "Helium",     2,   4.0026, 1.40, "cyan",      "#D9FFFF"),
    "Li": ElementInfo("Li", "Lithium",    3,   6.94,   1.82, "purple",    "#CC80FF"),
    "Be": ElementInfo("Be", "Beryllium",  4,   9.0122, 1.53, "green",     "#C2FF00"),
    "B":  ElementInfo("B",  "Boron",      5,  10.81,   1.92, "pink",      "#FFB5B5"),
    "C":  ElementInfo("C",  "Carbon",     6,  12.011,  1.70, "cyan",      "#909090"),
    "N":  ElementInfo("N",  "Nitrogen",   7,  14.007,  1.55, "blue",      "#3050F8"),
    "O":  ElementInfo("O",  "Oxygen",     8,  15.999,  1.52, "red",       "#FF0D0D"),
    "F":  ElementInfo("F",  "Fluorine",   9,  18.998,  1.47, "green",     "#90E050"),
    "Ne": ElementInfo("Ne", "Neon",      10,  20.180,  1.54, "cyan",      "#B3E3F5"),
    "Na": ElementInfo("Na", "Sodium",    11,  22.990,  2.27, "yellow",    "#AB5CF2"),
    "Mg": ElementInfo("Mg", "Magnesium", 12,  24.305,  1.73, "green",     "#8AFF00"),
    "Al": ElementInfo("Al", "Aluminum",  13,  26.982,  1.84, "silver",    "#BFA6A6"),
    "Si": ElementInfo("Si", "Silicon",   14,  28.085,  2.10, "ochre",     "#F0C8A0"),
    "P":  ElementInfo("P",  "Phosphorus",15,  30.974,  1.80, "orange",    "#FF8000"),
    "S":  ElementInfo("S",  "Sulfur",    16,  32.06,   1.80, "yellow",    "#FFFF30"),
    "Cl": ElementInfo("Cl", "Chlorine",  17,  35.45,   1.75, "green",     "#1FF01F"),
    "Ar": ElementInfo("Ar", "Argon",     18,  39.948,  1.88, "cyan",      "#80D1E3"),
    "K":  ElementInfo("K",  "Potassium", 19,  39.098,  2.75, "purple",    "#8F40D4"),
    "Ca": ElementInfo("Ca", "Calcium",   20,  40.078,  2.31, "green",     "#3DFF00"),
    "Sc": ElementInfo("Sc", "Scandium",  21,  44.956,  2.11, "silver",    "#E6E6E6"),
    "Ti": ElementInfo("Ti", "Titanium",  22,  47.867,  2.00, "silver",    "#BFC2C7"),
    "V":  ElementInfo("V",  "Vanadium",  23,  50.942,  2.00, "silver",    "#A6A6AB"),
    "Cr": ElementInfo("Cr", "Chromium",  24,  51.996,  2.00, "blue2",     "#8A99C7"),
    "Mn": ElementInfo("Mn", "Manganese", 25,  54.938,  2.00, "purple2",   "#9C7AC7"),
    "Fe": ElementInfo("Fe", "Iron",      26,  55.845,  2.00, "orange2",   "#E06633"),
    "Co": ElementInfo("Co", "Cobalt",    27,  58.933,  2.00, "pink2",     "#F090A0"),
    "Ni": ElementInfo("Ni", "Nickel",    28,  58.693,  1.63, "green2",    "#50D050"),
    "Cu": ElementInfo("Cu", "Copper",    29,  63.546,  1.40, "ochre",     "#C88033"),
    "Zn": ElementInfo("Zn", "Zinc",      30,  65.38,   1.39, "silver",    "#7D80B0"),
    "Ga": ElementInfo("Ga", "Gallium",   31,  69.723,  1.87, "silver",    "#C28F8F"),
    "Ge": ElementInfo("Ge", "Germanium", 32,  72.63,   2.11, "silver",    "#668F8F"),
    "As": ElementInfo("As", "Arsenic",   33,  74.922,  1.85, "orange",    "#BD80E3"),
    "Se": ElementInfo("Se", "Selenium",  34,  78.971,  1.90, "yellow",    "#FFA100"),
    "Br": ElementInfo("Br", "Bromine",   35,  79.904,  1.85, "red2",      "#A62929"),
    "Kr": ElementInfo("Kr", "Krypton",   36,  83.798,  2.02, "cyan",      "#5CB8D1"),
    "Rb": ElementInfo("Rb", "Rubidium",  37,  85.468,  3.03, "purple",    "#702EB0"),
    "Sr": ElementInfo("Sr", "Strontium", 38,  87.62,   2.49, "green",     "#00FF00"),
    "Y":  ElementInfo("Y",  "Yttrium",   39,  88.906,  2.00, "silver",    "#94FFFF"),
    "Zr": ElementInfo("Zr", "Zirconium", 40,  91.224,  2.00, "silver",    "#94E0E0"),
    "Nb": ElementInfo("Nb", "Niobium",   41,  92.906,  2.00, "silver",    "#73C2C9"),
    "Mo": ElementInfo("Mo", "Molybdenum",42,  95.95,   2.00, "cyan2",     "#54B5B5"),
    "Ru": ElementInfo("Ru", "Ruthenium", 44, 101.07,   2.00, "silver",    "#248F8F"),
    "Rh": ElementInfo("Rh", "Rhodium",   45, 102.91,   2.00, "silver",    "#0A7D8C"),
    "Pd": ElementInfo("Pd", "Palladium", 46, 106.42,   1.63, "silver",    "#006985"),
    "Ag": ElementInfo("Ag", "Silver",    47, 107.87,   1.72, "silver",    "#C0C0C0"),
    "Cd": ElementInfo("Cd", "Cadmium",   48, 112.41,   1.58, "silver",    "#FFD98F"),
    "In": ElementInfo("In", "Indium",    49, 114.82,   1.93, "silver",    "#A67573"),
    "Sn": ElementInfo("Sn", "Tin",       50, 118.71,   2.17, "silver",    "#668080"),
    "Sb": ElementInfo("Sb", "Antimony",  51, 121.76,   2.06, "silver",    "#9E63B5"),
    "Te": ElementInfo("Te", "Tellurium", 52, 127.60,   2.06, "yellow",    "#D47A00"),
    "I":  ElementInfo("I",  "Iodine",    53, 126.90,   1.98, "purple",    "#940094"),
    "Xe": ElementInfo("Xe", "Xenon",     54, 131.29,   2.16, "cyan",      "#429EB0"),
    "Cs": ElementInfo("Cs", "Cesium",    55, 132.91,   3.43, "purple",    "#57178F"),
    "Ba": ElementInfo("Ba", "Barium",    56, 137.33,   2.68, "green",     "#00C900"),
    "La": ElementInfo("La", "Lanthanum", 57, 138.91,   2.00, "silver",    "#70D4FF"),
    "Ce": ElementInfo("Ce", "Cerium",    58, 140.12,   2.00, "silver",    "#FFFFC7"),
    "W":  ElementInfo("W",  "Tungsten",  74, 183.84,   2.00, "silver",    "#2194D6"),
    "Pt": ElementInfo("Pt", "Platinum",  78, 195.08,   1.75, "silver",    "#D0D0E0"),
    "Au": ElementInfo("Au", "Gold",      79, 196.97,   1.66, "yellow",    "#FFD123"),
    "Hg": ElementInfo("Hg", "Mercury",   80, 200.59,   1.55, "silver",    "#B8B8D0"),
    "Pb": ElementInfo("Pb", "Lead",      82, 207.2,    2.02, "silver",    "#575961"),
    "Bi": ElementInfo("Bi", "Bismuth",   83, 208.98,   2.07, "purple",    "#9E4FB5"),
    "U":  ElementInfo("U",  "Uranium",   92, 238.03,   1.86, "green",     "#008FFF"),
}

UNKNOWN_ELEMENT = ElementInfo("X", "Unknown", 0, 0.0, 1.5, "silver", "#A0A0A0")


def extract_element_from_comment(comment: str) -> Optional[str]:
    """
    Tries to find a valid element symbol inside a comment line.
    E.g.:
      '# C' -> 'C'
      '# C_sp2' -> 'C'
      '# OW' -> 'O'
      '# HW1' -> 'H'
      '# Fe3+' -> 'Fe'
      '# Type 1 is C' -> 'C'
    """
    if not comment:
        return None
    
    clean = comment.lstrip("#").strip()
    tokens = re.split(r"[\s,;:=]+", clean)
    for token in tokens:
        if not token:
            continue
        # Check direct match
        token_cap = token.capitalize()
        if token_cap in ELEMENTS_DB:
            return token_cap
        # Check 2-letter then 1-letter match (e.g. Fe in Fe_atom, Cl in Cl1, O in OW)
        for length in [2, 1]:
            candidate = token[:length].capitalize()
            if candidate in ELEMENTS_DB:
                return candidate
    return None


def guess_element_from_mass(mass: float, comment: str = "") -> Tuple[str, ElementInfo]:
    """
    Guesses the chemical element based on comment first, then atomic mass.
    Returns (symbol, ElementInfo).
    """
    # 1. Try comment first
    from_comment = extract_element_from_comment(comment)
    if from_comment and from_comment in ELEMENTS_DB:
        return from_comment, ELEMENTS_DB[from_comment]

    if mass <= 0:
        return "X", UNKNOWN_ELEMENT

    # 2. Nearest mass matching
    best_symbol = "X"
    best_info = UNKNOWN_ELEMENT
    min_diff = float("inf")

    for symbol, info in ELEMENTS_DB.items():
        diff = abs(info.mass - mass)
        if diff < min_diff:
            min_diff = diff
            best_symbol = symbol
            best_info = info

    return best_symbol, best_info


def get_element_info(symbol: str) -> ElementInfo:
    """Returns ElementInfo for a given element symbol, or UNKNOWN_ELEMENT."""
    sym = symbol.strip().capitalize()
    return ELEMENTS_DB.get(sym, UNKNOWN_ELEMENT)
