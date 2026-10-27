"""
VMD Tcl script generator.

Builds a self-contained Tcl script that is executed by VMD (through ``vmd -e``)
and applies the selected element radii, exact RGB colors, unit cell and display
settings. Data files are loaded through TopoTools, dump trajectories through
VMD's native ``lammpstrj`` reader.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .parser import AtomTypeData, LammpsDataInfo


TYPE_COLOR_BASE = 33
TYPE_COLOR_SLOTS = 900
BACKGROUND_COLOR_ID = 1000
BOX_COLOR_ID = 1001


@dataclass
class VisualSettings:
    preset_name: str = "publication"
    rep_style: str = "CPK"  # CPK, VDW, Licorice, DynamicBonds, Lines
    sphere_scale: float = 0.35
    bond_radius: float = 0.18
    material: str = "Opaque"
    bg_color: str = "#FFFFFF"
    projection: str = "Orthographic"
    show_axes: bool = False
    depthcue: bool = False
    show_box: bool = True
    box_color: str = "#1A1A1A"
    box_width: float = 1.5
    auto_bonds: bool = True
    bond_cutoff: float = 1.6


class VmdScriptGenerator:
    """Generates the VMD startup script."""

    PRESETS = {
        "publication": VisualSettings(
            preset_name="publication",
            rep_style="CPK",
            sphere_scale=0.35,
            bond_radius=0.18,
            material="Opaque",
            bg_color="#FFFFFF",
            projection="Orthographic",
            show_axes=False,
            depthcue=False,
            show_box=True,
            box_color="#1A1A1A",
            box_width=1.5,
        ),
        "dark": VisualSettings(
            preset_name="dark",
            rep_style="CPK",
            sphere_scale=0.32,
            bond_radius=0.16,
            material="Glossy",
            bg_color="#000000",
            projection="Perspective",
            show_axes=True,
            depthcue=True,
            show_box=True,
            box_color="#00C8C8",
            box_width=1.5,
        ),
        "spacefill": VisualSettings(
            preset_name="spacefill",
            rep_style="VDW",
            sphere_scale=1.0,
            bond_radius=0.1,
            material="Opaque",
            bg_color="#FFFFFF",
            projection="Orthographic",
            show_axes=False,
            depthcue=False,
            show_box=True,
            box_color="#808080",
            box_width=1.5,
        ),
        "skeleton": VisualSettings(
            preset_name="skeleton",
            rep_style="Licorice",
            sphere_scale=0.25,
            bond_radius=0.22,
            material="Opaque",
            bg_color="#000000",
            projection="Perspective",
            show_axes=True,
            depthcue=True,
            show_box=True,
            box_color="#EDC948",
            box_width=1.5,
        ),
    }

    @classmethod
    def generate(
        cls,
        info: LammpsDataInfo,
        atom_types: Optional[Dict[int, AtomTypeData]] = None,
        settings: Optional[VisualSettings] = None,
    ) -> str:
        if settings is None:
            settings = cls.PRESETS["publication"]
        if atom_types is None:
            atom_types = info.atom_types

        types = sorted(atom_types.values(), key=lambda item: item.type_id)
        lines: List[str] = []

        lines.append("# ============================================================")
        lines.append("#  LAMMPS -> VMD")
        lines.append(f"#  file type : {info.file_type}")
        lines.append(f"#  atoms     : {info.num_atoms}")
        lines.append(f"#  bonds     : {info.num_bonds}")
        lines.append(f"#  atom types: {len(types)}")
        lines.append("# ============================================================")
        lines.append("")

        lines.append("set lvPath " + cls._tcl_string(info.filepath))
        lines.append("")

        # ---------------------------------------------------------- helpers
        lines.append("proc ::lv__set_radii {molid pairs} {")
        lines.append("    foreach {tid radius} $pairs {")
        lines.append('        set sel [atomselect $molid "type $tid"]')
        lines.append("        if {[$sel num] > 0} { $sel set radius $radius }")
        lines.append("        $sel delete")
        lines.append("    }")
        lines.append("}")
        lines.append("")
        lines.append("proc ::lv__frame_radii {molid pairs args} {")
        lines.append("    catch { ::lv__set_radii $molid $pairs }")
        lines.append("}")
        lines.append("")

        if info.is_trajectory:
            lines.append("# Load a LAMMPS text dump (native lammpstrj molfile reader)")
            lines.append("catch { package require pbctools }")
            lines.append("set lvMolid [mol new $lvPath type lammpstrj waitfor all]")
            lines.append('if {$lvMolid < 0} { error "VMD could not read the LAMMPS trajectory file" }')
        else:
            lines.append("# Load a LAMMPS data file through TopoTools")
            lines.append("if {[catch { package require topotools } lvPkgErr]} {")
            lines.append('    error "TopoTools is required to read data files: $lvPkgErr"')
            lines.append("}")
            lines.append("catch { package require pbctools }")
            lines.append("")
            lines.append("proc ::lv__load_data {path styles} {")
            lines.append("    foreach style $styles {")
            lines.append("        if {![catch {topo readlammpsdata $path $style} m]} {")
            lines.append("            if {[molinfo $m get numatoms] > 0} { return $m }")
            lines.append("            catch { mol delete $m }")
            lines.append("        }")
            lines.append("    }")
            lines.append('    error "TopoTools could not read the data file (styles: $styles)"')
            lines.append("}")
            lines.append("")
            styles = " ".join(info.style_candidates())
            lines.append(f"set lvMolid [::lv__load_data $lvPath {{{styles}}}]")

        lines.append("mol top $lvMolid")
        lines.append("")

        # ---------------------------------------------------------- unit cell
        if info.box:
            a, b, c, alpha, beta, gamma = info.box.to_vmd_unitcell()
            lines.append("# Simulation cell")
            lines.append("if {[catch {")
            lines.append(f"    molinfo $lvMolid set a {a:.4f}")
            lines.append(f"    molinfo $lvMolid set b {b:.4f}")
            lines.append(f"    molinfo $lvMolid set c {c:.4f}")
            lines.append(f"    molinfo $lvMolid set alpha {alpha:.4f}")
            lines.append(f"    molinfo $lvMolid set beta {beta:.4f}")
            lines.append(f"    molinfo $lvMolid set gamma {gamma:.4f}")
            lines.append("} lvErr]} { puts \"Cell setup skipped: $lvErr\" }")
            lines.append("")

        # ------------------------------------------------- types, colors, radii
        lines.append("# Per-type colors (exact RGB), elements and radii")
        for index, atom_type in enumerate(types):
            color_id = TYPE_COLOR_BASE + (index % TYPE_COLOR_SLOTS)
            red, green, blue = cls._hex_to_rgb(atom_type.color)
            lines.append(f"color change rgb {color_id} {red:.4f} {green:.4f} {blue:.4f}")
            lines.append(f"color Type {atom_type.type_id} {color_id}")
        lines.append("")

        for atom_type in types:
            element = atom_type.element.strip()
            lines.append(f'set sel [atomselect $lvMolid "type {atom_type.type_id}"]')
            lines.append("if {[$sel num] > 0} {")
            lines.append(f"    $sel set radius {atom_type.radius:.3f}")
            if element and element != "X":
                lines.append(f'    $sel set name "{element}"')
                lines.append(f'    $sel set element "{element}"')
            lines.append("}")
            lines.append("$sel delete")
        lines.append("")

        if types:
            pairs = " ".join(f"{item.type_id} {item.radius:.3f}" for item in types)
            lines.append(f"set lvRadii {{{pairs}}}")
            lines.append("::lv__set_radii $lvMolid $lvRadii")
            lines.append("if {[molinfo $lvMolid get numframes] > 1} {")
            lines.append(
                "    catch { trace add variable ::vmd_frame($lvMolid) write "
                "[list ::lv__frame_radii $lvMolid $lvRadii] }"
            )
            lines.append("}")
            lines.append("")

        # ---------------------------------------------------------- display env
        bg_red, bg_green, bg_blue = cls._hex_to_rgb(settings.bg_color)
        lines.append("# Display environment")
        lines.append(
            f"color change rgb {BACKGROUND_COLOR_ID} {bg_red:.4f} {bg_green:.4f} {bg_blue:.4f}"
        )
        lines.append(f"color Display Background {BACKGROUND_COLOR_ID}")
        lines.append(f"display projection {settings.projection}")
        lines.append(f"display depthcue {'on' if settings.depthcue else 'off'}")
        lines.append(f"axes location {'lowerleft' if settings.show_axes else 'off'}")
        lines.append("catch { display rendermode GLSL }")
        lines.append("catch { material change ambient Opaque 0.15 }")
        lines.append("catch { material change diffuse Opaque 0.80 }")
        lines.append("catch { material change specular Opaque 0.35 }")
        lines.append("catch { material change shininess Opaque 0.35 }")
        lines.append("catch { material change ambient Glossy 0.16 }")
        lines.append("catch { material change diffuse Glossy 0.82 }")
        lines.append("catch { material change specular Glossy 0.24 }")
        lines.append("catch { material change shininess Glossy 0.35 }")
        lines.append("")

        # ---------------------------------------------------------- representation
        rep_args = cls._representation_args(settings)
        lines.append("# Representation")
        lines.append("if {[molinfo $lvMolid get numreps] < 1} { mol addrep $lvMolid }")
        lines.append("if {[catch {")
        lines.append(f"    mol modstyle 0 $lvMolid {rep_args}")
        lines.append("    mol modcolor 0 $lvMolid Type")
        lines.append(f"    mol modmaterial 0 $lvMolid {settings.material}")
        lines.append('    mol modselect 0 $lvMolid "all"')
        lines.append("} lvErr]} {")
        lines.append('    puts "Representation fallback: $lvErr"')
        lines.append("    catch { mol modstyle 0 $lvMolid CPK 0.35 0.18 24 20 }")
        lines.append("}")
        lines.append("")

        auto_bonds = (
            settings.auto_bonds
            and info.num_bonds == 0
            and settings.rep_style.upper() in ("CPK", "LICORICE", "LINES")
        )
        if auto_bonds:
            lines.append("# Distance-based bonds for topologies without bonds")
            lines.append("mol addrep $lvMolid")
            lines.append("set lvRep [expr {[molinfo $lvMolid get numreps] - 1}]")
            lines.append(
                f"catch {{ mol modstyle $lvRep $lvMolid DynamicBonds "
                f"{settings.bond_cutoff:.2f} {settings.bond_radius:.2f} 20 }}"
            )
            lines.append("catch { mol modcolor $lvRep $lvMolid Type }")
            lines.append("catch { mol modmaterial $lvRep $lvMolid Opaque }")
            lines.append('catch { mol modselect $lvRep $lvMolid "all" }')
            lines.append("")

        # ---------------------------------------------------------- box and camera
        if settings.show_box and info.box:
            red, green, blue = cls._hex_to_rgb(settings.box_color)
            lines.append("# Simulation box")
            lines.append(
                f"color change rgb {BOX_COLOR_ID} {red:.4f} {green:.4f} {blue:.4f}"
            )
            lines.append(
                f"if {{[catch {{ pbc box -molid $lvMolid -color {BOX_COLOR_ID} "
                f"-width {settings.box_width:.2f} }} lvErr]}} {{"
            )
            lines.append('    catch { pbc box -molid $lvMolid -color black -width 1.5 }')
            lines.append("}")
            lines.append("")

        lines.append("# Center and fit the view")
        lines.append("mol center $lvMolid")
        lines.append("display resetview")
        if info.box:
            box_span = max(info.box.to_vmd_unitcell()[:3])
            lines.append("set lvSel [atomselect $lvMolid all]")
            lines.append("set lvMinmax [measure minmax $lvSel]")
            lines.append("$lvSel delete")
            lines.append("set lvSpan 0.0")
            lines.append("foreach lvI {0 1 2} {")
            lines.append(
                "    set lvD [expr {abs([lindex $lvMinmax 1 $lvI] - "
                "[lindex $lvMinmax 0 $lvI])}]"
            )
            lines.append("    if {$lvD > $lvSpan} { set lvSpan $lvD }")
            lines.append("}")
            lines.append(f"set lvBoxSpan {box_span:.4f}")
            lines.append("if {$lvSpan > 0.0 && $lvBoxSpan > $lvSpan} {")
            lines.append("    catch { scale by [expr {0.92 * $lvSpan / $lvBoxSpan}] }")
            lines.append("}")
        lines.append("display update ui")
        lines.append("")

        # ---------------------------------------------------------- console
        lines.append('puts "=========================================================="')
        lines.append('puts " LAMMPS -> VMD : loaded molecule $lvMolid"')
        lines.append('puts " File   : $lvPath"')
        lines.append('puts " Atoms  : [molinfo $lvMolid get numatoms]"')
        lines.append('puts " Frames : [molinfo $lvMolid get numframes]"')
        lines.append('puts "=========================================================="')
        lines.append("")
        lines.append("# Open the VMD Tk Console so the scene can be refined interactively")
        lines.append("after idle { after 2 { catch { menu tkcon on } } }")

        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _hex_to_rgb(color: str) -> Tuple[float, float, float]:
        value = (color or "").strip().lstrip("#")
        if len(value) == 3:
            value = "".join(char * 2 for char in value)
        if len(value) != 6:
            return (0.8, 0.8, 0.8)
        try:
            return (
                int(value[0:2], 16) / 255.0,
                int(value[2:4], 16) / 255.0,
                int(value[4:6], 16) / 255.0,
            )
        except ValueError:
            return (0.8, 0.8, 0.8)

    @staticmethod
    def _tcl_string(text: str) -> str:
        """Builds an ASCII-only double-quoted Tcl string from an arbitrary path."""
        text = text.replace("\\", "/")
        out: List[str] = ['"']
        for char in text:
            code = ord(char)
            if char == '"':
                out.append('\\"')
            elif char == "$":
                out.append("\\$")
            elif char == "[":
                out.append("\\[")
            elif char == "]":
                out.append("\\]")
            elif char == "\n":
                out.append("\\n")
            elif code < 0x20 or code > 0x7E:
                if code <= 0xFFFF:
                    out.append(f"\\u{code:04x}")
                else:
                    out.append(f"\\U{code:08x}")
            else:
                out.append(char)
        out.append('"')
        return "".join(out)

    @staticmethod
    def _representation_args(settings: VisualSettings) -> str:
        style = settings.rep_style.upper()
        if style == "CPK":
            return f"CPK {settings.sphere_scale:.2f} {settings.bond_radius:.2f} 32 32"
        if style == "VDW":
            return f"VDW {settings.sphere_scale:.2f} 32"
        if style == "LICORICE":
            return f"Licorice {settings.bond_radius:.2f} 20 20"
        if style == "DYNAMICBONDS":
            return (
                f"DynamicBonds {settings.bond_cutoff:.2f} "
                f"{settings.bond_radius:.2f} 20"
            )
        if style == "LINES":
            return f"Lines {max(1.0, settings.bond_radius * 10):.1f}"
        return f"CPK {settings.sphere_scale:.2f} {settings.bond_radius:.2f} 32 32"
