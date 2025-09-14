#!/bin/bash
#
# BootForge Security Verification Library
# Shared functions for integrity verification and security checks
#

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Security functions
security_info() { echo -e "${BLUE}🔒 $1${NC}"; }
security_success() { echo -e "${GREEN}✅ $1${NC}"; }
security_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
security_error() { echo -e "${RED}❌ $1${NC}"; }

# Detect system architecture
detect_architecture() {
    local arch=$(uname -m)
    case $arch in
        x86_64|amd64)
            echo "x64"
            ;;
        aarch64|arm64)
            echo "arm64"
            ;;
        i386|i686)
            security_error "32-bit systems are not supported for security reasons"
            return 1
            ;;
        *)
            security_error "Unsupported architecture: $arch"
            return 1
            ;;
    esac
}

# Get dynamic base URL
get_base_url() {
    local base_url="${BOOTFORGE_BASE_URL:-https://bootforge.dev}"
    
    # Remove trailing slash
    base_url="${base_url%/}"
    
    echo "$base_url"
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
        security_error "Checksum verification FAILED!"
        security_error "Expected: $expected_checksum"
        security_error "Actual:   $actual_checksum"
        security_error "This could indicate a corrupted or tampered file"
        return 1
    fi
}

# Download file with integrity verification
secure_download() {
    local url="$1"
    local output_file="$2"
    local expected_checksum="$3"
    
    security_info "Downloading $url..."
    
    # Create temporary file
    local temp_file=$(mktemp)
    local success=false
    
    # Try curl first, then wget
    if command -v curl >/dev/null 2>&1; then
        if curl -fsSL "$url" -o "$temp_file"; then
            success=true
        fi
    elif command -v wget >/dev/null 2>&1; then
        if wget -q "$url" -O "$temp_file"; then
            success=true
        fi
    else
        security_error "Neither curl nor wget found"
        rm -f "$temp_file"
        return 1
    fi
    
    if [ "$success" = false ]; then
        security_error "Download failed"
        rm -f "$temp_file"
        return 1
    fi
    
    # Verify file is not empty
    if [ ! -s "$temp_file" ]; then
        security_error "Downloaded file is empty"
        rm -f "$temp_file"
        return 1
    fi
    
    # Verify checksum if provided
    if [ -n "$expected_checksum" ]; then
        if ! verify_checksum "$temp_file" "$expected_checksum"; then
            security_error "Integrity verification failed - removing file"
            rm -f "$temp_file"
            return 1
        fi
    else
        security_warning "No checksum provided - skipping integrity verification"
    fi
    
    # Move to final location
    mv "$temp_file" "$output_file"
    security_success "Download completed and verified"
    return 0
}

# Get checksum from server
get_remote_checksum() {
    local base_url="$1"
    local filename="$2"
    
    local checksum_url="${base_url}/checksum/${filename}"
    
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

# Complete secure download with automatic checksum fetching
secure_download_with_checksum() {
    local base_url="$1"
    local filename="$2"
    local output_file="$3"
    
    # Get checksum from server
    local expected_checksum
    expected_checksum=$(get_remote_checksum "$base_url" "$filename")
    
    if [ $? -eq 0 ] && [ -n "$expected_checksum" ]; then
        security_info "Using checksum from server: ${expected_checksum:0:16}..."
    else
        security_warning "Proceeding without checksum verification"
        expected_checksum=""
    fi
    
    # Download with verification
    local download_url="${base_url}/download/${filename}"
    secure_download "$download_url" "$output_file" "$expected_checksum"
}

# Architecture-aware binary download
download_platform_binary() {
    local base_url="$1"
    local platform="$2"
    local arch="$3"
    local output_file="$4"
    
    local binary_name="${platform}-${arch}"
    
    security_info "Downloading BootForge for $platform $arch..."
    
    # First check if the architecture is available
    local download_url="${base_url}/download/${binary_name}"
    
    # Test if URL is accessible
    local test_response
    if command -v curl >/dev/null 2>&1; then
        test_response=$(curl -fsSL -I "$download_url" 2>/dev/null)
    elif command -v wget >/dev/null 2>&1; then
        test_response=$(wget -qS --spider "$download_url" 2>&1)
    fi
    
    if [ $? -ne 0 ]; then
        security_error "$platform $arch binary not available"
        security_error "Available architectures: x64, arm64"
        return 1
    fi
    
    # Download with automatic checksum verification
    secure_download_with_checksum "$base_url" "$binary_name" "$output_file"
}

# Validate system requirements
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

# Check if running with appropriate privileges
check_privileges() {
    local require_admin="$1"
    
    if [ "$require_admin" = "true" ]; then
        if [ "$EUID" -ne 0 ]; then
            security_warning "Running without administrator privileges"
            security_warning "Some features may not work properly"
            security_warning "Consider running with 'sudo' for full functionality"
        else
            security_info "Running with administrator privileges"
        fi
    fi
}

# Cleanup function for security
security_cleanup() {
    local temp_dir="$1"
    
    if [ -n "$temp_dir" ] && [ -d "$temp_dir" ]; then
        security_info "Cleaning up temporary files..."
        rm -rf "$temp_dir"
    fi
}

# Export functions for use in other scripts
export -f detect_architecture get_base_url verify_checksum secure_download 
export -f get_remote_checksum secure_download_with_checksum download_platform_binary
export -f validate_system_requirements check_privileges security_cleanup
export -f security_info security_success security_warning security_error