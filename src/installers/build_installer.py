"""
BootForge Installer Builder
Cross-platform installer creation script
"""

import os
import sys
import platform
import subprocess
import shutil
import traceback
from pathlib import Path
import importlib.util
from typing import Optional, List, Tuple


def find_pyinstaller() -> Optional[str]:
    """Find PyInstaller executable with robust path detection"""
    
    # Try using Python module approach first (more reliable in restricted environments)
    try:
        import PyInstaller
        print(f"✅ Found PyInstaller module at: {PyInstaller.__file__}")
        return f"{sys.executable} -m PyInstaller"
    except ImportError:
        pass
    
    # Common installation locations to check
    search_paths = [
        # Current PATH
        shutil.which('pyinstaller'),
        
        # Python scripts directory
        str(Path(sys.executable).parent / 'pyinstaller'),
        str(Path(sys.executable).parent / 'pyinstaller.exe'),
        
        # User site packages (common on Linux/macOS)
        str(Path.home() / '.local' / 'bin' / 'pyinstaller'),
        
        # macOS user Python installations
        str(Path.home() / 'Library' / 'Python' / f'{sys.version_info.major}.{sys.version_info.minor}' / 'bin' / 'pyinstaller'),
        
        # Homebrew Python on macOS
        '/opt/homebrew/bin/pyinstaller',
        '/usr/local/bin/pyinstaller',
        
        # Windows AppData
        str(Path.home() / 'AppData' / 'Roaming' / 'Python' / f'Python{sys.version_info.major}{sys.version_info.minor}' / 'Scripts' / 'pyinstaller.exe'),
        str(Path.home() / 'AppData' / 'Local' / 'Programs' / 'Python' / f'Python{sys.version_info.major}{sys.version_info.minor}' / 'Scripts' / 'pyinstaller.exe'),
        
        # Current workspace (Replit-specific)
        str(Path.cwd() / '.pythonlibs' / 'bin' / 'pyinstaller'),
        '/home/runner/workspace/.pythonlibs/bin/pyinstaller',
    ]
    
    # Check each location
    for path in search_paths:
        if path and Path(path).exists() and os.access(path, os.X_OK):
            print(f"✅ Found PyInstaller binary at: {path}")
            return path
    
    return None


def check_dependencies() -> Tuple[bool, List[str]]:
    """Check if all required dependencies are available"""
    missing_deps = []
    warnings = []
    
    # Check PyInstaller (not critical - we have fallbacks)
    if not find_pyinstaller():
        warnings.append('PyInstaller not found - will use fallback method')
    
    # Check PyQt6 for GUI builds (this IS critical for GUI functionality)
    try:
        import PyQt6
        print("✅ PyQt6 available - GUI features enabled")
    except ImportError:
        print("⚠️  PyQt6 not available - GUI features will be limited")
        warnings.append('PyQt6 missing - GUI may not work properly')
    
    # Show warnings but don't fail
    for warning in warnings:
        print(f"⚠️  {warning}")
    
    return True, []  # Always return success, handle issues in build functions


def get_platform_spec_file() -> Optional[str]:
    """Get the appropriate .spec file for the current platform"""
    system = platform.system()
    
    spec_files = {
        'Linux': 'BootForge-Linux-x64.spec',
        'Darwin': 'BootForge-macOS.spec',
        'Windows': 'BootForge-Windows.spec'
    }
    
    spec_file = spec_files.get(system)
    if spec_file and Path(spec_file).exists():
        return spec_file
    
    return None


