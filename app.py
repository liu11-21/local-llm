"""Local LLM desktop application."""
import os
from pathlib import Path
from queue import Empty, SimpleQueue
import shutil
from threading import Event, Thread
import time
import tkinter as tk
from tkinter import filedialog, ttk

from catalog import RECOMMENDED, model_files, recommended_file, search_models
from downloads import DownloadCancelled, check_gguf, download_model
from engine import LocalEngine
from hardware import FIT_LABELS, Fit, detect_hardware, estimate_ram, model_fit

VERSION = "0.3.0"
APP_DIR = Path(__file__).resolve().parent
MODEL_DIR = APP_DIR / "models"
ENGINE_PATH = APP_DIR / "engine" / "llama-server.exe"
SAMPLE_URL = (
    "https://huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF/"
    "resolve/09816ac/SmolLM2-135M-Instruct-Q4_K_M.gguf"
)
QWEN_URL = (
    "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/"
    "resolve/9217f5d/qwen2.5-0.5b-instruct-q4_k_m.gguf"
)

BG = "#111724"
PANEL = "#1a2334"
FIELD = "#111928"
TEXT = "#edf3ff"
MUTED = "#aab9d1"
ACCENT = "#8ee4c5"
BORDER = "#34415a"
FONT = "Microsoft JhengHei UI"


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
        self.catalog_busy = False
        self.catalog_files = []
        self.showing_recommended = True
        self.catalog_query = tk.StringVar()
        self.catalog_status = tk.StringVar()
        self.hardware_status = tk.StringVar()

        self.selected = tk.StringVar()
        system_engine = shutil.which("llama-server")
        self.executable = Path(system_engine) if system_engine and not ENGINE_PATH.is_file() else ENGINE_PATH
        self.engine_status = tk.StringVar(value="請選擇模型並啟動")
        self.engine_label = tk.StringVar(value=self.executable.name)
        self.model_info = tk.StringVar(value="尚未選擇模型")
        self.chat_status = tk.StringVar(value="啟動模型後即可開始對話")
        self.url = tk.StringVar(value=SAMPLE_URL)
        self.workers = tk.StringVar(value="4")
        self.download_status = tk.StringVar(value="等待下載")
        self.progress = tk.DoubleVar()

        self.root.title(f"Local LLM v{VERSION} · 本機模型工作台")
        self.root.geometry("1050x690")
        self.root.minsize(820, 610)
        self.root.configure(bg=BG)
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
        style.map("TButton", background=[("active", "#2b3a54")], foreground=[("disabled", "#8492a8")])
        style.configure("Primary.TButton", background=ACCENT, foreground=BG, bordercolor=ACCENT)
        style.map("Primary.TButton", background=[("disabled", PANEL), ("active", "#b4f4dc")],
                  foreground=[("disabled", "#8492a8"), ("active", BG)])
        for name in ("TEntry", "TCombobox", "TSpinbox"):
            style.configure(name, fieldbackground=FIELD, foreground=TEXT, insertcolor=TEXT,
                            background=PANEL, arrowcolor=TEXT, padding=6)
            style.map(name, fieldbackground=[("readonly", FIELD)], foreground=[("readonly", TEXT)],
                      selectbackground=[("readonly", FIELD)], selectforeground=[("readonly", TEXT)])
        style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(0, 0, 0, 0))
        style.configure("TNotebook.Tab", padding=(16, 9), background=PANEL, foreground=MUTED)
        style.map("TNotebook.Tab", background=[("selected", FIELD)], foreground=[("selected", ACCENT)])
        style.configure("Treeview", background=FIELD, fieldbackground=FIELD, foreground=TEXT, rowheight=26)
        style.map("Treeview", background=[("selected", "#344967")], foreground=[("selected", TEXT)])
        style.configure("Horizontal.TProgressbar", background=ACCENT, troughcolor=FIELD, bordercolor=BORDER)
        self.root.option_add("*TCombobox*Listbox.background", FIELD)
        self.root.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", "#2b3a54")
        self.root.option_add("*TCombobox*Listbox.selectForeground", TEXT)

    def build(self):
        shell = ttk.Frame(self.root, padding=(24, 18))
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(1, weight=1)
        header = ttk.Frame(shell)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 18))
        ttk.Label(header, text="Local LLM", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="本機模型工作台  /  GGUF 模型下載與串流對話", style="Muted.TLabel").pack(anchor="w")

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
        self.engine_button = ttk.Button(side, text="選擇 llama-server…", command=self.choose_engine)
        self.engine_button.pack(fill="x")
        self.load_button = ttk.Button(side, text="啟動模型", style="Primary.TButton", command=self.load_model)
        self.load_button.pack(fill="x", pady=(10, 5))
        self.stop_button = ttk.Button(side, text="停止模型", command=self.stop_model)
        self.stop_button.pack(fill="x")
        ttk.Label(side, textvariable=self.engine_status, style="CardMuted.TLabel", wraplength=210,
                  justify="left").pack(anchor="w", pady=(12, 0))

        self.tabs = ttk.Notebook(shell)
        self.tabs.grid(row=1, column=1, sticky="nsew")
        chat = ttk.Frame(self.tabs, padding=(14, 12))
        catalog = ttk.Frame(self.tabs, padding=(16, 14))
        self.download_tab = ttk.Frame(self.tabs, padding=(20, 18))
        self.tabs.add(chat, text="對話")
        self.tabs.add(catalog, text="模型清單")
        self.tabs.add(self.download_tab, text="模型下載")
        self.build_chat(chat)
        self.build_catalog(catalog)
        self.build_download(self.download_tab)

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
        self.output.tag_configure("notice", foreground="#ffd08e")
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

    def textbox(self, parent, **options):
        return tk.Text(parent, bg=FIELD, fg=TEXT, insertbackground=TEXT, selectbackground="#344967",
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
            self.refresh_buttons()

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
        if self.closing and not any((self.loading, self.stopping, self.answering, self.download_cancel)):
            self.root.destroy()
            return
        self.root.after(30, self.dispatch)

    def refresh_buttons(self):
        locked = self.ready or self.loading or self.stopping or self.answering or self.closing
        downloading = self.download_cancel is not None
        self.picker.configure(state="disabled" if locked else "readonly")
        for widget, enabled in (
            (self.import_button, not locked),
            (self.engine_button, not locked),
            (self.load_button, not locked and bool(self.selected.get())),
            (self.stop_button, self.ready and not self.stopping and not self.closing),
            (self.clear_button, not self.answering and not self.closing),
            (self.send_button, self.ready and not self.answering and not self.stopping and not self.closing),
            (self.url_entry, not downloading and not self.closing),
            (self.worker_box, not downloading and not self.closing),
            (self.sample_button, not downloading and not self.closing),
            (self.qwen_button, not downloading and not self.closing),
            (self.download_button, not downloading and not self.closing),
            (self.cancel_button, downloading and not self.download_cancel.is_set() and not self.closing),
        ):
            widget.configure(state="normal" if enabled else "disabled")
        self.refresh_catalog_buttons()

    def load_model(self):
        if not self.executable.is_file():
            self.engine_status.set("找不到 llama-server.exe，請選擇引擎。")
            return
        model = self.models[self.selected.get()]
        executable = self.executable
        self.loading = True
        self.engine_status.set("正在載入模型…")
        self.chat_status.set("正在載入模型…")
        self.refresh_buttons()

        def done(_, error):
            self.loading = False
            self.ready = error is None
            if self.closing and self.ready:
                self.stop_model()
            elif self.ready:
                self.clear_chat()
                self.engine_status.set("模型已就緒 · CPU")
                self.chat_status.set(model.name)
                self.tabs.select(0)
                self.prompt.focus_set()
            elif error and not self.closing:
                self.engine_status.set("啟動失敗，詳見對話頁")
                self.chat_status.set("模型未就緒")
                self.append(f"啟動失敗\n{error}\n\n", "notice")
                self.tabs.select(0)
            self.refresh_buttons()

        self.background(lambda: self.engine.start(executable, model, self.shutdown), done)

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
        if self.ready and not self.stopping:
            self.stop_model()
        self.refresh_buttons()


if __name__ == "__main__":
    window = tk.Tk()
    LocalLLM(window)
    window.mainloop()
