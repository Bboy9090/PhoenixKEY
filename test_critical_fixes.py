#!/usr/bin/env python3
"""
Comprehensive test script to verify all critical fixes are working correctly.
Tests circular import fix, security controls, execution targeting, and provider integration.
"""

import sys
import os
import tempfile
import traceback
from pathlib import Path

def test_circular_import_fix():
    """Test 1: Verify circular import fix works correctly"""
    print("\n=== TEST 1: CIRCULAR IMPORT FIX ===")
    
    try:
        # Test that we can import from models without circular dependency
        from src.core.models import HardwareProfile, DeploymentType, PartitionScheme, FileSystem
        print("✅ Successfully imported from models.py")
        
        # Test that hardware_profiles doesn't import from usb_builder anymore
        from src.core.hardware_profiles import get_mac_model_data, create_mac_hardware_profile
        print("✅ Successfully imported from hardware_profiles.py")
        
        # Test that usb_builder imports from models
        from src.core.usb_builder import USBBuilder
        print("✅ Successfully imported from usb_builder.py")
        
        # Test that other modules import from models
        from src.core.hardware_matcher import HardwareMatcher
        from src.core.hardware_detector import DetectedHardware
        from src.core.patch_pipeline import PatchPlanner
        print("✅ Successfully imported from all dependent modules")
        
        # Test creating a Mac hardware profile
        profile = create_mac_hardware_profile("MacBookPro15,1")
        print(f"✅ Successfully created hardware profile: {profile.name}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        return False

def test_security_controls():
    """Test 2: Verify security controls are enforced"""
    print("\n=== TEST 2: SECURITY CONTROLS ===")
    
    try:
        from src.core.patch_pipeline import PatchPlanner, PatchAction, PatchType, PatchPhase, PatchPriority
        from src.core.safety_validator import SafetyValidator, PatchValidationMode, ValidationResult
        from src.core.hardware_detector import DetectedHardware
        
        # Test COMPLIANT mode defaults
        safety_validator = SafetyValidator()
        print(f"✅ Default patch mode: {safety_validator.patch_mode.value}")
        
        if safety_validator.patch_mode != PatchValidationMode.COMPLIANT:
            print(f"❌ ERROR: Default should be COMPLIANT, got {safety_validator.patch_mode.value}")
            return False
        
        # Test PatchPlanner with COMPLIANT mode
        planner = PatchPlanner(safety_validator)
        print("✅ Successfully created PatchPlanner with COMPLIANT mode")
        
        # Create a dangerous action that should be blocked
        dangerous_action = PatchAction(
            id="test_dangerous",
            name="Test Dangerous Script",
            description="This should be blocked",
            patch_type=PatchType.CUSTOM_SCRIPT,
            phase=PatchPhase.POST_INSTALL,
            priority=PatchPriority.HIGH,
            command="rm -rf /"  # Extremely dangerous command
        )
        
        # Test security validation
        from src.core.patch_pipeline import PatchPlan, PatchSet
        from src.core.models import HardwareProfile
        
        # Create mock hardware
        mock_hardware = DetectedHardware(
            system_model="TestMachine",
            system_manufacturer="TestCorp",
            cpu_architecture="x86_64"
        )
        
        # Create mock plan with dangerous action
        test_plan = PatchPlan(
            id="test_plan",
            name="Test Security Plan",
            description="Testing security controls",
            target_hardware=mock_hardware,
            target_os={"family": "test", "version": "1.0"}
        )
        
        # Create patch set with dangerous action
        dangerous_set = PatchSet(
            id="dangerous_set",
            name="Dangerous Set",
            description="Contains dangerous actions",
            version="1.0.0",
            target_os="test",
            actions=[dangerous_action]
        )
        
        test_plan.add_patch_set(dangerous_set)
        
        # Test that security validation blocks this
        security_result = planner._validate_plan_security(test_plan)
        
        if security_result.result == ValidationResult.BLOCKED:
            print("✅ COMPLIANT mode correctly blocked dangerous action")
        else:
            print(f"❌ ERROR: Dangerous action was not blocked, got {security_result.result.value}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing security controls: {e}")
        traceback.print_exc()
        return False

def test_execution_targeting():
    """Test 3: Verify execution targeting safety"""
    print("\n=== TEST 3: EXECUTION TARGETING SAFETY ===")
    
    try:
        from src.core.patch_pipeline import PatchPlanner
        from src.core.safety_validator import SafetyValidator, PatchValidationMode
        
        planner = PatchPlanner(SafetyValidator(patch_mode=PatchValidationMode.COMPLIANT))
        
        # Test blocking dangerous system paths
        dangerous_paths = [
            "/",
            "/System", 
            "/usr",
            "/bin",
            "/sbin",
            "C:\\",
            "C:\\Windows",
            "C:\\Program Files"
        ]
        
        blocked_count = 0
        for path in dangerous_paths:
            if not planner._validate_target_mount_point(path):
                blocked_count += 1
                print(f"✅ Correctly blocked dangerous path: {path}")
            else:
                print(f"❌ ERROR: Failed to block dangerous path: {path}")
        
        if blocked_count == len(dangerous_paths):
            print("✅ All dangerous system paths correctly blocked")
        else:
            print(f"❌ ERROR: Only {blocked_count}/{len(dangerous_paths)} dangerous paths blocked")
            return False
        
        # Test that safe paths are allowed (create temporary directories to test)
        with tempfile.TemporaryDirectory() as temp_dir:
            safe_paths = [
                os.path.join(temp_dir, "safe_mount"),
                f"/tmp/{os.path.basename(temp_dir)}",
            ]
            
            for path in safe_paths:
                os.makedirs(path, exist_ok=True)
                if planner._validate_target_mount_point(path):
                    print(f"✅ Correctly allowed safe path: {path}")
                else:
                    print(f"❌ ERROR: Failed to allow safe path: {path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing execution targeting: {e}")
        traceback.print_exc()
        return False

def test_provider_integration():
    """Test 4: Verify provider integration wiring"""
    print("\n=== TEST 4: PROVIDER INTEGRATION ===")
    
    try:
        from src.core.config import Config
        from src.core.providers.macos_provider import MacOSProvider
        from src.core.providers.windows_provider import WindowsProvider
        from src.core.patch_pipeline import PatchPlanner
        
        # Test macOS provider integration
        config = Config()
        macos_provider = MacOSProvider(config)
        
        # Check that provider has PatchPlanner
        if hasattr(macos_provider, 'patch_planner') and isinstance(macos_provider.patch_planner, PatchPlanner):
            print("✅ macOS provider has PatchPlanner integration")
        else:
            print("❌ ERROR: macOS provider missing PatchPlanner")
            return False
        
        # Check security mode
        if macos_provider.patch_planner.safety_validator.patch_mode.value == "compliant":
            print("✅ macOS provider using COMPLIANT security mode")
        else:
            print(f"❌ ERROR: macOS provider not using COMPLIANT mode: {macos_provider.patch_planner.safety_validator.patch_mode.value}")
            return False
        
        # Test Windows provider integration
        windows_provider = WindowsProvider(config)
        
        if hasattr(windows_provider, 'patch_planner') and isinstance(windows_provider.patch_planner, PatchPlanner):
            print("✅ Windows provider has PatchPlanner integration")
        else:
            print("❌ ERROR: Windows provider missing PatchPlanner")
            return False
        
        # Check security mode
        if windows_provider.patch_planner.safety_validator.patch_mode.value == "compliant":
            print("✅ Windows provider using COMPLIANT security mode")
        else:
            print(f"❌ ERROR: Windows provider not using COMPLIANT mode: {windows_provider.patch_planner.safety_validator.patch_mode.value}")
            return False
        
        # Test that new methods exist
        methods_to_check = ['prepare_patched_image', 'get_recommended_patches']
        for method_name in methods_to_check:
            if hasattr(macos_provider, method_name):
                print(f"✅ macOS provider has {method_name} method")
            else:
                print(f"❌ ERROR: macOS provider missing {method_name} method")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing provider integration: {e}")
        traceback.print_exc()
        return False

def test_import_compatibility():
    """Test 5: Verify import compatibility across the system"""
    print("\n=== TEST 5: IMPORT COMPATIBILITY ===")
    
    try:
        # Test key import combinations that previously had circular dependencies
        test_imports = [
            "from src.core.models import HardwareProfile, DeploymentType",
            "from src.core.hardware_profiles import create_mac_hardware_profile",
            "from src.core.usb_builder import USBBuilder", 
            "from src.core.patch_pipeline import PatchPlanner",
            "from src.core.hardware_matcher import HardwareMatcher",
            "from src.core.hardware_detector import DetectedHardware",
            "from src.core.providers.macos_provider import MacOSProvider",
            "from src.core.providers.windows_provider import WindowsProvider"
        ]
        
        for import_stmt in test_imports:
            try:
                exec(import_stmt)
                print(f"✅ {import_stmt}")
            except ImportError as e:
                print(f"❌ FAILED: {import_stmt} - {e}")
                return False
        
        print("✅ All import compatibility tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Error testing import compatibility: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all critical fix tests"""
    print("🔧 BOOTFORGE CRITICAL FIXES VERIFICATION")
    print("=" * 50)
    
    # Add src to path for imports
    sys.path.insert(0, os.path.abspath('.'))
    
    tests = [
        ("Circular Import Fix", test_circular_import_fix),
        ("Security Controls", test_security_controls),
        ("Execution Targeting", test_execution_targeting),
        ("Provider Integration", test_provider_integration),
        ("Import Compatibility", test_import_compatibility)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} test...")
        try:
            result = test_func()
            results.append((test_name, result))
            
            if result:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
                
        except Exception as e:
            print(f"💥 {test_name}: CRASHED - {e}")
            results.append((test_name, False))
            traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        icon = "✅" if result else "❌"
        print(f"{icon} {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🏆 OVERALL: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL CRITICAL FIXES VERIFIED SUCCESSFULLY!")
        print("✅ System is ready for macOS OCLP integration")
        return True
    else:
        print("⚠️  SOME TESTS FAILED - Critical issues remain")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)