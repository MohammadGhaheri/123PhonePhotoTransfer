from __future__ import annotations

import json
from tkinter import messagebox

from app_config import PRESETS


class SettingsMixin:
    def load_settings(self) -> None:
        try:
            data = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except Exception:
            return
        self.adb_var.set(data.get("adb_path", ""))
        self.source_var.set(data.get("source", PRESETS[0]))
        self.dest_var.set(data.get("destination", ""))
        self.ext_var.set(data.get("extensions", self.ext_var.get()))
        self.retry_var.set(int(data.get("retries", 3)))
        self.mode_var.set("move" if data.get("move") else "copy")

    def save_settings(self) -> None:
        data = {
            "adb_path": self.adb.adb_path if self.adb else self.adb_var.get().strip(),
            "source": self.source_var.get().strip(),
            "destination": self.dest_var.get().strip(),
            "extensions": self.ext_var.get().strip(),
            "retries": int(self.retry_var.get() or 3),
            "move": self.mode_var.get() == "move",
        }
        try:
            self.settings_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def on_close(self) -> None:
        if self.worker and self.worker.is_running():
            if not messagebox.askyesno("خروج", "انتقال در حال اجراست. عملیات متوقف و برنامه بسته شود؟"):
                return
            self.worker.stop()
        self.save_settings()
        self.root.destroy()
