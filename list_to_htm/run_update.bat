@echo off
cd /d "%~dp0"
echo ========================================
echo   Updating list.HTM from data.txt
echo   (Original file will be overwritten)
echo ========================================
echo.
python update_htm.py
echo.
echo ========================================
pause
