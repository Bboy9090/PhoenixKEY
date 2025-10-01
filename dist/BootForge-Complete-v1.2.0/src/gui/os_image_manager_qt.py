"""
BootForge Qt Bridge for OS Image Manager
Qt wrapper that bridges pure Python callbacks to Qt signals for GUI integration
"""

import logging
from typing import Optional, List, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal

from src.core.os_image_manager import (
    OSImageManager, OSImageInfo, ImageStatus, VerificationMethod, 
    DownloadProgress, OSImageProvider
)
from src.core.config import Config


class OSImageManagerQt(QObject):
    """Qt bridge wrapper for OSImageManager that provides Qt signals"""
    
    # Qt signals for GUI integration
    images_updated = pyqtSignal()
    download_progress = pyqtSignal(object)  # DownloadProgress
    
    def __init__(self, config: Config):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Create core manager with callback bindings
        self._core_manager = OSImageManager(
            config=config,
            progress_callback=self._on_progress_callback,
            images_updated_callback=self._on_images_updated_callback
        )
        
        self.logger.info("Qt bridge for OSImageManager initialized")
    
    def _on_progress_callback(self, progress: DownloadProgress):
        """Bridge progress callbacks to Qt signals"""
        self.download_progress.emit(progress)
    
    def _on_images_updated_callback(self):
        """Bridge images updated callbacks to Qt signals"""
        self.images_updated.emit()
    
    # Delegate all public methods to core manager
    def register_provider(self, provider: OSImageProvider):
        """Register a new image provider"""
        return self._core_manager.register_provider(provider)
    
    def get_available_images(self, provider_name: Optional[str] = None) -> List[OSImageInfo]:
        """Get available images from providers"""
        return self._core_manager.get_available_images(provider_name)
    
    def search_images(self, query: str, os_family: Optional[str] = None, 
                     provider_name: Optional[str] = None) -> List[OSImageInfo]:
        """Search for images matching query"""
        return self._core_manager.search_images(query, os_family)
    
    def get_cached_images(self, status: Optional[ImageStatus] = None) -> List[OSImageInfo]:
        """Get cached images"""
        # Core manager takes os_family, not status - filter by status after retrieval
        all_cached = self._core_manager.get_cached_images()
        if status is None:
            return all_cached
        return [img for img in all_cached if img.status == status]
    
    def download_image(self, image_info: OSImageInfo, 
                      download_dir: Optional[str] = None) -> bool:
        """Start downloading an OS image"""
        # Core manager doesn't support custom download_dir parameter
        return self._core_manager.download_image(image_info)
    
    def pause_download(self, image_id: str) -> bool:
        """Pause an active download"""
        # pause_download is on DownloadEngine, not OSImageManager
        if hasattr(self._core_manager, 'download_engine'):
            self._core_manager.download_engine.pause_download(image_id)
            return True
        return False
    
    def cancel_download(self, image_id: str) -> bool:
        """Cancel an active download"""
        # cancel_download is on DownloadEngine, not OSImageManager
        if hasattr(self._core_manager, 'download_engine'):
            self._core_manager.download_engine.cancel_download(image_id)
            return True
        return False
    
    def verify_image(self, image_id: str) -> bool:
        """Verify a downloaded image"""
        return self._core_manager.verify_image(image_id)
    
    def get_image_for_recipe(self, recipe_file_name: str) -> Optional[OSImageInfo]:
        """Get appropriate image for a recipe's required file"""
        return self._core_manager.get_image_for_recipe(recipe_file_name)
    
    def get_provider_info(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Get provider information"""
        if provider_name in self._core_manager.providers:
            return self._core_manager.providers[provider_name].get_provider_info()
        return None
    
    def get_providers(self) -> Dict[str, OSImageProvider]:
        """Get all registered providers"""
        return self._core_manager.providers.copy()
    
    def cleanup(self):
        """Cleanup resources"""
        if hasattr(self._core_manager, 'download_engine'):
            # Cancel all active downloads instead of using _stop_event
            download_engine = self._core_manager.download_engine
            active_ids = list(download_engine.active_downloads.keys())
            for image_id in active_ids:
                download_engine.cancel_download(image_id)
            
            if download_engine.is_alive():
                download_engine.join(timeout=1.0)
        
        self.logger.info("OSImageManager Qt bridge cleaned up")