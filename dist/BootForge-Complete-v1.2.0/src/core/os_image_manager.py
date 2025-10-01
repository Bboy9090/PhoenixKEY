"""
BootForge OS Image Manager
Intelligent cloud-based OS image downloading, verification, and caching system
"""

import os
import json
import time
import uuid
import sqlite3
import hashlib
import logging
import requests
import tempfile
import threading
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from enum import Enum
from typing import Dict, List, Optional, Tuple, Callable, Any, Union
from dataclasses import dataclass, asdict, field
from urllib.parse import urlparse
# Qt dependencies removed for CLI compatibility

from src.core.config import Config


class ImageStatus(Enum):
    """OS Image status tracking"""
    UNKNOWN = "unknown"
    AVAILABLE = "available"          # Can be downloaded
    DOWNLOADING = "downloading"       # Currently downloading
    PAUSED = "paused"                # Download paused
    DOWNLOADED = "downloaded"        # Download complete
    VERIFYING = "verifying"          # Checking checksums/signatures
    VERIFIED = "verified"            # Ready to use
    FAILED = "failed"                # Download or verification failed
    CACHED = "cached"                # Available offline


class VerificationMethod(Enum):
    """Verification methods for OS images"""
    NONE = "none"
    SHA256 = "sha256"
    SHA512 = "sha512"
    MD5 = "md5"
    GPG = "gpg"
    HYBRID = "hybrid"  # Multiple methods


@dataclass
class OSImageInfo:
    """OS Image metadata and tracking"""
    id: str                          # Unique identifier
    name: str                        # Display name (e.g., "Ubuntu 22.04.3 LTS")
    os_family: str                   # "linux", "windows", "macos"
    version: str                     # Version string
    architecture: str                # "x86_64", "arm64", "i386"
    size_bytes: int                  # File size in bytes
    download_url: str                # Source URL
    local_path: Optional[str] = None # Local file path if cached
    checksum: Optional[str] = None   # Expected checksum
    checksum_type: str = "sha256"    # Checksum algorithm
    signature_url: Optional[str] = None  # GPG signature URL
    verification_method: VerificationMethod = VerificationMethod.SHA256
    status: ImageStatus = ImageStatus.UNKNOWN
    download_progress: float = 0.0   # Progress percentage (0-100)
    download_speed: float = 0.0      # Speed in MB/s
    eta_seconds: int = 0             # Estimated time remaining
    created_at: Optional[str] = None # ISO timestamp
    updated_at: Optional[str] = None # ISO timestamp
    provider: str = "unknown"        # Provider name
    metadata: Dict[str, Any] = field(default_factory=dict)  # Extra data
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        if not self.updated_at:
            self.updated_at = self.created_at


@dataclass
class DownloadProgress:
    """Download progress information"""
    image_id: str
    status: ImageStatus
    progress_percent: float
    speed_mbps: float
    eta_seconds: int
    downloaded_bytes: int
    total_bytes: int
    error_message: Optional[str] = None


