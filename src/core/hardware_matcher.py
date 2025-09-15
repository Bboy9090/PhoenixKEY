"""
BootForge Smart Hardware Profile Matching System
Intelligent matching of detected hardware to deployment profiles with confidence scoring
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from src.core.hardware_detector import DetectedHardware, DetectionConfidence, ProfileMatch
from src.core.vendor_database import VendorDatabase
from src.core.models import HardwareProfile
from src.core.hardware_profiles import get_default_profiles, get_profiles_by_platform


class MatchCriteria(Enum):
    """Hardware matching criteria"""
    EXACT_MODEL = "exact_model"           # Exact system model match
    MANUFACTURER_MODEL = "manufacturer_model"  # Manufacturer + partial model match
    PLATFORM = "platform"                # Platform match (mac/windows/linux)
    ARCHITECTURE = "architecture"        # CPU architecture match
    CPU_FAMILY = "cpu_family"           # CPU family/generation match
    YEAR = "year"                       # Manufacturing year proximity
    SPECIAL_FEATURES = "special_features" # Special hardware features/requirements


@dataclass
class MatchReason:
    """Explanation for why a profile matched"""
    criteria: MatchCriteria
    score: float  # 0-100
    explanation: str
    confidence: float  # 0-1


class HardwareMatcher:
    """Intelligent hardware profile matching engine"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.vendor_db = VendorDatabase()
        self._available_profiles = get_default_profiles()
        
        # Matching weights for different criteria
        self._match_weights = {
            MatchCriteria.EXACT_MODEL: 40.0,
            MatchCriteria.MANUFACTURER_MODEL: 25.0,
            MatchCriteria.PLATFORM: 15.0,
            MatchCriteria.ARCHITECTURE: 10.0,
            MatchCriteria.CPU_FAMILY: 5.0,
            MatchCriteria.YEAR: 3.0,
            MatchCriteria.SPECIAL_FEATURES: 2.0
        }
        
        self.logger.info(f"Hardware matcher initialized with {len(self._available_profiles)} profiles")
    
    def find_matching_profiles(self, detected_hardware: DetectedHardware, max_results: int = 5) -> List[ProfileMatch]:
        """Find matching hardware profiles for detected hardware"""
        if not detected_hardware:
            self.logger.error("No hardware data provided for matching")
            return []
        
        self.logger.info(f"Finding matches for: {detected_hardware.get_summary()}")
        
        # Get candidate profiles based on platform
        candidates = self._get_candidate_profiles(detected_hardware)
        self.logger.info(f"Found {len(candidates)} candidate profiles")
        
        # Score each candidate profile
        profile_matches = []
        for profile in candidates:
            match = self._score_profile_match(detected_hardware, profile)
            if match.match_score > 0:  # Only include non-zero matches
                profile_matches.append(match)
        
        # Sort by match score (descending)
        profile_matches.sort(key=lambda x: x.match_score, reverse=True)
        
        # Limit results and set confidence levels
        results = profile_matches[:max_results]
        for match in results:
            match.confidence = self._calculate_match_confidence(match.match_score, detected_hardware)
        
        self.logger.info(f"Found {len(results)} matching profiles")
        for match in results[:3]:  # Log top 3 matches
            self.logger.info(f"  {match.profile.name}: {match.match_score:.1f}% ({match.confidence.value})")
        
        return results
    
    def _get_candidate_profiles(self, detected_hardware: DetectedHardware) -> List[HardwareProfile]:
        """Get candidate profiles based on detected platform"""
        if not detected_hardware.platform:
            return self._available_profiles
        
        # Primary platform match
        platform_profiles = get_profiles_by_platform(detected_hardware.platform)
        
        # For unknown hardware, also include generic profiles
        if detected_hardware.detection_confidence == DetectionConfidence.UNKNOWN:
            generic_profiles = [p for p in self._available_profiles 
                             if "generic" in p.model.lower() or "unknown" in p.name.lower()]
            platform_profiles.extend(generic_profiles)
        
        # Remove duplicates while preserving order
        seen = set()
        candidates = []
        for profile in platform_profiles:
            profile_key = (profile.name, profile.model)
            if profile_key not in seen:
                seen.add(profile_key)
                candidates.append(profile)
        
        return candidates
    
    def _score_profile_match(self, hardware: DetectedHardware, profile: HardwareProfile) -> ProfileMatch:
        """Score how well a hardware profile matches detected hardware"""
        match_reasons = []
        total_score = 0.0
        
        # Exact model matching (highest priority)
        model_score = self._score_model_match(hardware, profile)
        if model_score > 0:
            match_reasons.append(MatchReason(
                criteria=MatchCriteria.EXACT_MODEL,
                score=model_score,
                explanation=f"Model match: {hardware.system_model} → {profile.model}",
                confidence=model_score / 100.0
            ))
            total_score += model_score * self._match_weights[MatchCriteria.EXACT_MODEL] / 100.0
        
        # Manufacturer + partial model matching
        manufacturer_score = self._score_manufacturer_match(hardware, profile)
        if manufacturer_score > 0:
            match_reasons.append(MatchReason(
                criteria=MatchCriteria.MANUFACTURER_MODEL,
                score=manufacturer_score,
                explanation=f"Manufacturer match: {hardware.system_manufacturer}",
                confidence=manufacturer_score / 100.0
            ))
            total_score += manufacturer_score * self._match_weights[MatchCriteria.MANUFACTURER_MODEL] / 100.0
        
        # Platform matching
        platform_score = self._score_platform_match(hardware, profile)
        if platform_score > 0:
            match_reasons.append(MatchReason(
                criteria=MatchCriteria.PLATFORM,
                score=platform_score,
                explanation=f"Platform match: {hardware.platform} → {profile.platform}",
                confidence=platform_score / 100.0
            ))
            total_score += platform_score * self._match_weights[MatchCriteria.PLATFORM] / 100.0
        
        # Architecture matching
        arch_score = self._score_architecture_match(hardware, profile)
        if arch_score > 0:
            match_reasons.append(MatchReason(
                criteria=MatchCriteria.ARCHITECTURE,
                score=arch_score,
                explanation=f"Architecture match: {hardware.cpu_architecture} → {profile.architecture}",
                confidence=arch_score / 100.0
            ))
            total_score += arch_score * self._match_weights[MatchCriteria.ARCHITECTURE] / 100.0
        
        # CPU family matching
        cpu_score = self._score_cpu_match(hardware, profile)
        if cpu_score > 0:
            match_reasons.append(MatchReason(
                criteria=MatchCriteria.CPU_FAMILY,
                score=cpu_score,
                explanation=f"CPU family match: {hardware.cpu_name} ≈ {profile.cpu_family}",
                confidence=cpu_score / 100.0
            ))
            total_score += cpu_score * self._match_weights[MatchCriteria.CPU_FAMILY] / 100.0
        
        # Year proximity matching
        year_score = self._score_year_match(hardware, profile)
        if year_score > 0:
            match_reasons.append(MatchReason(
                criteria=MatchCriteria.YEAR,
                score=year_score,
                explanation=f"Year proximity match",
                confidence=year_score / 100.0
            ))
            total_score += year_score * self._match_weights[MatchCriteria.YEAR] / 100.0
        
        # Special features matching (GPU, network, etc.)
        features_score = self._score_features_match(hardware, profile)
        if features_score > 0:
            match_reasons.append(MatchReason(
                criteria=MatchCriteria.SPECIAL_FEATURES,
                score=features_score,
                explanation=f"Special features match",
                confidence=features_score / 100.0
            ))
            total_score += features_score * self._match_weights[MatchCriteria.SPECIAL_FEATURES] / 100.0
        
        return ProfileMatch(
            profile=profile,
            confidence=DetectionConfidence.UNKNOWN,  # Will be set later
            match_score=min(total_score, 100.0),  # Cap at 100%
            match_reasons=[reason.explanation for reason in match_reasons],
            detection_data=hardware
        )
    
    def _score_model_match(self, hardware: DetectedHardware, profile: HardwareProfile) -> float:
        """Score exact model matching"""
        if not hardware.system_model or not profile.model:
            return 0.0
        
        hardware_model = hardware.system_model.lower().strip()
        profile_model = profile.model.lower().strip()
        
        # Exact match
        if hardware_model == profile_model:
            return 100.0
        
        # macOS model identifier matching (e.g., "MacBookPro16,1")
        if hardware.platform == "mac" and profile.platform == "mac":
            # Check if hardware model is a Mac model identifier
            if re.match(r"^[a-z]+\d+,\d+$", hardware_model, re.IGNORECASE):
                if hardware_model == profile_model:
                    return 100.0
                # Check if it's a similar model (e.g., MacBookPro16,1 vs MacBookPro16,2)
                if hardware_model.split(',')[0] == profile_model.split(',')[0]:
                    return 85.0
        
        # Partial matching with fuzzy logic
        # Check if one model name contains the other
        if hardware_model in profile_model or profile_model in hardware_model:
            overlap = min(len(hardware_model), len(profile_model))
            total = max(len(hardware_model), len(profile_model))
            return (overlap / total) * 80.0  # Max 80% for partial matches
        
        # Check for common keywords/model numbers
        hardware_words = set(re.findall(r'\w+', hardware_model))
        profile_words = set(re.findall(r'\w+', profile_model))
        
        if hardware_words and profile_words:
            intersection = hardware_words & profile_words
            union = hardware_words | profile_words
            
            if intersection:
                similarity = len(intersection) / len(union)
                return similarity * 60.0  # Max 60% for keyword matching
        
        return 0.0
    
    def _score_manufacturer_match(self, hardware: DetectedHardware, profile: HardwareProfile) -> float:
        """Score manufacturer matching"""
        if not hardware.system_manufacturer:
            return 0.0
        
        hardware_mfg = hardware.system_manufacturer.lower().strip()
        
        # Normalize manufacturer names
        hardware_mfg = self.vendor_db.normalize_vendor_name(hardware_mfg).lower()
        
        # Check different manufacturer indicators
        manufacturer_indicators = {
            "apple": ["mac", "imac", "macbook", "mac mini", "mac pro"],
            "dell": ["dell", "optiplex", "inspiron", "latitude", "precision"],
            "hp": ["hp", "hewlett", "pavilion", "envy", "elitebook", "probook"],
            "lenovo": ["lenovo", "thinkpad", "ideapad", "yoga", "legion"],
            "asus": ["asus", "asustek", "rog", "zenbook", "vivobook"],
            "msi": ["msi", "micro-star", "gaming", "prestige"],
            "microsoft": ["surface", "microsoft"],
            "samsung": ["samsung", "galaxy book"],
            "acer": ["acer", "aspire", "predator", "swift"],
            "alienware": ["alienware", "dell alienware"]
        }
        
        profile_name = profile.name.lower()
        profile_model = profile.model.lower()
        
        for manufacturer, indicators in manufacturer_indicators.items():
            if manufacturer in hardware_mfg:
                # Check if any indicator appears in profile
                for indicator in indicators:
                    if indicator in profile_name or indicator in profile_model:
                        return 100.0  # Perfect manufacturer match
        
        # Generic matching for common manufacturers
        if hardware_mfg in profile_name or hardware_mfg in profile_model:
            return 90.0
        
        return 0.0
    
    def _score_platform_match(self, hardware: DetectedHardware, profile: HardwareProfile) -> float:
        """Score platform matching"""
        if not hardware.platform or not profile.platform:
            return 0.0
        
        if hardware.platform == profile.platform:
            return 100.0
        
        # Cross-platform compatibility scoring
        platform_compatibility = {
            "mac": ["mac"],  # Mac is exclusive
            "windows": ["windows", "generic"],  # Windows can use generic profiles
            "linux": ["linux", "generic"]   # Linux can use generic profiles
        }
        
        compatible_platforms = platform_compatibility.get(hardware.platform, [])
        if profile.platform in compatible_platforms:
            return 70.0  # Partial compatibility
        
        return 0.0
    
    def _score_architecture_match(self, hardware: DetectedHardware, profile: HardwareProfile) -> float:
        """Score CPU architecture matching"""
        if not hardware.cpu_architecture or not profile.architecture:
            return 0.0
        
        hardware_arch = hardware.cpu_architecture.lower()
        profile_arch = profile.architecture.lower()
        
        # Exact match
        if hardware_arch == profile_arch:
            return 100.0
        
        # Architecture compatibility mapping
        arch_compatibility = {
            "x86_64": ["x86_64", "amd64", "x64"],
            "arm64": ["arm64", "aarch64", "arm"],
            "x86": ["x86", "i386", "i686"]
        }
        
        for arch_family, compatible_archs in arch_compatibility.items():
            if hardware_arch in compatible_archs:
                if profile_arch in compatible_archs:
                    return 90.0  # High compatibility within family
        
        return 0.0
    
    def _score_cpu_match(self, hardware: DetectedHardware, profile: HardwareProfile) -> float:
        """Score CPU family/generation matching"""
        if not hardware.cpu_name or not profile.cpu_family:
            return 0.0
        
        # Use vendor database to identify CPU family
        cpu_info = self.vendor_db.identify_cpu(hardware.cpu_name)
        hardware_family = cpu_info.get("family", "").lower()
        hardware_vendor = cpu_info.get("vendor", "").lower()
        
        profile_family = profile.cpu_family.lower()
        
        # Exact family match
        if hardware_family and hardware_family in profile_family:
            return 100.0
        
        # Vendor matching
        if hardware_vendor:
            if hardware_vendor in profile_family:
                return 60.0  # Same vendor, different family
        
        # Generation/series matching (Intel Core i5/i7, AMD Ryzen 5/7, etc.)
        hardware_series = self._extract_cpu_series(hardware.cpu_name)
        profile_series = self._extract_cpu_series(profile.cpu_family)
        
        if hardware_series and profile_series:
            if hardware_series == profile_series:
                return 80.0  # Same series, might be different generation
        
        return 0.0
    
    def _score_year_match(self, hardware: DetectedHardware, profile: HardwareProfile) -> float:
        """Score manufacturing year proximity"""
        # This is complex without direct hardware year detection
        # For Mac, we can extract year from model identifiers
        if hardware.platform == "mac" and hardware.system_model:
            mac_info = self.vendor_db.lookup_mac_model(hardware.system_model)
            if mac_info and profile.year:
                hardware_year = mac_info.get("year")
                if hardware_year:
                    year_diff = abs(hardware_year - profile.year)
                    if year_diff == 0:
                        return 100.0
                    elif year_diff <= 1:
                        return 80.0
                    elif year_diff <= 3:
                        return 60.0
                    elif year_diff <= 5:
                        return 40.0
        
        return 0.0
    
    def _score_features_match(self, hardware: DetectedHardware, profile: HardwareProfile) -> float:
        """Score special features and hardware components matching"""
        score = 0.0
        feature_count = 0
        
        # GPU matching
        if hardware.gpus and profile.gpu_info:
            gpu_match = self._match_gpu_features(hardware.gpus, profile.gpu_info)
            score += gpu_match
            feature_count += 1
        
        # Network adapter matching
        if hardware.network_adapters and profile.network_adapters:
            network_match = self._match_network_features(hardware.network_adapters, profile.network_adapters)
            score += network_match
            feature_count += 1
        
        # Special requirements matching
        if hasattr(profile, 'special_requirements') and profile.special_requirements:
            special_match = self._match_special_requirements(hardware, profile.special_requirements)
            score += special_match
            feature_count += 1
        
        return score / feature_count if feature_count > 0 else 0.0
    
    def _match_gpu_features(self, hardware_gpus: List[Dict], profile_gpus: List[str]) -> float:
        """Match GPU features between hardware and profile"""
        if not hardware_gpus or not profile_gpus:
            return 0.0
        
        # Extract GPU vendors from detected hardware
        detected_vendors = set()
        for gpu in hardware_gpus:
            gpu_name = gpu.get("name", "")
            vendor_info = self.vendor_db.identify_gpu_vendor(gpu_name)
            if vendor_info["vendor"] != "Unknown":
                detected_vendors.add(vendor_info["vendor"].lower())
        
        # Check if profile GPU info mentions same vendors
        profile_gpu_text = " ".join(profile_gpus).lower()
        
        matches = 0
        for vendor in detected_vendors:
            if vendor in profile_gpu_text:
                matches += 1
        
        return (matches / len(detected_vendors)) * 100.0 if detected_vendors else 0.0
    
    def _match_network_features(self, hardware_adapters: List[Dict], profile_adapters: List[str]) -> float:
        """Match network adapter features"""
        if not hardware_adapters or not profile_adapters:
            return 0.0
        
        # Simple matching based on adapter names/manufacturers
        hardware_names = [adapter.get("name", "").lower() for adapter in hardware_adapters]
        profile_text = " ".join(profile_adapters).lower()
        
        matches = 0
        for name in hardware_names:
            if name and any(word in profile_text for word in name.split() if len(word) > 3):
                matches += 1
        
        return (matches / len(hardware_names)) * 100.0 if hardware_names else 0.0
    
    def _match_special_requirements(self, hardware: DetectedHardware, requirements: Dict[str, Any]) -> float:
        """Match special hardware requirements"""
        matches = 0
        total_requirements = len(requirements)
        
        for requirement, expected_value in requirements.items():
            if requirement == "secure_boot":
                # Check if this is a Surface or enterprise device
                if hardware.system_manufacturer and "microsoft" in hardware.system_manufacturer.lower():
                    matches += 1
            elif requirement == "surface_drivers":
                if hardware.system_manufacturer and "microsoft" in hardware.system_manufacturer.lower():
                    matches += 1
            elif requirement == "boot_partition":
                # This would require more detailed disk analysis
                matches += 0.5  # Partial credit
            # Add more special requirement checks as needed
        
        return (matches / total_requirements) * 100.0 if total_requirements > 0 else 0.0
    
    def _extract_cpu_series(self, cpu_name: str) -> Optional[str]:
        """Extract CPU series identifier from CPU name"""
        if not cpu_name:
            return None
        
        cpu_lower = cpu_name.lower()
        
        # Intel series patterns
        intel_patterns = [
            r"core\s*i3",
            r"core\s*i5", 
            r"core\s*i7",
            r"core\s*i9",
            r"xeon",
            r"celeron",
            r"pentium"
        ]
        
        for pattern in intel_patterns:
            match = re.search(pattern, cpu_lower)
            if match:
                return match.group(0).replace(" ", "")
        
        # AMD series patterns
        amd_patterns = [
            r"ryzen\s*3",
            r"ryzen\s*5",
            r"ryzen\s*7", 
            r"ryzen\s*9",
            r"threadripper",
            r"epyc",
            r"fx"
        ]
        
        for pattern in amd_patterns:
            match = re.search(pattern, cpu_lower)
            if match:
                return match.group(0).replace(" ", "")
        
        # Apple series patterns
        if re.search(r"apple.*m\d+", cpu_lower):
            match = re.search(r"m\d+(\s+pro|\s+max|\s+ultra)?", cpu_lower)
            if match:
                return match.group(0).replace(" ", "")
        
        return None
    
    def _calculate_match_confidence(self, match_score: float, hardware: DetectedHardware) -> DetectionConfidence:
        """Calculate overall match confidence based on score and hardware detection quality"""
        base_confidence = match_score / 100.0
        
        # Adjust confidence based on hardware detection quality
        detection_confidence_multiplier = {
            DetectionConfidence.EXACT_MATCH: 1.0,
            DetectionConfidence.HIGH_CONFIDENCE: 0.9,
            DetectionConfidence.MEDIUM_CONFIDENCE: 0.8,
            DetectionConfidence.LOW_CONFIDENCE: 0.6,
            DetectionConfidence.UNKNOWN: 0.4
        }
        
        multiplier = detection_confidence_multiplier.get(hardware.detection_confidence, 0.4)
        adjusted_confidence = base_confidence * multiplier
        
        # Map to confidence levels
        if adjusted_confidence >= 0.9:
            return DetectionConfidence.EXACT_MATCH
        elif adjusted_confidence >= 0.75:
            return DetectionConfidence.HIGH_CONFIDENCE
        elif adjusted_confidence >= 0.6:
            return DetectionConfidence.MEDIUM_CONFIDENCE
        elif adjusted_confidence >= 0.4:
            return DetectionConfidence.LOW_CONFIDENCE
        else:
            return DetectionConfidence.UNKNOWN
    
    def get_best_match(self, detected_hardware: DetectedHardware) -> Optional[ProfileMatch]:
        """Get the single best matching profile"""
        matches = self.find_matching_profiles(detected_hardware, max_results=1)
        return matches[0] if matches else None
    
    def suggest_generic_profile(self, detected_hardware: DetectedHardware) -> Optional[ProfileMatch]:
        """Suggest a generic profile when no specific matches are found"""
        # Find generic profiles for the platform
        generic_profiles = [
            p for p in self._available_profiles
            if "generic" in p.model.lower() and p.platform == detected_hardware.platform
        ]
        
        if generic_profiles:
            # Score the generic profiles
            best_generic = None
            best_score = 0.0
            
            for profile in generic_profiles:
                match = self._score_profile_match(detected_hardware, profile)
                if match.match_score > best_score:
                    best_score = match.match_score
                    best_generic = match
            
            if best_generic:
                best_generic.match_reasons.append("Generic fallback profile selected")
                return best_generic
        
        return None
    
    def explain_match(self, match: ProfileMatch) -> str:
        """Generate human-readable explanation of why a profile was matched"""
        if not match.match_reasons:
            return f"Profile selected with {match.match_score:.1f}% confidence"
        
        explanation_parts = [
            f"Selected '{match.profile.name}' with {match.match_score:.1f}% confidence ({match.get_confidence_text()}):",
            ""
        ]
        
        # Group reasons by importance
        for reason in match.match_reasons[:3]:  # Top 3 reasons
            explanation_parts.append(f"• {reason}")
        
        if len(match.match_reasons) > 3:
            explanation_parts.append(f"• ...and {len(match.match_reasons) - 3} other factors")
        
        return "\n".join(explanation_parts)