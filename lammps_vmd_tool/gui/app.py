"""Win11-style Tkinter front-end for the LAMMPS -> VMD viewer."""

from __future__ import annotations

import ctypes
import os
import sys
import tempfile
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk
from typing import Dict, List, Optional

from ..core.launcher import find_vmd_executable, launch_vmd, save_config
from ..core.parser import (
    AtomTypeData,
    InvalidEncodingError,
    LammpsDataInfo,
    LammpsDataParser,
    LammpsFileError,
)
from ..core.vmd_generator import VisualSettings, VmdScriptGenerator
from . import theme
from .dnd import hook_drop_files
from .theme import (
    ColorChip,
    ColorField,
    DropZone,
    FONTS,
    ModernSlider,
    ScrollList,
    SegmentedControl,
    Theme,
    ToggleSwitch,
    make_card,
    normalize_hex,
)


REP_OPTIONS = [
    ("CPK 球棍", "CPK"),
    ("VDW 空间填充", "VDW"),
    ("Licorice 棍状", "Licorice"),
    ("DynamicBonds 动态键", "DynamicBonds"),
    ("Lines 线框", "Lines"),
]

PRESET_OPTIONS = [
    ("publication", "期刊"),
    ("dark", "深色"),
    ("spacefill", "填充"),
    ("skeleton", "骨架"),
]

PROJECTION_OPTIONS = [
    ("Orthographic", "正交"),
    ("Perspective", "透视"),
]


def _enable_dpi_awareness() -> None:
    if not sys.platform.startswith("win"):
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _resource_path(relative: str) -> str:
    base = getattr(sys, "_MEIPASS", None)
    if base is None:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, relative)


