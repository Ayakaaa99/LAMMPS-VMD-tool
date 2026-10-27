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


def _find_in_vmd_folders(root: str) -> List[str]:
    """Finds vmd.exe inside immediate sub-folders such as ``VMD2.0``."""
    results: List[str] = []
    try:
        entries = os.listdir(root)
    except OSError:
        return results
    for entry in sorted(entries, reverse=True):
        if not entry.lower().startswith("vmd"):
            continue
        candidate = os.path.join(root, entry, "vmd.exe")
        if os.path.isfile(candidate):
            results.append(candidate)
    return results


def find_vmd_executable(custom_path: Optional[str] = None) -> Optional[str]:
    """
    Finds the VMD executable path.
    1. Checks custom_path if provided.
    2. Checks saved configuration.
    3. Checks PATH environment.
    4. Scans common Windows installation directories.
    """
    if custom_path and os.path.isfile(custom_path):
        save_config({"vmd_path": custom_path})
        return custom_path

    cfg = load_config()
    saved = cfg.get("vmd_path")
    if saved and os.path.isfile(saved):
        return saved

    in_path = shutil.which("vmd") or shutil.which("vmd.exe")
    if in_path:
        return in_path

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
            r"E:\Program Files (x86)",
            r"C:\VMD",
            r"D:\VMD",
            r"E:\VMD",
        ]

        scan_roots: List[str] = []
        for pdir in program_dirs:
            if not os.path.isdir(pdir):
                continue
            uiuc = os.path.join(pdir, "University of Illinois")
            if os.path.isdir(uiuc):
                candidates.extend(_find_in_vmd_folders(uiuc))
            candidates.extend(_find_in_vmd_folders(pdir))
            direct = os.path.join(pdir, "vmd.exe")
            if os.path.isfile(direct):
                candidates.append(direct)

        for letter in "CDEFGH":
            drive = f"{letter}:\\"
            if not os.path.isdir(drive):
                continue
            scan_roots.extend(
                [
                    drive,
                    os.path.join(drive, "software"),
                    os.path.join(drive, "Program Files"),
                ]
            )
        for root in scan_roots:
            if os.path.isdir(root):
                candidates.extend(_find_in_vmd_folders(root))

    elif sys.platform == "darwin":
        candidates.extend(
            [
                "/Applications/VMD 1.9.4.app/Contents/vmd/vmd_MACOSX",
                "/Applications/VMD 1.9.3.app/Contents/vmd/vmd_MACOSX",
                "/usr/local/bin/vmd",
                "/opt/homebrew/bin/vmd",
            ]
        )
    else:  # Linux
        candidates.extend(
            ["/usr/local/bin/vmd", "/usr/bin/vmd", "/opt/vmd/bin/vmd"]
        )

    for candidate in candidates:
        if os.path.isfile(candidate):
            save_config({"vmd_path": candidate})
            return candidate

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
