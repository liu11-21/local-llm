"""Desktop controls for a model team run."""
import os
import tkinter as tk
from tkinter import ttk
from threading import Event

from model_team import MAX_MEMBERS, MAX_PROMPT, Member, cloud_member, run_team


class TeamPanel:
    def __init__(self, app, pane, output):
        self.app = app
        self.output = output
        self.members = []
        self.cancel = None
        self.result_directory = None
        self.status = tk.StringVar(value="加入至少兩個模型，選一個當主模型。")
        self.serial = tk.BooleanVar()
        self.lead = tk.StringVar()
        self.local = tk.StringVar()

        pane.columnconfigure(0, weight=1)
        pane.rowconfigure(6, weight=1)
        ttk.Label(pane, text="模型團隊", style="Section.TLabel").grid(row=0, sticky="w")
        tools = ttk.Frame(pane)
        tools.grid(row=1, sticky="ew", pady=(5, 4))
        tools.columnconfigure(0, weight=1)
        self.local_picker = ttk.Combobox(tools, textvariable=self.local, width=12, state="readonly")
        self.local_picker.grid(row=0, column=0, sticky="ew")
        self.add_local = ttk.Button(tools, text="加入本機", command=self.add_local_model)
        self.add_local.grid(row=0, column=1, padx=4)
        self.add_cloud = ttk.Button(tools, text="加入雲端", command=self.add_cloud_model)
        self.add_cloud.grid(row=0, column=2)
        self.remove = ttk.Button(tools, text="移除", command=self.remove_model)
        self.remove.grid(row=0, column=3, padx=(4, 0))

        table = ttk.Frame(pane)
        table.grid(row=2, sticky="ew")
        table.columnconfigure(0, weight=1)
        self.table = ttk.Treeview(table, columns=("model", "source", "status"), show="headings", height=3,
                                  selectmode="browse")
        for key, name, width in (("model", "模型", 175), ("source", "來源", 130), ("status", "狀態", 120)):
            self.table.heading(key, text=name)
            self.table.column(key, width=width, minwidth=70)
        self.table.grid(row=0, column=0, sticky="ew")
        scroll = ttk.Scrollbar(table, orient="vertical", command=self.table.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.table.configure(yscrollcommand=scroll.set)
        self.table.bind("<<TreeviewSelect>>", lambda _: self.refresh())

        options = ttk.Frame(pane)
        options.grid(row=3, sticky="ew", pady=4)
        options.columnconfigure(1, weight=1)
        ttk.Label(options, text="主模型").grid(row=0, column=0, padx=(0, 5))
        self.lead_picker = ttk.Combobox(options, textvariable=self.lead, width=12, state="readonly")
        self.lead_picker.grid(row=0, column=1, sticky="ew")
        self.lead_picker.bind("<<ComboboxSelected>>", lambda _: self.refresh())
        self.queue = ttk.Checkbutton(options, text="本機一律排隊", variable=self.serial)
        self.queue.grid(row=0, column=2, padx=(8, 0))

        ttk.Label(pane, text="提示詞").grid(row=4, sticky="w")
        self.prompt = app.textbox(pane, height=3, width=25)
        self.prompt.grid(row=5, sticky="ew", pady=(3, 4))

        result = ttk.Frame(pane)
        result.grid(row=6, sticky="nsew")
        result.columnconfigure(0, weight=1)
        result.rowconfigure(1, weight=1)
        ttk.Label(result, text="最終回答").grid(row=0, sticky="w")
        self.answer = app.textbox(result, height=2, width=25, state="disabled")
        self.answer.grid(row=1, column=0, sticky="nsew", pady=(3, 0))
        answer_scroll = ttk.Scrollbar(result, orient="vertical", command=self.answer.yview)
        answer_scroll.grid(row=1, column=1, sticky="ns")
        self.answer.configure(yscrollcommand=answer_scroll.set)

        actions = ttk.Frame(pane)
        actions.grid(row=7, sticky="ew", pady=(5, 2))
        self.run = ttk.Button(actions, text="執行團隊", style="Primary.TButton", command=self.start)
        self.run.pack(side="left")
        self.stop = ttk.Button(actions, text="取消", command=self.request_cancel)
        self.stop.pack(side="left", padx=4)
        self.open = ttk.Button(actions, text="開啟結果資料夾", command=self.open_results)
        self.open.pack(side="left")
        ttk.Label(pane, textvariable=self.status, style="Muted.TLabel", wraplength=460).grid(row=8, sticky="w")
        self.cloud_note = ttk.Label(pane, style="Muted.TLabel", wraplength=460)
        self.cloud_note.grid(row=9, sticky="w")
        self.cloud_note.grid_remove()

    def local_models_changed(self):
        labels = list(self.app.models)
        self.local_picker.configure(values=labels)
        if self.local.get() not in labels:
            self.local.set(labels[0] if labels else "")

    def refresh(self):
        app = self.app
        idle = self.cancel is None and not app.closing
        room = len(self.members) < MAX_MEMBERS
        self.local_picker.configure(state="readonly" if idle and app.models else "disabled")
        self.lead_picker.configure(state="readonly" if idle and self.members else "disabled")
        self.prompt.configure(state="normal" if idle else "disabled")
        blocked = app.ready or app.loading or app.stopping or app.media_busy or app.comfy_busy
        for widget, enabled in (
            (self.add_local, idle and room and app.models), (self.add_cloud, idle and room),
            (self.remove, idle and self.table.selection()), (self.queue, idle),
            (self.run, idle and len(self.members) >= 2 and not blocked),
            (self.stop, self.cancel is not None and not self.cancel.is_set() and not app.closing),
            (self.open, self.result_directory is not None and not app.closing),
        ):
            widget.configure(state="normal" if enabled else "disabled")
        if any(member.url for member in self.members):
            lead = self.lead_picker.current()
            self.cloud_note.configure(text="雲端成員會收到提示詞。" + (
                "雲端主模型也會收到所有成功草稿。" if lead >= 0 and self.members[lead].url else ""))
            self.cloud_note.grid()
        else:
            self.cloud_note.grid_remove()

    def refresh_members(self, preferred=None):
        rows = self.table.get_children()
        if rows:
            self.table.delete(*rows)
        for index, member in enumerate(self.members):
            self.table.insert("", "end", iid=str(index), values=(member.label, member.host or "本機 GGUF", "待執行"))
        self.lead_picker.configure(values=[f"{i + 1}. {member.label}" for i, member in enumerate(self.members)])
        if self.members:
            self.lead_picker.current(self.members.index(preferred) if preferred in self.members else 0)
        else:
            self.lead.set("")
        self.refresh()

    def add(self, member):
        if len(self.members) >= MAX_MEMBERS:
            raise ValueError("每個團隊最多六個模型。")
        if any((other.path, other.url, other.model) == (member.path, member.url, member.model)
               for other in self.members):
            raise ValueError("這個模型已在團隊中。")
        selected = self.lead_picker.current()
        lead = self.members[selected] if selected >= 0 else None
        self.members.append(member)
        self.status.set(f"已加入 {member.label}")
        self.refresh_members(lead)

    def add_local_model(self):
        path = self.app.models.get(self.local.get())
        if path is not None:
            try:
                self.add(Member(path.name, path=path.resolve()))
            except ValueError as error:
                self.status.set(str(error))

    def add_cloud_model(self):
        dialog = tk.Toplevel(self.app.root)
        dialog.title("加入雲端模型")
        dialog.transient(self.app.root)
        dialog.resizable(False, False)
        box = ttk.Frame(dialog, padding=16)
        box.pack(fill="both", expand=True)
        values = [tk.StringVar(master=dialog) for _ in range(4)]
        values[1].set("https://api.openai.com/v1")
        first = None
        for i, (label, value) in enumerate(zip(("名稱（選填）", "API 網址", "模型 ID", "API 金鑰"), values)):
            ttk.Label(box, text=label).grid(row=i, column=0, sticky="w", padx=(0, 8), pady=3)
            entry = ttk.Entry(box, textvariable=value, width=42, show="*" if i == 3 else "")
            entry.grid(row=i, column=1, sticky="ew")
            if i == 0:
                first = entry
        message = tk.StringVar(master=dialog, value="支援相容的 Chat Completions API。金鑰只留在本次開啟的程式。")
        ttk.Label(box, textvariable=message, wraplength=395).grid(row=4, columnspan=2, sticky="w", pady=6)

        def submit(event=None):
            try:
                self.add(cloud_member(*(value.get() for value in values)))
            except ValueError as error:
                message.set(str(error))
            else:
                dialog.destroy()

        ttk.Button(box, text="加入", style="Primary.TButton", command=submit).grid(row=5, column=1, sticky="e")
        dialog.bind("<Return>", submit)
        dialog.bind("<Escape>", lambda _: dialog.destroy())
        dialog.grab_set()
        first.focus_set()

    def remove_model(self):
        selection = self.table.selection()
        if selection:
            lead = self.members[self.lead_picker.current()]
            self.members.pop(int(selection[0]))
            self.refresh_members(lead)

    def set_answer(self, text):
        self.answer.configure(state="normal")
        self.answer.delete("1.0", "end")
        self.answer.insert("1.0", text)
        self.answer.configure(state="disabled")

    def start(self):
        if not self.run.instate(["!disabled"]):
            return
        prompt = self.prompt.get("1.0", "end-1c")
        if not prompt.strip() or len(prompt) > MAX_PROMPT:
            self.status.set(f"請輸入 1–{MAX_PROMPT:,} 字的提示詞。")
            return
        members = tuple(self.members)
        main = self.lead_picker.current()
        if not 0 <= main < len(members):
            self.status.set("請選擇主模型。")
            return
        executable = self.app.executable
        if any(member.path for member in members) and not executable.is_file():
            self.status.set("找不到本機引擎，請先在左欄選擇引擎。")
            return
        serial = self.serial.get()
        cancel = self.cancel = Event()
        self.set_answer("")
        self.result_directory = None
        for i in range(len(members)):
            self.table.set(str(i), "status", "排隊中")
        self.status.set("正在啟動模型團隊…")
        self.app.refresh_buttons()

        def show_progress(message):
            if not cancel.is_set():
                self.status.set(message)

        def report(message):
            self.app.events.put((show_progress, (message,)))

        def row(index, status):
            self.app.events.put((self.table.set, (str(index), "status", status)))

        def done(result, error):
            self.cancel = None
            if error:
                self.status.set(str(error))
            else:
                self.result_directory = result.directory
                self.status.set(result.status)
                self.set_answer(result.answer)
            self.app.refresh_buttons()

        self.app.background(lambda: run_team(members, main, prompt, executable, self.output, cancel,
                                             report, row, serial), done)

    def request_cancel(self):
        if self.cancel is not None:
            self.cancel.set()
            self.status.set("正在停止本機模型並等待已送出的請求結束…")
            self.refresh()

    def open_results(self):
        if self.result_directory:
            try:
                os.startfile(self.result_directory)
            except OSError as error:
                self.status.set(str(error))
