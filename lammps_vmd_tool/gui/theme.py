"""Win11-inspired colors, fonts, ttk styles and small custom widgets."""

from __future__ import annotations

import re
import tkinter as tk
from tkinter import colorchooser, font as tkfont, ttk
from typing import Callable, Dict, List, Optional, Sequence, Tuple


class Theme:
    BG = "#F3F3F3"
    CARD = "#FFFFFF"
    BORDER = "#E5E5E5"
    BORDER_STRONG = "#D6D6D6"
    TEXT = "#1B1B1B"
    TEXT_MUTED = "#5F5F5F"
    TEXT_FAINT = "#8A8A8A"
    ACCENT = "#0067C0"
    ACCENT_HOVER = "#0078D4"
    ACCENT_PRESSED = "#005A9E"
    ACCENT_TINT = "#EAF4FF"
    HOVER = "#F5F5F5"
    SUCCESS = "#0F7B0F"
    SUCCESS_TINT = "#E6F4E6"
    DANGER = "#C42B1C"
    DANGER_TINT = "#FDE7E9"
    WARNING = "#9D5D00"
    TRACK = "#EDEDED"


FONTS: Dict[str, Tuple] = {
    "hero": ("Segoe UI", 20, "bold"),
    "title": ("Segoe UI", 13, "bold"),
    "body": ("Segoe UI", 10),
    "bold": ("Segoe UI", 10, "bold"),
    "small": ("Segoe UI", 9),
    "small_bold": ("Segoe UI", 9, "bold"),
    "mono": ("Consolas", 9),
}


def _pick_family(root: tk.Misc, candidates: Sequence[str]) -> str:
    available = set(tkfont.families(root))
    for family in candidates:
        if family in available:
            return family
    return candidates[-1]


