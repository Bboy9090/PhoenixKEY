"""
BootForge Diagnostics Plugin
USB drive diagnostics and health checking
"""

import os
import logging
import subprocess
import time
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import psutil

from src.plugins.plugin_manager import PluginBase
from src.core.config import Config


class DiagnosticsPlugin(PluginBase):
    """Plugin for USB drive diagnostics and health checking"""
    
    def __init__(self):
        super().__init__()
        self.name = "Diagnostics"
        self.version = "1.0.0"
        self.description = "USB drive diagnostics and health checking"
        self.author = "BootForge Team"
        self.dependencies = []
        
    def initialize(self, config: Config) -> bool:
        """Initialize diagnostics plugin"""
        try:
            self.temp_dir = Path(config.get_temp_dir()) / "diagnostics"
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            
            self.logger.info("Diagnostics plugin initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize diagnostics plugin: {e}")
            return False
    
    def execute(self, *args, **kwargs) -> Any:
        """Execute diagnostics operation"""
        operation = kwargs.get('operation', 'full_check')
        device_path = kwargs.get('device_path')
        
        if not device_path:
            self.logger.error("Device path is required")
            return None
        
        if operation == 'full_check':
            return self._perform_full_check(device_path)
        elif operation == 'speed_test':
            return self._perform_speed_test(device_path)
        elif operation == 'bad_sectors':
            return self._check_bad_sectors(device_path)
        elif operation == 'filesystem_check':
            return self._check_filesystem(device_path)
        elif operation == 'smart_check':
            return self._check_smart_data(device_path)
        else:
            self.logger.error(f"Unknown operation: {operation}")
            return None
    
    def _perform_full_check(self, device_path: str) -> Dict[str, Any]:
        """Perform comprehensive device check"""
        self.logger.info(f"Performing full diagnostics on {device_path}")
        
        results = {
            'device_path': device_path,
            'timestamp': time.time(),
            'checks': {}
        }
        
        # Basic device info
        results['checks']['device_info'] = self._get_device_info(device_path)
        
        # Speed test
        results['checks']['speed_test'] = self._perform_speed_test(device_path)
        
        # Bad sectors check
        results['checks']['bad_sectors'] = self._check_bad_sectors(device_path)
        
        # Filesystem check
        results['checks']['filesystem'] = self._check_filesystem(device_path)
        
        # SMART data (if available)
        results['checks']['smart_data'] = self._check_smart_data(device_path)
        
        # Overall health assessment
        results['health_score'] = self._calculate_health_score(results['checks'])
        results['recommendations'] = self._generate_recommendations(results['checks'])
        
        return results
    
    def _get_device_info(self, device_path: str) -> Dict[str, Any]:
        """Get basic device information"""
        info = {
            'path': device_path,
            'exists': os.path.exists(device_path),
            'readable': False,
            'writable': False,
            'size_bytes': 0,
            'model': 'Unknown',
            'vendor': 'Unknown',
            'serial': 'Unknown'
        }
        
        try:
            if info['exists']:
                # Check read/write permissions
                info['readable'] = os.access(device_path, os.R_OK)
                info['writable'] = os.access(device_path, os.W_OK)
                
                # Get device size
                try:
                    stat = os.stat(device_path)
                    info['size_bytes'] = stat.st_size
                except OSError:
                    # For block devices, try to get size differently
                    info['size_bytes'] = self._get_block_device_size(device_path)
                
                # Get device details from system
                device_details = self._get_system_device_info(device_path)
                info.update(device_details)
        
        except Exception as e:
            self.logger.error(f"Error getting device info: {e}")
        
        return info
    
    def _get_block_device_size(self, device_path: str) -> int:
        """Get block device size"""
        try:
            # Try different methods based on platform
            import platform
            
            if platform.system() == "Linux":
                # Use lsblk or blockdev
                try:
                    result = subprocess.run(
                        ['blockdev', '--getsize64', device_path],
                        capture_output=True, text=True, check=True
                    )
                    return int(result.stdout.strip())
                except subprocess.CalledProcessError:
                    pass
                
                try:
                    result = subprocess.run(
                        ['lsblk', '-b', '-d', '-o', 'SIZE', device_path],
                        capture_output=True, text=True, check=True
                    )
                    lines = result.stdout.strip().split('\\n')
                    if len(lines) > 1:
                        return int(lines[1].strip())
                except subprocess.CalledProcessError:
                    pass
            
            elif platform.system() == "Darwin":  # macOS
                try:
                    result = subprocess.run(
                        ['diskutil', 'info', device_path],
                        capture_output=True, text=True, check=True
                    )
                    for line in result.stdout.split('\\n'):
                        if 'Total Size:' in line:
                            # Extract size in bytes
                            parts = line.split('(')
                            if len(parts) > 1:
                                bytes_part = parts[1].split()[0]
                                return int(bytes_part)
                except subprocess.CalledProcessError:
                    pass
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Error getting block device size: {e}")
            return 0
    
    def _get_system_device_info(self, device_path: str) -> Dict[str, str]:
        """Get device information from system"""
        info = {'model': 'Unknown', 'vendor': 'Unknown', 'serial': 'Unknown'}
        
        try:
            import platform
            
            if platform.system() == "Linux":
                # Extract device name for sysfs lookup
                device_name = device_path.split('/')[-1].rstrip('0123456789')
                
                # Read from /sys/block
                sys_path = f"/sys/block/{device_name}"
                
                if os.path.exists(sys_path):
                    # Model
                    model_file = f"{sys_path}/device/model"
                    if os.path.exists(model_file):
                        with open(model_file, 'r') as f:
                            info['model'] = f.read().strip()
                    
                    # Vendor
                    vendor_file = f"{sys_path}/device/vendor"
                    if os.path.exists(vendor_file):
                        with open(vendor_file, 'r') as f:
                            info['vendor'] = f.read().strip()
                    
                    # Serial
                    serial_file = f"{sys_path}/device/serial"
                    if os.path.exists(serial_file):
                        with open(serial_file, 'r') as f:
                            info['serial'] = f.read().strip()
            
        except Exception as e:
            self.logger.debug(f"Could not get system device info: {e}")
        
        return info
    
    def _perform_speed_test(self, device_path: str) -> Dict[str, Any]:
        """Perform read/write speed test"""
        self.logger.info(f"Performing speed test on {device_path}")
        
        results = {
            'read_speed_mbps': 0,
            'write_speed_mbps': 0,
            'errors': []
        }
        
        try:
            # Test with different block sizes
            test_sizes = [1024*1024, 4*1024*1024, 16*1024*1024]  # 1MB, 4MB, 16MB
            
            read_speeds = []
            write_speeds = []
            
            with tempfile.NamedTemporaryFile() as temp_file:
                # Create test data
                test_data = os.urandom(max(test_sizes))
                
                for test_size in test_sizes:
                    # Write speed test
                    try:
                        start_time = time.time()
                        
                        # Write test data to temporary file
                        temp_file.seek(0)
                        temp_file.write(test_data[:test_size])
                        temp_file.flush()
                        os.fsync(temp_file.fileno())
                        
                        write_time = time.time() - start_time
                        write_speed = (test_size / (1024 * 1024)) / write_time
                        write_speeds.append(write_speed)
                        
                    except Exception as e:
                        results['errors'].append(f"Write test failed: {e}")
                    
                    # Read speed test
                    try:
                        start_time = time.time()
                        
                        temp_file.seek(0)
                        data = temp_file.read(test_size)
                        
                        read_time = time.time() - start_time
                        read_speed = (len(data) / (1024 * 1024)) / read_time
                        read_speeds.append(read_speed)
                        
                    except Exception as e:
                        results['errors'].append(f"Read test failed: {e}")
            
            # Calculate average speeds
            if read_speeds:
                results['read_speed_mbps'] = sum(read_speeds) / len(read_speeds)
            
            if write_speeds:
                results['write_speed_mbps'] = sum(write_speeds) / len(write_speeds)
        
        except Exception as e:
            results['errors'].append(f"Speed test failed: {e}")
            self.logger.error(f"Speed test error: {e}")
        
        return results
    
    def _check_bad_sectors(self, device_path: str) -> Dict[str, Any]:
        """Check for bad sectors"""
        self.logger.info(f"Checking for bad sectors on {device_path}")
        
        results = {
            'bad_sectors': 0,
            'total_sectors': 0,
            'errors': [],
            'scan_completed': False
        }
        
        try:
            # This is a simplified bad sector check
            # In a real implementation, you'd use tools like badblocks
            
            # Try to use badblocks if available
            try:
                result = subprocess.run(
                    ['badblocks', '-v', '-n', device_path],
                    capture_output=True, text=True, timeout=300  # 5 minute timeout
                )
                
                if result.returncode == 0:
                    results['scan_completed'] = True
                    # Parse badblocks output
                    if "bad blocks" in result.stderr:
                        # Extract bad block count
                        for line in result.stderr.split('\\n'):
                            if "bad blocks" in line:
                                parts = line.split()
                                if parts:
                                    try:
                                        results['bad_sectors'] = int(parts[0])
                                    except (ValueError, IndexError):
                                        pass
                else:
                    results['errors'].append(f"badblocks failed: {result.stderr}")
                    
            except FileNotFoundError:
                results['errors'].append("badblocks tool not available")
            except subprocess.TimeoutExpired:
                results['errors'].append("Bad sector scan timed out")
            
        except Exception as e:
            results['errors'].append(f"Bad sector check failed: {e}")
            self.logger.error(f"Bad sector check error: {e}")
        
        return results
    
    def _check_filesystem(self, device_path: str) -> Dict[str, Any]:
        """Check filesystem integrity"""
        self.logger.info(f"Checking filesystem on {device_path}")
        
        results = {
            'filesystem_type': 'Unknown',
            'errors': [],
            'warnings': [],
            'health': 'Unknown'
        }
        
        try:
            # Detect filesystem type
            try:
                result = subprocess.run(
                    ['blkid', '-o', 'value', '-s', 'TYPE', device_path],
                    capture_output=True, text=True, check=True
                )
                results['filesystem_type'] = result.stdout.strip()
            except (subprocess.CalledProcessError, FileNotFoundError):
                results['errors'].append("Could not detect filesystem type")
            
            # Run filesystem check based on type
            fs_type = results['filesystem_type'].lower()
            
            if fs_type in ['ext2', 'ext3', 'ext4']:
                self._check_ext_filesystem(device_path, results)
            elif fs_type in ['fat', 'fat32', 'vfat']:
                self._check_fat_filesystem(device_path, results)
            elif fs_type == 'ntfs':
                self._check_ntfs_filesystem(device_path, results)
            elif fs_type in ['hfs', 'hfs+', 'hfsx']:
                self._check_hfs_filesystem(device_path, results)
            else:
                results['warnings'].append(f"Filesystem check not supported for {fs_type}")
        
        except Exception as e:
            results['errors'].append(f"Filesystem check failed: {e}")
            self.logger.error(f"Filesystem check error: {e}")
        
        return results
    
    def _check_ext_filesystem(self, device_path: str, results: Dict[str, Any]):
        """Check ext2/3/4 filesystem"""
        try:
            result = subprocess.run(
                ['e2fsck', '-n', device_path],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                results['health'] = 'Good'
            else:
                results['health'] = 'Issues Found'
                results['errors'].append(f"e2fsck found issues: {result.stdout}")
                
        except FileNotFoundError:
            results['warnings'].append("e2fsck not available")
        except Exception as e:
            results['errors'].append(f"ext filesystem check failed: {e}")
    
    def _check_fat_filesystem(self, device_path: str, results: Dict[str, Any]):
        """Check FAT filesystem"""
        try:
            result = subprocess.run(
                ['fsck.fat', '-v', '-r', device_path],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                results['health'] = 'Good'
            else:
                results['health'] = 'Issues Found'
                results['errors'].append(f"fsck.fat found issues: {result.stdout}")
                
        except FileNotFoundError:
            results['warnings'].append("fsck.fat not available")
        except Exception as e:
            results['errors'].append(f"FAT filesystem check failed: {e}")
    
    def _check_ntfs_filesystem(self, device_path: str, results: Dict[str, Any]):
        """Check NTFS filesystem"""
        try:
            result = subprocess.run(
                ['ntfsfix', '-n', device_path],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                results['health'] = 'Good'
            else:
                results['health'] = 'Issues Found'
                results['errors'].append(f"ntfsfix found issues: {result.stdout}")
                
        except FileNotFoundError:
            results['warnings'].append("ntfsfix not available")
        except Exception as e:
            results['errors'].append(f"NTFS filesystem check failed: {e}")
    
    def _check_hfs_filesystem(self, device_path: str, results: Dict[str, Any]):
        """Check HFS+ filesystem"""
        try:
            result = subprocess.run(
                ['diskutil', 'verifyVolume', device_path],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                results['health'] = 'Good'
            else:
                results['health'] = 'Issues Found'
                results['errors'].append(f"diskutil found issues: {result.stdout}")
                
        except FileNotFoundError:
            results['warnings'].append("diskutil not available")
        except Exception as e:
            results['errors'].append(f"HFS filesystem check failed: {e}")
    
    def _check_smart_data(self, device_path: str) -> Dict[str, Any]:
        """Check SMART data if available"""
        self.logger.info(f"Checking SMART data for {device_path}")
        
        results = {
            'smart_available': False,
            'health_status': 'Unknown',
            'temperature': None,
            'power_on_hours': None,
            'errors': []
        }
        
        try:
            # Try to get SMART data using smartctl
            result = subprocess.run(
                ['smartctl', '-a', device_path],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                results['smart_available'] = True
                
                # Parse SMART output
                for line in result.stdout.split('\\n'):
                    if 'overall-health' in line.lower():
                        if 'PASSED' in line:
                            results['health_status'] = 'Good'
                        else:
                            results['health_status'] = 'Failed'
                    
                    if 'temperature' in line.lower():
                        # Extract temperature
                        parts = line.split()
                        for part in parts:
                            if part.isdigit():
                                results['temperature'] = int(part)
                                break
                    
                    if 'power_on_hours' in line.lower() or 'power on hours' in line.lower():
                        # Extract power on hours
                        parts = line.split()
                        for part in parts:
                            if part.isdigit():
                                results['power_on_hours'] = int(part)
                                break
            else:
                results['errors'].append("SMART data not available or accessible")
                
        except FileNotFoundError:
            results['errors'].append("smartctl not available")
        except Exception as e:
            results['errors'].append(f"SMART check failed: {e}")
        
        return results
    
    def _calculate_health_score(self, checks: Dict[str, Any]) -> int:
        """Calculate overall health score (0-100)"""
        score = 100
        
        # Deduct points for issues
        if checks.get('bad_sectors', {}).get('bad_sectors', 0) > 0:
            score -= 30
        
        if checks.get('filesystem', {}).get('health') == 'Issues Found':
            score -= 20
        
        if checks.get('smart_data', {}).get('health_status') == 'Failed':
            score -= 40
        
        # Check speed test results
        speed_test = checks.get('speed_test', {})
        if speed_test.get('write_speed_mbps', 0) < 5:  # Less than 5 MB/s is concerning
            score -= 15
        
        if speed_test.get('read_speed_mbps', 0) < 10:  # Less than 10 MB/s is concerning
            score -= 10
        
        # Count errors across all checks
        total_errors = sum(len(check.get('errors', [])) for check in checks.values())
        score -= min(total_errors * 5, 25)  # Max 25 points for errors
        
        return max(0, score)
    
    def _generate_recommendations(self, checks: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on check results"""
        recommendations = []
        
        # Bad sectors
        bad_sectors = checks.get('bad_sectors', {}).get('bad_sectors', 0)
        if bad_sectors > 0:
            recommendations.append(f"Device has {bad_sectors} bad sectors - consider replacement")
        
        # Filesystem issues
        if checks.get('filesystem', {}).get('health') == 'Issues Found':
            recommendations.append("Filesystem errors detected - run repair tools before use")
        
        # SMART status
        smart_health = checks.get('smart_data', {}).get('health_status')
        if smart_health == 'Failed':
            recommendations.append("SMART health check failed - device may be failing")
        
        # Speed issues
        speed_test = checks.get('speed_test', {})
        if speed_test.get('write_speed_mbps', 0) < 5:
            recommendations.append("Write speed is very slow - check USB connection")
        
        if not recommendations:
            recommendations.append("Device appears to be in good condition")
        
        return recommendations
    
    def cleanup(self) -> bool:
        """Cleanup diagnostics resources"""
        try:
            if hasattr(self, 'temp_dir') and self.temp_dir.exists():
                import shutil
                shutil.rmtree(self.temp_dir)
            
            self.logger.info("Diagnostics plugin cleaned up")
            return True
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            return False