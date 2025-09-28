"""
BootForge Error Prevention & Recovery Engine
Smart retry mechanisms, automatic rollback, and comprehensive error recovery
"""

import logging
import time
import threading
import shutil
import hashlib
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import json
import pickle


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types"""
    RETRY = "retry"                    # Simple retry with backoff
    ROLLBACK = "rollback"             # Restore to previous state
    ALTERNATIVE = "alternative"        # Try alternative approach
    USER_INTERVENTION = "user_intervention"  # Require user action
    ABORT = "abort"                   # Stop operation safely


class ErrorSeverity(Enum):
    """Error severity levels"""
    WARNING = "warning"        # Recoverable warnings
    RECOVERABLE = "recoverable" # Can be automatically recovered
    CRITICAL = "critical"      # Requires intervention but recoverable
    FATAL = "fatal"            # Cannot be recovered


class OperationPhase(Enum):
    """Phases of storage deployment operations"""
    PREPARATION = "preparation"
    VALIDATION = "validation"
    BACKUP = "backup"
    PARTITIONING = "partitioning"
    FORMATTING = "formatting"
    WRITING = "writing"
    VERIFICATION = "verification"
    CLEANUP = "cleanup"


@dataclass
class ErrorContext:
    """Context information for an error"""
    error_type: str
    error_message: str
    phase: OperationPhase
    severity: ErrorSeverity
    timestamp: float = field(default_factory=time.time)
    stack_trace: Optional[str] = None
    operation_id: Optional[str] = None
    affected_files: List[str] = field(default_factory=list)
    system_state: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0


@dataclass
class RecoveryAction:
    """Recovery action to be taken"""
    strategy: RecoveryStrategy
    description: str
    confidence: float  # 0.0 to 1.0
    estimated_time: float  # seconds
    requires_user_approval: bool = False
    rollback_point: Optional[str] = None
    alternative_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CheckpointState:
    """System checkpoint for rollback"""
    checkpoint_id: str
    timestamp: float
    operation_phase: OperationPhase
    device_state: Dict[str, Any]
    file_checksums: Dict[str, str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def save_to_file(self, filepath: Path):
        """Save checkpoint to file"""
        with open(filepath, 'wb') as f:
            pickle.dump(self, f)
    
    @classmethod
    def load_from_file(cls, filepath: Path) -> 'CheckpointState':
        """Load checkpoint from file"""
        with open(filepath, 'rb') as f:
            return pickle.load(f)


class ErrorRecoveryEngine(ABC):
    """Base class for error recovery engines"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def can_handle(self, error_context: ErrorContext) -> bool:
        """Check if this engine can handle the error"""
        pass
    
    @abstractmethod
    def analyze_error(self, error_context: ErrorContext) -> List[RecoveryAction]:
        """Analyze error and suggest recovery actions"""
        pass
    
    @abstractmethod
    def execute_recovery(self, action: RecoveryAction, error_context: ErrorContext) -> bool:
        """Execute recovery action"""
        pass


