from abc import ABC, abstractmethod
from braindrive_installer.config.AppConfig import AppConfig
from braindrive_installer.core.platform_utils import PlatformUtils
from braindrive_installer.core.installer_logger import get_installer_logger

class BaseInstaller(ABC):
    """
    Abstract base class for handling system installations and configurations.
    """

    def __init__(self, name, status_updater=None, base_path=None):
        self.name = name
        self.status_updater = status_updater
        self._is_installed = False
        self._has_env = False
        self.config = AppConfig(base_path=base_path)
        self.logger = get_installer_logger()

    def set_status_updater(self, status_updater):
        """
        Update the status updater for this installer instance.
        """
        self.status_updater = status_updater

    @property
    def is_installed(self):
        """
        Property to check if the system is installed.
        This should be overridden by subclasses with specific checks.
        """
        return self._is_installed

    @property
    def has_env(self):
        """
        Property to check if the required environment is set up.
        This should be overridden by subclasses with specific checks.
        """
        return self._has_env


    @abstractmethod
    def check_installed(self):
        """
        Check if the system is already installed.
        :return: Boolean indicating installation status.
        """
        pass

    @abstractmethod
    def install(self):
        """
        Install the system.
        """
        pass

    @abstractmethod
    def check_requirements(self):
        """
        Check if all pre-installation requirements are met.
        :return: Boolean indicating readiness to install.
        """
        pass

    @abstractmethod
    def setup_environment(self, env_name):
        """
        Set up the required environment for the system.
        :param env_name: The name of the environment to set up.
        """
        pass

    @abstractmethod
    def update(self):
        """
        Update the system to the latest version.
        """
        pass

    @abstractmethod
    def clone_repository(self, repo_url, target_path, branch="main"):
        """
        Clone a Git repository to the specified path.
        :param repo_url: URL of the repository to clone
        :param target_path: Local path where repository should be cloned
        :param branch: Branch to clone (default: main)
        :return: Boolean indicating success
        """
        pass

    @abstractmethod
    def build_plugins(self):
        """
        Build application plugins using Node.js/npm.
        :return: Boolean indicating success
        """
        pass

    @abstractmethod
    def start_services(self):
        """
        Start application services (backend and frontend servers).
        :return: Boolean indicating success
        """
        pass

    @abstractmethod
    def stop_services(self):
        """
        Stop all running application services.
        :return: Boolean indicating success
        """
        pass

    def check_git_available(self):
        """
        Check if Git is available on the system.
        :return: Boolean indicating Git availability
        """
        git_cmd = PlatformUtils.get_git_executable_name()
        return PlatformUtils.is_command_available(git_cmd)

    def check_node_available(self):
        """
        Check if Node.js and npm are available on the system.
        :return: Boolean indicating Node.js availability
        """
        node_available = PlatformUtils.is_command_available('node')
        npm_cmd = PlatformUtils.get_npm_executable_name()
        npm_available = PlatformUtils.is_command_available(npm_cmd)
        return node_available and npm_available

    def check_conda_available(self):
        """
        Check if Conda is available on the system.
        :return: Boolean indicating Conda availability
        """
        conda_cmd = PlatformUtils.get_conda_executable_name()
        return PlatformUtils.is_command_available(conda_cmd)

    def get_system_requirements_status(self):
        """
        Get the status of all system requirements.
        :return: Dictionary with requirement status
        """
        return {
            'git_available': self.check_git_available(),
            'node_available': self.check_node_available(),
            'conda_available': self.check_conda_available(),
            'os_type': PlatformUtils.get_os_type(),
            'system_info': PlatformUtils.get_system_info()
        }

    def log_status(self, message, level="info"):
        """
        Log a status message using the status updater if available.
        :param message: Message to log
        :param level: Log level (info, warning, error)
        """
        log_func = getattr(self.logger, level, self.logger.info)
        log_func(message)

        if self.status_updater:
            if level == "error":
                self.status_updater.update_status(f"ERROR: {message}", "", 0)
            elif level == "warning":
                self.status_updater.update_status(f"WARNING: {message}", "", 50)
            else:
                self.status_updater.update_status(message, "", 50)
        else:
            print(f"[{level.upper()}] {self.name}: {message}")

    def create_directory_safely(self, path):
        """
        Create a directory safely with error handling.
        :param path: Directory path to create
        :return: Boolean indicating success
        """
        try:
            success = PlatformUtils.create_directory_if_not_exists(path)
            if success:
                self.log_status(f"Created directory: {path}")
            else:
                self.log_status(f"Failed to create directory: {path}", "error")
            return success
        except Exception as e:
            self.log_status(f"Error creating directory {path}: {str(e)}", "error")
            return False

    def check_disk_space(self, required_gb=5):
        """
        Check if there's enough disk space for installation.
        :param required_gb: Required disk space in GB
        :return: Boolean indicating sufficient space
        """
        try:
            free_bytes = PlatformUtils.get_free_disk_space(self.config.base_path)
            required_bytes = required_gb * 1024 * 1024 * 1024  # Convert GB to bytes
            
            if free_bytes >= required_bytes:
                self.log_status(f"Sufficient disk space available: {PlatformUtils.format_bytes(free_bytes)}")
                return True
            else:
                self.log_status(
                    f"Insufficient disk space. Required: {PlatformUtils.format_bytes(required_bytes)}, "
                    f"Available: {PlatformUtils.format_bytes(free_bytes)}",
                    "error"
                )
                return False
        except Exception as e:
            self.log_status(f"Error checking disk space: {str(e)}", "warning")
            return True  # Assume sufficient space if check fails
