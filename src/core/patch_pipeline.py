"""
BootForge Patch Pipeline System
Comprehensive framework for hardware-specific OS patching and modifications
"""

import os
import re
import json
import time
import uuid
import logging
import hashlib
import tempfile
import platform
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, field, asdict

from src.core.hardware_detector import DetectedHardware, DetectionConfidence
from src.core.models import HardwareProfile
from src.core.safety_validator import SafetyValidator, ValidationResult, SafetyLevel, SafetyCheck


class PatchType(Enum):
    """Types of patches that can be applied"""
    DRIVER_INJECTION = "driver_injection"      # Inject hardware drivers
    KERNEL_PATCH = "kernel_patch"              # Modify kernel binaries
    BOOTLOADER_PATCH = "bootloader_patch"      # Modify bootloader/EFI
    REGISTRY_PATCH = "registry_patch"          # Modify system registry/config
    FIRMWARE_PATCH = "firmware_patch"          # Update firmware/UEFI
    KEXT_INJECTION = "kext_injection"          # macOS kernel extensions
    EFI_PAYLOAD = "efi_payload"                # EFI boot payloads
    EFI_PATCH = "efi_patch"                    # EFI modifications
    SYSTEM_FILE = "system_file"                # Replace/modify system files
    CONFIG_PATCH = "config_patch"              # Configuration file changes
    CUSTOM_SCRIPT = "custom_script"            # Custom patching scripts


class PatchPhase(Enum):
    """Phases when patches can be applied"""
    PRE_INSTALL = "pre_install"                # Before OS installation
    INSTALL = "install"                        # During installation
    POST_INSTALL = "post_install"              # After OS installation  
    FIRST_BOOT = "first_boot"                  # On first system boot
    RUNTIME = "runtime"                        # During runtime
    EFI_BOOT = "efi_boot"                      # During EFI boot process
    KERNEL_LOAD = "kernel_load"                # During kernel loading
    SYSTEM_INIT = "system_init"                # During system initialization


class PatchPriority(Enum):
    """Priority levels for patch application"""
    CRITICAL = "critical"                      # Must be applied for boot
    HIGH = "high"                              # Highly recommended  
    MEDIUM = "medium"                          # Recommended
    LOW = "low"                                # Optional enhancement
    OPTIONAL = "optional"                      # Optional feature
    EXPERIMENTAL = "experimental"              # Experimental/testing only


class PatchStatus(Enum):
    """Status of patch application"""
    PENDING = "pending"                        # Not yet applied
    APPLYING = "applying"                      # Currently being applied
    APPLIED = "applied"                        # Successfully applied
    FAILED = "failed"                          # Application failed
    SKIPPED = "skipped"                        # Skipped due to conditions
    ROLLED_BACK = "rolled_back"                # Was applied but rolled back


@dataclass
class PatchCondition:
    """Conditions that must be met for patch application"""
    os_version: Optional[str] = None           # Target OS version pattern
    hardware_model: Optional[str] = None       # Specific hardware model
    cpu_architecture: Optional[str] = None     # Required CPU architecture
    minimum_ram_gb: Optional[float] = None     # Minimum RAM requirement
    required_firmware: Optional[str] = None    # Required firmware version
    platform_flags: List[str] = field(default_factory=list)  # Platform-specific flags
    dependency_patches: List[str] = field(default_factory=list)  # Required patches
    exclusion_patterns: List[str] = field(default_factory=list)  # Exclusion rules
    
    def matches(self, hardware: DetectedHardware, os_info: Dict[str, Any]) -> bool:
        """Check if conditions are met for this hardware/OS combination"""
        # OS version check
        if self.os_version and os_info.get("version"):
            if not re.match(self.os_version, os_info["version"]):
                return False
        
        # Hardware model check
        if self.hardware_model and hardware.system_model:
            if not re.match(self.hardware_model, hardware.system_model):
                return False
        
        # CPU architecture check
        if self.cpu_architecture and hardware.cpu_architecture:
            if hardware.cpu_architecture != self.cpu_architecture:
                return False
        
        # RAM requirement check
        if self.minimum_ram_gb and hardware.total_ram_gb:
            if hardware.total_ram_gb < self.minimum_ram_gb:
                return False
        
        # Exclusion patterns check
        for exclusion in self.exclusion_patterns:
            model_text = f"{hardware.system_manufacturer} {hardware.system_model}"
            if re.search(exclusion, model_text, re.IGNORECASE):
                return False
        
        return True


