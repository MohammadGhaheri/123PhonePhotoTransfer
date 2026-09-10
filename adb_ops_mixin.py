from __future__ import annotations

import shlex
import subprocess
import time
from pathlib import Path
from threading import Event
from typing import Callable, Optional

from adb_types import CREATE_NO_WINDOW, AdbError, Device, DeviceUnavailable


class ADBOpsMixin:
    def save_portable_path_hint(self) -> None:
        """Best-effort portable hint beside the app; useful for doctor.bat and future launches."""
        try:
            (self._app_dir() / "adb_path.txt").write_text(self.adb_path, encoding="utf-8")
        except OSError:
            pass

    def _base_args(self, serial: str | None = None) -> list[str]:
        args = [self.adb_path]
        if serial:
            args += ["-s", serial]
        return args

    def run(
        self,
        args: list[str],
        *,
        serial: str | None = None,
        timeout: float | None = 30,
        check: bool = True,
        cancel_event: Event | None = None,
        on_process: Optional[Callable[[subprocess.Popen], None]] = None,
    ) -> subprocess.CompletedProcess[str]:
        cmd = self._base_args(serial) + args
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=CREATE_NO_WINDOW,
        )
        if on_process:
            on_process(proc)
        # IMPORTANT: always drain stdout/stderr while the child is running.
        # The old poll()-then-communicate() loop could deadlock when commands such
        # as `adb shell find` produced more data than the OS pipe buffer.  This is
        # common for phone folders containing thousands of photos/videos.
        start = time.monotonic()
        stdout = ""
        stderr = ""
        try:
            while True:
                try:
                    stdout, stderr = proc.communicate(timeout=0.25)
                    break
                except subprocess.TimeoutExpired:
                    if cancel_event and cancel_event.is_set():
                        proc.terminate()
                        try:
                            stdout, stderr = proc.communicate(timeout=2)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                            stdout, stderr = proc.communicate()
                        raise AdbError("عملیات توسط کاربر متوقف شد.")
                    if timeout is not None and time.monotonic() - start > timeout:
                        proc.kill()
                        stdout, stderr = proc.communicate()
                        raise AdbError(f"ADB timeout after {timeout:g}s: {' '.join(args)}")
        finally:
            if on_process:
                on_process(None)  # type: ignore[arg-type]

        result = subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)
        if check and proc.returncode != 0:
            message = (stderr or stdout or "ADB command failed").strip()
            raise AdbError(message)
        return result

    def list_devices(self) -> list[Device]:
        result = self.run(["devices", "-l"], timeout=10)
        devices: list[Device] = []
        for raw in result.stdout.splitlines()[1:]:
            line = raw.strip()
            if not line:
                continue
            parts = line.split(maxsplit=2)
            serial = parts[0]
            state = parts[1] if len(parts) > 1 else "unknown"
            details = parts[2] if len(parts) > 2 else ""
            devices.append(Device(serial, state, details))
        return devices

    def ensure_ready(self, serial: str) -> None:
        devices = {d.serial: d for d in self.list_devices()}
        device = devices.get(serial)
        if not device:
            raise DeviceUnavailable("گوشی در ADB دیده نمی‌شود. کابل/USB debugging را بررسی کنید.")
        if device.state == "unauthorized":
            raise DeviceUnavailable("گوشی Unauthorized است. پیام RSA روی گوشی را Allow کنید.")
        if device.state != "device":
            raise DeviceUnavailable(f"وضعیت گوشی آماده نیست: {device.state}")

    def shell(self, command: str, *, serial: str, timeout: float | None = 30, cancel_event: Event | None = None) -> str:
        return self.run(["shell", command], serial=serial, timeout=timeout, cancel_event=cancel_event).stdout

    def list_files(self, remote_root: str, *, serial: str, cancel_event: Event | None = None) -> list[str]:
        root_q = shlex.quote(remote_root.rstrip("/"))
        command = f"find {root_q} -type f 2>/dev/null"
        out = self.shell(command, serial=serial, timeout=None, cancel_event=cancel_event)
        files = [line.rstrip("\r") for line in out.splitlines() if line.strip()]
        if not files:
            probe = self.shell(f"if [ -d {root_q} ]; then echo OK; else echo MISSING; fi", serial=serial)
            if "MISSING" in probe:
                raise AdbError(f"پوشه روی گوشی پیدا نشد: {remote_root}")
        return files

    def file_size(self, remote_path: str, *, serial: str, cancel_event: Event | None = None) -> int:
        q = shlex.quote(remote_path)
        command = f"stat -c %s {q} 2>/dev/null || toybox stat -c %s {q} 2>/dev/null"
        out = self.shell(command, serial=serial, timeout=20, cancel_event=cancel_event).strip()
        try:
            return int(out.splitlines()[-1])
        except (ValueError, IndexError) as exc:
            raise AdbError(f"اندازه فایل خوانده نشد: {remote_path}") from exc

    def pull(
        self,
        remote_path: str,
        local_path: str | Path,
        *,
        serial: str,
        cancel_event: Event | None = None,
        on_process: Optional[Callable[[subprocess.Popen | None], None]] = None,
    ) -> str:
        result = self.run(
            ["pull", remote_path, str(local_path)],
            serial=serial,
            timeout=None,
            cancel_event=cancel_event,
            on_process=on_process,
        )
        return (result.stdout + "\n" + result.stderr).strip()

    def delete_file(self, remote_path: str, *, serial: str, cancel_event: Event | None = None) -> None:
        q = shlex.quote(remote_path)
        self.shell(f"rm -f {q}", serial=serial, timeout=20, cancel_event=cancel_event)
