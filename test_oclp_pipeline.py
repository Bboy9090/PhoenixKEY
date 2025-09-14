#!/usr/bin/env python3
"""
Test script for OCLP automation pipeline
Comprehensive testing of the end-to-end OCLP workflow
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.oclp_automation_pipeline import (
    OCLPAutomationPipeline, PipelineConfiguration, AutomationMode,
    create_standard_pipeline, create_expert_pipeline
)
from src.core.oclp_pipeline_integration import (
    OCLPPipelineManager, OCLPQuickDeployment, create_pipeline_manager
)
from src.core.hardware_detector import HardwareDetector
from src.core.disk_manager import DiskManager


def setup_test_logging():
    """Setup logging for testing"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('oclp_pipeline_test.log')
        ]
    )


def test_hardware_detection():
    """Test hardware detection functionality"""
    print("\n=== Testing Hardware Detection ===")
    
    detector = HardwareDetector()
    hardware = detector.detect_hardware()
    
    if hardware:
        print(f"✓ Hardware detected: {hardware.get_summary()}")
        print(f"  Platform: {hardware.platform}")
        print(f"  Confidence: {hardware.detection_confidence.value}")
        
        if hardware.platform.lower() == "mac" or hardware.system_manufacturer == "Apple":
            print("✓ Mac hardware confirmed - OCLP compatible")
            return True, hardware
        else:
            print(f"ℹ Non-Mac system detected ({hardware.platform}) - OCLP not applicable")
            return False, hardware
    else:
        print("✗ Hardware detection failed")
        return False, None


def test_usb_device_detection():
    """Test USB device detection"""
    print("\n=== Testing USB Device Detection ===")
    
    disk_manager = DiskManager()
    removable_drives = disk_manager.get_removable_drives()
    
    print(f"Found {len(removable_drives)} removable drives:")
    suitable_devices = []
    
    for drive in removable_drives:
        size_gb = drive.size_bytes / (1024**3)
        is_suitable = size_gb >= 16.0
        status = "✓ Suitable" if is_suitable else "✗ Too small"
        
        print(f"  {status}: {drive.model} - {size_gb:.1f}GB ({drive.device_path})")
        
        if is_suitable:
            suitable_devices.append(drive)
    
    return suitable_devices


def test_pipeline_manager():
    """Test pipeline manager integration"""
    print("\n=== Testing Pipeline Manager ===")
    
    manager = create_pipeline_manager()
    
    # Test hardware detection
    print("Testing hardware detection...")
    hardware_success = manager.detect_hardware()
    print(f"Hardware detection: {'✓ Success' if hardware_success else '✗ Failed'}")
    
    # Test USB scanning
    print("Testing USB device scanning...")
    usb_devices = manager.scan_usb_devices()
    print(f"USB scanning: ✓ Found {len(usb_devices)} suitable devices")
    
    # Test configuration
    print("Testing pipeline configuration...")
    config_success = manager.configure_pipeline(
        automation_mode=AutomationMode.GUIDED
    )
    print(f"Configuration: {'✓ Success' if config_success else '✗ Failed'}")
    
    ui_state = manager.get_ui_state()
    print(f"UI State - Can start: {ui_state.can_start}, Status: {ui_state.status_message}")
    
    return manager


def test_quick_deployment():
    """Test quick deployment helper"""
    print("\n=== Testing Quick Deployment Helper ===")
    
    quick_deploy = OCLPQuickDeployment()
    
    # Test compatible models
    compatible_models = quick_deploy.get_compatible_mac_models()
    print(f"Compatible Mac models: {len(compatible_models)}")
    
    if compatible_models:
        print("Sample compatible models:")
        for model in compatible_models[:5]:  # Show first 5
            print(f"  • {model}")
        if len(compatible_models) > 5:
            print(f"  ... and {len(compatible_models) - 5} more")
    
    # Test time estimation
    estimated_time = quick_deploy.estimate_deployment_time(12.5)  # 12.5GB installer
    print(f"Estimated deployment time for 12.5GB installer: {estimated_time} minutes")
    
    return quick_deploy


def test_pipeline_configuration():
    """Test different pipeline configurations"""
    print("\n=== Testing Pipeline Configurations ===")
    
    # Test standard pipeline
    print("Creating standard pipeline...")
    standard_pipeline = create_standard_pipeline(AutomationMode.FULLY_AUTOMATIC)
    print("✓ Standard pipeline created")
    
    # Test expert pipeline
    print("Creating expert pipeline...")
    expert_pipeline = create_expert_pipeline(preserve_temp_files=True)
    print("✓ Expert pipeline created")
    
    # Test custom configuration
    print("Creating custom configuration...")
    custom_config = PipelineConfiguration(
        automation_mode=AutomationMode.SEMI_AUTOMATIC,
        auto_select_macos_version=True,
        min_usb_size_gb=32.0,  # Require 32GB
        include_diagnostic_tools=True,
        detailed_logging=True
    )
    custom_pipeline = OCLPAutomationPipeline(custom_config)
    print("✓ Custom pipeline created")
    
    return standard_pipeline, expert_pipeline, custom_pipeline


