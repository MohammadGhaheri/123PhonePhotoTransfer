from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox

from adb_manager import ADBManager, AdbError


class ADBMixin:
    def init_adb(self) -> None:
        configured = self.adb_var.get().strip()
        try:
            self.adb = ADBManager(configured or None)
            self.adb_var.set(self.adb.adb_path)
            self.adb.save_portable_path_hint()
            self.device_status_var.set(f"ADB آماده ({self.adb.discovery_method}) — {self.adb.adb_path}")
            self.append_log(f"ADB auto-detected via {self.adb.discovery_method}: {self.adb.adb_path}")
            self.save_settings()
            self.refresh_devices()
        except AdbError as exc:
            self.adb = None
            self.device_status_var.set("ADB پیدا نشد — مسیر adb.exe را انتخاب کنید.")
            self.append_log(str(exc))

    def choose_adb(self) -> None:
        start = self.adb_var.get().strip()
        initialdir = str(Path(start).parent) if start and Path(start).parent.exists() else str(Path.home())
        filename = filedialog.askopenfilename(
            title="انتخاب adb.exe",
            initialdir=initialdir,
            filetypes=[("ADB executable", "adb.exe"), ("All files", "*.*")],
        )
        if not filename:
            return
        try:
            candidate = ADBManager(filename)
            candidate.run(["version"], timeout=8)
            self.adb = candidate
            candidate.save_portable_path_hint()
            self.adb_var.set(candidate.adb_path)
            self.device_status_var.set(f"ADB آماده — {candidate.adb_path}")
            self.append_log(f"ADB selected: {candidate.adb_path}")
            self.save_settings()
            self.refresh_devices()
        except Exception as exc:
            messagebox.showerror("ADB", f"این فایل به‌عنوان ADB قابل استفاده نیست:\n{exc}")

    def auto_detect_adb(self) -> None:
        self.adb_var.set("")
        self.init_adb()

    def _periodic_refresh_devices(self) -> None:
        if not (self.worker and self.worker.is_running()):
            self.refresh_devices(silent=True)
        self.root.after(2500, self._periodic_refresh_devices)

    def refresh_devices(self, silent: bool = False) -> None:
        if not self.adb:
            return
        try:
            devices = self.adb.list_devices()
        except Exception as exc:
            self.device_status_var.set(f"ADB error: {exc}")
            if not silent:
                self.append_log(f"ADB error: {exc}")
            return

        old_serial = self._devices_by_label.get(self.device_var.get())
        labels: list[str] = []
        self._devices_by_label = {}
        for d in devices:
            model = ""
            for token in d.details.split():
                if token.startswith("model:"):
                    model = token.split(":", 1)[1]
                    break
            label = f"{model + ' — ' if model else ''}{d.serial} — {d.state}"
            labels.append(label)
            self._devices_by_label[label] = d.serial
        self.device_combo["values"] = labels

        chosen = ""
        if old_serial:
            for label, serial in self._devices_by_label.items():
                if serial == old_serial:
                    chosen = label
                    break
        if not chosen and labels:
            chosen = labels[0]
        self.device_var.set(chosen)

        if not devices:
            self.device_status_var.set(f"ADB آماده است، اما گوشی دیده نشد — {self.adb.adb_path}")
        elif any(d.state == "unauthorized" for d in devices):
            self.device_status_var.set("گوشی دیده شد ولی Unauthorized است؛ پیام RSA روی گوشی را Allow کنید.")
        else:
            ready = sum(1 for d in devices if d.state == "device")
            self.device_status_var.set(f"ADB آماده — {ready} دستگاه آماده")

    def choose_destination(self) -> None:
        start = self.dest_var.get().strip() or str(Path.home() / "Pictures" / "Phone Backup")
        path = filedialog.askdirectory(title="انتخاب پوشه مقصد", initialdir=start if Path(start).exists() else str(Path.home()))
        if path:
            self.dest_var.set(path)

    def parsed_extensions(self) -> set[str]:
        raw = self.ext_var.get().replace(";", ",")
        values = set()
        for item in raw.split(","):
            ext = item.strip().lower()
            if ext:
                values.add(ext if ext.startswith(".") else "." + ext)
        return values

    def validate_inputs(self):
        if not self.adb:
            messagebox.showerror("ADB", "ADB پیدا نشده است.")
            return None
        label = self.device_var.get()
        serial = self._devices_by_label.get(label)
        if not serial:
            messagebox.showwarning("گوشی", "هیچ گوشی ADB انتخاب نشده است.")
            return None
        remote = self.source_var.get().strip()
        dest = self.dest_var.get().strip()
        exts = self.parsed_extensions()
        if not remote.startswith("/"):
            messagebox.showwarning("مسیر", "مسیر پوشه گوشی باید با / شروع شود.")
            return None
        if not dest:
            messagebox.showwarning("مقصد", "پوشه مقصد ویندوز را انتخاب کنید.")
            return None
        if not exts:
            messagebox.showwarning("پسوندها", "حداقل یک پسوند فایل وارد کنید.")
            return None
        move = self.mode_var.get() == "move"
        if move:
            ok = messagebox.askyesno(
                "تأیید Move",
                "در حالت Move، هر فایل فقط بعد از کپی کامل و تطبیق اندازه از گوشی حذف می‌شود.\n\nادامه می‌دهید؟",
                default="no",
            )
            if not ok:
                return None
        try:
            retries = max(1, min(10, int(self.retry_var.get())))
        except Exception:
            retries = 3
            self.retry_var.set(3)
        return serial, remote, dest, exts, move, retries
