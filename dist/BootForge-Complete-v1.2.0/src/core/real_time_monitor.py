"""
BootForge Real-Time Health Monitoring System
Continuous monitoring of system health, device performance, and operation safety
"""

import logging
import time
import threading
import queue
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
import psutil
import json
from pathlib import Path


class MonitoringLevel(Enum):
    """Monitoring intensity levels"""
    BASIC = "basic"
    STANDARD = "standard" 
    INTENSIVE = "intensive"
    DIAGNOSTIC = "diagnostic"


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning" 
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class HealthMetric:
    """Single health metric measurement"""
    name: str
    value: float
    unit: str
    threshold_warning: float
    threshold_critical: float
    timestamp: float = field(default_factory=time.time)
    
    @property
    def severity(self) -> AlertSeverity:
        """Determine severity based on thresholds"""
        if self.value >= self.threshold_critical:
            return AlertSeverity.CRITICAL
        elif self.value >= self.threshold_warning:
            return AlertSeverity.WARNING
        return AlertSeverity.INFO


@dataclass
class DeviceHealthReport:
    """Health report for a specific device"""
    device_path: str
    device_name: str
    metrics: List[HealthMetric] = field(default_factory=list)
    last_updated: float = field(default_factory=time.time)
    overall_health: str = "good"  # good, warning, critical
    
    def add_metric(self, metric: HealthMetric):
        """Add a health metric"""
        self.metrics.append(metric)
        self.last_updated = time.time()
        self._update_overall_health()
    
    def _update_overall_health(self):
        """Update overall health status"""
        if any(m.severity == AlertSeverity.CRITICAL for m in self.metrics):
            self.overall_health = "critical"
        elif any(m.severity == AlertSeverity.WARNING for m in self.metrics):
            self.overall_health = "warning"
        else:
            self.overall_health = "good"


@dataclass
class SystemHealthReport:
    """Comprehensive system health report"""
    cpu_percent: float
    memory_percent: float  
    temperature: Optional[float] = None
    disk_io_read_mbps: float = 0.0
    disk_io_write_mbps: float = 0.0
    network_sent_mbps: float = 0.0
    network_recv_mbps: float = 0.0
    active_processes: int = 0
    timestamp: float = field(default_factory=time.time)
    
    @property
    def overall_health(self) -> AlertSeverity:
        """Determine overall system health"""
        if (self.cpu_percent > 90 or 
            self.memory_percent > 90 or 
            (self.temperature and self.temperature > 85)):
            return AlertSeverity.CRITICAL
        elif (self.cpu_percent > 70 or 
              self.memory_percent > 75 or 
              (self.temperature and self.temperature > 75)):
            return AlertSeverity.WARNING
        return AlertSeverity.INFO