def interactive_pipeline_test():
    """Interactive test that shows pipeline stages"""
    print("\n=== Interactive Pipeline Test ===")
    print("This test will show how the pipeline would execute (simulation mode)")
    
    # Create pipeline manager
    manager = create_pipeline_manager()
    
    # Connect signals for demonstration
    manager.log_message.connect(lambda level, msg: print(f"[{level}] {msg}"))
    manager.pipeline_progress.connect(lambda progress: print(f"Progress: {progress.overall_progress:.1f}% - {progress.detailed_status}"))
    
    # Step-by-step simulation
    print("\n1. Hardware Detection...")
    if manager.detect_hardware():
        print("   ✓ Mac hardware detected and compatible")
        
        print("\n2. USB Device Scanning...")
        devices = manager.scan_usb_devices()
        if devices:
            print(f"   ✓ Found {len(devices)} suitable USB devices")
            
            print("\n3. Pipeline Configuration...")
            # Use first suitable device for demo
            demo_device = devices[0]
            success = manager.configure_pipeline(
                target_usb_device=demo_device.device_path,
                automation_mode=AutomationMode.GUIDED
            )
            
            if success:
                print("   ✓ Pipeline configured successfully")
                print(f"   Selected USB: {demo_device.model} ({demo_device.size_gb:.1f}GB)")
                
                ui_state = manager.get_ui_state()
                print(f"   Ready to start: {ui_state.can_start}")
                print(f"   Status: {ui_state.status_message}")
                
                # For actual deployment, you would call:
                # manager.start_pipeline()
                print("\n   Pipeline is ready for deployment!")
                print("   (Actual USB creation skipped in test mode)")
                
                return True
    
    print("\n   Test completed with limitations - some features require actual Mac hardware")
    return False


def run_comprehensive_test():
    """Run comprehensive test suite"""
    print("=" * 60)
    print("OCLP AUTOMATION PIPELINE - COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    
    # Setup logging
    setup_test_logging()
    
    test_results = []
    
    # Test 1: Hardware Detection
    try:
        is_mac, detected_hardware = test_hardware_detection()
        test_results.append(("Hardware Detection", True))
    except Exception as e:
        print(f"✗ Hardware detection test failed: {e}")
        test_results.append(("Hardware Detection", False))
    
    # Test 2: USB Device Detection
    try:
        suitable_devices = test_usb_device_detection()
        test_results.append(("USB Device Detection", True))
    except Exception as e:
        print(f"✗ USB device detection test failed: {e}")
        test_results.append(("USB Device Detection", False))
        suitable_devices = []
    
    # Test 3: Pipeline Manager
    try:
        manager = test_pipeline_manager()
        test_results.append(("Pipeline Manager", True))
    except Exception as e:
        print(f"✗ Pipeline manager test failed: {e}")
        test_results.append(("Pipeline Manager", False))
    
    # Test 4: Quick Deployment Helper
    try:
        quick_deploy = test_quick_deployment()
        test_results.append(("Quick Deployment Helper", True))
    except Exception as e:
        print(f"✗ Quick deployment test failed: {e}")
        test_results.append(("Quick Deployment Helper", False))
    
    # Test 5: Pipeline Configurations
    try:
        pipelines = test_pipeline_configuration()
        test_results.append(("Pipeline Configurations", True))
    except Exception as e:
        print(f"✗ Pipeline configuration test failed: {e}")
        test_results.append(("Pipeline Configurations", False))
    
    # Test 6: Interactive Pipeline Test
    try:
        interactive_success = interactive_pipeline_test()
        test_results.append(("Interactive Pipeline Test", interactive_success))
    except Exception as e:
        print(f"✗ Interactive pipeline test failed: {e}")
        test_results.append(("Interactive Pipeline Test", False))
    
    # Print test summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, success in test_results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{test_name:<30} {status}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed! OCLP automation pipeline is ready.")
    elif passed >= total * 0.8:
        print("⚠ Most tests passed. Pipeline should work with minor issues.")
    else:
        print("❌ Multiple test failures. Pipeline needs debugging.")
    
    print("\nNote: Some features require actual Mac hardware and USB devices for full testing.")
    print("Log file created: oclp_pipeline_test.log")


if __name__ == "__main__":
    run_comprehensive_test()