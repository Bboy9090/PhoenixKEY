#!/usr/bin/env python3
"""
BootForge Standalone Script
Generated portable version of BootForge
"""

import sys
import os
from pathlib import Path

# Add src directory to path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir / "src"))

def main():
    """Main entry point"""
    # Import after path setup
    try:
        from main import main as bootforge_main
        bootforge_main()
    except Exception as e:
        print(f"Error running BootForge: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
