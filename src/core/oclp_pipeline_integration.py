"""
BootForge OCLP Pipeline Integration
Integration helpers and utilities for connecting the OCLP automation pipeline
with BootForge's existing GUI and core systems
"""

import logging
from typing import Dict, List, Optional, Callable, Any
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal
from dataclasses import dataclass

from src.core.oclp_automation_pipeline import (
    OCLPAutomationPipeline, PipelineConfiguration, PipelineProgress, 
    PipelineResult, AutomationMode, PipelineStage
)
from src.core.hardware_detector import HardwareDetector, DetectedHardware
from src.core.disk_manager import DiskManager, DiskInfo
import logging

def get_logger(name):
    return logging.getLogger(name)


@dataclass
class PipelineUIState:
    """UI state information for the OCLP pipeline"""
    is_running: bool = False
    can_start: bool = True
    can_cancel: bool = False
    can_pause: bool = False
    
    # Configuration state
    macos_installer_selected: bool = False
    target_device_selected: bool = False
    configuration_complete: bool = False
    
    # Progress state
    current_stage_name: str = ""
    overall_progress: float = 0.0
    stage_progress: float = 0.0
    
    # Messages
    status_message: str = "Ready to start OCLP deployment"
    last_error: Optional[str] = None
    warnings_count: int = 0