def apply_theme(root: tk.Tk) -> None:
    """Configures fonts, ttk styles and combobox popup colors."""
    text_family = _pick_family(
        root, ("Segoe UI Variable Text", "Segoe UI", "Microsoft YaHei UI", "Tahoma")
    )
    display_family = _pick_family(
        root,
        (
            "Segoe UI Variable Display",
            "Segoe UI Semibold",
            "Segoe UI",
            "Microsoft YaHei UI",
            "Tahoma",
        ),
    )

    FONTS.update(
        {
            "hero": (display_family, 20, "bold"),
            "title": (display_family, 12, "bold"),
            "body": (text_family, 10),
            "bold": (text_family, 10, "bold"),
            "small": (text_family, 9),
            "small_bold": (text_family, 9, "bold"),
            "mono": ("Consolas", 9),
        }
    )

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    root.option_add("*Font", FONTS["body"])
    root.option_add("*TCombobox*Listbox.background", Theme.CARD)
    root.option_add("*TCombobox*Listbox.foreground", Theme.TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", Theme.ACCENT_TINT)
    root.option_add("*TCombobox*Listbox.selectForeground", Theme.ACCENT)
    root.option_add("*TCombobox*Listbox.font", FONTS["body"])

    style.configure(".", background=Theme.BG, foreground=Theme.TEXT, font=FONTS["body"])
    style.configure("TFrame", background=Theme.BG)

    style.configure(
        "TButton",
        background=Theme.CARD,
        foreground=Theme.TEXT,
        bordercolor=Theme.BORDER_STRONG,
        lightcolor=Theme.CARD,
        darkcolor=Theme.CARD,
        relief="flat",
        padding=(14, 7),
        font=FONTS["small"],
    )
    style.map(
        "TButton",
        background=[
            ("pressed", "#EBEBEB"),
            ("active", Theme.HOVER),
            ("disabled", "#FAFAFA"),
        ],
        foreground=[("disabled", Theme.TEXT_FAINT)],
        bordercolor=[("disabled", Theme.BORDER)],
    )

    style.configure(
        "Accent.TButton",
        background=Theme.ACCENT,
        foreground="#FFFFFF",
        bordercolor=Theme.ACCENT,
        lightcolor=Theme.ACCENT,
        darkcolor=Theme.ACCENT,
        relief="flat",
        padding=(20, 9),
        font=FONTS["bold"],
    )
    style.map(
        "Accent.TButton",
        background=[
            ("pressed", Theme.ACCENT_PRESSED),
            ("active", Theme.ACCENT_HOVER),
            ("disabled", "#C9C9C9"),
        ],
        foreground=[("disabled", "#FFFFFF")],
        bordercolor=[("disabled", "#C9C9C9")],
    )

    style.configure(
        "Ghost.TButton",
        background=Theme.BG,
        foreground=Theme.TEXT_MUTED,
        borderwidth=0,
        relief="flat",
        padding=(10, 5),
        font=FONTS["small"],
    )
    style.map(
        "Ghost.TButton",
        background=[("pressed", "#E9E9E9"), ("active", "#EAEAEA")],
        foreground=[("active", Theme.TEXT)],
    )

    style.configure(
        "CardGhost.TButton",
        background=Theme.CARD,
        foreground=Theme.TEXT_MUTED,
        borderwidth=0,
        relief="flat",
        padding=(8, 4),
        font=FONTS["small"],
    )
    style.map(
        "CardGhost.TButton",
        background=[("pressed", "#E9E9E9"), ("active", Theme.HOVER)],
        foreground=[("active", Theme.TEXT)],
    )

    style.configure(
        "TEntry",
        fieldbackground=Theme.CARD,
        foreground=Theme.TEXT,
        bordercolor=Theme.BORDER_STRONG,
        lightcolor=Theme.BORDER_STRONG,
        darkcolor=Theme.BORDER_STRONG,
        padding=(8, 5),
        relief="flat",
    )
    style.map(
        "TEntry",
        bordercolor=[("focus", Theme.ACCENT)],
        lightcolor=[("focus", Theme.ACCENT)],
        darkcolor=[("focus", Theme.ACCENT)],
    )

    style.configure(
        "Cell.TEntry",
        fieldbackground=Theme.CARD,
        foreground=Theme.TEXT,
        bordercolor=Theme.CARD,
        lightcolor=Theme.CARD,
        darkcolor=Theme.CARD,
        padding=(2, 0),
        relief="flat",
    )
    style.map(
        "Cell.TEntry",
        bordercolor=[("focus", Theme.ACCENT)],
        lightcolor=[("focus", Theme.ACCENT)],
        darkcolor=[("focus", Theme.ACCENT)],
    )

    style.configure(
        "TCombobox",
        fieldbackground=Theme.CARD,
        background=Theme.CARD,
        foreground=Theme.TEXT,
        arrowcolor=Theme.TEXT_MUTED,
        bordercolor=Theme.BORDER_STRONG,
        lightcolor=Theme.CARD,
        darkcolor=Theme.CARD,
        padding=(8, 4),
        arrowsize=14,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", Theme.CARD)],
        foreground=[("readonly", Theme.TEXT)],
        selectbackground=[("readonly", Theme.CARD)],
        selectforeground=[("readonly", Theme.TEXT)],
        bordercolor=[("focus", Theme.ACCENT)],
    )

    style.configure(
        "Vertical.TScrollbar",
        background="#DADADA",
        troughcolor=Theme.CARD,
        bordercolor=Theme.CARD,
        arrowcolor=Theme.CARD,
        gripcount=0,
        width=8,
    )
    style.layout(
        "Vertical.TScrollbar",
        [
            (
                "Vertical.Scrollbar.trough",
                {
                    "sticky": "ns",
                    "children": [
                        ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})
                    ],
                },
            )
        ],
    )


def make_card(parent: tk.Misc) -> tk.Frame:
    return tk.Frame(
        parent,
        bg=Theme.CARD,
        bd=0,
        highlightthickness=1,
        highlightbackground=Theme.BORDER,
        highlightcolor=Theme.BORDER,
    )


def separator(parent: tk.Misc, bg: str = Theme.CARD) -> tk.Frame:
    frame = tk.Frame(parent, bg=bg, height=1)
    frame.pack(fill="x")
    return frame


def _rounded_points(x1: float, y1: float, x2: float, y2: float, radius: float) -> List[float]:
    radius = max(0.0, min(radius, (x2 - x1) / 2.0, (y2 - y1) / 2.0))
    return [
        x1 + radius,
        y1,
        x2 - radius,
        y1,
        x2,
        y1,
        x2,
        y1 + radius,
        x2,
        y2 - radius,
        x2,
        y2,
        x2 - radius,
        y2,
        x1 + radius,
        y2,
        x1,
        y2,
        x1,
        y2 - radius,
        x1,
        y1 + radius,
        x1,
        y1,
    ]


