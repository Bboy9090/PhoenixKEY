"""
BootForge Hardware Profiles - Comprehensive Mac Model Database
Enhanced hardware profile management with detailed Mac model specifications,
patch requirements, and OCLP compatibility mapping.
Integrated with patch pipeline system for universal OS deployment.
"""

from .models import HardwareProfile, DeploymentType
from .patch_pipeline import (
    PatchSet, PatchAction, PatchType, PatchPhase, PatchPriority, 
    PatchCondition, PatchStatus
)
from .vendor_database import PatchCapability, SecurityLevel, PatchCompatibility
from typing import List, Dict, Optional, Any
import re
import logging


def get_mac_model_data() -> Dict[str, Dict[str, Any]]:
    """
    Get comprehensive Mac model database with detailed specifications and patch requirements.
    
    Returns comprehensive data for Mac models from 2015-2024+ including:
    - Basic hardware specifications 
    - OCLP compatibility levels
    - Native macOS support matrix
    - Required patches per macOS version
    - Graphics, audio, WiFi/Bluetooth requirements
    """
    
    mac_models = {
        # ===== Intel Mac Models (2015-2020) - OCLP Compatible =====
        
        # MacBook Air (2015-2017) - Broadwell/Skylake/Kaby Lake
        "MacBookAir7,1": {
            "name": "MacBook Air 11\" (Early 2015)", "year": 2015, "cpu_family": "Intel Core i5/i7 (Broadwell)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.10": True, "10.11": True, "10.12": True, "10.13": True, "10.14": True, "10.15": True, "11.0": False, "12.0": False, "13.0": False, "14.0": False},
            "required_patches": {
                "11.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock"],
                "12.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock", "BlueToolFixup"],
                "13.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock", "BlueToolFixup", "CryptexFixup"],
                "14.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock", "BlueToolFixup", "CryptexFixup"]
            },
            "graphics_patches": ["Intel5000Controller"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["BrcmPatchRAM3", "BrcmFirmwareData", "BrcmBluetoothInjector"],
            "secure_boot_model": "j132", "sip_requirements": "disabled",
            "notes": ["Excellent OCLP support", "All features working", "Bluetooth requires patching"]
        },
        
        "MacBookAir7,2": {
            "name": "MacBook Air 13\" (Early 2015)", "year": 2015, "cpu_family": "Intel Core i5/i7 (Broadwell)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.10": True, "10.11": True, "10.12": True, "10.13": True, "10.14": True, "10.15": True, "11.0": False, "12.0": False, "13.0": False, "14.0": False},
            "required_patches": {
                "11.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock"],
                "12.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock", "BlueToolFixup"],
                "13.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock", "BlueToolFixup", "CryptexFixup"],
                "14.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock", "BlueToolFixup", "CryptexFixup"]
            },
            "graphics_patches": ["Intel5000Controller"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["BrcmPatchRAM3", "BrcmFirmwareData", "BrcmBluetoothInjector"],
            "secure_boot_model": "j132", "sip_requirements": "disabled",
            "notes": ["Excellent OCLP support", "Popular model for OCLP"]
        },
        
        "MacBookAir8,1": {
            "name": "MacBook Air 13\" (Late 2018)", "year": 2018, "cpu_family": "Intel Core i5 (Amber Lake)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.14": True, "10.15": True, "11.0": True, "12.0": True, "13.0": False, "14.0": False},
            "required_patches": {
                "13.0": ["AMFIPass", "RestrictEvents"],
                "14.0": ["AMFIPass", "RestrictEvents", "CryptexFixup"]
            },
            "graphics_patches": ["IntelUHD617"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["AirportBrcmFixup", "BrcmPatchRAM3"],
            "secure_boot_model": "j140k", "sip_requirements": "disabled",
            "notes": ["T2 Security Chip", "Secure Boot supported", "TouchID compatible"]
        },
        
        "MacBookAir8,2": {
            "name": "MacBook Air 13\" (Mid 2019)", "year": 2019, "cpu_family": "Intel Core i5 (Amber Lake)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported", 
            "native_macos_support": {"10.14": True, "10.15": True, "11.0": True, "12.0": True, "13.0": False, "14.0": False},
            "required_patches": {
                "13.0": ["AMFIPass", "RestrictEvents"],
                "14.0": ["AMFIPass", "RestrictEvents", "CryptexFixup"]
            },
            "graphics_patches": ["IntelUHD617"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["AirportBrcmFixup", "BrcmPatchRAM3"],
            "secure_boot_model": "j140k", "sip_requirements": "disabled",
            "notes": ["T2 Security Chip", "True Tone display"]
        },
        
        # MacBook Pro 13" (2015-2020)
        "MacBookPro12,1": {
            "name": "MacBook Pro 13\" (Early 2015)", "year": 2015, "cpu_family": "Intel Core i5/i7 (Broadwell)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.10": True, "10.11": True, "10.12": True, "10.13": True, "10.14": True, "10.15": True, "11.0": False, "12.0": False, "13.0": False, "14.0": False},
            "required_patches": {
                "11.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock"],
                "12.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock", "BlueToolFixup"],
                "13.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock", "BlueToolFixup", "CryptexFixup"],
                "14.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock", "BlueToolFixup", "CryptexFixup"]
            },
            "graphics_patches": ["Intel5000Controller"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["BrcmPatchRAM3", "BrcmFirmwareData"],
            "secure_boot_model": "j52", "sip_requirements": "disabled",
            "notes": ["Force Touch trackpad", "Full OCLP support"]
        },
        
        "MacBookPro13,1": {
            "name": "MacBook Pro 13\" (Late 2016)", "year": 2016, "cpu_family": "Intel Core i5/i7 (Skylake)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.12": True, "10.13": True, "10.14": True, "10.15": True, "11.0": True, "12.0": False, "13.0": False, "14.0": False},
            "required_patches": {
                "12.0": ["AMFIPass", "RestrictEvents"],
                "13.0": ["AMFIPass", "RestrictEvents", "BlueToolFixup"],
                "14.0": ["AMFIPass", "RestrictEvents", "BlueToolFixup", "CryptexFixup"]
            },
            "graphics_patches": ["IntelSkylakeGraphics"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["AirportBrcmFixup", "BrcmPatchRAM3"],
            "secure_boot_model": "j79", "sip_requirements": "disabled",
            "notes": ["USB-C only", "No TouchBar", "Excellent compatibility"]
        },
        
        "MacBookPro13,2": {
            "name": "MacBook Pro 13\" with TouchBar (Late 2016)", "year": 2016, "cpu_family": "Intel Core i5/i7 (Skylake)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.12": True, "10.13": True, "10.14": True, "10.15": True, "11.0": True, "12.0": False, "13.0": False, "14.0": False},
            "required_patches": {
                "12.0": ["AMFIPass", "RestrictEvents"],
                "13.0": ["AMFIPass", "RestrictEvents", "BlueToolFixup"],
                "14.0": ["AMFIPass", "RestrictEvents", "BlueToolFixup", "CryptexFixup"]
            },
            "graphics_patches": ["IntelSkylakeGraphics"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["AirportBrcmFixup", "BrcmPatchRAM3"],
            "usb_patches": ["USBToolBox"],
            "secure_boot_model": "j79", "sip_requirements": "disabled",
            "notes": ["TouchBar support", "TouchID support", "T1 Security Chip"]
        },
        
        "MacBookPro14,1": {
            "name": "MacBook Pro 13\" (Mid 2017)", "year": 2017, "cpu_family": "Intel Core i5/i7 (Kaby Lake)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.12": True, "10.13": True, "10.14": True, "10.15": True, "11.0": True, "12.0": True, "13.0": False, "14.0": False},
            "required_patches": {
                "13.0": ["AMFIPass", "RestrictEvents"],
                "14.0": ["AMFIPass", "RestrictEvents", "CryptexFixup"]
            },
            "graphics_patches": ["IntelKabyLakeGraphics"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["AirportBrcmFixup", "BrcmPatchRAM3"],
            "secure_boot_model": "j79", "sip_requirements": "disabled",
            "notes": ["No TouchBar", "Improved keyboard", "Strong OCLP support"]
        },
        
        "MacBookPro14,2": {
            "name": "MacBook Pro 13\" with TouchBar (Mid 2017)", "year": 2017, "cpu_family": "Intel Core i5/i7 (Kaby Lake)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.12": True, "10.13": True, "10.14": True, "10.15": True, "11.0": True, "12.0": True, "13.0": False, "14.0": False},
            "required_patches": {
                "13.0": ["AMFIPass", "RestrictEvents"],
                "14.0": ["AMFIPass", "RestrictEvents", "CryptexFixup"]
            },
            "graphics_patches": ["IntelKabyLakeGraphics"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["AirportBrcmFixup", "BrcmPatchRAM3"],
            "secure_boot_model": "j79", "sip_requirements": "disabled",
            "notes": ["TouchBar and TouchID", "T1 chip", "Improved thermals"]
        },
        
        "MacBookPro15,2": {
            "name": "MacBook Pro 13\" with TouchBar (Mid 2018)", "year": 2018, "cpu_family": "Intel Core i5/i7 (Coffee Lake)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.13": True, "10.14": True, "10.15": True, "11.0": True, "12.0": True, "13.0": True, "14.0": False},
            "required_patches": {
                "14.0": ["AMFIPass", "RestrictEvents"]
            },
            "graphics_patches": ["IntelCoffeeLakeGraphics"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["AirportBrcmFixup", "BrcmPatchRAM3"],
            "secure_boot_model": "j132", "sip_requirements": "disabled",
            "notes": ["T2 Security Chip", "True Tone display", "Improved keyboard"]
        },
        
        "MacBookPro15,4": {
            "name": "MacBook Pro 13\" with TouchBar (Mid 2019)", "year": 2019, "cpu_family": "Intel Core i5/i7 (Coffee Lake Refresh)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.14": True, "10.15": True, "11.0": True, "12.0": True, "13.0": True, "14.0": False},
            "required_patches": {
                "14.0": ["AMFIPass", "RestrictEvents"]
            },
            "graphics_patches": ["IntelCoffeeLakeGraphics"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["AirportBrcmFixup", "BrcmPatchRAM3"],
            "secure_boot_model": "j132", "sip_requirements": "disabled",
            "notes": ["T2 Security Chip", "Quad-core option", "Butterfly keyboard"]
        },
        
        "MacBookPro16,2": {
            "name": "MacBook Pro 13\" (Mid 2020)", "year": 2020, "cpu_family": "Intel Core i5/i7 (Ice Lake)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.15": True, "11.0": True, "12.0": True, "13.0": True, "14.0": False},
            "required_patches": {
                "14.0": ["AMFIPass", "RestrictEvents"]
            },
            "graphics_patches": ["IntelIceLakeGraphics"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["AirportBrcmFixup", "BrcmPatchRAM3"],
            "secure_boot_model": "j214k", "sip_requirements": "disabled",
            "notes": ["T2 Security Chip", "Magic Keyboard", "10th gen Intel"]
        },
        
        # MacBook Pro 15" (2015-2019)
        "MacBookPro11,4": {
            "name": "MacBook Pro 15\" (Mid 2015)", "year": 2015, "cpu_family": "Intel Core i7 (Haswell/Crystalwell)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.10": True, "10.11": True, "10.12": True, "10.13": True, "10.14": True, "10.15": True, "11.0": False, "12.0": False, "13.0": False, "14.0": False},
            "required_patches": {
                "11.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock"],
                "12.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock", "BlueToolFixup"],
                "13.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock", "BlueToolFixup", "CryptexFixup"],
                "14.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock", "BlueToolFixup", "CryptexFixup"]
            },
            "graphics_patches": ["IntelHD5000", "AMDRadeonX4000"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["BrcmPatchRAM3", "BrcmFirmwareData"],
            "secure_boot_model": "j45", "sip_requirements": "disabled",
            "notes": ["Dual GPU (Intel + AMD)", "Force Touch trackpad", "DGPU switching issues possible"]
        },
        
        "MacBookPro11,5": {
            "name": "MacBook Pro 15\" (Mid 2015)", "year": 2015, "cpu_family": "Intel Core i7 (Haswell/Crystalwell)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.10": True, "10.11": True, "10.12": True, "10.13": True, "10.14": True, "10.15": True, "11.0": False, "12.0": False, "13.0": False, "14.0": False},
            "required_patches": {
                "11.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock"],
                "12.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock", "BlueToolFixup"],
                "13.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock", "BlueToolFixup", "CryptexFixup"],
                "14.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock", "BlueToolFixup", "CryptexFixup"]
            },
            "graphics_patches": ["IntelHD5000", "AMDRadeonX4000"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["BrcmPatchRAM3", "BrcmFirmwareData"],
            "secure_boot_model": "j45", "sip_requirements": "disabled",
            "notes": ["Dual GPU variant", "AMD R9 M370X graphics", "dGPU may require disabling"]
        },
        
        "MacBookPro13,3": {
            "name": "MacBook Pro 15\" with TouchBar (Late 2016)", "year": 2016, "cpu_family": "Intel Core i7 (Skylake)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.12": True, "10.13": True, "10.14": True, "10.15": True, "11.0": True, "12.0": False, "13.0": False, "14.0": False},
            "required_patches": {
                "12.0": ["AMFIPass", "RestrictEvents"],
                "13.0": ["AMFIPass", "RestrictEvents", "BlueToolFixup"],
                "14.0": ["AMFIPass", "RestrictEvents", "BlueToolFixup", "CryptexFixup"]
            },
            "graphics_patches": ["IntelSkylakeGraphics", "AMDRadeonX5000"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["AirportBrcmFixup", "BrcmPatchRAM3"],
            "secure_boot_model": "j79", "sip_requirements": "disabled",
            "notes": ["First TouchBar MBP", "Dual GPU issues", "T1 Security Chip"]
        },
        
        "MacBookPro14,3": {
            "name": "MacBook Pro 15\" with TouchBar (Mid 2017)", "year": 2017, "cpu_family": "Intel Core i7 (Kaby Lake)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.12": True, "10.13": True, "10.14": True, "10.15": True, "11.0": True, "12.0": True, "13.0": False, "14.0": False},
            "required_patches": {
                "13.0": ["AMFIPass", "RestrictEvents"],
                "14.0": ["AMFIPass", "RestrictEvents", "CryptexFixup"]
            },
            "graphics_patches": ["IntelKabyLakeGraphics", "AMDRadeonX5000"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["AirportBrcmFixup", "BrcmPatchRAM3"],
            "secure_boot_model": "j79", "sip_requirements": "disabled",
            "notes": ["Improved thermals", "AMD Radeon Pro 555/560", "Keyboard issues common"]
        },
        
        "MacBookPro15,1": {
            "name": "MacBook Pro 15\" with TouchBar (Mid 2018)", "year": 2018, "cpu_family": "Intel Core i7/i9 (Coffee Lake)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.13": True, "10.14": True, "10.15": True, "11.0": True, "12.0": True, "13.0": True, "14.0": False},
            "required_patches": {
                "14.0": ["AMFIPass", "RestrictEvents"]
            },
            "graphics_patches": ["IntelCoffeeLakeGraphics", "AMDRadeonX6000"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["AirportBrcmFixup", "BrcmPatchRAM3"],
            "secure_boot_model": "j132", "sip_requirements": "disabled",
            "notes": ["T2 Security Chip", "6-core and 8-core options", "AMD Radeon Pro 555X/560X"]
        },
        
        "MacBookPro15,3": {
            "name": "MacBook Pro 15\" with TouchBar (Mid 2019)", "year": 2019, "cpu_family": "Intel Core i7/i9 (Coffee Lake Refresh)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.14": True, "10.15": True, "11.0": True, "12.0": True, "13.0": True, "14.0": False},
            "required_patches": {
                "14.0": ["AMFIPass", "RestrictEvents"]
            },
            "graphics_patches": ["IntelCoffeeLakeGraphics", "AMDRadeonX6000"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["AirportBrcmFixup", "BrcmPatchRAM3"],
            "secure_boot_model": "j132", "sip_requirements": "disabled",
            "notes": ["T2 Security Chip", "AMD Radeon Pro 555X/560X/Vega 16/20", "8-core available"]
        },
        
        # MacBook Pro 16" (2019)
        "MacBookPro16,1": {
            "name": "MacBook Pro 16\" (Late 2019)", "year": 2019, "cpu_family": "Intel Core i7/i9 (Coffee Lake)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.15": True, "11.0": True, "12.0": True, "13.0": True, "14.0": False},
            "required_patches": {
                "14.0": ["AMFIPass", "RestrictEvents"]
            },
            "graphics_patches": ["IntelCoffeeLakeGraphics", "AMDRadeonX6000"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["AirportBrcmFixup", "BrcmPatchRAM3"],
            "secure_boot_model": "j152f", "sip_requirements": "disabled",
            "notes": ["T2 Security Chip", "Magic Keyboard", "AMD Radeon Pro 5300M/5500M/5600M", "Excellent OCLP support"]
        },
        
        "MacBookPro16,4": {
            "name": "MacBook Pro 16\" (Late 2019)", "year": 2019, "cpu_family": "Intel Core i9 (Coffee Lake)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.15": True, "11.0": True, "12.0": True, "13.0": True, "14.0": False},
            "required_patches": {
                "14.0": ["AMFIPass", "RestrictEvents"]
            },
            "graphics_patches": ["IntelCoffeeLakeGraphics", "AMDRadeonX6000"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["AirportBrcmFixup", "BrcmPatchRAM3"],
            "secure_boot_model": "j152f", "sip_requirements": "disabled",
            "notes": ["T2 Security Chip", "High-end configuration", "8-core processor"]
        },
        
        # iMac (2015-2020)
        "iMac16,1": {
            "name": "iMac 21.5\" (Late 2015)", "year": 2015, "cpu_family": "Intel Core i5 (Broadwell)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.11": True, "10.12": True, "10.13": True, "10.14": True, "10.15": True, "11.0": False, "12.0": False, "13.0": False, "14.0": False},
            "required_patches": {
                "11.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock"],
                "12.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock", "BlueToolFixup"],
                "13.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock", "BlueToolFixup", "CryptexFixup"],
                "14.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock", "BlueToolFixup", "CryptexFixup"]
            },
            "graphics_patches": ["Intel5000Controller"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["BrcmPatchRAM3", "BrcmFirmwareData"],
            "secure_boot_model": "j78", "sip_requirements": "disabled",
            "notes": ["Broadwell integrated graphics only", "4K display", "Good OCLP support"]
        },
        
        "iMac16,2": {
            "name": "iMac 21.5\" (Late 2015)", "year": 2015, "cpu_family": "Intel Core i5/i7 (Broadwell)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.11": True, "10.12": True, "10.13": True, "10.14": True, "10.15": True, "11.0": False, "12.0": False, "13.0": False, "14.0": False},
            "required_patches": {
                "11.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock"],
                "12.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock", "BlueToolFixup"],
                "13.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock", "BlueToolFixup", "CryptexFixup"],
                "14.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock", "BlueToolFixup", "CryptexFixup"]
            },
            "graphics_patches": ["Intel5000Controller", "AMDRadeonX4000"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["BrcmPatchRAM3", "BrcmFirmwareData"],
            "secure_boot_model": "j78", "sip_requirements": "disabled",
            "notes": ["Dual GPU option", "AMD R9 M380", "dGPU switching possible"]
        },
        
        "iMac17,1": {
            "name": "iMac 27\" (Late 2015)", "year": 2015, "cpu_family": "Intel Core i5/i7 (Skylake)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.11": True, "10.12": True, "10.13": True, "10.14": True, "10.15": True, "11.0": False, "12.0": False, "13.0": False, "14.0": False},
            "required_patches": {
                "11.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock"],
                "12.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock", "BlueToolFixup"],
                "13.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock", "BlueToolFixup", "CryptexFixup"],
                "14.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock", "BlueToolFixup", "CryptexFixup"]
            },
            "graphics_patches": ["IntelSkylakeGraphics", "AMDRadeonX4000"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["BrcmPatchRAM3", "BrcmFirmwareData"],
            "secure_boot_model": "j95", "sip_requirements": "disabled",
            "notes": ["5K Retina display", "AMD R9 M380/M390/M395", "Excellent OCLP compatibility"]
        },
        
        "iMac18,1": {
            "name": "iMac 21.5\" (Mid 2017)", "year": 2017, "cpu_family": "Intel Core i5 (Kaby Lake)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.12": True, "10.13": True, "10.14": True, "10.15": True, "11.0": True, "12.0": True, "13.0": False, "14.0": False},
            "required_patches": {
                "13.0": ["AMFIPass", "RestrictEvents"],
                "14.0": ["AMFIPass", "RestrictEvents", "CryptexFixup"]
            },
            "graphics_patches": ["IntelKabyLakeGraphics"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["AirportBrcmFixup", "BrcmPatchRAM3"],
            "secure_boot_model": "j78", "sip_requirements": "disabled",
            "notes": ["Kaby Lake integrated graphics", "4K display", "Strong OCLP support"]
        },
        
        "iMac18,2": {
            "name": "iMac 21.5\" (Mid 2017)", "year": 2017, "cpu_family": "Intel Core i5/i7 (Kaby Lake)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.12": True, "10.13": True, "10.14": True, "10.15": True, "11.0": True, "12.0": True, "13.0": False, "14.0": False},
            "required_patches": {
                "13.0": ["AMFIPass", "RestrictEvents"],
                "14.0": ["AMFIPass", "RestrictEvents", "CryptexFixup"]
            },
            "graphics_patches": ["IntelKabyLakeGraphics", "AMDRadeonX5000"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["AirportBrcmFixup", "BrcmPatchRAM3"],
            "secure_boot_model": "j78", "sip_requirements": "disabled",
            "notes": ["Dual GPU option", "AMD Radeon Pro 555/560", "4K display"]
        },
        
        "iMac18,3": {
            "name": "iMac 27\" (Mid 2017)", "year": 2017, "cpu_family": "Intel Core i5/i7 (Kaby Lake)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.12": True, "10.13": True, "10.14": True, "10.15": True, "11.0": True, "12.0": True, "13.0": False, "14.0": False},
            "required_patches": {
                "13.0": ["AMFIPass", "RestrictEvents"],
                "14.0": ["AMFIPass", "RestrictEvents", "CryptexFixup"]
            },
            "graphics_patches": ["IntelKabyLakeGraphics", "AMDRadeonX5000"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["AirportBrcmFixup", "BrcmPatchRAM3"],
            "secure_boot_model": "j95", "sip_requirements": "disabled",
            "notes": ["5K Retina display", "AMD Radeon Pro 570/575/580", "Excellent performance"]
        },
        
        "iMac19,1": {
            "name": "iMac 27\" (Mid 2019)", "year": 2019, "cpu_family": "Intel Core i5/i9 (Coffee Lake)",
            "architecture": "x86_64", "oclp_compatibility": "partially_supported",
            "native_macos_support": {"10.14": True, "10.15": True, "11.0": True, "12.0": True, "13.0": False, "14.0": False},
            "required_patches": {
                "13.0": ["AMFIPass", "RestrictEvents", "TeraScale2Support"],
                "14.0": ["AMFIPass", "RestrictEvents", "TeraScale2Support", "CryptexFixup"]
            },
            "graphics_patches": ["IntelCoffeeLakeGraphics", "AMDRadeonX6000"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["AirportBrcmFixup", "BrcmPatchRAM3"],
            "secure_boot_model": "j95", "sip_requirements": "disabled",
            "notes": ["5K Retina display", "AMD Radeon Pro 570X/575X/580X/Vega 48", "Some GPU acceleration issues"]
        },
        
        "iMac19,2": {
            "name": "iMac 21.5\" (Mid 2019)", "year": 2019, "cpu_family": "Intel Core i3/i5/i7 (Coffee Lake)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.14": True, "10.15": True, "11.0": True, "12.0": True, "13.0": False, "14.0": False},
            "required_patches": {
                "13.0": ["AMFIPass", "RestrictEvents"],
                "14.0": ["AMFIPass", "RestrictEvents", "CryptexFixup"]
            },
            "graphics_patches": ["IntelCoffeeLakeGraphics", "AMDRadeonX6000"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["AirportBrcmFixup", "BrcmPatchRAM3"],
            "secure_boot_model": "j78", "sip_requirements": "disabled",
            "notes": ["4K display", "AMD Radeon Pro 555X/560X", "Good OCLP compatibility"]
        },
        
        "iMac20,1": {
            "name": "iMac 27\" (Mid 2020)", "year": 2020, "cpu_family": "Intel Core i5/i7/i9 (Comet Lake)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.15": True, "11.0": True, "12.0": True, "13.0": True, "14.0": False},
            "required_patches": {
                "14.0": ["AMFIPass", "RestrictEvents"]
            },
            "graphics_patches": ["IntelCometLakeGraphics", "AMDRadeonX6000"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["AirportBrcmFixup", "BrcmPatchRAM3"],
            "secure_boot_model": "j185", "sip_requirements": "disabled",
            "notes": ["5K Retina display", "AMD Radeon Pro 5300/5500 XT/5700/5700 XT", "Latest Intel iMac", "Excellent OCLP support"]
        },
        
        "iMac20,2": {
            "name": "iMac 27\" (Mid 2020)", "year": 2020, "cpu_family": "Intel Core i7/i9 (Comet Lake)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.15": True, "11.0": True, "12.0": True, "13.0": True, "14.0": False},
            "required_patches": {
                "14.0": ["AMFIPass", "RestrictEvents"]
            },
            "graphics_patches": ["IntelCometLakeGraphics", "AMDRadeonX6000"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["AirportBrcmFixup", "BrcmPatchRAM3"],
            "secure_boot_model": "j185f", "sip_requirements": "disabled",
            "notes": ["High-end configuration", "10-core processor option", "Best Intel iMac for OCLP"]
        },
        
        # iMac Pro (2017)
        "iMacPro1,1": {
            "name": "iMac Pro (2017)", "year": 2017, "cpu_family": "Intel Xeon W (Skylake-X)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.13": True, "10.14": True, "10.15": True, "11.0": True, "12.0": True, "13.0": True, "14.0": False},
            "required_patches": {
                "14.0": ["AMFIPass", "RestrictEvents"]
            },
            "graphics_patches": ["AMDRadeonX6000"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["AirportBrcmFixup", "BrcmPatchRAM3"],
            "secure_boot_model": "j137", "sip_requirements": "disabled",
            "notes": ["Professional workstation", "AMD Radeon Pro Vega 56/64", "T2 Security Chip", "Excellent OCLP support", "Space Gray design"]
        },
        
        # Mac Pro (2019)
        "MacPro7,1": {
            "name": "Mac Pro (2019)", "year": 2019, "cpu_family": "Intel Xeon W (Cascade Lake)",
            "architecture": "x86_64", "oclp_compatibility": "unsupported",
            "native_macos_support": {"10.15": True, "11.0": True, "12.0": True, "13.0": True, "14.0": True, "15.0": True},
            "required_patches": {},
            "graphics_patches": [],
            "audio_patches": [],
            "wifi_bluetooth_patches": [],
            "secure_boot_model": "j160", "sip_requirements": "enabled",
            "notes": ["Modern Mac Pro", "Native macOS support", "OCLP not required", "T2 Security Chip", "Modular design"]
        },
        
        # Mac mini (2014-2020)
        "Macmini7,1": {
            "name": "Mac mini (Late 2014)", "year": 2014, "cpu_family": "Intel Core i5/i7 (Haswell)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.10": True, "10.11": True, "10.12": True, "10.13": True, "10.14": True, "10.15": True, "11.0": False, "12.0": False, "13.0": False, "14.0": False},
            "required_patches": {
                "11.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock"],
                "12.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock", "BlueToolFixup"],
                "13.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock", "BlueToolFixup", "CryptexFixup"],
                "14.0": ["AMFIPass", "RestrictEvents", "FeatureUnlock", "BlueToolFixup", "CryptexFixup"]
            },
            "graphics_patches": ["IntelHD5000"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["BrcmPatchRAM3", "BrcmFirmwareData"],
            "secure_boot_model": "j64", "sip_requirements": "disabled",
            "notes": ["Last Haswell Mac mini", "Integrated graphics only", "Good OCLP support", "Compact design"]
        },
        
        "Macmini8,1": {
            "name": "Mac mini (Late 2018)", "year": 2018, "cpu_family": "Intel Core i3/i5/i7 (Coffee Lake)",
            "architecture": "x86_64", "oclp_compatibility": "fully_supported",
            "native_macos_support": {"10.14": True, "10.15": True, "11.0": True, "12.0": True, "13.0": True, "14.0": False},
            "required_patches": {
                "14.0": ["AMFIPass", "RestrictEvents"]
            },
            "graphics_patches": ["IntelCoffeeLakeGraphics"],
            "audio_patches": ["AppleALC"],
            "wifi_bluetooth_patches": ["AirportBrcmFixup", "BrcmPatchRAM3"],
            "secure_boot_model": "j174", "sip_requirements": "disabled",
            "notes": ["T2 Security Chip", "Space Gray design", "4 Thunderbolt 3 ports", "Excellent OCLP support"]
        },
        
        # ===== Apple Silicon Macs (2020+) - No OCLP Support Needed =====
        
        # MacBook Air M1/M2
        "MacBookAir10,1": {
            "name": "MacBook Air M1 (Late 2020)", "year": 2020, "cpu_family": "Apple M1",
            "architecture": "arm64", "oclp_compatibility": "unsupported",
            "native_macos_support": {"11.0": True, "12.0": True, "13.0": True, "14.0": True, "15.0": True},
            "required_patches": {},
            "graphics_patches": [], "audio_patches": [], "wifi_bluetooth_patches": [],
            "notes": ["Apple Silicon", "Native macOS support", "OCLP not required", "Fanless design"]
        },
        
        "Mac14,2": {
            "name": "MacBook Air M2 (Mid 2022)", "year": 2022, "cpu_family": "Apple M2",
            "architecture": "arm64", "oclp_compatibility": "unsupported",
            "native_macos_support": {"12.0": True, "13.0": True, "14.0": True, "15.0": True},
            "required_patches": {},
            "graphics_patches": [], "audio_patches": [], "wifi_bluetooth_patches": [],
            "notes": ["Apple Silicon M2", "Native macOS support", "Redesigned chassis", "MagSafe charging"]
        },
        
        "Mac15,12": {
            "name": "MacBook Air M3 (Mid 2024)", "year": 2024, "cpu_family": "Apple M3",
            "architecture": "arm64", "oclp_compatibility": "unsupported",
            "native_macos_support": {"14.0": True, "15.0": True},
            "required_patches": {},
            "graphics_patches": [], "audio_patches": [], "wifi_bluetooth_patches": [],
            "notes": ["Latest Apple Silicon", "Native macOS support", "M3 performance", "Midnight color option"]
        },
        
        # MacBook Pro M1/M2/M3
        "MacBookPro17,1": {
            "name": "MacBook Pro 13\" M1 (Late 2020)", "year": 2020, "cpu_family": "Apple M1",
            "architecture": "arm64", "oclp_compatibility": "unsupported",
            "native_macos_support": {"11.0": True, "12.0": True, "13.0": True, "14.0": True, "15.0": True},
            "required_patches": {},
            "graphics_patches": [], "audio_patches": [], "wifi_bluetooth_patches": [],
            "notes": ["Apple Silicon", "Native macOS support", "TouchBar model", "Excellent performance"]
        },
        
        "MacBookPro18,1": {
            "name": "MacBook Pro 14\" M1 Pro (Late 2021)", "year": 2021, "cpu_family": "Apple M1 Pro",
            "architecture": "arm64", "oclp_compatibility": "unsupported",
            "native_macos_support": {"12.0": True, "13.0": True, "14.0": True, "15.0": True},
            "required_patches": {},
            "graphics_patches": [], "audio_patches": [], "wifi_bluetooth_patches": [],
            "notes": ["Apple Silicon Pro", "Native macOS support", "Mini-LED display", "MagSafe 3", "ProMotion"]
        },
        
        "MacBookPro18,2": {
            "name": "MacBook Pro 16\" M1 Pro (Late 2021)", "year": 2021, "cpu_family": "Apple M1 Pro",
            "architecture": "arm64", "oclp_compatibility": "unsupported", 
            "native_macos_support": {"12.0": True, "13.0": True, "14.0": True, "15.0": True},
            "required_patches": {},
            "graphics_patches": [], "audio_patches": [], "wifi_bluetooth_patches": [],
            "notes": ["Apple Silicon Pro", "16-inch display", "120Hz ProMotion", "Excellent for development"]
        },
        
        "MacBookPro18,3": {
            "name": "MacBook Pro 14\" M1 Max (Late 2021)", "year": 2021, "cpu_family": "Apple M1 Max",
            "architecture": "arm64", "oclp_compatibility": "unsupported",
            "native_macos_support": {"12.0": True, "13.0": True, "14.0": True, "15.0": True},
            "required_patches": {},
            "graphics_patches": [], "audio_patches": [], "wifi_bluetooth_patches": [],
            "notes": ["Apple Silicon Max", "High-end configuration", "32-core GPU option", "64GB RAM support"]
        },
        
        "MacBookPro18,4": {
            "name": "MacBook Pro 16\" M1 Max (Late 2021)", "year": 2021, "cpu_family": "Apple M1 Max",
            "architecture": "arm64", "oclp_compatibility": "unsupported",
            "native_macos_support": {"12.0": True, "13.0": True, "14.0": True, "15.0": True},
            "required_patches": {},
            "graphics_patches": [], "audio_patches": [], "wifi_bluetooth_patches": [],
            "notes": ["Apple Silicon Max", "Professional workstation", "32-core GPU", "64GB RAM support"]
        },
        
        # iMac M1/M3
        "iMac21,1": {
            "name": "iMac 24\" M1 (Mid 2021)", "year": 2021, "cpu_family": "Apple M1",
            "architecture": "arm64", "oclp_compatibility": "unsupported",
            "native_macos_support": {"11.0": True, "12.0": True, "13.0": True, "14.0": True, "15.0": True},
            "required_patches": {},
            "graphics_patches": [], "audio_patches": [], "wifi_bluetooth_patches": [],
            "notes": ["Apple Silicon", "24-inch 4.5K display", "Colorful design", "Thin profile", "Magic Keyboard with Touch ID"]
        },
        
        "iMac21,2": {
            "name": "iMac 24\" M1 (Mid 2021)", "year": 2021, "cpu_family": "Apple M1",
            "architecture": "arm64", "oclp_compatibility": "unsupported",
            "native_macos_support": {"11.0": True, "12.0": True, "13.0": True, "14.0": True, "15.0": True},
            "required_patches": {},
            "graphics_patches": [], "audio_patches": [], "wifi_bluetooth_patches": [],
            "notes": ["Apple Silicon", "Higher-end M1 configuration", "8-core GPU", "Ethernet option"]
        },
        
        # Mac mini M1/M2
        "Macmini9,1": {
            "name": "Mac mini M1 (Late 2020)", "year": 2020, "cpu_family": "Apple M1",
            "architecture": "arm64", "oclp_compatibility": "unsupported",
            "native_macos_support": {"11.0": True, "12.0": True, "13.0": True, "14.0": True, "15.0": True},
            "required_patches": {},
            "graphics_patches": [], "audio_patches": [], "wifi_bluetooth_patches": [],
            "notes": ["Apple Silicon", "Compact design", "Native macOS support", "Excellent value"]
        },
        
        "Mac14,3": {
            "name": "Mac mini M2 (Early 2023)", "year": 2023, "cpu_family": "Apple M2",
            "architecture": "arm64", "oclp_compatibility": "unsupported",
            "native_macos_support": {"13.0": True, "14.0": True, "15.0": True},
            "required_patches": {},
            "graphics_patches": [], "audio_patches": [], "wifi_bluetooth_patches": [],
            "notes": ["Apple Silicon M2", "Updated design", "M2 Pro option available"]
        },
        
        # Mac Studio M1/M2
        "MacStudio1,1": {
            "name": "Mac Studio M1 Max (Early 2022)", "year": 2022, "cpu_family": "Apple M1 Max",
            "architecture": "arm64", "oclp_compatibility": "unsupported",
            "native_macos_support": {"12.0": True, "13.0": True, "14.0": True, "15.0": True},
            "required_patches": {},
            "graphics_patches": [], "audio_patches": [], "wifi_bluetooth_patches": [],
            "notes": ["Apple Silicon Max", "Professional desktop", "Compact workstation", "Excellent connectivity"]
        },
        
        "MacStudio1,2": {
            "name": "Mac Studio M1 Ultra (Early 2022)", "year": 2022, "cpu_family": "Apple M1 Ultra",
            "architecture": "arm64", "oclp_compatibility": "unsupported",
            "native_macos_support": {"12.0": True, "13.0": True, "14.0": True, "15.0": True},
            "required_patches": {},
            "graphics_patches": [], "audio_patches": [], "wifi_bluetooth_patches": [],
            "notes": ["Apple Silicon Ultra", "Dual M1 Max", "128GB RAM support", "Ultimate performance"]
        }
    }
    
    return mac_models


