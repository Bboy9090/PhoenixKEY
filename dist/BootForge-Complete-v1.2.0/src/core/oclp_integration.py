"""
BootForge OpenCore Legacy Patcher Integration
Comprehensive OCLP command-line integration for automated macOS legacy hardware support
"""

import os
import re
import json
import time
import shutil
import logging
import platform
import subprocess
import tempfile
from pathlib import Path
from enum import Enum
from typing import Dict, List, Optional, Tuple, Callable, Any, Union
from dataclasses import dataclass, field

# Optional PyQt6 imports for headless operation support
try:
    from PyQt6.QtCore import QThread, pyqtSignal
    HAS_PYQT6 = True
except ImportError:
    QThread = object  # Fallback base class
    pyqtSignal = lambda *args: None  # Dummy signal
    HAS_PYQT6 = False

from src.core.hardware_detector import DetectedHardware, DetectionConfidence
from src.core.usb_builder import HardwareProfile
from src.core.hardware_profiles import get_mac_model_data, get_patch_requirements_for_model


class OCLPAvailability(Enum):
    """OCLP installation availability status"""
    AVAILABLE = "available"
    NOT_INSTALLED = "not_installed"
    WRONG_PLATFORM = "wrong_platform"
    INSUFFICIENT_PERMISSIONS = "insufficient_permissions"
    CORRUPTED = "corrupted"


class OCLPBuildStatus(Enum):
    """OCLP build operation status"""
    INITIALIZING = "initializing"
    ANALYZING_HARDWARE = "analyzing_hardware"
    GENERATING_CONFIG = "generating_config"
    BUILDING_OPENCORE = "building_opencore"
    EXTRACTING_FILES = "extracting_files"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OCLPCompatibility(Enum):
    """Mac model OCLP compatibility levels"""
    FULLY_SUPPORTED = "fully_supported"        # Full OCLP support with all features
    PARTIALLY_SUPPORTED = "partially_supported" # Some limitations or missing features
    EXPERIMENTAL = "experimental"               # Experimental support, may be unstable
    UNSUPPORTED = "unsupported"                # Not supported by OCLP
    UNKNOWN = "unknown"                        # Unknown compatibility status


@dataclass
class OCLPConfiguration:
    """OCLP configuration settings for a specific Mac model"""
    model_identifier: str
    display_name: str
    compatibility: OCLPCompatibility
    
    # Hardware-specific settings
    sip_status: Optional[str] = None  # "enabled", "disabled", "partial"
    secure_boot_model: Optional[str] = None
    
    # Required patches
    required_patches: List[str] = field(default_factory=list)
    optional_patches: List[str] = field(default_factory=list)
    
    # GPU support
    gpu_acceleration: bool = True
    metal_support: bool = True
    
    # Networking
    wifi_patches: List[str] = field(default_factory=list)
    ethernet_patches: List[str] = field(default_factory=list)
    
    # Audio
    audio_patches: List[str] = field(default_factory=list)
    
    # USB and I/O
    usb_patches: List[str] = field(default_factory=list)
    
    # macOS version compatibility
    min_supported_version: Optional[str] = None
    max_supported_version: Optional[str] = None
    recommended_version: Optional[str] = None
    
    # Special requirements
    requires_root_patch: bool = False
    requires_amfi_patches: bool = False
    requires_sip_disable: bool = False
    
    # Build settings
    build_arguments: List[str] = field(default_factory=list)
    post_build_scripts: List[str] = field(default_factory=list)
    
    # Metadata
    last_verified_oclp_version: Optional[str] = None
    notes: List[str] = field(default_factory=list)


@dataclass
class OCLPBuildResult:
    """Result of OCLP build operation"""
    success: bool
    model_identifier: str
    oclp_version: str
    build_time: float
    
    # Generated files
    opencore_efi_path: Optional[Path] = None
    kext_files: List[Path] = field(default_factory=list)
    config_plist_path: Optional[Path] = None
    
    # Build artifacts
    build_log: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    # Configuration used
    configuration: Optional[OCLPConfiguration] = None
    
    # Output paths for USB integration
    efi_folder_path: Optional[Path] = None
    drivers_folder_path: Optional[Path] = None
    tools_folder_path: Optional[Path] = None


@dataclass
class OCLPProgress:
    """OCLP operation progress information"""
    current_status: OCLPBuildStatus
    step_name: str
    step_number: int
    total_steps: int
    step_progress: float  # 0-100
    overall_progress: float  # 0-100
    estimated_time_remaining: Optional[int] = None  # seconds
    current_operation: str = ""
    detailed_log: List[str] = field(default_factory=list)


