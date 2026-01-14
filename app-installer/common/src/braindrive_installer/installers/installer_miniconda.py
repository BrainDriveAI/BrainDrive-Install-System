import os
import platform
import threading
import urllib.request
import subprocess
import ssl
try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    # Fallback: try system certificates, or disable verification as last resort
    try:
        SSL_CONTEXT = ssl.create_default_context()
    except Exception:
        SSL_CONTEXT = ssl._create_unverified_context()

from braindrive_installer.core.base_installer import BaseInstaller
from braindrive_installer.core.platform_utils import PlatformUtils
from braindrive_installer.core.installer_logger import get_installer_logger

class MinicondaInstaller(BaseInstaller):
    def __init__(self, status_updater=None):
        super().__init__("Miniconda", status_updater)
        self.miniconda_path = self.config.miniconda_path
        self.conda_exe = self.config.conda_exe
        self.base_path = self.config.base_path
        
        # Cross-platform installer configuration
        os_type = PlatformUtils.get_os_type()
        machine_arch = platform.machine().lower()  # 'arm64' for Apple Silicon, 'x86_64' for Intel
        
        if os_type == 'windows':
            self.installer_filename = "MinicondaInstaller.exe"
            self.miniconda_url = "https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe"
        elif os_type == 'macos':
            self.installer_filename = "MinicondaInstaller.sh"
            # Detect Apple Silicon (arm64) vs Intel (x86_64)
            if machine_arch == 'arm64':
                self.miniconda_url = "https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh"
            else:
                self.miniconda_url = "https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh"
        else:  # linux
            self.installer_filename = "MinicondaInstaller.sh"
            # Also handle ARM Linux (e.g., Raspberry Pi, AWS Graviton)
            if machine_arch == 'aarch64' or machine_arch == 'arm64':
                self.miniconda_url = "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh"
            else:
                self.miniconda_url = "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
        
        self.installer_path = PlatformUtils.join_paths(self.config.base_path, self.installer_filename)
        
        self.logger.info(f"MinicondaInstaller initialized - OS: {os_type}, URL: {self.miniconda_url}")
        self.logger.info(f"Installer path: {self.installer_path}")
        self.logger.info(f"Miniconda path: {self.miniconda_path}")
        self.logger.info(f"Conda executable: {self.conda_exe}")

    def check_installed(self):
        """
        Check if Miniconda is installed by verifying the presence of conda.exe.
        """
        installed = os.path.exists(self.conda_exe)
        self.logger.info(f"Miniconda installation check: {installed} (checking {self.conda_exe})")
        return installed

    def install(self):
        """
        Install Miniconda by downloading and running the installer sequentially.
        Cross-platform implementation.
        """
        self.logger.info("Starting Miniconda installation process")
        
        if self.check_installed():
            self.logger.info("Miniconda already installed, skipping installation")
            if self.status_updater:
                self.status_updater.update_status(
                        "Step: [3/3] Miniconda Already Installed.",
                        "Miniconda is already installed. Skipping installation.",
                        100,
                    )
            return

        try:
            self.logger.info("Miniconda not found, proceeding with installation")
            # Ensure the base path exists (for the installer script download)
            self.log_status(f"Creating base directory: {os.path.dirname(self.installer_path)}")
            self.create_directory_safely(os.path.dirname(self.installer_path))
            
            # Remove any existing miniconda directory - installer wants to create it fresh
            if os.path.exists(self.miniconda_path):
                self.log_status(f"Removing existing Miniconda directory: {self.miniconda_path}")
                import shutil
                shutil.rmtree(self.miniconda_path)
            
            self.download_installer()

            # Run the installer silently
            if self.status_updater:
                self.status_updater.update_status(
                        "Step: [2/3] Installing Miniconda...",
                        "Running the Miniconda installer. Please wait.",
                        60,
                    )
            
            # Cross-platform installer command
            os_type = PlatformUtils.get_os_type()
            if os_type == 'windows':
                install_cmd = [
                    self.installer_path,
                    "/S",
                    "/InstallationType=JustMe",
                    "/AddToPath=0",
                    "/RegisterPython=0",
                    f"/D={self.miniconda_path}",
                ]
            else:  # macOS and Linux
                install_cmd = [
                    "bash",
                    self.installer_path,
                    "-b",  # Batch mode
                    "-p", self.miniconda_path  # Installation prefix
                ]
            
            self.log_status(f"Running installer command: {' '.join(install_cmd)}")
            self.run_command(install_cmd, capture_output=False)
            
            # Verify installation
            if self.check_installed():
                if self.status_updater:
                    self.status_updater.update_status(
                            "Step: [3/3] Installation Complete.",
                            "Miniconda installation completed successfully.",
                            100,
                        )
                self.log_status("Miniconda installation verified successfully")
            else:
                raise Exception("Miniconda installation failed - conda executable not found after installation")
                
        except Exception as e:
            error_msg = f"Miniconda installation failed: {str(e)}"
            self.log_status(error_msg, "error")
            if self.status_updater:
                self.status_updater.update_status(
                        "Error: Miniconda Installation Failed.",
                        f"Cannot proceed with BrainDrive installation.",
                        0,
                    )
            raise Exception(error_msg)


    def download_installer(self):
        """
        Download the Miniconda installer.
        """
        if not os.path.exists(self.installer_path):
            try:
                if self.status_updater:
                    self.status_updater.update_status(
                            "Step: [1/3] Downloading Miniconda...",
                            "Downloading the Miniconda installer. This may take a few minutes.",
                            10,
                        )
                self.log_status(f"Downloading Miniconda from: {self.miniconda_url}")
                self.log_status(f"Saving to: {self.installer_path}")
                
                # Use SSL context with certifi certificates for macOS compatibility
                with urllib.request.urlopen(self.miniconda_url, context=SSL_CONTEXT) as response:
                    with open(self.installer_path, 'wb') as out_file:
                        out_file.write(response.read())
                
                # Verify download
                if os.path.exists(self.installer_path):
                    file_size = os.path.getsize(self.installer_path)
                    self.log_status(f"Download completed. File size: {file_size} bytes")
                    if self.status_updater:
                        self.status_updater.update_status(
                                "Step: [1/3] Download Complete.",
                                "Miniconda installer downloaded successfully.",
                                30,
                            )
                else:
                    raise Exception("Downloaded file not found after download")
                    
            except Exception as e:
                error_msg = f"Failed to download Miniconda installer: {str(e)}"
                self.log_status(error_msg, "error")
                raise Exception(error_msg)
        else:
            file_size = os.path.getsize(self.installer_path)
            self.log_status(f"Installer already exists: {self.installer_path} ({file_size} bytes)")
            if self.status_updater:
                self.status_updater.update_status(
                        "Step: [1/3] Installer Found.",
                        "Miniconda installer already exists. Skipping download.",
                        30,
                    )

    def check_requirements(self):
        """
        Ensure the installation directory exists.
        """
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path, exist_ok=True)
            print(f"Created base path: {self.base_path}")
        return True

    def setup_environment(self, env_name="BrainDriveInstaller", packages=None):
        """
        Set up a Conda environment with optional additional packages.
        Default environment name is 'BrainDriveInstaller' for BrainDrive project.
        
        :param env_name: The name of the environment to create.
        :param packages: A list of additional packages to install. Defaults to None.
        """
        if not self.check_installed():
            raise RuntimeError(f"{self.name} is not installed. Please install it first.")

        env_path = PlatformUtils.join_paths(self.config.base_path, env_name)

        # Base command to create the environment with BrainDrive requirements
        create_cmd = [
            self.conda_exe,
            "create",
            "--prefix", env_path,
            "python=3.11",
            "nodejs",  # Required for BrainDrive frontend
            "git"      # Required for BrainDrive repository operations
        ]

        # Add additional packages to the command if provided
        if packages:
            create_cmd.extend(packages)

        # Add the '-y' flag to confirm environment creation
        create_cmd.append("-y")

        try:
            self.run_command(create_cmd)
            self.log_status(f"Environment {env_name} set up successfully with Python 3.11, Node.js, and Git.")
        except subprocess.CalledProcessError as e:
            self.log_status(f"Failed to create environment {env_name}: {e}", "error")
            raise

    def setup_braindrive_environment(self):
        """
        Set up the BrainDrive installer environment with all required dependencies.
        """
        return self.setup_environment("BrainDriveInstaller")



    def update(self):
        """
        Update Conda to the latest version.
        """
        if not self.check_installed():
            raise RuntimeError(f"{self.name} is not installed. Please install it first.")

        try:
            self.run_command([self.conda_exe, "update", "-n", "base", "-c", "defaults", "conda", "-y"])
            print(f"{self.name} updated successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to update Conda: {e}")
            raise



    def run_command(self, cmd_list, cwd=None, capture_output=True):
        """
        Runs a command and logs output in real-time. Cross-platform implementation
        that prevents console windows from appearing.
        
        :param cmd_list: List of command and arguments to run.
        :param cwd: Directory to execute the command in.
        :param capture_output: Whether to capture and return stdout and stderr.
        :return: The process's stdout and stderr as a tuple (stdout, stderr).
        :raises: subprocess.CalledProcessError if the command fails.
        """
        try:
            command_str = ' '.join(cmd_list)
            self.log_status(f"Running command: {command_str}")

            # Get cross-platform process creation flags
            process_flags = PlatformUtils.create_no_window_flags()

            process = subprocess.Popen(
                cmd_list,
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.PIPE if capture_output else None,
                text=True,
                cwd=cwd,
                env=os.environ.copy(),  # Ensure environment variables are inherited
                **process_flags  # Apply platform-specific flags
            )

            stdout, stderr = process.communicate()

            # Log output if capture_output is True
            if stdout:
                self.log_status(f"Command output: {stdout}")
            if stderr:
                self.log_status(f"Command stderr: {stderr}", "warning")

            # Check for errors and raise if process failed
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, cmd_list, output=stdout, stderr=stderr)

            return stdout, stderr
        except subprocess.CalledProcessError as e:
            self.log_status(f"Command failed: {' '.join(e.cmd)}, Return Code: {e.returncode}", "error")
            self.log_status(f"Error Output: {e.stderr}", "error")
            raise
        except Exception as e:
            self.log_status(f"Unexpected error while running command: {e}", "error")
            raise

    # Implement abstract methods from BaseInstaller
    def clone_repository(self, repo_url, target_path, branch="main"):
        """
        Not applicable for Miniconda installer.
        """
        raise NotImplementedError("Miniconda installer does not support repository cloning")

    def build_plugins(self):
        """
        Not applicable for Miniconda installer.
        """
        raise NotImplementedError("Miniconda installer does not support plugin building")

    def start_services(self):
        """
        Not applicable for Miniconda installer.
        """
        raise NotImplementedError("Miniconda installer does not manage services")

    def stop_services(self):
        """
        Not applicable for Miniconda installer.
        """
        raise NotImplementedError("Miniconda installer does not manage services")
