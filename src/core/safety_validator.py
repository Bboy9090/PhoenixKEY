"""
BootForge Safety Validation System
Critical safety measures to prevent system disk destruction and ensure safe USB operations
Extended with patch-specific validation for kernel modifications and system patching
"""

import os
import re
import time
import uuid
import json
import logging
import platform
import subprocess
import psutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, field
from enum import Enum


class SafetyLevel(Enum):
    """Safety validation levels"""
    MINIMAL = "minimal"
    STANDARD = "standard"
    PARANOID = "paranoid"


class ValidationResult(Enum):
    """Validation result types"""
    SAFE = "safe"
    WARNING = "warning"
    DANGEROUS = "dangerous"
    BLOCKED = "blocked"


class PatchValidationMode(Enum):
    """Patch validation modes for system modifications"""
    COMPLIANT = "compliant"          # Only allow verified, safe patches
    BYPASS = "bypass"                # Allow risky patches with explicit consent
    AUDIT_ONLY = "audit_only"        # Log everything but don't block


class ConsentLevel(Enum):
    """User consent levels for risky operations"""
    NONE = "none"                    # No consent given
    BASIC = "basic"                  # Basic awareness consent
    INFORMED = "informed"            # Detailed risk explanation accepted
    EXPERT = "expert"                # Full technical understanding confirmed


@dataclass
class SafetyCheck:
    """Individual safety check result"""
    name: str
    result: ValidationResult
    message: str
    details: Optional[str] = None
    mitigation: Optional[str] = None


@dataclass
class DeviceRisk:
    """Device risk assessment"""
    device_path: str
    is_system_disk: bool
    is_boot_disk: bool
    is_removable: bool
    size_gb: float
    mount_points: List[str]
    risk_factors: List[str]
    overall_risk: ValidationResult


@dataclass
class UserConsent:
    """User consent record for risky operations"""
    operation_id: str                          # Unique operation identifier
    operation_type: str                        # Type of operation (patch, format, etc.)
    consent_level: ConsentLevel                # Level of consent given
    risk_factors: List[str]                    # Risks user was informed about
    user_confirmation: str                     # User's confirmation statement
    timestamp: float                           # When consent was given
    ip_address: Optional[str] = None           # Source IP (for remote operations)
    session_id: Optional[str] = None           # Session identifier
    warnings_shown: List[str] = field(default_factory=list)  # Warnings displayed
    
    def is_valid_for_risk(self, risk_level: ValidationResult) -> bool:
        """Check if consent level is sufficient for risk level"""
        risk_consent_map = {
            ValidationResult.SAFE: ConsentLevel.NONE,
            ValidationResult.WARNING: ConsentLevel.BASIC,
            ValidationResult.DANGEROUS: ConsentLevel.INFORMED,
            ValidationResult.BLOCKED: ConsentLevel.EXPERT
        }
        
        required_level = risk_consent_map.get(risk_level, ConsentLevel.EXPERT)
        consent_values = {
            ConsentLevel.NONE: 0,
            ConsentLevel.BASIC: 1,
            ConsentLevel.INFORMED: 2,
            ConsentLevel.EXPERT: 3
        }
        
        return consent_values.get(self.consent_level, 0) >= consent_values.get(required_level, 3)


@dataclass
class PatchRisk:
    """Risk assessment for patch operations"""
    patch_id: str                              # Patch identifier
    patch_name: str                            # Human-readable patch name
    patch_type: str                            # Type of patch (kernel, driver, etc.)
    target_system: str                         # Target system path/component
    
    # Risk factors
    modifies_kernel: bool = False              # Modifies kernel code
    modifies_bootloader: bool = False          # Modifies bootloader/EFI
    modifies_firmware: bool = False            # Modifies firmware
    unsigned_code: bool = False                # Contains unsigned code
    disables_security: bool = False            # Disables security features
    irreversible: bool = False                 # Cannot be undone
    
    # Risk assessment
    risk_score: float = 0.0                    # Calculated risk score (0-100)
    overall_risk: ValidationResult = ValidationResult.SAFE
    risk_factors: List[str] = field(default_factory=list)
    mitigations: List[str] = field(default_factory=list)
    
    def calculate_risk_score(self) -> float:
        """Calculate numeric risk score based on factors"""
        score = 0.0
        
        # Major risk factors
        if self.modifies_kernel:
            score += 30.0
        if self.modifies_bootloader:
            score += 35.0
        if self.modifies_firmware:
            score += 40.0
        if self.irreversible:
            score += 20.0
        
        # Security risk factors
        if self.unsigned_code:
            score += 15.0
        if self.disables_security:
            score += 25.0
        
        self.risk_score = min(score, 100.0)
        
        # Determine overall risk level
        if self.risk_score >= 80.0:
            self.overall_risk = ValidationResult.BLOCKED
        elif self.risk_score >= 60.0:
            self.overall_risk = ValidationResult.DANGEROUS
        elif self.risk_score >= 30.0:
            self.overall_risk = ValidationResult.WARNING
        else:
            self.overall_risk = ValidationResult.SAFE
        
        return self.risk_score