class OCLPCompatibilityDatabase:
    """Database of Mac model OCLP compatibility and configurations"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._configurations: Dict[str, OCLPConfiguration] = {}
        self._init_compatibility_database()
    
    def _init_compatibility_database(self):
        """Initialize OCLP compatibility database using comprehensive Mac model data"""
        # Import comprehensive Mac model database
        mac_models = get_mac_model_data()
        
        # Convert comprehensive Mac model data to OCLP configurations
        for model_id, model_data in mac_models.items():
            # Map compatibility levels
            oclp_compatibility_map = {
                "fully_supported": OCLPCompatibility.FULLY_SUPPORTED,
                "partially_supported": OCLPCompatibility.PARTIALLY_SUPPORTED,
                "experimental": OCLPCompatibility.EXPERIMENTAL,
                "unsupported": OCLPCompatibility.UNSUPPORTED,
                "unknown": OCLPCompatibility.UNKNOWN
            }
            
            compatibility = oclp_compatibility_map.get(
                model_data.get("oclp_compatibility", "unknown"),
                OCLPCompatibility.UNKNOWN
            )
            
            # Determine required patches for macOS 13.0 (default)
            required_patches = model_data.get("required_patches", {}).get("13.0", [])
            
            # Create OCLP configuration from comprehensive data
            config = OCLPConfiguration(
                model_identifier=model_id,
                display_name=model_data["name"],
                compatibility=compatibility,
                sip_status=model_data.get("sip_requirements"),
                secure_boot_model=model_data.get("secure_boot_model"),
                required_patches=required_patches,
                optional_patches=model_data.get("optional_patches", {}).get("13.0", []),
                gpu_acceleration=compatibility in [OCLPCompatibility.FULLY_SUPPORTED, OCLPCompatibility.PARTIALLY_SUPPORTED],
                metal_support=compatibility == OCLPCompatibility.FULLY_SUPPORTED,
                wifi_patches=model_data.get("wifi_bluetooth_patches", []),
                ethernet_patches=[],  # Not specified in current data
                audio_patches=model_data.get("audio_patches", []),
                usb_patches=model_data.get("usb_patches", []),
                min_supported_version="11.0" if compatibility != OCLPCompatibility.UNSUPPORTED else None,
                max_supported_version="14.0" if compatibility != OCLPCompatibility.UNSUPPORTED else None,
                recommended_version="13.0" if compatibility != OCLPCompatibility.UNSUPPORTED else None,
                requires_root_patch=False,  # Can be enhanced later
                requires_amfi_patches="AMFIPass" in required_patches,
                requires_sip_disable=model_data.get("sip_requirements") == "disabled",
                build_arguments=["--build", "--model", model_id] if compatibility != OCLPCompatibility.UNSUPPORTED else [],
                post_build_scripts=[],
                last_verified_oclp_version=None,
                notes=model_data.get("notes", [])
            )
            
            self._add_configuration(config)
        
        # Log the number of configurations loaded from comprehensive database
        self.logger.info(f"Loaded {len(self._configurations)} Mac model OCLP configurations from comprehensive database")
    
    def _add_configuration(self, config: OCLPConfiguration):
        """Add a configuration to the database"""
        self._configurations[config.model_identifier] = config
    
    def get_configuration(self, model_identifier: str) -> Optional[OCLPConfiguration]:
        """Get OCLP configuration for a Mac model"""
        return self._configurations.get(model_identifier)
    
    def get_all_supported_models(self) -> List[str]:
        """Get list of all supported Mac models"""
        return [
            model for model, config in self._configurations.items()
            if config.compatibility in [
                OCLPCompatibility.FULLY_SUPPORTED,
                OCLPCompatibility.PARTIALLY_SUPPORTED,
                OCLPCompatibility.EXPERIMENTAL
            ]
        ]
    
    def is_model_supported(self, model_identifier: str) -> bool:
        """Check if a Mac model is supported by OCLP"""
        config = self.get_configuration(model_identifier)
        return config is not None and config.compatibility != OCLPCompatibility.UNSUPPORTED
    
    def get_compatibility_level(self, model_identifier: str) -> OCLPCompatibility:
        """Get compatibility level for a Mac model"""
        config = self.get_configuration(model_identifier)
        return config.compatibility if config else OCLPCompatibility.UNKNOWN


class OCLPIntegration(QThread if HAS_PYQT6 else object):
    """
    Comprehensive OpenCore Legacy Patcher integration for BootForge
    Provides automated OCLP workflow integration with hardware detection and USB building
    """
    
    # Qt signals for progress reporting
    progress_updated = pyqtSignal(object)  # OCLPProgress
    build_completed = pyqtSignal(object)  # OCLPBuildResult
    build_started = pyqtSignal(str)  # model_identifier
    log_message = pyqtSignal(str, str)  # level, message
    status_changed = pyqtSignal(str)  # status description
    
    def __init__(self):
        if HAS_PYQT6:
            super().__init__()
        self._headless_mode = not HAS_PYQT6
        self.logger = logging.getLogger(self.__class__.__name__)
        self.compatibility_db = OCLPCompatibilityDatabase()
        
        # OCLP installation paths - comprehensive discovery
        self.oclp_paths = self._get_comprehensive_oclp_paths()
        
        # User-configurable OCLP path
        self.custom_oclp_path: Optional[Path] = None
        
        # Current operation state
        self.current_build: Optional[OCLPBuildResult] = None
        self.is_cancelled = False
        self.temp_dir: Optional[Path] = None
        
        # Operation tracking
        self._total_steps = 7
        self._current_step = 0
        self._step_progress = 0.0
        
        self.logger.info("OCLP Integration initialized")
    
    def _get_comprehensive_oclp_paths(self) -> List[Path]:
        """Get comprehensive list of potential OCLP installation paths"""
        paths = []
        
        # Standard macOS application paths
        paths.extend([
            Path("/Applications/OpenCore-Patcher.app"),
            Path("/System/Applications/OpenCore-Patcher.app"),
            Path.home() / "Applications" / "OpenCore-Patcher.app",
            Path("/Applications/Utilities/OpenCore-Patcher.app"),
        ])
        
        # Homebrew and package manager paths
        paths.extend([
            Path("/usr/local/bin/oclp"),
            Path("/opt/homebrew/bin/oclp"),
            Path("/usr/bin/oclp"),
            Path("/opt/local/bin/oclp"),  # MacPorts
        ])
        
        # Development and alternative paths
        paths.extend([
            Path.home() / "bin" / "oclp",
            Path.home() / ".local" / "bin" / "oclp",
            Path("/Developer/OpenCore-Patcher.app"),
        ])
        
        # Environment-based paths
        if oclp_home := os.environ.get("OCLP_HOME"):
            paths.append(Path(oclp_home))
        
        if oclp_path := os.environ.get("OCLP_PATH"):
            paths.append(Path(oclp_path))
        
        # PATH-based discovery fallbacks
        path_env = os.environ.get("PATH", "")
        for path_dir in path_env.split(os.pathsep):
            if path_dir.strip():
                paths.append(Path(path_dir) / "oclp")
        
        return paths
    
    def set_custom_oclp_path(self, path: Union[str, Path]) -> bool:
        """Set custom OCLP executable path"""
        custom_path = Path(path)
        if custom_path.exists():
            self.custom_oclp_path = custom_path
            self.logger.info(f"Custom OCLP path set: {custom_path}")
            return True
        else:
            self.logger.warning(f"Custom OCLP path does not exist: {custom_path}")
            return False
    
    def _emit_signal_safe(self, signal, *args):
        """Safely emit signals in both GUI and headless modes"""
        if HAS_PYQT6 and not self._headless_mode:
            try:
                signal.emit(*args)
            except Exception as e:
                self.logger.debug(f"Signal emission failed (expected in headless mode): {e}")
        # In headless mode, signals are no-ops
    
    def check_oclp_availability(self) -> OCLPAvailability:
        """Check if OCLP is available and properly installed"""
        try:
            # Check platform compatibility
            if platform.system().lower() != "darwin":
                self.logger.warning("OCLP requires macOS platform")
                return OCLPAvailability.WRONG_PLATFORM
            
            # Check for OCLP installation
            oclp_path = self._find_oclp_executable()
            if not oclp_path:
                self.logger.warning("OCLP not found in standard installation paths")
                return OCLPAvailability.NOT_INSTALLED
            
            # Verify OCLP functionality
            if not self._verify_oclp_installation(oclp_path):
                self.logger.error("OCLP installation appears corrupted")
                return OCLPAvailability.CORRUPTED
            
            # Check permissions
            if not self._check_oclp_permissions():
                self.logger.warning("Insufficient permissions for OCLP operations")
                return OCLPAvailability.INSUFFICIENT_PERMISSIONS
            
            self.logger.info(f"OCLP available at: {oclp_path}")
            return OCLPAvailability.AVAILABLE
            
        except Exception as e:
            self.logger.error(f"Error checking OCLP availability: {e}")
            return OCLPAvailability.CORRUPTED
    
    def _find_oclp_executable(self) -> Optional[Path]:
        """Find OCLP executable in standard installation paths"""
        # Check custom path first if set
        if self.custom_oclp_path:
            if self.custom_oclp_path.exists() and os.access(self.custom_oclp_path, os.X_OK):
                self.logger.info(f"Using custom OCLP path: {self.custom_oclp_path}")
                return self.custom_oclp_path
            else:
                self.logger.warning(f"Custom OCLP path no longer valid: {self.custom_oclp_path}")
        
        for path in self.oclp_paths:
            path = Path(path)
            
            # Check for app bundle
            if path.suffix == ".app" and path.exists():
                # Look for executable inside app bundle
                exec_path = path / "Contents" / "MacOS" / "OpenCore-Patcher"
                if exec_path.exists() and os.access(exec_path, os.X_OK):
                    return exec_path
            
            # Check for direct executable
            elif path.exists() and os.access(path, os.X_OK):
                return path
        
        # Try to find via which command
        try:
            result = subprocess.run(
                ["which", "oclp"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                path = Path(result.stdout.strip())
                if path.exists():
                    return path
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass
        
        return None
    
    def _verify_oclp_installation(self, oclp_path: Path) -> bool:
        """Verify OCLP installation is functional"""
        try:
            # Try to get OCLP version
            result = subprocess.run(
                [str(oclp_path), "--version"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                version_output = result.stdout.strip()
                self.logger.info(f"OCLP version: {version_output}")
                return True
            else:
                self.logger.error(f"OCLP version check failed: {result.stderr}")
                return False
                
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
            self.logger.error(f"OCLP verification failed: {e}")
            return False
    
    def _check_oclp_permissions(self) -> bool:
        """Check if we have sufficient permissions for OCLP operations"""
        try:
            # Check if we can create temporary files
            with tempfile.NamedTemporaryFile() as tmp:
                pass
            
            # Check if we have write access to common OCLP directories
            test_dirs = [
                Path.home() / ".oclp",
                Path("/tmp"),
                Path.home() / "Downloads"
            ]
            
            for test_dir in test_dirs:
                if test_dir.exists() and os.access(test_dir, os.W_OK):
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Permission check failed: {e}")
            return False
    
    def get_oclp_version(self) -> Optional[str]:
        """Get installed OCLP version"""
        oclp_path = self._find_oclp_executable()
        if not oclp_path:
            return None
        
        try:
            result = subprocess.run(
                [str(oclp_path), "--version"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Parse version from output
                version_match = re.search(r"(\d+\.\d+\.\d+)", result.stdout)
                if version_match:
                    return version_match.group(1)
                return result.stdout.strip()
            
        except Exception as e:
            self.logger.error(f"Failed to get OCLP version: {e}")
        
        return None
    
    def analyze_mac_compatibility(self, hardware: DetectedHardware) -> Optional[OCLPConfiguration]:
        """Analyze Mac hardware compatibility with OCLP"""
        if not hardware.system_model:
            self.logger.warning("No Mac model identifier found in hardware data")
            return None
        
        model_identifier = hardware.system_model
        self.logger.info(f"Analyzing OCLP compatibility for: {model_identifier}")
        
        config = self.compatibility_db.get_configuration(model_identifier)
        if config:
            self.logger.info(f"Found OCLP configuration: {config.compatibility.value}")
            return config
        else:
            self.logger.warning(f"No OCLP configuration found for: {model_identifier}")
            # Create a basic unknown configuration
            return OCLPConfiguration(
                model_identifier=model_identifier,
                display_name=f"Unknown Mac ({model_identifier})",
                compatibility=OCLPCompatibility.UNKNOWN,
                notes=["Model not in OCLP database", "Manual configuration may be required"]
            )
    
    def start_oclp_build(self, hardware: DetectedHardware, target_macos_version: Optional[str] = None) -> bool:
        """Start OCLP build process for detected hardware"""
        if not hardware.system_model:
            self.emit_log("ERROR", "No Mac model identifier found")
            return False
        
        # Analyze compatibility
        config = self.analyze_mac_compatibility(hardware)
        if not config or config.compatibility == OCLPCompatibility.UNSUPPORTED:
            self.emit_log("ERROR", f"Mac model {hardware.system_model} is not supported by OCLP")
            return False
        
        # Set up build parameters
        self.target_model = hardware.system_model
        self.target_config = config
        self.target_macos_version = target_macos_version or config.recommended_version
        self.is_cancelled = False
        
        # Start the build thread
        self.start()
        return True
    
    def cancel_build(self):
        """Cancel current OCLP build operation"""
        self.is_cancelled = True
        self.emit_log("INFO", "OCLP build cancelled by user")
    
    def run(self):
        """Main OCLP build thread execution"""
        try:
            self.build_started.emit(self.target_model)
            self.emit_log("INFO", f"Starting OCLP build for {self.target_model}")
            
            # Initialize build result
            start_time = time.time()
            self.current_build = OCLPBuildResult(
                success=False,
                model_identifier=self.target_model,
                oclp_version=self.get_oclp_version() or "unknown",
                build_time=0.0,
                configuration=self.target_config
            )
            
            # Create temporary working directory
            self.temp_dir = Path(tempfile.mkdtemp(prefix="bootforge_oclp_"))
            self.emit_log("INFO", f"Created temporary directory: {self.temp_dir}")
            
            # Execute build steps
            if self._execute_build_workflow():
                # Build successful
                self.current_build.success = True
                self.current_build.build_time = time.time() - start_time
                self.emit_log("INFO", f"OCLP build completed successfully in {self.current_build.build_time:.1f}s")
                self._emit_progress(OCLPBuildStatus.COMPLETED, "Build completed", 100.0)
            else:
                # Build failed
                self.current_build.build_time = time.time() - start_time
                self.emit_log("ERROR", "OCLP build failed")
                self._emit_progress(OCLPBuildStatus.FAILED, "Build failed", 0.0)
            
            # Emit completion signal
            self.build_completed.emit(self.current_build)
            
        except Exception as e:
            self.logger.error(f"OCLP build error: {e}")
            self.emit_log("ERROR", f"OCLP build error: {str(e)}")
            if self.current_build:
                self.current_build.errors.append(str(e))
            self._emit_progress(OCLPBuildStatus.FAILED, f"Error: {str(e)}", 0.0)
        
        finally:
            # Cleanup
            if self.temp_dir and self.temp_dir.exists():
                try:
                    shutil.rmtree(self.temp_dir)
                except Exception as e:
                    self.logger.warning(f"Failed to cleanup temp directory: {e}")
    
    def _execute_build_workflow(self) -> bool:
        """Execute the complete OCLP build workflow"""
        try:
            # Step 1: Initialize and validate
            self._current_step = 1
            self._emit_progress(OCLPBuildStatus.INITIALIZING, "Initializing OCLP build", 5.0)
            if self.is_cancelled or not self._initialize_build():
                return False
            
            # Step 2: Analyze hardware requirements
            self._current_step = 2
            self._emit_progress(OCLPBuildStatus.ANALYZING_HARDWARE, "Analyzing hardware requirements", 15.0)
            if self.is_cancelled or not self._analyze_hardware_requirements():
                return False
            
            # Step 3: Generate OpenCore configuration
            self._current_step = 3
            self._emit_progress(OCLPBuildStatus.GENERATING_CONFIG, "Generating OpenCore configuration", 30.0)
            if self.is_cancelled or not self._generate_opencore_config():
                return False
            
            # Step 4: Build OpenCore EFI
            self._current_step = 4
            self._emit_progress(OCLPBuildStatus.BUILDING_OPENCORE, "Building OpenCore EFI", 60.0)
            if self.is_cancelled or not self._build_opencore_efi():
                return False
            
            # Step 5: Extract and organize files
            self._current_step = 5
            self._emit_progress(OCLPBuildStatus.EXTRACTING_FILES, "Extracting build artifacts", 80.0)
            if self.is_cancelled or not self._extract_build_files():
                return False
            
            # Step 6: Validate build results
            self._current_step = 6
            self._emit_progress(OCLPBuildStatus.EXTRACTING_FILES, "Validating build results", 95.0)
            if self.is_cancelled or not self._validate_build_results():
                return False
            
            # Step 7: Finalize
            self._current_step = 7
            self._emit_progress(OCLPBuildStatus.COMPLETED, "Build completed successfully", 100.0)
            return True
            
        except Exception as e:
            self.logger.error(f"Build workflow error: {e}")
            if self.current_build:
                self.current_build.errors.append(f"Workflow error: {str(e)}")
            return False
    
    def _initialize_build(self) -> bool:
        """Initialize OCLP build environment"""
        try:
            # Check OCLP availability
            availability = self.check_oclp_availability()
            if availability != OCLPAvailability.AVAILABLE:
                self.emit_log("ERROR", f"OCLP not available: {availability.value}")
                return False
            
            # Create build directories
            self.build_output_dir = self.temp_dir / "oclp_output"
            self.build_output_dir.mkdir(exist_ok=True)
            
            self.emit_log("INFO", "OCLP build environment initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Build initialization failed: {e}")
            return False
    
    def _analyze_hardware_requirements(self) -> bool:
        """Analyze hardware requirements and validate configuration"""
        try:
            if not self.target_config:
                self.emit_log("ERROR", "No target configuration available")
                return False
            
            # Log compatibility information
            self.emit_log("INFO", f"Target model: {self.target_config.display_name}")
            self.emit_log("INFO", f"Compatibility: {self.target_config.compatibility.value}")
            
            if self.target_config.compatibility == OCLPCompatibility.EXPERIMENTAL:
                self.emit_log("WARNING", "Experimental support - build may be unstable")
            
            # Validate required patches
            if self.target_config.required_patches:
                self.emit_log("INFO", f"Required patches: {', '.join(self.target_config.required_patches)}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Hardware analysis failed: {e}")
            return False
    
    def _generate_opencore_config(self) -> bool:
        """Generate OpenCore configuration using OCLP"""
        try:
            # Handle platform constraints - OCLP only runs on macOS
            if platform.system().lower() != "darwin":
                self.emit_log("INFO", "Running on non-macOS platform - generating template config")
                return self._generate_template_config()
            
            oclp_path = self._find_oclp_executable()
            if not oclp_path:
                self.emit_log("ERROR", "OCLP executable not found")
                return self._generate_template_config()  # Fallback to template
            
            # Prepare OCLP command with proper arguments
            cmd = [str(oclp_path)]
            
            # Build arguments based on target config
            if self.target_config.build_arguments:
                cmd.extend(self.target_config.build_arguments)
            else:
                # Default build arguments
                cmd.extend(["--build", "--model", self.target_config.model_identifier])
            
            # Add output directory
            cmd.extend(["--output", str(self.build_output_dir)])
            
            # Add macOS version if specified
            if self.target_macos_version:
                cmd.extend(["--version", self.target_macos_version])
            
            self.emit_log("INFO", f"Running OCLP: {' '.join(cmd)}")
            
            # Execute OCLP build command
            result = subprocess.run(
                cmd,
                cwd=str(self.temp_dir),
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout for OCLP builds
            )
            
            # Process and log output
            success = self._process_oclp_output(result)
            
            if success:
                self.emit_log("INFO", "OpenCore configuration generated successfully")
            else:
                self.emit_log("ERROR", "OCLP build failed, attempting template generation")
                return self._generate_template_config()
            
            return success
            
        except subprocess.TimeoutExpired:
            self.emit_log("ERROR", "OCLP build timed out")
            return self._generate_template_config()
        except Exception as e:
            self.logger.error(f"Config generation failed: {e}")
            return self._generate_template_config()
    
    def _build_opencore_efi(self) -> bool:
        """Build OpenCore EFI from generated configuration"""
        try:
            # Look for EFI folder structure first (most common OCLP output)
            efi_folder = self.build_output_dir / "EFI"
            if efi_folder.exists():
                self.current_build.efi_folder_path = efi_folder
                self.emit_log("INFO", f"Found EFI folder: {efi_folder}")
                
                # Verify critical EFI structure
                boot_folder = efi_folder / "BOOT"
                oc_folder = efi_folder / "OC"
                
                if not boot_folder.exists():
                    self.emit_log("ERROR", "EFI/BOOT folder missing from build output")
                    return False
                    
                if not oc_folder.exists():
                    self.emit_log("ERROR", "EFI/OC folder missing from build output")
                    return False
                
                # Look for OpenCore.efi in BOOT folder
                opencore_efi = boot_folder / "BOOTx64.efi"
                if not opencore_efi.exists():
                    opencore_efi = boot_folder / "OpenCore.efi"
                
                if opencore_efi.exists():
                    self.current_build.opencore_efi_path = opencore_efi
                    self.emit_log("INFO", f"Found OpenCore bootloader: {opencore_efi}")
                
                # Look for config.plist
                config_plist = oc_folder / "config.plist"
                if config_plist.exists():
                    self.current_build.config_plist_path = config_plist
                    self.emit_log("INFO", f"Found config.plist: {config_plist}")
                else:
                    self.emit_log("WARNING", "config.plist not found in EFI/OC folder")
                
                # Look for additional OCLP components
                drivers_folder = oc_folder / "Drivers"
                kexts_folder = oc_folder / "Kexts"
                tools_folder = oc_folder / "Tools"
                
                if drivers_folder.exists():
                    self.current_build.drivers_folder_path = drivers_folder
                    driver_count = len(list(drivers_folder.rglob("*.efi")))
                    self.emit_log("INFO", f"Found {driver_count} drivers in EFI/OC/Drivers")
                
                if kexts_folder.exists():
                    kext_files = list(kexts_folder.rglob("*.kext"))
                    self.current_build.kext_files = kext_files
                    self.emit_log("INFO", f"Found {len(kext_files)} kexts in EFI/OC/Kexts")
                
                if tools_folder.exists():
                    self.current_build.tools_folder_path = tools_folder
                    tool_count = len(list(tools_folder.rglob("*.efi")))
                    self.emit_log("INFO", f"Found {tool_count} tools in EFI/OC/Tools")
                
            else:
                # Fallback: look for individual EFI files
                efi_candidates = list(self.build_output_dir.rglob("*.efi"))
                opencore_efi = None
                
                for efi_file in efi_candidates:
                    if "opencore" in efi_file.name.lower() or "bootx64" in efi_file.name.lower():
                        opencore_efi = efi_file
                        break
                
                if opencore_efi:
                    self.current_build.opencore_efi_path = opencore_efi
                    self.emit_log("INFO", f"Found OpenCore EFI: {opencore_efi}")
                else:
                    self.emit_log("ERROR", "No OpenCore EFI files found in build output")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"OpenCore EFI build failed: {e}")
            return False
    
    def _extract_build_files(self) -> bool:
        """Extract and organize build files for USB integration"""
        try:
            # Create organized output structure
            organized_output = self.temp_dir / "bootforge_oclp_build"
            organized_output.mkdir(exist_ok=True)
            
            # Extract EFI folder
            if self.current_build.efi_folder_path:
                efi_dest = organized_output / "EFI"
                shutil.copytree(self.current_build.efi_folder_path, efi_dest, dirs_exist_ok=True)
                self.current_build.efi_folder_path = efi_dest
                self.emit_log("INFO", f"Extracted EFI folder to: {efi_dest}")
            
            # Extract kext files
            kext_files = list(self.build_output_dir.rglob("*.kext"))
            if kext_files:
                kext_dest = organized_output / "Kexts"
                kext_dest.mkdir(exist_ok=True)
                for kext in kext_files:
                    dest_kext = kext_dest / kext.name
                    if kext.is_dir():
                        shutil.copytree(kext, dest_kext, dirs_exist_ok=True)
                    else:
                        shutil.copy2(kext, dest_kext)
                    self.current_build.kext_files.append(dest_kext)
                
                self.emit_log("INFO", f"Extracted {len(kext_files)} kext files")
            
            # Extract drivers
            driver_files = list(self.build_output_dir.rglob("*.efi"))
            driver_files = [f for f in driver_files if "driver" in f.parent.name.lower()]
            if driver_files:
                drivers_dest = organized_output / "Drivers"
                drivers_dest.mkdir(exist_ok=True)
                for driver in driver_files:
                    shutil.copy2(driver, drivers_dest / driver.name)
                
                self.current_build.drivers_folder_path = drivers_dest
                self.emit_log("INFO", f"Extracted {len(driver_files)} driver files")
            
            # Extract tools
            tool_files = list(self.build_output_dir.rglob("*.efi"))
            tool_files = [f for f in tool_files if "tool" in f.parent.name.lower()]
            if tool_files:
                tools_dest = organized_output / "Tools"
                tools_dest.mkdir(exist_ok=True)
                for tool in tool_files:
                    shutil.copy2(tool, tools_dest / tool.name)
                
                self.current_build.tools_folder_path = tools_dest
                self.emit_log("INFO", f"Extracted {len(tool_files)} tool files")
            
            return True
            
        except Exception as e:
            self.logger.error(f"File extraction failed: {e}")
            return False
    
    def _validate_build_results(self) -> bool:
        """Validate OCLP build results"""
        try:
            validation_passed = True
            
            # Check for essential files
            if not self.current_build.efi_folder_path:
                self.emit_log("ERROR", "No EFI folder found in build output")
                validation_passed = False
            
            if not self.current_build.config_plist_path:
                self.emit_log("WARNING", "No config.plist found - build may be incomplete")
            
            # Validate EFI structure
            if self.current_build.efi_folder_path:
                required_paths = [
                    self.current_build.efi_folder_path / "BOOT",
                    self.current_build.efi_folder_path / "OC"
                ]
                
                for required_path in required_paths:
                    if not required_path.exists():
                        self.emit_log("ERROR", f"Missing required EFI component: {required_path.name}")
                        validation_passed = False
            
            # Log validation results
            if validation_passed:
                self.emit_log("INFO", "Build validation passed")
            else:
                self.emit_log("ERROR", "Build validation failed")
            
            return validation_passed
            
        except Exception as e:
            self.logger.error(f"Build validation failed: {e}")
            return False
    
    def _emit_progress(self, status: OCLPBuildStatus, step_name: str, overall_progress: float):
        """Emit progress update signal"""
        progress = OCLPProgress(
            current_status=status,
            step_name=step_name,
            step_number=self._current_step,
            total_steps=self._total_steps,
            step_progress=self._step_progress,
            overall_progress=overall_progress,
            current_operation=step_name
        )
        self.progress_updated.emit(progress)
    
    def emit_log(self, level: str, message: str):
        """Emit log message signal"""
        self.log_message.emit(level, message)
        
        # Also log to standard logger
        log_func = getattr(self.logger, level.lower(), self.logger.info)
        log_func(message)
    
    def _generate_template_config(self) -> bool:
        """Generate template OpenCore configuration for development/testing"""
        try:
            self.emit_log("INFO", "Generating template OpenCore configuration")
            
            # Create template EFI structure
            template_efi = self.build_output_dir / "EFI"
            template_efi.mkdir(exist_ok=True)
            
            # Create BOOT folder with placeholder bootloader
            boot_folder = template_efi / "BOOT"
            boot_folder.mkdir(exist_ok=True)
            
            # Create placeholder BOOTx64.efi (for development)
            bootx64_placeholder = boot_folder / "BOOTx64.efi"
            with open(bootx64_placeholder, 'wb') as f:
                f.write(b'OCLP_TEMPLATE_BOOTLOADER')  # Placeholder content
            
            # Create OC folder structure
            oc_folder = template_efi / "OC"
            oc_folder.mkdir(exist_ok=True)
            
            # Create subdirectories
            for subdir in ["Drivers", "Kexts", "Tools", "ACPI", "Resources"]:
                (oc_folder / subdir).mkdir(exist_ok=True)
            
            # Generate template config.plist based on target configuration
            config_content = self._generate_template_config_plist()
            config_plist = oc_folder / "config.plist"
            with open(config_plist, 'w') as f:
                f.write(config_content)
            
            # Update build result
            self.current_build.efi_folder_path = template_efi
            self.current_build.config_plist_path = config_plist
            self.current_build.opencore_efi_path = bootx64_placeholder
            
            self.emit_log("INFO", "Template configuration generated successfully")
            self.emit_log("WARNING", "Using template config - actual OCLP build requires macOS platform")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Template config generation failed: {e}")
            return False
    
    def _generate_template_config_plist(self) -> str:
        """Generate template config.plist content"""
        if not self.target_config:
            model_id = "Unknown"
            display_name = "Unknown Mac"
            patches = []
        else:
            model_id = self.target_config.model_identifier
            display_name = self.target_config.display_name
            patches = self.target_config.required_patches
        
        # Basic OpenCore config template
        template = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- BootForge Template OpenCore Configuration -->
    <!-- Target Model: {display_name} ({model_id}) -->
    <!-- Generated: {time.strftime("%Y-%m-%d %H:%M:%S")} -->
    
    <key>ACPI</key>
    <dict>
        <key>Add</key>
        <array>
            <!-- ACPI patches will be added here by OCLP -->
        </array>
        <key>Delete</key>
        <array>
        </array>
        <key>Patch</key>
        <array>
        </array>
        <key>Quirks</key>
        <dict>
            <key>FadtEnableReset</key>
            <false/>
            <key>NormalizeHeaders</key>
            <false/>
            <key>RebaseRegions</key>
            <false/>
            <key>ResetHwSig</key>
            <false/>
            <key>ResetLogoStatus</key>
            <false/>
        </dict>
    </dict>
    
    <key>PlatformInfo</key>
    <dict>
        <key>Automatic</key>
        <true/>
        <key>CustomMemory</key>
        <false/>
        <key>Generic</key>
        <dict>
            <key>AdviseWindows</key>
            <false/>
            <key>MaxBIOSVersion</key>
            <false/>
            <key>MLB</key>
            <string>M0000000000000001</string>
            <key>ProcessorType</key>
            <integer>0</integer>
            <key>ROM</key>
            <data>ESIzRFVm</data>
            <key>SpoofVendor</key>
            <true/>
            <key>SystemMemoryStatus</key>
            <string>Auto</string>
            <key>SystemProductName</key>
            <string>{model_id}</string>
            <key>SystemSerialNumber</key>
            <string>W00000000001</string>
            <key>SystemUUID</key>
            <string>00000000-0000-1000-8000-0C2901000001</string>
        </dict>
        <key>UpdateDataHub</key>
        <true/>
        <key>UpdateNVRAM</key>
        <true/>
        <key>UpdateSMBIOS</key>
        <true/>
        <key>UpdateSMBIOSMode</key>
        <string>Create</string>
    </dict>
    
    <key>UEFI</key>
    <dict>
        <key>ConnectDrivers</key>
        <true/>
        <key>Drivers</key>
        <array>
            <string>OpenRuntime.efi</string>
            <!-- Additional drivers will be added here by OCLP -->
        </array>
    </dict>
</dict>
</plist>'''
        
        return template
    
    def _process_oclp_output(self, result: subprocess.CompletedProcess) -> bool:
        """Process OCLP command output and determine success"""
        try:
            success = result.returncode == 0
            
            # Process stdout
            if result.stdout:
                stdout_lines = result.stdout.split('\n')
                self.current_build.build_log.extend(stdout_lines)
                
                for line in stdout_lines:
                    line = line.strip()
                    if not line:
                        continue
                        
                    # Log OCLP output with appropriate levels
                    if any(keyword in line.lower() for keyword in ['error', 'failed', 'exception']):
                        self.current_build.errors.append(line)
                        self.emit_log("ERROR", f"OCLP: {line}")
                        success = False
                    elif any(keyword in line.lower() for keyword in ['warning', 'warn']):
                        self.current_build.warnings.append(line)
                        self.emit_log("WARNING", f"OCLP: {line}")
                    elif any(keyword in line.lower() for keyword in ['success', 'completed', 'generated']):
                        self.emit_log("INFO", f"OCLP: {line}")
                    else:
                        self.emit_log("DEBUG", f"OCLP: {line}")
            
            # Process stderr
            if result.stderr:
                stderr_lines = result.stderr.split('\n')
                for line in stderr_lines:
                    line = line.strip()
                    if not line:
                        continue
                        
                    # Most stderr output from OCLP is errors
                    self.current_build.errors.append(line)
                    self.emit_log("ERROR", f"OCLP Error: {line}")
                    success = False
            
            # Final status based on return code and error analysis
            if result.returncode != 0:
                self.emit_log("ERROR", f"OCLP process failed with exit code {result.returncode}")
                success = False
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to process OCLP output: {e}")
            return False
    
    def get_build_result(self) -> Optional[OCLPBuildResult]:
        """Get the current build result"""
        return self.current_build
    
    def prepare_oclp_build_async(self, hardware: DetectedHardware, progress_callback: Optional[Callable] = None) -> bool:
        """Prepare and start OCLP build asynchronously"""
        try:
            if progress_callback:
                self.progress_updated.connect(progress_callback)
            
            # Start the OCLP build for the detected hardware
            return self.start_oclp_build(hardware)
            
        except Exception as e:
            self.logger.error(f"Failed to prepare async OCLP build: {e}")
            return False
    
    def get_oclp_build_artifacts(self) -> Optional[OCLPBuildResult]:
        """Get OCLP build artifacts if build is complete"""
        if self.current_build and self.current_build.success:
            return self.current_build
        return None
    
    def get_supported_models(self) -> List[str]:
        """Get list of Mac models supported by OCLP"""
        return self.compatibility_db.get_all_supported_models()
    
    def is_model_supported(self, model_identifier: str) -> bool:
        """Check if a Mac model is supported by OCLP"""
        return self.compatibility_db.is_model_supported(model_identifier)


# Integration helper functions for BootForge workflows
class OCLPBootForgeIntegration:
    """Helper class for integrating OCLP with BootForge workflows"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.oclp_integration = OCLPIntegration()
        self.logger.info("OCLP-BootForge integration helper initialized")
    
    def prepare_oclp_build_async(self, hardware: DetectedHardware, progress_callback: Optional[Callable] = None) -> bool:
        """Prepare and start OCLP build asynchronously"""
        return self.oclp_integration.prepare_oclp_build_async(hardware, progress_callback)
    
    def get_oclp_build_artifacts(self) -> Optional[OCLPBuildResult]:
        """Get OCLP build artifacts if build is complete"""
        return self.oclp_integration.get_oclp_build_artifacts()
    
    def auto_detect_and_configure_oclp(self, hardware: DetectedHardware) -> Tuple[bool, Optional[OCLPConfiguration], str]:
        """
        Automatically detect Mac hardware and determine OCLP configuration
        
        Returns:
            Tuple of (is_supported, config, message)
        """
        try:
            # Check if this is a Mac
            if hardware.platform.lower() != "mac" and hardware.system_manufacturer != "Apple":
                return False, None, "Hardware is not a Mac - OCLP not applicable"
            
            # Check OCLP availability
            availability = self.oclp_integration.check_oclp_availability()
            if availability != OCLPAvailability.AVAILABLE:
                return False, None, f"OCLP not available: {availability.value}"
            
            # Analyze compatibility
            config = self.oclp_integration.analyze_mac_compatibility(hardware)
            if not config:
                return False, None, "Unable to determine Mac model compatibility"
            
            if config.compatibility == OCLPCompatibility.UNSUPPORTED:
                return False, config, f"Mac model {config.model_identifier} is not supported by OCLP"
            
            if config.compatibility == OCLPCompatibility.UNKNOWN:
                return False, config, f"Mac model {config.model_identifier} has unknown OCLP compatibility"
            
            # Success cases
            compatibility_messages = {
                OCLPCompatibility.FULLY_SUPPORTED: f"Mac model {config.display_name} is fully supported by OCLP",
                OCLPCompatibility.PARTIALLY_SUPPORTED: f"Mac model {config.display_name} is partially supported by OCLP",
                OCLPCompatibility.EXPERIMENTAL: f"Mac model {config.display_name} has experimental OCLP support"
            }
            
            message = compatibility_messages.get(config.compatibility, "OCLP compatibility determined")
            return True, config, message
            
        except Exception as e:
            self.logger.error(f"Auto-detection failed: {e}")
            return False, None, f"Auto-detection failed: {str(e)}"
    
    def create_oclp_usb_recipe(self, config: OCLPConfiguration, macos_version: str = "13.0") -> Optional['DeploymentRecipe']:
        """
        Create a customized USB deployment recipe for OCLP
        
        Args:
            config: OCLP configuration for the target Mac
            macos_version: Target macOS version
            
        Returns:
            Customized DeploymentRecipe for OCLP deployment
        """
        try:
            from src.core.usb_builder import DeploymentRecipe, DeploymentType, PartitionScheme, PartitionInfo, FileSystem
            
            # Create customized recipe based on Mac model
            recipe_name = f"macOS {macos_version} with OCLP for {config.display_name}"
            
            # Adjust partition sizes based on compatibility
            oclp_tools_size = 1024  # Default 1GB
            if config.compatibility == OCLPCompatibility.EXPERIMENTAL:
                oclp_tools_size = 2048  # 2GB for experimental models (more debugging tools)
            
            partitions = [
                PartitionInfo("EFI", 200, FileSystem.FAT32, bootable=True, label="EFI"),
                PartitionInfo("macOS Installer", -1, FileSystem.HFS_PLUS, label="Install macOS"),
                PartitionInfo("OCLP Tools", oclp_tools_size, FileSystem.FAT32, label="OCLP-Tools")
            ]
            
            # Add model-specific requirements
            required_files = ["macOS_installer.app", "OpenCore-Legacy-Patcher.app"]
            optional_files = []
            verification_steps = ["verify_efi_boot", "verify_oclp_installation"]
            
            # Add model-specific files and verification
            if config.required_patches:
                optional_files.append("additional_kexts.zip")
                verification_steps.append("verify_kexts")
            
            if config.wifi_patches:
                optional_files.append("wifi_drivers.zip")
                verification_steps.append("verify_wifi_drivers")
            
            recipe = DeploymentRecipe(
                name=recipe_name,
                description=f"Create bootable macOS {macos_version} installer with OCLP for {config.display_name}",
                deployment_type=DeploymentType.MACOS_OCLP,
                partition_scheme=PartitionScheme.GPT,
                partitions=partitions,
                hardware_profiles=[config.model_identifier],
                required_files=required_files,
                optional_files=optional_files,
                verification_steps=verification_steps,
                metadata={
                    "oclp_config": config.model_identifier,
                    "compatibility": config.compatibility.value,
                    "macos_version": macos_version,
                    "required_patches": config.required_patches,
                    "notes": config.notes
                }
            )
            
            self.logger.info(f"Created OCLP USB recipe for {config.display_name}")
            return recipe
            
        except Exception as e:
            self.logger.error(f"Failed to create OCLP USB recipe: {e}")
            return None
    
    def prepare_oclp_build_async(self, hardware: DetectedHardware, progress_callback: Optional[Callable] = None) -> bool:
        """
        Prepare and start an async OCLP build process
        
        Args:
            hardware: Detected hardware information
            progress_callback: Optional callback for progress updates
            
        Returns:
            True if build started successfully, False otherwise
        """
        try:
            # Connect progress callback if provided
            if progress_callback:
                self.oclp_integration.progress_updated.connect(progress_callback)
            
            # Start OCLP build
            success = self.oclp_integration.start_oclp_build(hardware)
            if success:
                self.logger.info("OCLP build started successfully")
            else:
                self.logger.error("Failed to start OCLP build")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to prepare OCLP build: {e}")
            return False
    
    def get_oclp_build_artifacts(self) -> Optional[OCLPBuildResult]:
        """
        Get the artifacts from the most recent OCLP build
        
        Returns:
            OCLPBuildResult with build artifacts, or None if no build available
        """
        return self.oclp_integration.get_build_result()
    
    def validate_mac_for_oclp(self, hardware: DetectedHardware) -> Tuple[bool, List[str], List[str]]:
        """
        Validate a Mac's readiness for OCLP deployment
        
        Args:
            hardware: Detected hardware information
            
        Returns:
            Tuple of (is_ready, requirements_met, requirements_missing)
        """
        requirements_met = []
        requirements_missing = []
        
        try:
            # Check basic requirements
            if hardware.platform.lower() == "mac" or hardware.system_manufacturer == "Apple":
                requirements_met.append("Mac hardware detected")
            else:
                requirements_missing.append("Mac hardware required")
                return False, requirements_met, requirements_missing
            
            # Check model identification
            if hardware.system_model:
                requirements_met.append(f"Mac model identified: {hardware.system_model}")
            else:
                requirements_missing.append("Mac model identification required")
            
            # Check OCLP compatibility
            config = self.oclp_integration.analyze_mac_compatibility(hardware)
            if config and config.compatibility != OCLPCompatibility.UNSUPPORTED:
                requirements_met.append(f"OCLP compatible: {config.compatibility.value}")
            else:
                requirements_missing.append("OCLP compatibility required")
            
            # Check OCLP availability
            availability = self.oclp_integration.check_oclp_availability()
            if availability == OCLPAvailability.AVAILABLE:
                requirements_met.append("OCLP installation detected")
            else:
                requirements_missing.append(f"OCLP installation required: {availability.value}")
            
            # Check system requirements
            if hardware.total_ram_gb and hardware.total_ram_gb >= 4.0:
                requirements_met.append("Sufficient RAM detected")
            else:
                requirements_missing.append("Minimum 4GB RAM required")
            
            # Additional checks based on Mac model
            if config:
                if config.requires_sip_disable:
                    requirements_missing.append("SIP (System Integrity Protection) must be disabled")
                
                if config.requires_root_patch:
                    requirements_missing.append("Root patches required - ensure backup available")
            
            is_ready = len(requirements_missing) == 0
            return is_ready, requirements_met, requirements_missing
            
        except Exception as e:
            self.logger.error(f"Mac validation failed: {e}")
            requirements_missing.append(f"Validation error: {str(e)}")
            return False, requirements_met, requirements_missing
    
    def get_recommended_macos_version(self, config: OCLPConfiguration) -> str:
        """
        Get recommended macOS version for a Mac model
        
        Args:
            config: OCLP configuration
            
        Returns:
            Recommended macOS version string
        """
        if config.recommended_version:
            return config.recommended_version
        
        # Default recommendations based on compatibility
        if config.compatibility == OCLPCompatibility.FULLY_SUPPORTED:
            return "13.0"  # macOS Ventura
        elif config.compatibility == OCLPCompatibility.PARTIALLY_SUPPORTED:
            return "12.0"  # macOS Monterey
        elif config.compatibility == OCLPCompatibility.EXPERIMENTAL:
            return "11.0"  # macOS Big Sur
        else:
            return "12.0"  # Safe default
    
    def cleanup_oclp_resources(self):
        """Clean up OCLP integration resources"""
        try:
            if hasattr(self.oclp_integration, 'temp_dir') and self.oclp_integration.temp_dir:
                if self.oclp_integration.temp_dir.exists():
                    shutil.rmtree(self.oclp_integration.temp_dir)
                    self.logger.info("Cleaned up OCLP temporary resources")
        except Exception as e:
            self.logger.warning(f"Failed to cleanup OCLP resources: {e}")


