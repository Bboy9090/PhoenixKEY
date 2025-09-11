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
    # Check if GUI is requested and available
    if len(sys.argv) > 1 and sys.argv[1] == "--gui":
        try:
            from src.gui.main_window import BootForgeMainWindow
            from src.core.config import Config
            from src.core.logger import setup_logging
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtCore import Qt
            
            # Enable high DPI scaling
            try:
                QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
                QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
            except AttributeError:
                # Handle older PyQt6 versions
                pass
            
            app = QApplication(sys.argv)
            app.setApplicationName("BootForge")
            app.setApplicationVersion("1.0.0")
            app.setOrganizationName("BootForge")
            
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
            
        except ImportError as e:
            print(f"GUI mode not available: {e}")
            print("Falling back to CLI mode...")
            print("Note: GUI requires a desktop environment with OpenGL support")
            print()
    
    # Use CLI interface
    try:
        from src.cli.cli_interface import cli
        
        # Remove --gui flag if present
        if len(sys.argv) > 1 and sys.argv[1] == "--gui":
            sys.argv.pop(1)
        
        cli()
    except ImportError as e:
        print(f"Error importing CLI interface: {e}")
        print("Please check your Python environment and dependencies.")
        sys.exit(1)


if __name__ == "__main__":
    main()