class HealthMonitor(ABC):
    """Base class for health monitors"""
    
    def __init__(self, name: str, update_interval: float = 1.0):
        self.name = name
        self.update_interval = update_interval
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self.callbacks: List[Callable[[Any], None]] = []
    
    def add_callback(self, callback: Callable[[Any], None]):
        """Add callback for monitor updates"""
        self.callbacks.append(callback)
    
    def start(self):
        """Start monitoring"""
        if self.is_running:
            return
        
        self.is_running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        self.logger.info(f"{self.name} monitor started")
    
    def stop(self):
        """Stop monitoring"""
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        self.logger.info(f"{self.name} monitor stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                data = self.collect_metrics()
                for callback in self.callbacks:
                    callback(data)
                time.sleep(self.update_interval)
            except Exception as e:
                self.logger.error(f"Error in {self.name} monitor: {e}")
                time.sleep(self.update_interval)
    
    @abstractmethod
    def collect_metrics(self) -> Any:
        """Collect health metrics"""
        pass


class SystemHealthMonitor(HealthMonitor):
    """Monitors overall system health"""
    
    def __init__(self, update_interval: float = 2.0):
        super().__init__("System Health", update_interval)
        self._last_disk_io = None
        self._last_network_io = None
        self._last_time = None
    
    def collect_metrics(self) -> SystemHealthReport:
        """Collect system health metrics"""
        current_time = time.time()
        
        # CPU and Memory
        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        
        # Temperature (if available)
        temperature = None
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                # Get CPU temperature if available
                for name, entries in temps.items():
                    if 'cpu' in name.lower() or 'core' in name.lower():
                        temperature = entries[0].current if entries else None
                        break
        except:
            pass
        
        # Disk I/O rates
        disk_io = psutil.disk_io_counters()
        disk_read_mbps = disk_write_mbps = 0.0
        
        if self._last_disk_io and self._last_time:
            time_diff = current_time - self._last_time
            if time_diff > 0:
                read_diff = disk_io.read_bytes - self._last_disk_io.read_bytes
                write_diff = disk_io.write_bytes - self._last_disk_io.write_bytes
                disk_read_mbps = (read_diff / time_diff) / (1024 * 1024)
                disk_write_mbps = (write_diff / time_diff) / (1024 * 1024)
        
        self._last_disk_io = disk_io
        
        # Network I/O rates
        net_io = psutil.net_io_counters()
        net_sent_mbps = net_recv_mbps = 0.0
        
        if self._last_network_io and self._last_time:
            time_diff = current_time - self._last_time
            if time_diff > 0:
                sent_diff = net_io.bytes_sent - self._last_network_io.bytes_sent
                recv_diff = net_io.bytes_recv - self._last_network_io.bytes_recv
                net_sent_mbps = (sent_diff / time_diff) / (1024 * 1024)
                net_recv_mbps = (recv_diff / time_diff) / (1024 * 1024)
        
        self._last_network_io = net_io
        self._last_time = current_time
        
        # Process count
        active_processes = len(psutil.pids())
        
        return SystemHealthReport(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            temperature=temperature,
            disk_io_read_mbps=disk_read_mbps,
            disk_io_write_mbps=disk_write_mbps,
            network_sent_mbps=net_sent_mbps,
            network_recv_mbps=net_recv_mbps,
            active_processes=active_processes
        )


class DeviceHealthMonitor(HealthMonitor):
    """Monitors storage device health"""
    
    def __init__(self, device_path: str, update_interval: float = 5.0):
        super().__init__(f"Device Health ({device_path})", update_interval)
        self.device_path = device_path
        self._last_io = None
        self._last_time = None
    
    def collect_metrics(self) -> DeviceHealthReport:
        """Collect device-specific health metrics"""
        report = DeviceHealthReport(self.device_path, self.device_path)
        current_time = time.time()
        
        try:
            # Disk usage
            usage = psutil.disk_usage(self.device_path)
            report.add_metric(HealthMetric(
                "disk_usage_percent",
                (usage.used / usage.total) * 100,
                "%",
                80.0,  # Warning at 80%
                95.0   # Critical at 95%
            ))
            
            # I/O performance
            io_counters = psutil.disk_io_counters(perdisk=True)
            device_name = self.device_path.split('/')[-1]
            
            if device_name in io_counters and self._last_io and self._last_time:
                current_io = io_counters[device_name]
                time_diff = current_time - self._last_time
                
                if time_diff > 0:
                    # Read/write speeds in MB/s
                    read_speed = (current_io.read_bytes - self._last_io.read_bytes) / time_diff / (1024*1024)
                    write_speed = (current_io.write_bytes - self._last_io.write_bytes) / time_diff / (1024*1024)
                    
                    report.add_metric(HealthMetric(
                        "read_speed_mbps",
                        read_speed,
                        "MB/s",
                        100.0,  # Warning if read speed drops below 100 MB/s
                        10.0    # Critical if below 10 MB/s
                    ))
                    
                    report.add_metric(HealthMetric(
                        "write_speed_mbps", 
                        write_speed,
                        "MB/s",
                        50.0,   # Warning if write speed drops below 50 MB/s
                        5.0     # Critical if below 5 MB/s
                    ))
                
                self._last_io = current_io
            elif device_name in io_counters:
                self._last_io = io_counters[device_name]
            
            self._last_time = current_time
            
        except Exception as e:
            self.logger.error(f"Error collecting device metrics for {self.device_path}: {e}")
        
        return report


class RealTimeHealthManager:
    """Manages all health monitoring systems"""
    
    def __init__(self, monitoring_level: MonitoringLevel = MonitoringLevel.STANDARD):
        self.monitoring_level = monitoring_level
        self.logger = logging.getLogger(__name__)
        
        # Monitors
        self.system_monitor = SystemHealthMonitor(
            update_interval=self._get_system_update_interval()
        )
        self.device_monitors: Dict[str, DeviceHealthMonitor] = {}
        
        # Health data storage
        self.health_history: List[SystemHealthReport] = []
        self.device_health: Dict[str, DeviceHealthReport] = {}
        self.max_history_size = 1000
        
        # Alert callbacks
        self.alert_callbacks: List[Callable[[AlertSeverity, str, Any], None]] = []
        
        # Setup callbacks
        self.system_monitor.add_callback(self._on_system_health_update)
        
        self.logger.info(f"Real-Time Health Manager initialized with {monitoring_level.value} monitoring")
    
    def _get_system_update_interval(self) -> float:
        """Get system update interval based on monitoring level"""
        intervals = {
            MonitoringLevel.BASIC: 5.0,
            MonitoringLevel.STANDARD: 2.0,
            MonitoringLevel.INTENSIVE: 1.0,
            MonitoringLevel.DIAGNOSTIC: 0.5
        }
        return intervals.get(self.monitoring_level, 2.0)
    
    def add_alert_callback(self, callback: Callable[[AlertSeverity, str, Any], None]):
        """Add callback for health alerts"""
        self.alert_callbacks.append(callback)
    
    def start_monitoring(self):
        """Start all health monitoring"""
        self.logger.info("Starting comprehensive health monitoring...")
        self.system_monitor.start()
        
        for monitor in self.device_monitors.values():
            monitor.start()
    
    def stop_monitoring(self):
        """Stop all health monitoring"""
        self.logger.info("Stopping health monitoring...")
        self.system_monitor.stop()
        
        for monitor in self.device_monitors.values():
            monitor.stop()
    
    def add_device_monitor(self, device_path: str):
        """Add monitoring for a specific device"""
        if device_path not in self.device_monitors:
            monitor = DeviceHealthMonitor(
                device_path,
                update_interval=self._get_device_update_interval()
            )
            monitor.add_callback(lambda report: self._on_device_health_update(device_path, report))
            self.device_monitors[device_path] = monitor
            
            if self.system_monitor.is_running:
                monitor.start()
            
            self.logger.info(f"Added device monitor for {device_path}")
    
    def remove_device_monitor(self, device_path: str):
        """Remove monitoring for a device"""
        if device_path in self.device_monitors:
            self.device_monitors[device_path].stop()
            del self.device_monitors[device_path]
            if device_path in self.device_health:
                del self.device_health[device_path]
            self.logger.info(f"Removed device monitor for {device_path}")
    
    def _get_device_update_interval(self) -> float:
        """Get device update interval based on monitoring level"""
        intervals = {
            MonitoringLevel.BASIC: 10.0,
            MonitoringLevel.STANDARD: 5.0,
            MonitoringLevel.INTENSIVE: 2.0,
            MonitoringLevel.DIAGNOSTIC: 1.0
        }
        return intervals.get(self.monitoring_level, 5.0)
    
    def _on_system_health_update(self, report: SystemHealthReport):
        """Handle system health updates"""
        self.health_history.append(report)
        
        # Limit history size
        if len(self.health_history) > self.max_history_size:
            self.health_history = self.health_history[-self.max_history_size:]
        
        # Check for alerts
        severity = report.overall_health
        if severity in [AlertSeverity.WARNING, AlertSeverity.CRITICAL]:
            message = self._format_system_health_alert(report)
            self._trigger_alert(severity, "System Health", report, message)
    
    def _on_device_health_update(self, device_path: str, report: DeviceHealthReport):
        """Handle device health updates"""
        self.device_health[device_path] = report
        
        # Check for device alerts
        critical_metrics = [m for m in report.metrics if m.severity == AlertSeverity.CRITICAL]
        warning_metrics = [m for m in report.metrics if m.severity == AlertSeverity.WARNING]
        
        if critical_metrics:
            message = f"Critical issues on {device_path}: {', '.join(m.name for m in critical_metrics)}"
            self._trigger_alert(AlertSeverity.CRITICAL, "Device Health", report, message)
        elif warning_metrics:
            message = f"Warnings on {device_path}: {', '.join(m.name for m in warning_metrics)}"
            self._trigger_alert(AlertSeverity.WARNING, "Device Health", report, message)
    
    def _format_system_health_alert(self, report: SystemHealthReport) -> str:
        """Format system health alert message"""
        issues = []
        if report.cpu_percent > 90:
            issues.append(f"High CPU usage: {report.cpu_percent:.1f}%")
        if report.memory_percent > 90:
            issues.append(f"High memory usage: {report.memory_percent:.1f}%")
        if report.temperature and report.temperature > 85:
            issues.append(f"High temperature: {report.temperature:.1f}°C")
        
        return "; ".join(issues) if issues else "System health issues detected"
    
    def _trigger_alert(self, severity: AlertSeverity, category: str, data: Any, message: str):
        """Trigger health alert"""
        self.logger.log(
            logging.CRITICAL if severity == AlertSeverity.CRITICAL else logging.WARNING,
            f"Health Alert [{category}]: {message}"
        )
        
        for callback in self.alert_callbacks:
            try:
                callback(severity, message, data)
            except Exception as e:
                self.logger.error(f"Error in alert callback: {e}")
    
    def get_current_system_health(self) -> Optional[SystemHealthReport]:
        """Get latest system health report"""
        return self.health_history[-1] if self.health_history else None
    
    def get_device_health(self, device_path: str) -> Optional[DeviceHealthReport]:
        """Get latest device health report"""
        return self.device_health.get(device_path)
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive health summary"""
        system_health = self.get_current_system_health()
        
        summary = {
            "system": {
                "status": system_health.overall_health.value if system_health else "unknown",
                "cpu_percent": system_health.cpu_percent if system_health else 0,
                "memory_percent": system_health.memory_percent if system_health else 0,
                "temperature": system_health.temperature if system_health else None,
                "timestamp": system_health.timestamp if system_health else 0
            },
            "devices": {}
        }
        
        for device_path, health in self.device_health.items():
            summary["devices"][device_path] = {
                "status": health.overall_health,
                "metrics_count": len(health.metrics),
                "last_updated": health.last_updated
            }
        
        return summary
    
    def export_health_data(self, filepath: Path):
        """Export health data to JSON file"""
        try:
            data = {
                "export_timestamp": time.time(),
                "monitoring_level": self.monitoring_level.value,
                "system_history": [
                    {
                        "timestamp": r.timestamp,
                        "cpu_percent": r.cpu_percent,
                        "memory_percent": r.memory_percent,
                        "temperature": r.temperature,
                        "disk_io_read_mbps": r.disk_io_read_mbps,
                        "disk_io_write_mbps": r.disk_io_write_mbps,
                        "overall_health": r.overall_health.value
                    }
                    for r in self.health_history[-100:]  # Last 100 entries
                ],
                "device_health": {
                    device_path: {
                        "device_name": health.device_name,
                        "overall_health": health.overall_health,
                        "last_updated": health.last_updated,
                        "metrics": [
                            {
                                "name": m.name,
                                "value": m.value,
                                "unit": m.unit,
                                "severity": m.severity.value,
                                "timestamp": m.timestamp
                            }
                            for m in health.metrics
                        ]
                    }
                    for device_path, health in self.device_health.items()
                }
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.info(f"Health data exported to {filepath}")
            
        except Exception as e:
            self.logger.error(f"Failed to export health data: {e}")