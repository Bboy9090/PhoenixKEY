"""
BootForge USB Recipe Manager GUI
Interface for creating deployment USB drives using the USB Builder Engine
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QPushButton, QComboBox, QListWidget,
    QListWidgetItem, QProgressBar, QTextEdit, QFileDialog,
    QMessageBox, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QLineEdit, QCheckBox, QSplitter, QFrame, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QInputDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QPixmap, QIcon, QColor, QPalette

from src.core.usb_builder import (
    StorageBuilderEngine, DeploymentRecipe, HardwareProfile,
    BuildProgress, DeploymentType, PartitionScheme, FileSystem
)
from src.core.disk_manager import DiskInfo
from src.core.safety_validator import SafetyValidator, SafetyLevel, ValidationResult
from src.core.config import Config
from src.core.hardware_detector import HardwareDetector, DetectedHardware, DetectionConfidence
from src.core.hardware_matcher import HardwareMatcher, ProfileMatch
from src.gui.os_image_widget import OSImageSelectionWidget


class RecipeSelectionWidget(QWidget):
    """Widget for selecting deployment recipes"""
    
    recipe_selected = pyqtSignal(str)  # recipe name
    
    def __init__(self):
        super().__init__()
        self.recipes: List[DeploymentRecipe] = []
        self.selected_recipe: Optional[DeploymentRecipe] = None
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup recipe selection UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Select Deployment Recipe")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Recipe list
        self.recipe_list = QListWidget()
        self.recipe_list.itemSelectionChanged.connect(self._on_recipe_selected)
        layout.addWidget(self.recipe_list)
        
        # Recipe details
        details_group = QGroupBox("Recipe Details")
        details_layout = QVBoxLayout(details_group)
        
        self.description_label = QLabel("Select a recipe to view details")
        self.description_label.setWordWrap(True)
        details_layout.addWidget(self.description_label)
        
        # Partition table
        self.partition_table = QTableWidget()
        self.partition_table.setColumnCount(4)
        self.partition_table.setHorizontalHeaderLabels(["Name", "Size (MB)", "Filesystem", "Bootable"])
        header = self.partition_table.horizontalHeader()
        if header:
            header.setStretchLastSection(True)
        self.partition_table.setMaximumHeight(150)
        details_layout.addWidget(self.partition_table)
        
        # Required files
        files_label = QLabel("Required Files:")
        files_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        details_layout.addWidget(files_label)
        
        self.required_files_list = QListWidget()
        self.required_files_list.setMaximumHeight(100)
        details_layout.addWidget(self.required_files_list)
        
        layout.addWidget(details_group)
    
    def load_recipes(self, recipes: List[DeploymentRecipe]):
        """Load available recipes"""
        self.recipes = recipes
        self.recipe_list.clear()
        
        for recipe in recipes:
            item = QListWidgetItem(recipe.name)
            item.setData(Qt.ItemDataRole.UserRole, recipe)
            
            # Add deployment type badge
            if recipe.deployment_type == DeploymentType.MACOS_OCLP:
                item.setBackground(QColor("#007AFF"))
            elif recipe.deployment_type == DeploymentType.WINDOWS_UNATTENDED:
                item.setBackground(QColor("#FF6B35"))
            elif recipe.deployment_type == DeploymentType.LINUX_AUTOMATED:
                item.setBackground(QColor("#28A745"))
            else:
                item.setBackground(QColor("#6C757D"))
            
            self.recipe_list.addItem(item)
    
    def _on_recipe_selected(self):
        """Handle recipe selection"""
        current_item = self.recipe_list.currentItem()
        if current_item:
            recipe = current_item.data(Qt.ItemDataRole.UserRole)
            self.selected_recipe = recipe
            self._update_recipe_details(recipe)
            self.recipe_selected.emit(recipe.name)
    
    def _update_recipe_details(self, recipe: DeploymentRecipe):
        """Update recipe details display"""
        # Description
        self.description_label.setText(recipe.description)
        
        # Partition table
        self.partition_table.setRowCount(len(recipe.partitions))
        
        for i, partition in enumerate(recipe.partitions):
            self.partition_table.setItem(i, 0, QTableWidgetItem(partition.name))
            
            size_text = "Remaining Space" if partition.size_mb == -1 else f"{partition.size_mb}"
            self.partition_table.setItem(i, 1, QTableWidgetItem(size_text))
            
            self.partition_table.setItem(i, 2, QTableWidgetItem(partition.filesystem.value))
            self.partition_table.setItem(i, 3, QTableWidgetItem("Yes" if partition.bootable else "No"))
        
        # Required files
        self.required_files_list.clear()
        for file_name in recipe.required_files:
            self.required_files_list.addItem(file_name)


class HardwareDetectionThread(QThread):
    """Thread for hardware detection to avoid blocking GUI"""
    
    detection_completed = pyqtSignal(object)  # DetectedHardware
    detection_failed = pyqtSignal(str)  # error message
    
    def __init__(self):
        super().__init__()
        self.detector = HardwareDetector()
    
    def run(self):
        """Run hardware detection in background"""
        try:
            detected_hardware = self.detector.detect_hardware()
            if detected_hardware:
                self.detection_completed.emit(detected_hardware)
            else:
                self.detection_failed.emit("Hardware detection failed - no data collected")
        except Exception as e:
            self.detection_failed.emit(f"Hardware detection error: {str(e)}")


class HardwareProfileWidget(QWidget):
    """Widget for selecting hardware profiles with auto-detection capabilities"""
    
    profile_selected = pyqtSignal(str)  # profile name
    detection_completed = pyqtSignal(object)  # DetectedHardware
    
    def __init__(self):
        super().__init__()
        self.profiles: List[HardwareProfile] = []
        self.selected_profile: Optional[HardwareProfile] = None
        self.detected_hardware: Optional[DetectedHardware] = None
        self.profile_matches: List[ProfileMatch] = []
        
        # Hardware detection components
        self.hardware_matcher = HardwareMatcher()
        self.detection_thread = HardwareDetectionThread()
        self.detection_thread.detection_completed.connect(self._on_detection_completed)
        self.detection_thread.detection_failed.connect(self._on_detection_failed)
        
        self._setup_ui()
        self._setup_detection_connections()
    
    def _setup_ui(self):
        """Setup hardware profile selection UI"""
        layout = QVBoxLayout(self)
        
        # Title and auto-detect
        title_layout = QHBoxLayout()
        
        title = QLabel("Target Hardware Profile")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title_layout.addWidget(title)
        
        title_layout.addStretch()
        
        self.auto_detect_btn = QPushButton("🔍 Auto-Detect Hardware")
        self.auto_detect_btn.setToolTip("Automatically detect current system hardware profile")
        self.auto_detect_btn.setMinimumWidth(160)
        title_layout.addWidget(self.auto_detect_btn)
        
        # Detection status indicator
        self.detection_status = QLabel("")
        self.detection_status.setStyleSheet("color: #6C757D; font-size: 10px;")
        title_layout.addWidget(self.detection_status)
        
        layout.addLayout(title_layout)
        
        # Profile list
        self.profile_list = QListWidget()
        self.profile_list.itemSelectionChanged.connect(self._on_profile_selected)
        layout.addWidget(self.profile_list)
        
        # Detection results section
        detection_group = QGroupBox("🎯 Detection Results")
        detection_layout = QVBoxLayout(detection_group)
        
        self.detection_results = QLabel("Click 'Auto-Detect Hardware' to scan your system")
        self.detection_results.setWordWrap(True)
        self.detection_results.setStyleSheet("padding: 10px; color: #6C757D;")
        detection_layout.addWidget(self.detection_results)
        
        # Detected hardware summary (initially hidden)
        self.hardware_summary = QLabel()
        self.hardware_summary.setWordWrap(True)
        self.hardware_summary.setStyleSheet("padding: 10px; background: #2D3748; color: #E2E8F0; border-radius: 4px;")
        self.hardware_summary.setVisible(False)
        detection_layout.addWidget(self.hardware_summary)
        
        layout.addWidget(detection_group)
        
        # Profile details
        details_group = QGroupBox("📋 Selected Profile Details")
        details_layout = QGridLayout(details_group)
        
        # Hardware info labels
        details_layout.addWidget(QLabel("Platform:"), 0, 0)
        self.platform_label = QLabel("-")
        details_layout.addWidget(self.platform_label, 0, 1)
        
        details_layout.addWidget(QLabel("Model:"), 1, 0)
        self.model_label = QLabel("-")
        details_layout.addWidget(self.model_label, 1, 1)
        
        details_layout.addWidget(QLabel("Architecture:"), 2, 0)
        self.arch_label = QLabel("-")
        details_layout.addWidget(self.arch_label, 2, 1)
        
        details_layout.addWidget(QLabel("Year:"), 3, 0)
        self.year_label = QLabel("-")
        details_layout.addWidget(self.year_label, 3, 1)
        
        details_layout.addWidget(QLabel("CPU Family:"), 4, 0)
        self.cpu_label = QLabel("-")
        details_layout.addWidget(self.cpu_label, 4, 1)
        
        # Match confidence (initially hidden)
        details_layout.addWidget(QLabel("Match Confidence:"), 5, 0)
        self.confidence_label = QLabel("-")
        self.confidence_label.setVisible(False)
        details_layout.addWidget(self.confidence_label, 5, 1)
        
        layout.addWidget(details_group)
    
    def load_profiles(self, profiles: List[HardwareProfile]):
        """Load available hardware profiles"""
        self.profiles = profiles
        self._update_profile_list()
    
    def _update_profile_list(self):
        """Update the profile list display with detection indicators"""
        self.profile_list.clear()
        
        # Group profiles by platform
        platform_groups = {}
        for profile in self.profiles:
            if profile.platform not in platform_groups:
                platform_groups[profile.platform] = []
            platform_groups[profile.platform].append(profile)
        
        # Sort profiles by match score if we have detection results
        if self.profile_matches:
            matched_profiles = {match.profile.name: match for match in self.profile_matches}
        else:
            matched_profiles = {}
        
        for platform, platform_profiles in platform_groups.items():
            # Add platform header
            header_item = QListWidgetItem(f"── {platform.upper()} ──")
            header_item.setFlags(Qt.ItemFlag.NoItemFlags)
            header_item.setBackground(QColor("#3C3C3C"))
            self.profile_list.addItem(header_item)
            
            # Sort profiles by match score for this platform
            platform_profiles_sorted = sorted(
                platform_profiles, 
                key=lambda p: matched_profiles[p.name].match_score if p.name in matched_profiles else 0, 
                reverse=True
            )
            
            # Add profiles with match indicators
            for profile in platform_profiles_sorted:
                # Build display text with confidence indicators
                display_text = f"  {profile.name}"
                
                # Add match indicator if this profile was matched
                if profile.name in matched_profiles:
                    match = matched_profiles[profile.name]
                    confidence_icons = {
                        DetectionConfidence.EXACT_MATCH: "🎯",
                        DetectionConfidence.HIGH_CONFIDENCE: "✅", 
                        DetectionConfidence.MEDIUM_CONFIDENCE: "⚠️",
                        DetectionConfidence.LOW_CONFIDENCE: "❓",
                        DetectionConfidence.UNKNOWN: "❌"
                    }
                    icon = confidence_icons.get(match.confidence, "")
                    display_text = f"  {icon} {profile.name} ({match.match_score:.0f}%)"
                
                item = QListWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, profile)
                
                # Color code by platform with match highlighting
                base_color = QColor("#6C757D")  # Default gray
                if profile.platform == "mac":
                    base_color = QColor("#007AFF")
                elif profile.platform == "windows":
                    base_color = QColor("#FF6B35")
                elif profile.platform == "linux":
                    base_color = QColor("#28A745")
                
                # Brighten color for high-confidence matches
                if profile.name in matched_profiles:
                    match = matched_profiles[profile.name]
                    if match.confidence in [DetectionConfidence.EXACT_MATCH, DetectionConfidence.HIGH_CONFIDENCE]:
                        # Make the color brighter for good matches
                        r, g, b = base_color.red(), base_color.green(), base_color.blue()
                        base_color = QColor(min(255, r + 40), min(255, g + 40), min(255, b + 40))
                
                item.setBackground(base_color)
                
                # Set tooltip with match details
                if profile.name in matched_profiles:
                    match = matched_profiles[profile.name]
                    tooltip = f"{profile.name}\n\nMatch Score: {match.match_score:.1f}%\nConfidence: {match.get_confidence_text()}\n\nReasons:\n"
                    for reason in match.match_reasons[:3]:
                        tooltip += f"• {reason}\n"
                    item.setToolTip(tooltip)
                else:
                    item.setToolTip(f"{profile.name}\nPlatform: {profile.platform}\nArchitecture: {profile.architecture}")
                
                self.profile_list.addItem(item)
    
    def _on_profile_selected(self):
        """Handle profile selection"""
        current_item = self.profile_list.currentItem()
        if current_item and current_item.data(Qt.ItemDataRole.UserRole):
            profile = current_item.data(Qt.ItemDataRole.UserRole)
            self.selected_profile = profile
            self._update_profile_details(profile)
            self.profile_selected.emit(profile.model)
    
    def _update_profile_details(self, profile: HardwareProfile):
        """Update profile details display"""
        self.platform_label.setText(profile.platform.capitalize())
        self.model_label.setText(profile.model)
        self.arch_label.setText(profile.architecture)
        self.year_label.setText(str(profile.year) if profile.year else "Unknown")
        self.cpu_label.setText(profile.cpu_family or "Unknown")
        
        # Update match confidence if available
        matched_profiles = {match.profile.name: match for match in self.profile_matches}
        if profile.name in matched_profiles:
            match = matched_profiles[profile.name]
            confidence_text = f"{match.get_confidence_text()} ({match.match_score:.1f}%)"
            self.confidence_label.setText(confidence_text)
            self.confidence_label.setVisible(True)
        else:
            self.confidence_label.setVisible(False)
    
    def _setup_detection_connections(self):
        """Setup hardware detection connections"""
        self.auto_detect_btn.clicked.connect(self._start_detection)
    
    def _start_detection(self):
        """Start hardware detection process"""
        if self.detection_thread.isRunning():
            return
        
        # Update UI to show detection in progress
        self.auto_detect_btn.setEnabled(False)
        self.auto_detect_btn.setText("🔄 Detecting...")
        self.detection_status.setText("Scanning hardware...")
        self.detection_results.setText("🔍 Scanning your system hardware...\nThis may take a few moments.")
        
        # Start detection thread
        self.detection_thread.start()
    
    def _on_detection_completed(self, detected_hardware: DetectedHardware):
        """Handle successful hardware detection"""
        self.detected_hardware = detected_hardware
        
        # Find matching profiles
        self.profile_matches = self.hardware_matcher.find_matching_profiles(detected_hardware, max_results=10)
        
        # Update UI
        self._update_detection_results()
        self._update_profile_list()
        
        # Auto-select best match if available
        if self.profile_matches:
            best_match = self.profile_matches[0]
            self._select_profile_by_name(best_match.profile.name)
        
        # Reset button state
        self.auto_detect_btn.setEnabled(True)
        self.auto_detect_btn.setText("🔍 Auto-Detect Hardware")
        self.detection_status.setText(f"✅ Detection completed ({detected_hardware.detection_confidence.value})")
        
        # Emit detection completed signal
        self.detection_completed.emit(detected_hardware)
    
    def _on_detection_failed(self, error_message: str):
        """Handle failed hardware detection"""
        # Update UI to show error
        self.detection_results.setText(f"❌ Hardware detection failed:\n{error_message}")
        self.detection_status.setText("❌ Detection failed")
        
        # Reset button state
        self.auto_detect_btn.setEnabled(True)
        self.auto_detect_btn.setText("🔍 Auto-Detect Hardware")
    
    def _update_detection_results(self):
        """Update the detection results display"""
        if not self.detected_hardware:
            return
        
        hw = self.detected_hardware
        
        # Create detection summary
        summary_parts = []
        summary_parts.append(f"🖥️  System: {hw.get_summary()}")
        summary_parts.append(f"🎯  Detection Confidence: {hw.detection_confidence.value.title()}")
        
        if hw.platform:
            summary_parts.append(f"💻  Platform: {hw.platform.title()}")
        
        if self.profile_matches:
            best_match = self.profile_matches[0]
            summary_parts.append(f"✨  Best Match: {best_match.profile.name} ({best_match.match_score:.0f}%)")
            summary_parts.append(f"📊  Found {len(self.profile_matches)} compatible profiles")
        
        summary_text = "\n".join(summary_parts)
        
        self.detection_results.setText("🎯 Hardware Detection Results:")
        self.hardware_summary.setText(summary_text)
        self.hardware_summary.setVisible(True)
    
    def _select_profile_by_name(self, profile_name: str):
        """Select a profile by name in the list"""
        for i in range(self.profile_list.count()):
            item = self.profile_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole):
                profile = item.data(Qt.ItemDataRole.UserRole)
                if profile.name == profile_name:
                    self.profile_list.setCurrentItem(item)
                    break
    
    def get_detection_summary(self) -> str:
        """Get a summary of the detection results for logging/reporting"""
        if not self.detected_hardware:
            return "No hardware detection performed"
        
        summary = []
        summary.append(f"Hardware Detection Summary:")
        summary.append(f"  System: {self.detected_hardware.get_summary()}")
        summary.append(f"  Platform: {self.detected_hardware.platform}")
        summary.append(f"  Confidence: {self.detected_hardware.detection_confidence.value}")
        
        if self.profile_matches:
            summary.append(f"  Profile Matches: {len(self.profile_matches)}")
            for i, match in enumerate(self.profile_matches[:3]):
                summary.append(f"    {i+1}. {match.profile.name} ({match.match_score:.1f}%)")
        
        return "\n".join(summary)


class FileSelectionWidget(QWidget):
    """Widget for selecting source files"""
    
    files_updated = pyqtSignal(dict)  # file mapping
    
    def __init__(self):
        super().__init__()
        self.required_files: List[str] = []
        self.optional_files: List[str] = []
        self.file_paths: Dict[str, str] = {}
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup file selection UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Source Files")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # File selection table
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(4)
        self.file_table.setHorizontalHeaderLabels(["File", "Required", "Path", "Browse"])
        
        header = self.file_table.horizontalHeader()
        if header:
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.file_table)
        
        # Status
        self.status_label = QLabel("Select files for the chosen recipe")
        layout.addWidget(self.status_label)
    
    def set_required_files(self, required: List[str], optional: Optional[List[str]] = None):
        """Set required and optional files"""
        self.required_files = required
        self.optional_files = optional if optional is not None else []
        self.file_paths = {}
        self._update_file_table()
    
    def _update_file_table(self):
        """Update file selection table"""
        all_files = [(f, True) for f in self.required_files] + [(f, False) for f in self.optional_files]
        
        self.file_table.setRowCount(len(all_files))
        
        for i, (file_name, is_required) in enumerate(all_files):
            # File name
            self.file_table.setItem(i, 0, QTableWidgetItem(file_name))
            
            # Required status
            required_item = QTableWidgetItem("Yes" if is_required else "No")
            if is_required:
                required_item.setBackground(QColor("#FF6B35"))
            else:
                required_item.setBackground(QColor("#28A745"))
            self.file_table.setItem(i, 1, required_item)
            
            # Path (empty initially)
            path_item = QTableWidgetItem("Not selected")
            path_item.setForeground(QColor("#6C757D"))
            self.file_table.setItem(i, 2, path_item)
            
            # Browse button
            browse_btn = QPushButton("Browse...")
            browse_btn.clicked.connect(lambda checked, fn=file_name: self._browse_file(fn))
            self.file_table.setCellWidget(i, 3, browse_btn)
        
        self._update_status()
    
    def _browse_file(self, file_name: str):
        """Browse for a specific file"""
        # Determine file filter based on file name
        file_filter = "All Files (*)"
        if file_name.endswith(".iso"):
            file_filter = "ISO Files (*.iso);;All Files (*)"
        elif file_name.endswith(".app"):
            file_filter = "macOS Applications (*.app);;All Files (*)"
        elif file_name.endswith(".xml"):
            file_filter = "XML Files (*.xml);;All Files (*)"
        elif file_name.endswith(".zip"):
            file_filter = "ZIP Archives (*.zip);;All Files (*)"
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Select {file_name}", "", file_filter
        )
        
        if file_path:
            self.file_paths[file_name] = file_path
            self._update_file_display(file_name, file_path)
            self._update_status()
            self.files_updated.emit(self.file_paths)
    
    def _update_file_display(self, file_name: str, file_path: str):
        """Update file path display in table"""
        for i in range(self.file_table.rowCount()):
            item = self.file_table.item(i, 0)
            if item and item.text() == file_name:
                path_item = QTableWidgetItem(file_path)
                path_item.setForeground(QColor("#28A745"))
                path_item.setToolTip(file_path)
                self.file_table.setItem(i, 2, path_item)
                break
    
    def _update_status(self):
        """Update status label"""
        required_count = len(self.required_files)
        selected_required = len([f for f in self.required_files if f in self.file_paths])
        
        if selected_required == required_count:
            self.status_label.setText(f"✅ All required files selected ({selected_required}/{required_count})")
            self.status_label.setStyleSheet("color: #28A745;")
        else:
            self.status_label.setText(f"⚠️ Missing required files ({selected_required}/{required_count})")
            self.status_label.setStyleSheet("color: #FF6B35;")
    
    def is_ready(self) -> bool:
        """Check if all required files are selected"""
        return all(f in self.file_paths for f in self.required_files)


class BuildProgressWidget(QWidget):
    """Widget for displaying build progress and logs"""
    
    def __init__(self):
        super().__init__()
        self.build_logs: List[str] = []
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup build progress UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Build Progress")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Progress bars
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        # Overall progress
        progress_layout.addWidget(QLabel("Overall Progress:"))
        self.overall_progress = QProgressBar()
        self.overall_progress.setFormat("%p% - %v/%m")
        progress_layout.addWidget(self.overall_progress)
        
        # Current step progress
        progress_layout.addWidget(QLabel("Current Step:"))
        self.step_progress = QProgressBar()
        progress_layout.addWidget(self.step_progress)
        
        # Status labels
        self.status_label = QLabel("Ready to build")
        self.status_label.setWordWrap(True)
        progress_layout.addWidget(self.status_label)
        
        self.eta_label = QLabel("")
        progress_layout.addWidget(self.eta_label)
        
        layout.addWidget(progress_group)
        
        # Build log
        log_group = QGroupBox("Build Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setMaximumHeight(200)
        log_layout.addWidget(self.log_text)
        
        # Log controls
        log_controls = QHBoxLayout()
        
        self.clear_log_btn = QPushButton("Clear Log")
        self.clear_log_btn.clicked.connect(self._clear_log)
        log_controls.addWidget(self.clear_log_btn)
        
        self.save_log_btn = QPushButton("Save Log")
        self.save_log_btn.clicked.connect(self._save_log)
        log_controls.addWidget(self.save_log_btn)
        
        log_controls.addStretch()
        log_layout.addLayout(log_controls)
        
        layout.addWidget(log_group)
    
    def update_progress(self, progress: BuildProgress):
        """Update progress display"""
        # Overall progress
        self.overall_progress.setValue(int(progress.overall_progress))
        self.overall_progress.setFormat(f"{progress.overall_progress:.1f}% - Step {progress.step_number}/{progress.total_steps}")
        
        # Step progress
        self.step_progress.setValue(int(progress.step_progress))
        self.step_progress.setFormat(f"{progress.current_step} - {progress.step_progress:.1f}%")
        
        # Status
        self.status_label.setText(progress.detailed_status)
        
        # ETA
        if progress.eta_seconds > 0:
            eta_text = f"ETA: {progress.eta_seconds // 60}m {progress.eta_seconds % 60}s"
            if progress.speed_mbps > 0:
                eta_text += f" ({progress.speed_mbps:.1f} MB/s)"
            self.eta_label.setText(eta_text)
        else:
            self.eta_label.setText("")
    
    def add_log_message(self, level: str, message: str):
        """Add log message"""
        import time
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        
        self.build_logs.append(log_entry)
        
        # Color code by level
        if level == "ERROR":
            color = "#FF6B35"
        elif level == "WARNING":
            color = "#FFB800"
        elif level == "INFO":
            color = "#28A745"
        else:
            color = "#FFFFFF"
        
        self.log_text.append(f'<span style="color: {color};">{log_entry}</span>')
        
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())
    
    def _clear_log(self):
        """Clear build log"""
        self.log_text.clear()
        self.build_logs.clear()
    
    def _save_log(self):
        """Save build log to file"""
        if not self.build_logs:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Build Log", "bootforge_build.log", "Log Files (*.log);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write('\n'.join(self.build_logs))
                
                QMessageBox.information(self, "Success", f"Build log saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save log: {str(e)}")


class USBRecipeManagerWidget(QWidget):
    """Main USB Recipe Manager widget"""
    
    def __init__(self, disk_manager=None, config=None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.storage_builder = StorageBuilderEngine()
        self.disk_manager = disk_manager
        self.safety_validator = SafetyValidator(SafetyLevel.STANDARD)
        
        # Initialize config
        self.config = config if config is not None else Config()
        
        # Current selections
        self.selected_recipe: Optional[str] = None
        self.selected_profile: Optional[str] = None
        self.selected_device: Optional[str] = None
        self.source_files: Dict[str, str] = {}
        
        self._setup_ui()
        self._load_data()
        self._setup_connections()
    
    def _setup_ui(self):
        """Setup main UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("USB Deployment Builder")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Main content splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(main_splitter)
        
        # Left panel - Configuration
        config_panel = self._create_config_panel()
        main_splitter.addWidget(config_panel)
        
        # Right panel - Progress and logs
        progress_panel = self._create_progress_panel()
        main_splitter.addWidget(progress_panel)
        
        # Set splitter proportions
        main_splitter.setSizes([600, 400])
        
        # Control buttons
        controls_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Refresh Devices")
        self.refresh_btn.clicked.connect(self._refresh_devices)
        controls_layout.addWidget(self.refresh_btn)
        
        controls_layout.addStretch()
        
        self.build_btn = QPushButton("Build USB Drive")
        self.build_btn.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0056CC;
            }
            QPushButton:disabled {
                background-color: #6C757D;
            }
        """)
        self.build_btn.clicked.connect(self._start_build)
        self.build_btn.setEnabled(False)
        controls_layout.addWidget(self.build_btn)
        
        self.cancel_btn = QPushButton("Cancel Build")
        self.cancel_btn.clicked.connect(self._cancel_build)
        self.cancel_btn.setEnabled(False)
        controls_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(controls_layout)
    
    def _create_config_panel(self) -> QWidget:
        """Create configuration panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Configuration tabs
        tab_widget = QTabWidget()
        
        # Recipe tab
        self.recipe_widget = RecipeSelectionWidget()
        tab_widget.addTab(self.recipe_widget, "1. Recipe")
        
        # Hardware tab
        self.hardware_widget = HardwareProfileWidget()
        tab_widget.addTab(self.hardware_widget, "2. Hardware")
        
        # OS Images tab (new!)
        self.os_image_widget = OSImageSelectionWidget(self.config)
        tab_widget.addTab(self.os_image_widget, "3. OS Images")
        
        # Files tab (now for additional files)
        self.files_widget = FileSelectionWidget()
        tab_widget.addTab(self.files_widget, "4. Files")
        
        # Device tab
        device_widget = self._create_device_selection_widget()
        tab_widget.addTab(device_widget, "5. Device")
        
        layout.addWidget(tab_widget)
        
        return panel
    
    def _create_device_selection_widget(self) -> QWidget:
        """Create device selection widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Title
        title = QLabel("Target USB Device")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Device list
        self.device_list = QListWidget()
        self.device_list.itemSelectionChanged.connect(self._on_device_selected)
        layout.addWidget(self.device_list)
        
        # Device details
        details_group = QGroupBox("Device Details")
        details_layout = QGridLayout(details_group)
        
        details_layout.addWidget(QLabel("Path:"), 0, 0)
        self.device_path_label = QLabel("-")
        details_layout.addWidget(self.device_path_label, 0, 1)
        
        details_layout.addWidget(QLabel("Size:"), 1, 0)
        self.device_size_label = QLabel("-")
        details_layout.addWidget(self.device_size_label, 1, 1)
        
        details_layout.addWidget(QLabel("Model:"), 2, 0)
        self.device_model_label = QLabel("-")
        details_layout.addWidget(self.device_model_label, 2, 1)
        
        details_layout.addWidget(QLabel("Health:"), 3, 0)
        self.device_health_label = QLabel("-")
        details_layout.addWidget(self.device_health_label, 3, 1)
        
        layout.addWidget(details_group)
        
        # Warning
        warning = QLabel("⚠️ WARNING: All data on the selected device will be erased!")
        warning.setStyleSheet("color: #FF6B35; font-weight: bold;")
        warning.setWordWrap(True)
        layout.addWidget(warning)
        
        return widget
    
    def _create_progress_panel(self) -> QWidget:
        """Create progress panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Progress widget
        self.progress_widget = BuildProgressWidget()
        layout.addWidget(self.progress_widget)
        
        return panel
    
    def _load_data(self):
        """Load initial data"""
        # Load recipes
        recipes = self.storage_builder.get_available_recipes()
        self.recipe_widget.load_recipes(recipes)
        
        # Load hardware profiles
        profiles = self.storage_builder.get_hardware_profiles()
        self.hardware_widget.load_profiles(profiles)
        
        # Auto-detect hardware if possible
        detected_profile = self.storage_builder.detect_hardware_profile()
        if detected_profile:
            self.logger.info(f"Auto-detected hardware: {detected_profile.name}")
        
        # Load devices
        self._refresh_devices()
    
    def _setup_connections(self):
        """Setup signal connections"""
        # Recipe selection
        self.recipe_widget.recipe_selected.connect(self._on_recipe_selected)
        
        # Hardware selection
        self.hardware_widget.profile_selected.connect(self._on_profile_selected)
        
        # OS Image selection (new!)
        self.os_image_widget.images_updated.connect(self._on_os_images_updated)
        
        # File selection
        self.files_widget.files_updated.connect(self._on_files_updated)
    
    def _refresh_devices(self):
        """Refresh USB device list"""
        try:
            if self.disk_manager:
                devices = self.disk_manager.get_removable_drives()
            else:
                devices = self.storage_builder.get_suitable_devices()
            
            self.device_list.clear()
            
            for device in devices:
                size_gb = device.size_bytes / (1024**3)
                item_text = f"{device.name} - {size_gb:.1f} GB"
                
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, device)
                
                # Color code by health
                if device.health_status == "Good":
                    item.setBackground(QColor("#28A745"))
                else:
                    item.setBackground(QColor("#FF6B35"))
                
                self.device_list.addItem(item)
            
            self.logger.info(f"Found {len(devices)} USB devices")
            
        except Exception as e:
            self.logger.error(f"Error refreshing devices: {e}")
    
    def _on_recipe_selected(self, recipe_name: str):
        """Handle recipe selection"""
        self.selected_recipe = recipe_name
        
        # Update required files for both OS Image Manager and traditional file selection
        recipes = self.storage_builder.get_available_recipes()
        recipe = next((r for r in recipes if r.name == recipe_name), None)
        
        if recipe:
            # Set required files for OS Image Manager (primary)
            self.os_image_widget.set_required_files(recipe.required_files)
            
            # Set only optional files for traditional file selection (secondary)
            self.files_widget.set_required_files([], recipe.optional_files)
        
        self._update_build_button()
    
    def _on_profile_selected(self, profile_name: str):
        """Handle hardware profile selection"""
        self.selected_profile = profile_name
        self._update_build_button()
    
    def _on_os_images_updated(self, os_images: Dict[str, str]):
        """Handle OS image selection updates"""
        # Merge OS images with traditional files
        self.source_files.update(os_images)
        self._update_build_button()
        self.logger.info(f"OS images updated: {len(os_images)} files ready")
    
    def _on_files_updated(self, files: Dict[str, str]):
        """Handle traditional file selection updates"""
        # Merge traditional files with OS images
        self.source_files.update(files)
        self._update_build_button()
    
    def _on_device_selected(self):
        """Handle device selection"""
        current_item = self.device_list.currentItem()
        if current_item:
            device = current_item.data(Qt.ItemDataRole.UserRole)
            self.selected_device = device.path
            self._update_device_details(device)
            self._update_build_button()
    
    def _update_device_details(self, device: DiskInfo):
        """Update device details display"""
        self.device_path_label.setText(device.path)
        
        size_gb = device.size_bytes / (1024**3)
        self.device_size_label.setText(f"{size_gb:.1f} GB")
        
        self.device_model_label.setText(f"{device.vendor} {device.model}")
        self.device_health_label.setText(device.health_status)
    
    def _update_build_button(self):
        """Update build button state"""
        # Check basic selections
        basic_ready = all([
            self.selected_recipe,
            self.selected_profile,
            self.selected_device
        ])
        
        # Check if OS images are ready
        os_images_ready = self.os_image_widget.is_ready()
        
        # Check if traditional files are ready (now only optional files)
        traditional_files_ready = self.files_widget.is_ready()
        
        # Overall readiness: basic selections + OS images ready
        # Traditional files are now optional since required files come from OS images
        ready = basic_ready and os_images_ready
        
        self.build_btn.setEnabled(ready)
        
        # Update status message
        if ready:
            status_msg = "✅ Ready to build USB drive"
        elif not basic_ready:
            missing = []
            if not self.selected_recipe: missing.append("recipe")
            if not self.selected_profile: missing.append("hardware profile")
            if not self.selected_device: missing.append("target device")
            status_msg = f"Please select: {', '.join(missing)}"
        elif not os_images_ready:
            status_msg = "⏳ Waiting for OS images to be assigned and verified"
        else:
            status_msg = "⚙️ Ready (some optional files may be missing)"
        
        # Update progress widget with status
        if hasattr(self, 'progress_widget'):
            # This will show the status in the progress panel
            pass
    
    def _start_build(self):
        """Start USB build process with comprehensive safety validation"""
        try:
            # Validate selections with proper type checking
            if not self.selected_recipe or not self.selected_device or not self.selected_profile:
                QMessageBox.warning(self, "Missing Selection", "Please complete all selections before building.")
                return
            
            self.progress_widget.add_log_message("INFO", "Starting comprehensive safety validation...")
            
            # CRITICAL: Comprehensive Device Safety Validation (matching CLI)
            # Type-safe device validation
            if self.selected_device is None:
                QMessageBox.warning(self, "Device Selection Required", "Please select a device before building.")
                return
            device_risk = self.safety_validator.validate_device_safety(self.selected_device)
            
            if device_risk.overall_risk == ValidationResult.BLOCKED:
                QMessageBox.critical(
                    self, "🚫 OPERATION BLOCKED FOR SAFETY 🚫",
                    f"Device: {self.selected_device}\n"
                    f"Size: {device_risk.size_gb:.1f}GB\n\n"
                    f"Risk Factors:\n" + "\n".join([f"• {factor}" for factor in device_risk.risk_factors]) + 
                    f"\n\nThis device is not safe to use for USB creation."
                )
                self.progress_widget.add_log_message("ERROR", f"BLOCKED device: {self.selected_device}")
                return
            
            if device_risk.overall_risk == ValidationResult.DANGEROUS:
                QMessageBox.critical(
                    self, "⚠️ DANGEROUS DEVICE DETECTED ⚠️",
                    f"Device: {self.selected_device} ({device_risk.size_gb:.1f}GB)\n\n"
                    f"Risk Factors:\n" + "\n".join([f"• {factor}" for factor in device_risk.risk_factors]) + 
                    f"\n\nThis operation could destroy important data.\n\n"
                    f"OPERATION BLOCKED FOR SAFETY"
                )
                self.progress_widget.add_log_message("ERROR", f"DANGEROUS device blocked: {self.selected_device}")
                return
            
            # Validate prerequisites
            prereq_checks = self.safety_validator.validate_prerequisites()
            blocked_checks = [check for check in prereq_checks if check.result == ValidationResult.BLOCKED]
            if blocked_checks:
                error_msg = "❌ MISSING PREREQUISITES:\n" + "\n".join([f"• {check.name}: {check.message}" for check in blocked_checks])
                QMessageBox.critical(self, "Missing Prerequisites", error_msg)
                for check in blocked_checks:
                    self.progress_widget.add_log_message("ERROR", f"Missing prerequisite: {check.name}")
                return
            
            # Validate source files
            source_checks = self.safety_validator.validate_source_files(self.source_files)
            blocked_sources = [check for check in source_checks if check.result == ValidationResult.BLOCKED]
            if blocked_sources:
                error_msg = "❌ SOURCE FILE ISSUES:\n" + "\n".join([f"• {check.name}: {check.message}" for check in blocked_sources])
                QMessageBox.critical(self, "Source File Issues", error_msg)
                for check in blocked_sources:
                    self.progress_widget.add_log_message("ERROR", f"Source file issue: {check.name}")
                return
            
            self.progress_widget.add_log_message("INFO", "✅ All safety validations passed")
            
            # Handle WARNING devices with typed confirmation (matching CLI)
            if device_risk.overall_risk == ValidationResult.WARNING:
                warning_msg = (
                    f"⚠️ WARNING: Device has risk factors\n\n"
                    f"Device: {self.selected_device} ({device_risk.size_gb:.1f}GB)\n\n"
                    f"Risk Factors:\n" + "\n".join([f"• {factor}" for factor in device_risk.risk_factors]) + 
                    f"\n\nThis operation will PERMANENTLY ERASE all data.\n\n"
                    f"To confirm, type the device name: {os.path.basename(self.selected_device) if self.selected_device else 'unknown'}"
                )
                
                text, ok = QInputDialog.getText(self, "⚠️ Confirm Risky Operation", warning_msg)
                device_name = os.path.basename(self.selected_device) if self.selected_device else 'unknown'
                if not ok or text != device_name:
                    self.progress_widget.add_log_message("INFO", "Operation cancelled - failed device name confirmation")
                    return
            
            # Final comprehensive confirmation dialog
            device_basename = os.path.basename(self.selected_device) if self.selected_device else 'unknown'
            final_confirmation = (
                f"🚨 FINAL WARNING - POINT OF NO RETURN 🚨\n\n"
                f"This will PERMANENTLY ERASE ALL DATA on:\n"
                f"Device: {self.selected_device}\n"
                f"Size: {device_risk.size_gb:.1f} GB\n\n"
                f"Recipe: {self.selected_recipe}\n"
                f"Hardware: {self.selected_profile}\n\n"
                f"⚠️ This action CANNOT BE UNDONE ⚠️\n\n"
                f"To proceed, type EXACTLY: {device_basename}"
            )
            
            text, ok = QInputDialog.getText(self, "🚨 Final Confirmation Required", final_confirmation)
            if not ok or text != device_basename:
                self.progress_widget.add_log_message("INFO", "Operation cancelled - failed final confirmation")
                return
            
            self.progress_widget.add_log_message("INFO", f"User confirmed operation on {self.selected_device}")
            
            # Setup progress monitoring with type-safe parameters
            # At this point we've already validated these are not None
            assert self.selected_recipe is not None
            assert self.selected_device is not None
            assert self.selected_profile is not None
            
            builder = self.storage_builder.create_deployment_usb(
                self.selected_recipe,
                self.selected_device,
                self.selected_profile,
                self.source_files
            )
            
            # Connect signals
            builder.progress_updated.connect(self.progress_widget.update_progress)
            builder.log_message.connect(self.progress_widget.add_log_message)
            builder.operation_completed.connect(self._on_build_completed)
            
            # Update UI state
            self.build_btn.setEnabled(False)
            self.cancel_btn.setEnabled(True)
            
            self.progress_widget.add_log_message("INFO", "✅ Starting USB build process with all safety checks passed")
            self.logger.info("Started USB build process with comprehensive safety validation")
            
        except Exception as e:
            self.logger.error(f"Error starting build: {e}")
            self.progress_widget.add_log_message("ERROR", f"Build start error: {str(e)}")
            QMessageBox.critical(self, "Build Error", f"Failed to start build: {str(e)}")
    
    def _cancel_build(self):
        """Cancel current build"""
        try:
            if hasattr(self.storage_builder, 'builder'):
                self.storage_builder.builder.cancel_build()
            
            self.build_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
            
            self.logger.info("Build cancelled by user")
            
        except Exception as e:
            self.logger.error(f"Error cancelling build: {e}")
    
    def _on_build_completed(self, success: bool, message: str):
        """Handle build completion"""
        # Update UI state
        self.build_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
        # Show result
        if success:
            QMessageBox.information(self, "Build Complete", message)
            self.logger.info(f"Build completed successfully: {message}")
        else:
            QMessageBox.critical(self, "Build Failed", message)
            self.logger.error(f"Build failed: {message}")