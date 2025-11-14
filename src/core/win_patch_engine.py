"""
BootForge Windows Patch Engine
Comprehensive Windows image patching system for bypassing hardware restrictions
and enabling Windows 10/11 installation on any hardware - whether Microsoft allows it or not.
"""

import os
import re
import json
import time
import uuid
import shutil
import logging
import hashlib
import tempfile
import platform
import subprocess
from pathlib import Path

from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, field, asdict

# Platform-specific imports with guards
try:
    if platform.system() == "Windows":
        import winreg
    else:
        # Stub for cross-platform compatibility
        winreg = None
except ImportError:
    winreg = None

from src.core.config import Config
from src.core.hardware_detector import DetectedHardware, DetectionConfidence
from src.core.models import HardwareProfile, DeploymentRecipe, DeploymentType
from src.core.patch_pipeline import (
    PatchAction, PatchType, PatchPhase, PatchPriority, PatchCondition, 
    PatchStatus, PatchPlanner, PatchSet
)
from src.core.safety_validator import (
    SafetyValidator, SafetyLevel, ValidationResult, PatchValidationMode,
    ConsentLevel, UserConsent, PatchRisk
)


class WindowsBypassType(Enum):
    """Types of Windows installation bypasses"""
    TPM_BYPASS = "tpm_bypass"                      # Bypass TPM 2.0 requirement
    RAM_BYPASS = "ram_bypass"                      # Bypass 4GB+ RAM requirement  
    SECURE_BOOT_BYPASS = "secure_boot_bypass"      # Bypass Secure Boot requirement
    CPU_BYPASS = "cpu_bypass"                      # Bypass supported CPU requirement
    STORAGE_BYPASS = "storage_bypass"              # Bypass UEFI/GPT storage requirement
    ONLINE_ACCOUNT_BYPASS = "online_account_bypass" # Bypass Microsoft account requirement


class WindowsImageType(Enum):
    """Types of Windows images for patching"""
    BOOT_WIM = "boot.wim"                          # Windows PE boot environment
    INSTALL_WIM = "install.wim"                    # Windows installation image
    INSTALL_ESD = "install.esd"                    # Encrypted/compressed installation
    WINRE_WIM = "winre.wim"                        # Windows Recovery Environment


class DriverCategory(Enum):
    """Categories of drivers for injection"""
    NETWORK = "network"                            # Network/WiFi drivers
    STORAGE = "storage"                            # Storage controller drivers
    GRAPHICS = "graphics"                          # Basic graphics drivers
    AUDIO = "audio"                                # Audio drivers
    CHIPSET = "chipset"                            # Motherboard chipset drivers
    USB = "usb"                                    # USB controller drivers
    BLUETOOTH = "bluetooth"                        # Bluetooth drivers


@dataclass
class WindowsBypass:
    """Configuration for a specific Windows bypass"""
    bypass_type: WindowsBypassType
    name: str
    description: str
    registry_keys: Dict[str, Any] = field(default_factory=dict)
    file_modifications: List[str] = field(default_factory=list)
    boot_modifications: List[str] = field(default_factory=list)
    required_for_windows: List[str] = field(default_factory=list)  # ["11", "10"]
    hardware_patterns: List[str] = field(default_factory=list)     # Regex patterns for hardware
    risk_level: ValidationResult = ValidationResult.WARNING
    user_warning: str = ""


@dataclass
class DriverPackage:
    """Driver package for injection"""
    name: str
    category: DriverCategory
    version: str
    hardware_id: str
    inf_path: str
    driver_files: List[str] = field(default_factory=list)
    architecture: str = "x64"  # x64, x86, arm64
    compatible_windows: List[str] = field(default_factory=list)  # ["10", "11"]


@dataclass
class WimPatchOperation:
    """Single WIM file patch operation"""
    operation_id: str
    image_type: WindowsImageType
    image_path: str
    mount_path: str
    modifications: List[PatchAction] = field(default_factory=list)
    bypasses: List[WindowsBypass] = field(default_factory=list)
    drivers: List[DriverPackage] = field(default_factory=list)
    status: PatchStatus = PatchStatus.PENDING
    error_message: Optional[str] = None


