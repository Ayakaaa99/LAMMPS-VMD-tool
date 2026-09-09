"""
Drag and drop support for Tkinter on Windows.
Wraps windnd or ctypes WM_DROPFILES to enable dropping files from File Explorer.
"""

import os
import sys
from typing import Callable, List


def hook_drop_files(widget, on_drop_callback: Callable[[List[str]], None]):
    """
    Hooks a Tkinter widget or window to accept dropped files from Windows Explorer.
    Calls on_drop_callback with a list of absolute file paths (str).
    """
    if not sys.platform.startswith("win"):
        return False

    # 1. Try windnd first
    try:
        import windnd

        def _windnd_handler(files):
            file_paths = []
            for f in files:
                if isinstance(f, bytes):
                    try:
                        decoded = f.decode("utf-8")
                    except UnicodeDecodeError:
                        decoded = f.decode("gbk", errors="replace")
                else:
                    decoded = str(f)
                if os.path.exists(decoded):
                    file_paths.append(os.path.abspath(decoded))
            if file_paths:
                on_drop_callback(file_paths)

        windnd.hook_dropfiles(widget, func=_windnd_handler, force_unicode=True)
        return True
    except Exception as e:
        pass

    # 2. Fallback to direct ctypes implementation
    try:
        import ctypes
        from ctypes.wintypes import DWORD

        hwnd = widget.winfo_id()
        if hasattr(widget, "wm_frame"):
            try:
                # Top level frame
                hwnd = int(widget.wm_frame(), 16)
            except Exception:
                hwnd = widget.winfo_id()

        import platform
        is_64bit = platform.architecture()[0] == "64bit"
        argtype = ctypes.c_uint64 if is_64bit else DWORD
        GetWindowLong = ctypes.windll.user32.GetWindowLongPtrA if is_64bit else ctypes.windll.user32.GetWindowLongW
        SetWindowLong = ctypes.windll.user32.SetWindowLongPtrA if is_64bit else ctypes.windll.user32.SetWindowLongW
        prototype = ctypes.WINFUNCTYPE(argtype, argtype, argtype, argtype, argtype)

        WM_DROPFILES = 0x0233
        GWL_WNDPROC = -4

        def py_drop_proc(h_wnd, msg, w_param, l_param):
            if msg == WM_DROPFILES:
                count = ctypes.windll.shell32.DragQueryFileW(argtype(w_param), -1, None, 0)
                file_paths = []
                buffer = ctypes.create_unicode_buffer(512)
                for i in range(count):
                    ctypes.windll.shell32.DragQueryFileW(argtype(w_param), i, buffer, 512)
                    path = buffer.value
                    if os.path.exists(path):
                        file_paths.append(os.path.abspath(path))
                ctypes.windll.shell32.DragFinish(argtype(w_param))
                if file_paths:
                    widget.after(10, lambda: on_drop_callback(file_paths))
            return ctypes.windll.user32.CallWindowProcW(old_proc, h_wnd, msg, w_param, l_param)

        old_proc = GetWindowLong(hwnd, GWL_WNDPROC)
        new_proc = prototype(py_drop_proc)
        # Keep reference to prevent garbage collection
        widget._dnd_new_proc = new_proc

        ctypes.windll.shell32.DragAcceptFiles(hwnd, True)
        SetWindowLong(hwnd, GWL_WNDPROC, new_proc)
        return True
    except Exception:
        return False