# Convenience functions for easy integration
def detect_mac_and_check_oclp_support(hardware: DetectedHardware) -> Dict[str, Any]:
    """
    Convenience function to detect Mac and check OCLP support
    
    Args:
        hardware: DetectedHardware from BootForge hardware detection
        
    Returns:
        Dictionary with detection results and recommendations
    """
    integration = OCLPBootForgeIntegration()
    
    # Auto-detect and configure
    is_supported, config, message = integration.auto_detect_and_configure_oclp(hardware)
    
    # Validate readiness
    is_ready, requirements_met, requirements_missing = integration.validate_mac_for_oclp(hardware)
    
    # Get recommended version
    recommended_version = None
    if config:
        recommended_version = integration.get_recommended_macos_version(config)
    
    return {
        "is_supported": is_supported,
        "is_ready": is_ready,
        "config": config,
        "message": message,
        "requirements_met": requirements_met,
        "requirements_missing": requirements_missing,
        "recommended_macos_version": recommended_version,
        "oclp_version": integration.oclp_integration.get_oclp_version()
    }


def create_oclp_deployment_recipe(hardware: DetectedHardware, macos_version: Optional[str] = None) -> Optional['DeploymentRecipe']:
    """
    Convenience function to create OCLP deployment recipe from detected hardware
    
    Args:
        hardware: DetectedHardware from BootForge hardware detection
        macos_version: Optional target macOS version
        
    Returns:
        DeploymentRecipe for OCLP USB creation, or None if not supported
    """
    integration = OCLPBootForgeIntegration()
    
    # Check support
    is_supported, config, _ = integration.auto_detect_and_configure_oclp(hardware)
    if not is_supported or not config:
        return None
    
    # Use recommended version if not specified
    if not macos_version:
        macos_version = integration.get_recommended_macos_version(config)
    
    # Create recipe
    return integration.create_oclp_usb_recipe(config, macos_version)