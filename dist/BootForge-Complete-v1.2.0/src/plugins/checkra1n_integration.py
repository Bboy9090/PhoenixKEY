"""
BootForge Checkra1n Integration Plugin
Integrates checkra1n jailbreak functionality for iOS bypass workflows
"""

import os
import logging
import subprocess
import platform
from pathlib import Path
from typing import Dict, List, Optional, Any

from src.plugins.plugin_manager import PluginBase
from src.core.config import Config


class Checkra1nPlugin(PluginBase):
    """Plugin for checkra1n integration"""
    
    def __init__(self):
        super().__init__()
        self.name = "Checkra1nIntegration"
        self.version = "1.0.0"
        self.description = "Integrate checkra1n for iOS bypass workflows"
        self.author = "BootForge Team"
        self.dependencies = []
        
        self.checkra1n_path = None
        self.supported_devices = []
        
    def initialize(self, config: Config) -> bool:
        """Initialize checkra1n plugin"""
        try:
            # Find checkra1n executable
            self.checkra1n_path = self._find_checkra1n()
            
            if not self.checkra1n_path:
                self.logger.warning("checkra1n executable not found")
                return False
            
            # Load supported devices
            self._load_supported_devices()
            
            self.logger.info("Checkra1n plugin initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize checkra1n plugin: {e}")
            return False
    
    def execute(self, *args, **kwargs) -> Any:
        """Execute checkra1n operation"""
        operation = kwargs.get('operation', 'jailbreak')
        device_udid = kwargs.get('device_udid')
        options = kwargs.get('options', {})
        
        if operation == 'jailbreak':
            return self._perform_jailbreak(device_udid, options)
        elif operation == 'detect_devices':
            return self._detect_devices()
        elif operation == 'check_compatibility':
            return self._check_device_compatibility(device_udid)
        else:
            self.logger.error(f"Unknown operation: {operation}")
            return False
    
    def _find_checkra1n(self) -> Optional[str]:
        """Find checkra1n executable"""
        possible_paths = []
        
        system = platform.system()
        if system == "Darwin":  # macOS
            possible_paths = [
                "/Applications/checkra1n.app/Contents/MacOS/checkra1n",
                "/usr/local/bin/checkra1n",
                "/opt/homebrew/bin/checkra1n"
            ]
        elif system == "Linux":
            possible_paths = [
                "/usr/bin/checkra1n",
                "/usr/local/bin/checkra1n",
                "/opt/checkra1n/checkra1n",
                "checkra1n"  # Check PATH
            ]
        
        # Check each possible path
        for path in possible_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                self.logger.info(f"Found checkra1n at: {path}")
                return path
        
        # Try to find in PATH
        try:
            result = subprocess.run(['which', 'checkra1n'], 
                                  capture_output=True, text=True, check=True)
            path = result.stdout.strip()
            if path:
                self.logger.info(f"Found checkra1n in PATH: {path}")
                return path
        except subprocess.CalledProcessError:
            pass
        
        return None
    
    def _load_supported_devices(self):
        """Load list of supported devices"""
        # This is a simplified list - in reality, you'd load from checkra1n or a database
        self.supported_devices = [
            # iPhone models
            {"model": "iPhone 5s", "identifier": "iPhone6,1", "min_ios": "12.0", "max_ios": "14.8.1"},
            {"model": "iPhone 6", "identifier": "iPhone7,2", "min_ios": "12.0", "max_ios": "14.8.1"},
            {"model": "iPhone 6 Plus", "identifier": "iPhone7,1", "min_ios": "12.0", "max_ios": "14.8.1"},
            {"model": "iPhone 6s", "identifier": "iPhone8,1", "min_ios": "12.0", "max_ios": "14.8.1"},
            {"model": "iPhone 6s Plus", "identifier": "iPhone8,2", "min_ios": "12.0", "max_ios": "14.8.1"},
            {"model": "iPhone SE", "identifier": "iPhone8,4", "min_ios": "12.0", "max_ios": "14.8.1"},
            {"model": "iPhone 7", "identifier": "iPhone9,1", "min_ios": "12.0", "max_ios": "14.8.1"},
            {"model": "iPhone 7 Plus", "identifier": "iPhone9,2", "min_ios": "12.0", "max_ios": "14.8.1"},
            {"model": "iPhone 8", "identifier": "iPhone10,1", "min_ios": "12.0", "max_ios": "14.8.1"},
            {"model": "iPhone 8 Plus", "identifier": "iPhone10,2", "min_ios": "12.0", "max_ios": "14.8.1"},
            {"model": "iPhone X", "identifier": "iPhone10,3", "min_ios": "12.0", "max_ios": "14.8.1"},
            
            # iPad models
            {"model": "iPad Air 2", "identifier": "iPad5,3", "min_ios": "12.0", "max_ios": "14.8.1"},
            {"model": "iPad Mini 4", "identifier": "iPad5,1", "min_ios": "12.0", "max_ios": "14.8.1"},
            {"model": "iPad Pro 9.7", "identifier": "iPad6,3", "min_ios": "12.0", "max_ios": "14.8.1"},
            {"model": "iPad Pro 12.9", "identifier": "iPad6,7", "min_ios": "12.0", "max_ios": "14.8.1"},
            
            # iPod models
            {"model": "iPod Touch 6", "identifier": "iPod7,1", "min_ios": "12.0", "max_ios": "14.8.1"},
            {"model": "iPod Touch 7", "identifier": "iPod9,1", "min_ios": "12.0", "max_ios": "14.8.1"},
        ]
    
    def _detect_devices(self) -> List[Dict[str, str]]:
        """Detect connected iOS devices"""
        devices = []
        
        try:
            # Use idevice_id to detect devices (if available)
            result = subprocess.run(['idevice_id', '-l'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                udids = result.stdout.strip().split('\\n')
                
                for udid in udids:
                    if udid:
                        device_info = self._get_device_info(udid)
                        if device_info:
                            devices.append(device_info)
            
        except subprocess.TimeoutExpired:
            self.logger.warning("Device detection timed out")
        except FileNotFoundError:
            self.logger.warning("idevice_id not found - install libimobiledevice")
        except Exception as e:
            self.logger.error(f"Error detecting devices: {e}")
        
        return devices
    
    def _get_device_info(self, udid: str) -> Optional[Dict[str, str]]:
        """Get device information"""
        try:
            # Get device info using ideviceinfo
            result = subprocess.run(
                ['ideviceinfo', '-u', udid, '-k', 'ProductType'], 
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                product_type = result.stdout.strip()
                
                # Get device name
                name_result = subprocess.run(
                    ['ideviceinfo', '-u', udid, '-k', 'DeviceName'], 
                    capture_output=True, text=True, timeout=5
                )
                device_name = name_result.stdout.strip() if name_result.returncode == 0 else "Unknown"
                
                # Get iOS version
                version_result = subprocess.run(
                    ['ideviceinfo', '-u', udid, '-k', 'ProductVersion'], 
                    capture_output=True, text=True, timeout=5
                )
                ios_version = version_result.stdout.strip() if version_result.returncode == 0 else "Unknown"
                
                return {
                    'udid': udid,
                    'name': device_name,
                    'model': product_type,
                    'ios_version': ios_version,
                    'compatible': self._is_device_compatible(product_type, ios_version)
                }
                
        except Exception as e:
            self.logger.error(f"Error getting device info for {udid}: {e}")
        
        return None
    
    def _is_device_compatible(self, product_type: str, ios_version: str) -> bool:
        """Check if device is compatible with checkra1n"""
        for device in self.supported_devices:
            if device['identifier'] == product_type:
                # Simple version comparison (you'd want a more robust implementation)
                return True
        return False
    
    def _check_device_compatibility(self, device_udid: str) -> Dict[str, Any]:
        """Check device compatibility"""
        device_info = self._get_device_info(device_udid)
        if not device_info:
            return {'compatible': False, 'reason': 'Device not found'}
        
        product_type = device_info['model']
        ios_version = device_info['ios_version']
        
        for device in self.supported_devices:
            if device['identifier'] == product_type:
                return {
                    'compatible': True,
                    'device': device,
                    'ios_version': ios_version,
                    'notes': f"Compatible with checkra1n"
                }
        
        return {
            'compatible': False,
            'reason': f"Device {product_type} not supported by checkra1n",
            'ios_version': ios_version
        }
    
    def _perform_jailbreak(self, device_udid: str, options: Dict[str, Any]) -> bool:
        """Perform checkra1n jailbreak"""
        if not self.checkra1n_path:
            self.logger.error("checkra1n executable not found")
            return False
        
        try:
            # Build checkra1n command
            cmd = [self.checkra1n_path]
            
            # Add options
            if options.get('cli_mode', True):
                cmd.append('-c')
            
            if options.get('safe_mode', False):
                cmd.append('-s')
            
            if options.get('verbose', False):
                cmd.append('-v')
            
            if device_udid:
                cmd.extend(['-d', device_udid])
            
            self.logger.info(f"Starting checkra1n jailbreak with command: {' '.join(cmd)}")
            
            # Execute checkra1n
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Monitor output
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    self.logger.info(f"checkra1n: {output.strip()}")
            
            return_code = process.poll()
            
            if return_code == 0:
                self.logger.info("Checkra1n jailbreak completed successfully")
                return True
            else:
                stderr = process.stderr.read()
                self.logger.error(f"Checkra1n failed with code {return_code}: {stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error performing jailbreak: {e}")
            return False
    
    def get_supported_devices(self) -> List[Dict[str, str]]:
        """Get list of supported devices"""
        return self.supported_devices
    
    def cleanup(self) -> bool:
        """Cleanup checkra1n plugin"""
        try:
            self.logger.info("Checkra1n plugin cleaned up")
            return True
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            return False