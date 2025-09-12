#!/bin/bash
# BootForge macOS Setup Script
# Run this after extracting the zip file

echo "🚀 Setting up BootForge on macOS..."
echo

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3:"
    echo "   brew install python3"
    echo "   or download from https://python.org"
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Install CLI dependencies (no PyQt6 for CLI-only)
echo "📦 Installing dependencies..."
pip3 install click colorama cryptography pillow psutil pyyaml requests

echo
echo "✅ BootForge CLI setup complete!"
echo
echo "🎯 Quick start commands:"
echo "   python3 main.py --help          # Show all commands"
echo "   python3 main.py list-devices    # List USB devices"
echo "   python3 main.py list-plugins    # Show available plugins"
echo
echo "🔧 For disk operations, you may need sudo permissions:"
echo "   sudo python3 main.py write-image -i image.iso -d /dev/diskX"
echo
echo "💡 Run with --verbose for detailed logging"
echo
echo "🎉 Ready to use! Enjoy BootForge on macOS!"