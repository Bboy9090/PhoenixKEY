# BootForge Windows Installation Script
# 
# Quick install: iwr https://bootforge.dev/install/windows | iex
# 
# This script downloads and installs BootForge on Windows systems.
# Run with -Verbose for detailed output, -Uninstall to remove BootForge.

param(
    [switch]$Verbose,
    [switch]$Uninstall,
    [switch]$Help
)

# Set error action
$ErrorActionPreference = "Stop"

# Configuration with environment variable support
$BootForgeUrl = if ($env:BOOTFORGE_BASE_URL) { $env:BOOTFORGE_BASE_URL.TrimEnd('/') } else { "https://bootforge.dev" }
$InstallDir = "$env:LOCALAPPDATA\BootForge"
$ExecutableName = "BootForge.exe"
$ConfigDir = "$env:APPDATA\BootForge"

# Colors for output (PowerShell 5.1+ compatible)
$Colors = @{
    Red = "Red"
    Green = "Green"
    Yellow = "Yellow"
    Blue = "Blue"
    Magenta = "Magenta"
    Cyan = "Cyan"
    White = "White"
}

# Logging functions
function Write-Info { 
    param($Message)
    Write-Host "ℹ️  $Message" -ForegroundColor $Colors.Blue
}

function Write-Success { 
    param($Message)
    Write-Host "✅ $Message" -ForegroundColor $Colors.Green
}

function Write-Warning { 
    param($Message)
    Write-Host "⚠️  $Message" -ForegroundColor $Colors.Yellow
}

function Write-Error { 
    param($Message)
    Write-Host "❌ $Message" -ForegroundColor $Colors.Red
}

function Write-Progress { 
    param($Message)
    Write-Host "🔄 $Message" -ForegroundColor $Colors.Magenta
}

# Print banner
function Show-Banner {
    Write-Host "╔══════════════════════════════════════════════╗" -ForegroundColor $Colors.Cyan
    Write-Host "║              BootForge Installer             ║" -ForegroundColor $Colors.Cyan
    Write-Host "║     Professional OS Deployment Tool         ║" -ForegroundColor $Colors.Cyan
    Write-Host "║                  Windows                     ║" -ForegroundColor $Colors.Cyan
    Write-Host "╚══════════════════════════════════════════════╝" -ForegroundColor $Colors.Cyan
}

# Detect system architecture
function Get-SystemArchitecture {
    $arch = $env:PROCESSOR_ARCHITECTURE
    if ($env:PROCESSOR_ARCHITEW6432) {
        $arch = $env:PROCESSOR_ARCHITEW6432
    }
    
    switch ($arch) {
        "AMD64" { return "x64" }
        "ARM64" { return "arm64" }
        "x86" { 
            Write-Error "32-bit Windows is not supported"
            exit 1
        }
        default {
            Write-Error "Unsupported architecture: $arch"
            exit 1
        }
    }
}

# Detect Windows version
function Get-WindowsVersion {
    $version = [System.Environment]::OSVersion.Version
    $friendlyName = (Get-WmiObject -Class Win32_OperatingSystem).Caption
    
    if ($version.Major -lt 10) {
        Write-Error "Windows 10 or later required. Current: $friendlyName"
        exit 1
    }
    
    return $friendlyName
}

# Check if running as administrator
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Request administrator privileges
function Request-AdminPrivileges {
    if (-not (Test-Administrator)) {
        Write-Warning "Administrator privileges required for installation"
        Write-Info "Attempting to restart with elevated privileges..."
        
        $arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
        if ($Verbose) { $arguments += " -Verbose" }
        if ($Uninstall) { $arguments += " -Uninstall" }
        
        try {
            Start-Process PowerShell -ArgumentList $arguments -Verb RunAs -Wait
            exit 0
        }
        catch {
            Write-Error "Failed to obtain administrator privileges"
            Write-Error "Please run this script as an administrator"
            exit 1
        }
    }
}

# Create directories
function New-InstallDirectories {
    Write-Progress "Creating installation directories..."
    
    if (!(Test-Path $InstallDir)) {
        New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    }
    
    if (!(Test-Path $ConfigDir)) {
        New-Item -ItemType Directory -Path $ConfigDir -Force | Out-Null
    }
    
    Write-Success "Directories created"
}