class IOErrorRecoveryEngine(ErrorRecoveryEngine):
    """Handles I/O related errors (disk write failures, permission issues, etc.)"""
    
    def __init__(self):
        super().__init__("I/O Error Recovery")
        self.max_retries = 3
        self.retry_delays = [1, 3, 5]  # seconds
    
    def can_handle(self, error_context: ErrorContext) -> bool:
        """Check if this is an I/O error"""
        io_error_types = [
            "PermissionError", "IOError", "OSError", "DiskError",
            "WriteError", "ReadError", "DeviceError"
        ]
        return any(error_type in error_context.error_type for error_type in io_error_types)
    
    def analyze_error(self, error_context: ErrorContext) -> List[RecoveryAction]:
        """Analyze I/O error and suggest recovery"""
        actions = []
        
        if error_context.retry_count < self.max_retries:
            # Try retry with exponential backoff
            actions.append(RecoveryAction(
                RecoveryStrategy.RETRY,
                f"Retry operation (attempt {error_context.retry_count + 1}/{self.max_retries})",
                0.8 - (error_context.retry_count * 0.2),
                self.retry_delays[min(error_context.retry_count, len(self.retry_delays) - 1)],
                requires_user_approval=False
            ))
        
        if "Permission" in error_context.error_type:
            # Permission-specific recovery
            actions.append(RecoveryAction(
                RecoveryStrategy.USER_INTERVENTION,
                "Elevate permissions or run as administrator",
                0.9,
                0,
                requires_user_approval=True
            ))
        
        if error_context.phase in [OperationPhase.WRITING, OperationPhase.FORMATTING]:
            # Rollback option for write operations
            actions.append(RecoveryAction(
                RecoveryStrategy.ROLLBACK,
                "Rollback to last checkpoint and try alternative method",
                0.7,
                10,
                requires_user_approval=True,
                rollback_point="pre_write"
            ))
        
        return actions
    
    def execute_recovery(self, action: RecoveryAction, error_context: ErrorContext) -> bool:
        """Execute I/O error recovery"""
        if action.strategy == RecoveryStrategy.RETRY:
            # Wait before retry
            time.sleep(action.estimated_time)
            self.logger.info(f"Retrying after {action.estimated_time}s delay")
            return True
        
        elif action.strategy == RecoveryStrategy.USER_INTERVENTION:
            # This would be handled by the UI layer
            self.logger.info("User intervention required for permission issues")
            return False  # Requires external action
        
        elif action.strategy == RecoveryStrategy.ROLLBACK:
            # This would be handled by the checkpoint manager
            self.logger.info(f"Initiating rollback to {action.rollback_point}")
            return True
        
        return False


class IntegrityErrorRecoveryEngine(ErrorRecoveryEngine):
    """Handles data integrity and verification errors"""
    
    def __init__(self):
        super().__init__("Integrity Error Recovery")
    
    def can_handle(self, error_context: ErrorContext) -> bool:
        """Check if this is an integrity error"""
        integrity_errors = [
            "ChecksumError", "HashMismatch", "CorruptionError",
            "IntegrityError", "VerificationError"
        ]
        return any(error_type in error_context.error_type for error_type in integrity_errors)
    
    def analyze_error(self, error_context: ErrorContext) -> List[RecoveryAction]:
        """Analyze integrity error"""
        actions = []
        
        if error_context.phase == OperationPhase.VERIFICATION:
            # Re-verify with different method
            actions.append(RecoveryAction(
                RecoveryStrategy.ALTERNATIVE,
                "Retry verification with alternative checksum method",
                0.8,
                5,
                alternative_params={"verification_method": "alternative"}
            ))
            
            # Re-write corrupted data
            actions.append(RecoveryAction(
                RecoveryStrategy.ROLLBACK,
                "Re-write data from clean source",
                0.7,
                30,
                rollback_point="pre_write",
                requires_user_approval=True
            ))
        
        if error_context.phase == OperationPhase.WRITING:
            # Retry with different write method
            actions.append(RecoveryAction(
                RecoveryStrategy.ALTERNATIVE,
                "Retry with slower, more reliable write method",
                0.85,
                60,
                alternative_params={"write_method": "safe_slow"}
            ))
        
        return actions
    
    def execute_recovery(self, action: RecoveryAction, error_context: ErrorContext) -> bool:
        """Execute integrity error recovery"""
        if action.strategy == RecoveryStrategy.ALTERNATIVE:
            self.logger.info(f"Using alternative method: {action.alternative_params}")
            return True
        
        elif action.strategy == RecoveryStrategy.ROLLBACK:
            self.logger.info("Rolling back for data re-write")
            return True
        
        return False


