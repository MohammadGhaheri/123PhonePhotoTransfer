from __future__ import annotations

import queue
import threading
from threading import Event

from adb_manager import ADBManager
from transfer_engine import TransferEngine, TransferStats


class TransferWorker:
    def __init__(
        self,
        *,
        adb: ADBManager,
        serial: str,
        remote_root: str,
        destination: str,
        extensions: set[str],
        move: bool,
        retries: int,
        events: queue.Queue,
    ) -> None:
        self.cancel_event = Event()
        self.current_process = None
        self.events = events
        self.thread: threading.Thread | None = None
        self.params = dict(
            adb=adb,
            serial=serial,
            remote_root=remote_root,
            destination_root=destination,
            extensions=extensions,
            move_after_verify=move,
            retries=retries,
            cancel_event=self.cancel_event,
            on_log=lambda msg: self.events.put(("log", msg)),
            on_progress=self._on_progress,
            on_process=self._on_process,
        )

    def _on_process(self, proc):
        self.current_process = proc

    def _on_progress(self, s: TransferStats, current: str):
        self.events.put(("progress", s.processed, s.total, s.copied, s.skipped, s.failed, current))

    def start(self):
        self.thread = threading.Thread(target=self._run, name="PhonePhotoTransferWorker", daemon=True)
        self.thread.start()

    def is_running(self) -> bool:
        return bool(self.thread and self.thread.is_alive())

    def stop(self):
        self.cancel_event.set()
        proc = self.current_process
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass

    def _run(self):
        try:
            stats = TransferEngine(**self.params).run()
            self.events.put(("done", stats))
        except Exception as exc:
            self.events.put(("failed", str(exc)))
        finally:
            self.events.put(("worker_finished",))