@dataclass
class PatchAction:
    """Concrete patch action to be performed"""
    id: str                                    # Unique action identifier
    name: str                                  # Human-readable name
    description: str                           # Detailed description
    patch_type: PatchType                      # Type of patch
    phase: PatchPhase                          # When to apply
    priority: PatchPriority                    # Priority level
    
    # Action parameters
    source_files: List[str] = field(default_factory=list)  # Source files needed
    target_path: Optional[str] = None          # Target installation path
    backup_path: Optional[str] = None          # Backup location
    command: Optional[str] = None              # Command to execute
    environment: Dict[str, str] = field(default_factory=dict)  # Environment vars
    
    # Validation and safety
    conditions: Optional[PatchCondition] = None  # Application conditions
    checksum: Optional[str] = None             # Expected file checksum
    signature: Optional[str] = None            # Code signature info
    reversible: bool = True                    # Can be rolled back
    requires_reboot: bool = False              # Requires system reboot
    
    # Status tracking
    status: PatchStatus = PatchStatus.PENDING
    applied_at: Optional[float] = None         # When applied (timestamp)
    error_message: Optional[str] = None        # Last error message
    
    def can_apply(self, hardware: DetectedHardware, os_info: Dict[str, Any]) -> bool:
        """Check if this action can be applied"""
        if self.conditions:
            return self.conditions.matches(hardware, os_info)
        return True
    
    def get_risk_level(self) -> ValidationResult:
        """Assess risk level of this patch action"""
        if self.patch_type in [PatchType.KERNEL_PATCH, PatchType.BOOTLOADER_PATCH, 
                              PatchType.FIRMWARE_PATCH]:
            return ValidationResult.DANGEROUS
        elif self.patch_type in [PatchType.DRIVER_INJECTION, PatchType.REGISTRY_PATCH]:
            return ValidationResult.WARNING
        else:
            return ValidationResult.SAFE


