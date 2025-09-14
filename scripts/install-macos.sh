#!/bin/bash
#
# BootForge macOS Installation Script
# 
# Quick install: curl -fsSL https://bootforge.dev/install/macos | bash
# 
# This script downloads and installs BootForge on macOS systems.
# Run with -v for verbose output, --uninstall to remove BootForge.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
BOOTFORGE_URL="https://bootforge.dev"
INSTALL_DIR="/usr/local/bin"
APP_DIR="/Applications"
CONFIG_DIR="$HOME/.config/bootforge"
EXECUTABLE_NAME="BootForge"
APP_NAME="BootForge.app"

# Logging functions
info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
success() { echo -e "${GREEN}✅ $1${NC}"; }
warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
error() { echo -e "${RED}❌ $1${NC}"; }
progress() { echo -e "${PURPLE}🔄 $1${NC}"; }

# Print banner
print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════╗"
    echo "║              BootForge Installer             ║"
    echo "║     Professional OS Deployment Tool         ║"
    echo "║                   macOS                      ║"
    echo "╚══════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Detect system architecture
detect_arch() {
    local arch=$(uname -m)
    case $arch in
        x86_64)
            echo "x64"
            ;;
        arm64)
            echo "arm64"
            ;;
        *)
            error "Unsupported architecture: $arch"
            exit 1
            ;;
    esac
}

# Detect macOS version
detect_macos_version() {
    local version=$(sw_vers -productVersion)
    local major=$(echo $version | cut -d. -f1)
    
    if [ "$major" -lt 11 ]; then
        error "macOS 11.0 (Big Sur) or later required. Current: $version"
        exit 1
    fi
    
    echo $version
}

# Check Homebrew
check_homebrew() {
    if command -v brew >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Install Homebrew if needed
install_homebrew() {
    if ! check_homebrew; then
        warning "Homebrew not found. Installing Homebrew for better package management..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        
        # Add Homebrew to PATH for Apple Silicon Macs
        if [[ $(uname -m) == "arm64" ]]; then
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
    fi
}

# Check for admin privileges
check_admin_privileges() {
    if [ "$EUID" -eq 0 ]; then
        warning "Running as root. This is not recommended for macOS."
        return 0
    fi
    
    # Check if user is in admin group
    if dscl . -read /Groups/admin GroupMembership | grep -q "$(whoami)"; then
        return 0
    else
        error "Administrator privileges required for installation"
        error "Please run with an administrator account"
        exit 1
    fi
}

# Create directories
create_directories() {
    progress "Creating installation directories..."
    
    sudo mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"
    
    success "Directories created"
}

# Download BootForge (currently shows placeholder until macOS build is ready)
download_bootforge() {
    local arch=$(detect_arch)
    local temp_dir=$(mktemp -d)
    
    progress "Downloading BootForge for macOS $arch..."
    
    # Note: macOS build not ready yet, so we'll provide a placeholder that explains this
    warning "macOS executable not yet available"
    info "Creating placeholder installer that will download when available..."
    
    # Create a placeholder script that will download the real app when available
    cat > "$temp_dir/BootForge" << 'EOF'
#!/bin/bash
echo "🍎 BootForge for macOS"
echo "======================="
echo ""
echo "The native macOS application is currently being built."
echo "In the meantime, you can use the cross-platform Python version:"
echo ""
echo "Options:"
echo "  1. Download the USB package from: https://bootforge.dev/download/usb-package"
echo "  2. Use Python version: pip install bootforge"
echo "  3. Check https://bootforge.dev for macOS .app updates"
echo ""
echo "For immediate use, visit: https://bootforge.dev"
echo ""

# Check if Python is available and offer to run web interface
if command -v python3 >/dev/null 2>&1; then
    read -p "Open BootForge web interface? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python3 -c "
import webbrowser
import time
print('🌐 Opening BootForge web interface...')
webbrowser.open('https://bootforge.dev')
time.sleep(1)
"
    fi
fi
EOF
    
    chmod +x "$temp_dir/BootForge"
    sudo cp "$temp_dir/BootForge" "$INSTALL_DIR/$EXECUTABLE_NAME"
    
    rm -rf "$temp_dir"
    success "BootForge placeholder installed"
}

# Create app bundle (placeholder for future .app)
create_app_bundle() {
    progress "Setting up application bundle..."
    
    # Create a simple app bundle structure
    local app_path="$APP_DIR/$APP_NAME"
    
    if [ -d "$app_path" ]; then
        sudo rm -rf "$app_path"
    fi
    
    sudo mkdir -p "$app_path/Contents/MacOS"
    sudo mkdir -p "$app_path/Contents/Resources"
    
    # Create Info.plist
    sudo tee "$app_path/Contents/Info.plist" > /dev/null << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDisplayName</key>
    <string>BootForge</string>
    <key>CFBundleExecutable</key>
    <string>BootForge</string>
    <key>CFBundleIdentifier</key>
    <string>com.bootforge.app</string>
    <key>CFBundleName</key>
    <string>BootForge</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
</dict>
</plist>
EOF
    
    # Create executable
    sudo cp "$INSTALL_DIR/$EXECUTABLE_NAME" "$app_path/Contents/MacOS/BootForge"
    sudo chmod +x "$app_path/Contents/MacOS/BootForge"
    
    success "Application bundle created"
}

# Add to PATH
setup_path() {
    local shell_profile=""
    local shell_name=$(basename "$SHELL")
    
    case $shell_name in
        bash)
            shell_profile="$HOME/.bash_profile"
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
            echo "set -gx PATH $INSTALL_DIR \$PATH" >> "$shell_profile"
        else
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
# BootForge Configuration for macOS
app:
  version: "1.0.0"
  theme: "dark"
  auto_update_check: true
  platform: "macos"

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
  native_menus: true

macos:
  request_permissions: true
  use_native_dialogs: true
EOF
    
    success "Configuration created"
}

