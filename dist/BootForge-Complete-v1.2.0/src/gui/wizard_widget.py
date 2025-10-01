"""
BootForge Wizard Widget
Step-by-step wizard interface for OS deployment operations
"""

import logging
from typing import List, Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    pass
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QLabel, QPushButton, QGroupBox, QRadioButton,
    QComboBox, QCheckBox, QListWidget, QListWidgetItem,
    QFileDialog, QProgressBar, QTextEdit, QButtonGroup,
    QGridLayout, QSpacerItem, QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QDateTime
from PyQt6.QtGui import QFont, QPixmap, QPalette

from src.core.disk_manager import DiskManager, DiskInfo, WriteProgress
from src.gui.stepper_header import StepperHeader, create_stepper_header
from src.gui.stepper_wizard import WizardController, WizardStep


class WizardPage(QWidget):
    """Base class for wizard pages"""
    
    def __init__(self, title: str, description: str):
        super().__init__()
        self.title = title
        self.description = description
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup page UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Title
        title_label = QLabel(self.title)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(self.description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #cccccc;")
        layout.addWidget(desc_label)
        
        # Content area
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        layout.addWidget(self.content_widget)
        
        # Spacer
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
    
    def validate_page(self) -> bool:
        """Validate page inputs before proceeding"""
        return True
    
    def get_page_data(self) -> Dict[str, Any]:
        """Get data from this page"""
        return {}


class OSSelectionPage(WizardPage):
    """OS selection page"""
    
    def __init__(self):
        super().__init__(
            "Select Operating System",
            "Choose the operating system you want to deploy and configure options."
        )
        self.os_group = QButtonGroup()
        self.selected_os = None
        self._setup_content()
    
    def _setup_content(self):
        """Setup OS selection content"""
        # OS selection group
        os_group_box = QGroupBox("Operating System")
        os_layout = QVBoxLayout(os_group_box)
        
        # macOS option
        self.macos_radio = QRadioButton("macOS")
        self.macos_radio.toggled.connect(lambda checked: self._os_selected("macos" if checked else None))
        self.os_group.addButton(self.macos_radio)
        os_layout.addWidget(self.macos_radio)
        
        macos_desc = QLabel("  • Create bootable macOS installer with OpenCore support")
        macos_desc.setStyleSheet("color: #aaaaaa; margin-left: 20px;")
        os_layout.addWidget(macos_desc)
        
        # Windows option
        self.windows_radio = QRadioButton("Windows")
        self.windows_radio.toggled.connect(lambda checked: self._os_selected("windows" if checked else None))
        self.os_group.addButton(self.windows_radio)
        os_layout.addWidget(self.windows_radio)
        
        windows_desc = QLabel("  • Create bootable Windows installer with driver support")
        windows_desc.setStyleSheet("color: #aaaaaa; margin-left: 20px;")
        os_layout.addWidget(windows_desc)
        
        # Linux option
        self.linux_radio = QRadioButton("Linux")
        self.linux_radio.toggled.connect(lambda checked: self._os_selected("linux" if checked else None))
        self.os_group.addButton(self.linux_radio)
        os_layout.addWidget(self.linux_radio)
        
        linux_desc = QLabel("  • Create bootable Linux distribution installer")
        linux_desc.setStyleSheet("color: #aaaaaa; margin-left: 20px;")
        os_layout.addWidget(linux_desc)
        
        self.content_layout.addWidget(os_group_box)
        
        # Options group (initially hidden)
        self.options_group = QGroupBox("Options")
        self.options_layout = QVBoxLayout(self.options_group)
        
        # EFI support
        self.efi_checkbox = QCheckBox("Enable EFI/UEFI support")
        self.efi_checkbox.setChecked(True)
        self.options_layout.addWidget(self.efi_checkbox)
        
        # Legacy support
        self.legacy_checkbox = QCheckBox("Include legacy BIOS support")
        self.options_layout.addWidget(self.legacy_checkbox)
        
        # Driver injection
        self.drivers_checkbox = QCheckBox("Inject additional drivers")
        self.options_layout.addWidget(self.drivers_checkbox)
        
        self.options_group.setVisible(False)
        self.content_layout.addWidget(self.options_group)
    
    def _os_selected(self, os_type: Optional[str]):
        """Handle OS selection"""
        self.selected_os = os_type
        self.options_group.setVisible(os_type is not None)
        
        # Configure options based on OS
        if os_type == "macos":
            self.legacy_checkbox.setVisible(False)
            self.drivers_checkbox.setText("Inject kext drivers")
        elif os_type == "windows":
            self.legacy_checkbox.setVisible(True)
            self.drivers_checkbox.setText("Inject Windows drivers")
        elif os_type == "linux":
            self.legacy_checkbox.setVisible(True)
            self.drivers_checkbox.setText("Include additional modules")
    
    def validate_page(self) -> bool:
        """Validate OS selection"""
        return self.selected_os is not None
    
    def get_page_data(self) -> Dict[str, Any]:
        """Get OS selection data"""
        return {
            "os_type": self.selected_os,
            "efi_support": self.efi_checkbox.isChecked(),
            "legacy_support": self.legacy_checkbox.isChecked(),
            "inject_drivers": self.drivers_checkbox.isChecked()
        }


class ImageSelectionPage(WizardPage):
    """Image file selection page"""
    
    def __init__(self):
        super().__init__(
            "Select Image File",
            "Choose the OS image file (ISO, DMG, or IMG) to write to the USB drive."
        )
        self.selected_image = None
        self._setup_content()
    
    def _setup_content(self):
        """Setup image selection content"""
        # File selection group
        file_group = QGroupBox("Image File")
        file_layout = QVBoxLayout(file_group)
        
        # File path display
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("padding: 8px; border: 1px solid #555555; background-color: #3c3c3c;")
        file_layout.addWidget(self.file_label)
        
        # Browse button
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_file)
        file_layout.addWidget(browse_button)
        
        self.content_layout.addWidget(file_group)
        
        # File info group
        self.info_group = QGroupBox("File Information")
        info_layout = QGridLayout(self.info_group)
        
        self.size_label = QLabel("Size: --")
        self.type_label = QLabel("Type: --")
        self.modified_label = QLabel("Modified: --")
        
        info_layout.addWidget(QLabel("File Size:"), 0, 0)
        info_layout.addWidget(self.size_label, 0, 1)
        info_layout.addWidget(QLabel("File Type:"), 1, 0)
        info_layout.addWidget(self.type_label, 1, 1)
        info_layout.addWidget(QLabel("Last Modified:"), 2, 0)
        info_layout.addWidget(self.modified_label, 2, 1)
        
        self.info_group.setVisible(False)
        self.content_layout.addWidget(self.info_group)
    
    def _browse_file(self):
        """Browse for image file"""
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilters([
            "All Supported (*.iso *.dmg *.img *.bin)",
            "ISO Files (*.iso)",
            "DMG Files (*.dmg)",
            "IMG Files (*.img)",
            "BIN Files (*.bin)",
            "All Files (*.*)"
        ])
        
        if file_dialog.exec():
            files = file_dialog.selectedFiles()
            if files:
                self.selected_image = files[0]
                self._update_file_info()
    
    def _update_file_info(self):
        """Update file information display"""
        if not self.selected_image:
            return
        
        file_path = Path(self.selected_image)
        
        # Update file label
        self.file_label.setText(str(file_path))
        
        # Update file info
        try:
            stat = file_path.stat()
            size_mb = stat.st_size / (1024 * 1024)
            
            self.size_label.setText(f"{size_mb:.1f} MB ({stat.st_size:,} bytes)")
            self.type_label.setText(file_path.suffix.upper())
            self.modified_label.setText(
                QDateTime.fromSecsSinceEpoch(int(stat.st_mtime)).toString()
            )
            
            self.info_group.setVisible(True)
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Error reading file info: {e}")
    
    def validate_page(self) -> bool:
        """Validate image selection"""
        return self.selected_image is not None and Path(self.selected_image).exists()
    
    def get_page_data(self) -> Dict[str, Any]:
        """Get image selection data"""
        return {
            "image_path": self.selected_image
        }


