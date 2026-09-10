# Changelog

## v0.2.2 — 2026-09-10

- Fixed a potential deadlock while scanning folders containing thousands of files by consuming ADB process output continuously.
- Kept transfer engine behavior unchanged: Copy, Resume, Move-after-verify, retries, and disconnect handling.
- Confirmed the existing five transfer tests still pass.

## v0.2.1

- Replaced the PySide6 GUI with Python's built-in tkinter GUI.
- Removed runtime dependency on PyPI/internet access.

## v0.2.0

- Added multi-stage ADB auto-discovery.
- Added remembered ADB path support.
- Added manual adb.exe selection as fallback.

## v0.1.0

- Initial ADB-based transfer engine.
- Copy and Move-after-verify modes.
- SQLite resume ledger.
- Basic Windows GUI and diagnostics.
