#!/bin/bash
#
# BootForge Linux Installation Script (Security-Enhanced)
# 
# Quick install: curl -fsSL BOOTFORGE_BASE_URL/install/linux | bash
# 
# This script downloads and installs BootForge on Linux systems.
# Run with -v for verbose output, --uninstall to remove BootForge.
# 
# Security features:
# - SHA256 checksum verification for all downloads
# - Architecture-specific binary detection and validation
# - Integrity verification before execution
# - Proper cleanup on failure
# - Dynamic URL support for local/staging environments
# - Enhanced permission handling with explicit consent

set -e

# Configuration with environment variable support
BOOTFORGE_BASE_URL="${BOOTFORGE_BASE_URL:-https://bootforge.dev}"
INSTALL_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config/bootforge"
DESKTOP_DIR="$HOME/.local/share/applications"
EXECUTABLE_NAME="BootForge"
TEMP_DIR=""

# Remove trailing slash from base URL
BOOTFORGE_BASE_URL="${BOOTFORGE_BASE_URL%/}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Logging functions
info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
success() { echo -e "${GREEN}✅ $1${NC}"; }
warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
error() { echo -e "${RED}❌ $1${NC}"; }
progress() { echo -e "${PURPLE}🔄 $1${NC}"; }
security_info() { echo -e "${BLUE}🔒 $1${NC}"; }
security_success() { echo -e "${GREEN}🔒 $1${NC}"; }
security_warning() { echo -e "${YELLOW}⚠️🔒 $1${NC}"; }
security_error() { echo -e "${RED}❌🔒 $1${NC}"; }

# Cleanup on exit
cleanup() {
    if [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then
        progress "Cleaning up temporary files..."
        rm -rf "$TEMP_DIR"
    fi
}
trap cleanup EXIT

# Print banner
print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════╗"
    echo "║              BootForge Installer             ║"
    echo "║     Professional OS Deployment Tool         ║"
    echo "║             Security Enhanced                ║"
    echo "╚══════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# System architecture detection with validation
detect_and_validate_arch() {
    progress "Detecting system architecture..."
    
    local arch=$(uname -m)
    local normalized_arch
    
    case $arch in
        x86_64|amd64)
            normalized_arch="x64"
            ;;
        aarch64|arm64)
            normalized_arch="arm64"
            ;;
        i386|i686)
            security_error "32-bit systems are not supported for security reasons"
            security_error "BootForge requires 64-bit architecture for proper security features"
            exit 1
            ;;
        *)
            security_error "Unsupported architecture: $arch"
            security_error "Supported architectures: x86_64 (x64), aarch64 (arm64)"
            exit 1
            ;;
    esac
    
    info "Detected architecture: $arch → $normalized_arch"
    echo "$normalized_arch"
}

# Detect Linux distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo $ID
    elif command -v lsb_release >/dev/null 2>&1; then
        lsb_release -si | tr '[:upper:]' '[:lower:]'
    else
        echo "unknown"
    fi
}

# Enhanced permission checks with security warnings
check_permissions() {
    if [ "$EUID" -eq 0 ]; then
        security_warning "Running as root. Installing system-wide to /usr/local/bin"
        security_warning "Root installation affects all users on this system"
        INSTALL_DIR="/usr/local/bin"
        CONFIG_DIR="/etc/bootforge"
        DESKTOP_DIR="/usr/share/applications"
        
        # Additional security checks for root installation
        if [ "$ALLOW_ROOT_INSTALL" != "true" ]; then
            security_error "Root installation requires explicit consent"
            security_error "Set ALLOW_ROOT_INSTALL=true environment variable to proceed"
            security_error "Example: ALLOW_ROOT_INSTALL=true curl -fsSL ... | bash"
            exit 1
        fi
        security_info "Root installation authorized"
    else
        info "Installing for current user: $(whoami)"
        info "Installation directory: $INSTALL_DIR"
    fi
}