class DeviceSelectionPage(WizardPage):
    """USB device selection page"""
    
    def __init__(self, disk_manager: DiskManager):
        self.disk_manager = disk_manager
        self.devices = []
        self.selected_device = None
        
        super().__init__(
            "Select Target Device",
            "Choose the USB drive where the OS image will be written. WARNING: All data will be erased!"
        )
        self._setup_content()
    
    def _setup_content(self):
        """Setup device selection content"""
        # Device list
        device_group = QGroupBox("Available USB Devices")
        device_layout = QVBoxLayout(device_group)
        
        # Refresh button
        refresh_button = QPushButton("Refresh Devices")
        refresh_button.clicked.connect(self._refresh_devices)
        device_layout.addWidget(refresh_button)
        
        # Device list widget
        self.device_list = QListWidget()
        self.device_list.itemSelectionChanged.connect(self._device_selected)
        device_layout.addWidget(self.device_list)
        
        self.content_layout.addWidget(device_group)
        
        # Device info
        self.device_info_group = QGroupBox("Device Information")
        info_layout = QGridLayout(self.device_info_group)
        
        self.device_name_label = QLabel("--")
        self.device_size_label = QLabel("--")
        self.device_filesystem_label = QLabel("--")
        self.device_vendor_label = QLabel("--")
        
        info_layout.addWidget(QLabel("Device:"), 0, 0)
        info_layout.addWidget(self.device_name_label, 0, 1)
        info_layout.addWidget(QLabel("Size:"), 1, 0)
        info_layout.addWidget(self.device_size_label, 1, 1)
        info_layout.addWidget(QLabel("Filesystem:"), 2, 0)
        info_layout.addWidget(self.device_filesystem_label, 2, 1)
        info_layout.addWidget(QLabel("Vendor:"), 3, 0)
        info_layout.addWidget(self.device_vendor_label, 3, 1)
        
        self.device_info_group.setVisible(False)
        self.content_layout.addWidget(self.device_info_group)
        
        # Warning
        warning_label = QLabel("⚠️  WARNING: All data on the selected device will be permanently erased!")
        warning_label.setStyleSheet("color: #ff6b6b; font-weight: bold; padding: 10px; border: 1px solid #ff6b6b; border-radius: 4px;")
        warning_label.setWordWrap(True)
        self.content_layout.addWidget(warning_label)
        
        # Initial device refresh
        self._refresh_devices()
    
    def _refresh_devices(self):
        """Refresh USB device list"""
        self.device_list.clear()
        self.devices = self.disk_manager.get_removable_drives()
        
        for device in self.devices:
            item = QListWidgetItem()
            size_gb = device.size_bytes / (1024**3)
            item.setText(f"{device.name} ({size_gb:.1f} GB) - {device.path}")
            item.setData(Qt.ItemDataRole.UserRole, device)
            self.device_list.addItem(item)
        
        if not self.devices:
            item = QListWidgetItem("No USB devices found")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.device_list.addItem(item)
    
    def _device_selected(self):
        """Handle device selection"""
        current_item = self.device_list.currentItem()
        if current_item and current_item.data(Qt.ItemDataRole.UserRole):
            device = current_item.data(Qt.ItemDataRole.UserRole)
            self.selected_device = device
            self._update_device_info(device)
        else:
            self.selected_device = None
            self.device_info_group.setVisible(False)
    
    def _update_device_info(self, device: DiskInfo):
        """Update device information display"""
        size_gb = device.size_bytes / (1024**3)
        
        self.device_name_label.setText(device.name)
        self.device_size_label.setText(f"{size_gb:.1f} GB ({device.size_bytes:,} bytes)")
        self.device_filesystem_label.setText(device.filesystem or "Unknown")
        self.device_vendor_label.setText(f"{device.vendor} {device.model}".strip())
        
        self.device_info_group.setVisible(True)
    
    def update_device_list(self, devices: List[DiskInfo]):
        """Update device list from external source"""
        self.devices = devices
        self._refresh_devices()
    
    def validate_page(self) -> bool:
        """Validate device selection"""
        return self.selected_device is not None
    
    def get_page_data(self) -> Dict[str, Any]:
        """Get device selection data"""
        return {
            "target_device": self.selected_device.path if self.selected_device else None,
            "device_info": self.selected_device
        }


