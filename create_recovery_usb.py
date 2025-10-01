
#!/usr/bin/env python3
"""
Quick BootForge Recovery USB Creator
Simple script to create a bootable USB for Mac recovery
"""

import os
import sys
from pathlib import Path

def main():
    print("🚀 BootForge Recovery USB Creator")
    print("=" * 40)
    print("This will create a bootable USB with BootForge GUI")
    print("Perfect for Mac recovery with OCLP support!")
    print()
    
    # Check if we're in the right directory
    if not Path("main.py").exists():
        print("❌ Error: Please run this from the BootForge directory")
        sys.exit(1)
    
    # Import and run the builder
    try:
        from build_system.create_bootable_usb import BootableUSBCreator
        creator = BootableUSBCreator()
        creator.build_bootable_usb()
        
        print("\n✅ SUCCESS! Your bootable USB files are ready!")
        print("\n📋 NEXT STEPS:")
        print("1. Get a USB drive (8GB+ recommended)")
        print("2. Format it as FAT32")
        print("3. Copy all files from 'bootable_usb' folder to USB")
        print("4. Boot your Mac from USB (hold Option key)")
        print("5. Run BootForge to create OCLP installer")
        
    except ImportError as e:
        print(f"❌ Error importing builder: {e}")
        print("Running builder directly...")
        
        # Fallback - run the builder script directly
        os.system("python3 build_system/create_bootable_usb.py")

if __name__ == "__main__":
    main()