class OSImageProvider(ABC):
    """Abstract base class for OS image providers"""
    
    def __init__(self, name: str, config: Config):
        self.name = name
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    @abstractmethod
    def get_available_images(self) -> List[OSImageInfo]:
        """Get list of available OS images from this provider"""
        pass
    
    @abstractmethod
    def search_images(self, query: str, os_family: Optional[str] = None) -> List[OSImageInfo]:
        """Search for OS images matching query"""
        pass
    
    @abstractmethod
    def get_latest_image(self, os_family: str, version_pattern: Optional[str] = None) -> Optional[OSImageInfo]:
        """Get the latest image for a specific OS family"""
        pass
    
    @abstractmethod
    def verify_image(self, image_info: OSImageInfo, local_path: str) -> bool:
        """Verify downloaded image integrity"""
        pass
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider metadata"""
        return {
            "name": self.name,
            "supported_families": self.get_supported_families(),
            "verification_methods": self.get_verification_methods(),
            "requires_auth": self.requires_authentication()
        }
    
    def get_supported_families(self) -> List[str]:
        """Get list of supported OS families"""
        return ["linux", "windows", "macos"]
    
    def get_verification_methods(self) -> List[VerificationMethod]:
        """Get supported verification methods"""
        return [VerificationMethod.SHA256]
    
    def requires_authentication(self) -> bool:
        """Whether this provider requires authentication"""
        return False


class ImageCache:
    """SQLite-based cache for OS images"""
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = cache_dir / "image_cache.db"
        self.logger = logging.getLogger(__name__)
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database schema"""
        with sqlite3.connect(str(self.db_path)) as conn:
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            
            # OS images table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS os_images (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    os_family TEXT NOT NULL,
                    version TEXT NOT NULL,
                    architecture TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    download_url TEXT NOT NULL,
                    local_path TEXT,
                    checksum TEXT,
                    checksum_type TEXT DEFAULT 'sha256',
                    signature_url TEXT,
                    verification_method TEXT DEFAULT 'sha256',
                    status TEXT DEFAULT 'unknown',
                    download_progress REAL DEFAULT 0.0,
                    download_speed REAL DEFAULT 0.0,
                    eta_seconds INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            
            # Download sessions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS download_sessions (
                    id TEXT PRIMARY KEY,
                    image_id TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    bytes_downloaded INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    error_message TEXT,
                    FOREIGN KEY (image_id) REFERENCES os_images (id)
                )
            """)
            
            # Verification log table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS verification_log (
                    id TEXT PRIMARY KEY,
                    image_id TEXT NOT NULL,
                    method TEXT NOT NULL,
                    result TEXT NOT NULL,
                    verified_at TEXT NOT NULL,
                    details TEXT,
                    FOREIGN KEY (image_id) REFERENCES os_images (id)
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_images_family ON os_images (os_family)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_images_status ON os_images (status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_images_provider ON os_images (provider)")
            
            conn.commit()
    
    def store_image(self, image_info: OSImageInfo) -> bool:
        """Store or update image information"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                image_info.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ")
                
                conn.execute("""
                    INSERT OR REPLACE INTO os_images (
                        id, name, os_family, version, architecture, size_bytes,
                        download_url, local_path, checksum, checksum_type, signature_url,
                        verification_method, status, download_progress, download_speed,
                        eta_seconds, created_at, updated_at, provider, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    image_info.id, image_info.name, image_info.os_family, image_info.version,
                    image_info.architecture, image_info.size_bytes, image_info.download_url,
                    image_info.local_path, image_info.checksum, image_info.checksum_type,
                    image_info.signature_url, image_info.verification_method.value,
                    image_info.status.value, image_info.download_progress,
                    image_info.download_speed, image_info.eta_seconds,
                    image_info.created_at, image_info.updated_at, image_info.provider,
                    json.dumps(image_info.metadata)
                ))
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Failed to store image {image_info.id}: {e}")
            return False
    
    def get_image(self, image_id: str) -> Optional[OSImageInfo]:
        """Retrieve image information by ID"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM os_images WHERE id = ?", (image_id,))
                row = cursor.fetchone()
                
                if row:
                    metadata = json.loads(row['metadata']) if row['metadata'] else {}
                    return OSImageInfo(
                        id=row['id'],
                        name=row['name'],
                        os_family=row['os_family'],
                        version=row['version'],
                        architecture=row['architecture'],
                        size_bytes=row['size_bytes'],
                        download_url=row['download_url'],
                        local_path=row['local_path'],
                        checksum=row['checksum'],
                        checksum_type=row['checksum_type'],
                        signature_url=row['signature_url'],
                        verification_method=VerificationMethod(row['verification_method']),
                        status=ImageStatus(row['status']),
                        download_progress=row['download_progress'],
                        download_speed=row['download_speed'],
                        eta_seconds=row['eta_seconds'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        provider=row['provider'],
                        metadata=metadata
                    )
                return None
        except Exception as e:
            self.logger.error(f"Failed to get image {image_id}: {e}")
            return None
    
    def list_images(self, status: Optional[ImageStatus] = None, 
                   os_family: Optional[str] = None) -> List[OSImageInfo]:
        """List images with optional filtering"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                
                query = "SELECT * FROM os_images WHERE 1=1"
                params = []
                
                if status:
                    query += " AND status = ?"
                    params.append(status.value)
                
                if os_family:
                    query += " AND os_family = ?"
                    params.append(os_family)
                
                query += " ORDER BY updated_at DESC"
                
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                images = []
                for row in rows:
                    metadata = json.loads(row['metadata']) if row['metadata'] else {}
                    images.append(OSImageInfo(
                        id=row['id'],
                        name=row['name'],
                        os_family=row['os_family'],
                        version=row['version'],
                        architecture=row['architecture'],
                        size_bytes=row['size_bytes'],
                        download_url=row['download_url'],
                        local_path=row['local_path'],
                        checksum=row['checksum'],
                        checksum_type=row['checksum_type'],
                        signature_url=row['signature_url'],
                        verification_method=VerificationMethod(row['verification_method']),
                        status=ImageStatus(row['status']),
                        download_progress=row['download_progress'],
                        download_speed=row['download_speed'],
                        eta_seconds=row['eta_seconds'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        provider=row['provider'],
                        metadata=metadata
                    ))
                
                return images
        except Exception as e:
            self.logger.error(f"Failed to list images: {e}")
            return []
    
    def update_download_progress(self, image_id: str, progress: float, 
                               speed: float, eta: int) -> bool:
        """Update download progress for an image"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute("""
                    UPDATE os_images 
                    SET download_progress = ?, download_speed = ?, eta_seconds = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (progress, speed, eta, time.strftime("%Y-%m-%dT%H:%M:%SZ"), image_id))
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Failed to update progress for {image_id}: {e}")
            return False


