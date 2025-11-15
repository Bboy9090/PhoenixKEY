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
            expected_plugins = ["DriverInjector", "Checkra1nIntegration", "Diagnostics"]
            
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

class TestConfigCustomSettings:
    """Test custom settings functionality added in config.py"""
    
    def test_custom_settings_storage(self):
        """Test that custom settings can be stored and retrieved"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.json"
            config = Config(str(config_file))
            
            # Set custom settings that aren't in AppConfig dataclass
            assert config.set("custom_key1", "custom_value1")
            assert config.set("custom_key2", 12345)
            assert config.set("custom_nested", {"nested": "data"})
            
            # Verify custom settings are stored
            assert config.get("custom_key1") == "custom_value1"
            assert config.get("custom_key2") == 12345
            assert config.get("custom_nested") == {"nested": "data"}
    
    def test_custom_settings_persistence(self):
        """Test that custom settings persist across save/load cycles"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.json"
            
            # Create config and set custom settings
            config1 = Config(str(config_file))
            config1.set("custom_plugin_setting", "plugin_value")
            config1.set("custom_number", 42)
            config1.set("custom_list", [1, 2, 3])
            assert config1.save()
            
            # Load config in new instance and verify custom settings
            config2 = Config(str(config_file))
            assert config2.get("custom_plugin_setting") == "plugin_value"
            assert config2.get("custom_number") == 42
            assert config2.get("custom_list") == [1, 2, 3]
    
    def test_known_fields_vs_custom_settings_separation(self):
        """Test that known fields and custom settings are properly separated"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.json"
            config = Config(str(config_file))
            
            # Set a known field
            assert config.set("log_level", "DEBUG")
            assert config.get("log_level") == "DEBUG"
            
            # Set a custom field with similar name
            assert config.set("custom_log_level", "CUSTOM_DEBUG")
            assert config.get("custom_log_level") == "CUSTOM_DEBUG"
            
            # Verify they don't interfere with each other
            assert config.get("log_level") == "DEBUG"
            assert config.get("custom_log_level") == "CUSTOM_DEBUG"
    
    def test_custom_settings_in_to_dict(self):
        """Test that custom settings appear in to_dict() output"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.json"
            config = Config(str(config_file))
            
            # Set both known and custom settings
            config.set("app_name", "TestApp")
            config.set("custom_feature", "enabled")
            config.set("custom_timeout", 30)
            
            # Get dictionary representation
            config_dict = config.to_dict()
            
            # Verify both types of settings are present
            assert "app_name" in config_dict
            assert config_dict["app_name"] == "TestApp"
            assert "custom_feature" in config_dict
            assert config_dict["custom_feature"] == "enabled"
            assert "custom_timeout" in config_dict
            assert config_dict["custom_timeout"] == 30
    
    def test_custom_settings_with_default_values(self):
        """Test custom settings with default values"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.json"
            config = Config(str(config_file))
            
            # Get non-existent custom setting with default
            assert config.get("nonexistent", "default_value") == "default_value"
            assert config.get("nonexistent", 999) == 999
            assert config.get("nonexistent") is None
    
    def test_mixed_config_load_with_custom_and_known_fields(self):
        """Test loading config file with both known and custom fields"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.json"
            
            # Create a config file manually with mixed content
            test_data = {
                "app_name": "BootForge",
                "version": "2.0.0",
                "log_level": "ERROR",
                "custom_plugin_path": "/custom/plugins",
                "experimental_feature": True,
                "custom_cache_ttl": 3600
            }
            
            with open(config_file, 'w') as f:
                json.dump(test_data, f)
            
            # Load config and verify separation
            config = Config(str(config_file))
            
            # Known fields should be in AppConfig
            assert config.get("app_name") == "BootForge"
            assert config.get("version") == "2.0.0"
            assert config.get("log_level") == "ERROR"
            
            # Custom fields should be accessible
            assert config.get("custom_plugin_path") == "/custom/plugins"
            assert config.get("experimental_feature") is True
            assert config.get("custom_cache_ttl") == 3600
    
    def test_custom_settings_overwrite(self):
        """Test that custom settings can be overwritten"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.json"
            config = Config(str(config_file))
            
            # Set initial custom setting
            config.set("custom_value", "initial")
            assert config.get("custom_value") == "initial"
            
            # Overwrite it
            config.set("custom_value", "updated")
            assert config.get("custom_value") == "updated"
            
            # Save and reload to verify persistence
            assert config.save()
            config2 = Config(str(config_file))
            assert config2.get("custom_value") == "updated"
    
    def test_custom_settings_with_complex_types(self):
        """Test custom settings with complex data types"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.json"
            config = Config(str(config_file))
            
            # Set various complex types
            config.set("custom_dict", {"key1": "value1", "key2": [1, 2, 3]})
            config.set("custom_list", [1, "two", 3.0, {"four": 4}])
            config.set("custom_nested", {
                "level1": {
                    "level2": {
                        "level3": "deep_value"
                    }
                }
            })
            
            # Save and reload
            assert config.save()
            config2 = Config(str(config_file))
            
            # Verify complex types are preserved
            assert config2.get("custom_dict") == {"key1": "value1", "key2": [1, 2, 3]}
            assert config2.get("custom_list") == [1, "two", 3.0, {"four": 4}]
            assert config2.get("custom_nested")["level1"]["level2"]["level3"] == "deep_value"
    
    def test_custom_settings_edge_cases(self):
        """Test edge cases for custom settings"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.json"
            config = Config(str(config_file))
            
            # Empty string
            config.set("empty_string", "")
            assert config.get("empty_string") == ""
            
            # Zero values
            config.set("zero_int", 0)
            config.set("zero_float", 0.0)
            assert config.get("zero_int") == 0
            assert config.get("zero_float") == 0.0
            
            # Boolean values
            config.set("bool_true", True)
            config.set("bool_false", False)
            assert config.get("bool_true") is True
            assert config.get("bool_false") is False
            
            # None value
            config.set("null_value", None)
            assert config.get("null_value") is None
            
            # Empty collections
            config.set("empty_list", [])
            config.set("empty_dict", {})
            assert config.get("empty_list") == []
            assert config.get("empty_dict") == {}


class TestConfigRobustness:
    """Test config robustness and error handling"""
    
    def test_config_handles_corrupted_json(self):
        """Test that config handles corrupted JSON gracefully"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.json"
            
            # Write corrupted JSON
            with open(config_file, 'w') as f:
                f.write("{ invalid json }")
            
            # Should not crash, should use defaults
            config = Config(str(config_file))
            assert config.get("app_name") == "BootForge"
    
    def test_config_handles_missing_fields_in_json(self):
        """Test that config handles missing required fields"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.json"
            
            # Write JSON with only some fields
            partial_data = {"app_name": "PartialApp"}
            with open(config_file, 'w') as f:
                json.dump(partial_data, f)
            
            # Should fill in defaults for missing fields
            config = Config(str(config_file))
            assert config.get("app_name") == "PartialApp"
            assert config.get("version") == "1.0.0"  # Should use default
            assert config.get("log_level") == "INFO"  # Should use default
    
    def test_config_handles_extra_fields_gracefully(self):
        """Test that config handles extra unknown fields"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.json"
            
            # Write JSON with extra fields
            data_with_extras = {
                "app_name": "BootForge",
                "version": "1.0.0",
                "unknown_field_1": "value1",
                "unknown_field_2": 123
            }
            with open(config_file, 'w') as f:
                json.dump(data_with_extras, f)
            
            # Should load without error and preserve extra fields
            config = Config(str(config_file))
            assert config.get("app_name") == "BootForge"
            assert config.get("unknown_field_1") == "value1"
            assert config.get("unknown_field_2") == 123