class OCLPPipelineManager(QObject):
    """
    Manager class for OCLP automation pipeline integration with BootForge GUI
    Provides a simplified interface for GUI components to interact with the pipeline
    """
    
    # Qt Signals for GUI integration
    pipeline_state_changed = pyqtSignal(object)  # PipelineUIState
    hardware_detected = pyqtSignal(object)       # DetectedHardware
    compatibility_checked = pyqtSignal(bool, str) # is_compatible, message
    usb_devices_found = pyqtSignal(list)         # List[DiskInfo]
    user_action_required = pyqtSignal(str, dict) # action_type, options
    
    # Progress signals
    pipeline_progress = pyqtSignal(object)       # PipelineProgress
    stage_progress = pyqtSignal(str, float)      # stage_name, progress
    log_message = pyqtSignal(str, str)           # level, message
    
    # Completion signals
    pipeline_succeeded = pyqtSignal(object)      # PipelineResult
    pipeline_failed = pyqtSignal(str)           # error_message
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
        
        # Core components
        self.hardware_detector = HardwareDetector()
        self.disk_manager = DiskManager()
        
        # Pipeline state
        self.current_pipeline: Optional[OCLPAutomationPipeline] = None
        self.ui_state = PipelineUIState()
        self.detected_hardware: Optional[DetectedHardware] = None
        self.available_usb_devices: List[DiskInfo] = []
        
        # Configuration
        self.pipeline_config = PipelineConfiguration()
        
        self.logger.info("OCLP Pipeline Manager initialized")
    
    def detect_hardware(self) -> bool:
        """Detect current Mac hardware"""
        try:
            self.logger.info("Starting hardware detection...")
            
            self.detected_hardware = self.hardware_detector.detect_hardware()
            if not self.detected_hardware:
                self._update_ui_state(status_message="Hardware detection failed", last_error="Could not detect system hardware")
                return False
            
            # Emit hardware detected signal
            self.hardware_detected.emit(self.detected_hardware)
            
            # Check if this is a Mac
            if self.detected_hardware.platform.lower() != "mac" and self.detected_hardware.system_manufacturer != "Apple":
                message = f"This is not a Mac system (detected: {self.detected_hardware.platform})"
                self._update_ui_state(status_message=message, last_error=message)
                self.compatibility_checked.emit(False, message)
                return False
            
            # Success
            message = f"Mac detected: {self.detected_hardware.get_summary()}"
            self._update_ui_state(status_message=message)
            self.compatibility_checked.emit(True, message)
            
            return True
            
        except Exception as e:
            error_msg = f"Hardware detection failed: {e}"
            self.logger.error(error_msg)
            self._update_ui_state(status_message="Hardware detection error", last_error=error_msg)
            return False
    
    def scan_usb_devices(self) -> List[DiskInfo]:
        """Scan for suitable USB devices"""
        try:
            self.logger.info("Scanning for USB devices...")
            
            # Get all removable drives
            all_devices = self.disk_manager.get_removable_drives()
            
            # Filter for suitable devices (minimum 16GB)
            min_size = 16 * 1024 * 1024 * 1024  # 16GB in bytes
            suitable_devices = [d for d in all_devices if d.size_bytes >= min_size]
            
            self.available_usb_devices = suitable_devices
            self.usb_devices_found.emit(suitable_devices)
            
            if suitable_devices:
                message = f"Found {len(suitable_devices)} suitable USB device(s)"
                self._update_ui_state(status_message=message)
            else:
                message = "No suitable USB devices found (minimum 16GB required)"
                self._update_ui_state(status_message=message, last_error=message)
            
            return suitable_devices
            
        except Exception as e:
            error_msg = f"USB device scan failed: {e}"
            self.logger.error(error_msg)
            self._update_ui_state(status_message="USB scan error", last_error=error_msg)
            return []
    
    def configure_pipeline(self, 
                          macos_installer_path: Optional[Path] = None,
                          target_usb_device: Optional[str] = None,
                          target_macos_version: Optional[str] = None,
                          automation_mode: AutomationMode = AutomationMode.FULLY_AUTOMATIC) -> bool:
        """Configure the OCLP automation pipeline"""
        try:
            # Update pipeline configuration
            if macos_installer_path:
                if not macos_installer_path.exists():
                    error_msg = f"macOS installer not found: {macos_installer_path}"
                    self._update_ui_state(last_error=error_msg)
                    return False
                self.pipeline_config.macos_installer_path = macos_installer_path
                self.ui_state.macos_installer_selected = True
            
            if target_usb_device:
                # Validate USB device
                valid_device = any(d.device_path == target_usb_device for d in self.available_usb_devices)
                if not valid_device:
                    error_msg = f"Invalid USB device selected: {target_usb_device}"
                    self._update_ui_state(last_error=error_msg)
                    return False
                self.pipeline_config.target_usb_device = target_usb_device
                self.ui_state.target_device_selected = True
            
            if target_macos_version:
                self.pipeline_config.target_macos_version = target_macos_version
            
            # Update automation mode
            self.pipeline_config.automation_mode = automation_mode
            
            # Check if configuration is complete
            self.ui_state.configuration_complete = (
                self.ui_state.macos_installer_selected and 
                self.ui_state.target_device_selected and
                self.detected_hardware is not None
            )
            
            self.ui_state.can_start = self.ui_state.configuration_complete and not self.ui_state.is_running
            
            self._update_ui_state(status_message="Pipeline configured successfully")
            return True
            
        except Exception as e:
            error_msg = f"Pipeline configuration failed: {e}"
            self.logger.error(error_msg)
            self._update_ui_state(last_error=error_msg)
            return False
    
    def start_pipeline(self) -> bool:
        """Start the OCLP automation pipeline"""
        try:
            if not self.ui_state.configuration_complete:
                error_msg = "Pipeline configuration incomplete"
                self._update_ui_state(last_error=error_msg)
                return False
            
            if self.ui_state.is_running:
                self.logger.warning("Pipeline is already running")
                return False
            
            self.logger.info("Starting OCLP automation pipeline...")
            
            # Create new pipeline instance
            self.current_pipeline = OCLPAutomationPipeline(self.pipeline_config)
            
            # Connect signals
            self._connect_pipeline_signals()
            
            # Update UI state
            self._update_ui_state(
                is_running=True,
                can_start=False,
                can_cancel=True,
                status_message="Starting OCLP automation pipeline..."
            )
            
            # Start pipeline
            self.current_pipeline.start()
            
            return True
            
        except Exception as e:
            error_msg = f"Failed to start pipeline: {e}"
            self.logger.error(error_msg)
            self._update_ui_state(last_error=error_msg)
            return False
    
    def cancel_pipeline(self) -> bool:
        """Cancel the running pipeline"""
        try:
            if not self.current_pipeline or not self.ui_state.is_running:
                return False
            
            self.logger.info("Cancelling OCLP automation pipeline...")
            
            self.current_pipeline.cancel_pipeline()
            
            self._update_ui_state(
                status_message="Cancelling pipeline...",
                can_cancel=False
            )
            
            return True
            
        except Exception as e:
            error_msg = f"Failed to cancel pipeline: {e}"
            self.logger.error(error_msg)
            return False
    
    def get_current_progress(self) -> Optional[PipelineProgress]:
        """Get current pipeline progress"""
        if self.current_pipeline:
            return self.current_pipeline.get_current_progress()
        return None
    
    def get_pipeline_result(self) -> Optional[PipelineResult]:
        """Get pipeline result (if completed)"""
        if self.current_pipeline:
            return self.current_pipeline.get_pipeline_result()
        return None
    
    def _connect_pipeline_signals(self):
        """Connect pipeline signals to manager slots"""
        if not self.current_pipeline:
            return
        
        self.current_pipeline.progress_updated.connect(self._handle_pipeline_progress)
        self.current_pipeline.stage_started.connect(self._handle_stage_started)
        self.current_pipeline.stage_completed.connect(self._handle_stage_completed)
        self.current_pipeline.log_message.connect(self._handle_log_message)
        self.current_pipeline.user_input_required.connect(self._handle_user_input_required)
        self.current_pipeline.pipeline_completed.connect(self._handle_pipeline_completed)
        self.current_pipeline.pipeline_failed.connect(self._handle_pipeline_failed)
    
    def _handle_pipeline_progress(self, progress: PipelineProgress):
        """Handle pipeline progress updates"""
        # Update UI state
        self.ui_state.current_stage_name = progress.stage_name
        self.ui_state.overall_progress = progress.overall_progress
        self.ui_state.stage_progress = progress.stage_progress
        self.ui_state.status_message = progress.detailed_status or progress.stage_name
        self.ui_state.warnings_count = len(progress.warnings)
        
        # Emit signals
        self.pipeline_progress.emit(progress)
        self.stage_progress.emit(progress.stage_name, progress.stage_progress)
        self._emit_ui_state()
    
    def _handle_stage_started(self, stage_name: str, stage_number: int):
        """Handle stage started"""
        self.logger.info(f"Pipeline stage started: {stage_name} ({stage_number})")
        self._update_ui_state(
            current_stage_name=stage_name,
            status_message=f"Starting {stage_name}..."
        )
    
    def _handle_stage_completed(self, stage_name: str, success: bool):
        """Handle stage completed"""
        if success:
            self.logger.info(f"Pipeline stage completed: {stage_name}")
        else:
            self.logger.error(f"Pipeline stage failed: {stage_name}")
    
    def _handle_log_message(self, level: str, message: str):
        """Handle log messages from pipeline"""
        self.log_message.emit(level, message)
        
        # Update UI state for errors
        if level == "ERROR":
            self.ui_state.last_error = message
            self._emit_ui_state()
    
    def _handle_user_input_required(self, input_type: str, options: dict):
        """Handle user input requirements"""
        self.logger.info(f"User input required: {input_type}")
        self._update_ui_state(status_message=f"User input required: {input_type}")
        self.user_action_required.emit(input_type, options)
    
    def _handle_pipeline_completed(self, result: PipelineResult):
        """Handle pipeline completion"""
        self.logger.info(f"Pipeline completed successfully in {result.completion_time:.1f}s")
        
        self._update_ui_state(
            is_running=False,
            can_start=True,
            can_cancel=False,
            overall_progress=100.0,
            status_message=result.summary_message
        )
        
        self.pipeline_succeeded.emit(result)
    
    def _handle_pipeline_failed(self, error_message: str):
        """Handle pipeline failure"""
        self.logger.error(f"Pipeline failed: {error_message}")
        
        self._update_ui_state(
            is_running=False,
            can_start=True,
            can_cancel=False,
            status_message="Pipeline failed",
            last_error=error_message
        )
        
        self.pipeline_failed.emit(error_message)
    
    def _update_ui_state(self, **kwargs):
        """Update UI state and emit signal"""
        for key, value in kwargs.items():
            if hasattr(self.ui_state, key):
                setattr(self.ui_state, key, value)
        
        self._emit_ui_state()
    
    def _emit_ui_state(self):
        """Emit UI state change signal"""
        self.pipeline_state_changed.emit(self.ui_state)
    
    def get_ui_state(self) -> PipelineUIState:
        """Get current UI state"""
        return self.ui_state
    
    def provide_user_input(self, input_type: str, response: dict) -> bool:
        """Provide user input response to pipeline"""
        try:
            if not self.current_pipeline:
                return False
            
            self.current_pipeline.set_user_input_response(response)
            self.logger.info(f"User input provided for: {input_type}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to provide user input: {e}")
            return False


