"""
Node.js Manager for BrainDrive Installer
Handles Node.js and npm operations including dependency installation and build processes.
"""

import os
import subprocess
import json
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
from braindrive_installer.core.platform_utils import PlatformUtils


class NodeManager:
    """Manages Node.js and npm operations for BrainDrive installation."""
    
    def __init__(self, status_updater=None):
        """
        Initialize Node.js Manager.
        
        Args:
            status_updater: Optional status updater for progress tracking
        """
        self.status_updater = status_updater
        self.logger = logging.getLogger(__name__)
        
    def _update_status(self, message: str, progress: Optional[int] = None):
        """Update status if status_updater is available."""
        if self.status_updater:
            self.status_updater.update_status(message, "", progress or 0)
        self.logger.info(message)
    
    def _run_node_command(self, command: list, cwd: Optional[str] = None, 
                         capture_output: bool = True, timeout: int = 600) -> Tuple[bool, str, str]:
        """
        Run a Node.js/npm command and return success status and output.
        
        Args:
            command: Command as list of strings (e.g., ['npm', 'install'])
            cwd: Working directory for the command
            capture_output: Whether to capture stdout/stderr
            timeout: Command timeout in seconds (default: 10 minutes)
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            # Get platform-specific process creation flags
            flags_dict = PlatformUtils.create_no_window_flags()
            
            # Add platform-specific executable extensions if needed
            if command[0] in ['npm', 'node', 'npx']:
                if PlatformUtils.get_os_type() == 'windows':
                    command[0] += '.cmd'
            
            # Prepare subprocess arguments
            subprocess_args = {
                'cwd': cwd,
                'capture_output': capture_output,
                'text': True,
                'timeout': timeout
            }
            
            # Add platform-specific flags
            if PlatformUtils.get_os_type() == 'windows':
                subprocess_args['creationflags'] = flags_dict.get('creationflags', 0)
                subprocess_args['startupinfo'] = flags_dict.get('startupinfo')
            
            result = subprocess.run(command, **subprocess_args)
            
            return result.returncode == 0, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            error_msg = f"Node command timed out: {' '.join(command)}"
            self.logger.error(error_msg)
            return False, "", error_msg
        except Exception as e:
            error_msg = f"Error running node command {' '.join(command)}: {str(e)}"
            self.logger.error(error_msg)
            return False, "", error_msg
    
    def check_node_available(self) -> Tuple[bool, Dict[str, str]]:
        """
        Check if Node.js and npm are installed and accessible.
        
        Returns:
            Tuple of (is_available, version_info_or_error)
        """
        self._update_status("Checking Node.js and npm availability...")
        
        version_info = {}
        
        # Check Node.js
        success, stdout, stderr = self._run_node_command(['node', '--version'])
        if success:
            version_info['node'] = stdout.strip()
        else:
            error_msg = f"Node.js not found: {stderr}"
            self._update_status(error_msg)
            return False, {"error": error_msg}
        
        # Check npm
        success, stdout, stderr = self._run_node_command(['npm', '--version'])
        if success:
            version_info['npm'] = stdout.strip()
        else:
            error_msg = f"npm not found: {stderr}"
            self._update_status(error_msg)
            return False, {"error": error_msg}
        
        # Check npx (optional but useful)
        success, stdout, stderr = self._run_node_command(['npx', '--version'])
        if success:
            version_info['npx'] = stdout.strip()
        
        self._update_status(f"Node.js tools found - Node: {version_info.get('node', 'N/A')}, npm: {version_info.get('npm', 'N/A')}")
        return True, version_info
    
    def check_package_json_exists(self, project_path: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if package.json exists and parse its contents.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Tuple of (exists, package_info)
        """
        package_json_path = os.path.join(project_path, 'package.json')
        
        if not os.path.exists(package_json_path):
            return False, {"error": "package.json not found"}
        
        try:
            with open(package_json_path, 'r', encoding='utf-8') as f:
                package_data = json.load(f)
            
            return True, {
                "name": package_data.get("name", "unknown"),
                "version": package_data.get("version", "unknown"),
                "scripts": package_data.get("scripts", {}),
                "dependencies": package_data.get("dependencies", {}),
                "devDependencies": package_data.get("devDependencies", {}),
                "path": package_json_path
            }
        except json.JSONDecodeError as e:
            return False, {"error": f"Invalid package.json: {str(e)}"}
        except Exception as e:
            return False, {"error": f"Error reading package.json: {str(e)}"}
    
    def install_dependencies(self, project_path: str, production_only: bool = False) -> Tuple[bool, str]:
        """
        Install npm dependencies in the specified project directory.
        
        Args:
            project_path: Path to the project directory containing package.json
            production_only: Whether to install only production dependencies
            
        Returns:
            Tuple of (success, error_message_if_failed)
        """
        self._update_status(f"Installing npm dependencies in {project_path}...")
        
        # Check if package.json exists
        exists, package_info = self.check_package_json_exists(project_path)
        if not exists:
            error_msg = f"Cannot install dependencies: {package_info.get('error', 'Unknown error')}"
            self._update_status(error_msg)
            return False, error_msg
        
        # Prepare install command
        install_command = ['npm', 'install']
        if production_only:
            install_command.append('--production')
        
        # Add additional flags for better reliability
        install_command.extend(['--no-audit', '--no-fund'])
        
        success, stdout, stderr = self._run_node_command(install_command, cwd=project_path, timeout=900)  # 15 minutes
        
        if success:
            self._update_status("npm dependencies installed successfully")
            return True, ""
        else:
            error_msg = f"Failed to install npm dependencies: {stderr}"
            self._update_status(error_msg)
            return False, error_msg
    
    def run_build_script(self, project_path: str, script_name: str = "build") -> Tuple[bool, str]:
        """
        Execute an npm script (e.g., build, dev, start).
        
        Args:
            project_path: Path to the project directory
            script_name: Name of the npm script to run
            
        Returns:
            Tuple of (success, error_message_if_failed)
        """
        self._update_status(f"Running npm script '{script_name}' in {project_path}...")
        
        # Check if package.json exists and has the script
        exists, package_info = self.check_package_json_exists(project_path)
        if not exists:
            error_msg = f"Cannot run script: {package_info.get('error', 'Unknown error')}"
            self._update_status(error_msg)
            return False, error_msg
        
        scripts = package_info.get("scripts", {})
        if script_name not in scripts:
            error_msg = f"Script '{script_name}' not found in package.json"
            self._update_status(error_msg)
            return False, error_msg
        
        # Run the script
        run_command = ['npm', 'run', script_name]
        success, stdout, stderr = self._run_node_command(run_command, cwd=project_path, timeout=1800)  # 30 minutes
        
        if success:
            self._update_status(f"npm script '{script_name}' completed successfully")
            return True, ""
        else:
            error_msg = f"Failed to run npm script '{script_name}': {stderr}"
            self._update_status(error_msg)
            return False, error_msg
    
    def start_dev_server(self, project_path: str, script_name: str = "dev") -> Tuple[bool, subprocess.Popen, str]:
        """
        Start npm development server as a background process.
        
        Args:
            project_path: Path to the project directory
            script_name: Name of the dev script (default: "dev")
            
        Returns:
            Tuple of (success, process_object, error_message_if_failed)
        """
        self._update_status(f"Starting npm dev server '{script_name}' in {project_path}...")
        
        # Check if package.json exists and has the script
        exists, package_info = self.check_package_json_exists(project_path)
        if not exists:
            error_msg = f"Cannot start dev server: {package_info.get('error', 'Unknown error')}"
            self._update_status(error_msg)
            return False, None, error_msg
        
        scripts = package_info.get("scripts", {})
        if script_name not in scripts:
            error_msg = f"Dev script '{script_name}' not found in package.json"
            self._update_status(error_msg)
            return False, None, error_msg
        
        try:
            # Get platform-specific process creation flags
            flags_dict = PlatformUtils.create_no_window_flags()
            
            # Prepare command
            dev_command = ['npm', 'run', script_name]
            if PlatformUtils.get_os_type() == 'windows':
                dev_command[0] = 'npm.cmd'
            
            # Prepare subprocess arguments
            popen_args = {
                'cwd': project_path,
                'stdout': subprocess.PIPE,
                'stderr': subprocess.PIPE,
                'text': True
            }
            
            # Add platform-specific flags
            if PlatformUtils.get_os_type() == 'windows':
                popen_args['creationflags'] = flags_dict.get('creationflags', 0)
                popen_args['startupinfo'] = flags_dict.get('startupinfo')
            else:
                # On Unix, start a new session so we can kill the whole group on Stop
                popen_args['start_new_session'] = True
            
            # Start the process
            process = subprocess.Popen(dev_command, **popen_args)
            
            self._update_status(f"npm dev server '{script_name}' started with PID {process.pid}")
            return True, process, ""
            
        except Exception as e:
            error_msg = f"Failed to start npm dev server: {str(e)}"
            self._update_status(error_msg)
            return False, None, error_msg
    
    def check_node_modules_exists(self, project_path: str) -> bool:
        """
        Check if node_modules directory exists and is not empty.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            True if node_modules exists and has content
        """
        node_modules_path = os.path.join(project_path, 'node_modules')
        
        if not os.path.exists(node_modules_path):
            return False
        
        if not os.path.isdir(node_modules_path):
            return False
        
        # Check if directory has content
        try:
            return len(os.listdir(node_modules_path)) > 0
        except OSError:
            return False
    
    def clean_node_modules(self, project_path: str) -> Tuple[bool, str]:
        """
        Remove node_modules directory to force clean install.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Tuple of (success, error_message_if_failed)
        """
        self._update_status(f"Cleaning node_modules in {project_path}...")
        
        node_modules_path = os.path.join(project_path, 'node_modules')
        
        if not os.path.exists(node_modules_path):
            self._update_status("node_modules directory does not exist")
            return True, ""
        
        try:
            import shutil
            shutil.rmtree(node_modules_path)
            self._update_status("node_modules directory removed successfully")
            return True, ""
        except Exception as e:
            error_msg = f"Failed to remove node_modules: {str(e)}"
            self._update_status(error_msg)
            return False, error_msg
    
    def get_installed_packages(self, project_path: str) -> Tuple[bool, Dict[str, str]]:
        """
        Get list of installed npm packages and their versions.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Tuple of (success, packages_dict)
        """
        success, stdout, stderr = self._run_node_command(['npm', 'list', '--json', '--depth=0'], cwd=project_path)
        
        if success:
            try:
                package_data = json.loads(stdout)
                dependencies = package_data.get('dependencies', {})
                
                # Extract package names and versions
                packages = {}
                for name, info in dependencies.items():
                    if isinstance(info, dict) and 'version' in info:
                        packages[name] = info['version']
                    else:
                        packages[name] = 'unknown'
                
                return True, packages
            except json.JSONDecodeError:
                return False, {}
        else:
            return False, {}
    
    def check_script_exists(self, project_path: str, script_name: str) -> bool:
        """
        Check if a specific npm script exists in package.json.
        
        Args:
            project_path: Path to the project directory
            script_name: Name of the script to check
            
        Returns:
            True if script exists
        """
        exists, package_info = self.check_package_json_exists(project_path)
        if not exists:
            return False
        
        scripts = package_info.get("scripts", {})
        return script_name in scripts
    
    def get_available_scripts(self, project_path: str) -> Tuple[bool, List[str]]:
        """
        Get list of available npm scripts.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Tuple of (success, list_of_script_names)
        """
        exists, package_info = self.check_package_json_exists(project_path)
        if not exists:
            return False, []
        
        scripts = package_info.get("scripts", {})
        return True, list(scripts.keys())
