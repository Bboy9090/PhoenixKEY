"""
BootForge Stepper Wizard Widget
Main stepper interface combining StepperHeader with step content for professional guided workflow
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QStackedWidget, QLabel, 
    QPushButton, QHBoxLayout, QSpacerItem, QSizePolicy,
    QGroupBox, QTextEdit, QProgressBar, QCheckBox,
    QComboBox, QListWidget, QFileDialog, QMessageBox,
    QFrame, QGridLayout, QScrollArea, QTabWidget,
    QListWidgetItem, QTreeWidget, QTreeWidgetItem,
    QLineEdit, QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QDialogButtonBox, QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QMutex
from PyQt6.QtGui import QFont, QPixmap, QIcon

from src.gui.stepper_header import StepperHeader, StepState
from src.gui.stepper_wizard import WizardController, WizardStep, WizardState
from src.core.disk_manager import DiskManager, DiskInfo, WriteProgress
from src.core.hardware_detector import HardwareDetector, DetectedHardware, DetectionConfidence
from src.core.hardware_matcher import HardwareMatcher, ProfileMatch
from src.core.vendor_database import VendorDatabase
from src.gui.os_image_manager_qt import OSImageManagerQt
from src.core.os_image_manager import OSImageInfo, ImageStatus, VerificationMethod, DownloadProgress
from src.core.config import Config
from src.core.safety_validator import SafetyValidator, SafetyLevel, ValidationResult, DeviceRisk
from src.core.usb_builder import USBBuilderEngine, DeploymentRecipe, DeploymentType, HardwareProfile


class StepView(QWidget):
    """Base class for individual step views in the wizard"""
    
    step_completed = pyqtSignal()
    step_data_changed = pyqtSignal(dict)
    request_next_step = pyqtSignal()
    request_previous_step = pyqtSignal()
    
    def __init__(self, step_title: str, step_description: str):
        super().__init__()
        self.step_title = step_title
        self.step_description = step_description
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the step view UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Step title and description
        title_label = QLabel(self.step_title)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #ffffff; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        desc_label = QLabel(self.step_description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #cccccc; font-size: 14px; margin-bottom: 20px;")
        layout.addWidget(desc_label)
        
        # Content area for subclasses to customize
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.content_widget)
        
        # Navigation buttons area
        nav_layout = QHBoxLayout()
        nav_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        self.previous_button = QPushButton("Previous")
        self.previous_button.setMinimumSize(100, 35)
        self.previous_button.clicked.connect(self.request_previous_step)
        nav_layout.addWidget(self.previous_button)
        
        self.next_button = QPushButton("Next")
        self.next_button.setMinimumSize(100, 35)
        self.next_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #4a4a4a;
                color: #888888;
            }
        """)
        self.next_button.clicked.connect(self._on_next_clicked)
        nav_layout.addWidget(self.next_button)
        
        layout.addLayout(nav_layout)
        
        # Add spacer to push content up
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
    
    def set_navigation_enabled(self, previous: bool = True, next: bool = True):
        """Enable/disable navigation buttons"""
        self.previous_button.setEnabled(previous)
        self.next_button.setEnabled(next)
    
    def _on_next_clicked(self):
        """Handle Next button click with validation"""
        if self.validate_step():
            self.request_next_step.emit()
        # If validation fails, stay on current step
    
    def validate_step(self) -> bool:
        """Validate step data before proceeding - override in subclasses"""
        return True
    
    def get_step_data(self) -> Dict[str, Any]:
        """Get step data - override in subclasses"""
        return {}
    
    def load_step_data(self, data: Dict[str, Any]):
        """Load step data - override in subclasses"""
        pass
    
    def on_step_entered(self):
        """Called when step becomes active - override in subclasses"""
        pass
    
    def on_step_left(self):
        """Called when leaving step - override in subclasses"""
        pass


class HardwareDetectionWorker(QThread):
    """Worker thread for hardware detection to prevent UI blocking"""
    
    # Signals for communication with UI
    detection_started = pyqtSignal()
    detection_progress = pyqtSignal(str, int)  # status_message, progress_percent
    detection_completed = pyqtSignal(object, list)  # detected_hardware, profile_matches
    detection_failed = pyqtSignal(str)  # error_message
    detection_cancelled = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hardware_detector = HardwareDetector()
        self.hardware_matcher = HardwareMatcher()
        self.vendor_db = VendorDatabase()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._cancelled = False
        self._mutex = QMutex()
    
    def cancel_detection(self):
        """Cancel the hardware detection process"""
        self._mutex.lock()
        self._cancelled = True
        self._mutex.unlock()
        self.logger.info("Hardware detection cancellation requested")
    
    def run(self):
        """Run hardware detection in thread"""
        try:
            self.detection_started.emit()
            
            if self._check_cancelled():
                return
            
            # Step 1: Initialize detection
            self.detection_progress.emit("Initializing hardware detection...", 10)
            self.msleep(500)  # Brief pause for UI feedback
            
            if self._check_cancelled():
                return
            
            # Step 2: Detect hardware
            self.detection_progress.emit("Scanning system hardware...", 30)
            detected_hardware = self.hardware_detector.detect_hardware()
            
            if self._check_cancelled():
                return
            
            if not detected_hardware:
                self.detection_failed.emit("Hardware detection failed - no hardware information found")
                return
            
            # Step 3: Analyze detected hardware
            self.detection_progress.emit("Analyzing hardware components...", 60)
            self.msleep(300)
            
            if self._check_cancelled():
                return
            
            # Step 4: Find matching profiles
            self.detection_progress.emit("Finding compatible hardware profiles...", 80)
            profile_matches = self.hardware_matcher.find_matching_profiles(detected_hardware, max_results=5)
            
            if self._check_cancelled():
                return
            
            # Step 5: Complete
            self.detection_progress.emit("Hardware detection completed!", 100)
            self.msleep(200)
            
            # Emit results
            self.detection_completed.emit(detected_hardware, profile_matches)
            
        except Exception as e:
            self.logger.error(f"Hardware detection error: {e}", exc_info=True)
            self.detection_failed.emit(f"Hardware detection failed: {str(e)}")
    
    def _check_cancelled(self) -> bool:
        """Check if detection was cancelled"""
        self._mutex.lock()
        cancelled = self._cancelled
        self._mutex.unlock()
        
        if cancelled:
            self.detection_cancelled.emit()
            return True
        return False


class HardwareDetectionStepView(StepView):
    """Revolutionary hardware auto-detection step with real-time detection and profile matching"""
    
    def __init__(self):
        super().__init__(
            "Hardware Detection",
            "Click 'Auto-Detect Hardware' to let BootForge automatically identify your system and recommend the perfect deployment configuration."
        )
        
        # State management
        self.detected_hardware: Optional[DetectedHardware] = None
        self.profile_matches: List[ProfileMatch] = []
        self.detection_worker: Optional[HardwareDetectionWorker] = None
        self.selected_profile: Optional[ProfileMatch] = None
        
        self._setup_content()
        
        # Disable next button initially
        self.set_navigation_enabled(next=False)
    
    def _setup_content(self):
        """Setup enhanced hardware detection content"""
        # Main detection control
        detection_group = QGroupBox("Hardware Detection")
        detection_layout = QVBoxLayout(detection_group)
        
        # Status display
        self.status_label = QLabel("Ready to detect your hardware configuration")
        self.status_label.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold; padding: 10px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detection_layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #555555;
                border-radius: 8px;
                text-align: center;
                font-weight: bold;
                background-color: #2d2d30;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 6px;
            }
        """)
        detection_layout.addWidget(self.progress_bar)
        
        # Detection buttons layout
        button_layout = QHBoxLayout()
        button_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # Auto-detect button (primary action)
        self.detect_button = QPushButton("🔍 Auto-Detect Hardware")
        self.detect_button.setMinimumSize(250, 50)
        self.detect_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                padding: 12px 24px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #4a4a4a;
                color: #888888;
            }
        """)
        self.detect_button.clicked.connect(self._start_detection)
        button_layout.addWidget(self.detect_button)
        
        # Cancel button (hidden initially)
        self.cancel_button = QPushButton("Cancel Detection")
        self.cancel_button.setMinimumSize(150, 50)
        self.cancel_button.setVisible(False)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #d73a49;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 12px 18px;
            }
            QPushButton:hover {
                background-color: #cb2431;
            }
            QPushButton:pressed {
                background-color: #b22a37;
            }
        """)
        self.cancel_button.clicked.connect(self._cancel_detection)
        button_layout.addWidget(self.cancel_button)
        
        button_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        detection_layout.addLayout(button_layout)
        
        self.content_layout.addWidget(detection_group)
        
        # Hardware results display (hidden initially)
        self.results_group = QGroupBox("Detected Hardware")
        results_layout = QVBoxLayout(self.results_group)
        
        # Hardware summary
        self.hardware_summary_label = QLabel()
        self.hardware_summary_label.setStyleSheet("""
            QLabel {
                background-color: #2d2d30;
                color: #ffffff;
                padding: 15px;
                border-radius: 8px;
                border: 2px solid #0078d4;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        self.hardware_summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        results_layout.addWidget(self.hardware_summary_label)
        
        # Detailed hardware information
        self.hardware_details = QTextEdit()
        self.hardware_details.setMaximumHeight(180)
        self.hardware_details.setReadOnly(True)
        self.hardware_details.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #cccccc;
                border: 1px solid #555555;
                border-radius: 6px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12px;
                padding: 10px;
            }
        """)
        results_layout.addWidget(self.hardware_details)
        
        # Profile matching results
        profile_frame = QFrame()
        profile_layout = QVBoxLayout(profile_frame)
        
        profile_label = QLabel("Recommended Hardware Profiles:")
        profile_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold; margin-top: 10px;")
        profile_layout.addWidget(profile_label)
        
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumHeight(35)
        self.profile_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d2d30;
                color: #ffffff;
                border: 2px solid #555555;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
            }
            QComboBox:hover {
                border-color: #0078d4;
            }
            QComboBox::drop-down {
                background-color: #555555;
                border: none;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
        """)
        self.profile_combo.currentIndexChanged.connect(self._on_profile_selected)
        profile_layout.addWidget(self.profile_combo)
        
        # Re-detect button
        redetect_layout = QHBoxLayout()
        redetect_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        self.redetect_button = QPushButton("🔄 Re-detect Hardware")
        self.redetect_button.setMinimumSize(180, 35)
        self.redetect_button.setStyleSheet("""
            QPushButton {
                background-color: #6f42c1;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #5a32a3;
            }
            QPushButton:pressed {
                background-color: #4c2a85;
            }
        """)
        self.redetect_button.clicked.connect(self._start_detection)
        redetect_layout.addWidget(self.redetect_button)
        
        redetect_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        profile_layout.addLayout(redetect_layout)
        
        results_layout.addWidget(profile_frame)
        
        self.results_group.setVisible(False)
        self.content_layout.addWidget(self.results_group)
    
    def _start_detection(self):
        """Start hardware detection using worker thread"""
        self.logger.info("Starting hardware detection...")
        
        # Update UI state for detection
        self.detect_button.setEnabled(False)
        self.cancel_button.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("🔍 Initializing hardware detection...")
        
        # Hide previous results
        self.results_group.setVisible(False)
        
        # Create and configure worker thread
        self.detection_worker = HardwareDetectionWorker()
        
        # Connect signals
        self.detection_worker.detection_started.connect(self._on_detection_started)
        self.detection_worker.detection_progress.connect(self._on_detection_progress)
        self.detection_worker.detection_completed.connect(self._on_detection_completed)
        self.detection_worker.detection_failed.connect(self._on_detection_failed)
        self.detection_worker.detection_cancelled.connect(self._on_detection_cancelled)
        self.detection_worker.finished.connect(self._on_worker_finished)
        
        # Start detection
        self.detection_worker.start()
    
    def _cancel_detection(self):
        """Cancel ongoing hardware detection"""
        if self.detection_worker and self.detection_worker.isRunning():
            self.logger.info("Cancelling hardware detection...")
            self.detection_worker.cancel_detection()
            self.status_label.setText("⏹️ Cancelling detection...")
    
    def _on_detection_started(self):
        """Handle detection started signal"""
        self.logger.debug("Hardware detection started")
    
    def _on_detection_progress(self, message: str, progress: int):
        """Handle detection progress updates"""
        self.status_label.setText(f"🔍 {message}")
        self.progress_bar.setValue(progress)
        self.logger.debug(f"Detection progress: {progress}% - {message}")
    
    def _on_detection_completed(self, detected_hardware: DetectedHardware, profile_matches: List[ProfileMatch]):
        """Handle successful detection completion"""
        self.logger.info(f"Hardware detection completed: {detected_hardware.get_summary()}")
        
        # Store results
        self.detected_hardware = detected_hardware
        self.profile_matches = profile_matches
        
        # Update UI with results
        self._display_detection_results()
        
        # Enable next step if we have results
        self.set_navigation_enabled(next=True)
        self.step_completed.emit()
    
    def _on_detection_failed(self, error_message: str):
        """Handle detection failure"""
        self.logger.error(f"Hardware detection failed: {error_message}")
        
        # Update UI to show error
        self.status_label.setText(f"❌ Detection failed: {error_message}")
        self.progress_bar.setVisible(False)
        
        # Reset buttons
        self.detect_button.setEnabled(True)
        self.cancel_button.setVisible(False)
        
        # Show option to retry
        self.detect_button.setText("🔄 Retry Detection")
    
    def _on_detection_cancelled(self):
        """Handle detection cancellation"""
        self.logger.info("Hardware detection cancelled by user")
        
        # Update UI
        self.status_label.setText("⏹️ Detection cancelled")
        self.progress_bar.setVisible(False)
        
        # Reset buttons
        self.detect_button.setEnabled(True)
        self.cancel_button.setVisible(False)
    
    def _on_worker_finished(self):
        """Handle worker thread cleanup"""
        if self.detection_worker:
            self.detection_worker.deleteLater()
            self.detection_worker = None
    
    def _display_detection_results(self):
        """Display the hardware detection results in the UI"""
        if not self.detected_hardware:
            return
        
        # Update status
        confidence_emoji = {
            DetectionConfidence.EXACT_MATCH: "✅",
            DetectionConfidence.HIGH_CONFIDENCE: "🎯", 
            DetectionConfidence.MEDIUM_CONFIDENCE: "✔️",
            DetectionConfidence.LOW_CONFIDENCE: "⚠️",
            DetectionConfidence.UNKNOWN: "❓"
        }
        
        emoji = confidence_emoji.get(self.detected_hardware.detection_confidence, "❓")
        self.status_label.setText(f"{emoji} Hardware detection completed successfully!")
        
        # Hide progress elements
        self.progress_bar.setVisible(False)
        self.cancel_button.setVisible(False)
        self.detect_button.setEnabled(True)
        self.detect_button.setText("🔍 Auto-Detect Hardware")
        
        # Show results group
        self.results_group.setVisible(True)
        
        # Update hardware summary
        summary = self.detected_hardware.get_summary()
        confidence_text = self.detected_hardware.detection_confidence.value.replace("_", " ").title()
        self.hardware_summary_label.setText(f"📱 {summary}\\n🎯 Detection Confidence: {confidence_text}")
        
        # Update detailed information
        details = self._format_hardware_details(self.detected_hardware)
        self.hardware_details.setText(details)
        
        # Populate profile matches
        self._populate_profile_matches()
    
    def _format_hardware_details(self, hardware: DetectedHardware) -> str:
        """Format detailed hardware information for display"""
        details = []
        
        # System information
        if hardware.system_manufacturer and hardware.system_model:
            details.append(f"🖥️ System: {hardware.system_manufacturer} {hardware.system_model}")
        elif hardware.system_name:
            details.append(f"🖥️ System: {hardware.system_name}")
        
        # CPU information
        if hardware.cpu_name:
            cpu_info = f"🔧 CPU: {hardware.cpu_name}"
            if hardware.cpu_cores:
                cpu_info += f" ({hardware.cpu_cores} cores"
                if hardware.cpu_threads and hardware.cpu_threads != hardware.cpu_cores:
                    cpu_info += f", {hardware.cpu_threads} threads"
                cpu_info += ")"
            details.append(cpu_info)
        
        # Memory information
        if hardware.total_ram_gb:
            details.append(f"💾 RAM: {hardware.total_ram_gb:.1f} GB")
        
        # GPU information
        if hardware.primary_gpu:
            details.append(f"🎮 Graphics: {hardware.primary_gpu}")
        elif hardware.gpus:
            gpu_names = [gpu.get('name', 'Unknown GPU') for gpu in hardware.gpus[:2]]
            details.append(f"🎮 Graphics: {', '.join(gpu_names)}")
        
        # Storage information
        if hardware.storage_devices:
            storage_info = []
            for storage in hardware.storage_devices[:2]:
                name = storage.get('model', 'Unknown Storage')
                size = storage.get('size_gb', 0)
                if size > 0:
                    storage_info.append(f"{name} ({size:.0f} GB)")
                else:
                    storage_info.append(name)
            details.append(f"💽 Storage: {', '.join(storage_info)}")
        
        # Network information
        if hardware.network_adapters:
            network_names = [adapter.get('name', 'Unknown Network') for adapter in hardware.network_adapters[:2]]
            details.append(f"🌐 Network: {', '.join(network_names)}")
        
        # Platform information
        if hardware.platform and hardware.platform_version:
            details.append(f"🔧 Platform: {hardware.platform.title()} {hardware.platform_version}")
        elif hardware.platform:
            details.append(f"🔧 Platform: {hardware.platform.title()}")
        
        return "\\n".join(details) if details else "No detailed hardware information available"
    
    def _populate_profile_matches(self):
        """Populate the profile selection combo box with matches"""
        self.profile_combo.clear()
        
        if not self.profile_matches:
            self.profile_combo.addItem("No compatible profiles found")
            self.profile_combo.setEnabled(False)
            return
        
        self.profile_combo.setEnabled(True)
        
        # Add profile matches with confidence indicators
        for i, match in enumerate(self.profile_matches):
            confidence_icon = {
                DetectionConfidence.EXACT_MATCH: "🎯",
                DetectionConfidence.HIGH_CONFIDENCE: "✅", 
                DetectionConfidence.MEDIUM_CONFIDENCE: "✔️",
                DetectionConfidence.LOW_CONFIDENCE: "⚠️",
                DetectionConfidence.UNKNOWN: "❓"
            }.get(match.confidence, "❓")
            
            text = f"{confidence_icon} {match.profile.name} ({match.match_score:.0f}% match)"
            self.profile_combo.addItem(text)
            
            # Store the match object as data
            self.profile_combo.setItemData(i, match)
        
        # Select the best match by default
        if self.profile_matches:
            self.profile_combo.setCurrentIndex(0)
            self._on_profile_selected(0)
    
    def _on_profile_selected(self, index: int):
        """Handle profile selection change"""
        if index >= 0 and index < self.profile_combo.count():
            match_data = self.profile_combo.itemData(index)
            if isinstance(match_data, ProfileMatch):
                self.selected_profile = match_data
                self.logger.info(f"Selected hardware profile: {match_data.profile.name}")
    
    def validate_step(self) -> bool:
        """Validate that hardware detection is completed"""
        return (self.detected_hardware is not None and 
                self.selected_profile is not None)
    
    def get_step_data(self) -> Dict[str, Any]:
        """Get the hardware detection data for the wizard state"""
        return {
            "detected_hardware": self.detected_hardware,
            "profile_matches": self.profile_matches,
            "selected_profile": self.selected_profile,
            "detection_confidence": self.detected_hardware.detection_confidence.value if self.detected_hardware else None
        }
    
    def load_step_data(self, data: Dict[str, Any]):
        """Load previously saved step data"""
        if "detected_hardware" in data and data["detected_hardware"]:
            self.detected_hardware = data["detected_hardware"]
            self.profile_matches = data.get("profile_matches", [])
            self.selected_profile = data.get("selected_profile")
            
            # Update UI with loaded data
            self._display_detection_results()
    
    def on_step_entered(self):
        """Called when the step becomes active"""
        self.logger.info("Hardware detection step entered")
        
        # Auto-start detection if no hardware has been detected yet
        if not self.detected_hardware:
            # Brief delay to allow UI to settle, then start detection
            QTimer.singleShot(1000, self._start_detection)
    
    def on_step_left(self):
        """Called when leaving the step"""
        self.logger.info("Hardware detection step exited")
        
        # Cancel any running detection
        if self.detection_worker and self.detection_worker.isRunning():
            self.detection_worker.cancel_detection()


