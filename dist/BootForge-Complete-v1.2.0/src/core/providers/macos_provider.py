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
import plistlib
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Any
from urllib.parse import urljoin, urlparse

from src.core.os_image_manager import (
    OSImageProvider, OSImageInfo, ImageStatus, VerificationMethod
)
from src.core.config import Config
from src.core.patch_pipeline import PatchPlanner
from src.core.hardware_detector import DetectedHardware
from src.core.models import HardwareProfile
from src.core.hardware_profiles import create_mac_hardware_profile, is_mac_oclp_compatible, get_recommended_macos_version_for_model
from src.core.safety_validator import SafetyValidator, PatchValidationMode
from src.core.oclp_integration import OCLPIntegration, OCLPCompatibility


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
        
        # OCLP Integration for unsupported Mac hardware
        self.oclp_integration = OCLPIntegration()
        
        self.logger.info("MacOSProvider initialized with COMPLIANT security mode and OCLP integration")
    
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
                "build": getattr(image_info, 'build', 'unknown'),
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
    
    def _parse_catalog(self, catalog_text: str) -> Optional[Dict[str, Any]]:
        """Parse Apple's software update catalog using proper plist parsing"""
        try:
            # Apple's catalogs are in plist XML format - parse properly
            catalog_data = plistlib.loads(catalog_text.encode('utf-8'))
            
            if not isinstance(catalog_data, dict):
                self.logger.warning("Catalog is not a dictionary structure")
                return None
            
            # Extract products section which contains all the package info
            products = catalog_data.get('Products', {})
            if not products:
                self.logger.warning("No Products section found in catalog")
                return None
            
            # Convert to simpler structure for processing
            packages = []
            for product_key, product_data in products.items():
                if not isinstance(product_data, dict):
                    continue
                    
                # Extract packages from this product
                product_packages = product_data.get('Packages', [])
                if not isinstance(product_packages, list):
                    continue
                    
                for package in product_packages:
                    if isinstance(package, dict):
                        # Add product metadata to each package
                        enhanced_package = package.copy()
                        enhanced_package['ProductKey'] = product_key
                        
                        # Add version info if available
                        if 'ExtendedMetaInfo' in product_data:
                            meta_info = product_data['ExtendedMetaInfo']
                            if isinstance(meta_info, dict):
                                enhanced_package.update(meta_info)
                        
                        packages.append(enhanced_package)
            
            return {"packages": packages}
            
        except Exception as e:
            self.logger.error(f"Failed to parse catalog with plist parser: {e}")
            # Fallback to trying as plain XML if plist parsing fails
            try:
                root = ET.fromstring(catalog_text)
                # Try to extract basic package info from XML
                packages = []
                # This would need more sophisticated XML parsing logic
                return {"packages": packages}
            except ET.ParseError:
                self.logger.error("Catalog is neither valid plist nor XML")
                return None
    
    def _is_macos_installer_package(self, package: Dict[str, Any]) -> bool:
        """Check if package is a macOS installer or recovery image"""
        try:
            url = package.get("URL", "")
            filename = url.split("/")[-1] if url else ""
            
            # Check for recovery images
            recovery_indicators = [
                "RecoveryHDUpdate", "RecoveryHDMetaDmg", "BaseSystem",
                "InstallESD", "InstallAssistant"
            ]
            
            # Check for installer packages
            installer_indicators = [
                "Install", "macOS", "OSInstall", "BaseSystem"
            ]
            
            # Check both URL and any metadata
            search_text = f"{url} {filename}".lower()
            
            return (any(indicator.lower() in search_text for indicator in recovery_indicators + installer_indicators) or
                    any(key.lower() in ["install", "recovery", "macos"] for key in package.keys()))
            
        except Exception:
            return False
    
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
                if not self._is_macos_installer_package(package):
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
                if not self._is_macos_installer_package(package):
                    continue
                
                # More specific filtering for full installers
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
    
    # ===== OCLP INTEGRATION METHODS =====
    
    def requires_oclp_integration(self, hardware: DetectedHardware, image_info: OSImageInfo) -> bool:
        """Determine if OCLP integration is required for this hardware/macOS combination"""
        try:
            if not hardware.system_model:
                return False  # Cannot determine without model info
            
            # Check if Mac model is OCLP compatible
            if not is_mac_oclp_compatible(hardware.system_model):
                return False  # Not an OCLP-compatible Mac
            
            # Create hardware profile to check compatibility
            hardware_profile = create_mac_hardware_profile(hardware.system_model)
            
            # Check if this macOS version needs OCLP patches for this model
            macos_version = image_info.version
            native_support = hardware_profile.native_macos_support.get(macos_version, False)
            
            # If not natively supported, OCLP is required
            if not native_support:
                self.logger.info(f"OCLP required: {hardware.system_model} does not natively support macOS {macos_version}")
                return True
            
            # Check for specific patch requirements even on supported versions
            required_patches = hardware_profile.required_patches.get(macos_version, [])
            if required_patches:
                self.logger.info(f"OCLP recommended: {hardware.system_model} has specific patch requirements for macOS {macos_version}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to determine OCLP requirement: {e}")
            return False  # Default to standard macOS installation
    
    def prepare_oclp_installer(self, image_info: OSImageInfo, hardware: DetectedHardware, 
                               target_mount_point: str, efi_mount_point: str) -> Tuple[bool, List[str]]:
        """Prepare macOS installer with OCLP integration"""
        try:
            self.logger.info(f"Preparing OCLP-enabled macOS installer for {hardware.get_summary()}")
            
            # Validate hardware compatibility
            if not hardware.system_model:
                return False, ["Cannot create OCLP installer without Mac model detection"]
            
            if not is_mac_oclp_compatible(hardware.system_model):
                return False, [f"Mac model {hardware.system_model} is not supported by OCLP"]
            
            # Get recommended macOS version for this hardware
            recommended_version = get_recommended_macos_version_for_model(hardware.system_model)
            if recommended_version and image_info.version < recommended_version:
                self.logger.warning(f"macOS {image_info.version} is older than recommended {recommended_version} for {hardware.system_model}")
            
            # Configure OCLP integration for this hardware
            oclp_config_success = self.oclp_integration.configure_for_hardware(
                model=hardware.system_model,
                macos_version=image_info.version
            )
            
            if not oclp_config_success:
                return False, ["Failed to configure OCLP for target hardware"]
            
            # Start OCLP build process
            build_success = self.oclp_integration.build_oclp_for_hardware()
            
            if not build_success:
                return False, ["OCLP build process failed"]
            
            # Get build results
            build_result = self.oclp_integration.get_build_result()
            if not build_result:
                return False, ["OCLP build completed but no results available"]
            
            # Stage OpenCore to EFI partition
            efi_success, efi_logs = self._stage_opencore_to_efi(build_result, efi_mount_point)
            if not efi_success:
                return False, efi_logs
            
            # Apply additional patches to the macOS installer
            patch_success, patch_logs = self._apply_oclp_installer_patches(
                build_result, target_mount_point
            )
            
            if not patch_success:
                return False, patch_logs
            
            success_logs = [
                f"OCLP installer prepared successfully for {hardware.system_model}",
                f"Target macOS version: {image_info.version}",
                f"OpenCore EFI staged to: {efi_mount_point}",
                f"Installer patches applied to: {target_mount_point}"
            ]
            success_logs.extend(efi_logs)
            success_logs.extend(patch_logs)
            
            return True, success_logs
            
        except Exception as e:
            error = f"Failed to prepare OCLP installer: {e}"
            self.logger.error(error)
            return False, [error]
    
    def _stage_opencore_to_efi(self, build_result, efi_mount_point: str) -> Tuple[bool, List[str]]:
        """Stage OpenCore build artifacts to EFI partition"""
        try:
            import shutil
            from pathlib import Path
            
            logs = []
            efi_path = Path(efi_mount_point)
            
            if not efi_path.exists():
                return False, [f"EFI mount point does not exist: {efi_mount_point}"]
            
            # Stage EFI folder structure
            if build_result.efi_folder_path and build_result.efi_folder_path.exists():
                dest_efi = efi_path / "EFI"
                
                # Remove existing EFI folder if present
                if dest_efi.exists():
                    shutil.rmtree(dest_efi)
                    logs.append("Removed existing EFI folder")
                
                # Copy OCLP EFI structure
                shutil.copytree(build_result.efi_folder_path, dest_efi)
                logs.append(f"Staged OpenCore EFI to {dest_efi}")
                
                # Verify critical files
                critical_files = [
                    dest_efi / "BOOT" / "BOOTx64.efi",
                    dest_efi / "OC" / "config.plist",
                    dest_efi / "OC" / "OpenCore.efi"
                ]
                
                for critical_file in critical_files:
                    if critical_file.exists():
                        logs.append(f"✓ Verified: {critical_file.name}")
                    else:
                        return False, [f"Missing critical file after staging: {critical_file}"]
            
            else:
                return False, ["No EFI folder available in OCLP build result"]
            
            return True, logs
            
        except Exception as e:
            error = f"Failed to stage OpenCore to EFI: {e}"
            self.logger.error(error)
            return False, [error]
    
    def _apply_oclp_installer_patches(self, build_result, target_mount_point: str) -> Tuple[bool, List[str]]:
        """Apply OCLP-specific patches to macOS installer"""
        try:
            import shutil
            from pathlib import Path
            
            logs = []
            target_path = Path(target_mount_point)
            
            if not target_path.exists():
                return False, [f"Target mount point does not exist: {target_mount_point}"]
            
            # Stage kext files to installer
            if build_result.kext_files:
                kexts_dest = target_path / "System" / "Library" / "Extensions"
                kexts_dest.mkdir(parents=True, exist_ok=True)
                
                for kext_file in build_result.kext_files:
                    if kext_file.exists():
                        dest_kext = kexts_dest / kext_file.name
                        if kext_file.is_dir():
                            if dest_kext.exists():
                                shutil.rmtree(dest_kext)
                            shutil.copytree(kext_file, dest_kext)
                        else:
                            shutil.copy2(kext_file, dest_kext)
                        logs.append(f"Staged kext: {kext_file.name}")
                
                logs.append(f"Staged {len(build_result.kext_files)} kext files")
            
            # Copy additional OCLP files if available
            if build_result.drivers_folder_path and build_result.drivers_folder_path.exists():
                drivers = list(build_result.drivers_folder_path.glob("*.efi"))
                logs.append(f"OCLP includes {len(drivers)} EFI drivers")
            
            if build_result.tools_folder_path and build_result.tools_folder_path.exists():
                tools = list(build_result.tools_folder_path.glob("*.efi"))
                logs.append(f"OCLP includes {len(tools)} EFI tools")
            
            logs.append("OCLP installer patches applied successfully")
            return True, logs
            
        except Exception as e:
            error = f"Failed to apply OCLP installer patches: {e}"
            self.logger.error(error)
            return False, [error]
    
    def get_oclp_compatibility_info(self, hardware: DetectedHardware) -> Dict[str, any]:
        """Get comprehensive OCLP compatibility information for detected hardware"""
        try:
            if not hardware.system_model:
                return {"compatible": False, "reason": "No Mac model detected"}
            
            # Check basic compatibility
            is_compatible = is_mac_oclp_compatible(hardware.system_model)
            if not is_compatible:
                return {"compatible": False, "reason": f"Mac model {hardware.system_model} is not supported by OCLP"}
            
            # Get hardware profile for detailed info
            hardware_profile = create_mac_hardware_profile(hardware.system_model)
            
            # Get recommended macOS version
            recommended_version = get_recommended_macos_version_for_model(hardware.system_model)
            
            # Get OCLP compatibility level
            compatibility_level = hardware_profile.oclp_compatibility
            
            return {
                "compatible": True,
                "model_name": hardware_profile.name,
                "compatibility_level": compatibility_level,
                "recommended_macos_version": recommended_version,
                "native_support": hardware_profile.native_macos_support,
                "required_patches": hardware_profile.required_patches,
                "graphics_patches": hardware_profile.graphics_patches,
                "audio_patches": hardware_profile.audio_patches,
                "wifi_bluetooth_patches": hardware_profile.wifi_bluetooth_patches,
                "usb_patches": hardware_profile.usb_patches,
                "sip_requirements": hardware_profile.sip_requirements,
                "notes": hardware_profile.notes
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get OCLP compatibility info: {e}")
            return {"compatible": False, "reason": f"Error checking compatibility: {e}"}
    
    def get_oclp_workflow_status(self) -> Dict[str, any]:
        """Get current status of OCLP workflow"""
        return {
            "integration_available": self.oclp_integration is not None,
            "oclp_executable_found": self.oclp_integration.check_oclp_availability() if self.oclp_integration else False,
            "current_build_status": self.oclp_integration.get_build_status() if self.oclp_integration else None,
            "build_result_available": bool(self.oclp_integration.get_build_result()) if self.oclp_integration else False
        }