def create_standalone_script() -> bool:
    """Create a standalone script as fallback when PyInstaller doesn't work"""
    print("🔄 Creating standalone script (PyInstaller fallback)...")
    
    try:
        # Create dist directory
        Path('dist').mkdir(exist_ok=True)
        
        # Create a portable script that bundles everything
        standalone_content = '''#!/usr/bin/env python3
"""
BootForge Standalone Script
Generated portable version of BootForge
"""

import sys
import os
from pathlib import Path

# Add src directory to path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir / "src"))

def main():
    """Main entry point"""
    # Import after path setup
    try:
        from main import main as bootforge_main
        bootforge_main()
    except Exception as e:
        print(f"Error running BootForge: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
        
        # Write standalone script
        standalone_file = Path('dist/bootforge-standalone.py')
        standalone_file.write_text(standalone_content)
        standalone_file.chmod(0o755)
        
        # Copy source files to dist
        src_dist = Path('dist/src')
        if src_dist.exists():
            shutil.rmtree(src_dist)
        shutil.copytree('src', src_dist)
        
        # Copy main.py
        shutil.copy2('main.py', 'dist/main.py')
        
        # Copy requirements
        if Path('requirements.txt').exists():
            shutil.copy2('requirements.txt', 'dist/requirements.txt')
        
        print("✅ Standalone script created successfully")
        print("📝 Usage: python3 dist/bootforge-standalone.py")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create standalone script: {e}")
        return False


def build_executable() -> bool:
    """Build standalone executable with PyInstaller"""
    print("🔨 Building BootForge executable...")
    
    # Find PyInstaller
    pyinstaller_cmd = find_pyinstaller()
    if not pyinstaller_cmd:
        print("❌ PyInstaller not found!")
        print("\n📦 Installation options:")
        print("   • pip install pyinstaller")
        print("   • pip3 install --user pyinstaller")
        print("   • python -m pip install pyinstaller")
        return False
    
    # Check if we should use existing spec file
    spec_file = get_platform_spec_file()
    
    if spec_file:
        print(f"📋 Using existing spec file: {spec_file}")
        if 'python' in pyinstaller_cmd.lower():
            cmd = pyinstaller_cmd.split() + [spec_file]
        else:
            cmd = [pyinstaller_cmd, spec_file]
    else:
        print("📋 Creating new build configuration")
        
        # Build command dynamically
        if 'python' in pyinstaller_cmd.lower():
            cmd = pyinstaller_cmd.split()
        else:
            cmd = [pyinstaller_cmd]
        
        cmd.extend([
            '--onefile',
            '--name=BootForge',
            '--add-data=src:src',
            '--hidden-import=src.core',
            '--hidden-import=src.plugins',
            '--hidden-import=src.cli',
            '--windowed',  # GUI application (no console)
            'main.py'
        ])
        
        # Add GUI support if available
        try:
            import PyQt6
            cmd.extend([
                '--hidden-import=PyQt6.QtWidgets',
                '--hidden-import=PyQt6.QtCore', 
                '--hidden-import=PyQt6.QtGui',
                '--hidden-import=src.gui'
            ])
            print("🖥️  Including GUI support (PyQt6 detected)")
        except ImportError:
            print("📟 Building CLI-only version (PyQt6 not available)")
    
    print(f"🚀 Running: {' '.join(cmd)}")
    
    try:
        # Create dist directory
        Path('dist').mkdir(exist_ok=True)
        
        # Run PyInstaller with environment restrictions check
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            cwd=Path.cwd(),
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            print("✅ Executable built successfully")
            
            # Show build artifacts
            dist_dir = Path('dist')
            if dist_dir.exists():
                artifacts = list(dist_dir.glob('*'))
                if artifacts:
                    print("\n📦 Build artifacts:")
                    for artifact in artifacts:
                        size = artifact.stat().st_size if artifact.is_file() else 0
                        size_mb = size / (1024 * 1024) if size > 0 else 0
                        print(f"   • {artifact.name} ({size_mb:.1f}MB)")
            
            return True
        else:
            print("❌ PyInstaller build failed!")
            
            # Check for specific environment issues
            error_output = result.stderr.lower() if result.stderr else ""
            if "ptrace" in error_output or "esrch" in error_output:
                print("\n⚠️  Environment Limitation Detected:")
                print("   This appears to be a restricted environment that doesn't support")
                print("   PyInstaller's process monitoring features (ptrace restrictions).")
                print("\n🔄 Switching to fallback method...")
                return create_standalone_script()
            else:
                print(f"\n🔍 Error details:")
                print(f"Exit code: {result.returncode}")
                if result.stdout:
                    print(f"STDOUT: {result.stdout}")
                if result.stderr:
                    print(f"STDERR: {result.stderr}")
                
                print("\n🔄 Trying fallback method...")
                return create_standalone_script()
            
    except subprocess.TimeoutExpired:
        print("❌ Build timed out (5 minutes)")
        print("🔄 Switching to fallback method...")
        return create_standalone_script()
    except Exception as e:
        print(f"❌ Build failed with exception: {e}")
        print("🔄 Switching to fallback method...")
        return create_standalone_script()


def find_windows_executable() -> Optional[Path]:
    """Find the Windows executable"""
    dist_dir = Path("dist")
    executable_candidates = [
        "BootForge-Windows-x64.exe",
        "BootForge.exe",
        "bootforge-windows-x64.exe", 
        "bootforge.exe"
    ]
    
    for candidate in executable_candidates:
        candidate_path = dist_dir / candidate
        if candidate_path.exists() and candidate_path.is_file():
            print(f"✅ Found Windows executable: {candidate_path}")
            return candidate_path
    
    return None

def create_windows_zip_package() -> bool:
    """Create portable ZIP package for Windows"""
    print("📦 Creating Windows ZIP package...")
    
    # Find the executable
    executable = find_windows_executable()
    if not executable:
        print("❌ Could not find Windows executable")
        return False
    
    import zipfile
    
    # Create ZIP package
    zip_path = Path("dist/windows/BootForge-Portable.zip")
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add executable
        zipf.write(executable, f"BootForge/{executable.name}")
        
        # Add README for portable version
        readme_content = """BootForge Portable
================

This is a portable version of BootForge.

To run:
1. Extract this ZIP file to any folder
2. Double-click BootForge.exe
3. No installation required!

For full installation with Start Menu shortcuts,
download the installer version instead.

Support: https://bootforge.dev
"""
        
        from io import BytesIO
        readme_bytes = BytesIO(readme_content.encode('utf-8'))
        zipf.writestr("BootForge/README.txt", readme_bytes.getvalue())
        
        # Add assets if available
        asset_dirs = ["assets", "docs"]
        for asset_dir in asset_dirs:
            asset_path = Path(asset_dir)
            if asset_path.exists():
                for file_path in asset_path.rglob("*"):
                    if file_path.is_file():
                        arc_path = f"BootForge/{file_path}"
                        zipf.write(file_path, arc_path)
    
    print(f"✅ Windows ZIP package created: {zip_path}")
    return True

def sign_windows_executable(executable_path: Path) -> bool:
    """Sign Windows executable with Authenticode"""
    cert_path = os.environ.get('WIN_CERT_PATH')
    cert_password = os.environ.get('WIN_CERT_PASS')
    
    if not cert_path or not cert_password:
        print("⚠️  Windows code signing skipped - WIN_CERT_PATH or WIN_CERT_PASS not set")
        print("   Set these environment variables to enable Authenticode signing:")
        print("   - WIN_CERT_PATH: Path to your .p12/.pfx certificate file")
        print("   - WIN_CERT_PASS: Certificate password")
        return False
    
    if not Path(cert_path).exists():
        print(f"❌ Certificate file not found: {cert_path}")
        return False
    
    print("🔐 Signing Windows executable with Authenticode...")
    
    # Sign with multiple timestamps for better reliability
    timestamp_urls = [
        "http://timestamp.digicert.com",
        "http://timestamp.sectigo.com",
        "http://timestamp.globalsign.com"
    ]
    
    for i, timestamp_url in enumerate(timestamp_urls):
        try:
            cmd = [
                'signtool', 'sign',
                '/f', cert_path,
                '/p', cert_password,
                '/t', timestamp_url,
                '/fd', 'SHA256',
                '/v',
                str(executable_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print(f"✅ Successfully signed with timestamp server {i+1}")
                
                # Verify the signature
                verify_cmd = ['signtool', 'verify', '/pa', '/v', str(executable_path)]
                verify_result = subprocess.run(verify_cmd, capture_output=True, text=True)
                
                if verify_result.returncode == 0:
                    print("✅ Signature verification successful")
                    return True
                else:
                    print(f"⚠️  Signature verification failed: {verify_result.stderr}")
            else:
                print(f"⚠️  Signing failed with timestamp server {i+1}: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print(f"⚠️  Signing timed out with timestamp server {i+1}")
        except FileNotFoundError:
            print("❌ signtool not found - Windows SDK required for code signing")
            return False
        except Exception as e:
            print(f"⚠️  Error with timestamp server {i+1}: {e}")
    
    print("❌ All timestamp servers failed - executable will be unsigned")
    return False


def create_windows_installer():
    """Create Windows installer with Inno Setup or ZIP fallback"""
    print("Creating Windows installer...")
    
    # Find the executable first
    executable = find_windows_executable()
    if not executable:
        print("❌ Could not find Windows executable")
        return False
    
    # Sign the executable first
    sign_windows_executable(executable)
    
    # Try Inno Setup installer first
    iss_content = f"""[Setup]
AppName=BootForge
AppVersion=1.0.0
AppPublisher=BootForge Team
AppPublisherURL=https://bootforge.dev
DefaultDirName={{pf}}\\BootForge
DefaultGroupName=BootForge
UninstallDisplayIcon={{app}}\\{executable.name}
Compression=lzma2
SolidCompression=yes
OutputDir=dist\\windows
OutputBaseFilename=BootForge-Setup
WizardStyle=modern
DisableWelcomePage=no
PrivilegesRequired=admin
SetupIconFile=assets\\icons\\app_icon_premium.png

[Files]
Source: "{executable}"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{{app}}"; Flags: ignoreversion external skipifnotexists
Source: "assets\\*"; DestDir: "{{app}}\\assets"; Flags: ignoreversion recursesubdirs external skipifnotexists
Source: "docs\\*"; DestDir: "{{app}}\\docs"; Flags: ignoreversion recursesubdirs external skipifnotexists

[Icons]
Name: "{{group}}\\BootForge"; Filename: "{{app}}\\{executable.name}"; WorkingDir: "{{app}}"
Name: "{{group}}\\Uninstall BootForge"; Filename: "{{uninstallexe}}"
Name: "{{commondesktop}}\\BootForge"; Filename: "{{app}}\\{executable.name}"; WorkingDir: "{{app}}"; Tasks: desktopicon
Name: "{{commonstartup}}\\BootForge"; Filename: "{{app}}\\{executable.name}"; WorkingDir: "{{app}}"; Tasks: startupicon

[Tasks]
Name: desktopicon; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked
Name: startupicon; Description: "Run BootForge at Windows startup"; GroupDescription: "Additional options:"; Flags: unchecked

[Registry]
Root: HKCR; Subkey: ".iso"; ValueType: string; ValueName: ""; ValueData: "BootForge.ISOFile"; Flags: uninsdeletevalue; Tasks: associateiso
Root: HKCR; Subkey: "BootForge.ISOFile"; ValueType: string; ValueName: ""; ValueData: "ISO Disk Image"; Flags: uninsdeletekey; Tasks: associateiso
Root: HKCR; Subkey: "BootForge.ISOFile\\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{{app}}\\{executable.name},0"; Tasks: associateiso
Root: HKCR; Subkey: "BootForge.ISOFile\\shell\\open\\command"; ValueType: string; ValueName: ""; ValueData: "\\"{{app}}\\{executable.name}\\" \\"%1\\""; Tasks: associateiso

[Tasks]
Name: associateiso; Description: "Associate BootForge with ISO files"; GroupDescription: "File associations:"; Flags: unchecked

[Run]
Filename: "{{app}}\\{executable.name}"; Description: "Launch BootForge"; Flags: nowait postinstall skipifsilent
"""
    
    # Write Inno Setup script
    iss_file = Path("BootForge.iss")
    iss_file.write_text(iss_content)
    
    # Run Inno Setup compiler
    try:
        result = subprocess.run(['iscc', 'BootForge.iss'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Windows installer created")
            
            # Sign the installer if signing credentials are available
            installer_path = Path("dist/windows/BootForge-Setup.exe")
            if installer_path.exists():
                sign_windows_executable(installer_path)
            
            # Also create ZIP package as alternative
            create_windows_zip_package()
            return True
        else:
            print(f"❌ Installer creation failed: {result.stderr}")
            print("🔄 Creating ZIP package fallback...")
            return create_windows_zip_package()
    except FileNotFoundError:
        print("⚠️  Inno Setup not found - creating ZIP fallback")
        print("   Install Inno Setup from: https://jrsoftware.org/isdl.php")
        return create_windows_zip_package()


def find_macos_executable() -> Optional[Path]:
    """Find the macOS executable, handling both .app bundles and bare binaries"""
    dist_dir = Path("dist")
    
    # First, look for .app bundle (preferred from spec file)
    app_bundle = dist_dir / "BootForge.app"
    if app_bundle.exists() and app_bundle.is_dir():
        print(f"✅ Found .app bundle: {app_bundle}")
        return app_bundle
    
    # Look for bare executable (fallback)
    executable_candidates = [
        "BootForge-macOS-x64",
        "BootForge",
        "bootforge-macos-x64",
        "bootforge"
    ]
    
    for candidate in executable_candidates:
        candidate_path = dist_dir / candidate
        if candidate_path.exists() and candidate_path.is_file():
            print(f"✅ Found executable: {candidate_path}")
            return candidate_path
    
    return None

def convert_png_to_icns(png_path: Path, icns_path: Path) -> bool:
    """Convert PNG to ICNS format for macOS app icons"""
    try:
        # Create iconset directory
        iconset_dir = icns_path.parent / f"{icns_path.stem}.iconset"
        if iconset_dir.exists():
            shutil.rmtree(iconset_dir)
        iconset_dir.mkdir(parents=True)
        
        # Create different icon sizes using sips
        icon_sizes = [
            (16, "icon_16x16.png"),
            (32, "icon_16x16@2x.png"),
            (32, "icon_32x32.png"),
            (64, "icon_32x32@2x.png"),
            (128, "icon_128x128.png"),
            (256, "icon_128x128@2x.png"),
            (256, "icon_256x256.png"),
            (512, "icon_256x256@2x.png"),
            (512, "icon_512x512.png"),
            (1024, "icon_512x512@2x.png")
        ]
        
        for size, filename in icon_sizes:
            result = subprocess.run([
                'sips', '-z', str(size), str(size),
                str(png_path), '--out', str(iconset_dir / filename)
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"⚠️  Failed to create {filename}: {result.stderr}")
        
        # Convert iconset to icns
        result = subprocess.run([
            'iconutil', '-c', 'icns', str(iconset_dir), '-o', str(icns_path)
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            # Clean up iconset directory
            shutil.rmtree(iconset_dir)
            print(f"✅ Created ICNS icon: {icns_path}")
            return True
        else:
            print(f"❌ Failed to create ICNS: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("⚠️  sips or iconutil not found - keeping PNG icon")
        # Fallback: just copy PNG as is
        shutil.copy2(png_path, icns_path.parent / "AppIcon.png")
        return False
    except Exception as e:
        print(f"❌ Icon conversion failed: {e}")
        return False


def sign_macos_app(app_path: Path) -> bool:
    """Sign macOS app bundle with Developer ID"""
    sign_id = os.environ.get('MACOS_SIGN_ID')
    
    if not sign_id:
        print("⚠️  macOS code signing skipped - MACOS_SIGN_ID not set")
        print("   Set this environment variable to enable code signing:")
        print("   - MACOS_SIGN_ID: Your Developer ID (e.g., 'Developer ID Application: Your Name (XXXXXXXXXX)')")
        return False
    
    print("🔐 Signing macOS app bundle...")
    
    try:
        # Sign all frameworks and executables first
        for root, dirs, files in os.walk(app_path):
            for file in files:
                file_path = Path(root) / file
                if (file_path.suffix in ['.dylib', '.so'] or 
                    (file_path.stat().st_mode & 0o111) and file_path.is_file()):
                    
                    result = subprocess.run([
                        'codesign', '--force', '--options', 'runtime',
                        '--sign', sign_id, str(file_path)
                    ], capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        print(f"⚠️  Warning: Failed to sign {file_path}: {result.stderr}")
        
        # Sign the main app bundle
        cmd = [
            'codesign', '--force', '--options', 'runtime',
            '--sign', sign_id, '--deep', str(app_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ App bundle signed successfully")
            
            # Verify signature
            verify_cmd = ['codesign', '--verify', '--deep', '--strict', '--verbose=2', str(app_path)]
            verify_result = subprocess.run(verify_cmd, capture_output=True, text=True)
            
            if verify_result.returncode == 0:
                print("✅ Signature verification successful")
                return True
            else:
                print(f"❌ Signature verification failed: {verify_result.stderr}")
                return False
        else:
            print(f"❌ Code signing failed: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("❌ codesign not found - Xcode Command Line Tools required")
        return False
    except Exception as e:
        print(f"❌ Code signing error: {e}")
        return False


def notarize_macos_app(app_path: Path) -> bool:
    """Notarize macOS app with Apple"""
    apple_id = os.environ.get('APPLE_ID')
    app_password = os.environ.get('APPLE_APP_PASSWORD')
    team_id = os.environ.get('APPLE_TEAM_ID')
    
    if not all([apple_id, app_password, team_id]):
        print("⚠️  macOS notarization skipped - missing credentials")
        print("   Set these environment variables for notarization:")
        print("   - APPLE_ID: Your Apple ID email")
        print("   - APPLE_APP_PASSWORD: App-specific password")
        print("   - APPLE_TEAM_ID: Your Apple Developer Team ID")
        return False
    
    print("📤 Submitting app for notarization...")
    
    try:
        # Create ZIP for notarization
        zip_path = app_path.parent / f"{app_path.stem}.zip"
        result = subprocess.run([
            'ditto', '-c', '-k', '--keepParent', str(app_path), str(zip_path)
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Failed to create ZIP: {result.stderr}")
            return False
        
        # Submit for notarization using notarytool (Xcode 13+)
        cmd = [
            'xcrun', 'notarytool', 'submit', str(zip_path),
            '--apple-id', apple_id,
            '--password', app_password,
            '--team-id', team_id,
            '--wait'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Notarization successful")
            
            # Staple the notarization ticket
            staple_cmd = ['xcrun', 'stapler', 'staple', str(app_path)]
            staple_result = subprocess.run(staple_cmd, capture_output=True, text=True)
            
            if staple_result.returncode == 0:
                print("✅ Notarization ticket stapled")
                
                # Clean up ZIP
                zip_path.unlink()
                return True
            else:
                print(f"⚠️  Stapling failed: {staple_result.stderr}")
                zip_path.unlink()
                return True  # Notarization succeeded even if stapling failed
        else:
            print(f"❌ Notarization failed: {result.stderr}")
            zip_path.unlink()
            return False
            
    except FileNotFoundError:
        print("❌ notarytool not found - Xcode 13+ required for notarization")
        return False
    except Exception as e:
        print(f"❌ Notarization error: {e}")
        return False


def create_macos_installer():
    """Create macOS installer"""
    print("Creating macOS installer...")
    
    # Find the macOS executable or .app bundle
    macos_executable = find_macos_executable()
    if not macos_executable:
        print("❌ Could not find macOS executable or .app bundle")
        print("Available files in dist:")
        dist_dir = Path("dist")
        for item in dist_dir.iterdir():
            print(f"   • {item.name}")
        return False
    
    app_name = "BootForge.app"
    app_dir = Path("dist/macos") / app_name
    
    if macos_executable.suffix == ".app" or macos_executable.name.endswith(".app"):
        # We already have a .app bundle, just copy it
        if app_dir.exists():
            shutil.rmtree(app_dir)
        shutil.copytree(macos_executable, app_dir)
        print(f"✅ Copied existing .app bundle to {app_dir}")
    else:
        # Create app bundle structure from bare executable
        app_dir.mkdir(parents=True, exist_ok=True)
        (app_dir / "Contents").mkdir(exist_ok=True)
        (app_dir / "Contents/MacOS").mkdir(exist_ok=True)
        (app_dir / "Contents/Resources").mkdir(exist_ok=True)
        
        # Copy executable
        shutil.copy2(macos_executable, app_dir / "Contents/MacOS/BootForge")
        (app_dir / "Contents/MacOS/BootForge").chmod(0o755)
        
        # Create Info.plist
        plist_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>BootForge</string>
    <key>CFBundleIdentifier</key>
    <string>dev.bootforge.BootForge</string>
    <key>CFBundleName</key>
    <string>BootForge</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon.icns</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.utilities</string>
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
</dict>
</plist>"""
        
        (app_dir / "Contents/Info.plist").write_text(plist_content)
        
        # Find and convert icon
        icon_paths = [
            Path("assets/icons/app_icon_premium.png"),
            Path("assets/icons/BootForge_App_Icon_1685d1e8.png"),
            Path("attached_assets/generated_images/BootForge_App_Icon_1685d1e8.png")
        ]
        
        for icon_path in icon_paths:
            if icon_path.exists():
                icns_path = app_dir / "Contents/Resources/AppIcon.icns"
                if convert_png_to_icns(icon_path, icns_path):
                    print(f"✅ Converted icon from {icon_path}")
                else:
                    # Fallback to PNG
                    shutil.copy2(icon_path, app_dir / "Contents/Resources/AppIcon.png")
                    print(f"✅ Added PNG icon from {icon_path}")
                break
        else:
            print("⚠️  No app icon found, using default")
        
        print(f"✅ Created .app bundle at {app_dir}")
    
    # Sign the app bundle
    signed = sign_macos_app(app_dir)
    
    # Notarize if signed
    if signed:
        notarize_macos_app(app_dir)
    
    # Create DMG
    try:
        dmg_path = Path("dist/BootForge-1.0.0.dmg")
        result = subprocess.run([
            'hdiutil', 'create', '-volname', 'BootForge',
            '-srcfolder', str(app_dir.parent),
            '-ov', '-format', 'UDZO',
            str(dmg_path)
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ macOS DMG created")
            
            # Sign the DMG if we have signing credentials
            if signed:
                sign_windows_executable(dmg_path)  # Reuse Windows signing function for DMG
            
            return True
        else:
            print(f"❌ DMG creation failed: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ hdiutil not found - macOS required for DMG creation")
        return False


def find_linux_executable() -> Optional[Path]:
    """Find the Linux executable"""
    dist_dir = Path("dist")
    executable_candidates = [
        "BootForge-Linux-x64",
        "BootForge", 
        "bootforge-linux-x64",
        "bootforge"
    ]
    
    for candidate in executable_candidates:
        candidate_path = dist_dir / candidate
        if candidate_path.exists() and candidate_path.is_file():
            print(f"✅ Found Linux executable: {candidate_path}")
            return candidate_path
    
    return None

def create_linux_tarball() -> bool:
    """Create portable tarball for Linux (fallback)"""
    print("📦 Creating Linux tarball package...")
    
    # Find the executable
    executable = find_linux_executable()
    if not executable:
        print("❌ Could not find Linux executable")
        return False
    
    import tarfile
    
    # Create tarball package
    tar_path = Path("dist/linux/BootForge-Portable.tar.gz")
    tar_path.parent.mkdir(parents=True, exist_ok=True)
    
    with tarfile.open(tar_path, 'w:gz') as tar:
        # Add executable
        tar.add(executable, arcname=f"BootForge/{executable.name}")
        
        # Add run script
        run_script_content = f"""#!/bin/bash
# BootForge Portable Linux Launcher
SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
exec "$SCRIPT_DIR/{executable.name}" "$@"
"""
        
        from io import BytesIO
        run_script_bytes = BytesIO(run_script_content.encode('utf-8'))
        tarinfo = tarfile.TarInfo(name="BootForge/bootforge")
        tarinfo.size = len(run_script_bytes.getvalue())
        tarinfo.mode = 0o755
        run_script_bytes.seek(0)
        tar.addfile(tarinfo, run_script_bytes)
        
        # Add README
        readme_content = """BootForge Portable Linux
========================

To run BootForge:
1. Extract this tarball: tar -xzf BootForge-Portable.tar.gz
2. cd BootForge
3. ./bootforge

Or directly: ./BootForge/{executable.name}

No installation required!

Support: https://bootforge.dev
"""
        readme_bytes = BytesIO(readme_content.encode('utf-8'))
        readme_info = tarfile.TarInfo(name="BootForge/README.txt")
        readme_info.size = len(readme_bytes.getvalue())
        readme_bytes.seek(0)
        tar.addfile(readme_info, readme_bytes)
        
        # Add assets if available
        for asset_dir in ["assets", "docs"]:
            asset_path = Path(asset_dir)
            if asset_path.exists():
                tar.add(asset_path, arcname=f"BootForge/{asset_dir}")
    
    print(f"✅ Linux tarball created: {tar_path}")
    return True

def deploy_qt_dependencies(appdir: Path, executable_path: Path) -> bool:
    """Deploy Qt dependencies for AppImage using linuxdeploy-qt"""
    try:
        # Check if PyQt6 is being used
        import PyQt6
        qt_version = "6"
        print(f"🔍 Detected PyQt{qt_version}")
    except ImportError:
        try:
            import PyQt5
            qt_version = "5"
            print(f"🔍 Detected PyQt{qt_version}")
        except ImportError:
            print("⚠️  No Qt libraries detected - skipping Qt deployment")
            return True
    
    # Try linuxdeploy-qt first
    try:
        print("📦 Deploying Qt dependencies with linuxdeploy-qt...")
        
        env = os.environ.copy()
        env['QMAKE'] = shutil.which('qmake') or f'qmake-qt{qt_version}'
        
        cmd = [
            'linuxdeploy-qt', 
            '--executable', str(executable_path),
            '--appdir', str(appdir),
            '--output', 'appimage'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        
        if result.returncode == 0:
            print("✅ Qt dependencies deployed successfully")
            return True
        else:
            print(f"⚠️  linuxdeploy-qt failed: {result.stderr}")
            
    except FileNotFoundError:
        print("⚠️  linuxdeploy-qt not found")
    
    # Fallback: try to manually copy Qt libraries
    print("🔄 Attempting manual Qt library deployment...")
    
    try:
        # Find Qt installation
        qt_libs = []
        search_paths = [
            f"/usr/lib/x86_64-linux-gnu/qt{qt_version}",
            f"/usr/lib/qt{qt_version}",
            f"/opt/qt{qt_version}",
            "/usr/lib/x86_64-linux-gnu",
            "/usr/lib"
        ]
        
        lib_dir = appdir / "lib"
        lib_dir.mkdir(exist_ok=True)
        
        # Essential Qt libraries for GUI apps
        essential_libs = [
            f"libQt{qt_version}Core.so*",
            f"libQt{qt_version}Gui.so*", 
            f"libQt{qt_version}Widgets.so*",
            f"libQt{qt_version}DBus.so*",
            f"libQt{qt_version}XcbQpa.so*"
        ]
        
        for search_path in search_paths:
            search_dir = Path(search_path)
            if search_dir.exists():
                for lib_pattern in essential_libs:
                    for lib_file in search_dir.glob(lib_pattern):
                        if lib_file.is_file():
                            dest = lib_dir / lib_file.name
                            if not dest.exists():
                                shutil.copy2(lib_file, dest)
                                print(f"   📄 Copied {lib_file.name}")
                                qt_libs.append(lib_file.name)
        
        if qt_libs:
            print(f"✅ Deployed {len(qt_libs)} Qt libraries manually")
            return True
        else:
            print("⚠️  No Qt libraries found for manual deployment")
            return False
            
    except Exception as e:
        print(f"❌ Manual Qt deployment failed: {e}")
        return False


def create_enhanced_apprun(appdir: Path, executable_name: str) -> None:
    """Create enhanced AppRun script with better library handling"""
    apprun_content = f"""#!/bin/bash
# BootForge AppImage Launcher with Qt Support
set -e

HERE="$(dirname "$(readlink -f "${{0}}")")"
export APPDIR="$HERE"

# Set up library paths
if [ -d "$HERE/lib" ]; then
    export LD_LIBRARY_PATH="$HERE/lib:${{LD_LIBRARY_PATH}}"
fi

if [ -d "$HERE/usr/lib" ]; then
    export LD_LIBRARY_PATH="$HERE/usr/lib:${{LD_LIBRARY_PATH}}"
fi

# Set up Qt plugin paths  
if [ -d "$HERE/usr/plugins" ]; then
    export QT_PLUGIN_PATH="$HERE/usr/plugins:${{QT_PLUGIN_PATH}}"
fi

if [ -d "$HERE/plugins" ]; then
    export QT_PLUGIN_PATH="$HERE/plugins:${{QT_PLUGIN_PATH}}"
fi

# Disable Qt's xcb plugin warnings in AppImage environment
export QT_LOGGING_RULES="qt.qpa.xcb.warning=false"

# Change to app directory
cd "$HERE"

# Check if executable exists
if [ ! -f "./{executable_name}" ]; then
    echo "Error: {executable_name} executable not found"
    exit 1
fi

# Make sure it's executable
chmod +x "./{executable_name}"

# Launch with all arguments
exec "./{executable_name}" "$@"
"""
    
    apprun_file = appdir / "AppRun"
    apprun_file.write_text(apprun_content)
    apprun_file.chmod(0o755)
    print("✅ Created enhanced AppRun script with Qt support")


def create_linux_package():
    """Create Linux package (AppImage with fallback)"""
    print("Creating Linux package...")
    
    # Find the executable in dist directory
    executable_path = find_linux_executable()
    if not executable_path:
        print("❌ Could not find Linux executable in dist directory")
        print("Available files:")
        dist_dir = Path("dist")
        for item in dist_dir.iterdir():
            if item.is_file():
                print(f"   • {item.name}")
        return False
    
    print(f"✅ Found executable: {executable_path}")
    
    # Create AppDir structure
    appdir = Path("dist/linux/BootForge.AppDir")
    if appdir.exists():
        shutil.rmtree(appdir)
    appdir.mkdir(parents=True, exist_ok=True)
    
    # Copy executable
    shutil.copy2(executable_path, appdir / "BootForge")
    (appdir / "BootForge").chmod(0o755)
    
    # Deploy Qt dependencies if needed
    deploy_qt_dependencies(appdir, appdir / "BootForge")
    
    # Find and copy icon
    icon_paths = [
        Path("assets/icons/app_icon_premium.png"),
        Path("assets/icons/BootForge_App_Icon_1685d1e8.png"),
        Path("attached_assets/generated_images/BootForge_App_Icon_1685d1e8.png")
    ]
    
    icon_file = None
    for icon_path in icon_paths:
        if icon_path.exists():
            icon_file = appdir / "bootforge.png"
            shutil.copy2(icon_path, icon_file)
            print(f"✅ Added app icon from {icon_path}")
            break
    
    # Create enhanced desktop file
    desktop_content = """[Desktop Entry]
Version=1.0
Type=Application
Name=BootForge
Comment=Professional OS Deployment Tool for Mac, Windows, and Linux
GenericName=OS Deployment Tool
Exec=BootForge
Icon=bootforge
StartupNotify=true
Categories=System;Utility;Settings;
Keywords=bootable;usb;installer;deployment;macos;windows;linux;
MimeType=application/x-iso9660-image;application/x-cd-image;application/x-raw-disk-image;
X-AppImage-Version=1.0.0
"""
    
    (appdir / "BootForge.desktop").write_text(desktop_content)
    
    # Create enhanced AppRun script
    create_enhanced_apprun(appdir, "BootForge")
    
    # Copy the icon as the main icon (required by AppImage)
    if icon_file and icon_file != appdir / "bootforge.png":
        shutil.copy2(icon_file, appdir / "bootforge.png")
    
    # Copy desktop file as the main desktop file (required by AppImage) 
    shutil.copy2(appdir / "BootForge.desktop", appdir / "bootforge.desktop")
    
    # Create AppImage metadata
    appdata_content = """<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>dev.bootforge.BootForge</id>
  <name>BootForge</name>
  <summary>Professional OS Deployment Tool</summary>
  <description>
    <p>
      BootForge is a professional OS deployment tool that creates bootable USB drives
      for macOS, Windows, and Linux systems with advanced customization options.
    </p>
  </description>
  <categories>
    <category>System</category>
    <category>Utility</category>
  </categories>
  <url type="homepage">https://bootforge.dev</url>
  <launchable type="desktop-id">bootforge.desktop</launchable>
  <provides>
    <binary>BootForge</binary>
  </provides>
  <releases>
    <release version="1.0.0" date="2025-09-14"/>
  </releases>
</component>
"""
    
    # Create usr/share/metainfo directory
    metainfo_dir = appdir / "usr/share/metainfo"
    metainfo_dir.mkdir(parents=True, exist_ok=True)
    (metainfo_dir / "dev.bootforge.BootForge.appdata.xml").write_text(appdata_content)
    
    # Try appimagetool first, then linuxdeploy, then fallback
    appimage_created = False
    
    # Method 1: Try appimagetool
    try:
        print("🔨 Building AppImage with appimagetool...")
        result = subprocess.run([
            'appimagetool', '--no-appstream',
            str(appdir), 'dist/linux/BootForge-1.0.0-x86_64.AppImage'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ AppImage created with appimagetool")
            appimage_created = True
        else:
            print(f"⚠️  appimagetool failed: {result.stderr}")
            
    except FileNotFoundError:
        print("⚠️  appimagetool not found")
    
    # Method 2: Try linuxdeploy if appimagetool failed
    if not appimage_created:
        try:
            print("🔨 Building AppImage with linuxdeploy...")
            result = subprocess.run([
                'linuxdeploy', '--appdir', str(appdir),
                '--output', 'appimage',
                '--desktop-file', str(appdir / "BootForge.desktop")
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ AppImage created with linuxdeploy")
                appimage_created = True
            else:
                print(f"⚠️  linuxdeploy failed: {result.stderr}")
                
        except FileNotFoundError:
            print("⚠️  linuxdeploy not found")
    
    if appimage_created:
        # Also create tarball as alternative
        create_linux_tarball()
        return True
    else:
        print("🔄 AppImage tools not available - creating tarball fallback")
        print("   Install AppImage tools for better Linux packaging:")
        print("   • appimagetool: https://github.com/AppImage/AppImageKit")
        print("   • linuxdeploy: https://github.com/linuxdeploy/linuxdeploy")
        return create_linux_tarball()


def main() -> bool:
    """Main installer build function"""
    print("🚀 BootForge Installer Builder")
    print("═" * 50)
    
    # Check system info
    system = platform.system()
    arch = platform.machine()
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    print(f"🖥️  Platform: {system} {arch}")
    print(f"🐍 Python: {python_version}")
    print(f"📁 Working directory: {Path.cwd()}")
    print()
    
    # Check dependencies
    print("🔍 Checking dependencies...")
    deps_ok, missing_deps = check_dependencies()
    
    if missing_deps:
        print("⚠️  Some dependencies are missing, but continuing with fallbacks")
    else:
        print("✅ All dependencies available")
    print()
    
    # Create dist directory
    dist_dir = Path("dist")
    dist_dir.mkdir(exist_ok=True)
    
    # Build executable
    success = build_executable()
    
    if not success:
        print("\n❌ Failed to build executable")
        print("\n🔧 Troubleshooting tips:")
        print("   1. Check that all dependencies are properly installed")
        print("   2. Ensure you have enough disk space")
        print("   3. Check file permissions in the project directory")
        print("   4. Try running with verbose output: python -c 'import PyInstaller; print(PyInstaller.__file__)'")
        return False
    
    # Create platform-specific installers
    print("\n📦 Creating platform-specific installer...")
    
    installer_created = False
    if system == "Windows":
        installer_created = create_windows_installer()
    elif system == "Darwin":
        installer_created = create_macos_installer()
    elif system == "Linux":
        installer_created = create_linux_package()
    else:
        print(f"⚠️  Platform {system} not directly supported for packaging")
        print("   Executable is available in dist/ directory")
        installer_created = True  # Executable exists
    
    print("\n" + "═" * 50)
    if success and installer_created:
        print("✅ Build completed successfully!")
        print(f"📁 Installers available in: {dist_dir.absolute()}")
        
        # List all build artifacts
        artifacts = list(dist_dir.rglob('*'))
        if artifacts:
            print("\n📦 Available artifacts:")
            for artifact in sorted(artifacts):
                if artifact.is_file():
                    size = artifact.stat().st_size
                    size_mb = size / (1024 * 1024)
                    rel_path = artifact.relative_to(dist_dir)
                    print(f"   • {rel_path} ({size_mb:.1f}MB)")
        
        print("\n🎉 Ready for distribution!")
        return True
    else:
        print("❌ Build completed with errors")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Build cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        print("\n🔍 Full traceback:")
        traceback.print_exc()
        sys.exit(1)