"""
BootForge Hardware Auto Detection System
Intelligent hardware detection for automatic profile matching and deployment optimization
"""

import os
import re
import json
import time
import logging
import platform
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum

from src.core.models import HardwareProfile


class DetectionConfidence(Enum):
    """Hardware detection confidence levels"""
    EXACT_MATCH = "exact"           # 100% confident (exact model match)
    HIGH_CONFIDENCE = "high"        # 80-99% confident (partial match with strong indicators)
    MEDIUM_CONFIDENCE = "medium"    # 60-79% confident (generic detection with some specifics)
    LOW_CONFIDENCE = "low"          # 40-59% confident (fallback/generic detection)
    UNKNOWN = "unknown"             # <40% confident (detection failed/insufficient data)


@dataclass
class DetectedHardware:
    """Detected hardware information"""
    # System identification
    system_name: Optional[str] = None
    system_manufacturer: Optional[str] = None
    system_model: Optional[str] = None
    system_serial: Optional[str] = None
    
    # CPU information
    cpu_name: Optional[str] = None
    cpu_manufacturer: Optional[str] = None
    cpu_architecture: Optional[str] = None
    cpu_cores: Optional[int] = None
    cpu_threads: Optional[int] = None
    
    # Memory information
    total_ram_gb: Optional[float] = None
    ram_modules: List[Dict[str, Any]] = field(default_factory=list)
    
    # GPU information
    gpus: List[Dict[str, Any]] = field(default_factory=list)
    primary_gpu: Optional[str] = None
    
    # Network information
    network_adapters: List[Dict[str, Any]] = field(default_factory=list)
    
    # Storage information
    storage_devices: List[Dict[str, Any]] = field(default_factory=list)
    
    # Platform-specific data
    platform: str = ""
    platform_version: Optional[str] = None
    bios_info: Dict[str, Any] = field(default_factory=dict)
    
    # Detection metadata
    detection_confidence: DetectionConfidence = DetectionConfidence.UNKNOWN
    detection_time: Optional[float] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def get_summary(self) -> str:
        """Get a human-readable summary of detected hardware"""
        parts = []
        
        if self.system_manufacturer and self.system_model:
            parts.append(f"{self.system_manufacturer} {self.system_model}")
        elif self.system_name:
            parts.append(self.system_name)
        
        if self.cpu_name:
            parts.append(f"CPU: {self.cpu_name}")
        
        if self.total_ram_gb:
            parts.append(f"RAM: {self.total_ram_gb:.1f}GB")
        
        if self.primary_gpu:
            parts.append(f"GPU: {self.primary_gpu}")
        
        return " | ".join(parts) if parts else "Unknown System"


@dataclass
class ProfileMatch:
    """Hardware profile match result"""
    profile: HardwareProfile
    confidence: DetectionConfidence
    match_score: float  # 0-100
    match_reasons: List[str] = field(default_factory=list)
    detection_data: Optional[DetectedHardware] = None
    
    def get_confidence_text(self) -> str:
        """Get human-readable confidence description"""
        confidence_map = {
            DetectionConfidence.EXACT_MATCH: "Exact Match",
            DetectionConfidence.HIGH_CONFIDENCE: "High Confidence",
            DetectionConfidence.MEDIUM_CONFIDENCE: "Medium Confidence", 
            DetectionConfidence.LOW_CONFIDENCE: "Low Confidence",
            DetectionConfidence.UNKNOWN: "Unknown"
        }
        return confidence_map.get(self.confidence, "Unknown")


class PlatformDetector(ABC):
    """Abstract base class for platform-specific hardware detection"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def detect_hardware(self) -> DetectedHardware:
        """Detect hardware on this platform"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if detection is available on this platform"""
        pass
    
    def _run_command(self, command: List[str], timeout: int = 30) -> Tuple[str, str, int]:
        """Safely run a system command with timeout"""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            self.logger.warning(f"Command timed out: {' '.join(command)}")
            return "", "Command timed out", -1
        except (OSError, subprocess.SubprocessError) as e:
            self.logger.error(f"Command execution failed: {e}")
            return "", str(e), -1


