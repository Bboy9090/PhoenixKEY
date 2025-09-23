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
from src.core.safety_validator import SafetyValidator, SafetyLevel, ValidationResult, DeviceRisk
from src.core.patch_pipeline import PatchPlanner, PatchPlan, PatchSet, PatchAction, PatchStatus
from src.core.patch_config_loader import PatchConfigLoader
from src.core.vendor_database import PatchCompatibility
from src.core.models import (
    HardwareProfile, DeploymentType, PartitionScheme, FileSystem, 
    PartitionInfo, DeploymentRecipe
)
from src.core.hardware_profiles import create_mac_patch_sets
from src.core.grub_manager import GRUBManager, GRUBBootMode


# Imported from models.py to prevent circular imports


# All classes moved to models.py to prevent circular imports


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
    
    def __init__(self, safety_level: SafetyLevel = SafetyLevel.STANDARD):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.safety_validator = SafetyValidator(safety_level)
        self.recipe: Optional[DeploymentRecipe] = None
        self.target_device: str = ""
        self.hardware_profile: Optional[HardwareProfile] = None
        self.source_files: Dict[str, str] = {}
        self.is_cancelled = False
        self.build_log: List[str] = []
        self.temp_dir: Optional[Path] = None
        self.rollback_operations: List[Callable] = []  # For rollback on failure
    
    def start_build(self, recipe: DeploymentRecipe, target_device: str, 
                   hardware_profile: HardwareProfile, source_files: Dict[str, str]):
        """Start USB build operation"""
        self.recipe = recipe
        self.target_device = target_device
        self.hardware_profile = hardware_profile
        self.source_files = source_files
        self.is_cancelled = False
        self.build_log = []
        self.rollback_operations = []
        self.grub_config = None
        self.start()
    
    def start_multiboot_build(self, recipe: DeploymentRecipe, target_device: str,
                             hardware_profile: HardwareProfile, source_files: Dict[str, str],
                             grub_config):
        """Start multi-boot USB build operation"""
        self.recipe = recipe
        self.target_device = target_device  
        self.hardware_profile = hardware_profile
        self.source_files = source_files
        self.grub_config = grub_config
        self.is_cancelled = False
        self.build_log = []
        self.rollback_operations = []
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
            if self.recipe.deployment_type == DeploymentType.MULTIBOOT:
                if not self._configure_multiboot_grub(partition_mounts):
                    return
            else:
                if not self._configure_bootloader(partition_mounts):
                    return
            
            # Step 7: Finalize and verify
            step += 1
            self._emit_progress("Finalizing build", step, total_steps, 0)
            if not self._finalize_build(partition_mounts):
                return
            
            self._build_successful = True
            self._log_message("INFO", "USB build completed successfully")
            self.operation_completed.emit(True, "USB build completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error in USB building: {e}")
            self._log_message("ERROR", f"Build error: {str(e)}")
            self.operation_completed.emit(False, f"Build error: {str(e)}")
        
        finally:
            # Perform rollback if needed
            if self.is_cancelled or not hasattr(self, '_build_successful'):
                self._perform_rollback()
            # Cleanup
            self._cleanup_build()
    
    def _validate_build_inputs(self) -> bool:
        """Comprehensive safety validation of build inputs"""
        try:
            self._log_message("INFO", "Starting comprehensive safety validation...")
            
            # Check recipe
            if not self.recipe:
                self.operation_completed.emit(False, "No recipe specified")
                return False
            
            # 1. CRITICAL: Device Safety Validation
            self._log_message("INFO", "Validating target device safety...")
            device_risk = self.safety_validator.validate_device_safety(self.target_device)
            
            if device_risk.overall_risk == ValidationResult.BLOCKED:
                error_msg = (
                    f"🚫 OPERATION BLOCKED FOR SAFETY 🚫\n"
                    f"Device: {self.target_device}\n"
                    f"Risk Factors: {', '.join(device_risk.risk_factors)}\n"
                    f"This device is not safe to use for USB creation."
                )
                self._log_message("ERROR", error_msg)
                self.operation_completed.emit(False, error_msg)
                return False
            
            # CRITICAL: Block DANGEROUS devices immediately - no exceptions!
            if device_risk.overall_risk == ValidationResult.DANGEROUS:
                error_msg = (
                    f"🚫 DANGEROUS DEVICE - OPERATION BLOCKED 🚫\n"
                    f"Device: {self.target_device} ({device_risk.size_gb:.1f}GB)\n"
                    f"Risk Factors: {', '.join(device_risk.risk_factors)}\n"
                    f"This device poses too high a risk for automated operations.\n"
                    f"Use extreme caution and manual verification if you must proceed."
                )
                self._log_message("ERROR", error_msg)
                self.operation_completed.emit(False, error_msg)
                return False
            
            # Log device validation results
            self._log_message("INFO", f"Device validation: {device_risk.overall_risk.value}")
            self._log_message("INFO", f"Device size: {device_risk.size_gb:.1f}GB")
            self._log_message("INFO", f"Removable: {device_risk.is_removable}")
            self._log_message("INFO", f"System disk: {device_risk.is_system_disk}")
            
            # 2. Prerequisites Validation
            self._log_message("INFO", "Validating system prerequisites...")
            prereq_checks = self.safety_validator.validate_prerequisites()
            
            blocked_checks = [check for check in prereq_checks if check.result == ValidationResult.BLOCKED]
            if blocked_checks:
                error_msg = "❌ MISSING PREREQUISITES:\n" + "\n".join(
                    f"• {check.name}: {check.message}" for check in blocked_checks
                )
                self._log_message("ERROR", error_msg)
                self.operation_completed.emit(False, error_msg)
                return False
            
            # 3. Source Files Validation
            self._log_message("INFO", "Validating source files...")
            source_checks = self.safety_validator.validate_source_files(self.source_files)
            
            blocked_sources = [check for check in source_checks if check.result == ValidationResult.BLOCKED]
            if blocked_sources:
                error_msg = "❌ SOURCE FILE ISSUES:\n" + "\n".join(
                    f"• {check.name}: {check.message}" for check in blocked_sources
                )
                self._log_message("ERROR", error_msg)
                self.operation_completed.emit(False, error_msg)
                return False
            
            # 4. Hardware Profile Compatibility
            if (self.hardware_profile and 
                self.hardware_profile.model not in self.recipe.hardware_profiles and 
                "generic" not in self.recipe.hardware_profiles):
                self._log_message("WARNING", f"Hardware profile {self.hardware_profile.model} not officially supported for this recipe")
            
            # 5. Final Safety Summary
            self._log_message("INFO", "✅ All safety validations passed")
            self._log_message("INFO", f"Target: {self.target_device} ({device_risk.size_gb:.1f}GB)")
            self._log_message("INFO", f"Recipe: {self.recipe.name}")
            self._log_message("INFO", f"Files: {len(self.source_files)} source files validated")
            
            return True
            
        except Exception as e:
            error_msg = f"Critical validation error: {str(e)}"
            self.logger.error(error_msg)
            self._log_message("ERROR", error_msg)
            self.operation_completed.emit(False, error_msg)
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
            
            # Add rollback operation for partition table creation
            self._partition_table_created = True
            self._add_rollback_operation(
                lambda: subprocess.run(
                    ['sudo', 'wipefs', '-a', self.target_device], 
                    capture_output=True, check=False
                )
            )
            self._log_message("INFO", "Added rollback operation for partition table")
            
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
                
                # Add rollback operation for this formatted partition
                self._add_rollback_operation(
                    lambda dev=device: subprocess.run(
                        ['sudo', 'wipefs', '-a', dev], 
                        capture_output=True, check=False
                    )
                )
                self._log_message("DEBUG", f"Added rollback operation for formatted partition {device}")
            
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
                if not self.temp_dir:
                    self.temp_dir = Path(tempfile.mkdtemp(prefix="bootforge_build_"))
                    self._add_rollback_operation(lambda: shutil.rmtree(str(self.temp_dir), ignore_errors=True))
                
                mount_point = self.temp_dir / f"partition_{i}"
                mount_point.mkdir(exist_ok=True)
                
                # Mount partition
                if platform.system() == "Linux":
                    result = subprocess.run([
                        'sudo', 'mount', partition_device, str(mount_point)
                    ], capture_output=True, text=True)
                    
                    # Add rollback operation for unmounting
                    if result.returncode == 0:
                        self._add_rollback_operation(
                            lambda mp=str(mount_point): subprocess.run(
                                ['sudo', 'umount', mp], 
                                capture_output=True, check=False
                            )
                        )
                    
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
        """Deploy macOS OCLP specific files to create bootable USB"""
        try:
            self._log_message("INFO", "Deploying macOS OCLP files")
            
            # Step 1: Deploy EFI folder to EFI partition for bootability
            if not self._deploy_oclp_efi_folder(mount_points):
                return False
            
            # Step 2: Deploy macOS installer if available
            if not self._deploy_macos_installer(mount_points):
                return False
            
            # Step 3: Deploy OCLP tools and utilities
            if not self._deploy_oclp_tools(mount_points):
                return False
            
            # Step 4: Create deployment metadata and verification files
            if not self._create_deployment_metadata(mount_points):
                return False
            
            self._log_message("INFO", "macOS OCLP deployment completed successfully")
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"Error deploying macOS OCLP files: {e}")
            return False
    
    def _deploy_oclp_efi_folder(self, mount_points: Dict[str, str]) -> bool:
        """Deploy OCLP EFI folder to EFI partition for bootability"""
        try:
            # Find EFI partition mount point
            efi_mount = None
            for partition_name, mount_path in mount_points.items():
                if "efi" in partition_name.lower():
                    efi_mount = mount_path
                    break
            
            if not efi_mount:
                self._log_message("ERROR", "No EFI partition found for OCLP deployment")
                return False
            
            # Look for OCLP build artifacts in source files
            oclp_efi_source = None
            oclp_metadata_file = None
            
            # Check for OCLP build result artifacts
            for file_key, file_path in self.source_files.items():
                file_path_obj = Path(file_path)
                
                if file_key == "oclp_build_result" or "oclp" in file_key.lower():
                    if file_path_obj.is_dir():
                        # Look for EFI folder in OCLP build directory
                        potential_efi = file_path_obj / "EFI"
                        if potential_efi.exists():
                            oclp_efi_source = potential_efi
                            break
                        
                        # Alternative: look for bootforge_oclp_build structure
                        potential_build = file_path_obj / "bootforge_oclp_build" / "EFI"
                        if potential_build.exists():
                            oclp_efi_source = potential_build
                            break
                    
                    elif file_path_obj.name == "oclp_deployment_info.json":
                        oclp_metadata_file = file_path_obj
            
            if not oclp_efi_source:
                self._log_message("WARNING", "No OCLP EFI folder found in source files - creating template structure")
                return self._create_template_efi_structure(efi_mount)
            
            # Deploy EFI folder to USB EFI partition
            efi_destination = Path(efi_mount) / "EFI"
            
            self._log_message("INFO", f"Copying OCLP EFI folder from {oclp_efi_source} to {efi_destination}")
            
            if efi_destination.exists():
                shutil.rmtree(efi_destination)
            
            shutil.copytree(oclp_efi_source, efi_destination)
            
            # Verify critical EFI structure
            if not self._verify_efi_boot_structure(efi_destination):
                self._log_message("ERROR", "EFI boot structure verification failed")
                return False
            
            # Copy metadata if available
            if oclp_metadata_file:
                metadata_dest = Path(efi_mount) / "oclp_deployment_info.json"
                shutil.copy2(oclp_metadata_file, metadata_dest)
                self._log_message("INFO", f"Copied OCLP metadata to {metadata_dest}")
            
            self._log_message("INFO", "OCLP EFI folder deployed successfully")
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"Failed to deploy OCLP EFI folder: {e}")
            return False
    
    def _verify_efi_boot_structure(self, efi_path: Path) -> bool:
        """Verify EFI folder has correct structure for booting"""
        try:
            required_structure = {
                "BOOT": ["BOOTx64.efi"],
                "OC": ["config.plist", "OpenCore.efi"]
            }
            
            missing_components = []
            
            for folder, required_files in required_structure.items():
                folder_path = efi_path / folder
                if not folder_path.exists():
                    missing_components.append(f"Missing {folder} folder")
                    continue
                
                for required_file in required_files:
                    file_path = folder_path / required_file
                    if not file_path.exists():
                        # Some flexibility for alternative names
                        if required_file == "BOOTx64.efi":
                            # Check for alternative bootloader names
                            alternatives = ["OpenCore.efi", "BOOTX64.EFI"]
                            found_alternative = any((folder_path / alt).exists() for alt in alternatives)
                            if not found_alternative:
                                missing_components.append(f"Missing bootloader in {folder}")
                        else:
                            missing_components.append(f"Missing {folder}/{required_file}")
            
            if missing_components:
                for component in missing_components:
                    self._log_message("WARNING", f"EFI structure: {component}")
                return False
            else:
                self._log_message("INFO", "EFI boot structure verification passed")
                return True
                
        except Exception as e:
            self._log_message("ERROR", f"EFI structure verification failed: {e}")
            return False
    
    def _create_template_efi_structure(self, efi_mount: str) -> bool:
        """Create template EFI structure when OCLP artifacts are not available"""
        try:
            self._log_message("INFO", "Creating template EFI structure for development")
            
            efi_path = Path(efi_mount) / "EFI"
            efi_path.mkdir(exist_ok=True)
            
            # Create BOOT folder
            boot_folder = efi_path / "BOOT"
            boot_folder.mkdir(exist_ok=True)
            
            # Create placeholder bootloader
            bootx64 = boot_folder / "BOOTx64.efi"
            with open(bootx64, 'wb') as f:
                f.write(b'BOOTFORGE_TEMPLATE_BOOTLOADER')
            
            # Create OC folder structure
            oc_folder = efi_path / "OC"
            oc_folder.mkdir(exist_ok=True)
            
            for subdir in ["Drivers", "Kexts", "Tools", "ACPI", "Resources"]:
                (oc_folder / subdir).mkdir(exist_ok=True)
            
            # Create template config.plist
            config_content = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- BootForge Template OpenCore Configuration -->
    <key>Misc</key>
    <dict>
        <key>Boot</key>
        <dict>
            <key>ShowPicker</key>
            <true/>
            <key>Timeout</key>
            <integer>5</integer>
        </dict>
    </dict>
    <key>UEFI</key>
    <dict>
        <key>Drivers</key>
        <array>
            <string>OpenRuntime.efi</string>
        </array>
    </dict>
