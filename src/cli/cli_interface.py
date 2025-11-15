"""
BootForge CLI Interface
Command-line interface for BootForge operations
"""

import click
import logging
import sys
import time
from pathlib import Path
from typing import List, Optional

# Import colorama for cross-platform colored output
try:
    from colorama import init, Fore, Back, Style
    init()  # Initialize colorama
    HAS_COLOR = True
except ImportError:
    # Fallback when colorama not available
    class MockColor:
        def __getattr__(self, name):
            return ""
    Fore = Back = Style = MockColor()
    HAS_COLOR = False

# Path already set by main.py entrypoint

from src.core.config import Config
from src.core.logger import setup_logging
from src.core.disk_manager import DiskManager
from src.core.system_monitor import SystemMonitor
from src.core.safety_validator import SafetyValidator, SafetyLevel, ValidationResult
from src.plugins.plugin_manager import PluginManager
from src.utils.doc_builder import PhoenixDocsBuilder


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--config', '-c', help='Configuration file path')
@click.pass_context
def cli(ctx, verbose, config):
    """BootForge - Professional Cross-Platform OS Deployment Tool"""
    # Setup logging
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(level=log_level)
    
    # Initialize configuration
    ctx.ensure_object(dict)
    ctx.obj['config'] = Config(config)
    ctx.obj['disk_manager'] = DiskManager()
    ctx.obj['safety_validator'] = SafetyValidator(SafetyLevel.STANDARD)
    ctx.obj['plugin_manager'] = PluginManager(ctx.obj['config'])
    
    # Professional banner
    click.echo(f"{Fore.CYAN}┌─────────────────────────────────────────┐{Style.RESET_ALL}")
    click.echo(f"{Fore.CYAN}│{Style.RESET_ALL} {Fore.BLUE}{Style.BRIGHT}BootForge CLI v1.0.0{Style.RESET_ALL}                 {Fore.CYAN}│{Style.RESET_ALL}")
    click.echo(f"{Fore.CYAN}│{Style.RESET_ALL} Professional OS Deployment Tool      {Fore.CYAN}│{Style.RESET_ALL}")
    click.echo(f"{Fore.CYAN}└─────────────────────────────────────────┘{Style.RESET_ALL}")
    
    if verbose:
        click.echo(f"{Fore.YELLOW}🔍 Verbose mode enabled{Style.RESET_ALL}")


@cli.command()
@click.pass_context
def list_devices(ctx):
    """List available USB devices"""
    disk_manager = ctx.obj['disk_manager']
    
    click.echo(f"{Fore.BLUE}🔍 Scanning for USB devices...{Style.RESET_ALL}")
    
    # Add a small animation for better UX
    for i in range(3):
        click.echo(f"   {'.' * (i + 1)}", nl=False)
        time.sleep(0.3)
        click.echo("\r   ", nl=False)
    click.echo("\r")
    
    devices = disk_manager.get_removable_drives()
    
    if not devices:
        click.echo(f"{Fore.YELLOW}⚠️  No USB devices found.{Style.RESET_ALL}")
        click.echo(f"{Fore.CYAN}💡 Make sure USB devices are connected and properly mounted.{Style.RESET_ALL}")
        return
    
    click.echo(f"{Fore.GREEN}✅ Found {len(devices)} USB device(s):{Style.RESET_ALL}")
    click.echo(f"{Fore.CYAN}{'─' * 60}{Style.RESET_ALL}")
    
    for i, device in enumerate(devices, 1):
        size_gb = device.size_bytes / (1024**3)
        
        # Color-code health status
        health_color = Fore.GREEN if device.health_status == "Good" else Fore.YELLOW
        
        click.echo(f"{Style.BRIGHT}{i}. {device.name}{Style.RESET_ALL}")
        click.echo(f"   📁 Path: {Fore.WHITE}{device.path}{Style.RESET_ALL}")
        click.echo(f"   💾 Size: {Fore.WHITE}{size_gb:.1f} GB{Style.RESET_ALL}")
        click.echo(f"   🗂️  Filesystem: {Fore.WHITE}{device.filesystem}{Style.RESET_ALL}")
        click.echo(f"   🏭 Vendor: {Fore.WHITE}{device.vendor} {device.model}{Style.RESET_ALL}")
        click.echo(f"   ❤️  Health: {health_color}{device.health_status}{Style.RESET_ALL}")
        click.echo()


