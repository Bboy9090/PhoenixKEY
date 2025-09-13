"""
BootForge OS Image Manager GUI Widget
Interface for downloading, managing, and selecting OS images
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QPushButton, QComboBox, QListWidget,
    QListWidgetItem, QProgressBar, QTextEdit, QFileDialog,
    QMessageBox, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QLineEdit, QCheckBox, QSplitter, QFrame, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QDialogButtonBox, QFormLayout, QSpinBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QPixmap, QIcon, QColor, QPalette

from src.core.os_image_manager import (
    OSImageInfo, ImageStatus, VerificationMethod, DownloadProgress
)
from src.gui.os_image_manager_qt import OSImageManagerQt
from src.core.config import Config


class OSImageSelectionWidget(QWidget):
    """Widget for selecting and managing OS images"""
    
    images_updated = pyqtSignal(dict)  # {file_name: local_path} mapping
    
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize OS Image Manager (Qt bridge)
        self.image_manager = OSImageManagerQt(config)
        self.image_manager.download_progress.connect(self._on_download_progress)
        self.image_manager.images_updated.connect(self._refresh_images)
        
        # State tracking
        self.required_files: List[str] = []
        self.available_images: List[OSImageInfo] = []
        self.selected_images: Dict[str, OSImageInfo] = {}  # file_name -> image
        self.download_progresses: Dict[str, DownloadProgress] = {}
        
        self._setup_ui()
        self._refresh_images()
    
    def _setup_ui(self):
        """Setup the OS image selection UI"""
        layout = QVBoxLayout(self)
        
        # Title and controls
        header_layout = QHBoxLayout()
        
        title = QLabel("OS Image Manager")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setToolTip("Refresh available images from providers")
        self.refresh_btn.clicked.connect(self._refresh_images)
        header_layout.addWidget(self.refresh_btn)
        
        self.import_btn = QPushButton("Import Image")
        self.import_btn.setToolTip("Import custom image file")
        self.import_btn.clicked.connect(self._import_custom_image)
        header_layout.addWidget(self.import_btn)
        
        layout.addLayout(header_layout)
        
        # Main content area
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: Available images
        available_group = QGroupBox("Available Images")
        available_layout = QVBoxLayout(available_group)
        
        # Provider filter
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Provider:"))
        
        self.provider_combo = QComboBox()
        self.provider_combo.addItem("All Providers", "all")
        self.provider_combo.addItem("Linux (Ubuntu)", "linux")
        self.provider_combo.addItem("macOS", "macos")
        self.provider_combo.addItem("Windows", "windows")
        self.provider_combo.addItem("Custom", "custom")
        self.provider_combo.currentTextChanged.connect(self._filter_images)
        filter_layout.addWidget(self.provider_combo)
        
        filter_layout.addStretch()
        
        # Search box
        filter_layout.addWidget(QLabel("Search:"))
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search images...")
        self.search_box.textChanged.connect(self._filter_images)
        filter_layout.addWidget(self.search_box)
        
        available_layout.addLayout(filter_layout)
        
        # Available images list
        self.available_list = QListWidget()
        self.available_list.itemDoubleClicked.connect(self._download_image)
        available_layout.addWidget(self.available_list)
        
        # Download button
        self.download_btn = QPushButton("Download Selected")
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self._download_selected_image)
        available_layout.addWidget(self.download_btn)
        
        main_splitter.addWidget(available_group)
        
        # Right side: Required files and assignments
        assignment_group = QGroupBox("File Assignments")
        assignment_layout = QVBoxLayout(assignment_group)
        
        # Instructions
        instructions = QLabel("Assign OS images to required files for your deployment recipe:")
        instructions.setWordWrap(True)
        assignment_layout.addWidget(instructions)
        
        # Assignment table
        self.assignment_table = QTableWidget()
        self.assignment_table.setColumnCount(4)
        self.assignment_table.setHorizontalHeaderLabels([
            "Required File", "Assigned Image", "Status", "Action"
        ])
        
        header = self.assignment_table.horizontalHeader()
        if header:
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        assignment_layout.addWidget(self.assignment_table)
        
        # Download progress area
        progress_group = QGroupBox("Download Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_widget = QWidget()
        self.progress_layout = QVBoxLayout(self.progress_widget)
        progress_layout.addWidget(self.progress_widget)
        
        assignment_layout.addWidget(progress_group)
        
        main_splitter.addWidget(assignment_group)
        
        # Set splitter proportions
        main_splitter.setSizes([400, 500])
        layout.addWidget(main_splitter)
        
        # Status bar
        self.status_label = QLabel("Ready - Select images for your deployment files")
        layout.addWidget(self.status_label)
    
    def set_required_files(self, required_files: List[str]):
        """Set the required files for the selected recipe"""
        self.required_files = required_files
        self.selected_images = {}
        self._update_assignment_table()
        self._update_status()
    
    def _refresh_images(self):
        """Refresh available images from all providers"""
        try:
            self.status_label.setText("Refreshing available images...")
            
            # Get available images from all providers
            self.available_images = self.image_manager.get_available_images()
            
            # Also get cached images
            cached_images = self.image_manager.get_cached_images()
            
            # Combine and deduplicate
            all_images = self.available_images + cached_images
            seen_ids = set()
            unique_images = []
            
            for image in all_images:
                if image.id not in seen_ids:
                    unique_images.append(image)
                    seen_ids.add(image.id)
            
            self.available_images = unique_images
            self._filter_images()
            
            self.status_label.setText(f"Found {len(self.available_images)} available images")
            
        except Exception as e:
            self.logger.error(f"Failed to refresh images: {e}")
            self.status_label.setText(f"Error refreshing images: {e}")
    
    def _filter_images(self):
        """Filter and display images based on current filters"""
        provider_filter = self.provider_combo.currentData()
        search_text = self.search_box.text().lower()
        
        filtered_images = []
        
        for image in self.available_images:
            # Provider filter
            if provider_filter != "all" and image.provider != provider_filter:
                continue
            
            # Search filter
            if search_text:
                searchable_text = f"{image.name} {image.version} {image.os_family}".lower()
                if search_text not in searchable_text:
                    continue
            
            filtered_images.append(image)
        
        # Update the list
        self.available_list.clear()
        
        for image in filtered_images:
            item = QListWidgetItem()
            
            # Create display text
            status_icon = self._get_status_icon(image.status)
            display_text = f"{status_icon} {image.name}"
            if image.version != "unknown":
                display_text += f" v{image.version}"
            
            item.setText(display_text)
            item.setData(Qt.ItemDataRole.UserRole, image)
            
            # Color code by status
            if image.status == ImageStatus.VERIFIED:
                item.setBackground(QColor("#28A745"))  # Green
            elif image.status == ImageStatus.DOWNLOADED:
                item.setBackground(QColor("#FFC107"))  # Yellow
            elif image.status == ImageStatus.DOWNLOADING:
                item.setBackground(QColor("#007AFF"))  # Blue
            elif image.status == ImageStatus.FAILED:
                item.setBackground(QColor("#DC3545"))  # Red
            else:
                item.setBackground(QColor("#6C757D"))  # Gray
            
            self.available_list.addItem(item)
        
        # Update download button
        self.download_btn.setEnabled(self.available_list.currentItem() is not None)
    
    def _get_status_icon(self, status: ImageStatus) -> str:
        """Get emoji icon for image status"""
        icons = {
            ImageStatus.AVAILABLE: "📡",
            ImageStatus.DOWNLOADING: "⬇️",
            ImageStatus.DOWNLOADED: "💾",
            ImageStatus.VERIFYING: "🔍",
            ImageStatus.VERIFIED: "✅",
            ImageStatus.FAILED: "❌",
            ImageStatus.CACHED: "💾",
            ImageStatus.PAUSED: "⏸️"
        }
        return icons.get(status, "❓")
    
    def _download_selected_image(self):
        """Download the currently selected image"""
        current_item = self.available_list.currentItem()
        if current_item:
            self._download_image(current_item)
    
    def _download_image(self, item: QListWidgetItem):
        """Download an image"""
        image = item.data(Qt.ItemDataRole.UserRole)
        
        if image.status in [ImageStatus.VERIFIED, ImageStatus.CACHED]:
            QMessageBox.information(self, "Already Available", 
                                   f"Image '{image.name}' is already downloaded and verified.")
            return
        
        if image.status == ImageStatus.DOWNLOADING:
            QMessageBox.information(self, "Download Active", 
                                   f"Image '{image.name}' is already being downloaded.")
            return
        
        # Start download
        try:
            success = self.image_manager.download_image(image)
            if success:
                self.status_label.setText(f"Started downloading {image.name}")
            else:
                QMessageBox.warning(self, "Download Failed", 
                                   f"Failed to start download for '{image.name}'")
        except Exception as e:
            QMessageBox.critical(self, "Download Error", f"Error starting download: {e}")
    
    def _on_download_progress(self, progress: DownloadProgress):
        """Handle download progress updates"""
        self.download_progresses[progress.image_id] = progress
        self._update_progress_display(progress)
        self._filter_images()  # Refresh to update status colors
    
    def _update_progress_display(self, progress: DownloadProgress):
        """Update the progress display for a download"""
        # Create or update progress widget
        progress_id = f"progress_{progress.image_id}"
        
        # Find existing progress widget or create new one
        existing_widget = self.progress_widget.findChild(QWidget, progress_id)
        if not existing_widget:
            # Create new progress widget
            progress_frame = QFrame()
            progress_frame.setObjectName(progress_id)
            progress_frame.setFrameStyle(QFrame.Shape.Box)
            
            layout = QVBoxLayout(progress_frame)
            layout.setContentsMargins(5, 5, 5, 5)
            
            # Image name
            name_label = QLabel()
            name_label.setObjectName("name_label")
            name_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            layout.addWidget(name_label)
            
            # Progress bar
            progress_bar = QProgressBar()
            progress_bar.setObjectName("progress_bar")
            layout.addWidget(progress_bar)
            
            # Status label
            status_label = QLabel()
            status_label.setObjectName("status_label")
            status_label.setFont(QFont("Arial", 8))
            layout.addWidget(status_label)
            
            # Control buttons
            controls_layout = QHBoxLayout()
            
            pause_btn = QPushButton("Pause")
            pause_btn.setObjectName("pause_btn")
            pause_btn.clicked.connect(lambda: self._pause_download(progress.image_id))
            controls_layout.addWidget(pause_btn)
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.setObjectName("cancel_btn")
            cancel_btn.clicked.connect(lambda: self._cancel_download(progress.image_id))
            controls_layout.addWidget(cancel_btn)
            
            controls_layout.addStretch()
            layout.addLayout(controls_layout)
            
            self.progress_layout.addWidget(progress_frame)
            existing_widget = progress_frame
        
        # Update progress widget
        name_label = existing_widget.findChild(QLabel, "name_label")
        progress_bar = existing_widget.findChild(QProgressBar, "progress_bar")
        status_label = existing_widget.findChild(QLabel, "status_label")
        
        # Find image name
        image_name = progress.image_id
        for image in self.available_images:
            if image.id == progress.image_id:
                image_name = image.name
                break
        
        if name_label:
            name_label.setText(image_name)
        
        if progress_bar:
            progress_bar.setValue(int(progress.progress_percent))
            progress_bar.setFormat(f"{progress.progress_percent:.1f}%")
        
        if status_label:
            if progress.status == ImageStatus.DOWNLOADING:
                speed_text = f"{progress.speed_mbps:.1f} MB/s" if progress.speed_mbps > 0 else "Calculating..."
                eta_text = f"{progress.eta_seconds}s" if progress.eta_seconds > 0 else "Unknown"
                status_text = f"Downloading - {speed_text} - ETA: {eta_text}"
            else:
                status_text = progress.status.value.title()
            
            status_label.setText(status_text)
        
        # Hide completed downloads after a delay
        if progress.status in [ImageStatus.VERIFIED, ImageStatus.FAILED]:
            QTimer.singleShot(5000, lambda: self._hide_progress_widget(progress_id))
    
    def _hide_progress_widget(self, progress_id: str):
        """Hide a completed progress widget"""
        widget = self.progress_widget.findChild(QWidget, progress_id)
        if widget:
            widget.hide()
            self.progress_layout.removeWidget(widget)
            widget.deleteLater()
    
    def _pause_download(self, image_id: str):
        """Pause a download"""
        # Implementation would depend on download engine capabilities
        self.logger.info(f"Pause requested for {image_id}")
        self.status_label.setText(f"Download paused for {image_id}")
    
    def _cancel_download(self, image_id: str):
        """Cancel a download"""
        # Implementation would depend on download engine capabilities
        self.logger.info(f"Cancel requested for {image_id}")
        self.status_label.setText(f"Download cancelled for {image_id}")
        
        # Hide progress widget
        self._hide_progress_widget(f"progress_{image_id}")
    
    def _update_assignment_table(self):
        """Update the file assignment table"""
        self.assignment_table.setRowCount(len(self.required_files))
        
        for i, file_name in enumerate(self.required_files):
            # Required file name
            self.assignment_table.setItem(i, 0, QTableWidgetItem(file_name))
            
            # Assigned image
            assigned_image = self.selected_images.get(file_name)
            if assigned_image:
                image_text = f"{assigned_image.name} v{assigned_image.version}"
                self.assignment_table.setItem(i, 1, QTableWidgetItem(image_text))
                
                # Status
                status_icon = self._get_status_icon(assigned_image.status)
                status_text = f"{status_icon} {assigned_image.status.value.title()}"
                status_item = QTableWidgetItem(status_text)
                
                if assigned_image.status == ImageStatus.VERIFIED:
                    status_item.setBackground(QColor("#28A745"))
                elif assigned_image.status == ImageStatus.FAILED:
                    status_item.setBackground(QColor("#DC3545"))
                
                self.assignment_table.setItem(i, 2, status_item)
            else:
                self.assignment_table.setItem(i, 1, QTableWidgetItem("Not assigned"))
                self.assignment_table.setItem(i, 2, QTableWidgetItem("❓ Pending"))
            
            # Action button
            assign_btn = QPushButton("Assign" if not assigned_image else "Change")
            assign_btn.clicked.connect(lambda checked, fn=file_name: self._assign_image(fn))
            self.assignment_table.setCellWidget(i, 3, assign_btn)
    
    def _assign_image(self, file_name: str):
        """Assign an image to a required file"""
        # Show dialog to select image
        dialog = ImageAssignmentDialog(self.available_images, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_image = dialog.get_selected_image()
            if selected_image:
                self.selected_images[file_name] = selected_image
                self._update_assignment_table()
                self._update_status()
    
    def _import_custom_image(self):
        """Import a custom image file"""
        try:
            # Get provider for custom images
            custom_provider = self.image_manager.providers.get("custom")
            if not custom_provider:
                QMessageBox.warning(self, "Provider Not Available", 
                                   "Custom image provider is not available.")
                return
            
            # Show import dialog
            dialog = CustomImageImportDialog(custom_provider, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self._refresh_images()
                self.status_label.setText("Custom image imported successfully")
                
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import custom image: {e}")
    
    def _update_status(self):
        """Update status based on current assignments"""
        if not self.required_files:
            self.status_label.setText("No files required for current recipe")
            return
        
        assigned_count = len(self.selected_images)
        ready_count = sum(1 for img in self.selected_images.values() 
                         if img.status == ImageStatus.VERIFIED)
        
        self.status_label.setText(
            f"Files: {assigned_count}/{len(self.required_files)} assigned, "
            f"{ready_count}/{len(self.required_files)} ready"
        )
        
        # Emit update signal
        if assigned_count == len(self.required_files) and ready_count == assigned_count:
            # All files are assigned and ready
            file_mapping = {}
            for file_name, image in self.selected_images.items():
                if image.local_path:
                    file_mapping[file_name] = image.local_path
            
            self.images_updated.emit(file_mapping)
    
    def get_file_mapping(self) -> Dict[str, str]:
        """Get the current file name to local path mapping"""
        mapping = {}
        for file_name, image in self.selected_images.items():
            if image.local_path and image.status == ImageStatus.VERIFIED:
                mapping[file_name] = image.local_path
        return mapping
    
    def is_ready(self) -> bool:
        """Check if all required files have verified images assigned"""
        if not self.required_files:
            return True
        
        return (len(self.selected_images) == len(self.required_files) and
                all(img.status == ImageStatus.VERIFIED for img in self.selected_images.values()))


class ImageAssignmentDialog(QDialog):
    """Dialog for assigning an image to a required file"""
    
    def __init__(self, available_images: List[OSImageInfo], parent=None):
        super().__init__(parent)
        self.available_images = available_images
        self.selected_image: Optional[OSImageInfo] = None
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the assignment dialog UI"""
        self.setWindowTitle("Assign OS Image")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel("Select an OS image to assign to this required file:")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Image list
        self.image_list = QListWidget()
        self.image_list.itemSelectionChanged.connect(self._on_selection_changed)
        
        for image in self.available_images:
            if image.status in [ImageStatus.VERIFIED, ImageStatus.CACHED]:
                item = QListWidgetItem()
                item.setText(f"{image.name} v{image.version} ({image.os_family})")
                item.setData(Qt.ItemDataRole.UserRole, image)
                self.image_list.addItem(item)
        
        layout.addWidget(self.image_list)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setEnabled(False)
    
    def _on_selection_changed(self):
        """Handle selection changes"""
        current_item = self.image_list.currentItem()
        if current_item:
            self.selected_image = current_item.data(Qt.ItemDataRole.UserRole)
            self.ok_button.setEnabled(True)
        else:
            self.selected_image = None
            self.ok_button.setEnabled(False)
    
    def get_selected_image(self) -> Optional[OSImageInfo]:
        """Get the selected image"""
        return self.selected_image


