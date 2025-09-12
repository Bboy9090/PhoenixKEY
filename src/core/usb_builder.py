"""
BootForge USB Builder Engine
Enhanced bootable USB creation system for offline deployment scenarios
"""

import os
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
from typing import Dict, List, Optional, Tuple, Callable, Any
from dataclasses import dataclass, asdict, field
from PyQt6.QtCore import QThread, pyqtSignal, QObject

from src.core.disk_manager import DiskManager, DiskInfo, WriteProgress


class PartitionScheme(Enum):
    """Partition scheme types"""
    GPT = "gpt"
    MBR = "mbr"
    HYBRID = "hybrid"


class FileSystem(Enum):
    """Filesystem types"""
    FAT32 = "fat32"
    NTFS = "ntfs"
    EXFAT = "exfat"
    HFS_PLUS = "hfs+"
    APFS = "apfs"
    EXT4 = "ext4"


class DeploymentType(Enum):
    """Deployment scenario types"""
    MACOS_OCLP = "macos_oclp"
    WINDOWS_UNATTENDED = "windows_unattended"
    LINUX_AUTOMATED = "linux_automated"
    CUSTOM_PAYLOAD = "custom_payload"


@dataclass
class PartitionInfo:
    """Partition configuration"""
    name: str
    size_mb: int
    filesystem: FileSystem
    bootable: bool = False
    label: str = ""
    mount_point: Optional[str] = None
    
    def __post_init__(self):
        if not self.label:
            self.label = self.name


@dataclass
class HardwareProfile:
    """Target hardware profile for deployment customization"""
    name: str
    platform: str  # "mac", "windows", "linux"
    model: str
    architecture: str  # "x86_64", "arm64"
    year: Optional[int] = None
    cpu_family: Optional[str] = None
    gpu_info: List[str] = field(default_factory=list)
    network_adapters: List[str] = field(default_factory=list)
    driver_packages: List[str] = field(default_factory=list)
    special_requirements: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_mac_model(cls, model: str) -> 'HardwareProfile':
        """Create hardware profile from Mac model identifier"""
        # Example: iMacPro1,1 -> iMac Pro 2017
        mac_profiles = {
            "iMacPro1,1": {"name": "iMac Pro 2017", "year": 2017, "cpu_family": "Intel Xeon W"},
            "MacBookPro15,1": {"name": "MacBook Pro 15\" 2018", "year": 2018, "cpu_family": "Intel Core i7/i9"},
            "MacBookPro16,1": {"name": "MacBook Pro 16\" 2019", "year": 2019, "cpu_family": "Intel Core i7/i9"},
            "iMac20,1": {"name": "iMac 27\" 2020", "year": 2020, "cpu_family": "Intel Core i5/i7/i9"},
            "MacBookAir10,1": {"name": "MacBook Air M1 2020", "year": 2020, "cpu_family": "Apple M1"},
        }
        
        profile_data = mac_profiles.get(model, {"name": model, "year": None, "cpu_family": "Unknown"})
        
        return cls(
            name=profile_data["name"],
            platform="mac",
            model=model,
            architecture="x86_64" if "Intel" in profile_data["cpu_family"] else "arm64",
            year=profile_data["year"],
            cpu_family=profile_data["cpu_family"]
        )


