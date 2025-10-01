"""
BootForge OCLP Automation Pipeline
Complete end-to-end workflow for automated Mac OCLP deployment
From hardware detection to bootable USB creation in one seamless process
"""

import os
import time
import shutil
import logging
import tempfile
from pathlib import Path
from enum import Enum
from typing import Dict, List, Optional, Tuple, Callable, Any, Union
from dataclasses import dataclass, field

# Optional PyQt6 imports for headless operation support
try:
    from PyQt6.QtCore import QThread, pyqtSignal, QObject
    HAS_PYQT6 = True
except ImportError:
    QThread = object  # Fallback base class
    pyqtSignal = lambda *args: None  # Dummy signal
    QObject = object  # Fallback base class
    HAS_PYQT6 = False

# Import BootForge core modules
from src.core.hardware_detector import HardwareDetector, DetectedHardware, DetectionConfidence
from src.core.oclp_integration import (
    OCLPBootForgeIntegration, OCLPConfiguration, OCLPBuildResult, 
    OCLPCompatibility, OCLPAvailability, detect_mac_and_check_oclp_support
)
from src.core.usb_builder import (
    StorageBuilderEngine, HardwareProfile, DeploymentRecipe, 
    DeploymentType, BuildProgress
)
from src.core.disk_manager import DiskInfo
from src.core.safety_validator import SafetyLevel

# Optional imports with fallbacks
try:
    from src.core.os_image_manager import OSImageManager, OSImageInfo, ImageStatus, DownloadProgress
except ImportError:
    OSImageManager = None
    OSImageInfo = None
    ImageStatus = None
    DownloadProgress = None

try:
    from src.core.config import Config
except ImportError:
    Config = None


class PipelineStage(Enum):
    """OCLP automation pipeline stages"""
    INITIALIZING = "initializing"
    HARDWARE_DETECTION = "hardware_detection"
    COMPATIBILITY_CHECK = "compatibility_check"
    MACOS_ACQUISITION = "macos_acquisition"
    PATCH_DETERMINATION = "patch_determination"
    OCLP_CONFIGURATION = "oclp_configuration"
    USB_PREPARATION = "usb_preparation"
    USB_CREATION = "usb_creation"
    FINALIZATION = "finalization"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AutomationMode(Enum):
    """Automation modes"""
    FULLY_AUTOMATIC = "fully_automatic"    # No user input needed
    SEMI_AUTOMATIC = "semi_automatic"      # Some user confirmations
    GUIDED = "guided"                      # Step-by-step with user control
    EXPERT = "expert"                      # Manual control over all stages


@dataclass
class PipelineConfiguration:
    """Configuration for the OCLP automation pipeline"""
    # Automation settings
    automation_mode: AutomationMode = AutomationMode.FULLY_AUTOMATIC
    auto_select_macos_version: bool = True
    auto_select_usb_device: bool = False  # Safety: require user to select USB device
    
    # Target specifications
    target_macos_version: Optional[str] = None  # If None, will auto-select
    target_usb_device: Optional[str] = None
    min_usb_size_gb: float = 16.0
    
    # Source file paths
    macos_installer_path: Optional[Path] = None
    oclp_app_path: Optional[Path] = None
    custom_kexts_path: Optional[Path] = None
    
    # Automatic installer acquisition
    auto_download_macos: bool = True
    macos_cache_dir: Optional[Path] = None
    
    # Build options
    include_recovery_tools: bool = True
    include_diagnostic_tools: bool = True
    create_backup: bool = True
    verify_creation: bool = True
    
    # Safety settings
    safety_level: SafetyLevel = SafetyLevel.STANDARD
    require_confirmation: bool = True
    enable_rollback: bool = True
    
    # Logging and debugging
    detailed_logging: bool = False
    preserve_temp_files: bool = False
    log_output_dir: Optional[Path] = None


@dataclass
class PipelineProgress:
    """Progress information for the automation pipeline"""
    current_stage: PipelineStage
    stage_name: str
    stage_number: int
    total_stages: int
    stage_progress: float  # 0-100
    overall_progress: float  # 0-100
    
    # Time estimates
    elapsed_time: float = 0.0
    estimated_total_time: Optional[float] = None
    estimated_remaining_time: Optional[float] = None
    
    # Current operation details
    current_operation: str = ""
    detailed_status: str = ""
    
    # Results from each stage
    detected_hardware: Optional[DetectedHardware] = None
    oclp_config: Optional[OCLPConfiguration] = None
    selected_usb_device: Optional[DiskInfo] = None
    deployment_recipe: Optional[DeploymentRecipe] = None
    macos_installer_info: Optional[OSImageInfo] = None
    
    # Logs and messages
    log_messages: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class PipelineResult:
    """Final result of the automation pipeline"""
    success: bool
    completion_time: float
    final_stage: PipelineStage
    
    # Created artifacts
    usb_device_path: Optional[str] = None
    deployment_metadata_path: Optional[Path] = None
    build_log_path: Optional[Path] = None
    
    # Configuration used
    detected_hardware: Optional[DetectedHardware] = None
    oclp_configuration: Optional[OCLPConfiguration] = None
    deployment_recipe: Optional[DeploymentRecipe] = None
    
    # Build results
    oclp_build_result: Optional[OCLPBuildResult] = None
    usb_build_log: List[str] = field(default_factory=list)
    
    # Summary information
    summary_message: str = ""
    detailed_report: Dict[str, Any] = field(default_factory=dict)
    next_steps: List[str] = field(default_factory=list)


