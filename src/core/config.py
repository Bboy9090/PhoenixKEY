"""
BootForge Configuration Management
Handles application settings, preferences, and plugin configurations
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, fields


@dataclass
class AppConfig:
    """Application configuration settings"""
    app_name: str = "BootForge"
    version: str = "1.0.0"
    log_level: str = "INFO"
    temp_dir: str = ""
    max_concurrent_writes: int = 2
    thermal_threshold: float = 85.0
    auto_update_check: bool = True
    plugin_directories: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.plugin_directories is None:
            self.plugin_directories = ["plugins"]
        if not self.temp_dir:
            self.temp_dir = str(Path.home() / ".bootforge" / "temp")


class Config:
    """Central configuration manager for BootForge"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.logger = logging.getLogger(__name__)

        # Default configuration paths
        self.app_dir = Path.home() / ".bootforge"
        self.config_file = config_file or str(self.app_dir / "config.json")

        # Initialize configuration
        self._config = AppConfig()
        self._custom_settings: Dict[str, Any] = {}
        self._known_fields = {f.name for f in fields(AppConfig)}
        self._ensure_directories()
        self.load()
    
    def _ensure_directories(self):
        """Create necessary application directories"""
        directories = [
            self.app_dir,
            Path(self._config.temp_dir),
            self.app_dir / "logs",
            self.app_dir / "plugins",
            self.app_dir / "cache"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Ensured directory exists: {directory}")
    
    def load(self) -> bool:
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    app_values = {k: v for k, v in data.items() if k in self._known_fields}
                    self._custom_settings = {k: v for k, v in data.items() if k not in self._known_fields}
                    self._config = AppConfig(**app_values)
                    self.logger.info(f"Configuration loaded from {self.config_file}")
                    return True
            else:
                self.logger.info("No configuration file found, using defaults")
                self.save()  # Create default config file
                return False
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            return False

    def save(self) -> bool:
        """Save configuration to file"""
        try:
            self._ensure_directories()
            with open(self.config_file, 'w') as f:
                data = asdict(self._config)
                data.update(self._custom_settings)
                json.dump(data, f, indent=2)
            self.logger.info(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        if hasattr(self._config, key):
            return getattr(self._config, key)
        return self._custom_settings.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """Set configuration value"""
        try:
            if key in self._known_fields:
                setattr(self._config, key, value)
                self.logger.debug(f"Configuration updated: {key} = {value}")
                return True
            self._custom_settings[key] = value
            self.logger.debug(f"Custom configuration updated: {key} = {value}")
            return True
        except Exception as e:
            self.logger.error(f"Error setting configuration: {e}")
            return False
    
    def get_app_dir(self) -> Path:
        """Get application directory path"""
        return self.app_dir
    
    def get_temp_dir(self) -> Path:
        """Get temporary directory path"""
        return Path(self._config.temp_dir)
    
    def get_log_dir(self) -> Path:
        """Get log directory path"""
        return self.app_dir / "logs"
    
    def get_plugin_dirs(self) -> List[Path]:
        """Get plugin directory paths"""
        if self._config.plugin_directories is None:
            return []
        return [Path(d) for d in self._config.plugin_directories]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        data = asdict(self._config)
        data.update(self._custom_settings)
        return data
