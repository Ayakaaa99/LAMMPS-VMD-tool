# ==============================================================================
# LAMMPS Data Loader Plugin for VMD
# Allows loading LAMMPS .data files directly inside VMD with intelligent element
# assignment, simulation box display, and customizable representations.
#
# Usage inside VMD Tk Console:
#   source lammps_loader.tcl
#   lammps_loader_gui
# ==============================================================================

package require topotools 1.7
package require pbctools 2.8

namespace eval ::LammpsLoader {
    variable w .lammps_loader_gui
    variable data_file ""
    variable atom_style "full"
    variable rep_style "CPK"
    variable sphere_scale 0.35
    variable bond_radius 0.18
    variable bg_color "white"
    variable show_box 1
    variable box_color "black"
    variable box_width 2.0
    variable auto_bonds 0
    variable bond_cutoff 1.6
    
    # Store detected atom types: type_id -> {mass element radius}
    variable atom_types
    array set atom_types {}
}

proc lammps_loader_gui {} {
    return [::LammpsLoader::create_gui]
}

proc ::LammpsLoader::guess_element_from_mass {mass} {
    # Reference mass table for common elements
    set db {
        1.008 H   4.0026 He  6.94 Li   9.012 Be  10.81 B   12.011 C
        14.007 N  15.999 O   18.998 F  20.18 Ne  22.99 Na  24.305 Mg
        26.982 Al 28.085 Si  30.97 P   32.06 S   35.45 Cl  39.098 K
        40.078 Ca 47.867 Ti  51.996 Cr 54.938 Mn 55.845 Fe 58.693 Ni
        63.546 Cu 65.38 Zn   79.904 Br 107.87 Ag 118.71 Sn 126.90 I
        196.97 Au 207.2 Pb
    }
    set min_diff 99999.0
    set best_elem "C"
    foreach {m sym} $db {
        set diff [expr {abs($m - $mass)}]
        if {$diff < $min_diff} {
            set min_diff $diff
            set best_elem $sym
        }
    }
    return $best_elem
}

proc ::LammpsLoader::guess_vdw_radius {elem} {
    set rdb {
        H 1.20 C 1.70 N 1.55 O 1.52 F 1.47 Na 2.27 Mg 1.73
        Al 1.84 Si 2.10 P 1.80 S 1.80 Cl 1.75 K 2.75 Ca 2.31
        Fe 2.00 Cu 1.40 Zn 1.39 Br 1.85 Ag 1.72 Au 1.66
    }
    if {[dict exists $rdb $elem]} {
        return [dict get $rdb $elem]
    }
    return 1.50
}

