"""
BootForge Core Data Models
Shared data classes and enums used across the BootForge system
Separated to prevent circular imports between modules
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


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
    
    # Enhanced Mac-specific fields
    oclp_compatibility: Optional[str] = None  # "fully_supported", "partially_supported", "experimental", "unsupported"
    native_macos_support: Dict[str, bool] = field(default_factory=dict)  # macOS versions natively supported
    required_patches: Dict[str, List[str]] = field(default_factory=dict)  # macOS version -> required patches
    optional_patches: Dict[str, List[str]] = field(default_factory=dict)  # macOS version -> optional patches
    graphics_patches: List[str] = field(default_factory=list)  # Graphics-specific patches needed
    audio_patches: List[str] = field(default_factory=list)  # Audio patches needed
    wifi_bluetooth_patches: List[str] = field(default_factory=list)  # WiFi/Bluetooth patches
    usb_patches: List[str] = field(default_factory=list)  # USB patches needed
    secure_boot_model: Optional[str] = None  # SecureBootModel for OCLP
    sip_requirements: Optional[str] = None  # "enabled", "disabled", "partial"
    notes: List[str] = field(default_factory=list)  # Additional notes for this model
    
    # Patch pipeline integration fields (using TYPE_CHECKING to avoid imports)
    patch_compatibility: Optional[Any] = None  # PatchCompatibility from vendor_database
    supported_os_versions: List[str] = field(default_factory=list)  # OS versions this profile supports
    deployment_type: Optional[str] = None  # Type of deployment this profile uses


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
            hardware_profiles=["generic_x64", "thinkpad_x1", "dell_precision"],
            required_files=["linux.iso", "preseed.cfg"],
            optional_files=["driver_pack.tar.gz", "postinstall.sh"]
        )