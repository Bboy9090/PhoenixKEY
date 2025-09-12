BootForge for Windows - Quick Setup Guide
==========================================

📦 INSTALLATION:
1. Extract bootforge-windows.zip to a folder (e.g., C:\bootforge\)
2. Right-click windows-setup.bat and "Run as Administrator"
3. The script will install all required dependencies

🚀 USAGE:
- Open Command Prompt or PowerShell
- Navigate to the BootForge folder: cd C:\bootforge
- Run commands: python main.py --help

🔧 IMPORTANT FOR DISK OPERATIONS:
- Run Command Prompt as Administrator for USB operations
- Windows device paths: \\.\PhysicalDrive0, \\.\PhysicalDrive1, etc.
- Use "python main.py list-devices" to see available drives

💡 EXAMPLES:
python main.py list-devices
python main.py write-image -i windows10.iso -d \\.\PhysicalDrive1 --dry-run
python main.py format-device -d \\.\PhysicalDrive1 -f fat32

✅ Features included:
- Professional CLI interface with colors
- USB device detection and health checking
- Safe multi-step confirmations for data protection
- Dry-run mode to preview operations
- Plugin system with diagnostics and driver injection
- Cross-platform compatibility

🛡️ SAFETY:
- Always verify the target device before writing
- Use --dry-run first to preview operations
- BootForge includes multi-step confirmations to prevent accidents
- Back up important data before any disk operations

Support: All CLI commands include built-in help with --help