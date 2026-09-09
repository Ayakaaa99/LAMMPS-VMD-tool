"""
Modern, streamlined Tkinter GUI for LAMMPS Data to VMD Visualization.
Features:
- Sleek modern card-based interface with high-contrast visual styling
- Drag & drop support across the entire window
- Auto-launch VMD option on file drop
- Robust element auto-detection and vibrant color mapping
- Publication-quality presets (Opaque/Glossy, no washed-out chalky white)
- 1-Click VMD launcher and .vmd script export
"""

import os
import sys
import tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from ..core.parser import LammpsDataParser, LammpsDataInfo, AtomTypeData
from ..core.periodic_table import ELEMENTS_DB, get_element_info, guess_element_from_mass
from ..core.vmd_generator import VmdScriptGenerator, VisualSettings
from ..core.launcher import find_vmd_executable, launch_vmd, save_config
from .dnd import hook_drop_files


class ModernTheme:
    BG_MAIN = "#F8FAFC"       # Slate 50
    CARD_BG = "#FFFFFF"       # Pure white card
    BORDER = "#E2E8F0"        # Subtle border
    PRIMARY = "#2563EB"       # Modern Royal Blue
    PRIMARY_HOVER = "#1D4ED8"
    TEXT_MAIN = "#0F172A"     # Slate 900
    TEXT_MUTED = "#64748B"    # Slate 500
    ACCENT_DROP = "#EFF6FF"   # Light blue tint for drop zone
    BORDER_DROP = "#BFDBFE"
    PILL_BG = "#F1F5F9"       # Slate 100