def _shorten(text: str, limit: int = 64) -> str:
    if len(text) <= limit:
        return text
    return text[: limit // 2 - 2] + "…" + text[-(limit // 2 - 1):]


class LammpsVmdApp(tk.Tk):
    def __init__(self, initial_file: str = ""):
        super().__init__()
        self.title("LAMMPS → VMD")
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        width = min(1100, max(900, screen_width - 80))
        height = min(800, max(650, screen_height - 110))
        self.geometry(
            f"{width}x{height}+{(screen_width - width) // 2}+"
            f"{max(0, (screen_height - height) // 2 - 20)}"
        )
        self.minsize(940, 650)
        self.configure(bg=Theme.BG)
        try:
            self.tk.call("tk", "scaling", self.winfo_fpixels("1i") / 72.0)
        except Exception:
            pass

        theme.apply_theme(self)
        self._set_window_icon()

        self.info: Optional[LammpsDataInfo] = None
        self.atom_types: Dict[int, AtomTypeData] = {}
        self.current_path = ""
        self.vmd_exe = find_vmd_executable() or ""
        self._file_card_visible = False

        # Visual state (kept in sync with the settings widgets)
        self.preset_key: Optional[str] = "publication"
        self.rep_style = "CPK"
        self.sphere_scale = 0.35
        self.bond_radius = 0.18
        self.material = "Opaque"
        self.bg_color = "#FFFFFF"
        self.projection = "Orthographic"
        self.show_axes = False
        self.depthcue = False
        self.show_box = True
        self.box_color = "#1A1A1A"
        self.auto_bonds = True

        self._rep_label_to_key = {label: key for label, key in REP_OPTIONS}
        self._rep_key_to_label = {key: label for label, key in REP_OPTIONS}

        self._build_ui()
        self._apply_preset("publication")
        self._update_vmd_status()
        self._update_actions()
        self._set_status("就绪 · 导入文件后可先调整设置，再点击“在 VMD 中显示”")

        hook_drop_files(self, self._on_files_dropped)

        if initial_file and os.path.isfile(initial_file):
            self.after(120, lambda: self._load_file(initial_file))

    # ------------------------------------------------------------------
    # Window scaffolding
    # ------------------------------------------------------------------
    def _set_window_icon(self) -> None:
        icon = _resource_path(os.path.join("assets", "app.ico"))
        if os.path.isfile(icon):
            try:
                self.iconbitmap(icon)
            except Exception:
                pass

    def _build_ui(self) -> None:
        header = tk.Frame(self, bg=Theme.BG)
        header.pack(fill="x", padx=26, pady=(18, 4))

        title_box = tk.Frame(header, bg=Theme.BG)
        title_box.pack(side="left")
        tk.Label(
            title_box,
            text="LAMMPS → VMD",
            font=FONTS["hero"],
            bg=Theme.BG,
            fg=Theme.TEXT,
        ).pack(anchor="w")
        tk.Label(
            title_box,
            text="拖入文件，调整好样式后再打开 VMD",
            font=FONTS["small"],
            bg=Theme.BG,
            fg=Theme.TEXT_MUTED,
        ).pack(anchor="w", pady=(2, 0))

        vmd_box = tk.Frame(header, bg=Theme.BG)
        vmd_box.pack(side="right")
        self.vmd_badge = tk.Label(
            vmd_box,
            text="检测 VMD …",
            font=FONTS["small_bold"],
            bg=Theme.CARD,
            fg=Theme.TEXT_MUTED,
            padx=10,
            pady=4,
        )
        self.vmd_badge.pack(side="left", padx=(0, 8))
        tk.Button(
            vmd_box,
            text="VMD 路径",
            font=FONTS["small"],
            bg=Theme.BG,
            fg=Theme.TEXT_MUTED,
            activebackground="#EAEAEA",
            activeforeground=Theme.TEXT,
            relief="flat",
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._on_set_vmd_path,
        ).pack(side="left")

        self._top_slot = tk.Frame(self, bg=Theme.BG)
        self._top_slot.pack(fill="x", padx=26, pady=(8, 0))
        self.drop_zone = DropZone(self._top_slot, command=self._on_browse, bg=Theme.BG)
        self.drop_zone.pack(fill="x")
        self.file_card = self._build_file_card(self._top_slot)

        self._build_footer()

        content = tk.Frame(self, bg=Theme.BG)
        content.pack(fill="both", expand=True, padx=26, pady=(14, 0))
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=3, minsize=520)
        content.grid_columnconfigure(1, weight=2, minsize=330)

        types_card = make_card(content)
        types_card.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        self._build_types_card(types_card)

        settings_card = make_card(content)
        settings_card.grid(row=0, column=1, sticky="nsew")
        self._build_settings_card(settings_card)

    def _build_footer(self) -> None:
        footer = tk.Frame(self, bg=Theme.BG)
        footer.pack(side="bottom", fill="x", padx=26, pady=(12, 14))

        self.status_label = tk.Label(
            footer,
            text="",
            font=FONTS["small"],
            bg=Theme.BG,
            fg=Theme.TEXT_MUTED,
            anchor="w",
            justify="left",
        )
        self.status_label.pack(side="left", fill="x", expand=True)

        self.btn_launch = tk.Button(
            footer,
            text="在 VMD 中显示",
            font=FONTS["bold"],
            bg=Theme.ACCENT,
            fg="#FFFFFF",
            activebackground=Theme.ACCENT_HOVER,
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            padx=20,
            pady=9,
            cursor="hand2",
            command=self._on_launch,
        )
        self.btn_launch.pack(side="right")

        self.btn_export = tk.Button(
            footer,
            text="导出脚本",
            font=FONTS["small"],
            bg=Theme.CARD,
            fg=Theme.TEXT,
            activebackground=Theme.HOVER,
            activeforeground=Theme.TEXT,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=Theme.BORDER_STRONG,
            padx=14,
            pady=7,
            cursor="hand2",
            command=self._on_export,
        )
        self.btn_export.pack(side="right", padx=(0, 10))

    def _build_file_card(self, parent: tk.Misc) -> tk.Frame:
        card = make_card(parent)
        inner = tk.Frame(card, bg=Theme.CARD, padx=18, pady=14)
        inner.pack(fill="both", expand=True)

        top = tk.Frame(inner, bg=Theme.CARD)
        top.pack(fill="x")

        self.file_badge = tk.Label(
            top,
            text="数据文件",
            font=FONTS["small_bold"],
            bg=Theme.ACCENT_TINT,
            fg=Theme.ACCENT,
            padx=8,
            pady=3,
        )
        self.file_badge.pack(side="left", padx=(0, 10))

        self.file_name_label = tk.Label(
            top,
            text="",
            font=FONTS["title"],
            bg=Theme.CARD,
            fg=Theme.TEXT,
            anchor="w",
        )
        self.file_name_label.pack(side="left")

        tk.Button(
            top,
            text="更换文件",
            font=FONTS["small"],
            bg=Theme.CARD,
            fg=Theme.TEXT_MUTED,
            activebackground=Theme.HOVER,
            activeforeground=Theme.TEXT,
            relief="flat",
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            command=self._on_browse,
        ).pack(side="right")
        tk.Button(
            top,
            text="重新加载",
            font=FONTS["small"],
            bg=Theme.CARD,
            fg=Theme.TEXT_MUTED,
            activebackground=Theme.HOVER,
            activeforeground=Theme.TEXT,
            relief="flat",
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            command=self._on_reload,
        ).pack(side="right", padx=(0, 2))

        self.file_path_label = tk.Label(
            inner,
            text="",
            font=FONTS["small"],
            bg=Theme.CARD,
            fg=Theme.TEXT_MUTED,
            anchor="w",
            justify="left",
        )
        self.file_path_label.pack(fill="x", pady=(4, 6))
        card.bind(
            "<Configure>",
            lambda event: self.file_path_label.configure(
                wraplength=max(240, event.width - 40)
            ),
        )

        stats_row = tk.Frame(inner, bg=Theme.CARD)
        stats_row.pack(fill="x")
        self.file_stats_label = tk.Label(
            stats_row,
            text="",
            font=FONTS["small"],
            bg=Theme.CARD,
            fg=Theme.TEXT_MUTED,
            anchor="w",
        )
        self.file_stats_label.pack(side="left")
        tk.Label(
            stats_row,
            text="可将其他文件直接拖入窗口替换",
            font=FONTS["small"],
            bg=Theme.CARD,
            fg=Theme.TEXT_FAINT,
        ).pack(side="right")

        return card

    def _build_types_card(self, card: tk.Frame) -> None:
        inner = tk.Frame(card, bg=Theme.CARD, padx=18, pady=16)
        inner.pack(fill="both", expand=True)

        head = tk.Frame(inner, bg=Theme.CARD)
        head.pack(fill="x")
        tk.Label(
            head,
            text="原子类型",
            font=FONTS["title"],
            bg=Theme.CARD,
            fg=Theme.TEXT,
        ).pack(side="left")
        tk.Label(
            head,
            text="点击色块修改颜色 · 半径可直接编辑",
            font=FONTS["small"],
            bg=Theme.CARD,
            fg=Theme.TEXT_FAINT,
        ).pack(side="right")

        self.types_header = tk.Frame(inner, bg=Theme.CARD)
        self.types_header.pack(fill="x", pady=(14, 6))
        columns = [
            ("类型", "w", 54),
            ("质量", "e", 66),
            ("半径 (Å)", "center", 72),
            ("颜色", "center", 50),
            ("注释说明", "w", 0),
        ]
        for index, (text, anchor, width) in enumerate(columns):
            if width:
                self.types_header.grid_columnconfigure(index, minsize=width)
            label = tk.Label(
                self.types_header,
                text=text,
                font=FONTS["small_bold"],
                bg=Theme.CARD,
                fg=Theme.TEXT_MUTED,
                anchor=anchor,
            )
            sticky = "w" if index in (0, 4) else ("e" if index == 1 else "ew")
            label.grid(row=0, column=index, sticky=sticky, padx=(0, 6))
        self.types_header.grid_columnconfigure(4, weight=1)

        self.types_list = ScrollList(inner, bg=Theme.CARD)
        self.types_list.pack(fill="both", expand=True)
        self._render_types()

    def _build_settings_card(self, card: tk.Frame) -> None:
        inner = tk.Frame(card, bg=Theme.CARD, padx=18, pady=16)
        inner.pack(fill="both", expand=True)

        tk.Label(
            inner,
            text="显示设置",
            font=FONTS["title"],
            bg=Theme.CARD,
            fg=Theme.TEXT,
        ).pack(anchor="w")

        preset_row = tk.Frame(inner, bg=Theme.CARD)
        preset_row.pack(fill="x", pady=(10, 0))
        tk.Label(
            preset_row,
            text="预设",
            font=FONTS["small"],
            bg=Theme.CARD,
            fg=Theme.TEXT_MUTED,
            width=8,
            anchor="w",
        ).pack(side="left")
        self.preset_control = SegmentedControl(
            preset_row,
            PRESET_OPTIONS,
            "publication",
            command=self._on_preset_change,
            bg=Theme.CARD,
        )
        self.preset_control.pack(side="left", padx=(8, 0))

        tk.Frame(inner, bg=Theme.BORDER, height=1).pack(fill="x", pady=(12, 8))

        form = tk.Frame(inner, bg=Theme.CARD)
        form.pack(fill="both", expand=True)
        form.grid_columnconfigure(0, minsize=84)
        form.grid_columnconfigure(1, weight=1)

        # Representation
        self._form_label(form, 0, "表示")
        self.rep_combo = theme.ttk.Combobox(
            form,
            values=[label for label, _key in REP_OPTIONS],
            state="readonly",
            width=18,
        )
        self.rep_combo.grid(row=0, column=1, sticky="w", pady=5)
        self.rep_combo.bind("<<ComboboxSelected>>", self._on_rep_changed)

        # Sphere scale
        self._form_label(form, 1, "球体缩放")
        sphere_box = tk.Frame(form, bg=Theme.CARD)
        sphere_box.grid(row=1, column=1, sticky="w", pady=3)
        self.sphere_slider = ModernSlider(
            sphere_box, 0.10, 1.50, 0.35, command=self._on_sphere_changed, bg=Theme.CARD
        )
        self.sphere_slider.pack(side="left")
        self.sphere_value = tk.Label(
            sphere_box, text="0.35", font=FONTS["mono"], bg=Theme.CARD, fg=Theme.TEXT
        )
        self.sphere_value.pack(side="left", padx=(8, 0))

        # Bond radius
        self._form_label(form, 2, "键半径")
        bond_box = tk.Frame(form, bg=Theme.CARD)
        bond_box.grid(row=2, column=1, sticky="w", pady=3)
        self.bond_slider = ModernSlider(
            bond_box, 0.05, 0.50, 0.18, command=self._on_bond_changed, bg=Theme.CARD
        )
        self.bond_slider.pack(side="left")
        self.bond_value = tk.Label(
            bond_box, text="0.18", font=FONTS["mono"], bg=Theme.CARD, fg=Theme.TEXT
        )
        self.bond_value.pack(side="left", padx=(8, 0))

        # Background
        self._form_label(form, 3, "背景颜色")
        self.bg_field = ColorField(
            form,
            ("#FFFFFF", "#000000", "#808080"),
            "#FFFFFF",
            on_change=self._on_bg_changed,
            bg=Theme.CARD,
        )
        self.bg_field.grid(row=3, column=1, sticky="w", pady=5)

        # Projection
        self._form_label(form, 4, "投影")
        self.projection_control = SegmentedControl(
            form,
            PROJECTION_OPTIONS,
            "Orthographic",
            command=self._on_projection_changed,
            bg=Theme.CARD,
        )
        self.projection_control.grid(row=4, column=1, sticky="w", pady=5)

        # Box + border color
        self._form_label(form, 5, "晶胞")
        box_row = tk.Frame(form, bg=Theme.CARD)
        box_row.grid(row=5, column=1, sticky="w", pady=5)
        self.box_toggle = ToggleSwitch(
            box_row, True, command=self._on_box_toggled, bg=Theme.CARD
        )
        self.box_toggle.pack(side="left")
        tk.Label(
            box_row,
            text="边框色",
            font=FONTS["small"],
            bg=Theme.CARD,
            fg=Theme.TEXT_MUTED,
        ).pack(side="left", padx=(14, 6))
        self.box_chip = ColorChip(
            box_row,
            self.box_color,
            size=22,
            command=self._pick_box_color,
            bg=Theme.CARD,
            badge=True,
        )
        self.box_chip.pack(side="left")
        self.box_hex = tk.Label(
            box_row, text=self.box_color, font=FONTS["mono"], bg=Theme.CARD, fg=Theme.TEXT_FAINT
        )
        self.box_hex.pack(side="left", padx=(8, 0))

        tk.Label(
            inner,
            text="脚本通过 VMD Tk Console 执行 · 无键体系自动生成距离键",
            font=FONTS["small"],
            bg=Theme.CARD,
            fg=Theme.TEXT_FAINT,
            anchor="w",
            justify="left",
            wraplength=300,
        ).pack(side="bottom", anchor="w", pady=(10, 0))

    def _form_label(self, parent: tk.Misc, row: int, text: str) -> None:
        tk.Label(
            parent,
            text=text,
            font=FONTS["small"],
            bg=Theme.CARD,
            fg=Theme.TEXT_MUTED,
            anchor="w",
        ).grid(row=row, column=0, sticky="w", pady=4)

    # ------------------------------------------------------------------
    # Settings sync
    # ------------------------------------------------------------------
    def _apply_preset(self, key: Optional[str]) -> None:
        if key is None:
            return
        settings = VmdScriptGenerator.PRESETS.get(key)
        if settings is None:
            return
        self.preset_key = key
        self.rep_style = settings.rep_style
        self.sphere_scale = settings.sphere_scale
        self.bond_radius = settings.bond_radius
        self.material = settings.material
        self.bg_color = settings.bg_color
        self.projection = settings.projection
        self.show_axes = settings.show_axes
        self.depthcue = settings.depthcue
        self.show_box = settings.show_box
        self.box_color = settings.box_color

        self.preset_control.set_value(key)
        self.rep_combo.set(self._rep_key_to_label.get(self.rep_style, self.rep_style))
        self.sphere_slider.set(self.sphere_scale)
        self.sphere_value.configure(text=f"{self.sphere_scale:.2f}")
        self.bond_slider.set(self.bond_radius)
        self.bond_value.configure(text=f"{self.bond_radius:.2f}")
        self.bg_field.set_value(self.bg_color, notify=False)
        self.projection_control.set_value(self.projection)
        self.box_toggle.set(self.show_box)
        self.box_chip.set_color(self.box_color)
        self.box_hex.configure(text=self.box_color)

    def _mark_custom(self) -> None:
        self.preset_key = None
        self.preset_control.set_value(None)

    def _on_preset_change(self, key: str) -> None:
        self._apply_preset(key)

    def _on_rep_changed(self, _event=None) -> None:
        key = self._rep_label_to_key.get(self.rep_combo.get())
        if key:
            self.rep_style = key
            self._mark_custom()

    def _on_sphere_changed(self, value: float) -> None:
        self.sphere_scale = round(value, 2)
        self.sphere_value.configure(text=f"{self.sphere_scale:.2f}")
        self._mark_custom()

    def _on_bond_changed(self, value: float) -> None:
        self.bond_radius = round(value, 2)
        self.bond_value.configure(text=f"{self.bond_radius:.2f}")
        self._mark_custom()

    def _on_bg_changed(self, color: str) -> None:
        self.bg_color = color
        self._mark_custom()

    def _on_projection_changed(self, value: str) -> None:
        self.projection = value
        self._mark_custom()

    def _on_box_toggled(self, value: bool) -> None:
        self.show_box = value
        self._mark_custom()

    def _pick_box_color(self) -> None:
        chosen = colorchooser.askcolor(
            color=self.box_color, title="选择晶胞边框颜色", parent=self
        )
        if chosen and chosen[1]:
            self.box_color = normalize_hex(chosen[1])
            self.box_chip.set_color(self.box_color)
            self.box_hex.configure(text=self.box_color)
            self._mark_custom()

    def _settings(self) -> VisualSettings:
        return VisualSettings(
            preset_name=self.preset_key or "custom",
            rep_style=self.rep_style,
            sphere_scale=self.sphere_scale,
            bond_radius=self.bond_radius,
            material=self.material,
            bg_color=self.bg_color,
            projection=self.projection,
            show_axes=self.show_axes,
            depthcue=self.depthcue,
            show_box=self.show_box,
            box_color=self.box_color,
            box_width=1.5,
            auto_bonds=self.auto_bonds,
            bond_cutoff=1.6,
        )

    # ------------------------------------------------------------------
    # File loading
    # ------------------------------------------------------------------
    def _on_files_dropped(self, files: List[str]) -> None:
        if files:
            self._load_file(files[0])

    def _on_browse(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="选择 LAMMPS data 或轨迹文件",
        )
        if path:
            self._load_file(path)

    def _on_reload(self) -> None:
        if not self.current_path:
            return
        if self._load_file(self.current_path):
            self._set_status(f"已重新加载 {os.path.basename(self.current_path)}")

    def _load_file(self, path: str) -> bool:
        self._set_status(f"正在读取 {os.path.basename(path)} …")
        self.update_idletasks()
        try:
            info = LammpsDataParser.parse(path)
        except InvalidEncodingError as exc:
            messagebox.showerror("编码错误", str(exc), parent=self)
            self._set_status("加载失败：文件不是 UTF-8 编码")
            return False
        except LammpsFileError as exc:
            messagebox.showerror("无法加载文件", str(exc), parent=self)
            self._set_status("加载失败：无法识别文件内容")
            return False
        except Exception as exc:
            messagebox.showerror(
                "无法加载文件", f"读取文件时发生错误：\n{exc}", parent=self
            )
            self._set_status("加载失败")
            return False

        self.info = info
        self.current_path = os.path.abspath(path)
        self.atom_types = dict(info.atom_types)
        self._show_file_card()
        self._render_types()
        self._update_actions()
        self._set_status(
            f"已加载 {os.path.basename(self.current_path)} · "
            f"{info.num_atoms:,} 原子 · 调整后点击“在 VMD 中显示”"
        )
        return True

    def _show_file_card(self) -> None:
        self.drop_zone.pack_forget()
        if not self._file_card_visible:
            self.file_card.pack(fill="x")
            self._file_card_visible = True

        info = self.info
        if info is None:
            return

        self.file_badge.configure(
            text="数据文件" if info.file_type == "data" else "轨迹文件"
        )
        self.file_name_label.configure(
            text=_shorten(os.path.basename(info.filepath), 58)
        )
        self.file_path_label.configure(text=info.filepath)

        parts = [f"{info.num_atoms:,} 原子"]
        if info.file_type == "data":
            parts.append(f"{info.num_bonds:,} 键")
        parts.append(f"{len(info.atom_types):,} 种类型")
        if info.box:
            box = info.box
            box_kind = "三斜晶胞" if box.is_triclinic else "正交晶胞"
            parts.append(
                f"{box_kind} {box.lx:.2f} × {box.ly:.2f} × {box.lz:.2f} Å"
            )
        else:
            parts.append("无晶胞信息")
        self.file_stats_label.configure(text="  ·  ".join(parts))

    def _render_types(self) -> None:
        self.types_list.clear()
        if not self.atom_types:
            tk.Label(
                self.types_list.inner,
                text="尚未加载文件" if self.info is None else "该文件未提供原子类型",
                font=FONTS["small"],
                bg=Theme.CARD,
                fg=Theme.TEXT_FAINT,
            ).pack(pady=44)
            return

        for atom_type in sorted(self.atom_types.values(), key=lambda item: item.type_id):
            self._add_type_row(atom_type)

    def _add_type_row(self, atom_type: AtomTypeData) -> None:
        row = tk.Frame(self.types_list.inner, bg=Theme.CARD)
        row.pack(fill="x")
        for index, width in enumerate((54, 66, 72, 50)):
            row.grid_columnconfigure(index, minsize=width)
        row.grid_columnconfigure(4, weight=1)

        tk.Label(
            row,
            text=str(atom_type.type_id),
            font=FONTS["bold"],
            bg=Theme.CARD,
            fg=Theme.TEXT,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=(0, 6), pady=7)

        mass_text = "—" if atom_type.mass <= 0 else f"{atom_type.mass:.3f}"
        tk.Label(
            row,
            text=mass_text,
            font=FONTS["small"],
            bg=Theme.CARD,
            fg=Theme.TEXT_MUTED,
            anchor="e",
        ).grid(row=0, column=1, sticky="e", padx=(0, 8), pady=7)

        radius_var = tk.StringVar(value=f"{atom_type.radius:.3f}")
        radius_entry = tk.Entry(
            row,
            textvariable=radius_var,
            font=FONTS["mono"],
            bg=Theme.CARD,
            fg=Theme.TEXT,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=Theme.CARD,
            highlightcolor=Theme.ACCENT,
            justify="center",
            width=7,
        )
        radius_entry.grid(row=0, column=2, sticky="ew", padx=(0, 8), pady=4)

        def commit_radius(var=radius_var, data=atom_type) -> None:
            try:
                value = float(var.get())
                if value <= 0:
                    raise ValueError
            except ValueError:
                var.set(f"{data.radius:.3f}")
                return
            data.radius = value
            var.set(f"{value:.3f}")

        radius_entry.bind("<Return>", lambda _event: commit_radius())
        radius_entry.bind("<FocusOut>", lambda _event: commit_radius())

        chip = ColorChip(
            row,
            atom_type.color,
            size=20,
            bg=Theme.CARD,
            command=lambda data=atom_type: self._pick_type_color(data),
        )
        chip.grid(row=0, column=3, sticky="w", padx=(0, 10), pady=6)

        comment = atom_type.comment.strip()
        tk.Label(
            row,
            text=comment if comment else "—",
            font=FONTS["small"],
            bg=Theme.CARD,
            fg=Theme.TEXT if comment else Theme.TEXT_FAINT,
            anchor="w",
        ).grid(row=0, column=4, sticky="ew", pady=7)

        tk.Frame(self.types_list.inner, bg="#F0F0F0", height=1).pack(fill="x")

    def _pick_type_color(self, atom_type: AtomTypeData) -> None:
        chosen = colorchooser.askcolor(
            color=atom_type.color,
            title=f"选择类型 {atom_type.type_id} 的颜色",
            parent=self,
        )
        if chosen and chosen[1]:
            atom_type.color = normalize_hex(chosen[1])
            self._render_types()

    # ------------------------------------------------------------------
    # VMD launch / export
    # ------------------------------------------------------------------
    def _update_actions(self) -> None:
        enabled = self.info is not None
        state = "normal" if enabled else "disabled"
        self.btn_launch.configure(
            state=state,
            bg=Theme.ACCENT if enabled else "#C9C9C9",
            activebackground=Theme.ACCENT_HOVER if enabled else "#C9C9C9",
            cursor="hand2" if enabled else "arrow",
        )
        self.btn_export.configure(
            state=state,
            fg=Theme.TEXT if enabled else Theme.TEXT_FAINT,
            cursor="hand2" if enabled else "arrow",
        )

    def _update_vmd_status(self) -> None:
        if self.vmd_exe and os.path.isfile(self.vmd_exe):
            folder = os.path.basename(os.path.dirname(self.vmd_exe))
            text = f"VMD 已就绪 · {folder}" if folder else "VMD 已就绪"
            self.vmd_badge.configure(text=text, bg=Theme.SUCCESS_TINT, fg=Theme.SUCCESS)
        else:
            self.vmd_badge.configure(
                text="未找到 VMD", bg=Theme.DANGER_TINT, fg=Theme.DANGER
            )

    def _on_set_vmd_path(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="选择 VMD 主程序 (vmd.exe)",
            filetypes=[("VMD 可执行文件", "vmd.exe"), ("所有文件", "*.*")],
        )
        if path and os.path.isfile(path):
            self.vmd_exe = path
            save_config({"vmd_path": path})
            self._update_vmd_status()
            self._set_status(f"VMD 路径已设置：{path}")

    def _ensure_vmd(self) -> bool:
        if self.vmd_exe and os.path.isfile(self.vmd_exe):
            return True
        detected = find_vmd_executable()
        if detected:
            self.vmd_exe = detected
            self._update_vmd_status()
            return True
        path = filedialog.askopenfilename(
            parent=self,
            title="未检测到 VMD，请选择 vmd.exe",
            filetypes=[("VMD 可执行文件", "vmd.exe"), ("所有文件", "*.*")],
        )
        if path and os.path.isfile(path):
            self.vmd_exe = path
            save_config({"vmd_path": path})
            self._update_vmd_status()
            return True
        self._set_status("未找到 VMD，请先设置 VMD 路径")
        return False

    def generate_script(self) -> str:
        if self.info is None:
            return "# No LAMMPS file loaded\n"
        return VmdScriptGenerator.generate(
            info=self.info,
            atom_types=self.atom_types,
            settings=self._settings(),
        )

    def _on_launch(self) -> None:
        self._launch_vmd()

    def _launch_vmd(self) -> None:
        if self.info is None:
            messagebox.showwarning("提示", "请先加载 LAMMPS 文件。", parent=self)
            return
        if not self._ensure_vmd():
            return

        script = self.generate_script()
        try:
            fd, script_path = tempfile.mkstemp(prefix="lammps_vmd_", suffix=".vmd")
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(script)
            launch_vmd(script_path, self.vmd_exe)
        except Exception as exc:
            messagebox.showerror("启动 VMD 失败", f"无法启动 VMD：\n{exc}", parent=self)
            self._set_status("启动 VMD 失败")
            return
        self._set_status(
            f"已在 VMD 中打开 {os.path.basename(self.info.filepath)}"
        )

    def _on_export(self) -> None:
        if self.info is None:
            return
        base = os.path.splitext(os.path.basename(self.info.filepath))[0]
        path = filedialog.asksaveasfilename(
            parent=self,
            title="导出 VMD 脚本",
            initialfile=f"{base}_view.vmd",
            defaultextension=".vmd",
            filetypes=[("VMD / Tcl 脚本", "*.vmd"), ("所有文件", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(self.generate_script())
        except OSError as exc:
            messagebox.showerror("导出失败", f"无法写入文件：\n{exc}", parent=self)
            return
        self._set_status(f"脚本已导出：{path}")

    def _set_status(self, text: str) -> None:
        self.status_label.configure(text=text)


def main() -> None:
    _enable_dpi_awareness()
    initial_file = ""
    for argument in sys.argv[1:]:
        if not argument.startswith("-") and os.path.isfile(argument):
            initial_file = argument
            break
    app = LammpsVmdApp(initial_file=initial_file)
    app.mainloop()


if __name__ == "__main__":
    main()
