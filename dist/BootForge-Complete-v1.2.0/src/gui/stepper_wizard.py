"""
BootForge Stepper Wizard System
Professional guided workflow implementation with finite state machine
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Any, Optional, Tuple, List, Callable
from pathlib import Path
import json
from datetime import datetime

from PyQt6.QtCore import QObject, pyqtSignal

from src.core.config import Config
from src.core.hardware_detector import DetectedHardware, HardwareDetector
from src.core.hardware_matcher import HardwareMatcher, ProfileMatch
from src.core.usb_builder import (
    DeploymentRecipe, HardwareProfile, StorageBuilderEngine, 
    BuildProgress
)
from src.core.disk_manager import DiskInfo
from src.core.safety_validator import SafetyValidator, SafetyLevel, ValidationResult


class WizardStep(Enum):
    """Enumeration of wizard steps in the deployment workflow"""
    DETECT_HARDWARE = auto()
    SELECT_OS_IMAGE = auto() 
    CONFIGURE_USB = auto()
    SAFETY_REVIEW = auto()
    BUILD_VERIFY = auto()
    SUMMARY = auto()


@dataclass
class OSImageInfo:
    """Information about selected OS image and verification status"""
    image_path: Optional[str] = None
    image_name: Optional[str] = None
    image_size_mb: Optional[int] = None
    os_type: Optional[str] = None  # "macos", "windows", "linux", "custom"
    os_version: Optional[str] = None
    verification_status: str = "pending"  # "pending", "verified", "failed", "skipped"
    verification_hash: Optional[str] = None
    verification_errors: List[str] = field(default_factory=list)
    
    def is_valid(self) -> bool:
        """Check if OS image selection is valid - SECURITY: Only verified images allowed"""
        return (self.image_path is not None and 
                Path(self.image_path).exists() and
                self.verification_status == "verified")


@dataclass 
class RecipeConfiguration:
    """Configuration for the selected deployment recipe"""
    selected_recipe: Optional[DeploymentRecipe] = None
    matched_hardware_profile: Optional[HardwareProfile] = None
    profile_match_confidence: float = 0.0
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    required_files: Dict[str, str] = field(default_factory=dict)  # filename -> filepath
    optional_files: Dict[str, str] = field(default_factory=dict)
    
    def is_valid(self) -> bool:
        """Check if recipe configuration is valid"""
        if not self.selected_recipe:
            return False
        
        # Check all required files are present
        for required_file in self.selected_recipe.required_files:
            if required_file not in self.required_files:
                return False
            file_path = self.required_files[required_file]
            if not Path(file_path).exists():
                return False
        
        return True


@dataclass
class UserConfirmations:
    """Safety confirmations and user acknowledgments"""
    safety_warnings_acknowledged: bool = False
    data_loss_warning_accepted: bool = False
    device_selection_confirmed: bool = False
    recipe_configuration_approved: bool = False
    final_build_authorized: bool = False
    emergency_stop_understood: bool = False
    
    # Additional safety metadata
    confirmation_timestamp: Optional[datetime] = None
    user_safety_level: SafetyLevel = SafetyLevel.STANDARD
    validation_results: List[ValidationResult] = field(default_factory=list)
    
    def all_required_confirmations(self) -> bool:
        """Check if all required safety confirmations are obtained"""
        return (self.safety_warnings_acknowledged and
                self.data_loss_warning_accepted and
                self.device_selection_confirmed and
                self.recipe_configuration_approved and
                self.final_build_authorized and
                self.emergency_stop_understood)


@dataclass
class BuildResult:
    """Results and status of the build operation"""
    build_started: bool = False
    build_completed: bool = False
    build_successful: bool = False
    build_progress: Optional[BuildProgress] = None
    build_duration_seconds: Optional[float] = None
    error_messages: List[str] = field(default_factory=list)
    warning_messages: List[str] = field(default_factory=list)
    build_log: List[str] = field(default_factory=list)
    verification_passed: bool = False
    final_message: str = ""
    
    # Rollback information
    rollback_performed: bool = False
    rollback_successful: bool = False
    rollback_errors: List[str] = field(default_factory=list)


@dataclass
class WizardState:
    """Complete state of the wizard workflow"""
    # Hardware detection state
    detected_hardware: Optional[DetectedHardware] = None
    hardware_detection_status: str = "pending"  # "pending", "running", "completed", "failed"
    hardware_profile_matches: List[ProfileMatch] = field(default_factory=list)
    
    # OS image selection state
    os_image: OSImageInfo = field(default_factory=OSImageInfo)
    
    # Target device state
    target_device: Optional[DiskInfo] = None
    available_devices: List[DiskInfo] = field(default_factory=list)
    device_safety_check: Optional[ValidationResult] = None
    
    # Recipe configuration state
    recipe_config: RecipeConfiguration = field(default_factory=RecipeConfiguration)
    
    # Safety and user confirmations
    user_confirmations: UserConfirmations = field(default_factory=UserConfirmations)
    
    # Build operation state
    build_result: BuildResult = field(default_factory=BuildResult)
    
    # Wizard metadata
    wizard_session_id: str = ""
    current_step: WizardStep = WizardStep.DETECT_HARDWARE
    step_history: List[WizardStep] = field(default_factory=list)
    session_start_time: Optional[datetime] = None
    last_step_change_time: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize wizard state after creation"""
        if not self.wizard_session_id:
            self.wizard_session_id = datetime.now().strftime("wizard_%Y%m%d_%H%M%S")
        if not self.session_start_time:
            self.session_start_time = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert wizard state to dictionary for persistence"""
        # Note: This is a simplified serialization for Config integration
        # Full object serialization would require custom encoders
        return {
            "wizard_session_id": self.wizard_session_id,
            "current_step": self.current_step.name,
            "hardware_detection_status": self.hardware_detection_status,
            "os_image_path": self.os_image.image_path,
            "target_device_path": self.target_device.path if self.target_device else None,
            "selected_recipe_name": self.recipe_config.selected_recipe.name if self.recipe_config.selected_recipe else None,
            "session_start_time": self.session_start_time.isoformat() if self.session_start_time else None,
            "step_history": [step.name for step in self.step_history]
        }
    
    def get_step_summary(self) -> Dict[str, str]:
        """Get summary of completion status for each step"""
        return {
            "Hardware Detection": "✓ Complete" if self.detected_hardware else "⏳ Pending",
            "OS Image Selection": "✓ Complete" if self.os_image.is_valid() else "⏳ Pending", 
            "USB Configuration": "✓ Complete" if self.recipe_config.is_valid() else "⏳ Pending",
            "Safety Review": "✓ Complete" if self.user_confirmations.all_required_confirmations() else "⏳ Pending",
            "Build & Verify": "✓ Complete" if self.build_result.build_successful else "⏳ Pending",
            "Summary": "✓ Complete" if self.build_result.verification_passed else "⏳ Pending"
        }


class BaseStep(ABC):
    """Abstract base class for wizard step implementations"""
    
    def __init__(self, step_type: WizardStep):
        self.step_type = step_type
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.wizard_state: Optional[WizardState] = None
        self._is_bound = False
    
    def bind(self, state: WizardState) -> None:
        """Bind this step to the wizard state"""
        self.wizard_state = state
        self._is_bound = True
        self.logger.debug(f"Step {self.step_type.name} bound to wizard state")
    
    @abstractmethod
    def validate(self) -> Tuple[bool, str]:
        """
        Validate if this step can proceed to the next step
        
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        pass
    
    @abstractmethod 
    def on_enter(self) -> None:
        """Called when entering this step"""
        pass
    
    @abstractmethod
    def on_exit(self) -> None:
        """Called when exiting this step"""
        pass
    
    def get_step_name(self) -> str:
        """Get human-readable step name"""
        step_names = {
            WizardStep.DETECT_HARDWARE: "Hardware Detection",
            WizardStep.SELECT_OS_IMAGE: "OS Image Selection",
            WizardStep.CONFIGURE_USB: "USB Configuration", 
            WizardStep.SAFETY_REVIEW: "Safety Review",
            WizardStep.BUILD_VERIFY: "Build & Verify",
            WizardStep.SUMMARY: "Summary"
        }
        return step_names.get(self.step_type, "Unknown Step")
    
    def get_step_description(self) -> str:
        """Get detailed step description"""
        descriptions = {
            WizardStep.DETECT_HARDWARE: "Automatically detect your hardware configuration and find compatible deployment profiles",
            WizardStep.SELECT_OS_IMAGE: "Select and verify the operating system image for deployment",
            WizardStep.CONFIGURE_USB: "Choose target USB device and configure deployment settings",
            WizardStep.SAFETY_REVIEW: "Review safety warnings and confirm deployment configuration",
            WizardStep.BUILD_VERIFY: "Build the bootable USB drive and verify the installation",
            WizardStep.SUMMARY: "Review the deployment results and access your new bootable drive"
        }
        return descriptions.get(self.step_type, "Step description not available")
    
    def is_bound(self) -> bool:
        """Check if step is bound to wizard state"""
        return self._is_bound and self.wizard_state is not None