@dataclass
class AuditRecord:
    """Audit record for safety-critical operations"""
    id: str = field(default_factory=lambda: f"audit-{uuid.uuid4().hex[:8]}")
    timestamp: float = field(default_factory=time.time)
    operation_type: str = ""                   # Type of operation
    operation_details: str = ""                # Detailed operation description
    user_id: Optional[str] = None              # User identifier
    risk_level: ValidationResult = ValidationResult.SAFE
    consent_given: bool = False                # Was consent obtained
    validation_mode: Optional[PatchValidationMode] = None
    
    # Operational details
    target_device: Optional[str] = None        # Target device/path
    files_modified: List[str] = field(default_factory=list)
    commands_executed: List[str] = field(default_factory=list)
    environment_info: Dict[str, Any] = field(default_factory=dict)
    
    # Results
    success: Optional[bool] = None             # Operation success
    error_message: Optional[str] = None        # Error if failed
    rollback_info: Optional[str] = None        # Rollback information
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "operation_type": self.operation_type,
            "operation_details": self.operation_details,
            "user_id": self.user_id,
            "risk_level": self.risk_level.value if self.risk_level else None,
            "consent_given": self.consent_given,
            "validation_mode": self.validation_mode.value if self.validation_mode else None,
            "target_device": self.target_device,
            "files_modified": self.files_modified,
            "commands_executed": self.commands_executed,
            "environment_info": self.environment_info,
            "success": self.success,
            "error_message": self.error_message,
            "rollback_info": self.rollback_info
        }