class OCLPQuickDeployment:
    """
    Simplified interface for quick OCLP deployments
    Provides one-click deployment functionality
    """
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.pipeline_manager = OCLPPipelineManager()
    
    def auto_detect_and_deploy(self, 
                              macos_installer_path: Path,
                              target_usb_device: str,
                              progress_callback: Optional[Callable] = None) -> bool:
        """
        Automatically detect Mac hardware and create OCLP deployment
        
        Args:
            macos_installer_path: Path to macOS installer
            target_usb_device: Target USB device path
            progress_callback: Optional progress callback function
            
        Returns:
            True if deployment started successfully
        """
        try:
            # Connect progress callback if provided
            if progress_callback:
                self.pipeline_manager.pipeline_progress.connect(progress_callback)
            
            # Step 1: Detect hardware
            if not self.pipeline_manager.detect_hardware():
                self.logger.error("Hardware detection failed")
                return False
            
            # Step 2: Scan USB devices
            usb_devices = self.pipeline_manager.scan_usb_devices()
            if not usb_devices:
                self.logger.error("No suitable USB devices found")
                return False
            
            # Step 3: Configure pipeline for automatic deployment
            config_success = self.pipeline_manager.configure_pipeline(
                macos_installer_path=macos_installer_path,
                target_usb_device=target_usb_device,
                automation_mode=AutomationMode.FULLY_AUTOMATIC
            )
            
            if not config_success:
                self.logger.error("Pipeline configuration failed")
                return False
            
            # Step 4: Start deployment
            return self.pipeline_manager.start_pipeline()
            
        except Exception as e:
            self.logger.error(f"Auto deployment failed: {e}")
            return False
    
    def get_compatible_mac_models(self) -> List[str]:
        """Get list of Mac models compatible with OCLP"""
        try:
            from src.core.oclp_integration import OCLPCompatibilityDatabase
            db = OCLPCompatibilityDatabase()
            return db.get_all_supported_models()
        except Exception as e:
            self.logger.error(f"Failed to get compatible models: {e}")
            return []
    
    def estimate_deployment_time(self, installer_size_gb: float) -> int:
        """
        Estimate deployment time in minutes
        
        Args:
            installer_size_gb: Size of macOS installer in GB
            
        Returns:
            Estimated time in minutes
        """
        # Base time for pipeline stages (5 minutes)
        base_time = 5
        
        # USB write time (assuming 20 MB/s write speed)
        write_time = (installer_size_gb * 1024) / 20 / 60  # Convert to minutes
        
        # OCLP build time (2-5 minutes depending on complexity)
        oclp_time = 3
        
        total_time = base_time + write_time + oclp_time
        return int(total_time)


