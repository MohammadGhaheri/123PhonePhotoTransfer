from __future__ import annotations

from pathlib import Path

from adb_candidate_mixin import ADBCandidateMixin
from adb_search_mixin import ADBSearchMixin
from adb_ops_mixin import ADBOpsMixin
from adb_types import AdbError, Device, DeviceUnavailable

__all__ = ["ADBManager", "AdbError", "DeviceUnavailable", "Device"]


class ADBManager(ADBCandidateMixin, ADBSearchMixin, ADBOpsMixin):
    """Locate and operate ADB without requiring it to be in Explorer/Python's PATH."""
    def __init__(self, adb_path: str | Path | None = None) -> None:
        if adb_path:
            chosen = self._normalise_candidate(adb_path)
            if not self._is_working_adb(chosen):
                raise AdbError(f"adb.exe در این مسیر پیدا نشد یا قابل اجرا نیست: {chosen}")
            self.adb_path = str(chosen.resolve())
            self.discovery_method = "configured"
        else:
            chosen, method = self._discover_adb()
            self.adb_path = str(chosen)
            self.discovery_method = method
