#!/usr/bin/env python3
"""
BootForge Web Demo Server
Simple web interface to showcase BootForge capabilities and serve downloads
"""

from flask import Flask, render_template, jsonify, send_from_directory, Response, request
import os
import sys
import hashlib
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

app = Flask(__name__)

# Configuration
BASE_URL = os.environ.get('BASE_URL', 'https://bootforge.dev')
DIST_DIR = 'dist'

# Supported architectures
SUPPORTED_ARCHITECTURES = {
    'linux': ['x64', 'arm64'],
    'windows': ['x64', 'arm64'],
    'macos': ['x64', 'arm64']
}

def get_base_url():
    """Get the base URL for the current request"""
    if 'X-Forwarded-Host' in request.headers:
        protocol = request.headers.get('X-Forwarded-Proto', 'https')
        host = request.headers.get('X-Forwarded-Host')
        return f"{protocol}://{host}"
    elif request.host:
        return f"{request.scheme}://{request.host}"
    else:
        return BASE_URL

def verify_file_integrity(file_path, expected_checksum=None):
    """Verify file integrity using SHA256"""
    try:
        with open(file_path, 'rb') as f:
            sha256_hash = hashlib.sha256()
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
            actual_checksum = sha256_hash.hexdigest()
            
        if expected_checksum:
            return actual_checksum == expected_checksum
        return actual_checksum
    except Exception:
        return None

