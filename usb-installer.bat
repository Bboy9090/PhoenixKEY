@echo off
echo 🚀 BootForge USB Installer for Windows
echo ====================================

set "INSTALL_DIR=%USERPROFILE%\BootForge"
mkdir "%INSTALL_DIR%" 2>nul

if exist "BootForge-Windows-x64.exe" (
    copy "BootForge-Windows-x64.exe" "%INSTALL_DIR%\" >nul
    echo ✅ BootForge installed to %INSTALL_DIR%
    
    REM Create desktop shortcut
    echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\CreateShortcut.vbs"
    echo sLinkFile = "%USERPROFILE%\Desktop\BootForge.lnk" >> "%TEMP%\CreateShortcut.vbs"
    echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\CreateShortcut.vbs"
    echo oLink.TargetPath = "%INSTALL_DIR%\BootForge-Windows-x64.exe" >> "%TEMP%\CreateShortcut.vbs"
    echo oLink.Arguments = "--gui" >> "%TEMP%\CreateShortcut.vbs"
    echo oLink.Description = "BootForge Professional OS Deployment Tool" >> "%TEMP%\CreateShortcut.vbs"
    echo oLink.Save >> "%TEMP%\CreateShortcut.vbs"
    cscript /nologo "%TEMP%\CreateShortcut.vbs"
    del "%TEMP%\CreateShortcut.vbs"
    
    echo ✅ Desktop shortcut created
    echo.
    echo 🎉 Installation complete!
    echo Run: "%INSTALL_DIR%\BootForge-Windows-x64.exe" --gui
    echo.
    pause
) else (
    echo ❌ Executable not found: BootForge-Windows-x64.exe
    pause
    exit /b 1
)