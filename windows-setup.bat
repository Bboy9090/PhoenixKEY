@echo off
REM BootForge Windows Setup Script
REM Run this after extracting the zip file

echo 🚀 Setting up BootForge on Windows...
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found. Please install Python 3:
    echo    Download from https://python.org
    echo    Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo ✅ Python found
python --version

echo.
echo 📦 Installing dependencies...
pip install click colorama cryptography pillow psutil pyyaml requests

echo.
echo ✅ BootForge CLI setup complete!
echo.
echo 🎯 Quick start commands:
echo    python main.py --help               # Show all commands
echo    python main.py list-devices         # List USB devices  
echo    python main.py list-plugins         # Show available plugins
echo.
echo 🔧 For disk operations, run Command Prompt as Administrator:
echo    python main.py write-image -i image.iso -d \\.\PhysicalDrive1
echo.
echo 💡 Run with --verbose for detailed logging
echo.
echo 🎉 Ready to use! Enjoy BootForge on Windows!
echo.
pause