"""Local LLM desktop application."""
import os
from pathlib import Path
from queue import Empty, SimpleQueue
import shutil
import sys
from threading import Event, Thread
import time
import tkinter as tk
from tkinter import filedialog, ttk
import webbrowser

from catalog import RECOMMENDED, model_files, recommended_file, search_models
from comfy_runtime import ASSETS, PROFILES, VERSION as COMFY_VERSION, ManagedComfy, check_port
from comfy_runtime import install as install_comfy, install_directory, installed
from downloads import DownloadCancelled, check_gguf, download_model
from engine import LocalEngine
from hardware import FIT_LABELS, Fit, detect_hardware, estimate_ram, model_fit
from load_plan import allocate, plan_load
from media import ComfyClient, MODELS

VERSION = "0.5.0"
APP_DIR = Path(__file__).resolve().parent
FROZEN = getattr(sys, "frozen", False)
DATA_DIR = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "LocalLLM" if FROZEN else APP_DIR
MODEL_DIR = DATA_DIR / "models"
OUTPUT_DIR = DATA_DIR / "outputs"
COMFY_DIR = DATA_DIR / "comfyui"
ENGINE_PATH = APP_DIR / "engine-vulkan" / "llama-server.exe"
SAMPLE_URL = (
    "https://huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF/"
    "resolve/09816ac/SmolLM2-135M-Instruct-Q4_K_M.gguf"
)
QWEN_URL = (
    "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/"
    "resolve/9217f5d/qwen2.5-0.5b-instruct-q4_k_m.gguf"
)

BG = "#f1f2f4"
PANEL = "#ffffff"
FIELD = "#ffffff"
TEXT = "#181a1e"
MUTED = "#535963"
ACCENT = "#b51e30"
BORDER = "#cdd0d6"
HOVER = "#e8eaee"
SELECTED = "#e8eaf0"
FONT = "Microsoft JhengHei UI"
MEDIA_GUIDES = {
    "image": "https://docs.comfy.org/tutorials/basic/text-to-image",
    "video": "https://comfyanonymous.github.io/ComfyUI_examples/wan/",
    "music": "https://docs.comfy.org/tutorials/audio/ace-step/ace-step-v1",
}


def format_size(value):
    return f"{value / (1024 ** 3):.2f} GiB" if value >= 1024 ** 3 else f"{value / (1024 ** 2):.1f} MiB"