class ConfirmationPage(WizardPage):
    """Operation confirmation page"""
    
    def __init__(self):
        super().__init__(
            "Confirm Operation",
            "Review your settings and confirm the operation. This action cannot be undone!"
        )
        self.operation_data = {}
        self._setup_content()
    
    def _setup_content(self):
        """Setup confirmation content"""
        # Summary group
        summary_group = QGroupBox("Operation Summary")
        summary_layout = QGridLayout(summary_group)
        
        self.os_label = QLabel("--")
        self.image_label = QLabel("--")
        self.device_label = QLabel("--")
        self.options_label = QLabel("--")
        
        summary_layout.addWidget(QLabel("Operating System:"), 0, 0)
        summary_layout.addWidget(self.os_label, 0, 1)
        summary_layout.addWidget(QLabel("Image File:"), 1, 0)
        summary_layout.addWidget(self.image_label, 1, 1)
        summary_layout.addWidget(QLabel("Target Device:"), 2, 0)
        summary_layout.addWidget(self.device_label, 2, 1)
        summary_layout.addWidget(QLabel("Options:"), 3, 0)
        summary_layout.addWidget(self.options_label, 3, 1)
        
        self.content_layout.addWidget(summary_group)
        
        # Verification options
        verify_group = QGroupBox("Verification")
        verify_layout = QVBoxLayout(verify_group)
        
        self.verify_checkbox = QCheckBox("Verify written data after completion")
        self.verify_checkbox.setChecked(True)
        verify_layout.addWidget(self.verify_checkbox)
        
        self.content_layout.addWidget(verify_group)
        
        # Final warning
        warning_text = QTextEdit()
        warning_text.setMaximumHeight(100)
        warning_text.setReadOnly(True)
        warning_text.setPlainText(
            "⚠️  FINAL WARNING  ⚠️\\n\\n"
            "This operation will completely erase all data on the target device. "
            "Make sure you have backed up any important data. "
            "This action cannot be undone!"
        )
        warning_text.setStyleSheet("background-color: #4a1f1f; border: 1px solid #ff6b6b; color: #ff9999;")
        self.content_layout.addWidget(warning_text)
    
    def update_summary(self, data: Dict[str, Any]):
        """Update operation summary"""
        self.operation_data = data
        
        # OS information
        os_type = data.get("os_type", "Unknown")
        options = []
        if data.get("efi_support"):
            options.append("EFI/UEFI")
        if data.get("legacy_support"):
            options.append("Legacy BIOS")
        if data.get("inject_drivers"):
            options.append("Driver Injection")
        
        self.os_label.setText(os_type.capitalize())
        self.options_label.setText(", ".join(options) if options else "None")
        
        # Image file
        image_path = data.get("image_path", "")
        if image_path:
            self.image_label.setText(Path(image_path).name)
        
        # Target device
        device_info = data.get("device_info")
        if device_info:
            size_gb = device_info.size_bytes / (1024**3)
            self.device_label.setText(f"{device_info.name} ({size_gb:.1f} GB)")
    
    def get_page_data(self) -> Dict[str, Any]:
        """Get confirmation data"""
        return {
            "verify_after_write": self.verify_checkbox.isChecked()
        }


