#!/usr/bin/env python3
"""
BootForge - Professional Cross-Platform OS Deployment Tool
Main application entry point
"""

import sys
import os
import logging
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def main():
    """Main application entry point"""
    # Check if GUI is requested and available (robust position detection)
    gui_requested = "--gui" in sys.argv
    if gui_requested:
        try:
            from src.gui.main_window import BootForgeMainWindow
            from src.core.config import Config
            from src.core.logger import setup_logging
            from src.gui.modern_theme import BootForgeTheme
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtCore import Qt
            
            # Enable high DPI scaling (PyQt6 compatibility)
            try:
                # These may not exist in all PyQt6 versions
                QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)  # type: ignore
                QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)  # type: ignore
            except (AttributeError, Exception):
                # Handle PyQt6 version differences gracefully
                pass
            
            app = QApplication(sys.argv)
            app.setApplicationName("BootForge")
            app.setApplicationVersion("1.0.0")
            app.setOrganizationName("BootForge")
            
            # Apply modern theme globally
            BootForgeTheme.apply_theme(app)
            
            # Setup logging
            setup_logging()
            logger = logging.getLogger(__name__)
            logger.info("Starting BootForge GUI application...")
            
            # Initialize configuration
            config = Config()
            
            # Create main window
            main_window = BootForgeMainWindow()
            main_window.show()
            
            # Run application
            sys.exit(app.exec())
            
        except (ImportError, RuntimeError, Exception) as e:
            error_type = type(e).__name__
            print("\n🖥️  GUI Mode Not Available")
            print("═" * 40)
            print(f"Error Type: {error_type}")
            print(f"Reason: {e}")
            print("\n📋 Falling back to CLI mode...")
            print("💡 Note: GUI requires a desktop environment with Qt/OpenGL support")
            print("\n🚀 CLI mode provides full functionality!")
            print("   Use 'python main.py --help' for available commands")
            print()
    
    # Use CLI interface
    try:
        from src.cli.cli_interface import cli
        
        # Remove --gui flag if present (robust removal)
        if "--gui" in sys.argv:
            sys.argv.remove("--gui")
        
        cli()
    except ImportError as e:
        print("\n❌ Critical Error")
        print("═" * 40)
        print(f"Error importing CLI interface: {e}")
        print("\n🔧 Please check your Python environment and dependencies:")
        print("   • Ensure all requirements are installed: pip install -r requirements.txt")
        print("   • Verify Python path and module availability")
        print("\n📖 See README.md for installation instructions")
        sys.exit(1)


if __name__ == "__main__":
    main()