class WindowsDetector(PlatformDetector):
    """Windows-specific hardware detection using PowerShell and WMI/CIM"""
    
    def detect_hardware(self) -> DetectedHardware:
        """Detect hardware on Windows using PowerShell CIM queries"""
        hardware = DetectedHardware(platform="windows")
        
        try:
            # Detect system information
            self._detect_system_info(hardware)
            
            # Detect CPU information
            self._detect_cpu_info(hardware)
            
            # Detect memory information
            self._detect_memory_info(hardware)
            
            # Detect GPU information
            self._detect_gpu_info(hardware)
            
            # Detect network adapters
            self._detect_network_info(hardware)
            
            # Detect storage devices
            self._detect_storage_info(hardware)
            
            # Set confidence based on detection success
            hardware.detection_confidence = self._calculate_confidence(hardware)
            
        except Exception as e:
            self.logger.error(f"Windows hardware detection failed: {e}")
            hardware.detection_confidence = DetectionConfidence.UNKNOWN
        
        return hardware
    
    def is_available(self) -> bool:
        """Check if Windows detection is available"""
        return platform.system().lower() == "windows"
    
    def _detect_system_info(self, hardware: DetectedHardware):
        """Detect system information using Win32_ComputerSystem"""
        command = [
            "powershell", "-Command",
            "Get-CimInstance Win32_ComputerSystem | Select-Object Name,Manufacturer,Model,TotalPhysicalMemory | ConvertTo-Json"
        ]
        
        stdout, stderr, returncode = self._run_command(command)
        if returncode == 0 and stdout.strip():
            try:
                data = json.loads(stdout)
                hardware.system_name = data.get("Name")
                hardware.system_manufacturer = data.get("Manufacturer")
                hardware.system_model = data.get("Model")
                
                # Convert total physical memory to GB
                total_memory = data.get("TotalPhysicalMemory")
                if total_memory:
                    hardware.total_ram_gb = int(total_memory) / (1024 ** 3)
                
                hardware.raw_data["win32_computer_system"] = data
                
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse system info JSON: {e}")
    
    def _detect_cpu_info(self, hardware: DetectedHardware):
        """Detect CPU information using Win32_Processor"""
        command = [
            "powershell", "-Command",
            "Get-CimInstance Win32_Processor | Select-Object Name,Manufacturer,Architecture,NumberOfCores,NumberOfLogicalProcessors | ConvertTo-Json"
        ]
        
        stdout, stderr, returncode = self._run_command(command)
        if returncode == 0 and stdout.strip():
            try:
                data = json.loads(stdout)
                # Handle both single processor and array of processors
                if isinstance(data, list):
                    data = data[0]  # Take the first processor
                
                hardware.cpu_name = data.get("Name", "").strip()
                hardware.cpu_manufacturer = data.get("Manufacturer")
                hardware.cpu_cores = data.get("NumberOfCores")
                hardware.cpu_threads = data.get("NumberOfLogicalProcessors")
                
                # Map architecture codes to standard names
                arch_map = {0: "x86", 1: "MIPS", 2: "Alpha", 3: "PowerPC", 6: "ia64", 9: "x64"}
                arch_code = data.get("Architecture")
                if arch_code in arch_map:
                    hardware.cpu_architecture = arch_map[arch_code]
                
                hardware.raw_data["win32_processor"] = data
                
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse CPU info JSON: {e}")
    
    def _detect_memory_info(self, hardware: DetectedHardware):
        """Detect memory modules using Win32_PhysicalMemory"""
        command = [
            "powershell", "-Command", 
            "Get-CimInstance Win32_PhysicalMemory | Select-Object Capacity,Speed,Manufacturer,PartNumber | ConvertTo-Json"
        ]
        
        stdout, stderr, returncode = self._run_command(command)
        if returncode == 0 and stdout.strip():
            try:
                data = json.loads(stdout)
                if not isinstance(data, list):
                    data = [data]  # Ensure it's a list
                
                for module in data:
                    capacity_gb = int(module.get("Capacity", 0)) / (1024 ** 3) if module.get("Capacity") else 0
                    hardware.ram_modules.append({
                        "capacity_gb": capacity_gb,
                        "speed": module.get("Speed"),
                        "manufacturer": module.get("Manufacturer"),
                        "part_number": module.get("PartNumber")
                    })
                
                hardware.raw_data["win32_physical_memory"] = data
                
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse memory info JSON: {e}")
    
    def _detect_gpu_info(self, hardware: DetectedHardware):
        """Detect GPU information using Win32_VideoController"""
        command = [
            "powershell", "-Command",
            "Get-CimInstance Win32_VideoController | Where-Object {$_.Name -notlike '*Remote*'} | Select-Object Name,AdapterCompatibility,DriverVersion,AdapterRAM | ConvertTo-Json"
        ]
        
        stdout, stderr, returncode = self._run_command(command)
        if returncode == 0 and stdout.strip():
            try:
                data = json.loads(stdout)
                if not isinstance(data, list):
                    data = [data]
                
                for gpu in data:
                    gpu_name = gpu.get("Name", "").strip()
                    if gpu_name and "remote" not in gpu_name.lower():
                        gpu_info = {
                            "name": gpu_name,
                            "vendor": gpu.get("AdapterCompatibility"),
                            "driver_version": gpu.get("DriverVersion"),
                            "memory_bytes": gpu.get("AdapterRAM")
                        }
                        hardware.gpus.append(gpu_info)
                        
                        # Set primary GPU (usually the first discrete GPU or integrated if only one)
                        if not hardware.primary_gpu:
                            hardware.primary_gpu = gpu_name
                
                hardware.raw_data["win32_video_controller"] = data
                
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse GPU info JSON: {e}")
    
    def _detect_network_info(self, hardware: DetectedHardware):
        """Detect network adapters using Win32_NetworkAdapter"""
        command = [
            "powershell", "-Command",
            "Get-CimInstance Win32_NetworkAdapter | Where-Object {$_.PhysicalAdapter -eq $true -and $_.NetConnectionStatus -ne $null} | Select-Object Name,Manufacturer,MACAddress,Speed | ConvertTo-Json"
        ]
        
        stdout, stderr, returncode = self._run_command(command)
        if returncode == 0 and stdout.strip():
            try:
                data = json.loads(stdout)
                if not isinstance(data, list):
                    data = [data]
                
                for adapter in data:
                    if adapter.get("Name"):
                        hardware.network_adapters.append({
                            "name": adapter.get("Name"),
                            "manufacturer": adapter.get("Manufacturer"),
                            "mac_address": adapter.get("MACAddress"),
                            "speed": adapter.get("Speed")
                        })
                
                hardware.raw_data["win32_network_adapter"] = data
                
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse network info JSON: {e}")
    
    def _detect_storage_info(self, hardware: DetectedHardware):
        """Detect storage devices using Win32_DiskDrive"""
        command = [
            "powershell", "-Command",
            "Get-CimInstance Win32_DiskDrive | Select-Object Model,Manufacturer,Size,MediaType | ConvertTo-Json"
        ]
        
        stdout, stderr, returncode = self._run_command(command)
        if returncode == 0 and stdout.strip():
            try:
                data = json.loads(stdout)
                if not isinstance(data, list):
                    data = [data]
                
                for disk in data:
                    if disk.get("Model"):
                        size_gb = int(disk.get("Size", 0)) / (1024 ** 3) if disk.get("Size") else 0
                        hardware.storage_devices.append({
                            "model": disk.get("Model"),
                            "manufacturer": disk.get("Manufacturer"),
                            "size_gb": size_gb,
                            "media_type": disk.get("MediaType")
                        })
                
                hardware.raw_data["win32_disk_drive"] = data
                
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse storage info JSON: {e}")
    
    def _calculate_confidence(self, hardware: DetectedHardware) -> DetectionConfidence:
        """Calculate detection confidence based on available data"""
        confidence_factors = 0
        total_factors = 5
        
        if hardware.system_manufacturer and hardware.system_model:
            confidence_factors += 1
        if hardware.cpu_name:
            confidence_factors += 1
        if hardware.total_ram_gb:
            confidence_factors += 1
        if hardware.gpus:
            confidence_factors += 1
        if hardware.network_adapters:
            confidence_factors += 1
        
        confidence_ratio = confidence_factors / total_factors
        
        if confidence_ratio >= 0.8:
            return DetectionConfidence.HIGH_CONFIDENCE
        elif confidence_ratio >= 0.6:
            return DetectionConfidence.MEDIUM_CONFIDENCE
        elif confidence_ratio >= 0.4:
            return DetectionConfidence.LOW_CONFIDENCE
        else:
            return DetectionConfidence.UNKNOWN


