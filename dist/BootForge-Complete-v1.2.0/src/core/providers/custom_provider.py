"""
BootForge Custom OS Image Provider
Flexible provider for user-provided images with customizable verification options
"""

import os
import re
import json
import logging
import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Union
from datetime import datetime

from src.core.os_image_manager import (
    OSImageProvider, OSImageInfo, ImageStatus, VerificationMethod
)
from src.core.config import Config


class CustomProvider(OSImageProvider):
    """Provider for custom user-provided OS images with flexible verification"""
    
    # Supported file formats and their characteristics
    SUPPORTED_FORMATS = {
        ".iso": {
            "name": "ISO Image",
            "description": "Standard ISO 9660 optical disc image",
            "typical_os": ["linux", "windows", "macos"],
            "magic_bytes": [b"CD001", b"BEA01", b"NSR0"],
            "min_size_mb": 100,
            "max_size_gb": 20
        },
        ".img": {
            "name": "Disk Image",
            "description": "Raw disk image file",
            "typical_os": ["linux", "embedded"],
            "magic_bytes": [],  # No specific magic bytes
            "min_size_mb": 10,
            "max_size_gb": 50
        },
        ".dmg": {
            "name": "Apple Disk Image",
            "description": "Apple macOS disk image",
            "typical_os": ["macos"],
            "magic_bytes": [b"koly"],  # DMG signature
            "min_size_mb": 100,
            "max_size_gb": 15
        },
        ".vhd": {
            "name": "Virtual Hard Disk",
            "description": "Microsoft Virtual Hard Disk",
            "typical_os": ["windows"],
            "magic_bytes": [b"conectix"],  # VHD signature
            "min_size_mb": 500,
            "max_size_gb": 100
        },
        ".vhdx": {
            "name": "Virtual Hard Disk Extended",
            "description": "Microsoft VHDX format",
            "typical_os": ["windows"],
            "magic_bytes": [b"vhdxfile"],
            "min_size_mb": 500,
            "max_size_gb": 100
        },
        ".vmdk": {
            "name": "VMware Disk",
            "description": "VMware virtual disk format",
            "typical_os": ["linux", "windows", "macos"],
            "magic_bytes": [b"KDMV"],  # VMDK signature
            "min_size_mb": 100,
            "max_size_gb": 100
        }
    }
    
    # Common architecture patterns
    ARCH_PATTERNS = {
        "x86_64": ["x64", "amd64", "x86_64", "64-bit", "64bit"],
        "i386": ["x86", "i386", "32-bit", "32bit"],
        "arm64": ["arm64", "aarch64", "arm_64"],
        "arm": ["arm", "armv7", "armhf"],
        "universal": ["universal", "fat", "multi-arch"]
    }
    
    def __init__(self, config: Config):
        super().__init__("custom", config)
        
        # Custom image registry
        self._custom_images: List[OSImageInfo] = []
        
        # Load existing custom images from cache
        self._load_custom_images()
    
    def _load_custom_images(self):
        """Load previously imported custom images from cache file"""
        try:
            cache_file = self.config.get_app_dir() / "cache" / "custom_images.json"
            
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    
                for image_data in data.get("images", []):
                    # Reconstruct OSImageInfo from saved data
                    image = OSImageInfo(
                        id=image_data["id"],
                        name=image_data["name"],
                        os_family=image_data["os_family"],
                        version=image_data["version"],
                        architecture=image_data["architecture"],
                        size_bytes=image_data["size_bytes"],
                        download_url=image_data.get("download_url", ""),
                        local_path=image_data.get("local_path"),
                        checksum=image_data.get("checksum"),
                        checksum_type=image_data.get("checksum_type", "sha256"),
                        verification_method=VerificationMethod(image_data.get("verification_method", "sha256")),
                        status=ImageStatus(image_data.get("status", "unknown")),
                        provider=self.name,
                        metadata=image_data.get("metadata", {})
                    )
                    
                    # Verify file still exists
                    if image.local_path and os.path.exists(image.local_path):
                        self._custom_images.append(image)
                    else:
                        self.logger.warning(f"Custom image file missing: {image.local_path}")
                        
        except Exception as e:
            self.logger.warning(f"Failed to load custom images cache: {e}")
    
    def _save_custom_images(self):
        """Save custom images to cache file"""
        try:
            cache_dir = self.config.get_app_dir() / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = cache_dir / "custom_images.json"
            
            data = {
                "version": "1.0",
                "updated": datetime.now().isoformat(),
                "images": []
            }
            
            for image in self._custom_images:
                data["images"].append({
                    "id": image.id,
                    "name": image.name,
                    "os_family": image.os_family,
                    "version": image.version,
                    "architecture": image.architecture,
                    "size_bytes": image.size_bytes,
                    "download_url": image.download_url,
                    "local_path": image.local_path,
                    "checksum": image.checksum,
                    "checksum_type": image.checksum_type,
                    "verification_method": image.verification_method.value,
                    "status": image.status.value,
                    "metadata": image.metadata
                })
            
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save custom images cache: {e}")
    
    def get_available_images(self) -> List[OSImageInfo]:
        """Get all custom imported images"""
        return self._custom_images.copy()
    
    def import_custom_image(self, image_path: str, name: Optional[str] = None,
                          os_family: Optional[str] = None, version: Optional[str] = None,
                          architecture: Optional[str] = None, 
                          expected_checksum: Optional[str] = None,
                          checksum_type: str = "sha256",
                          verification_method: VerificationMethod = VerificationMethod.SHA256,
                          additional_metadata: Optional[Dict] = None) -> Optional[OSImageInfo]:
        """Import a custom image file with flexible verification options"""
        try:
            image_path_obj = Path(image_path)
            
            if not image_path_obj.exists():
                self.logger.error(f"Image file not found: {image_path}")
                return None
            
            # Analyze the file
            file_info = self._analyze_image_file(image_path_obj)
            if not file_info:
                self.logger.error(f"Could not analyze image file: {image_path}")
                return None
            
            # Use provided metadata or auto-detected values
            final_name = name or self._generate_default_name(image_path_obj, file_info)
            final_os_family = os_family or file_info.get("suggested_os_family", "unknown")
            final_version = version or file_info.get("suggested_version", "unknown")
            final_architecture = architecture or file_info.get("suggested_architecture", "unknown")
            
            # Calculate checksum if not provided or for verification
            self.logger.info(f"Calculating {checksum_type} checksum...")
            calculated_checksum = self._calculate_checksum(str(image_path_obj), checksum_type)
            
            # Verify checksum if provided
            checksum_verified = True
            if expected_checksum:
                checksum_verified = (calculated_checksum.lower() == expected_checksum.lower())
                if not checksum_verified:
                    self.logger.error(f"Checksum verification failed!")
                    self.logger.error(f"Expected: {expected_checksum}")
                    self.logger.error(f"Calculated: {calculated_checksum}")
            
            # Create image info
            import uuid
            image_id = f"custom-{uuid.uuid4().hex[:8]}"
            
            # Prepare metadata
            metadata = {
                "file_format": file_info["format"],
                "format_description": file_info["format_description"],
                "original_filename": image_path_obj.name,
                "import_date": datetime.now().isoformat(),
                "file_info": file_info,
                "user_provided_checksum": expected_checksum,
                "checksum_verified": checksum_verified,
                "import_method": "custom"
            }
            
            if additional_metadata:
                metadata.update(additional_metadata)
            
            image = OSImageInfo(
                id=image_id,
                name=final_name,
                os_family=final_os_family,
                version=final_version,
                architecture=final_architecture,
                size_bytes=image_path_obj.stat().st_size,
                download_url="",  # Local file
                local_path=str(image_path_obj),
                checksum=calculated_checksum,
                checksum_type=checksum_type,
                verification_method=verification_method,
                status=ImageStatus.DOWNLOADED,
                provider=self.name,
                metadata=metadata
            )
            
            # Verify the image
            if self.verify_image(image, str(image_path_obj)):
                image.status = ImageStatus.VERIFIED if checksum_verified else ImageStatus.DOWNLOADED
                self._custom_images.append(image)
                self._save_custom_images()
                self.logger.info(f"Successfully imported custom image: {image.name}")
                return image
            else:
                self.logger.warning(f"Image imported but verification failed: {image.name}")
                image.status = ImageStatus.FAILED
                return image
                
        except Exception as e:
            self.logger.error(f"Failed to import custom image: {e}")
            return None
    
    def _analyze_image_file(self, file_path: Path) -> Optional[Dict]:
        """Analyze image file to extract information"""
        try:
            filename = file_path.name.lower()
            file_ext = file_path.suffix.lower()
            file_size = file_path.stat().st_size
            
            # Get format information
            format_info = self.SUPPORTED_FORMATS.get(file_ext)
            if not format_info:
                # Try to detect by magic bytes
                format_info = self._detect_format_by_magic(file_path)
            
            if not format_info:
                format_info = {
                    "name": "Unknown Format",
                    "description": f"Unknown format ({file_ext})",
                    "typical_os": ["unknown"],
                    "magic_bytes": [],
                    "min_size_mb": 0,
                    "max_size_gb": 1000
                }
            
            # Validate file size
            size_mb = file_size / (1024 * 1024)
            size_gb = file_size / (1024 * 1024 * 1024)
            size_valid = (size_mb >= format_info["min_size_mb"] and 
                         size_gb <= format_info["max_size_gb"])
            
            # Extract metadata from filename
            suggested_os = self._suggest_os_family(filename, format_info)
            suggested_arch = self._suggest_architecture(filename)
            suggested_version = self._suggest_version(filename)
            
            return {
                "format": file_ext,
                "format_description": format_info["description"],
                "size_mb": size_mb,
                "size_gb": size_gb,
                "size_valid": size_valid,
                "suggested_os_family": suggested_os,
                "suggested_architecture": suggested_arch,
                "suggested_version": suggested_version,
                "format_info": format_info
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze image file: {e}")
            return None
    
    def _detect_format_by_magic(self, file_path: Path) -> Optional[Dict]:
        """Detect file format by magic bytes"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(8192)  # Read first 8KB
            
            for ext, format_info in self.SUPPORTED_FORMATS.items():
                for magic in format_info["magic_bytes"]:
                    if magic in header:
                        return format_info
            
            return None
            
        except Exception:
            return None
    
    def _suggest_os_family(self, filename: str, format_info: Dict) -> str:
        """Suggest OS family based on filename and format"""
        # Check filename for OS indicators
        os_indicators = {
            "linux": ["ubuntu", "debian", "centos", "rhel", "fedora", "opensuse", "mint", "arch", "linux"],
            "windows": ["windows", "win10", "win11", "server", "microsoft"],
            "macos": ["macos", "osx", "darwin", "apple", "mac"],
            "freebsd": ["freebsd", "bsd"],
            "embedded": ["raspberry", "pi", "embedded", "iot", "firmware"]
        }
        
        filename_lower = filename.lower()
        
        for os_family, indicators in os_indicators.items():
            if any(indicator in filename_lower for indicator in indicators):
                return os_family
        
        # Fall back to format typical OS
        typical_os = format_info.get("typical_os", ["unknown"])
        return typical_os[0] if typical_os else "unknown"
    
    def _suggest_architecture(self, filename: str) -> str:
        """Suggest architecture based on filename"""
        filename_lower = filename.lower()
        
        for arch, patterns in self.ARCH_PATTERNS.items():
            if any(pattern in filename_lower for pattern in patterns):
                return arch
        
        return "unknown"
    
    def _suggest_version(self, filename: str) -> str:
        """Suggest version based on filename"""
        # Look for version patterns
        version_patterns = [
            r'(\d+\.\d+\.\d+)',  # x.y.z
            r'(\d+\.\d+)',       # x.y
            r'v(\d+)',          # v1, v2, etc.
            r'(\d{4})',         # Year
        ]
        
        for pattern in version_patterns:
            match = re.search(pattern, filename)
            if match:
                return match.group(1)
        
        return "unknown"
    
    def _generate_default_name(self, file_path: Path, file_info: Dict) -> str:
        """Generate a default name for the image"""
        base_name = file_path.stem
        
        # Clean up the filename
        base_name = re.sub(r'[_-]', ' ', base_name)
        base_name = ' '.join(word.capitalize() for word in base_name.split())
        
        # Add format information if not obvious
        format_name = file_info["format_info"]["name"]
        if not any(fmt.lower() in base_name.lower() for fmt in ["iso", "image", "disk"]):
            base_name = f"{base_name} ({format_name})"
        
        return base_name
    
    def _calculate_checksum(self, file_path: str, checksum_type: str) -> str:
        """Calculate file checksum"""
        if checksum_type.lower() == "sha256":
            return self._calculate_sha256(file_path)
        elif checksum_type.lower() == "sha1":
            return self._calculate_sha1(file_path)
        elif checksum_type.lower() == "md5":
            return self._calculate_md5(file_path)
        else:
            raise ValueError(f"Unsupported checksum type: {checksum_type}")
    
    def _calculate_sha256(self, file_path: str) -> str:
        """Calculate SHA256 checksum"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
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
    
    def remove_custom_image(self, image_id: str) -> bool:
        """Remove a custom image from the registry"""
        try:
            for i, image in enumerate(self._custom_images):
                if image.id == image_id:
                    del self._custom_images[i]
                    self._save_custom_images()
                    self.logger.info(f"Removed custom image: {image.name}")
                    return True
            
            self.logger.warning(f"Custom image not found: {image_id}")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to remove custom image: {e}")
            return False
    
    def search_images(self, query: str, os_family: Optional[str] = None) -> List[OSImageInfo]:
        """Search custom images"""
        results = []
        query_lower = query.lower()
        
        for image in self._custom_images:
            # Skip if OS family filter doesn't match
            if os_family and image.os_family != os_family:
                continue
            
            # Search in name, version, and metadata
            searchable_text = f"{image.name} {image.version} {image.metadata.get('original_filename', '')}"
            
            if query_lower in searchable_text.lower():
                results.append(image)
        
        return results
    
    def get_latest_image(self, os_family: str, version_pattern: Optional[str] = None) -> Optional[OSImageInfo]:
        """Get the latest custom image for an OS family"""
        images = [img for img in self._custom_images if img.os_family == os_family]
        
        # Filter by version pattern if provided
        if version_pattern:
            pattern_lower = version_pattern.lower()
            images = [img for img in images if 
                     pattern_lower in img.version.lower() or 
                     pattern_lower in img.name.lower()]
        
        if not images:
            return None
        
        # Sort by import date (most recent first)
        def import_date_key(image: OSImageInfo) -> str:
            return image.metadata.get("import_date", "1970-01-01T00:00:00")
        
        sorted_images = sorted(images, key=import_date_key, reverse=True)
        return sorted_images[0]
    
    def verify_image(self, image_info: OSImageInfo, local_path: str) -> bool:
        """Verify custom image"""
        try:
            self.logger.info(f"Verifying custom image: {local_path}")
            
            # Check file exists
            if not os.path.exists(local_path):
                self.logger.error(f"File does not exist: {local_path}")
                return False
            
            # Check file size matches
            actual_size = os.path.getsize(local_path)
            if actual_size != image_info.size_bytes:
                self.logger.error(f"File size mismatch: expected {image_info.size_bytes}, got {actual_size}")
                return False
            
            # Verify checksum if available
            if image_info.checksum:
                calculated = self._calculate_checksum(local_path, image_info.checksum_type)
                
                if calculated.lower() == image_info.checksum.lower():
                    self.logger.info("Custom image checksum verification successful")
                    return True
                else:
                    self.logger.error(f"Checksum mismatch: expected {image_info.checksum}, got {calculated}")
                    return False
            else:
                # No checksum - just verify basic file properties
                format_info = image_info.metadata.get("file_info", {})
                if format_info.get("size_valid", True):
                    self.logger.info("Custom image basic validation successful")
                    return True
                else:
                    self.logger.warning("File size seems unusual for this format")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Custom image verification failed: {e}")
            return False
    
    def get_supported_families(self) -> List[str]:
        """Get supported OS families"""
        return ["linux", "windows", "macos", "freebsd", "embedded", "unknown"]
    
    def get_verification_methods(self) -> List[VerificationMethod]:
        """Get supported verification methods"""
        return [VerificationMethod.SHA256, VerificationMethod.SHA1, VerificationMethod.MD5, VerificationMethod.NONE]
    
    def get_supported_formats(self) -> Dict[str, Dict]:
        """Get information about supported file formats"""
        return self.SUPPORTED_FORMATS.copy()
    
    def get_import_dialog_info(self) -> Dict[str, str]:
        """Get information for file import dialog"""
        # Create file filter from supported formats
        format_filters = []
        for ext, info in self.SUPPORTED_FORMATS.items():
            format_filters.append(f"{info['name']} (*{ext})")
        
        all_formats = " ".join(f"*{ext}" for ext in self.SUPPORTED_FORMATS.keys())
        format_filters.insert(0, f"All Supported Formats ({all_formats})")
        format_filters.append("All Files (*)")
        
        file_filter = ";;".join(format_filters)
        
        return {
            "title": "Import Custom OS Image",
            "file_filter": file_filter,
            "instructions": f"""
            Select a custom OS image file to import into BootForge.
            
            Supported formats:
            {chr(10).join(f"• {info['name']}: {info['description']}" for info in self.SUPPORTED_FORMATS.values())}
            
            The image will be analyzed for OS type, architecture, and version.
            You can provide custom metadata and verification checksums.
            """
        }