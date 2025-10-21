import os
import tempfile
import sys

from braindrive_installer.core.installer_state import InstallerState
from braindrive_installer.ui.status_updater import StatusUpdater
from braindrive_installer.core.platform_utils import PlatformUtils

class AppConfig:
    _instance = None

    def __new__(cls, base_path=None):
        if not cls._instance:
            cls._instance = super(AppConfig, cls).__new__(cls)
            cls._instance._initialize(base_path)
        return cls._instance

    def _initialize(self, base_path):
        if not hasattr(self, "base_path"):  # Prevent reinitialization
            resolved_base = base_path or self.get_default_base_path()
            self._configure_paths(resolved_base)
            # Initialize status components
            self._status_display = None
            self._status_updater = None

    def _configure_paths(self, base_path):
        """Compute and cache path attributes derived from the base path."""
        self.base_path = base_path
        self.miniconda_path = PlatformUtils.join_paths(self.base_path, "miniconda3")
        self.env_path = PlatformUtils.join_paths(self.base_path, "BrainDriveInstaller")

        # BrainDrive specific paths
        self.repo_path = PlatformUtils.join_paths(self.base_path, "BrainDrive")
        self.backend_path = PlatformUtils.join_paths(self.repo_path, "backend")
        self.frontend_path = PlatformUtils.join_paths(self.repo_path, "frontend")
        self.plugins_path = PlatformUtils.join_paths(self.repo_path, "plugins")

        # Cross-platform conda executable path
        if PlatformUtils.get_os_type() == 'windows':
            self.conda_exe = PlatformUtils.join_paths(self.miniconda_path, "Scripts", "conda.exe")
        else:
            self.conda_exe = PlatformUtils.join_paths(self.miniconda_path, "bin", "conda")

    @staticmethod
    def get_default_base_path():
        """
        Determines the default base path for BrainDrive installation:
        - Cross-platform: Uses user's home directory with 'BrainDrive' folder
        - Handles PyInstaller executable and script execution modes
        """
        executable_dir = PlatformUtils.get_executable_directory()
        saved_path = InstallerState.get_install_path(current_installer_dir=executable_dir)
        if saved_path:
            normalized = os.path.abspath(saved_path)
            temp_root = os.path.abspath(tempfile.gettempdir())
            try:
                under_temp = os.path.commonpath([normalized, temp_root]) == temp_root
            except ValueError:
                under_temp = False
            if os.path.isdir(normalized) or not under_temp:
                return normalized

        executable_dir = PlatformUtils.get_executable_directory()
        if executable_dir and os.path.isdir(executable_dir):
            return executable_dir
        return PlatformUtils.get_braindrive_base_path()

    def set_base_path(self, base_path):
        """
        Update the base path and refresh all derived paths.
        """
        if not base_path or (hasattr(self, "base_path") and self.base_path == base_path):
            return
        self._configure_paths(base_path)

    @property
    def is_miniconda_installed(self):
        """
        Checks if Miniconda is installed by verifying the presence of conda.exe.
        """
        return os.path.exists(self.conda_exe)

    @property
    def has_braindrive_env(self):
        """
        Checks if the BrainDrive installer environment is set up.
        Ensures Miniconda is installed first.
        """
        if not self.is_miniconda_installed:
            print("Miniconda is not installed.")
            return False
        if not os.path.exists(self.env_path):
            print("BrainDrive installer environment is not set up.")
            return False
        return True

    @property
    def has_braindrive_repo(self):
        """
        Checks if the BrainDrive repository is cloned.
        """
        if not os.path.exists(self.repo_path):
            print("BrainDrive repository is not cloned.")
            return False
        
        # Check for key files to ensure it's a valid BrainDrive repo
        backend_main = PlatformUtils.join_paths(self.backend_path, "main.py")
        frontend_package = PlatformUtils.join_paths(self.frontend_path, "package.json")
        
        if not os.path.exists(backend_main):
            print("BrainDrive backend not found.")
            return False
        if not os.path.exists(frontend_package):
            print("BrainDrive frontend not found.")
            return False
        
        return True

    @property
    def braindrive_repo_url(self):
        """
        Returns the BrainDrive repository URL.
        """
        return "https://github.com/BrainDriveAI/BrainDrive.git"

    @property
    def backend_env_file(self):
        """
        Returns the path to the backend .env file.
        """
        return PlatformUtils.join_paths(self.backend_path, ".env")

    @property
    def frontend_env_file(self):
        """
        Returns the path to the frontend .env file.
        """
        return PlatformUtils.join_paths(self.frontend_path, ".env")

    @property
    def backend_requirements_file(self):
        """
        Returns the path to the backend requirements.txt file.
        """
        return PlatformUtils.join_paths(self.backend_path, "requirements.txt")

    @property
    def frontend_package_file(self):
        """
        Returns the path to the frontend package.json file.
        """
        return PlatformUtils.join_paths(self.frontend_path, "package.json")

    @property
    def status_display(self):
        """Get or create the StatusDisplay."""
        if self._status_display is None:
            raise AttributeError("StatusDisplay has not been initialized.")
        return self._status_display

    @status_display.setter
    def status_display(self, display):
        """Set the StatusDisplay and initialize StatusUpdater."""
        self._status_display = display
        components = display.get_components()
        self._status_updater = StatusUpdater(*components)

    @property
    def status_updater(self):
        """Access the StatusUpdater."""
        if self._status_updater is None:
            raise AttributeError("StatusUpdater has not been initialized.")
        return self._status_updater

    def start_spinner(self):
        """Start the spinner."""
        if hasattr(self.status_display, "spinner"):
            self.status_display.spinner.start()

    def stop_spinner(self):
        """Stop the spinner."""
        if hasattr(self.status_display, "spinner"):
            self.status_display.spinner.stop()


    def get_system_info(self):
        """
        Get comprehensive system and configuration information.
        """
        system_info = PlatformUtils.get_system_info()
        config_info = {
            'base_path': self.base_path,
            'miniconda_path': self.miniconda_path,
            'env_path': self.env_path,
            'repo_path': self.repo_path,
            'backend_path': self.backend_path,
            'frontend_path': self.frontend_path,
            'plugins_path': self.plugins_path,
            'conda_exe': self.conda_exe,
            'miniconda_installed': self.is_miniconda_installed,
            'braindrive_env_ready': self.has_braindrive_env,
            'braindrive_repo_ready': self.has_braindrive_repo
        }
        return {**system_info, **config_info}

    def __str__(self):
        """
        String representation for debugging.
        """
        return (
            f"Base Path: {self.base_path}\n"
            f"Miniconda Path: {self.miniconda_path}\n"
            f"BrainDrive Installer Environment: {self.env_path}\n"
            f"BrainDrive Repository: {self.repo_path}\n"
            f"Backend Path: {self.backend_path}\n"
            f"Frontend Path: {self.frontend_path}\n"
            f"Plugins Path: {self.plugins_path}\n"
            f"Conda Executable: {self.conda_exe}\n"
            f"OS Type: {PlatformUtils.get_os_type()}\n"
        )
