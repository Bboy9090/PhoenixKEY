#!/usr/bin/env python3
"""
BootForge Cross-Platform Build Script
Builds executables for Linux, Windows, and macOS
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command with error handling"""
    print(f"🔨 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Error: {result.stderr}")
            return False
        print(f"✅ Success: {description}")
        return True
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def build_linux():
    """Build Linux executable"""
    cmd = """pyinstaller --onefile --name=BootForge-Linux-x64 \
        --add-data="src:src" \
        --hidden-import=PyQt6.QtWidgets \
        --hidden-import=PyQt6.QtCore \
        --hidden-import=PyQt6.QtGui \
        --hidden-import=src.gui.main_window \
        --hidden-import=src.core.config \
        --hidden-import=src.core.logger \
        --clean main.py"""
    
    return run_command(cmd, "Building Linux executable")

def prepare_windows_build():
    """Prepare Windows build configuration"""
    # Create Windows-specific spec file
    spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('src', 'src')],
    hiddenimports=[
        'PyQt6.QtWidgets',
        'PyQt6.QtCore', 
        'PyQt6.QtGui',
        'src.gui.main_window',
        'src.core.config',
        'src.core.logger',
        'click',
        'colorama',
        'psutil',
        'cryptography'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='BootForge-Windows-x64',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if os.path.exists('assets/icon.ico') else None,
)
'''
    
    with open('BootForge-Windows.spec', 'w') as f:
        f.write(spec_content)
    print("✅ Windows build spec created")
    return True

def prepare_macos_build():
    """Prepare macOS build configuration"""
    # Create macOS-specific spec file
    spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('src', 'src')],
    hiddenimports=[
        'PyQt6.QtWidgets',
        'PyQt6.QtCore', 
        'PyQt6.QtGui',
        'src.gui.main_window',
        'src.core.config',
        'src.core.logger',
        'click',
        'colorama',
        'psutil',
        'cryptography'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='BootForge-macOS-x64',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

app = BUNDLE(
    exe,
    name='BootForge.app',
    icon='assets/icon.icns' if os.path.exists('assets/icon.icns') else None,
    bundle_identifier='com.bootforge.app',
    version='1.0.0',
)
'''
    
    with open('BootForge-macOS.spec', 'w') as f:
        f.write(spec_content)
    print("✅ macOS build spec created")
    return True

def create_usb_installer():
    """Create USB distribution package"""
    usb_content = '''#!/bin/bash
# BootForge USB Installer Script

echo "🚀 BootForge USB Installer"
echo "========================="

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="linux"
    EXECUTABLE="BootForge-Linux-x64"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macos"
    EXECUTABLE="BootForge.app"
elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]]; then
    PLATFORM="windows"
    EXECUTABLE="BootForge-Windows-x64.exe"
else
    echo "❌ Unsupported platform: $OSTYPE"
    exit 1
fi

echo "📱 Detected platform: $PLATFORM"

# Create install directory
INSTALL_DIR="$HOME/BootForge"
mkdir -p "$INSTALL_DIR"

# Copy executable
if [ -f "./$EXECUTABLE" ]; then
    cp "./$EXECUTABLE" "$INSTALL_DIR/"
    chmod +x "$INSTALL_DIR/$EXECUTABLE"
    echo "✅ BootForge installed to $INSTALL_DIR"
    
    # Create desktop shortcut (Linux)
    if [[ "$PLATFORM" == "linux" ]]; then
        cat > "$HOME/Desktop/BootForge.desktop" << EOF
[Desktop Entry]
Name=BootForge
Comment=Professional OS Deployment Tool
Exec=$INSTALL_DIR/$EXECUTABLE --gui
Icon=applications-system
Terminal=false
Type=Application
Categories=System;
EOF
        chmod +x "$HOME/Desktop/BootForge.desktop"
        echo "✅ Desktop shortcut created"
    fi
    
    echo ""
    echo "🎉 Installation complete!"
    echo "Run: $INSTALL_DIR/$EXECUTABLE --gui"
    echo ""
else
    echo "❌ Executable not found: $EXECUTABLE"
    exit 1
fi
'''
    
    with open('usb-installer.sh', 'w') as f:
        f.write(usb_content)
    
    # Create Windows installer
    windows_installer = '''@echo off
echo 🚀 BootForge USB Installer for Windows
echo ====================================

set "INSTALL_DIR=%USERPROFILE%\\BootForge"
mkdir "%INSTALL_DIR%" 2>nul

if exist "BootForge-Windows-x64.exe" (
    copy "BootForge-Windows-x64.exe" "%INSTALL_DIR%\\" >nul
    echo ✅ BootForge installed to %INSTALL_DIR%
    
    REM Create desktop shortcut
    echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\\CreateShortcut.vbs"
    echo sLinkFile = "%USERPROFILE%\\Desktop\\BootForge.lnk" >> "%TEMP%\\CreateShortcut.vbs"
    echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\\CreateShortcut.vbs"
    echo oLink.TargetPath = "%INSTALL_DIR%\\BootForge-Windows-x64.exe" >> "%TEMP%\\CreateShortcut.vbs"
    echo oLink.Arguments = "--gui" >> "%TEMP%\\CreateShortcut.vbs"
    echo oLink.Description = "BootForge Professional OS Deployment Tool" >> "%TEMP%\\CreateShortcut.vbs"
    echo oLink.Save >> "%TEMP%\\CreateShortcut.vbs"
    cscript /nologo "%TEMP%\\CreateShortcut.vbs"
    del "%TEMP%\\CreateShortcut.vbs"
    
    echo ✅ Desktop shortcut created
    echo.
    echo 🎉 Installation complete!
    echo Run: "%INSTALL_DIR%\\BootForge-Windows-x64.exe" --gui
    echo.
    pause
) else (
    echo ❌ Executable not found: BootForge-Windows-x64.exe
    pause
    exit /b 1
)
'''
    
    with open('usb-installer.bat', 'w') as f:
        f.write(windows_installer)
    
    print("✅ USB installer scripts created")
    return True

def main():
    """Main build process"""
    print("🏗️ BootForge Cross-Platform Build System")
    print("=========================================")
    
    # Create dist directory
    os.makedirs('dist', exist_ok=True)
    
    # Build for current platform (Linux)
    print("\n📱 Building for Linux...")
    if not build_linux():
        print("❌ Linux build failed")
        return False
    
    # Prepare cross-platform specs
    print("\n🪟 Preparing Windows build configuration...")
    prepare_windows_build()
    
    print("\n🍎 Preparing macOS build configuration...")  
    prepare_macos_build()
    
    # Create USB installers
    print("\n💾 Creating USB installer scripts...")
    create_usb_installer()
    
    print(f"\n✅ Build process complete!")
    print(f"📁 Files created in: {os.path.abspath('dist')}")
    print(f"📦 Linux executable: dist/BootForge-Linux-x64 ({os.path.getsize('dist/BootForge-Linux-x64') / 1024 / 1024:.1f} MB)")
    
    print(f"\n📋 Next steps:")
    print(f"   • Linux: Ready for distribution")
    print(f"   • Windows: Run build on Windows system with: pyinstaller BootForge-Windows.spec")  
    print(f"   • macOS: Run build on Mac system with: pyinstaller BootForge-macOS.spec")
    print(f"   • USB: Copy executables + installer scripts to USB drive")
    
    return True

if __name__ == '__main__':
    main()