proc ::LammpsLoader::create_gui {} {
    variable w
    if {[winfo exists $w]} {
        wm deiconify $w
        raise $w
        return
    }

    toplevel $w
    wm title $w "LAMMPS Data Loader for VMD"
    wm resizable $w 1 1

    # 1. File Selection Frame
    frame $w.file_frame -relief groove -bd 2 -padx 8 -pady 6
    pack $w.file_frame -fill x -padx 8 -pady 4

    label $w.file_frame.lbl -text "LAMMPS Data File:" -font {Helvetica 9 bold}
    pack $w.file_frame.lbl -anchor w

    frame $w.file_frame.sub
    pack $w.file_frame.sub -fill x -pady 2

    entry $w.file_frame.sub.ent -textvariable ::LammpsLoader::data_file -width 40
    pack $w.file_frame.sub.ent -side left -fill x -expand 1 -padx 4

    button $w.file_frame.sub.btn -text "Browse..." -command ::LammpsLoader::browse_file
    pack $w.file_frame.sub.btn -side left -padx 2

    button $w.file_frame.sub.btn_scan -text "Scan" -command ::LammpsLoader::scan_file
    pack $w.file_frame.sub.btn_scan -side left -padx 2

    # 2. Options Frame
    frame $w.opts_frame -relief groove -bd 2 -padx 8 -pady 6
    pack $w.opts_frame -fill x -padx 8 -pady 4

    # Atom Style
    frame $w.opts_frame.r1
    pack $w.opts_frame.r1 -fill x -pady 2
    label $w.opts_frame.r1.l -text "Atom Style:" -width 14 -anchor w
    pack $w.opts_frame.r1.l -side left
    menubutton $w.opts_frame.r1.mb -textvariable ::LammpsLoader::atom_style -indicatoron 1 -relief raised -bd 1
    menu $w.opts_frame.r1.mb.m -tearoff 0
    foreach st {full molecular atomic charge metal dipole} {
        $w.opts_frame.r1.mb.m add radiobutton -label $st -variable ::LammpsLoader::atom_style -value $st
    }
    $w.opts_frame.r1.mb configure -menu $w.opts_frame.r1.mb.m
    pack $w.opts_frame.r1.mb -side left

    # Visual Representation
    frame $w.opts_frame.r2
    pack $w.opts_frame.r2 -fill x -pady 2
    label $w.opts_frame.r2.l -text "Representation:" -width 14 -anchor w
    pack $w.opts_frame.r2.l -side left
    menubutton $w.opts_frame.r2.mb -textvariable ::LammpsLoader::rep_style -indicatoron 1 -relief raised -bd 1
    menu $w.opts_frame.r2.mb.m -tearoff 0
    foreach rep {CPK VDW Licorice DynamicBonds Lines} {
        $w.opts_frame.r2.mb.m add radiobutton -label $rep -variable ::LammpsLoader::rep_style -value $rep
    }
    $w.opts_frame.r2.mb configure -menu $w.opts_frame.r2.mb.m
    pack $w.opts_frame.r2.mb -side left

    label $w.opts_frame.r2.ls -text "  Scale:"
    pack $w.opts_frame.r2.ls -side left
    entry $w.opts_frame.r2.es -textvariable ::LammpsLoader::sphere_scale -width 6
    pack $w.opts_frame.r2.es -side left

    label $w.opts_frame.r2.lb -text "  Bond Radius:"
    pack $w.opts_frame.r2.lb -side left
    entry $w.opts_frame.r2.eb -textvariable ::LammpsLoader::bond_radius -width 6
    pack $w.opts_frame.r2.eb -side left

    # Display & Box
    frame $w.opts_frame.r3
    pack $w.opts_frame.r3 -fill x -pady 2
    label $w.opts_frame.r3.l -text "Background:" -width 14 -anchor w
    pack $w.opts_frame.r3.l -side left
    menubutton $w.opts_frame.r3.mb -textvariable ::LammpsLoader::bg_color -indicatoron 1 -relief raised -bd 1
    menu $w.opts_frame.r3.mb.m -tearoff 0
    foreach col {white black gray} {
        $w.opts_frame.r3.mb.m add radiobutton -label $col -variable ::LammpsLoader::bg_color -value $col
    }
    $w.opts_frame.r3.mb configure -menu $w.opts_frame.r3.mb.m
    pack $w.opts_frame.r3.mb -side left

    checkbutton $w.opts_frame.r3.chk_box -text "Show Simulation Box" -variable ::LammpsLoader::show_box
    pack $w.opts_frame.r3.chk_box -side left -padx 12

    # 3. Atom Types Table Frame
    frame $w.types_frame -relief groove -bd 2 -padx 8 -pady 6
    pack $w.types_frame -fill both -expand 1 -padx 8 -pady 4

    label $w.types_frame.lbl -text "Atom Types Mapping (Scanned from file):" -font {Helvetica 9 bold}
    pack $w.types_frame.lbl -anchor w

    canvas $w.types_frame.can -height 160
    scrollbar $w.types_frame.sb -orient vertical -command "$w.types_frame.can yview"
    frame $w.types_frame.list
    $w.types_frame.can configure -yscrollcommand "$w.types_frame.sb set"

    pack $w.types_frame.sb -side right -fill y
    pack $w.types_frame.can -side left -fill both -expand 1
    $w.types_frame.can create window (0,0) -window $w.types_frame.list -anchor nw
    bind $w.types_frame.list <Configure> [list ::LammpsLoader::scroll_conf $w.types_frame.can]

    # Header in list
    frame $w.types_frame.list.hdr
    pack $w.types_frame.list.hdr -fill x -pady 2
    label $w.types_frame.list.hdr.c1 -text "Type ID" -width 8 -font {Helvetica 8 bold}
    label $w.types_frame.list.hdr.c2 -text "Mass" -width 12 -font {Helvetica 8 bold}
    label $w.types_frame.list.hdr.c3 -text "Element" -width 10 -font {Helvetica 8 bold}
    label $w.types_frame.list.hdr.c4 -text "Radius (Å)" -width 12 -font {Helvetica 8 bold}
    pack $w.types_frame.list.hdr.c1 $w.types_frame.list.hdr.c2 $w.types_frame.list.hdr.c3 $w.types_frame.list.hdr.c4 -side left

    # 4. Action Buttons
    frame $w.btn_frame -padx 8 -pady 6
    pack $w.btn_frame -fill x -side bottom

    button $w.btn_frame.btn_load -text "Load into VMD" -font {Helvetica 10 bold} -command ::LammpsLoader::load_data
    pack $w.btn_frame.btn_load -side right -padx 6

    button $w.btn_frame.btn_close -text "Close" -command [list destroy $w]
    pack $w.btn_frame.btn_close -side right -padx 6
}

