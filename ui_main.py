from __future__ import annotations

import queue
import tkinter as tk
from tkinter import ttk

from app_config import APP_VERSION, PRESETS, app_data_dir
from app_worker import TransferWorker
from transfer_engine import DEFAULT_EXTENSIONS
from ui_adb_mixin import ADBMixin
from ui_transfer_mixin import TransferMixin
from ui_settings_mixin import SettingsMixin


class MainWindow(ADBMixin, TransferMixin, SettingsMixin):
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(f"Phone Photo Transfer v{APP_VERSION}")
        self.root.geometry("900x700")
        self.root.minsize(760, 580)

        self.adb: ADBManager | None = None
        self.worker: TransferWorker | None = None
        self.events: queue.Queue = queue.Queue()
        self.settings_path = app_data_dir() / "settings.json"
        self._devices_by_label: dict[str, str] = {}

        self.adb_var = tk.StringVar()
        self.device_status_var = tk.StringVar(value="در حال بررسی ADB…")
        self.device_var = tk.StringVar()
        self.source_var = tk.StringVar(value=PRESETS[0])
        self.dest_var = tk.StringVar()
        self.ext_var = tk.StringVar(value=", ".join(sorted(e.lstrip(".") for e in DEFAULT_EXTENSIONS)))
        self.mode_var = tk.StringVar(value="copy")
        self.retry_var = tk.IntVar(value=3)
        self.stats_var = tk.StringVar(value="آماده")
        self.current_var = tk.StringVar(value="")
        self.progress_var = tk.DoubleVar(value=0)

        self._build_ui()
        self.load_settings()
        self.init_adb()
        self.root.after(100, self._poll_events)
        self.root.after(2500, self._periodic_refresh_devices)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(10, weight=1)

        title = ttk.Label(outer, text="انتقال مطمئن عکس و ویدئو از گوشی به کامپیوتر با ADB", font=("Segoe UI", 14, "bold"))
        title.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

        status = ttk.Label(outer, textvariable=self.device_status_var)
        status.grid(row=1, column=0, columnspan=3, sticky="we", pady=(0, 12))

        ttk.Label(outer, text="ADB:").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
        adb_entry = ttk.Entry(outer, textvariable=self.adb_var)
        adb_entry.grid(row=2, column=1, sticky="we", pady=4)
        adb_buttons = ttk.Frame(outer)
        adb_buttons.grid(row=2, column=2, sticky="e", pady=4)
        ttk.Button(adb_buttons, text="انتخاب adb.exe…", command=self.choose_adb).pack(side="left", padx=(6, 0))
        ttk.Button(adb_buttons, text="تشخیص خودکار", command=self.auto_detect_adb).pack(side="left", padx=(6, 0))

        ttk.Label(outer, text="گوشی:").grid(row=3, column=0, sticky="w", padx=(0, 8), pady=4)
        self.device_combo = ttk.Combobox(outer, textvariable=self.device_var, state="readonly")
        self.device_combo.grid(row=3, column=1, columnspan=2, sticky="we", pady=4)

        ttk.Label(outer, text="پوشه روی گوشی:").grid(row=4, column=0, sticky="w", padx=(0, 8), pady=4)
        self.source_combo = ttk.Combobox(outer, textvariable=self.source_var, values=PRESETS, state="normal")
        self.source_combo.grid(row=4, column=1, columnspan=2, sticky="we", pady=4)

        ttk.Label(outer, text="پوشه مقصد ویندوز:").grid(row=5, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(outer, textvariable=self.dest_var).grid(row=5, column=1, sticky="we", pady=4)
        ttk.Button(outer, text="انتخاب…", command=self.choose_destination).grid(row=5, column=2, sticky="e", padx=(6, 0), pady=4)

        ttk.Label(outer, text="پسوندها:").grid(row=6, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(outer, textvariable=self.ext_var).grid(row=6, column=1, columnspan=2, sticky="we", pady=4)

        options = ttk.Frame(outer)
        options.grid(row=7, column=0, columnspan=3, sticky="we", pady=(8, 6))
        ttk.Label(options, text="حالت انتقال:").pack(side="left")
        ttk.Radiobutton(options, text="Copy — فقط کپی کن (پیشنهادی)", variable=self.mode_var, value="copy").pack(side="left", padx=(10, 14))
        ttk.Radiobutton(options, text="Move — بعد از Verify از گوشی حذف کن", variable=self.mode_var, value="move").pack(side="left")
        ttk.Label(options, text="Retry:").pack(side="left", padx=(24, 6))
        ttk.Spinbox(options, from_=1, to=10, textvariable=self.retry_var, width=4).pack(side="left")

        buttons = ttk.Frame(outer)
        buttons.grid(row=8, column=0, columnspan=3, sticky="we", pady=(4, 8))
        self.start_btn = ttk.Button(buttons, text="شروع انتقال", command=self.start_transfer)
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(buttons, text="توقف امن", command=self.stop_transfer, state="disabled")
        self.stop_btn.pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="بررسی مجدد گوشی", command=self.refresh_devices).pack(side="left", padx=(8, 0))

        self.progress = ttk.Progressbar(outer, variable=self.progress_var, maximum=1, mode="determinate")
        self.progress.grid(row=9, column=0, columnspan=3, sticky="we", pady=(0, 4))
        ttk.Label(outer, textvariable=self.stats_var).grid(row=10, column=0, columnspan=3, sticky="w")
        ttk.Label(outer, textvariable=self.current_var, wraplength=850).grid(row=11, column=0, columnspan=3, sticky="we", pady=(2, 6))

        log_frame = ttk.Frame(outer)
        log_frame.grid(row=12, column=0, columnspan=3, sticky="nsew")
        outer.rowconfigure(12, weight=1)
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.log_box = tk.Text(log_frame, wrap="none", height=14, font=("Consolas", 9))
        self.log_box.grid(row=0, column=0, sticky="nsew")
        scroll_y = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_box.yview)
        scroll_y.grid(row=0, column=1, sticky="ns")
        self.log_box.configure(yscrollcommand=scroll_y.set)

    def append_log(self, msg: str) -> None:
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