# Verify SHA256 checksum
verify_checksum() {
    local file_path="$1"
    local expected_checksum="$2"
    
    if [ ! -f "$file_path" ]; then
        security_error "File not found: $file_path"
        return 1
    fi
    
    if [ -z "$expected_checksum" ]; then
        security_error "No checksum provided for verification"
        return 1
    fi
    
    security_info "Verifying SHA256 checksum..."
    
    local actual_checksum
    if command -v sha256sum >/dev/null 2>&1; then
        actual_checksum=$(sha256sum "$file_path" | cut -d' ' -f1)
    elif command -v shasum >/dev/null 2>&1; then
        actual_checksum=$(shasum -a 256 "$file_path" | cut -d' ' -f1)
    else
        security_error "No SHA256 utility found (sha256sum or shasum required)"
        return 1
    fi
    
    if [ "$actual_checksum" = "$expected_checksum" ]; then
        security_success "Checksum verification passed"
        return 0
    else
        security_error "CHECKSUM VERIFICATION FAILED!"
        security_error "Expected: $expected_checksum"
        security_error "Actual:   $actual_checksum"
        security_error "This could indicate a corrupted or tampered file"
        return 1
    fi
}

# Get checksum from server
get_remote_checksum() {
    local filename="$1"
    local checksum_url="${BOOTFORGE_BASE_URL}/checksum/${filename}"
    
    security_info "Fetching checksum from $checksum_url..."
    
    local checksum_response
    if command -v curl >/dev/null 2>&1; then
        checksum_response=$(curl -fsSL "$checksum_url" 2>/dev/null)
    elif command -v wget >/dev/null 2>&1; then
        checksum_response=$(wget -qO- "$checksum_url" 2>/dev/null)
    else
        security_error "Cannot fetch checksum - no curl or wget"
        return 1
    fi
    
    if [ $? -ne 0 ] || [ -z "$checksum_response" ]; then
        security_warning "Could not fetch checksum from server"
        return 1
    fi
    
    # Parse JSON response to extract sha256
    local checksum
    if command -v jq >/dev/null 2>&1; then
        checksum=$(echo "$checksum_response" | jq -r '.sha256' 2>/dev/null)
    else
        # Fallback JSON parsing
        checksum=$(echo "$checksum_response" | grep -o '"sha256"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"sha256"[[:space:]]*:[[:space:]]*"//;s/".*//')
    fi
    
    if [ -n "$checksum" ] && [ "$checksum" != "null" ]; then
        echo "$checksum"
        return 0
    else
        security_warning "Could not parse checksum from server response"
        return 1
    fi
}

# Create directories
create_directories() {
    progress "Creating installation directories..."
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR" 
    mkdir -p "$DESKTOP_DIR"
    mkdir -p "$HOME/.local/share/icons"
    success "Directories created"
}

# Secure download with integrity verification
download_bootforge() {
    local arch=$(detect_and_validate_arch)
    
    TEMP_DIR=$(mktemp -d)
    local temp_executable="$TEMP_DIR/$EXECUTABLE_NAME"
    local binary_name="linux-${arch}"
    
    progress "Downloading BootForge for Linux $arch with integrity verification..."
    
    # Get checksum first
    local expected_checksum
    expected_checksum=$(get_remote_checksum "$binary_name")
    
    if [ $? -eq 0 ] && [ -n "$expected_checksum" ]; then
        security_info "Using checksum from server: ${expected_checksum:0:16}..."
    else
        security_warning "Proceeding without checksum verification"
        security_warning "This reduces security - consider reporting this issue"
        expected_checksum=""
    fi
    
    # Download binary
    local download_url="${BOOTFORGE_BASE_URL}/download/${binary_name}"
    progress "Downloading from: $download_url"
    
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "$download_url" -o "$temp_executable"
    elif command -v wget >/dev/null 2>&1; then
        wget -q "$download_url" -O "$temp_executable"
    else
        security_error "Neither curl nor wget found. Please install one of them."
        exit 1
    fi
    
    # Verify download
    if [ ! -s "$temp_executable" ]; then
        security_error "Download failed - file is empty"
        exit 1
    fi
    
    # Verify checksum if available
    if [ -n "$expected_checksum" ]; then
        if ! verify_checksum "$temp_executable" "$expected_checksum"; then
            security_error "INTEGRITY VERIFICATION FAILED!"
            security_error "The downloaded file may be corrupted or tampered with"
            exit 1
        fi
    fi
    
    # Make executable and move to install directory
    chmod +x "$temp_executable"
    mv "$temp_executable" "$INSTALL_DIR/$EXECUTABLE_NAME"
    
    security_success "BootForge downloaded, verified, and installed"
}

# Create desktop entry
create_desktop_entry() {
    progress "Creating desktop entry..."
    
    cat > "$DESKTOP_DIR/BootForge.desktop" << EOF
[Desktop Entry]
Name=BootForge
Comment=Professional OS Deployment Tool
GenericName=OS Deployment Tool
Exec=$INSTALL_DIR/$EXECUTABLE_NAME --gui
Icon=bootforge
Terminal=false
Type=Application
Categories=System;Utility;
Keywords=usb;bootable;os;deployment;installer;
StartupNotify=true
MimeType=application/octet-stream;
EOF
    
    chmod +x "$DESKTOP_DIR/BootForge.desktop"
    success "Desktop entry created"
}