@cli.command()
@click.option('--image', '-i', required=True, help='Path to OS image file')
@click.option('--device', '-d', required=True, help='Target device path')
@click.option('--verify/--no-verify', default=True, help='Verify written data')
@click.option('--force', is_flag=True, help='Force operation without confirmation')
@click.option('--dry-run', is_flag=True, help='Show what would be done without actually doing it')
@click.pass_context
def write_image(ctx, image, device, verify, force, dry_run):
    """Write OS image to USB device with comprehensive safety validation"""
    safety_validator = ctx.obj['safety_validator']
    disk_manager = ctx.obj['disk_manager']
    
    click.echo(f"{Fore.BLUE}🔍 Starting comprehensive safety validation...{Style.RESET_ALL}")
    
    # CRITICAL: Comprehensive Device Safety Validation
    device_risk = safety_validator.validate_device_safety(device)
    
    if device_risk.overall_risk == ValidationResult.BLOCKED:
        click.echo(f"{Fore.RED}{Style.BRIGHT}🚫 OPERATION BLOCKED FOR SAFETY 🚫{Style.RESET_ALL}")
        click.echo(f"{Fore.RED}Device: {device}{Style.RESET_ALL}")
        click.echo(f"{Fore.RED}Size: {device_risk.size_gb:.1f}GB{Style.RESET_ALL}")
        click.echo(f"{Fore.RED}Risk Factors:{Style.RESET_ALL}")
        for factor in device_risk.risk_factors:
            click.echo(f"{Fore.RED}  • {factor}{Style.RESET_ALL}")
        click.echo(f"{Fore.RED}This device is not safe to use for USB creation.{Style.RESET_ALL}")
        sys.exit(1)
    
    if device_risk.overall_risk == ValidationResult.DANGEROUS:
        click.echo(f"{Fore.RED}{Style.BRIGHT}⚠️ DANGEROUS DEVICE DETECTED ⚠️{Style.RESET_ALL}")
        click.echo(f"{Fore.RED}Device: {device} ({device_risk.size_gb:.1f}GB){Style.RESET_ALL}")
        click.echo(f"{Fore.RED}Risk Factors:{Style.RESET_ALL}")
        for factor in device_risk.risk_factors:
            click.echo(f"{Fore.RED}  • {factor}{Style.RESET_ALL}")
        click.echo(f"{Fore.RED}This operation could destroy important data.{Style.RESET_ALL}")
        sys.exit(1)
    
    # Validate prerequisites
    prereq_checks = safety_validator.validate_prerequisites()
    blocked_checks = [check for check in prereq_checks if check.result == ValidationResult.BLOCKED]
    if blocked_checks:
        click.echo(f"{Fore.RED}❌ MISSING PREREQUISITES:{Style.RESET_ALL}")
        for check in blocked_checks:
            click.echo(f"{Fore.RED}  • {check.name}: {check.message}{Style.RESET_ALL}")
        sys.exit(1)
    
    # Validate source files
    source_files = {'image': image}
    source_checks = safety_validator.validate_source_files(source_files)
    blocked_sources = [check for check in source_checks if check.result == ValidationResult.BLOCKED]
    if blocked_sources:
        click.echo(f"{Fore.RED}❌ SOURCE FILE ISSUES:{Style.RESET_ALL}")
        for check in blocked_sources:
            click.echo(f"{Fore.RED}  • {check.name}: {check.message}{Style.RESET_ALL}")
        sys.exit(1)
    
    click.echo(f"{Fore.GREEN}✅ All safety validations passed{Style.RESET_ALL}")
    
    # Get image info for summary
    image_path = Path(image)
    size_mb = image_path.stat().st_size / (1024 * 1024)
    
    # Get device info for detailed display
    devices = disk_manager.get_removable_drives()
    target_device = None
    for dev in devices:
        if dev.path == device:
            target_device = dev
            break
    
    # Show detailed operation summary  
    device_size_gb = device_risk.size_gb
    
    click.echo(f"{Fore.CYAN}{'═' * 60}{Style.RESET_ALL}")
    click.echo(f"{Fore.YELLOW}{Style.BRIGHT}📋 OPERATION SUMMARY{Style.RESET_ALL}")
    click.echo(f"{Fore.CYAN}{'═' * 60}{Style.RESET_ALL}")
    click.echo(f"  📁 Image File: {Fore.WHITE}{image_path.name}{Style.RESET_ALL} ({size_mb:.1f} MB)")
    click.echo(f"  🗂️  Full Path: {Fore.WHITE}{image_path}{Style.RESET_ALL}")
    click.echo(f"  🎯 Target Device: {Fore.WHITE}{target_device.name if target_device else 'Unknown'}{Style.RESET_ALL} ({device_size_gb:.1f} GB)")
    click.echo(f"  🛡️ Device Safety: {Fore.WHITE}{device_risk.overall_risk.value.upper()}{Style.RESET_ALL}")
    click.echo(f"  📱 Removable: {Fore.WHITE}{'Yes' if device_risk.is_removable else 'No'}{Style.RESET_ALL}")
    click.echo(f"  📍 Device Path: {Fore.WHITE}{device}{Style.RESET_ALL}")
    click.echo(f"  ✅ Verification: {Fore.WHITE}{'Enabled' if verify else 'Disabled'}{Style.RESET_ALL}")
    if dry_run:
        click.echo(f"  🔍 Mode: {Fore.BLUE}DRY RUN (no actual changes){Style.RESET_ALL}")
    click.echo(f"{Fore.CYAN}{'═' * 60}{Style.RESET_ALL}")
    click.echo()
    
    # Multi-step safety confirmation
    if not force:
        # First warning
        click.echo(f"{Fore.RED}{Style.BRIGHT}⚠️  CRITICAL WARNING ⚠️{Style.RESET_ALL}")
        click.echo(f"{Fore.RED}This operation will PERMANENTLY and IRREVERSIBLY ERASE ALL DATA{Style.RESET_ALL}")
        click.echo(f"{Fore.RED}on the target device: {target_device.name if target_device else 'Unknown'} ({device}){Style.RESET_ALL}")
        click.echo()
        
        # First confirmation
        if not click.confirm(f"{Fore.YELLOW}Do you understand that all data will be lost?{Style.RESET_ALL}"):
            click.echo(f"{Fore.GREEN}✅ Operation cancelled for safety.{Style.RESET_ALL}")
            sys.exit(0)
        
        click.echo()
        # Second confirmation - require typing device path
        click.echo(f"{Fore.RED}{Style.BRIGHT}🔒 FINAL SAFETY CHECK{Style.RESET_ALL}")
        click.echo(f"To proceed, type the {Style.BRIGHT}exact device path{Style.RESET_ALL}: {Fore.WHITE}{device}{Style.RESET_ALL}")
        
        confirmation_input = click.prompt(f"{Fore.YELLOW}Enter device path to confirm{Style.RESET_ALL}", type=str)
        
        if confirmation_input != device:
            click.echo(f"{Fore.RED}❌ Device path mismatch. Operation cancelled for safety.{Style.RESET_ALL}")
            click.echo(f"   Expected: {device}")
            click.echo(f"   Entered: {confirmation_input}")
            sys.exit(0)
        
        click.echo(f"{Fore.GREEN}✅ Device path confirmed.{Style.RESET_ALL}")
        click.echo()
    
    if dry_run:
        click.echo(f"{Fore.BLUE}🔍 DRY RUN: Would write {image_path.name} to {device}{Style.RESET_ALL}")
        click.echo(f"{Fore.BLUE}🔍 DRY RUN: Would verify data: {'Yes' if verify else 'No'}{Style.RESET_ALL}")
        click.echo(f"{Fore.GREEN}✅ Dry run completed. No actual changes made.{Style.RESET_ALL}")
        sys.exit(0)
    
    # Start write operation
    click.echo("Starting write operation...")
    
    # Create progress callback
    def progress_callback(progress):
        percentage = progress.percentage
        speed = progress.speed_mbps
        eta = progress.eta_seconds
        
        eta_min = eta // 60
        eta_sec = eta % 60
        
        click.echo(f"Progress: {percentage:.1f}% | Speed: {speed:.1f} MB/s | ETA: {eta_min:02d}:{eta_sec:02d}")
    
    try:
        writer = disk_manager.write_image_to_device(
            str(image_path), device, verify, progress_callback
        )
        
        # Wait for completion
        writer.wait()
        
        click.echo("✅ Operation completed successfully!")
        
    except Exception as e:
        click.echo(f"❌ Operation failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--device', '-d', required=True, help='Device to diagnose')
@click.pass_context
def diagnose(ctx, device):
    """Run diagnostics on USB device"""
    plugin_manager = ctx.obj['plugin_manager']
    
    # Load diagnostics plugin
    plugin_manager.discover_plugins()
    if not plugin_manager.load_plugin("Diagnostics"):
        click.echo("Error: Could not load diagnostics plugin", err=True)
        sys.exit(1)
    
    click.echo(f"Running diagnostics on {device}...")
    
    # Run full diagnostics
    results = plugin_manager.execute_plugin(
        "Diagnostics",
        operation="full_check",
        device_path=device
    )
    
    if not results:
        click.echo("Error: Diagnostics failed", err=True)
        sys.exit(1)
    
    # Display results
    click.echo()
    click.echo("=== DIAGNOSTIC RESULTS ===")
    click.echo()
    
    # Device info
    device_info = results['checks']['device_info']
    click.echo("Device Information:")
    click.echo(f"  Path: {device_info['path']}")
    click.echo(f"  Size: {device_info['size_bytes'] / (1024**3):.1f} GB")
    click.echo(f"  Model: {device_info['model']}")
    click.echo(f"  Vendor: {device_info['vendor']}")
    click.echo(f"  Readable: {'Yes' if device_info['readable'] else 'No'}")
    click.echo(f"  Writable: {'Yes' if device_info['writable'] else 'No'}")
    click.echo()
    
    # Speed test
    speed_test = results['checks']['speed_test']
    click.echo("Speed Test:")
    click.echo(f"  Read Speed: {speed_test['read_speed_mbps']:.1f} MB/s")
    click.echo(f"  Write Speed: {speed_test['write_speed_mbps']:.1f} MB/s")
    if speed_test['errors']:
        click.echo("  Errors:")
        for error in speed_test['errors']:
            click.echo(f"    - {error}")
    click.echo()
    
    # Bad sectors
    bad_sectors = results['checks']['bad_sectors']
    click.echo("Bad Sectors:")
    click.echo(f"  Bad Sectors: {bad_sectors['bad_sectors']}")
    click.echo(f"  Scan Completed: {'Yes' if bad_sectors['scan_completed'] else 'No'}")
    if bad_sectors['errors']:
        click.echo("  Errors:")
        for error in bad_sectors['errors']:
            click.echo(f"    - {error}")
    click.echo()
    
    # Filesystem
    filesystem = results['checks']['filesystem']
    click.echo("Filesystem:")
    click.echo(f"  Type: {filesystem['filesystem_type']}")
    click.echo(f"  Health: {filesystem['health']}")
    if filesystem['errors']:
        click.echo("  Errors:")
        for error in filesystem['errors']:
            click.echo(f"    - {error}")
    if filesystem['warnings']:
        click.echo("  Warnings:")
        for warning in filesystem['warnings']:
            click.echo(f"    - {warning}")
    click.echo()
    
    # Overall health
    click.echo(f"Overall Health Score: {results['health_score']}/100")
    click.echo()
    
    # Recommendations
    click.echo("Recommendations:")
    for rec in results['recommendations']:
        click.echo(f"  • {rec}")


@cli.command()
@click.pass_context
def list_plugins(ctx):
    """List available plugins"""
    plugin_manager = ctx.obj['plugin_manager']
    
    # Discover plugins
    plugins = plugin_manager.discover_plugins()
    
    if not plugins:
        click.echo("No plugins found.")
        return
    
    click.echo(f"Found {len(plugins)} plugin(s):")
    click.echo()
    
    for plugin in plugins:
        status = "✅ Loaded" if plugin.name in plugin_manager.get_loaded_plugins() else "⏸️ Available"
        click.echo(f"{plugin.name} v{plugin.version} - {status}")
        click.echo(f"  Description: {plugin.description}")
        click.echo(f"  Author: {plugin.author}")
        if plugin.dependencies:
            click.echo(f"  Dependencies: {', '.join(plugin.dependencies)}")
        click.echo()


@cli.command()
@click.option('--device', '-d', help='Device to format')
@click.option('--filesystem', '-f', default='fat32', 
              type=click.Choice(['fat32', 'ntfs', 'ext4']),
              help='Filesystem type')
@click.option('--force', is_flag=True, help='Force operation without confirmation')
@click.option('--dry-run', is_flag=True, help='Show what would be done without actually doing it')
@click.pass_context
def format_device(ctx, device, filesystem, force, dry_run):
    """Format USB device"""
    disk_manager = ctx.obj['disk_manager']
    
    if not device:
        # List devices and let user choose
        devices = disk_manager.get_removable_drives()
        if not devices:
            click.echo("No USB devices found.")
            sys.exit(1)
        
        click.echo("Available devices:")
        for i, dev in enumerate(devices, 1):
            size_gb = dev.size_bytes / (1024**3)
            click.echo(f"{i}. {dev.name} - {dev.path} ({size_gb:.1f} GB)")
        
        choice = click.prompt("Select device number", type=int)
        if choice < 1 or choice > len(devices):
            click.echo("Invalid selection.")
            sys.exit(1)
        
        device = devices[choice - 1].path
    
    # Validate device
    if not Path(device).exists():
        click.echo(f"Error: Device not found: {device}", err=True)
        sys.exit(1)
    
    # Get device info for summary
    devices = disk_manager.get_removable_drives()
    target_device = None
    for dev in devices:
        if dev.path == device:
            target_device = dev
            break
    
    device_size_gb = target_device.size_bytes / (1024**3) if target_device else 0
    
    # Show detailed operation summary
    click.echo(f"{Fore.CYAN}{'═' * 60}{Style.RESET_ALL}")
    click.echo(f"{Fore.YELLOW}{Style.BRIGHT}📋 FORMAT OPERATION SUMMARY{Style.RESET_ALL}")
    click.echo(f"{Fore.CYAN}{'═' * 60}{Style.RESET_ALL}")
    click.echo(f"  🎯 Target Device: {Fore.WHITE}{target_device.name if target_device else 'Unknown'}{Style.RESET_ALL} ({device_size_gb:.1f} GB)")
    if target_device:
        click.echo(f"  🏭 Device Model: {Fore.WHITE}{target_device.vendor} {target_device.model}{Style.RESET_ALL}")
    click.echo(f"  📍 Device Path: {Fore.WHITE}{device}{Style.RESET_ALL}")
    click.echo(f"  💾 New Filesystem: {Fore.WHITE}{filesystem.upper()}{Style.RESET_ALL}")
    if dry_run:
        click.echo(f"  🔍 Mode: {Fore.BLUE}DRY RUN (no actual changes){Style.RESET_ALL}")
    click.echo(f"{Fore.CYAN}{'═' * 60}{Style.RESET_ALL}")
    click.echo()
    
    # Multi-step safety confirmation
    if not force:
        # First warning
        click.echo(f"{Fore.RED}{Style.BRIGHT}⚠️  CRITICAL WARNING ⚠️{Style.RESET_ALL}")
        click.echo(f"{Fore.RED}This operation will PERMANENTLY and IRREVERSIBLY ERASE ALL DATA{Style.RESET_ALL}")
        click.echo(f"{Fore.RED}on device: {device}{Style.RESET_ALL}")
        click.echo()
        
        # First confirmation
        if not click.confirm(f"{Fore.YELLOW}Do you understand that all data will be lost?{Style.RESET_ALL}"):
            click.echo(f"{Fore.GREEN}✅ Operation cancelled for safety.{Style.RESET_ALL}")
            sys.exit(0)
        
        click.echo()
        # Second confirmation - require typing "ERASE"
        click.echo(f"{Fore.RED}{Style.BRIGHT}🔒 FINAL SAFETY CHECK{Style.RESET_ALL}")
        click.echo(f"To proceed with formatting, type: {Style.BRIGHT}ERASE{Style.RESET_ALL}")
        
        confirmation_input = click.prompt(f"{Fore.YELLOW}Type ERASE to confirm{Style.RESET_ALL}", type=str)
        
        if confirmation_input != "ERASE":
            click.echo(f"{Fore.RED}❌ Confirmation failed. Operation cancelled for safety.{Style.RESET_ALL}")
            click.echo(f"   Expected: ERASE")
            click.echo(f"   Entered: {confirmation_input}")
            sys.exit(0)
        
        click.echo(f"{Fore.GREEN}✅ Format confirmation received.{Style.RESET_ALL}")
        click.echo()
    
    if dry_run:
        click.echo(f"{Fore.BLUE}🔍 DRY RUN: Would format {device} as {filesystem.upper()}{Style.RESET_ALL}")
        click.echo(f"{Fore.GREEN}✅ Dry run completed. No actual changes made.{Style.RESET_ALL}")
        sys.exit(0)
    
    # Format device
    click.echo(f"{Fore.BLUE}🔄 Formatting {device} as {filesystem.upper()}...{Style.RESET_ALL}")
    
    try:
        success = disk_manager.format_device(device, filesystem)
        
        if success:
            click.echo(f"{Fore.GREEN}✅ Format completed successfully!{Style.RESET_ALL}")
        else:
            click.echo(f"{Fore.RED}❌ Format failed!{Style.RESET_ALL}", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"{Fore.RED}❌ Format failed: {e}{Style.RESET_ALL}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def system_info(ctx):
    """Show system information"""
    click.echo("Gathering system information...")
    
    # Create temporary system monitor
    import time
    from src.core.system_monitor import SystemMonitor
    
    # This would need to be adapted for CLI use
    click.echo("System information gathering is currently only available in GUI mode.")
    click.echo("For basic system info, use standard tools like 'lscpu', 'free', 'lsblk'.")


if __name__ == '__main__':
    cli()
@cli.command(name="build-phoenix-docs")
@click.option(
    "--source",
    default="docs/phoenix_docs",
    show_default=True,
    help="Path to the PhoenixDocs Markdown directory",
)
@click.option(
    "--output",
    default="dist/phoenix_docs_html",
    show_default=True,
    help="Destination directory for generated HTML",
)
@click.option(
    "--version",
    default="1.0.0",
    show_default=True,
    help="Version stamp to embed in generated documentation",
)
def build_phoenix_docs(source: str, output: str, version: str):
    """Render PhoenixDocs Markdown into offline HTML."""

    click.echo(f"{Fore.BLUE}🛠  Building PhoenixDocs offline library...{Style.RESET_ALL}")
    builder = PhoenixDocsBuilder(source, output, build_version=version)

    try:
        manifest = builder.build()
    except FileNotFoundError as exc:
        click.echo(f"{Fore.RED}❌ {exc}{Style.RESET_ALL}")
        sys.exit(1)

    doc_count = len(manifest.get("documents", []))
    click.echo(
        f"{Fore.GREEN}✅ Generated {doc_count} document(s) into {output}{Style.RESET_ALL}"
    )
    click.echo(f"{Fore.CYAN}📄 Manifest: phoenix_docs_manifest.json{Style.RESET_ALL}")
