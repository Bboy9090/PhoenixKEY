"""
BootForge Plugin Manager
Manages loading, execution, and configuration of plugins
"""

import os
import logging
import importlib.util
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Any, Type
from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.core.config import Config


@dataclass
class PluginInfo:
    """Plugin information"""
    name: str
    version: str
    description: str
    author: str
    dependencies: List[str]
    enabled: bool
    path: str


class PluginBase(ABC):
    """Base class for all BootForge plugins"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.name = self.__class__.__name__
        self.version = "1.0.0"
        self.description = "BootForge Plugin"
        self.author = "Unknown"
        self.dependencies = []
        self.enabled = True
        
    @abstractmethod
    def initialize(self, config: Config) -> bool:
        """Initialize the plugin"""
        pass
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """Execute plugin functionality"""
        pass
    
    @abstractmethod
    def cleanup(self) -> bool:
        """Cleanup plugin resources"""
        pass
    
    def get_info(self) -> PluginInfo:
        """Get plugin information"""
        return PluginInfo(
            name=self.name,
            version=self.version,
            description=self.description,
            author=self.author,
            dependencies=self.dependencies,
            enabled=self.enabled,
            path=""
        )


class PluginManager:
    """Plugin manager for BootForge"""
    
    def __init__(self, config: Config):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.plugins: Dict[str, PluginBase] = {}
        self.plugin_info: Dict[str, PluginInfo] = {}
        
        # Plugin directories
        self.plugin_directories = [
            Path(__file__).parent,  # Built-in plugins
            *config.get_plugin_dirs()  # User plugin directories
        ]
        
        self.logger.info("Plugin manager initialized")
    
    def discover_plugins(self) -> List[PluginInfo]:
        """Discover available plugins"""
        discovered = []
        
        for plugin_dir in self.plugin_directories:
            if not plugin_dir.exists():
                continue
                
            self.logger.info(f"Scanning plugin directory: {plugin_dir}")
            
            for plugin_file in plugin_dir.glob("*.py"):
                if plugin_file.name.startswith("_"):
                    continue
                    
                try:
                    plugin_info = self._load_plugin_info(plugin_file)
                    if plugin_info:
                        discovered.append(plugin_info)
                        self.plugin_info[plugin_info.name] = plugin_info
                        
                except Exception as e:
                    self.logger.error(f"Error discovering plugin {plugin_file}: {e}")
        
        self.logger.info(f"Discovered {len(discovered)} plugins")
        return discovered
    
    def _load_plugin_info(self, plugin_file: Path) -> Optional[PluginInfo]:
        """Load plugin information without importing"""
        try:
            spec = importlib.util.spec_from_file_location("temp_plugin", plugin_file)
            if not spec or not spec.loader:
                return None
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find plugin class
            plugin_class = None
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, PluginBase) and 
                    obj != PluginBase):
                    plugin_class = obj
                    break
            
            if not plugin_class:
                return None
                
            # Create temporary instance to get info
            temp_instance = plugin_class()
            info = temp_instance.get_info()
            info.path = str(plugin_file)
            
            return info
            
        except Exception as e:
            self.logger.error(f"Error loading plugin info from {plugin_file}: {e}")
            return None
    
    def load_plugin(self, plugin_name: str) -> bool:
        """Load a specific plugin"""
        if plugin_name in self.plugins:
            self.logger.warning(f"Plugin {plugin_name} is already loaded")
            return True
            
        plugin_info = self.plugin_info.get(plugin_name)
        if not plugin_info:
            self.logger.error(f"Plugin {plugin_name} not found")
            return False
        
        try:
            # Check dependencies
            if not self._check_dependencies(plugin_info):
                self.logger.error(f"Dependencies not met for plugin {plugin_name}")
                return False
            
            # Load plugin module
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_info.path)
            if not spec or not spec.loader:
                return False
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find and instantiate plugin class
            plugin_class = None
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, PluginBase) and 
                    obj != PluginBase):
                    plugin_class = obj
                    break
            
            if not plugin_class:
                self.logger.error(f"No valid plugin class found in {plugin_info.path}")
                return False
            
            # Create and initialize plugin
            plugin_instance = plugin_class()
            if plugin_instance.initialize(self.config):
                self.plugins[plugin_name] = plugin_instance
                self.logger.info(f"Plugin {plugin_name} loaded successfully")
                return True
            else:
                self.logger.error(f"Plugin {plugin_name} initialization failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Error loading plugin {plugin_name}: {e}")
            return False
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin"""
        if plugin_name not in self.plugins:
            self.logger.warning(f"Plugin {plugin_name} is not loaded")
            return True
        
        try:
            plugin = self.plugins[plugin_name]
            if plugin.cleanup():
                del self.plugins[plugin_name]
                self.logger.info(f"Plugin {plugin_name} unloaded successfully")
                return True
            else:
                self.logger.error(f"Plugin {plugin_name} cleanup failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Error unloading plugin {plugin_name}: {e}")
            return False
    
    def load_all_plugins(self) -> bool:
        """Load all discovered plugins"""
        self.discover_plugins()
        
        success_count = 0
        for plugin_name, plugin_info in self.plugin_info.items():
            if plugin_info.enabled and self.load_plugin(plugin_name):
                success_count += 1
        
        self.logger.info(f"Loaded {success_count}/{len(self.plugin_info)} plugins")
        return success_count > 0
    
    def execute_plugin(self, plugin_name: str, *args, **kwargs) -> Any:
        """Execute a plugin"""
        if plugin_name not in self.plugins:
            self.logger.error(f"Plugin {plugin_name} is not loaded")
            return None
        
        try:
            return self.plugins[plugin_name].execute(*args, **kwargs)
        except Exception as e:
            self.logger.error(f"Error executing plugin {plugin_name}: {e}")
            return None
    
    def get_loaded_plugins(self) -> List[str]:
        """Get list of loaded plugin names"""
        return list(self.plugins.keys())
    
    def get_plugin_info_list(self) -> List[PluginInfo]:
        """Get list of all plugin information"""
        return list(self.plugin_info.values())
    
    def _check_dependencies(self, plugin_info: PluginInfo) -> bool:
        """Check if plugin dependencies are met"""
        for dependency in plugin_info.dependencies:
            if dependency not in self.plugins:
                return False
        return True
    
    def cleanup_all(self) -> bool:
        """Cleanup all loaded plugins"""
        success = True
        for plugin_name in list(self.plugins.keys()):
            if not self.unload_plugin(plugin_name):
                success = False
        return success