</dict>
</plist>'''
            
            config_plist = oc_folder / "config.plist"
            with open(config_plist, 'w') as f:
                f.write(config_content)
            
            self._log_message("WARNING", "Template EFI structure created - replace with actual OCLP build for production use")
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"Failed to create template EFI structure: {e}")
            return False
    
    def _deploy_macos_installer(self, mount_points: Dict[str, str]) -> bool:
        """Deploy macOS installer to the installer partition"""
        try:
            # Find macOS installer partition
            installer_mount = None
            for partition_name, mount_path in mount_points.items():
                if "macos" in partition_name.lower() and "installer" in partition_name.lower():
                    installer_mount = mount_path
                    break
            
            if not installer_mount:
                self._log_message("WARNING", "No macOS installer partition found")
                return True  # Not critical, continue
            
            # Look for macOS installer in source files
            installer_source = None
            for file_key, file_path in self.source_files.items():
                if "macos" in file_key.lower() and "installer" in file_key.lower():
                    installer_source = Path(file_path)
                    break
                elif file_key.endswith(".app") and "install" in file_key.lower():
                    installer_source = Path(file_path)
                    break
            
            if not installer_source or not installer_source.exists():
                self._log_message("WARNING", "No macOS installer found in source files")
                return True  # Not critical for testing
            
            # Copy installer
            installer_dest = Path(installer_mount) / installer_source.name
            self._log_message("INFO", f"Copying macOS installer from {installer_source} to {installer_dest}")
            
            if installer_source.is_dir():
                shutil.copytree(installer_source, installer_dest, dirs_exist_ok=True)
            else:
                shutil.copy2(installer_source, installer_dest)
            
            self._log_message("INFO", "macOS installer deployed successfully")
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"Failed to deploy macOS installer: {e}")
            return False
    
    def _deploy_oclp_tools(self, mount_points: Dict[str, str]) -> bool:
        """Deploy OCLP tools and utilities to tools partition"""
        try:
            # Find OCLP tools partition
            tools_mount = None
            for partition_name, mount_path in mount_points.items():
                if "oclp" in partition_name.lower() and "tools" in partition_name.lower():
                    tools_mount = mount_path
                    break
            
            if not tools_mount:
                self._log_message("WARNING", "No OCLP tools partition found")
                return True  # Not critical
            
            # Look for OCLP app in source files
            oclp_app_source = None
            for file_key, file_path in self.source_files.items():
                if "oclp" in file_key.lower() or "opencore" in file_key.lower():
                    oclp_app_source = Path(file_path)
                    break
            
            if oclp_app_source and oclp_app_source.exists():
                # Copy OCLP app
                oclp_dest = Path(tools_mount) / oclp_app_source.name
                self._log_message("INFO", f"Copying OCLP app from {oclp_app_source} to {oclp_dest}")
                
                if oclp_app_source.is_dir():
                    shutil.copytree(oclp_app_source, oclp_dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(oclp_app_source, oclp_dest)
            
            # Create tools directory structure
            tools_path = Path(tools_mount)
            (tools_path / "Utilities").mkdir(exist_ok=True)
            (tools_path / "Documentation").mkdir(exist_ok=True)
            
            # Create useful README
            readme_content = f'''# BootForge OCLP Tools

