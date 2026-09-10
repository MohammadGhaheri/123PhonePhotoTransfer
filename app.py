from __future__ import annotations

try:
    import tkinter as tk
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Tkinter is not available in this Python installation. "
        "Install a standard Python.org Windows build with Tcl/Tk support."
    ) from exc

from ui_main import MainWindow


def main() -> None:
    root = tk.Tk()
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
