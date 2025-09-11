"""
BootForge CLI Interface
Command-line interface for BootForge operations
"""

import click
import logging
import sys
from pathlib import Path
from typing import List, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import Config
from src.core.logger import setup_logging
from src.core.disk_manager import DiskManager
from src.core.system_monitor import SystemMonitor
from src.plugins.plugin_manager import PluginManager


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
    ctx.obj['plugin_manager'] = PluginManager(ctx.obj['config'])
    
    click.echo("BootForge CLI v1.0.0")
    if verbose:
        click.echo("Verbose mode enabled")


@cli.command()
@click.pass_context
def list_devices(ctx):
    """List available USB devices"""
    disk_manager = ctx.obj['disk_manager']
    
    click.echo("Scanning for USB devices...")
    devices = disk_manager.get_removable_drives()
    
    if not devices:
        click.echo("No USB devices found.")
        return
    
    click.echo(f"Found {len(devices)} USB device(s):")
    click.echo()
    
    for i, device in enumerate(devices, 1):
        size_gb = device.size_bytes / (1024**3)
        click.echo(f"{i}. {device.name}")
        click.echo(f"   Path: {device.path}")
        click.echo(f"   Size: {size_gb:.1f} GB")
        click.echo(f"   Filesystem: {device.filesystem}")
        click.echo(f"   Vendor: {device.vendor} {device.model}")
        click.echo(f"   Health: {device.health_status}")
        click.echo()


@cli.command()
@click.option('--image', '-i', required=True, help='Path to OS image file')
@click.option('--device', '-d', required=True, help='Target device path')
@click.option('--verify/--no-verify', default=True, help='Verify written data')
@click.option('--force', is_flag=True, help='Force operation without confirmation')
@click.pass_context
def write_image(ctx, image, device, verify, force):
    """Write OS image to USB device"""
    disk_manager = ctx.obj['disk_manager']
    
    # Validate image file
    image_path = Path(image)
    if not image_path.exists():
        click.echo(f"Error: Image file not found: {image}", err=True)
        sys.exit(1)
    
    # Validate device
    device_path = Path(device)
    if not device_path.exists():
        click.echo(f"Error: Device not found: {device}", err=True)
        sys.exit(1)
    
    # Get device info
    devices = disk_manager.get_removable_drives()
    target_device = None
    for dev in devices:
        if dev.path == device:
            target_device = dev
            break
    
    if not target_device:
        click.echo(f"Error: {device} is not a removable USB device", err=True)
        sys.exit(1)
    
    # Show operation details
    size_mb = image_path.stat().st_size / (1024 * 1024)
    device_size_gb = target_device.size_bytes / (1024**3)
    
    click.echo("Operation Details:")
    click.echo(f"  Image: {image_path.name} ({size_mb:.1f} MB)")
    click.echo(f"  Target: {target_device.name} ({device_size_gb:.1f} GB)")
    click.echo(f"  Device: {device}")
    click.echo(f"  Verify: {'Yes' if verify else 'No'}")
    click.echo()
    
    # Warning
    click.echo("⚠️  WARNING: This will PERMANENTLY ERASE all data on the target device!")
    click.echo()
    
    # Confirmation
    if not force:
        if not click.confirm("Are you sure you want to continue?"):
            click.echo("Operation cancelled.")
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
@click.pass_context
def format_device(ctx, device, filesystem, force):
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
    
    # Warning
    click.echo(f"⚠️  WARNING: This will ERASE all data on {device}!")
    click.echo(f"Filesystem: {filesystem.upper()}")
    click.echo()
    
    # Confirmation
    if not force:
        if not click.confirm("Are you sure you want to continue?"):
            click.echo("Operation cancelled.")
            sys.exit(0)
    
    # Format device
    click.echo(f"Formatting {device} as {filesystem.upper()}...")
    
    try:
        success = disk_manager.format_device(device, filesystem)
        
        if success:
            click.echo("✅ Format completed successfully!")
        else:
            click.echo("❌ Format failed!", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Format failed: {e}", err=True)
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