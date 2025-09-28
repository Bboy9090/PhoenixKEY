#!/usr/bin/env python3
"""
BootForge Package Builder
Creates downloadable packages for Windows (.exe), macOS (.dmg), and Linux (.AppImage)
"""

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path
import zipfile
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PackageBuilder:
    """Builds BootForge packages for all platforms"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.dist_dir = self.project_root / "dist"
        self.build_dir = self.project_root / "build"
        self.current_platform = platform.system().lower()
        
        # Package configurations
        self.app_name = "BootForge"
        self.app_version = "1.0.0"
        self.app_author = "BootForge Team"
        self.app_description = "Professional Cross-Platform OS Deployment Tool"
        
        logger.info(f"Package Builder initialized for {self.current_platform}")
    
    def clean_build_dirs(self):
        """Clean build and dist directories"""
        for dir_path in [self.dist_dir, self.build_dir]:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                logger.info(f"Cleaned {dir_path}")
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def build_executable(self):
        """Build standalone executable using PyInstaller"""
        logger.info("Building standalone executable...")
        
        # Platform-specific separator for --add-data
        separator = ";" if self.current_platform == "windows" else ":"
        
        # PyInstaller command - all options before the script name
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--name", self.app_name,
            "--onedir",  # Create a directory with all dependencies
            "--windowed",  # No console window (GUI app)
            f"--add-data", f"src{separator}src",  # Include source directory
            "--hidden-import", "PyQt6.QtCore",
            "--hidden-import", "PyQt6.QtWidgets", 
            "--hidden-import", "PyQt6.QtGui",
            "--hidden-import", "psutil",
            "--hidden-import", "requests",
            "--hidden-import", "cryptography",
            "--collect-all", "PyQt6"
        ]
        
        # Add icon if it exists (before script name)
        if Path("assets/icon.ico").exists():
            cmd.extend(["--icon", "assets/icon.ico"])
            
        # Add assets if they exist (before script name)
        if Path("assets").exists():
            cmd.extend(["--add-data", f"assets{separator}assets"])
        
        # Script name must be last
        cmd.append("main.py")
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info("Executable built successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to build executable: {e}")
            logger.error(f"Output: {e.stdout}")
            logger.error(f"Error: {e.stderr}")
            return False
    
    def create_windows_installer(self):
        """Create Windows installer (.exe)"""
        if self.current_platform != "windows":
            logger.info("Skipping Windows installer (not on Windows)")
            return True
        
        logger.info("Creating Windows installer...")
        
        # Create NSIS installer script
        nsis_script = self.build_dir / "installer.nsi"
        with open(nsis_script, 'w') as f:
            f.write(f'''
; BootForge Windows Installer
!define APP_NAME "{self.app_name}"
!define APP_VERSION "{self.app_version}"
!define APP_PUBLISHER "{self.app_author}"
!define APP_DESCRIPTION "{self.app_description}"

Name "${{APP_NAME}} ${{APP_VERSION}}"
OutFile "..\\dist\\{self.app_name}-{self.app_version}-Windows-Setup.exe"
InstallDir "$PROGRAMFILES\\${{APP_NAME}}"
RequestExecutionLevel admin

Page components
Page directory
Page instfiles

Section "BootForge Application" SecApp
  SetOutPath "$INSTDIR"
  File /r "dist\\{self.app_name}\\*"
  
  ; Create desktop shortcut
  CreateShortCut "$DESKTOP\\{self.app_name}.lnk" "$INSTDIR\\{self.app_name}.exe"
  
  ; Create start menu shortcut
  CreateDirectory "$SMPROGRAMS\\{self.app_name}"
  CreateShortCut "$SMPROGRAMS\\{self.app_name}\\{self.app_name}.lnk" "$INSTDIR\\{self.app_name}.exe"
  CreateShortCut "$SMPROGRAMS\\{self.app_name}\\Uninstall.lnk" "$INSTDIR\\uninstall.exe"
  
  ; Write uninstaller
  WriteUninstaller "$INSTDIR\\uninstall.exe"
  
  ; Registry entries
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{self.app_name}" "DisplayName" "{self.app_name}"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{self.app_name}" "UninstallString" "$INSTDIR\\uninstall.exe"
SectionEnd

Section "Uninstall"
  Delete "$INSTDIR\\*"
  RMDir /r "$INSTDIR"
  Delete "$DESKTOP\\{self.app_name}.lnk"
  RMDir /r "$SMPROGRAMS\\{self.app_name}"
  DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{self.app_name}"
SectionEnd
''')
        
        # Run NSIS (if available)
        try:
            subprocess.run(["makensis", str(nsis_script)], check=True)
            logger.info("Windows installer created successfully")
            return True
        except FileNotFoundError:
            logger.warning("NSIS not found - creating simple ZIP package instead")
            return self.create_zip_package("Windows")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create Windows installer: {e}")
            return False
    
    def create_macos_app(self):
        """Create macOS application bundle (.app)"""
        if self.current_platform != "darwin":
            logger.info("Skipping macOS app (not on macOS)")
            return True
        
        logger.info("Creating macOS application bundle...")
        
        app_bundle = self.dist_dir / f"{self.app_name}.app"
        contents_dir = app_bundle / "Contents"
        macos_dir = contents_dir / "MacOS"
        resources_dir = contents_dir / "Resources"
        
        # Create directory structure
        for dir_path in [macos_dir, resources_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Copy executable
        exe_path = self.dist_dir / self.app_name / f"{self.app_name}"
        if exe_path.exists():
            shutil.copy2(exe_path, macos_dir / self.app_name)
            os.chmod(macos_dir / self.app_name, 0o755)
        
        # Copy resources
        src_resources = self.dist_dir / self.app_name
        if src_resources.exists():
            for item in src_resources.iterdir():
                if item.name != self.app_name:  # Don't copy the executable again
                    if item.is_dir():
                        shutil.copytree(item, resources_dir / item.name, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, resources_dir)
        
        # Create Info.plist
        plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>{self.app_name}</string>
    <key>CFBundleDisplayName</key>
    <string>{self.app_name}</string>
    <key>CFBundleIdentifier</key>
    <string>com.bootforge.{self.app_name.lower()}</string>
    <key>CFBundleVersion</key>
    <string>{self.app_version}</string>
    <key>CFBundleShortVersionString</key>
    <string>{self.app_version}</string>
    <key>CFBundleExecutable</key>
    <string>{self.app_name}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
</dict>
</plist>'''
        
        with open(contents_dir / "Info.plist", 'w') as f:
            f.write(plist_content)
        
        logger.info("macOS app bundle created successfully")
        return True
    
    def create_macos_dmg(self):
        """Create macOS disk image (.dmg)"""
        if self.current_platform != "darwin":
            logger.info("Skipping macOS DMG (not on macOS)")
            return True
        
        logger.info("Creating macOS disk image...")
        
        app_bundle = self.dist_dir / f"{self.app_name}.app"
        dmg_path = self.dist_dir / f"{self.app_name}-{self.app_version}-macOS.dmg"
        
        if not app_bundle.exists():
            logger.error("App bundle not found - cannot create DMG")
            return False
        
        try:
            # Create DMG
            cmd = [
                "hdiutil", "create",
                "-volname", f"{self.app_name} {self.app_version}",
                "-srcfolder", str(app_bundle),
                "-format", "UDZO",
                "-compression", "9",
                str(dmg_path)
            ]
            
            subprocess.run(cmd, check=True)
            logger.info("macOS disk image created successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create DMG: {e}")
            return False
    
    def create_linux_appimage(self):
        """Create Linux AppImage"""
        if self.current_platform != "linux":
            logger.info("Skipping Linux AppImage (not on Linux)")
            return True
        
        logger.info("Creating Linux AppImage...")
        
        # Create AppDir structure
        appdir = self.build_dir / f"{self.app_name}.AppDir"
        appdir.mkdir(exist_ok=True)
        
        # Copy application files
        app_src = self.dist_dir / self.app_name
        if app_src.exists():
            shutil.copytree(app_src, appdir / "usr" / "bin", dirs_exist_ok=True)
        
        # Create .desktop file
        desktop_content = f'''[Desktop Entry]
Type=Application
Name={self.app_name}
Comment={self.app_description}
Exec={self.app_name}
Icon={self.app_name.lower()}
Categories=System;Utility;
Terminal=false
'''
        
        with open(appdir / f"{self.app_name}.desktop", 'w') as f:
            f.write(desktop_content)
        
        # Create AppRun script
        apprun_content = f'''#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${{SELF%/*}}
export PATH="${{HERE}}/usr/bin:${{PATH}}"
export LD_LIBRARY_PATH="${{HERE}}/usr/lib:${{LD_LIBRARY_PATH}}"
exec "${{HERE}}/usr/bin/{self.app_name}" "$@"
'''
        
        apprun_path = appdir / "AppRun"
        with open(apprun_path, 'w') as f:
            f.write(apprun_content)
        os.chmod(apprun_path, 0o755)
        
        # Download and use appimagetool
        try:
            appimage_path = self.dist_dir / f"{self.app_name}-{self.app_version}-Linux.AppImage"
            
            # Try to use appimagetool if available
            subprocess.run([
                "appimagetool", str(appdir), str(appimage_path)
            ], check=True)
            
            logger.info("Linux AppImage created successfully")
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            logger.warning("appimagetool not found - creating tar.gz package instead")
            return self.create_tar_package("Linux")
    
    def create_zip_package(self, platform_name: str):
        """Create ZIP package as fallback"""
        logger.info(f"Creating ZIP package for {platform_name}...")
        
        zip_path = self.dist_dir / f"{self.app_name}-{self.app_version}-{platform_name}.zip"
        app_dir = self.dist_dir / self.app_name
        
        if not app_dir.exists():
            logger.error(f"Application directory not found: {app_dir}")
            return False
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in app_dir.rglob('*'):
                if file_path.is_file():
                    zf.write(file_path, file_path.relative_to(app_dir.parent))
        
        logger.info(f"ZIP package created: {zip_path}")
        return True
    
    def create_tar_package(self, platform_name: str):
        """Create tar.gz package as fallback"""
        logger.info(f"Creating tar.gz package for {platform_name}...")
        
        tar_path = self.dist_dir / f"{self.app_name}-{self.app_version}-{platform_name}.tar.gz"
        app_dir = self.dist_dir / self.app_name
        
        if not app_dir.exists():
            logger.error(f"Application directory not found: {app_dir}")
            return False
        
        import tarfile
        with tarfile.open(tar_path, 'w:gz') as tf:
            tf.add(app_dir, arcname=self.app_name)
        
        logger.info(f"tar.gz package created: {tar_path}")
        return True
    
    def create_readme(self):
        """Create README file for distribution"""
        readme_content = f'''# {self.app_name} v{self.app_version}

{self.app_description}

## Installation Instructions

### Windows
1. Download `{self.app_name}-{self.app_version}-Windows-Setup.exe`
2. Run the installer as Administrator
3. Follow the installation wizard
4. Launch from Desktop shortcut or Start Menu

### macOS  
1. Download `{self.app_name}-{self.app_version}-macOS.dmg`
2. Open the disk image
3. Drag {self.app_name}.app to Applications folder
4. Launch from Applications or Launchpad

### Linux
1. Download `{self.app_name}-{self.app_version}-Linux.AppImage`
2. Make executable: `chmod +x {self.app_name}-{self.app_version}-Linux.AppImage`
3. Run: `./{self.app_name}-{self.app_version}-Linux.AppImage`

## System Requirements

### Minimum Requirements
- RAM: 4GB (8GB recommended)
- Storage: 2GB free space
- USB port for target device creation
- Internet connection for OS downloads

### Supported Operating Systems
- Windows 10/11 (64-bit)
- macOS 10.15+ (Catalina or later)
- Linux distributions with GLIBC 2.27+

## Features

✅ **Multi-Layer Safety Pipeline** - Bulletproof device protection  
✅ **Real-Time Health Monitoring** - Continuous system monitoring  
✅ **Intelligent Guidance System** - Smart auto-detection & recommendations  
✅ **Error Prevention & Recovery** - Automatic rollback & smart retry  
✅ **One-Click Deployment Profiles** - 8 perfect profiles for any scenario  

## Support

For support, documentation, and updates, visit:
https://github.com/bootforge/bootforge

## License

Copyright © 2025 {self.app_author}. All rights reserved.
'''
        
        readme_path = self.dist_dir / "README.md"
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        
        logger.info("README.md created")
    
    def build_all(self):
        """Build packages for all platforms"""
        logger.info("Starting complete package build process...")
        
        # Clean build directories
        self.clean_build_dirs()
        
        # Build executable
        if not self.build_executable():
            logger.error("Failed to build executable - aborting")
            return False
        
        success_count = 0
        
        # Platform-specific packages
        if self.current_platform == "windows":
            if self.create_windows_installer():
                success_count += 1
        elif self.current_platform == "darwin":  # macOS
            if self.create_macos_app() and self.create_macos_dmg():
                success_count += 1
        elif self.current_platform == "linux":
            if self.create_linux_appimage():
                success_count += 1
        
        # Create universal ZIP for current platform
        platform_names = {
            "windows": "Windows",
            "darwin": "macOS", 
            "linux": "Linux"
        }
        
        platform_name = platform_names.get(self.current_platform, "Unknown")
        if self.create_zip_package(platform_name):
            success_count += 1
        
        # Create documentation
        self.create_readme()
        
        logger.info(f"Package build completed - {success_count} package(s) created")
        
        # List created packages
        logger.info("Created packages:")
        for package in self.dist_dir.glob(f"{self.app_name}-*"):
            logger.info(f"  📦 {package.name} ({package.stat().st_size / 1024 / 1024:.1f} MB)")
        
        return success_count > 0

def main():
    """Main entry point"""
    builder = PackageBuilder()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "clean":
            builder.clean_build_dirs()
            return
        elif command == "exe":
            builder.build_executable()
            return
        elif command == "readme":
            builder.create_readme()
            return
    
    # Build all packages
    success = builder.build_all()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()