class DownloadEngine(threading.Thread):
    """Threaded download engine with resume support"""
    
    def __init__(self, cache: ImageCache, 
                 progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
                 completion_callback: Optional[Callable[[str, bool, str], None]] = None,
                 start_callback: Optional[Callable[[str], None]] = None):
        super().__init__(daemon=True)
        self.cache = cache
        self.logger = logging.getLogger(__name__)
        self.active_downloads: Dict[str, bool] = {}  # image_id -> should_continue
        self.session = requests.Session()
        
        # Callback functions instead of Qt signals
        self.progress_callback = progress_callback
        self.completion_callback = completion_callback  
        self.start_callback = start_callback
        
        # Configure session with reasonable defaults
        self.session.headers.update({
            'User-Agent': 'BootForge/1.1 (OS Image Manager)'
        })
    
    def start_download(self, image_info: OSImageInfo, target_dir: Path):
        """Start downloading an OS image"""
        if image_info.id in self.active_downloads:
            self.logger.warning(f"Download already active for {image_info.id}")
            return
        
        self.image_info = image_info
        self.target_dir = target_dir
        self.active_downloads[image_info.id] = True
        
        # Update status
        image_info.status = ImageStatus.DOWNLOADING
        self.cache.store_image(image_info)
        
        self.start()
    
    def pause_download(self, image_id: str):
        """Pause an active download"""
        if image_id in self.active_downloads:
            self.active_downloads[image_id] = False
            self.logger.info(f"Pausing download for {image_id}")
    
    def cancel_download(self, image_id: str):
        """Cancel an active download"""
        if image_id in self.active_downloads:
            del self.active_downloads[image_id]
            self.logger.info(f"Cancelling download for {image_id}")
    
    def run(self):
        """Main download thread"""
        image_id = self.image_info.id
        
        try:
            if self.start_callback:
                self.start_callback(image_id)
            
            # Determine local file path
            filename = os.path.basename(urlparse(self.image_info.download_url).path)
            if not filename or '.' not in filename:
                filename = f"{self.image_info.id}.iso"
            
            local_path = self.target_dir / filename
            temp_path = self.target_dir / f".{filename}.tmp"
            
            # Check for existing partial download
            resume_from = 0
            if temp_path.exists():
                resume_from = temp_path.stat().st_size
                self.logger.info(f"Resuming download from byte {resume_from}")
            
            # Prepare download request
            headers = {}
            if resume_from > 0:
                headers['Range'] = f'bytes={resume_from}-'
            
            # Start download
            response = self.session.get(self.image_info.download_url, 
                                      headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # Get total size
            total_size = int(response.headers.get('content-length', 0))
            if 'content-range' in response.headers:
                # Parse content-range: bytes 1024-2047/2048
                range_info = response.headers['content-range']
                total_size = int(range_info.split('/')[-1])
            
            # Download with progress tracking
            downloaded = resume_from
            start_time = time.time()
            last_update = start_time
            
            with open(temp_path, 'ab') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    # Check if download should continue
                    if image_id not in self.active_downloads or not self.active_downloads[image_id]:
                        self.logger.info(f"Download paused for {image_id}")
                        self._update_status(image_id, ImageStatus.PAUSED)
                        return
                    
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Update progress periodically
                        current_time = time.time()
                        if current_time - last_update >= 0.5:  # Update every 500ms
                            self._update_progress(image_id, downloaded, total_size, 
                                                current_time - start_time)
                            last_update = current_time
            
            # Download complete - move to final location
            if local_path.exists():
                local_path.unlink()
            temp_path.rename(local_path)
            
            # Update image info
            self.image_info.local_path = str(local_path)
            self.image_info.status = ImageStatus.DOWNLOADED
            self.image_info.download_progress = 100.0
            self.cache.store_image(self.image_info)
            
            if self.completion_callback:
                self.completion_callback(image_id, True, f"Download completed: {local_path}")
            
        except Exception as e:
            self.logger.error(f"Download failed for {image_id}: {e}")
            self._update_status(image_id, ImageStatus.FAILED)
            if self.completion_callback:
                self.completion_callback(image_id, False, str(e))
        finally:
            if image_id in self.active_downloads:
                del self.active_downloads[image_id]
    
    def _update_progress(self, image_id: str, downloaded: int, total: int, elapsed: float):
        """Update download progress"""
        if total > 0:
            progress = (downloaded / total) * 100
        else:
            progress = 0
        
        # Calculate speed and ETA
        speed_bps = downloaded / elapsed if elapsed > 0 else 0
        speed_mbps = speed_bps / (1024 * 1024)
        
        if speed_bps > 0 and total > downloaded:
            eta = int((total - downloaded) / speed_bps)
        else:
            eta = 0
        
        # Update cache
        self.cache.update_download_progress(image_id, progress, speed_mbps, eta)
        
        # Emit signal
        progress_info = DownloadProgress(
            image_id=image_id,
            status=ImageStatus.DOWNLOADING,
            progress_percent=progress,
            speed_mbps=speed_mbps,
            eta_seconds=eta,
            downloaded_bytes=downloaded,
            total_bytes=total
        )
        if self.progress_callback:
            self.progress_callback(progress_info)
    
    def _update_status(self, image_id: str, status: ImageStatus):
        """Update image status"""
        image_info = self.cache.get_image(image_id)
        if image_info:
            image_info.status = status
            self.cache.store_image(image_info)


class OSImageManager:
    """Main OS Image Manager class"""
    
    def __init__(self, config: Config, 
                 progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
                 images_updated_callback: Optional[Callable[[], None]] = None):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Callback functions instead of Qt signals
        self.images_updated_callback = images_updated_callback
        self.progress_callback = progress_callback
        
        # Initialize cache
        cache_dir = config.get_app_dir() / "cache" / "os_images"
        self.cache = ImageCache(cache_dir)
        
        # Initialize download engine with callbacks
        self.download_engine = DownloadEngine(
            self.cache,
            progress_callback=progress_callback,
            completion_callback=self._on_download_completed
        )
        
        # Provider registry
        self.providers: Dict[str, OSImageProvider] = {}
        
        # Load built-in providers
        self._register_builtin_providers()
    
    def _register_builtin_providers(self):
        """Register built-in image providers"""
        try:
            from src.core.providers.linux_provider import LinuxProvider
            from src.core.providers.macos_provider import MacOSProvider
            from src.core.providers.windows_provider import WindowsProvider
            from src.core.providers.custom_provider import CustomProvider
            
            # Register all providers
            self.register_provider(LinuxProvider(self.config))
            self.register_provider(MacOSProvider(self.config))
            self.register_provider(WindowsProvider(self.config))
            self.register_provider(CustomProvider(self.config))
            
            self.logger.info("All built-in providers registered successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to register built-in providers: {e}")
    
    def register_provider(self, provider: OSImageProvider):
        """Register a new image provider"""
        self.providers[provider.name] = provider
        self.logger.info(f"Registered provider: {provider.name}")
    
    def get_available_images(self, provider_name: Optional[str] = None) -> List[OSImageInfo]:
        """Get available images from providers"""
        images = []
        
        if provider_name:
            if provider_name in self.providers:
                images.extend(self.providers[provider_name].get_available_images())
        else:
            for provider in self.providers.values():
                try:
                    images.extend(provider.get_available_images())
                except Exception as e:
                    self.logger.warning(f"Provider {provider.name} failed: {e}")
        
        return images
    
    def search_images(self, query: str, os_family: Optional[str] = None) -> List[OSImageInfo]:
        """Search for images across all providers"""
        results = []
        
        for provider in self.providers.values():
            try:
                results.extend(provider.search_images(query, os_family))
            except Exception as e:
                self.logger.warning(f"Search failed for provider {provider.name}: {e}")
        
        return results
    
    def get_cached_images(self, os_family: Optional[str] = None) -> List[OSImageInfo]:
        """Get locally cached images"""
        return self.cache.list_images(
            status=ImageStatus.VERIFIED,
            os_family=os_family
        )
    
    def download_image(self, image_info: OSImageInfo) -> bool:
        """Start downloading an image"""
        try:
            # Store in cache
            self.cache.store_image(image_info)
            
            # Start download
            download_dir = self.config.get_app_dir() / "cache" / "downloads"
            download_dir.mkdir(parents=True, exist_ok=True)
            
            self.download_engine.start_download(image_info, download_dir)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start download for {image_info.id}: {e}")
            return False
    
    def verify_image(self, image_id: str) -> bool:
        """Verify a downloaded image"""
        image_info = self.cache.get_image(image_id)
        if not image_info or not image_info.local_path:
            return False
        
        # Get appropriate provider
        provider = self.providers.get(image_info.provider)
        if not provider:
            self.logger.error(f"Provider {image_info.provider} not found")
            return False
        
        # Verify image
        try:
            image_info.status = ImageStatus.VERIFYING
            self.cache.store_image(image_info)
            
            verified = provider.verify_image(image_info, image_info.local_path)
            
            image_info.status = ImageStatus.VERIFIED if verified else ImageStatus.FAILED
            self.cache.store_image(image_info)
            
            return verified
            
        except Exception as e:
            self.logger.error(f"Verification failed for {image_id}: {e}")
            image_info.status = ImageStatus.FAILED
            self.cache.store_image(image_info)
            return False
    
    def get_image_for_recipe(self, recipe_file_name: str) -> Optional[OSImageInfo]:
        """Get appropriate image for a recipe's required file"""
        # This will be used to integrate with USB Builder
        # Map recipe file names to cached images
        cached_images = self.get_cached_images()
        
        # Simple mapping for now - can be enhanced
        if "ubuntu" in recipe_file_name.lower() or "linux" in recipe_file_name.lower():
            for image in cached_images:
                if image.os_family == "linux" and "ubuntu" in image.name.lower():
                    return image
        elif "macos" in recipe_file_name.lower() or "mac" in recipe_file_name.lower():
            for image in cached_images:
                if image.os_family == "macos":
                    return image
        elif "windows" in recipe_file_name.lower():
            for image in cached_images:
                if image.os_family == "windows":
                    return image
        
        return None
    
    def _on_download_completed(self, image_id: str, success: bool, message: str):
        """Handle download completion"""
        if success:
            self.logger.info(f"Download completed for {image_id}")
            # Auto-verify after download
            self.verify_image(image_id)
        else:
            self.logger.error(f"Download failed for {image_id}: {message}")
        
        if self.images_updated_callback:
            self.images_updated_callback()