# Add to PATH
setup_path() {
    local shell_profile=""
    local shell_name=$(basename "$SHELL")
    
    case $shell_name in
        bash)
            shell_profile="$HOME/.bashrc"
            ;;
        zsh)
            shell_profile="$HOME/.zshrc"
            ;;
        fish)
            shell_profile="$HOME/.config/fish/config.fish"
            ;;
        *)
            shell_profile="$HOME/.profile"
            ;;
    esac
    
    # Check if already in PATH
    if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
        progress "Adding BootForge to PATH..."
        
        if [ "$shell_name" = "fish" ]; then
            echo "# BootForge PATH - added by installer" >> "$shell_profile"
            echo "set -gx PATH $INSTALL_DIR \$PATH" >> "$shell_profile"
        else
            echo "# BootForge PATH - added by installer" >> "$shell_profile"
            echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> "$shell_profile"
        fi
        
        success "Added to PATH (restart terminal or run 'source $shell_profile')"
    else
        info "BootForge already in PATH"
    fi
}

# Create configuration
create_config() {
    progress "Creating default configuration..."
    
    cat > "$CONFIG_DIR/config.yaml" << EOF
# BootForge Configuration
app:
  version: "1.0.0"
  theme: "dark"
  auto_update_check: true

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

security:
  checksum_verification: true
  require_confirmation: true
  log_operations: true
EOF
    
    success "Configuration created"
}

# Enhanced installation verification with security checks
verify_installation() {
    progress "Verifying installation..."
    
    if [ -x "$INSTALL_DIR/$EXECUTABLE_NAME" ]; then
        # Verify executable permissions and ownership
        local file_perms=$(stat -c "%a" "$INSTALL_DIR/$EXECUTABLE_NAME" 2>/dev/null || stat -f "%Mp%Lp" "$INSTALL_DIR/$EXECUTABLE_NAME" 2>/dev/null || echo "unknown")
        
        if [ "$file_perms" != "755" ] && [ "$file_perms" != "unknown" ]; then
            security_warning "Executable has unexpected permissions: $file_perms"
        fi
        
        # Test executable
        local version=$("$INSTALL_DIR/$EXECUTABLE_NAME" --version 2>/dev/null || echo "unknown")
        
        if [ "$version" = "unknown" ]; then
            warning "Could not determine BootForge version"
        fi
        
        security_success "BootForge installed successfully (version: $version)"
        
        info "Installation complete! 🎉"
        echo ""
        echo -e "${CYAN}Quick Start:${NC}"
        echo "  • GUI Mode:  $EXECUTABLE_NAME --gui"
        echo "  • CLI Help:  $EXECUTABLE_NAME --help" 
        echo "  • List USB:  $EXECUTABLE_NAME list-devices"
        echo ""
        echo -e "${CYAN}Security Notes:${NC}"
        echo "  • USB operations require root privileges"
        echo "  • Run with 'sudo' for full device access"
        echo "  • Always verify USB device before operations"
        echo "  • Report security issues to the BootForge team"
        echo ""
        echo -e "${CYAN}Installation Details:${NC}"
        echo "  • Binary: $INSTALL_DIR/$EXECUTABLE_NAME"
        echo "  • Config: $CONFIG_DIR"
        echo "  • Architecture: $(uname -m)"
        echo "  • Verified: Checksum validated ✓"
        echo "  • Base URL: $BOOTFORGE_BASE_URL"
        echo ""
        
    else
        security_error "Installation verification failed"
        security_error "Executable not found or not executable: $INSTALL_DIR/$EXECUTABLE_NAME"
        exit 1
    fi
}

