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
    MULTIBOOT = "multiboot"  # Multi-boot system with GRUB


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
    
    @classmethod
    def from_mac_model(cls, model: str) -> 'HardwareProfile':
        """Create hardware profile from Mac model identifier using comprehensive database"""
        # Import here to avoid circular imports
        from .hardware_profiles import get_mac_model_data
        
        mac_models = get_mac_model_data()
        
        if model in mac_models:
            model_data = mac_models[model]
            return cls(
                name=model_data["name"],
                platform="mac",
                model=model,
                architecture=model_data["architecture"],
                year=model_data.get("year"),
                cpu_family=model_data.get("cpu_family"),
                oclp_compatibility=model_data.get("oclp_compatibility"),
                native_macos_support=model_data.get("native_macos_support", {}),
                required_patches=model_data.get("required_patches", {}),
                optional_patches=model_data.get("optional_patches", {}),
                graphics_patches=model_data.get("graphics_patches", []),
                audio_patches=model_data.get("audio_patches", []),
                wifi_bluetooth_patches=model_data.get("wifi_bluetooth_patches", []),
                usb_patches=model_data.get("usb_patches", []),
                secure_boot_model=model_data.get("secure_boot_model"),
                sip_requirements=model_data.get("sip_requirements"),
                notes=model_data.get("notes", [])
            )
        else:
            # Fallback for unknown models
            return cls(
                name=f"Unknown Mac ({model})",
                platform="mac",
                model=model,
                architecture="x86_64",  # Default assumption
                oclp_compatibility="unknown",
                notes=[f"Unknown Mac model: {model}"]
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
            hardware_profiles=["generic_x64", "thinkpad_x1", "dell_precision"],
            required_files=["linux.iso", "preseed.cfg"],
            optional_files=["driver_pack.tar.gz", "postinstall.sh"]
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
    
    @classmethod
    def create_multiboot_recipe(cls) -> 'DeploymentRecipe':
        """Create multi-boot deployment recipe with GRUB bootloader"""
        return cls(
            name="Multi-Boot System (macOS + Windows + Linux)",
            description="Create multi-boot USB with GRUB bootloader supporting macOS, Windows, and Linux",
            deployment_type=DeploymentType.MULTIBOOT,
            partition_scheme=PartitionScheme.GPT,
            partitions=[
                PartitionInfo("EFI System", 512, FileSystem.FAT32, bootable=True, label="EFI"),
                PartitionInfo("BIOS Boot", 2, None, label="BIOSBOOT"),  # EF02 for legacy BIOS (unformatted)
                PartitionInfo("macOS Installer", 8192, FileSystem.HFS_PLUS, label="macOS"),
                PartitionInfo("Windows Installer", 8192, FileSystem.NTFS, label="Windows"),
                PartitionInfo("Linux Installer", 4096, FileSystem.EXT4, label="Linux"),
                PartitionInfo("Shared Data", -1, FileSystem.EXFAT, label="Data")
            ],
            hardware_profiles=["generic_x64", "iMacPro1,1", "MacBookPro15,1", "dell_optiplex"],
            required_files=["grub.cfg"],
            optional_files=[
                "macos_installer.dmg", "macos_recovery.dmg", 
                "windows.iso", "autounattend.xml",
                "linux.iso", "preseed.cfg",
                "opencore-legacy-patcher.zip"
            ],
            verification_steps=[
                "verify_grub_installation",
                "verify_efi_boot_entries", 
                "verify_os_boot_menu",
                "test_multiboot_functionality"
            ],
            metadata={
                "supports_uefi": True,
                "supports_legacy_bios": True,
                "bootloader": "grub2",
                "max_os_count": 10,
                "supports_os_detection": True,
                "grub_modules": ["part_gpt", "part_msdos", "fat", "ext2", "ntfs", "hfsplus", "apfs", "iso9660", "configfile", "normal", "search", "search_fs_uuid", "probe"]
            }
        )