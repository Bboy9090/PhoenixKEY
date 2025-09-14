"""
BootForge Hardware Profiles - Comprehensive Mac Model Database
Enhanced hardware profile management with detailed Mac model specifications,
patch requirements, and OCLP compatibility mapping.
"""

from .usb_builder import HardwareProfile, DeploymentType
from typing import List, Dict, Optional, Any


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