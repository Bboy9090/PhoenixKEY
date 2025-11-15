# BootForge - Professional Cross-Platform OS Deployment Tool

BootForge is a comprehensive, professional-grade tool for creating bootable USB drives for macOS, Windows, and Linux operating systems. It features a modular plugin architecture, advanced system monitoring, and support for both GUI and CLI interfaces.

> **Looking for the Phoenix Key master plan?** Read the [BootForge Phoenix Key — Legendary Forge Blueprint](docs/phoenix_key_legendary_blueprint.md) for the full multi-platform recovery vision, product pillars, and implementation roadmap.

### Phoenix Key Brand Assets

* Explore the [Phoenix Key Brand Guide](docs/phoenix_brand/brand_guide.md) for color palettes, typography, and usage rules.
* Source-ready SVGs live under [`assets/logo/`](assets/logo/) and include badge, wordmark, and monochrome variants tuned for UI, packaging, and engraving workflows.


## Features

### Core Functionality
- **Cross-Platform Support**: Works on Windows, macOS, and Linux
- **Multiple OS Support**: Create bootable drives for macOS, Windows, and Linux
- **USB Drive Detection**: Automatic detection and health checking of USB devices
- **Image Writing**: Fast, reliable image writing with verification
- **Progress Monitoring**: Real-time progress tracking with speed and ETA

### Advanced Features
- **Plugin System**: Modular architecture with extensible plugins
- **Driver Injection**: Inject Windows drivers and macOS kexts into images
- **System Monitoring**: Real-time CPU, memory, and thermal monitoring
- **Diagnostics**: Comprehensive USB drive health checking
- **Resume Support**: Resume interrupted write operations
- **Multi-Drive**: Support for writing to multiple drives simultaneously

### Professional Tools
- **Checkra1n Integration**: iOS jailbreak workflow support
- **EFI/UEFI Support**: Advanced boot configuration
- **Serial Modification**: Hardware identification management
- **Cloud Offload**: Handle large images with limited local storage
- **Thermal Protection**: Automatic pause on system overheating

## Installation

### Prerequisites
- Python 3.11 or higher
- Administrative/root privileges for disk operations

### From Source
```bash
# Clone the repository
git clone https://github.com/bootforge/bootforge.git
cd bootforge

# Install dependencies
pip install -r requirements.txt

# Run BootForge
python main.py --help
```

