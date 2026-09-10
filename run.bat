@echo off
setlocal
cd /d "%~dp0"
echo PhonePhotoTransfer v0.2.2
echo Starting with Python standard-library GUI. No pip install / internet required.
echo.
python app.py
if errorlevel 1 (
  echo.
  echo ERROR: PhonePhotoTransfer could not start.
  echo Run doctor.bat to verify ADB. If Python reports tkinter missing, install the standard Python.org Windows build with Tcl/Tk.
  pause
)
