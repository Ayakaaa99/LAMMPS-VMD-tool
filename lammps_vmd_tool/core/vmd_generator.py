"""
VMD Tcl script generator for LAMMPS data visualization.
Generates publication-quality Tcl visualization scripts with topotools and pbctools.
"""

from dataclasses import dataclass
import os
from typing import Dict, Optional

from .parser import LammpsDataInfo, AtomTypeData


@dataclass
class VisualSettings:
    preset_name: str = "ball_and_stick"
    # Representation: "CPK", "VDW", "Licorice", "DynamicBonds", "Lines"
    rep_style: str = "CPK"
    sphere_scale: float = 0.35
    bond_radius: float = 0.18
    color_by: str = "Element"  # "Element", "Type", "Charge", "Index"
    material: str = "AOChalky"  # "AOChalky", "Diffuse", "Glossy", "Opaque", "Goodsell"
    # Environment
    bg_color: str = "white"     # "white", "black"
    projection: str = "Orthographic"  # "Orthographic", "Perspective"
    show_axes: bool = True
    axes_location: str = "lowerleft"  # "lowerleft", "off"
    depthcue: bool = False
    # Box
    show_box: bool = True
    box_color: str = "black"
    box_width: float = 1.5
    # Auto-bonds
    auto_bonds: bool = False
    bond_cutoff: float = 1.6


