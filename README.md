# BrainDrive Installer

[![License](https://img.shields.io/badge/License-MIT%20License-green.svg)](LICENSE)

One-click setup for your [BrainDrive](https://BrainDrive.ai) self-hosted AI platform. 

BrainDrive Installer is a cross-platform GUI application that automates the complete setup of BrainDrive and provides 1-click updated. It handles all dependency installation, environment configuration, and service management—so you can get your BrainDrive running in minutes.

## What It Does

- **Automates Everything**: Downloads and configures Miniconda, Python, Node.js, Git, and the entire BrainDrive platform
- **Manages Services**: Start, stop, and monitor BrainDrive's backend (FastAPI) and frontend (React) servers
- **Cross-Platform**: Works on Windows 10/11, macOS 10.14+, and Linux (Ubuntu 18.04+, Debian 10+, CentOS 7+)
- **Plugin Ready**: Automatically builds and configures all BrainDrive plugins during installation

## Quick Start

### For End Users

1. **Download** the installer for your OS from [GitHub Releases](https://github.com/BrainDriveAI/BrainDrive-Install-System/releases)
   - Windows: `BrainDriveInstaller-win-x64.exe`
   - macOS: `BrainDriveInstaller-macos-universal.dmg`

2. **Run** the installer
   - **Windows**: Double-click the `.exe` (you may need to bypass SmartScreen)
   - **macOS**: Right-click the app and select "Open" (required for unsigned apps)

3. **Install** by clicking "Install BrainDrive" and following on-screen prompts

4. **Launch** BrainDrive from the installer when setup completes

**System Requirements**: 4GB RAM minimum (8GB recommended), 10GB free disk space, internet connection for initial setup

### For Developers

**Clone and set up:**

```bash
git clone https://github.com/BrainDriveAI/BrainDrive-Install-System.git
cd BrainDrive-Install-System

# Create environment
conda env create -f environment.yml
conda activate BrainDriveInstaller
```

**Run from source:**

```bash
python app-installer/common/src/braindrive_installer/ui/main_interface.py
```

**Build installers:**

```bash
# Windows
app-installer/windows/build-windows.bat

# macOS
bash app-installer/macos/build-macos.sh

# Linux
bash app-installer/ubuntu/build-linux.sh
```

Builds output to `dist/` directory.

## How It Works

The installer follows this flow:

1. **Check prerequisites** and system requirements
2. **Install Miniconda** (if not present) with Python 3.11, Node.js, and Git
3. **Clone BrainDrive** repository from GitHub
4. **Install dependencies** for both backend (pip) and frontend (npm)
5. **Build plugins** automatically
6. **Generate configuration** files (.env) for both services
7. **Launch services** and open BrainDrive in your browser

All actions are logged to `logs/BrainDriveInstaller_<timestamp>.log` for troubleshooting.

## Configuration

Settings are managed through:

- **GUI Settings Dialog**: Adjust ports, enable/disable features, modify theme
- **JSON Settings File**: `braindrive_settings.json` (persists between runs)
- **Environment Files**: Generated `.env` files for backend and frontend (auto-created from templates)

Default configuration:
- Backend: `localhost:8005`
- Frontend: `localhost:5173`
- Install path: `~/BrainDrive` (Linux/macOS) or `C:\Users\<Name>\BrainDrive` (Windows)

## Contributing

We welcome contributions! To get started:

1. Fork the repository and create a feature branch
2. Follow existing code style (PEP8 for Python)
3. Add tests for new features (`python -m pytest`)
4. Submit a pull request with a clear description

See our [Contributing Guide](https://docs.braindrive.ai/core/CONTRIBUTING) for details.

## Platform-Specific Notes

**Windows**
- Runs without admin rights (installs to user directory)
- May trigger SmartScreen warning (app is not yet code-signed)

**macOS**
- Currently unsigned—use Right-click → Open on first launch
- Supports both Intel and Apple Silicon

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port already in use | Edit `.env` files to change ports, or stop conflicting services |
| Package install fails | Run `pip install --upgrade pip` and retry |
| Module not found | Verify environment is activated: `conda activate BrainDriveInstaller` |
| macOS won't open app | Use Right-click → Open (required for unsigned apps) |

For more help, visit [community.braindrive.ai](https://community.braindrive.ai)

## License

MIT License. See [LICENSE](LICENSE) for details.

## Links

- [BrainDrive Core](https://github.com/BrainDriveAI/BrainDrive-Core)
- [Documentation](https://docs.braindrive.ai)
- [Community Forum](https://community.braindrive.ai)
- [Releases](https://github.com/BrainDriveAI/BrainDrive-Install-System/releases)

---

**Your AI. Your Rules.**