class NetworkErrorRecoveryEngine(ErrorRecoveryEngine):
    """Handles network-related errors during downloads"""
    
    def __init__(self):
        super().__init__("Network Error Recovery")
        self.max_retries = 5
        self.retry_delays = [2, 5, 10, 20, 30]
    
    def can_handle(self, error_context: ErrorContext) -> bool:
        """Check if this is a network error"""
        network_errors = [
            "ConnectionError", "TimeoutError", "URLError", "HTTPError",
            "NetworkError", "DownloadError", "DNSError"
        ]
        return any(error_type in error_context.error_type for error_type in network_errors)
    
    def analyze_error(self, error_context: ErrorContext) -> List[RecoveryAction]:
        """Analyze network error"""
        actions = []
        
        if error_context.retry_count < self.max_retries:
            # Progressive retry with increasing delays
            delay = self.retry_delays[min(error_context.retry_count, len(self.retry_delays) - 1)]
            actions.append(RecoveryAction(
                RecoveryStrategy.RETRY,
                f"Retry download (attempt {error_context.retry_count + 1}/{self.max_retries})",
                0.9 - (error_context.retry_count * 0.15),
                delay
            ))
        
        # Alternative download sources
        if "HTTPError" in error_context.error_type:
            actions.append(RecoveryAction(
                RecoveryStrategy.ALTERNATIVE,
                "Try alternative download mirror",
                0.7,
                10,
                alternative_params={"use_mirror": True}
            ))
        
        return actions
    
    def execute_recovery(self, action: RecoveryAction, error_context: ErrorContext) -> bool:
        """Execute network error recovery"""
        if action.strategy == RecoveryStrategy.RETRY:
            time.sleep(action.estimated_time)
            self.logger.info(f"Retrying network operation after {action.estimated_time}s")
            return True
        
        elif action.strategy == RecoveryStrategy.ALTERNATIVE:
            self.logger.info("Switching to alternative download source")
            return True
        
        return False


class CheckpointManager:
    """Manages operation checkpoints for rollback capability"""
    
    def __init__(self, checkpoint_dir: Path):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__ + ".CheckpointManager")
        self.checkpoints: Dict[str, CheckpointState] = {}
    
    def create_checkpoint(
        self, 
        checkpoint_id: str, 
        phase: OperationPhase, 
        device_path: str,
        source_files: List[Path] = None
    ) -> CheckpointState:
        """Create a system checkpoint"""
        self.logger.info(f"Creating checkpoint: {checkpoint_id} at phase {phase.value}")
        
        # Collect system state
        device_state = self._capture_device_state(device_path)
        file_checksums = self._calculate_file_checksums(source_files or [])
        
        checkpoint = CheckpointState(
            checkpoint_id=checkpoint_id,
            timestamp=time.time(),
            operation_phase=phase,
            device_state=device_state,
            file_checksums=file_checksums,
            metadata={
                "device_path": device_path,
                "source_files": [str(f) for f in (source_files or [])]
            }
        )
        
        # Save checkpoint
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.checkpoint"
        checkpoint.save_to_file(checkpoint_file)
        self.checkpoints[checkpoint_id] = checkpoint
        
        self.logger.info(f"Checkpoint {checkpoint_id} created successfully")
        return checkpoint
    
    def rollback_to_checkpoint(self, checkpoint_id: str) -> bool:
        """Rollback system to a specific checkpoint"""
        try:
            if checkpoint_id not in self.checkpoints:
                # Try loading from file
                checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.checkpoint"
                if checkpoint_file.exists():
                    checkpoint = CheckpointState.load_from_file(checkpoint_file)
                    self.checkpoints[checkpoint_id] = checkpoint
                else:
                    self.logger.error(f"Checkpoint {checkpoint_id} not found")
                    return False
            
            checkpoint = self.checkpoints[checkpoint_id]
            self.logger.info(f"Rolling back to checkpoint {checkpoint_id} from {checkpoint.timestamp}")
            
            # Restore device state (this would involve actual restoration logic)
            success = self._restore_device_state(checkpoint.device_state)
            
            if success:
                self.logger.info(f"Successfully rolled back to checkpoint {checkpoint_id}")
            else:
                self.logger.error(f"Failed to rollback to checkpoint {checkpoint_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error during rollback: {e}")
            return False
    
    def _capture_device_state(self, device_path: str) -> Dict[str, Any]:
        """Capture current device state for rollback"""
        # This would capture partition table, filesystem info, etc.
        # Simplified implementation
        return {
            "device_path": device_path,
            "timestamp": time.time(),
            "partition_info": "captured"  # Placeholder
        }
    
    def _restore_device_state(self, device_state: Dict[str, Any]) -> bool:
        """Restore device to previous state"""
        # This would implement actual device restoration
        # Simplified implementation
        self.logger.info(f"Restoring device state: {device_state}")
        return True  # Placeholder
    
    def _calculate_file_checksums(self, files: List[Path]) -> Dict[str, str]:
        """Calculate checksums for source files"""
        checksums = {}
        for file_path in files:
            if file_path.exists():
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read(1024 * 1024)  # First MB for quick checksum
                        checksums[str(file_path)] = hashlib.sha256(content).hexdigest()
                except Exception as e:
                    self.logger.warning(f"Could not checksum {file_path}: {e}")
        return checksums
    
    def cleanup_old_checkpoints(self, max_age_hours: int = 24):
        """Clean up old checkpoints"""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        for checkpoint_id in list(self.checkpoints.keys()):
            checkpoint = self.checkpoints[checkpoint_id]
            if current_time - checkpoint.timestamp > max_age_seconds:
                # Remove from memory and disk
                del self.checkpoints[checkpoint_id]
                checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.checkpoint"
                if checkpoint_file.exists():
                    checkpoint_file.unlink()
                self.logger.info(f"Cleaned up old checkpoint: {checkpoint_id}")


