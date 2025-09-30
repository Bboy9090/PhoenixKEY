# BootForge - Professional Cross-Platform OS Deployment Tool

## Overview

BootForge is a professional-grade tool for creating bootable USB drives for macOS, Windows, and Linux operating systems. The application features a modular plugin architecture with both CLI and GUI interfaces, designed for cross-platform compatibility. It provides advanced functionality including driver injection, system monitoring, iOS jailbreak integration (checkra1n), and comprehensive USB drive diagnostics. The tool is built with Python and PyQt6, targeting power users and system administrators who need reliable OS deployment capabilities.

## Recent Changes

**September 30, 2025 - Complete Windows Compatibility & LSP Cleanup (v1.1.2):**
- ✅ Fixed ALL Windows compatibility issues for production-ready Windows builds
- ✅ Implemented proper Windows volume dismounting with PowerShell (prevents write failures)
- ✅ Fixed Windows USB eject functionality with drive letter mapping
- ✅ Fixed Manual Selection dialog crash on Windows (table header configuration)
- ✅ Fixed missing 'accent' key in BootForgeTheme.COLORS dictionary (KeyError crash)
- ✅ Auto-enables GUI mode when double-clicking BootForge.exe on Windows
- ✅ Cleaned up ALL LSP type errors (6 errors → 0 errors)
- ✅ Added robust error handling for PyQt6 cross-platform compatibility
- ✅ All code compiles successfully on all platforms
- ✅ App starts successfully without any crashes

**September 30, 2025 - GUI Dialogs & Build System Fix (v1.1.1):**
- ✅ Implemented Format Device dialog with USB drive selection and format type options
- ✅ Created comprehensive Documentation dialog with Quick Start Guide and OCLP instructions
- ✅ Fixed debug_build.py syntax error for proper Windows path separator handling
- ✅ All placeholder features now fully functional

**September 30, 2025 - Manual Hardware Profile Selection (v1.1):**
- ✅ Added "Manual Selection" feature to Hardware Detection step
- ✅ Users can now select hardware profiles for OTHER computers (not just current one)
- ✅ Organized profiles by platform (Mac, Windows, Linux) in searchable tabbed dialog
- ✅ Enables creating bootable USBs for multiple computers from one workstation
- ✅ Perfect for users with multiple devices (iMacs, laptops, etc.)

**September 12, 2025 - USB Builder Engine Complete (v1.0):**
- ✅ Implemented complete OpenCore Legacy Patcher-style USB deployment system
- ✅ Added 4 deployment recipes: macOS OCLP, Windows unattended, Linux automated, Custom payload
- ✅ Created hardware profile system with 14 profiles (7 Mac, 4 Windows, 3 Linux)
- ✅ Built bulletproof safety system with device protection and risk assessment
- ✅ Added comprehensive rollback mechanism for failed operations
- ✅ Polished all LSP diagnostics and achieved clean codebase
- ✅ Successfully tested CLI functionality with comprehensive logging
- ✅ **ARCHITECT APPROVED FOR PRODUCTION v1.0**

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Application Structure
- **Modular Design**: Core functionality separated into distinct modules (core, GUI, CLI, plugins, utils)
- **Plugin System**: Extensible architecture allowing custom plugins for specialized operations
- **Cross-Platform Support**: Designed to work on Windows, macOS, and Linux with platform-specific adaptations
- **Dual Interface**: Both command-line interface (CLI) and graphical user interface (GUI) support

### Core Components
- **Configuration Management**: Centralized config system with JSON persistence and application directory structure
- **Disk Management**: Thread-based disk operations with progress monitoring and verification capabilities
- **System Monitoring**: Real-time system resource tracking including CPU, memory, temperature, and USB device detection
- **Logging System**: Comprehensive logging with file rotation, GUI integration, and multiple output levels

### Frontend Architecture
- **GUI Framework**: PyQt6-based interface with wizard-style workflows
- **Responsive Design**: Multi-widget layout with status monitoring, log viewing, and step-by-step operations
- **Thread Safety**: GUI operations separated from blocking I/O operations using QThread
- **Real-time Updates**: Signal-slot architecture for live system monitoring and progress updates

### Plugin Architecture
- **Base Plugin System**: Abstract base class enforcing consistent plugin interface
- **Dynamic Loading**: Runtime plugin discovery and initialization
- **Specialized Plugins**: 
  - Driver injection for Windows/macOS systems
  - USB diagnostics and health checking
  - Checkra1n integration for iOS workflows
- **Configuration Integration**: Plugins integrate with central configuration system

### Data Management
- **Configuration Storage**: JSON-based configuration files in user home directory (~/.bootforge/)
- **Temporary Files**: Managed temporary directory structure for operation artifacts
- **Log Management**: Rotating log files with configurable retention policies
- **Driver Cache**: Local caching system for frequently used drivers and kexts

## External Dependencies

### Core Runtime Dependencies
- **click**: CLI framework for command-line interface
- **colorama**: Cross-platform colored terminal output
- **cryptography**: Security operations and verification
- **pillow**: Image processing capabilities
- **psutil**: System and process monitoring
- **pyyaml**: Configuration file parsing
- **requests**: HTTP operations for downloads and updates

### GUI Dependencies
- **PyQt6**: Main GUI framework providing widgets, threading, and cross-platform support

### System Integration Tools
- **Platform-Specific Tools**: 
  - Linux: badblocks, e2fsprogs, dosfstools, ntfs-3g
  - macOS: diskutil (system built-in)
  - Windows: format (system built-in)
- **Mobile Device Support**: libimobiledevice for iOS device interaction
- **Specialized Tools**: checkra1n for iOS jailbreak workflows

### Development and Distribution
- **pyinstaller**: Binary packaging and distribution
- **pytest**: Testing framework for core functionality verification

### Optional Integrations
- **Cloud Services**: Support for handling large OS images with limited local storage
- **Hardware Monitoring**: Platform-specific temperature and thermal monitoring APIs
- **USB Health**: Integration with system-level disk health reporting tools