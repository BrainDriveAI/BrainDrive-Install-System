"""
Cross-platform compatibility utilities for BrainDrive Installer.
Handles OS detection, path management, and platform-specific operations.
"""

import os
import sys
import platform
import subprocess
import stat
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class PlatformUtils:
    """Utility class for cross-platform operations."""
    
    @staticmethod
    def get_os_type() -> str:
        """
        Returns the operating system type.
        
        Returns:
            str: 'windows', 'macos', or 'linux'
        """
        system = platform.system().lower()
        if system == 'windows':
            return 'windows'
        elif system == 'darwin':
            return 'macos'
        elif system == 'linux':
            return 'linux'
        else:
            # Default to linux for other Unix-like systems
            return 'linux'
    
    @staticmethod
    def get_home_directory() -> Path:
        """
        Get the user's home directory in a cross-platform way.
        
        Returns:
            Path: User's home directory path
        """
        return Path.home()
    
    @staticmethod
    def get_braindrive_base_path() -> str:
        """
        Get the base path for BrainDrive installation.
        
        Returns:
            str: Platform-appropriate base path
        """
        home = PlatformUtils.get_home_directory()
        return str(home / "BrainDrive")
    
    @staticmethod
    def get_executable_directory() -> str:
        """
        Determine the directory containing the running executable or script.

        Returns:
            str: Absolute path to the executable directory.
        """
        if getattr(sys, "frozen", False):
            # PyInstaller executable
            return os.path.dirname(sys.executable)

        executable_path = os.path.abspath(sys.argv[0]) if sys.argv else os.getcwd()
        if os.path.isdir(executable_path):
            return executable_path
        return os.path.dirname(executable_path)
    
    @staticmethod
    def get_executable_extension() -> str:
        """
        Get the executable file extension for the current platform.
        
        Returns:
            str: '.exe' for Windows, empty string for Unix-like systems
        """
        return '.exe' if PlatformUtils.get_os_type() == 'windows' else ''

    @staticmethod
    def ensure_writable(path: str) -> None:
        """
        Recursively clear read-only flags so files/directories can be moved or deleted.
        Primarily used on Windows where Git pack files may be marked read-only.
        """
        if not path:
            return

        target = Path(path)
        if not target.exists():
            return

        for entry in [target, *target.rglob('*')]:
            try:
                mode = entry.stat().st_mode
                os.chmod(entry, mode | stat.S_IWRITE)
            except Exception:
                # Ignore entries we cannot modify; best effort only.
                continue
    
    @staticmethod
    def get_conda_executable_name() -> str:
        """
        Get the conda executable name for the current platform.
        
        Returns:
            str: 'conda.exe' for Windows, 'conda' for Unix-like systems
        """
        return 'conda.exe' if PlatformUtils.get_os_type() == 'windows' else 'conda'
    
    @staticmethod
    def get_python_executable_name() -> str:
        """
        Get the Python executable name for the current platform.
        
        Returns:
            str: 'python.exe' for Windows, 'python' for Unix-like systems
        """
        return 'python.exe' if PlatformUtils.get_os_type() == 'windows' else 'python'
    
    @staticmethod
    def get_npm_executable_name() -> str:
        """
        Get the npm executable name for the current platform.
        
        Returns:
            str: 'npm.cmd' for Windows, 'npm' for Unix-like systems
        """
        return 'npm.cmd' if PlatformUtils.get_os_type() == 'windows' else 'npm'
    
    @staticmethod
    def get_git_executable_name() -> str:
        """
        Get the git executable name for the current platform.
        
        Returns:
            str: 'git.exe' for Windows, 'git' for Unix-like systems
        """
        return 'git.exe' if PlatformUtils.get_os_type() == 'windows' else 'git'
    
    @staticmethod
    def create_no_window_flags() -> Dict:
        """
        Create platform-specific process creation flags to hide console windows.
        
        Returns:
            Dict: Flags for subprocess.Popen
        """
        if PlatformUtils.get_os_type() == 'windows':
            import subprocess
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            return {
                'creationflags': subprocess.CREATE_NO_WINDOW,
                'startupinfo': startupinfo
            }
        else:
            return {}
    
    @staticmethod
    def get_default_shell() -> Optional[str]:
        """
        Get the default shell for subprocess operations.
        
        Returns:
            Optional[str]: Shell path or None for default
        """
        os_type = PlatformUtils.get_os_type()
        if os_type == 'windows':
            return None  # Use default cmd.exe
        elif os_type == 'macos':
            return '/bin/bash'
        else:  # linux
            return '/bin/bash'
    
    @staticmethod
    def get_path_separator() -> str:
        """
        Get the path separator for the current platform.
        
        Returns:
            str: ';' for Windows, ':' for Unix-like systems
        """
        return ';' if PlatformUtils.get_os_type() == 'windows' else ':'
    
    @staticmethod
    def normalize_path(path: str) -> str:
        """
        Normalize a path for the current platform.
        
        Args:
            path: Path to normalize
            
        Returns:
            str: Normalized path
        """
        return os.path.normpath(path)
    
    @staticmethod
    def join_paths(*paths: str) -> str:
        """
        Join multiple path components in a cross-platform way.
        
        Args:
            *paths: Path components to join
            
        Returns:
            str: Joined path
        """
        return os.path.join(*paths)
    
    @staticmethod
    def get_environment_activation_command(env_name: str) -> List[str]:
        """
        Get the command to activate a conda environment.
        
        Args:
            env_name: Name of the conda environment
            
        Returns:
            List[str]: Command components for environment activation
        """
        os_type = PlatformUtils.get_os_type()
        conda_exe = PlatformUtils.get_conda_executable_name()
        
        if os_type == 'windows':
            return [conda_exe, 'activate', env_name]
        else:
            return ['conda', 'activate', env_name]
    
    @staticmethod
    def get_conda_create_command(env_name: str, python_version: str = "3.11") -> List[str]:
        """
        Get the command to create a conda environment.
        
        Args:
            env_name: Name of the environment to create
            python_version: Python version to install
            
        Returns:
            List[str]: Command components for environment creation
        """
        conda_exe = PlatformUtils.get_conda_executable_name()
        return [
            conda_exe, 'create', '-n', env_name, 
            f'python={python_version}', 'nodejs', 'git', '-y'
        ]
    
    @staticmethod
    def is_command_available(command: str) -> bool:
        """
        Check if a command is available in the system PATH.
        
        Args:
            command: Command to check
            
        Returns:
            bool: True if command is available, False otherwise
        """
        try:
            subprocess.run(
                [command, '--version'], 
                capture_output=True, 
                check=True,
                **PlatformUtils.create_no_window_flags()
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    @staticmethod
    def get_system_info() -> Dict[str, str]:
        """
        Get comprehensive system information.
        
        Returns:
            Dict[str, str]: System information dictionary
        """
        return {
            'os_type': PlatformUtils.get_os_type(),
            'platform': platform.platform(),
            'architecture': platform.architecture()[0],
            'machine': platform.machine(),
            'processor': platform.processor(),
            'python_version': platform.python_version(),
            'home_directory': str(PlatformUtils.get_home_directory()),
            'base_path': PlatformUtils.get_braindrive_base_path()
        }
    
    @staticmethod
    def create_directory_if_not_exists(path: str) -> bool:
        """
        Create a directory if it doesn't exist.
        
        Args:
            path: Directory path to create
            
        Returns:
            bool: True if directory was created or already exists, False on error
        """
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"Error creating directory {path}: {e}")
            return False
    
    @staticmethod
    def get_free_disk_space(path: str) -> int:
        """
        Get free disk space for a given path in bytes.
        
        Args:
            path: Path to check disk space for
            
        Returns:
            int: Free disk space in bytes
        """
        try:
            if PlatformUtils.get_os_type() == 'windows':
                import shutil
                return shutil.disk_usage(path).free
            else:
                import shutil
                return shutil.disk_usage(path).free
        except Exception:
            return 0
    
    @staticmethod
    def format_bytes(bytes_value: int) -> str:
        """
        Format bytes into human-readable format.
        
        Args:
            bytes_value: Number of bytes
            
        Returns:
            str: Formatted string (e.g., "1.5 GB")
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