class ProgressPage(WizardPage):
    """Operation progress page"""
    
    def __init__(self):
        super().__init__(
            "Writing Image",
            "Please wait while the image is being written to the USB drive..."
        )
        self._setup_content()
    
    def _setup_content(self):
        """Setup progress content"""
        # Progress group
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        # Main progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        progress_layout.addWidget(self.progress_bar)
        
        # Status labels
        self.status_label = QLabel("Initializing...")
        progress_layout.addWidget(self.status_label)
        
        self.speed_label = QLabel("Speed: --")
        self.eta_label = QLabel("ETA: --")
        
        stats_layout = QHBoxLayout()
        stats_layout.addWidget(self.speed_label)
        stats_layout.addWidget(self.eta_label)
        progress_layout.addLayout(stats_layout)
        
        self.content_layout.addWidget(progress_group)
        
        # Log output
        log_group = QGroupBox("Operation Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(200)
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        self.content_layout.addWidget(log_group)
    
    def update_progress(self, progress: WriteProgress):
        """Update progress display"""
        self.progress_bar.setValue(int(progress.percentage))
        self.status_label.setText(progress.current_operation)
        
        if progress.speed_mbps > 0:
            self.speed_label.setText(f"Speed: {progress.speed_mbps:.1f} MB/s")
        else:
            self.speed_label.setText("Speed: --")
        
        if progress.eta_seconds > 0:
            eta_min = progress.eta_seconds // 60
            eta_sec = progress.eta_seconds % 60
            self.eta_label.setText(f"ETA: {eta_min:02d}:{eta_sec:02d}")
        else:
            self.eta_label.setText("ETA: --")
    
    def add_log_message(self, message: str):
        """Add message to log"""
        self.log_text.append(message)


class BootForgeWizard(QWidget):
    """Main wizard widget"""
    
    # Signals
    operation_started = pyqtSignal(str)
    operation_completed = pyqtSignal(bool, str)
    progress_updated = pyqtSignal(object)
    
    def __init__(self, disk_manager: DiskManager):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.disk_manager = disk_manager
        
        # Wizard data
        self.wizard_data = {}
        self.current_page_index = 0
        
        # Pages
        self.pages: List[WizardPage] = []
        self.stacked_widget: Optional[QStackedWidget] = None
        
        # Stepper header integration
        self.wizard_controller: Optional[WizardController] = None
        self.stepper_header: Optional[StepperHeader] = None
        
        # Operation thread
        self.operation_thread = None
        
        self._setup_ui()
        self._setup_pages()
        self._setup_stepper_integration()
    
    def _setup_ui(self):
        """Setup wizard UI with beautiful stepper header"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Create stepper header
        self.stepper_header = create_stepper_header()
        self.stepper_header.step_clicked.connect(self._on_stepper_navigation)
        layout.addWidget(self.stepper_header)
        
        # Add separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("QFrame { color: #555555; }")
        layout.addWidget(separator)
        
        # Pages stack
        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget)
        
        # Navigation buttons
        nav_layout = QHBoxLayout()
        nav_layout.addStretch()
        
        self.back_button = QPushButton("< Back")
        self.back_button.clicked.connect(self._go_back)
        self.back_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border: 1px solid #666666;
                border-radius: 4px;
                background-color: #4a4a4a;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        nav_layout.addWidget(self.back_button)
        
        self.next_button = QPushButton("Next >")
        self.next_button.clicked.connect(self._go_next)
        self.next_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border: 1px solid #0078d4;
                border-radius: 4px;
                background-color: #0078d4;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        nav_layout.addWidget(self.next_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._cancel_operation)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border: 1px solid #666666;
                border-radius: 4px;
                background-color: #4a4a4a;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        nav_layout.addWidget(self.cancel_button)
        
        layout.addLayout(nav_layout)
    
    def _setup_pages(self):
        """Setup wizard pages"""
        # Create pages
        self.os_page = OSSelectionPage()
        self.image_page = ImageSelectionPage()
        self.device_page = DeviceSelectionPage(self.disk_manager)
        self.confirm_page = ConfirmationPage()
        self.progress_page = ProgressPage()
        
        # Add pages to stack
        self.pages = [
            self.os_page,
            self.image_page,
            self.device_page,
            self.confirm_page,
            self.progress_page
        ]
        
        for page in self.pages:
            if self.stacked_widget is not None:
                self.stacked_widget.addWidget(page)
        
        self._update_navigation()
    
    def _update_navigation(self):
        """Update navigation button states"""
        current_page = self.current_page_index
        total_pages = len(self.pages) - 1  # Exclude progress page from normal navigation
        
        # Back button
        self.back_button.setEnabled(current_page > 0)
        
        # Next button
        if current_page < total_pages - 1:
            self.next_button.setText("Next >")
            self.next_button.setEnabled(True)
        elif current_page == total_pages - 1:  # Confirmation page
            self.next_button.setText("Start Operation")
            self.next_button.setEnabled(True)
        else:  # Progress page
            self.next_button.setText("Finish")
            self.next_button.setEnabled(False)  # Enabled when operation completes
    
    def _go_back(self):
        """Go to previous page"""
        if self.current_page_index > 0:
            self.current_page_index -= 1
            if self.stacked_widget is not None:
                self.stacked_widget.setCurrentIndex(self.current_page_index)
            
            # Update stepper header
            if self.stepper_header:
                self.stepper_header.set_current_step(self.current_page_index)
            
            self._update_navigation()
    
    def _go_next(self):
        """Go to next page or start operation"""
        current_page = self.pages[self.current_page_index]
        
        # Validate current page
        if not current_page.validate_page():
            return
        
        # Store page data
        self.wizard_data.update(current_page.get_page_data())
        
        # Check if this is the confirmation page
        if self.current_page_index == len(self.pages) - 2:  # Confirmation page
            # Update confirmation summary
            self.confirm_page.update_summary(self.wizard_data)
            self.wizard_data.update(self.confirm_page.get_page_data())
            
            # Start operation
            self._start_disk_operation()
            return
        
        # Move to next page
        if self.current_page_index < len(self.pages) - 1:
            # Mark current step as complete before moving
            if self.stepper_header and self.current_page_index < len(self.pages) - 1:
                self.stepper_header.mark_step_complete(self.current_page_index)
            
            self.current_page_index += 1
            if self.stacked_widget is not None:
                self.stacked_widget.setCurrentIndex(self.current_page_index)
            
            # Update stepper header
            if self.stepper_header:
                self.stepper_header.set_current_step(self.current_page_index)
            
            self._update_navigation()
    
    def _cancel_operation(self):
        """Cancel current operation"""
        if self.operation_thread and self.operation_thread.isRunning():
            self.operation_thread.cancel_operation()
            self.operation_thread.wait(5000)  # Wait up to 5 seconds
        
        self.reset_wizard()
    
    def _start_disk_operation(self):
        """Start disk writing operation"""
        # Move to progress page
        self.current_page_index = len(self.pages) - 1
        if self.stacked_widget is not None:
            self.stacked_widget.setCurrentIndex(self.current_page_index)
        self._update_navigation()
        
        # Disable navigation during operation
        self.back_button.setEnabled(False)
        self.next_button.setEnabled(False)
        
        # Start operation thread
        self.operation_thread = self.disk_manager.write_image_to_device(
            self.wizard_data["image_path"],
            self.wizard_data["target_device"],
            self.wizard_data["verify_after_write"],
            self.progress_page.update_progress
        )
        
        # Connect signals
        self.operation_thread.progress_updated.connect(self.progress_updated.emit)
        self.operation_thread.operation_started.connect(self._handle_operation_started)
        self.operation_thread.operation_completed.connect(self._handle_operation_completed)
        
        # Emit started signal
        device_name = self.wizard_data.get("device_info", {}).get("name", "device")
        self.operation_started.emit(f"Writing image to {device_name}")
    
    def _handle_operation_started(self, description: str):
        """Handle operation start"""
        self.progress_page.add_log_message(f"Started: {description}")
    
    def _handle_operation_completed(self, success: bool, message: str):
        """Handle operation completion"""
        self.progress_page.add_log_message(f"Completed: {message}")
        
        # Enable finish button
        self.next_button.setEnabled(True)
        if success:
            self.next_button.setText("Finish")
        else:
            self.next_button.setText("Close")
        
        # Emit completion signal
        self.operation_completed.emit(success, message)
    
    def start_operation(self):
        """Start operation from external trigger"""
        if self.current_page_index == len(self.pages) - 2:  # Confirmation page
            self._go_next()
    
    def stop_operation(self):
        """Stop current operation from external trigger"""
        self._cancel_operation()
    
    def reset_wizard(self):
        """Reset wizard to initial state"""
        self.current_page_index = 0
        self.wizard_data = {}
        if self.stacked_widget is not None:
            self.stacked_widget.setCurrentIndex(0)
        
        # Reset stepper header to beginning
        if self.stepper_header:
            self.stepper_header.reset_to_beginning()
        
        self._update_navigation()
        
        # Reset pages
        for page in self.pages:
            if hasattr(page, 'reset') and callable(getattr(page, 'reset', None)):
                getattr(page, 'reset')()
    
    def update_device_list(self, devices: List[DiskInfo]):
        """Update device list"""
        self.device_page.update_device_list(devices)
    
    def _setup_stepper_integration(self):
        """Setup integration between stepper header and wizard navigation"""
        try:
            # For now, use basic stepper functionality without full WizardController
            # This allows the stepper to work with the existing wizard pages
            if self.stepper_header:
                # Set initial state
                self.stepper_header.set_current_step(0)
                self.logger.info("Stepper header integration initialized")
                
        except Exception as e:
            self.logger.error(f"Failed to setup stepper integration: {e}")
    
    def _on_stepper_navigation(self, step_index: int):
        """Handle navigation from stepper header clicks"""
        try:
            # Only allow navigation to completed or current steps
            if step_index <= self.current_page_index:
                self._navigate_to_step(step_index)
                self.logger.info(f"Navigated to step {step_index} via stepper")
            else:
                self.logger.debug(f"Step {step_index} not accessible - current page: {self.current_page_index}")
        except Exception as e:
            self.logger.error(f"Error in stepper navigation: {e}")
    
    def _navigate_to_step(self, step_index: int):
        """Navigate to a specific step by index"""
        if 0 <= step_index < len(self.pages) and self.stacked_widget:
            # Update current page
            old_index = self.current_page_index
            self.current_page_index = step_index
            
            # Switch to the page
            self.stacked_widget.setCurrentIndex(step_index)
            
            # Update stepper header
            if self.stepper_header:
                self.stepper_header.set_current_step(step_index)
            
            # Update navigation buttons
            self._update_navigation()
            
            self.logger.debug(f"Navigated from step {old_index} to {step_index}")
    
    def _update_stepper_state(self):
        """Update stepper header to reflect current wizard state"""
        if not self.stepper_header:
            return
            
        try:
            # Mark completed steps
            for i in range(self.current_page_index):
                self.stepper_header.mark_step_complete(i)
            
            # Set current step
            self.stepper_header.set_current_step(self.current_page_index)
            
        except Exception as e:
            self.logger.error(f"Error updating stepper state: {e}")