class VmdScriptGenerator:
    """Generates VMD startup / visualization Tcl scripts."""

    PRESETS = {
        "publication": VisualSettings(
            preset_name="publication",
            rep_style="CPK",
            sphere_scale=0.35,
            bond_radius=0.18,
            color_by="Type",  # Match explicit type colors
            material="Opaque",  # Vibrant, clear solid color
            bg_color="white",
            projection="Orthographic",
            show_axes=False,
            axes_location="off",
            depthcue=False,
            show_box=True,
            box_color="black",
            box_width=2.0
        ),
        "ball_and_stick": VisualSettings(
            preset_name="ball_and_stick",
            rep_style="CPK",
            sphere_scale=0.32,
            bond_radius=0.16,
            color_by="Type",
            material="Glossy",
            bg_color="black",
            projection="Perspective",
            show_axes=True,
            axes_location="lowerleft",
            depthcue=True,
            show_box=True,
            box_color="cyan",
            box_width=1.5
        ),
        "vdw_spacefill": VisualSettings(
            preset_name="vdw_spacefill",
            rep_style="VDW",
            sphere_scale=1.0,
            bond_radius=0.1,
            color_by="Type",
            material="Opaque",
            bg_color="white",
            projection="Orthographic",
            show_axes=False,
            axes_location="off",
            depthcue=False,
            show_box=True,
            box_color="gray",
            box_width=1.5
        ),
        "licorice": VisualSettings(
            preset_name="licorice",
            rep_style="Licorice",
            sphere_scale=0.25,
            bond_radius=0.25,
            color_by="Type",
            material="Opaque",
            bg_color="black",
            projection="Perspective",
            show_axes=True,
            axes_location="lowerleft",
            depthcue=True,
            show_box=True,
            box_color="yellow",
            box_width=1.5
        )
    }

    @classmethod
    def generate(cls,
                 info: LammpsDataInfo,
                 atom_types: Optional[Dict[int, AtomTypeData]] = None,
                 settings: Optional[VisualSettings] = None,
                 custom_atom_style: Optional[str] = None) -> str:
        """
        Generates full VMD Tcl script text.
        """
        if settings is None:
            settings = cls.PRESETS["publication"]
        if atom_types is None:
            atom_types = info.atom_types

        style = custom_atom_style if custom_atom_style else info.atom_style

        # Normalize filepath to forward slashes for Tcl compatibility on Windows
        clean_path = info.filepath.replace("\\", "/")

        tcl = []
        tcl.append("# ==========================================================")
        tcl.append(f"# VMD Visualization Script generated for LAMMPS Data File")
        tcl.append(f"# Source File: {info.filepath}")
        tcl.append(f"# Atoms: {info.num_atoms}, Bonds: {info.num_bonds}, Style: {style}")
        tcl.append("# ==========================================================\n")

        tcl.append("# Require necessary VMD packages")
        tcl.append("package require topotools 1.7")
        tcl.append("package require pbctools 2.8\n")

        tcl.append("# Load LAMMPS data file using topotools")
        tcl.append(f'puts "Loading LAMMPS data ({style} style)..."')
        tcl.append(f'set molid [topo readlammpsdata "{clean_path}" {style}]\n')

        # Periodic unit cell configuration
        if info.box:
            a, b, c, alpha, beta, gamma = info.box.to_vmd_unitcell()
            tcl.append("# Simulation Box & Unit Cell setup")
            tcl.append(f"molinfo $molid set a {a:.4f}")
            tcl.append(f"molinfo $molid set b {b:.4f}")
            tcl.append(f"molinfo $molid set c {c:.4f}")
            tcl.append(f"molinfo $molid set alpha {alpha:.4f}")
            tcl.append(f"molinfo $molid set beta {beta:.4f}")
            tcl.append(f"molinfo $molid set gamma {gamma:.4f}\n")

        # Element, name, radius, and color assignment per atom type
        tcl.append("# Assign chemical elements, names, radii, and vibrant colors")
        for tid, tdata in sorted(atom_types.items()):
            elem = tdata.element.strip()
            rad = tdata.radius
            vmd_col = tdata.color
            tcl.append(f'catch {{ color Type {tid} "{vmd_col}" }}')
            tcl.append(f'catch {{ color Element "{elem}" "{vmd_col}" }}')
            tcl.append(f'catch {{ color Name "{elem}" "{vmd_col}" }}')
            tcl.append(f'set sel [atomselect $molid "type {tid}"]')
            tcl.append(f'if {{[$sel num] > 0}} {{')
            tcl.append(f'    $sel set element "{elem}"')
            tcl.append(f'    $sel set name "{elem}"')
            tcl.append(f'    $sel set radius {rad:.3f}')
            tcl.append(f'}}')
            tcl.append(f'$sel delete\n')

        # Auto-detect bonds if no bonds in data file and requested
        if info.num_bonds == 0 and settings.auto_bonds:
            tcl.append("# Recalculate dynamic bonds")
            tcl.append(f'mol bondsrecalc $molid\n')

        # Visual Environment & Lighting (Prevents washed-out/grayish display in VMD 2.0)
        tcl.append("# Display & Lighting Environment")
        tcl.append(f"color Display Background {settings.bg_color}")
        tcl.append(f"display projection {settings.projection}")
        tcl.append(f"display depthcue {'on' if settings.depthcue else 'off'}")
        tcl.append(f"axes location {settings.axes_location}")
        tcl.append("display rendermode GLSL")
        tcl.append("catch { material change ambient Opaque 0.15 }")
        tcl.append("catch { material change diffuse Opaque 0.80 }")
        tcl.append("catch { material change specular Opaque 0.35 }")
        tcl.append("catch { material change shininess Opaque 0.35 }")
        tcl.append("display update ui\n")

        # Representations
        tcl.append("# Representations")
        tcl.append("mol delrep 0 $molid")

        rep_style = settings.rep_style.upper()
        if rep_style == "CPK":
            rep_cmd = f"CPK {settings.sphere_scale:.2f} {settings.bond_radius:.2f} 32 32"
        elif rep_style == "VDW":
            rep_cmd = f"VDW {settings.sphere_scale:.2f} 32"
        elif rep_style == "LICORICE":
            rep_cmd = f"Licorice {settings.bond_radius:.2f} 20 20"
        elif rep_style == "DYNAMICBONDS":
            rep_cmd = f"DynamicBonds {settings.bond_cutoff:.2f} {settings.bond_radius:.2f} 20"
        elif rep_style == "LINES":
            rep_cmd = f"Lines {int(settings.bond_radius * 10)}"
        else:
            rep_cmd = f"CPK {settings.sphere_scale:.2f} {settings.bond_radius:.2f} 32 32"

        tcl.append(f'mol representation {rep_cmd}')
        tcl.append(f'mol color {settings.color_by}')
        tcl.append(f'mol selection "all"')
        tcl.append(f'mol material {settings.material}')
        tcl.append(f'mol addrep $molid\n')

        # If bonds were absent and DynamicBonds wasn't the main representation, add bonds if requested
        if info.num_bonds == 0 and not settings.auto_bonds and rep_style == "CPK":
            tcl.append("# Optional: Add dynamic bonds representation for bondless atomic systems")
            tcl.append(f'mol representation DynamicBonds {settings.bond_cutoff:.2f} {settings.bond_radius:.2f} 20')
            tcl.append(f'mol color {settings.color_by}')
            tcl.append(f'mol selection "all"')
            tcl.append(f'mol material {settings.material}')
            tcl.append(f'mol addrep $molid\n')

        # PBC Box Drawing
        if settings.show_box and info.box:
            tcl.append("# Render Simulation Box boundary")
            tcl.append(f'pbc box -molid $molid -color {settings.box_color} -width {settings.box_width:.1f}\n')

        # Camera & Centering
        tcl.append("# Center and adjust view")
        tcl.append("mol center $molid")
        tcl.append("display resetview")
        tcl.append("# Open VMD Tk Console automatically so user can interact")
        tcl.append("catch { menu tkcon on }")
        tcl.append('puts "=========================================================="')
        tcl.append('puts " [LAMMPS Visualizer] Data file loaded into VMD successfully!"')
        tcl.append(f'puts " File: {clean_path}"')
        tcl.append(f'puts " Atoms: {info.num_atoms} | Bonds: {info.num_bonds} | Style: {style}"')
        tcl.append('puts "=========================================================="')

        return "\n".join(tcl) + "\n"
