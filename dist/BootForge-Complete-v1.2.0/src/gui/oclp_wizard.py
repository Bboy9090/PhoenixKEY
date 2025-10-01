"""
BootForge OCLP Integration GUI Wizard
Interactive wizard for Mac model detection and OCLP configuration
"""

import logging
import platform
from typing import Dict, List, Optional, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QProgressBar, QGroupBox, QCheckBox, QComboBox, QTableWidget, QTableWidgetItem,
    QTabWidget, QWidget, QScrollArea, QFrame, QMessageBox, QStackedWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QIcon

from src.core.hardware_detector import HardwareDetector, DetectedHardware
from src.core.oclp_integration import OCLPIntegration, OCLPCompatibility, OCLPBuildStatus
from src.core.oclp_safety_controller import OCLPSafetyController, OCLPRiskLevel
from src.core.hardware_profiles import (
    is_mac_oclp_compatible, get_recommended_macos_version_for_model,
    create_mac_hardware_profile, get_mac_oclp_requirements
)
from src.core.providers.macos_provider import MacOSProvider


class MacModelDetectionWorker(QThread):
    """Worker thread for Mac model detection"""
    
    detection_completed = pyqtSignal(object)  # DetectedHardware
    detection_failed = pyqtSignal(str)
    progress_updated = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.hardware_detector = HardwareDetector()
    
    def run(self):
        try:
            self.progress_updated.emit("Detecting Mac hardware...")
            
            # Detect hardware with enhanced Mac-specific detection
            detected_hardware = self.hardware_detector.detect_hardware()
            
            self.progress_updated.emit("Analyzing Mac model compatibility...")
            
            # Enhanced detection for Mac-specific information
            if platform.system() == "Darwin":
                import subprocess
                
                # Get Mac model identifier
                try:
                    result = subprocess.run(
                        ["system_profiler", "SPHardwareDataType"],
                        capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0:
                        for line in result.stdout.split('\\n'):
                            if "Model Identifier:" in line:
                                model_id = line.split(":")[1].strip()
                                detected_hardware.system_model = model_id
                                break
                except Exception as e:
                    logging.warning(f"Failed to get Mac model identifier: {e}")
            
            self.detection_completed.emit(detected_hardware)
            
        except Exception as e:
            self.detection_failed.emit(str(e))


class OCLPConfigurationWidget(QWidget):
    """Widget for OCLP configuration and patch selection"""
    
    def __init__(self, hardware: DetectedHardware, parent=None):
        super().__init__(parent)
        self.hardware = hardware
        self.oclp_requirements = {}
        self.recommended_patches = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Hardware Information Section
        hardware_group = QGroupBox("Detected Mac Hardware")
        hardware_layout = QVBoxLayout()
        
        if self.hardware.system_model:
            model_label = QLabel(f"Model: {self.hardware.system_model}")
            model_label.setFont(QFont("", 10, QFont.Weight.Bold))
            hardware_layout.addWidget(model_label)
            
            # Get hardware profile for display
            try:
                hardware_profile = create_mac_hardware_profile(self.hardware.system_model)
                display_name_label = QLabel(f"Name: {hardware_profile.name}")
                hardware_layout.addWidget(display_name_label)
                
                # Get OCLP requirements
                self.oclp_requirements = get_mac_oclp_requirements(
                    self.hardware.system_model, "13.0"  # Default to Ventura
                )
                
            except Exception as e:
                error_label = QLabel(f"Error getting hardware info: {e}")
                error_label.setStyleSheet("color: red;")
                hardware_layout.addWidget(error_label)
        else:
            no_model_label = QLabel("Mac model not detected")
            no_model_label.setStyleSheet("color: red;")
            hardware_layout.addWidget(no_model_label)
        
        hardware_group.setLayout(hardware_layout)
        layout.addWidget(hardware_group)
        
        # OCLP Compatibility Section
        compat_group = QGroupBox("OCLP Compatibility")
        compat_layout = QVBoxLayout()
        
        if self.hardware.system_model and is_mac_oclp_compatible(self.hardware.system_model):
            compat_level = self.oclp_requirements.get("oclp_compatibility", "unknown")
            compat_label = QLabel(f"Compatibility: {compat_level.replace('_', ' ').title()}")
            
            # Style based on compatibility level
            if compat_level == "fully_supported":
                compat_label.setStyleSheet("color: green; font-weight: bold;")
            elif compat_level == "partially_supported":
                compat_label.setStyleSheet("color: orange; font-weight: bold;")
            elif compat_level == "experimental":
                compat_label.setStyleSheet("color: red; font-weight: bold;")
            
            compat_layout.addWidget(compat_label)
            
            # Recommended macOS version
            recommended_version = get_recommended_macos_version_for_model(self.hardware.system_model)
            if recommended_version:
                version_label = QLabel(f"Recommended macOS: {recommended_version}")
                compat_layout.addWidget(version_label)
        else:
            not_compat_label = QLabel("This Mac is not compatible with OCLP")
            not_compat_label.setStyleSheet("color: red; font-weight: bold;")
            compat_layout.addWidget(not_compat_label)
        
        compat_group.setLayout(compat_layout)
        layout.addWidget(compat_group)
        
        # Patch Requirements Section
        if self.oclp_requirements:
            patches_group = QGroupBox("Required Patches")
            patches_layout = QVBoxLayout()
            
            # Create patch table
            patch_table = QTableWidget()
            patch_types = [
                ("Graphics", "graphics_patches"),
                ("Audio", "audio_patches"), 
                ("WiFi/Bluetooth", "wifi_bluetooth_patches"),
                ("USB", "usb_patches")
            ]
            
            patch_table.setColumnCount(3)
            patch_table.setHorizontalHeaderLabels(["Patch Type", "Required", "Description"])
            patch_table.setRowCount(len(patch_types))
            
            for row, (patch_name, patch_key) in enumerate(patch_types):
                # Patch type
                patch_table.setItem(row, 0, QTableWidgetItem(patch_name))
                
                # Required status
                patches = self.oclp_requirements.get(patch_key, [])
                required = "Yes" if patches else "No"
                required_item = QTableWidgetItem(required)
                if patches:
                    required_item.setBackground(Qt.GlobalColor.yellow)
                patch_table.setItem(row, 1, required_item)
                
                # Description
                if patches:
                    desc = f"{len(patches)} patches required"
                else:
                    desc = "No patches needed"
                patch_table.setItem(row, 2, QTableWidgetItem(desc))
            
            patch_table.resizeColumnsToContents()
            patches_layout.addWidget(patch_table)
            
            # SIP Requirements
            sip_req = self.oclp_requirements.get("sip_requirements")
            if sip_req == "disabled":
                sip_warning = QLabel("⚠️ System Integrity Protection (SIP) must be disabled")
                sip_warning.setStyleSheet("color: red; font-weight: bold; background: yellow; padding: 5px;")
                patches_layout.addWidget(sip_warning)
            
            patches_group.setLayout(patches_layout)
            layout.addWidget(patches_group)
        
        # Notes Section
        if self.oclp_requirements.get("notes"):
            notes_group = QGroupBox("Important Notes")
            notes_layout = QVBoxLayout()
            
            notes_text = QTextEdit()
            notes_text.setPlainText("\\n".join(self.oclp_requirements["notes"]))
            notes_text.setReadOnly(True)
            notes_text.setMaximumHeight(100)
            notes_layout.addWidget(notes_text)
            
            notes_group.setLayout(notes_layout)
            layout.addWidget(notes_group)
        
        self.setLayout(layout)


class OCLPWizard(QDialog):
    """Main OCLP configuration wizard dialog"""
    
    oclp_configured = pyqtSignal(dict)  # OCLP configuration
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.detected_hardware: Optional[DetectedHardware] = None
        self.oclp_integration = OCLPIntegration()
        self.safety_controller = OCLPSafetyController()
        
        # Setup UI
        self.setWindowTitle("BootForge - OCLP Configuration Wizard")
        self.setModal(True)
        self.resize(800, 600)
        
        self.init_ui()
        self.setup_connections()
        
        # Start hardware detection immediately
        self.start_hardware_detection()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Title
        title_label = QLabel("OpenCore Legacy Patcher Integration")
        title_font = QFont("", 16, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel("Configure OCLP settings for your Mac hardware")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("color: gray; margin-bottom: 20px;")
        layout.addWidget(subtitle_label)
        
        # Stacked widget for different wizard pages
        self.stacked_widget = QStackedWidget()
        
        # Page 1: Hardware Detection
        self.detection_page = self.create_detection_page()
        self.stacked_widget.addWidget(self.detection_page)
        
        # Page 2: OCLP Configuration (created after detection)
        self.config_page = None
        
        # Page 3: Build Progress (created when building)
        self.build_page = None
        
        layout.addWidget(self.stacked_widget)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        self.back_button = QPushButton("Back")
        self.back_button.setEnabled(False)
        button_layout.addWidget(self.back_button)
        
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        button_layout.addWidget(self.cancel_button)
        
        self.next_button = QPushButton("Next")
        self.next_button.setEnabled(False)
        button_layout.addWidget(self.next_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def create_detection_page(self) -> QWidget:
        """Create hardware detection page"""
        page = QWidget()
        layout = QVBoxLayout()
        
        # Detection progress
        self.detection_label = QLabel("Detecting Mac hardware...")
        layout.addWidget(self.detection_label)
        
        self.detection_progress = QProgressBar()
        self.detection_progress.setRange(0, 0)  # Indeterminate progress
        layout.addWidget(self.detection_progress)
        
        # Detection results area (initially hidden)
        self.detection_results = QTextEdit()
        self.detection_results.setReadOnly(True)
        self.detection_results.setVisible(False)
        layout.addWidget(self.detection_results)
        
        page.setLayout(layout)
        return page
    
    def setup_connections(self):
        """Setup signal connections"""
        self.cancel_button.clicked.connect(self.reject)
        self.next_button.clicked.connect(self.next_page)
        self.back_button.clicked.connect(self.previous_page)
        
        # Safety controller connections
        self.safety_controller.consent_required.connect(self.show_consent_dialog)
    
    def start_hardware_detection(self):
        """Start Mac hardware detection"""
        self.detection_worker = MacModelDetectionWorker()
        self.detection_worker.detection_completed.connect(self.on_detection_completed)
        self.detection_worker.detection_failed.connect(self.on_detection_failed)
        self.detection_worker.progress_updated.connect(self.detection_label.setText)
        self.detection_worker.start()
    
    def on_detection_completed(self, hardware: DetectedHardware):
        """Handle successful hardware detection"""
        self.detected_hardware = hardware
        
        # Update detection UI
        self.detection_progress.setRange(0, 1)
        self.detection_progress.setValue(1)
        
        if hardware.system_model:
            self.detection_label.setText(f"✅ Detected: {hardware.system_model}")
            
            # Show detection results
            results_text = f"Mac Model: {hardware.system_model}\\n"
            results_text += f"Architecture: {hardware.architecture}\\n"
            results_text += f"CPU: {hardware.cpu_info.get('name', 'Unknown')}\\n"
            results_text += f"Memory: {hardware.memory_total_gb:.1f} GB\\n"
            
            # Check OCLP compatibility
            if is_mac_oclp_compatible(hardware.system_model):
                results_text += "\\n✅ OCLP Compatible\\n"
                self.next_button.setEnabled(True)
            else:
                results_text += "\\n❌ Not OCLP Compatible\\n"
                results_text += "This Mac may be natively supported by newer macOS versions.\\n"
            
            self.detection_results.setPlainText(results_text)
            self.detection_results.setVisible(True)
        else:
            self.detection_label.setText("❌ Could not detect Mac model")
            self.detection_results.setPlainText("Mac model detection failed. OCLP configuration is not possible.")
            self.detection_results.setVisible(True)
    
    def on_detection_failed(self, error: str):
        """Handle hardware detection failure"""
        self.detection_progress.setRange(0, 1)
        self.detection_progress.setValue(0)
        self.detection_label.setText(f"❌ Detection failed: {error}")
        
        self.detection_results.setPlainText(f"Hardware detection failed: {error}")
        self.detection_results.setVisible(True)
    
    def next_page(self):
        """Navigate to next wizard page"""
        current_index = self.stacked_widget.currentIndex()
        
        if current_index == 0:  # Detection -> Configuration
            self.show_configuration_page()
        elif current_index == 1:  # Configuration -> Build
            self.start_oclp_build()
    
    def previous_page(self):
        """Navigate to previous wizard page"""
        current_index = self.stacked_widget.currentIndex()
        
        if current_index > 0:
            self.stacked_widget.setCurrentIndex(current_index - 1)
            self.update_button_states()
    
    def show_configuration_page(self):
        """Show OCLP configuration page"""
        if not self.config_page and self.detected_hardware:
            self.config_page = OCLPConfigurationWidget(self.detected_hardware)
            self.stacked_widget.addWidget(self.config_page)
        
        if self.config_page:
            self.stacked_widget.setCurrentWidget(self.config_page)
            self.next_button.setText("Build OCLP")
            self.back_button.setEnabled(True)
            self.update_button_states()
    
    def start_oclp_build(self):
        """Start OCLP build process with safety checks"""
        if not self.detected_hardware or not self.detected_hardware.system_model:
            QMessageBox.warning(self, "Error", "No Mac hardware detected for OCLP build")
            return
        
        # Perform safety assessment
        risk_assessment = self.safety_controller.assess_oclp_risks(
            model_id=self.detected_hardware.system_model,
            macos_version="13.0",  # Default version
            requested_patches=[]
        )
        
        if risk_assessment.user_consent_required:
            # Request user consent
            def consent_callback(consented: bool):
                if consented:
                    self._proceed_with_build()
                else:
                    self.logger.info("User declined OCLP build due to risks")
            
            self.safety_controller.request_user_consent(
                "OCLP Build Operation",
                risk_assessment,
                consent_callback
            )
        else:
            self._proceed_with_build()
    
    def _proceed_with_build(self):
        """Proceed with OCLP build after consent"""
        # Create build progress page
        self.build_page = self.create_build_page()
        self.stacked_widget.addWidget(self.build_page)
        self.stacked_widget.setCurrentWidget(self.build_page)
        
        # Update buttons
        self.next_button.setEnabled(False)
        self.back_button.setEnabled(False)
        
        # Configure and start OCLP build
        if self.oclp_integration.configure_for_hardware(
            model=self.detected_hardware.system_model,
            macos_version="13.0"
        ):
            self.oclp_integration.build_oclp_for_hardware()
        else:
            QMessageBox.critical(self, "Error", "Failed to configure OCLP for detected hardware")
    
    def create_build_page(self) -> QWidget:
        """Create OCLP build progress page"""
        page = QWidget()
        layout = QVBoxLayout()
        
        # Build status
        self.build_status_label = QLabel("Preparing OCLP build...")
        layout.addWidget(self.build_status_label)
        
        # Progress bar
        self.build_progress = QProgressBar()
        layout.addWidget(self.build_progress)
        
        # Build log
        build_log_group = QGroupBox("Build Log")
        log_layout = QVBoxLayout()
        
        self.build_log = QTextEdit()
        self.build_log.setReadOnly(True)
        self.build_log.setFont(QFont("Courier", 9))
        log_layout.addWidget(self.build_log)
        
        build_log_group.setLayout(log_layout)
        layout.addWidget(build_log_group)
        
        page.setLayout(layout)
        return page
    
    def show_consent_dialog(self, title: str, risk_assessment, callback: callable):
        """Show user consent dialog for OCLP risks"""
        dialog = QMessageBox(self)
        dialog.setWindowTitle(title)
        dialog.setIcon(QMessageBox.Icon.Warning)
        
        # Build detailed message
        message_parts = [
            f"Risk Level: {risk_assessment.overall_risk.value.title()}",
            "",
            "Risk Factors:"
        ]
        
        for risk_factor in risk_assessment.risk_factors[:5]:  # Limit to first 5
            message_parts.append(f"• {risk_factor}")
        
        if risk_assessment.warnings:
            message_parts.extend(["", "Warnings:"])
            for warning in risk_assessment.warnings[:3]:  # Limit to first 3
                message_parts.append(f"• {warning}")
        
        message_parts.extend([
            "",
            f"Warranty Impact: {'Yes' if risk_assessment.warranty_implications else 'No'}",
            f"Reversibility: {risk_assessment.reversibility_level.replace('_', ' ').title()}",
            "",
            "Do you want to proceed with this OCLP operation?"
        ])
        
        dialog.setText("\\n".join(message_parts))
        dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        dialog.setDefaultButton(QMessageBox.StandardButton.No)
        
        # Show dialog and handle response
        result = dialog.exec()
        callback(result == QMessageBox.StandardButton.Yes)
    
    def update_button_states(self):
        """Update button enabled states based on current page"""
        current_index = self.stacked_widget.currentIndex()
        
        if current_index == 0:  # Detection page
            self.back_button.setEnabled(False)
            self.next_button.setEnabled(bool(
                self.detected_hardware and 
                self.detected_hardware.system_model and 
                is_mac_oclp_compatible(self.detected_hardware.system_model)
            ))
        elif current_index == 1:  # Configuration page
            self.back_button.setEnabled(True)
            self.next_button.setEnabled(True)
            self.next_button.setText("Build OCLP")
        else:  # Build page
            self.back_button.setEnabled(False)
            self.next_button.setEnabled(False)