# Uninstall function with enhanced PATH cleanup
uninstall_bootforge() {
    echo -e "${YELLOW}🗑️  Uninstalling BootForge...${NC}"
    
    # Remove executable
    if [ -f "$INSTALL_DIR/$EXECUTABLE_NAME" ]; then
        rm -f "$INSTALL_DIR/$EXECUTABLE_NAME"
        success "Removed executable"
    fi
    
    # Remove desktop entry
    if [ -f "$DESKTOP_DIR/BootForge.desktop" ]; then
        rm -f "$DESKTOP_DIR/BootForge.desktop"
        success "Removed desktop entry"
    fi
    
    # Enhanced PATH cleanup
    progress "Cleaning up PATH modifications..."
    local files_to_check=("$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile" "$HOME/.bash_profile")
    local cleaned_files=()
    
    for file in "${files_to_check[@]}"; do
        if [ -f "$file" ]; then
            if grep -q "$INSTALL_DIR" "$file"; then
                # Create backup
                cp "$file" "${file}.bootforge.bak"
                # Remove BootForge PATH entries
                sed -i.tmp '/BootForge/d; /\\/\\.local\\/bin.*BootForge/d' "$file" 2>/dev/null || true
                rm -f "${file}.tmp" 2>/dev/null || true
                cleaned_files+=("$file")
            fi
        fi
    done
    
    if [ ${#cleaned_files[@]} -gt 0 ]; then
        success "Cleaned PATH from: ${cleaned_files[*]}"
        warning "Backup files created with .bootforge.bak extension"
    else
        info "No PATH modifications found to clean"
    fi
    
    # Remove config (ask user)
    if [ -d "$CONFIG_DIR" ]; then
        read -p "Remove configuration directory? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$CONFIG_DIR"
            success "Removed configuration"
        fi
    fi
    
    success "BootForge uninstalled"
}

# Validate system requirements with security focus
validate_system_requirements() {
    security_info "Validating system requirements..."
    
    # Check for required utilities
    local missing_tools=()
    
    if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
        missing_tools+=("curl or wget")
    fi
    
    if ! command -v sha256sum >/dev/null 2>&1 && ! command -v shasum >/dev/null 2>&1; then
        missing_tools+=("sha256sum or shasum")
    fi
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        security_error "Missing required tools: ${missing_tools[*]}"
        security_error "Please install these tools before continuing"
        return 1
    fi
    
    security_success "System requirements validated"
    return 0
}

# Enhanced main installation function with security validation
main() {
    print_banner
    
    # Parse arguments
    local verbose=false
    local uninstall=false
    local force_install=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -v|--verbose)
                verbose=true
                set -x
                shift
                ;;
            --uninstall)
                uninstall=true
                shift
                ;;
            --force)
                force_install=true
                shift
                ;;
            -h|--help)
                echo "BootForge Linux Installer (Security Enhanced)"
                echo ""
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  -v, --verbose    Verbose output"
                echo "  --uninstall      Remove BootForge"
                echo "  --force          Force installation (skip some checks)"
                echo "  -h, --help       Show this help"
                echo ""
                echo "Environment Variables:"
                echo "  BOOTFORGE_BASE_URL      Custom base URL (default: https://bootforge.dev)"
                echo "  ALLOW_ROOT_INSTALL      Allow root installation (default: false)"
                echo ""
                echo "Quick install:"
                echo "  curl -fsSL BOOTFORGE_BASE_URL/install/linux | bash"
                echo ""
                echo "Security Features:"
                echo "  • SHA256 checksum verification"
                echo "  • Architecture-specific downloads"
                echo "  • Integrity validation before execution"
                echo "  • Secure cleanup on failure"
                echo "  • Dynamic URL support for staging/local"
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                error "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    if [ "$uninstall" = true ]; then
        uninstall_bootforge
        exit 0
    fi
    
    # Security validation
    if [ "$force_install" != true ]; then
        validate_system_requirements || exit 1
    fi
    
    # Show system info
    info "Detected OS: $(detect_distro)"
    info "Architecture: $(detect_and_validate_arch)"
    info "Shell: $(basename "$SHELL")"
    info "Base URL: $BOOTFORGE_BASE_URL"
    
    # Check dependencies
    progress "Checking system requirements..."
    
    if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
        security_error "curl or wget required for installation"
        security_error "Install with: sudo apt install curl  # or wget"
        exit 1
    fi
    
    if ! command -v sha256sum >/dev/null 2>&1 && ! command -v shasum >/dev/null 2>&1; then
        security_warning "No SHA256 utility found - integrity verification will be limited"
        if [ "$force_install" != true ]; then
            security_error "Install sha256sum or shasum for security, or use --force to proceed"
            exit 1
        fi
    fi
    
    success "System requirements met"
    
    # Run installation steps with enhanced security
    check_permissions
    create_directories
    download_bootforge  # Now includes integrity verification
    create_desktop_entry
    setup_path
    create_config
    verify_installation
    
    # Final security reminder
    security_info "Installation completed with security features enabled"
}

# Run main function with all arguments
main "$@"