# Install BootForge with working functionality
function Install-BootForge {
    $arch = Get-SystemArchitecture
    Write-Progress "Installing BootForge for Windows $arch..."
    
    # Check if Python is available for Python-based installation
    $hasPython = $false
    try {
        $pythonOutput = & python --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Info "Python detected: $pythonOutput"
            $hasPython = $true
        }
    } catch {
        # Python not found
    }
    
    if ($hasPython) {
        Write-Info "Creating Python-based BootForge launcher..."
        $workingScript = @"
@echo off
title BootForge for Windows
color 0A
cls
echo.
echo ╔══════════════════════════════════════════════╗
echo ║                   BootForge                  ║
echo ║       Professional OS Deployment Tool       ║
echo ╚══════════════════════════════════════════════╝
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is required but not found
    echo 📥 Install Python from: https://python.org/downloads
    echo.
    echo After installing Python, run this launcher again.
    pause
    exit /b 1
)

echo 🐍 Python detected - checking dependencies...

REM Check if PyQt6 is available
python -c "import PyQt6" >nul 2>&1
if %errorlevel% neq 0 (
    echo 📦 Installing PyQt6...
    python -m pip install PyQt6 requests pyyaml pillow psutil colorama cryptography
    if %errorlevel% neq 0 (
        echo ❌ Failed to install dependencies
        pause
        exit /b 1
    )
)

echo ✅ Dependencies ready

REM Download BootForge source if not present
if not exist "%USERPROFILE%\BootForge\main.py" (
    echo 📥 Downloading BootForge source code...
    mkdir "%USERPROFILE%\BootForge" 2>nul
    cd /d "%USERPROFILE%\BootForge"
    
    REM Download source using curl or PowerShell
    curl -L "$BootForgeUrl/download/usb-package" -o BootForge.tar.gz 2>nul
    if %errorlevel% neq 0 (
        echo Using PowerShell to download...
        powershell -Command "Invoke-WebRequest -Uri '$BootForgeUrl/download/usb-package' -OutFile 'BootForge.tar.gz'"
    )
    
    REM Extract if we have tar
    tar -xzf BootForge.tar.gz 2>nul
    if %errorlevel% neq 0 (
        echo ⚠️  Please manually extract BootForge.tar.gz and run main.py
        pause
        exit /b 1
    )
    
    echo ✅ BootForge source downloaded
)

echo 🚀 Starting BootForge...
cd /d "%USERPROFILE%\BootForge"

REM Try to find main.py
if exist "main.py" (
    python main.py %*
) else if exist "usb-package\main.py" (
    cd usb-package
    python main.py %*
) else if exist "BootForge-USB-Package\main.py" (
    cd BootForge-USB-Package
    python main.py %*
) else (
    echo ❌ BootForge main.py not found
    echo 🌐 Opening web interface instead...
    start "$BootForgeUrl"
    pause
)
"@
    } else {
        Write-Warning "Python not detected - creating web launcher"
        $workingScript = @"
@echo off
title BootForge for Windows
color 0A
cls
echo.
echo ╔══════════════════════════════════════════════╗
echo ║                   BootForge                  ║
echo ║       Professional OS Deployment Tool       ║
echo ╚══════════════════════════════════════════════╝
echo.
echo 🪟 BootForge Installation Complete!
echo.
echo Python is required for the desktop application.
echo Choose an option below:
echo.
echo [1] Install Python + Desktop App (Recommended)
echo [2] Use Web Interface (No installation needed)
echo [3] Use via WSL (Linux Subsystem)
echo [4] Download USB Package
echo.
set /p choice="Select option (1-4): "

if "%choice%"=="1" (
    echo 📥 Opening Python download page...
    start https://python.org/downloads
    echo.
    echo After installing Python, run this launcher again for desktop app.
    pause
) else if "%choice%"=="2" (
    echo 🌐 Opening BootForge web interface...
    start "$BootForgeUrl"
) else if "%choice%"=="3" (
    echo 🐧 Installing via WSL...
    wsl curl -fsSL $BootForgeUrl/install/linux ^| bash
    echo Run 'wsl BootForge --gui' to start
    pause
) else if "%choice%"=="4" (
    echo 📦 Opening USB package download...
    start "$BootForgeUrl/download/usb-package"
) else (
    echo 🌐 Opening web interface...
    start "$BootForgeUrl"
)
"@
    }
    
    # Create the working launcher
    $executablePath = Join-Path $InstallDir $ExecutableName
    $batPath = $executablePath -replace '\.exe$', '.bat'
    $workingScript | Out-File -FilePath $batPath -Encoding ASCII
    
    Write-Success "✅ BootForge installed successfully!"
    if ($hasPython) {
        Write-Info "🐍 Python-based launcher created - will download source on first run"
    } else {
        Write-Info "🌐 Web launcher created - provides multiple installation options"
    }
    Write-Info "📍 Location: $batPath"
}