class LinuxDetector(PlatformDetector):
    """Linux-specific hardware detection using system tools"""
    
    def detect_hardware(self) -> DetectedHardware:
        """Detect hardware on Linux using various system tools"""
        hardware = DetectedHardware(platform="linux")
        
        try:
            # Detect system information
            self._detect_system_info(hardware)
            
            # Detect CPU information  
            self._detect_cpu_info(hardware)
            
            # Detect memory information
            self._detect_memory_info(hardware)
            
            # Detect GPU information
            self._detect_gpu_info(hardware)
            
            # Detect network information
            self._detect_network_info(hardware)
            
            # Detect storage information
            self._detect_storage_info(hardware)
            
            # Set confidence based on detection success
            hardware.detection_confidence = self._calculate_confidence(hardware)
            
        except Exception as e:
            self.logger.error(f"Linux hardware detection failed: {e}")
            hardware.detection_confidence = DetectionConfidence.UNKNOWN
        
        return hardware
    
    def is_available(self) -> bool:
        """Check if Linux detection is available"""
        return platform.system().lower() == "linux"
    
    def _detect_system_info(self, hardware: DetectedHardware):
        """Detect system information using DMI data"""
        # Try dmidecode first (requires root on some systems)
        dmi_commands = [
            ["dmidecode", "-s", "system-manufacturer"],
            ["dmidecode", "-s", "system-product-name"],
            ["dmidecode", "-s", "system-serial-number"]
        ]
        
        dmi_results = []
        for cmd in dmi_commands:
            stdout, stderr, returncode = self._run_command(cmd)
            dmi_results.append(stdout.strip() if returncode == 0 else "")
        
        hardware.system_manufacturer = dmi_results[0] if dmi_results[0] else None
        hardware.system_model = dmi_results[1] if dmi_results[1] else None
        hardware.system_serial = dmi_results[2] if dmi_results[2] else None
        
        # Fallback to /sys/class/dmi/id/ if dmidecode fails
        if not hardware.system_manufacturer:
            try:
                with open("/sys/class/dmi/id/sys_vendor", "r") as f:
                    hardware.system_manufacturer = f.read().strip()
            except (IOError, OSError):
                pass
        
        if not hardware.system_model:
            try:
                with open("/sys/class/dmi/id/product_name", "r") as f:
                    hardware.system_model = f.read().strip()
            except (IOError, OSError):
                pass
    
    def _detect_cpu_info(self, hardware: DetectedHardware):
        """Detect CPU information from /proc/cpuinfo"""
        try:
            with open("/proc/cpuinfo", "r") as f:
                cpuinfo = f.read()
            
            # Parse CPU information
            lines = cpuinfo.split("\n")
            cpu_data = {}
            
            for line in lines:
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key == "model name":
                        hardware.cpu_name = value
                    elif key == "cpu cores":
                        hardware.cpu_cores = int(value)
                    elif key == "siblings":
                        hardware.cpu_threads = int(value)
                    elif key == "vendor_id":
                        hardware.cpu_manufacturer = value
            
            # Detect architecture
            stdout, stderr, returncode = self._run_command(["uname", "-m"])
            if returncode == 0:
                arch = stdout.strip()
                # Normalize architecture names
                if arch in ["x86_64", "amd64"]:
                    hardware.cpu_architecture = "x86_64"
                elif arch.startswith("arm") or arch.startswith("aarch"):
                    hardware.cpu_architecture = "arm64"
                else:
                    hardware.cpu_architecture = arch
            
            hardware.raw_data["proc_cpuinfo"] = cpuinfo[:1000]  # First 1000 chars only
            
        except (IOError, OSError, ValueError) as e:
            self.logger.warning(f"Failed to read CPU info: {e}")
    
    def _detect_memory_info(self, hardware: DetectedHardware):
        """Detect memory information from /proc/meminfo"""
        try:
            with open("/proc/meminfo", "r") as f:
                meminfo = f.read()
            
            # Parse memory information
            for line in meminfo.split("\n"):
                if line.startswith("MemTotal:"):
                    # Extract memory size in kB and convert to GB
                    mem_kb = int(line.split()[1])
                    hardware.total_ram_gb = mem_kb / (1024 ** 2)
                    break
            
            hardware.raw_data["proc_meminfo"] = meminfo[:500]  # First 500 chars only
            
        except (IOError, OSError, ValueError) as e:
            self.logger.warning(f"Failed to read memory info: {e}")
    
    def _detect_gpu_info(self, hardware: DetectedHardware):
        """Detect GPU information using lspci"""
        stdout, stderr, returncode = self._run_command(["lspci", "-nn"])
        
        if returncode == 0:
            lines = stdout.split("\n")
            for line in lines:
                # Look for VGA controllers and 3D controllers
                if "VGA" in line or "3D controller" in line:
                    # Extract GPU name
                    if ":" in line:
                        gpu_line = line.split(":", 2)[-1].strip()
                        # Remove PCI vendor/device IDs if present
                        if "[" in gpu_line and "]" in gpu_line:
                            gpu_name = gpu_line.split("[")[0].strip()
                        else:
                            gpu_name = gpu_line
                        
                        gpu_info = {"name": gpu_name}
                        
                        # Identify vendor
                        gpu_lower = gpu_name.lower()
                        if "nvidia" in gpu_lower or "geforce" in gpu_lower or "quadro" in gpu_lower:
                            gpu_info["vendor"] = "NVIDIA"
                        elif "amd" in gpu_lower or "radeon" in gpu_lower:
                            gpu_info["vendor"] = "AMD"
                        elif "intel" in gpu_lower:
                            gpu_info["vendor"] = "Intel"
                        
                        hardware.gpus.append(gpu_info)
                        
                        if not hardware.primary_gpu:
                            hardware.primary_gpu = gpu_name
            
            hardware.raw_data["lspci"] = stdout[:1000]  # First 1000 chars only
    
    def _detect_network_info(self, hardware: DetectedHardware):
        """Detect network adapters using various methods"""
        # Try using lspci for PCI network cards
        stdout, stderr, returncode = self._run_command(["lspci", "-nn"])
        
        if returncode == 0:
            lines = stdout.split("\n")
            for line in lines:
                if "Ethernet controller" in line or "Network controller" in line:
                    if ":" in line:
                        adapter_name = line.split(":", 2)[-1].strip()
                        if "[" in adapter_name:
                            adapter_name = adapter_name.split("[")[0].strip()
                        
                        hardware.network_adapters.append({"name": adapter_name})
        
        # Try to get network interface names
        try:
            net_path = Path("/sys/class/net")
            if net_path.exists():
                for interface in net_path.iterdir():
                    if interface.name != "lo":  # Skip loopback
                        interface_info = {"interface": interface.name}
                        
                        # Try to get MAC address
                        try:
                            mac_file = interface / "address"
                            if mac_file.exists():
                                with open(mac_file, "r") as f:
                                    interface_info["mac_address"] = f.read().strip()
                        except (IOError, OSError):
                            pass
                        
                        hardware.network_adapters.append(interface_info)
        except (IOError, OSError):
            pass
    
    def _detect_storage_info(self, hardware: DetectedHardware):
        """Detect storage devices using lsblk"""
        stdout, stderr, returncode = self._run_command(["lsblk", "-bno", "NAME,SIZE,MODEL,TYPE"])
        
        if returncode == 0:
            lines = stdout.split("\n")[1:]  # Skip header
            for line in lines:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 4 and parts[3] == "disk":  # Only physical disks
                        name = parts[0]
                        try:
                            size_bytes = int(parts[1])
                            size_gb = size_bytes / (1024 ** 3)
                        except (ValueError, IndexError):
                            size_gb = 0
                        
                        model = " ".join(parts[2:-1]) if len(parts) > 4 else parts[2] if len(parts) > 2 else ""
                        
                        hardware.storage_devices.append({
                            "name": name,
                            "model": model,
                            "size_gb": size_gb
                        })
            
            hardware.raw_data["lsblk"] = stdout[:1000]  # First 1000 chars only
    
    def _calculate_confidence(self, hardware: DetectedHardware) -> DetectionConfidence:
        """Calculate detection confidence based on available data"""
        confidence_factors = 0
        total_factors = 5
        
        if hardware.system_manufacturer and hardware.system_model:
            confidence_factors += 1
        if hardware.cpu_name:
            confidence_factors += 1
        if hardware.total_ram_gb:
            confidence_factors += 1
        if hardware.gpus:
            confidence_factors += 1
        if hardware.network_adapters:
            confidence_factors += 1
        
        confidence_ratio = confidence_factors / total_factors
        
        if confidence_ratio >= 0.8:
            return DetectionConfidence.HIGH_CONFIDENCE
        elif confidence_ratio >= 0.6:
            return DetectionConfidence.MEDIUM_CONFIDENCE
        elif confidence_ratio >= 0.4:
            return DetectionConfidence.LOW_CONFIDENCE
        else:
            return DetectionConfidence.UNKNOWN