### Binary Releases
Download pre-built binaries from the [Releases](https://github.com/bootforge/bootforge/releases) page:
- **Windows**: `BootForge-Setup.exe`
- **macOS**: `BootForge-1.0.0.dmg`
- **Linux**: `BootForge-1.0.0-x86_64.AppImage`

## Usage

### CLI Interface (Recommended)
BootForge includes a comprehensive CLI interface for all operations:

```bash
# List available USB devices
python main.py list-devices

# Write OS image to USB device
python main.py write-image -i /path/to/image.iso -d /dev/sdb

# Run diagnostics on USB device
python main.py diagnose -d /dev/sdb

# Format USB device
python main.py format-device -d /dev/sdb -f fat32

# List available plugins
python main.py list-plugins

# Get help
python main.py --help
```

### GUI Interface
For desktop environments with OpenGL support:

```bash
# Launch GUI (requires PyQt6 and OpenGL)
python main.py --gui
```

### PhoenixDocs Offline Library
Generate the themed PhoenixDocs knowledge base for offline use and the Phoenix Web GUI:

```bash
python main.py build-phoenix-docs --output dist/phoenix_docs_html
```

The command renders every Markdown guide in `docs/phoenix_docs/`, produces HTML artefacts, and writes a manifest (`phoenix_docs_manifest.json`) consumed by the Phoenix Key web interface.

## Plugin System

BootForge features a modular plugin architecture with built-in plugins:

### Driver Injector Plugin
Inject drivers and kexts into OS images:
- Windows `.sys` and `.inf` files
- macOS `.kext` and `.dext` bundles
- Automatic registry/cache updates

### Diagnostics Plugin
Comprehensive USB drive health checking:
- Bad sector scanning
- Filesystem integrity checks
- SMART data analysis
- Performance benchmarking

### Checkra1n Integration Plugin
iOS jailbreak workflow support:
- Device compatibility checking
- Automated jailbreak process
- Bypass workflow management

## Configuration

BootForge stores configuration in `~/.bootforge/`:
- `config.json`: Main configuration file
- `logs/`: Application logs
- `plugins/`: User plugins directory
- `drivers/`: Driver storage directory

### Configuration Options
```json
{
  "log_level": "INFO",
  "temp_dir": "/tmp/bootforge",
  "max_concurrent_writes": 2,
  "thermal_threshold": 85.0,
  "auto_update_check": true,
  "plugin_directories": ["plugins"]
}
```

## Development

### Project Structure
```
bootforge/
├── main.py                 # Main application entry point
├── src/
│   ├── core/              # Core system components
│   │   ├── config.py      # Configuration management
│   │   ├── logger.py      # Logging system
│   │   ├── system_monitor.py  # System monitoring
│   │   └── disk_manager.py    # Disk operations
│   ├── gui/               # PyQt6 GUI components
│   │   ├── main_window.py # Main window
│   │   ├── wizard_widget.py  # Operation wizard
│   │   └── status_widget.py  # Status display
│   ├── cli/               # CLI interface
│   │   └── cli_interface.py  # Click-based CLI
│   ├── plugins/           # Plugin system
│   │   ├── plugin_manager.py # Plugin management
│   │   ├── driver_injector.py # Driver injection
│   │   ├── checkra1n_integration.py # iOS tools
│   │   └── diagnostics.py     # USB diagnostics
│   └── installers/        # Packaging scripts
│       └── build_installer.py # Cross-platform builds
├── tests/                 # Test suite
├── docs/                  # Documentation
└── assets/                # Resources and assets
```

### Building Installers
```bash
# Build platform-specific installer
python src/installers/build_installer.py

# Manual PyInstaller build
pyinstaller --onefile --name=BootForge main.py
```

### Running Tests
```bash
# Run test suite
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=src
```

## Platform-Specific Notes

### Linux
- Requires `sudo` for disk operations
- Install `badblocks`, `e2fsprogs`, `dosfstools` for full functionality
- USB device paths: `/dev/sdX`

### macOS
- Requires `sudo` for disk operations
- Uses built-in `diskutil` for disk management
- USB device paths: `/dev/diskX`

### Windows
- Requires Administrator privileges
- Uses Windows format utilities
- USB device paths: `\\.\PhysicalDriveX`

## Security Considerations

⚠️ **WARNING**: BootForge performs destructive disk operations. Always:
- Verify target device before writing
- Backup important data
- Run with appropriate privileges only
- Use in controlled environments

### Safety Features
- Multi-step confirmation for destructive operations
- Device validation and removability checks
- Write verification and integrity checking
- Automatic privilege escalation prompts

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement changes with tests
4. Submit a pull request

### Plugin Development
Create custom plugins by extending `PluginBase`:

```python
from src.plugins.plugin_manager import PluginBase

class MyPlugin(PluginBase):
    def __init__(self):
        super().__init__()
        self.name = "MyPlugin"
        self.version = "1.0.0"
        self.description = "Custom plugin description"
    
    def initialize(self, config):
        # Plugin initialization
        return True
    
    def execute(self, *args, **kwargs):
        # Plugin execution
        return True
    
    def cleanup(self):
        # Plugin cleanup
        return True
```

## License

BootForge is released under the MIT License. See [LICENSE](LICENSE) for details.

## Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/bootforge/bootforge/issues)
- **Discussions**: [GitHub Discussions](https://github.com/bootforge/bootforge/discussions)

## Disclaimer

BootForge is provided "as is" without warranty. Users are responsible for data safety and proper usage. Always backup important data before performing disk operations.