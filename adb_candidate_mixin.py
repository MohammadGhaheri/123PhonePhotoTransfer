from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from adb_types import CREATE_NO_WINDOW


class ADBCandidateMixin:
    @staticmethod
    def _app_dir() -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return Path(__file__).resolve().parent

    @staticmethod
    def _exe_name() -> str:
        return "adb.exe" if os.name == "nt" else "adb"

    @classmethod
    def _normalise_candidate(cls, path: str | Path) -> Path:
        p = Path(os.path.expandvars(os.path.expanduser(str(path).strip().strip('"'))))
        exe = cls._exe_name()
        # A path ending in a directory may be an SDK root or platform-tools directory.
        if p.name.lower() == "platform-tools":
            p = p / exe
        elif p.suffix == "" and p.name.lower() != exe.lower():
            if p.name.lower() in {"sdk", "android-sdk", "androidsdk"}:
                p = p / "platform-tools" / exe
            elif p.is_dir():
                direct = p / exe
                sdk = p / "platform-tools" / exe
                p = direct if direct.is_file() else sdk
        return p

    @classmethod
    def _is_working_adb(cls, path: Path) -> bool:
        try:
            if not path.is_file():
                return False
            result = subprocess.run(
                [str(path), "version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=4,
                creationflags=CREATE_NO_WINDOW,
            )
            text = (result.stdout + "\n" + result.stderr).lower()
            return result.returncode == 0 and "android debug bridge" in text
        except (OSError, subprocess.SubprocessError):
            return False

    @classmethod
    def _exact_candidates(cls) -> list[tuple[Path, str]]:
        """Likely exact locations in priority order."""
        exe = cls._exe_name()
        app_dir = cls._app_dir()
        candidates: list[tuple[Path, str]] = []
        seen: set[str] = set()

        def add(path: str | Path | None, method: str) -> None:
            if not path:
                return
            p = cls._normalise_candidate(path)
            key = os.path.normcase(os.path.abspath(str(p)))
            if key not in seen:
                seen.add(key)
                candidates.append((p, method))

        # Explicit override and the previously remembered path beside a portable build.
        add(os.environ.get("ADB_PATH"), "ADB_PATH")
        config_file = app_dir / "adb_path.txt"
        if config_file.is_file():
            try:
                add(config_file.read_text(encoding="utf-8-sig").strip(), "adb_path.txt")
            except OSError:
                pass

        # Portable layouts beside source/EXE.
        add(app_dir / "platform-tools" / exe, "bundled platform-tools")
        add(app_dir / exe, "beside application")

        # PATH: shutil.which plus Windows where.exe. where.exe is useful when Python was
        # launched from a GUI whose PATH handling differs from a developer shell.
        which = shutil.which("adb") or shutil.which(exe)
        add(which, "PATH")
        if os.name == "nt":
            try:
                result = subprocess.run(
                    ["where.exe", "adb.exe"],
                    capture_output=True,
                    text=True,
                    timeout=4,
                    creationflags=CREATE_NO_WINDOW,
                )
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        add(line.strip(), "where.exe")
            except (OSError, subprocess.SubprocessError):
                pass

        # Android SDK environment variables used by Android Studio/Gradle/CLI tools.
        for var in ("ANDROID_SDK_ROOT", "ANDROID_HOME"):
            root = os.environ.get(var)
            if root:
                add(Path(root) / "platform-tools" / exe, var)

        local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        roaming = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        profile = Path(os.environ.get("USERPROFILE", Path.home()))
        pf = Path(os.environ.get("ProgramFiles", "C:/Program Files"))
        pfx86 = Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
        pdata = Path(os.environ.get("ProgramData", "C:/ProgramData"))

        common = [
            (local / "Android" / "Sdk" / "platform-tools" / exe, "Android Studio SDK"),
            (profile / "AppData" / "Local" / "Android" / "Sdk" / "platform-tools" / exe, "Android Studio SDK"),
            (profile / "platform-tools" / exe, "user platform-tools"),
            (profile / "Android" / "Sdk" / "platform-tools" / exe, "user Android SDK"),
            (profile / "scoop" / "apps" / "adb" / "current" / exe, "Scoop adb"),
            (profile / "scoop" / "apps" / "android-platform-tools" / "current" / exe, "Scoop platform-tools"),
            (pdata / "chocolatey" / "bin" / exe, "Chocolatey"),
            (pdata / "chocolatey" / "lib" / "adb" / "tools" / exe, "Chocolatey adb"),
            (pdata / "chocolatey" / "lib" / "android-sdk" / "tools" / "platform-tools" / exe, "Chocolatey Android SDK"),
            (pf / "Android" / "android-sdk" / "platform-tools" / exe, "Program Files Android SDK"),
            (pfx86 / "Android" / "android-sdk" / "platform-tools" / exe, "Program Files x86 Android SDK"),
            (pf / "Microsoft" / "AndroidSDK" / "25" / "platform-tools" / exe, "Microsoft Android SDK"),
            (pfx86 / "Microsoft" / "AndroidSDK" / "25" / "platform-tools" / exe, "Microsoft Android SDK"),
            (Path("C:/platform-tools") / exe, "C:\\platform-tools"),
            (Path("C:/Android/platform-tools") / exe, "C:\\Android"),
            (Path("C:/Android/Sdk/platform-tools") / exe, "C:\\Android SDK"),
        ]
        for p, method in common:
            add(p, method)

        # Some developer tools keep their own SDK/tool cache under Local/Roaming.
        # Exact guesses here are cheap; bounded recursive discovery below handles the rest.
        add(roaming / "Android" / "Sdk" / "platform-tools" / exe, "Roaming Android SDK")
        return candidates