class LocalLLM:
    def __init__(self, root):
        self.root = root
        self.engine = LocalEngine()
        self.events = SimpleQueue()
        self.models = {}
        self.imports = set()
        self.history = []
        self.loading = self.ready = self.stopping = self.answering = self.closing = False
        self.download_cancel = None
        self.shutdown = Event()
        self.preview_generation = 0
        self.media_busy = False
        self.media_result = None
        self.comfy = ManagedComfy()
        self.comfy_busy = False
        self.comfy_cancel = None
        self.comfy_profile = tk.StringVar(value=next((profile for profile in PROFILES
            if installed(install_directory(COMFY_DIR, profile))), "CPU"))
        self.comfy_status = tk.StringVar()
        self.comfy_progress = tk.DoubleVar()
        self.media_kind = tk.StringVar(value=MODELS["image"][0])
        self.media_port = tk.StringVar(value="8188")
        self.media_hint = tk.StringVar()
        self.media_status = tk.StringVar(value="先啟動本機 ComfyUI，再選擇要生成的媒體。")
        self.catalog_busy = False
        self.catalog_files = []
        self.showing_recommended = True
        self.catalog_query = tk.StringVar()
        self.catalog_status = tk.StringVar()
        self.hardware_status = tk.StringVar()

        self.selected = tk.StringVar()
        legacy_engine = APP_DIR / "engine" / "llama-server.exe"
        system_engine = shutil.which("llama-server")
        engines = (ENGINE_PATH, legacy_engine, Path(system_engine) if system_engine else ENGINE_PATH)
        self.executable = next((path for path in engines if path.is_file()), ENGINE_PATH)
        self.engine_status = tk.StringVar(value="請選擇模型並啟動")
        self.engine_label = tk.StringVar(value="自動配置 · llama.cpp")
        self.model_info = tk.StringVar(value="尚未選擇模型")
        self.placement = tk.StringVar(value="選擇模型後顯示啟動預估")
        self.chat_status = tk.StringVar(value="從模型清單下載，或選擇本機 GGUF 開始。")
        self.url = tk.StringVar(value=SAMPLE_URL)
        self.workers = tk.StringVar(value="4")
        self.download_status = tk.StringVar(value="等待下載")
        self.progress = tk.DoubleVar()

        self.root.title(f"Local LLM v{VERSION} · 本機模型工作台")
        self.root.geometry("1120x740")
        self.root.minsize(850, 660)
        self.root.configure(bg=BG)
        self.icon = tk.PhotoImage(file=str(APP_DIR / "logo.png"))
        self.brand_mark = self.icon.subsample(10)
        self.root.iconphoto(True, self.icon)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.style()
        self.build()
        self.refresh_models()
        self.refresh_buttons()
        self.root.after(30, self.dispatch)

    def style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", font=(FONT, 10), background=BG, foreground=TEXT, bordercolor=BORDER)
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("Card.TLabel", background=PANEL, foreground=TEXT)
        style.configure("Muted.TLabel", background=BG, foreground=MUTED)
        style.configure("CardMuted.TLabel", background=PANEL, foreground=MUTED)
        style.configure("Title.TLabel", font=(FONT, 22, "bold"))
        style.configure("Section.TLabel", font=(FONT, 14, "bold"))
        style.configure("TButton", padding=(11, 6), background=PANEL, foreground=TEXT, focuscolor=BORDER)
        style.map("TButton", background=[("active", HOVER)], foreground=[("disabled", "#6d737d")])
        style.configure("Primary.TButton", background=ACCENT, foreground=PANEL, bordercolor=ACCENT)
        style.map("Primary.TButton", background=[("disabled", HOVER), ("active", "#901725")],
                  foreground=[("disabled", "#6d737d"), ("active", PANEL)])
        for name in ("TEntry", "TCombobox", "TSpinbox"):
            style.configure(name, fieldbackground=FIELD, foreground=TEXT, insertcolor=TEXT,
                            background=PANEL, arrowcolor=TEXT, padding=6)
            style.map(name, fieldbackground=[("readonly", FIELD)], foreground=[("readonly", TEXT)],
                      selectbackground=[("readonly", FIELD)], selectforeground=[("readonly", TEXT)])
        style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(0, 0, 0, 0))
        style.configure("TNotebook.Tab", padding=(16, 9), background=PANEL, foreground=MUTED)
        style.map("TNotebook.Tab", background=[("selected", FIELD)], foreground=[("selected", ACCENT)])
        style.configure("Treeview", background=FIELD, fieldbackground=FIELD, foreground=TEXT, rowheight=26)
        style.map("Treeview", background=[("selected", SELECTED)], foreground=[("selected", TEXT)])
        style.configure("Horizontal.TProgressbar", background=ACCENT, troughcolor=FIELD, bordercolor=BORDER)
        self.root.option_add("*TCombobox*Listbox.background", FIELD)
        self.root.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", SELECTED)
        self.root.option_add("*TCombobox*Listbox.selectForeground", TEXT)

    def build(self):
        shell = ttk.Frame(self.root, padding=(24, 18))
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(1, weight=1)
        header = ttk.Frame(shell)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 18))
        ttk.Label(header, image=self.brand_mark).pack(side="left", padx=(0, 12))
        name = ttk.Frame(header)
        name.pack(side="left")
        ttk.Label(name, text="Local LLM", style="Title.TLabel").pack(anchor="w")
        ttk.Label(name, text="本機對話與媒體生成", style="Muted.TLabel").pack(anchor="w")
        ttk.Label(header, text=f"v{VERSION}", style="Muted.TLabel").pack(side="right")

        side = ttk.Frame(shell, style="Card.TFrame", padding=(15, 16))
        side.grid(row=1, column=0, sticky="ns", padx=(0, 16))
        ttk.Label(side, text="本機模型", style="Card.TLabel", font=(FONT, 13, "bold")).pack(anchor="w", pady=(0, 8))
        self.picker = ttk.Combobox(side, textvariable=self.selected, width=27, state="readonly")
        self.picker.pack(fill="x")
        self.picker.bind("<<ComboboxSelected>>", lambda _: self.show_model_info())
        ttk.Label(side, textvariable=self.model_info, style="CardMuted.TLabel", wraplength=210).pack(anchor="w", pady=(6, 12))
        self.import_button = ttk.Button(side, text="選擇本機 GGUF…", command=self.import_model)
        self.import_button.pack(fill="x")
        ttk.Separator(side).pack(fill="x", pady=16)
        ttk.Label(side, text="推理引擎", style="Card.TLabel", font=(FONT, 13, "bold")).pack(anchor="w")
        ttk.Label(side, textvariable=self.engine_label, style="CardMuted.TLabel", wraplength=210).pack(anchor="w", pady=(5, 8))
        self.engine_button = ttk.Button(side, text="更換推理引擎…", command=self.choose_engine)
        self.engine_button.pack(fill="x")
        self.load_button = ttk.Button(side, text="啟動模型", style="Primary.TButton", command=self.load_model)
        self.load_button.pack(fill="x", pady=(10, 5))
        self.stop_button = ttk.Button(side, text="停止模型", command=self.stop_model)
        self.stop_button.pack(fill="x")
        ttk.Label(side, textvariable=self.engine_status, style="CardMuted.TLabel", wraplength=210,
                  justify="left").pack(anchor="w", pady=(12, 0))
        ttk.Separator(side).pack(fill="x", pady=12)
        ttk.Label(side, text="啟動資源預估", style="Card.TLabel", font=(FONT, 11, "bold")).pack(anchor="w")
        ttk.Label(side, textvariable=self.placement, style="CardMuted.TLabel", wraplength=220,
                  justify="left").pack(anchor="w", pady=(5, 0))

        self.tabs = ttk.Notebook(shell)
        self.tabs.grid(row=1, column=1, sticky="nsew")
        chat = ttk.Frame(self.tabs, padding=(14, 12))
        catalog = ttk.Frame(self.tabs, padding=(16, 14))
        self.download_tab = ttk.Frame(self.tabs, padding=(20, 18))
        media = ttk.Frame(self.tabs, padding=(20, 18))
        self.tabs.add(chat, text="對話")
        self.tabs.add(catalog, text="模型清單")
        self.tabs.add(self.download_tab, text="模型下載")
        self.tabs.add(media, text="創作")
        self.build_chat(chat)
        self.build_catalog(catalog)
        self.build_download(self.download_tab)
        self.build_media(media)

    def build_chat(self, pane):
        header = ttk.Frame(pane)
        header.pack(fill="x", pady=(0, 8))
        ttk.Label(header, textvariable=self.chat_status, style="Muted.TLabel").pack(side="left", fill="x", expand=True)
        self.clear_button = ttk.Button(header, text="新對話", command=self.clear_chat)
        self.clear_button.pack(side="right")
        transcript = ttk.Frame(pane)
        transcript.pack(fill="both", expand=True)
        scrollbar = ttk.Scrollbar(transcript)
        scrollbar.pack(side="right", fill="y")
        self.output = self.textbox(transcript, state="disabled", yscrollcommand=scrollbar.set)
        self.output.tag_configure("speaker", foreground=ACCENT, font=(FONT, 11, "bold"))
        self.output.tag_configure("notice", foreground=ACCENT)
        self.output.pack(side="left", fill="both", expand=True)
        scrollbar.configure(command=self.output.yview)

        compose = ttk.Frame(pane)
        compose.pack(fill="x", pady=(12, 0))
        self.prompt = self.textbox(compose, height=3)
        self.prompt.pack(side="left", fill="x", expand=True)
        self.prompt.bind("<Return>", self.enter_to_send)
        self.send_button = ttk.Button(compose, text="傳送", style="Primary.TButton", command=self.send)
        self.send_button.pack(side="right", padx=(10, 0), fill="y")
        ttk.Label(pane, text="Enter 傳送  ·  Shift + Enter 換行", style="Muted.TLabel").pack(anchor="w", pady=(5, 0))

    def build_catalog(self, pane):
        ttk.Label(pane, text="推薦模型與 Hugging Face 搜尋", style="Section.TLabel").pack(anchor="w")
        hardware = ttk.Frame(pane)
        hardware.pack(fill="x", pady=(6, 0))
        ttk.Label(hardware, textvariable=self.hardware_status, style="Muted.TLabel", wraplength=360).pack(
            side="left", fill="x", expand=True)
        self.hardware_refresh = ttk.Button(hardware, text="重新偵測並推薦", command=self.show_recommended)
        self.hardware_refresh.pack(side="right", padx=(6, 0))
        search = ttk.Frame(pane)
        search.pack(fill="x", pady=(10, 8))
        self.catalog_entry = ttk.Entry(search, textvariable=self.catalog_query)
        self.catalog_entry.pack(side="left", fill="x", expand=True)
        self.catalog_entry.bind("<Return>", lambda _: self.find_models())
        self.catalog_search = ttk.Button(search, text="線上搜尋", command=self.find_models)
        self.catalog_search.pack(side="left", padx=(6, 0))

        listing = ttk.Frame(pane)
        listing.pack(fill="both", expand=True)
        self.catalog_list = ttk.Treeview(listing, columns=("repo", "info"), show="headings",
                                         selectmode="browse", height=5)
        self.catalog_list.heading("repo", text="Hugging Face 倉庫")
        self.catalog_list.heading("info", text="適配 / 下載次數")
        self.catalog_list.column("repo", width=290, minwidth=120)
        self.catalog_list.column("info", width=130, minwidth=85, stretch=False)
        scrollbar = ttk.Scrollbar(listing, command=self.catalog_list.yview)
        self.catalog_list.configure(yscrollcommand=scrollbar.set)
        self.catalog_list.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.catalog_list.bind("<<TreeviewSelect>>", self.catalog_selection_changed)

        self.catalog_versions = ttk.Button(pane, text="查看 GGUF 版本", command=self.read_versions)
        self.catalog_versions.pack(anchor="w", pady=(8, 5))
        choose = ttk.Frame(pane)
        choose.pack(fill="x")
        self.catalog_picker = ttk.Combobox(choose, state="disabled", width=20)
        self.catalog_picker.pack(side="left", fill="x", expand=True)
        self.catalog_picker.bind("<<ComboboxSelected>>", self.show_file_fit)
        self.catalog_download = ttk.Button(choose, text="前往下載", style="Primary.TButton",
                                           command=self.use_catalog_file)
        self.catalog_download.pack(side="right", padx=(8, 0))
        ttk.Label(pane, textvariable=self.catalog_status, style="Muted.TLabel", wraplength=440).pack(
            anchor="w", pady=(6, 0))
        self.show_recommended()

    def set_catalog_rows(self, rows):
        self.catalog_list.delete(*self.catalog_list.get_children())
        for repo, info in rows:
            self.catalog_list.insert("", "end", values=(repo, info))
        self.catalog_selection_changed()

    def show_recommended(self):
        self.detect_resources()
        self.showing_recommended = True
        ranked = []
        for repo in RECOMMENDED:
            filename, size, _ = recommended_file(repo)
            ranked.append((self.file_fit(filename, size), size, repo))
        prefer_larger = (self.hardware.cpu_threads or 0) >= 8
        ranked.sort(key=lambda item: (item[0], -item[1] if prefer_larger and item[0] == Fit.GOOD else item[1]))
        self.set_catalog_rows((repo, FIT_LABELS[fit]) for fit, _, repo in ranked)
        self.catalog_status.set("可選擇模型查看估算，或留空搜尋熱門 GGUF。")
        if ranked[0][0] == Fit.GOOD:
            first = self.catalog_list.get_children()[0]
            self.catalog_list.selection_set(first)
            self.catalog_selection_changed()

    def detect_resources(self):
        self.hardware = detect_hardware(MODEL_DIR)
        threads = self.hardware.cpu_threads or "未知"
        available = format_size(self.hardware.ram_available) if self.hardware.ram_available is not None else "未知"
        total = format_size(self.hardware.ram_total) if self.hardware.ram_total is not None else "未知"
        disk = format_size(self.hardware.disk_available) if self.hardware.disk_available is not None else "未知"
        self.hardware_status.set(f"CPU {threads} 執行緒 · 可用 RAM {available} / {total}\n模型磁碟剩餘 {disk}")

    def file_fit(self, filename, size):
        local = MODEL_DIR / Path(filename).name
        try:
            installed = local.is_file() and local.stat().st_size == size
        except OSError:
            installed = False
        return model_fit(self.hardware, size, installed=installed)

    def set_catalog_files(self, files):
        self.catalog_files = files
        self.catalog_picker.configure(values=[
            f"{name} · {format_size(size)} · {FIT_LABELS[self.file_fit(name, size)]}" if size else f"{name} · 大小未知"
            for name, size, _ in files
        ])
        if files:
            self.catalog_picker.current(0)
        else:
            self.catalog_picker.set("")

    def catalog_selection_changed(self, event=None):
        selected = self.catalog_list.selection()
        if selected and self.showing_recommended:
            repo = self.catalog_list.item(selected[0], "values")[0]
            self.set_catalog_files([recommended_file(repo)])
            self.show_file_fit()
        else:
            self.set_catalog_files([])
            if selected and not self.catalog_busy:
                self.catalog_status.set("按「查看 GGUF 版本」讀取檔案與適配估算。")
        self.refresh_catalog_buttons()

    def show_file_fit(self, event=None):
        index = self.catalog_picker.current()
        if index < 0:
            return
        name, size, _ = self.catalog_files[index]
        fit = FIT_LABELS[self.file_fit(name, size)]
        if not size:
            self.catalog_status.set("Hugging Face 未提供大小，無法估算所需記憶體。")
            return
        selected = self.catalog_list.selection()
        purpose = ""
        if self.showing_recommended and selected:
            repo = self.catalog_list.item(selected[0], "values")[0]
            purpose = RECOMMENDED[repo][0] + " · "
        self.catalog_status.set(f"{purpose}{fit} · 估計需 {format_size(estimate_ram(size))} 可用 RAM")

    def refresh_catalog_buttons(self):
        available = not self.catalog_busy and not self.closing
        has_files = available and bool(self.catalog_files)
        self.catalog_picker.configure(state="readonly" if has_files else "disabled")
        for widget, enabled in (
            (self.catalog_entry, available),
            (self.catalog_search, available),
            (self.hardware_refresh, available),
            (self.catalog_versions, available and bool(self.catalog_list.selection())),
            (self.catalog_download, has_files and self.download_cancel is None),
        ):
            widget.configure(state="normal" if enabled else "disabled")

    def catalog_request(self, task, status, apply_result):
        if self.catalog_busy or self.closing:
            return
        self.catalog_busy = True
        self.catalog_status.set(status)
        self.refresh_catalog_buttons()

        def done(result, error):
            self.catalog_busy = False
            if error:
                self.catalog_status.set(str(error))
            else:
                apply_result(result)
            self.refresh_catalog_buttons()

        self.background(task, done)

    def find_models(self):
        if self.catalog_busy or self.closing:
            return
        query = self.catalog_query.get().strip()
        self.showing_recommended = False
        self.set_catalog_rows(())

        def show(results):
            self.set_catalog_rows((repo, f"{count:,}" if type(count) is int else "—") for repo, count in results)
            self.catalog_status.set(f"找到 {len(results)} 筆。選擇模型後查看版本。" if results else "找不到符合的模型。")

        self.catalog_request(lambda: search_models(query), "正在搜尋 Hugging Face…", show)

    def read_versions(self):
        selected = self.catalog_list.selection()
        if not selected:
            return
        repo = self.catalog_list.item(selected[0], "values")[0]
        self.detect_resources()

        def show(files):
            if self.catalog_list.selection() != selected:
                self.catalog_status.set("請按「查看 GGUF 版本」載入目前選擇的模型。")
                return
            preferred = RECOMMENDED[repo][1] if repo in RECOMMENDED else None
            files.sort(key=lambda item: (self.file_fit(item[0], item[1]), item[0] != preferred, item[1] or 0))
            self.set_catalog_files(files)
            if files:
                self.show_file_fit()
            else:
                self.catalog_status.set("此倉庫沒有支援的單檔 GGUF。")

        self.catalog_request(lambda: model_files(repo), f"正在讀取 {repo}…", show)

    def use_catalog_file(self):
        index = self.catalog_picker.current()
        if index >= 0 and self.download_cancel is None:
            self.url.set(self.catalog_files[index][2])
            self.tabs.select(self.download_tab)

    def build_download(self, pane):
        ttk.Label(pane, text="下載 GGUF 模型", style="Section.TLabel").pack(anchor="w")
        ttk.Label(pane, text="從模型清單選擇版本，或貼上公開 HTTPS 的 GGUF 直連網址。",
                  style="Muted.TLabel", wraplength=520).pack(anchor="w", pady=(6, 18))
        ttk.Label(pane, text="模型檔案網址").pack(anchor="w", pady=(0, 5))
        self.url_entry = ttk.Entry(pane, textvariable=self.url)
        self.url_entry.pack(fill="x")
        presets = ttk.Frame(pane)
        presets.pack(fill="x", pady=(7, 16))
        self.sample_button = ttk.Button(presets, text="SmolLM2 英文測試（105 MB）",
                                        command=lambda: self.url.set(SAMPLE_URL))
        self.sample_button.pack(side="left", padx=(0, 8))
        self.qwen_button = ttk.Button(presets, text="Qwen2.5 中文聊天（491 MB）",
                                      command=lambda: self.url.set(QWEN_URL))
        self.qwen_button.pack(side="left")
        options = ttk.Frame(pane)
        options.pack(fill="x")
        ttk.Label(options, text="下載執行緒").pack(side="left")
        self.worker_box = ttk.Spinbox(options, from_=1, to=16, textvariable=self.workers, width=5)
        self.worker_box.pack(side="left", padx=8)
        self.download_button = ttk.Button(options, text="開始下載", style="Primary.TButton", command=self.download)
        self.download_button.pack(side="right")
        self.cancel_button = ttk.Button(options, text="取消", command=self.cancel_download)
        self.cancel_button.pack(side="right", padx=(0, 8))
        self.progress_bar = ttk.Progressbar(pane, maximum=100, variable=self.progress)
        self.progress_bar.pack(fill="x", pady=(22, 9))
        ttk.Label(pane, textvariable=self.download_status, wraplength=500).pack(anchor="w")
        ttk.Label(pane, text="支援 Range 的來源會平行下載各區段。不支援 Range 時會標示為單一連線。",
                  style="Muted.TLabel", wraplength=500).pack(anchor="w", pady=(16, 0))

    def build_media(self, pane):
        ttk.Label(pane, text="本機創作", style="Section.TLabel").pack(anchor="w")
        launcher = ttk.Frame(pane, style="Card.TFrame", padding=(10, 6))
        launcher.pack(fill="x", pady=(8, 0))
        controls = ttk.Frame(launcher, style="Card.TFrame")
        controls.pack(fill="x")
        ttk.Label(controls, text="ComfyUI", style="Card.TLabel").pack(side="left", padx=(0, 8))
        self.comfy_profiles = ttk.Combobox(controls, textvariable=self.comfy_profile,
                                          values=tuple(PROFILES), state="readonly", width=16)
        self.comfy_profiles.pack(side="left")
        self.comfy_profiles.bind("<<ComboboxSelected>>", self.show_comfy_profile)
        self.comfy_action = ttk.Button(controls, command=self.toggle_comfy)
        self.comfy_action.pack(side="left", padx=6)
        self.comfy_cancel_button = ttk.Button(controls, text="取消", command=self.cancel_comfy)
        self.comfy_cancel_button.pack(side="left")
        shortcuts = ttk.Frame(launcher, style="Card.TFrame")
        shortcuts.pack(fill="x", pady=(4, 0))
        self.comfy_models = ttk.Button(shortcuts, text="模型資料夾", command=self.open_comfy_models)
        self.comfy_models.pack(side="left")
        self.comfy_web = ttk.Button(shortcuts, text="開啟網頁", command=self.open_comfy_web)
        self.comfy_web.pack(side="left", padx=6)
        ttk.Progressbar(shortcuts, maximum=100, variable=self.comfy_progress, length=100).pack(
            side="left", fill="x", expand=True, padx=(8, 0))
        ttk.Label(launcher, textvariable=self.comfy_status, style="CardMuted.TLabel", wraplength=470).pack(
            anchor="w", pady=(5, 0))
        options = ttk.Frame(pane)
        options.pack(fill="x", pady=(10, 6))
        self.media_picker = ttk.Combobox(options, textvariable=self.media_kind,
                                        values=[entry[0] for entry in MODELS.values()], state="readonly", width=10)
        self.media_picker.pack(side="left")
        self.media_picker.bind("<<ComboboxSelected>>", self.show_media_kind)
        ttk.Button(options, text="模型安裝說明",
                   command=lambda: webbrowser.open(MEDIA_GUIDES[self.selected_media()])).pack(side="right")
        ttk.Label(options, text="ComfyUI 連接埠").pack(side="left", padx=(12, 5))
        self.media_port_entry = ttk.Entry(options, textvariable=self.media_port, width=7)
        self.media_port_entry.pack(side="left")
        ttk.Label(pane, textvariable=self.media_hint, style="Muted.TLabel", wraplength=480).pack(anchor="w", pady=(3, 8))
        ttk.Label(pane, text="描述你想生成的作品").pack(anchor="w")
        self.media_prompt = self.textbox(pane, height=4)
        self.lyrics_row = ttk.Frame(pane)
        ttk.Label(self.lyrics_row, text="歌詞（選填）").pack(anchor="w")
        self.lyrics = self.textbox(self.lyrics_row, height=2)
        self.lyrics.pack(fill="x", pady=(4, 7))
        ttk.Label(pane, textvariable=self.media_status, style="Muted.TLabel", wraplength=460).pack(
            side="bottom", fill="x", pady=(8, 0))
        self.media_actions = ttk.Frame(pane)
        self.media_actions.pack(side="bottom", fill="x")
        self.media_generate = ttk.Button(self.media_actions, text="開始生成", style="Primary.TButton",
                                         command=self.generate_media)
        self.media_generate.pack(side="left")
        self.media_open = ttk.Button(self.media_actions, text="開啟作品", command=self.open_media)
        self.media_open.pack(side="left", padx=8)
        self.media_prompt.pack(fill="both", expand=True, pady=(5, 8))
        self.show_media_kind()
        self.show_comfy_profile()

    def comfy_directory(self):
        return install_directory(COMFY_DIR, self.comfy_profile.get())

    def show_comfy_profile(self, event=None):
        ready = installed(self.comfy_directory())
        asset = ASSETS[PROFILES[self.comfy_profile.get()][0]]
        details = "已安裝，可以直接啟動" if ready else f"首次下載 {format_size(asset.size)}，模型另裝"
        self.comfy_status.set(f"官方便攜版 {COMFY_VERSION} · {details}")
        self.comfy_progress.set(0)
        if event is not None:
            self.refresh_buttons()

    def toggle_comfy(self):
        if self.comfy_busy or self.media_busy or self.closing:
            return
        if self.comfy.running():
            self.stop_comfy()
            return
        if self.ready or self.loading or self.stopping:
            return
        try:
            port = int(self.media_port.get())
            ComfyClient(port)
        except ValueError:
            self.comfy_status.set("請輸入有效的 ComfyUI 連接埠，例如 8188。")
            return
        profile = self.comfy_profile.get()
        cancel = self.comfy_cancel = Event()
        self.comfy_busy = True
        self.comfy_progress.set(0)
        self.refresh_buttons()

        def status(message):
            self.events.put((self.comfy_status.set, (message,)))

        def progress(received, total):
            self.events.put((self.comfy_progress.set, (received * 100 / total,)))
            status(f"正在下載官方 ComfyUI… {format_size(received)} / {format_size(total)}")

        def run():
            check_port(port)
            path = install_comfy(COMFY_DIR, profile, cancel, status, progress)
            status("正在啟動 ComfyUI，首次啟動可能需要一些時間…")
            self.comfy.start(path, profile, port, cancel)

        def done(_, error):
            self.comfy_busy = False
            self.comfy_cancel = None
            if error:
                self.comfy_progress.set(0)
                self.comfy_status.set("已取消 ComfyUI 作業。" if cancel.is_set() else str(error).strip().split("\n")[0])
            elif self.closing or cancel.is_set():
                self.stop_comfy()
            else:
                self.comfy_progress.set(100)
                self.comfy_status.set(f"ComfyUI 已就緒 · 127.0.0.1:{port}")
                self.media_status.set("選擇創作類型與模型，輸入描述後即可生成。")
            self.refresh_buttons()

        self.background(run, done)

    def cancel_comfy(self):
        if self.comfy_cancel is not None:
            self.comfy_cancel.set()
            self.comfy_status.set("正在取消 ComfyUI 作業…")
            self.refresh_buttons()

    def stop_comfy(self):
        self.comfy_busy = True
        self.comfy_status.set("正在停止 ComfyUI…")
        self.refresh_buttons()

        def done(_, error):
            self.comfy_busy = False
            self.comfy_progress.set(0)
            self.comfy_status.set(str(error) if error else "ComfyUI 已停止，可以重新啟動。")
            self.refresh_buttons()

        self.background(self.comfy.stop, done)

    def open_comfy_models(self):
        path = self.comfy_directory() / "ComfyUI" / "models"
        try:
            path.mkdir(exist_ok=True)
            os.startfile(path)
        except OSError as error:
            self.comfy_status.set(str(error))

    def open_comfy_web(self):
        if self.comfy.running():
            webbrowser.open(f"http://127.0.0.1:{self.comfy.port}/")

    def selected_media(self):
        return next(key for key, value in MODELS.items() if value[0] == self.media_kind.get())

    def show_media_kind(self, event=None):
        kind = self.selected_media()
        model = MODELS[kind][1]
        size = {"image": "512 × 512 · PNG", "video": "約 2 秒 · WEBM", "music": "20 秒 · FLAC"}[kind]
        self.media_hint.set(f"{model} · {size} · 由本機 ComfyUI 生成")
        if kind == "music":
            self.lyrics_row.pack(side="bottom", fill="x", before=self.media_prompt)
        else:
            self.lyrics_row.pack_forget()

    def generate_media(self):
        if self.media_busy or self.comfy_busy or self.ready or self.loading or self.stopping or self.closing:
            return
        prompt = self.media_prompt.get("1.0", "end-1c").strip()
        if not prompt:
            self.media_status.set("請先輸入作品描述。")
            return
        try:
            client = ComfyClient(self.comfy.port if self.comfy.running() else int(self.media_port.get()))
        except ValueError:
            self.media_status.set("請輸入有效的 ComfyUI 連接埠，例如 8188。")
            return
        kind = self.selected_media()
        lyrics = self.lyrics.get("1.0", "end-1c").strip() if kind == "music" else ""
        self.media_busy = True
        self.media_result = None
        self.media_status.set("正在檢查 ComfyUI 和模型…")
        self.refresh_buttons()

        def report(message):
            self.events.put((self.media_status.set, (message,)))

        def done(path, error):
            self.media_busy = False
            self.media_result = path
            self.media_status.set(str(error) if error else f"已儲存作品 {path.name}")
            self.refresh_buttons()

        self.background(lambda: client.generate(kind, prompt, lyrics, OUTPUT_DIR, self.shutdown, report), done)

    def open_media(self):
        if self.media_result:
            try:
                os.startfile(self.media_result)
            except OSError as error:
                self.media_status.set(str(error))

    def textbox(self, parent, **options):
        return tk.Text(parent, bg=FIELD, fg=TEXT, insertbackground=TEXT, selectbackground=SELECTED,
                       relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT,
                       font=(FONT, 11), wrap="word", padx=12, pady=9, **options)

    def refresh_models(self, select=None):
        previous = select or self.models.get(self.selected.get())
        paths = set(MODEL_DIR.glob("*.gguf")) | self.imports
        self.models = {}
        for path in sorted(paths, key=lambda value: (value.name.lower(), str(value).lower())):
            if path.is_file():
                name = path.name if path.name not in self.models else str(path)
                self.models[name] = path
        self.picker.configure(values=list(self.models))
        label = next((name for name, path in self.models.items() if path == previous), "")
        self.selected.set(label or next(iter(self.models), ""))
        self.show_model_info()

    def show_model_info(self):
        model = self.models.get(self.selected.get())
        try:
            self.model_info.set(format_size(model.stat().st_size) if model else "下載或選擇本機 GGUF")
        except OSError:
            self.model_info.set("找不到此模型檔案")
        self.refresh_buttons()
        if self.ready or self.loading:
            return
        self.preview_generation += 1
        generation = self.preview_generation
        if not model or not self.executable.is_file():
            self.placement.set("選擇模型與推理引擎後顯示啟動預估")
            return
        executable = self.executable
        self.placement.set("正在估算顯存、RAM 與磁碟…")

        def done(plan, error):
            if generation == self.preview_generation and not self.closing and not self.loading and not self.ready:
                self.placement.set("無法讀取模型大小" if error else self.describe_plan(plan))

        self.background(lambda: plan_load(executable, model), done)

    def describe_plan(self, plan):
        gpu = f"{format_size(plan.vram)} · {plan.layers}/{plan.total_layers} 層" if plan.layers else "0 · CPU"
        memory = "（含 GPU 共用）" if plan.shared else ""
        disk = "磁碟映射" if plan.mmap_args else "模型檔案"
        return f"GPU {gpu}\nRAM {format_size(plan.ram)}{memory}\n{disk} {format_size(plan.mapped_bytes)}"

    def import_model(self):
        selected = filedialog.askopenfilename(parent=self.root, title="選擇本機 GGUF", filetypes=[("GGUF", "*.gguf")])
        if not selected:
            return
        path = Path(selected)
        try:
            check_gguf(path)
        except (OSError, ValueError) as error:
            self.engine_status.set(str(error))
            return
        self.imports.add(path)
        self.refresh_models(path)

    def choose_engine(self):
        selected = filedialog.askopenfilename(parent=self.root, title="選擇 llama-server",
                                              filetypes=[("llama-server", "llama-server.exe")])
        if selected:
            self.executable = Path(selected)
            self.engine_label.set(self.executable.name)
            self.engine_status.set("已選擇引擎")
            self.show_model_info()

    def background(self, task, done):
        def run():
            try:
                result = task()
            except Exception as error:
                self.events.put((done, (None, error)))
            else:
                self.events.put((done, (result, None)))

        Thread(target=run, daemon=True).start()

    def dispatch(self):
        for _ in range(150):
            try:
                callback, args = self.events.get_nowait()
            except Empty:
                break
            callback(*args)
        if not self.comfy_busy and self.comfy.port is not None and not self.comfy.running():
            self.comfy.stop()
            self.comfy_progress.set(0)
            self.comfy_status.set("ComfyUI 已結束。啟動日誌位於便攜版資料夾。")
            self.refresh_buttons()
        if self.closing and not any((self.loading, self.stopping, self.answering, self.download_cancel,
                                     self.media_busy, self.comfy_busy)):
            self.root.destroy()
            return
        self.root.after(30, self.dispatch)

    def refresh_buttons(self):
        locked = self.ready or self.loading or self.stopping or self.answering or self.closing
        downloading = self.download_cancel is not None
        comfy_running = self.comfy.running()
        comfy_idle = not self.comfy_busy and not self.closing
        comfy_installed = installed(self.comfy_directory())
        self.comfy_action.configure(text=("停止 ComfyUI" if comfy_running else
                                          "啟動 ComfyUI" if comfy_installed else "下載並啟動"))
        self.comfy_profiles.configure(state="readonly" if comfy_idle and not comfy_running else "disabled")
        self.picker.configure(state="disabled" if locked else "readonly")
        for widget, enabled in (
            (self.import_button, not locked),
            (self.engine_button, not locked),
            (self.load_button, not locked and not self.media_busy and not self.comfy_busy and bool(self.selected.get())),
            (self.stop_button, self.ready and not self.stopping and not self.closing),
            (self.clear_button, not self.answering and not self.closing),
            (self.send_button, self.ready and not self.answering and not self.stopping and not self.closing),
            (self.url_entry, not downloading and not self.closing),
            (self.worker_box, not downloading and not self.closing),
            (self.sample_button, not downloading and not self.closing),
            (self.qwen_button, not downloading and not self.closing),
            (self.download_button, not downloading and not self.closing),
            (self.cancel_button, downloading and not self.download_cancel.is_set() and not self.closing),
            (self.media_port_entry, comfy_idle and not comfy_running and not self.media_busy),
            (self.media_generate, comfy_idle and not self.media_busy and not locked),
            (self.media_open, self.media_result is not None and not self.closing),
            (self.comfy_action, comfy_idle and not self.media_busy and (comfy_running or not locked)),
            (self.comfy_cancel_button, not self.closing and self.comfy_cancel is not None
             and not self.comfy_cancel.is_set()),
            (self.comfy_models, comfy_idle and comfy_installed),
            (self.comfy_web, comfy_idle and comfy_running),
        ):
            widget.configure(state="normal" if enabled else "disabled")
        self.refresh_catalog_buttons()
        self.media_picker.configure(state="disabled" if self.media_busy or self.closing else "readonly")
        if self.ready or self.loading or self.stopping:
            self.media_status.set("先停止對話模型，讓創作引擎使用記憶體。")
        elif self.media_status.get() == "先停止對話模型，讓創作引擎使用記憶體。":
            self.media_status.set("先啟動本機 ComfyUI，再選擇要生成的媒體。")

    def load_model(self):
        if not self.executable.is_file():
            self.engine_status.set("找不到 llama-server.exe，請選擇引擎。")
            return
        model = self.models[self.selected.get()]
        executable = self.executable
        self.loading = True
        self.preview_generation += 1
        self.engine_status.set("正在估算並載入模型…")
        self.chat_status.set("正在載入模型…")
        self.refresh_buttons()

        def launch():
            plan = plan_load(executable, model)
            self.events.put((self.placement.set, (self.describe_plan(plan),)))
            try:
                self.engine.start(executable, model, self.shutdown, plan)
                return plan, False
            except (OSError, RuntimeError) as gpu_error:
                if not plan.layers or self.shutdown.is_set():
                    raise
                cpu = allocate(plan.mapped_bytes, plan.total_layers, [], mmap_args=plan.mmap_args)
                self.events.put((self.placement.set, (self.describe_plan(cpu),)))
                try:
                    self.engine.start(executable, model, self.shutdown, cpu)
                except (OSError, RuntimeError) as cpu_error:
                    raise RuntimeError(f"GPU：{gpu_error}\nCPU：{cpu_error}") from cpu_error
                return cpu, True

        def done(result, error):
            self.loading = False
            self.ready = error is None
            if self.closing and self.ready:
                self.stop_model()
            elif self.ready:
                self.clear_chat()
                plan, fallback = result
                self.engine_status.set("GPU 啟動失敗，已改用 CPU" if fallback
                                       else f"模型已就緒 · {plan.device or 'CPU'}")
                self.chat_status.set(model.name)
                self.tabs.select(0)
                self.prompt.focus_set()
            elif error and not self.closing:
                self.engine_status.set("啟動失敗，詳見對話頁")
                self.chat_status.set("模型未就緒")
                self.append(f"啟動失敗\n{error}\n\n", "notice")
                self.tabs.select(0)
            self.refresh_buttons()

        self.background(launch, done)

    def stop_model(self):
        self.stopping = True
        self.ready = False
        self.engine_status.set("正在停止模型…")
        self.refresh_buttons()

        def done(_, error):
            self.stopping = False
            self.engine_status.set("模型已停止" if error is None else str(error))
            self.chat_status.set("啟動模型後即可開始對話")
            self.refresh_buttons()

        self.background(self.engine.stop, done)

    def clear_chat(self):
        self.history.clear()
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")

    def append(self, text, tag=None):
        self.output.configure(state="normal")
        self.output.insert("end", text, (tag,) if tag else ())
        self.output.see("end")
        self.output.configure(state="disabled")

    def enter_to_send(self, event):
        if event.state & 1:
            return None
        self.send()
        return "break"

    def send(self):
        if not self.ready or self.answering or self.stopping or self.closing:
            return
        prompt = self.prompt.get("1.0", "end-1c").strip()
        if not prompt:
            return
        self.prompt.delete("1.0", "end")
        self.append("你\n", "speaker")
        self.append(prompt + "\n\n")
        self.append("模型\n", "speaker")
        self.answering = True
        self.chat_status.set("模型正在回覆…")
        self.refresh_buttons()
        user = {"role": "user", "content": prompt}
        messages = [*self.history, user]

        def task():
            tokens = []
            for token in self.engine.stream(messages):
                tokens.append(token)
                self.events.put((self.append, (token,)))
            return "".join(tokens)

        def done(answer, error):
            self.answering = False
            if error is None and answer:
                self.history.extend((user, {"role": "assistant", "content": answer}))
            elif not self.closing:
                self.append(f"\n{error or '模型回傳空白內容。'}", "notice")
            self.append("\n\n")
            if self.ready:
                if self.engine.running():
                    self.chat_status.set(self.engine.model.name)
                else:
                    self.stop_model()
            self.refresh_buttons()

        self.background(task, done)

    def download(self):
        try:
            workers = int(self.workers.get())
            if not 1 <= workers <= 16:
                raise ValueError
        except ValueError:
            self.download_status.set("下載執行緒須介於 1 到 16。")
            return
        url = self.url.get().strip()
        cancel = self.download_cancel = Event()
        self.progress.set(0)
        self.download_status.set("正在檢查下載來源…")
        self.refresh_buttons()
        start = time.monotonic()
        last_update = 0.0

        def report(received, total, count):
            nonlocal last_update
            now = time.monotonic()
            if received not in (0, total) and now - last_update < 0.12:
                return
            last_update = now
            rate = received / max(now - start, 0.01)
            self.events.put((self.update_progress, (received, total, count, rate)))

        def done(model, error):
            self.download_cancel = None
            self.progress_bar.stop()
            self.progress_bar.configure(mode="determinate")
            if isinstance(error, DownloadCancelled) or (error is not None and cancel.is_set()):
                self.progress.set(0)
                self.download_status.set("下載已取消")
            elif error:
                self.progress.set(0)
                self.download_status.set(f"下載失敗：{error}")
            else:
                self.progress.set(100)
                self.download_status.set(f"下載完成 · {model.name}")
                self.refresh_models(None if self.ready or self.loading or self.stopping else model)
            self.refresh_buttons()

        self.background(lambda: download_model(url, MODEL_DIR, workers, cancel, report), done)

    def update_progress(self, received, total, count, rate):
        if self.download_cancel.is_set():
            return
        if total:
            self.progress.set(received / total * 100)
        elif self.progress_bar.cget("mode") != "indeterminate":
            self.progress_bar.configure(mode="indeterminate")
            self.progress_bar.start(40)
        size = f" / {format_size(total)}" if total else ""
        self.download_status.set(f"{count} 個執行緒  ·  {format_size(received)}{size}  ·  {format_size(rate)}/秒")

    def cancel_download(self):
        if self.download_cancel is not None:
            self.download_cancel.set()
            self.download_status.set("正在取消下載…")
            self.refresh_buttons()

    def close(self):
        if self.closing:
            return
        self.closing = True
        self.shutdown.set()
        self.cancel_download()
        self.cancel_comfy()
        if not self.comfy_busy and self.comfy.running():
            self.stop_comfy()
        if self.ready and not self.stopping:
            self.stop_model()
        self.refresh_buttons()


if __name__ == "__main__":
    window = tk.Tk()
    LocalLLM(window)
    window.mainloop()
