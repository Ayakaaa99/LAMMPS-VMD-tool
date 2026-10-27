"""
Native Windows drag & drop support for Tkinter windows.

Uses WM_DROPFILES through ctypes, so no third-party package is required and
the frozen one-file executable behaves exactly like the Python version.
"""

from __future__ import annotations

import ctypes
import os
import sys
from ctypes import wintypes
from typing import Callable, List

WM_DROPFILES = 0x0233
GWLP_WNDPROC = -4


def _window_handle(widget) -> int:
    widget.update_idletasks()
    frame = widget.wm_frame()
    try:
        return int(frame, 16)
    except (TypeError, ValueError):
        return int(frame)


def hook_drop_files(widget, on_drop: Callable[[List[str]], None]) -> bool:
    """Registers a Tk toplevel window to receive files dropped from Explorer."""
    if not sys.platform.startswith("win"):
        return False

    try:
        user32 = ctypes.windll.user32
        shell32 = ctypes.windll.shell32

        is_64bit = ctypes.sizeof(ctypes.c_void_p) == 8
        long_ptr = ctypes.c_ssize_t if is_64bit else ctypes.c_long
        get_long = user32.GetWindowLongPtrW if is_64bit else user32.GetWindowLongW
        set_long = user32.SetWindowLongPtrW if is_64bit else user32.SetWindowLongW

        get_long.argtypes = [wintypes.HWND, ctypes.c_int]
        get_long.restype = long_ptr
        set_long.argtypes = [wintypes.HWND, ctypes.c_int, long_ptr]
        set_long.restype = long_ptr

        user32.CallWindowProcW.argtypes = [
            ctypes.c_void_p,
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        user32.CallWindowProcW.restype = ctypes.c_ssize_t

        shell32.DragQueryFileW.argtypes = [
            wintypes.HANDLE,
            wintypes.UINT,
            wintypes.LPWSTR,
            wintypes.UINT,
        ]
        shell32.DragQueryFileW.restype = wintypes.UINT
        shell32.DragFinish.argtypes = [wintypes.HANDLE]
        shell32.DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]

        proc_type = ctypes.WINFUNCTYPE(
            ctypes.c_ssize_t,
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )

        hwnd = _window_handle(widget)
        old_proc = get_long(hwnd, GWLP_WNDPROC)

        def handler(hwnd_value, message, wparam, lparam):
            if message == WM_DROPFILES:
                try:
                    drop_handle = wintypes.HANDLE(wparam)
                    count = shell32.DragQueryFileW(drop_handle, 0xFFFFFFFF, None, 0)
                    paths: List[str] = []
                    for index in range(count):
                        length = shell32.DragQueryFileW(drop_handle, index, None, 0)
                        buffer = ctypes.create_unicode_buffer(length + 1)
                        shell32.DragQueryFileW(drop_handle, index, buffer, length + 1)
                        if os.path.isfile(buffer.value):
                            paths.append(os.path.abspath(buffer.value))
                    shell32.DragFinish(drop_handle)
                    if paths:
                        widget.after(10, lambda: on_drop(paths))
                except Exception:
                    pass
            return user32.CallWindowProcW(
                ctypes.c_void_p(old_proc), hwnd_value, message, wparam, lparam
            )

        new_proc = proc_type(handler)
        widget._drop_handler = new_proc
        widget._drop_old_proc = old_proc
        set_long(hwnd, GWLP_WNDPROC, ctypes.cast(new_proc, ctypes.c_void_p).value)
        shell32.DragAcceptFiles(hwnd, True)
        return True
    except Exception:
        return False