class MacOSDetector(PlatformDetector):
    """macOS-specific hardware detection using system_profiler and ioreg"""
    
    def detect_hardware(self) -> DetectedHardware:
        """Detect hardware on macOS using system_profiler"""
        hardware = DetectedHardware(platform="mac")
        
        try:
            # Detect system information
            self._detect_system_info(hardware)
            
            # Detect CPU information
            self._detect_cpu_info(hardware)
            
            # Detect memory information
            self._detect_memory_info(hardware)
            
            # Detect GPU information
            self._detect_gpu_info(hardware)
            
            # Detect network information
            self._detect_network_info(hardware)
            
            # Detect storage information
            self._detect_storage_info(hardware)
            
            # Set confidence based on detection success
            hardware.detection_confidence = self._calculate_confidence(hardware)
            
        except Exception as e:
            self.logger.error(f"macOS hardware detection failed: {e}")
            hardware.detection_confidence = DetectionConfidence.UNKNOWN
        
        return hardware
    
    def is_available(self) -> bool:
        """Check if macOS detection is available"""
        return platform.system().lower() == "darwin"
    
    def _detect_system_info(self, hardware: DetectedHardware):
        """Detect system information using system_profiler"""
        command = ["system_profiler", "SPHardwareDataType", "-json"]
        stdout, stderr, returncode = self._run_command(command, timeout=60)
        
        if returncode == 0 and stdout.strip():
            try:
                data = json.loads(stdout)
                hardware_info = data.get("SPHardwareDataType", [{}])[0]
                
                hardware.system_manufacturer = "Apple"
                hardware.system_model = hardware_info.get("machine_model")
                hardware.system_name = hardware_info.get("machine_name")
                hardware.system_serial = hardware_info.get("serial_number")
                
                # Memory information
                total_memory = hardware_info.get("physical_memory")
                if total_memory:
                    # Parse memory string like "16 GB"
                    memory_match = re.search(r"(\d+(?:\.\d+)?)\s*(GB|MB)", total_memory)
                    if memory_match:
                        amount = float(memory_match.group(1))
                        unit = memory_match.group(2)
                        if unit == "GB":
                            hardware.total_ram_gb = amount
                        elif unit == "MB":
                            hardware.total_ram_gb = amount / 1024
                
                hardware.raw_data["sphardware"] = hardware_info
                
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse system info JSON: {e}")
    
    def _detect_cpu_info(self, hardware: DetectedHardware):
        """Detect CPU information using system_profiler"""
        # CPU information is often in the hardware data type
        if "sphardware" in hardware.raw_data:
            hardware_info = hardware.raw_data["sphardware"]
            
            hardware.cpu_name = hardware_info.get("chip_type")
            if not hardware.cpu_name:
                hardware.cpu_name = hardware_info.get("cpu_type")
            
            # Parse number of cores
            cores_info = hardware_info.get("number_processors")
            if cores_info:
                # Parse strings like "1 (8 cores, 4 performance and 4 efficiency)"
                cores_match = re.search(r"(\d+)\s*cores?", cores_info)
                if cores_match:
                    hardware.cpu_cores = int(cores_match.group(1))
            
            # Determine architecture based on chip type
            if hardware.cpu_name:
                cpu_lower = hardware.cpu_name.lower()
                if "apple" in cpu_lower and ("m1" in cpu_lower or "m2" in cpu_lower or "m3" in cpu_lower):
                    hardware.cpu_architecture = "arm64"
                    hardware.cpu_manufacturer = "Apple"
                elif "intel" in cpu_lower:
                    hardware.cpu_architecture = "x86_64"
                    hardware.cpu_manufacturer = "Intel"
    
    def _detect_memory_info(self, hardware: DetectedHardware):
        """Detect detailed memory information"""
        command = ["system_profiler", "SPMemoryDataType", "-json"]
        stdout, stderr, returncode = self._run_command(command)
        
        if returncode == 0 and stdout.strip():
            try:
                data = json.loads(stdout)
                memory_data = data.get("SPMemoryDataType", [])
                
                for bank in memory_data:
                    if bank.get("_name") == "Memory":
                        # Parse memory modules
                        for key, value in bank.items():
                            if key.startswith("dimm") and isinstance(value, dict):
                                size_str = value.get("dimm_size", "")
                                size_match = re.search(r"(\d+)\s*(GB|MB)", size_str)
                                if size_match:
                                    amount = int(size_match.group(1))
                                    unit = size_match.group(2)
                                    size_gb = amount if unit == "GB" else amount / 1024
                                    
                                    hardware.ram_modules.append({
                                        "capacity_gb": size_gb,
                                        "speed": value.get("dimm_speed"),
                                        "type": value.get("dimm_type")
                                    })
                
                hardware.raw_data["spmemory"] = memory_data
                
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse memory info JSON: {e}")
    
    def _detect_gpu_info(self, hardware: DetectedHardware):
        """Detect GPU information using system_profiler"""
        command = ["system_profiler", "SPDisplaysDataType", "-json"]
        stdout, stderr, returncode = self._run_command(command)
        
        if returncode == 0 and stdout.strip():
            try:
                data = json.loads(stdout)
                displays_data = data.get("SPDisplaysDataType", [])
                
                for display in displays_data:
                    gpu_name = display.get("sppci_model")
                    if not gpu_name:
                        gpu_name = display.get("_name")
                    
                    if gpu_name:
                        gpu_info = {"name": gpu_name}
                        
                        # Get VRAM information
                        vram = display.get("spdisplays_vram")
                        if vram:
                            gpu_info["vram"] = vram
                        
                        # Identify vendor
                        gpu_lower = gpu_name.lower()
                        if "intel" in gpu_lower:
                            gpu_info["vendor"] = "Intel"
                        elif "amd" in gpu_lower or "radeon" in gpu_lower:
                            gpu_info["vendor"] = "AMD"
                        elif "nvidia" in gpu_lower:
                            gpu_info["vendor"] = "NVIDIA"
                        elif "apple" in gpu_lower:
                            gpu_info["vendor"] = "Apple"
                        
                        hardware.gpus.append(gpu_info)
                        
                        if not hardware.primary_gpu:
                            hardware.primary_gpu = gpu_name
                
                hardware.raw_data["spdisplays"] = displays_data
                
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse GPU info JSON: {e}")
    
    def _detect_network_info(self, hardware: DetectedHardware):
        """Detect network information using system_profiler"""
        command = ["system_profiler", "SPNetworkDataType", "-json"]
        stdout, stderr, returncode = self._run_command(command)
        
        if returncode == 0 and stdout.strip():
            try:
                data = json.loads(stdout)
                network_data = data.get("SPNetworkDataType", [])
                
                for interface in network_data:
                    interface_name = interface.get("_name", "")
                    if interface_name and interface_name not in ["Bluetooth", "Thunderbolt Bridge"]:
                        adapter_info = {
                            "name": interface_name,
                            "type": interface.get("spnetwork_interface_type"),
                            "mac_address": interface.get("spnetwork_ethernet_mac_address")
                        }
                        hardware.network_adapters.append(adapter_info)
                
                hardware.raw_data["spnetwork"] = network_data
                
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse network info JSON: {e}")
    
    def _detect_storage_info(self, hardware: DetectedHardware):
        """Detect storage information using system_profiler"""
        command = ["system_profiler", "SPStorageDataType", "-json"]
        stdout, stderr, returncode = self._run_command(command)
        
        if returncode == 0 and stdout.strip():
            try:
                data = json.loads(stdout)
                storage_data = data.get("SPStorageDataType", [])
                
                for device in storage_data:
                    device_name = device.get("_name", "")
                    if device_name:
                        # Parse size
                        size_str = device.get("com.apple.SystemProfiler.SPStorageReporter.FreeSizeBytes", "")
                        total_size_str = device.get("com.apple.SystemProfiler.SPStorageReporter.TotalSizeBytes", "")
                        
                        size_gb = 0
                        if total_size_str:
                            try:
                                size_gb = int(total_size_str) / (1024 ** 3)
                            except (ValueError, TypeError):
                                pass
                        
                        storage_info = {
                            "name": device_name,
                            "size_gb": size_gb,
                            "mount_point": device.get("mount_point"),
                            "file_system": device.get("file_system")
                        }
                        hardware.storage_devices.append(storage_info)
                
                hardware.raw_data["spstorage"] = storage_data
                
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse storage info JSON: {e}")
    
    def _calculate_confidence(self, hardware: DetectedHardware) -> DetectionConfidence:
        """Calculate detection confidence based on available data"""
        confidence_factors = 0
        total_factors = 5
        
        # macOS detection is generally very reliable
        if hardware.system_model:  # We almost always get system model on Mac
            confidence_factors += 2  # Double weight for system model
            total_factors += 1
        if hardware.cpu_name:
            confidence_factors += 1
        if hardware.total_ram_gb:
            confidence_factors += 1
        if hardware.gpus:
            confidence_factors += 1
        
        confidence_ratio = confidence_factors / total_factors
        
        if confidence_ratio >= 0.9:
            return DetectionConfidence.EXACT_MATCH  # Mac detection is very precise
        elif confidence_ratio >= 0.7:
            return DetectionConfidence.HIGH_CONFIDENCE
        elif confidence_ratio >= 0.5:
            return DetectionConfidence.MEDIUM_CONFIDENCE
        else:
            return DetectionConfidence.LOW_CONFIDENCE