class CustomImageImportDialog(QDialog):
    """Dialog for importing custom images"""
    
    def __init__(self, custom_provider, parent=None):
        super().__init__(parent)
        self.custom_provider = custom_provider
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the import dialog UI"""
        self.setWindowTitle("Import Custom OS Image")
        self.setModal(True)
        self.resize(500, 300)
        
        layout = QVBoxLayout(self)
        
        # File selection
        file_group = QGroupBox("Image File")
        file_layout = QHBoxLayout(file_group)
        
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select image file...")
        file_layout.addWidget(self.file_path_edit)
        
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(browse_btn)
        
        layout.addWidget(file_group)
        
        # Metadata
        metadata_group = QGroupBox("Image Metadata")
        metadata_layout = QFormLayout(metadata_group)
        
        self.name_edit = QLineEdit()
        metadata_layout.addRow("Name:", self.name_edit)
        
        self.os_combo = QComboBox()
        self.os_combo.addItems(["linux", "windows", "macos", "freebsd", "embedded", "unknown"])
        metadata_layout.addRow("OS Family:", self.os_combo)
        
        self.version_edit = QLineEdit()
        metadata_layout.addRow("Version:", self.version_edit)
        
        self.arch_combo = QComboBox()
        self.arch_combo.addItems(["x86_64", "i386", "arm64", "arm", "universal", "unknown"])
        metadata_layout.addRow("Architecture:", self.arch_combo)
        
        layout.addWidget(metadata_group)
        
        # Verification
        verify_group = QGroupBox("Verification (Optional)")
        verify_layout = QFormLayout(verify_group)
        
        self.checksum_edit = QLineEdit()
        self.checksum_edit.setPlaceholderText("Enter expected checksum...")
        verify_layout.addRow("Expected Checksum:", self.checksum_edit)
        
        self.checksum_type_combo = QComboBox()
        self.checksum_type_combo.addItems(["sha256", "sha1", "md5"])
        verify_layout.addRow("Checksum Type:", self.checksum_type_combo)
        
        layout.addWidget(verify_group)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._import_image)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _browse_file(self):
        """Browse for image file"""
        dialog_info = self.custom_provider.get_import_dialog_info()
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            dialog_info["title"],
            "",
            dialog_info["file_filter"]
        )
        
        if file_path:
            self.file_path_edit.setText(file_path)
            
            # Auto-fill some metadata from filename
            file_name = Path(file_path).name.lower()
            
            if not self.name_edit.text():
                self.name_edit.setText(Path(file_path).stem.replace('_', ' ').replace('-', ' ').title())
            
            # Try to detect OS family
            if "ubuntu" in file_name or "linux" in file_name:
                self.os_combo.setCurrentText("linux")
            elif "windows" in file_name or "win" in file_name:
                self.os_combo.setCurrentText("windows")
            elif "macos" in file_name or "mac" in file_name:
                self.os_combo.setCurrentText("macos")
    
    def _import_image(self):
        """Import the custom image"""
        file_path = self.file_path_edit.text().strip()
        if not file_path:
            QMessageBox.warning(self, "Missing File", "Please select an image file.")
            return
        
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "File Not Found", "The selected file does not exist.")
            return
        
        try:
            # Prepare import parameters
            name = self.name_edit.text().strip() or None
            os_family = self.os_combo.currentText() if self.os_combo.currentText() != "unknown" else None
            version = self.version_edit.text().strip() or None
            architecture = self.arch_combo.currentText() if self.arch_combo.currentText() != "unknown" else None
            expected_checksum = self.checksum_edit.text().strip() or None
            checksum_type = self.checksum_type_combo.currentText()
            
            # Import the image
            result = self.custom_provider.import_custom_image(
                image_path=file_path,
                name=name,
                os_family=os_family,
                version=version,
                architecture=architecture,
                expected_checksum=expected_checksum,
                checksum_type=checksum_type
            )
            
            if result:
                QMessageBox.information(self, "Import Successful", 
                                       f"Successfully imported: {result.name}")
                self.accept()
            else:
                QMessageBox.warning(self, "Import Failed", 
                                   "Failed to import the image. Check the logs for details.")
                
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Error importing image: {e}")
    
    def validate_step(self) -> bool:
        """SECURITY: Validate that only verified images are selected before proceeding to next step"""
        
        # Check if we have any selected images for the required files
        if not self.selected_images:
            QMessageBox.warning(self, "No Images Selected", 
                               "Please select and verify OS images for all required files before proceeding.")
            return False
        
        # Check if all required files have selected images
        for required_file in self.required_files:
            if required_file not in self.selected_images:
                QMessageBox.warning(self, "Missing Required Images", 
                                   f"Please select an image for required file: {required_file}")
                return False
        
        # CRITICAL SECURITY CHECK: Ensure all selected images are verified
        unverified_images = []
        for file_name, image in self.selected_images.items():
            if image.status != ImageStatus.VERIFIED:
                unverified_images.append(f"{image.name} (Status: {image.status.value})")
        
        if unverified_images:
            QMessageBox.critical(self, "Security Warning - Unverified Images", 
                                f"The following images are not verified and cannot be used:\n\n" +
                                "\n".join(unverified_images) +
                                "\n\nPlease ensure all images are downloaded and verified before proceeding.")
            return False
        
        # All validations passed
        return True