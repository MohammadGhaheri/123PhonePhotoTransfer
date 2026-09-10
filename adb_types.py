from __future__ import annotations

import os
from dataclasses import dataclass

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

class AdbError(RuntimeError):
    pass

class DeviceUnavailable(AdbError):
    """Raised when the selected Android device is disconnected/offline/unauthorized."""
    pass

@dataclass(frozen=True)
class Device:
    serial: str
    state: str
    details: str = ""