proc ::LammpsLoader::scroll_conf {canvas} {
    $canvas configure -scrollregion [$canvas bbox all]
}

proc ::LammpsLoader::browse_file {} {
    variable data_file
    set f [tk_getOpenFile -title "Select LAMMPS Data File" -filetypes {
        {"LAMMPS Data" {*.data *.lmp data.* *.dat}}
        {"All Files" *}
    }]
    if {$f ne ""} {
        set data_file $f
        ::LammpsLoader::scan_file
    }
}

proc ::LammpsLoader::scan_file {} {
    variable data_file
    variable atom_types
    variable w

    if {$data_file eq "" || ![file exists $data_file]} {
        return
    }

    array unset atom_types
    set f [open $data_file r]
    set in_masses 0
    set detected_style ""

    while {[gets $f line] >= 0} {
        set trim_line [string trim $line]
        if {[string match -nocase "atoms*" $trim_line] && [string first "#" $trim_line] >= 0} {
            set comment [string range $trim_line [expr {[string first "#" $trim_line] + 1}] end]
            foreach s {full molecular atomic charge dipole metal} {
                if {[string match -nocase "*$s*" $comment]} {
                    set ::LammpsLoader::atom_style $s
                }
            }
        }
        if {[string match -nocase "masses*" $trim_line]} {
            set in_masses 1
            continue
        }
        if {$in_masses} {
            if {$trim_line eq ""} continue
            set first_w [lindex $trim_line 0]
            if {[string is integer -strict $first_w]} {
                set tid $first_w
                set mass [lindex $trim_line 1]
                set elem [::LammpsLoader::guess_element_from_mass $mass]
                set rad [::LammpsLoader::guess_vdw_radius $elem]
                set atom_types($tid) [list $mass $elem $rad]
            } else {
                set in_masses 0
            }
        }
    }
    close $f

    # Update GUI list
    set lframe $w.types_frame.list
    foreach child [winfo children $lframe] {
        if {$child ne "$lframe.hdr"} {
            destroy $child
        }
    }

    foreach tid [lsort -integer [array names atom_types]] {
        set val $atom_types($tid)
        set mass [lindex $val 0]
        set elem [lindex $val 1]
        set rad [lindex $val 2]

        frame $lframe.row_$tid
        pack $lframe.row_$tid -fill x -pady 1

        label $lframe.row_$tid.c1 -text $tid -width 8
        label $lframe.row_$tid.c2 -text [format "%.3f" $mass] -width 12
        entry $lframe.row_$tid.c3 -width 10
        $lframe.row_$tid.c3 insert 0 $elem
        entry $lframe.row_$tid.c4 -width 12
        $lframe.row_$tid.c4 insert 0 [format "%.2f" $rad]

        pack $lframe.row_$tid.c1 $lframe.row_$tid.c2 $lframe.row_$tid.c3 $lframe.row_$tid.c4 -side left
    }
}

