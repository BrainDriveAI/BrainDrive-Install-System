import os
import secrets
import shutil
import socket
import stat
import subprocess
import threading
import urllib.error
import urllib.request
from urllib.parse import urlparse
import time
import sys
from pathlib import Path
import importlib.resources as resources
from braindrive_installer.core.base_installer import BaseInstaller
from braindrive_installer.core.installer_state import InstallerState
from braindrive_installer.core.platform_utils import PlatformUtils
from braindrive_installer.core.git_manager import GitManager
from braindrive_installer.core.node_manager import NodeManager
from braindrive_installer.core.plugin_builder import PluginBuilder
from braindrive_installer.core.process_manager import ProcessManager
from braindrive_installer.core.port_selector import (
    DEFAULT_PORT_PAIRS,
    is_managed_port_pair,
    select_available_port_pair,
)
from braindrive_installer.utils.installer_bundle import sync_installer_bundle

DEFAULT_BACKEND_PORT = DEFAULT_PORT_PAIRS[0][0]
DEFAULT_FRONTEND_PORT = DEFAULT_PORT_PAIRS[0][1]

class BrainDriveInstaller(BaseInstaller):
    """
    BrainDrive installer implementation with dual server architecture support.
    Handles complete BrainDrive installation workflow including:
    - Git repository cloning
    - Conda environment setup
    - Plugin building
    - Backend and frontend configuration
    - Dual server management
    """

    def __init__(self, status_updater=None, base_path=None):
        executable_dir = PlatformUtils.get_executable_directory()
        default_base = PlatformUtils.get_default_install_dir()
        resolved_base = (
            base_path
            or InstallerState.get_install_path(current_installer_dir=executable_dir)
            or default_base
            or executable_dir
        )
        super().__init__("BrainDrive", status_updater, base_path=resolved_base)
        
        # Initialize managers
        self.git_manager = GitManager(status_updater)
        self.node_manager = NodeManager(status_updater)
        self.process_manager = ProcessManager(status_updater)
        
        # BrainDrive configuration
        self.repo_url = "https://github.com/BrainDriveAI/BrainDrive.git"
        # Environment name for conda (set before refreshing paths)
        self.env_name = "BrainDriveDev"
        self._refresh_paths()
        self.plugin_builder = PluginBuilder(self.plugins_path, status_updater)
        
        # Server configuration - load from settings if available
        self._load_settings()
        
        # Log initialization
        self.logger.info(f"BrainDriveInstaller initialized")
        self.logger.info(f"Using ports - Backend: {self.backend_port}, Frontend: {self.frontend_port}")
        self.logger.info(f"Environment name: {self.env_name}")
        self.logger.info(f"Repository URL: {self.repo_url}")
        self.logger.info(f"Repository path: {self.repo_path}")
        self.logger.info(f"Backend path: {self.backend_path}")
        self.logger.info(f"Frontend path: {self.frontend_path}")
        self.logger.info(f"Plugins path: {self.plugins_path}")
        
        # Check for and adopt any orphaned BrainDrive processes
        try:
            adopted_count = self.process_manager.adopt_orphaned_processes()
            if adopted_count > 0:
                self.logger.info(f"Adopted {adopted_count} orphaned BrainDrive processes")
        except Exception as e:
            self.logger.warning(f"Error checking for orphaned processes: {e}")

    def _get_conda_executable(self):
        """
        Resolve absolute path to the bundled conda executable, with a fallback to PATH.
        """
        conda_path = getattr(self.config, "conda_exe", None)
        if conda_path and os.path.exists(conda_path):
            return conda_path
        fallback = PlatformUtils.get_conda_executable_name()
        self.logger.warning(
            "Conda executable not found at '%s'; falling back to '%s'.",
            conda_path,
            fallback
        )
        return fallback

    def _ensure_conda_terms_accepted(self, conda_cmd: str) -> bool:
        """
        Ensure the required Anaconda channel Terms of Service are accepted.
        """
        channels = [
            "https://repo.anaconda.com/pkgs/main",
            "https://repo.anaconda.com/pkgs/r",
            "https://repo.anaconda.com/pkgs/msys2"
        ]
        all_ok = True
        for channel in channels:
            cmd = [
                conda_cmd,
                "tos",
                "accept",
                "--override-channels",
                "--channel",
                channel
            ]
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    **PlatformUtils.create_no_window_flags()
                )
                output = " ".join(filter(None, [(result.stdout or "").strip(), (result.stderr or "").strip()]))
                if result.returncode != 0 and "already accepted" not in output.lower():
                    self.log_status(
                        f"Failed to accept Conda ToS for {channel}: {output or 'No output'}",
                        "error"
                    )
                    return False
                if output:
                    self.logger.info("Conda ToS response for %s: %s", channel, output)
            except Exception as exc:
                self.log_status(f"Error accepting Conda ToS for {channel}: {exc}", "error")
                all_ok = False
        return all_ok

    def check_installed(self):
        """
        Check if BrainDrive is properly installed by verifying:
        - Repository exists
        - Backend dependencies installed
        - Frontend dependencies installed
        - Configuration files exist
        """
        try:
            # Check if repository exists
            if not os.path.exists(self.repo_path):
                return False
            
            # Check if it's a valid git repository
            if not self.git_manager.get_repository_status(self.repo_path):
                return False
            
            # Check backend setup
            backend_requirements = os.path.join(self.backend_path, "requirements.txt")
            backend_env = os.path.join(self.backend_path, ".env")
            if not (os.path.exists(backend_requirements) and os.path.exists(backend_env)):
                return False
            
            # Check frontend setup
            frontend_package = os.path.join(self.frontend_path, "package.json")
            frontend_env = os.path.join(self.frontend_path, ".env")
            frontend_modules = os.path.join(self.frontend_path, "node_modules")
            if not (os.path.exists(frontend_package) and os.path.exists(frontend_env) and os.path.exists(frontend_modules)):
                return False
            
            self._is_installed = True
            return True
            
        except Exception as e:
            self.log_status(f"Error checking installation: {str(e)}", "error")
            return False

    def check_requirements(self):
        """
        Check if all pre-installation requirements are met:
        - Git available
        - Node.js and npm available
        - Conda available
        - Sufficient disk space
        """
        try:
            requirements_status = self.get_system_requirements_status()
            
            missing_requirements = []
            
            if not requirements_status['git_available']:
                missing_requirements.append("Git")
            
            if not requirements_status['node_available']:
                missing_requirements.append("Node.js and npm")
            
            if not requirements_status['conda_available']:
                missing_requirements.append("Conda/Miniconda")
            
            # Check disk space (require at least 5GB)
            if not self.check_disk_space(5):
                missing_requirements.append("Sufficient disk space (5GB required)")
            
            if missing_requirements:
                error_msg = f"Missing requirements: {', '.join(missing_requirements)}"
                self.log_status(error_msg, "error")
                return False
            
            return True
            
        except Exception as e:
            self.log_status(f"Error checking requirements: {str(e)}", "error")
            return False

    def setup_environment(self, env_name):
        """
        Set up conda environment with Python 3.11, Node.js, and Git.
        """
        try:
            self.log_status(f"Setting up conda environment: {env_name}", "info")
            
            conda_cmd = self._get_conda_executable()
            env_prefix = self.env_prefix

            if not self._ensure_conda_terms_accepted(conda_cmd):
                return False

            if os.path.exists(env_prefix):
                self.log_status(f"Environment {env_name} already exists at {env_prefix}", "info")
                return True
            
            # Create new environment with required packages
            create_cmd = [
                conda_cmd, "create", "--prefix", env_prefix, "-y",
                "python=3.11", "nodejs", "git"
            ]
            
            self.log_status("Creating conda environment with Python 3.11, Node.js, and Git...", "info")
            
            result = subprocess.run(
                create_cmd,
                capture_output=True,
                text=True,
                **PlatformUtils.create_no_window_flags()
            )
            
            if result.returncode != 0:
                stdout = (result.stdout or "").strip()
                stderr = (result.stderr or "").strip()
                combined = " | ".join(filter(None, [stdout, stderr])) or "No output"
                self.log_status(
                    f"Failed to create environment (exit {result.returncode}): {combined}",
                    "error"
                )
                return False
            
            self.log_status(f"Successfully created environment: {env_name}", "info")
            return True
            
        except Exception as e:
            self.log_status(f"Error setting up environment: {str(e)}", "error")
            return False

    def clone_repository(self, repo_url=None, target_path=None, branch="main"):
        """
        Clone BrainDrive repository to the specified path.
        """
        try:
            repo_url = repo_url or self.repo_url
            target_path = target_path or self.repo_path
            
            self.logger.info(f"Starting repository clone: {repo_url} -> {target_path}")
            self.log_status(f"Cloning BrainDrive repository from {repo_url}", "info")
            
            # Ensure parent directory exists
            parent_dir = os.path.dirname(target_path)
            self.logger.info(f"Ensuring parent directory exists: {parent_dir}")
            self.create_directory_safely(parent_dir)
            
            # Clone repository - git_manager returns (success, error_message)
            success, error_message = self.git_manager.clone_repository(repo_url, target_path, branch)
            
            if success:
                self.logger.info("Repository cloning completed successfully")
                self.log_status("Successfully cloned BrainDrive repository", "info")
                return True
            else:
                self.logger.error(f"Repository cloning failed: {error_message}")
                self.log_status(f"Failed to clone BrainDrive repository: {error_message}", "error")
                return False
                
        except Exception as e:
            self.logger.exception(f"Exception during repository cloning: {str(e)}")
            self.log_status(f"Error cloning repository: {str(e)}", "error")
            return False

    def build_plugins(self):
        """
        Build all BrainDrive plugins using the plugin builder.
        """
        try:
            self.log_status("Building BrainDrive plugins...", "info")
            
            # Check if plugins directory exists
            if not os.path.exists(self.plugins_path):
                self.log_status("No plugins directory found, skipping plugin build", "info")
                return True
            
            # Build all plugins
            success = self.plugin_builder.build_all_plugins()
            
            if success:
                self.log_status("Successfully built all plugins", "info")
                return True
            else:
                self.log_status("Failed to build some plugins", "error")
                return False
                
        except Exception as e:
            self.log_status(f"Error building plugins: {str(e)}", "error")
            return False

    def setup_backend(self):
        """
        Set up BrainDrive backend:
        - Install Python dependencies
        - Create .env configuration file
        """
        try:
            self.log_status("Setting up BrainDrive backend...", "info")
            
            # Check if backend directory exists
            if not os.path.exists(self.backend_path):
                self.log_status("Backend directory not found", "error")
                return False
            
            # Install Python dependencies
            requirements_file = os.path.join(self.backend_path, "requirements.txt")
            if os.path.exists(requirements_file):
                self.log_status("Installing backend dependencies...", "info")
                
                # Use conda environment pip
                conda_cmd = self._get_conda_executable()
                pip_cmd = [
                    conda_cmd,
                    "run",
                    "--prefix",
                    self.env_prefix,
                    "pip",
                    "install",
                    "-r",
                    requirements_file
                ]
                
                result = subprocess.run(
                    pip_cmd,
                    cwd=self.backend_path,
                    capture_output=True,
                    text=True,
                    **PlatformUtils.create_no_window_flags()
                )
                
                if result.returncode != 0:
                    stdout = (result.stdout or "").strip()
                    stderr = (result.stderr or "").strip()
                    combined = " | ".join(filter(None, [stdout, stderr])) or "No output"
                    if "EnvironmentLocationNotFound" in combined:
                        self.log_status(
                            "Detected stale BrainDriveDev environment; recreating...",
                            "warning"
                        )
                        cleanup_result = subprocess.run(
                            [conda_cmd, "env", "remove", "--prefix", self.env_prefix, "-y"],
                            capture_output=True,
                            text=True,
                            **PlatformUtils.create_no_window_flags()
                        )
                        cleanup_output = " | ".join(filter(None, [(cleanup_result.stdout or "").strip(), (cleanup_result.stderr or "").strip()])) or "No output"
                        if cleanup_result.returncode != 0:
                            self.log_status(
                                f"Failed to remove stale environment: {cleanup_output}",
                                "error"
                            )
                            return False
                        self.log_status("Removed stale environment; recreating...", "warning")
                        if not self.setup_environment(self.env_name):
                            return False
                        return self.setup_backend()
                    
                    self.log_status(
                        f"Failed to install backend dependencies: {combined}",
                        "error"
                    )
                    return False
                
                self.log_status("Backend dependencies installed successfully", "info")
            
            # Create backend .env file
            backend_env_path = os.path.join(self.backend_path, ".env")
            if not os.path.exists(backend_env_path):
                self.log_status("Creating backend .env file...", "info")
                success = self._create_backend_env_file(backend_env_path)
                if not success:
                    return False
            
            self.log_status("Backend setup completed successfully", "info")
            return True
            
        except Exception as e:
            self.log_status(f"Error setting up backend: {str(e)}", "error")
            return False

    def setup_frontend(self):
        """
        Set up BrainDrive frontend:
        - Install npm dependencies
        - Create .env configuration file
        """
        try:
            self.log_status("Setting up BrainDrive frontend...", "info")
            
            # Check if frontend directory exists
            if not os.path.exists(self.frontend_path):
                self.log_status("Frontend directory not found", "error")
                return False
            
            # Install npm dependencies
            package_json = os.path.join(self.frontend_path, "package.json")
            if os.path.exists(package_json):
                self.log_status("Installing frontend dependencies...", "info")
                
                success = self.node_manager.install_dependencies(self.frontend_path)
                if not success:
                    self.log_status("Failed to install frontend dependencies", "error")
                    return False
                
                self.log_status("Frontend dependencies installed successfully", "info")
            
            # Create frontend .env file
            frontend_env_path = os.path.join(self.frontend_path, ".env")
            if not os.path.exists(frontend_env_path):
                self.log_status("Creating frontend .env file...", "info")
                success = self._create_frontend_env_file(frontend_env_path)
                if not success:
                    return False
            
            self.log_status("Frontend setup completed successfully", "info")
            return True
            
        except Exception as e:
            self.log_status(f"Error setting up frontend: {str(e)}", "error")
            return False

    def install(self):
        """
        Complete BrainDrive installation process.
        """
        install_started_at = time.perf_counter()
        install_success = False
        try:
            self.logger.info("=== STARTING BRAINDRIVE INSTALLATION ===")
            self.log_status("Starting BrainDrive installation...", "info")

            # Refresh settings to capture latest install path and configuration
            self._load_settings()
            
            # Check if already installed
            if self.check_installed():
                self.logger.info("BrainDrive is already installed, skipping installation")
                self.log_status("BrainDrive is already installed", "info")
                install_success = True
                return True
            
            # Step 1: Check requirements
            self.logger.info("Step 1/7: Checking system requirements")
            self.log_status("Step 1/7: Checking system requirements...", "info")
            if not self.check_requirements():
                self.logger.error("System requirements check failed")
                return False
            
            # Step 2: Setup conda environment
            self.logger.info("Step 2/7: Setting up conda environment")
            self.log_status("Step 2/7: Setting up conda environment...", "info")
            if not self.setup_environment(self.env_name):
                self.logger.error("Conda environment setup failed")
                return False
            
            # Step 3: Clone repository
            self.logger.info("Step 3/7: Cloning BrainDrive repository")
            self.log_status("Step 3/7: Cloning BrainDrive repository...", "info")
            staging_path = self._create_staging_path("install")
            if not self.clone_repository(target_path=staging_path):
                self.logger.error("Repository cloning failed")
                self._cleanup_directory(staging_path)
                return False

            if not self._validate_repository_structure(staging_path):
                self.logger.error("Repository validation failed")
                self._cleanup_directory(staging_path)
                return False

            if not self._promote_staging_directory(staging_path):
                self.logger.error("Failed to promote staged repository into place")
                self._cleanup_directory(staging_path)
                return False

            self._apply_preinstall_settings_if_present()
            
            # Step 4: Build plugins
            self.logger.info("Step 4/7: Building plugins")
            self.log_status("Step 4/7: Building plugins...", "info")
            if not self.build_plugins():
                self.logger.error("Plugin building failed")
                return False
            
            # Step 5: Setup backend
            self.logger.info("Step 5/7: Setting up backend")
            self.log_status("Step 5/7: Setting up backend...", "info")
            if not self.setup_backend():
                self.logger.error("Backend setup failed")
                return False
            
            # Step 6: Setup frontend
            self.logger.info("Step 6/7: Setting up frontend")
            self.log_status("Step 6/7: Setting up frontend...", "info")
            if not self.setup_frontend():
                self.logger.error("Frontend setup failed")
                return False
            
            # Step 7: Verify installation
            self.logger.info("Step 7/7: Verifying installation")
            self.log_status("Step 7/7: Verifying installation...", "info")
            if not self.check_installed():
                self.logger.error("Installation verification failed")
                self.log_status("Installation verification failed", "error")
                return False
            
            self.logger.info("=== BRAINDRIVE INSTALLATION COMPLETED SUCCESSFULLY ===")
            self.log_status("BrainDrive installation completed successfully!", "info")
            self._is_installed = True
            InstallerState.set_install_path(self.config.base_path)
            try:
                bundle_path = sync_installer_bundle(self.config.base_path)
                if bundle_path:
                    self.logger.info(f"Installer bundle synced to {bundle_path}")
            except Exception as bundle_error:
                self.logger.warning(f"Failed to sync installer bundle: {bundle_error}")
            install_success = True
            return True
        
        except Exception as e:
            self.logger.exception(f"Installation failed with exception: {str(e)}")
            self.log_status(f"Installation failed: {str(e)}", "error")
            return False
        finally:
            elapsed = time.perf_counter() - install_started_at
            outcome_text = "completed successfully" if install_success else "ended with errors"
            self.logger.info(f"BrainDrive installation {outcome_text} in {elapsed:.2f} seconds")

    def start_services(self):
        """
        Start BrainDrive backend and frontend servers.
        """
        start_started_at = time.perf_counter()
        start_success = False
        try:
            self.log_status("Starting BrainDrive services...", "info")

            try:
                self._load_settings()
            except Exception as refresh_error:
                self.logger.warning(f"Could not refresh settings prior to start: {refresh_error}")

            # Check if already running
            backend_bind_host = "0.0.0.0"
            frontend_bind_host = self._normalize_host_for_binding(self.frontend_host, allow_wildcard=True, default="localhost")

            if self.process_manager.is_process_running("braindrive_backend"):
                self.log_status("Backend server is already running", "info")
            else:
                # Start backend server
                self.log_status("Starting backend server...", "info")
                conda_cmd = self._get_conda_executable()
                backend_cmd = [
                    conda_cmd, "run", "--prefix", self.env_prefix,
                    "uvicorn", "main:app",
                    "--host", backend_bind_host,
                    "--port", str(self.backend_port)
                ]
                if getattr(self, "debug_mode", False):
                    backend_cmd.insert(6, "--reload")

                success, error_msg = self.process_manager.start_process(
                    "braindrive_backend",
                    backend_cmd,
                    cwd=self.backend_path
                )

                if not success:
                    self.log_status(f"Failed to start backend server: {error_msg}", "error")
                    self.process_manager.log_process_debug("braindrive_backend", logger=self.logger)
                    return False

                # Wait a moment for backend to start
                if not self._wait_for_backend_ready(
                    host=self._get_backend_health_host(self.backend_host),
                    port=self.backend_port
                ):
                    self.log_status("Backend did not respond on expected host/port", "error")
                    self.process_manager.log_process_debug("braindrive_backend", logger=self.logger)
                    return False

            if self.process_manager.is_process_running("braindrive_frontend"):
                self.log_status("Frontend server is already running", "info")
            else:
                # Start frontend server
                self.log_status("Starting frontend server...", "info")
                npm_cmd = PlatformUtils.get_npm_executable_name()
                frontend_cmd = [npm_cmd, "run", "dev", "--", "--host", self.frontend_host, "--port", str(self.frontend_port)]

                success, error_msg = self.process_manager.start_process(
                    "braindrive_frontend",
                    frontend_cmd,
                    cwd=self.frontend_path
                )

                if not success:
                    self.log_status(f"Failed to start frontend server: {error_msg}", "error")
                    self.process_manager.log_process_debug("braindrive_frontend", logger=self.logger)
                    return False
            
            self.log_status("BrainDrive services started successfully", "info")
            self.log_status(f"Backend: {self._build_service_url(self.backend_host, self.backend_port)}", "info")
            self.log_status(f"Frontend: {self._build_browser_url(self.frontend_host, self.frontend_port)}", "info")
            start_success = True
            return True
            
        except Exception as e:
            self.log_status(f"Error starting services: {str(e)}", "error")
            return False
        finally:
            elapsed = time.perf_counter() - start_started_at
            outcome_text = "completed successfully" if start_success else "ended with errors"
            self.logger.info(f"BrainDrive service start {outcome_text} in {elapsed:.2f} seconds")

    def stop_services(self):
        """
        Stop all BrainDrive services with systematic verification and cleanup.
        """
        stop_started_at = time.perf_counter()
        stop_success = False
        try:
            self.log_status("Stopping BrainDrive services...", "info")
            
            # STEP 1: Try to stop processes through ProcessManager (normal way)
            self.log_status("Step 1: Attempting normal process stop...", "info")
            backend_stopped = self.process_manager.stop_process("braindrive_backend")
            frontend_stopped = self.process_manager.stop_process("braindrive_frontend")
            
            self.log_status(f"Normal stop results - Backend: {backend_stopped}, Frontend: {frontend_stopped}", "info")
            
            # STEP 2: Double-check if processes are actually stopped
            self.log_status("Step 2: Verifying processes are actually stopped...", "info")
            
            # Wait a moment for processes to fully terminate
            time.sleep(2)
            
            # Check if ports are actually free
            backend_port_free = self._check_port_free(self.backend_port)
            frontend_port_free = self._check_port_free(self.frontend_port)

            self.log_status(f"Port status - Backend ({self.backend_port}): {'FREE' if backend_port_free else 'IN USE'}, Frontend ({self.frontend_port}): {'FREE' if frontend_port_free else 'IN USE'}", "info")
            
            # STEP 3: If processes are still running, use backup cleanup
            if not backend_port_free or not frontend_port_free:
                self.log_status("Step 3: Processes still running, using backup cleanup...", "warning")
                
                # Define comprehensive patterns for both backend and frontend (using dynamic ports)
                backend_patterns = [
                    f"uvicorn main:app --reload --host {self.backend_host} --port {self.backend_port}",
                    f"uvicorn main:app --reload --host localhost --port {self.backend_port}",
                    "uvicorn main:app",
                    "main:app --reload",
                    f"--port {self.backend_port}",
                    "BrainDriveDev\\python.exe",
                    "multiprocessing.spawn"
                ]
                
                frontend_patterns = [
                    "npm run dev",
                    "npm-cli.js run dev",
                    "vite.js",
                    "vite\\bin\\vite.js",
                    f"--port {self.frontend_port}",
                    "BrainDriveInstaller\\node.exe"
                ]
                
                # Kill backend processes
                if not backend_port_free:
                    backend_killed = self.process_manager.kill_processes_by_pattern(
                        backend_patterns, "backend processes"
                    )
                    self.log_status(f"Backup cleanup killed {backend_killed} backend processes", "info")
                
                # Kill frontend processes
                if not frontend_port_free:
                    frontend_killed = self.process_manager.kill_processes_by_pattern(
                        frontend_patterns, "frontend processes"
                    )
                    self.log_status(f"Backup cleanup killed {frontend_killed} frontend processes", "info")
                
                # Wait for cleanup to take effect
                time.sleep(3)
            
            # STEP 4: Final verification
            self.log_status("Step 4: Final verification...", "info")
            
            final_backend_free = self._check_port_free(self.backend_port)
            final_frontend_free = self._check_port_free(self.frontend_port)

            self.log_status(f"Final port status - Backend ({self.backend_port}): {'FREE' if final_backend_free else 'STILL IN USE'}, Frontend ({self.frontend_port}): {'FREE' if final_frontend_free else 'STILL IN USE'}", "info")
            
            if final_backend_free and final_frontend_free:
                self.log_status("✅ All BrainDrive services stopped successfully - all ports are free", "info")
                stop_success = True
                return True
            else:
                ports_still_used = []
                if not final_backend_free:
                    ports_still_used.append(f"{self.backend_port} (backend)")
                if not final_frontend_free:
                    ports_still_used.append(f"{self.frontend_port} (frontend)")
                self.log_status(f"❌ Some services are still running - ports still in use: {', '.join(ports_still_used)}", "error")
                return False
                
        except Exception as e:
            self.log_status(f"Error stopping services: {str(e)}", "error")
            return False
        finally:
            elapsed = time.perf_counter() - stop_started_at
            outcome_text = "completed successfully" if stop_success else "ended with errors"
            self.logger.info(f"BrainDrive service stop {outcome_text} in {elapsed:.2f} seconds")
    
    def _check_port_free(self, port: int) -> bool:
        """
        Check if a port is free (not in use).
        
        Args:
            port: Port number to check
            
        Returns:
            True if port is free, False if in use
        """
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result != 0  # Port is free if connection failed
        except Exception:
            return True  # Assume free if we can't check

    def update(self):
        """
        Update BrainDrive to the latest version.
        """
        try:
            self.log_status("Updating BrainDrive repository (git pull --rebase)...", "info")

            # Ensure paths and configuration are current
            self._load_settings()

            if not os.path.isdir(self.repo_path):
                self.log_status(f"Repository path not found: {self.repo_path}", "error")
                return False

            # Ensure services are not running before updating
            if self.process_manager.is_process_running("braindrive_backend") or self.process_manager.is_process_running("braindrive_frontend"):
                self.log_status("Please stop BrainDrive services before running an update.", "error")
                return False

            success, error_message = self.git_manager.pull_with_rebase(self.repo_path)
            if not success:
                self.log_status(f"Git pull --rebase failed: {error_message}", "error")
                return False

            self.log_status("BrainDrive repository updated successfully.", "info")
            return True
        except Exception as e:
            self.log_status(f"Error updating BrainDrive: {str(e)}", "error")
            return False

    def _create_backend_env_file(self, env_path):
        """
        Create backend .env file with proper configuration using template.
        """
        try:
            # Load the backend environment template
            template_content = self._load_template_content("backend_env_template.txt")
            if not template_content:
                self.log_status("Backend template not found in packaged resources.", "error")
                return False
            
            # Generate secret key
            secret_key = secrets.token_urlsafe(32)
            
            # Replace template variables
            env_content = template_content.replace("{BACKEND_HOST}", "0.0.0.0")
            env_content = env_content.replace("{BACKEND_PORT}", str(self.backend_port))
            env_content = env_content.replace("{FRONTEND_HOST}", self.frontend_host)
            env_content = env_content.replace("{FRONTEND_PORT}", str(self.frontend_port))
            env_content = env_content.replace("{SECRET_KEY}", secret_key)
            env_content = env_content.replace("{LOG_LEVEL}", "info")
            env_content = env_content.replace("{DATABASE_PATH}", "sqlite:///braindrive.db")
            env_content = env_content.replace("{DEBUG_MODE}", "false")
            env_content = env_content.replace("{ENABLE_REGISTRATION}", "true")
            env_content = env_content.replace("{ENABLE_API_DOCS}", "true")
            env_content = env_content.replace("{ENABLE_METRICS}", "false")
            env_content = env_content.replace("{WORKER_COUNT}", "1")
            env_content = env_content.replace("{MAX_UPLOAD_SIZE}", "100000000")
            
            # Generate CORS origins and allowed hosts
            cors_origins = [
                f"http://{self.frontend_host}:{self.frontend_port}",
                f"http://127.0.0.1:{self.frontend_port}",
                f"http://localhost:{self.frontend_port}"
            ]
            allowed_hosts = [
                "0.0.0.0",
                self.frontend_host,
                "localhost",
                "127.0.0.1"
            ]
            
            env_content = env_content.replace("{CORS_ORIGINS}", str(cors_origins).replace("'", '"'))
            env_content = env_content.replace("{ALLOWED_HOSTS}", str(list(set(allowed_hosts))).replace("'", '"'))
            
            # Write the processed content to the .env file
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(env_content)
            
            self.log_status("Backend .env file created successfully from template", "info")
            return True
            
        except Exception as e:
            self.log_status(f"Error creating backend .env file: {str(e)}", "error")
            return False

    def _create_frontend_env_file(self, env_path):
        """
        Create frontend .env file with proper configuration using template.
        """
        try:
            template_content = self._load_template_content("frontend_env_template.txt")
            if not template_content:
                self.log_status("Frontend template not found in packaged resources.", "error")
                return False
            
            # Load optional settings for richer template substitution
            settings_manager = None
            try:
                from braindrive_installer.ui.settings_manager import BrainDriveSettingsManager
                settings_manager = BrainDriveSettingsManager(self.repo_path)
            except Exception:
                settings_manager = None

            backend_host = getattr(self, "backend_host", None)
            backend_port = getattr(self, "backend_port", None)
            frontend_host = getattr(self, "frontend_host", None)
            frontend_port = getattr(self, "frontend_port", None)

            enable_pwa = None
            enable_analytics = None
            debug_mode = None
            default_theme = None

            if settings_manager:
                enable_pwa = settings_manager.get_setting('ui', 'enable_pwa', True)
                enable_analytics = settings_manager.get_setting('ui', 'enable_analytics', False)
                debug_mode = settings_manager.get_setting('security', 'debug_mode', False)
                default_theme = settings_manager.get_setting('ui', 'default_theme', "light")

                if backend_host is None:
                    backend_host = settings_manager.get_setting('network', 'backend_host', 'localhost')
                if backend_port is None:
                    backend_port = settings_manager.get_setting('network', 'backend_port', DEFAULT_BACKEND_PORT)
                if frontend_host is None:
                    frontend_host = settings_manager.get_setting('network', 'frontend_host', 'localhost')
                if frontend_port is None:
                    frontend_port = settings_manager.get_setting('network', 'frontend_port', DEFAULT_FRONTEND_PORT)

            backend_host = backend_host or "localhost"
            backend_port = backend_port or DEFAULT_BACKEND_PORT
            frontend_host = frontend_host or "localhost"
            frontend_port = frontend_port or DEFAULT_FRONTEND_PORT
            enable_pwa_str = str(bool(enable_pwa if enable_pwa is not None else True)).lower()
            enable_analytics_str = str(bool(enable_analytics if enable_analytics is not None else False)).lower()
            debug_mode_str = str(bool(debug_mode if debug_mode is not None else False)).lower()
            default_theme = default_theme or "light"
            
            # Replace template variables
            env_content = template_content.replace("{BACKEND_HOST}", str(backend_host))
            env_content = env_content.replace("{BACKEND_PORT}", str(backend_port))
            env_content = env_content.replace("{FRONTEND_HOST}", str(frontend_host))
            env_content = env_content.replace("{FRONTEND_PORT}", str(frontend_port))
            env_content = env_content.replace("{ENABLE_PWA}", enable_pwa_str)
            env_content = env_content.replace("{ENABLE_ANALYTICS}", enable_analytics_str)
            env_content = env_content.replace("{DEBUG_MODE}", debug_mode_str)
            env_content = env_content.replace("{DEFAULT_THEME}", default_theme)
            
            # Write the processed content to the .env file
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(env_content)
            
            self.log_status("Frontend .env file created successfully from template", "info")
            return True
            
        except Exception as e:
            self.log_status(f"Error creating frontend .env file: {str(e)}", "error")
            return False

    def get_service_status(self):
        """
        Get the status of BrainDrive services.
        """
        return {
            'backend_running': self.process_manager.is_process_running("braindrive_backend"),
            'frontend_running': self.process_manager.is_process_running("braindrive_frontend"),
            'backend_url': f"http://{self.backend_host}:{self.backend_port}",
            'frontend_url': f"http://{self.frontend_host}:{self.frontend_port}",
            'installed': self.check_installed()
        }

    def _auto_select_ports_if_default(self, settings_manager=None) -> bool:
        """
        Automatically pick the first preferred port pair that is currently free.

        Returns True when the ports were changed (and persisted if a manager is provided).
        """
        current_pair = (self.backend_port, self.frontend_port)
        if not is_managed_port_pair(*current_pair, preferred_pairs=DEFAULT_PORT_PAIRS):
            return False

        backend_host = self.backend_host or "localhost"
        frontend_host = self.frontend_host or "localhost"
        target_backend, target_frontend = select_available_port_pair(
            preferred_pairs=DEFAULT_PORT_PAIRS,
            backend_host=backend_host,
            frontend_host=frontend_host,
        )

        if (target_backend, target_frontend) == current_pair:
            return False

        self.logger.info(
            "Default ports %s/%s unavailable; switched to %s/%s",
            current_pair[0],
            current_pair[1],
            target_backend,
            target_frontend,
        )
        self.backend_port, self.frontend_port = target_backend, target_frontend
        if settings_manager:
            settings_manager.update_setting('network', 'backend_port', self.backend_port)
            settings_manager.update_setting('network', 'frontend_port', self.frontend_port)
            saved = settings_manager.save_settings()
            if saved:
                try:
                    install_path = getattr(settings_manager, "installation_path", "") or ""
                    backend_dir = os.path.join(install_path, "backend")
                    frontend_dir = os.path.join(install_path, "frontend")
                    if os.path.isdir(backend_dir) and os.path.isdir(frontend_dir):
                        if settings_manager.regenerate_env_files():
                            self.logger.info("Updated env files after auto-selecting ports.")
                        else:
                            self.logger.warning("Failed to update env files after auto-selecting ports.")
                except Exception as exc:
                    self.logger.warning("Failed to refresh env files after auto-selecting ports: %s", exc)
        return True

    def _load_settings(self):
        """Load settings from JSON file if available, otherwise use defaults"""
        # Default values
        self.backend_port = DEFAULT_BACKEND_PORT
        self.frontend_port = DEFAULT_FRONTEND_PORT
        self.backend_host = "localhost"
        self.frontend_host = "localhost"
        self.debug_mode = False
        
        try:
            from braindrive_installer.ui.settings_manager import BrainDriveSettingsManager
            repo_manager = BrainDriveSettingsManager(self.repo_path)
            preinstall_manager = BrainDriveSettingsManager(self.config.env_path)
            active_manager = None
            source_label = "defaults"

            installed = False
            try:
                installed = self.check_installed()
            except Exception:
                installed = False

            manager = repo_manager if installed else preinstall_manager
            active_manager = manager

            self.backend_port = manager.get_setting('network', 'backend_port', DEFAULT_BACKEND_PORT)
            self.frontend_port = manager.get_setting('network', 'frontend_port', DEFAULT_FRONTEND_PORT)
            self.backend_host = manager.get_setting('network', 'backend_host', 'localhost')
            self.frontend_host = manager.get_setting('network', 'frontend_host', 'localhost')
            self.debug_mode = manager.get_setting('security', 'debug_mode', False)
            install_base = manager.get_setting('installation', 'path', self.config.base_path)
            self._adopt_install_path_from_settings(install_base, require_repo=installed)

            settings_file = repo_manager.settings_file
            if os.path.exists(settings_file):
                source_label = "repo JSON" if installed else "pre-install JSON"
            else:
                self.logger.info("No settings file found, using auto-selected defaults")
                if installed:
                    try:
                        if manager.save_settings():
                            manager.regenerate_env_files()
                    except Exception as exc:
                        self.logger.warning("Failed to persist default settings: %s", exc)

            if active_manager:
                changed = self._auto_select_ports_if_default(active_manager)
                if changed:
                    self.logger.info(
                        "Auto-selected ports - Backend %s, Frontend %s",
                        self.backend_port,
                        self.frontend_port,
                    )

            self.logger.info(
                f"Loaded settings from {source_label}: Backend {self.backend_host}:{self.backend_port}, "
                f"Frontend {self.frontend_host}:{self.frontend_port}"
            )

        except Exception as e:
            self.logger.warning(f"Could not load settings, using defaults: {e}")

    def get_installation_path(self):
        """Get the BrainDrive installation path"""
        return self.repo_path

    def _create_staging_path(self, purpose="install"):
        """Create a unique staging directory for cloning operations."""
        parent_dir = os.path.dirname(self.repo_path)
        os.makedirs(parent_dir, exist_ok=True)
        suffix = secrets.token_hex(4)
        return os.path.join(parent_dir, f".braindrive_{purpose}_staging_{suffix}")

    def _create_backup_path(self):
        """Generate a path for storing the previous installation during updates."""
        parent_dir = os.path.dirname(self.repo_path)
        os.makedirs(parent_dir, exist_ok=True)
        suffix = secrets.token_hex(4)
        return os.path.join(parent_dir, f".braindrive_backup_{suffix}")

    def _cleanup_directory(self, path):
        """Remove a directory tree if it exists."""
        if not path or not os.path.exists(path):
            return

        try:
            PlatformUtils.ensure_writable(path)
            shutil.rmtree(path, onerror=self._handle_remove_readonly)
        except Exception as exc:
            self.logger.warning(f"Failed to cleanup directory {path}: {exc}")

    def _handle_remove_readonly(self, func, path, exc_info):
        """Callback for shutil.rmtree to clear read-only flags and retry."""
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception as exc:
            self.logger.warning(f"Failed to remove read-only path {path}: {exc}")

    def _load_template_content(self, filename: str):
        """Load template content from package resources or bundled data paths."""
        checked_paths = []

        # Try Python package resources first.
        try:
            template_file = resources.files('braindrive_installer.templates').joinpath(filename)
            checked_paths.append(str(template_file))
            if template_file.is_file():
                return template_file.read_text(encoding='utf-8')
        except Exception as exc:
            self.logger.debug(f"Template {filename} not found in package resources: {exc}")

        # Fallback search paths for PyInstaller data directories and development tree.
        candidate_roots = [
            Path(getattr(sys, "_MEIPASS", "")) / 'templates',
            Path(getattr(sys, "_MEIPASS", "")) / 'braindrive_installer' / 'installers' / 'templates',
            Path(__file__).resolve().parent / 'templates',
            Path(__file__).resolve().parent.parent / 'templates',
            Path(PlatformUtils.get_executable_directory()) / 'templates',
        ]

        for root in candidate_roots:
            if not root:
                continue
            candidate = root / filename
            checked_paths.append(str(candidate))
            if candidate.exists():
                return candidate.read_text(encoding='utf-8')

        self.logger.error(
            "Template %s not found. Locations checked: %s",
            filename,
            ", ".join(checked_paths)
        )
        return None

    def _validate_repository_structure(self, repo_root):
        """Ensure the cloned repository contains the expected structure."""
        expected_items = [
            os.path.join(repo_root, "backend"),
            os.path.join(repo_root, "frontend"),
            os.path.join(repo_root, "backend", "requirements.txt"),
            os.path.join(repo_root, "frontend", "package.json")
        ]

        for item in expected_items:
            if not os.path.exists(item):
                self.log_status(f"Missing expected repository item: {item}", "error")
                return False
        return True

    def _promote_staging_directory(self, staging_path):
        """Move the staging repository into the live install location."""
        try:
            PlatformUtils.ensure_writable(staging_path)
            if os.path.exists(self.repo_path):
                if os.listdir(self.repo_path):
                    self.log_status("Installation directory already exists and is not empty.", "error")
                    return False
                PlatformUtils.ensure_writable(self.repo_path)
                self._cleanup_directory(self.repo_path)

            shutil.move(staging_path, self.repo_path)
            return True
        except Exception as exc:
            self.logger.error(f"Failed to promote staging repository: {exc}")
            # Attempt fallback copy if move fails (e.g., due to antivirus locking files)
            try:
                PlatformUtils.ensure_writable(self.repo_path)
                shutil.copytree(staging_path, self.repo_path, dirs_exist_ok=True)
                self._cleanup_directory(staging_path)
                return True
            except Exception as copy_exc:
                self.logger.error(f"Fallback copy of staging repository failed: {copy_exc}")
                return False

    def _migrate_configuration(self, source_repo, target_repo):
        """Copy configuration artifacts from the existing install into the new repo."""
        files_to_copy = [
            "braindrive_settings.json",
            os.path.join("backend", ".env"),
            os.path.join("frontend", ".env")
        ]

        for relative in files_to_copy:
            source = os.path.join(source_repo, relative)
            destination = os.path.join(target_repo, relative)

            if os.path.exists(source):
                try:
                    os.makedirs(os.path.dirname(destination), exist_ok=True)
                    shutil.copy2(source, destination)
                except Exception as exc:
                    self.logger.warning(f"Failed to migrate {relative}: {exc}")

    def _apply_preinstall_settings_if_present(self):
        """Copy pre-install settings into the freshly cloned repository if available."""
        preinstall_settings = os.path.join(self.config.env_path, "braindrive_settings.json")
        repo_settings = os.path.join(self.repo_path, "braindrive_settings.json")

        if os.path.exists(preinstall_settings) and not os.path.exists(repo_settings):
            try:
                shutil.copy2(preinstall_settings, repo_settings)
                self.logger.info("Applied pre-install BrainDrive settings to new installation.")
                # Reload settings from the repo copy so subsequent steps use the persisted values
                self._load_settings()
            except Exception as exc:
                self.logger.warning(f"Failed to apply pre-install settings: {exc}")

    def _swap_repository_with_backup(self, staging_path):
        """
        Replace the current repository with the staged clone, keeping a backup of the prior install.

        Returns:
            Tuple of (success flag, backup path or None).
        """
        backup_path = None
        try:
            if os.path.exists(self.repo_path):
                backup_path = self._create_backup_path()
                shutil.move(self.repo_path, backup_path)

            shutil.move(staging_path, self.repo_path)
            return True, backup_path
        except Exception as exc:
            self.logger.error(f"Failed to swap repository with staged clone: {exc}")
            # Attempt to restore previous installation if it was moved
            if backup_path and os.path.exists(backup_path) and not os.path.exists(self.repo_path):
                try:
                    shutil.move(backup_path, self.repo_path)
                except Exception as restore_error:
                    self.logger.error(f"Failed to restore backup after swap failure: {restore_error}")
            return False, backup_path

    def _restore_backup(self, backup_path):
        """Restore the backup repository if an update step fails."""
        if not backup_path or not os.path.exists(backup_path):
            return

        try:
            if os.path.exists(self.repo_path):
                self._cleanup_directory(self.repo_path)
            shutil.move(backup_path, self.repo_path)
        except Exception as exc:
            self.logger.error(f"Failed to restore backup repository: {exc}")

    def _cleanup_backup(self, backup_path):
        """Remove backup directory after a successful update."""
        if backup_path and os.path.exists(backup_path):
            self._cleanup_directory(backup_path)

    def _normalize_host_for_binding(self, host, allow_wildcard=False, default="localhost"):
        """Normalize host strings for process bindings."""
        if not host:
            return default
        host = host.strip()
        if "://" in host:
            parsed = urlparse(host)
            host = parsed.hostname or default
        if allow_wildcard:
            return host or default
        if host in ("0.0.0.0", "*"):
            return default
        return host or default

    def _get_display_host(self, host):
        """Convert binding host into a user-friendly address."""
        if not host:
            return "localhost"
        host = host.strip()
        if "://" in host:
            parsed = urlparse(host)
            host = parsed.hostname or host
        if host in ("0.0.0.0", "*"):
            return "127.0.0.1"
        return host

    def _get_backend_health_host(self, host):
        """Return the host to probe when checking backend availability."""
        display = self._get_display_host(host)
        return display or "127.0.0.1"

    def _build_service_url(self, host, port):
        """Build an HTTP URL suitable for logging/service links."""
        display_host = self._get_display_host(host or "localhost")
        port_part = f":{port}" if port else ""
        return f"http://{display_host}{port_part}"

    def _build_browser_url(self, host, port):
        """Build a browser-friendly URL accounting for schemes in settings."""
        if not host:
            host = "localhost"
        host = host.strip()
        if "://" in host:
            parsed = urlparse(host)
            browse_host = parsed.hostname or self._get_display_host(host)
            scheme = parsed.scheme or "http"
            effective_port = parsed.port or port
            port_part = f":{effective_port}" if effective_port else ""
            path = parsed.path or ""
            return f"{scheme}://{browse_host}{port_part}{path}"

        browse_host = self._get_display_host(host)
        port_part = f":{port}" if port else ""
        return f"http://{browse_host}{port_part}"

    def _wait_for_backend_ready(self, host, port, timeout=120):
        """Poll the backend until it responds or timeout elapses."""
        endpoints = ["/health", "/api/health", "/status", "/docs", "/openapi.json", "/"]
        start_time = time.time()

        while time.time() - start_time < timeout:
            for path in endpoints:
                url = f"http://{host}:{port}{path}"
                try:
                    with urllib.request.urlopen(url, timeout=3) as response:
                        if 200 <= response.status < 400:
                            self.logger.info(f"Backend responded to probe at {url} (status {response.status})")
                            return True
                except urllib.error.URLError as exc:
                    self.logger.debug(f"Backend probe failed for {url}: {exc}")
                except Exception as exc:
                    self.logger.debug(f"Backend probe encountered error for {url}: {exc}")
            time.sleep(1)

        self.logger.error(f"Backend did not respond on {host}:{port} within {timeout} seconds")
        return False

    def _refresh_paths(self):
        """Sync instance path attributes with the current AppConfig state."""
        self.repo_path = self.config.repo_path
        self.backend_path = self.config.backend_path
        self.frontend_path = self.config.frontend_path
        self.plugins_path = self.config.plugins_path
        env_name = getattr(self, "env_name", "BrainDriveDev")
        self.env_prefix = PlatformUtils.join_paths(self.config.miniconda_path, "envs", env_name)

        if hasattr(self, "plugin_builder"):
            self.plugin_builder.plugins_path = self.plugins_path

    def set_installation_path(self, base_path: str):
        """
        Update the installation base path and persist the selection.

        Args:
            base_path: Desired install directory for BrainDrive.
        """
        if not base_path:
            return

        self.config.set_base_path(base_path)
        self._refresh_paths()

        if not InstallerState.set_install_path(self.config.base_path):
            self.logger.warning("Unable to persist install path to installer state.")

    def _adopt_install_path_from_settings(self, candidate_path: str, require_repo: bool):
        """
        Update the installation path based on a value read from settings.

        Args:
            candidate_path: The base directory requested in settings.
            require_repo: If True, only adopt when an existing repo resides at the path.
        """
        if not candidate_path or not isinstance(candidate_path, str):
            return

        normalized_candidate = os.path.abspath(candidate_path)
        if not os.path.isabs(normalized_candidate):
            return

        current_base = os.path.abspath(self.config.base_path)
        if os.path.normcase(normalized_candidate) == os.path.normcase(current_base):
            return

        expected_repo = os.path.join(normalized_candidate, "BrainDrive")
        if require_repo and not os.path.exists(expected_repo):
            return

        # When not requiring repo, avoid switching away from an existing install inadvertently.
        if not require_repo and os.path.exists(self.repo_path) and self.check_installed():
            return

        self.set_installation_path(normalized_candidate)