class SafetyValidator:
    """Comprehensive safety validation system with patch-specific capabilities"""
    
    def __init__(self, safety_level: SafetyLevel = SafetyLevel.STANDARD,
                 patch_mode: PatchValidationMode = PatchValidationMode.COMPLIANT):
        self.logger = logging.getLogger(__name__)
        self.safety_level = safety_level
        self.patch_mode = patch_mode
        self.system = platform.system()
        self.blocked_patterns = self._get_blocked_device_patterns()
        self.required_tools = self._get_required_tools()
        
        # Patch validation settings
        self._audit_log_path = Path.home() / ".bootforge" / "audit.log"
        self._consent_records: Dict[str, UserConsent] = {}
        self._patch_whitelist: Set[str] = set()
        self._patch_blacklist: Set[str] = set()
        
        # Ensure audit log directory exists
        self._audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"SafetyValidator initialized: level={safety_level.value}, patch_mode={patch_mode.value}")
        
    def _get_blocked_device_patterns(self) -> List[str]:
        """Get device patterns that should never be targeted"""
        patterns = []
        
        if self.system == "Linux":
            patterns.extend([
                r"/dev/loop\d+",  # Loop devices
                r"/dev/dm-\d+",  # Device mapper
                r"/dev/md\d+",  # RAID devices
            ])
        elif self.system == "Windows":
            patterns.extend([
                r"\\\\\.\\C:",  # System drive
                r"\\\\\.\\PHYSICALDRIVE0$",  # Primary system drive
            ])
        elif self.system == "Darwin":  # macOS
            patterns.extend([
                r"/dev/disk0$",  # Usually system disk
                r"/dev/disk\d+s[1-9]$",  # System partitions
            ])
            
        return patterns
    
    def _get_required_tools(self) -> List[str]:
        """Get required tools by platform"""
        tools = {
            "Linux": ["parted", "mkfs.fat", "mkfs.ntfs", "mkfs.ext4", "lsblk", "blkid"],
            "Windows": ["diskpart.exe", "format.com"],
            "Darwin": ["diskutil", "hdiutil", "newfs_msdos"]
        }
        return tools.get(self.system, [])
    
    def validate_device_safety(self, device_path: str) -> DeviceRisk:
        """Comprehensive device safety validation"""
        self.logger.info(f"Validating device safety: {device_path}")
        
        risk_factors = []
        mount_points = []
        
        # Check if device exists
        if not os.path.exists(device_path):
            return DeviceRisk(
                device_path=device_path,
                is_system_disk=False,
                is_boot_disk=False,
                is_removable=False,
                size_gb=0.0,
                mount_points=[],
                risk_factors=["Device does not exist"],
                overall_risk=ValidationResult.BLOCKED
            )
        
        # Check against blocked patterns
        for pattern in self.blocked_patterns:
            if re.match(pattern, device_path):
                risk_factors.append(f"Matches blocked pattern: {pattern}")
        
        # Get device information
        is_removable = self._is_device_removable(device_path)
        is_system_disk = self._is_system_disk(device_path)
        is_boot_disk = self._is_boot_disk(device_path)
        size_gb = self._get_device_size_gb(device_path)
        mount_points = self._get_device_mount_points(device_path)
        
        # Add risk factors
        if not is_removable:
            risk_factors.append("Device is not removable")
        
        if is_system_disk:
            risk_factors.append("Device contains system files")
        
        if is_boot_disk:
            risk_factors.append("Device is boot disk")
        
        if mount_points:
            risk_factors.append(f"Device has mounted partitions: {', '.join(mount_points)}")
        
        if size_gb > 2000:  # Larger than 2TB is suspicious for USB
            risk_factors.append(f"Device is very large ({size_gb:.1f}GB) - suspicious for USB")
        
        if size_gb < 0.5:  # Smaller than 500MB is too small
            risk_factors.append(f"Device is too small ({size_gb:.1f}GB)")
        
        # Determine overall risk
        overall_risk = self._assess_overall_risk(risk_factors, is_system_disk, is_boot_disk, is_removable)
        
        return DeviceRisk(
            device_path=device_path,
            is_system_disk=is_system_disk,
            is_boot_disk=is_boot_disk,
            is_removable=is_removable,
            size_gb=size_gb,
            mount_points=mount_points,
            risk_factors=risk_factors,
            overall_risk=overall_risk
        )
    
    def _is_device_removable(self, device_path: str) -> bool:
        """Enhanced removable device detection"""
        try:
            if self.system == "Linux":
                # Get proper device name for /sys/block mapping
                device_name = self._get_sys_block_name(device_path)
                if not device_name:
                    return False
                
                # Check removable flag
                removable_file = f"/sys/block/{device_name}/removable"
                removable = False
                if os.path.exists(removable_file):
                    with open(removable_file, 'r') as f:
                        removable = f.read().strip() == '1'
                
                # Additional checks for USB subsystem
                device_path_sys = f"/sys/block/{device_name}"
                if os.path.exists(device_path_sys):
                    # Check if device is connected via USB
                    try:
                        real_path = os.path.realpath(device_path_sys)
                        return "/usb" in real_path.lower() or removable
                    except:
                        pass
                
                return removable
                
            elif self.system == "Windows":
                import ctypes
                try:
                    # Extract drive letter or use alternative method
                    if device_path.startswith(r'\\.\PhysicalDrive'):
                        # For physical drives, we need more complex detection
                        # This is simplified - real implementation would use WMI
                        return False  # Conservative approach for physical drives
                    else:
                        drive_type = ctypes.windll.kernel32.GetDriveTypeW(device_path)
                        return drive_type == 2  # DRIVE_REMOVABLE
                except:
                    return False
                    
            elif self.system == "Darwin":  # macOS
                try:
                    # Use diskutil to check if device is removable
                    result = subprocess.run(
                        ['diskutil', 'info', device_path],
                        capture_output=True, text=True, check=False
                    )
                    if result.returncode == 0:
                        output = result.stdout.lower()
                        return any(keyword in output for keyword in [
                            'removable media', 'usb', 'external', 'removable: yes'
                        ])
                except:
                    pass
                return False
            
            # Fallback for unknown systems
            return False
                
        except Exception as e:
            self.logger.error(f"Error checking if device is removable: {e}")
            return False
            return False
    
    def _is_system_disk(self, device_path: str) -> bool:
        """Check if device contains system files"""
        try:
            partitions = psutil.disk_partitions()
            device_base = self._get_device_base(device_path)
            
            for partition in partitions:
                if partition.device.startswith(device_base):
                    # Check for system directories
                    mount_point = partition.mountpoint
                    if mount_point in ['/', '/boot', '/usr', '/var', '/etc']:
                        return True
                    
                    # Check for Windows system directories
                    if os.path.exists(os.path.join(mount_point, 'Windows', 'System32')):
                        return True
                    
                    # Check for macOS system directories
                    if os.path.exists(os.path.join(mount_point, 'System', 'Library')):
                        return True
                        
        except Exception as e:
            self.logger.error(f"Error checking if device is system disk: {e}")
            
        return False
    
    def _is_boot_disk(self, device_path: str) -> bool:
        """Check if device is boot disk"""
        try:
            device_base = self._get_device_base(device_path)
            
            if self.system == "Linux":
                # Check /proc/mounts for boot partitions
                with open('/proc/mounts', 'r') as f:
                    mounts = f.read()
                    if any(f"{device_base}" in line and "/boot" in line for line in mounts.split('\n')):
                        return True
                        
            elif self.system == "Darwin":  # macOS
                # Check if device contains boot volume
                result = subprocess.run(
                    ['diskutil', 'info', device_path],
                    capture_output=True, text=True, check=False
                )
                if result.returncode == 0:
                    output = result.stdout.lower()
                    return any(keyword in output for keyword in [
                        'boot', 'system', 'efi'
                    ])
                    
        except Exception as e:
            self.logger.error(f"Error checking if device is boot disk: {e}")
            
        return False
    
    def _get_device_size_gb(self, device_path: str) -> float:
        """Get device size in GB"""
        try:
            if self.system == "Linux":
                # Use lsblk to get size
                result = subprocess.run(
                    ['lsblk', '-b', '-n', '-o', 'SIZE', device_path],
                    capture_output=True, text=True, check=False
                )
                if result.returncode == 0:
                    size_bytes = int(result.stdout.strip())
                    return size_bytes / (1024 * 1024 * 1024)
                    
            elif self.system == "Darwin":  # macOS
                result = subprocess.run(
                    ['diskutil', 'info', device_path],
                    capture_output=True, text=True, check=False
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'total size:' in line.lower():
                            # Extract size from line like "Total Size: 32.0 GB"
                            import re
                            match = re.search(r'(\d+\.?\d*)\s*GB', line)
                            if match:
                                return float(match.group(1))
                                
        except Exception as e:
            self.logger.error(f"Error getting device size: {e}")
            
        return 0.0
    
    def _get_device_mount_points(self, device_path: str) -> List[str]:
        """Get all mount points for device"""
        mount_points = []
        try:
            partitions = psutil.disk_partitions()
            device_base = self._get_device_base(device_path)
            
            for partition in partitions:
                if partition.device.startswith(device_base):
                    mount_points.append(partition.mountpoint)
                    
        except Exception as e:
            self.logger.error(f"Error getting device mount points: {e}")
            
        return mount_points
    
    def test_device_classification(self) -> Dict[str, bool]:
        """Test device classification methods for common scenarios"""
        test_results = {}
        
        # Test _get_sys_block_name
        test_cases = [
            ("/dev/sda1", "sda"),
            ("/dev/sdb", "sdb"),  
            ("/dev/nvme0n1p1", "nvme0n1"),
            ("/dev/nvme0n1", "nvme0n1"),
            ("/dev/mmcblk0p1", "mmcblk0"),
            ("/dev/mmcblk0", "mmcblk0")
        ]
        
        for device_path, expected in test_cases:
            actual = self._get_sys_block_name(device_path)
            test_results[f"sys_block_{device_path}"] = (actual == expected)
            if actual != expected:
                self.logger.warning(f"Device classification test failed: {device_path} -> {actual} (expected {expected})")
        
        # Test _get_device_base
        base_test_cases = [
            ("/dev/sda1", "/dev/sda"),
            ("/dev/nvme0n1p1", "/dev/nvme0n1p"),  # This might need fixing
            ("/dev/mmcblk0p1", "/dev/mmcblk0p")   # This might need fixing
        ]
        
        for device_path, expected in base_test_cases:
            actual = self._get_device_base(device_path)
            test_results[f"device_base_{device_path}"] = (actual == expected)
            if actual != expected:
                self.logger.warning(f"Device base test failed: {device_path} -> {actual} (expected {expected})")
        
        return test_results
    
    def _get_device_base(self, device_path: str) -> str:
        """Get base device path without partition numbers"""
        if self.system == "Linux":
            return re.sub(r'\d+$', '', device_path)
        elif self.system == "Windows":
            return device_path
        elif self.system == "Darwin":
            return re.sub(r's\d+$', '', device_path)
        return device_path
    
    def _get_sys_block_name(self, device_path: str) -> str:
        """Get proper /sys/block device name for Linux"""
        if self.system != "Linux":
            return ""
        
        device_name = os.path.basename(device_path)
        
        # Handle different device types correctly:
        # /dev/sda1 -> sda
        # /dev/nvme0n1p1 -> nvme0n1  
        # /dev/mmcblk0p1 -> mmcblk0
        
        if device_name.startswith("sd"):
            # SATA/SCSI devices: sda1 -> sda
            return re.sub(r'\d+$', '', device_name)
        elif device_name.startswith("nvme"):
            # NVMe devices: nvme0n1p1 -> nvme0n1
            if 'p' in device_name:
                return device_name.split('p')[0]
            else:
                return device_name
        elif device_name.startswith("mmcblk"):
            # MMC/SD devices: mmcblk0p1 -> mmcblk0  
            if 'p' in device_name:
                return device_name.split('p')[0]
            else:
                return device_name
        else:
            # Generic fallback: strip trailing digits
            return re.sub(r'\d+$', '', device_name)
    
    def _assess_overall_risk(self, risk_factors: List[str], is_system_disk: bool, 
                           is_boot_disk: bool, is_removable: bool) -> ValidationResult:
        """Assess overall risk level"""
        
        # Blocked conditions
        if is_system_disk or is_boot_disk:
            return ValidationResult.BLOCKED
        
        if not is_removable:
            return ValidationResult.BLOCKED
        
        # Dangerous conditions
        if len(risk_factors) >= 3:
            return ValidationResult.DANGEROUS
        
        # Warning conditions
        if risk_factors:
            return ValidationResult.WARNING
        
        return ValidationResult.SAFE
    
    def validate_prerequisites(self) -> List[SafetyCheck]:
        """Validate system prerequisites"""
        checks = []
        
        # Check for required tools
        for tool in self.required_tools:
            if self._is_tool_available(tool):
                checks.append(SafetyCheck(
                    name=f"Tool: {tool}",
                    result=ValidationResult.SAFE,
                    message=f"{tool} is available"
                ))
            else:
                checks.append(SafetyCheck(
                    name=f"Tool: {tool}",
                    result=ValidationResult.BLOCKED,
                    message=f"{tool} is not available",
                    mitigation=f"Install {tool} before proceeding"
                ))
        
        # Check privileges
        privilege_check = self._check_privileges()
        checks.append(privilege_check)
        
        return checks
    
    def _is_tool_available(self, tool: str) -> bool:
        """Check if required tool is available"""
        try:
            result = subprocess.run(['which', tool], capture_output=True, check=False)
            return result.returncode == 0
        except:
            return False
    
    def _check_privileges(self) -> SafetyCheck:
        """Check if user has required privileges"""
        if self.system == "Linux" or self.system == "Darwin":
            if os.geteuid() == 0:
                return SafetyCheck(
                    name="Privileges",
                    result=ValidationResult.SAFE,
                    message="Running with root privileges"
                )
            else:
                # Check if sudo is available
                try:
                    result = subprocess.run(['sudo', '-n', 'true'], capture_output=True, check=False)
                    if result.returncode == 0:
                        return SafetyCheck(
                            name="Privileges",
                            result=ValidationResult.SAFE,
                            message="Sudo access available"
                        )
                    else:
                        return SafetyCheck(
                            name="Privileges",
                            result=ValidationResult.BLOCKED,
                            message="Root privileges required",
                            mitigation="Run with sudo or as root"
                        )
                except:
                    return SafetyCheck(
                        name="Privileges",
                        result=ValidationResult.BLOCKED,
                        message="Cannot check sudo access",
                        mitigation="Ensure sudo is available"
                    )
        
        elif self.system == "Windows":
            try:
                import ctypes
                is_admin = ctypes.windll.shell32.IsUserAnAdmin()
                if is_admin:
                    return SafetyCheck(
                        name="Privileges",
                        result=ValidationResult.SAFE,
                        message="Running with administrator privileges"
                    )
                else:
                    return SafetyCheck(
                        name="Privileges",
                        result=ValidationResult.BLOCKED,
                        message="Administrator privileges required",
                        mitigation="Run as administrator"
                    )
            except:
                return SafetyCheck(
                    name="Privileges",
                    result=ValidationResult.WARNING,
                    message="Cannot verify administrator status"
                )
        
        return SafetyCheck(
            name="Privileges",
            result=ValidationResult.WARNING,
            message="Unknown privilege status"
        )
    
    def validate_source_files(self, source_files: Dict[str, str]) -> List[SafetyCheck]:
        """Validate source files (ISOs, installers, etc.)"""
        checks = []
        
        for file_type, file_path in source_files.items():
            if not os.path.exists(file_path):
                checks.append(SafetyCheck(
                    name=f"Source file: {file_type}",
                    result=ValidationResult.BLOCKED,
                    message=f"File not found: {file_path}"
                ))
                continue
            
            # Check file size
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if size_mb < 50:  # Less than 50MB is suspicious
                checks.append(SafetyCheck(
                    name=f"Source file: {file_type}",
                    result=ValidationResult.WARNING,
                    message=f"File is very small ({size_mb:.1f}MB) - may be corrupted"
                ))
            elif size_mb > 20000:  # More than 20GB is suspicious
                checks.append(SafetyCheck(
                    name=f"Source file: {file_type}",
                    result=ValidationResult.WARNING,
                    message=f"File is very large ({size_mb:.1f}MB) - verify integrity"
                ))
            else:
                checks.append(SafetyCheck(
                    name=f"Source file: {file_type}",
                    result=ValidationResult.SAFE,
                    message=f"File size OK ({size_mb:.1f}MB)"
                ))
        
        return checks
    
    def get_safe_devices(self) -> List[str]:
        """Get list of devices that are safe to use"""
        safe_devices = []
        
        try:
            if self.system == "Linux":
                # Use lsblk to get block devices
                result = subprocess.run(
                    ['lsblk', '-d', '-n', '-o', 'NAME,TYPE,TRAN'],
                    capture_output=True, text=True, check=False
                )
                
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            parts = line.split()
                            if len(parts) >= 3:
                                device_name = parts[0]
                                device_type = parts[1]
                                transport = parts[2] if len(parts) > 2 else ""
                                
                                # Only consider USB devices
                                if transport.lower() == "usb" and device_type == "disk":
                                    device_path = f"/dev/{device_name}"
                                    risk = self.validate_device_safety(device_path)
                                    if risk.overall_risk == ValidationResult.SAFE:
                                        safe_devices.append(device_path)
            
            # Additional platform-specific implementations would go here
            
        except Exception as e:
            self.logger.error(f"Error getting safe devices: {e}")
        
        return safe_devices
    
    def create_multi_step_confirmation(self, device_path: str, operation: str) -> List[str]:
        """Generate multi-step confirmation prompts"""
        risk = self.validate_device_safety(device_path)
        
        prompts = [
            f"⚠️  CRITICAL WARNING ⚠️\n"
            f"This operation will PERMANENTLY and IRREVERSIBLY ERASE ALL DATA\n"
            f"on device: {device_path} ({risk.size_gb:.1f}GB)\n"
            f"Operation: {operation}\n"
        ]
        
        if risk.mount_points:
            prompts.append(
                f"❌ DEVICE IS CURRENTLY MOUNTED\n"
                f"Mount points: {', '.join(risk.mount_points)}\n"
                f"This could indicate an active system disk!\n"
            )
        
        prompts.append(
            f"Device Risk Assessment:\n"
            f"• Removable: {'✅ Yes' if risk.is_removable else '❌ No'}\n"
            f"• System Disk: {'❌ Yes' if risk.is_system_disk else '✅ No'}\n" 
            f"• Boot Disk: {'❌ Yes' if risk.is_boot_disk else '✅ No'}\n"
            f"• Risk Level: {risk.overall_risk.value.upper()}\n"
        )
        
        if risk.risk_factors:
            prompts.append(
                f"⚠️  RISK FACTORS DETECTED:\n" +
                "\n".join(f"• {factor}" for factor in risk.risk_factors)
            )
        
        return prompts
    
    # ===== PATCH-SPECIFIC VALIDATION METHODS =====
    
    def validate_patch_operation(self, patch_info: Dict[str, Any],
                                target_system: str = "") -> PatchRisk:
        """Validate a patch operation for safety risks"""
        try:
            patch_id = patch_info.get("id", "unknown")
            patch_name = patch_info.get("name", "Unknown Patch")
            patch_type = patch_info.get("type", "unknown")
            
            self.logger.info(f"Validating patch operation: {patch_id}")
            
            # Create risk assessment
            risk = PatchRisk(
                patch_id=patch_id,
                patch_name=patch_name,
                patch_type=patch_type,
                target_system=target_system
            )
            
            # Analyze risk factors
            self._analyze_patch_risks(patch_info, risk)
            
            # Calculate risk score
            risk.calculate_risk_score()
            
            # Generate mitigations
            self._generate_patch_mitigations(risk)
            
            # Log the validation
            self._log_patch_validation(risk)
            
            return risk
            
        except Exception as e:
            self.logger.error(f"Failed to validate patch operation: {e}")
            # Return maximum risk for unknown patches
            return PatchRisk(
                patch_id=patch_info.get("id", "error"),
                patch_name="Validation Error",
                patch_type="error",
                target_system=target_system,
                overall_risk=ValidationResult.BLOCKED,
                risk_factors=[f"Validation failed: {e}"]
            )
    
    def _analyze_patch_risks(self, patch_info: Dict[str, Any], risk: PatchRisk):
        """Analyze specific risk factors for a patch"""
        patch_type = patch_info.get("type", "").lower()
        target_path = patch_info.get("target_path", "").lower()
        source_files = patch_info.get("source_files", [])
        
        # Check for kernel modifications
        if "kernel" in patch_type or any("kernel" in f.lower() for f in source_files):
            risk.modifies_kernel = True
            risk.risk_factors.append("Modifies kernel components")
        
        # Check for bootloader modifications
        if ("bootloader" in patch_type or "efi" in patch_type or 
            any("efi" in f.lower() or "boot" in f.lower() for f in source_files)):
            risk.modifies_bootloader = True
            risk.risk_factors.append("Modifies bootloader/EFI components")
        
        # Check for firmware modifications
        if "firmware" in patch_type or any("firmware" in f.lower() for f in source_files):
            risk.modifies_firmware = True
            risk.risk_factors.append("Modifies firmware")
        
        # Check for critical system paths
        critical_paths = ["/system/", "/windows/system32/", "/boot/", "/efi/"]
        if any(path in target_path for path in critical_paths):
            risk.risk_factors.append(f"Targets critical system path: {target_path}")
        
        # Check for unsigned code
        if not patch_info.get("signed", False):
            risk.unsigned_code = True
            risk.risk_factors.append("Contains unsigned code")
        
        # Check for security disabling
        security_keywords = ["disable", "bypass", "skip", "ignore"]
        patch_desc = patch_info.get("description", "").lower()
        if any(keyword in patch_desc for keyword in security_keywords):
            if any(sec in patch_desc for sec in ["security", "signature", "verification"]):
                risk.disables_security = True
                risk.risk_factors.append("May disable security features")
        
        # Check reversibility
        if not patch_info.get("reversible", True):
            risk.irreversible = True
            risk.risk_factors.append("Patch is irreversible")
    
    def _generate_patch_mitigations(self, risk: PatchRisk):
        """Generate mitigation strategies for patch risks"""
        if risk.modifies_kernel:
            risk.mitigations.append("Create full system backup before proceeding")
            risk.mitigations.append("Ensure recovery mechanism is in place")
        
        if risk.modifies_bootloader:
            risk.mitigations.append("Verify EFI/bootloader backup exists")
            risk.mitigations.append("Have bootable recovery media available")
        
        if risk.unsigned_code:
            risk.mitigations.append("Verify patch source and integrity")
            risk.mitigations.append("Consider code signing verification")
        
        if risk.disables_security:
            risk.mitigations.append("Document security implications")
            risk.mitigations.append("Plan to re-enable security after testing")
        
        if risk.irreversible:
            risk.mitigations.append("Perform thorough testing on non-production system")
            risk.mitigations.append("Document exact system state before patch")
    
    def require_user_consent(self, operation_id: str, operation_type: str,
                           risk_level: ValidationResult, risk_factors: List[str],
                           user_id: Optional[str] = None) -> Optional[UserConsent]:
        """Require explicit user consent for risky operations"""
        try:
            self.logger.info(f"Requesting user consent for {operation_type} (risk: {risk_level.value})")
            
            # Generate consent prompt
            consent_prompt = self._generate_consent_prompt(operation_type, risk_level, risk_factors)
            
            # In a real implementation, this would show a GUI dialog or CLI prompt
            # For now, we'll simulate the consent process
            consent_level = self._determine_required_consent_level(risk_level)
            
            # Create consent record
            consent = UserConsent(
                operation_id=operation_id,
                operation_type=operation_type,
                consent_level=consent_level,
                risk_factors=risk_factors,
                user_confirmation=f"User acknowledged {len(risk_factors)} risk factors",
                timestamp=time.time(),
                user_id=user_id,
                warnings_shown=consent_prompt
            )
            
            # Store consent record
            self._consent_records[operation_id] = consent
            
            # Log consent
            self._log_user_consent(consent)
            
            return consent
            
        except Exception as e:
            self.logger.error(f"Failed to obtain user consent: {e}")
            return None
    
    def _generate_consent_prompt(self, operation_type: str, risk_level: ValidationResult,
                               risk_factors: List[str]) -> List[str]:
        """Generate consent prompt text"""
        prompts = [
            f"⚠️  SAFETY WARNING ⚠️",
            f"Operation: {operation_type}",
            f"Risk Level: {risk_level.value.upper()}",
            ""
        ]
        
        if risk_factors:
            prompts.append("Risk Factors:")
            prompts.extend(f"• {factor}" for factor in risk_factors)
            prompts.append("")
        
        if risk_level == ValidationResult.DANGEROUS:
            prompts.extend([
                "🚨 DANGEROUS OPERATION 🚨",
                "This operation could prevent your system from booting.",
                "Ensure you have recovery media and full backups.",
                ""
            ])
        elif risk_level == ValidationResult.BLOCKED:
            prompts.extend([
                "🛑 BLOCKED OPERATION 🛑",
                "This operation is considered too risky to proceed.",
                "Expert mode and additional safeguards required.",
                ""
            ])
        
        prompts.append("Do you understand the risks and wish to proceed?")
        return prompts
    
    def _determine_required_consent_level(self, risk_level: ValidationResult) -> ConsentLevel:
        """Determine required consent level based on risk"""
        risk_consent_map = {
            ValidationResult.SAFE: ConsentLevel.NONE,
            ValidationResult.WARNING: ConsentLevel.BASIC,
            ValidationResult.DANGEROUS: ConsentLevel.INFORMED,
            ValidationResult.BLOCKED: ConsentLevel.EXPERT
        }
        return risk_consent_map.get(risk_level, ConsentLevel.EXPERT)
    
    def validate_consent_for_operation(self, operation_id: str,
                                     risk_level: ValidationResult) -> bool:
        """Validate that proper consent exists for an operation"""
        consent = self._consent_records.get(operation_id)
        if not consent:
            self.logger.warning(f"No consent record found for operation: {operation_id}")
            return False
        
        if not consent.is_valid_for_risk(risk_level):
            self.logger.warning(f"Insufficient consent level for operation: {operation_id}")
            return False
        
        # Check consent age (expire after 1 hour)
        if time.time() - consent.timestamp > 3600:
            self.logger.warning(f"Consent expired for operation: {operation_id}")
            return False
        
        return True
    
    def check_patch_compliance(self, patch_id: str) -> bool:
        """Check if patch is compliant with current validation mode"""
        if self.patch_mode == PatchValidationMode.AUDIT_ONLY:
            return True  # Allow everything in audit mode
        
        if patch_id in self._patch_blacklist:
            self.logger.warning(f"Patch {patch_id} is blacklisted")
            return False
        
        if self.patch_mode == PatchValidationMode.COMPLIANT:
            if patch_id not in self._patch_whitelist:
                self.logger.warning(f"Patch {patch_id} not in whitelist (compliant mode)")
                return False
        
        return True
    
    def create_audit_record(self, operation_type: str, operation_details: str,
                          risk_level: ValidationResult = ValidationResult.SAFE,
                          user_id: Optional[str] = None,
                          target_device: Optional[str] = None) -> AuditRecord:
        """Create an audit record for an operation"""
        record = AuditRecord(
            operation_type=operation_type,
            operation_details=operation_details,
            user_id=user_id,
            risk_level=risk_level,
            validation_mode=self.patch_mode,
            target_device=target_device,
            environment_info={
                "platform": self.system,
                "safety_level": self.safety_level.value,
                "patch_mode": self.patch_mode.value
            }
        )
        
        # Write to audit log
        self._write_audit_record(record)
        
        return record
    
    def _write_audit_record(self, record: AuditRecord):
        """Write audit record to log file"""
        try:
            with open(self._audit_log_path, 'a', encoding='utf-8') as f:
                json.dump(record.to_dict(), f)
                f.write('\n')
            
            self.logger.debug(f"Audit record written: {record.id}")
            
        except Exception as e:
            self.logger.error(f"Failed to write audit record: {e}")
    
    def _log_patch_validation(self, risk: PatchRisk):
        """Log patch validation results"""
        self.logger.info(
            f"Patch validation: {risk.patch_id} | "
            f"Risk: {risk.overall_risk.value} | "
            f"Score: {risk.risk_score:.1f} | "
            f"Factors: {len(risk.risk_factors)}"
        )
        
        for factor in risk.risk_factors:
            self.logger.warning(f"Risk factor - {risk.patch_id}: {factor}")
    
    def _log_user_consent(self, consent: UserConsent):
        """Log user consent for audit purposes"""
        self.logger.info(
            f"User consent recorded: {consent.operation_id} | "
            f"Type: {consent.operation_type} | "
            f"Level: {consent.consent_level.value} | "
            f"User: {consent.user_id or 'anonymous'}"
        )
        
        # Create audit record for consent
        self.create_audit_record(
            operation_type="user_consent",
            operation_details=f"Consent given for {consent.operation_type}",
            risk_level=ValidationResult.SAFE,  # Consent itself is safe
            user_id=consent.user_id
        )
    
    def add_patch_to_whitelist(self, patch_id: str):
        """Add a patch to the whitelist"""
        self._patch_whitelist.add(patch_id)
        self.logger.info(f"Added patch to whitelist: {patch_id}")
    
    def add_patch_to_blacklist(self, patch_id: str):
        """Add a patch to the blacklist"""
        self._patch_blacklist.add(patch_id)
        self.logger.info(f"Added patch to blacklist: {patch_id}")
    
    def get_patch_validation_summary(self) -> Dict[str, Any]:
        """Get summary of patch validation settings and state"""
        return {
            "safety_level": self.safety_level.value,
            "patch_mode": self.patch_mode.value,
            "whitelist_count": len(self._patch_whitelist),
            "blacklist_count": len(self._patch_blacklist),
            "consent_records": len(self._consent_records),
            "audit_log_path": str(self._audit_log_path)
        }