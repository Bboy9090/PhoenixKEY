"""
BootForge Vendor/Device ID Database
Comprehensive hardware identification database for mapping device IDs to vendor names and models
Enhanced with patch capability flags for hardware-specific OS modifications
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum


class PatchCapability(Enum):
    """Hardware patch capabilities"""
    DRIVER_INJECTION = "driver_injection"        # Supports driver injection
    KERNEL_PATCHING = "kernel_patching"          # Supports kernel patches
    EFI_MODIFICATION = "efi_modification"        # Supports EFI/bootloader mods
    FIRMWARE_UPDATE = "firmware_update"          # Supports firmware updates
    KEXT_LOADING = "kext_loading"                # Supports macOS kernel extensions
    REGISTRY_PATCHING = "registry_patching"      # Supports Windows registry mods
    SECURE_BOOT_BYPASS = "secure_boot_bypass"    # Can bypass secure boot
    SIGNATURE_BYPASS = "signature_bypass"        # Can bypass code signing
    CUSTOM_SCRIPTS = "custom_scripts"            # Supports custom scripts


class SecurityLevel(Enum):
    """Hardware security levels"""
    OPEN = "open"                    # No restrictions, full patch support
    MODERATE = "moderate"            # Some restrictions, requires validation
    STRICT = "strict"                # High restrictions, limited patching
    LOCKED = "locked"                # Highly restricted, minimal patching


@dataclass
class PatchCompatibility:
    """Patch compatibility information for hardware"""
    supported_capabilities: Set[PatchCapability] = field(default_factory=set)
    security_level: SecurityLevel = SecurityLevel.MODERATE
    
    # OS-specific compatibility
    macos_support: Dict[str, List[str]] = field(default_factory=dict)  # version -> supported features
    windows_support: Dict[str, List[str]] = field(default_factory=dict)
    linux_support: Dict[str, List[str]] = field(default_factory=dict)
    
    # Restrictions and requirements
    requires_signed_drivers: bool = True
    requires_secure_boot_off: bool = False
    requires_sip_disabled: bool = False         # macOS System Integrity Protection
    requires_test_signing: bool = False         # Windows test signing mode
    
    # Known issues and limitations
    known_issues: List[str] = field(default_factory=list)
    workarounds: List[str] = field(default_factory=list)
    tested_versions: List[str] = field(default_factory=list)
    
    def supports_capability(self, capability: PatchCapability) -> bool:
        """Check if hardware supports a specific patch capability"""
        return capability in self.supported_capabilities
    
    def get_os_support(self, os_family: str, os_version: str) -> List[str]:
        """Get supported features for specific OS version"""
        os_support_map = {
            "macos": self.macos_support,
            "windows": self.windows_support,
            "linux": self.linux_support
        }
        
        support_dict = os_support_map.get(os_family.lower(), {})
        
        # Try exact version match first
        if os_version in support_dict:
            return support_dict[os_version]
        
        # Try pattern matching for version ranges
        for version_pattern, features in support_dict.items():
            if re.match(version_pattern, os_version):
                return features
        
        return []


@dataclass
class VendorInfo:
    """Enhanced vendor information structure with patch capabilities"""
    vendor_id: str
    name: str
    full_name: Optional[str] = None
    website: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    
    # Patch-related information
    patch_compatibility: Optional[PatchCompatibility] = None
    driver_support_url: Optional[str] = None
    patch_documentation: Optional[str] = None
    
    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []
        if self.patch_compatibility is None:
            self.patch_compatibility = PatchCompatibility()


@dataclass
class DeviceInfo:
    """Enhanced device information structure with patch capabilities"""
    vendor_id: str
    device_id: str
    name: str
    category: str
    subsystem_vendor: Optional[str] = None
    subsystem_device: Optional[str] = None
    
    # Patch-related information
    patch_compatibility: Optional[PatchCompatibility] = None
    driver_package: Optional[str] = None            # Driver package name/ID
    firmware_version: Optional[str] = None          # Current/required firmware version
    patch_notes: Optional[str] = None               # Special patching notes
    
    def __post_init__(self):
        if self.patch_compatibility is None:
            self.patch_compatibility = PatchCompatibility()


class VendorDatabase:
    """Hardware vendor and device identification database"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._vendors = {}
        self._devices = {}
        self._mac_models = {}
        self._cpu_patterns = {}
        self._gpu_vendors = {}
        
        # Initialize databases
        self._init_pci_vendors()
        self._init_pci_devices()
        self._init_mac_models()
        self._init_cpu_patterns()
        self._init_gpu_vendors()
        
        self.logger.info(f"Vendor database initialized with {len(self._vendors)} vendors, {len(self._devices)} devices")
    
    def _init_pci_vendors(self):
        """Initialize PCI vendor database with major vendors"""
        vendors = [
            # Major CPU/Chipset vendors
            ("8086", "Intel", "Intel Corporation", "https://intel.com", ["Intel Corp"]),
            ("1022", "AMD", "Advanced Micro Devices", "https://amd.com", ["AMD Inc", "AuthenticAMD"]),
            ("1002", "ATI", "ATI Technologies Inc", "https://ati.com", ["AMD/ATI"]),
            
            # GPU vendors
            ("10de", "NVIDIA", "NVIDIA Corporation", "https://nvidia.com", ["nVidia"]),
            ("1002", "AMD", "Advanced Micro Devices", "https://amd.com", ["ATI", "AMD/ATI"]),
            ("8086", "Intel", "Intel Corporation", "https://intel.com", ["Intel Graphics"]),
            
            # Network vendors
            ("8086", "Intel", "Intel Corporation", "https://intel.com", ["Intel Network"]),
            ("14e4", "Broadcom", "Broadcom Corporation", "https://broadcom.com", ["Broadcom Inc"]),
            ("10ec", "Realtek", "Realtek Semiconductor", "https://realtek.com", ["Realtek Inc"]),
            ("1969", "Atheros", "Atheros Communications", "https://qca.qualcomm.com", ["Qualcomm Atheros"]),
            ("168c", "Atheros", "Atheros Communications", "https://qca.qualcomm.com", ["QCA"]),
            
            # System vendors
            ("1028", "Dell", "Dell Inc.", "https://dell.com", ["Dell Computer"]),
            ("103c", "HP", "Hewlett-Packard Company", "https://hp.com", ["Hewlett Packard", "HPE"]),
            ("17aa", "Lenovo", "Lenovo Group Ltd.", "https://lenovo.com", ["IBM", "ThinkPad"]),
            ("1043", "ASUSTeK", "ASUSTeK Computer Inc.", "https://asus.com", ["ASUS"]),
            ("1462", "MSI", "Micro-Star International", "https://msi.com", ["MSI Computer"]),
            ("1458", "Gigabyte", "Gigabyte Technology", "https://gigabyte.com", ["GIGABYTE"]),
            ("1849", "ASRock", "ASRock Inc.", "https://asrock.com", []),
            
            # Storage vendors
            ("1179", "Toshiba", "Toshiba Corporation", "https://toshiba.com", []),
            ("144d", "Samsung", "Samsung Electronics", "https://samsung.com", []),
            ("15b7", "SanDisk", "SanDisk Corporation", "https://sandisk.com", ["Western Digital"]),
            ("1987", "Phison", "Phison Electronics", "https://phison.com", []),
            ("126f", "Silicon Motion", "Silicon Motion Inc.", "https://siliconmotion.com", ["SMI"]),
            
            # USB/Audio vendors
            ("046d", "Logitech", "Logitech Inc.", "https://logitech.com", []),
            ("0781", "SanDisk", "SanDisk Corporation", "https://sandisk.com", []),
            ("05ac", "Apple", "Apple Inc.", "https://apple.com", []),
            ("1532", "Razer", "Razer USA Ltd.", "https://razer.com", []),
            
            # Generic/Common vendors
            ("0000", "Unknown", "Unknown Vendor", None, []),
            ("ffff", "Invalid", "Invalid Vendor ID", None, [])
        ]
        
        for vendor_id, name, full_name, website, aliases in vendors:
            # Create enhanced vendor info with patch capabilities
            patch_compat = self._create_vendor_patch_compatibility(vendor_id, name)
            
            self._vendors[vendor_id.upper()] = VendorInfo(
                vendor_id=vendor_id.upper(),
                name=name,
                full_name=full_name,
                website=website,
                aliases=aliases,
                patch_compatibility=patch_compat
            )
    
    def _init_pci_devices(self):
        """Initialize PCI device database with common devices"""
        devices = [
            # Intel CPUs/Chipsets (sample)
            ("8086", "0046", "Intel Core Processor Integrated Graphics", "graphics"),
            ("8086", "0116", "Intel HD Graphics 3000", "graphics"),
            ("8086", "0166", "Intel HD Graphics 4000", "graphics"),
            ("8086", "041e", "Intel HD Graphics 4400", "graphics"),
            ("8086", "1916", "Intel HD Graphics 520", "graphics"),
            ("8086", "5916", "Intel HD Graphics 620", "graphics"),
            ("8086", "3e9b", "Intel UHD Graphics 630", "graphics"),
            ("8086", "9bc4", "Intel UHD Graphics", "graphics"),
            
            # Intel Network adapters (sample)
            ("8086", "10d3", "Intel 82574L Gigabit Network Connection", "network"),
            ("8086", "15b7", "Intel Ethernet Connection", "network"),
            ("8086", "15b8", "Intel Ethernet Connection", "network"),
            ("8086", "1539", "Intel I211 Gigabit Network Connection", "network"),
            
            # NVIDIA GPUs (sample)
            ("10de", "1c03", "NVIDIA GeForce GTX 1060 6GB", "graphics"),
            ("10de", "1b81", "NVIDIA GeForce GTX 1070", "graphics"),
            ("10de", "1b80", "NVIDIA GeForce GTX 1080", "graphics"),
            ("10de", "1e04", "NVIDIA GeForce RTX 2080 Ti", "graphics"),
            ("10de", "2208", "NVIDIA GeForce RTX 3080", "graphics"),
            ("10de", "220a", "NVIDIA GeForce RTX 3080", "graphics"),
            ("10de", "2484", "NVIDIA GeForce RTX 3070", "graphics"),
            ("10de", "249d", "NVIDIA GeForce RTX 3070", "graphics"),
            
            # AMD GPUs (sample) 
            ("1002", "67df", "AMD Radeon RX 480", "graphics"),
            ("1002", "67ff", "AMD Radeon RX 580", "graphics"),
            ("1002", "699f", "AMD Radeon RX 5700 XT", "graphics"),
            ("1002", "73df", "AMD Radeon RX 6700 XT", "graphics"),
            ("1002", "73bf", "AMD Radeon RX 6800 XT", "graphics"),
            
            # Realtek Network
            ("10ec", "8168", "Realtek RTL8111/8168/8411 PCI Express Gigabit Ethernet Controller", "network"),
            ("10ec", "8125", "Realtek RTL8125 2.5GbE Controller", "network"),
            
            # Broadcom Network
            ("14e4", "1684", "Broadcom NetXtreme BCM5764M Gigabit Ethernet", "network"),
            ("14e4", "16b4", "Broadcom NetXtreme BCM57765 Gigabit Ethernet", "network"),
        ]
        
        for vendor_id, device_id, name, category in devices:
            key = f"{vendor_id.upper()}:{device_id.upper()}"
            self._devices[key] = DeviceInfo(
                vendor_id=vendor_id.upper(),
                device_id=device_id.upper(),
                name=name,
                category=category
            )
    
    def _init_mac_models(self):
        """Initialize macOS model identifier database"""
        mac_models = {
            # iMacs
            "iMac14,1": {"name": "iMac 21.5-inch Late 2013", "year": 2013, "screen": 21.5},
            "iMac14,2": {"name": "iMac 27-inch Late 2013", "year": 2013, "screen": 27},
            "iMac15,1": {"name": "iMac 27-inch Late 2014/Mid 2015", "year": 2014, "screen": 27},
            "iMac16,1": {"name": "iMac 21.5-inch Late 2015", "year": 2015, "screen": 21.5},
            "iMac16,2": {"name": "iMac 21.5-inch Late 2015", "year": 2015, "screen": 21.5},
            "iMac17,1": {"name": "iMac 21.5-inch Late 2015", "year": 2015, "screen": 21.5},
            "iMac18,1": {"name": "iMac 21.5-inch 2017", "year": 2017, "screen": 21.5},
            "iMac18,2": {"name": "iMac 21.5-inch 2017", "year": 2017, "screen": 21.5},
            "iMac18,3": {"name": "iMac 27-inch 2017", "year": 2017, "screen": 27},
            "iMac19,1": {"name": "iMac 27-inch 2019", "year": 2019, "screen": 27},
            "iMac19,2": {"name": "iMac 21.5-inch 2019", "year": 2019, "screen": 21.5},
            "iMac20,1": {"name": "iMac 27-inch 2020", "year": 2020, "screen": 27},
            "iMac20,2": {"name": "iMac 27-inch 2020", "year": 2020, "screen": 27},
            "iMac21,1": {"name": "iMac 24-inch M1 2021", "year": 2021, "screen": 24, "chip": "M1"},
            "iMac21,2": {"name": "iMac 24-inch M1 2021", "year": 2021, "screen": 24, "chip": "M1"},
            
            # iMac Pro
            "iMacPro1,1": {"name": "iMac Pro 2017", "year": 2017, "screen": 27},
            
            # MacBook Air
            "MacBookAir6,1": {"name": "MacBook Air 11-inch Mid 2013/Early 2014", "year": 2013, "screen": 11},
            "MacBookAir6,2": {"name": "MacBook Air 13-inch Mid 2013/Early 2014", "year": 2013, "screen": 13},
            "MacBookAir7,1": {"name": "MacBook Air 11-inch Early 2015", "year": 2015, "screen": 11},
            "MacBookAir7,2": {"name": "MacBook Air 13-inch 2015/2017", "year": 2015, "screen": 13},
            "MacBookAir8,1": {"name": "MacBook Air 13-inch 2018", "year": 2018, "screen": 13},
            "MacBookAir8,2": {"name": "MacBook Air 13-inch 2019", "year": 2019, "screen": 13},
            "MacBookAir9,1": {"name": "MacBook Air 13-inch 2020", "year": 2020, "screen": 13},
            "MacBookAir10,1": {"name": "MacBook Air M1 2020", "year": 2020, "screen": 13, "chip": "M1"},
            "MacBookAir10,2": {"name": "MacBook Air M2 2022", "year": 2022, "screen": 13, "chip": "M2"},
            
            # MacBook Pro 13-inch
            "MacBookPro11,1": {"name": "MacBook Pro 13-inch Late 2013/Mid 2014", "year": 2013, "screen": 13},
            "MacBookPro12,1": {"name": "MacBook Pro 13-inch Early 2015", "year": 2015, "screen": 13},
            "MacBookPro13,1": {"name": "MacBook Pro 13-inch 2016", "year": 2016, "screen": 13},
            "MacBookPro13,2": {"name": "MacBook Pro 13-inch 2016", "year": 2016, "screen": 13},
            "MacBookPro14,1": {"name": "MacBook Pro 13-inch 2017", "year": 2017, "screen": 13},
            "MacBookPro14,2": {"name": "MacBook Pro 13-inch 2017", "year": 2017, "screen": 13},
            "MacBookPro15,2": {"name": "MacBook Pro 13-inch 2018/2019", "year": 2018, "screen": 13},
            "MacBookPro16,2": {"name": "MacBook Pro 13-inch 2020", "year": 2020, "screen": 13},
            "MacBookPro17,1": {"name": "MacBook Pro M1 13-inch 2020", "year": 2020, "screen": 13, "chip": "M1"},
            
            # MacBook Pro 15-inch
            "MacBookPro11,2": {"name": "MacBook Pro 15-inch Late 2013", "year": 2013, "screen": 15},
            "MacBookPro11,3": {"name": "MacBook Pro 15-inch Late 2013", "year": 2013, "screen": 15},
            "MacBookPro11,4": {"name": "MacBook Pro 15-inch Mid 2015", "year": 2015, "screen": 15},
            "MacBookPro11,5": {"name": "MacBook Pro 15-inch Mid 2015", "year": 2015, "screen": 15},
            "MacBookPro13,3": {"name": "MacBook Pro 15-inch 2016", "year": 2016, "screen": 15},
            "MacBookPro14,3": {"name": "MacBook Pro 15-inch 2017", "year": 2017, "screen": 15},
            "MacBookPro15,1": {"name": "MacBook Pro 15-inch 2018/2019", "year": 2018, "screen": 15},
            "MacBookPro15,3": {"name": "MacBook Pro 15-inch 2019", "year": 2019, "screen": 15},
            
            # MacBook Pro 16-inch
            "MacBookPro16,1": {"name": "MacBook Pro 16-inch 2019/2020", "year": 2019, "screen": 16},
            "MacBookPro18,1": {"name": "MacBook Pro M1 Pro 16-inch 2021", "year": 2021, "screen": 16, "chip": "M1 Pro"},
            "MacBookPro18,2": {"name": "MacBook Pro M1 Max 16-inch 2021", "year": 2021, "screen": 16, "chip": "M1 Max"},
            
            # MacBook Pro 14-inch
            "MacBookPro18,3": {"name": "MacBook Pro M1 Pro 14-inch 2021", "year": 2021, "screen": 14, "chip": "M1 Pro"},
            "MacBookPro18,4": {"name": "MacBook Pro M1 Max 14-inch 2021", "year": 2021, "screen": 14, "chip": "M1 Max"},
            
            # Mac mini
            "Macmini6,1": {"name": "Mac mini Late 2012", "year": 2012},
            "Macmini6,2": {"name": "Mac mini Late 2012", "year": 2012},
            "Macmini7,1": {"name": "Mac mini Late 2014", "year": 2014},
            "Macmini8,1": {"name": "Mac mini 2018", "year": 2018},
            "Macmini9,1": {"name": "Mac mini M1 2020", "year": 2020, "chip": "M1"},
            
            # Mac Pro
            "MacPro6,1": {"name": "Mac Pro Late 2013", "year": 2013},
            "MacPro7,1": {"name": "Mac Pro 2019", "year": 2019},
            
            # Mac Studio
            "MacStudio1,1": {"name": "Mac Studio M1 Max 2022", "year": 2022, "chip": "M1 Max"},
            "MacStudio1,2": {"name": "Mac Studio M1 Ultra 2022", "year": 2022, "chip": "M1 Ultra"},
        }
        
        self._mac_models = mac_models
    
    def _init_cpu_patterns(self):
        """Initialize CPU identification patterns"""
        cpu_patterns = {
            # Intel CPU patterns
            "intel_core_i3": {
                "pattern": r"Intel.*Core.*i3[-\s]*(\d+)([KHU]?)",
                "vendor": "Intel",
                "family": "Core i3",
                "architecture": "x86_64"
            },
            "intel_core_i5": {
                "pattern": r"Intel.*Core.*i5[-\s]*(\d+)([KHUG]?)",
                "vendor": "Intel", 
                "family": "Core i5",
                "architecture": "x86_64"
            },
            "intel_core_i7": {
                "pattern": r"Intel.*Core.*i7[-\s]*(\d+)([KHUG]?)",
                "vendor": "Intel",
                "family": "Core i7", 
                "architecture": "x86_64"
            },
            "intel_core_i9": {
                "pattern": r"Intel.*Core.*i9[-\s]*(\d+)([KHUG]?)",
                "vendor": "Intel",
                "family": "Core i9",
                "architecture": "x86_64"
            },
            "intel_xeon": {
                "pattern": r"Intel.*Xeon.*([EWD]?[-\s]*\d+)",
                "vendor": "Intel",
                "family": "Xeon",
                "architecture": "x86_64"
            },
            "intel_celeron": {
                "pattern": r"Intel.*Celeron.*(\d+)",
                "vendor": "Intel",
                "family": "Celeron",
                "architecture": "x86_64"
            },
            "intel_pentium": {
                "pattern": r"Intel.*Pentium.*(\d+)",
                "vendor": "Intel",
                "family": "Pentium",
                "architecture": "x86_64"
            },
            
            # AMD CPU patterns
            "amd_ryzen_3": {
                "pattern": r"AMD.*Ryzen.*3.*(\d+)",
                "vendor": "AMD",
                "family": "Ryzen 3",
                "architecture": "x86_64"
            },
            "amd_ryzen_5": {
                "pattern": r"AMD.*Ryzen.*5.*(\d+)",
                "vendor": "AMD",
                "family": "Ryzen 5",
                "architecture": "x86_64"
            },
            "amd_ryzen_7": {
                "pattern": r"AMD.*Ryzen.*7.*(\d+)",
                "vendor": "AMD",
                "family": "Ryzen 7",
                "architecture": "x86_64"
            },
            "amd_ryzen_9": {
                "pattern": r"AMD.*Ryzen.*9.*(\d+)",
                "vendor": "AMD",
                "family": "Ryzen 9",
                "architecture": "x86_64"
            },
            "amd_threadripper": {
                "pattern": r"AMD.*Ryzen.*Threadripper.*(\d+)",
                "vendor": "AMD",
                "family": "Threadripper",
                "architecture": "x86_64"
            },
            "amd_epyc": {
                "pattern": r"AMD.*EPYC.*(\d+)",
                "vendor": "AMD",
                "family": "EPYC",
                "architecture": "x86_64"
            },
            "amd_fx": {
                "pattern": r"AMD.*FX[-\s]*(\d+)",
                "vendor": "AMD",
                "family": "FX",
                "architecture": "x86_64"
            },
            
            # Apple Silicon patterns
            "apple_m1": {
                "pattern": r"Apple.*M1(\s+Pro|\s+Max|\s+Ultra)?",
                "vendor": "Apple",
                "family": "Apple Silicon M1",
                "architecture": "arm64"
            },
            "apple_m2": {
                "pattern": r"Apple.*M2(\s+Pro|\s+Max|\s+Ultra)?",
                "vendor": "Apple",
                "family": "Apple Silicon M2",
                "architecture": "arm64"
            },
            "apple_m3": {
                "pattern": r"Apple.*M3(\s+Pro|\s+Max|\s+Ultra)?",
                "vendor": "Apple",
                "family": "Apple Silicon M3",
                "architecture": "arm64"
            },
            
            # ARM patterns (generic)
            "arm_cortex_a": {
                "pattern": r"ARM.*Cortex[-\s]*A(\d+)",
                "vendor": "ARM",
                "family": "Cortex-A",
                "architecture": "arm64"
            },
            "arm_generic": {
                "pattern": r"ARM.*(\w+)",
                "vendor": "ARM",
                "family": "ARM Generic",
                "architecture": "arm64"
            },
        }
        
        self._cpu_patterns = cpu_patterns
    
    def _init_gpu_vendors(self):
        """Initialize GPU vendor detection patterns"""
        gpu_vendors = {
            "nvidia": {
                "patterns": [
                    r"NVIDIA",
                    r"GeForce",
                    r"Quadro",
                    r"Tesla",
                    r"RTX",
                    r"GTX"
                ],
                "vendor": "NVIDIA"
            },
            "amd": {
                "patterns": [
                    r"AMD",
                    r"Radeon", 
                    r"FirePro",
                    r"RX\s*\d+",
                    r"Vega",
                    r"RDNA"
                ],
                "vendor": "AMD"
            },
            "intel": {
                "patterns": [
                    r"Intel.*Graphics",
                    r"Intel.*HD",
                    r"Intel.*UHD",
                    r"Intel.*Iris",
                    r"Intel.*Xe"
                ],
                "vendor": "Intel"
            },
            "apple": {
                "patterns": [
                    r"Apple.*M\d+",
                    r"Apple.*GPU"
                ],
                "vendor": "Apple"
            }
        }
        
        self._gpu_vendors = gpu_vendors
    
    def lookup_vendor(self, vendor_id: str) -> Optional[VendorInfo]:
        """Look up vendor information by PCI vendor ID"""
        return self._vendors.get(vendor_id.upper())
    
    def lookup_device(self, vendor_id: str, device_id: str) -> Optional[DeviceInfo]:
        """Look up device information by PCI vendor:device ID"""
        key = f"{vendor_id.upper()}:{device_id.upper()}"
        return self._devices.get(key)
    
    def lookup_mac_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Look up Mac model information by model identifier"""
        return self._mac_models.get(model_id)
    
    def identify_cpu(self, cpu_name: str) -> Dict[str, Any]:
        """Identify CPU vendor, family, and architecture from CPU name"""
        result = {
            "vendor": "Unknown",
            "family": "Unknown", 
            "architecture": "unknown",
            "model": cpu_name,
            "match_confidence": 0.0
        }
        
        if not cpu_name:
            return result
        
        # Try to match against known CPU patterns
        best_match = None
        best_confidence = 0.0
        
        for pattern_name, pattern_info in self._cpu_patterns.items():
            pattern = pattern_info["pattern"]
            match = re.search(pattern, cpu_name, re.IGNORECASE)
            
            if match:
                # Calculate confidence based on pattern specificity
                confidence = 0.7 + (len(match.group(0)) / len(cpu_name)) * 0.3
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = pattern_info
        
        if best_match:
            result.update({
                "vendor": best_match["vendor"],
                "family": best_match["family"],
                "architecture": best_match["architecture"],
                "match_confidence": best_confidence
            })
        
        return result
    
    def identify_gpu_vendor(self, gpu_name: str) -> Dict[str, Any]:
        """Identify GPU vendor from GPU name"""
        result = {
            "vendor": "Unknown",
            "confidence": 0.0
        }
        
        if not gpu_name:
            return result
        
        # Try to match against known GPU vendor patterns
        best_confidence = 0.0
        best_vendor = "Unknown"
        
        for vendor_key, vendor_info in self._gpu_vendors.items():
            for pattern in vendor_info["patterns"]:
                if re.search(pattern, gpu_name, re.IGNORECASE):
                    # Higher confidence for more specific matches
                    confidence = 0.8 + (len(pattern) / len(gpu_name)) * 0.2
                    
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_vendor = vendor_info["vendor"]
        
        result.update({
            "vendor": best_vendor,
            "confidence": best_confidence
        })
        
        return result
    
    def search_vendors(self, search_term: str, limit: int = 10) -> List[VendorInfo]:
        """Search vendors by name or alias"""
        matches = []
        search_lower = search_term.lower()
        
        for vendor in self._vendors.values():
            # Check name match
            if search_lower in vendor.name.lower():
                matches.append((vendor, 1.0))
                continue
            
            # Check full name match
            if vendor.full_name and search_lower in vendor.full_name.lower():
                matches.append((vendor, 0.8))
                continue
            
            # Check aliases
            for alias in vendor.aliases:
                if search_lower in alias.lower():
                    matches.append((vendor, 0.6))
                    break
        
        # Sort by relevance score and return top matches
        matches.sort(key=lambda x: x[1], reverse=True)
        return [match[0] for match in matches[:limit]]
    
    def get_vendor_summary(self) -> Dict[str, int]:
        """Get summary statistics of the vendor database"""
        return {
            "total_vendors": len(self._vendors),
            "total_devices": len(self._devices), 
            "mac_models": len(self._mac_models),
            "cpu_patterns": len(self._cpu_patterns),
            "gpu_vendors": len(self._gpu_vendors)
        }
    
    def normalize_vendor_name(self, vendor_name: str) -> str:
        """Normalize vendor name to standard form"""
        if not vendor_name:
            return "Unknown"
        
        # Common normalizations
        normalizations = {
            "intel corp": "Intel",
            "intel corporation": "Intel",
            "advanced micro devices": "AMD",
            "amd inc": "AMD",
            "authenticamd": "AMD",
            "nvidia corporation": "NVIDIA",
            "nvdia": "NVIDIA",  # Common typo
            "ati technologies inc": "ATI/AMD",
            "apple inc": "Apple",
            "apple computer": "Apple",
            "microsoft corporation": "Microsoft",
            "broadcom inc": "Broadcom",
            "broadcom corporation": "Broadcom",
            "realtek semiconductor": "Realtek",
            "qualcomm atheros": "Qualcomm",
            "dell inc": "Dell",
            "hewlett-packard": "HP",
            "hewlett packard": "HP",
            "lenovo group ltd": "Lenovo",
            "asustek computer inc": "ASUS",
            "micro-star international": "MSI"
        }
        
        vendor_lower = vendor_name.lower().strip()
        return normalizations.get(vendor_lower, vendor_name)
    
    def get_architecture_from_cpu(self, cpu_name: str) -> str:
        """Get CPU architecture from CPU name"""
        cpu_info = self.identify_cpu(cpu_name)
        return cpu_info.get("architecture", "unknown")
    
    def is_mobile_cpu(self, cpu_name: str) -> bool:
        """Detect if CPU is a mobile/laptop variant"""
        if not cpu_name:
            return False
        
        mobile_indicators = [
            "mobile", "m ", "h ", "u ", "y ", "hq", "hk", 
            "laptop", "notebook", "ultra low power"
        ]
        
        cpu_lower = cpu_name.lower()
        return any(indicator in cpu_lower for indicator in mobile_indicators)
    
    def get_cpu_generation(self, cpu_name: str) -> Optional[int]:
        """Extract CPU generation from name (Intel/AMD)"""
        if not cpu_name:
            return None
        
        # Intel patterns (i3-8350, i7-10700K, etc.)
        intel_match = re.search(r"i[357][-\s]*(\d)(\d+)", cpu_name, re.IGNORECASE)
        if intel_match:
            return int(intel_match.group(1))
        
        # AMD Ryzen patterns (Ryzen 5 3600, Ryzen 7 5800X, etc.)
        amd_match = re.search(r"ryzen.*[357].*(\d)(\d+)", cpu_name, re.IGNORECASE)
        if amd_match:
            return int(amd_match.group(1))
        
        return None
    
    # ===== PATCH CAPABILITY METHODS =====
    
    def _create_vendor_patch_compatibility(self, vendor_id: str, vendor_name: str) -> PatchCompatibility:
        """Create patch compatibility information for a vendor"""
        try:
            # Create default compatibility with vendor-specific capabilities
            capabilities = set()
            security_level = SecurityLevel.MODERATE
            
            # Set capabilities based on vendor
            vendor_lower = vendor_name.lower()
            
            if vendor_lower in ["intel", "amd"]:
                # CPU/Chipset vendors - support most patching
                capabilities.update([
                    PatchCapability.DRIVER_INJECTION,
                    PatchCapability.KERNEL_PATCHING,
                    PatchCapability.EFI_MODIFICATION,
                    PatchCapability.REGISTRY_PATCHING,
                    PatchCapability.CUSTOM_SCRIPTS
                ])
                security_level = SecurityLevel.MODERATE
                
            elif vendor_lower in ["nvidia", "ati", "amd"]:
                # GPU vendors - support driver injection and some patches
                capabilities.update([
                    PatchCapability.DRIVER_INJECTION,
                    PatchCapability.KERNEL_PATCHING,
                    PatchCapability.KEXT_LOADING,
                    PatchCapability.REGISTRY_PATCHING
                ])
                security_level = SecurityLevel.MODERATE
                
            elif vendor_lower in ["broadcom", "realtek", "atheros", "qualcomm"]:
                # Network vendors - mainly driver injection
                capabilities.update([
                    PatchCapability.DRIVER_INJECTION,
                    PatchCapability.KEXT_LOADING,
                    PatchCapability.REGISTRY_PATCHING
                ])
                security_level = SecurityLevel.MODERATE
                
            elif vendor_lower == "apple":
                # Apple hardware - limited patching due to security
                capabilities.update([
                    PatchCapability.KEXT_LOADING,
                    PatchCapability.EFI_MODIFICATION,
                    PatchCapability.CUSTOM_SCRIPTS
                ])
                security_level = SecurityLevel.STRICT
                
            else:
                # Generic vendors - basic capabilities
                capabilities.update([
                    PatchCapability.DRIVER_INJECTION,
                    PatchCapability.REGISTRY_PATCHING
                ])
                security_level = SecurityLevel.MODERATE
            
            # Create OS-specific support mapping
            macos_support = {}
            windows_support = {}
            linux_support = {}
            
            if PatchCapability.KEXT_LOADING in capabilities:
                macos_support.update({
                    "11.*": ["kext_injection", "sip_bypass"],
                    "12.*": ["kext_injection", "sip_bypass"], 
                    "13.*": ["kext_injection", "sip_bypass"],
                    "14.*": ["kext_injection", "sip_bypass"]
                })
            
            if PatchCapability.DRIVER_INJECTION in capabilities:
                windows_support.update({
                    "10.*": ["driver_injection", "registry_patch"],
                    "11.*": ["driver_injection", "registry_patch"]
                })
                linux_support.update({
                    ".*": ["driver_injection", "kernel_module"]
                })
            
            return PatchCompatibility(
                supported_capabilities=capabilities,
                security_level=security_level,
                macos_support=macos_support,
                windows_support=windows_support,
                linux_support=linux_support,
                requires_signed_drivers=(security_level != SecurityLevel.OPEN),
                requires_secure_boot_off=(PatchCapability.SECURE_BOOT_BYPASS in capabilities),
                requires_sip_disabled=(PatchCapability.KEXT_LOADING in capabilities)
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create patch compatibility for {vendor_name}: {e}")
            return PatchCompatibility()  # Return default compatibility
    
    def get_vendor_patch_capabilities(self, vendor_id: str) -> Optional[PatchCompatibility]:
        """Get patch capabilities for a vendor"""
        vendor = self._vendors.get(vendor_id.upper())
        return vendor.patch_compatibility if vendor else None
    
    def get_device_patch_capabilities(self, vendor_id: str, device_id: str) -> Optional[PatchCompatibility]:
        """Get patch capabilities for a specific device"""
        device_key = f"{vendor_id.upper()}:{device_id.upper()}"
        device = self._devices.get(device_key)
        
        if device and device.patch_compatibility:
            return device.patch_compatibility
        
        # Fall back to vendor capabilities
        return self.get_vendor_patch_capabilities(vendor_id)
    
    def check_patch_support(self, vendor_id: str, device_id: str, 
                          capability: PatchCapability) -> bool:
        """Check if a device supports a specific patch capability"""
        patch_compat = self.get_device_patch_capabilities(vendor_id, device_id)
        return patch_compat.supports_capability(capability) if patch_compat else False
    
    def get_os_patch_support(self, vendor_id: str, device_id: str,
                           os_family: str, os_version: str) -> List[str]:
        """Get OS-specific patch support for a device"""
        patch_compat = self.get_device_patch_capabilities(vendor_id, device_id)
        return patch_compat.get_os_support(os_family, os_version) if patch_compat else []
    
    def find_devices_with_capability(self, capability: PatchCapability) -> List[DeviceInfo]:
        """Find all devices that support a specific patch capability"""
        matching_devices = []
        
        for device in self._devices.values():
            if device.patch_compatibility and device.patch_compatibility.supports_capability(capability):
                matching_devices.append(device)
        
        return matching_devices
    
    def get_security_level(self, vendor_id: str, device_id: Optional[str] = None) -> SecurityLevel:
        """Get security level for vendor or device"""
        if device_id:
            patch_compat = self.get_device_patch_capabilities(vendor_id, device_id)
        else:
            patch_compat = self.get_vendor_patch_capabilities(vendor_id)
        
        return patch_compat.security_level if patch_compat else SecurityLevel.STRICT
    
    def add_device_patch_info(self, vendor_id: str, device_id: str,
                            patch_compatibility: PatchCompatibility,
                            driver_package: Optional[str] = None,
                            patch_notes: Optional[str] = None):
        """Add or update patch information for a device"""
        device_key = f"{vendor_id.upper()}:{device_id.upper()}"
        device = self._devices.get(device_key)
        
        if device:
            device.patch_compatibility = patch_compatibility
            device.driver_package = driver_package
            device.patch_notes = patch_notes
            self.logger.info(f"Updated patch info for device: {device_key}")
        else:
            self.logger.warning(f"Device not found in database: {device_key}")
    
    def get_patch_requirements(self, vendor_id: str, device_id: str,
                             os_family: str) -> Dict[str, bool]:
        """Get patch requirements for a device on specific OS"""
        patch_compat = self.get_device_patch_capabilities(vendor_id, device_id)
        
        if not patch_compat:
            return {}
        
        requirements = {
            "signed_drivers": patch_compat.requires_signed_drivers,
            "secure_boot_off": patch_compat.requires_secure_boot_off,
            "test_signing": patch_compat.requires_test_signing
        }
        
        # OS-specific requirements
        if os_family.lower() == "macos":
            requirements["sip_disabled"] = patch_compat.requires_sip_disabled
        elif os_family.lower() == "windows":
            requirements["test_signing"] = patch_compat.requires_test_signing
        
        return requirements
    
    def get_patch_statistics(self) -> Dict[str, Any]:
        """Get statistics about patch capabilities in the database"""
        try:
            stats = {
                "total_vendors_with_patches": 0,
                "total_devices_with_patches": 0,
                "capabilities_by_count": {},
                "security_levels": {},
                "os_support": {"macos": 0, "windows": 0, "linux": 0}
            }
            
            # Count vendors with patch capabilities
            for vendor in self._vendors.values():
                if vendor.patch_compatibility and vendor.patch_compatibility.supported_capabilities:
                    stats["total_vendors_with_patches"] += 1
            
            # Count devices with patch capabilities
            for device in self._devices.values():
                if device.patch_compatibility and device.patch_compatibility.supported_capabilities:
                    stats["total_devices_with_patches"] += 1
                    
                    # Count capabilities
                    for capability in device.patch_compatibility.supported_capabilities:
                        cap_name = capability.value
                        stats["capabilities_by_count"][cap_name] = stats["capabilities_by_count"].get(cap_name, 0) + 1
                    
                    # Count security levels
                    sec_level = device.patch_compatibility.security_level.value
                    stats["security_levels"][sec_level] = stats["security_levels"].get(sec_level, 0) + 1
                    
                    # Count OS support
                    if device.patch_compatibility.macos_support:
                        stats["os_support"]["macos"] += 1
                    if device.patch_compatibility.windows_support:
                        stats["os_support"]["windows"] += 1
                    if device.patch_compatibility.linux_support:
                        stats["os_support"]["linux"] += 1
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get patch statistics: {e}")
            return {}