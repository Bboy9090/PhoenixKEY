"""
BootForge macOS OS Image Provider
Downloads and verifies macOS recovery images from Apple's Software Update catalogs
"""

import re
import os
import json
import logging
import hashlib
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from urllib.parse import urljoin, urlparse

from src.core.os_image_manager import (
    OSImageProvider, OSImageInfo, ImageStatus, VerificationMethod
)
from src.core.config import Config
from src.core.patch_pipeline import PatchPlanner
from src.core.hardware_detector import DetectedHardware
from src.core.models import HardwareProfile
from src.core.hardware_profiles import create_mac_hardware_profile
from src.core.safety_validator import SafetyValidator, PatchValidationMode


class MacOSProvider(OSImageProvider):
    """Provider for macOS recovery images from Apple's Software Update catalogs"""
    
    # Apple Software Update catalog URLs
    MACOS_CATALOGS = {
        "14": "https://swscan.apple.com/content/catalogs/others/index-14-13-12-10.16-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog",
        "13": "https://swscan.apple.com/content/catalogs/others/index-13-12-10.16-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog",
        "12": "https://swscan.apple.com/content/catalogs/others/index-12-10.16-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog",
        "11": "https://swscan.apple.com/content/catalogs/others/index-10.16-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog",
        "10.15": "https://swscan.apple.com/content/catalogs/others/index-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog"
    }
    
    # Known macOS versions and their details
    MACOS_VERSIONS = {
        "14": {"name": "macOS Sonoma", "min_version": "14.0"},
        "13": {"name": "macOS Ventura", "min_version": "13.0"},
        "12": {"name": "macOS Monterey", "min_version": "12.0"},
        "11": {"name": "macOS Big Sur", "min_version": "11.0"},
        "10.15": {"name": "macOS Catalina", "min_version": "10.15.0"},
        "10.14": {"name": "macOS Mojave", "min_version": "10.14.0"},
        "10.13": {"name": "macOS High Sierra", "min_version": "10.13.0"}
    }
    
    def __init__(self, config: Config):
        super().__init__("macos", config)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        # Cache for catalog data
        self._catalog_cache: Dict[str, Dict] = {}
        self._cache_expires = 0
        self._image_cache: List[OSImageInfo] = []
        
        # CRITICAL INTEGRATION: PatchPlanner with strict security defaults
        safety_validator = SafetyValidator(patch_mode=PatchValidationMode.COMPLIANT)
        self.patch_planner = PatchPlanner(safety_validator)
        self.logger.info("MacOSProvider initialized with COMPLIANT security mode")
    
    def get_available_images(self) -> List[OSImageInfo]:
        """Get all available macOS recovery images"""
        import time
        
        # Use cache if still valid (2 hours for macOS)
        if time.time() < self._cache_expires and self._image_cache:
            return self._image_cache.copy()
        
        images = []
        
        # Process each catalog
        for major_version, catalog_url in self.MACOS_CATALOGS.items():
            try:
                catalog_images = self._process_catalog(major_version, catalog_url)
                images.extend(catalog_images)
            except Exception as e:
                self.logger.warning(f"Failed to process catalog for macOS {major_version}: {e}")
        
        # Update cache
        self._image_cache = images
        self._cache_expires = time.time() + 7200  # Cache for 2 hours
        
        return images.copy()
    
    def prepare_patched_image(self, image_info: OSImageInfo, hardware: DetectedHardware, 
                             target_mount_point: str, dry_run: bool = True) -> Tuple[bool, List[str]]:
        """Prepare macOS image with hardware-specific patches using PatchPlanner"""
        try:
            self.logger.info(f"Preparing patched macOS image for {hardware.get_summary()}")
            
            # Create Mac hardware profile from detected hardware
            if hardware.system_model:
                hardware_profile = create_mac_hardware_profile(hardware.system_model)
            else:
                self.logger.warning("No system model detected, using generic Mac profile")
                hardware_profile = HardwareProfile(
                    name="Generic Mac",
                    platform="mac", 
                    model="unknown",
                    architecture="x86_64"
                )
            
            # Prepare OS info
            os_info = {
                "family": "macos",
                "version": image_info.version,
                "build": image_info.build_number,
                "edition": getattr(image_info, 'edition', 'Standard')
            }
            
            # Create patch plan using PatchPlanner
            patch_plan = self.patch_planner.create_patch_plan(
                hardware=hardware,
                os_info=os_info,
                hardware_profile=hardware_profile
            )
            
            if not patch_plan:
                return True, ["No patches required for this hardware/OS combination"]
            
            # Apply patches with strict security controls
            success, execution_log = self.patch_planner.apply_patch_plan(
                plan=patch_plan,
                target_mount_point=target_mount_point,
                dry_run=dry_run
            )
            
            if success:
                self.logger.info(f"macOS image patching {'simulated' if dry_run else 'completed'} successfully")
            else:
                self.logger.error(f"macOS image patching failed: {execution_log[-1] if execution_log else 'Unknown error'}")
            
            return success, execution_log
            
        except Exception as e:
            error = f"Failed to prepare patched macOS image: {e}"
            self.logger.error(error)
            return False, [error]
    
    def get_recommended_patches(self, image_info: OSImageInfo, hardware: DetectedHardware) -> List[str]:
        """Get list of recommended patches for macOS image and hardware combination"""
        try:
            # Create hardware profile
            if hardware.system_model:
                hardware_profile = create_mac_hardware_profile(hardware.system_model)
            else:
                return []  # No patches for unknown hardware
            
            # Prepare OS info
            os_info = {
                "family": "macos",
                "version": image_info.version,
                "build": image_info.build_number
            }
            
            # Get patch plan
            patch_plan = self.patch_planner.create_patch_plan(
                hardware=hardware,
                os_info=os_info,
                hardware_profile=hardware_profile
            )
            
            if not patch_plan:
                return []
            
            # Extract patch names
            patch_names = []
            for patch_set in patch_plan.patch_sets:
                patch_names.append(f"{patch_set.name} ({patch_set.id})")
                for action in patch_set.actions:
                    patch_names.append(f"  - {action.name} ({action.patch_type.value})")
            
            return patch_names
            
        except Exception as e:
            self.logger.error(f"Failed to get recommended patches: {e}")
            return []
    
    def _process_catalog(self, major_version: str, catalog_url: str) -> List[OSImageInfo]:
        """Process Apple's software update catalog"""
        images = []
        
        try:
            self.logger.info(f"Processing macOS {major_version} catalog...")
            
            # Download catalog
            response = self.session.get(catalog_url, timeout=30)
            response.raise_for_status()
            
            # Parse catalog (Apple uses property list format)
            catalog_data = self._parse_catalog(response.text)
            
            if not catalog_data:
                self.logger.warning(f"Could not parse catalog for macOS {major_version}")
                return images
            
            # Find recovery images in catalog
            recovery_images = self._extract_recovery_images(catalog_data, major_version)
            images.extend(recovery_images)
            
            # Also look for InstallAssistant packages (newer method)
            installer_images = self._extract_installer_images(catalog_data, major_version)
            images.extend(installer_images)
            
        except Exception as e:
            self.logger.error(f"Failed to process catalog for macOS {major_version}: {e}")
        
        return images
    
    def _parse_catalog(self, catalog_text: str) -> Optional[Dict]:
        """Parse Apple's software update catalog (simplified XML parsing)"""
        try:
            # Apple's catalogs are in a proprietary plist format
            # We'll try to extract useful information using regex patterns
            
            # Look for package references
            package_pattern = re.compile(r'<key>Packages</key>\s*<array>(.*?)</array>', re.DOTALL)
            package_match = package_pattern.search(catalog_text)
            
            if not package_match:
                return None
            
            packages_section = package_match.group(1)
            
            # Extract individual packages
            packages = []
            dict_pattern = re.compile(r'<dict>(.*?)</dict>', re.DOTALL)
            
            for dict_match in dict_pattern.finditer(packages_section):
                package_data = self._parse_package_dict(dict_match.group(1))
                if package_data:
                    packages.append(package_data)
            
            return {"packages": packages}
            
        except Exception as e:
            self.logger.error(f"Failed to parse catalog: {e}")
            return None
    
    def _parse_package_dict(self, dict_content: str) -> Optional[Dict]:
        """Parse individual package dictionary from catalog"""
        try:
            package = {}
            
            # Extract key-value pairs
            key_pattern = re.compile(r'<key>(.*?)</key>\s*<string>(.*?)</string>')
            for match in key_pattern.finditer(dict_content):
                key, value = match.groups()
                package[key] = value
            
            # Extract integer values
            int_pattern = re.compile(r'<key>(.*?)</key>\s*<integer>(.*?)</integer>')
            for match in int_pattern.finditer(dict_content):
                key, value = match.groups()
                package[key] = int(value)
            
            return package if package else None
            
        except Exception as e:
            self.logger.debug(f"Failed to parse package dict: {e}")
            return None
    
    def _extract_recovery_images(self, catalog_data: Dict, major_version: str) -> List[OSImageInfo]:
        """Extract recovery images from catalog data"""
        images = []
        
        try:
            packages = catalog_data.get("packages", [])
            
            for package in packages:
                # Look for recovery-related packages
                url = package.get("URL", "")
                filename = package.get("Filename", "")
                size = package.get("Size", 0)
                
                if not url or not filename:
                    continue
                
                # Filter for recovery-related files
                if not self._is_recovery_package(url, filename):
                    continue
                
                # Extract version information
                version_info = self._extract_version_info(url, filename, major_version)
                if not version_info:
                    continue
                
                # Create image info
                image_id = f"macos-{version_info['version']}-recovery"
                version_name = self.MACOS_VERSIONS.get(major_version, {}).get("name", f"macOS {major_version}")
                
                image = OSImageInfo(
                    id=image_id,
                    name=f"{version_name} Recovery ({version_info['version']})",
                    os_family="macos",
                    version=version_info["version"],
                    architecture="x86_64",  # Most recovery images are universal or x86_64
                    size_bytes=size,
                    download_url=url,
                    checksum=package.get("SHA1", package.get("MD5")),
                    checksum_type="sha1" if package.get("SHA1") else "md5",
                    verification_method=VerificationMethod.SHA256,  # We'll calculate SHA256
                    status=ImageStatus.AVAILABLE,
                    provider=self.name,
                    metadata={
                        "major_version": major_version,
                        "filename": filename,
                        "package_type": "recovery",
                        "architecture_hint": self._detect_architecture_hint(url, filename)
                    }
                )
                
                images.append(image)
                
        except Exception as e:
            self.logger.error(f"Failed to extract recovery images: {e}")
        
        return images
    
    def _extract_installer_images(self, catalog_data: Dict, major_version: str) -> List[OSImageInfo]:
        """Extract InstallAssistant packages (full installers)"""
        images = []
        
        try:
            packages = catalog_data.get("packages", [])
            
            for package in packages:
                url = package.get("URL", "")
                filename = package.get("Filename", "")
                size = package.get("Size", 0)
                
                if not url or not filename:
                    continue
                
                # Look for InstallAssistant packages
                if not ("InstallAssistant" in filename or "Install" in filename):
                    continue
                
                # Skip if it's clearly not a full installer
                if size < 1000000000:  # Less than 1GB is probably not a full installer
                    continue
                
                # Extract version
                version_info = self._extract_version_info(url, filename, major_version)
                if not version_info:
                    continue
                
                # Create image info
                image_id = f"macos-{version_info['version']}-installer"
                version_name = self.MACOS_VERSIONS.get(major_version, {}).get("name", f"macOS {major_version}")
                
                image = OSImageInfo(
                    id=image_id,
                    name=f"{version_name} Installer ({version_info['version']})",
                    os_family="macos",
                    version=version_info["version"],
                    architecture="universal",
                    size_bytes=size,
                    download_url=url,
                    checksum=package.get("SHA1", package.get("MD5")),
                    checksum_type="sha1" if package.get("SHA1") else "md5",
                    verification_method=VerificationMethod.SHA256,
                    status=ImageStatus.AVAILABLE,
                    provider=self.name,
                    metadata={
                        "major_version": major_version,
                        "filename": filename,
                        "package_type": "installer",
                        "architecture_hint": "universal"
                    }
                )
                
                images.append(image)
                
        except Exception as e:
            self.logger.error(f"Failed to extract installer images: {e}")
        
        return images
    
    def _is_recovery_package(self, url: str, filename: str) -> bool:
        """Check if package is related to recovery"""
        recovery_indicators = [
            "recovery", "RecoveryHDUpdate", "RecoveryOS",
            "BaseSystem", "boot.efi", "macOSUpd"
        ]
        
        text_to_check = f"{url} {filename}".lower()
        return any(indicator.lower() in text_to_check for indicator in recovery_indicators)
    
    def _extract_version_info(self, url: str, filename: str, major_version: str) -> Optional[Dict]:
        """Extract version information from URL/filename"""
        # Try to extract version from filename or URL
        version_patterns = [
            r'(\d+\.\d+\.\d+)',  # x.y.z
            r'(\d+\.\d+)',       # x.y
            r'macOS(\d+)',       # macOS14
        ]
        
        text_to_search = f"{url} {filename}"
        
        for pattern in version_patterns:
            match = re.search(pattern, text_to_search)
            if match:
                version = match.group(1)
                
                # Validate version makes sense for major version
                if self._version_matches_major(version, major_version):
                    return {"version": version}
        
        # Fallback to major version
        return {"version": major_version}
    
    def _version_matches_major(self, version: str, major_version: str) -> bool:
        """Check if extracted version matches expected major version"""
        try:
            if "." in version:
                version_major = version.split(".")[0]
            else:
                version_major = version
            
            if "." in major_version:
                expected_major = major_version.split(".")[0]
            else:
                expected_major = major_version
            
            return version_major == expected_major
        except:
            return False
    
    def _detect_architecture_hint(self, url: str, filename: str) -> str:
        """Detect architecture hints from URL/filename"""
        text = f"{url} {filename}".lower()
        
        if "arm64" in text or "apple silicon" in text:
            return "arm64"
        elif "intel" in text or "x86_64" in text:
            return "x86_64"
        else:
            return "universal"
    
    def search_images(self, query: str, os_family: Optional[str] = None) -> List[OSImageInfo]:
        """Search for macOS images matching query"""
        if os_family and os_family != "macos":
            return []
        
        all_images = self.get_available_images()
        results = []
        
        query_lower = query.lower()
        
        for image in all_images:
            # Search in name, version, and metadata
            searchable_text = f"{image.name} {image.version} {image.metadata.get('major_version', '')}"
            
            if query_lower in searchable_text.lower():
                results.append(image)
        
        return results
    
    def get_latest_image(self, os_family: str, version_pattern: Optional[str] = None) -> Optional[OSImageInfo]:
        """Get the latest macOS image"""
        if os_family != "macos":
            return None
        
        images = self.get_available_images()
        
        # Filter by version pattern if provided
        if version_pattern:
            pattern_lower = version_pattern.lower()
            images = [img for img in images if 
                     pattern_lower in img.version.lower() or 
                     pattern_lower in img.name.lower()]
        
        # Prefer installers over recovery images
        installer_images = [img for img in images if img.metadata.get("package_type") == "installer"]
        if installer_images:
            # Sort by version (newest first)
            return sorted(installer_images, 
                         key=lambda x: self._version_sort_key(x.version), 
                         reverse=True)[0]
        
        # Fall back to recovery images
        recovery_images = [img for img in images if img.metadata.get("package_type") == "recovery"]
        if recovery_images:
            return sorted(recovery_images, 
                         key=lambda x: self._version_sort_key(x.version), 
                         reverse=True)[0]
        
        return None
    
    def _version_sort_key(self, version: str) -> Tuple:
        """Create sort key for version strings"""
        try:
            # Handle versions like "14.0.1" or "13"
            parts = version.split('.')
            return tuple(int(part) for part in parts)
        except:
            return (0,)
    
    def verify_image(self, image_info: OSImageInfo, local_path: str) -> bool:
        """Verify macOS image checksum"""
        try:
            self.logger.info(f"Verifying macOS image: {local_path}")
            
            # Calculate file checksum
            if image_info.checksum_type == "sha1":
                actual_checksum = self._calculate_sha1(local_path)
            elif image_info.checksum_type == "md5":
                actual_checksum = self._calculate_md5(local_path)
            else:
                # Default to SHA256
                actual_checksum = self._calculate_sha256(local_path)
            
            # Compare with expected checksum
            if image_info.checksum:
                expected = image_info.checksum.lower()
                actual = actual_checksum.lower()
                
                if expected == actual:
                    self.logger.info("macOS image verification successful")
                    return True
                else:
                    self.logger.error(f"Checksum mismatch: expected {expected}, got {actual}")
                    return False
            else:
                # No checksum available - just verify file exists and is reasonable size
                file_size = os.path.getsize(local_path)
                if file_size > 100000000:  # At least 100MB
                    self.logger.info("macOS image verification passed (no checksum available)")
                    return True
                else:
                    self.logger.error("File too small to be valid macOS image")
                    return False
                    
        except Exception as e:
            self.logger.error(f"macOS image verification failed: {e}")
            return False
    
    def _calculate_sha1(self, file_path: str) -> str:
        """Calculate SHA1 checksum"""
        sha1_hash = hashlib.sha1()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha1_hash.update(chunk)
        return sha1_hash.hexdigest()
    
    def _calculate_md5(self, file_path: str) -> str:
        """Calculate MD5 checksum"""
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    
    def _calculate_sha256(self, file_path: str) -> str:
        """Calculate SHA256 checksum"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def get_supported_families(self) -> List[str]:
        """Get supported OS families"""
        return ["macos"]
    
    def get_verification_methods(self) -> List[VerificationMethod]:
        """Get supported verification methods"""
        return [VerificationMethod.SHA256, VerificationMethod.SHA1, VerificationMethod.MD5]