class LammpsVmdApp(tk.Tk):
    def __init__(self, initial_file: str = "", auto_launch: bool = False):
        super().__init__()
        self.title("LAMMPS Data -> VMD Visualizer")
        self.geometry("1000x800")
        self.minsize(880, 660)
        self.configure(bg=ModernTheme.BG_MAIN)

        # Apply modern styling
        self._setup_styles()

        # Data states
        self.current_info: LammpsDataInfo = None
        self.atom_types_data: dict[int, AtomTypeData] = {}
        self.vmd_exe_path: str = find_vmd_executable() or ""

        # UI Variables
        self.file_path_var = tk.StringVar(value=initial_file)
        self.auto_launch_on_drop_var = tk.BooleanVar(value=True)
        self.style_var = tk.StringVar(value="full")
        self.preset_var = tk.StringVar(value="publication")
        self.rep_style_var = tk.StringVar(value="CPK")
        self.sphere_scale_var = tk.DoubleVar(value=0.35)
        self.bond_radius_var = tk.DoubleVar(value=0.18)
        self.color_by_var = tk.StringVar(value="Type")
        self.material_var = tk.StringVar(value="Opaque")
        self.bg_color_var = tk.StringVar(value="white")
        self.projection_var = tk.StringVar(value="Orthographic")
        self.show_axes_var = tk.BooleanVar(value=False)
        self.show_box_var = tk.BooleanVar(value=True)
        self.box_color_var = tk.StringVar(value="black")
        self.box_width_var = tk.DoubleVar(value=2.0)
        self.auto_bonds_var = tk.BooleanVar(value=False)
        self.bond_cutoff_var = tk.DoubleVar(value=1.6)
        self.status_var = tk.StringVar(value="Ready. Drag & drop a LAMMPS data file here to visualize.")

        # Build UI layout
        self._build_ui()

        # Hook drag and drop
        hook_drop_files(self, self._on_files_dropped)
        hook_drop_files(self.drop_card, self._on_files_dropped)

        if initial_file and os.path.isfile(initial_file):
            self.load_file(initial_file)
            if auto_launch:
                self.after(200, self._on_launch_vmd)

    def _setup_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # Notebook tabs
        style.configure("TNotebook", background=ModernTheme.BG_MAIN, borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background=ModernTheme.CARD_BG,
            foreground=ModernTheme.TEXT_MAIN,
            padding=(16, 8),
            font=("Segoe UI", 9, "bold"),
            borderwidth=1,
            lightcolor=ModernTheme.BORDER,
            darkcolor=ModernTheme.BORDER
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", ModernTheme.PRIMARY), ("active", "#DBEAFE")],
            foreground=[("selected", "#FFFFFF"), ("active", ModernTheme.PRIMARY)]
        )

        # Primary Action Button
        style.configure(
            "Primary.TButton",
            font=("Segoe UI", 10, "bold"),
            background=ModernTheme.PRIMARY,
            foreground="#FFFFFF",
            padding=(18, 8),
            borderwidth=0
        )
        style.map("Primary.TButton", background=[("active", ModernTheme.PRIMARY_HOVER)])

        # Standard clean button
        style.configure("TButton", font=("Segoe UI", 9), padding=(10, 5))
        style.configure("TLabel", background=ModernTheme.CARD_BG, font=("Segoe UI", 9))
        style.configure("TLabelframe", background=ModernTheme.CARD_BG, relief="solid", borderwidth=1)
        style.configure("TLabelframe.Label", background=ModernTheme.CARD_BG, font=("Segoe UI", 9, "bold"), foreground=ModernTheme.TEXT_MAIN)

    def _build_ui(self):
        # 1. Top Card: Drag & Drop Zone + File Selector
        self.drop_card = tk.Frame(
            self,
            bg=ModernTheme.ACCENT_DROP,
            bd=1,
            relief="solid",
            highlightbackground=ModernTheme.BORDER_DROP,
            highlightthickness=1,
            cursor="hand2"
        )
        self.drop_card.pack(fill="x", padx=14, pady=(12, 6))

        # Drop Banner Row
        banner_row = tk.Frame(self.drop_card, bg=ModernTheme.ACCENT_DROP)
        banner_row.pack(fill="x", padx=14, pady=(10, 4))

        lbl_icon_title = tk.Label(
            banner_row,
            text="📥  拖拽 LAMMPS .data 文件至此处（或窗口任意位置）即刻在 VMD 中展示",
            font=("Microsoft YaHei", 10, "bold"),
            bg=ModernTheme.ACCENT_DROP,
            fg=ModernTheme.PRIMARY
        )
        lbl_icon_title.pack(side="left")

        chk_auto = ttk.Checkbutton(
            banner_row,
            text="拖入后立即自动启动 VMD (Auto-Launch)",
            variable=self.auto_launch_on_drop_var
        )
        chk_auto.pack(side="right")

        # File path & browse row
        path_row = tk.Frame(self.drop_card, bg=ModernTheme.ACCENT_DROP)
        path_row.pack(fill="x", padx=14, pady=(4, 10))

        ent_file = ttk.Entry(path_row, textvariable=self.file_path_var, font=("Consolas", 10))
        ent_file.pack(side="left", fill="x", expand=True, padx=(0, 8))

        btn_browse = ttk.Button(path_row, text="浏览... (Browse)", command=self._on_browse_file)
        btn_browse.pack(side="left", padx=3)

        btn_reload = ttk.Button(path_row, text="重新加载", command=self._on_reload_file)
        btn_reload.pack(side="left", padx=3)

        # 2. System Overview Stats Pills
        self.stats_frame = tk.Frame(self, bg=ModernTheme.BG_MAIN)
        self.stats_frame.pack(fill="x", padx=14, pady=(0, 6))

        self.lbl_pills = tk.Label(
            self.stats_frame,
            text="💡 提示：请先选择或拖入 LAMMPS 数据文件（支持 .data / .lmp）",
            font=("Segoe UI", 9),
            bg=ModernTheme.BG_MAIN,
            fg=ModernTheme.TEXT_MUTED
        )
        self.lbl_pills.pack(side="left", pady=2)

        # Style dropdown on the right of stats
        style_sub = tk.Frame(self.stats_frame, bg=ModernTheme.BG_MAIN)
        style_sub.pack(side="right")
        tk.Label(style_sub, text="Atom Style:", bg=ModernTheme.BG_MAIN, font=("Segoe UI", 9, "bold")).pack(side="left", padx=4)
        self.combo_style = ttk.Combobox(
            style_sub,
            textvariable=self.style_var,
            values=["full", "molecular", "atomic", "charge", "dipole", "metal"],
            width=10,
            state="readonly"
        )
        self.combo_style.pack(side="left")
        self.combo_style.bind("<<ComboboxSelected>>", lambda e: self.update_script_preview())

        # 3. Main Notebook Card
        notebook_card = tk.Frame(self, bg=ModernTheme.CARD_BG, bd=1, relief="solid")
        notebook_card.pack(fill="both", expand=True, padx=14, pady=4)

        self.notebook = ttk.Notebook(notebook_card)
        self.notebook.pack(fill="both", expand=True, padx=4, pady=4)

        # Tab 1: Atom Types & Elements
        tab_elements = tk.Frame(self.notebook, bg=ModernTheme.CARD_BG, padx=8, pady=8)
        self.notebook.add(tab_elements, text=" 🧬 原子与元素映射 (Elements) ")
        self._build_elements_tab(tab_elements)

        # Tab 2: Visual Style & Box
        tab_visual = tk.Frame(self.notebook, bg=ModernTheme.CARD_BG, padx=10, pady=8)
        self.notebook.add(tab_visual, text=" 🎨 视觉预设与晶胞 (Display & Box) ")
        self._build_visual_tab(tab_visual)

        # Tab 3: Script Preview
        tab_script = tk.Frame(self.notebook, bg=ModernTheme.CARD_BG, padx=8, pady=8)
        self.notebook.add(tab_script, text=" 📜 VMD 脚本预览 (Tcl Script) ")
        self._build_script_tab(tab_script)

        # 4. Bottom Action Footer Bar
        footer = tk.Frame(self, bg=ModernTheme.BG_MAIN, pady=6)
        footer.pack(fill="x", side="bottom", padx=14)

        # Left: VMD status badge
        vmd_box = tk.Frame(footer, bg=ModernTheme.BG_MAIN)
        vmd_box.pack(side="left")

        self.lbl_vmd_badge = tk.Label(
            vmd_box,
            text=f"● VMD: {os.path.basename(self.vmd_exe_path)}" if self.vmd_exe_path else "○ VMD: 未检测到",
            font=("Segoe UI", 9, "bold"),
            bg="#DCFCE7" if self.vmd_exe_path else "#FEE2E2",
            fg="#166534" if self.vmd_exe_path else "#991B1B",
            padx=8,
            pady=4
        )
        self.lbl_vmd_badge.pack(side="left", padx=(0, 6))

        btn_cfg_vmd = ttk.Button(vmd_box, text="配置 VMD 路径...", command=self._on_set_vmd_path)
        btn_cfg_vmd.pack(side="left")

        # Right: Action Buttons
        btn_box = tk.Frame(footer, bg=ModernTheme.BG_MAIN)
        btn_box.pack(side="right")

        btn_copy = ttk.Button(btn_box, text="📋 复制代码", command=self._on_copy_script)
        btn_copy.pack(side="left", padx=4)

        btn_export = ttk.Button(btn_box, text="💾 导出 .vmd 脚本", command=self._on_save_script)
        btn_export.pack(side="left", padx=4)

        self.btn_launch = ttk.Button(
            btn_box,
            text="🚀 一键在 VMD 中展示",
            style="Primary.TButton",
            command=self._on_launch_vmd
        )
        self.btn_launch.pack(side="left", padx=6)

        # 5. Bottom Status Bar
        self.status_bar = tk.Label(
            self,
            textvariable=self.status_var,
            relief="flat",
            anchor="w",
            font=("Segoe UI", 8),
            bg="#E2E8F0",
            fg=ModernTheme.TEXT_MUTED,
            padx=14,
            pady=3
        )
        self.status_bar.pack(fill="x", side="bottom")

    def _build_elements_tab(self, parent):
        top_hint = tk.Frame(parent, bg=ModernTheme.CARD_BG)
        top_hint.pack(fill="x", pady=(0, 6))

        tk.Label(
            top_hint,
            text="💡 根据原子质量自动匹配化学元素与范德华半径。双击任意行即可修改元素符号或半径：",
            font=("Segoe UI", 9),
            bg=ModernTheme.CARD_BG,
            fg=ModernTheme.TEXT_MUTED
        ).pack(side="left")

        btn_auto_all = ttk.Button(top_hint, text="↺ 恢复自动匹配", command=self._on_reset_elements)
        btn_auto_all.pack(side="right")

        # Table
        cols = ("type_id", "mass", "element", "radius", "color", "comment")
        self.tree_elements = ttk.Treeview(parent, columns=cols, show="headings", height=12)
        self.tree_elements.heading("type_id", text="Type ID")
        self.tree_elements.heading("mass", text="Mass (amu)")
        self.tree_elements.heading("element", text="匹配元素")
        self.tree_elements.heading("radius", text="范德华半径 (Å)")
        self.tree_elements.heading("color", text="VMD 颜色")
        self.tree_elements.heading("comment", text="文件注释说明")

        self.tree_elements.column("type_id", width=80, anchor="center")
        self.tree_elements.column("mass", width=110, anchor="center")
        self.tree_elements.column("element", width=120, anchor="center")
        self.tree_elements.column("radius", width=130, anchor="center")
        self.tree_elements.column("color", width=130, anchor="center")
        self.tree_elements.column("comment", width=260, anchor="w")

        sb = ttk.Scrollbar(parent, orient="vertical", command=self.tree_elements.yview)
        self.tree_elements.configure(yscrollcommand=sb.set)

        self.tree_elements.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree_elements.bind("<Double-1>", self._on_tree_double_click)

    def _build_visual_tab(self, parent):
        # 2-Column Clean Layout
        col_left = ttk.LabelFrame(parent, text=" 🌟 视觉主题预设 (Presets) ", padding=12)
        col_left.pack(side="left", fill="both", expand=True, padx=(0, 6), pady=4)

        presets = [
            ("publication", "📄 期刊发表标准 (Publication Ready)\n    白底 · Opaque饱和材质 · 正交投影 · 黑色边框"),
            ("ball_and_stick", "🌌 深色高对比 (Dark Contrast)\n    黑底 · Glossy光泽材质 · 透视投影 · 青色边框"),
            ("vdw_spacefill", "🔮 真实空间填充 (Space Filling)\n    真实范德华球体填充 · 白底 · 立体无死角"),
            ("licorice", "🧪 分子骨架 (Licorice Stick)\n    纯骨架棍状模型 · 黑底 · 适合复杂大分子")
        ]
        for val, desc in presets:
            f_r = tk.Frame(col_left, bg=ModernTheme.CARD_BG, pady=4)
            f_r.pack(fill="x", anchor="w")
            ttk.Radiobutton(
                f_r,
                text=desc,
                value=val,
                variable=self.preset_var,
                command=self._on_preset_change
            ).pack(anchor="w")

        col_right = ttk.LabelFrame(parent, text=" ⚙️ 详细参数微调 (Tuning) ", padding=12)
        col_right.pack(side="right", fill="both", expand=True, padx=(6, 0), pady=4)

        # Rep & Color
        r_grid = tk.Frame(col_right, bg=ModernTheme.CARD_BG)
        r_grid.pack(fill="both", expand=True)

        tk.Label(r_grid, text="显示形式:").grid(row=0, column=0, sticky="w", pady=4)
        c_rep = ttk.Combobox(r_grid, textvariable=self.rep_style_var, values=["CPK", "VDW", "Licorice", "DynamicBonds", "Lines"], width=12, state="readonly")
        c_rep.grid(row=0, column=1, sticky="w", pady=4, padx=4)
        c_rep.bind("<<ComboboxSelected>>", lambda e: self.update_script_preview())

        tk.Label(r_grid, text="球体缩放:").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Spinbox(r_grid, from_=0.1, to=2.0, increment=0.05, textvariable=self.sphere_scale_var, width=10, command=self.update_script_preview).grid(row=1, column=1, sticky="w", pady=4, padx=4)

        tk.Label(r_grid, text="化学键粗细(Å):").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Spinbox(r_grid, from_=0.05, to=1.0, increment=0.02, textvariable=self.bond_radius_var, width=10, command=self.update_script_preview).grid(row=2, column=1, sticky="w", pady=4, padx=4)

        tk.Label(r_grid, text="渲染材质:").grid(row=3, column=0, sticky="w", pady=4)
        c_mat = ttk.Combobox(r_grid, textvariable=self.material_var, values=["Opaque", "Glossy", "Diffuse", "Goodsell", "Transparent"], width=12, state="readonly")
        c_mat.grid(row=3, column=1, sticky="w", pady=4, padx=4)
        c_mat.bind("<<ComboboxSelected>>", lambda e: self.update_script_preview())

        tk.Label(r_grid, text="背景颜色:").grid(row=0, column=2, sticky="w", pady=4, padx=(14, 0))
        c_bg = ttk.Combobox(r_grid, textvariable=self.bg_color_var, values=["white", "black", "gray"], width=10, state="readonly")
        c_bg.grid(row=0, column=3, sticky="w", pady=4, padx=4)
        c_bg.bind("<<ComboboxSelected>>", lambda e: self.update_script_preview())

        tk.Label(r_grid, text="视角投影:").grid(row=1, column=2, sticky="w", pady=4, padx=(14, 0))
        c_proj = ttk.Combobox(r_grid, textvariable=self.projection_var, values=["Orthographic", "Perspective"], width=10, state="readonly")
        c_proj.grid(row=1, column=3, sticky="w", pady=4, padx=4)
        c_proj.bind("<<ComboboxSelected>>", lambda e: self.update_script_preview())

        ttk.Checkbutton(r_grid, text="绘制模拟晶胞边界框", variable=self.show_box_var, command=self.update_script_preview).grid(row=2, column=2, columnspan=2, sticky="w", pady=4, padx=(14, 0))

        ttk.Checkbutton(r_grid, text="无键体系自动计算动态键", variable=self.auto_bonds_var, command=self.update_script_preview).grid(row=3, column=2, columnspan=2, sticky="w", pady=4, padx=(14, 0))

    def _build_script_tab(self, parent):
        self.txt_script = tk.Text(parent, font=("Consolas", 10), bg="#F8FAFC", relief="flat", wrap="none", padx=8, pady=8)
        sy = ttk.Scrollbar(parent, orient="vertical", command=self.txt_script.yview)
        sx = ttk.Scrollbar(parent, orient="horizontal", command=self.txt_script.xview)
        self.txt_script.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)

        self.txt_script.pack(side="left", fill="both", expand=True)
        sy.pack(side="right", fill="y")
        sx.pack(side="bottom", fill="x")

    def _on_files_dropped(self, files):
        if not files:
            return
        target = files[0]
        if not os.path.isfile(target):
            return
        self.file_path_var.set(target)
        self.load_file(target)
        if self.auto_launch_on_drop_var.get():
            self.status_var.set(f"自动启动 VMD 加载: {os.path.basename(target)}...")
            self.after(150, self._on_launch_vmd)

    def _on_browse_file(self):
        f = filedialog.askopenfilename(
            title="选择 LAMMPS 数据文件",
            filetypes=[("LAMMPS Data", "*.data *.lmp data.* *.dat"), ("All files", "*.*")]
        )
        if f:
            self.file_path_var.set(f)
            self.load_file(f)

    def _on_reload_file(self):
        p = self.file_path_var.get().strip()
        if p and os.path.isfile(p):
            self.load_file(p)

    def load_file(self, filepath: str):
        try:
            self.current_info = LammpsDataParser.parse(filepath)
            self.atom_types_data = dict(self.current_info.atom_types)
            self.style_var.set(self.current_info.atom_style)

            # Update stats badges
            box_info = "无盒子"
            if self.current_info.box:
                b = self.current_info.box
                b_type = "三斜" if b.is_triclinic else "正交"
                box_info = f"{b_type} [{b.lx:.2f}×{b.ly:.2f}×{b.lz:.2f} Å]"

            pills_text = (
                f"📄 {os.path.basename(filepath)}   |   "
                f"⚛️ {self.current_info.num_atoms:,} 原子   |   "
                f"🔗 {self.current_info.num_bonds:,} 键   |   "
                f"🏷️ {self.current_info.num_atom_types} 种原子类型   |   "
                f"📦 {box_info}"
            )
            self.lbl_pills.config(text=pills_text, fg=ModernTheme.TEXT_MAIN, font=("Segoe UI", 9, "bold"))

            self._refresh_treeview()
            self.update_script_preview()
            self.status_var.set(f"成功加载文件 '{os.path.basename(filepath)}'，准备就绪。")
        except Exception as ex:
            messagebox.showerror("解析 LAMMPS 数据失败", f"无法解析文件:\n{ex}")
            self.status_var.set("加载失败。")

    def _refresh_treeview(self):
        for item in self.tree_elements.get_children():
            self.tree_elements.delete(item)

        for tid, tdata in sorted(self.atom_types_data.items()):
            self.tree_elements.insert(
                "",
                "end",
                iid=str(tid),
                values=(
                    f"Type {tdata.type_id}",
                    f"{tdata.mass:.3f}" if tdata.mass > 0 else "0.000",
                    f"{tdata.element} ({tdata.element_info.name})",
                    f"{tdata.radius:.2f}",
                    tdata.color,
                    tdata.comment
                )
            )

    def _on_tree_double_click(self, event):
        item_id = self.tree_elements.focus()
        if not item_id:
            return

        tid = int(item_id)
        current = self.atom_types_data.get(tid)
        if not current:
            return

        # Simple Dialog to edit element & radius
        dlg = tk.Toplevel(self)
        dlg.title(f"修改原子类型 {tid}")
        dlg.geometry("340x240")
        dlg.transient(self)
        dlg.grab_set()

        tk.Label(dlg, text=f"Type ID: {tid}  |  质量: {current.mass:.3f} amu", font=("Segoe UI", 9, "bold")).pack(pady=(12, 6))

        frame = ttk.Frame(dlg, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="化学元素:").grid(row=0, column=0, sticky="w", pady=4)
        elem_var = tk.StringVar(value=current.element)
        c_elem = ttk.Combobox(frame, textvariable=elem_var, values=sorted(list(ELEMENTS_DB.keys())), width=12)
        c_elem.grid(row=0, column=1, sticky="w", pady=4)

        ttk.Label(frame, text="范德华半径 (Å):").grid(row=1, column=0, sticky="w", pady=4)
        rad_var = tk.DoubleVar(value=current.radius)
        ttk.Entry(frame, textvariable=rad_var, width=14).grid(row=1, column=1, sticky="w", pady=4)

        ttk.Label(frame, text="VMD 颜色:").grid(row=2, column=0, sticky="w", pady=4)
        col_var = tk.StringVar(value=current.color)
        c_col = ttk.Combobox(frame, textvariable=col_var, values=["cyan", "red", "white", "blue", "yellow", "green", "silver", "orange", "ochre", "purple"], width=12)
        c_col.grid(row=2, column=1, sticky="w", pady=4)

        def on_elem_changed(e=None):
            sym = elem_var.get().strip().capitalize()
            info = get_element_info(sym)
            if info.symbol != "X":
                rad_var.set(info.vdw_radius)
                col_var.set(info.vmd_color)

        c_elem.bind("<<ComboboxSelected>>", on_elem_changed)

        def on_save():
            sym = elem_var.get().strip().capitalize()
            try:
                rad = float(rad_var.get())
            except ValueError:
                rad = 1.5
            einfo = get_element_info(sym)
            current.element = sym
            current.radius = rad
            current.color = col_var.get().strip() or einfo.vmd_color
            current.element_info = einfo

            self._refresh_treeview()
            self.update_script_preview()
            dlg.destroy()

        b_box = ttk.Frame(dlg, padding=10)
        b_box.pack(fill="x", side="bottom")
        ttk.Button(b_box, text="取消", command=dlg.destroy).pack(side="right", padx=4)
        ttk.Button(b_box, text="保存修改", command=on_save).pack(side="right", padx=4)

    def _on_reset_elements(self):
        if not self.current_info:
            return
        for tid, tdata in self.atom_types_data.items():
            elem, einfo = guess_element_from_mass(tdata.mass, tdata.comment)
            tdata.element = elem
            tdata.element_info = einfo
            tdata.radius = einfo.vdw_radius
            tdata.color = einfo.vmd_color
        self._refresh_treeview()
        self.update_script_preview()

    def _on_preset_change(self):
        p_key = self.preset_var.get()
        s = VmdScriptGenerator.PRESETS.get(p_key)
        if not s:
            return

        self.rep_style_var.set(s.rep_style)
        self.sphere_scale_var.set(s.sphere_scale)
        self.bond_radius_var.set(s.bond_radius)
        self.color_by_var.set(s.color_by)
        self.material_var.set(s.material)
        self.bg_color_var.set(s.bg_color)
        self.projection_var.set(s.projection)
        self.show_axes_var.set(s.show_axes)
        self.show_box_var.set(s.show_box)
        self.box_color_var.set(s.box_color)
        self.box_width_var.set(s.box_width)

        self.update_script_preview()

    def _get_current_settings(self) -> VisualSettings:
        return VisualSettings(
            rep_style=self.rep_style_var.get(),
            sphere_scale=self.sphere_scale_var.get(),
            bond_radius=self.bond_radius_var.get(),
            color_by=self.color_by_var.get(),
            material=self.material_var.get(),
            bg_color=self.bg_color_var.get(),
            projection=self.projection_var.get(),
            show_axes=self.show_axes_var.get(),
            axes_location="lowerleft" if self.show_axes_var.get() else "off",
            show_box=self.show_box_var.get(),
            box_color=self.box_color_var.get(),
            box_width=self.box_width_var.get(),
            auto_bonds=self.auto_bonds_var.get(),
            bond_cutoff=self.bond_cutoff_var.get()
        )

    def generate_script_content(self) -> str:
        if not self.current_info:
            return "# 请先在上方选择或拖入 LAMMPS .data 文件。\n"
        s = self._get_current_settings()
        return VmdScriptGenerator.generate(
            info=self.current_info,
            atom_types=self.atom_types_data,
            settings=s,
            custom_atom_style=self.style_var.get()
        )

    def update_script_preview(self):
        script = self.generate_script_content()
        self.txt_script.delete("1.0", "end")
        self.txt_script.insert("1.0", script)

    def _on_copy_script(self):
        script = self.generate_script_content()
        self.clipboard_clear()
        self.clipboard_append(script)
        self.status_var.set("已复制 VMD Tcl 脚本到剪贴板！")

    def _on_save_script(self):
        if not self.current_info:
            messagebox.showwarning("提示", "请先载入 LAMMPS 数据文件。")
            return
        default_name = os.path.splitext(os.path.basename(self.current_info.filepath))[0] + "_view.vmd"
        out_path = filedialog.asksaveasfilename(
            title="保存 VMD 脚本",
            defaultextension=".vmd",
            initialfile=default_name,
            filetypes=[("VMD Script", "*.vmd *.tcl"), ("All Files", "*.*")]
        )
        if out_path:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(self.generate_script_content())
            self.status_var.set(f"脚本已保存至: {out_path}")
            messagebox.showinfo("已保存", f"VMD 渲染脚本保存成功：\n{out_path}")

    def _on_set_vmd_path(self):
        chosen = filedialog.askopenfilename(
            title="选择 VMD 主执行文件 (vmd.exe)",
            filetypes=[("VMD Executable", "vmd.exe vmd"), ("All Files", "*.*")]
        )
        if chosen and os.path.isfile(chosen):
            self.vmd_exe_path = chosen
            save_config({"vmd_path": chosen})
            self.lbl_vmd_badge.config(
                text=f"● VMD: {os.path.basename(chosen)}",
                bg="#DCFCE7",
                fg="#166534"
            )
            self.status_var.set(f"已设置 VMD 路径: {chosen}")

    def _on_launch_vmd(self):
        if not self.current_info:
            messagebox.showwarning("提示", "请先载入 LAMMPS 数据文件。")
            return

        if not self.vmd_exe_path or not os.path.isfile(self.vmd_exe_path):
            self._on_set_vmd_path()
            if not self.vmd_exe_path:
                return

        script_text = self.generate_script_content()
        temp_dir = tempfile.gettempdir()
        script_file = os.path.join(temp_dir, "lammps_vmd_launch.vmd")
        with open(script_file, "w", encoding="utf-8") as f:
            f.write(script_text)

        try:
            launch_vmd(script_file, self.vmd_exe_path)
            self.status_var.set("已成功启动 VMD 渲染展示！")
        except Exception as ex:
            messagebox.showerror("启动 VMD 失败", f"无法启动 VMD:\n{ex}")


def main():
    initial_file = ""
    auto_launch = False
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg in ("--launch", "-l"):
                auto_launch = True
            elif not arg.startswith("-") and os.path.isfile(arg):
                initial_file = arg

    app = LammpsVmdApp(initial_file=initial_file, auto_launch=auto_launch)
    app.mainloop()


if __name__ == "__main__":
    main()
