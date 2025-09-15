"""
BootForge Patch Configuration Loader
Loads and parses YAML patch configurations into PatchSet objects
for the patch pipeline system.
"""

import yaml
import os
import re
import logging
from typing import List, Dict, Optional, Any, Set
from pathlib import Path
from dataclasses import dataclass

from .patch_pipeline import (
    PatchSet, PatchAction, PatchType, PatchPhase, PatchPriority,
    PatchCondition, PatchStatus
)
from .vendor_database import PatchCapability, SecurityLevel


@dataclass
class PatchConfigMetadata:
    """Metadata from patch configuration files"""
    name: str
    version: str
    description: str
    author: str
    created: str
    compatibility_version: str


@dataclass 
class PatchDependency:
    """Represents a patch dependency"""
    name: str
    version: str
    source: str
    description: str
    required_for: List[str]


class PatchConfigLoader:
    """Loads and validates patch configurations from YAML files"""
    
    def __init__(self, config_dir: str = "configs/patches"):
        self.config_dir = Path(config_dir)
        self.logger = logging.getLogger(__name__)
        self._loaded_configs: Dict[str, Dict[str, Any]] = {}
        self._metadata_cache: Dict[str, PatchConfigMetadata] = {}
        
    def load_all_configs(self) -> List[PatchSet]:
        """Load all patch configurations from the config directory"""
        patch_sets = []
        
        if not self.config_dir.exists():
            self.logger.warning(f"Patch config directory not found: {self.config_dir}")
            return patch_sets
        
        for yaml_file in self.config_dir.glob("*.yaml"):
            try:
                config_patch_sets = self.load_config_file(yaml_file)
                patch_sets.extend(config_patch_sets)
                self.logger.debug(f"Loaded {len(config_patch_sets)} patch sets from {yaml_file.name}")
            except Exception as e:
                self.logger.error(f"Failed to load patch config {yaml_file}: {e}")
        
        self.logger.info(f"Loaded {len(patch_sets)} total patch sets from {len(list(self.config_dir.glob('*.yaml')))} config files")
        return patch_sets
    
    def load_config_file(self, file_path: Path) -> List[PatchSet]:
        """Load patch sets from a single YAML configuration file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Cache the config
            self._loaded_configs[str(file_path)] = config
            
            # Validate configuration structure
            self._validate_config_structure(config, file_path)
            
            # Parse metadata
            metadata = self._parse_metadata(config.get('metadata', {}))
            self._metadata_cache[str(file_path)] = metadata
            
            # Convert patch sets to PatchSet objects
            patch_sets = []
            patch_sets_config = config.get('patch_sets', {})
            
            for set_id, set_config in patch_sets_config.items():
                patch_set = self._create_patch_set(set_id, set_config, metadata, config)
                if patch_set:
                    patch_sets.append(patch_set)
            
            return patch_sets
            
        except Exception as e:
            self.logger.error(f"Failed to load config file {file_path}: {e}")
            raise
    
    def _validate_config_structure(self, config: Dict[str, Any], file_path: Path):
        """Validate the basic structure of a patch configuration"""
        required_sections = ['metadata', 'patch_sets']
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required section '{section}' in {file_path}")
        
        # Validate metadata
        metadata = config['metadata']
        required_metadata = ['name', 'version', 'description', 'author']
        for field in required_metadata:
            if field not in metadata:
                raise ValueError(f"Missing required metadata field '{field}' in {file_path}")
        
        # Validate patch sets
        patch_sets = config['patch_sets']
        if not isinstance(patch_sets, dict) or not patch_sets:
            raise ValueError(f"patch_sets must be a non-empty dictionary in {file_path}")
    
    def _parse_metadata(self, metadata_config: Dict[str, Any]) -> PatchConfigMetadata:
        """Parse metadata section from configuration"""
        return PatchConfigMetadata(
            name=metadata_config.get('name', 'Unknown'),
            version=metadata_config.get('version', '1.0.0'),
            description=metadata_config.get('description', ''),
            author=metadata_config.get('author', 'Unknown'),
            created=metadata_config.get('created', ''),
            compatibility_version=metadata_config.get('compatibility_version', '1.0')
        )
    
    def _create_patch_set(self, set_id: str, set_config: Dict[str, Any], 
                         metadata: PatchConfigMetadata, 
                         full_config: Dict[str, Any]) -> Optional[PatchSet]:
        """Create a PatchSet object from configuration"""
        try:
            # Extract basic information
            patch_set_id = set_config.get('id', set_id)
            name = set_config.get('name', set_id.replace('_', ' ').title())
            description = set_config.get('description', '')
            
            # Parse target information
            target_hardware = self._parse_target_hardware(set_config.get('target_hardware', {}))
            target_os = set_config.get('target_os', {})
            target_versions = target_os.get('versions', [])
            
            # Create patch actions
            actions = self._create_patch_actions(set_config.get('actions', {}), set_id)
            
            patch_set = PatchSet(
                id=patch_set_id,
                name=name,
                description=description,
                version=metadata.version,
                target_os=target_os.get('family', 'unknown'),
                target_versions=target_versions,
                target_hardware=target_hardware,
                actions=actions,
                author=metadata.author,
                created_at=1234567890.0  # Placeholder - could parse from metadata.created
            )
            
            return patch_set
            
        except Exception as e:
            self.logger.error(f"Failed to create patch set {set_id}: {e}")
            return None
    
    def _parse_target_hardware(self, hardware_config: Dict[str, Any]) -> List[str]:
        """Parse target hardware patterns from configuration"""
        patterns = []
        
        # Add explicit patterns
        explicit_patterns = hardware_config.get('patterns', [])
        patterns.extend(explicit_patterns)
        
        # Convert CPU families to patterns (simplified)
        cpu_families = hardware_config.get('cpu_families', [])
        for cpu_family in cpu_families:
            # Create regex pattern from CPU family description
            pattern = cpu_family.replace(' ', '.*').replace('(', r'\(').replace(')', r'\)')
            patterns.append(pattern)
        
        return patterns
    
    def _create_patch_actions(self, actions_config: Dict[str, Any], set_id: str) -> List[PatchAction]:
        """Create PatchAction objects from actions configuration"""
        actions = []
        
        for category, category_actions in actions_config.items():
            if not isinstance(category_actions, list):
                continue
                
            for action_config in category_actions:
                action = self._create_single_patch_action(action_config, category, set_id)
                if action:
                    actions.append(action)
        
        return actions
    
    def _create_single_patch_action(self, action_config: Dict[str, Any], 
                                   category: str, set_id: str) -> Optional[PatchAction]:
        """Create a single PatchAction from configuration"""
        try:
            # Basic information
            action_id = action_config.get('id', f"{set_id}_{category}_action")
            name = action_config.get('name', action_id.replace('_', ' ').title())
            description = action_config.get('description', '')
            
            # Determine patch type
            patch_type = self._parse_patch_type(action_config.get('type', 'kext_injection'))
            
            # Determine phase and priority
            phase = self._parse_patch_phase(action_config.get('phase', 'post_install'))
            priority = self._parse_patch_priority(action_config.get('priority', 'medium'))
            
            # Parse files and paths
            source_files = self._parse_source_files(action_config.get('files', []))
            target_path = action_config.get('target_path', '')
            
            # Parse conditions
            conditions = self._parse_conditions(action_config.get('conditions', {}))
            
            # Parse command if present
            command = action_config.get('command', '')
            
            # Other properties
            reversible = action_config.get('reversible', True)
            requires_reboot = action_config.get('requires_reboot', False)
            backup_path = action_config.get('backup_path', None)
            
            action = PatchAction(
                id=action_id,
                name=name,
                description=description,
                patch_type=patch_type,
                phase=phase,
                priority=priority,
                source_files=source_files,
                target_path=target_path,
                command=command,
                reversible=reversible,
                requires_reboot=requires_reboot,
                backup_path=backup_path,
                conditions=conditions
            )
            
            return action
            
        except Exception as e:
            self.logger.error(f"Failed to create patch action from config: {e}")
            return None
    
    def _parse_patch_type(self, type_str: str) -> PatchType:
        """Parse patch type from string"""
        type_mapping = {
            'kext_injection': PatchType.KEXT_INJECTION,
            'kernel_patch': PatchType.KERNEL_PATCH,
            'driver_injection': PatchType.DRIVER_INJECTION,
            'registry_patch': PatchType.REGISTRY_PATCH,
            'config_patch': PatchType.CONFIG_PATCH,
            'system_file': PatchType.SYSTEM_FILE,
            'efi_patch': PatchType.EFI_PATCH
        }
        return type_mapping.get(type_str.lower(), PatchType.SYSTEM_FILE)
    
    def _parse_patch_phase(self, phase_str: str) -> PatchPhase:
        """Parse patch phase from string"""
        phase_mapping = {
            'pre_install': PatchPhase.PRE_INSTALL,
            'install': PatchPhase.INSTALL,
            'post_install': PatchPhase.POST_INSTALL,
            'first_boot': PatchPhase.FIRST_BOOT,
            'runtime': PatchPhase.RUNTIME
        }
        return phase_mapping.get(phase_str.lower(), PatchPhase.POST_INSTALL)
    
    def _parse_patch_priority(self, priority_str: str) -> PatchPriority:
        """Parse patch priority from string"""
        priority_mapping = {
            'critical': PatchPriority.CRITICAL,
            'high': PatchPriority.HIGH,
            'medium': PatchPriority.MEDIUM,
            'low': PatchPriority.LOW,
            'optional': PatchPriority.OPTIONAL
        }
        return priority_mapping.get(priority_str.lower(), PatchPriority.MEDIUM)
    
    def _parse_source_files(self, files_config: List[Dict[str, Any]]) -> List[str]:
        """Parse source files from configuration"""
        source_files = []
        
        for file_config in files_config:
            if isinstance(file_config, str):
                source_files.append(file_config)
            elif isinstance(file_config, dict):
                source = file_config.get('source', '')
                if source:
                    source_files.append(source)
        
        return source_files
    
    def _parse_conditions(self, conditions_config: Dict[str, Any]) -> Optional[PatchCondition]:
        """Parse patch conditions from configuration"""
        if not conditions_config:
            return None
        
        return PatchCondition(
            os_version=conditions_config.get('os_version'),
            hardware_model=conditions_config.get('hardware_model'),
            cpu_architecture=conditions_config.get('architecture'),
            required_firmware=conditions_config.get('required_firmware'),
            minimum_ram_gb=conditions_config.get('min_ram_gb'),
            platform_flags=conditions_config.get('required_features', [])
        )
    
    def get_patch_sets_for_hardware(self, hardware_model: str, 
                                   os_family: str = None) -> List[PatchSet]:
        """Get applicable patch sets for specific hardware"""
        applicable_sets = []
        
        # Load all configs if not already loaded
        if not self._loaded_configs:
            self.load_all_configs()
        
        for config_file, config in self._loaded_configs.items():
            patch_sets = config.get('patch_sets', {})
            
            for set_id, set_config in patch_sets.items():
                if self._is_hardware_compatible(hardware_model, set_config, os_family):
                    patch_set = self._create_patch_set(
                        set_id, set_config, 
                        self._metadata_cache[config_file],
                        config
                    )
                    if patch_set:
                        applicable_sets.append(patch_set)
        
        return applicable_sets
    
    def _is_hardware_compatible(self, hardware_model: str, 
                               set_config: Dict[str, Any],
                               os_family: str = None) -> bool:
        """Check if hardware is compatible with patch set"""
        target_hardware = set_config.get('target_hardware', {})
        patterns = target_hardware.get('patterns', [])
        
        # Check hardware patterns
        for pattern in patterns:
            try:
                if re.match(pattern, hardware_model):
                    # Check OS family if specified
                    if os_family:
                        target_os = set_config.get('target_os', {})
                        if target_os.get('family') and target_os['family'] != os_family:
                            continue
                    return True
            except re.error:
                self.logger.warning(f"Invalid regex pattern: {pattern}")
                continue
        
        return False
    
    def validate_patch_config(self, config_path: Path) -> Dict[str, Any]:
        """Validate a patch configuration and return validation results"""
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'patch_count': 0,
            'security_level': 'unknown'
        }
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Structural validation
            try:
                self._validate_config_structure(config, config_path)
            except ValueError as e:
                results['errors'].append(str(e))
                results['valid'] = False
                return results
            
            # Count patches and assess security level
            patch_sets = config.get('patch_sets', {})
            total_patches = 0
            high_security_patches = 0
            
            for set_config in patch_sets.values():
                actions = set_config.get('actions', {})
                for category_actions in actions.values():
                    if isinstance(category_actions, list):
                        total_patches += len(category_actions)
                        
                        # Check for high-security patches
                        for action in category_actions:
                            if action.get('security_impact') == 'high':
                                high_security_patches += 1
            
            results['patch_count'] = total_patches
            
            # Determine overall security level
            if high_security_patches > 0:
                results['security_level'] = 'high'
            elif total_patches > 0:
                results['security_level'] = 'medium'
            else:
                results['security_level'] = 'low'
            
            # Additional warnings
            if high_security_patches > 0:
                results['warnings'].append(
                    f"Configuration contains {high_security_patches} high-security patches"
                )
            
            # Check for experimental patches
            experimental_count = 0
            for set_config in patch_sets.values():
                actions = set_config.get('actions', {})
                for category_actions in actions.values():
                    if isinstance(category_actions, list):
                        for action in category_actions:
                            if action.get('experimental', False):
                                experimental_count += 1
            
            if experimental_count > 0:
                results['warnings'].append(
                    f"Configuration contains {experimental_count} experimental patches"
                )
            
        except Exception as e:
            results['errors'].append(f"Failed to validate config: {e}")
            results['valid'] = False
        
        return results
    
    def get_available_configurations(self) -> List[Dict[str, Any]]:
        """Get list of available patch configurations with metadata"""
        configurations = []
        
        if not self.config_dir.exists():
            return configurations
        
        for yaml_file in self.config_dir.glob("*.yaml"):
            try:
                validation = self.validate_patch_config(yaml_file)
                
                # Get basic metadata
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                metadata = config.get('metadata', {})
                
                config_info = {
                    'file_path': str(yaml_file),
                    'name': metadata.get('name', yaml_file.stem),
                    'version': metadata.get('version', 'unknown'),
                    'description': metadata.get('description', ''),
                    'author': metadata.get('author', 'unknown'),
                    'patch_count': validation['patch_count'],
                    'security_level': validation['security_level'],
                    'valid': validation['valid'],
                    'errors': validation['errors'],
                    'warnings': validation['warnings']
                }
                
                configurations.append(config_info)
                
            except Exception as e:
                self.logger.error(f"Failed to process config {yaml_file}: {e}")
                configurations.append({
                    'file_path': str(yaml_file),
                    'name': yaml_file.stem,
                    'valid': False,
                    'errors': [str(e)]
                })
        
        return configurations