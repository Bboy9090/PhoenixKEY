"""
BootForge Intelligent Guidance System  
Auto-detection, optimal settings, and intelligent recommendations for perfect results
"""

import logging
import platform
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path

from src.core.hardware_detector import HardwareDetector, DetectedHardware
from src.core.hardware_matcher import HardwareMatcher, ProfileMatch
from src.core.disk_manager import DiskInfo, DiskManager
from src.core.usb_builder import DeploymentRecipe, HardwareProfile


class GuidanceLevel(Enum):
    """Guidance assistance levels"""
    MINIMAL = "minimal"      # Basic recommendations only
    STANDARD = "standard"    # Smart recommendations with explanations
    COMPREHENSIVE = "comprehensive"  # Full guidance with alternatives
    EXPERT = "expert"        # Advanced options with technical details


class RecommendationType(Enum):
    """Types of recommendations"""
    OPTIMAL = "optimal"          # Best choice for the scenario
    ALTERNATIVE = "alternative"  # Good alternative options
    CAUTION = "caution"         # Important warnings or considerations
    IMPROVEMENT = "improvement"  # Suggestions to improve the setup


@dataclass
class Recommendation:
    """Single recommendation with confidence and reasoning"""
    type: RecommendationType
    title: str
    description: str
    confidence: float  # 0.0 to 1.0
    reasoning: str
    action: Optional[str] = None  # What the user should do
    technical_details: Optional[str] = None
    priority: int = 1  # 1=highest, 5=lowest
    
    @property
    def confidence_description(self) -> str:
        """Human-readable confidence level"""
        if self.confidence >= 0.9:
            return "Very High"
        elif self.confidence >= 0.7:
            return "High"
        elif self.confidence >= 0.5:
            return "Medium"
        elif self.confidence >= 0.3:
            return "Low"
        else:
            return "Very Low"


@dataclass  
class GuidanceContext:
    """Context for guidance recommendations"""
    detected_hardware: Optional[DetectedHardware] = None
    available_devices: List[DiskInfo] = field(default_factory=list)
    selected_device: Optional[DiskInfo] = None
    target_os: Optional[str] = None  # "macos", "windows", "linux"
    user_experience_level: str = "beginner"  # beginner, intermediate, expert
    previous_failures: List[str] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)


