"""
BootForge OCLP Safety Controller
Comprehensive safety controls and user consent flows for OCLP operations
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal

from src.core.safety_validator import SafetyValidator, ValidationResult, DeviceRisk
from src.core.hardware_profiles import is_mac_oclp_compatible, get_mac_oclp_requirements


class OCLPRiskLevel(Enum):
    """OCLP operation risk levels"""
    LOW = "low"              # Minor patches, reversible
    MEDIUM = "medium"        # System modifications, mostly reversible  
    HIGH = "high"           # Deep system changes, warranty implications
    CRITICAL = "critical"   # Experimental patches, potential data loss


@dataclass
class OCLPRiskAssessment:
    """Assessment of risks for OCLP operation"""
    overall_risk: OCLPRiskLevel
    risk_factors: List[str]
    warnings: List[str]
    user_consent_required: bool
    recommended_actions: List[str]
    warranty_implications: bool
    reversibility_level: str  # "fully_reversible", "mostly_reversible", "irreversible"


@dataclass
class OCLPConsentRecord:
    """Record of user consent for OCLP operations"""
    risk_id: str
    risk_level: OCLPRiskLevel
    user_acknowledged: bool
    timestamp: str
    ip_address: Optional[str] = None
    user_notes: Optional[str] = None


class OCLPSafetyController(QObject):
    """Safety controller for OCLP operations with comprehensive risk assessment"""
    
    # Signals for user interaction
    consent_required = pyqtSignal(str, object, object)  # title, risk_assessment, callback
    warning_issued = pyqtSignal(str, str)  # level, message
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.safety_validator = SafetyValidator()
        self.consent_records: Dict[str, OCLPConsentRecord] = {}
        
        # Risk assessment thresholds
        self.risk_thresholds = {
            "system_modification": OCLPRiskLevel.MEDIUM,
            "kext_injection": OCLPRiskLevel.MEDIUM,
            "sip_disable_required": OCLPRiskLevel.HIGH,
            "amfi_patches": OCLPRiskLevel.HIGH,
            "experimental_support": OCLPRiskLevel.CRITICAL,
            "warranty_void": OCLPRiskLevel.HIGH
        }
    
    def assess_oclp_risks(self, model_id: str, macos_version: str, 
                          requested_patches: List[str]) -> OCLPRiskAssessment:
        """Comprehensive risk assessment for OCLP operation"""
        try:
            # Check basic compatibility
            if not is_mac_oclp_compatible(model_id):
                return OCLPRiskAssessment(
                    overall_risk=OCLPRiskLevel.CRITICAL,
                    risk_factors=[f"Mac model {model_id} is not supported by OCLP"],
                    warnings=["This hardware is not compatible with OpenCore Legacy Patcher"],
                    user_consent_required=True,
                    recommended_actions=["Use standard macOS installer if supported"],
                    warranty_implications=False,
                    reversibility_level="not_applicable"
                )
            
            # Get comprehensive requirements
            oclp_requirements = get_mac_oclp_requirements(model_id, macos_version)
            if not oclp_requirements:
                return self._create_unknown_risk_assessment(model_id)
            
            risk_factors = []
            warnings = []
            recommended_actions = []
            overall_risk = OCLPRiskLevel.LOW
            warranty_implications = False
            
            # Assess compatibility level risks
            compatibility = oclp_requirements.get("oclp_compatibility", "unknown")
            if compatibility == "experimental":
                risk_factors.append("Experimental OCLP support - may be unstable")
                warnings.append("This Mac model has experimental OCLP support and may experience instability")
                overall_risk = max(overall_risk, OCLPRiskLevel.CRITICAL)
                recommended_actions.append("Consider using a newer Mac model if possible")
            elif compatibility == "partially_supported":
                risk_factors.append("Partial OCLP support - some features may not work")
                warnings.append("Some hardware features may not work properly with OCLP")
                overall_risk = max(overall_risk, OCLPRiskLevel.MEDIUM)
            
            # Assess patch-specific risks
            required_patches = oclp_requirements.get("required_patches", [])
            graphics_patches = oclp_requirements.get("graphics_patches", [])
            audio_patches = oclp_requirements.get("audio_patches", [])
            
            if required_patches:
                risk_factors.append(f"Requires {len(required_patches)} system patches")
                overall_risk = max(overall_risk, OCLPRiskLevel.MEDIUM)
                warranty_implications = True
            
            if graphics_patches:
                risk_factors.append("Graphics driver patches required")
                warnings.append("Graphics performance may be reduced compared to native support")
                overall_risk = max(overall_risk, OCLPRiskLevel.MEDIUM)
            
            if audio_patches:
                risk_factors.append("Audio driver patches required")
                warnings.append("Audio functionality may have limitations")
            
            # Assess SIP and security implications
            sip_requirements = oclp_requirements.get("sip_requirements")
            if sip_requirements == "disabled":
                risk_factors.append("Requires disabling System Integrity Protection (SIP)")
                warnings.append("SIP must be disabled, reducing system security")
                overall_risk = max(overall_risk, OCLPRiskLevel.HIGH)
                warranty_implications = True
                recommended_actions.append("Understand that disabling SIP reduces system security")
            
            # Check for AMFI patches
            if any("amfi" in patch.lower() for patch in required_patches):
                risk_factors.append("Apple Mobile File Integrity (AMFI) patches required")
                warnings.append("AMFI patches modify system security mechanisms")
                overall_risk = max(overall_risk, OCLPRiskLevel.HIGH)
                warranty_implications = True
            
            # Determine reversibility
            reversibility_level = "mostly_reversible"
            if overall_risk in [OCLPRiskLevel.HIGH, OCLPRiskLevel.CRITICAL]:
                reversibility_level = "partially_reversible"
            if sip_requirements == "disabled":
                reversibility_level = "partially_reversible"
            
            # Add general recommendations
            recommended_actions.extend([
                "Create a full system backup before proceeding",
                "Ensure you understand the implications of OCLP patches",
                "Have recovery media available in case of issues"
            ])
            
            if warranty_implications:
                warnings.append("OCLP modifications may void your Mac's warranty")
                recommended_actions.append("Consider warranty implications before proceeding")
            
            return OCLPRiskAssessment(
                overall_risk=overall_risk,
                risk_factors=risk_factors,
                warnings=warnings,
                user_consent_required=overall_risk in [OCLPRiskLevel.HIGH, OCLPRiskLevel.CRITICAL],
                recommended_actions=recommended_actions,
                warranty_implications=warranty_implications,
                reversibility_level=reversibility_level
            )
            
        except Exception as e:
            self.logger.error(f"Risk assessment failed for {model_id}: {e}")
            return self._create_error_risk_assessment(str(e))
    
    def request_user_consent(self, operation_name: str, risk_assessment: OCLPRiskAssessment,
                            callback: Callable[[bool], None]) -> None:
        """Request user consent for OCLP operation with comprehensive risk disclosure"""
        try:
            # Generate consent title and detailed message
            title = f"OCLP Operation Consent Required - {risk_assessment.overall_risk.value.title()} Risk"
            
            message_parts = [
                f"BootForge is requesting consent to perform OpenCore Legacy Patcher operations.",
                f"Operation: {operation_name}",
                f"Risk Level: {risk_assessment.overall_risk.value.title()}",
                "",
                "Risk Factors:"
            ]
            
            for risk_factor in risk_assessment.risk_factors:
                message_parts.append(f"• {risk_factor}")
            
            if risk_assessment.warnings:
                message_parts.extend(["", "Warnings:"])
                for warning in risk_assessment.warnings:
                    message_parts.append(f"• {warning}")
            
            if risk_assessment.recommended_actions:
                message_parts.extend(["", "Recommended Actions:"])
                for action in risk_assessment.recommended_actions:
                    message_parts.append(f"• {action}")
            
            message_parts.extend([
                "",
                f"Warranty Implications: {'Yes' if risk_assessment.warranty_implications else 'No'}",
                f"Reversibility: {risk_assessment.reversibility_level.replace('_', ' ').title()}",
                "",
                "Do you consent to proceed with this OCLP operation?",
                "",
                "By clicking 'Yes', you acknowledge that you understand the risks and",
                "accept responsibility for any consequences of this operation."
            ])
            
            message = "\\n".join(message_parts)
            
            # Store callback for response handling
            risk_id = f"{operation_name}_{hash(message)}"
            self.consent_records[risk_id] = OCLPConsentRecord(
                risk_id=risk_id,
                risk_level=risk_assessment.overall_risk,
                user_acknowledged=False,
                timestamp=str(time.time())
            )
            
            # Create consent callback wrapper
            def consent_callback(user_consented: bool):
                self.consent_records[risk_id].user_acknowledged = user_consented
                if user_consented:
                    self.logger.info(f"User consented to OCLP operation: {operation_name}")
                else:
                    self.logger.info(f"User declined OCLP operation: {operation_name}")
                callback(user_consented)
            
            # Emit consent request signal
            self.consent_required.emit(title, risk_assessment, consent_callback)
            
        except Exception as e:
            self.logger.error(f"Failed to request user consent: {e}")
            callback(False)  # Default to denial on error
    
    def validate_oclp_safety(self, model_id: str, macos_version: str, 
                            target_device: str) -> ValidationResult:
        """Validate safety of OCLP operation using SafetyValidator"""
        try:
            # Use SafetyValidator for additional device safety checks
            device_validation = self.safety_validator.validate_device_safety(
                device_path=target_device,
                operation_type="oclp_installation"
            )
            
            if not device_validation.is_safe:
                return ValidationResult(
                    is_safe=False,
                    risk_level=device_validation.risk_level,
                    issues=device_validation.issues,
                    warnings=device_validation.warnings,
                    recommendations=device_validation.recommendations
                )
            
            # Additional OCLP-specific safety checks
            oclp_issues = []
            oclp_warnings = []
            oclp_recommendations = []
            
            # Check for known problematic combinations
            if not is_mac_oclp_compatible(model_id):
                oclp_issues.append(f"Mac model {model_id} is not compatible with OCLP")
            
            # Check macOS version compatibility
            if macos_version.startswith("15."):  # macOS Sequoia
                oclp_warnings.append("macOS Sequoia support may be experimental")
                oclp_recommendations.append("Consider using macOS Ventura or Monterey for better stability")
            
            return ValidationResult(
                is_safe=len(oclp_issues) == 0,
                risk_level=device_validation.risk_level,
                issues=device_validation.issues + oclp_issues,
                warnings=device_validation.warnings + oclp_warnings,
                recommendations=device_validation.recommendations + oclp_recommendations
            )
            
        except Exception as e:
            self.logger.error(f"OCLP safety validation failed: {e}")
            return ValidationResult(
                is_safe=False,
                risk_level=DeviceRisk.HIGH,
                issues=[f"Safety validation failed: {e}"],
                warnings=[],
                recommendations=["Contact support for assistance"]
            )
    
    def _create_unknown_risk_assessment(self, model_id: str) -> OCLPRiskAssessment:
        """Create risk assessment for unknown Mac model"""
        return OCLPRiskAssessment(
            overall_risk=OCLPRiskLevel.CRITICAL,
            risk_factors=[f"Unknown Mac model {model_id} - cannot assess compatibility"],
            warnings=["Cannot determine OCLP compatibility for this Mac model"],
            user_consent_required=True,
            recommended_actions=[
                "Verify Mac model identification is correct",
                "Check OCLP documentation for model support",
                "Proceed with extreme caution"
            ],
            warranty_implications=True,
            reversibility_level="unknown"
        )
    
    def _create_error_risk_assessment(self, error: str) -> OCLPRiskAssessment:
        """Create risk assessment for error conditions"""
        return OCLPRiskAssessment(
            overall_risk=OCLPRiskLevel.CRITICAL,
            risk_factors=[f"Risk assessment failed: {error}"],
            warnings=["Cannot properly assess risks due to system error"],
            user_consent_required=True,
            recommended_actions=[
                "Resolve the underlying error before proceeding",
                "Contact support if the issue persists"
            ],
            warranty_implications=True,
            reversibility_level="unknown"
        )
    
    def get_consent_history(self) -> List[OCLPConsentRecord]:
        """Get history of user consent records"""
        return list(self.consent_records.values())
    
    def clear_consent_history(self) -> None:
        """Clear all consent records"""
        self.consent_records.clear()
        self.logger.info("OCLP consent history cleared")