"""
BootForge Driver Injector Plugin
Injects drivers and kexts into OS images
"""

import os
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any
from zipfile import ZipFile

from src.plugins.plugin_manager import PluginBase
from src.core.config import Config


class DriverInjectorPlugin(PluginBase):
    """Plugin for injecting drivers into OS images"""
    
    def __init__(self):
        super().__init__()
        self.name = "DriverInjector"
        self.version = "1.0.0"
        self.description = "Inject drivers and kexts into OS images"
        self.author = "BootForge Team"
        self.dependencies = []
        
        self.driver_cache = {}
        self.supported_formats = ['.sys', '.inf', '.kext', '.dext']
        
    def initialize(self, config: Config) -> bool:
        """Initialize driver injector plugin"""
        try:
            self.temp_dir = Path(config.get_temp_dir()) / "driver_injection"
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            
            self.driver_dir = config.get_app_dir() / "drivers"
            self.driver_dir.mkdir(parents=True, exist_ok=True)
            
            self.logger.info("Driver injector plugin initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize driver injector: {e}")
            return False
    
    def execute(self, *args, **kwargs) -> Any:
        """Execute driver injection"""
        image_path = kwargs.get('image_path')
        drivers = kwargs.get('drivers', [])
        os_type = kwargs.get('os_type', 'windows')
        
        if not image_path or not drivers:
            self.logger.error("Image path and drivers are required")
            return False
        
        try:
            if os_type.lower() == 'windows':
                return self._inject_windows_drivers(image_path, drivers)
            elif os_type.lower() == 'macos':
                return self._inject_macos_kexts(image_path, drivers)
            else:
                self.logger.error(f"Unsupported OS type: {os_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Driver injection failed: {e}")
            return False
    
    def _inject_windows_drivers(self, image_path: str, drivers: List[str]) -> bool:
        """Inject Windows drivers into image"""
        self.logger.info(f"Injecting Windows drivers into {image_path}")
        
        try:
            with tempfile.TemporaryDirectory() as temp_mount:
                # Mount the image (this is a simplified example)
                mount_point = Path(temp_mount) / "mount"
                mount_point.mkdir()
                
                # Extract drivers to appropriate locations
                drivers_dir = mount_point / "Windows" / "System32" / "drivers"
                inf_dir = mount_point / "Windows" / "INF"
                
                drivers_dir.mkdir(parents=True, exist_ok=True)
                inf_dir.mkdir(parents=True, exist_ok=True)
                
                for driver_path in drivers:
                    driver_file = Path(driver_path)
                    
                    if driver_file.suffix.lower() == '.sys':
                        # Copy .sys file to drivers directory
                        shutil.copy2(driver_file, drivers_dir)
                        self.logger.info(f"Copied driver: {driver_file.name}")
                        
                    elif driver_file.suffix.lower() == '.inf':
                        # Copy .inf file to INF directory
                        shutil.copy2(driver_file, inf_dir)
                        self.logger.info(f"Copied INF: {driver_file.name}")
                        
                    elif driver_file.suffix.lower() == '.zip':
                        # Extract driver package
                        self._extract_driver_package(driver_file, drivers_dir, inf_dir)
                
                # Update registry if needed (simplified)
                self._update_windows_registry(mount_point, drivers)
                
                self.logger.info("Windows driver injection completed")
                return True
                
        except Exception as e:
            self.logger.error(f"Windows driver injection failed: {e}")
            return False
    
    def _inject_macos_kexts(self, image_path: str, kexts: List[str]) -> bool:
        """Inject macOS kexts into image"""
        self.logger.info(f"Injecting macOS kexts into {image_path}")
        
        try:
            with tempfile.TemporaryDirectory() as temp_mount:
                mount_point = Path(temp_mount) / "mount"
                mount_point.mkdir()
                
                # Mount DMG (simplified)
                extensions_dir = mount_point / "System" / "Library" / "Extensions"
                extra_dir = mount_point / "Library" / "Extensions"
                
                extensions_dir.mkdir(parents=True, exist_ok=True)
                extra_dir.mkdir(parents=True, exist_ok=True)
                
                for kext_path in kexts:
                    kext_file = Path(kext_path)
                    
                    if kext_file.suffix.lower() == '.kext':
                        # Determine target directory based on kext type
                        if self._is_system_kext(kext_file):
                            target_dir = extensions_dir
                        else:
                            target_dir = extra_dir
                        
                        # Copy kext bundle
                        target_path = target_dir / kext_file.name
                        if kext_file.is_dir():
                            shutil.copytree(kext_file, target_path)
                        else:
                            shutil.copy2(kext_file, target_path)
                        
                        self.logger.info(f"Copied kext: {kext_file.name}")
                        
                    elif kext_file.suffix.lower() == '.dext':
                        # Handle DriverKit extensions
                        dext_dir = mount_point / "System" / "Library" / "DriverExtensions"
                        dext_dir.mkdir(parents=True, exist_ok=True)
                        
                        shutil.copy2(kext_file, dext_dir)
                        self.logger.info(f"Copied dext: {kext_file.name}")
                
                # Update kext cache (simplified)
                self._update_kext_cache(mount_point)
                
                self.logger.info("macOS kext injection completed")
                return True
                
        except Exception as e:
            self.logger.error(f"macOS kext injection failed: {e}")
            return False
    
    def _extract_driver_package(self, package_path: Path, sys_dir: Path, inf_dir: Path):
        """Extract driver package to appropriate directories"""
        try:
            with ZipFile(package_path, 'r') as zip_file:
                for file_info in zip_file.infolist():
                    file_path = Path(file_info.filename)
                    
                    if file_path.suffix.lower() == '.sys':
                        zip_file.extract(file_info, sys_dir)
                    elif file_path.suffix.lower() == '.inf':
                        zip_file.extract(file_info, inf_dir)
                        
        except Exception as e:
            self.logger.error(f"Failed to extract driver package {package_path}: {e}")
    
    def _is_system_kext(self, kext_path: Path) -> bool:
        """Determine if kext should go in System/Library/Extensions"""
        # Simplified logic - in reality, you'd check the kext's Info.plist
        system_kexts = [
            'IOUSBFamily.kext', 'IOStorageFamily.kext', 'IONetworkingFamily.kext'
        ]
        return kext_path.name in system_kexts
    
    def _update_windows_registry(self, mount_point: Path, drivers: List[str]):
        """Update Windows registry for driver installation"""
        # This is a simplified placeholder
        # Real implementation would modify the registry hive files
        self.logger.info("Updating Windows registry for drivers")
    
    def _update_kext_cache(self, mount_point: Path):
        """Update macOS kext cache"""
        # This is a simplified placeholder
        # Real implementation would rebuild the kernel cache
        self.logger.info("Updating macOS kext cache")
    
    def get_available_drivers(self, os_type: str) -> List[Dict[str, str]]:
        """Get list of available drivers for OS type"""
        drivers = []
        
        try:
            os_driver_dir = self.driver_dir / os_type.lower()
            if os_driver_dir.exists():
                for driver_file in os_driver_dir.rglob("*"):
                    if driver_file.suffix.lower() in self.supported_formats:
                        drivers.append({
                            'name': driver_file.stem,
                            'path': str(driver_file),
                            'type': driver_file.suffix.lower(),
                            'size': driver_file.stat().st_size if driver_file.is_file() else 0
                        })
                        
        except Exception as e:
            self.logger.error(f"Error getting available drivers: {e}")
        
        return drivers
    
    def cleanup(self) -> bool:
        """Cleanup driver injector resources"""
        try:
            if hasattr(self, 'temp_dir') and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
            
            self.logger.info("Driver injector plugin cleaned up")
            return True
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            return False