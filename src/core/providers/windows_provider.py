"""
BootForge Windows OS Image Provider
Handles manual Windows ISO upload and verification with checksum support
"""

import os
import re
import json
import logging
import hashlib
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from urllib.parse import urlparse

from src.core.os_image_manager import (
    OSImageProvider, OSImageInfo, ImageStatus, VerificationMethod
)
from src.core.config import Config
from src.core.patch_pipeline import PatchPlanner
from src.core.hardware_detector import DetectedHardware
from src.core.models import HardwareProfile
from src.core.safety_validator import SafetyValidator, PatchValidationMode


class WindowsProvider(OSImageProvider):
    """Provider for Windows ISOs with manual upload and verification support"""
    
    # Known Windows versions and their identifiers
    WINDOWS_VERSIONS = {
        "11": {
            "name": "Windows 11",
            "editions": ["Home", "Pro", "Enterprise", "Education"],
            "min_size_gb": 4.0,
            "max_size_gb": 8.0
        },
        "10": {
            "name": "Windows 10",
            "editions": ["Home", "Pro", "Enterprise", "Education", "LTSC"],
            "min_size_gb": 3.5,
            "max_size_gb": 6.0
        },
        "server2022": {
            "name": "Windows Server 2022",
            "editions": ["Standard", "Datacenter", "Essentials"],
            "min_size_gb": 4.5,
            "max_size_gb": 8.0
        },
        "server2019": {
            "name": "Windows Server 2019",
            "editions": ["Standard", "Datacenter", "Essentials"],
            "min_size_gb": 4.0,
            "max_size_gb": 7.0
        }
    }
    
    # Common checksum sources for Windows ISOs
    CHECKSUM_SOURCES = {
        "microsoft_techbench": "https://www.microsoft.com/en-us/software-download/",
        "msdn_checksums": "https://msdn.microsoft.com/",
        "community_checksums": "https://files.rg-adguard.net/version/"  # Community-maintained checksums
    }
    
    def __init__(self, config: Config):
        super().__init__("windows", config)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Local image registry
        self._imported_images: List[OSImageInfo] = []
        self._checksum_database: Dict[str, str] = {}
        
        # Load known checksums
        self._load_checksum_database()
        
        # CRITICAL INTEGRATION: PatchPlanner with strict security defaults
        safety_validator = SafetyValidator(patch_mode=PatchValidationMode.COMPLIANT)
        self.patch_planner = PatchPlanner(safety_validator)
        self.logger.info("WindowsProvider initialized with COMPLIANT security mode")
    
    def _load_checksum_database(self):
        """Load known Windows ISO checksums from various sources"""
        # This would be populated with known good checksums
        # For now, we'll have a basic structure that can be extended
        self._checksum_database = {
            # Windows 11 22H2 checksums (example)
            "Win11_22H2_English_x64v1.iso": "4bc6c7e7c61af4b5d1b086c5d279947357cff45c2f82dcb6a83010a0f4f7ab38",
            "Win11_22H2_English_x32v1.iso": "b8c7e8c1e61af4b5d1b086c5d279947357cff45c2f82dcb6a83010a0f4f7ab39",
            
            # Windows 10 22H2 checksums (example)
            "Win10_22H2_English_x64.iso": "a6f470ca6d331eb4b4820f7b13e5c1e956c1de5b8b7f8c7b6a7f8c7b6a7f8c7b",
            "Win10_22H2_English_x32.iso": "b7f470ca6d331eb4b4820f7b13e5c1e956c1de5b8b7f8c7b6a7f8c7b6a7f8c7c",
        }
    
    def get_available_images(self) -> List[OSImageInfo]:
        """Get manually imported Windows images"""
        return self._imported_images.copy()
    
    def import_windows_iso(self, iso_path: str, version_hint: Optional[str] = None,
                          edition_hint: Optional[str] = None) -> Optional[OSImageInfo]:
        """Import a Windows ISO file into the image manager"""
        try:
            iso_path_obj = Path(iso_path)
            
            if not iso_path_obj.exists():
                self.logger.error(f"ISO file not found: {iso_path}")
                return None
            
            if not iso_path_obj.suffix.lower() == '.iso':
                self.logger.error(f"File is not an ISO: {iso_path}")
                return None
            
            # Analyze the ISO
            iso_info = self._analyze_windows_iso(iso_path_obj, version_hint, edition_hint)
            if not iso_info:
                self.logger.error(f"Could not analyze Windows ISO: {iso_path}")
                return None
            
            # Calculate checksum
            self.logger.info("Calculating ISO checksum...")
            checksum = self._calculate_sha256(str(iso_path_obj))
            
            # Create image info
            image_id = f"windows-{iso_info['version']}-{iso_info['architecture']}-{checksum[:8]}"
            
            image = OSImageInfo(
                id=image_id,
                name=f"{iso_info['display_name']} ({iso_info['architecture']})",
                os_family="windows",
                version=iso_info["version"],
                architecture=iso_info["architecture"],
                size_bytes=iso_path_obj.stat().st_size,
                download_url="",  # Local file
                local_path=str(iso_path_obj),
                checksum=checksum,
                checksum_type="sha256",
                verification_method=VerificationMethod.SHA256,
                status=ImageStatus.DOWNLOADED,  # Already local
                provider=self.name,
                metadata={
                    "edition": iso_info.get("edition", "Unknown"),
                    "build": iso_info.get("build", "Unknown"),
                    "language": iso_info.get("language", "Unknown"),
                    "filename": iso_path_obj.name,
                    "import_method": "manual",
                    "original_path": str(iso_path_obj),
                    "verified_checksum": self._verify_known_checksum(iso_path_obj.name, checksum)
                }
            )
            
            # Verify the image
            if self.verify_image(image, str(iso_path_obj)):
                image.status = ImageStatus.VERIFIED
                self._imported_images.append(image)
                self.logger.info(f"Successfully imported Windows ISO: {image.name}")
                return image
            else:
                self.logger.warning(f"ISO imported but verification failed: {image.name}")
                image.status = ImageStatus.FAILED
                return image
                
        except Exception as e:
            self.logger.error(f"Failed to import Windows ISO: {e}")
            return None
    
    def _analyze_windows_iso(self, iso_path: Path, version_hint: Optional[str] = None,
                           edition_hint: Optional[str] = None) -> Optional[Dict]:
        """Analyze Windows ISO to extract version information"""
        try:
            filename = iso_path.name.lower()
            
            # Extract information from filename
            version_info = self._extract_version_from_filename(filename, version_hint)
            architecture = self._extract_architecture_from_filename(filename)
            edition = self._extract_edition_from_filename(filename, edition_hint)
            language = self._extract_language_from_filename(filename)
            build = self._extract_build_from_filename(filename)
            
            # Validate file size
            file_size_gb = iso_path.stat().st_size / (1024 ** 3)
            if not self._validate_file_size(version_info, file_size_gb):
                self.logger.warning(f"File size {file_size_gb:.1f}GB seems unusual for {version_info}")
            
            # Create display name
            windows_info = self.WINDOWS_VERSIONS.get(version_info, {})
            base_name = windows_info.get("name", f"Windows {version_info}")
            
            if edition != "Unknown":
                display_name = f"{base_name} {edition}"
            else:
                display_name = base_name
            
            return {
                "version": version_info,
                "architecture": architecture,
                "edition": edition,
                "language": language,
                "build": build,
                "display_name": display_name,
                "file_size_gb": file_size_gb
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze Windows ISO: {e}")
            return None
    
    def _extract_version_from_filename(self, filename: str, hint: Optional[str] = None) -> str:
        """Extract Windows version from filename"""
        if hint:
            return hint
        
        # Common patterns
        patterns = [
            r'win(?:dows)?[\s_-]?11',
            r'win(?:dows)?[\s_-]?10',
            r'win(?:dows)?[\s_-]?server[\s_-]?2022',
            r'win(?:dows)?[\s_-]?server[\s_-]?2019',
            r'win(?:dows)?[\s_-]?8\.1',
            r'win(?:dows)?[\s_-]?8',
            r'win(?:dows)?[\s_-]?7'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                matched_text = match.group(0).lower()
                if '11' in matched_text:
                    return '11'
                elif '10' in matched_text:
                    return '10'
                elif 'server' in matched_text and '2022' in matched_text:
                    return 'server2022'
                elif 'server' in matched_text and '2019' in matched_text:
                    return 'server2019'
                elif '8.1' in matched_text:
                    return '8.1'
                elif '8' in matched_text:
                    return '8'
                elif '7' in matched_text:
                    return '7'
        
        # Default to 10 if can't determine
        self.logger.warning(f"Could not determine Windows version from filename: {filename}")
        return "10"
    
    def _extract_architecture_from_filename(self, filename: str) -> str:
        """Extract architecture from filename"""
        if any(arch in filename for arch in ['x64', 'amd64', '64-bit', '64bit']):
            return 'x86_64'
        elif any(arch in filename for arch in ['x86', 'x32', '32-bit', '32bit']):
            return 'i386'
        elif any(arch in filename for arch in ['arm64', 'aarch64']):
            return 'arm64'
        else:
            # Default to x64 for modern Windows
            return 'x86_64'
    
    def _extract_edition_from_filename(self, filename: str, hint: Optional[str] = None) -> str:
        """Extract Windows edition from filename"""
        if hint:
            return hint
        
        editions = ['enterprise', 'professional', 'pro', 'home', 'education', 'ltsc', 
                   'standard', 'datacenter', 'essentials']
        
        for edition in editions:
            if edition in filename:
                if edition == 'pro':
                    return 'Pro'
                elif edition == 'professional':
                    return 'Pro'
                else:
                    return edition.capitalize()
        
        return "Unknown"
    
    def _extract_language_from_filename(self, filename: str) -> str:
        """Extract language from filename"""
        languages = {
            'english': 'English',
            'en-us': 'English (US)',
            'en-gb': 'English (UK)',
            'spanish': 'Spanish',
            'french': 'French',
            'german': 'German',
            'chinese': 'Chinese',
            'japanese': 'Japanese'
        }
        
        for lang_key, lang_name in languages.items():
            if lang_key in filename:
                return lang_name
        
        return "Unknown"
    
    def _extract_build_from_filename(self, filename: str) -> str:
        """Extract build number from filename"""
        # Look for build patterns like 22H2, 21H2, 19041, etc.
        build_patterns = [
            r'(\d{2}H[12])',  # 22H2, 21H1, etc.
            r'(\d{5})',       # 19041, 22000, etc.
            r'build[\s_-]?(\d+)',
        ]
        
        for pattern in build_patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return "Unknown"
    
    def _validate_file_size(self, version: str, size_gb: float) -> bool:
        """Validate that file size is reasonable for Windows version"""
        version_info = self.WINDOWS_VERSIONS.get(version, {})
        min_size = version_info.get("min_size_gb", 3.0)
        max_size = version_info.get("max_size_gb", 10.0)
        
        return min_size <= size_gb <= max_size
    
    def _verify_known_checksum(self, filename: str, calculated_checksum: str) -> bool:
        """Check if calculated checksum matches known good checksums"""
        known_checksum = self._checksum_database.get(filename)
        if known_checksum:
            return known_checksum.lower() == calculated_checksum.lower()
        return False
    
    def search_images(self, query: str, os_family: Optional[str] = None) -> List[OSImageInfo]:
        """Search imported Windows images"""
        if os_family and os_family != "windows":
            return []
        
        results = []
        query_lower = query.lower()
        
        for image in self._imported_images:
            searchable_text = f"{image.name} {image.version} {image.metadata.get('edition', '')}"
            if query_lower in searchable_text.lower():
                results.append(image)
        
        return results
    
    def get_latest_image(self, os_family: str, version_pattern: Optional[str] = None) -> Optional[OSImageInfo]:
        """Get the latest imported Windows image"""
        if os_family != "windows":
            return None
        
        images = self._imported_images.copy()
        
        # Filter by version pattern if provided
        if version_pattern:
            pattern_lower = version_pattern.lower()
            images = [img for img in images if 
                     pattern_lower in img.version.lower() or 
                     pattern_lower in img.name.lower()]
        
        if not images:
            return None
        
        # Sort by version (prefer Windows 11 > 10 > older)
        def version_sort_key(image: OSImageInfo) -> Tuple:
            version = image.version
            if version == "11":
                return (11, 0)
            elif version == "10":
                return (10, 0)
            elif version.startswith("server"):
                # Extract year from server version
                year_match = re.search(r'(\d{4})', version)
                year = int(year_match.group(1)) if year_match else 2000
                return (0, year)  # Servers come after client OS
            else:
                try:
                    return (int(float(version)), 0)
                except:
                    return (0, 0)
        
        sorted_images = sorted(images, key=version_sort_key, reverse=True)
        return sorted_images[0]
    
    def verify_image(self, image_info: OSImageInfo, local_path: str) -> bool:
        """Verify Windows ISO"""
        try:
            self.logger.info(f"Verifying Windows ISO: {local_path}")
            
            # Check file exists
            if not os.path.exists(local_path):
                self.logger.error(f"File does not exist: {local_path}")
                return False
            
            # Check file size is reasonable
            file_size = os.path.getsize(local_path)
            if file_size < 1000000000:  # Less than 1GB
                self.logger.error(f"File too small to be Windows ISO: {file_size} bytes")
                return False
            
            # Verify checksum if available
            if image_info.checksum:
                if image_info.checksum_type == "sha256":
                    calculated = self._calculate_sha256(local_path)
                elif image_info.checksum_type == "md5":
                    calculated = self._calculate_md5(local_path)
                else:
                    self.logger.warning(f"Unsupported checksum type: {image_info.checksum_type}")
                    return True  # Skip checksum verification
                
                if calculated.lower() == image_info.checksum.lower():
                    self.logger.info("Windows ISO checksum verification successful")
                    return True
                else:
                    self.logger.error(f"Checksum mismatch: expected {image_info.checksum}, got {calculated}")
                    return False
            else:
                # No checksum - do basic file validation
                # Check if it's actually an ISO file (basic magic number check)
                with open(local_path, 'rb') as f:
                    # Read first few bytes to check ISO signature
                    header = f.read(32768)  # Read 32KB
                    
                    # Look for ISO 9660 signature or UDF signature
                    if b'CD001' in header or b'BEA01' in header or b'NSR0' in header:
                        self.logger.info("Windows ISO basic validation successful")
                        return True
                    else:
                        self.logger.warning("File does not appear to be a valid ISO")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Windows ISO verification failed: {e}")
            return False
    
    def _calculate_sha256(self, file_path: str) -> str:
        """Calculate SHA256 checksum"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def _calculate_md5(self, file_path: str) -> str:
        """Calculate MD5 checksum"""
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    
    def get_supported_families(self) -> List[str]:
        """Get supported OS families"""
        return ["windows"]
    
    def get_verification_methods(self) -> List[VerificationMethod]:
        """Get supported verification methods"""
        return [VerificationMethod.SHA256, VerificationMethod.MD5]
    
    def get_import_dialog_info(self) -> Dict[str, str]:
        """Get information for file import dialog"""
        return {
            "title": "Import Windows ISO",
            "file_filter": "ISO Files (*.iso);;All Files (*)",
            "instructions": """
            Select a Windows ISO file to import into BootForge.
            
            Supported Windows versions:
            • Windows 11 (Home, Pro, Enterprise, Education)
            • Windows 10 (Home, Pro, Enterprise, Education, LTSC)
            • Windows Server 2022 (Standard, Datacenter, Essentials)
            • Windows Server 2019 (Standard, Datacenter, Essentials)
            
            The ISO will be analyzed for version, edition, and architecture.
            A SHA256 checksum will be calculated for verification.
            """
        }