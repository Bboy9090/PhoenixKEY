"""
BootForge Logging System
Comprehensive logging setup with file rotation and GUI integration
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal


class GuiLogHandler(logging.Handler, QObject):
    """Custom log handler that emits Qt signals for GUI display"""
    
    log_message = pyqtSignal(str, str, str)  # level, timestamp, message
    
    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)
        
    def emit(self, record):
        """Emit log record as Qt signal"""
        try:
            timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
            message = self.format(record)
            self.log_message.emit(record.levelname, timestamp, message)
        except Exception:
            # Avoid infinite recursion in case of logging errors
            pass


class BootForgeLogger:
    """Enhanced logging system for BootForge"""
    
    def __init__(self, log_dir: Optional[Path] = None, level: str = "INFO"):
        self.log_dir = log_dir or Path.home() / ".bootforge" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.level = getattr(logging, level.upper(), logging.INFO)
        self.gui_handler = None
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure logging system"""
        # Create root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.level)
        
        # Clear existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # File handler with rotation
        log_file = self.log_dir / "bootforge.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(self.level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        
        # Error file handler
        error_file = self.log_dir / "errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)
        
        # GUI handler (will be connected later)
        self.gui_handler = GuiLogHandler()
        self.gui_handler.setLevel(self.level)
        self.gui_handler.setFormatter(logging.Formatter('%(message)s'))
        root_logger.addHandler(self.gui_handler)
        
        logging.info("BootForge logging system initialized")
    
    def get_gui_handler(self) -> GuiLogHandler:
        """Get GUI log handler for connecting to UI"""
        return self.gui_handler
    
    def set_level(self, level: str):
        """Change logging level"""
        self.level = getattr(logging, level.upper(), logging.INFO)
        root_logger = logging.getLogger()
        root_logger.setLevel(self.level)
        
        for handler in root_logger.handlers:
            handler.setLevel(self.level)
    
    def get_log_files(self) -> Dict[str, Path]:
        """Get paths to log files"""
        return {
            'main': self.log_dir / "bootforge.log",
            'errors': self.log_dir / "errors.log"
        }


def setup_logging(log_dir: Optional[Path] = None, level: str = "INFO") -> BootForgeLogger:
    """Setup BootForge logging system"""
    logger_system = BootForgeLogger(log_dir, level)
    return logger_system


# Convenience function for getting logger
def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)