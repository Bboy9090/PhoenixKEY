#!/usr/bin/env python3
"""
BootForge Web Demo Server
Simple web interface to showcase BootForge capabilities and serve downloads
"""

from flask import Flask, render_template, jsonify, send_from_directory
import os
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

app = Flask(__name__)

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
            <strong>✅ Ready for Distribution:</strong> Linux executable and USB package are ready for download. 
            The USB package includes auto-installers for all platforms and works on Windows/Mac/Linux computers.
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
            <a href="/download/linux" class="download-btn available">📱 Linux (64-bit) - Ready!</a>
            <a href="/download/usb-package" class="download-btn available">💾 USB Package - All Platforms</a>
            <a href="#" class="download-btn coming-soon" onclick="alert('Windows build coming soon!')">🪟 Windows - Coming Soon</a>
            <a href="#" class="download-btn coming-soon" onclick="alert('macOS build coming soon!')">🍎 macOS - Coming Soon</a>
            <a href="/cli-demo" class="download-btn">🔧 CLI Demo</a>
            <p style="margin-top: 1rem; color: #cccccc;">
                Cross-platform builds will be available soon
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

@app.route('/download/linux')
def download_linux():
    """Serve the Linux executable"""
    try:
        return send_from_directory('dist', 'BootForge-Linux-x64', as_attachment=True, 
                                 download_name='BootForge-Linux-x64')
    except FileNotFoundError:
        return jsonify({"error": "Linux executable not found. Build in progress."}), 404
    except Exception as e:
        return jsonify({"error": f"Download failed: {str(e)}"}), 500

@app.route('/download/usb-package')
def download_usb_package():
    """Serve the complete USB distribution package"""
    try:
        return send_from_directory('dist', 'BootForge-USB-Package.tar.gz', as_attachment=True, 
                                 download_name='BootForge-USB-Package.tar.gz')
    except FileNotFoundError:
        return jsonify({"error": "USB package not found. Build in progress."}), 404
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

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "app": "BootForge Web Demo"})

@app.route('/api')
def api():
    """API endpoint for health checks"""
    return jsonify({"status": "ok", "message": "BootForge Web API is running"})

@app.route('/api/health')
def api_health():
    """Alternative health check"""
    return jsonify({"status": "healthy", "service": "BootForge"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)