def get_enhanced_mac_profiles() -> List[HardwareProfile]:
    """
    Get enhanced Mac hardware profiles with comprehensive specifications and patch requirements.
    
    Returns a list of HardwareProfile objects for all supported Mac models,
    including detailed OCLP compatibility, patch requirements, and hardware specifications.
    """
    profiles = []
    mac_models = get_mac_model_data()
    
    for model_id, model_data in mac_models.items():
        # Create enhanced HardwareProfile with all the new fields
        profile = HardwareProfile(
            name=model_data["name"],
            platform="mac",
            model=model_id,
            architecture=model_data["architecture"],
            year=model_data.get("year"),
            cpu_family=model_data.get("cpu_family"),
            
            # Enhanced Mac-specific fields
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
        
        profiles.append(profile)
    
    return profiles


def get_default_profiles() -> List[HardwareProfile]:
    """Get default hardware profiles for common devices including enhanced Mac models"""
    profiles = []
    
    # Get comprehensive Mac profiles
    profiles.extend(get_enhanced_mac_profiles())
    
    # Windows profiles
    profiles.extend([
        HardwareProfile(
            name="Generic x64 PC",
            platform="windows",
            model="generic_x64",
            architecture="x86_64",
            cpu_family="Generic Intel/AMD"
        ),
        HardwareProfile(
            name="Surface Pro Series",
            platform="windows", 
            model="surface_pro",
            architecture="x86_64",
            cpu_family="Intel Core",
            special_requirements={"secure_boot": True, "surface_drivers": True}
        ),
        HardwareProfile(
            name="Dell OptiPlex Series",
            platform="windows",
            model="dell_optiplex",
            architecture="x86_64", 
            cpu_family="Intel Core",
            driver_packages=["intel_management_engine", "dell_command_update"]
        ),
        HardwareProfile(
            name="Lenovo ThinkPad Series",
            platform="windows",
            model="thinkpad",
            architecture="x86_64",
            cpu_family="Intel Core",
            driver_packages=["lenovo_vantage", "thinkpad_drivers"]
        )
    ])
    
    # Linux profiles
    profiles.extend([
        HardwareProfile(
            name="Generic Linux x86_64",
            platform="linux",
            model="generic_linux_x64",
            architecture="x86_64",
            cpu_family="Generic Intel/AMD"
        ),
        HardwareProfile(
            name="Raspberry Pi 4",
            platform="linux",
            model="rpi4",
            architecture="arm64",
            cpu_family="Broadcom BCM2711",
            special_requirements={"boot_partition": "fat32", "gpu_memory_split": 64}
        ),
        HardwareProfile(
            name="Framework Laptop",
            platform="linux",
            model="framework_laptop",
            architecture="x86_64",
            cpu_family="Intel Core/AMD Ryzen",
            special_requirements={"modular_ports": True}
        )
    ])
    
    return profiles


def from_mac_model(model: str) -> HardwareProfile:
    """Create hardware profile from Mac model identifier using comprehensive database"""
    mac_models = get_mac_model_data()
    
    if model in mac_models:
        model_data = mac_models[model]
        return HardwareProfile(
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
        return HardwareProfile(
            name=f"Unknown Mac ({model})",
            platform="mac",
            model=model,
            architecture="x86_64",  # Default assumption
            oclp_compatibility="unknown",
            notes=[f"Unknown Mac model: {model}"]
        )


def get_profiles_by_platform(platform: str) -> List[HardwareProfile]:
    """Get hardware profiles filtered by platform"""
    all_profiles = get_default_profiles()
    return [profile for profile in all_profiles if profile.platform == platform]


def get_mac_profiles_by_oclp_compatibility(compatibility: str) -> List[HardwareProfile]:
    """
    Get Mac profiles filtered by OCLP compatibility level.
    
    Args:
        compatibility: "fully_supported", "partially_supported", "experimental", "unsupported"
    """
    mac_profiles = get_enhanced_mac_profiles()
    return [profile for profile in mac_profiles if profile.oclp_compatibility == compatibility]


def get_mac_profiles_by_macos_version(macos_version: str, native_only: bool = False) -> List[HardwareProfile]:
    """
    Get Mac profiles that support a specific macOS version.
    
    Args:
        macos_version: macOS version like "14.0", "13.0", etc.
        native_only: If True, only return profiles with native support
    """
    mac_profiles = get_enhanced_mac_profiles()
    compatible_profiles = []
    
    for profile in mac_profiles:
        if native_only:
            # Only include if natively supported
            if profile.native_macos_support.get(macos_version, False):
                compatible_profiles.append(profile)
        else:
            # Include if natively supported OR has patches available
            if (profile.native_macos_support.get(macos_version, False) or 
                macos_version in profile.required_patches):
                compatible_profiles.append(profile)
    
    return compatible_profiles


def get_compatible_profiles(deployment_type: DeploymentType) -> List[HardwareProfile]:
    """Get hardware profiles compatible with specific deployment type"""
    all_profiles = get_default_profiles()
    
    if deployment_type == DeploymentType.MACOS_OCLP:
        # Return only Mac profiles that support OCLP (exclude unsupported ones)
        mac_profiles = [profile for profile in all_profiles if profile.platform == "mac"]
        return [profile for profile in mac_profiles 
                if getattr(profile, 'oclp_compatibility', None) != 'unsupported']
    elif deployment_type == DeploymentType.WINDOWS_UNATTENDED:
        # Return Windows and generic profiles
        return [profile for profile in all_profiles if profile.platform in ["windows", "generic"]]
    elif deployment_type == DeploymentType.LINUX_AUTOMATED:
        # Return Linux profiles
        return [profile for profile in all_profiles if profile.platform == "linux"]
    else:
        # Custom payload can work on any platform
        return all_profiles


def get_patch_requirements_for_model(model: str, macos_version: str) -> Dict[str, List[str]]:
    """
    Get specific patch requirements for a Mac model and macOS version.
    
    Args:
        model: Mac model identifier (e.g., "iMacPro1,1")
        macos_version: macOS version (e.g., "14.0")
        
    Returns:
        Dictionary with patch categories and required patches
    """
    mac_models = get_mac_model_data()
    
    if model not in mac_models:
        return {}
    
    model_data = mac_models[model]
    
    # Check if native support exists
    if model_data.get("native_macos_support", {}).get(macos_version, False):
        return {"note": ["This model has native macOS support for this version"]}
    
    # Get required patches for this version
    required_patches = model_data.get("required_patches", {}).get(macos_version, [])
    
    if not required_patches:
        return {"note": ["No patches available for this macOS version"]}
    
    return {
        "required_patches": required_patches,
        "graphics_patches": model_data.get("graphics_patches", []),
        "audio_patches": model_data.get("audio_patches", []),
        "wifi_bluetooth_patches": model_data.get("wifi_bluetooth_patches", []),
        "usb_patches": model_data.get("usb_patches", []),
        "sip_requirements": [model_data.get("sip_requirements", "")] if model_data.get("sip_requirements") else [],
        "secure_boot_model": [model_data.get("secure_boot_model", "")] if model_data.get("secure_boot_model") else [],
        "notes": model_data.get("notes", [])
    }


def get_macos_compatibility_matrix() -> Dict[str, Dict[str, str]]:
    """
    Get macOS compatibility matrix showing native support vs OCLP requirements.
    
    Returns:
        Dictionary mapping Mac models to macOS versions and their support status
    """
    compatibility_matrix = {}
    mac_models = get_mac_model_data()
    
    # Define macOS versions to check
    macos_versions = ["10.15", "11.0", "12.0", "13.0", "14.0", "15.0"]
    
    for model_id, model_data in mac_models.items():
        model_name = model_data["name"]
        compatibility_matrix[model_name] = {}
        
        for version in macos_versions:
            if model_data.get("native_macos_support", {}).get(version, False):
                compatibility_matrix[model_name][version] = "native"
            elif version in model_data.get("required_patches", {}):
                if model_data.get("oclp_compatibility") == "fully_supported":
                    compatibility_matrix[model_name][version] = "oclp_full"
                elif model_data.get("oclp_compatibility") == "partially_supported":
                    compatibility_matrix[model_name][version] = "oclp_partial"
                else:
                    compatibility_matrix[model_name][version] = "oclp_experimental"
            else:
                compatibility_matrix[model_name][version] = "unsupported"
    
    return compatibility_matrix


def get_hardware_specific_recommendations(model: str, target_macos_version: str) -> Dict[str, Any]:
    """
    Get intelligent hardware-specific recommendations for a Mac model and macOS version.
    
    Args:
        model: Mac model identifier (e.g., "iMacPro1,1")
        target_macos_version: Target macOS version (e.g., "14.0")
        
    Returns:
        Dictionary with comprehensive recommendations including:
        - Required actions
        - Patch recommendations
        - Compatibility warnings
        - Performance expectations
        - Troubleshooting tips
    """
    mac_models = get_mac_model_data()
    
    if model not in mac_models:
        return {
            "status": "unknown_model",
            "message": f"Unknown Mac model: {model}",
            "recommendations": [],
            "warnings": ["Model not found in database"],
            "compatibility": "unknown"
        }
    
    model_data = mac_models[model]
    recommendations = {
        "model_name": model_data["name"],
        "target_macos": target_macos_version,
        "status": "unknown",
        "message": "",
        "recommendations": [],
        "warnings": [],
        "patches_required": [],
        "compatibility": model_data.get("oclp_compatibility", "unknown"),
        "performance_notes": [],
        "troubleshooting_tips": []
    }
    
    # Check native macOS support
    native_support = model_data.get("native_macos_support", {}).get(target_macos_version, False)
    
    if native_support:
        recommendations.update({
            "status": "native_support",
            "message": f"{model_data['name']} has native support for macOS {target_macos_version}",
            "recommendations": [
                "No patches required",
                "Standard macOS installation supported",
                "All hardware features should work out-of-the-box"
            ],
            "performance_notes": ["Expected to run at full performance", "All hardware acceleration available"]
        })
        return recommendations
    
    # Check OCLP compatibility
    oclp_compatibility = model_data.get("oclp_compatibility")
    required_patches = model_data.get("required_patches", {}).get(target_macos_version, [])
    
    if oclp_compatibility == "unsupported":
        recommendations.update({
            "status": "unsupported",
            "message": f"{model_data['name']} is not supported for macOS {target_macos_version}",
            "warnings": [
                "This Mac model cannot run the target macOS version",
                "Consider using a supported macOS version instead",
                "Modern Apple Silicon Macs don't need OCLP"
            ]
        })
        return recommendations
    
    if not required_patches:
        recommendations.update({
            "status": "no_patches_available",
            "message": f"No OCLP patches available for {model_data['name']} on macOS {target_macos_version}",
            "warnings": [
                "Target macOS version may not be supported",
                "Check for newer OCLP versions",
                "Consider using a different macOS version"
            ]
        })
        return recommendations
    
    # Generate detailed recommendations based on compatibility level
    if oclp_compatibility == "fully_supported":
        recommendations.update({
            "status": "oclp_fully_supported",
            "message": f"{model_data['name']} is fully supported with OCLP for macOS {target_macos_version}",
            "recommendations": [
                "Use OpenCore Legacy Patcher for installation",
                "All major hardware features should work",
                "Stable experience expected"
            ],
            "performance_notes": [
                "Near-native performance expected",
                "Hardware acceleration should work",
                "Most features fully functional"
            ]
        })
    
    elif oclp_compatibility == "partially_supported":
        recommendations.update({
            "status": "oclp_partial_support",
            "message": f"{model_data['name']} has partial OCLP support for macOS {target_macos_version}",
            "recommendations": [
                "Use OpenCore Legacy Patcher with caution",
                "Some hardware features may not work",
                "Test thoroughly before daily use"
            ],
            "warnings": [
                "Some features may be missing or unstable",
                "Graphics acceleration might be limited",
                "Check compatibility notes carefully"
            ],
            "performance_notes": [
                "Performance may be reduced",
                "Some hardware acceleration may be unavailable"
            ]
        })
    
    elif oclp_compatibility == "experimental":
        recommendations.update({
            "status": "oclp_experimental",
            "message": f"{model_data['name']} has experimental OCLP support for macOS {target_macos_version}",
            "recommendations": [
                "Use at your own risk",
                "Backup your system before attempting",
                "Consider using a test machine first"
            ],
            "warnings": [
                "Experimental support - stability not guaranteed",
                "May have significant issues or missing features",
                "Not recommended for production use",
                "Frequent crashes or hardware malfunctions possible"
            ],
            "performance_notes": [
                "Performance likely to be degraded",
                "Hardware acceleration probably unavailable"
            ]
        })
    
    # Add specific patch recommendations
    recommendations["patches_required"] = required_patches
    
    # Graphics-specific recommendations
    graphics_patches = model_data.get("graphics_patches", [])
    if graphics_patches:
        recommendations["recommendations"].extend([
            f"Graphics patches required: {', '.join(graphics_patches)}",
            "Graphics performance may be affected"
        ])
        if "Intel" in str(graphics_patches):
            recommendations["troubleshooting_tips"].append(
                "If experiencing graphics issues, try disabling hardware acceleration in problematic apps"
            )
        if "AMD" in str(graphics_patches):
            recommendations["troubleshooting_tips"].append(
                "AMD graphics may require specific kext loading order"
            )
    
    # Audio-specific recommendations
    audio_patches = model_data.get("audio_patches", [])
    if audio_patches:
        recommendations["recommendations"].append(
            f"Audio patches required: {', '.join(audio_patches)}"
        )
        recommendations["troubleshooting_tips"].append(
            "If audio issues occur, check Audio MIDI Setup for correct output devices"
        )
    
    # WiFi/Bluetooth recommendations
    wifi_bluetooth_patches = model_data.get("wifi_bluetooth_patches", [])
    if wifi_bluetooth_patches:
        recommendations["recommendations"].extend([
            f"WiFi/Bluetooth patches required: {', '.join(wifi_bluetooth_patches)}",
            "Network functionality may require additional setup"
        ])
        recommendations["troubleshooting_tips"].extend([
            "Reset NVRAM if WiFi/Bluetooth issues persist",
            "Some Bluetooth devices may require re-pairing after OCLP installation"
        ])
    
    # USB-specific recommendations
    usb_patches = model_data.get("usb_patches", [])
    if usb_patches:
        recommendations["recommendations"].append(
            f"USB patches required: {', '.join(usb_patches)}"
        )
        recommendations["troubleshooting_tips"].append(
            "Map USB ports properly if experiencing USB device issues"
        )
    
    # SIP and security recommendations
    if model_data.get("sip_requirements") == "disabled":
        recommendations["recommendations"].extend([
            "System Integrity Protection (SIP) must be disabled",
            "SecureBootModel configuration required"
        ])
        recommendations["warnings"].append(
            "Disabling SIP reduces system security - understand the implications"
        )
    
    # Add model-specific notes
    model_notes = model_data.get("notes", [])
    if model_notes:
        recommendations["performance_notes"].extend(model_notes)
    
    # Version-specific recommendations
    if target_macos_version == "14.0":
        recommendations["recommendations"].append(
            "macOS Sonoma requires latest OCLP version for best compatibility"
        )
        recommendations["troubleshooting_tips"].append(
            "If login screen issues occur, try safe mode boot first"
        )
    
    elif target_macos_version == "13.0":
        recommendations["recommendations"].append(
            "macOS Ventura has excellent OCLP compatibility for most supported models"
        )
    
    elif target_macos_version in ["11.0", "12.0"]:
        recommendations["recommendations"].append(
            "Older macOS versions typically have better compatibility"
        )
    
    return recommendations


def get_optimal_macos_version_recommendation(model: str) -> Dict[str, Any]:
    """
    Get the optimal macOS version recommendation for a specific Mac model.
    
    Args:
        model: Mac model identifier
        
    Returns:
        Dictionary with optimal version recommendation and reasoning
    """
    mac_models = get_mac_model_data()
    
    if model not in mac_models:
        return {
            "status": "error",
            "message": f"Unknown Mac model: {model}"
        }
    
    model_data = mac_models[model]
    native_support = model_data.get("native_macos_support", {})
    oclp_compatibility = model_data.get("oclp_compatibility")
    
    # Find the highest natively supported version
    highest_native = None
    for version in ["15.0", "14.0", "13.0", "12.0", "11.0", "10.15", "10.14"]:
        if native_support.get(version, False):
            highest_native = version
            break
    
    # Find the highest OCLP-supported version
    highest_oclp = None
    required_patches = model_data.get("required_patches", {})
    for version in ["14.0", "13.0", "12.0", "11.0"]:
        if version in required_patches and oclp_compatibility in ["fully_supported", "partially_supported"]:
            highest_oclp = version
            break
    
    recommendation = {
        "model_name": model_data["name"],
        "optimal_version": None,
        "reasoning": [],
        "alternatives": [],
        "oclp_required": False
    }
    
    if highest_native:
        recommendation.update({
            "optimal_version": highest_native,
            "reasoning": [
                f"Native support available for macOS {highest_native}",
                "No patches or modifications required",
                "Optimal performance and stability",
                "All hardware features supported"
            ],
            "oclp_required": False
        })
        
        # Add OCLP alternatives if available
        if highest_oclp and highest_oclp > highest_native:
            recommendation["alternatives"].append({
                "version": highest_oclp,
                "method": "OCLP",
                "description": f"Newer macOS {highest_oclp} available with OCLP",
                "trade_offs": ["Requires patches", "May have some limitations", "Less stable than native"]
            })
    
    elif highest_oclp:
        recommendation.update({
            "optimal_version": highest_oclp,
            "reasoning": [
                f"OCLP support available for macOS {highest_oclp}",
                f"Compatibility level: {oclp_compatibility}",
                "Patches required for installation"
            ],
            "oclp_required": True
        })
        
        if oclp_compatibility == "partially_supported":
            recommendation["reasoning"].append("Some features may have limitations")
        elif oclp_compatibility == "experimental":
            recommendation["reasoning"].extend([
                "Experimental support - use with caution",
                "Consider using older macOS version for better stability"
            ])
    
    else:
        recommendation.update({
            "optimal_version": "unsupported",
            "reasoning": [
                "No supported macOS versions found",
                "This model may be too old or too new for OCLP",
                "Stick with originally supported macOS version"
            ]
        })
    
    return recommendation


# ===== PATCH PIPELINE INTEGRATION =====

def create_mac_patch_sets() -> List[PatchSet]:
    """Convert Mac model data into PatchSet format for patch pipeline"""
    logger = logging.getLogger(__name__)
    patch_sets = []
    
    try:
        mac_data = get_mac_model_data()
        
        # Group models by similar patch requirements
        patch_groups = _group_models_by_patches(mac_data)
        
        for group_name, models in patch_groups.items():
            # Create patch set for this group
            patch_set = _create_patch_set_for_group(group_name, models)
            if patch_set:
                patch_sets.append(patch_set)
                logger.debug(f"Created patch set: {patch_set.id}")
        
        logger.info(f"Created {len(patch_sets)} Mac patch sets")
        return patch_sets
        
    except Exception as e:
        logger.error(f"Failed to create Mac patch sets: {e}")
        return []


def _group_models_by_patches(mac_data: Dict[str, Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group Mac models with similar patch requirements"""
    groups = {}
    
    for model_id, model_data in mac_data.items():
        # Create a signature based on patch requirements
        patch_signature = _create_patch_signature(model_data)
        
        if patch_signature not in groups:
            groups[patch_signature] = []
        
        # Add model with ID
        model_data_with_id = model_data.copy()
        model_data_with_id["model_id"] = model_id
        groups[patch_signature].append(model_data_with_id)
    
    return groups


def _create_patch_signature(model_data: Dict[str, Any]) -> str:
    """Create a signature string based on patch requirements"""
    signature_parts = []
    
    # Include major patch categories
    graphics_patches = model_data.get("graphics_patches", [])
    audio_patches = model_data.get("audio_patches", [])
    wifi_patches = model_data.get("wifi_bluetooth_patches", [])
    
    # Create signature from patch types
    if graphics_patches:
        signature_parts.append(f"gfx:{':'.join(sorted(graphics_patches))}")
    if audio_patches:
        signature_parts.append(f"audio:{':'.join(sorted(audio_patches))}")
    if wifi_patches:
        signature_parts.append(f"wifi:{':'.join(sorted(wifi_patches))}")
    
    # Include architecture and year range
    arch = model_data.get("architecture", "unknown")
    year = model_data.get("year", 0)
    year_range = f"{(year // 5) * 5}-{((year // 5) + 1) * 5 - 1}"  # Group by 5-year ranges
    
    signature_parts.extend([f"arch:{arch}", f"year:{year_range}"])
    
    return "|".join(signature_parts)


def _create_patch_set_for_group(group_name: str, models: List[Dict[str, Any]]) -> Optional[PatchSet]:
    """Create a PatchSet for a group of similar models"""
    try:
        if not models:
            return None
        
        # Use first model as representative
        representative = models[0]
        
        # Create patch set ID
        patch_set_id = f"macos_{group_name.replace('|', '_').replace(':', '_')}"
        patch_set_id = re.sub(r'[^a-zA-Z0-9_]', '_', patch_set_id)[:50]  # Sanitize and limit length
        
        # Create patch set name
        model_names = [model.get("name", "Unknown") for model in models[:3]]  # First 3 models
        if len(models) > 3:
            model_names.append(f"and {len(models) - 3} more")
        patch_set_name = f"macOS Patches for {', '.join(model_names)}"
        
        # Create target hardware patterns
        target_hardware = [model["model_id"] for model in models]
        
        # Create patch actions from model data
        actions = []
        actions.extend(_create_graphics_actions(representative))
        actions.extend(_create_audio_actions(representative))
        actions.extend(_create_wifi_actions(representative))
        actions.extend(_create_system_actions(representative))
        
        # Create patch set
        patch_set = PatchSet(
            id=patch_set_id,
            name=patch_set_name,
            description=f"Hardware-specific patches for {len(models)} Mac models",
            version="1.0.0",
            target_os="macos",
            target_versions=_get_supported_macos_versions(models),
            target_hardware=target_hardware,
            actions=actions,
            author="BootForge",
            created_at=1234567890.0  # Placeholder timestamp
        )
        
        return patch_set
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to create patch set for group {group_name}: {e}")
        return None


def _create_graphics_actions(model_data: Dict[str, Any]) -> List[PatchAction]:
    """Create graphics-related patch actions"""
    actions = []
    graphics_patches = model_data.get("graphics_patches", [])
    
    for patch_name in graphics_patches:
        action = PatchAction(
            id=f"graphics_{patch_name.lower()}",
            name=f"Graphics Patch: {patch_name}",
            description=f"Install {patch_name} for graphics compatibility",
            patch_type=PatchType.KEXT_INJECTION,
            phase=PatchPhase.POST_INSTALL,
            priority=PatchPriority.CRITICAL,
            source_files=[f"{patch_name}.kext"],
            target_path="/System/Library/Extensions/",
            reversible=True,
            requires_reboot=True,
            conditions=PatchCondition(
                os_version="1[1-4]\..*",  # macOS 11-14
                required_firmware="UEFI"
            )
        )
        actions.append(action)
    
    return actions


def _create_audio_actions(model_data: Dict[str, Any]) -> List[PatchAction]:
    """Create audio-related patch actions"""
    actions = []
    audio_patches = model_data.get("audio_patches", [])
    
    for patch_name in audio_patches:
        action = PatchAction(
            id=f"audio_{patch_name.lower()}",
            name=f"Audio Patch: {patch_name}",
            description=f"Install {patch_name} for audio functionality",
            patch_type=PatchType.KEXT_INJECTION,
            phase=PatchPhase.POST_INSTALL,
            priority=PatchPriority.HIGH,
            source_files=[f"{patch_name}.kext"],
            target_path="/System/Library/Extensions/",
            reversible=True,
            requires_reboot=True
        )
        actions.append(action)
    
    return actions


def _create_wifi_actions(model_data: Dict[str, Any]) -> List[PatchAction]:
    """Create WiFi/Bluetooth-related patch actions"""
    actions = []
    wifi_patches = model_data.get("wifi_bluetooth_patches", [])
    
    for patch_name in wifi_patches:
        action = PatchAction(
            id=f"wifi_{patch_name.lower()}",
            name=f"WiFi/Bluetooth Patch: {patch_name}",
            description=f"Install {patch_name} for network connectivity",
            patch_type=PatchType.KEXT_INJECTION,
            phase=PatchPhase.POST_INSTALL,
            priority=PatchPriority.HIGH,
            source_files=[f"{patch_name}.kext"],
            target_path="/System/Library/Extensions/",
            reversible=True,
            requires_reboot=True
        )
        actions.append(action)
    
    return actions


def _create_system_actions(model_data: Dict[str, Any]) -> List[PatchAction]:
    """Create system-level patch actions"""
    actions = []
    
    # Get required patches by macOS version
    required_patches = model_data.get("required_patches", {})
    
    for os_version, patch_list in required_patches.items():
        for patch_name in patch_list:
            # Determine patch type based on name
            if "AMFI" in patch_name:
                patch_type = PatchType.KERNEL_PATCH
                priority = PatchPriority.CRITICAL
            elif "Fixup" in patch_name:
                patch_type = PatchType.KEXT_INJECTION
                priority = PatchPriority.HIGH
            else:
                patch_type = PatchType.SYSTEM_FILE
                priority = PatchPriority.MEDIUM
            
            action = PatchAction(
                id=f"system_{patch_name.lower()}_{os_version.replace('.', '_')}",
                name=f"System Patch: {patch_name}",
                description=f"Install {patch_name} for macOS {os_version} compatibility",
                patch_type=patch_type,
                phase=PatchPhase.POST_INSTALL,
                priority=priority,
                source_files=[f"{patch_name}.kext"],
                target_path="/System/Library/Extensions/",
                reversible=True,
                requires_reboot=True,
                conditions=PatchCondition(
                    os_version=os_version.replace(".", r"\.") + r"\..*"
                )
            )
            actions.append(action)
    
    # Add SIP disable action if required
    if model_data.get("sip_requirements") == "disabled":
        sip_action = PatchAction(
            id="disable_sip",
            name="Disable System Integrity Protection",
            description="Disable SIP to allow kernel extensions loading",
            patch_type=PatchType.CONFIG_PATCH,
            phase=PatchPhase.PRE_INSTALL,
            priority=PatchPriority.CRITICAL,
            command="csrutil disable",
            reversible=True,
            requires_reboot=True
        )
        actions.append(sip_action)
    
    return actions


def _get_supported_macos_versions(models: List[Dict[str, Any]]) -> List[str]:
    """Get supported macOS versions for a group of models"""
    all_versions = set()
    
    for model in models:
        # Get versions from native support
        native_support = model.get("native_macos_support", {})
        for version, supported in native_support.items():
            if supported:
                all_versions.add(version)
        
        # Get versions from required patches (OCLP support)
        required_patches = model.get("required_patches", {})
        for version in required_patches.keys():
            all_versions.add(version)
    
    # Convert to patterns
    version_patterns = []
    for version in sorted(all_versions):
        if "." in version:
            # Convert version like "11.0" to pattern "11\..*"
            pattern = version.replace(".", r"\.") + r"\..*"
        else:
            # Single number version
            pattern = f"{version}\..*"
        version_patterns.append(pattern)
    
    return version_patterns


def get_hardware_patch_compatibility(model_id: str) -> Optional[PatchCompatibility]:
    """Get patch compatibility information for a specific Mac model"""
    try:
        mac_data = get_mac_model_data()
        model_data = mac_data.get(model_id)
        
        if not model_data:
            return None
        
        # Create patch compatibility based on model data
        capabilities = set()
        
        # All Mac models support kext loading
        capabilities.add(PatchCapability.KEXT_LOADING)
        
        # Models with OCLP support can do EFI modifications
        if model_data.get("oclp_compatibility") in ["fully_supported", "partially_supported"]:
            capabilities.add(PatchCapability.EFI_MODIFICATION)
            capabilities.add(PatchCapability.CUSTOM_SCRIPTS)
        
        # Newer models (T2 chip) have stricter security
        security_level = SecurityLevel.STRICT
        if "T2" in str(model_data.get("notes", [])):
            security_level = SecurityLevel.STRICT
        elif model_data.get("year", 0) < 2018:
            security_level = SecurityLevel.MODERATE
        
        # Create macOS support mapping
        macos_support = {}
        native_support = model_data.get("native_macos_support", {})
        required_patches = model_data.get("required_patches", {})
        
        for version in set(list(native_support.keys()) + list(required_patches.keys())):
            features = []
            if native_support.get(version, False):
                features.append("native_support")
            if version in required_patches:
                features.extend(["oclp_patches", "kext_injection"])
            
            if features:
                macos_support[version] = features
        
        return PatchCompatibility(
            supported_capabilities=capabilities,
            security_level=security_level,
            macos_support=macos_support,
            requires_signed_drivers=False,  # macOS allows unsigned kexts with SIP disabled
            requires_sip_disabled=(model_data.get("sip_requirements") == "disabled"),
            tested_versions=list(macos_support.keys())
        )
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to get patch compatibility for {model_id}: {e}")
        return None


def create_mac_hardware_profile(model: str) -> HardwareProfile:
    """Create hardware profile from Mac model identifier (moved from models to break circular import)"""
    mac_profiles = get_mac_model_data()
    
    profile_data = mac_profiles.get(model, {"name": model, "year": None, "cpu_family": "Unknown"})
    
    # Get patch compatibility for this model
    patch_compatibility = get_hardware_patch_compatibility(model)
    
    # Extract supported OS versions
    supported_versions = []
    native_support = profile_data.get("native_macos_support", {})
    required_patches = profile_data.get("required_patches", {})
    for version in set(list(native_support.keys()) + list(required_patches.keys())):
        if native_support.get(version, False) or version in required_patches:
            supported_versions.append(version)
    
    return HardwareProfile(
        name=profile_data.get("name", model),
        platform="mac",
        model=model,
        architecture="x86_64" if "Intel" in profile_data.get("cpu_family", "") else "arm64",
        year=profile_data.get("year"),
        cpu_family=profile_data.get("cpu_family"),
        
        # Mac-specific fields
        oclp_compatibility=profile_data.get("oclp_compatibility"),
        native_macos_support=profile_data.get("native_macos_support", {}),
        required_patches=profile_data.get("required_patches", {}),
        optional_patches=profile_data.get("optional_patches", {}),
        graphics_patches=profile_data.get("graphics_patches", []),
        audio_patches=profile_data.get("audio_patches", []),
        wifi_bluetooth_patches=profile_data.get("wifi_bluetooth_patches", []),
        usb_patches=profile_data.get("usb_patches", []),
        secure_boot_model=profile_data.get("secure_boot_model"),
        sip_requirements=profile_data.get("sip_requirements"),
        notes=profile_data.get("notes", []),
        
        # Patch pipeline integration
        patch_compatibility=patch_compatibility,
        supported_os_versions=supported_versions,
        deployment_type="macos_oclp" if profile_data.get("oclp_compatibility") else "macos_native"
    )