# Add to PATH
function Add-ToPath {
    Write-Progress "Adding BootForge to PATH..."
    
    $currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    
    if ($currentPath -notlike "*$InstallDir*") {
        $newPath = if ($currentPath) { "$currentPath;$InstallDir" } else { $InstallDir }
        [Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
        
        # Update current session PATH
        $env:PATH = "$env:PATH;$InstallDir"
        
        Write-Success "Added to PATH (restart terminal for changes to take effect)"
    }
    else {
        Write-Info "BootForge already in PATH"
    }
}

# Create desktop shortcut
function New-DesktopShortcut {
    Write-Progress "Creating desktop shortcut..."
    
    $shell = New-Object -ComObject WScript.Shell
    $shortcutPath = [System.IO.Path]::Combine([Environment]::GetFolderPath("Desktop"), "BootForge.lnk")
    $shortcut = $shell.CreateShortcut($shortcutPath)
    
    $executablePath = Join-Path $InstallDir $ExecutableName
    $batPath = $executablePath -replace '\.exe$', '.bat'
    
    $shortcut.TargetPath = $batPath
    $shortcut.Arguments = ""
    $shortcut.Description = "BootForge Professional OS Deployment Tool"
    $shortcut.WorkingDirectory = $InstallDir
    $shortcut.Save()
    
    Write-Success "Desktop shortcut created"
}

# Create start menu entry
function New-StartMenuEntry {
    Write-Progress "Creating Start Menu entry..."
    
    $startMenuPath = [System.IO.Path]::Combine([Environment]::GetFolderPath("Programs"), "BootForge")
    
    if (!(Test-Path $startMenuPath)) {
        New-Item -ItemType Directory -Path $startMenuPath -Force | Out-Null
    }
    
    $shell = New-Object -ComObject WScript.Shell
    $shortcutPath = Join-Path $startMenuPath "BootForge.lnk"
    $shortcut = $shell.CreateShortcut($shortcutPath)
    
    $executablePath = Join-Path $InstallDir $ExecutableName
    $batPath = $executablePath -replace '\.exe$', '.bat'
    
    $shortcut.TargetPath = $batPath
    $shortcut.Arguments = ""
    $shortcut.Description = "BootForge Professional OS Deployment Tool"
    $shortcut.WorkingDirectory = $InstallDir
    $shortcut.Save()
    
    Write-Success "Start Menu entry created"
}

# Create configuration
function New-Configuration {
    Write-Progress "Creating default configuration..."
    
    $configContent = @"
# BootForge Configuration for Windows
app:
  version: "1.0.0"
  theme: "dark"
  auto_update_check: true
  platform: "windows"

logging:
  level: "info"
  max_files: 10
  max_size_mb: 50

usb:
  verify_operations: true
  safety_checks: true
  show_all_devices: false

gui:
  remember_window_size: true
  show_progress_details: true
  enable_animations: true
  use_native_dialogs: true

windows:
  request_uac: true
  check_drivers: true
"@
    
    $configPath = Join-Path $ConfigDir "config.yaml"
    $configContent | Out-File -FilePath $configPath -Encoding UTF8
    
    Write-Success "Configuration created"
}

# Create uninstaller
function New-Uninstaller {
    $uninstallScript = @"
@echo off
echo Uninstalling BootForge...

REM Remove from PATH
for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "CurrentPath=%%B"
if defined CurrentPath (
    set "NewPath=%CurrentPath:;$InstallDir=%"
    set "NewPath=%NewPath:$InstallDir;=%"
    set "NewPath=%NewPath:$InstallDir=%"
    reg add "HKCU\Environment" /v PATH /t REG_EXPAND_SZ /d "%NewPath%" /f >nul
)

REM Remove shortcuts
del "%USERPROFILE%\Desktop\BootForge.lnk" 2>nul
rmdir /s /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\BootForge" 2>nul

REM Remove installation directory
rmdir /s /q "$InstallDir" 2>nul

echo BootForge uninstalled successfully.
echo Configuration files in %APPDATA%\BootForge were preserved.
pause
"@
    
    $uninstallPath = Join-Path $InstallDir "Uninstall.bat"
    $uninstallScript | Out-File -FilePath $uninstallPath -Encoding ASCII
    
    Write-Success "Uninstaller created"
}

# Verify installation
function Test-Installation {
    Write-Progress "Verifying installation..."
    
    $executablePath = Join-Path $InstallDir $ExecutableName
    $batPath = $executablePath -replace '\.exe$', '.bat'
    
    if (Test-Path $batPath) {
        Write-Success "BootForge installed successfully"
        
        Write-Info "Installation complete! 🎉"
        Write-Host ""
        Write-Host "Quick Start:" -ForegroundColor $Colors.Cyan
        Write-Host "  • Desktop:    Double-click BootForge shortcut"
        Write-Host "  • Start Menu: Search for 'BootForge'"
        Write-Host "  • Web UI:     Visit $BootForgeUrl"
        Write-Host ""
        Write-Host "Note: Full native Windows app coming soon!" -ForegroundColor $Colors.Cyan
        Write-Host "      Current version provides compatibility layer"
        Write-Host ""
        
    }
    else {
        Write-Error "Installation verification failed"
        exit 1
    }
}

# Uninstall function
function Remove-BootForge {
    Write-Host "🗑️  Uninstalling BootForge..." -ForegroundColor $Colors.Yellow
    
    # Remove from PATH
    $currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    if ($currentPath -like "*$InstallDir*") {
        $newPath = $currentPath -replace [regex]::Escape(";$InstallDir"), ""
        $newPath = $newPath -replace [regex]::Escape("$InstallDir;"), ""
        $newPath = $newPath -replace [regex]::Escape("$InstallDir"), ""
        [Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
        Write-Success "Removed from PATH"
    }
    
    # Remove shortcuts
    $desktopShortcut = [System.IO.Path]::Combine([Environment]::GetFolderPath("Desktop"), "BootForge.lnk")
    if (Test-Path $desktopShortcut) {
        Remove-Item $desktopShortcut -Force
        Write-Success "Removed desktop shortcut"
    }
    
    $startMenuPath = [System.IO.Path]::Combine([Environment]::GetFolderPath("Programs"), "BootForge")
    if (Test-Path $startMenuPath) {
        Remove-Item $startMenuPath -Recurse -Force
        Write-Success "Removed Start Menu entry"
    }
    
    # Remove installation directory
    if (Test-Path $InstallDir) {
        Remove-Item $InstallDir -Recurse -Force
        Write-Success "Removed installation directory"
    }
    
    # Ask about configuration
    $removeConfig = Read-Host "Remove configuration directory? (y/N)"
    if ($removeConfig -eq 'y' -or $removeConfig -eq 'Y') {
        if (Test-Path $ConfigDir) {
            Remove-Item $ConfigDir -Recurse -Force
            Write-Success "Removed configuration"
        }
    }
    
    Write-Success "BootForge uninstalled"
}

# Main function
function Main {
    # Show help if requested
    if ($Help) {
        Write-Host "BootForge Windows Installer"
        Write-Host ""
        Write-Host "Usage: powershell -ExecutionPolicy Bypass -File install-windows.ps1 [OPTIONS]"
        Write-Host ""
        Write-Host "Options:"
        Write-Host "  -Verbose      Verbose output"
        Write-Host "  -Uninstall    Remove BootForge"
        Write-Host "  -Help         Show this help"
        Write-Host ""
        Write-Host "Quick install:"
        Write-Host "  iwr https://bootforge.dev/install/windows | iex"
        return
    }
    
    Show-Banner
    
    if ($Uninstall) {
        Remove-BootForge
        return
    }
    
    # Show system info
    Write-Info "Windows Version: $(Get-WindowsVersion)"
    Write-Info "Architecture: $(Get-SystemArchitecture)"
    Write-Info "PowerShell Version: $($PSVersionTable.PSVersion)"
    
    # Check requirements
    Write-Progress "Checking system requirements..."
    
    # Check PowerShell version
    if ($PSVersionTable.PSVersion.Major -lt 5) {
        Write-Error "PowerShell 5.0 or later required"
        exit 1
    }
    
    Write-Success "System requirements satisfied"
    
    # Request admin privileges
    Request-AdminPrivileges
    
    # Proceed with installation
    New-InstallDirectories
    Install-BootForge
    Add-ToPath
    New-DesktopShortcut
    New-StartMenuEntry
    New-Configuration
    New-Uninstaller
    Test-Installation
}

# Handle Ctrl+C gracefully
try {
    Main
}
catch {
    Write-Error "Installation failed: $_"
    exit 1
}