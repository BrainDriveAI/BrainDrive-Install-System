# BrainDrive Installer

A cross-platform GUI installer for setting up and managing BrainDrive AI platform with automated environment configuration and dual-server management.

---

## Overview

**BrainDrive Installer** is a Python-based GUI application that simplifies the installation and management of the BrainDrive AI platform. It automatically handles all dependencies, creates optimized environments, and provides an intuitive interface for managing both backend and frontend servers.

## Features

- **Cross-Platform Support:** Works seamlessly on Windows, macOS, and Linux
- **Automated Environment Setup:** Creates conda environments with Python 3.11, Node.js, and Git
- **BrainDrive Installation:** Clones and configures the complete BrainDrive platform
- **Dual Server Management:** Manages both FastAPI backend (port 8005) and React frontend (port 5173)
- **Plugin System:** Automatically builds and configures BrainDrive plugins
- **Graphical User Interface:** Intuitive interface for installation, updates, and server management
- **Process Management:** Advanced process lifecycle management with monitoring
- **Error Recovery:** Robust error handling and recovery mechanisms
- **Desktop Integration:** Optional desktop shortcuts and system integration

---

## Quick Start

### Download and Run

1. **Download the Installer:**
   - Visit the [Releases](https://github.com/BrainDriveAI/BrainDriveInstaller/releases) page
   - Download the appropriate installer for your operating system:
     - Windows: `BrainDriveInstaller-Windows.exe`
     - macOS: `BrainDriveInstaller-macOS.app`
     - Linux: `BrainDriveInstaller-Linux`

2. **Run the Installer:**
   - Double-click the downloaded file to launch the installer
   - Follow the on-screen instructions

### From Source

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/BrainDriveAI/BrainDriveInstaller.git
   cd BrainDriveInstaller
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Application:**
   ```bash
   python main_interface.py
   ```

---

## System Requirements

### Minimum Requirements
- **Operating System:** Windows 10+, macOS 10.14+, or Linux (Ubuntu 18.04+)
- **RAM:** 4 GB minimum, 8 GB recommended
- **Storage:** 10 GB free space for installation
- **Network:** Internet connection for downloading dependencies

### Supported Platforms
- **Windows:** 10, 11 (x64)
- **macOS:** 10.14+ (Intel and Apple Silicon)
- **Linux:** Ubuntu 18.04+, CentOS 7+, Debian 10+

### Dependencies (Automatically Installed)
- **Miniconda/Conda:** Python environment management
- **Git:** Version control for repository operations
- **Node.js:** JavaScript runtime for frontend
- **Python 3.11:** Backend runtime environment

---

## Usage Guide

### Installation Process

1. **Launch the Application:**
   - Run the installer executable or `python main_interface.py`

2. **Install BrainDrive:**
   - Click the **"Install BrainDrive"** button
   - The installer will automatically:
     - Download and install Miniconda (if needed)
     - Create a conda environment with Python 3.11, Node.js, and Git
     - Clone the BrainDrive repository
     - Build all plugins
     - Install backend dependencies
     - Install frontend dependencies
     - Configure environment files

3. **Start BrainDrive:**
   - Once installation is complete, click **"Start BrainDrive"**
   - The installer will launch both servers:
     - Backend server: `http://localhost:8005`
     - Frontend server: `http://localhost:5173`
   - Your default browser will open to the BrainDrive interface

4. **Manage BrainDrive:**
   - **Update:** Click "Update BrainDrive" to get the latest version
   - **Stop:** Click "Stop BrainDrive" to shut down all services
   - **Restart:** Stop and start again to restart services

### Advanced Features

- **Environment Management:** Automatic conda environment creation and management
- **Plugin Building:** Automatic discovery and building of BrainDrive plugins
- **Process Monitoring:** Real-time monitoring of backend and frontend processes
- **Error Recovery:** Automatic recovery from common installation issues
- **Cross-Platform Paths:** Intelligent path handling across different operating systems

---

## Architecture

### Core Components

- **Platform Utils:** Cross-platform compatibility layer
- **Git Manager:** Repository operations and version control
- **Node Manager:** Node.js and npm operations
- **Process Manager:** Service lifecycle management
- **Plugin Builder:** Automatic plugin discovery and building
- **Configuration Manager:** Environment and settings management

### Installation Workflow

1. **Prerequisites Check:** Verify system requirements
2. **Environment Setup:** Create conda environment with dependencies
3. **Repository Clone:** Download BrainDrive source code
4. **Plugin Building:** Build all available plugins
5. **Backend Setup:** Install Python dependencies and configure
6. **Frontend Setup:** Install npm dependencies and configure
7. **Service Management:** Start and monitor both servers

---

## Troubleshooting

### Common Issues

**Installation Fails:**
- Ensure you have sufficient disk space (10+ GB)
- Check internet connection for downloading dependencies
- Run as administrator/sudo if permission errors occur

**Servers Won't Start:**
- Check if ports 8005 and 5173 are available
- Verify conda environment was created successfully
- Check the application logs for specific error messages

**Plugin Build Errors:**
- Ensure Node.js is properly installed in the conda environment
- Check for any missing build dependencies
- Try running the installation again

For more detailed troubleshooting, see [docs/troubleshooting.md](docs/troubleshooting.md).

---

## Development

### Building from Source

1. **Setup Development Environment:**
   ```bash
   git clone https://github.com/BrainDriveAI/BrainDriveInstaller.git
   cd BrainDriveInstaller
   pip install -r requirements.txt
   ```

2. **Run Tests:**
   ```bash
   python -m pytest tests/
   ```

3. **Build Executable:**
   ```bash
   # Windows
   build-windows.bat
   
   # macOS
   ./build-macos.sh
   
   # Linux
   ./build-linux.sh
   ```

For detailed development instructions, see [docs/development-setup.md](docs/development-setup.md).

---

## Contributing

We welcome contributions! Please see our [Contributing Guide](docs/contributing.md) for details on:

- Setting up the development environment
- Code style and standards
- Testing requirements
- Pull request process

### Quick Contribution Steps

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes and add tests
4. Run the test suite: `python -m pytest`
5. Commit your changes: `git commit -m "Add your feature description"`
6. Push to your fork: `git push origin feature/your-feature-name`
7. Open a pull request

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Support

- **Documentation:** [docs/](docs/)
- **Issues:** [GitHub Issues](https://github.com/BrainDriveAI/BrainDriveInstaller/issues)
- **Discussions:** [GitHub Discussions](https://github.com/BrainDriveAI/BrainDriveInstaller/discussions)

---

## Acknowledgments

- [BrainDrive](https://github.com/BrainDriveAI/BrainDrive) - The AI platform this installer manages
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html) - Python environment management
- [PyInstaller](https://pyinstaller.org/) - Executable packaging
- [Tkinter](https://docs.python.org/3/library/tkinter.html) - GUI framework

---

## Version Information

**Current Version:** 1.0.2  
**BrainDrive Compatibility:** Latest  
**Last Updated:** February 2025

For version history and release notes, see [CHANGELOG.md](CHANGELOG.md).
