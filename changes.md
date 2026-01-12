# BrainDrive Installer - macOS Fixes Changelog

This document details the issues discovered and fixes applied to make the macOS DMG installer functional.

---

## Overview

The Windows installer was working correctly, but the macOS DMG was crashing on launch and failing during installation. After investigation, we identified and fixed 6 distinct issues.

---

## Issue #1: App Crashes on Launch - Read-Only Filesystem

### Error
```
PermissionError: [Errno 1] Operation not permitted: '/Volumes/BrainDrive Installer/BrainDriveInstaller.app/Contents/MacOS/logs'
```

### Root Cause
When running from a mounted DMG, the application bundle is on a **read-only filesystem**. The logger was attempting to create a `logs/` directory inside the app bundle, which fails on macOS.

### Fix
Modified `installer_logger.py` to detect when running from a read-only location and use a writable alternative:

**File:** `app-installer/common/src/braindrive_installer/core/installer_logger.py`

```python
@staticmethod
def _get_writable_log_dir():
    """Find a writable directory for logs, with macOS DMG support."""
    
    # On macOS, prefer ~/Library/Logs for app logs
    if sys.platform == 'darwin':
        mac_log_dir = Path.home() / "Library" / "Logs" / "BrainDriveInstaller"
        try:
            mac_log_dir.mkdir(parents=True, exist_ok=True)
            test_file = mac_log_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
            return mac_log_dir
        except (PermissionError, OSError):
            pass
    
    # Fallback chain for other platforms or if macOS path fails
    # ... additional fallbacks
```

**Log location on macOS:** `~/Library/Logs/BrainDriveInstaller/`

---

## Issue #2: Wrong Miniconda Architecture for Apple Silicon

### Error
```
Command failed: bash MinicondaInstaller.sh -b -p /Users/.../miniconda3
Return Code: 1
```

### Root Cause
The installer was downloading the **x86_64** version of Miniconda on **Apple Silicon (ARM64)** Macs. The x86_64 binary cannot run natively on ARM64.

### Fix
Added architecture detection in `installer_miniconda.py`:

**File:** `app-installer/common/src/braindrive_installer/installers/installer_miniconda.py`

```python
import platform

machine_arch = platform.machine().lower()

if os_type == 'macos':
    self.installer_filename = "MinicondaInstaller.sh"
    if machine_arch == 'arm64':
        self.miniconda_url = "https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh"
    else:
        self.miniconda_url = "https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh"
```

---

## Issue #3: SSL Certificate Verification Failed

### Error
```
SSL: CERTIFICATE_VERIFY_FAILED - unable to get local issuer certificate
```

### Root Cause
PyInstaller bundles don't include system SSL certificates. When the app tries to download Miniconda via HTTPS, SSL verification fails because it can't find the CA certificates.

### Fix
1. Added `certifi` package to provide CA certificates
2. Created SSL context using certifi's certificate bundle

**File:** `app-installer/common/src/braindrive_installer/installers/installer_miniconda.py`

```python
import ssl
import certifi

SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

# In download_installer():
with urllib.request.urlopen(self.miniconda_url, context=SSL_CONTEXT) as response:
    # ... download code
```

**File:** `app-installer/macos/braindrive-installer-macos.spec`

```python
import certifi
datas += collect_data_files('certifi')
hiddenimports += ['certifi']
```

---

## Issue #4: Miniconda Installer Fails on Existing Directory

### Error
```
Command failed: bash MinicondaInstaller.sh -b -p /Users/.../miniconda3
Return Code: 1
```

### Root Cause
The Miniconda installer refuses to install into an **existing directory**. If a previous installation attempt failed partway through, the directory would exist but be incomplete, causing subsequent attempts to fail.

### Fix
Remove the target directory before running the Miniconda installer:

**File:** `app-installer/common/src/braindrive_installer/installers/installer_miniconda.py`

```python
# Before running installer, remove existing directory if present
if os.path.exists(self.miniconda_path):
    self.log_status(f"Removing existing miniconda directory: {self.miniconda_path}")
    import shutil
    shutil.rmtree(self.miniconda_path)
```

---

## Issue #5: Requirements Check Fails for Conda/Node

### Error
```
Missing requirements: Node.js and npm, Conda/Miniconda
```

### Root Cause
After Miniconda is installed, the requirements check was looking for `conda` and `node` in the **system PATH**. However, they're installed in the Miniconda directory which isn't in PATH.

### Fix
Modified the check methods to look in the installed Miniconda path:

**File:** `app-installer/common/src/braindrive_installer/core/base_installer.py`

```python
def check_conda_available(self):
    """Check if Conda is available in PATH or installed location."""
    # First check PATH
    conda_cmd = "conda"
    try:
        result = subprocess.run([conda_cmd, "--version"], ...)
        if result.returncode == 0:
            return True
    except FileNotFoundError:
        pass
    
    # Check installed location
    if hasattr(self, 'config') and self.config.conda_exe:
        if os.path.exists(self.config.conda_exe):
            return True
    
    return False
```

Also removed the Node.js check from initial requirements since Node is installed **as part of** the conda environment setup (which happens after the requirements check).

---

## Issue #6: npm Not Found When Starting Frontend

### Error
```
Failed to start frontend server: [Errno 2] No such file or directory: 'npm'
```

### Root Cause
The frontend start command used `npm` directly, but npm is installed inside the conda environment and not in the system PATH.

**Original code:**
```python
npm_cmd = PlatformUtils.get_npm_executable_name()  # Returns "npm"
frontend_cmd = [npm_cmd, "run", "dev", ...]  # npm not in PATH!
```

### Fix
Use `conda run` to execute npm from within the conda environment:

**File:** `app-installer/common/src/braindrive_installer/installers/installer_braindrive.py`

```python
# For npm install during setup:
npm_install_cmd = [
    self.config.conda_exe,
    "run", "--prefix", env_path,
    "npm", "install", "--no-audit", "--no-fund"
]

# For starting frontend:
frontend_cmd = [
    conda_cmd, "run", "--prefix", self.env_prefix,
    "npm", "run", "dev", "--", "--host", self.frontend_host, "--port", str(self.frontend_port)
]
```

This ensures npm runs within the correct conda environment where it's installed.

---

## Files Modified

| File | Changes |
|------|---------|
| `core/installer_logger.py` | Writable log directory detection for macOS |
| `core/base_installer.py` | Check conda/node in installed path, not just PATH |
| `installers/installer_miniconda.py` | ARM64 detection, SSL fix, remove existing dir |
| `installers/installer_braindrive.py` | Use `conda run` for npm operations |
| `macos/braindrive-installer-macos.spec` | Bundle certifi for SSL certificates |
| `macos/build-macos.sh` | Use conda environment for building |

---

## Windows Compatibility

All changes are **backward compatible** with Windows:

- Log directory fallback has Windows-specific paths
- Architecture detection only affects macOS/Linux (Windows uses x86_64)
- SSL certifi fix is cross-platform
- `conda run` approach works identically on Windows

The Windows installer should continue to work without issues.

---

## Testing

After applying all fixes:
1. ✅ DMG opens without crashing
2. ✅ Installation completes successfully
3. ✅ Miniconda downloads correct architecture
4. ✅ Conda environment created with Python, Node.js, Git
5. ✅ Backend starts successfully
6. ✅ Frontend starts successfully
7. ✅ BrainDrive accessible at configured ports
