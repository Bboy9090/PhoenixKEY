BootForge USB Distribution Package
==================================

This USB package contains everything you need to install and run BootForge on your target systems.

CONTENTS:
- BootForge-Linux-x64: Linux executable (ready to use)
- usb-installer.sh: Auto-installer for Linux/macOS systems  
- usb-installer.bat: Auto-installer for Windows systems
- README.txt: This file

INSTALLATION:

For Linux:
1. Copy this entire folder to your target Linux computer
2. Open terminal and navigate to this folder
3. Run: ./usb-installer.sh
4. BootForge will be installed to ~/BootForge/ with desktop shortcut

For Windows:
1. Copy this entire folder to your target Windows computer
2. Double-click usb-installer.bat
3. BootForge will be installed to %USERPROFILE%\BootForge\ with desktop shortcut
   (Note: Windows executable coming soon!)

For macOS:
1. Copy this entire folder to your target Mac
2. Open Terminal and navigate to this folder  
3. Run: ./usb-installer.sh
   (Note: macOS executable coming soon!)

MANUAL INSTALLATION:
1. Copy BootForge-Linux-x64 to your desired location
2. Make it executable: chmod +x BootForge-Linux-x64
3. Run with: ./BootForge-Linux-x64 --gui

SYSTEM REQUIREMENTS:
- Linux: 64-bit system with GUI support (X11/Wayland)
- Windows: Windows 10/11 64-bit (executable coming soon)
- macOS: macOS 10.15+ (executable coming soon)
- RAM: 512MB minimum, 1GB recommended
- Storage: 100MB free space
- USB: Root/admin privileges for USB device access

USAGE:
- GUI Mode: Run with --gui flag for graphical interface
- CLI Mode: Run without flags for command-line interface
- Help: Run with --help for all available commands

For support and documentation, visit: https://github.com/bootforge

Version 1.0.0 - Professional OS Deployment Tool