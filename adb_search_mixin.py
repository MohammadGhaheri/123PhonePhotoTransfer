from __future__ import annotations

import os
import time
from pathlib import Path

from adb_types import AdbError


class ADBSearchMixin:
    @classmethod
    def _search_roots(cls) -> list[Path]:
        """Small, developer-oriented roots safe enough for bounded recursive search."""
        home = Path(os.environ.get("USERPROFILE", Path.home()))
        local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
        roaming = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        pf = Path(os.environ.get("ProgramFiles", "C:/Program Files"))
        pfx86 = Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
        roots = [
            local / "Android",
            local / "Programs",
            local / "Google",
            roaming / "Android",
            home / "Android",
            home / "platform-tools",
            home / "scoop" / "apps",
            pf / "Android",
            pfx86 / "Android",
            pf / "Microsoft" / "AndroidSDK",
            pfx86 / "Microsoft" / "AndroidSDK",
            Path("C:/Android"),
        ]
        # Also inspect the application and a couple of parent folders; useful for projects
        # that carry platform-tools in a sibling directory.
        app = cls._app_dir()
        roots.extend([app, app.parent])

        unique: list[Path] = []
        seen: set[str] = set()
        for root in roots:
            key = os.path.normcase(os.path.abspath(str(root)))
            if key not in seen and root.exists():
                seen.add(key)
                unique.append(root)
        return unique

    @classmethod
    def _bounded_recursive_search(cls, max_seconds: float = 7.0) -> tuple[Path, str] | None:
        """Find adb.exe in likely developer directories without crawling the whole disk."""
        exe_lower = cls._exe_name().lower()
        deadline = time.monotonic() + max_seconds
        skip_dirs = {
            "node_modules", ".git", "cache", "caches", "temp", "tmp", "packages",
            "windowsapps", "$recycle.bin", "system volume information",
        }

        for root in cls._search_roots():
            if time.monotonic() >= deadline:
                break
            try:
                for dirpath, dirnames, filenames in os.walk(root, topdown=True, onerror=lambda _e: None):
                    if time.monotonic() >= deadline:
                        return None
                    dirnames[:] = [d for d in dirnames if d.lower() not in skip_dirs]
                    # Avoid descending absurdly deep caches; adb normally sits near SDK/platform-tools.
                    try:
                        rel_depth = len(Path(dirpath).relative_to(root).parts)
                    except ValueError:
                        rel_depth = 0
                    if rel_depth >= 7:
                        dirnames[:] = []
                    if any(name.lower() == exe_lower for name in filenames):
                        candidate = Path(dirpath) / cls._exe_name()
                        if cls._is_working_adb(candidate):
                            return candidate.resolve(), f"auto-search ({root})"
            except OSError:
                continue
        return None

    @classmethod
    def discover_candidates(cls, include_recursive: bool = True) -> list[tuple[str, str, bool]]:
        """Diagnostic helper: return path, method, and whether the ADB executable works."""
        results: list[tuple[str, str, bool]] = []
        for path, method in cls._exact_candidates():
            results.append((str(path), method, cls._is_working_adb(path)))
        if include_recursive and not any(ok for _, _, ok in results):
            found = cls._bounded_recursive_search()
            if found:
                path, method = found
                results.append((str(path), method, True))
        return results

    @classmethod
    def _discover_adb(cls) -> tuple[Path, str]:
        candidates = cls._exact_candidates()
        for path, method in candidates:
            if cls._is_working_adb(path):
                return path.resolve(), method

        found = cls._bounded_recursive_search()
        if found:
            return found

        checked = "\n".join(f"  - {p} [{method}]" for p, method in candidates[:24])
        raise AdbError(
            "ADB به‌صورت خودکار پیدا نشد. PhonePhotoTransfer مسیرهای استاندارد Android SDK، "
            "PATH/where.exe و پوشه‌های محتمل توسعه را بررسی کرد. اگر ADB داخل یک مسیر غیرمعمول است، "
            "فقط یک‌بار آن را از داخل برنامه انتخاب کنید؛ مسیر برای اجراهای بعدی ذخیره می‌شود."
            + (f"\n\nمسیرهای مستقیم بررسی‌شده:\n{checked}" if checked else "")
        )