class OCLPAutomationPipeline(QThread if HAS_PYQT6 else object):
    """
    Complete OCLP Automation Pipeline
    
    Provides end-to-end automation from Mac hardware detection to bootable USB creation.
    Designed to make OCLP deployment as simple as selecting a Mac model and clicking "Create".
    """
    
    # Qt Signals for real-time updates
    progress_updated = pyqtSignal(object)  # PipelineProgress
    stage_started = pyqtSignal(str, int)   # stage_name, stage_number
    stage_completed = pyqtSignal(str, bool) # stage_name, success
    log_message = pyqtSignal(str, str)     # level, message
    user_input_required = pyqtSignal(str, dict)  # input_type, options
    pipeline_completed = pyqtSignal(object)  # PipelineResult
    pipeline_failed = pyqtSignal(str, object)   # error_message, partial_result
    
    def __init__(self, config: Optional[PipelineConfiguration] = None):
        if HAS_PYQT6:
            super().__init__()
        self._headless_mode = not HAS_PYQT6
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Configuration
        self.config = config or PipelineConfiguration()
        
        # Pipeline state
        self.current_stage = PipelineStage.INITIALIZING
        self.progress = PipelineProgress(
            current_stage=self.current_stage,
            stage_name="Initializing",
            stage_number=0,
            total_stages=9,  # Updated to include macOS acquisition stage
            stage_progress=0.0,
            overall_progress=0.0
        )
        self.start_time = 0.0
        self.is_cancelled = False
        
        # Results and intermediate data
        self.pipeline_result = PipelineResult(success=False, completion_time=0.0, final_stage=self.current_stage)
        self.temp_dir: Optional[Path] = None
        
        # Core components
        self.hardware_detector = HardwareDetector()
        self.oclp_integration = OCLPBootForgeIntegration()
        self.storage_builder_engine = StorageBuilderEngine()
        
        # Initialize OS Image Manager
        try:
            if Config and OSImageManager:
                config = Config()
                self.os_image_manager = OSImageManager(
                    config,
                    progress_callback=self._handle_download_progress,
                    images_updated_callback=self._handle_images_updated
                )
            else:
                self.os_image_manager = None
                self.logger.warning("OSImageManager not available - manual macOS installer path required")
        except Exception as e:
            self.logger.warning(f"Failed to initialize OSImageManager: {e}")
            self.os_image_manager = None
        
        # User input handling
        self.pending_user_input: Optional[dict] = None
        self.user_input_response: Optional[dict] = None
        
        self.logger.info("OCLP Automation Pipeline initialized")
    
    def _emit_signal_safe(self, signal, *args):
        """Safely emit signals in both GUI and headless modes"""
        if HAS_PYQT6 and not self._headless_mode:
            try:
                signal.emit(*args)
            except Exception as e:
                self.logger.debug(f"Signal emission failed (expected in headless mode): {e}")
        # In headless mode, signals are no-ops
    
    def run(self):
        """Main pipeline execution method"""
        try:
            self.start_time = time.time()
            self._log_message("INFO", "Starting OCLP automation pipeline")
            
            # Execute pipeline stages in order
            if not self._execute_stage_1_hardware_detection():
                return self._handle_pipeline_failure("Hardware detection failed")
            
            if not self._execute_stage_2_compatibility_check():
                return self._handle_pipeline_failure("Compatibility check failed")
            
            if not self._execute_stage_3_macos_acquisition():
                return self._handle_pipeline_failure("macOS acquisition failed")
            
            if not self._execute_stage_4_patch_determination():
                return self._handle_pipeline_failure("Patch determination failed")
            
            if not self._execute_stage_5_oclp_configuration():
                return self._handle_pipeline_failure("OCLP configuration failed")
            
            if not self._execute_stage_6_usb_preparation():
                return self._handle_pipeline_failure("USB preparation failed")
            
            if not self._execute_stage_7_usb_creation():
                return self._handle_pipeline_failure("USB creation failed")
            
            if not self._execute_stage_8_finalization():
                return self._handle_pipeline_failure("Finalization failed")
            
            # Success!
            self._complete_pipeline_successfully()
            
        except Exception as e:
            self.logger.error(f"Pipeline execution failed with exception: {e}")
            self._handle_pipeline_failure(f"Unexpected error: {str(e)}")
        
        finally:
            self._cleanup_pipeline()
    
    def _execute_stage_1_hardware_detection(self) -> bool:
        """Stage 1: Detect Mac hardware and system information"""
        self._start_stage(PipelineStage.HARDWARE_DETECTION, "Detecting Mac Hardware", 1)
        
        try:
            self._log_message("INFO", "Starting hardware detection...")
            self._update_stage_progress(10.0, "Initializing hardware detection")
            
            # Detect hardware
            detected_hardware = self.hardware_detector.detect_hardware()
            if not detected_hardware:
                self._log_message("ERROR", "Failed to detect hardware")
                return False
            
            self._update_stage_progress(50.0, f"Hardware detected: {detected_hardware.get_summary()}")
            
            # Validate this is a Mac
            if detected_hardware.platform.lower() != "mac" and detected_hardware.system_manufacturer != "Apple":
                self._log_message("ERROR", f"This is not a Mac system (detected: {detected_hardware.platform})")
                return False
            
            # Store results
            self.progress.detected_hardware = detected_hardware
            self.pipeline_result.detected_hardware = detected_hardware
            
            self._update_stage_progress(90.0, f"Mac hardware confirmed: {detected_hardware.system_model}")
            self._log_message("INFO", f"Successfully detected Mac: {detected_hardware.get_summary()}")
            
            self._complete_stage("Hardware Detection", True)
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"Hardware detection failed: {e}")
            self._complete_stage("Hardware Detection", False)
            return False
    
    def _execute_stage_2_compatibility_check(self) -> bool:
        """Stage 2: Check OCLP compatibility and requirements"""
        self._start_stage(PipelineStage.COMPATIBILITY_CHECK, "Checking OCLP Compatibility", 2)
        
        try:
            if not self.progress.detected_hardware:
                self._log_message("ERROR", "No hardware data available for compatibility check")
                return False
            
            self._update_stage_progress(10.0, "Checking OCLP compatibility")
            
            # Use the comprehensive OCLP integration
            compatibility_result = detect_mac_and_check_oclp_support(self.progress.detected_hardware)
            
            self._update_stage_progress(40.0, "Analyzing compatibility results")
            
            # Check if Mac is supported
            if not compatibility_result["is_supported"]:
                message = compatibility_result.get("message", "Mac model is not supported by OCLP")
                self._log_message("ERROR", f"OCLP compatibility check failed: {message}")
                return False
            
            # Store OCLP configuration
            oclp_config = compatibility_result.get("config")
            if not oclp_config:
                self._log_message("ERROR", "Failed to get OCLP configuration")
                return False
            
            self.progress.oclp_config = oclp_config
            self.pipeline_result.oclp_configuration = oclp_config
            
            self._update_stage_progress(70.0, f"Mac model {oclp_config.display_name} is {oclp_config.compatibility.value}")
            
            # Log compatibility details
            self._log_message("INFO", f"OCLP Compatibility: {oclp_config.compatibility.value}")
            self._log_message("INFO", f"Recommended macOS: {compatibility_result.get('recommended_macos_version', 'N/A')}")
            
            # Check requirements
            requirements_met = compatibility_result.get("requirements_met", [])
            requirements_missing = compatibility_result.get("requirements_missing", [])
            
            for req in requirements_met:
                self._log_message("INFO", f"✓ {req}")
            
            for req in requirements_missing:
                self._log_message("WARNING", f"⚠ {req}")
            
            # Auto-select macOS version if not specified
            if self.config.auto_select_macos_version and not self.config.target_macos_version:
                recommended_version = compatibility_result.get("recommended_macos_version", "13.0")
                self.config.target_macos_version = recommended_version
                self._log_message("INFO", f"Auto-selected macOS version: {recommended_version}")
            
            self._update_stage_progress(100.0, f"Compatibility confirmed for {oclp_config.display_name}")
            self._complete_stage("Compatibility Check", True)
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"Compatibility check failed: {e}")
            self._complete_stage("Compatibility Check", False)
            return False
    
    def _execute_stage_3_macos_acquisition(self) -> bool:
        """Stage 3: Acquire macOS installer"""
        self._start_stage(PipelineStage.MACOS_ACQUISITION, "Acquiring macOS Installer", 3)
        
        try:
            # Check if installer already provided
            if self.config.macos_installer_path and self.config.macos_installer_path.exists():
                self._log_message("INFO", f"Using provided macOS installer: {self.config.macos_installer_path}")
                self._update_stage_progress(100.0, "macOS installer already available")
                self._complete_stage("macOS Acquisition", True)
                return True
            
            # Check if auto-download is disabled
            if not self.config.auto_download_macos:
                if self.config.automation_mode == AutomationMode.FULLY_AUTOMATIC:
                    self._log_message("ERROR", "No macOS installer provided and auto-download is disabled")
                    return False
                else:
                    self._request_user_input("provide_macos_installer", {
                        "message": "Please provide macOS installer path",
                        "required": True
                    })
                    return False  # Will resume after user input
            
            # Check if OSImageManager is available
            if not self.os_image_manager:
                self._log_message("ERROR", "OS Image Manager not available for automatic installer acquisition")
                return False
            
            self._update_stage_progress(10.0, "Determining optimal macOS version")
            
            # Determine target macOS version based on hardware compatibility
            target_version = self._determine_optimal_macos_version()
            if not target_version:
                self._log_message("ERROR", "Unable to determine suitable macOS version")
                return False
            
            self._update_stage_progress(30.0, f"Searching for macOS {target_version} installer")
            
            # Search for macOS installer
            available_images = self.os_image_manager.search_images(
                f"macOS {target_version}",
                os_family="macos"
            )
            
            # Filter for installer images
            installer_images = [
                img for img in available_images
                if "installer" in img.name.lower() and img.version.startswith(target_version)
            ]
            
            if not installer_images:
                self._log_message("ERROR", f"No macOS {target_version} installer found")
                return False
            
            # Select the latest installer
            selected_image = max(installer_images, key=lambda x: x.version)
            self._log_message("INFO", f"Selected installer: {selected_image.name}")
            
            self._update_stage_progress(50.0, f"Starting download of {selected_image.name}")
            
            # Start download
            cache_dir = self.config.macos_cache_dir or (Path.cwd() / "cache" / "macos_installers")
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            success = self.os_image_manager.download_image(selected_image.id, cache_dir)
            
            if not success:
                self._log_message("ERROR", f"Failed to download {selected_image.name}")
                return False
            
            # Wait for download completion
            max_wait_time = 3600  # 1 hour
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                if self.is_cancelled:
                    self.os_image_manager.cancel_download(selected_image.id)
                    return False
                
                # Check download status
                updated_image = self.os_image_manager.get_image_info(selected_image.id)
                if updated_image and updated_image.status == ImageStatus.VERIFIED:
                    # Download complete and verified
                    self.config.macos_installer_path = Path(updated_image.local_path)
                    self.progress.macos_installer_info = updated_image
                    
                    self._update_stage_progress(95.0, f"Download complete: {updated_image.local_path}")
                    break
                elif updated_image and updated_image.status == ImageStatus.FAILED:
                    self._log_message("ERROR", "macOS installer download failed")
                    return False
                
                # Update progress based on download status
                if updated_image:
                    download_progress = 50.0 + (updated_image.download_progress * 0.4)  # 50-90% range
                    self._update_stage_progress(download_progress, f"Downloading... ({updated_image.download_progress:.1f}%)")
                
                time.sleep(2)  # Check every 2 seconds
            else:
                self._log_message("ERROR", "macOS installer download timed out")
                return False
            
            self._update_stage_progress(100.0, "macOS installer acquisition complete")
            self._complete_stage("macOS Acquisition", True)
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"macOS acquisition failed: {e}")
            self._complete_stage("macOS Acquisition", False)
            return False
    
    def _determine_optimal_macos_version(self) -> Optional[str]:
        """Determine the optimal macOS version for the detected hardware"""
        if not self.progress.oclp_config:
            return None
        
        oclp_config = self.progress.oclp_config
        
        # Use configured target version if specified
        if self.config.target_macos_version:
            return self.config.target_macos_version
        
        # Use recommended version from OCLP config
        if oclp_config.recommended_version:
            return oclp_config.recommended_version
        
        # Default to macOS 13.0 for maximum compatibility
        return "13.0"
    
    def _handle_download_progress(self, progress: DownloadProgress):
        """Handle download progress updates from OSImageManager"""
        if progress.image_id == getattr(self.progress.macos_installer_info, 'id', None):
            # Update progress if this is our installer download
            stage_progress = 50.0 + (progress.progress_percent * 0.4)  # Map to 50-90% range
            speed_text = f"({progress.speed_mbps:.1f} MB/s)" if progress.speed_mbps > 0 else ""
            self._update_stage_progress(
                stage_progress,
                f"Downloading macOS installer... {progress.progress_percent:.1f}% {speed_text}"
            )
    
    def _handle_images_updated(self):
        """Handle images updated callback from OSImageManager"""
        # This could be used to refresh available installers if needed
        pass
    
    def _execute_stage_4_patch_determination(self) -> bool:
        """Stage 4: Determine required patches and kexts"""
        self._start_stage(PipelineStage.PATCH_DETERMINATION, "Determining Required Patches", 4)
        
        try:
            if not self.progress.oclp_config:
                self._log_message("ERROR", "No OCLP configuration available")
                return False
            
            oclp_config = self.progress.oclp_config
            target_version = self.config.target_macos_version or "13.0"
            
            self._update_stage_progress(20.0, f"Analyzing patch requirements for macOS {target_version}")
            
            # Log patch requirements
            if oclp_config.required_patches:
                self._log_message("INFO", f"Required patches ({len(oclp_config.required_patches)}):")
                for patch in oclp_config.required_patches:
                    self._log_message("INFO", f"  • {patch}")
            
            self._update_stage_progress(50.0, "Analyzing optional patches")
            
            if oclp_config.optional_patches:
                self._log_message("INFO", f"Optional patches ({len(oclp_config.optional_patches)}):")
                for patch in oclp_config.optional_patches:
                    self._log_message("INFO", f"  • {patch}")
            
            self._update_stage_progress(70.0, "Checking hardware-specific requirements")
            
            # Log hardware-specific patches
            patch_categories = [
                ("Graphics", oclp_config.wifi_patches),
                ("Audio", oclp_config.audio_patches), 
                ("WiFi/Bluetooth", oclp_config.wifi_patches),
                ("USB", oclp_config.usb_patches)
            ]
            
            for category, patches in patch_categories:
                if patches:
                    self._log_message("INFO", f"{category} patches: {', '.join(patches)}")
            
            self._update_stage_progress(90.0, "Patch analysis complete")
            
            # Log special requirements
            special_requirements = []
            if oclp_config.requires_sip_disable:
                special_requirements.append("SIP must be disabled")
            if oclp_config.requires_root_patch:
                special_requirements.append("Root patches required")
            if oclp_config.requires_amfi_patches:
                special_requirements.append("AMFI patches required")
            
            if special_requirements:
                self._log_message("WARNING", "Special requirements:")
                for req in special_requirements:
                    self._log_message("WARNING", f"  ⚠ {req}")
            
            self._update_stage_progress(100.0, f"Patch determination complete for {oclp_config.display_name}")
            self._complete_stage("Patch Determination", True)
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"Patch determination failed: {e}")
            self._complete_stage("Patch Determination", False)
            return False
    
    def _execute_stage_5_oclp_configuration(self) -> bool:
        """Stage 5: Configure OCLP and prepare OpenCore build"""
        self._start_stage(PipelineStage.OCLP_CONFIGURATION, "Configuring OpenCore", 5)
        
        try:
            if not self.progress.oclp_config or not self.progress.detected_hardware:
                self._log_message("ERROR", "Missing required data for OCLP configuration")
                return False
            
            self._update_stage_progress(10.0, "Preparing OCLP build environment")
            
            # Start OCLP build process (async)
            build_started = self.oclp_integration.prepare_oclp_build_async(
                self.progress.detected_hardware,
                progress_callback=self._handle_oclp_progress
            )
            
            if not build_started:
                self._log_message("ERROR", "Failed to start OCLP build process")
                return False
            
            self._update_stage_progress(30.0, "OCLP build process started")
            
            # Wait for OCLP build to complete (with timeout)
            timeout = 300  # 5 minutes
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if self.is_cancelled:
                    self._log_message("INFO", "OCLP build cancelled by user")
                    return False
                
                # Check if build completed
                build_result = self.oclp_integration.get_oclp_build_artifacts()
                if build_result:
                    self.pipeline_result.oclp_build_result = build_result
                    
                    if build_result.success:
                        self._update_stage_progress(90.0, "OCLP build completed successfully")
                        self._log_message("INFO", f"OpenCore EFI generated: {build_result.opencore_efi_path}")
                        break
                    else:
                        self._log_message("ERROR", "OCLP build failed")
                        return False
                
                time.sleep(2)  # Check every 2 seconds
                self._update_stage_progress(30.0 + (time.time() - start_time) / timeout * 60.0, "Building OpenCore configuration...")
            else:
                self._log_message("ERROR", "OCLP build timed out")
                return False
            
            self._update_stage_progress(100.0, "OpenCore configuration complete")
            self._complete_stage("OCLP Configuration", True)
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"OCLP configuration failed: {e}")
            self._complete_stage("OCLP Configuration", False)
            return False
    
    def _execute_stage_6_usb_preparation(self) -> bool:
        """Stage 6: Prepare USB device and deployment recipe"""
        self._start_stage(PipelineStage.USB_PREPARATION, "Preparing USB Device", 6)
        
        try:
            self._update_stage_progress(10.0, "Scanning for suitable USB devices")
            
            # Get suitable USB devices
            suitable_devices = self.storage_builder_engine.get_suitable_devices(
                min_size_gb=self.config.min_usb_size_gb
            )
            
            if not suitable_devices:
                self._log_message("ERROR", f"No suitable USB devices found (minimum {self.config.min_usb_size_gb}GB required)")
                return False
            
            self._update_stage_progress(30.0, f"Found {len(suitable_devices)} suitable USB device(s)")
            
            # Select USB device
            selected_device = None
            if self.config.target_usb_device:
                # Use specified device
                for device in suitable_devices:
                    if device.device_path == self.config.target_usb_device:
                        selected_device = device
                        break
                
                if not selected_device:
                    self._log_message("ERROR", f"Specified USB device not found: {self.config.target_usb_device}")
                    return False
            
            elif self.config.auto_select_usb_device and len(suitable_devices) == 1:
                # Auto-select if only one device
                selected_device = suitable_devices[0]
                self._log_message("INFO", f"Auto-selected USB device: {selected_device.model}")
            
            else:
                # Require user selection
                if self.config.automation_mode == AutomationMode.FULLY_AUTOMATIC:
                    self._log_message("ERROR", "Multiple USB devices found but auto-selection is disabled")
                    return False
                else:
                    # Request user input
                    self._request_user_input("select_usb_device", {
                        "devices": suitable_devices,
                        "message": "Please select a USB device for OCLP deployment"
                    })
                    return False  # Will resume after user input
            
            if not selected_device:
                self._log_message("ERROR", "No USB device selected")
                return False
            
            self.progress.selected_usb_device = selected_device
            self._update_stage_progress(50.0, f"Selected USB device: {selected_device.model} ({selected_device.size_gb:.1f}GB)")
            
            # Create deployment recipe
            if not self.progress.oclp_config:
                self._log_message("ERROR", "No OCLP configuration available for recipe creation")
                return False
            
            self._update_stage_progress(70.0, "Creating deployment recipe")
            
            recipe = self.oclp_integration.create_oclp_usb_recipe(
                self.progress.oclp_config,
                self.config.target_macos_version or "13.0"
            )
            
            if not recipe:
                self._log_message("ERROR", "Failed to create deployment recipe")
                return False
            
            self.progress.deployment_recipe = recipe
            self.pipeline_result.deployment_recipe = recipe
            
            self._update_stage_progress(90.0, f"Deployment recipe created: {recipe.name}")
            self._log_message("INFO", f"Recipe: {recipe.description}")
            
            self._update_stage_progress(100.0, "USB preparation complete")
            self._complete_stage("USB Preparation", True)
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"USB preparation failed: {e}")
            self._complete_stage("USB Preparation", False)
            return False
    
    def _execute_stage_7_usb_creation(self) -> bool:
        """Stage 7: Create the bootable USB drive"""
        self._start_stage(PipelineStage.USB_CREATION, "Creating Bootable USB", 7)
        
        try:
            if not all([self.progress.selected_usb_device, self.progress.deployment_recipe, self.progress.oclp_config]):
                self._log_message("ERROR", "Missing required components for USB creation")
                return False
            
            self._update_stage_progress(10.0, "Preparing USB build environment")
            
            # Prepare source files
            source_files = {}
            
            # macOS installer
            if self.config.macos_installer_path and self.config.macos_installer_path.exists():
                source_files["macOS_installer.app"] = str(self.config.macos_installer_path)
            else:
                self._log_message("WARNING", "macOS installer not specified - user will need to provide")
            
            # OCLP app
            if self.config.oclp_app_path and self.config.oclp_app_path.exists():
                source_files["OpenCore-Legacy-Patcher.app"] = str(self.config.oclp_app_path)
            
            # OCLP build artifacts
            if self.pipeline_result.oclp_build_result:
                if self.pipeline_result.oclp_build_result.opencore_efi_path:
                    source_files["OpenCore.efi"] = str(self.pipeline_result.oclp_build_result.opencore_efi_path)
                
                if self.pipeline_result.oclp_build_result.config_plist_path:
                    source_files["config.plist"] = str(self.pipeline_result.oclp_build_result.config_plist_path)
            
            self._update_stage_progress(30.0, "Starting USB creation process")
            
            # Create hardware profile for USB builder
            hardware_profile = HardwareProfile.from_mac_model(self.progress.oclp_config.model_identifier)
            
            # Add hardware profile to USB builder engine if not already present
            if hardware_profile.model not in self.storage_builder_engine.hardware_profiles:
                self.storage_builder_engine.hardware_profiles[hardware_profile.model] = hardware_profile
            
            # Start USB build
            storage_builder = self.storage_builder_engine.create_deployment_usb(
                recipe_name=self.progress.deployment_recipe.name,
                target_device=self.progress.selected_usb_device.device_path,
                hardware_profile_name=hardware_profile.model,
                source_files=source_files,
                progress_callback=self._handle_usb_progress
            )
            
            self._update_stage_progress(40.0, "USB build started")
            
            # Wait for USB build to complete
            timeout = 1800  # 30 minutes
            start_time = time.time()
            
            while usb_builder.isRunning() and time.time() - start_time < timeout:
                if self.is_cancelled:
                    usb_builder.cancel_build()
                    self._log_message("INFO", "USB build cancelled by user")
                    return False
                
                self.msleep(1000)  # Check every second
            
            if usb_builder.isRunning():
                self._log_message("ERROR", "USB build timed out")
                usb_builder.cancel_build()
                return False
            
            # Check build result
            if hasattr(usb_builder, '_build_successful') and usb_builder._build_successful:
                self.pipeline_result.usb_device_path = self.progress.selected_usb_device.device_path
                self.pipeline_result.usb_build_log = getattr(usb_builder, 'build_log', [])
                
                self._update_stage_progress(90.0, "USB creation completed successfully")
                self._log_message("INFO", f"Bootable USB created: {self.progress.selected_usb_device.model}")
            else:
                self._log_message("ERROR", "USB build failed")
                return False
            
            self._update_stage_progress(100.0, "Bootable USB creation complete")
            self._complete_stage("USB Creation", True)
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"USB creation failed: {e}")
            self._complete_stage("USB Creation", False)
            return False
    
    def _execute_stage_8_finalization(self) -> bool:
        """Stage 8: Finalize deployment and generate reports"""
        self._start_stage(PipelineStage.FINALIZATION, "Finalizing Deployment", 8)
        
        try:
            self._update_stage_progress(20.0, "Creating deployment report")
            
            # Create comprehensive deployment report
            report = {
                "deployment_timestamp": time.time(),
                "total_time_seconds": time.time() - self.start_time,
                "detected_hardware": {
                    "model": self.progress.detected_hardware.system_model if self.progress.detected_hardware else "Unknown",
                    "summary": self.progress.detected_hardware.get_summary() if self.progress.detected_hardware else "N/A"
                },
                "oclp_configuration": {
                    "model_identifier": self.progress.oclp_config.model_identifier if self.progress.oclp_config else "Unknown",
                    "compatibility": self.progress.oclp_config.compatibility.value if self.progress.oclp_config else "Unknown",
                    "required_patches": self.progress.oclp_config.required_patches if self.progress.oclp_config else []
                },
                "deployment_details": {
                    "macos_version": self.config.target_macos_version,
                    "usb_device": self.progress.selected_usb_device.model if self.progress.selected_usb_device else "Unknown",
                    "recipe_name": self.progress.deployment_recipe.name if self.progress.deployment_recipe else "Unknown"
                }
            }
            
            self.pipeline_result.detailed_report = report
            
            self._update_stage_progress(50.0, "Generating user guidance")
            
            # Generate next steps for user
            next_steps = []
            if self.progress.oclp_config:
                if self.progress.oclp_config.requires_sip_disable:
                    next_steps.append("Disable SIP (System Integrity Protection) on your Mac")
                
                if self.progress.oclp_config.requires_root_patch:
                    next_steps.append("Create a backup of your Mac before applying root patches")
                
                next_steps.extend([
                    "Boot your Mac from the USB drive (hold Option key during startup)",
                    "Install macOS using the installer on the USB drive",
                    "Run OpenCore Legacy Patcher from the OCLP Tools partition after installation",
                    "Apply required patches for your Mac model"
                ])
            
            self.pipeline_result.next_steps = next_steps
            
            self._update_stage_progress(70.0, "Creating summary message")
            
            # Create summary message
            if self.progress.oclp_config and self.progress.selected_usb_device:
                summary = (f"Successfully created OCLP deployment for {self.progress.oclp_config.display_name} "
                          f"on {self.progress.selected_usb_device.model}. "
                          f"macOS {self.config.target_macos_version} is ready for installation.")
            else:
                summary = "OCLP deployment completed successfully."
            
            self.pipeline_result.summary_message = summary
            
            self._update_stage_progress(90.0, "Saving deployment metadata")
            
            # Save logs if requested
            if self.config.log_output_dir:
                log_file = self.config.log_output_dir / f"oclp_deployment_{int(time.time())}.log"
                log_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(log_file, 'w') as f:
                    f.write(f"OCLP Automation Pipeline Log\n")
                    f.write(f"Generated: {time.ctime()}\n\n")
                    for message in self.progress.log_messages:
                        f.write(f"{message}\n")
                
                self.pipeline_result.build_log_path = log_file
                self._log_message("INFO", f"Build log saved: {log_file}")
            
            self._update_stage_progress(100.0, "Deployment finalized")
            self._complete_stage("Finalization", True)
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"Finalization failed: {e}")
            self._complete_stage("Finalization", False)
            return False
    
    def _complete_pipeline_successfully(self):
        """Complete the pipeline successfully"""
        self.current_stage = PipelineStage.COMPLETED
        self.pipeline_result.success = True
        self.pipeline_result.completion_time = time.time() - self.start_time
        self.pipeline_result.final_stage = PipelineStage.COMPLETED
        
        self._update_overall_progress(100.0, "Pipeline completed successfully")
        
        self._log_message("INFO", f"OCLP automation pipeline completed successfully in {self.pipeline_result.completion_time:.1f} seconds")
        self._log_message("INFO", self.pipeline_result.summary_message)
        
        self.pipeline_completed.emit(self.pipeline_result)
    
    def _handle_pipeline_failure(self, error_message: str):
        """Handle pipeline failure"""
        self.current_stage = PipelineStage.FAILED
        self.pipeline_result.success = False
        self.pipeline_result.completion_time = time.time() - self.start_time
        self.pipeline_result.final_stage = self.current_stage
        self.pipeline_result.summary_message = f"Pipeline failed: {error_message}"
        
        self._log_message("ERROR", f"Pipeline failed: {error_message}")
        self.pipeline_failed.emit(error_message, self.pipeline_result)
    
    def _cleanup_pipeline(self):
        """Clean up pipeline resources"""
        try:
            if self.temp_dir and self.temp_dir.exists() and not self.config.preserve_temp_files:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                self._log_message("INFO", "Cleaned up temporary files")
            
            # Cleanup OCLP integration resources
            self.oclp_integration.cleanup_oclp_resources()
            
        except Exception as e:
            self._log_message("WARNING", f"Cleanup error: {e}")
    
    # Progress and status update methods
    
    def _start_stage(self, stage: PipelineStage, stage_name: str, stage_number: int):
        """Start a new pipeline stage"""
        self.current_stage = stage
        self.progress.current_stage = stage
        self.progress.stage_name = stage_name
        self.progress.stage_number = stage_number
        self.progress.stage_progress = 0.0
        
        self._log_message("INFO", f"Starting stage {stage_number}: {stage_name}")
        self.stage_started.emit(stage_name, stage_number)
        self._update_overall_progress()
    
    def _complete_stage(self, stage_name: str, success: bool):
        """Complete current pipeline stage"""
        self.progress.stage_progress = 100.0
        self._update_overall_progress()
        
        self._log_message("INFO" if success else "ERROR", 
                         f"Stage {stage_name} {'completed' if success else 'failed'}")
        self.stage_completed.emit(stage_name, success)
    
    def _update_stage_progress(self, progress: float, operation: str = ""):
        """Update progress within current stage"""
        self.progress.stage_progress = min(100.0, max(0.0, progress))
        if operation:
            self.progress.current_operation = operation
            self.progress.detailed_status = operation
        
        self._update_overall_progress()
    
    def _update_overall_progress(self, overall: Optional[float] = None, status: str = ""):
        """Update overall pipeline progress"""
        if overall is not None:
            self.progress.overall_progress = overall
        else:
            # Calculate based on stage progress
            base_progress = ((self.progress.stage_number - 1) / self.progress.total_stages) * 100
            stage_contribution = (self.progress.stage_progress / self.progress.total_stages)
            self.progress.overall_progress = min(100.0, base_progress + stage_contribution)
        
        # Update time estimates
        self.progress.elapsed_time = time.time() - self.start_time
        
        if self.progress.overall_progress > 0:
            estimated_total = (self.progress.elapsed_time / self.progress.overall_progress) * 100
            self.progress.estimated_total_time = estimated_total
            self.progress.estimated_remaining_time = estimated_total - self.progress.elapsed_time
        
        if status:
            self.progress.detailed_status = status
        
        # Emit progress signal
        self.progress_updated.emit(self.progress)
    
    def _log_message(self, level: str, message: str):
        """Log message and add to progress tracking"""
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {level}: {message}"
        
        self.progress.log_messages.append(formatted_message)
        
        # Categorize messages
        if level == "ERROR":
            self.progress.errors.append(message)
        elif level == "WARNING":
            self.progress.warnings.append(message)
        
        # Emit log signal
        self.log_message.emit(level, message)
        
        # Also log to Python logger
        log_func = getattr(self.logger, level.lower(), self.logger.info)
        log_func(message)
    
    def _handle_oclp_progress(self, oclp_progress):
        """Handle progress updates from OCLP integration"""
        if hasattr(oclp_progress, 'overall_progress'):
            stage_progress = oclp_progress.overall_progress
            operation = getattr(oclp_progress, 'current_operation', '')
            self._update_stage_progress(stage_progress, f"OCLP: {operation}")
    
    def _handle_usb_progress(self, usb_progress):
        """Handle progress updates from USB builder"""
        if hasattr(usb_progress, 'overall_progress'):
            stage_progress = usb_progress.overall_progress
            operation = getattr(usb_progress, 'current_step', '')
            self._update_stage_progress(stage_progress, f"USB: {operation}")
    
    def _request_user_input(self, input_type: str, options: dict):
        """Request user input and pause execution"""
        self.pending_user_input = {"type": input_type, "options": options}
        self.user_input_required.emit(input_type, options)
        
        # Pause execution until user responds
        self.msleep(100)  # Brief pause to emit signal
    
    # Public methods for external control
    
    def set_user_input_response(self, response: dict):
        """Set user input response and resume execution"""
        self.user_input_response = response
        self.pending_user_input = None
    
    def cancel_pipeline(self):
        """Cancel the pipeline execution"""
        self.is_cancelled = True
        self._log_message("INFO", "Pipeline cancellation requested")
    
    def get_current_progress(self) -> PipelineProgress:
        """Get current pipeline progress"""
        return self.progress
    
    def get_pipeline_result(self) -> Optional[PipelineResult]:
        """Get pipeline result (only available after completion)"""
        return self.pipeline_result if self.pipeline_result.success or self.pipeline_result.final_stage == PipelineStage.FAILED else None
    
    # Configuration methods
    
    def update_configuration(self, new_config: PipelineConfiguration):
        """Update pipeline configuration (only before starting)"""
        if self.isRunning():
            raise RuntimeError("Cannot update configuration while pipeline is running")
        
        self.config = new_config
        self._log_message("INFO", "Pipeline configuration updated")
    
    def set_macos_installer_path(self, path: Path):
        """Set macOS installer path"""
        if path.exists():
            self.config.macos_installer_path = path
            self._log_message("INFO", f"macOS installer path set: {path}")
        else:
            raise FileNotFoundError(f"macOS installer not found: {path}")
    
    def set_oclp_app_path(self, path: Path):
        """Set OCLP app path"""
        if path.exists():
            self.config.oclp_app_path = path
            self._log_message("INFO", f"OCLP app path set: {path}")
        else:
            raise FileNotFoundError(f"OCLP app not found: {path}")


