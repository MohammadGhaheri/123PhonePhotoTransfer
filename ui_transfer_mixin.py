from __future__ import annotations

import queue
from pathlib import Path
from tkinter import messagebox

from app_worker import TransferWorker
from transfer_engine import TransferStats


class TransferMixin:
    def start_transfer(self) -> None:
        params = self.validate_inputs()
        if not params:
            return
        serial, remote, dest, exts, move, retries = params
        Path(dest).mkdir(parents=True, exist_ok=True)
        self.save_settings()

        self.worker = TransferWorker(
            adb=self.adb,
            serial=serial,
            remote_root=remote,
            destination=dest,
            extensions=exts,
            move=move,
            retries=retries,
            events=self.events,
        )
        self.progress.configure(mode="indeterminate")
        self.progress.start(12)
        self.stats_var.set("در حال اسکن فایل‌ها…")
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.worker.start()

    def stop_transfer(self) -> None:
        if self.worker and self.worker.is_running():
            self.append_log("Stopping safely…")
            self.worker.stop()
            self.stop_btn.configure(state="disabled")

    def _poll_events(self) -> None:
        try:
            while True:
                item = self.events.get_nowait()
                kind = item[0]
                if kind == "log":
                    self.append_log(item[1])
                elif kind == "progress":
                    _, processed, total, copied, skipped, failed, current = item
                    if str(self.progress.cget("mode")) != "determinate":
                        self.progress.stop()
                        self.progress.configure(mode="determinate")
                    self.progress.configure(maximum=max(total, 1))
                    self.progress_var.set(processed)
                    self.stats_var.set(f"{processed}/{total}  |  کپی: {copied}  |  ردشده: {skipped}  |  خطا: {failed}")
                    self.current_var.set(current)
                elif kind == "done":
                    stats: TransferStats = item[1]
                    mb = stats.bytes_copied / (1024 * 1024)
                    self.append_log(f"DONE — copied={stats.copied}, skipped={stats.skipped}, failed={stats.failed}, {mb:.1f} MB")
                    messagebox.showinfo(
                        "تمام شد",
                        f"انتقال تمام شد.\n\nکپی: {stats.copied}\nردشده: {stats.skipped}\nخطا: {stats.failed}\nحذف از گوشی: {stats.deleted}",
                    )
                elif kind == "failed":
                    message = item[1]
                    self.append_log(f"STOPPED/FAILED — {message}")
                    if "متوقف" not in message:
                        messagebox.showerror("خطا", message)
                elif kind == "worker_finished":
                    self.progress.stop()
                    self.progress.configure(mode="determinate")
                    self.start_btn.configure(state="normal")
                    self.stop_btn.configure(state="disabled")
                    self.worker = None
                    self.refresh_devices(silent=True)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)
