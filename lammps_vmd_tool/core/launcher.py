"""
VMD executable detector and process launcher.
Finds VMD installation paths across Windows, Linux, and macOS, and launches VMD with scripts.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import List, Optional


CONFIG_FILE = Path.home() / ".lammps_vmd_tool.json"


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_config(data: dict) -> None:
    try:
        current = load_config()
        current.update(data)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)
    except Exception:
        pass


def find_vmd_executable(custom_path: Optional[str] = None) -> Optional[str]:
    """
    Finds the VMD executable path.
    1. Checks custom_path if provided.
    2. Checks saved configuration.
    3. Checks PATH environment.
    4. Checks standard Windows / Unix installation directories.
    """
    if custom_path and os.path.isfile(custom_path):
        save_config({"vmd_path": custom_path})
        return custom_path

    # Check saved config
    cfg = load_config()
    saved = cfg.get("vmd_path")
    if saved and os.path.isfile(saved):
        return saved

    # Check system PATH
    in_path = shutil.which("vmd") or shutil.which("vmd.exe")
    if in_path:
        return in_path

    # Standard candidate directories
    candidates: List[str] = []
    
    if sys.platform.startswith("win"):
        program_dirs = [
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
            r"C:\Program Files",
            r"C:\Program Files (x86)",
            r"D:\Program Files",
            r"D:\Program Files (x86)",
            r"E:\Program Files",
            r"C:\VMD",
            r"D:\VMD",
            r"E:\VMD"
        ]
        
        for pdir in program_dirs:
            if not os.path.isdir(pdir):
                continue
            # Look for University of Illinois\VMD*
            uillinois = os.path.join(pdir, "University of Illinois")
            if os.path.isdir(uillinois):
                try:
                    for folder in sorted(os.listdir(uillinois), reverse=True):
                        if folder.lower().startswith("vmd"):
                            vmd_bin = os.path.join(uillinois, folder, "vmd.exe")
                            if os.path.isfile(vmd_bin):
                                candidates.append(vmd_bin)
                except Exception:
                    pass
            # Direct VMD folders
            vmd_bin = os.path.join(pdir, "vmd.exe")
            if os.path.isfile(vmd_bin):
                candidates.append(vmd_bin)

    elif sys.platform == "darwin":
        candidates.extend([
            "/Applications/VMD 1.9.4.app/Contents/vmd/vmd_MACOSX",
            "/Applications/VMD 1.9.3.app/Contents/vmd/vmd_MACOSX",
            "/usr/local/bin/vmd",
            "/opt/homebrew/bin/vmd"
        ])
    else:  # Linux
        candidates.extend([
            "/usr/local/bin/vmd",
            "/usr/bin/vmd",
            "/opt/vmd/bin/vmd"
        ])

    for c in candidates:
        if os.path.isfile(c):
            save_config({"vmd_path": c})
            return c

    return None


def launch_vmd(script_path: str, vmd_path: Optional[str] = None) -> subprocess.Popen:
    """
    Launches VMD with the given Tcl script.
    """
    exe = find_vmd_executable(vmd_path)
    if not exe:
        raise FileNotFoundError(
            "VMD executable (vmd.exe) could not be located automatically.\n"
            "Please specify the path to vmd.exe."
        )

    if not os.path.isfile(script_path):
        raise FileNotFoundError(f"Script file not found: {script_path}")

    # Launch VMD process asynchronously with -e script
    cmd = [exe, "-e", script_path]
    return subprocess.Popen(cmd)
