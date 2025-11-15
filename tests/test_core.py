"""
BootForge Core Tests
Test suite for core functionality
"""

import pytest
import tempfile
import os
from pathlib import Path
import sys

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.config import Config, AppConfig
from src.core.disk_manager import DiskManager, DiskInfo
from src.plugins.plugin_manager import PluginManager


class TestConfig:
    """Test configuration management"""
    
    def test_config_creation(self):
        """Test configuration creation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.json"
            config = Config(str(config_file))
            
            assert config.get("app_name") == "BootForge"
            assert config.get("version") == "1.0.0"
            assert config_file.exists()
    
    def test_config_load_save(self):
        """Test configuration load and save"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.json"
            
            # Create and save config
            config = Config(str(config_file))
            config.set("test_value", "test_data")
            assert config.save()
            
            # Load config in new instance
            config2 = Config(str(config_file))
            assert config2.get("test_value") == "test_data"
    
    def test_app_config_defaults(self):
        """Test AppConfig defaults"""
        app_config = AppConfig()
        
        assert app_config.app_name == "BootForge"
        assert app_config.version == "1.0.0"
        assert app_config.log_level == "INFO"
        assert app_config.max_concurrent_writes == 2
        assert app_config.thermal_threshold == 85.0


class TestDiskManager:
    """Test disk management functionality"""
    
    def test_disk_manager_creation(self):
        """Test disk manager creation"""
        disk_manager = DiskManager()
        assert disk_manager is not None
    
    def test_get_removable_drives(self):
        """Test removable drive detection"""
        disk_manager = DiskManager()
        drives = disk_manager.get_removable_drives()
        
        # Should return a list (may be empty in test environment)
        assert isinstance(drives, list)
        
        # If drives found, check structure
        for drive in drives:
            assert isinstance(drive, DiskInfo)
            assert hasattr(drive, 'path')
            assert hasattr(drive, 'name')
            assert hasattr(drive, 'size_bytes')
    
    def test_disk_info_structure(self):
        """Test DiskInfo data structure"""
        disk_info = DiskInfo(
            path="/dev/test",
            name="Test Drive",
            size_bytes=1024*1024*1024,
            filesystem="fat32",
            mountpoint="/mnt/test",
            is_removable=True,
            model="Test Model",
            vendor="Test Vendor",
            serial="12345",
            health_status="Good",
            write_speed_mbps=25.0
        )
        
        assert disk_info.path == "/dev/test"
        assert disk_info.size_bytes == 1024*1024*1024
        assert disk_info.is_removable is True


class TestPluginManager:
    """Test plugin management functionality"""
    
    def test_plugin_manager_creation(self):
        """Test plugin manager creation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config()
            plugin_manager = PluginManager(config)
            assert plugin_manager is not None
    
    def test_plugin_discovery(self):
        """Test plugin discovery"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config()
            plugin_manager = PluginManager(config)
            
            # Discover built-in plugins
            plugins = plugin_manager.discover_plugins()
            
            # Should find built-in plugins
            assert isinstance(plugins, list)
            
            # Check for expected plugins
            plugin_names = [p.name for p in plugins]
            expected_plugins = ["DriverInjector", "Diagnostics"]
            
            for expected in expected_plugins:
                assert expected in plugin_names
    
    def test_plugin_loading(self):
        """Test plugin loading"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config()
            plugin_manager = PluginManager(config)
            
            # Discover plugins first
            plugins = plugin_manager.discover_plugins()
            
            if plugins:
                # Try to load first plugin
                plugin_name = plugins[0].name
                success = plugin_manager.load_plugin(plugin_name)
                
                # Loading might fail due to missing dependencies, but should not crash
                assert isinstance(success, bool)
                
                # Check loaded plugins
                loaded = plugin_manager.get_loaded_plugins()
                assert isinstance(loaded, list)


class TestIntegration:
    """Test integration between components"""
    
    def test_config_plugin_integration(self):
        """Test config and plugin manager integration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config()
            plugin_manager = PluginManager(config)
            
            # Should be able to access config
            assert plugin_manager.config is not None
            assert plugin_manager.config.get("app_name") == "BootForge"
    
    def test_disk_plugin_integration(self):
        """Test disk manager and plugin integration"""
        disk_manager = DiskManager()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config()
            plugin_manager = PluginManager(config)
            
            # Components should work together
            drives = disk_manager.get_removable_drives()
            plugins = plugin_manager.discover_plugins()
            
            assert isinstance(drives, list)
            assert isinstance(plugins, list)


if __name__ == "__main__":
    pytest.main([__file__])