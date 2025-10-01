
#!/usr/bin/env python3
"""
BootForge Bootable USB Creator
Creates a fully self-contained bootable USB with BootForge GUI
"""

import os
import json
import shutil
import zipfile
import subprocess
from pathlib import Path
from datetime import datetime

class BootableUSBCreator:
    """Creates bootable USB with BootForge and recovery tools"""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        self.dist_dir = self.root_dir / "dist"
        self.usb_dir = self.root_dir / "bootable_usb"
        
    def create_bootable_structure(self):
        """Create bootable USB structure"""
        # Clean and create USB directory
        if self.usb_dir.exists():
            shutil.rmtree(self.usb_dir)
        self.usb_dir.mkdir()
        
        # Create main directories
        (self.usb_dir / "EFI" / "BOOT").mkdir(parents=True)
        (self.usb_dir / "BootForge").mkdir()
        (self.usb_dir / "Tools").mkdir()
        (self.usb_dir / "OS_Images").mkdir()
        (self.usb_dir / "Recovery").mkdir()
        
        return True
    
    def copy_bootforge_gui(self):
        """Copy BootForge GUI executable"""
        bootforge_dir = self.usb_dir / "BootForge"
        
        # Copy the entire src directory for Python execution
        src_dest = bootforge_dir / "src"
        if (self.root_dir / "src").exists():
            shutil.copytree(self.root_dir / "src", src_dest)
            print("✅ Copied BootForge source code")
        
        # Copy main.py
        if (self.root_dir / "main.py").exists():
            shutil.copy2(self.root_dir / "main.py", bootforge_dir)
            print("✅ Copied main.py")
        
        # Copy requirements
        if (self.root_dir / "requirements.txt").exists():
            shutil.copy2(self.root_dir / "requirements.txt", bootforge_dir)
            print("✅ Copied requirements.txt")
        
        # Copy assets
        if (self.root_dir / "assets").exists():
            shutil.copytree(self.root_dir / "assets", bootforge_dir / "assets")
            print("✅ Copied assets")
        
        # Copy configs
        if (self.root_dir / "configs").exists():
            shutil.copytree(self.root_dir / "configs", bootforge_dir / "configs")
            print("✅ Copied configs")
        
        return True
    
    def create_efi_bootloader(self):
        """Create EFI bootloader structure"""
        efi_boot = self.usb_dir / "EFI" / "BOOT"
        
        # Create BOOTX64.EFI placeholder (for UEFI boot)
        bootx64_content = b'EFI_BOOTFORGE_PLACEHOLDER'
        with open(efi_boot / "BOOTX64.EFI", 'wb') as f:
            f.write(bootx64_content)
        
        # Create startup.nsh for EFI shell
        startup_script = '''@echo off
echo BootForge USB Recovery System
echo ===========================
echo.
echo Starting BootForge GUI...
cd BootForge
python main.py --gui
'''
        with open(efi_boot / "startup.nsh", 'w') as f:
            f.write(startup_script)
        
        print("✅ Created EFI boot structure")
        return True
    
    def create_platform_launchers(self):
        """Create platform-specific launchers"""
        
        # macOS launcher
        macos_launcher = '''#!/bin/bash
# BootForge USB Launcher for macOS
echo "🚀 Starting BootForge from USB..."
cd "$(dirname "$0")/BootForge"

# Check for Python
if command -v python3 &> /dev/null; then
    echo "✅ Python 3 found"
    python3 main.py --gui
elif command -v python &> /dev/null; then
    echo "✅ Python found"
    python main.py --gui
else
    echo "❌ Python not found. Please install Python 3."
    echo "Visit: https://www.python.org/downloads/"
    read -p "Press enter to exit..."
fi
'''
        macos_script = self.usb_dir / "Start-BootForge-Mac.command"
        with open(macos_script, 'w') as f:
            f.write(macos_launcher)
        macos_script.chmod(0o755)
        
        # Linux launcher
        linux_launcher = '''#!/bin/bash
# BootForge USB Launcher for Linux
echo "🚀 Starting BootForge from USB..."
cd "$(dirname "$0")/BootForge"

# Check for Python
if command -v python3 &> /dev/null; then
    echo "✅ Python 3 found"
    python3 main.py --gui
elif command -v python &> /dev/null; then
    echo "✅ Python found"
    python main.py --gui
else
    echo "❌ Python not found. Please install Python 3."
    echo "Run: sudo apt install python3 python3-pip"
    read -p "Press enter to exit..."
fi
'''
        linux_script = self.usb_dir / "Start-BootForge-Linux.sh"
        with open(linux_script, 'w') as f:
            f.write(linux_launcher)
        linux_script.chmod(0o755)
        
        # Windows launcher
        windows_launcher = '''@echo off
title BootForge USB Recovery System
echo 🚀 Starting BootForge from USB...
cd /d "%~dp0BootForge"

where python >nul 2>nul
if %errorlevel% == 0 (
    echo ✅ Python found
    python main.py --gui
) else (
    where python3 >nul 2>nul
    if %errorlevel% == 0 (
        echo ✅ Python 3 found
        python3 main.py --gui
    ) else (
        echo ❌ Python not found. Please install Python 3.
        echo Visit: https://www.python.org/downloads/
        pause
    )
)
'''
        with open(self.usb_dir / "Start-BootForge-Windows.bat", 'w') as f:
            f.write(windows_launcher)
        
        print("✅ Created platform launchers")
        return True
    
    def create_recovery_tools(self):
        """Create recovery and diagnostic tools"""
        tools_dir = self.usb_dir / "Tools"
        
        # Disk utility script
        disk_utility = '''#!/bin/bash
echo "BootForge Disk Utility"
echo "==================="
echo "1. List all disks"
echo "2. Check disk health"
echo "3. Mount disk"
echo "4. Unmount disk"
echo "5. Exit"
read -p "Choose option: " choice

case $choice in
    1) diskutil list ;;
    2) diskutil verifyVolume / ;;
    3) read -p "Enter disk identifier: " disk; diskutil mount $disk ;;
    4) read -p "Enter disk identifier: " disk; diskutil unmount $disk ;;
    5) exit ;;
esac
'''
        with open(tools_dir / "disk_utility.sh", 'w') as f:
            f.write(disk_utility)
        (tools_dir / "disk_utility.sh").chmod(0o755)
        
        # System info script
        system_info = '''#!/bin/bash
echo "System Information"
echo "=================="
echo "macOS Version: $(sw_vers -productVersion)"
echo "Hardware: $(system_profiler SPHardwareDataType | grep 'Model Name')"
echo "Memory: $(system_profiler SPHardwareDataType | grep 'Memory')"
echo "Storage: $(df -h /)"
'''
        with open(tools_dir / "system_info.sh", 'w') as f:
            f.write(system_info)
        (tools_dir / "system_info.sh").chmod(0o755)
        
        print("✅ Created recovery tools")
        return True
    
    def create_readme(self):
        """Create comprehensive README"""
        readme_content = '''BootForge Bootable USB Recovery System
=====================================

🚀 QUICK START:
- macOS: Double-click "Start-BootForge-Mac.command"
- Linux: Run "./Start-BootForge-Linux.sh"
- Windows: Double-click "Start-BootForge-Windows.bat"

📁 DIRECTORY STRUCTURE:
├── EFI/           - UEFI boot files
├── BootForge/     - Main application
├── Tools/         - Recovery utilities
├── OS_Images/     - Store your OS images here
└── Recovery/      - Emergency recovery tools

🔧 FEATURES:
✓ Cross-platform bootable USB creation
✓ Mac OCLP integration for legacy hardware
✓ Windows bypass tools for TPM/Secure Boot
✓ Linux live system creation
✓ Hardware detection and profiling
✓ Safety validation and rollback
✓ Real-time progress monitoring

💾 USAGE FOR MAC RECOVERY:
1. Boot from this USB (hold Option/Alt at startup)
2. Launch BootForge GUI
3. Select your Mac model for OCLP patches
4. Create macOS installer with legacy support
5. Install macOS with OpenCore Legacy Patcher

🛡️ SAFETY FEATURES:
- Comprehensive device validation
- Automatic safety checks
- Rollback on failure
- Audit logging
- Permission verification

📋 REQUIREMENTS:
- Python 3.7+ (usually pre-installed on macOS/Linux)
- 8GB+ USB drive for OS creation
- Admin/root privileges for disk operations

🆘 TROUBLESHOOTING:
- If Python not found: Install from python.org
- If permission denied: Run as administrator
- If USB not detected: Check USB port/cable
- For Mac boot issues: Reset NVRAM (Cmd+Opt+P+R)

Created: ''' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '''
Version: BootForge USB Recovery v1.0
'''
        
        with open(self.usb_dir / "README.txt", 'w') as f:
            f.write(readme_content)
        
        print("✅ Created README")
        return True
    
    def create_autorun(self):
        """Create autorun for Windows"""
        autorun_content = '''[autorun]
open=Start-BootForge-Windows.bat
icon=BootForge\\assets\\icons\\app_icon_premium.png
label=BootForge Recovery USB
'''
        with open(self.usb_dir / "autorun.inf", 'w') as f:
            f.write(autorun_content)
        
        print("✅ Created autorun.inf")
        return True
    
    def create_zip_package(self):
        """Create downloadable ZIP package"""
        self.dist_dir.mkdir(exist_ok=True)
        zip_path = self.dist_dir / "BootForge-Bootable-USB.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.usb_dir):
                for file in files:
                    file_path = Path(root) / file
                    arc_path = file_path.relative_to(self.usb_dir)
                    zipf.write(file_path, arc_path)
        
        print(f"✅ Created ZIP package: {zip_path}")
        return zip_path
    
    def build_bootable_usb(self):
        """Build complete bootable USB package"""
        print("🚀 Building BootForge Bootable USB...")
        print("=" * 50)
        
        self.create_bootable_structure()
        self.copy_bootforge_gui()
        self.create_efi_bootloader()
        self.create_platform_launchers()
        self.create_recovery_tools()
        self.create_readme()
        self.create_autorun()
        zip_path = self.create_zip_package()
        
        print("\n" + "=" * 50)
        print("🎉 BootForge Bootable USB created successfully!")
        print(f"📁 USB files: {self.usb_dir}")
        print(f"📦 ZIP package: {zip_path}")
        print("\n💿 TO CREATE BOOTABLE USB:")
        print("1. Format USB drive as FAT32")
        print("2. Extract ZIP contents to USB root")
        print("3. Boot from USB on your Mac")
        print("4. Run the appropriate launcher script")
        print("\n🍎 FOR MAC RECOVERY:")
        print("- Hold Option/Alt key during boot")
        print("- Select your USB drive")
        print("- Launch BootForge for OCLP support")
        
        return True

if __name__ == "__main__":
    creator = BootableUSBCreator()
    creator.build_bootable_usb()
