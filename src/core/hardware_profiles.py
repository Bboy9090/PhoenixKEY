"""
BootForge Hardware Profiles Shim
Re-exports and utility functions for hardware profile management
"""

from .usb_builder import HardwareProfile, DeploymentType
from typing import List, Dict, Optional


def get_default_profiles() -> List[HardwareProfile]:
    """Get default hardware profiles for common devices"""
    profiles = []
    
    # macOS profiles
    mac_models = {
        "iMacPro1,1": {"name": "iMac Pro 2017", "year": 2017, "cpu_family": "Intel Xeon W"},
        "MacBookPro15,1": {"name": "MacBook Pro 15\" 2018", "year": 2018, "cpu_family": "Intel Core i7/i9"},
        "MacBookPro16,1": {"name": "MacBook Pro 16\" 2019", "year": 2019, "cpu_family": "Intel Core i7/i9"},
        "iMac20,1": {"name": "iMac 27\" 2020", "year": 2020, "cpu_family": "Intel Core i5/i7/i9"},
        "MacBookAir10,1": {"name": "MacBook Air M1 2020", "year": 2020, "cpu_family": "Apple M1"},
        "MacBookPro18,1": {"name": "MacBook Pro 14\" M1 Pro 2021", "year": 2021, "cpu_family": "Apple M1 Pro"},
        "iMac24,1": {"name": "iMac 24\" M1 2021", "year": 2021, "cpu_family": "Apple M1"},
    }
    
    for model, info in mac_models.items():
        profiles.append(HardwareProfile(
            name=info["name"],
            platform="mac",
            model=model,
            architecture="x86_64" if "Intel" in info["cpu_family"] else "arm64",
            year=info["year"],
            cpu_family=info["cpu_family"]
        ))
    
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
    """Create hardware profile from Mac model identifier"""
    return HardwareProfile.from_mac_model(model)


def get_profiles_by_platform(platform: str) -> List[HardwareProfile]:
    """Get hardware profiles filtered by platform"""
    all_profiles = get_default_profiles()
    return [profile for profile in all_profiles if profile.platform == platform]


def get_compatible_profiles(deployment_type: DeploymentType) -> List[HardwareProfile]:
    """Get hardware profiles compatible with specific deployment type"""
    all_profiles = get_default_profiles()
    
    if deployment_type == DeploymentType.MACOS_OCLP:
        # Return only Mac profiles for macOS OCLP
        return [profile for profile in all_profiles if profile.platform == "mac"]
    elif deployment_type == DeploymentType.WINDOWS_UNATTENDED:
        # Return Windows and generic profiles
        return [profile for profile in all_profiles if profile.platform in ["windows", "generic"]]
    elif deployment_type == DeploymentType.LINUX_AUTOMATED:
        # Return Linux profiles
        return [profile for profile in all_profiles if profile.platform == "linux"]
    else:
        # Custom payload can work on any platform
        return all_profiles