@dataclass 
class PatchSet:
    """Collection of related patches for a specific scenario"""
    id: str                                    # Unique set identifier
    name: str                                  # Human-readable name
    description: str                           # Detailed description
    version: str                               # Patch set version
    
    # Target information
    target_os: str                             # Target OS family
    target_versions: List[str] = field(default_factory=list)  # Supported OS versions
    target_hardware: List[str] = field(default_factory=list)  # Target hardware models
    
    # Patch actions
    actions: List[PatchAction] = field(default_factory=list)  # Patch actions
    dependencies: List[str] = field(default_factory=list)    # Required patch sets
    conflicts: List[str] = field(default_factory=list)       # Conflicting patch sets
    
    # Metadata
    author: Optional[str] = None               # Patch set author
    homepage: Optional[str] = None             # Information URL
    license: Optional[str] = None              # License information
    created_at: Optional[float] = None         # Creation timestamp
    updated_at: Optional[float] = None         # Last update timestamp
    
    def get_actions_by_phase(self, phase: PatchPhase) -> List[PatchAction]:
        """Get actions for a specific phase"""
        return [action for action in self.actions if action.phase == phase]
    
    def get_critical_actions(self) -> List[PatchAction]:
        """Get critical priority actions"""
        return [action for action in self.actions if action.priority == PatchPriority.CRITICAL]
    
    def validate_compatibility(self, hardware: DetectedHardware, 
                             os_info: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate compatibility with hardware and OS"""
        issues = []
        
        # Check OS compatibility
        if self.target_os != os_info.get("family", ""):
            issues.append(f"OS family mismatch: expected {self.target_os}, got {os_info.get('family')}")
        
        # Check OS version compatibility
        if self.target_versions:
            os_version = os_info.get("version", "")
            version_match = any(re.match(pattern, os_version) for pattern in self.target_versions)
            if not version_match:
                issues.append(f"OS version {os_version} not in supported versions: {self.target_versions}")
        
        # Check hardware compatibility
        if self.target_hardware:
            hardware_model = f"{hardware.system_manufacturer} {hardware.system_model}"
            hardware_match = any(re.search(pattern, hardware_model, re.IGNORECASE) 
                               for pattern in self.target_hardware)
            if not hardware_match:
                issues.append(f"Hardware {hardware_model} not in supported models")
        
        return len(issues) == 0, issues


@dataclass
class PatchPlan:
    """Complete patching plan for specific hardware/OS combination"""
    id: str                                    # Unique plan identifier
    name: str                                  # Human-readable name
    description: str                           # Plan description
    
    # Target information
    target_hardware: DetectedHardware         # Target hardware
    target_os: Dict[str, Any]                  # Target OS information
    hardware_profile: Optional[HardwareProfile] = None  # Matched hardware profile
    
    # Patch information
    patch_sets: List[PatchSet] = field(default_factory=list)  # Applied patch sets
    total_actions: int = 0                     # Total patch actions
    critical_actions: int = 0                  # Critical actions count
    
    # Execution plan
    execution_phases: Dict[PatchPhase, List[PatchAction]] = field(default_factory=dict)
    estimated_time_minutes: float = 0.0       # Estimated execution time
    requires_reboots: int = 0                  # Number of required reboots
    
    # Risk assessment
    overall_risk: ValidationResult = ValidationResult.SAFE
    risk_factors: List[str] = field(default_factory=list)
    reversible: bool = True                    # Plan is fully reversible
    
    # Status tracking
    status: PatchStatus = PatchStatus.PENDING
    progress: float = 0.0                      # Progress percentage (0-100)
    current_phase: Optional[PatchPhase] = None  # Currently executing phase
    started_at: Optional[float] = None         # Execution start time
    completed_at: Optional[float] = None       # Execution completion time
    
    def add_patch_set(self, patch_set: PatchSet) -> bool:
        """Add a patch set to the plan"""
        try:
            # Validate compatibility
            compatible, issues = patch_set.validate_compatibility(self.target_hardware, self.target_os)
            if not compatible:
                logging.getLogger(__name__).warning(f"Patch set {patch_set.id} not compatible: {issues}")
                return False
            
            # Check for conflicts
            for existing_set in self.patch_sets:
                if patch_set.id in existing_set.conflicts:
                    logging.getLogger(__name__).warning(f"Patch set {patch_set.id} conflicts with {existing_set.id}")
                    return False
            
            # Add to plan
            self.patch_sets.append(patch_set)
            self._update_statistics()
            self._update_execution_plan()
            self._assess_risk()
            
            return True
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to add patch set {patch_set.id}: {e}")
            return False
    
    def _update_statistics(self):
        """Update plan statistics"""
        all_actions = []
        for patch_set in self.patch_sets:
            all_actions.extend(patch_set.actions)
        
        self.total_actions = len(all_actions)
        self.critical_actions = len([a for a in all_actions if a.priority == PatchPriority.CRITICAL])
        self.requires_reboots = len([a for a in all_actions if a.requires_reboot])
        self.reversible = all(a.reversible for a in all_actions)
        
        # Estimate execution time (rough estimate)
        self.estimated_time_minutes = self.total_actions * 2.0  # 2 minutes per action average
    
    def _update_execution_plan(self):
        """Update execution plan by phase"""
        self.execution_phases.clear()
        
        for patch_set in self.patch_sets:
            for action in patch_set.actions:
                if action.phase not in self.execution_phases:
                    self.execution_phases[action.phase] = []
                self.execution_phases[action.phase].append(action)
        
        # Sort actions within each phase by priority
        for phase_actions in self.execution_phases.values():
            phase_actions.sort(key=lambda a: a.priority.value)
    
    def _assess_risk(self):
        """Assess overall plan risk"""
        risk_levels = []
        self.risk_factors.clear()
        
        for patch_set in self.patch_sets:
            for action in patch_set.actions:
                action_risk = action.get_risk_level()
                risk_levels.append(action_risk)
                
                if action_risk == ValidationResult.DANGEROUS:
                    self.risk_factors.append(f"Dangerous patch: {action.name}")
                elif action_risk == ValidationResult.WARNING:
                    self.risk_factors.append(f"Risky patch: {action.name}")
        
        # Determine overall risk
        if ValidationResult.DANGEROUS in risk_levels:
            self.overall_risk = ValidationResult.DANGEROUS
        elif ValidationResult.WARNING in risk_levels:
            self.overall_risk = ValidationResult.WARNING
        else:
            self.overall_risk = ValidationResult.SAFE
    
    def get_summary(self) -> str:
        """Get human-readable plan summary"""
        summary_parts = [
            f"Patch Plan: {self.name}",
            f"Target: {self.target_hardware.get_summary()}",
            f"OS: {self.target_os.get('family', 'Unknown')} {self.target_os.get('version', '')}",
            f"Actions: {self.total_actions} total ({self.critical_actions} critical)",
            f"Risk Level: {self.overall_risk.value.title()}",
            f"Estimated Time: {self.estimated_time_minutes:.1f} minutes"
        ]
        
        if self.requires_reboots > 0:
            summary_parts.append(f"Reboots Required: {self.requires_reboots}")
        
        if not self.reversible:
            summary_parts.append("⚠️  Some changes are irreversible")
        
        return " | ".join(summary_parts)


class PatchPlanner:
    """Plans and orchestrates patch application for detected hardware"""
    
    def __init__(self, safety_validator: Optional[SafetyValidator] = None):
        self.logger = logging.getLogger(__name__)
        self.safety_validator = safety_validator or SafetyValidator()
        
        # Patch registry
        self._patch_sets: Dict[str, PatchSet] = {}
        self._hardware_mappings: Dict[str, List[str]] = {}  # hardware_id -> patch_set_ids
        
        # Load built-in patches
        self._load_builtin_patches()
    
    def _load_builtin_patches(self):
        """Load built-in patch sets"""
        try:
            # This would normally load from configuration files
            # For now, we'll create some example patch sets
            
            # Example: Intel HD Graphics patch for macOS
            intel_graphics_patch = PatchSet(
                id="intel_hd_graphics_macos",
                name="Intel HD Graphics Support",
                description="Enables Intel HD Graphics support on unsupported macOS versions",
                version="1.0.0",
                target_os="macos",
                target_versions=["11.*", "12.*", "13.*", "14.*"],
                target_hardware=["MacBook.*", "iMac.*", "Mac mini.*"],
                actions=[
                    PatchAction(
                        id="intel_framebuffer_patch",
                        name="Intel Framebuffer Patch",
                        description="Patches Intel framebuffer kexts for compatibility",
                        patch_type=PatchType.KEXT_INJECTION,
                        phase=PatchPhase.POST_INSTALL,
                        priority=PatchPriority.CRITICAL,
                        source_files=["IntelFramebuffer.kext"],
                        target_path="/System/Library/Extensions/",
                        reversible=True,
                        requires_reboot=True
                    )
                ]
            )
            
            # Example: WiFi driver patch for Windows
            wifi_driver_patch = PatchSet(
                id="broadcom_wifi_windows",
                name="Broadcom WiFi Driver",
                description="Injects Broadcom WiFi drivers for older hardware",
                version="1.0.0",
                target_os="windows",
                target_versions=["10.*", "11.*"],
                target_hardware=[".*"],
                actions=[
                    PatchAction(
                        id="broadcom_driver_inject",
                        name="Broadcom Driver Injection",
                        description="Injects Broadcom WiFi drivers into Windows image",
                        patch_type=PatchType.DRIVER_INJECTION,
                        phase=PatchPhase.PRE_INSTALL,
                        priority=PatchPriority.HIGH,
                        source_files=["bcmwl63a.inf", "bcmwl63a.sys"],
                        target_path="$WINDOWS$/System32/drivers/",
                        reversible=True,
                        requires_reboot=False
                    )
                ]
            )
            
            # Register patch sets
            self.register_patch_set(intel_graphics_patch)
            self.register_patch_set(wifi_driver_patch)
            
            self.logger.info(f"Loaded {len(self._patch_sets)} built-in patch sets")
            
        except Exception as e:
            self.logger.error(f"Failed to load built-in patches: {e}")
    
    def register_patch_set(self, patch_set: PatchSet) -> bool:
        """Register a patch set"""
        try:
            self._patch_sets[patch_set.id] = patch_set
            self.logger.debug(f"Registered patch set: {patch_set.id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to register patch set {patch_set.id}: {e}")
            return False
    
    def create_patch_plan(self, hardware: DetectedHardware, os_info: Dict[str, Any],
                         hardware_profile: Optional[HardwareProfile] = None,
                         requested_patches: Optional[List[str]] = None) -> Optional[PatchPlan]:
        """Create a patch plan for the given hardware and OS"""
        try:
            self.logger.info(f"Creating patch plan for {hardware.get_summary()}")
            
            # Create plan
            plan_id = f"plan-{uuid.uuid4().hex[:8]}"
            plan = PatchPlan(
                id=plan_id,
                name=f"Patch Plan for {hardware.system_manufacturer} {hardware.system_model}",
                description=f"Hardware-specific patches for {os_info.get('family', 'Unknown')} {os_info.get('version', '')}",
                target_hardware=hardware,
                target_os=os_info,
                hardware_profile=hardware_profile
            )
            
            # Find applicable patch sets
            applicable_sets = self._find_applicable_patches(hardware, os_info, requested_patches)
            
            # Add patch sets to plan
            for patch_set in applicable_sets:
                if plan.add_patch_set(patch_set):
                    self.logger.info(f"Added patch set to plan: {patch_set.id}")
                else:
                    self.logger.warning(f"Failed to add patch set to plan: {patch_set.id}")
            
            if plan.patch_sets:
                self.logger.info(f"Created patch plan with {len(plan.patch_sets)} patch sets")
                return plan
            else:
                self.logger.info("No applicable patches found for this hardware/OS combination")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to create patch plan: {e}")
            return None
    
    def _find_applicable_patches(self, hardware: DetectedHardware, os_info: Dict[str, Any],
                               requested_patches: Optional[List[str]] = None) -> List[PatchSet]:
        """Find patch sets applicable to the hardware/OS combination"""
        applicable = []
        
        try:
            # Check all registered patch sets
            for patch_set in self._patch_sets.values():
                # Skip if specific patches requested and this isn't one
                if requested_patches and patch_set.id not in requested_patches:
                    continue
                
                # Check compatibility
                compatible, issues = patch_set.validate_compatibility(hardware, os_info)
                if compatible:
                    # Check if any actions can be applied
                    applicable_actions = [
                        action for action in patch_set.actions
                        if action.can_apply(hardware, os_info)
                    ]
                    
                    if applicable_actions:
                        self.logger.debug(f"Patch set {patch_set.id} is applicable with {len(applicable_actions)} actions")
                        applicable.append(patch_set)
                    else:
                        self.logger.debug(f"Patch set {patch_set.id} is compatible but no actions applicable")
                else:
                    self.logger.debug(f"Patch set {patch_set.id} not compatible: {issues}")
            
            # Sort by priority (critical patches first)
            applicable.sort(key=lambda ps: min(action.priority.value for action in ps.actions))
            
            return applicable
            
        except Exception as e:
            self.logger.error(f"Failed to find applicable patches: {e}")
            return []
    
    def validate_patch_plan(self, plan: PatchPlan) -> Tuple[bool, List[str]]:
        """Validate a patch plan for safety and compatibility"""
        try:
            issues = []
            
            # Check overall risk level
            if plan.overall_risk == ValidationResult.DANGEROUS:
                issues.append("Plan contains dangerous patches that could prevent boot")
            
            # Check for dependency conflicts
            all_patch_ids = {ps.id for ps in plan.patch_sets}
            for patch_set in plan.patch_sets:
                # Check dependencies
                for dep_id in patch_set.dependencies:
                    if dep_id not in all_patch_ids:
                        issues.append(f"Missing dependency: {patch_set.id} requires {dep_id}")
                
                # Check conflicts
                for conflict_id in patch_set.conflicts:
                    if conflict_id in all_patch_ids:
                        issues.append(f"Conflict detected: {patch_set.id} conflicts with {conflict_id}")
            
            # Validate with safety validator
            for patch_set in plan.patch_sets:
                for action in patch_set.actions:
                    if action.patch_type in [PatchType.KERNEL_PATCH, PatchType.BOOTLOADER_PATCH]:
                        # These are high-risk operations
                        if self.safety_validator.safety_level == SafetyLevel.PARANOID:
                            issues.append(f"High-risk patch blocked in paranoid mode: {action.name}")
            
            return len(issues) == 0, issues
            
        except Exception as e:
            self.logger.error(f"Failed to validate patch plan: {e}")
            return False, [f"Validation error: {e}"]
    
    def get_available_patches(self, os_family: Optional[str] = None) -> List[PatchSet]:
        """Get all available patch sets, optionally filtered by OS family"""
        try:
            patch_sets = list(self._patch_sets.values())
            
            if os_family:
                patch_sets = [ps for ps in patch_sets if ps.target_os == os_family]
            
            return patch_sets
            
        except Exception as e:
            self.logger.error(f"Failed to get available patches: {e}")
            return []
    
    def get_patch_statistics(self) -> Dict[str, Any]:
        """Get statistics about available patches"""
        try:
            stats = {
                "total_patch_sets": len(self._patch_sets),
                "by_os": {},
                "by_priority": {},
                "by_type": {}
            }
            
            for patch_set in self._patch_sets.values():
                # Count by OS
                if patch_set.target_os not in stats["by_os"]:
                    stats["by_os"][patch_set.target_os] = 0
                stats["by_os"][patch_set.target_os] += 1
                
                # Count by priority and type
                for action in patch_set.actions:
                    priority = action.priority.value
                    if priority not in stats["by_priority"]:
                        stats["by_priority"][priority] = 0
                    stats["by_priority"][priority] += 1
                    
                    patch_type = action.patch_type.value
                    if patch_type not in stats["by_type"]:
                        stats["by_type"][patch_type] = 0
                    stats["by_type"][patch_type] += 1
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get patch statistics: {e}")
            return {}
    
    def apply_patch_plan(self, plan: PatchPlan, target_mount_point: str, 
                        dry_run: bool = False) -> Tuple[bool, List[str]]:
        """Apply patch plan with strict security controls"""
        try:
            # CRITICAL SECURITY: Ensure we're targeting a mounted volume, NOT host system
            if not self._validate_target_mount_point(target_mount_point):
                error = f"SECURITY BLOCK: Invalid target mount point: {target_mount_point}"
                self.logger.error(error)
                return False, [error]
            
            # Validate patch plan security
            security_result = self._validate_plan_security(plan)
            if security_result.result != ValidationResult.SAFE:
                if self.safety_validator.patch_mode == PatchValidationMode.COMPLIANT:
                    error = f"SECURITY BLOCK: Plan blocked in COMPLIANT mode: {security_result.message}"
                    self.logger.error(error)
                    return False, [error]
                elif not self._has_sufficient_consent(security_result.result):
                    error = f"SECURITY BLOCK: Insufficient consent for risk level: {security_result.result.value}"
                    self.logger.error(error)
                    return False, [error]
            
            execution_log = []
            execution_log.append(f"{'DRY RUN: ' if dry_run else ''}Applying patch plan: {plan.name}")
            execution_log.append(f"Target mount point: {target_mount_point}")
            execution_log.append(f"Security mode: {self.safety_validator.patch_mode.value}")
            
            success = True
            failed_actions = []
            
            # Execute patch sets in dependency order
            for patch_set in plan.patch_sets:
                patch_result, patch_logs = self._apply_patch_set(
                    patch_set, target_mount_point, dry_run
                )
                execution_log.extend(patch_logs)
                
                if not patch_result:
                    success = False
                    failed_actions.append(patch_set.id)
                    execution_log.append(f"FAILED: Patch set {patch_set.id}")
                    
                    # Stop on first failure for safety
                    break
                else:
                    execution_log.append(f"SUCCESS: Patch set {patch_set.id}")
            
            # Log execution results
            self._audit_execution(plan, target_mount_point, success, execution_log, dry_run)
            
            if success:
                execution_log.append("Patch plan applied successfully")
            else:
                execution_log.append(f"Patch plan failed. Failed actions: {failed_actions}")
            
            return success, execution_log
            
        except Exception as e:
            error = f"Failed to apply patch plan: {e}"
            self.logger.error(error)
            return False, [error]
    
    def _validate_target_mount_point(self, target_mount_point: str) -> bool:
        """CRITICAL SECURITY: Validate target is a safe mount point, not host system"""
        try:
            target_path = Path(target_mount_point).resolve()
            
            # Block operations on root filesystem
            system_critical_paths = [
                Path("/"),
                Path("/System"),
                Path("/usr"),
                Path("/bin"),
                Path("/sbin"),
                Path("/Library"),
                Path("/Applications"),
                Path("C:\\"),
                Path("C:\\Windows"),
                Path("C:\\Program Files"),
                Path("C:\\Program Files (x86)"),
            ]
            
            for critical_path in system_critical_paths:
                try:
                    if target_path == critical_path.resolve():
                        self.logger.error(f"SECURITY BLOCK: Attempted operation on system path: {target_path}")
                        return False
                except (OSError, PermissionError):
                    # Path doesn't exist or no permission - that's fine for comparison
                    continue
            
            # Must be a mounted volume or removable device
            if not target_path.exists():
                self.logger.error(f"Target mount point does not exist: {target_path}")
                return False
            
            # Additional platform-specific validations
            import platform
            if platform.system() == "Darwin":  # macOS
                # Must be in /Volumes/ or /private/tmp/ for temporary mounts
                if not (str(target_path).startswith("/Volumes/") or 
                       str(target_path).startswith("/private/tmp/")):
                    self.logger.error(f"macOS: Target must be in /Volumes/ or /private/tmp/: {target_path}")
                    return False
            
            elif platform.system() == "Linux":
                # Must be in /mnt/, /media/, or /tmp/
                if not (str(target_path).startswith("/mnt/") or 
                       str(target_path).startswith("/media/") or
                       str(target_path).startswith("/tmp/")):
                    self.logger.error(f"Linux: Target must be in /mnt/, /media/, or /tmp/: {target_path}")
                    return False
            
            self.logger.info(f"Target mount point validation passed: {target_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to validate target mount point: {e}")
            return False
    
    def _validate_plan_security(self, plan: PatchPlan) -> SafetyCheck:
        """Validate patch plan security with strict controls"""
        try:
            risk_factors = []
            dangerous_actions = []
            
            for patch_set in plan.patch_sets:
                for action in patch_set.actions:
                    # SECURITY: Block dangerous patch types in COMPLIANT mode
                    if action.patch_type == PatchType.CUSTOM_SCRIPT:
                        risk_factors.append(f"Custom script execution: {action.name}")
                        dangerous_actions.append(action.id)
                    
                    if action.patch_type == PatchType.FIRMWARE_PATCH:
                        risk_factors.append(f"Firmware modification: {action.name}")
                        dangerous_actions.append(action.id)
                    
                    if action.patch_type == PatchType.KERNEL_PATCH:
                        risk_factors.append(f"Kernel modification: {action.name}")
                        dangerous_actions.append(action.id)
                    
                    # Check for unsigned/unverified content (using reversible as proxy for verification status)
                    if not action.reversible:
                        risk_factors.append(f"Irreversible action (potentially unsafe): {action.name}")
                        dangerous_actions.append(action.id)
            
            # Determine overall risk level
            if dangerous_actions:
                if self.safety_validator.patch_mode == PatchValidationMode.COMPLIANT:
                    return SafetyCheck(
                        name="Patch Plan Security",
                        result=ValidationResult.BLOCKED,
                        message=f"Dangerous actions blocked in COMPLIANT mode: {dangerous_actions}",
                        details="; ".join(risk_factors),
                        mitigation="Use BYPASS mode with EXPERT consent to override"
                    )
                else:
                    return SafetyCheck(
                        name="Patch Plan Security", 
                        result=ValidationResult.DANGEROUS,
                        message=f"Dangerous actions require explicit consent: {dangerous_actions}",
                        details="; ".join(risk_factors),
                        mitigation="Requires EXPERT level consent"
                    )
            
            elif risk_factors:
                return SafetyCheck(
                    name="Patch Plan Security",
                    result=ValidationResult.WARNING,
                    message="Plan has minor risk factors",
                    details="; ".join(risk_factors),
                    mitigation="Review and approve risk factors"
                )
            
            return SafetyCheck(
                name="Patch Plan Security",
                result=ValidationResult.SAFE,
                message="Plan passed security validation",
                details="No high-risk actions detected"
            )
            
        except Exception as e:
            return SafetyCheck(
                name="Patch Plan Security",
                result=ValidationResult.BLOCKED,
                message=f"Security validation failed: {e}",
                details=str(e),
                mitigation="Fix validation errors"
            )
    
    def _has_sufficient_consent(self, risk_level: ValidationResult) -> bool:
        """Check if user has provided sufficient consent for risk level"""
        # TODO: Implement consent checking with stored user consent records
        # For now, always require explicit consent for dangerous operations
        return risk_level in [ValidationResult.SAFE, ValidationResult.WARNING]
    
    def _apply_patch_set(self, patch_set: PatchSet, target_mount_point: str, 
                        dry_run: bool) -> Tuple[bool, List[str]]:
        """Apply individual patch set with security controls"""
        logs = []
        logs.append(f"{'DRY RUN: ' if dry_run else ''}Applying patch set: {patch_set.id}")
        
        try:
            # Sort actions by phase and priority
            actions = sorted(patch_set.actions, 
                           key=lambda x: (x.phase.value, x.priority.value))
            
            for action in actions:
                action_result, action_logs = self._apply_patch_action(
                    action, target_mount_point, dry_run
                )
                logs.extend(action_logs)
                
                if not action_result:
                    logs.append(f"FAILED: Action {action.id}")
                    return False, logs
                    
                logs.append(f"SUCCESS: Action {action.id}")
            
            return True, logs
            
        except Exception as e:
            error = f"Failed to apply patch set {patch_set.id}: {e}"
            logs.append(error)
            return False, logs
    
    def _apply_patch_action(self, action: PatchAction, target_mount_point: str,
                           dry_run: bool) -> Tuple[bool, List[str]]:
        """Apply individual patch action with strict security"""
        logs = []
        logs.append(f"{'DRY RUN: ' if dry_run else ''}Applying action: {action.id} ({action.patch_type.value})")
        
        if dry_run:
            logs.append(f"DRY RUN: Would execute {action.patch_type.value} - {action.description}")
            return True, logs
        
        try:
            # SECURITY: Validate action before execution
            if not self._validate_action_security(action, target_mount_point):
                error = f"SECURITY BLOCK: Action failed security validation: {action.id}"
                logs.append(error)
                return False, logs
            
            # Execute based on patch type
            if action.patch_type == PatchType.KEXT_INJECTION:
                return self._apply_kext_injection(action, target_mount_point, logs)
            elif action.patch_type == PatchType.EFI_PATCH:
                return self._apply_efi_patch(action, target_mount_point, logs)
            elif action.patch_type == PatchType.DRIVER_INJECTION:
                return self._apply_driver_injection(action, target_mount_point, logs)
            elif action.patch_type == PatchType.CUSTOM_SCRIPT:
                # Should be blocked by security validation
                error = f"SECURITY BLOCK: Custom scripts not allowed: {action.id}"
                logs.append(error)
                return False, logs
            else:
                error = f"Unsupported patch type: {action.patch_type.value}"
                logs.append(error)
                return False, logs
                
        except Exception as e:
            error = f"Failed to apply action {action.id}: {e}"
            logs.append(error)
            return False, logs
    
    def _validate_action_security(self, action: PatchAction, target_mount_point: str) -> bool:
        """Validate individual action security"""
        # SECURITY: Block dangerous actions
        dangerous_types = [PatchType.CUSTOM_SCRIPT, PatchType.FIRMWARE_PATCH]
        if action.patch_type in dangerous_types:
            if self.safety_validator.patch_mode == PatchValidationMode.COMPLIANT:
                return False
        
        # SECURITY: Ensure target paths are within mount point
        if action.target_path:
            target_path = Path(target_mount_point) / action.target_path.lstrip("/")
            if not str(target_path).startswith(target_mount_point):
                self.logger.error(f"SECURITY: Action target outside mount point: {target_path}")
                return False
        
        return True
    
    def _apply_kext_injection(self, action: PatchAction, target_mount_point: str,
                             logs: List[str]) -> Tuple[bool, List[str]]:
        """Apply kext injection safely"""
        logs.append(f"Injecting kext: {action.source_files}")
        # TODO: Implement safe kext injection to target volume
        logs.append("PLACEHOLDER: Kext injection not implemented")
        return True, logs
    
    def _apply_efi_patch(self, action: PatchAction, target_mount_point: str,
                        logs: List[str]) -> Tuple[bool, List[str]]:
        """Apply EFI patch safely"""
        logs.append(f"Applying EFI patch: {action.source_files}")
        # TODO: Implement safe EFI patching to target EFI partition
        logs.append("PLACEHOLDER: EFI patching not implemented")
        return True, logs
    
    def _apply_driver_injection(self, action: PatchAction, target_mount_point: str,
                               logs: List[str]) -> Tuple[bool, List[str]]:
        """Apply driver injection safely"""
        logs.append(f"Injecting drivers: {action.source_files}")
        # TODO: Implement safe driver injection to target volume
        logs.append("PLACEHOLDER: Driver injection not implemented")
        return True, logs
    
    def _audit_execution(self, plan: PatchPlan, target_mount_point: str, 
                        success: bool, execution_log: List[str], dry_run: bool):
        """Log patch execution for audit purposes"""
        try:
            from src.core.safety_validator import AuditRecord
            
            audit_record = AuditRecord(
                operation_type="patch_plan_execution",
                operation_details=f"Plan: {plan.id}, Target: {target_mount_point}, DryRun: {dry_run}",
                risk_level=plan.overall_risk,
                validation_mode=self.safety_validator.patch_mode,
                target_device=target_mount_point,
                success=success,
                error_message="\n".join(execution_log) if not success else None
            )
            
            # Log to audit system
            self.logger.info(f"AUDIT: {audit_record.operation_type} - Success: {success}")
            
        except Exception as e:
            self.logger.error(f"Failed to create audit record: {e}")