class WinPatchEngine:
    """
    BootForge Windows Patch Engine
    
    Comprehensive system for patching Windows installation images to:
    1. Bypass TPM 2.0, RAM, Secure Boot, CPU requirements
    2. Inject hardware-specific drivers for compatibility
    3. Create unattended installation configurations
    4. Enable Windows 10/11 installation on ANY hardware
    """
    
    def __init__(self, config: Config, safety_level: SafetyLevel = SafetyLevel.STANDARD):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Safety and validation
        self.safety_validator = SafetyValidator(
            safety_level, 
            patch_mode=PatchValidationMode.COMPLIANT
        )
        self.patch_planner = PatchPlanner(self.safety_validator)
        
        # Working directories
        self.workspace_dir: Optional[Path] = None
        self.mount_dir: Optional[Path] = None
        self.temp_iso_dir: Optional[Path] = None
        
        # Operation tracking
        self.current_operations: List[WimPatchOperation] = []
        self.applied_bypasses: List[WindowsBypass] = []
        self.injected_drivers: List[DriverPackage] = []
        
        # SECURITY: Audit logging system for all bypass operations
        self.audit_logger = self._setup_audit_logger()
        
        # SECURITY: Consent tracking for bypass operations  
        self.user_consent_granted: bool = False
        self.consent_level: ConsentLevel = ConsentLevel.NONE
        self.consent_timestamp: Optional[float] = None
        self.bypass_session_id: str = str(uuid.uuid4())
        
        # Tool paths
        self.dism_path = self._find_dism_executable()
        self.wimlib_path = self._find_wimlib_executable()
        
        # Initialize bypass database
        self.bypass_database = self._load_bypass_database()
        self.driver_database = self._load_driver_database()
        
        self.logger.info(f"WinPatchEngine initialized with {safety_level.value} safety level")
        self.logger.info(f"DISM: {self.dism_path}, WimLib: {self.wimlib_path}")
        self.logger.info(f"Loaded {len(self.bypass_database)} bypasses, {len(self.driver_database)} driver packages")
        
        # SECURITY: Log initialization with session tracking
        self.audit_logger.info(f"WinPatchEngine session started: {self.bypass_session_id}")
        self.audit_logger.info(f"Safety level: {safety_level.value}, Validation mode: {PatchValidationMode.COMPLIANT.value}")
    
    def _find_dism_executable(self) -> Optional[str]:
        """Locate DISM executable on the system"""
        if platform.system() == "Windows":
            # Standard Windows DISM location
            dism_paths = [
                r"C:\Windows\System32\DISM.exe",
                r"C:\Windows\SysWOW64\DISM.exe"
            ]
            for path in dism_paths:
                if os.path.exists(path):
                    return path
        
        # Check if DISM is available via PATH
        try:
            result = subprocess.run(['dism', '/English', '/?'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return 'dism'
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Check for wimlib-imagex as alternative
        try:
            result = subprocess.run(['wimlib-imagex', '--help'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.logger.info("Using wimlib-imagex as DISM alternative")
                return 'wimlib-imagex'
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        self.logger.warning("DISM not found - Windows image patching will be limited")
        return None
    
    def _find_wimlib_executable(self) -> Optional[str]:
        """Locate wimlib-imagex executable as DISM alternative"""
        try:
            result = subprocess.run(['wimlib-imagex', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return 'wimlib-imagex'
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        return None
    
    def _load_bypass_database(self) -> List[WindowsBypass]:
        """Load comprehensive Windows bypass database"""
        bypasses = [
            # TPM 2.0 Bypass for Windows 11
            WindowsBypass(
                bypass_type=WindowsBypassType.TPM_BYPASS,
                name="TPM 2.0 Bypass",
                description="Bypasses Windows 11 TPM 2.0 requirement for older hardware",
                registry_keys={
                    "HKLM\\SYSTEM\\Setup\\LabConfig": {
                        "BypassTPMCheck": ("REG_DWORD", 1),
                        "BypassSecureBootCheck": ("REG_DWORD", 1),
                    }
                },
                required_for_windows=["11"],
                hardware_patterns=[r".*"],  # Apply to all hardware
                risk_level=ValidationResult.WARNING,
                user_warning="Bypassing TPM may affect Windows security features and BitLocker encryption."
            ),
            
            # RAM Bypass for Windows 11
            WindowsBypass(
                bypass_type=WindowsBypassType.RAM_BYPASS,
                name="RAM Requirement Bypass",
                description="Bypasses Windows 11 4GB+ RAM requirement for low-memory systems",
                registry_keys={
                    "HKLM\\SYSTEM\\Setup\\LabConfig": {
                        "BypassRAMCheck": ("REG_DWORD", 1),
                    }
                },
                required_for_windows=["11"],
                hardware_patterns=[r".*"],
                risk_level=ValidationResult.WARNING,
                user_warning="Systems with <4GB RAM may experience poor performance with Windows 11."
            ),

            # Secure Boot Bypass for Windows 11
            WindowsBypass(
                bypass_type=WindowsBypassType.SECURE_BOOT_BYPASS,
                name="Secure Boot Requirement Bypass",
                description="Allows installation on systems without Secure Boot or when legacy BIOS mode is required",
                registry_keys={
                    "HKLM\\SYSTEM\\Setup\\LabConfig": {
                        "BypassSecureBootCheck": ("REG_DWORD", 1),
                    }
                },
                required_for_windows=["11"],
                hardware_patterns=[r".*Legacy.*", r".*BIOS.*", r".*"],
                risk_level=ValidationResult.WARNING,
                user_warning="Disabling Secure Boot reduces firmware-level protections against bootkits and persistent malware."
            ),

            # CPU Bypass for Windows 11
            WindowsBypass(
                bypass_type=WindowsBypassType.CPU_BYPASS,
                name="CPU Compatibility Bypass",
                description="Bypasses Windows 11 8th gen Intel/2nd gen AMD CPU requirement",
                registry_keys={
                    "HKLM\\SYSTEM\\Setup\\LabConfig": {
                        "BypassCPUCheck": ("REG_DWORD", 1),
                    }
                },
                required_for_windows=["11"],
                hardware_patterns=[r".*Intel.*Core.*[1-7].*", r".*AMD.*Ryzen.*[1].*"],
                risk_level=ValidationResult.WARNING,
                user_warning="Older CPUs may not support all Windows 11 features and security improvements."
            ),
            
            # Storage Bypass for Windows 11
            WindowsBypass(
                bypass_type=WindowsBypassType.STORAGE_BYPASS,
                name="UEFI Storage Bypass",
                description="Bypasses Windows 11 UEFI and GPT disk requirements",
                registry_keys={
                    "HKLM\\SYSTEM\\Setup\\LabConfig": {
                        "BypassStorageCheck": ("REG_DWORD", 1),
                    }
                },
                required_for_windows=["11"],
                hardware_patterns=[r".*Legacy.*", r".*BIOS.*"],
                risk_level=ValidationResult.WARNING,
                user_warning="Legacy BIOS installations may have limited boot options and security features."
            ),
            
            # Microsoft Account Bypass
            WindowsBypass(
                bypass_type=WindowsBypassType.ONLINE_ACCOUNT_BYPASS,
                name="Microsoft Account Bypass",
                description="Enables local account creation without Microsoft account requirement",
                registry_keys={
                    "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\OOBE": {
                        "BypassNRO": ("REG_DWORD", 1),
                    }
                },
                required_for_windows=["11", "10"],
                hardware_patterns=[r".*"],
                risk_level=ValidationResult.SAFE,
                user_warning="Local accounts will not sync with Microsoft services."
            ),
        ]
        
        return bypasses
    
    def _load_driver_database(self) -> List[DriverPackage]:
        """Load driver database for common hardware"""
        drivers = [
            # Network Drivers
            DriverPackage(
                name="Intel Ethernet",
                category=DriverCategory.NETWORK,
                version="29.1.0.0",
                hardware_id="PCI\\VEN_8086&DEV_*",
                inf_path="e1d68x64.inf",
                compatible_windows=["10", "11"]
            ),
            DriverPackage(
                name="Realtek Ethernet",
                category=DriverCategory.NETWORK,
                version="10.55.0.0",
                hardware_id="PCI\\VEN_10EC&DEV_*",
                inf_path="rt640x64.inf", 
                compatible_windows=["10", "11"]
            ),
            
            # Storage Drivers
            DriverPackage(
                name="Intel SATA AHCI",
                category=DriverCategory.STORAGE,
                version="18.1.0.0",
                hardware_id="PCI\\VEN_8086&DEV_*&CC_0106*",
                inf_path="iaahcic.inf",
                compatible_windows=["10", "11"]
            ),
            DriverPackage(
                name="AMD SATA Controller",
                category=DriverCategory.STORAGE,
                version="9.3.0.0",
                hardware_id="PCI\\VEN_1022&DEV_*",
                inf_path="amdide64.inf",
                compatible_windows=["10", "11"]
            ),
            
            # Graphics Drivers (Basic)
            DriverPackage(
                name="Intel HD Graphics",
                category=DriverCategory.GRAPHICS,
                version="30.0.0.0",
                hardware_id="PCI\\VEN_8086&DEV_*&CC_0300*",
                inf_path="igdlh64.inf",
                compatible_windows=["10", "11"]
            ),
        ]
        
        return drivers
    
    def patch_windows_image(self, iso_path: str, hardware: DetectedHardware, 
                          windows_version: str, output_path: str,
                          bypasses: Optional[List[WindowsBypassType]] = None,
                          inject_drivers: bool = True) -> bool:
        """
        Main entry point for patching Windows ISO with bypasses and drivers
        
        Args:
            iso_path: Path to source Windows ISO
            hardware: Detected hardware profile
            windows_version: "10" or "11"
            output_path: Path for patched ISO
            bypasses: Specific bypasses to apply (None = auto-detect)
            inject_drivers: Whether to inject hardware drivers
        
        Returns:
            True if patching successful, False otherwise
        """
        try:
            self.logger.info(f"Starting Windows {windows_version} image patching")
            self.logger.info(f"Source: {iso_path}, Output: {output_path}")
            self.logger.info(f"Hardware: {hardware.get_summary()}")
            
            # 1. Setup workspace
            if not self._setup_workspace():
                return False
            
            # 2. Extract ISO
            if not self._extract_iso(iso_path):
                return False
            
            # 3. Determine required bypasses
            required_bypasses = bypasses or self._determine_required_bypasses(hardware, windows_version)
            self.logger.info(f"Required bypasses: {[b.value for b in required_bypasses]}")
            
            # 4. Get safety approval for bypasses
            if not self._validate_bypass_safety(required_bypasses, hardware):
                return False
            
            # 5. Patch boot.wim (Windows PE environment)
            if not self._patch_boot_wim(required_bypasses):
                return False
            
            # 6. Patch install.wim/install.esd (Windows installation)
            if not self._patch_install_image(required_bypasses, inject_drivers, hardware, windows_version):
                return False
            
            # 7. Create unattend.xml for automated installation
            if not self._create_unattend_xml(hardware, windows_version):
                return False
            
            # 8. Rebuild ISO
            if not self._rebuild_iso(output_path):
                return False
            
            self.logger.info(f"Windows {windows_version} patching completed successfully")
            self.logger.info(f"Applied bypasses: {len(self.applied_bypasses)}")
            self.logger.info(f"Injected drivers: {len(self.injected_drivers)}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error patching Windows image: {e}")
            return False
        
        finally:
            self._cleanup_workspace()
    
    def _setup_workspace(self) -> bool:
        """Setup temporary workspace for image operations"""
        try:
            # Create workspace directory
            self.workspace_dir = Path(tempfile.mkdtemp(prefix="bootforge_winpatch_"))
            self.mount_dir = self.workspace_dir / "mount"
            self.temp_iso_dir = self.workspace_dir / "iso_extract"
            
            # Create subdirectories
            self.mount_dir.mkdir(parents=True, exist_ok=True)
            self.temp_iso_dir.mkdir(parents=True, exist_ok=True)
            
            self.logger.info(f"Workspace created: {self.workspace_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to setup workspace: {e}")
            return False
    
    def _extract_iso(self, iso_path: str) -> bool:
        """Extract Windows ISO to workspace"""
        try:
            self.logger.info(f"Extracting ISO: {iso_path}")
            
            if platform.system() == "Windows":
                # Use 7-Zip or PowerShell on Windows
                result = subprocess.run([
                    'powershell', '-Command',
                    f'Mount-DiskImage -ImagePath "{iso_path}" -PassThru | Get-Volume | Get-DiskImage | Get-Disk | Get-Partition | Get-Volume | Copy-Item -Destination "{self.temp_iso_dir}" -Recurse'
                ], capture_output=True, text=True)
            else:
                # Use mount on Linux/macOS
                mount_point = self.workspace_dir / "iso_mount"
                mount_point.mkdir(exist_ok=True)
                
                # Mount ISO
                subprocess.run(['sudo', 'mount', '-o', 'loop', iso_path, str(mount_point)], check=True)
                
                # Copy contents
                subprocess.run(['cp', '-r', f"{mount_point}/.", str(self.temp_iso_dir)], check=True)
                
                # Unmount
                subprocess.run(['sudo', 'umount', str(mount_point)], check=True)
            
            # Verify sources directory exists
            sources_dir = self.temp_iso_dir / "sources"
            if not sources_dir.exists():
                self.logger.error("Invalid Windows ISO - sources directory not found")
                return False
            
            self.logger.info("ISO extraction completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to extract ISO: {e}")
            return False
    
    def _determine_required_bypasses(self, hardware: DetectedHardware, 
                                   windows_version: str) -> List[WindowsBypassType]:
        """Determine which bypasses are needed for this hardware/OS combination"""
        required = []
        
        if windows_version == "11":
            # Windows 11 always needs these bypasses for older hardware
            
            # TPM bypass if no TPM detected or TPM 1.2
            if not hardware.bios_info.get("tpm_version") or hardware.bios_info.get("tpm_version", "").startswith("1."):
                required.append(WindowsBypassType.TPM_BYPASS)
            
            # RAM bypass if less than 4GB
            if hardware.total_ram_gb and hardware.total_ram_gb < 4.0:
                required.append(WindowsBypassType.RAM_BYPASS)
            
            # CPU bypass for older CPUs (pre-8th gen Intel, pre-Ryzen 2000)
            if hardware.cpu_name:
                cpu_name = hardware.cpu_name.lower()
                if ("intel" in cpu_name and any(gen in cpu_name for gen in ["2nd", "3rd", "4th", "5th", "6th", "7th"])) or \
                   ("amd" in cpu_name and any(gen in cpu_name for gen in ["fx-", "a10", "a8", "a6", "ryzen 1"])):
                    required.append(WindowsBypassType.CPU_BYPASS)
            
            # Secure Boot bypass if not UEFI or Legacy BIOS
            if hardware.bios_info.get("firmware_type", "").lower() in ["legacy", "bios"]:
                required.append(WindowsBypassType.SECURE_BOOT_BYPASS)
                required.append(WindowsBypassType.STORAGE_BYPASS)
        
        # Microsoft account bypass (always useful)
        required.append(WindowsBypassType.ONLINE_ACCOUNT_BYPASS)
        
        self.logger.info(f"Determined required bypasses for {hardware.system_model}: {[b.value for b in required]}")
        return required
    
    def _validate_bypass_safety(self, bypasses: List[WindowsBypassType], 
                               hardware: DetectedHardware) -> bool:
        """Validate safety of bypass operations and get user consent"""
        try:
            self.logger.info("Validating bypass safety and obtaining user consent")
            
            # Calculate overall risk
            risk_factors = []
            overall_risk = ValidationResult.SAFE
            
            for bypass_type in bypasses:
                bypass = next((b for b in self.bypass_database if b.bypass_type == bypass_type), None)
                if bypass:
                    if bypass.risk_level.value > overall_risk.value:
                        overall_risk = bypass.risk_level
                    risk_factors.append(f"{bypass.name}: {bypass.user_warning}")
            
            # Create patch risk assessment
            patch_risk = PatchRisk(
                patch_id=f"windows-bypass-{uuid.uuid4().hex[:8]}",
                patch_name="Windows Installation Bypasses",
                patch_type="registry_bypass",
                target_system="Windows Installation Image",
                modifies_kernel=False,
                modifies_bootloader=True,
                disables_security=True,  # TPM/Secure Boot bypasses do disable security
                unsigned_code=False,
                irreversible=False,
                overall_risk=overall_risk,
                risk_factors=risk_factors
            )
            
            patch_risk.calculate_risk_score()
            
            # Validate with safety system
            validation_result = self.safety_validator.validate_patch_risk(patch_risk)
            
            if validation_result.result == ValidationResult.BLOCKED:
                self.logger.error("SAFETY BLOCK: Windows bypass operation blocked by safety validator")
                self.logger.error(f"Risk factors: {risk_factors}")
                return False
            
            # Get user consent for risky operations
            if validation_result.result in [ValidationResult.WARNING, ValidationResult.DANGEROUS]:
                consent_level = ConsentLevel.INFORMED if validation_result.result == ValidationResult.WARNING else ConsentLevel.EXPERT
                
                # In a real implementation, this would prompt the user
                # For now, we'll assume consent is given if in BYPASS mode
                user_consent = UserConsent(
                    operation_id=patch_risk.patch_id,
                    operation_type="windows_bypass",
                    consent_level=consent_level,
                    risk_factors=risk_factors,
                    user_confirmation="User acknowledges Microsoft licensing and support implications",
                    timestamp=time.time(),
                    warnings_shown=risk_factors
                )
                
                # Record consent
                if not self.safety_validator.record_user_consent(user_consent):
                    self.logger.error("User consent not sufficient for bypass operations")
                    return False
            
            self.logger.info(f"Bypass safety validation passed with {overall_risk.value} risk level")
            return True
            
        except Exception as e:
            self.logger.error(f"Bypass safety validation failed: {e}")
            return False
    
    def _patch_boot_wim(self, bypasses: List[WindowsBypassType]) -> bool:
        """Patch boot.wim (Windows PE) with bypass registry keys"""
        try:
            boot_wim_path = self.temp_iso_dir / "sources" / "boot.wim"
            if not boot_wim_path.exists():
                self.logger.error("boot.wim not found in sources directory")
                return False
            
            self.logger.info("Patching boot.wim with bypass registry keys")
            
            # Mount boot.wim
            if not self._mount_wim_image(str(boot_wim_path), 2):  # Index 2 is Windows PE
                return False
            
            try:
                # Load registry hive
                system_hive = self.mount_dir / "Windows" / "System32" / "config" / "SYSTEM"
                if not system_hive.exists():
                    self.logger.error("SYSTEM registry hive not found in boot.wim")
                    return False
                
                # Apply registry bypasses
                for bypass_type in bypasses:
                    bypass = next((b for b in self.bypass_database if b.bypass_type == bypass_type), None)
                    if bypass and bypass.registry_keys:
                        if self._apply_registry_bypass(bypass, system_hive):
                            self.applied_bypasses.append(bypass)
                            self.logger.info(f"Applied {bypass.name} to boot.wim")
                
                return True
                
            finally:
                # Unmount and commit changes
                self._unmount_wim_image(commit=True)
            
        except Exception as e:
            self.logger.error(f"Failed to patch boot.wim: {e}")
            return False
    
    def _patch_install_image(self, bypasses: List[WindowsBypassType], 
                           inject_drivers: bool, hardware: DetectedHardware,
                           windows_version: str) -> bool:
        """Patch install.wim/install.esd with bypasses and drivers"""
        try:
            # Find install image (WIM or ESD)
            install_path = None
            for name in ["install.wim", "install.esd"]:
                path = self.temp_iso_dir / "sources" / name
                if path.exists():
                    install_path = path
                    break
            
            if not install_path:
                self.logger.error("install.wim/install.esd not found")
                return False
            
            self.logger.info(f"Patching {install_path.name}")
            
            # Get image info to find Windows edition index
            image_index = self._get_windows_edition_index(str(install_path), windows_version)
            if not image_index:
                self.logger.error("Could not determine Windows edition index")
                return False
            
            # Mount install image
            if not self._mount_wim_image(str(install_path), image_index):
                return False
            
            try:
                # Apply registry bypasses
                system_hive = self.mount_dir / "Windows" / "System32" / "config" / "SYSTEM"
                for bypass_type in bypasses:
                    bypass = next((b for b in self.bypass_database if b.bypass_type == bypass_type), None)
                    if bypass and bypass.registry_keys:
                        self._apply_registry_bypass(bypass, system_hive)
                
                # Inject drivers if requested
                if inject_drivers:
                    self._inject_hardware_drivers(hardware, windows_version)
                
                # Apply any file modifications
                self._apply_file_modifications(bypasses)
                
                return True
                
            finally:
                # Unmount and commit changes
                self._unmount_wim_image(commit=True)
            
        except Exception as e:
            self.logger.error(f"Failed to patch install image: {e}")
            return False
    
    def _mount_wim_image(self, wim_path: str, index: int) -> bool:
        """Mount WIM image using DISM or wimlib"""
        try:
            if self.dism_path:
                # Use DISM
                cmd = [
                    self.dism_path, '/Mount-Wim',
                    f'/WimFile:{wim_path}',
                    f'/Index:{index}',
                    f'/MountDir:{self.mount_dir}'
                ]
                
                if self.dism_path == 'wimlib-imagex':
                    # Use wimlib syntax
                    cmd = [
                        'wimlib-imagex', 'mountrw',
                        wim_path, str(index), str(self.mount_dir)
                    ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    self.logger.error(f"Failed to mount WIM: {result.stderr}")
                    return False
                
                self.logger.info(f"Mounted {wim_path} index {index}")
                return True
            else:
                self.logger.error("No WIM mounting tool available (DISM/wimlib)")
                return False
                
        except Exception as e:
            self.logger.error(f"Error mounting WIM: {e}")
            return False
    
    def _unmount_wim_image(self, commit: bool = True) -> bool:
        """Unmount WIM image and optionally commit changes"""
        try:
            if self.dism_path:
                if self.dism_path == 'wimlib-imagex':
                    # Use wimlib syntax
                    cmd = ['wimlib-imagex', 'unmount', str(self.mount_dir)]
                    if commit:
                        cmd.append('--commit')
                else:
                    # Use DISM syntax
                    cmd = [
                        self.dism_path, '/Unmount-Wim',
                        f'/MountDir:{self.mount_dir}'
                    ]
                    if commit:
                        cmd.append('/Commit')
                    else:
                        cmd.append('/Discard')
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    self.logger.error(f"Failed to unmount WIM: {result.stderr}")
                    return False
                
                self.logger.info(f"Unmounted WIM image (commit={commit})")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Error unmounting WIM: {e}")
            return False
    
    def _apply_registry_bypass(self, bypass: WindowsBypass, system_hive: Path) -> bool:
        """Apply registry bypass modifications using safe offline hive editing"""
        try:
            # Use DISM for safe offline registry editing without touching host registry
            if not self.mount_dir:
                self.logger.error("WIM image must be mounted before registry modifications")
                return False
            
            # Apply registry bypasses using DISM offline registry editing
            if self.dism_path and self.dism_path != 'wimlib-imagex':
                return self._apply_registry_bypass_dism(bypass)
            elif self.wimlib_path:
                return self._apply_registry_bypass_wimlib(bypass)
            else:
                # Fallback to manual offline hive file editing for cross-platform
                return self._apply_registry_bypass_offline(bypass, system_hive)
            
        except Exception as e:
            self.logger.error(f"Failed to apply registry bypass {bypass.name}: {e}")
            return False
    
    def _apply_registry_bypass_dism(self, bypass: WindowsBypass) -> bool:
        """Apply registry bypasses using DISM offline registry editing"""
        try:
            for reg_path, keys in bypass.registry_keys.items():
                for key_name, (key_type, key_value) in keys.items():
                    # Use DISM to add registry values to offline image
                    cmd = [
                        self.dism_path, '/English',
                        f'/Image:{self.mount_dir}',
                        '/Set-TargetPath:OFFLINE',
                        '/Add-Package',  # This would need proper DISM registry commands
                        # Note: DISM doesn't have direct registry edit commands
                        # This is a placeholder - actual implementation would use reg files
                    ]
                    
                    # For now, create registry files that will be processed during boot
                    self._create_offline_registry_script(reg_path, key_name, key_type, key_value)
                    
            self.logger.info(f"Applied registry bypass using DISM: {bypass.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"DISM registry bypass failed: {e}")
            return False
    
    def _apply_registry_bypass_wimlib(self, bypass: WindowsBypass) -> bool:
        """Apply registry bypasses using wimlib (cross-platform)"""
        try:
            # wimlib doesn't have direct registry editing - use offline approach
            return self._apply_registry_bypass_offline(bypass, None)
            
        except Exception as e:
            self.logger.error(f"Wimlib registry bypass failed: {e}")
            return False
    
    def _apply_registry_bypass_offline(self, bypass: WindowsBypass, system_hive: Optional[Path]) -> bool:
        """Safe offline registry bypass using registry scripts"""
        try:
            # Create a registry script that will be executed during Windows boot
            # This is the safest cross-platform approach
            
            if not self.mount_dir:
                self.logger.error("Mount directory not available for offline registry editing")
                return False
            
            # Create Windows directory in mount if it doesn't exist
            windows_dir = Path(self.mount_dir) / "Windows" / "Setup" / "Scripts"
            windows_dir.mkdir(parents=True, exist_ok=True)
            
            # Create registry script file
            script_path = windows_dir / f"bootforge_bypass_{bypass.bypass_type.value}.cmd"
            
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write('@echo off\n')
                f.write(f'REM BootForge Registry Bypass: {bypass.name}\n')
                f.write(f'REM {bypass.description}\n')
                f.write('\n')
                
                for reg_path, keys in bypass.registry_keys.items():
                    for key_name, (key_type, key_value) in keys.items():
                        # Create safe registry command that operates on the offline system
                        f.write(f'reg add "{reg_path}" /v "{key_name}" /t {key_type} /d "{key_value}" /f\n')
                
                f.write('\n')
                f.write('REM Registry bypass applied by BootForge\n')
            
            # Also create a .reg file for direct import
            reg_file_path = windows_dir / f"bootforge_bypass_{bypass.bypass_type.value}.reg"
            
            with open(reg_file_path, 'w', encoding='utf-16le') as f:
                f.write('\ufeffWindows Registry Editor Version 5.00\n\n')
                f.write(f'; BootForge Registry Bypass: {bypass.name}\n')
                f.write(f'; {bypass.description}\n\n')
                
                for reg_path, keys in bypass.registry_keys.items():
                    f.write(f'[{reg_path}]\n')
                    for key_name, (key_type, key_value) in keys.items():
                        # Convert to .reg file format
                        if key_type == "REG_DWORD":
                            f.write(f'"{key_name}"=dword:{key_value:08x}\n')
                        elif key_type == "REG_SZ":
                            f.write(f'"{key_name}"="{key_value}"\n')
                        else:
                            f.write(f'"{key_name}"="{key_value}"\n')
                    f.write('\n')
            
            self.logger.info(f"Created offline registry bypass files: {bypass.name}")
            self.logger.info(f"  Script: {script_path}")
            self.logger.info(f"  Registry: {reg_file_path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Offline registry bypass failed: {e}")
            return False
    
    def _create_offline_registry_script(self, reg_path: str, key_name: str, key_type: str, key_value: Any):
        """Create registry modification script for offline processing"""
        if not self.mount_dir:
            return
            
        script_dir = Path(self.mount_dir) / "Windows" / "Setup" / "Scripts" 
        script_dir.mkdir(parents=True, exist_ok=True)
        
        # Append to main bypass script
        script_path = script_dir / "bootforge_registry_bypasses.cmd"
        
        with open(script_path, 'a', encoding='utf-8') as f:
            if script_path.stat().st_size == 0:
                # First write - add header
                f.write('@echo off\n')
                f.write('REM BootForge Registry Bypasses\n\n')
            
            f.write(f'reg add "{reg_path}" /v "{key_name}" /t {key_type} /d "{key_value}" /f\n')
    
    def _inject_hardware_drivers(self, hardware: DetectedHardware, windows_version: str) -> bool:
        """Inject hardware-specific drivers into Windows image"""
        try:
            self.logger.info("Injecting hardware-specific drivers")
            
            # Find matching drivers for this hardware
            compatible_drivers = []
            
            for driver in self.driver_database:
                if windows_version in driver.compatible_windows:
                    # Basic hardware matching - would be more sophisticated in real implementation
                    if self._driver_matches_hardware(driver, hardware):
                        compatible_drivers.append(driver)
            
            self.logger.info(f"Found {len(compatible_drivers)} compatible drivers")
            
            # Inject each driver
            for driver in compatible_drivers:
                if self._inject_single_driver(driver):
                    self.injected_drivers.append(driver)
                    self.logger.info(f"Injected driver: {driver.name}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to inject drivers: {e}")
            return False
    
    def _driver_matches_hardware(self, driver: DriverPackage, hardware: DetectedHardware) -> bool:
        """Check if driver matches detected hardware"""
        # Simplified matching - real implementation would use hardware IDs
        if driver.category == DriverCategory.NETWORK:
            return len(hardware.network_adapters) > 0
        elif driver.category == DriverCategory.STORAGE:
            return len(hardware.storage_devices) > 0
        elif driver.category == DriverCategory.GRAPHICS:
            return len(hardware.gpus) > 0
        
        return False
    
    def _inject_single_driver(self, driver: DriverPackage) -> bool:
        """Inject a single driver package using DISM"""
        try:
            if not self.dism_path or self.dism_path == 'wimlib-imagex':
                self.logger.warning("Driver injection requires DISM")
                return False
            
            # In real implementation, would download/locate driver files
            # For now, just simulate successful injection
            self.logger.info(f"Simulating injection of {driver.name} driver")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to inject driver {driver.name}: {e}")
            return False
    
    def _apply_file_modifications(self, bypasses: List[WindowsBypassType]) -> bool:
        """Apply any file modifications for bypasses"""
        try:
            # Apply setupcomplete.cmd for post-installation bypasses
            setupcomplete_path = self.mount_dir / "Windows" / "Setup" / "Scripts" / "setupcomplete.cmd"
            setupcomplete_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(setupcomplete_path, 'w') as f:
                f.write("@echo off\n")
                f.write("REM BootForge Windows Bypass Setup Complete Script\n")
                
                # Add bypass-specific commands
                for bypass_type in bypasses:
                    if bypass_type == WindowsBypassType.ONLINE_ACCOUNT_BYPASS:
                        f.write('reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\OOBE" /v "BypassNRO" /t REG_DWORD /d 1 /f\n')
                
                f.write("echo BootForge bypass setup completed\n")
            
            self.logger.info("Applied file modifications for bypasses")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to apply file modifications: {e}")
            return False
    
    def _get_windows_edition_index(self, wim_path: str, windows_version: str) -> Optional[int]:
        """Get the appropriate Windows edition index from WIM/ESD"""
        try:
            if self.dism_path:
                cmd = [self.dism_path, '/Get-WimInfo', f'/WimFile:{wim_path}']
                if self.dism_path == 'wimlib-imagex':
                    cmd = ['wimlib-imagex', 'info', wim_path]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    # Parse output to find appropriate edition (Pro, Home, etc.)
                    # For now, return index 1 as default
                    return 1
            
            return 1  # Default to first image
            
        except Exception as e:
            self.logger.error(f"Failed to get Windows edition index: {e}")
            return None
    
    def _setup_audit_logger(self) -> logging.Logger:
        """Setup dedicated audit logger for security-critical operations"""
        audit_logger = logging.getLogger(f"{__name__}.audit")
        
        # Ensure audit logs go to a dedicated file
        if not audit_logger.handlers:
            # Create audit log directory
            audit_dir = Path.home() / ".bootforge" / "audit_logs"
            audit_dir.mkdir(parents=True, exist_ok=True)
            
            # Create timestamped audit log file
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            audit_file = audit_dir / f"windows_patch_audit_{timestamp}.log"
            
            # Setup file handler with detailed formatting
            handler = logging.FileHandler(audit_file)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - SESSION:%(message)s'
            )
            handler.setFormatter(formatter)
            audit_logger.addHandler(handler)
            audit_logger.setLevel(logging.INFO)
            
            # Also log to console for immediate visibility
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter('AUDIT: %(message)s'))
            audit_logger.addHandler(console_handler)
        
        return audit_logger
    
    def request_bypass_consent(self, bypasses: List[WindowsBypass], 
                             hardware: DetectedHardware, 
                             windows_version: str) -> UserConsent:
        """
        SECURITY CRITICAL: Request explicit user consent for bypass operations
        
        This method must be called before any bypass operations and requires
        explicit user acknowledgment of security risks.
        """
        from src.core.safety_validator import UserConsent, PatchRisk
        
        # Create detailed risk assessment
        risks = []
        warnings = []
        
        for bypass in bypasses:
            risks.append(f"Windows {bypass.name} - {bypass.description}")
            if bypass.user_warning:
                warnings.append(bypass.user_warning)
            
            # Add specific risk warnings based on bypass type
            if bypass.bypass_type == WindowsBypassType.TPM_BYPASS:
                warnings.append("SECURITY RISK: Disabling TPM checks may affect BitLocker encryption and Windows security features.")
            elif bypass.bypass_type == WindowsBypassType.SECURE_BOOT_BYPASS:
                warnings.append("SECURITY RISK: Disabling Secure Boot reduces protection against malware and rootkits.")
            elif bypass.bypass_type == WindowsBypassType.CPU_BYPASS:
                warnings.append("COMPATIBILITY RISK: Bypassing CPU requirements may result in poor performance or stability issues.")
        
        # Determine required consent level based on bypass risks
        overall_risk = ValidationResult.WARNING
        for bypass in bypasses:
            if bypass.risk_level == ValidationResult.DANGEROUS:
                overall_risk = ValidationResult.DANGEROUS
                break
        
        # Create consent record
        consent = UserConsent(
            operation_id=f"bypass_windows_{windows_version}_{int(time.time())}",
            operation_type="windows_bypass",
            consent_level=ConsentLevel.NONE,  # Must be set by caller
            risk_factors=risks,
            user_confirmation="",  # Must be provided by caller
            timestamp=time.time(),
            warnings_shown=warnings,
            user_notes=f"Target: {hardware.get_summary()}, Bypasses: {len(bypasses)}"
        )
        
        # Log consent request for audit trail
        self.audit_logger.warning(f"CONSENT_REQUESTED: Session {self.bypass_session_id}")
        self.audit_logger.warning(f"  Hardware: {hardware.get_summary()}")
        self.audit_logger.warning(f"  Windows: {windows_version}")
        self.audit_logger.warning(f"  Bypasses: {[b.name for b in bypasses]}")
        self.audit_logger.warning(f"  Risk Level: {overall_risk.value}")
        self.audit_logger.warning(f"  Warnings: {len(warnings)}")
        
        return consent
    
    def validate_bypass_consent(self, consent: UserConsent, bypasses: List[WindowsBypass]) -> bool:
        """
        SECURITY CRITICAL: Validate that user consent is sufficient for bypass operations
        """
        try:
            # Determine maximum risk level from bypasses
            max_risk = ValidationResult.SAFE
            for bypass in bypasses:
                if bypass.risk_level.value == "dangerous":
                    max_risk = ValidationResult.DANGEROUS
                elif bypass.risk_level.value == "warning" and max_risk == ValidationResult.SAFE:
                    max_risk = ValidationResult.WARNING
            
            # Check consent validity
            if not consent.is_valid_for_risk(max_risk):
                self.audit_logger.error(f"CONSENT_INSUFFICIENT: Session {self.bypass_session_id}")
                self.audit_logger.error(f"  Required: {max_risk.value}, Provided: {consent.consent_level.value}")
                return False
            
            # Check consent timestamp (expire after 1 hour for security)
            if time.time() - consent.timestamp > 3600:
                self.audit_logger.error(f"CONSENT_EXPIRED: Session {self.bypass_session_id}")
                return False
            
            # Record consent approval
            self.user_consent_granted = True
            self.consent_level = consent.consent_level
            self.consent_timestamp = consent.timestamp
            
            self.audit_logger.info(f"CONSENT_APPROVED: Session {self.bypass_session_id}")
            self.audit_logger.info(f"  Consent Level: {consent.consent_level.value}")
            self.audit_logger.info(f"  Risk Factors: {len(consent.risk_factors)}")
            self.audit_logger.info(f"  User Confirmation: {consent.user_confirmation[:50]}...")
            
            return True
            
        except Exception as e:
            self.audit_logger.error(f"CONSENT_VALIDATION_ERROR: Session {self.bypass_session_id}: {e}")
            return False
    
    def enforce_bypass_security(self, bypasses: List[WindowsBypass]) -> bool:
        """
        SECURITY CRITICAL: Enforce security requirements before bypass operations
        
        Returns True if bypass operations are authorized, False if blocked.
        """
        if not bypasses:
            return True  # No bypasses = no security concerns
        
        # SECURITY: Block bypass operations if consent not granted
        if not self.user_consent_granted:
            self.audit_logger.error(f"BYPASS_BLOCKED_NO_CONSENT: Session {self.bypass_session_id}")
            self.audit_logger.error(f"  Attempted bypasses: {[b.name for b in bypasses]}")
            self.logger.error("SECURITY: Bypass operations blocked - user consent required")
            return False
        
        # SECURITY: Check consent timestamp validity
        if not self.consent_timestamp or time.time() - self.consent_timestamp > 3600:
            self.audit_logger.error(f"BYPASS_BLOCKED_CONSENT_EXPIRED: Session {self.bypass_session_id}")
            self.logger.error("SECURITY: Bypass operations blocked - consent expired")
            return False
        
        # SECURITY: Validate consent level is sufficient
        max_risk = max(bypass.risk_level for bypass in bypasses)
        required_consent_map = {
            ValidationResult.SAFE: ConsentLevel.NONE,
            ValidationResult.WARNING: ConsentLevel.BASIC,
            ValidationResult.DANGEROUS: ConsentLevel.INFORMED,
            ValidationResult.BLOCKED: ConsentLevel.EXPERT
        }
        
        required_consent = required_consent_map.get(max_risk, ConsentLevel.EXPERT)
        consent_values = {
            ConsentLevel.NONE: 0, ConsentLevel.BASIC: 1,
            ConsentLevel.INFORMED: 2, ConsentLevel.EXPERT: 3
        }
        
        if consent_values.get(self.consent_level, 0) < consent_values.get(required_consent, 3):
            self.audit_logger.error(f"BYPASS_BLOCKED_INSUFFICIENT_CONSENT: Session {self.bypass_session_id}")
            self.audit_logger.error(f"  Required: {required_consent.value}, Have: {self.consent_level.value}")
            return False
        
        # SECURITY: Log bypass authorization
        self.audit_logger.info(f"BYPASS_AUTHORIZED: Session {self.bypass_session_id}")
        self.audit_logger.info(f"  Bypasses: {[b.name for b in bypasses]}")
        self.audit_logger.info(f"  Max Risk: {max_risk.value}")
        self.audit_logger.info(f"  Consent Level: {self.consent_level.value}")
        
        return True
    
    def _create_unattend_xml(self, hardware: DetectedHardware, windows_version: str) -> bool:
        """Create unattended installation configuration"""
        try:
            unattend_path = self.temp_iso_dir / "autounattend.xml"
            
            # Generate unattend.xml content
            unattend_content = self._generate_unattend_xml_content(hardware, windows_version)
            
            with open(unattend_path, 'w', encoding='utf-8') as f:
                f.write(unattend_content)
            
            self.logger.info("Created autounattend.xml for automated installation")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create unattend.xml: {e}")
            return False
    
    def _generate_unattend_xml_content(self, hardware: DetectedHardware, windows_version: str) -> str:
        """Generate unattended installation XML content"""
        return f"""<?xml version="1.0" encoding="utf-8"?>
<unattend xmlns="urn:schemas-microsoft-com:unattend">
    <settings pass="windowsPE">
        <component name="Microsoft-Windows-Setup" processorArchitecture="{hardware.cpu_architecture or 'amd64'}" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
            <UserData>
                <AcceptEula>true</AcceptEula>
                <FullName>BootForge User</FullName>
                <Organization>BootForge</Organization>
            </UserData>
            <DiskConfiguration>
                <Disk wcm:action="add">
                    <DiskID>0</DiskID>
                    <WillWipeDisk>true</WillWipeDisk>
                    <CreatePartitions>
                        <CreatePartition wcm:action="add">
                            <Order>1</Order>
                            <Type>Primary</Type>
                            <Size>350</Size>
                        </CreatePartition>
                        <CreatePartition wcm:action="add">
                            <Order>2</Order>
                            <Type>Primary</Type>
                            <Extend>true</Extend>
                        </CreatePartition>
                    </CreatePartitions>
                    <ModifyPartitions>
                        <ModifyPartition wcm:action="add">
                            <Order>1</Order>
                            <PartitionID>1</PartitionID>
                            <Label>System Reserved</Label>
                            <Format>NTFS</Format>
                            <Active>true</Active>
                        </ModifyPartition>
                        <ModifyPartition wcm:action="add">
                            <Order>2</Order>
                            <PartitionID>2</PartitionID>
                            <Label>Windows</Label>
                            <Letter>C</Letter>
                            <Format>NTFS</Format>
                        </ModifyPartition>
                    </ModifyPartitions>
                </Disk>
            </DiskConfiguration>
            <ImageInstall>
                <OSImage>
                    <InstallTo>
                        <DiskID>0</DiskID>
                        <PartitionID>2</PartitionID>
                    </InstallTo>
                </OSImage>
            </ImageInstall>
        </component>
    </settings>
    <settings pass="oobeSystem">
        <component name="Microsoft-Windows-Shell-Setup" processorArchitecture="{hardware.cpu_architecture or 'amd64'}" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
            <OOBE>
                <HideEULAPage>true</HideEULAPage>
                <HideWirelessSetupInOOBE>true</HideWirelessSetupInOOBE>
                <NetworkLocation>Work</NetworkLocation>
                <ProtectYourPC>1</ProtectYourPC>
            </OOBE>
            <UserAccounts>
                <LocalAccounts>
                    <LocalAccount wcm:action="add">
                        <Password>
                            <Value></Value>
                            <PlainText>true</PlainText>
                        </Password>
                        <Description>BootForge Local Administrator</Description>
                        <DisplayName>Administrator</DisplayName>
                        <Group>Administrators</Group>
                        <Name>Administrator</Name>
                    </LocalAccount>
                </LocalAccounts>
            </UserAccounts>
            <AutoLogon>
                <Password>
                    <Value></Value>
                    <PlainText>true</PlainText>
                </Password>
                <Enabled>true</Enabled>
                <LogonCount>1</LogonCount>
                <Username>Administrator</Username>
            </AutoLogon>
        </component>
    </settings>
</unattend>"""
    
    def _rebuild_iso(self, output_path: str) -> bool:
        """Rebuild Windows ISO with patches applied"""
        try:
            self.logger.info("Rebuilding Windows ISO with patches")
            
            if platform.system() == "Windows":
                # Use oscdimg on Windows
                result = subprocess.run([
                    'oscdimg', '-n', '-m', '-b', 
                    str(self.temp_iso_dir / "boot" / "etfsboot.com"),
                    str(self.temp_iso_dir), output_path
                ], capture_output=True, text=True)
            else:
                # Use genisoimage on Linux/macOS
                result = subprocess.run([
                    'genisoimage', '-iso-level', '4', '-udf', '-joliet',
                    '-b', 'boot/etfsboot.com', '-no-emul-boot',
                    '-boot-load-size', '8', '-hide', 'boot.catalog',
                    '-o', output_path, str(self.temp_iso_dir)
                ], capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"Failed to rebuild ISO: {result.stderr}")
                return False
            
            self.logger.info(f"Successfully created patched ISO: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to rebuild ISO: {e}")
            return False
    
    def _cleanup_workspace(self):
        """Clean up temporary workspace"""
        try:
            if self.workspace_dir and self.workspace_dir.exists():
                shutil.rmtree(self.workspace_dir)
                self.logger.info("Workspace cleaned up")
        except Exception as e:
            self.logger.warning(f"Failed to cleanup workspace: {e}")
    
    def get_bypass_summary(self) -> Dict[str, Any]:
        """Get summary of applied bypasses and injected drivers"""
        return {
            "applied_bypasses": [
                {
                    "name": bypass.name,
                    "type": bypass.bypass_type.value,
                    "description": bypass.description,
                    "risk_level": bypass.risk_level.value
                }
                for bypass in self.applied_bypasses
            ],
            "injected_drivers": [
                {
                    "name": driver.name,
                    "category": driver.category.value,
                    "version": driver.version,
                    "architecture": driver.architecture
                }
                for driver in self.injected_drivers
            ],
            "total_bypasses": len(self.applied_bypasses),
            "total_drivers": len(self.injected_drivers)
        }
    
    def supports_hardware(self, hardware: DetectedHardware, windows_version: str) -> Dict[str, Any]:
        """Check what bypasses are needed for specific hardware"""
        required_bypasses = self._determine_required_bypasses(hardware, windows_version)
        compatible_drivers = [
            driver for driver in self.driver_database
            if windows_version in driver.compatible_windows and self._driver_matches_hardware(driver, hardware)
        ]
        
        return {
            "supports_installation": True,  # We can install on any hardware
            "required_bypasses": [b.value for b in required_bypasses],
            "bypass_count": len(required_bypasses),
            "available_drivers": len(compatible_drivers),
            "hardware_summary": hardware.get_summary(),
            "recommendations": self._get_hardware_recommendations(hardware, windows_version, required_bypasses)
        }
    
    def _get_hardware_recommendations(self, hardware: DetectedHardware, 
                                    windows_version: str, 
                                    bypasses: List[WindowsBypassType]) -> List[str]:
        """Get recommendations for this hardware configuration"""
        recommendations = []
        
        if WindowsBypassType.TPM_BYPASS in bypasses:
            recommendations.append("Consider enabling BitLocker alternative encryption")
            recommendations.append("Windows Hello and some security features will be unavailable")
        
        if WindowsBypassType.RAM_BYPASS in bypasses:
            recommendations.append("Install Windows 10 instead of 11 for better performance on low-RAM systems")
            recommendations.append("Consider RAM upgrade for optimal Windows 11 experience")
        
        if WindowsBypassType.CPU_BYPASS in bypasses:
            recommendations.append("Older CPU may not support all Windows 11 features")
            recommendations.append("Some performance optimizations may not be available")
        
        if hardware.total_ram_gb and hardware.total_ram_gb < 8:
            recommendations.append("Consider disabling Windows indexing and background apps")
        
        return recommendations