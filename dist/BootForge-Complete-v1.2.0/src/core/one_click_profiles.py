"""
BootForge One-Click Deployment Profiles
Pre-configured deployment profiles for common use cases with effortless operation
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

from src.core.usb_builder import DeploymentRecipe, HardwareProfile, DeploymentType
from src.core.intelligent_guidance import GuidanceContext, IntelligentGuidanceManager


class ProfileCategory(Enum):
    """Categories of deployment profiles"""
    POPULAR = "popular"           # Most commonly used profiles
    BEGINNER = "beginner"         # Perfect for first-time users  
    PROFESSIONAL = "professional" # Advanced profiles for power users
    SPECIALIZED = "specialized"   # Specific use cases


@dataclass
class OneClickProfile:
    """Complete one-click deployment profile"""
    id: str
    name: str
    description: str
    category: ProfileCategory
    
    # Target specifications
    target_os: str                    # "macos", "windows", "linux"
    recommended_hardware: List[str]   # Hardware compatibility
    min_storage_gb: int              # Minimum storage requirement
    
    # Deployment configuration
    recipe_name: str                 # Recipe to use
    auto_settings: Dict[str, Any]    # Automatic settings
    
    # User experience
    difficulty_level: str            # "beginner", "intermediate", "expert"  
    estimated_time_minutes: int      # Expected completion time
    success_rate: float             # Historical success rate (0.0-1.0)
    
    # Guidance and help
    instructions: List[str]          # Step-by-step instructions
    requirements: List[str]          # What user needs before starting
    warnings: List[str] = field(default_factory=list)
    tips: List[str] = field(default_factory=list)
    
    @property
    def difficulty_emoji(self) -> str:
        """Emoji representation of difficulty"""
        levels = {
            "beginner": "🟢",
            "intermediate": "🟡", 
            "expert": "🔴"
        }
        return levels.get(self.difficulty_level, "⚪")
    
    @property
    def success_emoji(self) -> str:
        """Emoji representation of success rate"""
        if self.success_rate >= 0.95:
            return "🎯"
        elif self.success_rate >= 0.85:
            return "✅"
        elif self.success_rate >= 0.75:
            return "🟡"
        else:
            return "⚠️"


class OneClickProfileManager:
    """Manages one-click deployment profiles"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.profiles: Dict[str, OneClickProfile] = {}
        self._create_built_in_profiles()
        
        self.logger.info(f"One-Click Profile Manager initialized with {len(self.profiles)} profiles")
    
    def _create_built_in_profiles(self):
        """Create built-in one-click profiles"""
        
        # macOS Profiles
        self._add_profile(OneClickProfile(
            id="macos_daily_driver",
            name="🍎 macOS Daily Driver",
            description="Perfect macOS setup for everyday use - works on any Mac from 2012+",
            category=ProfileCategory.POPULAR,
            target_os="macos",
            recommended_hardware=["MacBook Air", "MacBook Pro", "iMac", "Mac Mini"],
            min_storage_gb=32,
            recipe_name="macos_oclp_optimized",
            auto_settings={
                "enable_oclp": True,
                "security_model": "compliant",
                "patch_level": "standard",
                "driver_injection": True,
                "performance_mode": "balanced"
            },
            difficulty_level="beginner",
            estimated_time_minutes=45,
            success_rate=0.96,
            instructions=[
                "1. Connect USB drive (32GB+ recommended)",
                "2. Select your Mac model (auto-detected)",
                "3. Choose macOS version (latest recommended)",
                "4. Click 'Start Deployment' and wait",
                "5. Boot from USB and install macOS"
            ],
            requirements=[
                "USB drive 32GB or larger",
                "Mac computer (2012 or newer)",
                "Stable internet connection",
                "macOS installer (will be downloaded)"
            ],
            tips=[
                "💡 Use USB 3.0 for faster installation",
                "💡 Latest macOS versions work best",
                "💡 Keep your Mac plugged in during installation"
            ]
        ))
        
        self._add_profile(OneClickProfile(
            id="macos_legacy_rescue",
            name="🔧 Legacy Mac Rescue",
            description="Breathe new life into old Macs (2008-2016) with modern macOS",
            category=ProfileCategory.SPECIALIZED,
            target_os="macos",
            recommended_hardware=["2008-2016 Macs"],
            min_storage_gb=64,
            recipe_name="macos_oclp_legacy",
            auto_settings={
                "enable_oclp": True,
                "security_model": "permissive",
                "patch_level": "aggressive",
                "legacy_support": True,
                "gpu_acceleration": "patched"
            },
            difficulty_level="intermediate",
            estimated_time_minutes=90,
            success_rate=0.89,
            instructions=[
                "1. Verify Mac model compatibility",
                "2. Connect high-speed USB drive (64GB+)",
                "3. Select appropriate macOS version",
                "4. Enable legacy compatibility patches",
                "5. Complete installation with patience"
            ],
            requirements=[
                "USB drive 64GB or larger", 
                "Legacy Mac (2008-2016)",
                "OCLP compatibility check passed",
                "Backup of current system"
            ],
            warnings=[
                "⚠️ Backup your data first - process modifies firmware",
                "⚠️ Some features may not work on very old hardware",
                "⚠️ Installation takes longer on legacy systems"
            ],
            tips=[
                "💡 Check OCLP compatibility guide first",
                "💡 Use wired connection for stability",
                "💡 Disable FileVault before starting"
            ]
        ))
        
        # Windows Profiles  
        self._add_profile(OneClickProfile(
            id="windows_11_bypass",
            name="🪟 Windows 11 Universal",
            description="Windows 11 with all hardware requirements bypassed - works on any PC",
            category=ProfileCategory.POPULAR,
            target_os="windows",
            recommended_hardware=["Any PC", "Older hardware welcome"],
            min_storage_gb=32,
            recipe_name="windows_11_bypass",
            auto_settings={
                "bypass_tpm": True,
                "bypass_secure_boot": True,
                "bypass_cpu_check": True,
                "bypass_memory_check": True,
                "unattended_install": True,
                "driver_injection": True
            },
            difficulty_level="beginner",
            estimated_time_minutes=60,
            success_rate=0.94,
            instructions=[
                "1. Connect USB drive (32GB+)",
                "2. Select Windows 11 version",
                "3. Enable hardware bypasses (automatic)",
                "4. Start deployment process",
                "5. Install Windows on any PC"
            ],
            requirements=[
                "USB drive 32GB or larger",
                "Any PC (hardware requirements bypassed)",
                "Windows 11 ISO (will be downloaded)", 
                "Valid Windows license"
            ],
            tips=[
                "💡 Works on PCs from 2010+",
                "💡 All hardware checks are automatically bypassed",
                "💡 Includes essential drivers for compatibility"
            ]
        ))
        
        self._add_profile(OneClickProfile(
            id="windows_gaming_rig",
            name="🎮 Gaming Rig Optimizer",
            description="High-performance Windows setup optimized for gaming",
            category=ProfileCategory.PROFESSIONAL,
            target_os="windows",
            recommended_hardware=["Gaming PC", "High-end hardware"],
            min_storage_gb=64,
            recipe_name="windows_gaming_optimized",
            auto_settings={
                "performance_mode": "maximum",
                "gaming_optimizations": True,
                "driver_bundle": "gaming",
                "debloat_windows": True,
                "gaming_services": True
            },
            difficulty_level="intermediate",
            estimated_time_minutes=75,
            success_rate=0.92,
            instructions=[
                "1. Use high-speed USB 3.0+ drive (64GB+)",
                "2. Select Windows 10/11 Gaming Edition",
                "3. Enable gaming optimizations",
                "4. Include GPU-specific drivers",
                "5. Install and optimize for gaming"
            ],
            requirements=[
                "Fast USB drive 64GB+",
                "Gaming PC with dedicated GPU",
                "Latest GPU drivers available",
                "Windows license"
            ],
            tips=[
                "💡 Includes optimized graphics drivers",
                "💡 Removes bloatware for better performance",
                "💡 Pre-configured for gaming best practices"
            ]
        ))
        
        # Linux Profiles
        self._add_profile(OneClickProfile(
            id="linux_ubuntu_starter",
            name="🐧 Ubuntu Perfect Start",
            description="Ubuntu Linux with everything configured - perfect for beginners",
            category=ProfileCategory.BEGINNER,
            target_os="linux",
            recommended_hardware=["Any PC", "Laptop", "Desktop"],
            min_storage_gb=16,
            recipe_name="ubuntu_optimized",
            auto_settings={
                "desktop_environment": "gnome",
                "codecs_included": True,
                "development_tools": False,
                "office_suite": True,
                "media_support": True
            },
            difficulty_level="beginner",
            estimated_time_minutes=30,
            success_rate=0.98,
            instructions=[
                "1. Connect USB drive (16GB+)",
                "2. Select Ubuntu LTS version", 
                "3. Choose software packages",
                "4. Create installation media",
                "5. Boot and install Ubuntu"
            ],
            requirements=[
                "USB drive 16GB or larger",
                "PC with 4GB+ RAM",
                "Ubuntu ISO (will be downloaded)",
                "Basic computer knowledge"
            ],
            tips=[
                "💡 Ubuntu LTS versions are most stable",
                "💡 Includes essential codecs and drivers",
                "💡 Perfect for switching from Windows/macOS"
            ]
        ))
        
        self._add_profile(OneClickProfile(
            id="linux_developer_powerhouse",
            name="⚡ Developer Powerhouse", 
            description="Complete Linux development environment with all tools included",
            category=ProfileCategory.PROFESSIONAL,
            target_os="linux",
            recommended_hardware=["Development workstation", "High-RAM system"],
            min_storage_gb=32,
            recipe_name="linux_development",
            auto_settings={
                "desktop_environment": "kde",
                "development_tools": True,
                "docker_included": True,
                "vscode_included": True,
                "git_configured": True,
                "nodejs_included": True,
                "python_dev": True
            },
            difficulty_level="expert",
            estimated_time_minutes=45,
            success_rate=0.91,
            instructions=[
                "1. Use fast USB drive (32GB+)",
                "2. Select development Linux distro",
                "3. Enable developer tool bundle",
                "4. Configure development environment",
                "5. Install and start coding"
            ],
            requirements=[
                "Fast USB drive 32GB+",
                "PC with 8GB+ RAM recommended",
                "Development experience helpful",
                "Internet for package downloads"
            ],
            tips=[
                "💡 Includes Docker, VS Code, Git, Node.js",
                "💡 Pre-configured for popular frameworks",
                "💡 KDE desktop optimized for development"
            ]
        ))
        
        # Multi-OS Profiles
        self._add_profile(OneClickProfile(
            id="multiboot_triple_threat",
            name="🎯 Triple Boot Master",
            description="Boot from macOS, Windows, and Linux on one drive",
            category=ProfileCategory.SPECIALIZED,
            target_os="multiboot",
            recommended_hardware=["Large storage device"],
            min_storage_gb=128,
            recipe_name="multiboot_grub",
            auto_settings={
                "partition_scheme": "multiboot",
                "bootloader": "grub2",
                "os_selection": ["macos", "windows", "linux"],
                "shared_storage": True
            },
            difficulty_level="expert",
            estimated_time_minutes=120,
            success_rate=0.83,
            instructions=[
                "1. Use large storage device (128GB+)",
                "2. Select which operating systems to include",
                "3. Configure partition sizes",
                "4. Create multi-boot media",
                "5. Install multiple OS with boot menu"
            ],
            requirements=[
                "Large storage device 128GB+",
                "All OS installers or ISOs",
                "Advanced technical knowledge",
                "Backup of important data"
            ],
            warnings=[
                "⚠️ Complex setup - backup everything first",
                "⚠️ Requires technical expertise",
                "⚠️ May take several hours to complete"
            ],
            tips=[
                "💡 Plan partition sizes carefully",
                "💡 Test each OS individually first",
                "💡 Keep bootloader backup"
            ]
        ))
    
    def _add_profile(self, profile: OneClickProfile):
        """Add a profile to the manager"""
        self.profiles[profile.id] = profile
        self.logger.debug(f"Added profile: {profile.name}")
    
    def get_profile(self, profile_id: str) -> Optional[OneClickProfile]:
        """Get a specific profile"""
        return self.profiles.get(profile_id)
    
    def get_profiles_by_category(self, category: ProfileCategory) -> List[OneClickProfile]:
        """Get profiles by category"""
        return [p for p in self.profiles.values() if p.category == category]
    
    def get_profiles_for_os(self, target_os: str) -> List[OneClickProfile]:
        """Get profiles for specific OS"""
        return [p for p in self.profiles.values() if p.target_os == target_os or p.target_os == "multiboot"]
    
    def get_beginner_friendly_profiles(self) -> List[OneClickProfile]:
        """Get profiles suitable for beginners"""
        return [p for p in self.profiles.values() if p.difficulty_level == "beginner"]
    
    def get_recommended_profiles(
        self, 
        guidance_context: Optional[GuidanceContext] = None
    ) -> List[OneClickProfile]:
        """Get recommended profiles based on context"""
        
        if not guidance_context:
            # Return popular profiles if no context
            popular = self.get_profiles_by_category(ProfileCategory.POPULAR)
            return sorted(popular, key=lambda p: p.success_rate, reverse=True)
        
        recommended = []
        
        # Filter by detected hardware
        if guidance_context.detected_hardware:
            hardware = guidance_context.detected_hardware
            
            # macOS recommendations for Apple hardware
            if "mac" in hardware.system_manufacturer.lower() if hardware.system_manufacturer else False:
                mac_profiles = self.get_profiles_for_os("macos")
                recommended.extend(mac_profiles)
            
            # Gaming profiles for high-end systems
            if hardware.total_memory_gb and hardware.total_memory_gb >= 16:
                gaming = [p for p in self.profiles.values() if "gaming" in p.name.lower()]
                recommended.extend(gaming)
            
            # Developer profiles for capable systems
            if hardware.total_memory_gb and hardware.total_memory_gb >= 8:
                dev = [p for p in self.profiles.values() if "developer" in p.name.lower()]
                recommended.extend(dev)
        
        # Filter by user experience level
        if guidance_context.user_experience_level == "beginner":
            beginner_profiles = self.get_beginner_friendly_profiles()
            recommended.extend(beginner_profiles)
        
        # Remove duplicates and sort by success rate
        unique_profiles = list({p.id: p for p in recommended}.values())
        return sorted(unique_profiles, key=lambda p: p.success_rate, reverse=True)[:5]
    
    def search_profiles(self, query: str) -> List[OneClickProfile]:
        """Search profiles by name, description, or tags"""
        query_lower = query.lower()
        results = []
        
        for profile in self.profiles.values():
            if (query_lower in profile.name.lower() or 
                query_lower in profile.description.lower() or
                query_lower in profile.target_os.lower()):
                results.append(profile)
        
        return sorted(results, key=lambda p: p.success_rate, reverse=True)
    
    def get_profile_statistics(self) -> Dict[str, Any]:
        """Get statistics about available profiles"""
        total = len(self.profiles)
        
        by_category = {}
        for category in ProfileCategory:
            by_category[category.value] = len(self.get_profiles_by_category(category))
        
        by_os = {}
        for os_name in ["macos", "windows", "linux", "multiboot"]:
            by_os[os_name] = len(self.get_profiles_for_os(os_name))
        
        by_difficulty = {}
        for difficulty in ["beginner", "intermediate", "expert"]:
            by_difficulty[difficulty] = len([
                p for p in self.profiles.values() if p.difficulty_level == difficulty
            ])
        
        avg_success_rate = sum(p.success_rate for p in self.profiles.values()) / total if total > 0 else 0
        
        return {
            "total_profiles": total,
            "by_category": by_category,
            "by_os": by_os, 
            "by_difficulty": by_difficulty,
            "average_success_rate": avg_success_rate,
            "highest_success_rate": max((p.success_rate for p in self.profiles.values()), default=0)
        }