"""
BootForge Main Window
PyQt6 GUI implementation for the main application window
"""

import logging
import sys
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QStackedWidget, QMenuBar, QStatusBar, QProgressBar,
    QLabel, QPushButton, QToolBar, QMessageBox, QSplitter,
    QTextEdit, QGroupBox, QTabWidget
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QAction, QIcon, QFont, QPixmap

from src.core.config import Config
from src.core.system_monitor import SystemMonitor, SystemInfo
from src.core.disk_manager import DiskManager
from src.gui.wizard_widget import BootForgeWizard
from src.gui.status_widget import StatusWidget
from src.gui.log_viewer import LogViewer
from src.gui.usb_recipe_manager import USBRecipeManagerWidget
from src.gui.stepper_wizard_widget import BootForgeStepperWizard
from src.gui.icon_manager import icon_manager
from src.gui.modern_theme import BootForgeTheme


class BootForgeMainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Initialize core components
        self.config = Config()
        self.system_monitor = SystemMonitor()
        self.disk_manager = DiskManager()
        
        # GUI components
        self.wizard = None
        self.stepper_wizard = None
        self.status_widget = None
        self.log_viewer = None
        
        # Initialize UI
        self._setup_ui()
        self._setup_connections()
        self._start_monitoring()
        
        self.logger.info("BootForge main window initialized")
    
    def _setup_ui(self):
        """Setup the main user interface"""
        self.setWindowTitle("BootForge - Professional OS Deployment Tool")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        
        # Set window icon (placeholder for now)
        self.setWindowIcon(self._create_app_icon())
        
        # Create central widget with splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create main splitter (horizontal)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter)
        
        # Left panel - Main wizard and operations
        left_panel = self._create_left_panel()
        main_splitter.addWidget(left_panel)
        
        # Right panel - Status and logs
        right_panel = self._create_right_panel()
        main_splitter.addWidget(right_panel)
        
        # Set splitter proportions
        main_splitter.setSizes([700, 300])
        
        # Create menu bar
        self._create_menu_bar()
        
        # Create tool bar
        self._create_toolbar()
        
        # Create status bar
        self._create_status_bar()
        
        # Apply modern theme
        self._apply_modern_theme()
    
    def _create_left_panel(self) -> QWidget:
        """Create the left panel with stepper wizard interface"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create main stepper wizard interface
        self.stepper_wizard = BootForgeStepperWizard(self.disk_manager)
        layout.addWidget(self.stepper_wizard)
        
        # Keep old wizard and USB recipe manager for potential future access
        # (they're just not displayed in the main interface now)
        self.wizard = BootForgeWizard(self.disk_manager)
        self.usb_recipe_manager = USBRecipeManagerWidget(self.disk_manager, self.config)
        
        return panel
    
    def _create_right_panel(self) -> QWidget:
        """Create the right panel with status and logs"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Create tab widget for status and logs
        tab_widget = QTabWidget()
        
        # Status tab
        self.status_widget = StatusWidget()
        tab_widget.addTab(self.status_widget, "System Status")
        
        # Log viewer tab
        self.log_viewer = LogViewer()
        tab_widget.addTab(self.log_viewer, "Logs")
        
        layout.addWidget(tab_widget)
        return panel
    
    def _create_menu_bar(self):
        """Create application menu bar"""
        menubar = self.menuBar()
        assert menubar is not None  # menuBar() should never return None for QMainWindow
        
        # File menu
        file_menu = menubar.addMenu("&File")
        assert file_menu is not None
        
        new_action = QAction("&New Project", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._new_project)
        file_menu.addAction(new_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        assert tools_menu is not None
        
        refresh_devices = QAction("&Refresh Devices", self)
        refresh_devices.setShortcut("F5")
        refresh_devices.triggered.connect(self._refresh_devices)
        tools_menu.addAction(refresh_devices)
        
        format_device = QAction("&Format Device", self)
        format_device.triggered.connect(self._format_device)
        tools_menu.addAction(format_device)
        
        tools_menu.addSeparator()
        
        preferences = QAction("&Preferences", self)
        preferences.triggered.connect(self._show_preferences)
        tools_menu.addAction(preferences)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        assert help_menu is not None
        
        about = QAction("&About BootForge", self)
        about.triggered.connect(self._show_about)
        help_menu.addAction(about)
        
        documentation = QAction("&Documentation", self)
        documentation.triggered.connect(self._show_documentation)
        help_menu.addAction(documentation)
    
    def _create_toolbar(self):
        """Create application toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(toolbar)
        
        # Refresh devices action
        refresh_action = QAction("Refresh", self)
        refresh_action.setIcon(self._create_icon("refresh"))
        refresh_action.setToolTip("Refresh USB devices")
        refresh_action.triggered.connect(self._refresh_devices)
        toolbar.addAction(refresh_action)
        
        toolbar.addSeparator()
        
        # Start operation action
        start_action = QAction("Start", self)
        start_action.setIcon(self._create_icon("play"))
        start_action.setToolTip("Start disk writing operation")
        start_action.triggered.connect(self._start_operation)
        toolbar.addAction(start_action)
        
        # Stop operation action
        stop_action = QAction("Stop", self)
        stop_action.setIcon(self._create_icon("stop"))
        stop_action.setToolTip("Stop current operation")
        stop_action.triggered.connect(self._stop_operation)
        toolbar.addAction(stop_action)
        
        toolbar.addSeparator()
        
        # Settings action
        settings_action = QAction("Settings", self)
        settings_action.setIcon(self._create_icon("settings"))
        settings_action.setToolTip("Application settings")
        settings_action.triggered.connect(self._show_preferences)
        toolbar.addAction(settings_action)
    
    def _create_status_bar(self):
        """Create application status bar"""
        status_bar = self.statusBar()
        assert status_bar is not None  # statusBar() should never return None for QMainWindow
        
        # Main status label
        self.status_label = QLabel("Ready")
        status_bar.addWidget(self.status_label)
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(200)
        status_bar.addPermanentWidget(self.progress_bar)
        
        # System info labels
        self.cpu_label = QLabel("CPU: --")
        self.memory_label = QLabel("Memory: --")
        self.temp_label = QLabel("Temp: --")
        
        status_bar.addPermanentWidget(self.cpu_label)
        status_bar.addPermanentWidget(self.memory_label)
        status_bar.addPermanentWidget(self.temp_label)
    
    def _create_app_icon(self) -> QIcon:
        """Create application icon"""
        return icon_manager.get_icon("app", 48)
    
    def _create_icon(self, name: str) -> QIcon:
        """Create toolbar icons"""
        return icon_manager.get_icon(name, 24)
    
    def _apply_modern_theme(self):
        """Apply modern professional theme styling"""
        # Apply the modern theme to the main window
        self.setStyleSheet(BootForgeTheme.get_stylesheet())
    
    def _setup_connections(self):
        """Setup signal connections"""
        # System monitor connections
        self.system_monitor.system_info_updated.connect(self._update_system_info)
        self.system_monitor.usb_devices_updated.connect(self._update_usb_devices)
        self.system_monitor.thermal_warning.connect(self._handle_thermal_warning)
        
        # Stepper wizard connections
        if self.stepper_wizard:
            self.stepper_wizard.wizard_completed.connect(self._handle_wizard_completed)
            self.stepper_wizard.step_changed.connect(self._handle_step_changed)
            self.stepper_wizard.status_updated.connect(self._handle_stepper_status_updated)
            self.stepper_wizard.progress_updated.connect(self._handle_stepper_progress_updated)
        
        # Classic wizard connections (kept for compatibility)
        if self.wizard:
            self.wizard.operation_started.connect(self._handle_operation_started)
            self.wizard.operation_completed.connect(self._handle_operation_completed)
            self.wizard.progress_updated.connect(self._handle_progress_updated)
    
    def _start_monitoring(self):
        """Start system monitoring"""
        self.system_monitor.start()
        self.logger.info("System monitoring started")
    
    def _update_system_info(self, info: SystemInfo):
        """Update system information display"""
        # Update status bar
        self.cpu_label.setText(f"CPU: {info.cpu_percent:.1f}%")
        self.memory_label.setText(f"Memory: {info.memory_percent:.1f}%")
        
        if info.temperature:
            self.temp_label.setText(f"Temp: {info.temperature:.1f}°C")
        else:
            self.temp_label.setText("Temp: --")
        
        # Update status widget
        if self.status_widget:
            self.status_widget.update_system_info(info)
    
    def _update_usb_devices(self, devices):
        """Update USB device list"""
        if self.wizard:
            self.wizard.update_device_list(devices)
        
        if self.status_widget:
            self.status_widget.update_device_list(devices)
    
    def _handle_thermal_warning(self, temperature: float):
        """Handle thermal warning"""
        self.logger.warning(f"Thermal warning: {temperature}°C")
        
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Thermal Warning")
        msg.setText(f"System temperature is high: {temperature:.1f}°C")
        msg.setInformativeText("Consider pausing operations to let the system cool down.")
        msg.show()
    
    def _handle_operation_started(self, description: str):
        """Handle operation start"""
        self.status_label.setText(description)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.logger.info(f"Operation started: {description}")
    
    def _handle_operation_completed(self, success: bool, message: str):
        """Handle operation completion"""
        self.progress_bar.setVisible(False)
        
        if success:
            self.status_label.setText("Operation completed successfully")
            self.logger.info(f"Operation completed: {message}")
        else:
            self.status_label.setText("Operation failed")
            self.logger.error(f"Operation failed: {message}")
            
            # Show error dialog
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Critical if not success else QMessageBox.Icon.Information)
            msg.setWindowTitle("Operation Result")
            msg.setText(message)
            msg.exec()
    
    def _handle_progress_updated(self, progress):
        """Handle progress updates"""
        self.progress_bar.setValue(int(progress.percentage))
        
        status_text = f"{progress.current_operation} - {progress.percentage:.1f}%"
        if progress.speed_mbps > 0:
            status_text += f" ({progress.speed_mbps:.1f} MB/s)"
        
        self.status_label.setText(status_text)
    
    def _handle_wizard_completed(self):
        """Handle stepper wizard completion"""
        self.status_label.setText("Wizard completed successfully")
        self.progress_bar.setVisible(False)
        self.logger.info("Stepper wizard completed")
    
    def _handle_step_changed(self, step_index: int, step_name: str):
        """Handle step change in stepper wizard"""
        self.status_label.setText(f"Step {step_index + 1}: {step_name}")
        self.logger.info(f"Stepper wizard step changed to: {step_name}")
        
        # Update log viewer with step change if needed
        if self.log_viewer:
            self.log_viewer.add_log_entry("INFO", datetime.now().strftime("%H:%M:%S"), f"Step changed to: {step_name}")
    
    def _handle_stepper_status_updated(self, status: str):
        """Handle status updates from stepper wizard"""
        self.status_label.setText(status)
        
        # Log the status update
        if self.log_viewer:
            self.log_viewer.add_log_entry("INFO", datetime.now().strftime("%H:%M:%S"), status)
    
    def _handle_stepper_progress_updated(self, progress: int):
        """Handle progress updates from stepper wizard"""
        if 0 <= progress <= 100:
            self.progress_bar.setVisible(progress > 0 and progress < 100)
            self.progress_bar.setValue(progress)
    
    def _new_project(self):
        """Start new project"""
        if self.wizard:
            self.wizard.reset_wizard()
        self.logger.info("New project started")
    
    def _refresh_devices(self):
        """Refresh device list"""
        self.logger.info("Refreshing device list")
        # The system monitor will automatically update devices
    
    def _format_device(self):
        """Format selected device"""
        # This would open a format dialog
        self.logger.info("Format device requested")
    
    def _start_operation(self):
        """Start disk operation"""
        if self.wizard:
            self.wizard.start_operation()
    
    def _stop_operation(self):
        """Stop current operation"""
        if self.wizard:
            self.wizard.stop_operation()
        self.logger.info("Operation stopped by user")
    
    def _show_preferences(self):
        """Show preferences dialog"""
        self.logger.info("Preferences dialog requested")
        # This would open a preferences dialog
    
    def _show_about(self):
        """Show about dialog"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QPixmap
        from pathlib import Path
        
        dialog = QDialog(self)
        dialog.setWindowTitle("About BootForge")
        dialog.setFixedSize(500, 350)
        dialog.setModal(True)
        
        # Apply theme styling
        dialog.setStyleSheet(BootForgeTheme.get_stylesheet())
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Hero banner
        banner_label = QLabel()
        banner_path = Path(__file__).parent.parent.parent / "assets" / "icons" / "hero_banner.png"
        if banner_path.exists():
            pixmap = QPixmap(str(banner_path))
            scaled_pixmap = pixmap.scaled(500, 150, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            banner_label.setPixmap(scaled_pixmap)
            banner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            banner_label.setStyleSheet("border: none; background-color: #1e1e1e;")
        layout.addWidget(banner_label)
        
        # Content area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(30, 20, 30, 20)
        content_layout.setSpacing(15)
        
        # Title
        title_label = QLabel("BootForge v1.0.0")
        title_label.setStyleSheet(f"""
            color: {BootForgeTheme.COLORS['text_primary']};
            font-size: {BootForgeTheme.FONTS['sizes']['2xl']}px;
            font-weight: 600;
            margin-bottom: 10px;
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel("Professional Cross-Platform OS Deployment Tool")
        subtitle_label.setStyleSheet(f"""
            color: {BootForgeTheme.COLORS['primary']};
            font-size: {BootForgeTheme.FONTS['sizes']['lg']}px;
            font-weight: 500;
        """)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(subtitle_label)
        
        # Description
        desc_label = QLabel("Create bootable USB drives for macOS, Windows, and Linux with advanced features including hardware detection, safety validation, and plugin support.")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"""
            color: {BootForgeTheme.COLORS['text_secondary']};
            font-size: {BootForgeTheme.FONTS['sizes']['base']}px;
            line-height: 1.5;
        """)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(desc_label)
        
        layout.addWidget(content_widget)
        
        # Button area
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(30, 0, 30, 30)
        button_layout.addStretch()
        
        close_button = QPushButton("Close")
        close_button.setMinimumSize(100, 35)
        close_button.setProperty("class", "primary")
        close_button.clicked.connect(dialog.close)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def _show_documentation(self):
        """Show documentation"""
        self.logger.info("Documentation requested")
        # This would open documentation
    
    def closeEvent(self, a0):
        """Handle application close"""
        event = a0  # Rename parameter to match parent class signature
        assert event is not None  # closeEvent should never receive None
        self.logger.info("Application closing")
        
        # Stop system monitoring
        if self.system_monitor.isRunning():
            self.system_monitor.stop()
            self.system_monitor.wait(3000)  # Wait up to 3 seconds
        
        # Save configuration
        self.config.save()
        
        event.accept()