def rounded_rect(
    canvas: tk.Canvas,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    radius: float,
    fill: str,
    outline: Optional[str] = None,
    width: int = 1,
    dash: Optional[Tuple[int, int]] = None,
) -> int:
    points = _rounded_points(x1, y1, x2, y2, radius)
    if outline:
        return canvas.create_polygon(
            points,
            smooth=True,
            splinesteps=16,
            fill=fill,
            outline=outline,
            width=width,
            dash=dash,
        )
    return canvas.create_polygon(points, smooth=True, splinesteps=16, fill=fill)


def normalize_hex(color: str) -> str:
    value = (color or "").strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        return value.upper()
    if re.fullmatch(r"#[0-9a-fA-F]{3}", value):
        return ("#" + "".join(char * 2 for char in value[1:])).upper()
    return "#FFFFFF"


class ColorChip(tk.Canvas):
    """A clickable color swatch that shows the current color directly."""

    def __init__(
        self,
        parent: tk.Misc,
        color: str,
        size: int = 24,
        command: Optional[Callable[[], None]] = None,
        bg: str = Theme.CARD,
        selected: bool = False,
        badge: bool = False,
    ):
        super().__init__(
            parent,
            width=size,
            height=size,
            bg=bg,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self._size = size
        self._color = normalize_hex(color)
        self._command = command
        self._selected = selected
        self._badge = badge
        self._hover = False
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self._redraw()

    def set_color(self, color: str, selected: Optional[bool] = None) -> None:
        self._color = normalize_hex(color)
        if selected is not None:
            self._selected = selected
        self._redraw()

    def _on_click(self, _event=None) -> None:
        if self._command:
            self._command()

    def _on_enter(self, _event=None) -> None:
        self._hover = True
        self._redraw()

    def _on_leave(self, _event=None) -> None:
        self._hover = False
        self._redraw()

    def _redraw(self) -> None:
        self.delete("all")
        size = self._size
        if self._selected:
            rounded_rect(self, 0, 0, size, size, 6, fill=Theme.ACCENT)
            rounded_rect(self, 2, 2, size - 2, size - 2, 5, fill=self._color, outline="#C8C8C8", width=1)
        else:
            outline = Theme.ACCENT if self._hover else "#CFCFCF"
            rounded_rect(
                self, 0, 0, size, size, 6, fill=self._color, outline=outline, width=1
            )
        if self._badge:
            badge_size = max(8, int(size * 0.4))
            x2 = size - 1
            y2 = size - 1
            x1 = x2 - badge_size
            y1 = y2 - badge_size
            rounded_rect(self, x1, y1, x2, y2, 4, fill=Theme.CARD, outline="#CFCFCF", width=1)
            pad = max(2, badge_size // 4)
            self.create_line(x1 + pad, (y1 + y2) / 2, x2 - pad, (y1 + y2) / 2, fill=Theme.ACCENT, width=1)
            self.create_line((x1 + x2) / 2, y1 + pad, (x1 + x2) / 2, y2 - pad, fill=Theme.ACCENT, width=1)


class ColorField(tk.Frame):
    """Preset color chips plus a custom color swatch and live hex value."""

    def __init__(
        self,
        parent: tk.Misc,
        presets: Sequence[str],
        value: str,
        on_change: Optional[Callable[[str], None]] = None,
        bg: str = Theme.CARD,
    ):
        super().__init__(parent, bg=bg)
        self._presets = [normalize_hex(item) for item in presets]
        self._value = normalize_hex(value)
        self._on_change = on_change
        self._chips: List[ColorChip] = []

        for preset in self._presets:
            chip = ColorChip(
                self,
                preset,
                size=22,
                command=lambda chosen=preset: self.set_value(chosen),
                bg=bg,
            )
            chip.pack(side="left", padx=(0, 6))
            self._chips.append(chip)

        self._custom = ColorChip(
            self,
            self._value,
            size=22,
            command=self._choose,
            bg=bg,
            badge=True,
        )
        self._custom.pack(side="left", padx=(2, 8))

        self._hex_label = tk.Label(
            self,
            text=self._value,
            font=FONTS["mono"],
            bg=bg,
            fg=Theme.TEXT_FAINT,
        )
        self._hex_label.pack(side="left")

        self._refresh(notify=False)

    def set_value(self, color: str, notify: bool = True) -> None:
        self._value = normalize_hex(color)
        self._refresh(notify=notify)

    def get_value(self) -> str:
        return self._value

    def _refresh(self, notify: bool) -> None:
        is_preset = self._value in self._presets
        for chip, preset in zip(self._chips, self._presets):
            chip.set_color(preset, selected=(preset == self._value))
        self._custom.set_color(self._value, selected=not is_preset)
        self._hex_label.configure(text=self._value)
        if notify and self._on_change:
            self._on_change(self._value)

    def _choose(self) -> None:
        chosen = colorchooser.askcolor(
            color=self._value,
            title="选择颜色",
            parent=self.winfo_toplevel(),
        )
        if chosen and chosen[1]:
            self.set_value(chosen[1])


class ToggleSwitch(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        value: bool = True,
        command: Optional[Callable[[bool], None]] = None,
        bg: str = Theme.CARD,
    ):
        super().__init__(
            parent,
            width=42,
            height=22,
            bg=bg,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self._value = bool(value)
        self._command = command
        self.bind("<Button-1>", self._toggle)
        self._redraw()

    def get(self) -> bool:
        return self._value

    def set(self, value: bool, notify: bool = False) -> None:
        self._value = bool(value)
        self._redraw()
        if notify and self._command:
            self._command(self._value)

    def _toggle(self, _event=None) -> None:
        self.set(not self._value, notify=True)

    def _redraw(self) -> None:
        self.delete("all")
        width, height = 42, 22
        track = Theme.ACCENT if self._value else "#C9C9C9"
        rounded_rect(self, 0, 2, width, height - 2, (height - 4) / 2, fill=track)
        radius = 8
        cy = height / 2
        cx = width - radius - 3 if self._value else radius + 3
        self.create_oval(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            fill="#FFFFFF",
            outline="",
        )


class SegmentedControl(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        options: Sequence[Tuple[str, str]],
        value: Optional[str],
        command: Optional[Callable[[str], None]] = None,
        bg: str = Theme.CARD,
    ):
        super().__init__(parent, bg=bg)
        self._command = command
        self._value = value
        self._labels: Dict[str, tk.Label] = {}

        track = tk.Frame(self, bg=Theme.TRACK, padx=2, pady=2)
        track.pack()
        for key, text in options:
            label = tk.Label(
                track,
                text=text,
                font=FONTS["small"],
                bg=Theme.TRACK,
                fg=Theme.TEXT_MUTED,
                padx=10,
                pady=4,
                cursor="hand2",
            )
            label.pack(side="left")
            label.bind("<Button-1>", lambda _event, k=key: self.set_value(k, notify=True))
            label.bind("<Enter>", lambda _event, k=key: self._hover(k, True))
            label.bind("<Leave>", lambda _event, k=key: self._hover(k, False))
            self._labels[key] = label
        self._apply()

    def get_value(self) -> Optional[str]:
        return self._value

    def set_value(self, value: Optional[str], notify: bool = False) -> None:
        self._value = value
        self._apply()
        if notify and self._command and value is not None:
            self._command(value)

    def _apply(self) -> None:
        for key, label in self._labels.items():
            if key == self._value:
                label.configure(
                    bg=Theme.CARD, fg=Theme.ACCENT, font=FONTS["small_bold"]
                )
            else:
                label.configure(
                    bg=Theme.TRACK, fg=Theme.TEXT_MUTED, font=FONTS["small"]
                )

    def _hover(self, key: str, entering: bool) -> None:
        label = self._labels.get(key)
        if label is None or key == self._value:
            return
        label.configure(fg=Theme.TEXT if entering else Theme.TEXT_MUTED)


class ModernSlider(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        minimum: float,
        maximum: float,
        value: float,
        command: Optional[Callable[[float], None]] = None,
        bg: str = Theme.CARD,
        width: int = 170,
    ):
        super().__init__(
            parent,
            width=width,
            height=24,
            bg=bg,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self._min = float(minimum)
        self._max = float(maximum)
        self._value = float(value)
        self._command = command
        self.bind("<Configure>", lambda _event: self._redraw())
        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self._redraw()

    def get(self) -> float:
        return self._value

    def set(self, value: float, notify: bool = False) -> None:
        self._value = max(self._min, min(self._max, float(value)))
        self._redraw()
        if notify and self._command:
            self._command(self._value)

    def _on_click(self, event) -> None:
        self._update_from_x(event.x, notify=True)

    def _on_drag(self, event) -> None:
        self._update_from_x(event.x, notify=True)

    def _update_from_x(self, x: float, notify: bool) -> None:
        width = max(self.winfo_width(), 40)
        left, right = 10, width - 10
        ratio = (x - left) / max(1, right - left)
        ratio = max(0.0, min(1.0, ratio))
        value = self._min + ratio * (self._max - self._min)
        self.set(value, notify=notify)

    def _redraw(self) -> None:
        self.delete("all")
        width = max(self.winfo_width(), 40)
        height = 24
        left, right = 10, width - 10
        center = height / 2
        ratio = (self._value - self._min) / max(1e-9, self._max - self._min)
        knob_x = left + ratio * (right - left)

        rounded_rect(self, left, center - 2, right, center + 2, 2, fill="#E4E4E4")
        if knob_x > left + 1:
            rounded_rect(self, left, center - 2, knob_x, center + 2, 2, fill=Theme.ACCENT)
        radius = 8
        self.create_oval(
            knob_x - radius + 0.5,
            center - radius + 0.5,
            knob_x + radius - 0.5,
            center + radius - 0.5,
            fill="#FFFFFF",
            outline="#C4C4C4",
            width=1,
        )


class DropZone(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        command: Callable[[], None],
        bg: str = Theme.BG,
        height: int = 136,
    ):
        super().__init__(
            parent,
            height=height,
            bg=bg,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self._command = command
        self._height = height
        self._hover = False
        self.bind("<Configure>", lambda _event: self._redraw())
        self.bind("<Button-1>", lambda _event: self._command())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self._redraw()

    def _on_enter(self, _event=None) -> None:
        self._hover = True
        self._redraw()

    def _on_leave(self, _event=None) -> None:
        self._hover = False
        self._redraw()

    def _redraw(self) -> None:
        self.delete("all")
        width = max(self.winfo_width(), 200)
        height = self._height
        border = Theme.ACCENT if self._hover else "#CFCFCF"
        points = _rounded_points(1, 1, width - 1, height - 1, 10)
        self.create_polygon(
            points,
            smooth=True,
            splinesteps=16,
            fill=Theme.ACCENT_TINT if self._hover else "#FBFBFB",
            outline=border,
            width=1,
            dash=(4, 3),
        )

        cx = width / 2
        icon_cy = 42
        self.create_oval(
            cx - 17,
            icon_cy - 17,
            cx + 17,
            icon_cy + 17,
            fill=Theme.ACCENT_TINT,
            outline="",
        )
        self.create_line(
            cx,
            icon_cy - 9,
            cx,
            icon_cy + 7,
            fill=Theme.ACCENT,
            width=2,
            arrow="last",
            arrowshape=(5, 7, 4),
        )
        self.create_line(
            cx - 8, icon_cy + 11, cx + 8, icon_cy + 11, fill=Theme.ACCENT, width=2
        )

        self.create_text(
            cx,
            84,
            text="将 LAMMPS data 或轨迹文件拖到这里",
            font=FONTS["bold"],
            fill=Theme.TEXT,
        )
        self.create_text(
            cx,
            105,
            text="或点击选择文件 · 不限后缀 · 加载后自行调整",
            font=FONTS["small"],
            fill=Theme.TEXT_MUTED,
        )


class ScrollList(tk.Frame):
    """A scrollable white list container with mouse-wheel support."""

    def __init__(self, parent: tk.Misc, bg: str = Theme.CARD):
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(
            self,
            orient="vertical",
            command=self.canvas.yview,
            style="Vertical.TScrollbar",
        )
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self._scrollbar_visible = False

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_wheel, add="+")

    def clear(self) -> None:
        for child in self.inner.winfo_children():
            child.destroy()
        self.canvas.yview_moveto(0)

    def _on_inner_configure(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._update_scrollbar()

    def _on_canvas_configure(self, event) -> None:
        self.canvas.itemconfigure(self._window, width=event.width)
        self._update_scrollbar()

    def _update_scrollbar(self) -> None:
        needed = self.inner.winfo_reqheight() > self.canvas.winfo_height()
        if needed and not self._scrollbar_visible:
            self.scrollbar.pack(side="right", fill="y")
            self._scrollbar_visible = True
        elif not needed and self._scrollbar_visible:
            self.scrollbar.pack_forget()
            self._scrollbar_visible = False

    def _on_wheel(self, event) -> None:
        widget = self.winfo_toplevel().winfo_containing(event.x_root, event.y_root)
        current = widget
        while current is not None:
            if current is self:
                break
            current = getattr(current, "master", None)
        else:
            return
        if self.inner.winfo_reqheight() <= self.canvas.winfo_height():
            return
        self.canvas.yview_scroll(int(-event.delta / 120), "units")
