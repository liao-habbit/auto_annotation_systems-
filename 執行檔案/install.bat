@echo off
cd /d "%~dp0.."
echo Installing packages...

python -m pip install -r requirements.txt

echo.
echo Installation finished.

pause