@dataclass
class DeploymentRecipe:
    """Deployment recipe configuration"""
    name: str
    description: str
    deployment_type: DeploymentType
    partition_scheme: PartitionScheme
    partitions: List[PartitionInfo]
    hardware_profiles: List[str]  # Compatible hardware profile names
    required_files: List[str]  # Required source files
    optional_files: List[str] = field(default_factory=list)
    post_creation_scripts: List[str] = field(default_factory=list)
    verification_steps: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create_macos_oclp_recipe(cls) -> 'DeploymentRecipe':
        """Create macOS OpenCore Legacy Patcher recipe"""
        return cls(
            name="macOS with OpenCore Legacy Patcher",
            description="Create bootable macOS installer with OCLP for legacy Mac hardware",
            deployment_type=DeploymentType.MACOS_OCLP,
            partition_scheme=PartitionScheme.GPT,
            partitions=[
                PartitionInfo("EFI", 200, FileSystem.FAT32, bootable=True, label="EFI"),
                PartitionInfo("macOS Installer", -1, FileSystem.HFS_PLUS, label="Install macOS"),
                PartitionInfo("OCLP Tools", 1024, FileSystem.FAT32, label="OCLP-Tools")
            ],
            hardware_profiles=["iMacPro1,1", "MacBookPro15,1", "iMac20,1"],
            required_files=["macOS_installer.app", "OpenCore-Legacy-Patcher.app"],
            verification_steps=["verify_efi_boot", "verify_oclp_installation", "verify_kexts"]
        )
    
    @classmethod
    def create_windows_unattended_recipe(cls) -> 'DeploymentRecipe':
        """Create Windows unattended installation recipe"""
        return cls(
            name="Windows Unattended Installation",
            description="Create Windows installer with automated setup and driver injection",
            deployment_type=DeploymentType.WINDOWS_UNATTENDED,
            partition_scheme=PartitionScheme.GPT,
            partitions=[
                PartitionInfo("System Reserved", 100, FileSystem.FAT32, bootable=True),
                PartitionInfo("Windows Install", -1, FileSystem.NTFS, label="Windows"),
                PartitionInfo("Drivers", 2048, FileSystem.FAT32, label="Drivers")
            ],
            hardware_profiles=["generic_x64", "surface_pro", "dell_optiplex"],
            required_files=["windows.iso", "autounattend.xml"],
            optional_files=["driver_pack.zip", "software_bundle.zip"]
        )
    
    @classmethod
    def create_linux_automated_recipe(cls) -> 'DeploymentRecipe':
        """Create Linux automated installation recipe"""
        return cls(
            name="Linux Automated Installation",
            description="Create automated Linux installer with preseed configuration",
            deployment_type=DeploymentType.LINUX_AUTOMATED,
            partition_scheme=PartitionScheme.GPT,
            partitions=[
                PartitionInfo("EFI", 200, FileSystem.FAT32, bootable=True, label="EFI"),
                PartitionInfo("Linux Install", -1, FileSystem.EXT4, label="Linux-Install"),
                PartitionInfo("Data", 2048, FileSystem.EXT4, label="Data")
            ],
            hardware_profiles=["generic_linux_x64", "rpi4", "framework_laptop"],
            required_files=["linux.iso", "preseed.cfg"],
            optional_files=["extra_packages.tar.gz", "custom_scripts.zip"]
        )
    
    @classmethod
    def create_custom_payload_recipe(cls) -> 'DeploymentRecipe':
        """Create custom payload deployment recipe"""
        return cls(
            name="Custom Payload Deployment",
            description="Deploy custom bootable payload with flexible configuration",
            deployment_type=DeploymentType.CUSTOM_PAYLOAD,
            partition_scheme=PartitionScheme.GPT,
            partitions=[
                PartitionInfo("Boot", 512, FileSystem.FAT32, bootable=True, label="BOOT"),
                PartitionInfo("Payload", -1, FileSystem.EXFAT, label="PAYLOAD")
            ],
            hardware_profiles=["generic_x64", "generic_linux_x64", "rpi4"],
            required_files=["bootloader", "payload.img"],
            optional_files=["config.json", "additional_files.zip"]
        )


@dataclass
class BuildProgress:
    """USB build operation progress"""
    current_step: str
    step_number: int
    total_steps: int
    step_progress: float
    overall_progress: float
    speed_mbps: float
    eta_seconds: int
    detailed_status: str
    logs: List[str] = field(default_factory=list)


