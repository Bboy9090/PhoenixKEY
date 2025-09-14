#!/bin/bash
# BootForge USB Installer Script

echo "🚀 BootForge USB Installer"
echo "========================="

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="linux"
    EXECUTABLE="BootForge-Linux-x64"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macos"
    EXECUTABLE="BootForge.app"
elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]]; then
    PLATFORM="windows"
    EXECUTABLE="BootForge-Windows-x64.exe"
else
    echo "❌ Unsupported platform: $OSTYPE"
    exit 1
fi

echo "📱 Detected platform: $PLATFORM"

# Create install directory
INSTALL_DIR="$HOME/BootForge"
mkdir -p "$INSTALL_DIR"

# Copy executable
if [ -f "./$EXECUTABLE" ]; then
    cp "./$EXECUTABLE" "$INSTALL_DIR/"
    chmod +x "$INSTALL_DIR/$EXECUTABLE"
    echo "✅ BootForge installed to $INSTALL_DIR"
    
    # Create desktop shortcut (Linux)
    if [[ "$PLATFORM" == "linux" ]]; then
        cat > "$HOME/Desktop/BootForge.desktop" << EOF
[Desktop Entry]
Name=BootForge
Comment=Professional OS Deployment Tool
Exec=$INSTALL_DIR/$EXECUTABLE --gui
Icon=applications-system
Terminal=false
Type=Application
Categories=System;
EOF
        chmod +x "$HOME/Desktop/BootForge.desktop"
        echo "✅ Desktop shortcut created"
    fi
    
    echo ""
    echo "🎉 Installation complete!"
    echo "Run: $INSTALL_DIR/$EXECUTABLE --gui"
    echo ""
else
    echo "❌ Executable not found: $EXECUTABLE"
    exit 1
fi