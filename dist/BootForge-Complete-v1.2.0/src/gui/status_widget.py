"""
BootForge Status Widget
System status monitoring and display widget
"""

import logging
from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QProgressBar, QListWidget, QListWidgetItem,
    QGridLayout, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPalette

from src.core.system_monitor import SystemInfo
from src.core.disk_manager import DiskInfo


class SystemStatusWidget(QWidget):
    """System status display widget"""
    
    def __init__(self):
        super().__init__()
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup status UI"""
        layout = QVBoxLayout(self)
        
        # CPU Status
        cpu_group = QGroupBox("CPU")
        cpu_layout = QGridLayout(cpu_group)
        
        self.cpu_label = QLabel("--")
        self.cpu_progress = QProgressBar()
        self.cpu_progress.setMaximum(100)
        
        cpu_layout.addWidget(QLabel("Usage:"), 0, 0)
        cpu_layout.addWidget(self.cpu_label, 0, 1)
        cpu_layout.addWidget(self.cpu_progress, 1, 0, 1, 2)
        
        layout.addWidget(cpu_group)
        
        # Memory Status
        memory_group = QGroupBox("Memory")
        memory_layout = QGridLayout(memory_group)
        
        self.memory_label = QLabel("--")
        self.memory_progress = QProgressBar()
        self.memory_progress.setMaximum(100)
        
        memory_layout.addWidget(QLabel("Usage:"), 0, 0)
        memory_layout.addWidget(self.memory_label, 0, 1)
        memory_layout.addWidget(self.memory_progress, 1, 0, 1, 2)
        
        layout.addWidget(memory_group)
        
        # Temperature Status
        temp_group = QGroupBox("Temperature")
        temp_layout = QGridLayout(temp_group)
        
        self.temp_label = QLabel("--")
        self.temp_progress = QProgressBar()
        self.temp_progress.setMaximum(100)
        
        temp_layout.addWidget(QLabel("CPU:"), 0, 0)
        temp_layout.addWidget(self.temp_label, 0, 1)
        temp_layout.addWidget(self.temp_progress, 1, 0, 1, 2)
        
        layout.addWidget(temp_group)
        
        # Disk I/O Status
        io_group = QGroupBox("Disk I/O")
        io_layout = QGridLayout(io_group)
        
        self.read_label = QLabel("Read: --")
        self.write_label = QLabel("Write: --")
        
        io_layout.addWidget(self.read_label, 0, 0)
        io_layout.addWidget(self.write_label, 0, 1)
        
        layout.addWidget(io_group)
        
        layout.addStretch()
    
    def update_system_info(self, info: SystemInfo):
        """Update system information display"""
        # CPU
        self.cpu_label.setText(f"{info.cpu_percent:.1f}%")
        self.cpu_progress.setValue(int(info.cpu_percent))
        
        # Set CPU progress bar color based on usage
        if info.cpu_percent > 80:
            self.cpu_progress.setStyleSheet("QProgressBar::chunk { background-color: #ff6b6b; }")
        elif info.cpu_percent > 60:
            self.cpu_progress.setStyleSheet("QProgressBar::chunk { background-color: #ffd43b; }")
        else:
            self.cpu_progress.setStyleSheet("QProgressBar::chunk { background-color: #51cf66; }")
        
        # Memory
        self.memory_label.setText(f"{info.memory_percent:.1f}%")
        self.memory_progress.setValue(int(info.memory_percent))
        
        # Set memory progress bar color
        if info.memory_percent > 90:
            self.memory_progress.setStyleSheet("QProgressBar::chunk { background-color: #ff6b6b; }")
        elif info.memory_percent > 75:
            self.memory_progress.setStyleSheet("QProgressBar::chunk { background-color: #ffd43b; }")
        else:
            self.memory_progress.setStyleSheet("QProgressBar::chunk { background-color: #51cf66; }")
        
        # Temperature
        if info.temperature:
            self.temp_label.setText(f"{info.temperature:.1f}°C")
            temp_percent = min(100, (info.temperature / 100) * 100)  # Scale to 100%
            self.temp_progress.setValue(int(temp_percent))
            
            # Set temperature progress bar color
            if info.temperature > 85:
                self.temp_progress.setStyleSheet("QProgressBar::chunk { background-color: #ff6b6b; }")
            elif info.temperature > 70:
                self.temp_progress.setStyleSheet("QProgressBar::chunk { background-color: #ffd43b; }")
            else:
                self.temp_progress.setStyleSheet("QProgressBar::chunk { background-color: #51cf66; }")
        else:
            self.temp_label.setText("--")
            self.temp_progress.setValue(0)
        
        # Disk I/O
        read_mbps = info.disk_io['read'] / (1024 * 1024)
        write_mbps = info.disk_io['write'] / (1024 * 1024)
        
        self.read_label.setText(f"Read: {read_mbps:.1f} MB/s")
        self.write_label.setText(f"Write: {write_mbps:.1f} MB/s")


class DeviceListWidget(QWidget):
    """USB device list widget"""
    
    def __init__(self):
        super().__init__()
        self.devices = []
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup device list UI"""
        layout = QVBoxLayout(self)
        
        # Device list
        device_group = QGroupBox("USB Devices")
        device_layout = QVBoxLayout(device_group)
        
        self.device_list = QListWidget()
        device_layout.addWidget(self.device_list)
        
        layout.addWidget(device_group)
    
    def update_device_list(self, devices: List[DiskInfo]):
        """Update device list"""
        self.devices = devices
        self.device_list.clear()
        
        if not devices:
            item = QListWidgetItem("No USB devices detected")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.device_list.addItem(item)
            return
        
        for device in devices:
            size_gb = device.size_bytes / (1024**3)
            text = f"{device.name}\\n"
            text += f"Size: {size_gb:.1f} GB\\n"
            text += f"Path: {device.path}\\n"
            text += f"Health: {device.health_status}"
            
            item = QListWidgetItem(text)
            
            # Set item color based on health
            if device.health_status == "Good":
                item.setBackground(QPalette().color(QPalette.ColorRole.Base))
            else:
                item.setBackground(QPalette().color(QPalette.ColorRole.AlternateBase))
            
            self.device_list.addItem(item)


class StatusWidget(QWidget):
    """Main status widget combining system and device status"""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup main status UI"""
        layout = QVBoxLayout(self)
        
        # System status
        self.system_status = SystemStatusWidget()
        layout.addWidget(self.system_status)
        
        # Device list
        self.device_list = DeviceListWidget()
        layout.addWidget(self.device_list)
    
    def update_system_info(self, info: SystemInfo):
        """Update system information"""
        self.system_status.update_system_info(info)
    
    def update_device_list(self, devices: List[DiskInfo]):
        """Update device list"""
        self.device_list.update_device_list(devices)