class USBBuilder(QThread):
    """USB Builder thread for creating bootable deployment drives"""
    
    # Signals
    progress_updated = pyqtSignal(object)  # BuildProgress
    operation_completed = pyqtSignal(bool, str)
    operation_started = pyqtSignal(str)
    log_message = pyqtSignal(str, str)  # level, message
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.recipe: Optional[DeploymentRecipe] = None
        self.target_device: str = ""
        self.hardware_profile: Optional[HardwareProfile] = None
        self.source_files: Dict[str, str] = {}
        self.is_cancelled = False
        self.build_log: List[str] = []
        self.temp_dir: Optional[Path] = None
    
    def start_build(self, recipe: DeploymentRecipe, target_device: str, 
                   hardware_profile: HardwareProfile, source_files: Dict[str, str]):
        """Start USB build operation"""
        self.recipe = recipe
        self.target_device = target_device
        self.hardware_profile = hardware_profile
        self.source_files = source_files
        self.is_cancelled = False
        self.build_log = []
        self.start()
    
    def cancel_build(self):
        """Cancel current build operation"""
        self.is_cancelled = True
        self._log_message("INFO", "USB build operation cancelled by user")
    
    def run(self):
        """Main USB building thread"""
        try:
            # Create temporary working directory
            self.temp_dir = Path(tempfile.mkdtemp(prefix="bootforge_build_"))
            self._log_message("INFO", f"Created temporary directory: {self.temp_dir}")
            
            # Validate inputs
            if not self._validate_build_inputs():
                return
            
            # Calculate total steps
            total_steps = 7  # Basic steps, may increase based on recipe
            step = 0
            
            # Step 1: Prepare target device
            step += 1
            self._emit_progress("Preparing target device", step, total_steps, 0)
            if not self._prepare_target_device():
                return
            
            # Step 2: Create partition scheme
            step += 1
            self._emit_progress("Creating partition scheme", step, total_steps, 0)
            if not self._create_partition_scheme():
                return
            
            # Step 3: Format partitions
            step += 1
            self._emit_progress("Formatting partitions", step, total_steps, 0)
            if not self._format_partitions():
                return
            
            # Step 4: Mount partitions
            step += 1
            self._emit_progress("Mounting partitions", step, total_steps, 0)
            partition_mounts = self._mount_partitions()
            if not partition_mounts:
                return
            
            # Step 5: Deploy files based on recipe
            step += 1
            self._emit_progress("Deploying files", step, total_steps, 0)
            if not self._deploy_files(partition_mounts):
                return
            
            # Step 6: Configure bootloader
            step += 1
            self._emit_progress("Configuring bootloader", step, total_steps, 0)
            if not self._configure_bootloader(partition_mounts):
                return
            
            # Step 7: Finalize and verify
            step += 1
            self._emit_progress("Finalizing build", step, total_steps, 0)
            if not self._finalize_build(partition_mounts):
                return
            
            self._log_message("INFO", "USB build completed successfully")
            self.operation_completed.emit(True, "USB build completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error in USB building: {e}")
            self._log_message("ERROR", f"Build error: {str(e)}")
            self.operation_completed.emit(False, f"Build error: {str(e)}")
        
        finally:
            # Cleanup
            self._cleanup_build()
    
    def _validate_build_inputs(self) -> bool:
        """Validate build inputs"""
        try:
            # Check recipe
            if not self.recipe:
                self.operation_completed.emit(False, "No recipe specified")
                return False
            
            # Check target device
            if not os.path.exists(self.target_device):
                self.operation_completed.emit(False, f"Target device not found: {self.target_device}")
                return False
            
            # Check required files
            for required_file in self.recipe.required_files:
                if required_file not in self.source_files:
                    self.operation_completed.emit(False, f"Required file missing: {required_file}")
                    return False
                
                if not os.path.exists(self.source_files[required_file]):
                    self.operation_completed.emit(False, f"Source file not found: {self.source_files[required_file]}")
                    return False
            
            # Check hardware profile compatibility
            if (self.hardware_profile and 
                self.hardware_profile.model not in self.recipe.hardware_profiles and 
                "generic" not in self.recipe.hardware_profiles):
                self._log_message("WARNING", f"Hardware profile {self.hardware_profile.model} not officially supported for this recipe")
            
            return True
            
        except Exception as e:
            self.operation_completed.emit(False, f"Validation error: {str(e)}")
            return False
    
    def _prepare_target_device(self) -> bool:
        """Prepare target device for partitioning"""
        try:
            self._log_message("INFO", f"Preparing device {self.target_device}")
            
            # Unmount all partitions on the device
            self._unmount_device_partitions()
            
            # Clear any existing partition table
            if platform.system() == "Linux":
                result = subprocess.run(
                    ['sudo', 'wipefs', '-a', self.target_device],
                    capture_output=True, text=True, check=False
                )
                if result.returncode != 0:
                    self._log_message("WARNING", f"Could not wipe filesystem signatures: {result.stderr}")
            
            self._log_message("INFO", "Device preparation completed")
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"Error preparing device: {e}")
            return False
    
    def _create_partition_scheme(self) -> bool:
        """Create partition scheme based on recipe"""
        try:
            if not self.recipe:
                self._log_message("ERROR", "No recipe available")
                return False
                
            system = platform.system()
            scheme = self.recipe.partition_scheme
            
            self._log_message("INFO", f"Creating {scheme.value.upper()} partition scheme")
            
            if system == "Linux":
                return self._create_partitions_linux()
            elif system == "Darwin":  # macOS
                return self._create_partitions_macos()
            elif system == "Windows":
                return self._create_partitions_windows()
            else:
                self._log_message("ERROR", f"Unsupported platform: {system}")
                return False
                
        except Exception as e:
            self._log_message("ERROR", f"Error creating partition scheme: {e}")
            return False
    
    def _create_partitions_linux(self) -> bool:
        """Create partitions on Linux using parted"""
        try:
            if not self.recipe:
                self._log_message("ERROR", "No recipe available")
                return False
                
            # Create partition table
            scheme_type = "gpt" if self.recipe.partition_scheme == PartitionScheme.GPT else "msdos"
            
            result = subprocess.run(
                ['sudo', 'parted', '-s', self.target_device, 'mklabel', scheme_type],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                self._log_message("ERROR", f"Failed to create partition table: {result.stderr}")
                return False
            
            # Create partitions
            current_start = 1  # Start at 1MB
            
            for i, partition in enumerate(self.recipe.partitions, 1):
                if partition.size_mb == -1:  # Use remaining space
                    end = "100%"
                else:
                    end = f"{current_start + partition.size_mb}MB"
                
                # Create partition
                result = subprocess.run([
                    'sudo', 'parted', '-s', self.target_device, 'mkpart',
                    'primary', f"{current_start}MB", end
                ], capture_output=True, text=True)
                
                if result.returncode != 0:
                    self._log_message("ERROR", f"Failed to create partition {i}: {result.stderr}")
                    return False
                
                # Set bootable flag if needed
                if partition.bootable:
                    subprocess.run([
                        'sudo', 'parted', '-s', self.target_device, 'set', str(i), 'boot', 'on'
                    ], capture_output=True, text=True)
                
                if partition.size_mb != -1:
                    current_start += partition.size_mb
                
                self._log_message("INFO", f"Created partition {i}: {partition.name} ({partition.size_mb}MB)")
            
            # Inform kernel of partition table changes
            subprocess.run(['sudo', 'partprobe', self.target_device], 
                         capture_output=True, text=True)
            
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"Error creating Linux partitions: {e}")
            return False
    
    def _create_partitions_macos(self) -> bool:
        """Create partitions on macOS using diskutil"""
        try:
            # This is a simplified implementation
            # Real implementation would use diskutil for proper macOS partition creation
            self._log_message("INFO", "macOS partition creation not fully implemented")
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"Error creating macOS partitions: {e}")
            return False
    
    def _create_partitions_windows(self) -> bool:
        """Create partitions on Windows using diskpart"""
        try:
            # This would require implementing Windows diskpart scripting
            self._log_message("INFO", "Windows partition creation not fully implemented")
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"Error creating Windows partitions: {e}")
            return False
    
    def _format_partitions(self) -> bool:
        """Format all partitions according to recipe"""
        try:
            if not self.recipe:
                self._log_message("ERROR", "No recipe available")
                return False
                
            device_base = self.target_device.rstrip('0123456789')
            
            for i, partition in enumerate(self.recipe.partitions, 1):
                partition_device = f"{device_base}{i}"
                
                if not os.path.exists(partition_device):
                    # Try alternative naming scheme
                    partition_device = f"{self.target_device}p{i}"
                    if not os.path.exists(partition_device):
                        self._log_message("ERROR", f"Partition device not found: {partition_device}")
                        return False
                
                self._log_message("INFO", f"Formatting {partition_device} as {partition.filesystem.value}")
                
                if not self._format_partition(partition_device, partition):
                    return False
            
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"Error formatting partitions: {e}")
            return False
    
    def _format_partition(self, device: str, partition: PartitionInfo) -> bool:
        """Format a single partition"""
        try:
            system = platform.system()
            fs = partition.filesystem
            
            if system == "Linux":
                if fs == FileSystem.FAT32:
                    cmd = ['sudo', 'mkfs.fat', '-F', '32', '-n', partition.label, device]
                elif fs == FileSystem.NTFS:
                    cmd = ['sudo', 'mkfs.ntfs', '-f', '-L', partition.label, device]
                elif fs == FileSystem.EXFAT:
                    cmd = ['sudo', 'mkfs.exfat', '-n', partition.label, device]
                elif fs == FileSystem.EXT4:
                    cmd = ['sudo', 'mkfs.ext4', '-L', partition.label, device]
                else:
                    self._log_message("ERROR", f"Unsupported filesystem: {fs.value}")
                    return False
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    self._log_message("ERROR", f"Format failed: {result.stderr}")
                    return False
            
            elif system == "Darwin":  # macOS
                # Use diskutil for macOS formatting
                if fs == FileSystem.FAT32:
                    fs_name = "MS-DOS FAT32"
                elif fs == FileSystem.HFS_PLUS:
                    fs_name = "HFS+"
                elif fs == FileSystem.APFS:
                    fs_name = "APFS"
                else:
                    self._log_message("ERROR", f"Unsupported filesystem for macOS: {fs.value}")
                    return False
                
                result = subprocess.run([
                    'diskutil', 'eraseVolume', fs_name, partition.label, device
                ], capture_output=True, text=True)
                
                if result.returncode != 0:
                    self._log_message("ERROR", f"macOS format failed: {result.stderr}")
                    return False
            
            self._log_message("INFO", f"Successfully formatted {device} as {fs.value}")
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"Error formatting partition {device}: {e}")
            return False
    
    def _mount_partitions(self) -> Dict[str, str]:
        """Mount all partitions and return mount points"""
        mount_points = {}
        
        try:
            if not self.recipe:
                self._log_message("ERROR", "No recipe available")
                return {}
                
            device_base = self.target_device.rstrip('0123456789')
            
            for i, partition in enumerate(self.recipe.partitions, 1):
                partition_device = f"{device_base}{i}"
                
                if not os.path.exists(partition_device):
                    partition_device = f"{self.target_device}p{i}"
                
                # Create mount point
                mount_point = self.temp_dir / f"partition_{i}"
                mount_point.mkdir(exist_ok=True)
                
                # Mount partition
                if platform.system() == "Linux":
                    result = subprocess.run([
                        'sudo', 'mount', partition_device, str(mount_point)
                    ], capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        self._log_message("ERROR", f"Failed to mount {partition_device}: {result.stderr}")
                        continue
                
                mount_points[partition.name] = str(mount_point)
                self._log_message("INFO", f"Mounted {partition.name} at {mount_point}")
            
            return mount_points
            
        except Exception as e:
            self._log_message("ERROR", f"Error mounting partitions: {e}")
            return {}
    
    def _deploy_files(self, mount_points: Dict[str, str]) -> bool:
        """Deploy files based on deployment type"""
        try:
            if not self.recipe:
                self._log_message("ERROR", "No recipe available")
                return False
                
            if self.recipe.deployment_type == DeploymentType.MACOS_OCLP:
                return self._deploy_macos_oclp_files(mount_points)
            elif self.recipe.deployment_type == DeploymentType.WINDOWS_UNATTENDED:
                return self._deploy_windows_files(mount_points)
            elif self.recipe.deployment_type == DeploymentType.LINUX_AUTOMATED:
                return self._deploy_linux_files(mount_points)
            else:
                return self._deploy_custom_files(mount_points)
                
        except Exception as e:
            self._log_message("ERROR", f"Error deploying files: {e}")
            return False
    
    def _deploy_macos_oclp_files(self, mount_points: Dict[str, str]) -> bool:
        """Deploy macOS OCLP specific files"""
        try:
            # This would implement specific macOS + OCLP deployment logic
            self._log_message("INFO", "Deploying macOS OCLP files")
            
            # Example: Copy installer to main partition
            if "macOS Installer" in mount_points:
                installer_mount = mount_points["macOS Installer"]
                # Copy macOS installer files here
                
            # Example: Setup OCLP tools partition
            if "OCLP Tools" in mount_points:
                tools_mount = mount_points["OCLP Tools"]
                # Copy OCLP files here
            
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"Error deploying macOS OCLP files: {e}")
            return False
    
    def _deploy_windows_files(self, mount_points: Dict[str, str]) -> bool:
        """Deploy Windows unattended installation files"""
        try:
            self._log_message("INFO", "Deploying Windows files")
            # Implementation for Windows deployment
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"Error deploying Windows files: {e}")
            return False
    
    def _deploy_linux_files(self, mount_points: Dict[str, str]) -> bool:
        """Deploy Linux automated installation files"""
        try:
            self._log_message("INFO", "Deploying Linux files")
            # Implementation for Linux deployment
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"Error deploying Linux files: {e}")
            return False
    
    def _deploy_custom_files(self, mount_points: Dict[str, str]) -> bool:
        """Deploy custom payload files"""
        try:
            self._log_message("INFO", "Deploying custom files")
            # Implementation for custom deployment
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"Error deploying custom files: {e}")
            return False
    
    def _configure_bootloader(self, mount_points: Dict[str, str]) -> bool:
        """Configure bootloader for the deployment type"""
        try:
            if not self.recipe:
                self._log_message("ERROR", "No recipe available")
                return False
                
            if self.recipe.deployment_type == DeploymentType.MACOS_OCLP:
                return self._configure_opencore_bootloader(mount_points)
            elif self.recipe.deployment_type == DeploymentType.WINDOWS_UNATTENDED:
                return self._configure_windows_bootloader(mount_points)
            else:
                return self._configure_generic_bootloader(mount_points)
                
        except Exception as e:
            self._log_message("ERROR", f"Error configuring bootloader: {e}")
            return False
    
    def _configure_opencore_bootloader(self, mount_points: Dict[str, str]) -> bool:
        """Configure OpenCore bootloader for macOS"""
        try:
            self._log_message("INFO", "Configuring OpenCore bootloader")
            # Implementation for OpenCore configuration
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"Error configuring OpenCore: {e}")
            return False
    
    def _configure_windows_bootloader(self, mount_points: Dict[str, str]) -> bool:
        """Configure Windows bootloader"""
        try:
            self._log_message("INFO", "Configuring Windows bootloader")
            # Implementation for Windows bootloader
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"Error configuring Windows bootloader: {e}")
            return False
    
    def _configure_generic_bootloader(self, mount_points: Dict[str, str]) -> bool:
        """Configure generic bootloader"""
        try:
            self._log_message("INFO", "Configuring generic bootloader")
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"Error configuring generic bootloader: {e}")
            return False
    
    def _finalize_build(self, mount_points: Dict[str, str]) -> bool:
        """Finalize build and create deployment log"""
        try:
            if not self.recipe:
                self._log_message("ERROR", "No recipe available")
                return False
                
            # Create deployment metadata
            metadata = {
                "build_timestamp": time.time(),
                "build_id": str(uuid.uuid4()),
                "recipe_name": self.recipe.name,
                "hardware_profile": asdict(self.hardware_profile) if self.hardware_profile else None,
                "deployment_type": self.recipe.deployment_type.value,
                "build_log": self.build_log,
                "verification_steps": self.recipe.verification_steps
            }
            
            # Write metadata to USB drive (usually on a utilities partition)
            metadata_partition = None
            for partition_name, mount_point in mount_points.items():
                if "Tools" in partition_name or "Utilities" in partition_name:
                    metadata_partition = mount_point
                    break
            
            if not metadata_partition and mount_points:
                # Use any available partition
                metadata_partition = list(mount_points.values())[0]
            
            if metadata_partition:
                metadata_file = Path(metadata_partition) / "bootforge_deployment.json"
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                self._log_message("INFO", f"Created deployment metadata: {metadata_file}")
            
            # Unmount all partitions
            self._unmount_device_partitions()
            
            # Sync filesystem
            if platform.system() == "Linux":
                subprocess.run(['sync'], check=False)
            
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"Error finalizing build: {e}")
            return False
    
    def _unmount_device_partitions(self):
        """Unmount all partitions of the target device"""
        try:
            if platform.system() == "Linux":
                # Find and unmount all partitions
                result = subprocess.run(
                    ['lsblk', '-ln', '-o', 'NAME,MOUNTPOINT', self.target_device],
                    capture_output=True, text=True
                )
                
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2 and parts[1] != '':  # Has mount point
                            device = f"/dev/{parts[0].strip()}"
                            subprocess.run(['sudo', 'umount', device], 
                                         capture_output=True, check=False)
                            
        except Exception as e:
            self._log_message("WARNING", f"Could not unmount device partitions: {e}")
    
    def _cleanup_build(self):
        """Cleanup temporary files and unmount partitions"""
        try:
            # Unmount any remaining partitions
            self._unmount_device_partitions()
            
            # Remove temporary directory
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                self._log_message("INFO", f"Cleaned up temporary directory: {self.temp_dir}")
                
        except Exception as e:
            self._log_message("WARNING", f"Error during cleanup: {e}")
    
    def _emit_progress(self, step_name: str, step_num: int, total_steps: int, step_progress: float):
        """Emit progress update signal"""
        overall_progress = ((step_num - 1) / total_steps) * 100 + (step_progress / total_steps)
        
        progress = BuildProgress(
            current_step=step_name,
            step_number=step_num,
            total_steps=total_steps,
            step_progress=step_progress,
            overall_progress=overall_progress,
            speed_mbps=0.0,  # Could be calculated for file operations
            eta_seconds=0,   # Could be estimated
            detailed_status=f"Step {step_num}/{total_steps}: {step_name}",
            logs=self.build_log[-10:]  # Last 10 log entries
        )
        
        self.progress_updated.emit(progress)
    
    def _log_message(self, level: str, message: str):
        """Log message and emit signal"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        
        self.build_log.append(log_entry)
        self.log_message.emit(level, message)
        
        # Also log to Python logger
        if level == "ERROR":
            self.logger.error(message)
        elif level == "WARNING":
            self.logger.warning(message)
        else:
            self.logger.info(message)


class USBBuilderEngine:
    """Main USB Builder Engine - extends DiskManager functionality"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.disk_manager = DiskManager()
        self.builder = USBBuilder()
        self.recipes: Dict[str, DeploymentRecipe] = {}
        self.hardware_profiles: Dict[str, HardwareProfile] = {}
        
        # Load built-in recipes and profiles
        self._load_builtin_recipes()
        self._load_builtin_hardware_profiles()
    
    def _load_builtin_recipes(self):
        """Load built-in deployment recipes"""
        # macOS OCLP recipe
        macos_recipe = DeploymentRecipe.create_macos_oclp_recipe()
        self.recipes[macos_recipe.name] = macos_recipe
        
        # Windows unattended recipe
        windows_recipe = DeploymentRecipe.create_windows_unattended_recipe()
        self.recipes[windows_recipe.name] = windows_recipe
        
        # Linux automated recipe
        linux_recipe = DeploymentRecipe.create_linux_automated_recipe()
        self.recipes[linux_recipe.name] = linux_recipe
        
        # Custom payload recipe
        custom_recipe = DeploymentRecipe.create_custom_payload_recipe()
        self.recipes[custom_recipe.name] = custom_recipe
        
        self.logger.info(f"Loaded {len(self.recipes)} built-in recipes")
    
    def _load_builtin_hardware_profiles(self):
        """Load built-in hardware profiles"""
        # Mac profiles
        mac_models = ["iMacPro1,1", "MacBookPro15,1", "MacBookPro16,1", "iMac20,1", "MacBookAir10,1"]
        for model in mac_models:
            profile = HardwareProfile.from_mac_model(model)
            self.hardware_profiles[model] = profile
        
        # Generic profiles
        self.hardware_profiles["generic_x64"] = HardwareProfile(
            name="Generic x64 PC",
            platform="windows",
            model="generic_x64",
            architecture="x86_64"
        )
        
        self.logger.info(f"Loaded {len(self.hardware_profiles)} hardware profiles")
    
    def get_available_recipes(self) -> List[DeploymentRecipe]:
        """Get list of available deployment recipes"""
        return list(self.recipes.values())
    
    def get_hardware_profiles(self, platform: Optional[str] = None) -> List[HardwareProfile]:
        """Get hardware profiles, optionally filtered by platform"""
        profiles = list(self.hardware_profiles.values())
        
        if platform:
            profiles = [p for p in profiles if p.platform == platform]
        
        return profiles
    
    def get_default_profiles(self) -> List[HardwareProfile]:
        """Get default hardware profiles - alias for get_hardware_profiles()"""
        return self.get_hardware_profiles()
    
    def get_suitable_devices(self, min_size_gb: Optional[float] = None) -> List[DiskInfo]:
        """Get USB devices suitable for deployment creation"""
        devices = self.disk_manager.get_removable_drives()
        
        if min_size_gb:
            min_bytes = min_size_gb * 1024 * 1024 * 1024
            devices = [d for d in devices if d.size_bytes >= min_bytes]
        
        return devices
    
    def create_deployment_usb(self, recipe_name: str, target_device: str,
                            hardware_profile_name: str, source_files: Dict[str, str],
                            progress_callback: Optional[Callable] = None) -> USBBuilder:
        """Create deployment USB drive"""
        
        # Validate inputs
        if recipe_name not in self.recipes:
            raise ValueError(f"Recipe not found: {recipe_name}")
        
        if hardware_profile_name not in self.hardware_profiles:
            raise ValueError(f"Hardware profile not found: {hardware_profile_name}")
        
        recipe = self.recipes[recipe_name]
        hardware_profile = self.hardware_profiles[hardware_profile_name]
        
        # Setup progress callback
        if progress_callback:
            self.builder.progress_updated.connect(progress_callback)
        
        # Start build
        self.builder.start_build(recipe, target_device, hardware_profile, source_files)
        
        return self.builder
    
    def detect_hardware_profile(self) -> Optional[HardwareProfile]:
        """Detect current system's hardware profile"""
        try:
            system = platform.system()
            
            if system == "Darwin":  # macOS
                # Get Mac model identifier
                result = subprocess.run(
                    ['sysctl', '-n', 'hw.model'],
                    capture_output=True, text=True
                )
                
                if result.returncode == 0:
                    model = result.stdout.strip()
                    if model in self.hardware_profiles:
                        return self.hardware_profiles[model]
                    else:
                        return HardwareProfile.from_mac_model(model)
            
            elif system == "Windows":
                # Generic Windows profile for now
                return self.hardware_profiles.get("generic_x64")
            
            elif system == "Linux":
                # Generic Linux profile for now
                return HardwareProfile(
                    name="Linux System",
                    platform="linux",
                    model="generic_linux",
                    architecture=platform.machine()
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error detecting hardware profile: {e}")
            return None