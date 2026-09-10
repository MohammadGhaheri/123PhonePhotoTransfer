@echo off
setlocal
cd /d "%~dp0"
echo Building standalone Windows EXE...
echo PyInstaller is needed only for building the EXE, not for normal use.
python -m pip install -r requirements-build.txt
if errorlevel 1 goto :fail
python -m PyInstaller --noconfirm --clean --windowed --onedir --name PhonePhotoTransfer app.py
if errorlevel 1 goto :fail

echo.
echo Build complete: dist\PhonePhotoTransfer\PhonePhotoTransfer.exe
echo ADB is auto-detected. You may also copy platform-tools beside the EXE for a fully portable package.
pause
exit /b 0

:fail
echo.
echo Build failed. This does NOT affect running the Python version with run.bat.
pause
exit /b 1