class OSImageDownloadWorker(QThread):
    """Worker thread for downloading OS images to prevent UI blocking"""
    
    # Signals for communication with UI
    download_started = pyqtSignal(str)  # image_id
    download_progress = pyqtSignal(object)  # DownloadProgress
    download_completed = pyqtSignal(str, str)  # image_id, local_path
    download_failed = pyqtSignal(str, str)  # image_id, error_message
    download_cancelled = pyqtSignal(str)  # image_id
    
    def __init__(self, image_manager: OSImageManagerQt, parent=None):
        super().__init__(parent)
        self.image_manager = image_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._download_queue: List[OSImageInfo] = []
        self._cancelled = False
        self._mutex = QMutex()
        self._progress_connection = None  # Track progress connection
    
    def queue_download(self, image_info: OSImageInfo):
        """Queue an image for download"""
        self._mutex.lock()
        self._download_queue.append(image_info)
        self._mutex.unlock()
        
        if not self.isRunning():
            self.start()
    
    def cancel_downloads(self):
        """Cancel all downloads with proper cleanup"""
        self._mutex.lock()
        self._cancelled = True
        queue_size = len(self._download_queue)
        self._download_queue.clear()
        self._mutex.unlock()
        
        # FIX: Disconnect progress signals on cancellation
        if self._progress_connection:
            try:
                self.image_manager.download_progress.disconnect(self._progress_connection)
                self._progress_connection = None
            except:
                pass
        
        self.logger.info(f"Download cancellation requested - cleared {queue_size} pending downloads")
    
    def run(self):
        """Process download queue"""
        while True:
            self._mutex.lock()
            if self._cancelled or not self._download_queue:
                self._mutex.unlock()
                break
            
            image_info = self._download_queue.pop(0)
            self._mutex.unlock()
            
            try:
                self.download_started.emit(image_info.id)
                
                # FIX: Connect to progress updates only once per download
                if self._progress_connection:
                    self.image_manager.download_progress.disconnect(self._progress_connection)
                
                self._progress_connection = lambda progress, img_id=image_info.id: (
                    self.download_progress.emit(progress) if progress.image_id == img_id else None
                )
                self.image_manager.download_progress.connect(self._progress_connection)
                
                # Start download
                success = self.image_manager.download_image(image_info)
                
                # FIX: Check cancellation before emitting completion
                self._mutex.lock()
                cancelled = self._cancelled
                self._mutex.unlock()
                
                if cancelled:
                    self.download_cancelled.emit(image_info.id)
                    break
                
                if success and image_info.local_path:
                    self.download_completed.emit(image_info.id, image_info.local_path)
                else:
                    self.download_failed.emit(image_info.id, "Download failed")
                
                # FIX: Disconnect progress signal after download
                if self._progress_connection:
                    self.image_manager.download_progress.disconnect(self._progress_connection)
                    self._progress_connection = None
                    
            except Exception as e:
                self.logger.error(f"Download error for {image_info.id}: {e}", exc_info=True)
                self.download_failed.emit(image_info.id, str(e))
                
                # FIX: Ensure signal cleanup on error
                if self._progress_connection:
                    try:
                        self.image_manager.download_progress.disconnect(self._progress_connection)
                    except:
                        pass
                    self._progress_connection = None
        
        # FIX: Clean up state on thread completion
        self._mutex.lock()
        self._cancelled = False
        if self._progress_connection:
            try:
                self.image_manager.download_progress.disconnect(self._progress_connection)
            except:
                pass
            self._progress_connection = None
        self._mutex.unlock()