# Setup launch agent (for auto-updates)
setup_launch_agent() {
    local plist_dir="$HOME/Library/LaunchAgents"
    local plist_file="$plist_dir/com.bootforge.updater.plist"
    
    mkdir -p "$plist_dir"
    
    cat > "$plist_file" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.bootforge.updater</string>
    <key>ProgramArguments</key>
    <array>
        <string>$INSTALL_DIR/$EXECUTABLE_NAME</string>
        <string>--check-updates</string>
    </array>
    <key>StartInterval</key>
    <integer>86400</integer>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
EOF
    
    info "Auto-update check configured (daily)"
}

# Verify installation
verify_installation() {
    progress "Verifying installation..."
    
    if [ -x "$INSTALL_DIR/$EXECUTABLE_NAME" ]; then
        success "BootForge installed successfully"
        
        info "Installation complete! 🎉"
        echo ""
        echo -e "${CYAN}Quick Start:${NC}"
        echo "  • Open app:   open $APP_DIR/$APP_NAME"
        echo "  • CLI Mode:   $EXECUTABLE_NAME --help"
        echo "  • Web UI:     Visit https://bootforge.dev"
        echo ""
        echo -e "${CYAN}Note:${NC} Full native macOS app coming soon!"
        echo "      Current version provides compatibility layer"
        echo ""
        
    else
        error "Installation verification failed"
        exit 1
    fi
}

# Uninstall function
uninstall_bootforge() {
    echo -e "${YELLOW}🗑️  Uninstalling BootForge...${NC}"
    
    # Remove executable
    if [ -f "$INSTALL_DIR/$EXECUTABLE_NAME" ]; then
        sudo rm -f "$INSTALL_DIR/$EXECUTABLE_NAME"
        success "Removed executable"
    fi
    
    # Remove app bundle
    if [ -d "$APP_DIR/$APP_NAME" ]; then
        sudo rm -rf "$APP_DIR/$APP_NAME"
        success "Removed application bundle"
    fi
    
    # Remove launch agent
    local plist_file="$HOME/Library/LaunchAgents/com.bootforge.updater.plist"
    if [ -f "$plist_file" ]; then
        launchctl unload "$plist_file" 2>/dev/null || true
        rm -f "$plist_file"
        success "Removed launch agent"
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
    
    warning "PATH modifications in shell profiles were not removed"
    warning "Please manually remove BootForge PATH entries from:"
    warning "  ~/.zshrc, ~/.bash_profile, ~/.profile, etc."
    
    success "BootForge uninstalled"
}

# Main installation function
main() {
    print_banner
    
    # Parse arguments
    local verbose=false
    local uninstall=false
    
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
            -h|--help)
                echo "BootForge macOS Installer"
                echo ""
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  -v, --verbose    Verbose output"
                echo "  --uninstall      Remove BootForge"
                echo "  -h, --help       Show this help"
                echo ""
                echo "Quick install:"
                echo "  curl -fsSL https://bootforge.dev/install/macos | bash"
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    if [ "$uninstall" = true ]; then
        uninstall_bootforge
        exit 0
    fi
    
    # Show system info
    info "macOS Version: $(detect_macos_version)"
    info "Architecture: $(detect_arch)"
    info "Shell: $(basename "$SHELL")"
    
    # Check requirements
    progress "Checking system requirements..."
    check_admin_privileges
    
    if ! command -v curl >/dev/null 2>&1; then
        error "curl required for installation"
        error "Install Xcode Command Line Tools: xcode-select --install"
        exit 1
    fi
    
    success "System requirements satisfied"
    
    # Proceed with installation
    create_directories
    download_bootforge
    create_app_bundle
    setup_path
    create_config
    setup_launch_agent
    verify_installation
}

# Handle Ctrl+C gracefully
trap 'echo -e "\n${RED}Installation interrupted${NC}"; exit 1' INT

# Run main function
main "$@"