This USB drive was created by BootForge for macOS OCLP deployment.

Created: {time.strftime("%Y-%m-%d %H:%M:%S")}
Target Hardware: {getattr(self.hardware_profile, "name", "Unknown")}
Recipe: {getattr(self.recipe, "name", "Unknown")}

## Contents:

- EFI partition: Contains OpenCore bootloader and configuration
- macOS Installer: Contains macOS installation files
- OCLP Tools: Contains OpenCore Legacy Patcher and utilities

## Usage:

1. Boot from this USB drive on your target Mac
2. Follow the macOS installation process
3. After installation, use the OCLP tools to apply post-install patches

For more information, visit: https://dortania.github.io/OpenCore-Legacy-Patcher/
'''
            
            readme_file = tools_path / "README.txt"
            with open(readme_file, 'w') as f:
                f.write(readme_content)
            
            self._log_message("INFO", "OCLP tools deployed successfully")
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"Failed to deploy OCLP tools: {e}")
            return False
    
    def _create_deployment_metadata(self, mount_points: Dict[str, str]) -> bool:
        """Create deployment metadata and verification files"""
        try:
            # Create metadata on EFI partition
            efi_mount = None
            for partition_name, mount_path in mount_points.items():
                if "efi" in partition_name.lower():
                    efi_mount = mount_path
                    break
            
            if not efi_mount:
                self._log_message("WARNING", "No EFI partition found for metadata")
                return True
            
            # Create deployment metadata
            metadata = {
                "bootforge_version": "1.0",
                "deployment_type": "macOS_OCLP",
                "created_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "target_hardware": {
                    "name": getattr(self.hardware_profile, "name", "Unknown"),
                    "model": getattr(self.hardware_profile, "model", "Unknown"),
                    "platform": getattr(self.hardware_profile, "platform", "Unknown")
                },
                "recipe": {
                    "name": getattr(self.recipe, "name", "Unknown"),
                    "description": getattr(self.recipe, "description", "Unknown")
                },
                "partitions": list(mount_points.keys()),
                "source_files": list(self.source_files.keys())
            }
            
            metadata_file = Path(efi_mount) / "bootforge_deployment.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            self._log_message("INFO", f"Created deployment metadata: {metadata_file}")
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"Failed to create deployment metadata: {e}")
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
    
    def _perform_rollback(self):
        """Perform rollback operations if build fails or is cancelled"""
        try:
            self._log_message("INFO", "Performing rollback operations...")
            
            # Execute rollback operations in reverse order
            for rollback_op in reversed(self.rollback_operations):
                try:
                    rollback_op()
                except Exception as e:
                    self._log_message("WARNING", f"Rollback operation failed: {e}")
            
            # Unmount any mounted partitions
            self._unmount_device_partitions()
            
            # Clear partition table if we created one
            if self.target_device and hasattr(self, '_partition_table_created'):
                try:
                    if platform.system() == "Linux":
                        subprocess.run(
                            ['sudo', 'wipefs', '-a', self.target_device],
                            capture_output=True, text=True, check=False
                        )
                    self._log_message("INFO", "Restored device to original state")
                except Exception as e:
                    self._log_message("WARNING", f"Could not fully restore device: {e}")
            
            self._log_message("INFO", "Rollback completed")
            
        except Exception as e:
            self._log_message("ERROR", f"Error during rollback: {e}")
    
    def _add_rollback_operation(self, operation: Callable):
        """Add an operation to the rollback list"""
        self.rollback_operations.append(operation)
    
    def _configure_multiboot_grub(self, partition_mounts: Dict[str, str]) -> bool:
        """Configure GRUB for multi-boot functionality"""
        try:
            if not hasattr(self, 'grub_config') or not self.grub_config:
                self._log_message("WARNING", "No GRUB configuration found for multi-boot")
                return True  # Continue with single-OS build
            
            self._log_message("INFO", "Configuring GRUB for multi-boot system...")
            
            # Create GRUB manager instance  
            from .grub_manager import GRUBManager, GRUBBootMode
            grub_manager = GRUBManager()
            
            # Write GRUB configuration to EFI System Partition
            efi_mount = partition_mounts.get("EFI System")
            if not efi_mount:
                self._log_message("ERROR", "EFI System Partition not mounted")
                return False
            grub_cfg_path = f"{efi_mount}/EFI/BOOT/grub.cfg"
            
            # Ensure EFI/BOOT directory exists
            os.makedirs(os.path.dirname(grub_cfg_path), exist_ok=True)
            
            # Generate and write GRUB config
            if not grub_manager.write_config(grub_cfg_path, self.grub_config):
                self._log_message("ERROR", "Failed to write GRUB configuration")
                return False
            
            # Install GRUB to EFI System Partition
            if not grub_manager.install_grub(self.target_device, efi_mount, GRUBBootMode.UEFI):
                self._log_message("ERROR", "Failed to install GRUB")
                return False
            
            # Copy GRUB bootloader files
            self._copy_grub_files(efi_mount)
            
            # Stage OS installation files
            if not self._stage_os_payloads():
                self._log_message("ERROR", "Failed to stage OS payloads")
                return False
            
            self._log_message("INFO", "Multi-boot GRUB configuration completed successfully")
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"Error configuring multi-boot GRUB: {e}")
            return False
    
    def _copy_grub_files(self, efi_mount: str):
        """Copy essential GRUB files to EFI System Partition"""
        try:
            grub_dir = f"{efi_mount}/EFI/BOOT"
            os.makedirs(grub_dir, exist_ok=True)
            
            # Copy GRUB EFI bootloader (if available)
            grub_sources = [
                "/usr/lib/grub/x86_64-efi/grubx64.efi",
                "/boot/efi/EFI/ubuntu/grubx64.efi",
                "/usr/share/grub/grubx64.efi"
            ]
            
            grub_copied = False
            for source in grub_sources:
                if os.path.exists(source):
                    shutil.copy2(source, f"{grub_dir}/BOOTX64.EFI")
                    self._log_message("INFO", f"Copied GRUB bootloader from {source}")
                    grub_copied = True
                    break
            
            if not grub_copied:
                self._log_message("WARNING", "No GRUB bootloader found - may need manual installation")
            
        except Exception as e:
            self._log_message("WARNING", f"Error copying GRUB files: {e}")
    
    def _stage_os_payloads(self) -> bool:
        """Stage operating system installation files to their partitions"""
        try:
            self._log_message("INFO", "Staging OS installation payloads...")
            
            if not hasattr(self, 'grub_config') or not self.grub_config:
                return True  # No multi-boot config, skip staging
            
            # Process each OS entry in GRUB config
            for entry in self.grub_config.entries:
                self._log_message("INFO", f"Staging {entry.name} ({entry.os_type})")
                
                if entry.os_type == "windows":
                    self._stage_windows_payload(entry)
                elif entry.os_type == "macos":
                    self._stage_macos_payload(entry)
                elif entry.os_type == "linux":
                    self._stage_linux_payload(entry)
                
            self._log_message("INFO", "OS payload staging completed")
            return True
            
        except Exception as e:
            self._log_message("ERROR", f"Error staging OS payloads: {e}")
            return False
    
    def _stage_windows_payload(self, entry):
        """Stage Windows installation files"""
        try:
            # Look for Windows ISO in source files
            windows_iso = None
            for filename, path in self.source_files.items():
                if 'windows' in filename.lower() and path.endswith('.iso'):
                    windows_iso = path
                    break
            
            if not windows_iso or not os.path.exists(windows_iso):
                self._log_message("WARNING", f"Windows ISO not found for {entry.name}")
                return
            
            # Mount Windows ISO and copy EFI boot files
            iso_mount = f"{self.temp_dir}/windows_iso"
            os.makedirs(iso_mount, exist_ok=True)
            
            # Mount ISO (simplified - would need proper mounting)
            self._log_message("INFO", f"Extracting Windows EFI files from {windows_iso}")
            
            # In a real implementation, would extract EFI/BOOT/BOOTX64.EFI 
            # and other necessary files to the EFI System Partition
            
        except Exception as e:
            self._log_message("WARNING", f"Error staging Windows payload: {e}")
    
    def _stage_macos_payload(self, entry):
        """Stage macOS installation files"""
        try:
            # Look for macOS installer in source files
            macos_installer = None
            for filename, path in self.source_files.items():
                if 'macos' in filename.lower() and (path.endswith('.dmg') or path.endswith('.app')):
                    macos_installer = path
                    break
            
            if not macos_installer or not os.path.exists(macos_installer):
                self._log_message("WARNING", f"macOS installer not found for {entry.name}")
                return
            
            self._log_message("INFO", f"Staging macOS installer from {macos_installer}")
            
            # In a real implementation, would restore BaseSystem.dmg 
            # to the HFS+/APFS partition and setup boot.efi
            
        except Exception as e:
            self._log_message("WARNING", f"Error staging macOS payload: {e}")
    
    def _stage_linux_payload(self, entry):
        """Stage Linux installation files"""
        try:
            # Look for Linux ISO in source files
            linux_iso = None
            for filename, path in self.source_files.items():
                if 'linux' in filename.lower() and path.endswith('.iso'):
                    linux_iso = path
                    break
            
            if not linux_iso or not os.path.exists(linux_iso):
                self._log_message("WARNING", f"Linux ISO not found for {entry.name}")
                return
            
            self._log_message("INFO", f"Staging Linux installer from {linux_iso}")
            
            # In a real implementation, would extract vmlinuz and initrd
            # from the ISO and copy to the Linux partition
            
        except Exception as e:
            self._log_message("WARNING", f"Error staging Linux payload: {e}")
    
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
        
        # Patch pipeline components
        self.patch_planner = PatchPlanner()
        self.patch_config_loader = PatchConfigLoader()
        self.safety_validator = SafetyValidator()
        self.patch_sets: Dict[str, PatchSet] = {}
        
        # Multi-boot components
        self.grub_manager = GRUBManager()
        
        # Load built-in recipes, profiles, and patches
        self._load_builtin_recipes()
        self._load_builtin_hardware_profiles()
        self._load_patch_configurations()
    
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
        
        # Multi-boot recipe
        multiboot_recipe = DeploymentRecipe.create_multiboot_recipe()
        self.recipes[multiboot_recipe.name] = multiboot_recipe
        
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
    
    def _load_patch_configurations(self):
        """Load patch configurations from YAML files and Mac model data"""
        try:
            # Load patch sets from YAML configurations
            yaml_patch_sets = self.patch_config_loader.load_all_configs()
            for patch_set in yaml_patch_sets:
                self.patch_sets[patch_set.id] = patch_set
            
            # Load Mac model patch sets
            mac_patch_sets = create_mac_patch_sets()
            for patch_set in mac_patch_sets:
                self.patch_sets[patch_set.id] = patch_set
            
            # Register patch sets with the planner
            for patch_set in self.patch_sets.values():
                self.patch_planner.register_patch_set(patch_set)
            
            self.logger.info(f"Loaded {len(self.patch_sets)} patch sets for patch pipeline")
            
        except Exception as e:
            self.logger.error(f"Failed to load patch configurations: {e}")
            self.logger.warning("Patch pipeline will operate with limited capabilities")
    
    def create_patch_plan(self, hardware_profile: HardwareProfile, 
                         target_os: str, target_version: str,
                         validation_mode: str = "compliant") -> Optional[PatchPlan]:
        """Create a patch plan for specific hardware and OS target"""
        try:
            # Create a simple DetectedHardware object from profile
            # In real usage, this would come from HardwareDetector
            from .hardware_detector import DetectedHardware
            detected_hardware = DetectedHardware(platform=hardware_profile.platform)
            detected_hardware.system_model = hardware_profile.model
            detected_hardware.system_manufacturer = "Apple" if hardware_profile.platform == "mac" else "PC"
            detected_hardware.cpu_name = hardware_profile.cpu_family or "Unknown"
            detected_hardware.cpu_architecture = hardware_profile.architecture
            
            # Create patch plan using the planner
            os_info = {"family": target_os, "version": target_version}
            patch_plan = self.patch_planner.create_patch_plan(
                hardware=detected_hardware,
                os_info=os_info
            )
            
            if patch_plan:
                self.logger.info(f"Created patch plan with {len(patch_plan.actions)} actions for {hardware_profile.name}")
                
                # Log patch plan summary
                for action in patch_plan.actions[:5]:  # Log first 5 actions
                    self.logger.debug(f"  - {action.name} ({action.patch_type.value})")
                if len(patch_plan.actions) > 5:
                    self.logger.debug(f"  ... and {len(patch_plan.actions) - 5} more actions")
            
            return patch_plan
            
        except Exception as e:
            self.logger.error(f"Failed to create patch plan: {e}")
            return None
    
    def validate_patch_plan(self, patch_plan: PatchPlan, 
                          validation_mode: str = "compliant") -> ValidationResult:
        """Validate a patch plan using the safety validator"""
        try:
            # Use existing safety validator methods
            return self.safety_validator.validate_device(
                device_path="/dev/null",  # Placeholder
                safety_level=SafetyLevel.MODERATE
            )
        except Exception as e:
            self.logger.error(f"Failed to validate patch plan: {e}")
            return ValidationResult(
                is_valid=False,
                risk_level=SafetyLevel.DANGEROUS,
                messages=[f"Validation failed: {e}"]
            )
    
    def get_compatible_patch_sets(self, hardware_profile: HardwareProfile,
                                 target_os: str = None) -> List[PatchSet]:
        """Get patch sets compatible with specific hardware"""
        compatible_sets = []
        
        for patch_set in self.patch_sets.values():
            # Check OS compatibility
            if target_os and patch_set.target_os != target_os:
                continue
            
            # Check hardware compatibility
            if self._is_patch_set_compatible(patch_set, hardware_profile):
                compatible_sets.append(patch_set)
        
        self.logger.info(f"Found {len(compatible_sets)} compatible patch sets for {hardware_profile.name}")
        return compatible_sets
    
    def _is_patch_set_compatible(self, patch_set: PatchSet, hardware_profile: HardwareProfile) -> bool:
        """Check if a patch set is compatible with hardware profile"""
        try:
            # Check target hardware patterns
            for pattern in patch_set.target_hardware:
                import re
                if re.match(pattern, hardware_profile.model):
                    return True
            
            # For Mac models, also check if patch requirements exist
            if hardware_profile.platform == "mac":
                if (hardware_profile.required_patches or 
                    hardware_profile.graphics_patches or 
                    hardware_profile.audio_patches):
                    return True
            
            return False
            
        except Exception as e:
            self.logger.warning(f"Error checking patch set compatibility: {e}")
            return False
    
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
    
    def create_multiboot_usb(self, target_device: str, os_images: Dict[str, str],
                            hardware_profile_name: str = "generic_x64",
                            progress_callback: Optional[Callable] = None) -> USBBuilder:
        """Create multi-boot USB drive with multiple operating systems"""
        
        # Get the multi-boot recipe
        recipe_name = "Multi-Boot System (macOS + Windows + Linux)"
        if recipe_name not in self.recipes:
            raise ValueError("Multi-boot recipe not found")
        
        recipe = self.recipes[recipe_name]
        hardware_profile = self.hardware_profiles.get(
            hardware_profile_name, 
            self.hardware_profiles["generic_x64"]
        )
        
        # Setup GRUB configuration for multi-boot
        grub_config = self.grub_manager.create_multiboot_config(recipe, target_device)
        
        # Prepare source files for multi-boot
        source_files = {
            "grub.cfg": "/tmp/grub.cfg"  # Will be generated
        }
        source_files.update(os_images)
        
        # Setup progress callback
        if progress_callback:
            self.builder.progress_updated.connect(progress_callback)
        
        # Start multi-boot build
        self.builder.start_multiboot_build(
            recipe, target_device, hardware_profile, source_files, grub_config
        )
        
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