class WizardController(QObject):
    """
    Finite state machine controller for the stepper wizard workflow
    
    Manages step transitions, state validation, and persistence integration
    """
    
    # Signals for GUI integration
    step_changed = pyqtSignal(object, object)  # old_step, new_step
    state_updated = pyqtSignal(object)  # wizard_state
    validation_failed = pyqtSignal(str, str)  # step_name, error_message
    
    def __init__(self, config: Optional[Config] = None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.config = config or Config()
        
        # Wizard state and step management
        self.wizard_state = WizardState()
        self.current_step_index = 0
        self.step_sequence = list(WizardStep)
        self.steps: Dict[WizardStep, BaseStep] = {}
        
        # Core system components
        self.hardware_detector = HardwareDetector()
        self.hardware_matcher = HardwareMatcher()
        self.storage_builder_engine = StorageBuilderEngine()
        self.safety_validator = SafetyValidator()
        
        # Transition guards and restrictions
        self._build_in_progress = False
        self._emergency_stop_triggered = False
        
        self.logger.info(f"Wizard controller initialized with session ID: {self.wizard_state.wizard_session_id}")
    
    def register_step(self, step: BaseStep) -> None:
        """Register a step implementation with the controller"""
        if not isinstance(step, BaseStep):
            raise ValueError("Step must inherit from BaseStep")
        
        step.bind(self.wizard_state)
        self.steps[step.step_type] = step
        self.logger.debug(f"Registered step: {step.get_step_name()}")
    
    def get_current_step(self) -> WizardStep:
        """Get the current wizard step"""
        return self.wizard_state.current_step
    
    def get_current_step_implementation(self) -> Optional[BaseStep]:
        """Get the current step implementation"""
        return self.steps.get(self.get_current_step())
    
    def can_go_next(self) -> Tuple[bool, str]:
        """
        Check if navigation to next step is allowed
        
        Returns:
            Tuple[bool, str]: (can_proceed, reason_if_not)
        """
        if self._emergency_stop_triggered:
            return False, "Emergency stop has been triggered"
        
        if self._build_in_progress:
            return False, "Cannot navigate during build operation"
        
        # Check if we're at the last step
        if self.current_step_index >= len(self.step_sequence) - 1:
            return False, "Already at final step"
        
        # Validate current step
        current_step_impl = self.get_current_step_implementation()
        if current_step_impl:
            is_valid, error_message = current_step_impl.validate()
            if not is_valid:
                return False, f"Current step validation failed: {error_message}"
        
        return True, ""
    
    def can_go_back(self) -> Tuple[bool, str]:
        """
        Check if navigation to previous step is allowed
        
        Returns:
            Tuple[bool, str]: (can_proceed, reason_if_not)
        """
        if self._emergency_stop_triggered:
            return False, "Emergency stop has been triggered"
        
        if self._build_in_progress:
            return False, "Cannot navigate during build operation"
        
        if self.current_step_index <= 0:
            return False, "Already at first step"
        
        return True, ""
    
    def next(self) -> bool:
        """
        Navigate to the next step
        
        Returns:
            bool: True if navigation was successful
        """
        can_proceed, reason = self.can_go_next()
        if not can_proceed:
            self.logger.warning(f"Cannot proceed to next step: {reason}")
            self.validation_failed.emit(self.get_current_step().name, reason)
            return False
        
        # Exit current step
        current_step_impl = self.get_current_step_implementation()
        if current_step_impl:
            current_step_impl.on_exit()
        
        # Move to next step
        old_step = self.wizard_state.current_step
        self.current_step_index += 1
        self.wizard_state.current_step = self.step_sequence[self.current_step_index]
        self.wizard_state.step_history.append(old_step)
        self.wizard_state.last_step_change_time = datetime.now()
        
        # Enter new step
        new_step_impl = self.get_current_step_implementation()
        if new_step_impl:
            new_step_impl.on_enter()
        
        self.logger.info(f"Advanced from {old_step.name} to {self.wizard_state.current_step.name}")
        self.step_changed.emit(old_step, self.wizard_state.current_step)
        self.state_updated.emit(self.wizard_state)
        self._save_state()
        
        return True
    
    def back(self) -> bool:
        """
        Navigate to the previous step
        
        Returns:
            bool: True if navigation was successful
        """
        can_proceed, reason = self.can_go_back()
        if not can_proceed:
            self.logger.warning(f"Cannot go back: {reason}")
            return False
        
        # Exit current step
        current_step_impl = self.get_current_step_implementation()
        if current_step_impl:
            current_step_impl.on_exit()
        
        # Move to previous step
        old_step = self.wizard_state.current_step
        self.current_step_index -= 1
        self.wizard_state.current_step = self.step_sequence[self.current_step_index]
        self.wizard_state.last_step_change_time = datetime.now()
        
        # Enter previous step
        new_step_impl = self.get_current_step_implementation()
        if new_step_impl:
            new_step_impl.on_enter()
        
        self.logger.info(f"Moved back from {old_step.name} to {self.wizard_state.current_step.name}")
        self.step_changed.emit(old_step, self.wizard_state.current_step)
        self.state_updated.emit(self.wizard_state)
        self._save_state()
        
        return True
    
    def reset(self) -> None:
        """Reset wizard to the first step and clear state"""
        self.logger.info("Resetting wizard to initial state")
        
        # Exit current step
        current_step_impl = self.get_current_step_implementation()
        if current_step_impl:
            current_step_impl.on_exit()
        
        # Reset state
        old_step = self.wizard_state.current_step
        self.wizard_state = WizardState()
        self.current_step_index = 0
        self._build_in_progress = False
        self._emergency_stop_triggered = False
        
        # Re-bind all steps to new state
        for step_impl in self.steps.values():
            step_impl.bind(self.wizard_state)
        
        # Enter first step
        first_step_impl = self.get_current_step_implementation()
        if first_step_impl:
            first_step_impl.on_enter()
        
        self.step_changed.emit(old_step, self.wizard_state.current_step)
        self.state_updated.emit(self.wizard_state)
        self._save_state()
    
    def emergency_stop(self) -> None:
        """Trigger emergency stop - prevents all navigation"""
        self.logger.critical("Emergency stop triggered!")
        self._emergency_stop_triggered = True
        
        # If build is in progress, attempt to cancel it
        if self._build_in_progress:
            # TODO: Implement emergency build cancellation
            pass
    
    def set_build_in_progress(self, in_progress: bool) -> None:
        """Set build operation status"""
        self._build_in_progress = in_progress
        if in_progress:
            self.logger.info("Build operation started - navigation restricted")
        else:
            self.logger.info("Build operation completed - navigation enabled")
    
    def get_step_progress(self) -> Tuple[int, int]:
        """
        Get current step progress
        
        Returns:
            Tuple[int, int]: (current_step_number, total_steps)
        """
        return (self.current_step_index + 1, len(self.step_sequence))
    
    def get_completion_percentage(self) -> float:
        """Get overall wizard completion percentage"""
        return (self.current_step_index / (len(self.step_sequence) - 1)) * 100
    
    def _save_state(self) -> None:
        """Save wizard state to configuration for persistence"""
        try:
            state_data = self.wizard_state.to_dict()
            self.config.set("wizard_state", state_data)
            self.config.save()
            self.logger.debug("Wizard state saved to configuration")
        except Exception as e:
            self.logger.error(f"Failed to save wizard state: {e}")
    
    def load_state(self) -> bool:
        """
        Load wizard state from configuration
        
        Returns:
            bool: True if state was loaded successfully
        """
        try:
            state_data = self.config.get("wizard_state")
            if not state_data:
                self.logger.debug("No saved wizard state found")
                return False
            
            # Restore basic state (full restoration would require more complex deserialization)
            if "current_step" in state_data:
                step_name = state_data["current_step"]
                for i, step in enumerate(self.step_sequence):
                    if step.name == step_name:
                        self.current_step_index = i
                        self.wizard_state.current_step = step
                        break
            
            if "wizard_session_id" in state_data:
                self.wizard_state.wizard_session_id = state_data["wizard_session_id"]
            
            self.logger.info(f"Wizard state loaded - current step: {self.wizard_state.current_step.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load wizard state: {e}")
            return False
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get comprehensive state summary for debugging and monitoring"""
        return {
            "session_id": self.wizard_state.wizard_session_id,
            "current_step": self.wizard_state.current_step.name,
            "step_progress": f"{self.current_step_index + 1}/{len(self.step_sequence)}",
            "completion_percentage": f"{self.get_completion_percentage():.1f}%",
            "build_in_progress": self._build_in_progress,
            "emergency_stop": self._emergency_stop_triggered,
            "hardware_detected": self.wizard_state.detected_hardware is not None,
            "os_image_valid": self.wizard_state.os_image.is_valid(),
            "recipe_valid": self.wizard_state.recipe_config.is_valid(),
            "confirmations_complete": self.wizard_state.user_confirmations.all_required_confirmations(),
            "build_successful": self.wizard_state.build_result.build_successful,
            "step_history": [step.name for step in self.wizard_state.step_history[-5:]],  # Last 5 steps
            "session_duration": str(datetime.now() - self.wizard_state.session_start_time) if self.wizard_state.session_start_time else "Unknown"
        }


# Concrete step implementations would be created separately as needed
# Example placeholder for future development:

class HardwareDetectionStep(BaseStep):
    """Concrete implementation of hardware detection step"""
    
    def __init__(self):
        super().__init__(WizardStep.DETECT_HARDWARE)
    
    def validate(self) -> Tuple[bool, str]:
        """Validate hardware detection completion"""
        if not self.wizard_state:
            return False, "Step not bound to wizard state"
        
        if self.wizard_state.detected_hardware is None:
            return False, "Hardware detection not completed"
        
        if self.wizard_state.hardware_detection_status != "completed":
            return False, f"Hardware detection status: {self.wizard_state.hardware_detection_status}"
        
        return True, ""
    
    def on_enter(self) -> None:
        """Initialize hardware detection"""
        self.logger.info("Entering hardware detection step")
        if self.wizard_state:
            self.wizard_state.hardware_detection_status = "pending"
    
    def on_exit(self) -> None:
        """Cleanup when leaving hardware detection"""
        self.logger.info("Exiting hardware detection step")


# Factory function for creating a fully configured wizard controller
def create_wizard_controller(config: Optional[Config] = None) -> WizardController:
    """
    Factory function to create a properly configured wizard controller
    
    Args:
        config: Optional configuration instance
        
    Returns:
        WizardController: Fully configured wizard controller
    """
    controller = WizardController(config)
    
    # Register default step implementations
    # (In a full implementation, these would be more sophisticated)
    controller.register_step(HardwareDetectionStep())
    
    # TODO: Register other step implementations:
    # controller.register_step(OSImageSelectionStep())
    # controller.register_step(USBConfigurationStep()) 
    # controller.register_step(SafetyReviewStep())
    # controller.register_step(BuildVerifyStep())
    # controller.register_step(SummaryStep())
    
    return controller