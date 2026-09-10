from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "PhonePhotoTransfer"
APP_VERSION = "0.2.2"
PRESETS = [
    "/sdcard/DCIM/Camera",
    "/sdcard/Pictures",
    "/sdcard/Download",
    "/sdcard/Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Images",
    "/sdcard/Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Video",
]

def app_data_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    p = Path(base) / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p
