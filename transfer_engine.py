from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from threading import Event
from typing import Callable

from adb_manager import ADBManager, AdbError, DeviceUnavailable
from transfer_database import TransferDatabase


DEFAULT_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".gif",
    ".mp4", ".mov", ".mkv", ".avi", ".3gp", ".webm",
}


@dataclass
class TransferStats:
    total: int = 0
    processed: int = 0
    copied: int = 0
    skipped: int = 0
    failed: int = 0
    deleted: int = 0
    bytes_copied: int = 0


class TransferEngine:
    def __init__(
        self,
        adb: ADBManager,
        *,
        serial: str,
        remote_root: str,
        destination_root: str | Path,
        extensions: set[str] | None = None,
        move_after_verify: bool = False,
        retries: int = 3,
        cancel_event: Event | None = None,
        on_log: Callable[[str], None] | None = None,
        on_progress: Callable[[TransferStats, str], None] | None = None,
        on_process: Callable[[subprocess.Popen | None], None] | None = None,
    ) -> None:
        self.adb = adb
        self.serial = serial
        self.remote_root = remote_root.rstrip("/")
        self.destination_root = Path(destination_root)
        self.extensions = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in (extensions or DEFAULT_EXTENSIONS)}
        self.move_after_verify = move_after_verify
        self.retries = max(1, retries)
        self.cancel_event = cancel_event or Event()
        self.on_log = on_log or (lambda _msg: None)
        self.on_progress = on_progress or (lambda _stats, _path: None)
        self.on_process = on_process
        self.stats = TransferStats()
        self.db = TransferDatabase(self.destination_root)

    def _check_cancelled(self) -> None:
        if self.cancel_event.is_set():
            raise AdbError("عملیات توسط کاربر متوقف شد.")

    def _filtered_files(self, files: list[str]) -> list[str]:
        return [p for p in files if PurePosixPath(p).suffix.lower() in self.extensions]

    def local_path_for(self, remote_path: str) -> Path:
        root = PurePosixPath(self.remote_root)
        path = PurePosixPath(remote_path)
        try:
            rel = path.relative_to(root)
        except ValueError:
            rel = PurePosixPath(path.name)
        # Prevent any unexpected parent traversal from reaching outside destination.
        safe_parts = [part for part in rel.parts if part not in ("", ".", "..")]
        return self.destination_root.joinpath(*safe_parts)

    def _is_resume_skip(self, remote_path: str) -> bool:
        row = self.db.get_completed(remote_path)
        if not row:
            return False
        saved_size, local_path, deleted_remote = row
        local = Path(local_path)
        if local.is_file() and local.stat().st_size == saved_size:
            if self.move_after_verify and not deleted_remote:
                # We copied it in an earlier copy-mode run; current move-mode should still remove remote safely.
                return False
            return True
        return False

    def _copy_one(self, remote_path: str) -> None:
        self._check_cancelled()
        local = self.local_path_for(remote_path)
        local.parent.mkdir(parents=True, exist_ok=True)
        part = local.with_name(local.name + ".part")

        remote_size = self.adb.file_size(remote_path, serial=self.serial, cancel_event=self.cancel_event)

        # Existing exact-size file is safe to register as complete, even if DB was lost.
        if local.is_file() and local.stat().st_size == remote_size:
            deleted = False
            if self.move_after_verify:
                self.adb.delete_file(remote_path, serial=self.serial, cancel_event=self.cancel_event)
                deleted = True
                self.stats.deleted += 1
            self.db.mark_completed(remote_path, remote_size, str(local), deleted)
            self.stats.skipped += 1
            return

        if part.exists():
            try:
                part.unlink()
            except OSError:
                pass

        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            self._check_cancelled()
            try:
                if attempt > 1:
                    self.on_log(f"Retry {attempt}/{self.retries}: {remote_path}")
                    time.sleep(min(2.0 * attempt, 5.0))
                    self.adb.ensure_ready(self.serial)

                self.adb.pull(
                    remote_path,
                    part,
                    serial=self.serial,
                    cancel_event=self.cancel_event,
                    on_process=self.on_process,
                )
                if not part.exists():
                    raise AdbError("ADB pull finished but temporary file was not created.")
                local_size = part.stat().st_size
                if local_size != remote_size:
                    raise AdbError(f"Verify failed: phone={remote_size} bytes, PC={local_size} bytes")

                os.replace(part, local)
                deleted = False
                if self.move_after_verify:
                    self.adb.delete_file(remote_path, serial=self.serial, cancel_event=self.cancel_event)
                    deleted = True
                    self.stats.deleted += 1

                self.db.mark_completed(remote_path, remote_size, str(local), deleted)
                self.stats.copied += 1
                self.stats.bytes_copied += remote_size
                return
            except DeviceUnavailable:
                if part.exists():
                    try:
                        part.unlink()
                    except OSError:
                        pass
                raise
            except Exception as exc:
                last_error = exc
                if part.exists():
                    try:
                        part.unlink()
                    except OSError:
                        pass

        self.db.mark_error(remote_path, remote_size, str(local))
        raise AdbError(str(last_error or "Unknown transfer error"))

    def run(self) -> TransferStats:
        try:
            self.adb.ensure_ready(self.serial)
            self.on_log(f"Scanning {self.remote_root} …")
            files = self._filtered_files(self.adb.list_files(self.remote_root, serial=self.serial, cancel_event=self.cancel_event))
            self.stats.total = len(files)
            self.on_log(f"Found {self.stats.total} matching media files.")
            self.on_progress(self.stats, "")

            for remote_path in files:
                self._check_cancelled()
                if self._is_resume_skip(remote_path):
                    self.stats.skipped += 1
                    self.stats.processed += 1
                    self.on_progress(self.stats, remote_path)
                    continue

                try:
                    self.on_log(f"Transfer: {remote_path}")
                    self._copy_one(remote_path)
                except DeviceUnavailable as exc:
                    self.on_log(f"DEVICE DISCONNECTED: {exc}")
                    raise
                except AdbError as exc:
                    if self.cancel_event.is_set():
                        raise
                    self.stats.failed += 1
                    self.on_log(f"ERROR: {remote_path} — {exc}")
                finally:
                    self.stats.processed += 1
                    self.on_progress(self.stats, remote_path)

            return self.stats
        finally:
            self.db.close()
