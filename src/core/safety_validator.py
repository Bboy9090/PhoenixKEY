"""
BootForge Safety Validation System
Critical safety measures to prevent system disk destruction and ensure safe USB operations
"""

import os
import re
import time
import logging
import platform
import subprocess
import psutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
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


class SafetyValidator:
    """Comprehensive safety validation system"""
    
    def __init__(self, safety_level: SafetyLevel = SafetyLevel.STANDARD):
        self.logger = logging.getLogger(__name__)
        self.safety_level = safety_level
        self.system = platform.system()
        self.blocked_patterns = self._get_blocked_device_patterns()
        self.required_tools = self._get_required_tools()
        
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
    
    def _get_required_tools(self) -> Dict[str, List[str]]:
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
                
        except Exception as e:
            self.logger.error(f"Error checking if device is removable: {e}")
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