proc ::LammpsLoader::load_data {} {
    variable data_file
    variable atom_style
    variable rep_style
    variable sphere_scale
    variable bond_radius
    variable bg_color
    variable show_box
    variable box_color
    variable box_width
    variable atom_types
    variable w

    if {$data_file eq "" || ![file exists $data_file]} {
        tk_messageBox -icon error -message "Please select a valid LAMMPS data file."
        return
    }

    puts "Loading LAMMPS data: $data_file ($atom_style)..."
    set molid [topo readlammpsdata $data_file $atom_style]

    # Gather user changes from entries
    set lframe $w.types_frame.list
    foreach tid [array names atom_types] {
        if {[winfo exists $lframe.row_$tid.c3]} {
            set elem [$lframe.row_$tid.c3 get]
            set rad [$lframe.row_$tid.c4 get]
            set col [::LammpsLoader::guess_vdw_radius $elem] ;# fallback
            # Color by element
            set cdb {
                H white C cyan N blue O red F green Na yellow Mg green
                Al silver Si ochre P orange S yellow Cl green K purple Ca green
                Fe orange2 Cu ochre Zn silver Br red2 Ag silver Au yellow
            }
            set elem_col "cyan"
            if {[dict exists $cdb $elem]} {
                set elem_col [dict get $cdb $elem]
            }
            catch { color Type $tid $elem_col }
            catch { color Element $elem $elem_col }
            catch { color Name $elem $elem_col }

            set sel [atomselect $molid "type $tid"]
            if {[$sel num] > 0} {
                $sel set element $elem
                $sel set name $elem
                $sel set radius $rad
            }
            $sel delete
        }
    }

    # Environment & Material Tuning (fixes grayish-white issue in VMD 2.0)
    color Display Background $bg_color
    display projection Orthographic
    display depthcue off
    axes location lowerleft
    display rendermode GLSL
    catch { material change ambient Opaque 0.15 }
    catch { material change diffuse Opaque 0.80 }
    catch { material change specular Opaque 0.35 }
    catch { material change shininess Opaque 0.35 }

    # Reps
    mol delrep 0 $molid
    if {$rep_style eq "CPK"} {
        mol representation CPK $sphere_scale $bond_radius 32 32
    } elseif {$rep_style eq "VDW"} {
        mol representation VDW $sphere_scale 32
    } elseif {$rep_style eq "Licorice"} {
        mol representation Licorice $bond_radius 20 20
    } elseif {$rep_style eq "DynamicBonds"} {
        mol representation DynamicBonds 1.6 $bond_radius 20
    } else {
        mol representation Lines
    }
    mol color Type
    mol selection "all"
    mol material Opaque
    mol addrep $molid

    # Simulation box
    if {$show_box} {
        pbc box -molid $molid -color $box_color -width $box_width
    }

    mol center $molid
    display resetview
    puts "=========================================================="
    puts " LAMMPS Data loaded into VMD (Molecule ID $molid)!"
    puts " Atoms: [molinfo $molid get numatoms] | Bonds: [molinfo $molid get numbonds]"
    puts "=========================================================="
}

# Fast command-line loader for VMD Tk Console
proc lammps_load {filepath {style "auto"}} {
    if {![file exists $filepath]} {
        puts "Error: File not found: $filepath"
        return
    }
    set ::LammpsLoader::data_file $filepath
    if {$style ne "auto"} {
        set ::LammpsLoader::atom_style $style
    }
    ::LammpsLoader::scan_file
    ::LammpsLoader::load_data
}

puts "=================================================================="
puts "  LAMMPS Data Loader Plugin for VMD"
puts "  - Use 'lammps_loader_gui' to open the graphical loader"
puts "  - Use 'lammps_load <path_to_data_file>' to load directly from console"
puts "=================================================================="

# Auto-open GUI when script is sourced
lammps_loader_gui