class ErrorPreventionRecoveryManager:
    """Main manager for error prevention and recovery"""
    
    def __init__(self, checkpoint_dir: Path):
        self.logger = logging.getLogger(__name__)
        
        # Initialize recovery engines
        self.recovery_engines = [
            IOErrorRecoveryEngine(),
            IntegrityErrorRecoveryEngine(),
            NetworkErrorRecoveryEngine()
        ]
        
        # Checkpoint manager
        self.checkpoint_manager = CheckpointManager(checkpoint_dir)
        
        # Error history
        self.error_history: List[ErrorContext] = []
        self.max_history_size = 100
        
        # Callbacks
        self.error_callbacks: List[Callable[[ErrorContext], None]] = []
        self.recovery_callbacks: List[Callable[[RecoveryAction, bool], None]] = []
        
        self.logger.info("Error Prevention & Recovery Manager initialized")
    
    def add_error_callback(self, callback: Callable[[ErrorContext], None]):
        """Add callback for error notifications"""
        self.error_callbacks.append(callback)
    
    def add_recovery_callback(self, callback: Callable[[RecoveryAction, bool], None]):
        """Add callback for recovery notifications"""  
        self.recovery_callbacks.append(callback)
    
    def handle_error(
        self, 
        error: Exception, 
        phase: OperationPhase, 
        operation_id: str = None,
        retry_count: int = 0
    ) -> List[RecoveryAction]:
        """Handle an error and suggest recovery actions"""
        
        # Create error context
        error_context = ErrorContext(
            error_type=type(error).__name__,
            error_message=str(error),
            phase=phase,
            severity=self._determine_severity(error, phase),
            operation_id=operation_id,
            retry_count=retry_count
        )
        
        # Add to history
        self.error_history.append(error_context)
        if len(self.error_history) > self.max_history_size:
            self.error_history = self.error_history[-self.max_history_size:]
        
        # Notify callbacks
        for callback in self.error_callbacks:
            try:
                callback(error_context)
            except Exception as e:
                self.logger.error(f"Error in error callback: {e}")
        
        # Find applicable recovery engines
        recovery_actions = []
        for engine in self.recovery_engines:
            if engine.can_handle(error_context):
                actions = engine.analyze_error(error_context)
                recovery_actions.extend(actions)
                self.logger.info(f"{engine.name} suggested {len(actions)} recovery actions")
        
        # Sort actions by confidence
        recovery_actions.sort(key=lambda a: a.confidence, reverse=True)
        
        self.logger.info(f"Generated {len(recovery_actions)} recovery actions for {error_context.error_type}")
        return recovery_actions
    
    def execute_recovery(self, action: RecoveryAction, error_context: ErrorContext) -> bool:
        """Execute a recovery action"""
        self.logger.info(f"Executing recovery action: {action.strategy.value} - {action.description}")
        
        success = False
        
        # Handle checkpoint-based recovery
        if action.strategy == RecoveryStrategy.ROLLBACK and action.rollback_point:
            success = self.checkpoint_manager.rollback_to_checkpoint(action.rollback_point)
        else:
            # Find the appropriate engine to execute the recovery
            for engine in self.recovery_engines:
                if engine.can_handle(error_context):
                    success = engine.execute_recovery(action, error_context)
                    break
        
        # Notify callbacks
        for callback in self.recovery_callbacks:
            try:
                callback(action, success)
            except Exception as e:
                self.logger.error(f"Error in recovery callback: {e}")
        
        if success:
            self.logger.info(f"Recovery action completed successfully: {action.description}")
        else:
            self.logger.warning(f"Recovery action failed: {action.description}")
        
        return success
    
    def create_operation_checkpoint(
        self, 
        phase: OperationPhase, 
        device_path: str,
        source_files: List[Path] = None
    ) -> str:
        """Create a checkpoint for the current operation"""
        checkpoint_id = f"{phase.value}_{int(time.time())}"
        self.checkpoint_manager.create_checkpoint(checkpoint_id, phase, device_path, source_files)
        return checkpoint_id
    
    def _determine_severity(self, error: Exception, phase: OperationPhase) -> ErrorSeverity:
        """Determine error severity based on error type and phase"""
        
        # Critical phases where errors are more severe
        critical_phases = [OperationPhase.PARTITIONING, OperationPhase.FORMATTING, OperationPhase.WRITING]
        
        # Fatal error types
        fatal_errors = ["SystemError", "FatalError", "CriticalError"]
        if any(fatal_error in str(type(error)) for fatal_error in fatal_errors):
            return ErrorSeverity.FATAL
        
        # Critical errors in critical phases
        critical_errors = ["PermissionError", "DiskError", "DeviceError"]
        if (phase in critical_phases and 
            any(critical_error in str(type(error)) for critical_error in critical_errors)):
            return ErrorSeverity.CRITICAL
        
        # Recoverable errors
        recoverable_errors = ["IOError", "NetworkError", "TimeoutError", "RetryableError"]
        if any(recoverable_error in str(type(error)) for recoverable_error in recoverable_errors):
            return ErrorSeverity.RECOVERABLE
        
        # Default to warning
        return ErrorSeverity.WARNING
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics and patterns"""
        if not self.error_history:
            return {"total_errors": 0}
        
        total_errors = len(self.error_history)
        error_types = {}
        severity_counts = {}
        phase_errors = {}
        
        for error in self.error_history:
            # Count error types
            error_types[error.error_type] = error_types.get(error.error_type, 0) + 1
            
            # Count severities
            severity_counts[error.severity.value] = severity_counts.get(error.severity.value, 0) + 1
            
            # Count phase errors
            phase_errors[error.phase.value] = phase_errors.get(error.phase.value, 0) + 1
        
        return {
            "total_errors": total_errors,
            "error_types": error_types,
            "severity_distribution": severity_counts,
            "phase_distribution": phase_errors,
            "recent_errors": len([e for e in self.error_history if time.time() - e.timestamp < 3600])  # Last hour
        }