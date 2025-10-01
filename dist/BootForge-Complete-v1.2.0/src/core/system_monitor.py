"""
BootForge System Monitor
Monitors system resources, temperature, and hardware health
"""

import os
import psutil
import time
import logging
import platform
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from PyQt6.QtCore import QThread, pyqtSignal, QTimer


@dataclass
class SystemInfo:
    """System information data structure"""
    cpu_percent: float
    memory_percent: float
    disk_usage: float
    temperature: Optional[float]
    network_io: Dict[str, int]
    disk_io: Dict[str, int]
    uptime: float
    platform: str
    architecture: str


@dataclass
class USBDevice:
    """USB device information"""
    path: str
    name: str
    size_bytes: int
    filesystem: str
    mountpoint: Optional[str]
    is_removable: bool
    vendor: str
    model: str
    serial: Optional[str]


class SystemMonitor(QThread):
    """System monitoring thread"""
    
    # Signals
    system_info_updated = pyqtSignal(SystemInfo)
    usb_devices_updated = pyqtSignal(list)
    thermal_warning = pyqtSignal(float)
    low_memory_warning = pyqtSignal(float)
    
    def __init__(self, update_interval: int = 5):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.update_interval = update_interval
        self.running = False
        self.thermal_threshold = 85.0
        self.memory_threshold = 90.0
        
        # Initialize baseline measurements
        self._last_network_io = psutil.net_io_counters()
        self._last_disk_io = psutil.disk_io_counters()
        self._last_time = time.time()
    
    def set_thresholds(self, thermal: float = 85.0, memory: float = 90.0):
        """Set warning thresholds"""
        self.thermal_threshold = thermal
        self.memory_threshold = memory
        self.logger.info(f"Updated thresholds - Thermal: {thermal}°C, Memory: {memory}%")
    
    def run(self):
        """Main monitoring loop"""
        self.running = True
        self.logger.info("System monitoring started")
        
        while self.running:
            try:
                # Collect system information
                system_info = self._collect_system_info()
                self.system_info_updated.emit(system_info)
                
                # Check for warnings
                if system_info.temperature and system_info.temperature > self.thermal_threshold:
                    self.thermal_warning.emit(system_info.temperature)
                
                if system_info.memory_percent > self.memory_threshold:
                    self.low_memory_warning.emit(system_info.memory_percent)
                
                # Collect USB devices
                usb_devices = self._detect_usb_devices()
                self.usb_devices_updated.emit(usb_devices)
                
                # Wait for next update
                self.msleep(self.update_interval * 1000)
                
            except Exception as e:
                self.logger.error(f"Error in system monitoring: {e}")
                self.msleep(1000)  # Brief pause before retry
    
    def stop(self):
        """Stop monitoring"""
        self.running = False
        self.logger.info("System monitoring stopped")
    
    def _collect_system_info(self) -> SystemInfo:
        """Collect current system information"""
        current_time = time.time()
        
        # CPU and Memory
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        
        # Disk usage (root partition)
        disk = psutil.disk_usage('/')
        disk_usage = (disk.used / disk.total) * 100
        
        # Temperature (if available)
        temperature = self._get_cpu_temperature()
        
        # Network I/O rates
        current_network = psutil.net_io_counters()
        network_io = self._calculate_io_rates(
            current_network, self._last_network_io, current_time, self._last_time
        )
        self._last_network_io = current_network
        
        # Disk I/O rates
        current_disk = psutil.disk_io_counters()
        disk_io = self._calculate_io_rates(
            current_disk, self._last_disk_io, current_time, self._last_time
        )
        self._last_disk_io = current_disk
        
        self._last_time = current_time
        
        # System info
        boot_time = psutil.boot_time()
        uptime = current_time - boot_time
        
        return SystemInfo(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            disk_usage=disk_usage,
            temperature=temperature,
            network_io=network_io,
            disk_io=disk_io,
            uptime=uptime,
            platform=platform.system(),
            architecture=platform.machine()
        )
    
    def _get_cpu_temperature(self) -> Optional[float]:
        """Get CPU temperature if available"""
        try:
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                
                # Try common temperature sensor names
                for sensor_name in ['coretemp', 'cpu_thermal', 'acpi']:
                    if sensor_name in temps:
                        for entry in temps[sensor_name]:
                            if 'Package' in entry.label or 'Core' in entry.label:
                                return entry.current
                        # If no specific core found, use first entry
                        if temps[sensor_name]:
                            return temps[sensor_name][0].current
                
                # Use any available temperature sensor
                for sensor_temps in temps.values():
                    if sensor_temps:
                        return sensor_temps[0].current
            
            return None
        except Exception as e:
            self.logger.debug(f"Could not read temperature: {e}")
            return None
    
    def _calculate_io_rates(self, current, previous, current_time, previous_time) -> Dict[str, int]:
        """Calculate I/O rates per second"""
        time_delta = current_time - previous_time
        if time_delta <= 0:
            return {'read': 0, 'write': 0}
        
        try:
            read_rate = (current.bytes_recv - previous.bytes_recv) / time_delta
            write_rate = (current.bytes_sent - previous.bytes_sent) / time_delta
            
            return {
                'read': int(read_rate),
                'write': int(write_rate)
            }
        except AttributeError:
            # Handle disk I/O counters
            try:
                read_rate = (current.read_bytes - previous.read_bytes) / time_delta
                write_rate = (current.write_bytes - previous.write_bytes) / time_delta
                
                return {
                    'read': int(read_rate),
                    'write': int(write_rate)
                }
            except AttributeError:
                return {'read': 0, 'write': 0}
    
    def _detect_usb_devices(self) -> List[USBDevice]:
        """Detect USB storage devices"""
        usb_devices = []
        
        try:
            # Get all disk partitions
            partitions = psutil.disk_partitions()
            
            for partition in partitions:
                try:
                    # Check if it's a removable device
                    if self._is_removable_device(partition.device):
                        # Get disk usage
                        usage = psutil.disk_usage(partition.mountpoint)
                        
                        # Create USB device info
                        device = USBDevice(
                            path=partition.device,
                            name=self._get_device_name(partition.device),
                            size_bytes=usage.total,
                            filesystem=partition.fstype,
                            mountpoint=partition.mountpoint,
                            is_removable=True,
                            vendor=self._get_device_vendor(partition.device),
                            model=self._get_device_model(partition.device),
                            serial=self._get_device_serial(partition.device)
                        )
                        
                        usb_devices.append(device)
                        
                except (PermissionError, OSError) as e:
                    self.logger.debug(f"Could not access device {partition.device}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error detecting USB devices: {e}")
        
        return usb_devices
    
    def _is_removable_device(self, device_path: str) -> bool:
        """Check if device is removable"""
        try:
            system = platform.system()
            
            if system == "Linux":
                # Check /sys/block for removable flag
                device_name = device_path.split('/')[-1].rstrip('0123456789')
                removable_file = f"/sys/block/{device_name}/removable"
                
                if os.path.exists(removable_file):
                    with open(removable_file, 'r') as f:
                        return f.read().strip() == '1'
                        
            elif system == "Windows":
                # On Windows, check drive type
                import ctypes
                drive_type = ctypes.windll.kernel32.GetDriveTypeW(device_path)
                return drive_type == 2  # DRIVE_REMOVABLE
                
            elif system == "Darwin":  # macOS
                # Check if device is in /Volumes (mounted external drives)
                return "/Volumes/" in device_path
                
            return False
            
        except Exception as e:
            self.logger.debug(f"Could not determine if device is removable: {e}")
            return False
    
    def _get_device_name(self, device_path: str) -> str:
        """Get human-readable device name"""
        try:
            system = platform.system()
            
            if system == "Linux":
                device_name = device_path.split('/')[-1]
                model_file = f"/sys/block/{device_name.rstrip('0123456789')}/device/model"
                
                if os.path.exists(model_file):
                    with open(model_file, 'r') as f:
                        return f.read().strip()
                        
            elif system == "Windows":
                # Use Windows API to get volume label
                import ctypes
                volume_name = ctypes.create_unicode_buffer(1024)
                ctypes.windll.kernel32.GetVolumeInformationW(
                    device_path, volume_name, ctypes.sizeof(volume_name),
                    None, None, None, None, 0
                )
                if volume_name.value:
                    return volume_name.value
                    
            return device_path.split('/')[-1]
            
        except Exception:
            return device_path.split('/')[-1]
    
    def _get_device_vendor(self, device_path: str) -> str:
        """Get device vendor"""
        try:
            system = platform.system()
            
            if system == "Linux":
                device_name = device_path.split('/')[-1].rstrip('0123456789')
                vendor_file = f"/sys/block/{device_name}/device/vendor"
                
                if os.path.exists(vendor_file):
                    with open(vendor_file, 'r') as f:
                        return f.read().strip()
                        
            return "Unknown"
            
        except Exception:
            return "Unknown"
    
    def _get_device_model(self, device_path: str) -> str:
        """Get device model"""
        return self._get_device_name(device_path)
    
    def _get_device_serial(self, device_path: str) -> Optional[str]:
        """Get device serial number"""
        try:
            system = platform.system()
            
            if system == "Linux":
                device_name = device_path.split('/')[-1].rstrip('0123456789')
                serial_file = f"/sys/block/{device_name}/device/serial"
                
                if os.path.exists(serial_file):
                    with open(serial_file, 'r') as f:
                        return f.read().strip()
                        
            return None
            
        except Exception:
            return None