class GuidanceEngine(ABC):
    """Base class for guidance engines"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def generate_recommendations(self, context: GuidanceContext) -> List[Recommendation]:
        """Generate recommendations based on context"""
        pass


class HardwareGuidanceEngine(GuidanceEngine):
    """Provides hardware-specific guidance"""
    
    def __init__(self):
        super().__init__("Hardware Guidance")
        self.hardware_detector = HardwareDetector()
        self.hardware_matcher = HardwareMatcher()
    
    def generate_recommendations(self, context: GuidanceContext) -> List[Recommendation]:
        """Generate hardware-specific recommendations"""
        recommendations = []
        
        if not context.detected_hardware:
            recommendations.append(Recommendation(
                RecommendationType.CAUTION,
                "Hardware Detection Required",
                "We couldn't automatically detect your hardware. Manual configuration may be needed.",
                0.8,
                "Hardware detection helps ensure optimal compatibility and performance",
                "Click 'Detect Hardware' to scan your system",
                "Modern systems usually support automatic detection via DMI/SMBIOS"
            ))
            return recommendations
        
        hardware = context.detected_hardware
        
        # Check hardware compatibility
        if hardware.cpu_architecture:
            arch_recommendations = self._get_architecture_recommendations(hardware.cpu_architecture, context.target_os)
            recommendations.extend(arch_recommendations)
        
        # Memory recommendations
        if hardware.total_memory_gb:
            memory_recommendations = self._get_memory_recommendations(hardware.total_memory_gb, context.target_os)
            recommendations.extend(memory_recommendations)
        
        # Storage recommendations
        storage_recommendations = self._get_storage_recommendations(hardware, context)
        recommendations.extend(storage_recommendations)
        
        return recommendations
    
    def _get_architecture_recommendations(self, arch: str, target_os: Optional[str]) -> List[Recommendation]:
        """Get architecture-specific recommendations"""
        recommendations = []
        
        if arch == "x86_64" or arch == "AMD64":
            recommendations.append(Recommendation(
                RecommendationType.OPTIMAL,
                "Excellent Hardware Compatibility", 
                f"Your {arch} processor has excellent compatibility with all operating systems.",
                0.95,
                "x86_64 architecture is widely supported across macOS, Windows, and Linux",
                "You can proceed with confidence with any OS choice"
            ))
        elif arch == "ARM64" or arch == "AArch64":
            if target_os == "macos":
                recommendations.append(Recommendation(
                    RecommendationType.OPTIMAL,
                    "Native Apple Silicon Support",
                    "Perfect compatibility with modern macOS versions on your ARM processor.",
                    0.9,
                    "Apple Silicon Macs have native ARM64 support",
                    "Use macOS 11.0 or later for best performance"
                ))
            else:
                recommendations.append(Recommendation(
                    RecommendationType.CAUTION,
                    "Limited OS Compatibility on ARM",
                    "ARM processors have limited support for Windows and some Linux distributions.",
                    0.7,
                    "ARM64 support varies significantly across operating systems",
                    "Check OS compatibility before proceeding",
                    "Windows 11 ARM64 and select Linux distributions supported"
                ))
        
        return recommendations
    
    def _get_memory_recommendations(self, memory_gb: float, target_os: Optional[str]) -> List[Recommendation]:
        """Get memory-based recommendations"""
        recommendations = []
        
        memory_requirements = {
            "macos": {"min": 4, "recommended": 8, "optimal": 16},
            "windows": {"min": 4, "recommended": 8, "optimal": 16}, 
            "linux": {"min": 2, "recommended": 4, "optimal": 8}
        }
        
        if target_os and target_os in memory_requirements:
            reqs = memory_requirements[target_os]
            
            if memory_gb >= reqs["optimal"]:
                recommendations.append(Recommendation(
                    RecommendationType.OPTIMAL,
                    "Excellent Memory Configuration",
                    f"Your {memory_gb:.1f}GB RAM is optimal for {target_os.title()}.",
                    0.9,
                    f"Exceeds recommended {reqs['recommended']}GB for smooth operation",
                    "You can expect excellent performance"
                ))
            elif memory_gb >= reqs["recommended"]:
                recommendations.append(Recommendation(
                    RecommendationType.OPTIMAL,
                    "Good Memory Configuration", 
                    f"Your {memory_gb:.1f}GB RAM meets recommendations for {target_os.title()}.",
                    0.8,
                    f"Meets recommended {reqs['recommended']}GB requirement",
                    "System should perform well"
                ))
            elif memory_gb >= reqs["min"]:
                recommendations.append(Recommendation(
                    RecommendationType.CAUTION,
                    "Minimum Memory Requirements",
                    f"Your {memory_gb:.1f}GB RAM meets minimum requirements but may limit performance.",
                    0.6,
                    f"Below recommended {reqs['recommended']}GB, may experience slower performance",
                    "Consider upgrading memory for better experience",
                    f"Minimum: {reqs['min']}GB, Recommended: {reqs['recommended']}GB, Optimal: {reqs['optimal']}GB"
                ))
            else:
                recommendations.append(Recommendation(
                    RecommendationType.CAUTION,
                    "Insufficient Memory",
                    f"Your {memory_gb:.1f}GB RAM is below minimum requirements for {target_os.title()}.",
                    0.3,
                    f"Below minimum {reqs['min']}GB requirement",
                    "Memory upgrade strongly recommended",
                    f"System may be unstable or unusably slow"
                ))
        
        return recommendations
    
    def _get_storage_recommendations(self, hardware: DetectedHardware, context: GuidanceContext) -> List[Recommendation]:
        """Get storage-related recommendations"""
        recommendations = []
        
        if context.available_devices:
            fast_devices = [d for d in context.available_devices if d.write_speed_mbps > 100]
            slow_devices = [d for d in context.available_devices if d.write_speed_mbps <= 100]
            
            if fast_devices:
                recommendations.append(Recommendation(
                    RecommendationType.OPTIMAL,
                    "Fast Storage Devices Available",
                    f"Detected {len(fast_devices)} high-speed storage device(s) for optimal performance.",
                    0.85,
                    "Fast storage significantly improves boot times and system responsiveness",
                    f"Recommend using: {', '.join(d.name for d in fast_devices[:2])}"
                ))
            
            if slow_devices and not fast_devices:
                recommendations.append(Recommendation(
                    RecommendationType.IMPROVEMENT,
                    "Storage Performance Consideration",
                    "Available storage devices have slower write speeds which may affect performance.",
                    0.6,
                    "Slower storage devices can significantly impact boot times and responsiveness",
                    "Consider using faster storage (SSD/NVMe) for better experience",
                    "USB 3.0+ or internal SSD recommended for optimal performance"
                ))
        
        return recommendations


class DeviceSelectionGuidanceEngine(GuidanceEngine):
    """Provides device selection guidance"""
    
    def __init__(self):
        super().__init__("Device Selection")
    
    def generate_recommendations(self, context: GuidanceContext) -> List[Recommendation]:
        """Generate device selection recommendations"""
        recommendations = []
        
        if not context.available_devices:
            recommendations.append(Recommendation(
                RecommendationType.CAUTION,
                "No Storage Devices Detected",
                "No suitable storage devices found. Please connect a USB drive or storage device.",
                0.9,
                "Storage device is required for creating bootable media",
                "Connect a USB drive (16GB+ recommended) or select storage device"
            ))
            return recommendations
        
        # Categorize devices
        usb_devices = [d for d in context.available_devices if d.is_removable]
        fixed_devices = [d for d in context.available_devices if not d.is_removable]
        fast_devices = [d for d in context.available_devices if d.write_speed_mbps > 100]
        large_devices = [d for d in context.available_devices if d.size_bytes > 32 * 1024**3]  # >32GB
        
        # USB device recommendations
        if usb_devices:
            best_usb = max(usb_devices, key=lambda d: (d.write_speed_mbps, d.size_bytes))
            recommendations.append(Recommendation(
                RecommendationType.OPTIMAL,
                "Recommended USB Device",
                f"Best USB option: {best_usb.name} ({best_usb.size_bytes/(1024**3):.1f}GB)",
                0.8,
                "USB devices are safest choice with good compatibility",
                f"Select {best_usb.name} for optimal balance of safety and performance",
                f"Speed: {best_usb.write_speed_mbps:.1f} MB/s, Health: {best_usb.health_status}"
            ))
        
        # Fixed device warnings
        if fixed_devices:
            recommendations.append(Recommendation(
                RecommendationType.CAUTION,
                "Fixed Storage Devices Detected",
                f"Found {len(fixed_devices)} internal storage device(s). Use with extreme caution.",
                0.9,
                "Writing to internal drives can damage your system if wrong device is selected",
                "Double-check device selection - data will be permanently erased",
                "Always backup important data before proceeding with internal drives"
            ))
        
        # Performance recommendations
        if fast_devices:
            fastest = max(fast_devices, key=lambda d: d.write_speed_mbps)
            recommendations.append(Recommendation(
                RecommendationType.IMPROVEMENT,
                "High-Performance Option Available",
                f"Fastest device: {fastest.name} at {fastest.write_speed_mbps:.1f} MB/s",
                0.75,
                "Higher write speeds significantly improve deployment time",
                f"Use {fastest.name} for fastest deployment experience"
            ))
        
        # Size recommendations
        if large_devices:
            largest = max(large_devices, key=lambda d: d.size_bytes)
            recommendations.append(Recommendation(
                RecommendationType.IMPROVEMENT,
                "Large Capacity Option",
                f"Largest device: {largest.name} ({largest.size_bytes/(1024**3):.1f}GB)",
                0.7,
                "Large capacity allows for multiple OS installations and extra storage",
                f"Use {largest.name} for multi-boot setups or additional storage space"
            ))
        
        return recommendations


class OSSelectionGuidanceEngine(GuidanceEngine):
    """Provides OS selection guidance"""
    
    def __init__(self):
        super().__init__("OS Selection")
    
    def generate_recommendations(self, context: GuidanceContext) -> List[Recommendation]:
        """Generate OS selection recommendations"""
        recommendations = []
        
        if not context.detected_hardware:
            return recommendations
        
        hardware = context.detected_hardware
        
        # Platform-specific recommendations
        current_platform = platform.system().lower()
        
        if current_platform == "darwin":  # macOS
            recommendations.extend(self._get_macos_recommendations(hardware, context))
        elif current_platform == "windows":
            recommendations.extend(self._get_windows_recommendations(hardware, context))
        elif current_platform == "linux":
            recommendations.extend(self._get_linux_recommendations(hardware, context))
        
        return recommendations
    
    def _get_macos_recommendations(self, hardware: DetectedHardware, context: GuidanceContext) -> List[Recommendation]:
        """macOS-specific recommendations"""
        recommendations = []
        
        # Apple Silicon vs Intel
        if hardware.cpu_architecture in ["ARM64", "AArch64"]:
            recommendations.append(Recommendation(
                RecommendationType.OPTIMAL,
                "Native macOS Support",
                "Your Apple Silicon Mac has native support for latest macOS versions.",
                0.95,
                "Apple Silicon provides optimal performance and compatibility",
                "Recommend macOS Monterey (12.0) or later",
                "OpenCore Legacy Patcher not required for Apple Silicon"
            ))
        else:
            # Intel Mac recommendations
            recommendations.append(Recommendation(
                RecommendationType.OPTIMAL,
                "Intel Mac Compatibility",
                "Your Intel Mac supports macOS with potential for newer versions via OpenCore.",
                0.8,
                "OpenCore Legacy Patcher can enable newer macOS on older Intel hardware",
                "Check OpenCore Legacy Patcher compatibility for your model",
                "OCLP can enable macOS Big Sur+ on 2012-2016 Macs"
            ))
        
        return recommendations
    
    def _get_windows_recommendations(self, hardware: DetectedHardware, context: GuidanceContext) -> List[Recommendation]:
        """Windows-specific recommendations"""
        recommendations = []
        
        # Windows 11 TPM/SecureBoot requirements
        recommendations.append(Recommendation(
            RecommendationType.IMPROVEMENT,
            "Windows 11 Compatibility",
            "Windows 11 has strict hardware requirements that can be bypassed if needed.",
            0.7,
            "TPM 2.0, Secure Boot, and CPU generation requirements can prevent installation",
            "Use Windows 11 bypass patches if your hardware doesn't meet requirements",
            "BootForge includes automatic bypass for TPM, Secure Boot, and CPU requirements"
        ))
        
        # Performance recommendations
        if hardware.total_memory_gb and hardware.total_memory_gb >= 8:
            recommendations.append(Recommendation(
                RecommendationType.OPTIMAL,
                "Good Windows Performance Expected",
                f"Your {hardware.total_memory_gb:.1f}GB RAM provides good Windows performance.",
                0.8,
                "8GB+ RAM ensures smooth Windows operation",
                "Windows 10 or 11 should perform well on your system"
            ))
        
        return recommendations
    
    def _get_linux_recommendations(self, hardware: DetectedHardware, context: GuidanceContext) -> List[Recommendation]:
        """Linux-specific recommendations"""
        recommendations = []
        
        # Linux compatibility (generally excellent)
        recommendations.append(Recommendation(
            RecommendationType.OPTIMAL,
            "Excellent Linux Compatibility",
            "Linux has outstanding hardware compatibility and performance on your system.",
            0.9,
            "Linux supports virtually all hardware architectures with excellent performance",
            "Any major Linux distribution should work perfectly",
            "Consider Ubuntu, Fedora, or Pop!_OS for beginners"
        ))
        
        # Resource efficiency
        if hardware.total_memory_gb and hardware.total_memory_gb < 4:
            recommendations.append(Recommendation(
                RecommendationType.IMPROVEMENT,
                "Lightweight Linux Recommended",
                "Consider lightweight Linux distributions for optimal performance on your system.",
                0.8,
                "Lightweight distros use fewer system resources",
                "Try Xubuntu, Linux Mint XFCE, or elementary OS",
                "These distributions are optimized for systems with limited resources"
            ))
        
        return recommendations


class IntelligentGuidanceManager:
    """Manages all guidance engines and provides comprehensive recommendations"""
    
    def __init__(self, guidance_level: GuidanceLevel = GuidanceLevel.STANDARD):
        self.guidance_level = guidance_level
        self.logger = logging.getLogger(__name__)
        
        # Initialize guidance engines
        self.engines = {
            "hardware": HardwareGuidanceEngine(),
            "device_selection": DeviceSelectionGuidanceEngine(),
            "os_selection": OSSelectionGuidanceEngine()
        }
        
        # Context and state
        self.current_context = GuidanceContext()
        self._cached_recommendations: Dict[str, List[Recommendation]] = {}
        
        self.logger.info(f"Intelligent Guidance Manager initialized with {guidance_level.value} level")
    
    def update_context(self, **kwargs):
        """Update guidance context"""
        for key, value in kwargs.items():
            if hasattr(self.current_context, key):
                setattr(self.current_context, key, value)
                self.logger.debug(f"Updated context: {key}")
        
        # Clear cached recommendations when context changes
        self._cached_recommendations.clear()
    
    def get_recommendations(self, engine_name: Optional[str] = None) -> List[Recommendation]:
        """Get recommendations from specified engine or all engines"""
        if engine_name:
            if engine_name not in self.engines:
                raise ValueError(f"Unknown engine: {engine_name}")
            
            if engine_name not in self._cached_recommendations:
                recommendations = self.engines[engine_name].generate_recommendations(self.current_context)
                self._cached_recommendations[engine_name] = recommendations
            
            return self._cached_recommendations[engine_name]
        
        # Get recommendations from all engines
        all_recommendations = []
        for name, engine in self.engines.items():
            recommendations = self.get_recommendations(name)
            all_recommendations.extend(recommendations)
        
        # Sort by priority and confidence
        all_recommendations.sort(key=lambda r: (r.priority, -r.confidence))
        
        return all_recommendations
    
    def get_top_recommendations(self, limit: int = 5) -> List[Recommendation]:
        """Get top recommendations by priority and confidence"""
        recommendations = self.get_recommendations()
        
        # Filter by guidance level
        if self.guidance_level == GuidanceLevel.MINIMAL:
            recommendations = [r for r in recommendations if r.confidence >= 0.8]
        elif self.guidance_level == GuidanceLevel.EXPERT:
            # Include all recommendations for expert level
            pass
        
        return recommendations[:limit]
    
    def get_critical_warnings(self) -> List[Recommendation]:
        """Get only critical warnings and cautions"""
        recommendations = self.get_recommendations()
        return [r for r in recommendations if r.type == RecommendationType.CAUTION and r.confidence >= 0.7]
    
    def get_optimal_suggestions(self) -> List[Recommendation]:
        """Get optimal configuration suggestions"""
        recommendations = self.get_recommendations()
        return [r for r in recommendations if r.type == RecommendationType.OPTIMAL and r.confidence >= 0.8]
    
    def auto_configure_optimal_settings(self) -> Dict[str, Any]:
        """Automatically configure optimal settings based on guidance"""
        optimal_config = {}
        
        # Get optimal recommendations
        optimal_recs = self.get_optimal_suggestions()
        
        # Device selection
        if self.current_context.available_devices:
            device_recs = [r for r in optimal_recs if "device" in r.title.lower()]
            if device_recs:
                # Find the recommended device
                for rec in device_recs:
                    if rec.action and "select" in rec.action.lower():
                        for device in self.current_context.available_devices:
                            if device.name in rec.action:
                                optimal_config["recommended_device"] = device
                                break
        
        # OS selection
        os_recs = [r for r in optimal_recs if any(os_name in r.title.lower() for os_name in ["macos", "windows", "linux"])]
        if os_recs and not optimal_config.get("recommended_os"):
            for rec in os_recs:
                if "macos" in rec.title.lower():
                    optimal_config["recommended_os"] = "macos"
                elif "windows" in rec.title.lower():
                    optimal_config["recommended_os"] = "windows"
                elif "linux" in rec.title.lower():
                    optimal_config["recommended_os"] = "linux"
        
        return optimal_config
    
    def explain_recommendation(self, recommendation: Recommendation) -> str:
        """Get detailed explanation for a recommendation"""
        explanation = f"**{recommendation.title}**\n\n"
        explanation += f"{recommendation.description}\n\n"
        explanation += f"**Confidence:** {recommendation.confidence_description} ({recommendation.confidence:.0%})\n"
        explanation += f"**Reasoning:** {recommendation.reasoning}\n"
        
        if recommendation.action:
            explanation += f"**Action:** {recommendation.action}\n"
        
        if recommendation.technical_details and self.guidance_level in [GuidanceLevel.COMPREHENSIVE, GuidanceLevel.EXPERT]:
            explanation += f"**Technical Details:** {recommendation.technical_details}\n"
        
        return explanation
    
    def get_guidance_summary(self) -> Dict[str, Any]:
        """Get comprehensive guidance summary"""
        recommendations = self.get_recommendations()
        
        return {
            "total_recommendations": len(recommendations),
            "critical_warnings": len(self.get_critical_warnings()),
            "optimal_suggestions": len(self.get_optimal_suggestions()),
            "confidence_distribution": {
                "high": len([r for r in recommendations if r.confidence >= 0.8]),
                "medium": len([r for r in recommendations if 0.5 <= r.confidence < 0.8]),
                "low": len([r for r in recommendations if r.confidence < 0.5])
            },
            "recommendation_types": {
                rtype.value: len([r for r in recommendations if r.type == rtype])
                for rtype in RecommendationType
            }
        }