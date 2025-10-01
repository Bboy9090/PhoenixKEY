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
from src.core.real_time_monitor import RealTimeHealthManager, MonitoringLevel
from src.core.intelligent_guidance import IntelligentGuidanceManager, GuidanceLevel
from src.core.error_prevention_recovery import ErrorPreventionRecoveryManager
from src.core.one_click_profiles import OneClickProfileManager
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
        
        # Load settings from config
        monitoring_level_str = self.config.get("monitoring_level", "standard")
        guidance_level_str = self.config.get("guidance_level", "standard")
        
        # Map string to enum values
        monitoring_level_map = {
            "basic": MonitoringLevel.BASIC,
            "standard": MonitoringLevel.STANDARD,
            "intensive": MonitoringLevel.INTENSIVE,
            "diagnostic": MonitoringLevel.DIAGNOSTIC
        }
        guidance_level_map = {
            "minimal": GuidanceLevel.MINIMAL,
            "standard": GuidanceLevel.STANDARD,
            "comprehensive": GuidanceLevel.COMPREHENSIVE,
            "expert": GuidanceLevel.EXPERT
        }
        
        monitoring_level = monitoring_level_map.get(monitoring_level_str, MonitoringLevel.STANDARD)
        guidance_level = guidance_level_map.get(guidance_level_str, GuidanceLevel.STANDARD)
        
        # Initialize advanced systems with loaded settings
        self.health_manager = RealTimeHealthManager(monitoring_level)
        self.guidance_manager = IntelligentGuidanceManager(guidance_level)
        self.recovery_manager = ErrorPreventionRecoveryManager(Path.home() / ".bootforge" / "checkpoints")
        self.profile_manager = OneClickProfileManager()
        
        # Setup advanced system callbacks
        self.health_manager.add_alert_callback(self._on_health_alert)
        self.recovery_manager.add_error_callback(self._on_error_occurred)
        
        # GUI components
        self.wizard = None
        self.stepper_wizard = None
        self.status_widget = None
        self.log_viewer = None
        
        # Initialize UI
        self._setup_ui()
        self._setup_connections()
        self._start_monitoring()
        
        # Start advanced systems
        self.health_manager.start_monitoring()
        
        self.logger.info("BootForge main window initialized with advanced systems")
    
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
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QLabel
        
        self.logger.info("Format device requested")
        
        # Get available devices from disk manager
        try:
            devices = self.disk_manager.get_removable_drives()
            if not devices:
                QMessageBox.information(self, "No Devices", "No USB devices found. Please connect a USB drive and try again.")
                return
            
            # Create format dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Format USB Device")
            dialog.setMinimumWidth(500)
            dialog.setModal(True)
            dialog.setStyleSheet(BootForgeTheme.get_stylesheet())
            
            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(15)
            
            # Warning label
            warning_label = QLabel("⚠️ WARNING: Formatting will PERMANENTLY ERASE ALL DATA on the selected device!")
            warning_label.setWordWrap(True)
            warning_label.setStyleSheet(f"""
                color: {BootForgeTheme.COLORS['error']};
                font-size: {BootForgeTheme.FONTS['sizes']['lg']}px;
                font-weight: 600;
                padding: 15px;
                background-color: rgba(239, 68, 68, 0.1);
                border: 2px solid {BootForgeTheme.COLORS['error']};
                border-radius: 8px;
            """)
            layout.addWidget(warning_label)
            
            # Device selection
            device_label = QLabel("Select Device:")
            device_label.setStyleSheet(f"color: {BootForgeTheme.COLORS['text_primary']}; font-weight: 600;")
            layout.addWidget(device_label)
            
            device_combo = QComboBox()
            for device in devices:
                size_gb = device.size_bytes / (1024 ** 3)
                device_info = f"{device.name} - {size_gb:.1f} GB ({device.path})"
                device_combo.addItem(device_info, device)
            device_combo.setStyleSheet(f"""
                QComboBox {{
                    padding: 8px;
                    border: 1px solid {BootForgeTheme.COLORS['border']};
                    border-radius: 6px;
                    background-color: {BootForgeTheme.COLORS['background_secondary']};
                    color: {BootForgeTheme.COLORS['text_primary']};
                }}
            """)
            layout.addWidget(device_combo)
            
            # Format type
            format_label = QLabel("Format Type:")
            format_label.setStyleSheet(f"color: {BootForgeTheme.COLORS['text_primary']}; font-weight: 600;")
            layout.addWidget(format_label)
            
            format_combo = QComboBox()
            format_combo.addItems(["FAT32 (Compatible)", "exFAT (Large files)", "NTFS (Windows)"])
            format_combo.setStyleSheet(f"""
                QComboBox {{
                    padding: 8px;
                    border: 1px solid {BootForgeTheme.COLORS['border']};
                    border-radius: 6px;
                    background-color: {BootForgeTheme.COLORS['background_secondary']};
                    color: {BootForgeTheme.COLORS['text_primary']};
                }}
            """)
            layout.addWidget(format_combo)
            
            layout.addStretch()
            
            # Buttons
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            
            cancel_button = QPushButton("Cancel")
            cancel_button.setMinimumSize(100, 35)
            cancel_button.clicked.connect(dialog.reject)
            button_layout.addWidget(cancel_button)
            
            format_button = QPushButton("Format Device")
            format_button.setMinimumSize(120, 35)
            format_button.setProperty("class", "danger")
            format_button.clicked.connect(dialog.accept)
            button_layout.addWidget(format_button)
            
            layout.addLayout(button_layout)
            
            # Show dialog
            if dialog.exec() == QDialog.DialogCode.Accepted:
                selected_device = device_combo.currentData()
                selected_format = format_combo.currentText().split()[0]  # Get FAT32, exFAT, or NTFS
                
                # Confirm again
                confirm = QMessageBox.warning(
                    self,
                    "Confirm Format",
                    f"Are you absolutely sure you want to format:\n\n{device_combo.currentText()}\n\nThis action CANNOT be undone!",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if confirm == QMessageBox.StandardButton.Yes:
                    # Map format type to filesystem
                    fs_map = {
                        "FAT32": "fat32",
                        "exFAT": "exfat", 
                        "NTFS": "ntfs"
                    }
                    filesystem = fs_map.get(selected_format, "fat32")
                    
                    # Show real progress dialog with cancel button
                    from PyQt6.QtWidgets import QProgressDialog
                    from PyQt6.QtCore import QThread, pyqtSignal, Qt
                    
                    progress_dialog = QProgressDialog(
                        f"Formatting {device_combo.currentText()}...\n\nThis may take a few minutes.",
                        "Cancel",
                        0, 0,  # Indeterminate progress (0-0 range)
                        self
                    )
                    progress_dialog.setWindowTitle("Formatting Device")
                    progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
                    progress_dialog.setMinimumDuration(0)  # Show immediately
                    progress_dialog.setCancelButton(None)  # No cancel during format (dangerous)
                    progress_dialog.show()
                    
                    # Format in background thread
                    class FormatThread(QThread):
                        format_finished = pyqtSignal(bool, str)  # Renamed to avoid conflict with QThread.finished
                        
                        def __init__(self, disk_manager, device_path, filesystem):
                            super().__init__()
                            self.disk_manager = disk_manager
                            self.device_path = device_path
                            self.filesystem = filesystem
                        
                        def run(self):
                            try:
                                success = self.disk_manager.format_device(self.device_path, self.filesystem)
                                if success:
                                    self.format_finished.emit(True, "Device formatted successfully!")
                                else:
                                    self.format_finished.emit(False, "Format operation failed. Check permissions and device status.")
                            except Exception as e:
                                self.format_finished.emit(False, f"Format error: {str(e)}")
                    
                    def on_format_finished(success: bool, message: str):
                        progress_dialog.close()
                        if success:
                            QMessageBox.information(self, "Format Complete", message)
                            self.logger.info(f"Successfully formatted {selected_device.path} as {filesystem}")
                        else:
                            QMessageBox.critical(self, "Format Failed", message)
                            self.logger.error(f"Format failed for {selected_device.path}: {message}")
                        # Clean up thread reference
                        if hasattr(self, '_format_thread'):
                            self._format_thread = None
                    
                    self._format_thread = FormatThread(self.disk_manager, selected_device.path, filesystem)
                    self._format_thread.format_finished.connect(on_format_finished)
                    self._format_thread.start()
        
        except Exception as e:
            self.logger.error(f"Error in format device dialog: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open format dialog: {str(e)}")
    
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
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QComboBox, QPushButton, QLabel, QHBoxLayout, QGroupBox
        from PyQt6.QtCore import Qt
        
        self.logger.info("Preferences dialog requested")
        
        dialog = QDialog(self)
        dialog.setWindowTitle("BootForge Settings")
        dialog.setMinimumWidth(500)
        dialog.setModal(True)
        dialog.setStyleSheet(BootForgeTheme.get_stylesheet())
        
        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Title
        title_label = QLabel("⚙️ Application Settings")
        title_label.setStyleSheet(f"""
            color: {BootForgeTheme.COLORS['primary']};
            font-size: {BootForgeTheme.FONTS['sizes']['xl']}px;
            font-weight: 600;
            padding-bottom: 10px;
        """)
        main_layout.addWidget(title_label)
        
        # Monitoring Settings
        monitoring_group = QGroupBox("System Monitoring")
        monitoring_group.setStyleSheet(f"""
            QGroupBox {{
                color: {BootForgeTheme.COLORS['text_primary']};
                font-weight: 600;
                border: 1px solid {BootForgeTheme.COLORS['border']};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 20px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
            }}
        """)
        monitoring_layout = QFormLayout(monitoring_group)
        monitoring_layout.setContentsMargins(15, 10, 15, 15)
        
        # Monitoring Level
        monitoring_combo = QComboBox()
        monitoring_combo.addItems(["Basic", "Standard", "Intensive", "Diagnostic"])
        monitoring_combo.setCurrentText(self.health_manager.monitoring_level.value.capitalize())
        monitoring_combo.setStyleSheet(f"""
            QComboBox {{
                padding: 8px;
                border: 1px solid {BootForgeTheme.COLORS['border']};
                border-radius: 6px;
                background-color: {BootForgeTheme.COLORS['background_secondary']};
                color: {BootForgeTheme.COLORS['text_primary']};
            }}
        """)
        monitoring_layout.addRow("Monitoring Level:", monitoring_combo)
        
        # Guidance Level
        guidance_combo = QComboBox()
        guidance_combo.addItems(["Minimal", "Standard", "Comprehensive", "Expert"])
        guidance_combo.setCurrentText(self.guidance_manager.guidance_level.value.capitalize())
        guidance_combo.setStyleSheet(f"""
            QComboBox {{
                padding: 8px;
                border: 1px solid {BootForgeTheme.COLORS['border']};
                border-radius: 6px;
                background-color: {BootForgeTheme.COLORS['background_secondary']};
                color: {BootForgeTheme.COLORS['text_primary']};
            }}
        """)
        monitoring_layout.addRow("Guidance Level:", guidance_combo)
        
        main_layout.addWidget(monitoring_group)
        
        # Safety Settings
        safety_group = QGroupBox("Safety & Validation")
        safety_group.setStyleSheet(f"""
            QGroupBox {{
                color: {BootForgeTheme.COLORS['text_primary']};
                font-weight: 600;
                border: 1px solid {BootForgeTheme.COLORS['border']};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 20px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
            }}
        """)
        safety_layout = QFormLayout(safety_group)
        safety_layout.setContentsMargins(15, 10, 15, 15)
        
        # Safety Level
        safety_combo = QComboBox()
        safety_combo.addItems(["Standard", "Strict", "Paranoid"])
        current_safety = self.config.get("safety_level", "standard")
        safety_combo.setCurrentText(current_safety.capitalize())
        safety_combo.setStyleSheet(f"""
            QComboBox {{
                padding: 8px;
                border: 1px solid {BootForgeTheme.COLORS['border']};
                border-radius: 6px;
                background-color: {BootForgeTheme.COLORS['background_secondary']};
                color: {BootForgeTheme.COLORS['text_primary']};
            }}
        """)
        safety_layout.addRow("Safety Level:", safety_combo)
        
        main_layout.addWidget(safety_group)
        
        # Info text
        info_label = QLabel("""
<b>Monitoring Level:</b> Controls system health monitoring intensity<br>
<b>Guidance Level:</b> Controls how much help you get during operations<br>
<b>Safety Level:</b> Controls validation strictness for disk operations
        """)
        info_label.setWordWrap(True)
        info_label.setStyleSheet(f"""
            color: {BootForgeTheme.COLORS['text_secondary']};
            font-size: {BootForgeTheme.FONTS['sizes']['sm']}px;
            padding: 10px;
            background-color: {BootForgeTheme.COLORS['background_tertiary']};
            border-radius: 6px;
        """)
        main_layout.addWidget(info_label)
        
        main_layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_button = QPushButton("Cancel")
        cancel_button.setMinimumSize(100, 35)
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)
        
        save_button = QPushButton("Save Settings")
        save_button.setMinimumSize(120, 35)
        save_button.setProperty("class", "primary")
        save_button.clicked.connect(dialog.accept)
        button_layout.addWidget(save_button)
        
        main_layout.addLayout(button_layout)
        
        # Show dialog and save settings if accepted
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Update monitoring level
            new_monitoring = monitoring_combo.currentText().lower()
            if new_monitoring == "basic":
                self.health_manager.monitoring_level = MonitoringLevel.BASIC
            elif new_monitoring == "standard":
                self.health_manager.monitoring_level = MonitoringLevel.STANDARD
            elif new_monitoring == "intensive":
                self.health_manager.monitoring_level = MonitoringLevel.INTENSIVE
            elif new_monitoring == "diagnostic":
                self.health_manager.monitoring_level = MonitoringLevel.DIAGNOSTIC
            
            # Update guidance level
            new_guidance = guidance_combo.currentText().lower()
            if new_guidance == "minimal":
                self.guidance_manager.guidance_level = GuidanceLevel.MINIMAL
            elif new_guidance == "standard":
                self.guidance_manager.guidance_level = GuidanceLevel.STANDARD
            elif new_guidance == "comprehensive":
                self.guidance_manager.guidance_level = GuidanceLevel.COMPREHENSIVE
            elif new_guidance == "expert":
                self.guidance_manager.guidance_level = GuidanceLevel.EXPERT
            
            # Update safety level
            new_safety = safety_combo.currentText().lower()
            
            # Save all settings to config for persistence
            self.config.set("monitoring_level", new_monitoring)
            self.config.set("guidance_level", new_guidance)
            self.config.set("safety_level", new_safety)
            self.config.save()
            
            self.logger.info(f"Settings updated and saved: monitoring={new_monitoring}, guidance={new_guidance}, safety={new_safety}")
            QMessageBox.information(self, "Settings Saved", "✅ Your settings have been saved successfully!")
    
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
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QPushButton, QHBoxLayout
        import webbrowser
        from pathlib import Path
        
        self.logger.info("Documentation requested")
        
        # Create documentation dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("BootForge Documentation")
        dialog.setMinimumSize(800, 600)
        dialog.setModal(False)  # Non-modal so user can reference while using app
        dialog.setStyleSheet(BootForgeTheme.get_stylesheet())
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Text browser for documentation
        doc_browser = QTextBrowser()
        doc_browser.setOpenExternalLinks(False)
        doc_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {BootForgeTheme.COLORS['background_primary']};
                color: {BootForgeTheme.COLORS['text_primary']};
                border: none;
                padding: 20px;
                font-size: {BootForgeTheme.FONTS['sizes']['base']}px;
            }}
        """)
        
        # Load documentation content
        readme_path = Path(__file__).parent.parent.parent / "README.md"
        replit_md_path = Path(__file__).parent.parent.parent / "replit.md"
        
        doc_content = f"""
        <h1 style="color: {BootForgeTheme.COLORS['primary']};">🔥 BootForge Documentation</h1>
        <p style="font-size: 16px; line-height: 1.6;">Professional Cross-Platform OS Deployment Tool</p>
        
        <h2 style="color: {BootForgeTheme.COLORS['accent']};">Quick Start Guide</h2>
        <ol style="line-height: 1.8;">
            <li><b>Hardware Detection:</b> Auto-detect your hardware or manually select a profile for another computer</li>
            <li><b>Select USB Drive:</b> Choose the target USB device for your bootable installer</li>
            <li><b>Choose OS Image:</b> Select from macOS, Windows, or Linux distributions</li>
            <li><b>Select Recipe:</b> Choose deployment method (OCLP for macOS, Unattended for Windows, etc.)</li>
            <li><b>Review & Build:</b> Confirm settings and create your bootable USB</li>
        </ol>
        
        <h2 style="color: {BootForgeTheme.COLORS['accent']};">Key Features</h2>
        <ul style="line-height: 1.8;">
            <li><b>Manual Hardware Selection:</b> Create bootable USBs for other computers (not just the current one)</li>
            <li><b>OpenCore Legacy Patcher (OCLP) Integration:</b> Full support for macOS on unsupported Macs</li>
            <li><b>Smart Hardware Detection:</b> Automatic detection with 66 hardware profiles</li>
            <li><b>Multiple OS Support:</b> macOS, Windows, Linux all in one tool</li>
            <li><b>Safety Validation:</b> Built-in checks to prevent data loss</li>
            <li><b>Deployment Recipes:</b> Pre-configured workflows for common scenarios</li>
        </ul>
        
        <h2 style="color: {BootForgeTheme.COLORS['accent']};">macOS OCLP Instructions</h2>
        <p style="line-height: 1.6;">
        To create a bootable macOS installer with OpenCore Legacy Patcher:
        </p>
        <ol style="line-height: 1.8;">
            <li>Select your target Mac model (e.g., iMac 18,1) in Hardware Detection</li>
            <li>Choose your USB drive (16GB+ recommended)</li>
            <li>Select a macOS version compatible with your hardware</li>
            <li>Choose the "macOS OCLP" recipe</li>
            <li>BootForge will create an Option-key bootable USB installer</li>
        </ol>
        
        <h2 style="color: {BootForgeTheme.COLORS['accent']};">Settings</h2>
        <p style="line-height: 1.6;">
        Access Settings from the toolbar to configure:
        </p>
        <ul style="line-height: 1.8;">
            <li><b>Monitoring Level:</b> Basic, Standard, Intensive, or Diagnostic system monitoring</li>
            <li><b>Guidance Level:</b> Minimal, Standard, Comprehensive, or Expert assistance</li>
            <li><b>Safety Level:</b> Standard, Strict, or Paranoid validation</li>
        </ul>
        
        <h2 style="color: {BootForgeTheme.COLORS['accent']};">Troubleshooting</h2>
        <ul style="line-height: 1.8;">
            <li><b>USB not detected:</b> Check USB connection, try a different port</li>
            <li><b>Build fails:</b> Ensure sufficient disk space and proper permissions</li>
            <li><b>macOS won't boot:</b> Verify OCLP compatibility with your Mac model</li>
            <li><b>Settings not saving:</b> Check file permissions in ~/.bootforge/</li>
        </ul>
        
        <h2 style="color: {BootForgeTheme.COLORS['accent']};">Additional Resources</h2>
        <p style="line-height: 1.6;">
        • Project documentation: <a href="file:///{readme_path}" style="color: {BootForgeTheme.COLORS['primary']};">README.md</a><br>
        • Configuration guide: <a href="file:///{replit_md_path}" style="color: {BootForgeTheme.COLORS['primary']};">replit.md</a><br>
        • OpenCore Legacy Patcher: <a href="https://dortania.github.io/OpenCore-Legacy-Patcher/" style="color: {BootForgeTheme.COLORS['primary']};">dortania.github.io</a>
        </p>
        
        <hr style="border: 1px solid {BootForgeTheme.COLORS['border']}; margin: 20px 0;">
        <p style="color: {BootForgeTheme.COLORS['text_secondary']}; font-size: 14px;">
        <i>Version 1.1 - September 2025</i>
        </p>
        """
        
        doc_browser.setHtml(doc_content)
        
        # Handle link clicks
        def on_anchor_clicked(url):
            url_str = url.toString()
            if url_str.startswith('http'):
                webbrowser.open(url_str)
            elif url_str.startswith('file:///'):
                file_path = url_str.replace('file:///', '')
                if Path(file_path).exists():
                    webbrowser.open(f'file:///{file_path}')
        
        doc_browser.anchorClicked.connect(on_anchor_clicked)
        
        layout.addWidget(doc_browser)
        
        # Close button
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(20, 10, 20, 20)
        button_layout.addStretch()
        
        close_button = QPushButton("Close")
        close_button.setMinimumSize(100, 35)
        close_button.setProperty("class", "primary")
        close_button.clicked.connect(dialog.close)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        dialog.show()
    
    def _on_health_alert(self, severity, message, data):
        """Handle health alerts from monitoring system"""
        self.logger.warning(f"Health Alert [{severity.value}]: {message}")
        
        # Show alert to user if critical
        if severity.value in ["critical", "emergency"]:
            QMessageBox.warning(self, "System Health Alert", f"⚠️ {message}")
    
    def _on_error_occurred(self, error_context):
        """Handle errors from recovery system"""
        self.logger.error(f"Operation Error: {error_context.error_message}")
        
        # You could show recovery options to user here
        if error_context.severity.value in ["critical", "fatal"]:
            QMessageBox.critical(self, "Operation Error", f"❌ {error_context.error_message}")

    def closeEvent(self, a0):
        """Handle application close"""
        event = a0  # Rename parameter to match parent class signature
        assert event is not None  # closeEvent should never receive None
        self.logger.info("Application closing")
        
        # Stop system monitoring
        if hasattr(self, 'system_monitor') and self.system_monitor and self.system_monitor.isRunning():
            self.system_monitor.stop()
            self.system_monitor.wait(3000)  # Wait up to 3 seconds
        
        # Stop advanced monitoring
        if hasattr(self, 'health_manager') and self.health_manager:
            self.health_manager.stop_monitoring()
        
        # Save configuration
        self.config.save()
        
        event.accept()