# Integration convenience functions

def create_pipeline_manager() -> OCLPPipelineManager:
    """Create a new OCLP pipeline manager"""
    return OCLPPipelineManager()


def create_quick_deployment() -> OCLPQuickDeployment:
    """Create a new quick deployment helper"""
    return OCLPQuickDeployment()


def get_pipeline_stage_descriptions() -> Dict[PipelineStage, str]:
    """Get user-friendly descriptions for pipeline stages"""
    return {
        PipelineStage.INITIALIZING: "Initializing automation pipeline...",
        PipelineStage.HARDWARE_DETECTION: "Detecting Mac hardware and system information",
        PipelineStage.COMPATIBILITY_CHECK: "Checking OCLP compatibility for your Mac model",
        PipelineStage.PATCH_DETERMINATION: "Determining required patches and kexts",
        PipelineStage.OCLP_CONFIGURATION: "Configuring OpenCore Legacy Patcher",
        PipelineStage.USB_PREPARATION: "Preparing USB device for deployment",
        PipelineStage.USB_CREATION: "Creating bootable USB drive",
        PipelineStage.FINALIZATION: "Finalizing deployment and generating reports",
        PipelineStage.COMPLETED: "OCLP deployment completed successfully",
        PipelineStage.FAILED: "Pipeline failed - please check the logs",
        PipelineStage.CANCELLED: "Pipeline was cancelled by user"
    }