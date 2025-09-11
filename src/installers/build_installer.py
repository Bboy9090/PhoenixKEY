"""
BootForge Installer Builder
Cross-platform installer creation script
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path


def build_executable():
    """Build standalone executable with PyInstaller"""
    print("Building BootForge executable...")
    
    # PyInstaller command
    cmd = [
        'pyinstaller',
        '--onefile',
        '--name=BootForge',
        '--add-data=src:src',
        '--hidden-import=src.core',
        '--hidden-import=src.plugins',
        '--hidden-import=src.cli',
        '--console',  # Console application
        'main.py'
    ]
    
    # Add GUI support if available
    try:
        import PyQt6
        cmd.extend([
            '--hidden-import=PyQt6.QtWidgets',
            '--hidden-import=PyQt6.QtCore',
            '--hidden-import=PyQt6.QtGui',
            '--hidden-import=src.gui'
        ])
    except ImportError:
        print("PyQt6 not available - building CLI-only version")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Executable built successfully")
        return True
    else:
        print(f"❌ Build failed: {result.stderr}")
        return False


def create_windows_installer():
    """Create Windows installer with Inno Setup"""
    print("Creating Windows installer...")
    
    # Inno Setup script
    iss_content = """
[Setup]
AppName=BootForge
AppVersion=1.0.0
AppPublisher=BootForge Team
AppPublisherURL=https://bootforge.dev
DefaultDirName={pf}\\BootForge
DefaultGroupName=BootForge
UninstallDisplayIcon={app}\\BootForge.exe
Compression=lzma2
SolidCompression=yes
OutputDir=dist\\windows
OutputBaseFilename=BootForge-Setup

[Files]
Source: "dist\\BootForge.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "docs\\*"; DestDir: "{app}\\docs"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\\BootForge"; Filename: "{app}\\BootForge.exe"
Name: "{group}\\Uninstall BootForge"; Filename: "{uninstallexe}"
Name: "{commondesktop}\\BootForge"; Filename: "{app}\\BootForge.exe"; Tasks: desktopicon

[Tasks]
Name: desktopicon; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\\BootForge.exe"; Description: "Launch BootForge"; Flags: nowait postinstall skipifsilent
"""
    
    # Write Inno Setup script
    iss_file = Path("BootForge.iss")
    iss_file.write_text(iss_content)
    
    # Run Inno Setup compiler
    try:
        result = subprocess.run(['iscc', 'BootForge.iss'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Windows installer created")
            return True
        else:
            print(f"❌ Installer creation failed: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ Inno Setup not found - install from https://jrsoftware.org/isinfo.php")
        return False


def create_macos_installer():
    """Create macOS installer"""
    print("Creating macOS installer...")
    
    app_name = "BootForge.app"
    app_dir = Path("dist/macos") / app_name
    
    # Create app bundle structure
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "Contents").mkdir(exist_ok=True)
    (app_dir / "Contents/MacOS").mkdir(exist_ok=True)
    (app_dir / "Contents/Resources").mkdir(exist_ok=True)
    
    # Copy executable
    shutil.copy2("dist/BootForge", app_dir / "Contents/MacOS/BootForge")
    
    # Create Info.plist
    plist_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>BootForge</string>
    <key>CFBundleIdentifier</key>
    <string>dev.bootforge.BootForge</string>
    <key>CFBundleName</key>
    <string>BootForge</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
</dict>
</plist>"""
    
    (app_dir / "Contents/Info.plist").write_text(plist_content)
    
    # Create DMG
    try:
        result = subprocess.run([
            'hdiutil', 'create', '-volname', 'BootForge',
            '-srcfolder', str(app_dir.parent),
            '-ov', '-format', 'UDZO',
            'dist/BootForge-1.0.0.dmg'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ macOS DMG created")
            return True
        else:
            print(f"❌ DMG creation failed: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ hdiutil not found - macOS required for DMG creation")
        return False


def create_linux_package():
    """Create Linux package (AppImage)"""
    print("Creating Linux package...")
    
    # Create AppDir structure
    appdir = Path("dist/linux/BootForge.AppDir")
    appdir.mkdir(parents=True, exist_ok=True)
    
    # Copy executable
    shutil.copy2("dist/BootForge", appdir / "BootForge")
    
    # Create desktop file
    desktop_content = """[Desktop Entry]
Type=Application
Name=BootForge
Comment=Professional OS Deployment Tool
Exec=BootForge
Icon=bootforge
Categories=System;
"""
    
    (appdir / "BootForge.desktop").write_text(desktop_content)
    
    # Create AppRun script
    apprun_content = """#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
exec "${HERE}/BootForge" "$@"
"""
    
    apprun_file = appdir / "AppRun"
    apprun_file.write_text(apprun_content)
    apprun_file.chmod(0o755)
    
    # Try to create AppImage
    try:
        result = subprocess.run([
            'appimagetool', str(appdir), 'dist/BootForge-1.0.0-x86_64.AppImage'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Linux AppImage created")
            return True
        else:
            print(f"❌ AppImage creation failed: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ appimagetool not found - install AppImageKit")
        return False


def main():
    """Main installer build function"""
    print("BootForge Installer Builder")
    print("=" * 40)
    
    # Create dist directory
    Path("dist").mkdir(exist_ok=True)
    
    # Build executable
    if not build_executable():
        print("❌ Failed to build executable")
        return False
    
    # Create platform-specific installers
    system = platform.system()
    
    if system == "Windows":
        create_windows_installer()
    elif system == "Darwin":
        create_macos_installer()
    elif system == "Linux":
        create_linux_package()
    else:
        print(f"Unsupported platform: {system}")
    
    print()
    print("Build completed!")
    print("Installers available in dist/ directory")


if __name__ == "__main__":
    main()