# Convenience functions for easy integration

def create_standard_pipeline(automation_mode: AutomationMode = AutomationMode.FULLY_AUTOMATIC) -> OCLPAutomationPipeline:
    """Create a standard OCLP automation pipeline with sensible defaults"""
    config = PipelineConfiguration(
        automation_mode=automation_mode,
        auto_select_macos_version=True,
        auto_select_usb_device=False,  # Safety: always require USB device selection
        min_usb_size_gb=16.0,
        include_recovery_tools=True,
        include_diagnostic_tools=True,
        safety_level=SafetyLevel.STANDARD,
        require_confirmation=automation_mode != AutomationMode.FULLY_AUTOMATIC,
        detailed_logging=True
    )
    
    return OCLPAutomationPipeline(config)


def create_expert_pipeline(preserve_temp_files: bool = True) -> OCLPAutomationPipeline:
    """Create an expert-mode pipeline with maximum control and logging"""
    config = PipelineConfiguration(
        automation_mode=AutomationMode.EXPERT,
        auto_select_macos_version=False,
        auto_select_usb_device=False,
        include_recovery_tools=True,
        include_diagnostic_tools=True,
        safety_level=SafetyLevel.PARANOID,
        require_confirmation=True,
        detailed_logging=True,
        preserve_temp_files=preserve_temp_files,
        log_output_dir=Path.cwd() / "oclp_logs"
    )
    
    return OCLPAutomationPipeline(config)


def quick_oclp_deployment(macos_installer_path: Path, target_usb_device: str) -> OCLPAutomationPipeline:
    """Create and configure pipeline for quick OCLP deployment"""
    config = PipelineConfiguration(
        automation_mode=AutomationMode.FULLY_AUTOMATIC,
        auto_select_macos_version=True,
        target_usb_device=target_usb_device,
        macos_installer_path=macos_installer_path,
        safety_level=SafetyLevel.STANDARD
    )
    
    return OCLPAutomationPipeline(config)