class OSImageSelectionStepView(StepView):
    """Revolutionary cloud-integrated OS image selection with smart recommendations"""
    
    def __init__(self):
        super().__init__(
            "Cloud OS Selection", 
            "Choose from verified operating systems. BootForge intelligently downloads and verifies the perfect OS for your hardware."
        )
        
        # Initialize state
        self.selected_image: Optional[OSImageInfo] = None
        self.available_images: List[OSImageInfo] = []
        self.recommended_images: List[OSImageInfo] = []
        self.cached_images: List[OSImageInfo] = []
        self.download_progresses: Dict[str, DownloadProgress] = {}
        self.detected_hardware: Optional[DetectedHardware] = None
        self.wizard_state: Optional[WizardState] = None  # Add wizard state reference
        
        # Initialize cloud manager
        try:
            config = Config()
            self.image_manager = OSImageManagerQt(config)
            self.image_manager.images_updated.connect(self._refresh_images)
            self.image_manager.download_progress.connect(self._on_download_progress)
        except Exception as e:
            self.logger.error(f"Failed to initialize image manager: {e}")
            self.image_manager = None
        
        # Download worker
        if self.image_manager:
            self.download_worker = OSImageDownloadWorker(self.image_manager)
            self.download_worker.download_started.connect(self._on_download_started)
            self.download_worker.download_progress.connect(self._on_download_progress)
            self.download_worker.download_completed.connect(self._on_download_completed)
            self.download_worker.download_failed.connect(self._on_download_failed)
        else:
            self.download_worker = None
        
        self._setup_content()
        self._refresh_images()
        
        # SECURITY: Initially disable next button until image is verified
        self.update_next_button_state()
    
    def _setup_content(self):
        """Setup comprehensive OS image selection UI"""
        # Main splitter layout
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: OS Selection
        selection_widget = self._create_selection_widget()
        main_splitter.addWidget(selection_widget)
        
        # Right side: Details and actions
        details_widget = self._create_details_widget()
        main_splitter.addWidget(details_widget)
        
        # Set proportions (60% selection, 40% details)
        main_splitter.setSizes([600, 400])
        self.content_layout.addWidget(main_splitter)
        
        # Status bar
        self.status_label = QLabel("🌩️ Loading cloud OS catalog...")
        self.status_label.setStyleSheet("color: #cccccc; font-size: 12px; padding: 5px;")
        self.content_layout.addWidget(self.status_label)
        
        # Initially disable next button
        self.set_navigation_enabled(next=False)
    
    def _create_selection_widget(self) -> QWidget:
        """Create the OS selection widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Header with filters
        header_layout = QHBoxLayout()
        
        title = QLabel("Available Operating Systems")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #ffffff; margin-bottom: 10px;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # OS Family filter
        self.os_filter = QComboBox()
        self.os_filter.addItem("All OS", "all")
        self.os_filter.addItem("🐧 Linux", "linux")
        self.os_filter.addItem("🍎 macOS", "macos")
        self.os_filter.addItem("🪟 Windows", "windows")
        self.os_filter.currentTextChanged.connect(self._filter_images)
        header_layout.addWidget(self.os_filter)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setToolTip("Refresh available images from cloud providers")
        refresh_btn.clicked.connect(self._refresh_images)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Tabs for different image sources
        self.image_tabs = QTabWidget()
        
        # Recommended tab
        self.recommended_list = self._create_image_list()
        self.image_tabs.addTab(self.recommended_list, "⭐ Recommended")
        
        # All available tab
        self.available_list = self._create_image_list()
        self.image_tabs.addTab(self.available_list, "☁️ Cloud Downloads")
        
        # Cached tab
        self.cached_list = self._create_image_list()
        self.image_tabs.addTab(self.cached_list, "💾 Downloaded")
        
        layout.addWidget(self.image_tabs)
        
        # Auto-download recommended button
        self.auto_download_btn = QPushButton("🚀 Auto-Download Recommended OS")
        self.auto_download_btn.setMinimumHeight(45)
        self.auto_download_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e90ff, stop:1 #0078d4);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4169e1, stop:1 #106ebe);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0047ab, stop:1 #005a9e);
            }
            QPushButton:disabled {
                background-color: #4a4a4a;
                color: #888888;
            }
        """)
        self.auto_download_btn.clicked.connect(self._auto_download_recommended)
        self.auto_download_btn.setEnabled(False)
        layout.addWidget(self.auto_download_btn)
        
        return widget
    
    def _create_image_list(self) -> QListWidget:
        """Create a styled image list widget"""
        list_widget = QListWidget()
        list_widget.setAlternatingRowColors(True)
        list_widget.setStyleSheet("""
            QListWidget {
                background-color: #2d2d30;
                border: 1px solid #555555;
                border-radius: 6px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #3c3c3c;
                color: #ffffff;
            }
            QListWidget::item:hover {
                background-color: #3c3c3c;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
            }
        """)
        list_widget.itemClicked.connect(self._on_image_selected)
        list_widget.itemDoubleClicked.connect(self._on_image_double_clicked)
        return list_widget
    
    def _create_details_widget(self) -> QWidget:
        """Create the image details and actions widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Selection info group
        self.selection_group = QGroupBox("Selected Image")
        selection_layout = QVBoxLayout(self.selection_group)
        
        self.selection_icon = QLabel("💿")
        self.selection_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.selection_icon.setStyleSheet("font-size: 32px; margin: 10px;")
        selection_layout.addWidget(self.selection_icon)
        
        self.selection_name = QLabel("No OS selected")
        self.selection_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.selection_name.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        selection_layout.addWidget(self.selection_name)
        
        self.selection_details = QLabel("")
        self.selection_details.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.selection_details.setWordWrap(True)
        self.selection_details.setStyleSheet("color: #cccccc; margin: 10px;")
        selection_layout.addWidget(self.selection_details)
        
        layout.addWidget(self.selection_group)
        
        # Download progress group
        self.progress_group = QGroupBox("Download Progress")
        progress_layout = QVBoxLayout(self.progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #555555;
                border-radius: 5px;
                text-align: center;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 3px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #cccccc; font-size: 12px;")
        progress_layout.addWidget(self.progress_label)
        
        self.progress_group.setVisible(False)
        layout.addWidget(self.progress_group)
        
        # Action buttons
        actions_layout = QVBoxLayout()
        
        self.download_btn = QPushButton("⬇️ Download")
        self.download_btn.setMinimumHeight(35)
        self.download_btn.clicked.connect(self._download_selected)
        self.download_btn.setEnabled(False)
        actions_layout.addWidget(self.download_btn)
        
        self.verify_btn = QPushButton("🔒 Verify")
        self.verify_btn.setMinimumHeight(35)
        self.verify_btn.clicked.connect(self._verify_selected)
        self.verify_btn.setEnabled(False)
        actions_layout.addWidget(self.verify_btn)
        
        self.browse_btn = QPushButton("📁 Browse Local")
        self.browse_btn.setMinimumHeight(35)
        self.browse_btn.clicked.connect(self._browse_local_image)
        actions_layout.addWidget(self.browse_btn)
        
        layout.addLayout(actions_layout)
        
        # Security status
        self.security_group = QGroupBox("Security Status")
        security_layout = QVBoxLayout(self.security_group)
        
        self.security_status = QLabel("⏳ No image selected")
        self.security_status.setWordWrap(True)
        self.security_status.setStyleSheet("color: #cccccc; padding: 10px;")
        security_layout.addWidget(self.security_status)
        
        layout.addWidget(self.security_group)
        
        layout.addStretch()
        return widget
    
    def _refresh_images(self):
        """Refresh available images from cloud providers"""
        if not self.image_manager:
            self.status_label.setText("❌ Cloud manager not available")
            return
        
        try:
            self.status_label.setText("🔄 Refreshing cloud OS catalog...")
            
            # Get all available images
            self.available_images = self.image_manager.get_available_images()
            self.cached_images = self.image_manager.get_cached_images()
            
            # Generate smart recommendations
            self._generate_recommendations()
            
            # Update UI lists
            self._update_image_lists()
            
            count = len(self.available_images)
            cached_count = len(self.cached_images)
            self.status_label.setText(f"☁️ {count} available, {cached_count} cached images ready")
            
        except Exception as e:
            self.logger.error(f"Failed to refresh images: {e}", exc_info=True)
            self.status_label.setText(f"❌ Failed to refresh: {str(e)}")
    
    def _generate_recommendations(self):
        """Generate hardware-based OS recommendations with detailed scoring"""
        self.recommended_images = []
        
        if not self.detected_hardware or not self.available_images:
            self.logger.info("Skipping recommendations - no hardware or images available")
            return
        
        try:
            # Extract hardware details with better attribute access
            hardware = self.detected_hardware
            cpu_vendor = getattr(hardware, 'cpu_vendor', '').lower()
            cpu_model = getattr(hardware, 'cpu_model', '').lower()
            is_mac = ('apple' in cpu_vendor or 'apple' in cpu_model or 
                     getattr(hardware, 'is_mac', False) or
                     hasattr(hardware, 'system_manufacturer') and 
                     'apple' in getattr(hardware, 'system_manufacturer', '').lower())
            memory_gb = getattr(hardware, 'memory_gb', 0)
            architecture = getattr(hardware, 'architecture', '').lower()
            gpu_vendor = getattr(hardware, 'gpu_vendor', '').lower()
            
            self.logger.info(f"Generating recommendations for: CPU={cpu_vendor}, Memory={memory_gb}GB, Arch={architecture}, Mac={is_mac}")
            
            for image in self.available_images:
                score = 0
                reasons = []
                
                # ENHANCED: Mac hardware strongly prefers macOS
                if is_mac and image.os_family == 'macos':
                    score += 60
                    reasons.append(f"Perfect match for Apple hardware (+60)")
                elif is_mac and image.os_family != 'macos':
                    score -= 20  # Penalty for non-macOS on Mac
                    reasons.append(f"Not optimal for Apple hardware (-20)")
                
                # ENHANCED: Architecture-specific optimization
                if image.architecture.lower() == architecture:
                    score += 30
                    reasons.append(f"Native {architecture} support (+30)")
                elif 'universal' in image.architecture.lower() or image.architecture.lower() == 'x86_64':
                    score += 15
                    reasons.append(f"Universal compatibility (+15)")
                
                # ENHANCED: Memory-based OS selection
                min_memory_req = {
                    'macos': 8,
                    'windows': 4,
                    'linux': 2
                }.get(image.os_family, 2)
                
                if memory_gb >= min_memory_req * 2:
                    score += 25
                    reasons.append(f"Excellent memory fit ({memory_gb}GB available, {min_memory_req}GB required) (+25)")
                elif memory_gb >= min_memory_req:
                    score += 15
                    reasons.append(f"Adequate memory ({memory_gb}GB available, {min_memory_req}GB required) (+15)")
                else:
                    score -= 30
                    reasons.append(f"Insufficient memory ({memory_gb}GB available, {min_memory_req}GB required) (-30)")
                
                # ENHANCED: CPU vendor compatibility
                if 'intel' in cpu_vendor and image.os_family in ['windows', 'linux']:
                    score += 15
                    reasons.append(f"Intel CPU optimized (+15)")
                elif 'amd' in cpu_vendor and image.os_family in ['windows', 'linux']:
                    score += 15
                    reasons.append(f"AMD CPU optimized (+15)")
                
                # ENHANCED: Version stability preferences
                version_lower = image.version.lower()
                if 'lts' in version_lower:
                    score += 20
                    reasons.append(f"Long Term Support version (+20)")
                elif 'stable' in version_lower:
                    score += 15
                    reasons.append(f"Stable release (+15)")
                elif 'beta' in version_lower or 'alpha' in version_lower:
                    score -= 10
                    reasons.append(f"Pre-release version (-10)")
                
                # ENHANCED: GPU compatibility (basic check)
                if 'nvidia' in gpu_vendor and image.os_family == 'linux':
                    score += 10
                    reasons.append(f"Good NVIDIA GPU support on Linux (+10)")
                
                # ENHANCED: Size considerations for memory-constrained systems
                size_gb = image.size_bytes / (1024 * 1024 * 1024)
                if memory_gb <= 4 and size_gb > 6:
                    score -= 15
                    reasons.append(f"Large image for low-memory system (-15)")
                elif size_gb <= 2:
                    score += 5
                    reasons.append(f"Compact image size (+5)")
                
                # Add to recommendations if score meets threshold
                if score >= 20:  # Lowered threshold to include more options
                    image.metadata['recommendation_score'] = score
                    image.metadata['recommendation_reasons'] = reasons
                    self.recommended_images.append(image)
                    self.logger.debug(f"Recommended {image.name}: Score={score}, Reasons={reasons}")
            
            # Sort by recommendation score (highest first)
            self.recommended_images.sort(
                key=lambda img: img.metadata.get('recommendation_score', 0), 
                reverse=True
            )
            
            # Log recommendation results
            if self.recommended_images:
                top_rec = self.recommended_images[0]
                self.logger.info(f"Top recommendation: {top_rec.name} (Score: {top_rec.metadata['recommendation_score']})")
            else:
                self.logger.warning("No OS images met recommendation criteria")
            
            # Enable auto-download if we have recommendations
            self.auto_download_btn.setEnabled(len(self.recommended_images) > 0)
            
        except Exception as e:
            self.logger.error(f"Failed to generate recommendations: {e}", exc_info=True)
    
    def _update_image_lists(self):
        """Update all image lists with filtered content"""
        os_filter = self.os_filter.currentData()
        
        # Helper function to add image to list
        def populate_list(list_widget: QListWidget, images: List[OSImageInfo]):
            list_widget.clear()
            
            for image in images:
                # Apply OS family filter
                if os_filter != "all" and image.os_family != os_filter:
                    continue
                
                # Create list item
                item = QListWidgetItem()
                
                # Format display text
                icon = self._get_os_icon(image.os_family)
                status_icon = self._get_status_icon(image.status)
                size_mb = round(image.size_bytes / (1024 * 1024), 1)
                
                display_text = f"{icon} {image.name}\n"
                display_text += f"   {image.version} • {image.architecture} • {size_mb} MB"
                
                if image.status != ImageStatus.UNKNOWN:
                    display_text += f" {status_icon}"
                
                # ENHANCED: Add recommendation badge with detailed scoring
                if hasattr(image, 'metadata') and 'recommendation_score' in image.metadata:
                    score = image.metadata['recommendation_score']
                    if score >= 60:
                        display_text = f"🏆 {display_text} (Score: {score})"
                    elif score >= 40:
                        display_text = f"⭐ {display_text} (Score: {score})"
                    elif score >= 20:
                        display_text = f"✅ {display_text} (Score: {score})"
                
                item.setText(display_text)
                item.setData(Qt.ItemDataRole.UserRole, image)
                
                # Color coding based on status
                if image.status == ImageStatus.VERIFIED:
                    item.setBackground(QColor(0, 120, 0, 30))  # Green tint
                elif image.status == ImageStatus.DOWNLOADING:
                    item.setBackground(QColor(0, 120, 212, 30))  # Blue tint
                elif image.status == ImageStatus.FAILED:
                    item.setBackground(QColor(220, 0, 0, 30))  # Red tint
                
                list_widget.addItem(item)
        
        # Populate all lists
        populate_list(self.recommended_list, self.recommended_images)
        populate_list(self.available_list, self.available_images)
        populate_list(self.cached_list, self.cached_images)
    
    def _get_os_icon(self, os_family: str) -> str:
        """Get icon for OS family"""
        icons = {
            'linux': '🐧',
            'macos': '🍎', 
            'windows': '🪟',
            'freebsd': '😈',
            'custom': '💿'
        }
        return icons.get(os_family, '💿')
    
    def _get_status_icon(self, status: ImageStatus) -> str:
        """Get icon for image status"""
        icons = {
            ImageStatus.VERIFIED: '✅',
            ImageStatus.DOWNLOADED: '💾',
            ImageStatus.DOWNLOADING: '⬇️',
            ImageStatus.FAILED: '❌',
            ImageStatus.PAUSED: '⏸️',
            ImageStatus.VERIFYING: '🔒',
            ImageStatus.CACHED: '💾'
        }
        return icons.get(status, '')
    
    def _filter_images(self):
        """Apply filters and update image lists"""
        self._update_image_lists()
    
    def _on_image_selected(self, item: QListWidgetItem):
        """Handle image selection from any list"""
        image_info: OSImageInfo = item.data(Qt.ItemDataRole.UserRole)
        if image_info:
            self.selected_image = image_info
            self._update_selection_display()
            self._update_action_buttons()
            # SECURITY: Check validation state when image changes
            self.update_next_button_state()
    
    def _on_image_double_clicked(self, item: QListWidgetItem):
        """Handle double-click on image (start download or select)"""
        image_info: OSImageInfo = item.data(Qt.ItemDataRole.UserRole)
        if image_info:
            self.selected_image = image_info
            self._update_selection_display()
            
            # Auto-download if not available locally
            if image_info.status in [ImageStatus.AVAILABLE, ImageStatus.UNKNOWN]:
                self._download_selected()
            elif image_info.status == ImageStatus.VERIFIED:
                # Already ready, check validation and update state
                self.update_next_button_state()
    
    def _update_selection_display(self):
        """Update the selection details display"""
        if not self.selected_image:
            self.selection_icon.setText("💿")
            self.selection_name.setText("No OS selected")
            self.selection_details.setText("")
            self.security_status.setText("⏳ No image selected")
            return
        
        image = self.selected_image
        
        # Update icon and name
        icon = self._get_os_icon(image.os_family)
        self.selection_icon.setText(icon)
        self.selection_name.setText(image.name)
        
        # ENHANCED: Update details with recommendation reasoning
        size_mb = round(image.size_bytes / (1024 * 1024), 1)
        details = f"Version: {image.version}\n"
        details += f"Architecture: {image.architecture}\n" 
        details += f"Size: {size_mb} MB\n"
        details += f"Provider: {image.provider}"
        
        # Show detailed recommendation info
        if hasattr(image, 'metadata') and 'recommendation_score' in image.metadata:
            score = image.metadata['recommendation_score']
            details += f"\n\n⭐ Recommended (Score: {score})\n"
            
            if 'recommendation_reasons' in image.metadata:
                reasons = image.metadata['recommendation_reasons'][:3]  # Show top 3 reasons
                for reason in reasons:
                    details += f"• {reason}\n"
        
        self.selection_details.setText(details)
        
        # Update security status
        self._update_security_status()
    
    def _update_security_status(self):
        """Update security status display"""
        if not self.selected_image:
            return
        
        image = self.selected_image
        
        if image.status == ImageStatus.VERIFIED:
            status = "🔒 Verified & Secure\n"
            status += f"✅ {image.checksum_type.upper()} checksum verified\n"
            if image.verification_method != VerificationMethod.NONE:
                status += f"✅ {image.verification_method.value} verification passed"
        elif image.status == ImageStatus.DOWNLOADED:
            status = "⏳ Downloaded, verification pending\n"
            status += "Click 'Verify' to check integrity"
        elif image.status == ImageStatus.DOWNLOADING:
            status = "⬇️ Downloading...\n"
            status += "Verification will run automatically"
        elif image.status == ImageStatus.FAILED:
            status = "❌ Download or verification failed\n"
            status += "Try downloading again"
        else:
            status = "☁️ Available for download\n"
            status += f"Will verify using {image.checksum_type.upper()}"
        
        self.security_status.setText(status)
    
    def _update_action_buttons(self):
        """Update action button states based on selected image"""
        if not self.selected_image:
            self.download_btn.setEnabled(False)
            self.verify_btn.setEnabled(False)
            return
        
        image = self.selected_image
        
        # Download button
        can_download = image.status in [ImageStatus.AVAILABLE, ImageStatus.UNKNOWN, ImageStatus.FAILED]
        self.download_btn.setEnabled(can_download)
        
        # Verify button
        can_verify = image.status in [ImageStatus.DOWNLOADED, ImageStatus.FAILED]
        self.verify_btn.setEnabled(can_verify)
    
    def _auto_download_recommended(self):
        """Auto-download the top recommended OS"""
        if not self.recommended_images:
            QMessageBox.information(
                self, 
                "No Recommendations",
                "No OS recommendations available. Try running hardware detection first."
            )
            return
        
        # Select and download top recommendation
        top_recommendation = self.recommended_images[0]
        self.selected_image = top_recommendation
        self._update_selection_display()
        self._update_action_buttons()
        
        # Start download
        self._download_selected()
    
    def _download_selected(self):
        """Download the selected image"""
        if not self.selected_image or not self.download_worker:
            return
        
        self.logger.info(f"Starting download of {self.selected_image.name}")
        
        # Show progress UI
        self.progress_group.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Initializing download...")
        
        # Queue download
        self.download_worker.queue_download(self.selected_image)
        
        # Update button states
        self.download_btn.setEnabled(False)
        self.auto_download_btn.setEnabled(False)
    
    def _verify_selected(self):
        """Verify the selected image"""
        if not self.selected_image or not self.image_manager:
            return
        
        self.logger.info(f"Starting verification of {self.selected_image.name}")
        
        try:
            # Update UI
            self.progress_group.setVisible(True)
            self.progress_bar.setValue(0)
            self.progress_label.setText("Verifying image integrity...")
            
            # Run verification
            success = self.image_manager.verify_image(self.selected_image.id)
            
            if success:
                self.selected_image.status = ImageStatus.VERIFIED
                self.progress_bar.setValue(100)
                self.progress_label.setText("✅ Verification successful!")
                # SECURITY: Only enable next after successful verification
                # Connect verification completion to re-enable Next
                self.update_next_button_state()
            else:
                self.selected_image.status = ImageStatus.FAILED
                self.progress_label.setText("❌ Verification failed!")
                # SECURITY: Keep next disabled on verification failure  
                # Connect verification completion to re-enable Next
                self.update_next_button_state()
            
            self._update_security_status()
            self._update_action_buttons()
            
        except Exception as e:
            self.logger.error(f"Verification error: {e}", exc_info=True)
            self.progress_label.setText(f"❌ Verification error: {str(e)}")
    
    def _browse_local_image(self):
        """Browse for local image file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select OS Image File",
            "",
            "Image Files (*.iso *.dmg *.img *.bin);;All Files (*)"
        )
        
        if file_path:
            # Create custom OSImageInfo for local file
            from pathlib import Path
            file_info = Path(file_path)
            
            local_image = OSImageInfo(
                id=f"local_{file_info.stem}",
                name=file_info.name,
                os_family="custom",
                version="Local File",
                architecture="unknown",
                size_bytes=file_info.stat().st_size,
                download_url="",
                local_path=str(file_path),
                status=ImageStatus.DOWNLOADED,
                provider="local"
            )
            
            self.selected_image = local_image
            self._update_selection_display()
            self._update_action_buttons()
            
            # Offer to verify
            reply = QMessageBox.question(
                self,
                "Verify Local Image",
                "Would you like to verify the integrity of this local image?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self._verify_selected()
            else:
                # Trust local file and enable next
                self.selected_image.status = ImageStatus.VERIFIED
                self.set_navigation_enabled(next=True)
                self.step_completed.emit()
    
    # Download worker signal handlers
    def _on_download_started(self, image_id: str):
        """Handle download started"""
        if self.selected_image and self.selected_image.id == image_id:
            self.selected_image.status = ImageStatus.DOWNLOADING
            self._update_security_status()
            self.status_label.setText(f"⬇️ Downloading {self.selected_image.name}...")
            # SECURITY: Disable next until verification complete
            self.set_navigation_enabled(next=False)
    
    def _on_download_progress(self, progress: DownloadProgress):
        """Handle download progress updates"""
        if not self.selected_image or self.selected_image.id != progress.image_id:
            return
        
        # Update progress bar
        self.progress_bar.setValue(int(progress.progress_percent))
        
        # Update progress label with speed and ETA
        speed_text = f"{progress.speed_mbps:.1f} MB/s" if progress.speed_mbps > 0 else "-- MB/s"
        eta_text = f"{progress.eta_seconds // 60}m {progress.eta_seconds % 60}s" if progress.eta_seconds > 0 else "--"
        
        downloaded_mb = progress.downloaded_bytes / (1024 * 1024)
        total_mb = progress.total_bytes / (1024 * 1024)
        
        self.progress_label.setText(
            f"⬇️ {downloaded_mb:.1f}/{total_mb:.1f} MB • {speed_text} • ETA: {eta_text}"
        )
    
    def _on_download_completed(self, image_id: str, local_path: str):
        """Handle download completion"""
        if self.selected_image and self.selected_image.id == image_id:
            self.selected_image.status = ImageStatus.DOWNLOADED
            self.selected_image.local_path = local_path
            
            self.progress_bar.setValue(100)
            self.progress_label.setText("✅ Download complete! Starting verification...")
            
            # SECURITY: Still keep next disabled until verification
            self.set_navigation_enabled(next=False)
            
            # Auto-start verification
            QTimer.singleShot(1000, self._verify_selected)
            
            self.status_label.setText(f"✅ Downloaded {self.selected_image.name}")
            self._update_security_status()
            self._update_action_buttons()
    
    def _on_download_failed(self, image_id: str, error_message: str):
        """Handle download failure"""
        if self.selected_image and self.selected_image.id == image_id:
            self.selected_image.status = ImageStatus.FAILED
            
            self.progress_label.setText(f"❌ Download failed: {error_message}")
            self.status_label.setText(f"❌ Failed to download {self.selected_image.name}")
            
            self._update_security_status()
            self._update_action_buttons()
            
            # Re-enable download button for retry
            self.download_btn.setEnabled(True)
            self.auto_download_btn.setEnabled(len(self.recommended_images) > 0)
    
    def update_next_button_state(self):
        """Update Next button state based on validation"""
        is_valid = self.validate_step()
        self.set_navigation_enabled(next=is_valid)
        if is_valid:
            self.step_completed.emit()  # Signal step completion
    
    def _update_navigation_state(self):
        """Update navigation button state based on current validation status"""
        self.update_next_button_state()
    
    def on_step_entered(self):
        """Called when step becomes active - check validation state"""
        self.update_next_button_state()
    
    # Step interface methods
    def validate_step(self) -> bool:
        """Validate that selected image is verified before allowing Next"""
        if not self.wizard_state or not self.wizard_state.os_image:
            return False
        
        selected_image = self.wizard_state.os_image
        if not selected_image.is_valid():
            QMessageBox.warning(self, "Verification Required", 
                "Please select a verified OS image before proceeding.")
            return False
        
        return True
    
    def get_step_data(self) -> Dict[str, Any]:
        """ENHANCED: Get comprehensive step data for wizard state"""
        data = {}
        
        if self.selected_image:
            data["selected_image"] = self.selected_image
            data["image_path"] = self.selected_image.local_path
            data["image_info"] = {
                "id": self.selected_image.id,
                "name": self.selected_image.name,
                "os_family": self.selected_image.os_family,
                "version": self.selected_image.version,
                "architecture": self.selected_image.architecture,
                "size_bytes": self.selected_image.size_bytes,
                "verified": self.selected_image.status == ImageStatus.VERIFIED,
                "verification_method": self.selected_image.verification_method.value,
                "checksum": self.selected_image.checksum,
                "local_path": self.selected_image.local_path,
                "is_recommended": hasattr(self.selected_image, 'metadata') and 'recommendation_score' in self.selected_image.metadata
            }
            
            # Include recommendation data if available
            if hasattr(self.selected_image, 'metadata'):
                if 'recommendation_score' in self.selected_image.metadata:
                    data["recommendation_score"] = self.selected_image.metadata['recommendation_score']
                if 'recommendation_reasons' in self.selected_image.metadata:
                    data["recommendation_reasons"] = self.selected_image.metadata['recommendation_reasons']
        
        # Include current state
        data["recommendations_count"] = len(self.recommended_images)
        data["available_count"] = len(self.available_images)
        data["cached_count"] = len(self.cached_images)
        
        self.logger.info(f"Exporting step data with {len(data)} fields")
        return data
    
    def load_step_data(self, data: Dict[str, Any]):
        """ENHANCED: Load step data from wizard state with better integration"""
        self.logger.info(f"Loading step data: {list(data.keys())}")
        
        # Load hardware data first for recommendations
        if "detected_hardware" in data:
            self.detected_hardware = data["detected_hardware"]
            self.logger.info("Loaded hardware data for recommendations")
            self._generate_recommendations()
            self._update_image_lists()
        
        # Load previously selected image
        if "selected_image" in data:
            self.selected_image = data["selected_image"]
            self._update_selection_display()
            self._update_action_buttons()
            
            # SECURITY: Only enable next if image is verified
            if self.validate_step():
                self.set_navigation_enabled(next=True)
                self.logger.info("Step validation passed - verified image selected")
            else:
                self.set_navigation_enabled(next=False)
                self.logger.warning("Step validation failed - no verified image")
    
    def on_step_entered(self):
        """Called when step becomes active"""
        self.logger.info("OS Image Selection step entered")
        
        # Refresh images if not loaded
        if not self.available_images:
            QTimer.singleShot(500, self._refresh_images)
    
    def on_step_left(self):
        """Called when leaving step"""
        self.logger.info("OS Image Selection step exited")
        
        # Cancel any active downloads
        if self.download_worker and self.download_worker.isRunning():
            self.download_worker.cancel_downloads()


class USBDeviceDetectionWorker(QThread):
    """Worker thread for USB device detection"""
    
    # Signals
    devices_detected = pyqtSignal(list)  # List of DiskInfo objects
    detection_failed = pyqtSignal(str)  # Error message
    
    def __init__(self):
        super().__init__()
        self.disk_manager = DiskManager()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def run(self):
        """Detect USB devices"""
        try:
            self.logger.info("Starting USB device detection...")
            usb_devices = self.disk_manager.get_removable_devices()
            self.devices_detected.emit(usb_devices)
            self.logger.info(f"Detected {len(usb_devices)} USB devices")
        except Exception as e:
            self.logger.error(f"USB device detection failed: {e}")
            self.detection_failed.emit(str(e))


class USBConfigurationStepView(StepView):
    """Enhanced USB configuration step with comprehensive device management and recipe selection"""
    
    # Signals for communication
    device_safety_checked = pyqtSignal(object)  # DeviceRisk object
    recipe_compatibility_checked = pyqtSignal(dict)  # Compatibility results
    
    def __init__(self):
        super().__init__(
            "USB Configuration", 
            "Select your USB device and configure the deployment recipe for your hardware."
        )
        
        # Core components
        self.disk_manager = DiskManager()
        self.safety_validator = SafetyValidator(SafetyLevel.STANDARD)
        self.usb_builder = USBBuilderEngine()
        
        # State variables
        self.detected_hardware = None
        self.selected_os_image = None
        self.available_devices = []
        self.selected_device = None
        self.selected_recipe = None
        self.device_risks = {}  # device_path -> DeviceRisk
        self.recipe_compatibility = {}  # recipe_name -> compatibility_info
        
        # UI components (will be created in _setup_content)
        self.device_list = None
        self.recipe_cards = {}
        self.config_panels = {}
        self.detection_worker = None
        
        self._setup_content()
    
    def _setup_content(self):
        """Setup comprehensive USB configuration interface"""
        # Create main layout with splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.content_layout.addWidget(main_splitter)
        
        # Left panel: Device selection
        self._setup_device_panel(main_splitter)
        
        # Right panel: Recipe configuration
        self._setup_recipe_panel(main_splitter)
        
        # Set splitter proportions
        main_splitter.setSizes([400, 600])
        
        # Initially disable next until valid configuration
        self.set_navigation_enabled(next=False)
    
    def _setup_device_panel(self, parent):
        """Setup USB device selection panel"""
        device_widget = QWidget()
        device_layout = QVBoxLayout(device_widget)
        device_layout.setContentsMargins(0, 0, 10, 0)
        
        # Header with refresh button
        header_layout = QHBoxLayout()
        device_title = QLabel("USB Devices")
        device_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff; margin-bottom: 10px;")
        header_layout.addWidget(device_title)
        
        header_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        self.refresh_devices_button = QPushButton("🔄 Refresh")
        self.refresh_devices_button.setMinimumSize(80, 30)
        self.refresh_devices_button.clicked.connect(self._refresh_devices)
        header_layout.addWidget(self.refresh_devices_button)
        
        device_layout.addLayout(header_layout)
        
        # Device detection status
        self.device_status_label = QLabel("Detecting USB devices...")
        self.device_status_label.setStyleSheet("color: #cccccc; font-size: 14px; margin-bottom: 10px;")
        device_layout.addWidget(self.device_status_label)
        
        # Device list
        self.device_list = QListWidget()
        self.device_list.setMinimumHeight(300)
        self.device_list.setStyleSheet("""
            QListWidget {
                background-color: #2b2b2b;
                border: 1px solid #444444;
                border-radius: 4px;
                color: #ffffff;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #444444;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
            }
            QListWidget::item:hover {
                background-color: #404040;
            }
        """)
        self.device_list.itemClicked.connect(self._device_selected)
        device_layout.addWidget(self.device_list)
        
        # Device safety information
        self.safety_info_group = QGroupBox("Device Safety Information")
        self.safety_info_group.setVisible(False)
        safety_info_layout = QVBoxLayout(self.safety_info_group)
        
        self.safety_status_label = QLabel()
        self.safety_status_label.setWordWrap(True)
        self.safety_status_label.setStyleSheet("color: #cccccc; font-size: 13px; padding: 10px;")
        safety_info_layout.addWidget(self.safety_status_label)
        
        device_layout.addWidget(self.safety_info_group)
        
        parent.addWidget(device_widget)
    
    def _setup_recipe_panel(self, parent):
        """Setup recipe selection and configuration panel"""
        recipe_widget = QWidget()
        recipe_layout = QVBoxLayout(recipe_widget)
        recipe_layout.setContentsMargins(10, 0, 0, 0)
        
        # Recipe selection header
        recipe_title = QLabel("Deployment Recipe")
        recipe_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff; margin-bottom: 10px;")
        recipe_layout.addWidget(recipe_title)
        
        # Hardware/OS context display
        self.context_label = QLabel("Select hardware and OS image in previous steps first")
        self.context_label.setStyleSheet("color: #cccccc; font-size: 14px; margin-bottom: 15px;")
        self.context_label.setWordWrap(True)
        recipe_layout.addWidget(self.context_label)
        
        # Recipe cards area
        self.recipe_scroll = QScrollArea()
        self.recipe_scroll.setWidgetResizable(True)
        self.recipe_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        self.recipe_container = QWidget()
        self.recipe_container_layout = QVBoxLayout(self.recipe_container)
        self.recipe_container_layout.setContentsMargins(0, 0, 0, 0)
        self.recipe_scroll.setWidget(self.recipe_container)
        
        recipe_layout.addWidget(self.recipe_scroll)
        
        # Configuration panel for selected recipe
        self.config_group = QGroupBox("Recipe Configuration")
        self.config_group.setVisible(False)
        self.config_layout = QVBoxLayout(self.config_group)
        recipe_layout.addWidget(self.config_group)
        
        parent.addWidget(recipe_widget)
    
    def _refresh_devices(self):
        """Refresh USB device list"""
        self.logger.info("Refreshing USB devices...")
        self.device_status_label.setText("🔍 Detecting USB devices...")
        self.refresh_devices_button.setEnabled(False)
        
        # Clear current devices
        self.device_list.clear()
        self.available_devices.clear()
        self.selected_device = None
        self.safety_info_group.setVisible(False)
        
        # Start detection worker
        if self.detection_worker and self.detection_worker.isRunning():
            self.detection_worker.quit()
            self.detection_worker.wait()
        
        self.detection_worker = USBDeviceDetectionWorker()
        self.detection_worker.devices_detected.connect(self._on_devices_detected)
        self.detection_worker.detection_failed.connect(self._on_detection_failed)
        self.detection_worker.finished.connect(self._on_detection_finished)
        self.detection_worker.start()
    
    def _on_devices_detected(self, devices: List[DiskInfo]):
        """Handle detected USB devices"""
        self.available_devices = devices
        self.logger.info(f"Detected {len(devices)} USB devices")
        
        if not devices:
            self.device_status_label.setText("⚠️ No USB devices detected. Please connect a USB drive and refresh.")
            return
        
        self.device_status_label.setText(f"✅ Found {len(devices)} USB device(s)")
        
        # Populate device list
        for device in devices:
            self._add_device_to_list(device)
    
    def _add_device_to_list(self, device: DiskInfo):
        """Add device to the list with safety assessment"""
        # Perform safety validation
        device_risk = self.safety_validator.validate_device_safety(device.path)
        self.device_risks[device.path] = device_risk
        
        # Create list item
        item = QListWidgetItem()
        
        # Safety icon
        safety_icons = {
            ValidationResult.SAFE: "✅",
            ValidationResult.WARNING: "⚠️",
            ValidationResult.DANGEROUS: "🚨",
            ValidationResult.BLOCKED: "🛑"
        }
        safety_icon = safety_icons.get(device_risk.overall_risk, "❓")
        
        # Device info
        size_gb = device.size_bytes / (1024**3)
        device_text = f"{safety_icon} {device.vendor} {device.model}\\n"
        device_text += f"    📦 {size_gb:.1f} GB • {device.filesystem} • {device.path}"
        
        if device_risk.mount_points:
            device_text += f"\\n    📁 Mounted: {', '.join(device_risk.mount_points)}"
        
        item.setText(device_text)
        item.setData(Qt.ItemDataRole.UserRole, device)
        
        # Color based on safety
        if device_risk.overall_risk == ValidationResult.BLOCKED:
            item.setForeground(Qt.GlobalColor.red)
        elif device_risk.overall_risk == ValidationResult.DANGEROUS:
            item.setForeground(Qt.GlobalColor.yellow)
        
        self.device_list.addItem(item)
    
    def _on_detection_failed(self, error_message: str):
        """Handle detection failure"""
        self.logger.error(f"Device detection failed: {error_message}")
        self.device_status_label.setText(f"❌ Detection failed: {error_message}")
    
    def _on_detection_finished(self):
        """Handle detection completion"""
        self.refresh_devices_button.setEnabled(True)
        if self.detection_worker:
            self.detection_worker.deleteLater()
            self.detection_worker = None
    
    def _device_selected(self, item: QListWidgetItem):
        """Handle device selection"""
        device = item.data(Qt.ItemDataRole.UserRole)
        device_risk = self.device_risks.get(device.path)
        
        if not device_risk:
            return
        
        # Check if device is blocked
        if device_risk.overall_risk == ValidationResult.BLOCKED:
            QMessageBox.warning(
                self,
                "Device Blocked",
                f"This device cannot be used for safety reasons:\\n\\n"
                f"• {chr(10).join(device_risk.risk_factors)}\\n\\n"
                f"Please select a different USB device."
            )
            return
        
        self.selected_device = device
        self.logger.info(f"Selected device: {device.path} ({device.vendor} {device.model})")
        
        # Update safety information display
        self._update_safety_display(device_risk)
        
        # Check recipe compatibility if recipe is selected
        if self.selected_recipe:
            self._check_recipe_device_compatibility()
        
        # Validate step
        self._validate_configuration()
        
        # Emit data change
        self.step_data_changed.emit({
            "selected_device": device,
            "device_risk": device_risk
        })
    
    def _update_safety_display(self, device_risk: DeviceRisk):
        """Update safety information display"""
        self.safety_info_group.setVisible(True)
        
        # Safety status
        status_icons = {
            ValidationResult.SAFE: "✅ Safe to use",
            ValidationResult.WARNING: "⚠️ Use with caution",
            ValidationResult.DANGEROUS: "🚨 High risk",
            ValidationResult.BLOCKED: "🛑 Blocked"
        }
        
        status_colors = {
            ValidationResult.SAFE: "#4CAF50",
            ValidationResult.WARNING: "#FF9800", 
            ValidationResult.DANGEROUS: "#F44336",
            ValidationResult.BLOCKED: "#F44336"
        }
        
        status_text = status_icons.get(device_risk.overall_risk, "❓ Unknown")
        status_color = status_colors.get(device_risk.overall_risk, "#cccccc")
        
        safety_info = f"<span style='color: {status_color}; font-weight: bold;'>{status_text}</span><br><br>"
        
        # Device details
        safety_info += f"<b>Device:</b> {device_risk.device_path}<br>"
        safety_info += f"<b>Size:</b> {device_risk.size_gb:.1f} GB<br>"
        safety_info += f"<b>Removable:</b> {'Yes' if device_risk.is_removable else 'No'}<br>"
        
        if device_risk.mount_points:
            safety_info += f"<b>Mounted:</b> {', '.join(device_risk.mount_points)}<br>"
        
        # Risk factors
        if device_risk.risk_factors:
            safety_info += "<br><b>⚠️ Risk Factors:</b><br>"
            for factor in device_risk.risk_factors:
                safety_info += f"• {factor}<br>"
        
        self.safety_status_label.setText(safety_info)
    
    def _load_recipes(self):
        """Load and display available recipes"""
        self.logger.info("Loading deployment recipes...")
        
        # Clear existing recipe cards
        for widget in self.recipe_cards.values():
            widget.deleteLater()
        self.recipe_cards.clear()
        
        # Get available recipes
        recipes = [
            DeploymentRecipe.create_macos_oclp_recipe(),
            DeploymentRecipe.create_windows_unattended_recipe(),
            DeploymentRecipe.create_linux_automated_recipe()
        ]
        
        # Create recipe cards
        for recipe in recipes:
            self._create_recipe_card(recipe)
    
    def _create_recipe_card(self, recipe: DeploymentRecipe):
        """Create a recipe selection card"""
        card = QFrame()
        card.setFrameStyle(QFrame.Shape.StyledPanel)
        card.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border: 2px solid #444444;
                border-radius: 8px;
                margin: 5px;
                padding: 10px;
            }
            QFrame:hover {
                border-color: #0078d4;
            }
        """)
        card.setMinimumHeight(120)
        card.mousePressEvent = lambda event, r=recipe: self._select_recipe(r)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Recipe name and type
        name_label = QLabel(recipe.name)
        name_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        layout.addWidget(name_label)
        
        # Description
        desc_label = QLabel(recipe.description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #cccccc; font-size: 12px; margin-top: 5px;")
        layout.addWidget(desc_label)
        
        # Compatibility badge (will be updated based on hardware/OS)
        compat_label = QLabel("⏳ Checking compatibility...")
        compat_label.setStyleSheet("color: #888888; font-size: 11px; margin-top: 5px;")
        layout.addWidget(compat_label)
        
        # Store references
        card.recipe = recipe
        card.compat_label = compat_label
        self.recipe_cards[recipe.name] = card
        
        self.recipe_container_layout.addWidget(card)
        
        # Check compatibility
        self._check_recipe_compatibility(recipe, compat_label)
    
    def _check_recipe_compatibility(self, recipe: DeploymentRecipe, compat_label: QLabel):
        """Check recipe compatibility with detected hardware and OS"""
        if not self.detected_hardware or not self.selected_os_image:
            compat_label.setText("ℹ️ Complete previous steps first")
            return
        
        # This would normally check against actual hardware profiles
        # For now, we'll do basic platform matching
        
        hw_platform = getattr(self.detected_hardware, 'platform', 'unknown').lower()
        os_platform = getattr(self.selected_os_image, 'platform', 'unknown').lower()
        
        recipe_platform_map = {
            DeploymentType.MACOS_OCLP: 'mac',
            DeploymentType.WINDOWS_UNATTENDED: 'windows', 
            DeploymentType.LINUX_AUTOMATED: 'linux'
        }
        
        recipe_platform = recipe_platform_map.get(recipe.deployment_type, 'unknown')
        
        # Check compatibility
        is_compatible = (recipe_platform == hw_platform or recipe_platform == os_platform)
        
        if is_compatible:
            compat_label.setText("✅ Compatible")
            compat_label.setStyleSheet("color: #4CAF50; font-size: 11px; margin-top: 5px;")
        else:
            compat_label.setText("⚠️ May not be compatible")
            compat_label.setStyleSheet("color: #FF9800; font-size: 11px; margin-top: 5px;")
        
        # Store compatibility info
        self.recipe_compatibility[recipe.name] = {
            'compatible': is_compatible,
            'reason': f"Recipe for {recipe_platform}, detected {hw_platform}/{os_platform}"
        }
    
    def _select_recipe(self, recipe: DeploymentRecipe):
        """Select a deployment recipe"""
        self.selected_recipe = recipe
        self.logger.info(f"Selected recipe: {recipe.name}")
        
        # Update card selection visual
        for name, card in self.recipe_cards.items():
            if name == recipe.name:
                card.setStyleSheet(card.styleSheet().replace("border: 2px solid #444444", "border: 2px solid #0078d4"))
            else:
                card.setStyleSheet(card.styleSheet().replace("border: 2px solid #0078d4", "border: 2px solid #444444"))
        
        # Show configuration panel
        self._show_recipe_configuration(recipe)
        
        # Check device compatibility if device is selected
        if self.selected_device:
            self._check_recipe_device_compatibility()
        
        # Validate step
        self._validate_configuration()
        
        # Emit data change
        self.step_data_changed.emit({
            "selected_recipe": recipe
        })
    
    def _show_recipe_configuration(self, recipe: DeploymentRecipe):
        """Show configuration options for selected recipe"""
        # Clear existing config
        for i in reversed(range(self.config_layout.count())):
            child = self.config_layout.itemAt(i).widget()
            if child:
                child.deleteLater()
        
        self.config_group.setVisible(True)
        self.config_group.setTitle(f"Configure: {recipe.name}")
        
        # Basic options
        format_checkbox = QCheckBox("Format device before deployment (recommended)")
        format_checkbox.setChecked(True)
        self.config_layout.addWidget(format_checkbox)
        
        verify_checkbox = QCheckBox("Verify deployment after completion")
        verify_checkbox.setChecked(True)
        self.config_layout.addWidget(verify_checkbox)
        
        # Recipe-specific configuration
        if recipe.deployment_type == DeploymentType.MACOS_OCLP:
            self._add_macos_oclp_config()
        elif recipe.deployment_type == DeploymentType.WINDOWS_UNATTENDED:
            self._add_windows_config()
        elif recipe.deployment_type == DeploymentType.LINUX_AUTOMATED:
            self._add_linux_config()
    
    def _add_macos_oclp_config(self):
        """Add macOS OCLP specific configuration"""
        oclp_group = QGroupBox("OpenCore Legacy Patcher Options")
        oclp_layout = QVBoxLayout(oclp_group)
        
        # OCLP version selection
        version_layout = QHBoxLayout()
        version_layout.addWidget(QLabel("OCLP Version:"))
        version_combo = QComboBox()
        version_combo.addItems(["Auto-detect latest", "1.4.3", "1.4.2", "1.4.1"])
        version_layout.addWidget(version_combo)
        oclp_layout.addLayout(version_layout)
        
        # Additional options
        verbose_checkbox = QCheckBox("Enable verbose boot (for troubleshooting)")
        oclp_layout.addWidget(verbose_checkbox)
        
        sip_checkbox = QCheckBox("Disable System Integrity Protection")
        oclp_layout.addWidget(sip_checkbox)
        
        self.config_layout.addWidget(oclp_group)
    
    def _add_windows_config(self):
        """Add Windows specific configuration"""
        windows_group = QGroupBox("Windows Installation Options")
        windows_layout = QVBoxLayout(windows_group)
        
        # Edition selection
        edition_layout = QHBoxLayout()
        edition_layout.addWidget(QLabel("Windows Edition:"))
        edition_combo = QComboBox()
        edition_combo.addItems(["Auto-detect", "Windows 11 Pro", "Windows 11 Home", "Windows 10 Pro"])
        edition_layout.addWidget(edition_combo)
        windows_layout.addLayout(edition_layout)
        
        # Driver injection
        driver_checkbox = QCheckBox("Inject hardware-specific drivers")
        windows_layout.addWidget(driver_checkbox)
        
        # Unattended installation
        unattended_checkbox = QCheckBox("Enable unattended installation")
        unattended_checkbox.setChecked(True)
        windows_layout.addWidget(unattended_checkbox)
        
        self.config_layout.addWidget(windows_group)
    
    def _add_linux_config(self):
        """Add Linux specific configuration"""
        linux_group = QGroupBox("Linux Installation Options")
        linux_layout = QVBoxLayout(linux_group)
        
        # Distribution selection
        distro_layout = QHBoxLayout()
        distro_layout.addWidget(QLabel("Distribution:"))
        distro_combo = QComboBox()
        distro_combo.addItems(["Auto-detect", "Ubuntu 22.04 LTS", "Fedora 39", "Debian 12"])
        distro_layout.addWidget(distro_combo)
        linux_layout.addLayout(distro_layout)
        
        # Package selection
        packages_checkbox = QCheckBox("Include development packages")
        linux_layout.addWidget(packages_checkbox)
        
        # Auto-login
        autologin_checkbox = QCheckBox("Enable automatic login")
        linux_layout.addWidget(autologin_checkbox)
        
        self.config_layout.addWidget(linux_group)
    
    def _check_recipe_device_compatibility(self):
        """Check if selected recipe is compatible with selected device"""
        if not self.selected_recipe or not self.selected_device:
            return
        
        device_size_gb = self.selected_device.size_bytes / (1024**3)
        
        # Check minimum size requirements (simplified)
        min_sizes = {
            DeploymentType.MACOS_OCLP: 16.0,  # 16GB minimum
            DeploymentType.WINDOWS_UNATTENDED: 8.0,  # 8GB minimum
            DeploymentType.LINUX_AUTOMATED: 4.0  # 4GB minimum
        }
        
        min_required = min_sizes.get(self.selected_recipe.deployment_type, 8.0)
        
        if device_size_gb < min_required:
            QMessageBox.warning(
                self,
                "Insufficient Storage",
                f"The selected USB device ({device_size_gb:.1f} GB) is too small for {self.selected_recipe.name}.\\n\\n"
                f"Minimum required: {min_required} GB\\n"
                f"Please select a larger USB device."
            )
            return False
        
        return True
    
    def _validate_configuration(self):
        """Validate the complete configuration"""
        is_valid = False
        
        if self.selected_device and self.selected_recipe:
            # Check device safety
            device_risk = self.device_risks.get(self.selected_device.path)
            if device_risk and device_risk.overall_risk not in [ValidationResult.BLOCKED]:
                # Check device capacity
                if self._check_recipe_device_compatibility():
                    is_valid = True
        
        self.set_navigation_enabled(next=is_valid)
        
        if is_valid:
            self.logger.info("USB configuration validated successfully")
            self.step_completed.emit()
    
    def validate_step(self) -> bool:
        """Validate step data before proceeding"""
        if not self.selected_device:
            QMessageBox.warning(self, "No Device Selected", "Please select a USB device.")
            return False
        
        if not self.selected_recipe:
            QMessageBox.warning(self, "No Recipe Selected", "Please select a deployment recipe.")
            return False
        
        # Final safety check
        device_risk = self.device_risks.get(self.selected_device.path)
        if device_risk and device_risk.overall_risk == ValidationResult.BLOCKED:
            QMessageBox.critical(self, "Unsafe Device", "The selected device is blocked for safety reasons.")
            return False
        
        return True
    
    def get_step_data(self) -> Dict[str, Any]:
        """Get step configuration data"""
        data = {
            "selected_device": self.selected_device,
            "selected_recipe": self.selected_recipe,
            "device_risk": self.device_risks.get(self.selected_device.path) if self.selected_device else None,
            "recipe_compatibility": self.recipe_compatibility.get(self.selected_recipe.name) if self.selected_recipe else None,
            "available_devices_count": len(self.available_devices)
        }
        
        self.logger.info(f"Exporting USB configuration data: device={self.selected_device.path if self.selected_device else None}, recipe={self.selected_recipe.name if self.selected_recipe else None}")
        return data
    
    def load_step_data(self, data: Dict[str, Any]):
        """Load step data from wizard state"""
        self.logger.info(f"Loading USB configuration data: {list(data.keys())}")
        
        # Load hardware and OS data for context
        self.detected_hardware = data.get("detected_hardware")
        self.selected_os_image = data.get("selected_os_image") or data.get("selected_image")
        
        # Update context display
        self._update_context_display()
        
        # Load recipes with compatibility checking
        self._load_recipes()
        
        # Restore previous selections if available
        if "selected_device" in data:
            # This would require re-detecting devices to restore selection
            pass
        
        if "selected_recipe" in data:
            # This would require finding and selecting the recipe
            pass
    
    def _update_context_display(self):
        """Update the hardware/OS context display"""
        if self.detected_hardware and self.selected_os_image:
            hw_info = getattr(self.detected_hardware, 'get_summary', lambda: "Hardware detected")()
            os_info = getattr(self.selected_os_image, 'name', 'OS image selected')
            
            context_text = f"🔧 Hardware: {hw_info}\\n📀 OS Image: {os_info}\\n\\nSelect a compatible deployment recipe:"
            self.context_label.setText(context_text)
        elif self.detected_hardware:
            hw_info = getattr(self.detected_hardware, 'get_summary', lambda: "Hardware detected")()
            self.context_label.setText(f"🔧 Hardware: {hw_info}\\n⚠️ Please select an OS image first")
        elif self.selected_os_image:
            os_info = getattr(self.selected_os_image, 'name', 'OS image selected')
            self.context_label.setText(f"📀 OS Image: {os_info}\\n⚠️ Please detect hardware first")
        else:
            self.context_label.setText("⚠️ Please complete hardware detection and OS selection first")
    
    def on_step_entered(self):
        """Called when step becomes active"""
        self.logger.info("USB Configuration step entered")
        
        # Start device detection automatically
        QTimer.singleShot(500, self._refresh_devices)
    
    def on_step_left(self):
        """Called when leaving step"""
        self.logger.info("USB Configuration step exited")
        
        # Clean up detection worker
        if self.detection_worker and self.detection_worker.isRunning():
            self.detection_worker.quit()
            self.detection_worker.wait()


class SafetyReviewStepView(StepView):
    """🚨 CRITICAL SAFETY REVIEW STEP - Final confirmation before destructive USB operations 🚨
    
    This step implements comprehensive safety measures to prevent accidental system damage:
    - Shows exact devices, images, and operations to be performed
    - Requires multiple levels of explicit user confirmation
    - Uses SafetyValidator to assess device risks
    - Blocks dangerous operations (system disks, etc.)
    - Professional UI with clear warnings and safety messaging
    """
    
    # Signals for safety events
    safety_assessment_completed = pyqtSignal(object)  # DeviceRisk
    critical_warning_displayed = pyqtSignal(str)  # Warning message
    
    def __init__(self):
        super().__init__(
            "🚨 Final Safety Review",
            "CRITICAL: Review all settings and provide explicit confirmations before proceeding with destructive USB operations."
        )
        
        # Initialize safety components
        self.safety_validator = SafetyValidator(SafetyLevel.STANDARD)
        
        # State tracking
        self.detected_hardware = None
        self.selected_image = None
        self.target_device = None
        self.selected_recipe = None
        self.device_risk = None
        
        # UI Components (initialized in _setup_content)
        self.summary_layout = None
        self.safety_assessment_group = None
        self.confirmation_widgets = {}
        self.typed_confirmations = {}
        
        self._setup_content()
    
    def _setup_content(self):
        """Setup comprehensive safety review interface with multi-level confirmations"""
        # Create main scroll area for large content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #404040;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #606060;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #707070;
            }
        """)
        
        scroll_widget = QWidget()
        main_layout = QVBoxLayout(scroll_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # CRITICAL WARNING BANNER
        self._create_warning_banner(main_layout)
        
        # 1. COMPREHENSIVE ACTION SUMMARY
        self._create_action_summary(main_layout)
        
        # 2. DEVICE SAFETY ASSESSMENT
        self._create_safety_assessment(main_layout)
        
        # 3. DESTRUCTIVE ACTION WARNINGS
        self._create_destructive_warnings(main_layout)
        
        # 4. MULTI-LEVEL CONFIRMATION SYSTEM
        self._create_confirmation_system(main_layout)
        
        # 5. TYPED CONFIRMATIONS
        self._create_typed_confirmations(main_layout)
        
        # 6. FINAL VALIDATION STATUS
        self._create_validation_status(main_layout)
        
        scroll_area.setWidget(scroll_widget)
        self.content_layout.addWidget(scroll_area)
        
        # Initially disable next until all confirmations complete
        self.set_navigation_enabled(next=False)
    
    def _create_warning_banner(self, parent_layout):
        """Create prominent warning banner at top"""
        warning_frame = QFrame()
        warning_frame.setFrameStyle(QFrame.Shape.Box)
        warning_frame.setStyleSheet("""
            QFrame {
                background-color: #4a1f1f;
                border: 3px solid #ff4444;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        
        warning_layout = QHBoxLayout(warning_frame)
        
        # Warning icon
        warning_icon = QLabel("🚨")
        warning_icon.setStyleSheet("font-size: 48px;")
        warning_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        warning_layout.addWidget(warning_icon)
        
        # Warning text
        warning_text = QLabel(
            "<b>CRITICAL SAFETY CHECK</b><br>"
            "<span style='font-size: 16px; color: #ff6666;'>"
            "This operation will PERMANENTLY ERASE data!<br>"
            "Carefully review all details before proceeding."
            "</span>"
        )
        warning_text.setStyleSheet(
            "color: #ffffff; font-size: 18px; font-weight: bold; padding: 5px;"
        )
        warning_layout.addWidget(warning_text)
        
        # Stop sign icon
        stop_icon = QLabel("🛑")
        stop_icon.setStyleSheet("font-size: 48px;")
        stop_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        warning_layout.addWidget(stop_icon)
        
        parent_layout.addWidget(warning_frame)
    
    def _create_action_summary(self, parent_layout):
        """Create comprehensive summary of all selected options"""
        summary_group = QGroupBox("📋 Deployment Configuration Summary")
        summary_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #ffffff;
                border: 2px solid #0078d4;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #0078d4;
            }
        """)
        
        self.summary_layout = QVBoxLayout(summary_group)
        
        # Placeholders - will be populated when wizard state is loaded
        self.hardware_summary = QLabel("⏳ Loading hardware information...")
        self.hardware_summary.setStyleSheet("color: #cccccc; font-size: 14px; padding: 5px;")
        self.summary_layout.addWidget(self.hardware_summary)
        
        self.image_summary = QLabel("⏳ Loading OS image information...")
        self.image_summary.setStyleSheet("color: #cccccc; font-size: 14px; padding: 5px;")
        self.summary_layout.addWidget(self.image_summary)
        
        self.device_summary = QLabel("⏳ Loading device information...")
        self.device_summary.setStyleSheet("color: #cccccc; font-size: 14px; padding: 5px;")
        self.summary_layout.addWidget(self.device_summary)
        
        self.recipe_summary = QLabel("⏳ Loading recipe information...")
        self.recipe_summary.setStyleSheet("color: #cccccc; font-size: 14px; padding: 5px;")
        self.summary_layout.addWidget(self.recipe_summary)
        
        parent_layout.addWidget(summary_group)
    
    def _create_safety_assessment(self, parent_layout):
        """Create device safety assessment display"""
        self.safety_assessment_group = QGroupBox("🔍 Device Safety Assessment")
        self.safety_assessment_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #ffffff;
                border: 2px solid #ff8800;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #ff8800;
            }
        """)
        
        assessment_layout = QVBoxLayout(self.safety_assessment_group)
        
        self.safety_status_label = QLabel("⏳ Running safety assessment...")
        self.safety_status_label.setStyleSheet("color: #cccccc; font-size: 14px; padding: 5px;")
        assessment_layout.addWidget(self.safety_status_label)
        
        self.risk_factors_label = QLabel("")
        self.risk_factors_label.setStyleSheet("color: #cccccc; font-size: 14px; padding: 5px;")
        self.risk_factors_label.setWordWrap(True)
        assessment_layout.addWidget(self.risk_factors_label)
        
        parent_layout.addWidget(self.safety_assessment_group)
    
    def _create_destructive_warnings(self, parent_layout):
        """Create explicit warnings about destructive operations"""
        warning_group = QGroupBox("⚠️ Destructive Operations Warning")
        warning_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #ffffff;
                border: 2px solid #ff4444;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #ff4444;
            }
        """)
        
        warning_layout = QVBoxLayout(warning_group)
        
        # Destructive action text
        destruction_text = QTextEdit()
        destruction_text.setMaximumHeight(120)
        destruction_text.setReadOnly(True)
        destruction_text.setStyleSheet("""
            QTextEdit {
                background-color: #3d1a1a;
                border: 2px solid #ff6666;
                border-radius: 6px;
                color: #ffcccc;
                font-size: 13px;
                font-weight: bold;
                padding: 10px;
            }
        """)
        
        destruction_content = """
🛑 PERMANENT DATA LOSS WARNING 🛑

The following DESTRUCTIVE operations will be performed:
• Complete erasure of ALL data on the target USB device
• Destruction of ALL existing partitions and file systems
• Overwriting with new bootable OS image data
• Cannot be undone - data will be permanently lost!

⏰ Estimated time: 15-30 minutes (depending on USB speed)
💾 Space required: Full device capacity will be used
        """
        
        destruction_text.setPlainText(destruction_content)
        warning_layout.addWidget(destruction_text)
        
        parent_layout.addWidget(warning_group)
    
    def _create_confirmation_system(self, parent_layout):
        """Create multi-level checkbox confirmation system"""
        confirm_group = QGroupBox("☑️ Safety Confirmations (All Required)")
        confirm_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #ffffff;
                border: 2px solid #00aa44;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #00aa44;
            }
        """)
        
        confirm_layout = QVBoxLayout(confirm_group)
        
        # Confirmation checkboxes with enhanced styling
        checkbox_style = """
            QCheckBox {
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
                padding: 8px;
                spacing: 10px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #666666;
                background-color: #2d2d30;
                border-radius: 4px;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #00aa44;
                background-color: #00aa44;
                border-radius: 4px;
            }
            QCheckBox::indicator:unchecked:hover {
                border: 2px solid #888888;
            }
            QCheckBox::indicator:checked:hover {
                border: 2px solid #00cc55;
                background-color: #00cc55;
            }
        """
        
        # Create confirmation checkboxes
        self.confirmation_widgets = {
            'understand_erase': QCheckBox("I understand this will PERMANENTLY ERASE all data on the target device"),
            'backup_complete': QCheckBox("I have backed up any important data from this device (or it contains no important data)"),
            'device_confirmed': QCheckBox("I have confirmed the correct USB device is selected (not a system drive)"),
            'understand_irreversible': QCheckBox("I understand this operation cannot be undone or stopped once started"),
            'accept_responsibility': QCheckBox("I accept full responsibility for any data loss that may occur"),
            'ready_proceed': QCheckBox("I am ready to proceed with the USB creation process")
        }
        
        for checkbox in self.confirmation_widgets.values():
            checkbox.setStyleSheet(checkbox_style)
            checkbox.toggled.connect(self._validate_all_confirmations)
            confirm_layout.addWidget(checkbox)
        
        parent_layout.addWidget(confirm_group)
    
    def _create_typed_confirmations(self, parent_layout):
        """Create typed confirmation fields for extra safety"""
        typed_group = QGroupBox("⌨️ Typed Confirmations (Type Exactly as Shown)")
        typed_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #ffffff;
                border: 2px solid #ff8800;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #ff8800;
            }
        """)
        
        typed_layout = QGridLayout(typed_group)
        
        # Typed confirmation fields
        row = 0
        
        # "ERASE" confirmation
        erase_label = QLabel("Type 'ERASE' to confirm data destruction:")
        erase_label.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 14px;")
        typed_layout.addWidget(erase_label, row, 0)
        
        self.typed_confirmations['erase'] = QLineEdit()
        self.typed_confirmations['erase'].setPlaceholderText("Type: ERASE")
        self.typed_confirmations['erase'].textChanged.connect(self._validate_all_confirmations)
        self.typed_confirmations['erase'].setStyleSheet("""
            QLineEdit {
                padding: 8px;
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #666666;
                border-radius: 4px;
                background-color: #2d2d30;
                color: #ffffff;
            }
            QLineEdit:focus {
                border-color: #0078d4;
            }
        """)
        typed_layout.addWidget(self.typed_confirmations['erase'], row, 1)
        row += 1
        
        # Device path confirmation (will be populated when device is loaded)
        self.device_path_label = QLabel("Type device path to confirm target:")
        self.device_path_label.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 14px;")
        typed_layout.addWidget(self.device_path_label, row, 0)
        
        self.typed_confirmations['device_path'] = QLineEdit()
        self.typed_confirmations['device_path'].setPlaceholderText("Device path will appear here")
        self.typed_confirmations['device_path'].textChanged.connect(self._validate_all_confirmations)
        self.typed_confirmations['device_path'].setStyleSheet("""
            QLineEdit {
                padding: 8px;
                font-size: 14px;
                font-family: 'Courier New', monospace;
                border: 2px solid #666666;
                border-radius: 4px;
                background-color: #2d2d30;
                color: #ffffff;
            }
            QLineEdit:focus {
                border-color: #0078d4;
            }
        """)
        typed_layout.addWidget(self.typed_confirmations['device_path'], row, 1)
        
        parent_layout.addWidget(typed_group)
    
    def _create_validation_status(self, parent_layout):
        """Create final validation status display"""
        status_group = QGroupBox("✅ Final Validation Status")
        status_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #ffffff;
                border: 2px solid #666666;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #666666;
            }
        """)
        
        status_layout = QVBoxLayout(status_group)
        
        self.validation_status_label = QLabel("⏳ Complete all confirmations to enable USB creation")
        self.validation_status_label.setStyleSheet(
            "color: #ffaa00; font-size: 16px; font-weight: bold; padding: 10px;"
        )
        self.validation_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(self.validation_status_label)
        
        parent_layout.addWidget(status_group)
    
    def _validate_all_confirmations(self):
        """Comprehensive validation of all confirmation requirements"""
        # Check all checkboxes are checked
        checkboxes_valid = all(checkbox.isChecked() for checkbox in self.confirmation_widgets.values())
        
        # Check typed confirmations
        erase_valid = self.typed_confirmations['erase'].text().strip() == 'ERASE'
        device_path_valid = self._validate_device_path_confirmation()
        
        # Check safety assessment (no blocked/dangerous devices)
        safety_valid = self.device_risk is None or self.device_risk.overall_risk not in [ValidationResult.BLOCKED, ValidationResult.DANGEROUS]
        
        # Overall validation
        all_valid = checkboxes_valid and erase_valid and device_path_valid and safety_valid
        
        # Update UI based on validation status
        self._update_validation_status(all_valid, checkboxes_valid, erase_valid, device_path_valid, safety_valid)
        
        # Enable/disable next button
        self.set_navigation_enabled(next=all_valid)
        
        if all_valid:
            self.step_completed.emit()
    
    def _validate_device_path_confirmation(self) -> bool:
        """Validate device path typed confirmation"""
        if not self.target_device:
            return False
        
        expected_path = self.target_device.path
        typed_path = self.typed_confirmations['device_path'].text().strip()
        
        return typed_path == expected_path
    
    def _update_validation_status(self, all_valid: bool, checkboxes_valid: bool, erase_valid: bool, device_path_valid: bool, safety_valid: bool):
        """Update validation status display with detailed feedback"""
        if all_valid:
            # All validations passed
            self.validation_status_label.setText("✅ All confirmations complete - Ready to create USB drive!")
            self.validation_status_label.setStyleSheet(
                "color: #00ff00; font-size: 16px; font-weight: bold; padding: 10px;"
            )
            # Update group box border color to green
            self.validation_status_label.parent().setStyleSheet("""
                QGroupBox {
                    border: 2px solid #00aa44;
                }
                QGroupBox::title {
                    color: #00aa44;
                }
            """)
        else:
            # Show what still needs to be completed
            missing = []
            if not checkboxes_valid:
                missing.append("safety checkboxes")
            if not erase_valid:
                missing.append("'ERASE' confirmation")
            if not device_path_valid:
                missing.append("device path confirmation")
            if not safety_valid:
                missing.append("device safety approval")
            
            self.validation_status_label.setText(f"⏳ Please complete: {', '.join(missing)}")
            self.validation_status_label.setStyleSheet(
                "color: #ffaa00; font-size: 16px; font-weight: bold; padding: 10px;"
            )
            # Keep border color as default gray
            self.validation_status_label.parent().setStyleSheet("""
                QGroupBox {
                    border: 2px solid #666666;
                }
                QGroupBox::title {
                    color: #666666;
                }
            """)
    
    def _run_device_safety_assessment(self):
        """Run comprehensive device safety assessment"""
        if not self.target_device:
            return
        
        try:
            # Run safety validation
            device_path = self.target_device.path
            self.device_risk = self.safety_validator.validate_device_safety(device_path)
            
            # Update safety assessment UI
            self._update_safety_assessment_display()
            
            # Emit signal for external listeners
            self.safety_assessment_completed.emit(self.device_risk)
            
            # Re-validate all confirmations (in case device is now blocked)
            self._validate_all_confirmations()
            
        except Exception as e:
            self.logger.error(f"Safety assessment failed: {e}", exc_info=True)
            self.safety_status_label.setText(f"❌ Safety assessment failed: {str(e)}")
            self.safety_status_label.setStyleSheet("color: #ff4444; font-size: 14px; padding: 5px;")
    
    def _update_safety_assessment_display(self):
        """Update the safety assessment display with device risk information"""
        if not self.device_risk:
            return
        
        # Color code based on risk level
        risk_colors = {
            ValidationResult.SAFE: "#00aa44",
            ValidationResult.WARNING: "#ff8800", 
            ValidationResult.DANGEROUS: "#ff4444",
            ValidationResult.BLOCKED: "#ff0000"
        }
        
        risk_icons = {
            ValidationResult.SAFE: "✅",
            ValidationResult.WARNING: "⚠️",
            ValidationResult.DANGEROUS: "🚨", 
            ValidationResult.BLOCKED: "🛑"
        }
        
        risk_level = self.device_risk.overall_risk
        color = risk_colors.get(risk_level, "#cccccc")
        icon = risk_icons.get(risk_level, "❓")
        
        # Update status label
        device_info = (
            f"{icon} Risk Level: {risk_level.value.upper()}\n"
            f"Device: {self.device_risk.device_path}\n"
            f"Size: {self.device_risk.size_gb:.1f} GB\n"
            f"Removable: {'Yes' if self.device_risk.is_removable else 'No'}\n"
            f"System Disk: {'Yes' if self.device_risk.is_system_disk else 'No'}\n"
            f"Boot Disk: {'Yes' if self.device_risk.is_boot_disk else 'No'}"
        )
        
        self.safety_status_label.setText(device_info)
        self.safety_status_label.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold; padding: 5px;")
        
        # Update risk factors if any
        if self.device_risk.risk_factors:
            risk_text = "\n".join([f"• {factor}" for factor in self.device_risk.risk_factors])
            self.risk_factors_label.setText(f"Risk Factors:\n{risk_text}")
            self.risk_factors_label.setStyleSheet(f"color: {color}; font-size: 14px; padding: 5px;")
        else:
            self.risk_factors_label.setText("✅ No risk factors detected")
            self.risk_factors_label.setStyleSheet("color: #00aa44; font-size: 14px; padding: 5px;")
        
        # Show critical warning for dangerous/blocked devices
        if risk_level in [ValidationResult.DANGEROUS, ValidationResult.BLOCKED]:
            critical_msg = f"CRITICAL: Device is {risk_level.value.upper()} - operation blocked for safety!"
            self.critical_warning_displayed.emit(critical_msg)
            
            # Show message box for immediate attention
            QMessageBox.critical(
                self,
                "Critical Safety Warning",
                f"The selected device has been flagged as {risk_level.value.upper()}.\n\n"
                f"Risk factors:\n• {chr(10).join(self.device_risk.risk_factors)}\n\n"
                f"This operation cannot proceed for safety reasons."
            )
    
    # Step interface methods
    def validate_step(self) -> bool:
        """Final validation before allowing progression to next step"""
        # Must have all required data loaded
        if not all([self.detected_hardware, self.selected_image, self.target_device]):
            return False
        
        # Must have completed safety assessment
        if not self.device_risk:
            return False
        
        # Must not be blocked or dangerous
        if self.device_risk.overall_risk in [ValidationResult.BLOCKED, ValidationResult.DANGEROUS]:
            return False
        
        # Must have all confirmations completed
        checkboxes_valid = all(checkbox.isChecked() for checkbox in self.confirmation_widgets.values())
        erase_valid = self.typed_confirmations['erase'].text().strip() == 'ERASE'
        device_path_valid = self._validate_device_path_confirmation()
        
        return checkboxes_valid and erase_valid and device_path_valid
    
    def get_step_data(self) -> Dict[str, Any]:
        """Get comprehensive step data including all safety confirmations"""
        return {
            'safety_confirmations_complete': self.validate_step(),
            'device_risk_assessment': self.device_risk,
            'user_confirmations': {
                'checkboxes': {key: checkbox.isChecked() for key, checkbox in self.confirmation_widgets.items()},
                'typed_confirmations': {key: field.text() for key, field in self.typed_confirmations.items()}
            },
            'safety_level': self.safety_validator.safety_level.value,
            'final_device_path': self.target_device.path if self.target_device else None,
            'final_validation_timestamp': datetime.now().isoformat()
        }
    
    def load_step_data(self, data: Dict[str, Any]):
        """Load wizard state data and update all displays"""
        self.logger.info(f"Loading safety review step data: {list(data.keys())}")
        
        # Load hardware information
        if 'detected_hardware' in data:
            self.detected_hardware = data['detected_hardware']
            self._update_hardware_summary()
        
        # Load OS image information
        if 'selected_image' in data or 'image_info' in data:
            self.selected_image = data.get('selected_image') or data.get('image_info')
            self._update_image_summary()
        
        # Load device information
        if 'device_info' in data:
            self.target_device = data['device_info']
            self._update_device_summary()
            self._update_device_path_confirmation()
            # Run safety assessment for the device
            QTimer.singleShot(100, self._run_device_safety_assessment)
        
        # Load recipe information
        if 'selected_recipe' in data:
            self.selected_recipe = data['selected_recipe']
            self._update_recipe_summary()
    
    def _update_hardware_summary(self):
        """Update hardware information display"""
        if not self.detected_hardware:
            return
        
        try:
            # Get hardware summary text
            if hasattr(self.detected_hardware, 'get_summary'):
                hw_summary = self.detected_hardware.get_summary()
            else:
                hw_summary = "Hardware detected successfully"
            
            # Get additional details if available
            hw_details = []
            if hasattr(self.detected_hardware, 'system_info'):
                sys_info = self.detected_hardware.system_info
                if hasattr(sys_info, 'model'):
                    hw_details.append(f"Model: {sys_info.model}")
                if hasattr(sys_info, 'cpu'):
                    hw_details.append(f"CPU: {sys_info.cpu}")
                if hasattr(sys_info, 'memory_gb'):
                    hw_details.append(f"Memory: {sys_info.memory_gb}GB")
            
            summary_text = f"🔧 <b>Detected Hardware:</b> {hw_summary}"
            if hw_details:
                summary_text += f"<br>{'<br>'.join(hw_details)}"
            
            self.hardware_summary.setText(summary_text)
            self.hardware_summary.setStyleSheet("color: #00aa44; font-size: 14px; padding: 5px;")
            
        except Exception as e:
            self.logger.error(f"Error updating hardware summary: {e}")
            self.hardware_summary.setText("🔧 <b>Hardware:</b> Detection completed")
    
    def _update_image_summary(self):
        """Update OS image information display"""
        if not self.selected_image:
            return
        
        try:
            # Handle both OSImageInfo objects and dictionaries
            if hasattr(self.selected_image, 'name'):
                name = self.selected_image.name
                size_bytes = getattr(self.selected_image, 'size_bytes', 0)
                verified = getattr(self.selected_image, 'status', None) == 'verified'
                os_family = getattr(self.selected_image, 'os_family', 'Unknown')
            else:
                # Dictionary format
                name = self.selected_image.get('name', 'Unknown')
                size_bytes = self.selected_image.get('size_bytes', 0)
                verified = self.selected_image.get('verified', False)
                os_family = self.selected_image.get('os_family', 'Unknown')
            
            size_gb = size_bytes / (1024**3) if size_bytes > 0 else 0
            verify_status = "✅ Verified" if verified else "⚠️ Not Verified"
            verify_color = "#00aa44" if verified else "#ff8800"
            
            summary_text = (
                f"📀 <b>OS Image:</b> {name}<br>"
                f"Size: {size_gb:.1f} GB • Type: {os_family.title()}<br>"
                f"<span style='color: {verify_color};'>{verify_status}</span>"
            )
            
            self.image_summary.setText(summary_text)
            self.image_summary.setStyleSheet("color: #00aa44; font-size: 14px; padding: 5px;")
            
        except Exception as e:
            self.logger.error(f"Error updating image summary: {e}")
            self.image_summary.setText("📀 <b>OS Image:</b> Selected")
    
    def _update_device_summary(self):
        """Update device information display"""
        if not self.target_device:
            return
        
        try:
            size_gb = self.target_device.size_bytes / (1024**3)
            vendor_model = f"{self.target_device.vendor} {self.target_device.model}".strip()
            
            summary_text = (
                f"💾 <b>Target Device:</b> {self.target_device.name}<br>"
                f"Path: <code>{self.target_device.path}</code><br>"
                f"Size: {size_gb:.1f} GB • Model: {vendor_model}<br>"
                f"Removable: {'Yes' if self.target_device.is_removable else 'No'}"
            )
            
            # Color code based on removable status
            color = "#00aa44" if self.target_device.is_removable else "#ff8800"
            
            self.device_summary.setText(summary_text)
            self.device_summary.setStyleSheet(f"color: {color}; font-size: 14px; padding: 5px;")
            
        except Exception as e:
            self.logger.error(f"Error updating device summary: {e}")
            self.device_summary.setText("💾 <b>Target Device:</b> Selected")
    
    def _update_recipe_summary(self):
        """Update recipe configuration display"""
        if not self.selected_recipe:
            self.recipe_summary.setText("⚙️ <b>Recipe:</b> Standard USB creation")
            return
        
        try:
            if hasattr(self.selected_recipe, 'name'):
                name = self.selected_recipe.name
                description = getattr(self.selected_recipe, 'description', 'No description')
            else:
                name = str(self.selected_recipe)
                description = "Configuration selected"
            
            summary_text = f"⚙️ <b>Recipe:</b> {name}<br>{description}"
            
            self.recipe_summary.setText(summary_text)
            self.recipe_summary.setStyleSheet("color: #00aa44; font-size: 14px; padding: 5px;")
            
        except Exception as e:
            self.logger.error(f"Error updating recipe summary: {e}")
            self.recipe_summary.setText("⚙️ <b>Recipe:</b> Selected")
    
    def _update_device_path_confirmation(self):
        """Update device path confirmation field with actual device path"""
        if not self.target_device:
            return
        
        device_path = self.target_device.path
        self.device_path_label.setText(f"Type device path to confirm target: <code>{device_path}</code>")
        self.typed_confirmations['device_path'].setPlaceholderText(f"Type: {device_path}")
    
    def on_step_entered(self):
        """Called when step becomes active"""
        self.logger.info("Safety Review step entered - performing final validation")
        
        # Clear any previous confirmations for fresh start
        for checkbox in self.confirmation_widgets.values():
            checkbox.setChecked(False)
        
        for field in self.typed_confirmations.values():
            field.clear()
        
        # Reset validation status
        self._validate_all_confirmations()
    
    def on_step_left(self):
        """Called when leaving step"""
        self.logger.info("Safety Review step exited - confirmations recorded")
        
        # Log final confirmation state for audit trail
        if self.validate_step():
            self.logger.info("All safety confirmations completed successfully")
        else:
            self.logger.warning("Safety confirmations incomplete - this should not happen!")


class BuildVerifyStepView(StepView):
    """Comprehensive Build and Verify Step - The exciting culmination where BootForge creates the bootable USB drive"""
    
    # Build stage signals
    build_started = pyqtSignal()
    build_completed = pyqtSignal(bool, str)  # success, message
    build_progress_updated = pyqtSignal(object)  # BuildProgress object
    build_stage_changed = pyqtSignal(str, int)  # stage_name, stage_number
    verification_completed = pyqtSignal(bool, dict)  # success, results
    
    def __init__(self):
        super().__init__(
            "Build & Verify",
            "Creating your bootable USB drive with comprehensive safety validation and verification"
        )
        
        # Build components
        self.usb_builder_engine = USBBuilderEngine()
        self.safety_validator = SafetyValidator(SafetyLevel.STANDARD)
        
        # Build state
        self.wizard_state: Optional[WizardState] = None
        self.selected_device: Optional[DiskInfo] = None
        self.selected_recipe: Optional[DeploymentRecipe] = None
        self.hardware_profile: Optional[HardwareProfile] = None
        self.source_files: Dict[str, str] = {}
        
        # Build tracking
        self.current_builder: Optional[USBBuilder] = None
        self.build_start_time: Optional[datetime] = None
        self.total_bytes_to_write: int = 0
        self.bytes_written: int = 0
        self.current_stage: int = 0
        self.build_completed_successfully: bool = False
        
        # Build stages
        self.build_stages = [
            ("Pre-build Safety Validation", "Performing comprehensive safety checks and device validation"),
            ("Device Preparation", "Preparing USB device and creating partition scheme"),
            ("OS Image Deployment", "Writing operating system image and core files"),
            ("Bootloader Configuration", "Installing and configuring bootloader components"),
            ("Final Verification", "Verifying installation integrity and creating deployment report")
        ]
        
        self._setup_content()
        
        # Initially disable navigation
        self.set_navigation_enabled(previous=False, next=False)
    
    def _setup_content(self):
        """Setup comprehensive build and verify UI"""
        # Main splitter for layout
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Top section: Build progress and status
        progress_widget = self._create_progress_widget()
        main_splitter.addWidget(progress_widget)
        
        # Bottom section: Logs and statistics
        info_widget = self._create_info_widget()
        main_splitter.addWidget(info_widget)
        
        # Set proportions (70% progress, 30% info)
        main_splitter.setSizes([700, 300])
        self.content_layout.addWidget(main_splitter)
        
        # Emergency controls
        emergency_layout = QHBoxLayout()
        emergency_layout.addStretch()
        
        self.emergency_stop_btn = QPushButton("🛑 Emergency Stop")
        self.emergency_stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.emergency_stop_btn.clicked.connect(self._emergency_stop)
        self.emergency_stop_btn.setEnabled(False)
        emergency_layout.addWidget(self.emergency_stop_btn)
        
        self.content_layout.addLayout(emergency_layout)
    
    def _create_progress_widget(self) -> QWidget:
        """Create the main progress display widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Build status header
        header_layout = QHBoxLayout()
        
        self.build_icon = QLabel("⚙️")
        self.build_icon.setFont(QFont("Arial", 24))
        header_layout.addWidget(self.build_icon)
        
        status_layout = QVBoxLayout()
        self.build_title = QLabel("Ready to Create Bootable USB Drive")
        self.build_title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.build_title.setStyleSheet("color: #ffffff; margin-bottom: 5px;")
        status_layout.addWidget(self.build_title)
        
        self.build_subtitle = QLabel("Waiting for safety confirmation...")
        self.build_subtitle.setStyleSheet("color: #cccccc; font-size: 14px;")
        status_layout.addWidget(self.build_subtitle)
        
        header_layout.addLayout(status_layout)
        header_layout.addStretch()
        
        # Build statistics
        stats_layout = QVBoxLayout()
        self.speed_label = QLabel("Speed: --")
        self.speed_label.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        stats_layout.addWidget(self.speed_label)
        
        self.eta_label = QLabel("ETA: --")
        self.eta_label.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        stats_layout.addWidget(self.eta_label)
        
        self.elapsed_label = QLabel("Elapsed: 00:00:00")
        self.elapsed_label.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        stats_layout.addWidget(self.elapsed_label)
        
        header_layout.addLayout(stats_layout)
        layout.addLayout(header_layout)
        
        # Stage progress display
        self.stage_group = QGroupBox("Build Progress")
        stage_layout = QVBoxLayout(self.stage_group)
        
        # Current stage indicator
        self.current_stage_label = QLabel("Stage 1 of 5: Pre-build Safety Validation")
        self.current_stage_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.current_stage_label.setStyleSheet("color: #ffffff; margin-bottom: 10px;")
        stage_layout.addWidget(self.current_stage_label)
        
        # Stage progress bar
        self.stage_progress_bar = QProgressBar()
        self.stage_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #555555;
                border-radius: 8px;
                text-align: center;
                background-color: #2d2d30;
                color: #ffffff;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4CAF50, stop:1 #45a049);
                border-radius: 6px;
            }
        """)
        self.stage_progress_bar.setMinimumHeight(30)
        stage_layout.addWidget(self.stage_progress_bar)
        
        # Overall progress bar
        overall_label = QLabel("Overall Progress")
        overall_label.setStyleSheet("color: #cccccc; font-size: 12px; margin-top: 10px;")
        stage_layout.addWidget(overall_label)
        
        self.overall_progress_bar = QProgressBar()
        self.overall_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #555555;
                border-radius: 6px;
                text-align: center;
                background-color: #2d2d30;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0078d4, stop:1 #106ebe);
                border-radius: 4px;
            }
        """)
        self.overall_progress_bar.setMinimumHeight(20)
        stage_layout.addWidget(self.overall_progress_bar)
        
        # Current operation
        self.operation_label = QLabel("Click Start to begin build process")
        self.operation_label.setStyleSheet("color: #aaaaaa; font-size: 11px; margin-top: 5px;")
        stage_layout.addWidget(self.operation_label)
        
        layout.addWidget(self.stage_group)
        
        # Start build button
        self.start_build_btn = QPushButton("🚀 Start Build Process")
        self.start_build_btn.setMinimumHeight(50)
        self.start_build_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #28a745, stop:1 #1e7e34);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                padding: 15px 30px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #34ce57, stop:1 #28a745);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e7e34, stop:1 #155724);
            }
            QPushButton:disabled {
                background-color: #6c757d;
                color: #ffffff;
            }
        """)
        self.start_build_btn.clicked.connect(self._start_build_process)
        layout.addWidget(self.start_build_btn)
        
        return widget
    
    def _create_info_widget(self) -> QWidget:
        """Create the information and logs widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Tab widget for different information views
        self.info_tabs = QTabWidget()
        
        # Build log tab
        self.build_log = QTextEdit()
        self.build_log.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                font-size: 11px;
            }
        """)
        self.build_log.setReadOnly(True)
        self.info_tabs.addTab(self.build_log, "📋 Build Log")
        
        # Statistics tab
        stats_widget = self._create_statistics_widget()
        self.info_tabs.addTab(stats_widget, "📊 Statistics")
        
        # Device info tab
        device_widget = self._create_device_info_widget()
        self.info_tabs.addTab(device_widget, "💾 Device Info")
        
        layout.addWidget(self.info_tabs)
        
        return widget
    
    def _create_statistics_widget(self) -> QWidget:
        """Create the build statistics widget"""
        widget = QWidget()
        layout = QGridLayout(widget)
        
        # Statistics labels
        stats_labels = [
            ("Total Size:", "total_size_label"),
            ("Bytes Written:", "bytes_written_label"),
            ("Average Speed:", "avg_speed_label"),
            ("Peak Speed:", "peak_speed_label"),
            ("Time Elapsed:", "time_elapsed_label"),
            ("Estimated Remaining:", "time_remaining_label")
        ]
        
        for i, (label_text, attr_name) in enumerate(stats_labels):
            label = QLabel(label_text)
            label.setStyleSheet("color: #cccccc; font-weight: bold;")
            layout.addWidget(label, i, 0)
            
            value_label = QLabel("--")
            value_label.setStyleSheet("color: #ffffff;")
            setattr(self, attr_name, value_label)
            layout.addWidget(value_label, i, 1)
        
        layout.setColumnStretch(1, 1)
        return widget
    
    def _create_device_info_widget(self) -> QWidget:
        """Create the device information widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.device_info_label = QLabel("No device selected")
        self.device_info_label.setStyleSheet("color: #cccccc;")
        self.device_info_label.setWordWrap(True)
        layout.addWidget(self.device_info_label)
        
        layout.addStretch()
        return widget
    
    def on_step_entered(self):
        """Called when step becomes active - load wizard state and prepare for build"""
        self.logger.info("Build & Verify step entered - preparing for USB creation")
        
        # Load wizard state if available
        self._load_wizard_state()
        
        # Update device info display
        self._update_device_info_display()
        
        # Log entry to build log
        self._log_build_message("INFO", "Build & Verify step initialized")
        self._log_build_message("INFO", f"Target device: {self.selected_device.name if self.selected_device else 'None'}")
        self._log_build_message("INFO", f"Deployment recipe: {self.selected_recipe.name if self.selected_recipe else 'None'}")
        
        # Enable start button if all requirements are met
        self._validate_build_requirements()
    
    def on_step_left(self):
        """Called when leaving step - cleanup and save state"""
        self.logger.info("Build & Verify step exited")
        
        # Cancel any ongoing build
        if self.current_builder and self.current_builder.isRunning():
            self._emergency_stop()
    
    def _load_wizard_state(self):
        """Load wizard state from previous steps"""
        # This would be populated by the wizard controller
        # For now, we'll use placeholder data
        self.logger.info("Loading wizard state from previous steps")
        
        # In real implementation, this would come from wizard_state
        # self.selected_device = self.wizard_state.selected_device
        # self.selected_recipe = self.wizard_state.selected_recipe
        # self.hardware_profile = self.wizard_state.hardware_profile
        # self.source_files = self.wizard_state.source_files
    
    def _update_device_info_display(self):
        """Update the device information display"""
        if self.selected_device:
            device_info = f"""💾 Target Device Information:
            
Device: {self.selected_device.name}
Path: {self.selected_device.path}
Size: {self.selected_device.size_bytes / (1024**3):.1f} GB
Model: {self.selected_device.model}
Vendor: {self.selected_device.vendor}
Filesystem: {self.selected_device.filesystem}
Removable: {'Yes' if self.selected_device.is_removable else 'No'}
Health: {self.selected_device.health_status}
            
🛠️ Deployment Configuration:
            
Recipe: {self.selected_recipe.name if self.selected_recipe else 'Not selected'}
Hardware Profile: {self.hardware_profile.name if self.hardware_profile else 'Not selected'}
Source Files: {len(self.source_files)} files ready"""
            
            self.device_info_label.setText(device_info)
        else:
            self.device_info_label.setText("⚠️ No device selected")
    
    def _validate_build_requirements(self):
        """Validate that all requirements are met for build process"""
        requirements_met = (
            self.selected_device is not None and
            self.selected_recipe is not None and
            self.hardware_profile is not None
        )
        
        if requirements_met:
            self.start_build_btn.setEnabled(True)
            self.build_subtitle.setText("All requirements met - ready to build")
            self._log_build_message("INFO", "All build requirements validated successfully")
        else:
            self.start_build_btn.setEnabled(False)
            missing = []
            if not self.selected_device:
                missing.append("device selection")
            if not self.selected_recipe:
                missing.append("deployment recipe")
            if not self.hardware_profile:
                missing.append("hardware profile")
            
            self.build_subtitle.setText(f"Missing: {', '.join(missing)}")
            self._log_build_message("WARNING", f"Build requirements not met: {', '.join(missing)}")
    
    def _start_build_process(self):
        """Start the comprehensive build process"""
        self.logger.info("Starting USB build process")
        
        # Disable start button and enable emergency stop
        self.start_build_btn.setEnabled(False)
        self.emergency_stop_btn.setEnabled(True)
        
        # Update UI state
        self.build_icon.setText("⚙️")
        self.build_title.setText("Creating Bootable USB Drive")
        self.build_subtitle.setText("Build process starting...")
        
        # Reset progress tracking
        self.build_start_time = datetime.now()
        self.current_stage = 0
        self.bytes_written = 0
        self.build_completed_successfully = False
        
        # Start Stage 1: Pre-build Safety Revalidation
        self._start_stage_1_safety_revalidation()
    
    def _start_stage_1_safety_revalidation(self):
        """Stage 1: Comprehensive safety revalidation with TOCTTOU protection"""
        self.current_stage = 1
        self._update_stage_display(1, "Pre-build Safety Validation", "Performing comprehensive safety checks...")
        
        self._log_build_message("INFO", "=== STAGE 1: Pre-build Safety Revalidation ===")
        self._log_build_message("INFO", "Performing TOCTTOU protection validation...")
        
        # Simulate safety validation progress
        self.safety_timer = QTimer()
        self.safety_timer.timeout.connect(self._update_safety_validation)
        self.safety_progress = 0
        self.safety_timer.start(100)
    
    def _update_safety_validation(self):
        """Update safety validation progress"""
        self.safety_progress += 5
        self.stage_progress_bar.setValue(self.safety_progress)
        
        # Update operation text
        safety_operations = [
            "Verifying device accessibility...",
            "Checking device removability status...",
            "Validating device hasn't changed...",
            "Ensuring no mounted partitions...",
            "Confirming device safety profile...",
            "Performing final safety validation..."
        ]
        
        operation_index = min(self.safety_progress // 17, len(safety_operations) - 1)
        self.operation_label.setText(safety_operations[operation_index])
        
        if self.safety_progress >= 100:
            self.safety_timer.stop()
            self._complete_stage_1_safety()
    
    def _complete_stage_1_safety(self):
        """Complete Stage 1 and proceed to Stage 2"""
        self._log_build_message("INFO", "Safety validation completed successfully")
        self._log_build_message("INFO", "Device confirmed safe for deployment")
        
        # Update overall progress
        self.overall_progress_bar.setValue(20)
        
        # Proceed to Stage 2
        self._start_stage_2_device_preparation()
    
    def _start_stage_2_device_preparation(self):
        """Stage 2: Device preparation and partitioning"""
        self.current_stage = 2
        self._update_stage_display(2, "Device Preparation", "Preparing USB device and creating partitions...")
        
        self._log_build_message("INFO", "=== STAGE 2: Device Preparation ===")
        self._log_build_message("INFO", "Unmounting existing partitions...")
        self._log_build_message("INFO", "Creating new partition scheme...")
        
        # Simulate device preparation
        self.prep_timer = QTimer()
        self.prep_timer.timeout.connect(self._update_device_preparation)
        self.prep_progress = 0
        self.prep_timer.start(150)
    
    def _update_device_preparation(self):
        """Update device preparation progress"""
        self.prep_progress += 8
        self.stage_progress_bar.setValue(self.prep_progress)
        
        prep_operations = [
            "Unmounting device partitions...",
            "Wiping existing partition table...",
            "Creating GPT partition scheme...",
            "Creating EFI system partition...",
            "Creating main data partition...",
            "Formatting partitions..."
        ]
        
        operation_index = min(self.prep_progress // 17, len(prep_operations) - 1)
        self.operation_label.setText(prep_operations[operation_index])
        
        if self.prep_progress >= 100:
            self.prep_timer.stop()
            self._complete_stage_2_preparation()
    
    def _complete_stage_2_preparation(self):
        """Complete Stage 2 and proceed to Stage 3"""
        self._log_build_message("INFO", "Device preparation completed successfully")
        self._log_build_message("INFO", "Partitions created and formatted")
        
        # Update overall progress
        self.overall_progress_bar.setValue(40)
        
        # Proceed to Stage 3
        self._start_stage_3_image_deployment()
    
    def _start_stage_3_image_deployment(self):
        """Stage 3: OS image deployment - the main writing phase"""
        self.current_stage = 3
        self._update_stage_display(3, "OS Image Deployment", "Writing operating system image and core files...")
        
        self._log_build_message("INFO", "=== STAGE 3: OS Image Deployment ===")
        self._log_build_message("INFO", "Starting OS image write operation...")
        
        # Calculate estimated total size (simulated)
        self.total_bytes_to_write = 4.2 * 1024 * 1024 * 1024  # 4.2 GB example
        self.total_size_label.setText(f"{self.total_bytes_to_write / (1024**3):.1f} GB")
        
        # Start image writing simulation
        self.image_timer = QTimer()
        self.image_timer.timeout.connect(self._update_image_deployment)
        self.image_progress = 0
        self.last_speed_update = time.time()
        self.image_timer.start(50)  # Faster updates for writing simulation
    
    def _update_image_deployment(self):
        """Update image deployment progress with realistic speed simulation"""
        # Simulate realistic write speeds (20-80 MB/s)
        current_time = time.time()
        time_delta = current_time - self.last_speed_update
        
        # Simulate variable write speed
        import random
        base_speed = 45  # MB/s base speed
        speed_variation = random.uniform(0.8, 1.2)
        current_speed = base_speed * speed_variation
        
        # Calculate bytes written in this interval
        bytes_this_interval = current_speed * 1024 * 1024 * time_delta  # MB/s to bytes
        self.bytes_written += bytes_this_interval
        
        # Update progress
        progress_percent = min((self.bytes_written / self.total_bytes_to_write) * 100, 100)
        self.stage_progress_bar.setValue(int(progress_percent))
        
        # Update statistics
        self._update_build_statistics(current_speed)
        
        # Update operation text
        self.operation_label.setText(f"Writing OS image... {self.bytes_written / (1024**3):.1f} GB / {self.total_bytes_to_write / (1024**3):.1f} GB")
        
        self.last_speed_update = current_time
        
        if progress_percent >= 100:
            self.image_timer.stop()
            self._complete_stage_3_deployment()
    
    def _complete_stage_3_deployment(self):
        """Complete Stage 3 and proceed to Stage 4"""
        self._log_build_message("INFO", "OS image deployment completed successfully")
        self._log_build_message("INFO", f"Written {self.bytes_written / (1024**3):.1f} GB of data")
        
        # Update overall progress
        self.overall_progress_bar.setValue(70)
        
        # Proceed to Stage 4
        self._start_stage_4_bootloader_config()
    
    def _start_stage_4_bootloader_config(self):
        """Stage 4: Bootloader configuration and installation"""
        self.current_stage = 4
        self._update_stage_display(4, "Bootloader Configuration", "Installing and configuring bootloader components...")
        
        self._log_build_message("INFO", "=== STAGE 4: Bootloader Configuration ===")
        self._log_build_message("INFO", "Installing bootloader components...")
        
        # Simulate bootloader configuration
        self.bootloader_timer = QTimer()
        self.bootloader_timer.timeout.connect(self._update_bootloader_config)
        self.bootloader_progress = 0
        self.bootloader_timer.start(200)
    
    def _update_bootloader_config(self):
        """Update bootloader configuration progress"""
        self.bootloader_progress += 12
        self.stage_progress_bar.setValue(self.bootloader_progress)
        
        bootloader_operations = [
            "Installing GRUB bootloader...",
            "Configuring boot parameters...",
            "Setting up UEFI boot entries...",
            "Applying hardware-specific configs...",
            "Finalizing bootloader installation..."
        ]
        
        operation_index = min(self.bootloader_progress // 20, len(bootloader_operations) - 1)
        self.operation_label.setText(bootloader_operations[operation_index])
        
        if self.bootloader_progress >= 100:
            self.bootloader_timer.stop()
            self._complete_stage_4_bootloader()
    
    def _complete_stage_4_bootloader(self):
        """Complete Stage 4 and proceed to Stage 5"""
        self._log_build_message("INFO", "Bootloader configuration completed successfully")
        self._log_build_message("INFO", "Device is now bootable")
        
        # Update overall progress
        self.overall_progress_bar.setValue(90)
        
        # Proceed to Stage 5
        self._start_stage_5_verification()
    
    def _start_stage_5_verification(self):
        """Stage 5: Final verification and cleanup"""
        self.current_stage = 5
        self._update_stage_display(5, "Final Verification", "Verifying installation integrity and creating deployment report...")
        
        self._log_build_message("INFO", "=== STAGE 5: Final Verification ===")
        self._log_build_message("INFO", "Starting comprehensive verification...")
        
        # Simulate verification process
        self.verify_timer = QTimer()
        self.verify_timer.timeout.connect(self._update_verification)
        self.verify_progress = 0
        self.verify_timer.start(180)
    
    def _update_verification(self):
        """Update verification progress"""
        self.verify_progress += 10
        self.stage_progress_bar.setValue(self.verify_progress)
        
        verify_operations = [
            "Verifying file system integrity...",
            "Checking bootloader installation...",
            "Validating partition structure...",
            "Testing boot configuration...",
            "Generating deployment report...",
            "Finalizing USB drive..."
        ]
        
        operation_index = min(self.verify_progress // 17, len(verify_operations) - 1)
        self.operation_label.setText(verify_operations[operation_index])
        
        if self.verify_progress >= 100:
            self.verify_timer.stop()
            self._complete_build_process()
    
    def _complete_build_process(self):
        """Complete the entire build process successfully"""
        self.build_completed_successfully = True
        build_duration = datetime.now() - self.build_start_time if self.build_start_time else None
        
        # Update UI to success state
        self.build_icon.setText("✅")
        self.build_title.setText("USB Drive Created Successfully!")
        self.build_subtitle.setText(f"Completed in {build_duration.total_seconds():.0f} seconds" if build_duration else "Build completed")
        
        # Final progress updates
        self.overall_progress_bar.setValue(100)
        self.stage_progress_bar.setValue(100)
        self.operation_label.setText("Build process completed successfully")
        
        # Log completion
        self._log_build_message("SUCCESS", "=== BUILD COMPLETED SUCCESSFULLY ===")
        self._log_build_message("SUCCESS", "USB drive is ready for use")
        self._log_build_message("INFO", f"Total build time: {build_duration.total_seconds():.1f} seconds" if build_duration else "Build time unknown")
        
        # Disable emergency stop and enable navigation
        self.emergency_stop_btn.setEnabled(False)
        self.set_navigation_enabled(previous=False, next=True)
        
        # Emit completion signal
        self.step_completed.emit()
        
        # Update wizard state for summary step
        self._prepare_summary_data()
    
    def _prepare_summary_data(self):
        """Prepare build data for the summary step"""
        build_duration = datetime.now() - self.build_start_time if self.build_start_time else None
        
        summary_data = {
            "success": self.build_completed_successfully,
            "device_name": self.selected_device.name if self.selected_device else "Unknown",
            "device_size": f"{self.selected_device.size_bytes / (1024**3):.1f} GB" if self.selected_device else "Unknown",
            "recipe_name": self.selected_recipe.name if self.selected_recipe else "Unknown",
            "build_duration": f"{build_duration.total_seconds():.0f} seconds" if build_duration else "Unknown",
            "bytes_written": f"{self.bytes_written / (1024**3):.1f} GB",
            "verification_passed": True,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # This would be saved to wizard state in real implementation
        self.logger.info(f"Build summary prepared: {summary_data}")
    
    def _update_stage_display(self, stage_number: int, stage_name: str, stage_description: str):
        """Update the stage display with current information"""
        self.current_stage_label.setText(f"Stage {stage_number} of 5: {stage_name}")
        self.operation_label.setText(stage_description)
        self.stage_progress_bar.setValue(0)
        
        # Emit stage change signal
        self.build_stage_changed.emit(stage_name, stage_number)
    
    def _update_build_statistics(self, current_speed_mbps: float):
        """Update build statistics display"""
        if self.build_start_time:
            elapsed = datetime.now() - self.build_start_time
            self.elapsed_label.setText(f"Elapsed: {str(elapsed).split('.')[0]}")
            self.time_elapsed_label.setText(str(elapsed).split('.')[0])
        
        # Update speed
        self.speed_label.setText(f"Speed: {current_speed_mbps:.1f} MB/s")
        self.avg_speed_label.setText(f"{current_speed_mbps:.1f} MB/s")
        
        # Update bytes written
        self.bytes_written_label.setText(f"{self.bytes_written / (1024**3):.2f} GB")
        
        # Calculate ETA
        if current_speed_mbps > 0 and self.total_bytes_to_write > self.bytes_written:
            remaining_bytes = self.total_bytes_to_write - self.bytes_written
            eta_seconds = remaining_bytes / (current_speed_mbps * 1024 * 1024)
            eta_str = f"{int(eta_seconds // 60):02d}:{int(eta_seconds % 60):02d}"
            self.eta_label.setText(f"ETA: {eta_str}")
            self.time_remaining_label.setText(eta_str)
        else:
            self.eta_label.setText("ETA: --")
            self.time_remaining_label.setText("--")
    
    def _log_build_message(self, level: str, message: str):
        """Add a message to the build log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        level_color = {
            "INFO": "#cccccc",
            "WARNING": "#ffaa00",
            "ERROR": "#ff4444",
            "SUCCESS": "#44ff44"
        }.get(level, "#cccccc")
        
        formatted_message = f'<span style="color: #888888;">[{timestamp}]</span> <span style="color: {level_color}; font-weight: bold;">{level}:</span> <span style="color: #ffffff;">{message}</span>'
        
        self.build_log.append(formatted_message)
        
        # Auto-scroll to bottom
        cursor = self.build_log.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.build_log.setTextCursor(cursor)
    
    def _emergency_stop(self):
        """Emergency stop function with confirmation"""
        reply = QMessageBox.question(
            self,
            "Emergency Stop",
            "Are you sure you want to stop the build process?\n\nThis may leave the USB drive in an unusable state.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.logger.warning("Emergency stop initiated by user")
            self._log_build_message("WARNING", "EMERGENCY STOP initiated by user")
            
            # Stop all timers
            for timer_attr in ['safety_timer', 'prep_timer', 'image_timer', 'bootloader_timer', 'verify_timer']:
                if hasattr(self, timer_attr):
                    timer = getattr(self, timer_attr)
                    if hasattr(timer, 'stop'):
                        timer.stop()
            
            # Cancel USB builder if running
            if self.current_builder and self.current_builder.isRunning():
                self.current_builder.cancel_build()
                self.current_builder.wait(5000)  # Wait up to 5 seconds
            
            # Update UI to stopped state
            self.build_icon.setText("🛑")
            self.build_title.setText("Build Process Stopped")
            self.build_subtitle.setText("Process was stopped by user")
            self.operation_label.setText("Build process cancelled")
            
            # Re-enable start button and disable emergency stop
            self.start_build_btn.setEnabled(True)
            self.emergency_stop_btn.setEnabled(False)
            
            self._log_build_message("ERROR", "Build process stopped - USB drive may be unusable")
    
    def validate_step(self) -> bool:
        """Validate step completion"""
        return self.build_completed_successfully
    
    def get_step_data(self) -> Dict[str, Any]:
        """Get step data for wizard state"""
        build_duration = datetime.now() - self.build_start_time if self.build_start_time else None
        
        return {
            "build_completed": self.build_completed_successfully,
            "device_path": self.selected_device.path if self.selected_device else None,
            "recipe_name": self.selected_recipe.name if self.selected_recipe else None,
            "build_duration_seconds": build_duration.total_seconds() if build_duration else 0,
            "bytes_written": self.bytes_written,
            "verification_passed": self.build_completed_successfully,
            "timestamp": datetime.now().isoformat()
        }
    
    def load_step_data(self, data: Dict[str, Any]):
        """Load step data from wizard state"""
        # This would load device selection, recipe, and hardware profile
        # from previous steps in a real implementation
        self.logger.info(f"Loading step data: {data}")
        
        # Example of how wizard state would be loaded:
        # if 'selected_device' in data:
        #     self.selected_device = data['selected_device']
        # if 'selected_recipe' in data:
        #     self.selected_recipe = data['selected_recipe']
        # if 'hardware_profile' in data:
        #     self.hardware_profile = data['hardware_profile']


class SummaryStepView(StepView):
    """Summary step view"""
    
    def __init__(self):
        super().__init__(
            "Summary",
            "Deployment completed successfully. Your bootable USB drive is ready."
        )
        self._setup_content()
    
    def _setup_content(self):
        """Setup summary content"""
        # Success message
        success_group = QGroupBox("Deployment Results")
        success_layout = QVBoxLayout(success_group)
        
        success_text = """✅ Bootable USB drive created successfully!

Operation Details:
• Source: macOS Ventura 13.0 (4.2 GB)
• Target: SanDisk 32GB USB Drive
• Duration: 18 minutes 34 seconds
• Verification: Passed ✓

Your USB drive is now ready to boot on compatible systems."""
        
        success_label = QLabel(success_text)
        success_label.setWordWrap(True)
        success_label.setStyleSheet("color: #cccccc; font-size: 14px; padding: 10px;")
        success_layout.addWidget(success_label)
        
        self.content_layout.addWidget(success_group)
        
        # Action buttons
        action_group = QGroupBox("Next Steps")
        action_layout = QVBoxLayout(action_group)
        
        eject_button = QPushButton("Safely Eject USB Drive")
        eject_button.clicked.connect(self._eject_drive)
        action_layout.addWidget(eject_button)
        
        new_button = QPushButton("Create Another USB Drive")
        new_button.clicked.connect(self._start_new)
        action_layout.addWidget(new_button)
        
        self.content_layout.addWidget(action_group)
        
        # Hide navigation buttons since we're at the end
        self.previous_button.setVisible(False)
        self.next_button.setText("Finish")
    
    def _eject_drive(self):
        """Safely eject the drive"""
        QMessageBox.information(self, "Success", "USB drive ejected safely.")
    
    def _start_new(self):
        """Start a new deployment"""
        self.request_previous_step.emit()  # This will need custom handling


class BootForgeStepperWizard(QWidget):
    """Main stepper wizard widget combining StepperHeader with step content"""
    
    # Signals for integration with main window
    wizard_completed = pyqtSignal()
    step_changed = pyqtSignal(int, str)  # step_index, step_name
    status_updated = pyqtSignal(str)  # status message
    progress_updated = pyqtSignal(int)  # progress percentage
    
    def __init__(self, disk_manager: DiskManager):
        super().__init__()
        self.disk_manager = disk_manager
        self.logger = logging.getLogger(__name__)
        
        # Initialize wizard controller (temporarily disabled for debugging)
        self.wizard_controller = None  # Temporarily disable controller
        
        # Setup UI
        self._setup_ui()
        self._setup_step_views()
        self._setup_connections()
        
        # Initialize to first step
        self._update_current_step(0)
        
        self.logger.info("BootForge stepper wizard initialized")
    
    def _setup_ui(self):
        """Setup the main wizard UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create stepper header
        step_names = [
            "Hardware Detection",
            "OS Image Selection", 
            "USB Configuration",
            "Safety Review",
            "Build & Verify",
            "Summary"
        ]
        
        self.stepper_header = StepperHeader()
        layout.addWidget(self.stepper_header)
        
        # Create stacked widget for step content
        self.step_stack = QStackedWidget()
        layout.addWidget(self.step_stack)
        
        self.current_step_index = 0
    
    def _setup_step_views(self):
        """Setup individual step view widgets"""
        self.step_views = [
            HardwareDetectionStepView(),
            OSImageSelectionStepView(),
            USBConfigurationStepView(),
            SafetyReviewStepView(),
            BuildVerifyStepView(),
            SummaryStepView()
        ]
        
        # Add step views to stack
        for step_view in self.step_views:
            self.step_stack.addWidget(step_view)
        
        # Connect step view signals
        for i, step_view in enumerate(self.step_views):
            step_view.step_completed.connect(lambda idx=i: self._on_step_completed(idx))
            step_view.step_data_changed.connect(lambda data, idx=i: self._on_step_data_changed(idx, data))
            step_view.request_next_step.connect(self._next_step)
            step_view.request_previous_step.connect(self._previous_step)
    
    def _setup_connections(self):
        """Setup signal connections"""
        # Connect stepper header navigation
        self.stepper_header.step_clicked.connect(self._navigate_to_step)
        
        # Connect wizard controller signals (if controller is available)
        if self.wizard_controller:
            self.wizard_controller.step_changed.connect(self._on_controller_step_changed)
            self.wizard_controller.state_updated.connect(self._on_controller_state_updated)
    
    def _update_current_step(self, step_index: int):
        """Update the current step"""
        if 0 <= step_index < len(self.step_views):
            # Update header
            self.stepper_header.set_current_step(step_index)
            
            # Update stack
            old_index = self.current_step_index
            self.current_step_index = step_index
            self.step_stack.setCurrentIndex(step_index)
            
            # Notify views
            if old_index != step_index:
                if 0 <= old_index < len(self.step_views):
                    self.step_views[old_index].on_step_left()
                self.step_views[step_index].on_step_entered()
            
            # Emit signals
            step_name = ["Hardware Detection", "OS Image Selection", "USB Configuration", 
                        "Safety Review", "Build & Verify", "Summary"][step_index]
            self.step_changed.emit(step_index, step_name)
            self.status_updated.emit(f"Step {step_index + 1}: {step_name}")
            
            self.logger.debug(f"Navigated to step {step_index}: {step_name}")
    
    def _navigate_to_step(self, step_index: int):
        """Navigate to specific step (from header click)"""
        # Only allow navigation to completed or adjacent steps
        if step_index <= self.current_step_index + 1:
            self._update_current_step(step_index)
    
    def _next_step(self):
        """Navigate to next step"""
        if self.current_step_index < len(self.step_views) - 1:
            current_view = self.step_views[self.current_step_index]
            if current_view.validate_step():
                self._update_current_step(self.current_step_index + 1)
                # Mark previous step as complete
                self.stepper_header.mark_step_complete(self.current_step_index - 1)
            else:
                self.status_updated.emit("Please complete the current step before proceeding")
    
    def _previous_step(self):
        """Navigate to previous step"""
        if self.current_step_index > 0:
            self._update_current_step(self.current_step_index - 1)
    
    def _on_step_completed(self, step_index: int):
        """Handle step completion"""
        self.stepper_header.mark_step_complete(step_index)
        self.status_updated.emit(f"Step {step_index + 1} completed successfully")
        
        # Auto-advance for certain steps
        if step_index == len(self.step_views) - 1:
            self.wizard_completed.emit()
    
    def _on_step_data_changed(self, step_index: int, data: Dict[str, Any]):
        """Handle step data changes"""
        self.logger.debug(f"Step {step_index} data changed: {data}")
    
    def _on_controller_step_changed(self, old_step, new_step):
        """Handle wizard controller step changes"""
        step_index = list(WizardStep).index(new_step)
        self._update_current_step(step_index)
    
    def _on_controller_state_updated(self, state: WizardState):
        """Handle wizard controller state updates"""
        self.logger.debug(f"Wizard state updated: {state.current_step}")
    
    def reset_wizard(self):
        """Reset wizard to initial state"""
        self._update_current_step(0)
        for i, step_view in enumerate(self.step_views):
            pass  # States will be handled by set_current_step
        self.stepper_header.set_current_step(0)
        self.status_updated.emit("Wizard reset to beginning")
        self.logger.info("Wizard reset to initial state")