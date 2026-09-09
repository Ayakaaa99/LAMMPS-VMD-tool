"""
Command-line interface (CLI) for LAMMPS to VMD visualizer.
"""

import argparse
import os
import sys
from typing import Optional

from ..core.parser import LammpsDataParser
from ..core.periodic_table import get_element_info
from ..core.vmd_generator import VmdScriptGenerator, VisualSettings
from ..core.launcher import find_vmd_executable, launch_vmd


def parse_element_mappings(mapping_str: str) -> dict:
    """
    Parses mappings like "1:C,2:H,3:O" into {1: 'C', 2: 'H', 3: 'O'}.
    """
    result = {}
    if not mapping_str:
        return result
    pairs = mapping_str.split(",")
    for pair in pairs:
        if ":" in pair:
            tid_str, sym = pair.split(":", 1)
            try:
                result[int(tid_str.strip())] = sym.strip().capitalize()
            except ValueError:
                pass
    return result


def main(args=None):
    parser = argparse.ArgumentParser(
        description="LAMMPS Data to VMD Visualization Tool - Convert, style, and launch directly in VMD."
    )
    parser.add_argument("data_file", nargs="?", default="", help="Path to LAMMPS data file (.data / .lmp)")
    parser.add_argument("-s", "--style", choices=["full", "molecular", "atomic", "charge", "dipole", "metal"],
                        help="Override atom style (auto-detected if omitted)")
    parser.add_argument("-p", "--preset", choices=["publication", "ball_and_stick", "vdw_spacefill", "licorice"],
                        default="publication", help="Visualization preset (default: publication)")
    parser.add_argument("-m", "--mapping", help="Custom element mapping, e.g. '1:C,2:H,3:O'")
    parser.add_argument("-o", "--output", help="Save generated VMD script to specified file (.vmd / .tcl)")
    parser.add_argument("-l", "--launch", action="store_true", help="Directly launch VMD with generated script")
    parser.add_argument("--vmd-path", help="Path to vmd.exe executable")
    parser.add_argument("--bg", choices=["white", "black"], default=None, help="Background color")
    parser.add_argument("--no-box", action="store_true", help="Disable simulation box drawing")
    parser.add_argument("--gui", action="store_true", help="Open the graphical user interface (GUI)")

    parsed = parser.parse_args(args)

    if parsed.gui or not parsed.data_file:
        from ..gui.app import LammpsVmdApp
        app = LammpsVmdApp(initial_file=parsed.data_file)
        app.mainloop()
        return 0

    if not os.path.isfile(parsed.data_file):
        print(f"Error: File not found: {parsed.data_file}", file=sys.stderr)
        return 1

    print(f"[*] Parsing LAMMPS data file: {parsed.data_file}")
    info = LammpsDataParser.parse(parsed.data_file)

    style = parsed.style or info.atom_style
    print(f"[*] System: {info.num_atoms} atoms, {info.num_bonds} bonds, style='{style}'")
    if info.box:
        print(f"[*] Box: lx={info.box.lx:.2f}, ly={info.box.ly:.2f}, lz={info.box.lz:.2f} A (triclinic={info.box.is_triclinic})")

    # Apply custom mapping if provided
    atom_types = dict(info.atom_types)
    custom_map = parse_element_mappings(parsed.mapping)
    for tid, sym in custom_map.items():
        if tid in atom_types:
            einfo = get_element_info(sym)
            atom_types[tid].element = sym
            atom_types[tid].element_info = einfo
            atom_types[tid].radius = einfo.vdw_radius
            atom_types[tid].color = einfo.vmd_color

    print("[*] Atom type element assignments:")
    for tid, tdata in sorted(atom_types.items()):
        print(f"    Type {tid}: mass={tdata.mass:.3f} amu -> Element {tdata.element} (radius={tdata.radius:.2f} A, color={tdata.color})")

    # Visual settings
    settings = VmdScriptGenerator.PRESETS.get(parsed.preset, VmdScriptGenerator.PRESETS["publication"])
    if parsed.bg:
        settings.bg_color = parsed.bg
    if parsed.no_box:
        settings.show_box = False

    script_content = VmdScriptGenerator.generate(
        info=info,
        atom_types=atom_types,
        settings=settings,
        custom_atom_style=style
    )

    out_file = parsed.output
    if not out_file:
        base, _ = os.path.splitext(parsed.data_file)
        out_file = f"{base}_view.vmd"

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(script_content)
    print(f"[OK] VMD script generated: {out_file}")

    if parsed.launch:
        exe = find_vmd_executable(parsed.vmd_path)
        if not exe:
            print("[!] Could not auto-detect VMD. Please pass --vmd-path <path/to/vmd.exe>", file=sys.stderr)
            return 1
        print(f"[*] Launching VMD ({exe})...")
        launch_vmd(out_file, exe)

    return 0


if __name__ == "__main__":
    sys.exit(main())