class TestConfigKnownFieldsTracking:
    """Test the _known_fields tracking mechanism"""
    
    def test_known_fields_initialization(self):
        """Test that _known_fields is properly initialized"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.json"
            config = Config(str(config_file))
            
            # Verify known fields contains AppConfig fields
            assert "app_name" in config._known_fields
            assert "version" in config._known_fields
            assert "log_level" in config._known_fields
            assert "max_concurrent_writes" in config._known_fields
            
            # Verify it doesn't contain non-existent fields
            assert "nonexistent_field" not in config._known_fields
    
    def test_set_uses_known_fields_for_routing(self):
        """Test that set() routes to correct storage based on _known_fields"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.json"
            config = Config(str(config_file))
            
            # Set known field - should go to _config
            config.set("version", "3.0.0")
            assert hasattr(config._config, "version")
            assert config._config.version == "3.0.0"
            assert "version" not in config._custom_settings
            
            # Set unknown field - should go to _custom_settings
            config.set("custom_field", "custom_value")
            assert "custom_field" in config._custom_settings
            assert config._custom_settings["custom_field"] == "custom_value"
    
    def test_get_checks_both_sources(self):
        """Test that get() checks both known fields and custom settings"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.json"
            config = Config(str(config_file))
            
            # Set values in both sources
            config.set("app_name", "TestApp")  # known field
            config.set("custom_setting", "CustomValue")  # custom field
            
            # Verify get() retrieves from both
            assert config.get("app_name") == "TestApp"
            assert config.get("custom_setting") == "CustomValue"
            
            # Verify precedence: known fields first
            assert config.get("app_name") == config._config.app_name


import json