class HardwareDetector:
    """Main hardware detection engine"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize platform-specific detectors
        self.detectors = {
            "windows": WindowsDetector(),
            "linux": LinuxDetector(),
            "mac": MacOSDetector()
        }
        
        # Detect current platform
        self.current_platform = self._detect_platform()
        self.logger.info(f"Detected platform: {self.current_platform}")
    
    def _detect_platform(self) -> str:
        """Detect the current operating system platform"""
        system = platform.system().lower()
        if system == "windows":
            return "windows"
        elif system == "linux":
            return "linux"
        elif system == "darwin":
            return "mac"
        else:
            self.logger.warning(f"Unknown platform: {system}")
            return "unknown"
    
    def detect_hardware(self) -> Optional[DetectedHardware]:
        """Detect hardware on the current platform"""
        if self.current_platform == "unknown":
            self.logger.error("Cannot detect hardware on unknown platform")
            return None
        
        detector = self.detectors.get(self.current_platform)
        if not detector:
            self.logger.error(f"No detector available for platform: {self.current_platform}")
            return None
        
        if not detector.is_available():
            self.logger.error(f"Detector not available for platform: {self.current_platform}")
            return None
        
        self.logger.info("Starting hardware detection...")
        start_time = time.time()
        
        try:
            hardware = detector.detect_hardware()
            hardware.detection_time = time.time() - start_time
            hardware.platform_version = platform.release()
            
            self.logger.info(f"Hardware detection completed in {hardware.detection_time:.2f}s")
            self.logger.info(f"Detection confidence: {hardware.detection_confidence.value}")
            self.logger.info(f"Hardware summary: {hardware.get_summary()}")
            
            return hardware
            
        except Exception as e:
            self.logger.error(f"Hardware detection failed: {e}")
            return None
    
    def get_available_detectors(self) -> List[str]:
        """Get list of available platform detectors"""
        available = []
        for platform_name, detector in self.detectors.items():
            if detector.is_available():
                available.append(platform_name)
        return available