@app.route('/')
def index():
    """Main landing page"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BootForge - Professional OS Deployment Tool</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e1e1e, #2d2d2d);
            color: #ffffff;
            min-height: 100vh;
        }
        .container { 
            max-width: 1200px; 
            margin: 0 auto; 
            padding: 2rem;
        }
        .header {
            text-align: center;
            margin-bottom: 3rem;
        }
        .logo {
            font-size: 3rem;
            font-weight: 700;
            background: linear-gradient(45deg, #00d4ff, #0099cc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1rem;
        }
        .subtitle {
            font-size: 1.2rem;
            color: #cccccc;
            margin-bottom: 2rem;
        }
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            margin: 3rem 0;
        }
        .feature {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 2rem;
            border: 1px solid rgba(0, 212, 255, 0.3);
        }
        .feature h3 {
            color: #00d4ff;
            margin-bottom: 1rem;
            font-size: 1.4rem;
        }
        .download-section {
            background: rgba(0, 212, 255, 0.1);
            border-radius: 12px;
            padding: 2rem;
            margin: 3rem 0;
            text-align: center;
            border: 2px solid #00d4ff;
        }
        .download-btn {
            display: inline-block;
            background: #00d4ff;
            color: #1e1e1e;
            padding: 1rem 2rem;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            margin: 1rem;
            transition: transform 0.2s;
        }
        .download-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 212, 255, 0.3);
        }
        .download-btn.available {
            background: #28a745;
        }
        .download-btn.coming-soon {
            background: #6c757d;
            opacity: 0.6;
            cursor: not-allowed;
        }
        .note {
            background: rgba(255, 193, 7, 0.1);
            border: 1px solid #ffc107;
            border-radius: 8px;
            padding: 1rem;
            margin: 2rem 0;
        }
        .status {
            background: rgba(40, 167, 69, 0.1);
            border: 1px solid #28a745;
            border-radius: 8px;
            padding: 1rem;
            margin: 2rem 0;
        }
        .tech-specs {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
            margin: 2rem 0;
        }
        .spec {
            background: rgba(255, 255, 255, 0.05);
            padding: 1rem;
            border-radius: 8px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="logo">BootForge</h1>
            <p class="subtitle">Professional Cross-Platform OS Deployment Tool</p>
            <p>Create bootable USB drives for macOS, Windows, and Linux with advanced features</p>
        </div>

        <div class="status">
            <strong>🏗️ Build Status:</strong> BootForge is production-ready with Linux support complete. 
            USB package includes cross-platform installers (Linux executable + Windows/Mac installer scripts ready for future builds).
        </div>

        <div class="features">
            <div class="feature">
                <h3>🔧 Hardware Detection</h3>
                <p>Automatic detection of Mac, PC, and custom hardware profiles with intelligent recommendations for optimal deployment strategies.</p>
            </div>
            <div class="feature">
                <h3>💾 Multiple OS Support</h3>
                <p>Deploy macOS (including OCLP), Windows (unattended), Linux (automated), and custom payloads with built-in recipes.</p>
            </div>
            <div class="feature">
                <h3>🛡️ Safety System</h3>
                <p>Comprehensive safety validation with device protection, risk assessment, and automatic rollback for failed operations.</p>
            </div>
            <div class="feature">
                <h3>🎨 Professional UI</h3>
                <p>Modern dark theme with 6-step wizard, visual progress indicators, and professional icon system for guided deployment.</p>
            </div>
            <div class="feature">
                <h3>⚡ Plugin System</h3>
                <p>Extensible architecture with driver injection, USB diagnostics, iOS jailbreak integration, and custom plugin support.</p>
            </div>
            <div class="feature">
                <h3>📊 System Monitoring</h3>
                <p>Real-time monitoring of CPU, memory, temperature, and USB devices with comprehensive logging and progress tracking.</p>
            </div>
        </div>

        <div class="download-section">
            <h2>Download BootForge</h2>
            <p>Get the full desktop application with hardware access and complete functionality</p>
            <a href="/download/linux" class="download-btn available">📱 Linux (64-bit)</a>
            <a href="/download/usb-package" class="download-btn available">💾 USB Distribution Package</a>
            <a href="#" class="download-btn coming-soon" onclick="alert('Windows executable coming soon! Use USB package for installer.')">🪟 Windows - Installer Ready</a>
            <a href="#" class="download-btn coming-soon" onclick="alert('macOS executable coming soon! Use USB package for installer.')">🍎 macOS - Installer Ready</a>
            <a href="/cli-demo" class="download-btn">🔧 CLI Demo</a>
            <a href="/install" class="download-btn available">⚡ One-Line Install</a>
            <p style="margin-top: 1rem; color: #cccccc;">
                USB package includes working Linux executable + Windows/Mac installers ready for when executables are built
            </p>
        </div>

        <div class="tech-specs">
            <div class="spec">
                <h4>🏗️ Architecture</h4>
                <p>Modular plugin system with GUI/CLI interfaces</p>
            </div>
            <div class="spec">
                <h4>🖼️ Framework</h4>
                <p>PyQt6 with modern theming and animations</p>
            </div>
            <div class="spec">
                <h4>🔐 Security</h4>
                <p>Device validation and operation verification</p>
            </div>
            <div class="spec">
                <h4>📝 Logging</h4>
                <p>Comprehensive logging with file rotation</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

# Architecture-aware download routes
@app.route('/download/<platform>-<arch>')
def download_platform_arch(platform, arch):
    """Serve platform and architecture specific executable"""
    if platform not in SUPPORTED_ARCHITECTURES or arch not in SUPPORTED_ARCHITECTURES[platform]:
        return jsonify({
            "error": "Unsupported platform/architecture",
            "platform": platform,
            "architecture": arch,
            "supported": SUPPORTED_ARCHITECTURES
        }), 400
    
    filename = f'BootForge-{platform.title()}-{arch}'
    file_path = os.path.join(DIST_DIR, filename)
    
    try:
        if not os.path.exists(file_path):
            return jsonify({
                "error": f"{platform.title()} {arch} executable not found",
                "message": f"Run 'python build_cross_platform.py' to build the {platform}-{arch} executable",
                "status": "build_required",
                "filename": filename
            }), 404
            
        return send_from_directory(DIST_DIR, filename, as_attachment=True, download_name=filename)
        
    except Exception as e:
        return jsonify({"error": f"Download failed: {str(e)}"}), 500

@app.route('/download/linux')
def download_linux():
    """Legacy Linux download - redirects to x64 by default"""
    return jsonify({
        "message": "Please use architecture-specific downloads",
        "architecture_required": True,
        "available_downloads": {
            "x64": f"{get_base_url()}/download/linux-x64",
            "arm64": f"{get_base_url()}/download/linux-arm64"
        },
        "auto_detect_url": f"{get_base_url()}/download/linux-auto"
    }), 400

@app.route('/download/linux-auto')
def download_linux_auto():
    """Auto-detect architecture and redirect"""
    user_agent = request.headers.get('User-Agent', '').lower()
    
    # Simple architecture detection from user agent
    if 'aarch64' in user_agent or 'arm64' in user_agent:
        arch = 'arm64'
    else:
        arch = 'x64'  # Default to x64
    
    return jsonify({
        "detected_architecture": arch,
        "download_url": f"{get_base_url()}/download/linux-{arch}",
        "message": f"Detected {arch} architecture. Use the download_url for your binary.",
        "manual_options": {
            "x64": f"{get_base_url()}/download/linux-x64",
            "arm64": f"{get_base_url()}/download/linux-arm64"
        }
    })

@app.route('/download/usb-package')
def download_usb_package():
    """Serve the complete USB distribution package"""
    filename = 'BootForge-USB-Package.tar.gz'
    file_path = os.path.join(DIST_DIR, filename)
    
    try:
        if not os.path.exists(file_path):
            return jsonify({
                "error": "USB package not found", 
                "message": "Run 'python build_cross_platform.py' to create the USB distribution package",
                "status": "build_required",
                "contains": "Linux executable + Windows/Mac installer scripts"
            }), 404
            
        return send_from_directory(DIST_DIR, filename, as_attachment=True, download_name=filename)
        
    except Exception as e:
        return jsonify({"error": f"Download failed: {str(e)}"}), 500

@app.route('/cli-demo')
def cli_demo():
    """Show CLI capabilities"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BootForge CLI Demo</title>
    <style>
        body { 
            font-family: 'Courier New', monospace;
            background: #1e1e1e;
            color: #00ff00;
            padding: 2rem;
            margin: 0;
        }
        .terminal {
            background: #000;
            border-radius: 8px;
            padding: 1rem;
            border: 1px solid #333;
            max-width: 800px;
            margin: 0 auto;
        }
        .prompt { color: #00d4ff; }
        .output { color: #cccccc; margin-left: 1rem; }
        a { color: #00d4ff; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="terminal">
        <div class="prompt">$ ./BootForge-Linux-x64 --help</div>
        <div class="output">
BootForge v1.0.0 - Professional OS Deployment Tool

Usage:
  ./BootForge-Linux-x64 [OPTIONS] COMMAND [ARGS]...

Commands:
  list-devices        List available USB devices
  write-image         Write OS image to USB device
  diagnose           Run hardware diagnostics
  format-device      Format USB device  
  list-plugins       Show available plugins
  --gui              Launch graphical interface

Options:
  --config PATH      Configuration file path
  --verbose         Enable verbose logging
  --help            Show this message and exit

Examples:
  ./BootForge-Linux-x64 --gui                    # Launch GUI
  ./BootForge-Linux-x64 list-devices            # List USB devices
  ./BootForge-Linux-x64 diagnose               # Hardware scan
        </div>
        
        <div style="margin-top: 2rem;">
            <div class="prompt">$ ./BootForge-Linux-x64 list-devices</div>
            <div class="output">
🔍 Scanning for USB devices...
📱 Found 0 devices (requires root privileges for full access)
💡 Run with sudo for complete device detection
            </div>
        </div>
        
        <div style="margin-top: 2rem; text-align: center;">
            <a href="/">← Back to Main Page</a>
        </div>
    </div>
</body>
</html>
"""

# Checksum verification routes
@app.route('/checksum/<filename>')
def get_checksum(filename):
    """Serve SHA256 checksum for a file"""
    checksum_file = f"{filename}.sha256"
    checksum_path = os.path.join(DIST_DIR, checksum_file)
    
    try:
        if not os.path.exists(checksum_path):
            # Generate checksum if it doesn't exist
            file_path = os.path.join(DIST_DIR, filename)
            if os.path.exists(file_path):
                checksum = verify_file_integrity(file_path)
                if checksum:
                    with open(checksum_path, 'w') as f:
                        f.write(f"{checksum}  {filename}\n")
                else:
                    return jsonify({"error": "Failed to generate checksum"}), 500
            else:
                return jsonify({"error": "File not found"}), 404
        
        with open(checksum_path, 'r') as f:
            checksum_content = f.read().strip()
            checksum = checksum_content.split()[0]
            
        return jsonify({
            "filename": filename,
            "sha256": checksum,
            "algorithm": "SHA256",
            "checksum_file": checksum_file
        })
        
    except Exception as e:
        return jsonify({"error": f"Checksum retrieval failed: {str(e)}"}), 500

@app.route('/verify/<filename>')
def verify_file(filename):
    """Verify file integrity and provide verification info"""
    file_path = os.path.join(DIST_DIR, filename)
    
    try:
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404
            
        actual_checksum = verify_file_integrity(file_path)
        if not actual_checksum:
            return jsonify({"error": "Failed to calculate checksum"}), 500
            
        # Try to get expected checksum
        checksum_file = f"{filename}.sha256"
        checksum_path = os.path.join(DIST_DIR, checksum_file)
        expected_checksum = None
        
        if os.path.exists(checksum_path):
            with open(checksum_path, 'r') as f:
                expected_checksum = f.read().strip().split()[0]
                
        verification_result = {
            "filename": filename,
            "sha256": actual_checksum,
            "verified": expected_checksum and actual_checksum == expected_checksum,
            "expected_checksum": expected_checksum,
            "file_size": os.path.getsize(file_path),
            "checksum_available": expected_checksum is not None
        }
        
        return jsonify(verification_result)
        
    except Exception as e:
        return jsonify({"error": f"Verification failed: {str(e)}"}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy", 
        "app": "BootForge Web Demo",
        "base_url": get_base_url(),
        "supported_architectures": SUPPORTED_ARCHITECTURES
    })

@app.route('/api')
def api():
    """API endpoint for health checks"""
    return jsonify({"status": "ok", "message": "BootForge Web API is running"})

@app.route('/api/health')
def api_health():
    """Alternative health check"""
    return jsonify({"status": "healthy", "service": "BootForge"})

# Installation script routes
@app.route('/install')
def install_instructions():
    """Show installation instructions for all platforms"""
    current_base_url = get_base_url()
    html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Install BootForge - One-Line Installation</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e1e1e, #2d2d2d);
            color: #ffffff;
            min-height: 100vh;
        }
        .container { 
            max-width: 1000px; 
            margin: 0 auto; 
            padding: 2rem;
        }
        .header {
            text-align: center;
            margin-bottom: 3rem;
        }
        .logo {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(45deg, #00d4ff, #0099cc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1rem;
        }
        .install-section {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 2rem;
            margin: 2rem 0;
            border: 1px solid rgba(0, 212, 255, 0.3);
        }
        .platform-title {
            color: #00d4ff;
            font-size: 1.5rem;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .command-box {
            background: #000;
            border-radius: 8px;
            padding: 1rem;
            margin: 1rem 0;
            border: 1px solid #333;
            font-family: 'Courier New', monospace;
            position: relative;
        }
        .command {
            color: #00ff00;
            font-size: 1.1rem;
            word-break: break-all;
        }
        .copy-btn {
            position: absolute;
            top: 0.5rem;
            right: 0.5rem;
            background: #00d4ff;
            color: #000;
            border: none;
            padding: 0.3rem 0.8rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .copy-btn:hover {
            background: #0099cc;
        }
        .note {
            background: rgba(255, 193, 7, 0.1);
            border: 1px solid #ffc107;
            border-radius: 8px;
            padding: 1rem;
            margin: 1rem 0;
            font-size: 0.9rem;
        }
        .security-note {
            background: rgba(40, 167, 69, 0.1);
            border: 1px solid #28a745;
            border-radius: 8px;
            padding: 1.5rem;
            margin: 2rem 0;
        }
        .back-link {
            display: inline-block;
            color: #00d4ff;
            text-decoration: none;
            margin-top: 2rem;
            padding: 0.5rem 1rem;
            border: 1px solid #00d4ff;
            border-radius: 6px;
            transition: background-color 0.2s;
        }
        .back-link:hover {
            background-color: rgba(0, 212, 255, 0.1);
        }
        .alternative {
            margin-top: 1rem;
            padding: 1rem;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 6px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="logo">⚡ Install BootForge</h1>
            <p>One-line installation for all platforms</p>
        </div>

        <div class="install-section">
            <h2 class="platform-title">🐧 Linux</h2>
            <div class="command-box">
                <code class="command">curl -fsSL {current_base_url}/install/linux | bash</code>
                <button class="copy-btn" onclick="copyToClipboard('curl -fsSL {current_base_url}/install/linux | bash')">Copy</button>
            </div>
            <div class="note">
                <strong>⚡ Features:</strong> Auto-detects architecture, creates desktop shortcuts, adds to PATH
            </div>
            <div class="alternative">
                <strong>📋 Alternative:</strong> First inspect the script<br>
                <code style="color: #00d4ff;">curl -fsSL {current_base_url}/install/linux</code>
            </div>
        </div>

        <div class="install-section">
            <h2 class="platform-title">🍎 macOS</h2>
            <div class="command-box">
                <code class="command">curl -fsSL {current_base_url}/install/macos | bash</code>
                <button class="copy-btn" onclick="copyToClipboard('curl -fsSL {current_base_url}/install/macos | bash')">Copy</button>
            </div>
            <div class="note">
                <strong>⚡ Features:</strong> Creates .app bundle in Applications, handles permissions, supports Apple Silicon
            </div>
            <div class="alternative">
                <strong>📋 Alternative:</strong> First inspect the script<br>
                <code style="color: #00d4ff;">curl -fsSL {current_base_url}/install/macos</code>
            </div>
        </div>

        <div class="install-section">
            <h2 class="platform-title">🪟 Windows</h2>
            <div class="command-box">
                <code class="command">iwr {current_base_url}/install/windows | iex</code>
                <button class="copy-btn" onclick="copyToClipboard('iwr {current_base_url}/install/windows | iex')">Copy</button>
            </div>
            <div class="note">
                <strong>⚡ Features:</strong> Creates Start Menu entries, desktop shortcuts, handles UAC, adds to PATH
            </div>
            <div class="alternative">
                <strong>📋 Alternative (PowerShell):</strong> First inspect the script<br>
                <code style="color: #00d4ff;">iwr {current_base_url}/install/windows</code>
            </div>
        </div>

        <div class="security-note">
            <h3>🔒 Security Best Practices</h3>
            <p><strong>Always inspect scripts before running them!</strong></p>
            <ul style="margin: 1rem 0; padding-left: 2rem;">
                <li>View any script first by removing the <code>| bash</code> or <code>| iex</code> part</li>
                <li>Our scripts use HTTPS and include integrity verification</li>
                <li>Scripts auto-detect your system and download appropriate versions</li>
                <li>All scripts include uninstall functionality with <code>--uninstall</code> flag</li>
            </ul>
        </div>

        <div class="install-section">
            <h2 class="platform-title">🚀 After Installation</h2>
            <div style="margin: 1rem 0;">
                <p><strong>Linux:</strong> <code>BootForge --gui</code> or search "BootForge" in applications</p>
                <p><strong>macOS:</strong> Open from Applications folder or Launchpad</p>
                <p><strong>Windows:</strong> Use Start Menu or desktop shortcut</p>
            </div>
            <div class="note">
                <strong>💡 Tip:</strong> USB operations require administrator/root privileges. Run with sudo/admin when working with USB devices.
            </div>
        </div>

        <div class="install-section">
            <h2 class="platform-title">🗑️ Uninstalling</h2>
            <p>All installation scripts support uninstallation:</p>
            <div style="margin: 1rem 0;">
                <p><strong>Linux/macOS:</strong> <code>curl -fsSL {current_base_url}/install/[platform] | bash -s -- --uninstall</code></p>
                <p><strong>Windows:</strong> <code>iwr {current_base_url}/install/windows | iex -Args --uninstall</code></p>
            </div>
        </div>

        <a href="/" class="back-link">← Back to Main Page</a>
    </div>

    <script>
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(function() {
                // Show feedback
                event.target.textContent = 'Copied!';
                setTimeout(() => {
                    event.target.textContent = 'Copy';
                }, 2000);
            }, function(err) {
                console.error('Could not copy text: ', err);
                // Fallback for older browsers
                const textArea = document.createElement('textarea');
                textArea.value = text;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
                
                event.target.textContent = 'Copied!';
                setTimeout(() => {
                    event.target.textContent = 'Copy';
                }, 2000);
            });
        }
    </script>
</body>
</html>
"""
    
    # Replace placeholders with actual base URL
    html_content = html_template.replace('{current_base_url}', current_base_url)
    return html_content

@app.route('/install/linux')
def install_linux():
    """Serve the Linux installation script with dynamic URL injection"""
    try:
        # Try secure script first, fallback to basic script
        script_paths = ['scripts/install-linux-secure.sh', 'scripts/install-linux.sh']
        script_content = None
        
        for script_path in script_paths:
            try:
                with open(script_path, 'r') as f:
                    script_content = f.read()
                break
            except FileNotFoundError:
                continue
        
        if script_content is None:
            return jsonify({
                "error": "Linux installation script not found",
                "message": "Neither secure nor basic installation script found"
            }), 404
        
        # Inject dynamic base URL
        current_base_url = get_base_url()
        script_content = script_content.replace('https://bootforge.dev', current_base_url)
        script_content = script_content.replace('BOOTFORGE_BASE_URL/install/linux', f'{current_base_url}/install/linux')
        
        return Response(script_content, mimetype='text/plain')
    except Exception as e:
        return jsonify({"error": f"Failed to serve script: {str(e)}"}), 500

@app.route('/install/macos')
def install_macos():
    """Serve the macOS installation script with dynamic URL injection"""
    try:
        # Try secure script first, fallback to basic script
        script_paths = ['scripts/install-macos-secure.sh', 'scripts/install-macos.sh']
        script_content = None
        
        for script_path in script_paths:
            try:
                with open(script_path, 'r') as f:
                    script_content = f.read()
                break
            except FileNotFoundError:
                continue
        
        if script_content is None:
            return jsonify({
                "error": "macOS installation script not found",
                "message": "Neither secure nor basic installation script found"
            }), 404
        
        # Inject dynamic base URL
        current_base_url = get_base_url()
        script_content = script_content.replace('https://bootforge.dev', current_base_url)
        script_content = script_content.replace('BOOTFORGE_BASE_URL/install/macos', f'{current_base_url}/install/macos')
        
        return Response(script_content, mimetype='text/plain')
    except Exception as e:
        return jsonify({"error": f"Failed to serve script: {str(e)}"}), 500

@app.route('/install/windows')
def install_windows():
    """Serve the Windows installation script with dynamic URL injection"""
    try:
        with open('scripts/install-windows.ps1', 'r') as f:
            script_content = f.read()
        
        # Inject dynamic base URL
        current_base_url = get_base_url()
        script_content = script_content.replace('https://bootforge.dev', current_base_url)
        script_content = script_content.replace('BOOTFORGE_BASE_URL/install/windows', f'{current_base_url}/install/windows')
        
        return Response(script_content, mimetype='text/plain')
    except FileNotFoundError:
        return jsonify({
            "error": "Windows installation script not found",
            "message": "Installation script is missing from the server"
        }), 404
    except Exception as e:
        return jsonify({"error": f"Failed to serve script: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)