"""
Process Manager for BrainDrive Installer
Handles dual server process management for backend and frontend services.
"""

import os
import subprocess
import psutil
import time
import logging
import signal
from typing import Optional, Tuple, Dict, Any, List
from braindrive_installer.core.platform_utils import PlatformUtils


class ProcessManager:
    """Manages dual server processes for BrainDrive installation."""
    
    def __init__(self, status_updater=None):
        """
        Initialize Process Manager.
        
        Args:
            status_updater: Optional status updater for progress tracking
        """
        self.status_updater = status_updater
        self.logger = logging.getLogger(__name__)
        self.processes = {}  # Dictionary to track named processes
        
    def _update_status(self, message: str, progress: Optional[int] = None):
        """Update status if status_updater is available."""
        if self.status_updater:
            self.status_updater.update_status(message, "", progress or 0)
        self.logger.info(message)
    
    def log_process_debug(self, name: str, include_output: bool = True, logger: Optional[logging.Logger] = None):
        """Log detailed information about a tracked process."""
        target_logger = logger or self.logger
        info = self.processes.get(name)
        if not info:
            target_logger.error("No tracked process named '%s'", name)
            return
        
        process = info.get("process")
        command_str = info.get("command_str") or " ".join(info.get("command", []))
        cwd_display = info.get("cwd") or os.getcwd()
        pid = info.get("pid")
        return_code = process.poll() if process else None
        
        target_logger.error(
            "Process '%s': pid=%s returncode=%s command=%s cwd=%s",
            name, pid, return_code, command_str, cwd_display
        )
        
        if include_output and process:
            if return_code is not None and not info.get("captured_output"):
                try:
                    stdout_data, stderr_data = process.communicate(timeout=1)
                except Exception as exc:
                    stdout_data, stderr_data = "", f"<failed to capture stderr: {exc}>"
                info["captured_output"] = True
                info["stdout"] = stdout_data
                info["stderr"] = stderr_data
            
            stdout_snapshot = info.get("stdout")
            stderr_snapshot = info.get("stderr")
            if stdout_snapshot:
                target_logger.error("Process '%s' stdout:%s%s", name, os.linesep, stdout_snapshot.strip())
            if stderr_snapshot:
                target_logger.error("Process '%s' stderr:%s%s", name, os.linesep, stderr_snapshot.strip())
    
    def start_process(self, name: str, command: List[str], cwd: Optional[str] = None, 
                     env: Optional[Dict[str, str]] = None, 
                     wait_for_startup: bool = False,
                     startup_timeout: int = 30) -> Tuple[bool, str]:
        """
        Start and track a named process.
        
        Args:
            name: Unique name for the process
            command: Command to execute as list of strings
            cwd: Working directory for the process
            env: Environment variables for the process
            wait_for_startup: Whether to wait for process to be ready
            startup_timeout: Timeout in seconds for startup wait
            
        Returns:
            Tuple of (success, error_message_if_failed)
        """
        command_str = " ".join(command)
        cwd_display = cwd or os.getcwd()
        self._update_status(f"Starting process '{name}'...")
        self._update_status(f" • Command: {command_str}")
        self._update_status(f" • Working directory: {cwd_display}")
        
        # Check if process with this name is already running
        if name in self.processes:
            if self.is_process_running(name):
                self._update_status(f"Process '{name}' is already running")
                return True, ""
            else:
                # Clean up dead process entry
                del self.processes[name]
        
        try:
            # Get platform-specific process creation flags
            flags_dict = PlatformUtils.create_no_window_flags()
            
            # Prepare environment
            process_env = os.environ.copy()
            if env:
                process_env.update(env)
            
            # Prepare subprocess arguments
            popen_args = {
                'cwd': cwd,
                'env': process_env,
                'stdout': subprocess.PIPE,
                'stderr': subprocess.PIPE,
                'text': True
            }
            
            # Add platform-specific flags
            if PlatformUtils.get_os_type() == 'windows':
                popen_args['creationflags'] = flags_dict.get('creationflags', 0)
                popen_args['startupinfo'] = flags_dict.get('startupinfo')
            
            # Start the process
            process = subprocess.Popen(command, **popen_args)
            
            # Store process information
            self.processes[name] = {
                "process": process,
                "command": command,
                "command_str": command_str,
                "cwd": cwd,
                "env": env,
                "start_time": time.time(),
                "pid": process.pid,
                "captured_output": False,
                "stdout": "",
                "stderr": ""
            }
            
            self._update_status(f"Process '{name}' started with PID {process.pid}")
            
            # Wait for startup if requested
            if wait_for_startup:
                self._update_status(f"Waiting for process '{name}' to be ready...")
                if not self._wait_for_process_ready(name, startup_timeout):
                    error_msg = f"Process '{name}' failed to start within {startup_timeout} seconds"
                    self._update_status(error_msg)
                    self.stop_process(name)
                    return False, error_msg
            
            return True, ""
            
        except Exception as e:
            error_msg = f"Failed to start process '{name}' (command: {command_str}, cwd={cwd_display}): {str(e)}"
            self._update_status(error_msg)
            return False, error_msg
    
    def stop_process(self, name: str, graceful_timeout: int = 10) -> Tuple[bool, str]:
        """
        Stop a named process gracefully, including all child processes.
        
        Args:
            name: Name of the process to stop
            graceful_timeout: Timeout in seconds for graceful shutdown
            
        Returns:
            Tuple of (success, error_message_if_failed)
        """
        self._update_status(f"Stopping process '{name}'...")
        
        if name not in self.processes:
            self._update_status(f"Process '{name}' is not being tracked")
            return True, ""
        
        process_info = self.processes[name]
        process = process_info["process"]
        
        try:
            # Check if process is still running
            if not self.is_process_running(name):
                self._update_status(f"Process '{name}' is already stopped")
                del self.processes[name]
                return True, ""
            
            # Get the process tree (parent + all children) using psutil
            import psutil
            try:
                parent_process = psutil.Process(process_info["pid"])
                process_tree = [parent_process] + parent_process.children(recursive=True)
                self._update_status(f"Found {len(process_tree)} processes in tree for '{name}'")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # Fallback to original process if psutil fails
                process_tree = [process]
            
            # Try graceful shutdown first
            self._update_status(f"Attempting graceful shutdown of process tree for '{name}'...")
            
            # Send termination signal to all processes in the tree
            for proc in process_tree:
                try:
                    if isinstance(proc, psutil.Process):
                        proc.terminate()
                    else:
                        # Original subprocess.Popen object
                        if PlatformUtils.get_os_type() == 'windows':
                            try:
                                proc.send_signal(signal.CTRL_BREAK_EVENT)
                            except:
                                proc.terminate()
                        else:
                            proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied, ProcessLookupError):
                    continue  # Process already dead or no access
            
            # Wait for graceful shutdown
            all_stopped = True
            try:
                # Wait for the main process
                process.wait(timeout=graceful_timeout)
                self._update_status(f"Main process '{name}' stopped gracefully")
                
                # Check if all child processes are also stopped
                for proc in process_tree:
                    if isinstance(proc, psutil.Process):
                        try:
                            if proc.is_running():
                                all_stopped = False
                                break
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue  # Process is dead
                            
            except subprocess.TimeoutExpired:
                all_stopped = False
            
            if not all_stopped:
                # Force kill all remaining processes
                self._update_status(f"Graceful shutdown timed out, force killing process tree for '{name}'...")
                for proc in process_tree:
                    try:
                        if isinstance(proc, psutil.Process):
                            if proc.is_running():
                                proc.kill()
                        else:
                            # Original subprocess.Popen object
                            proc.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied, ProcessLookupError):
                        continue  # Process already dead or no access
                
                # Wait a bit more for force kill
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass  # Process might be completely stuck
                    
                self._update_status(f"Process tree for '{name}' force killed")
            
            # Clean up process tracking
            del self.processes[name]
            return True, ""
            
        except Exception as e:
            error_msg = f"Error stopping process '{name}': {str(e)}"
            self._update_status(error_msg)
            return False, error_msg
    
    def is_process_running(self, name: str) -> bool:
        """
        Check if a named process is running.
        
        Args:
            name: Name of the process to check
            
        Returns:
            True if process is running
        """
        if name not in self.processes:
            return False
        
        process = self.processes[name]["process"]
        
        try:
            # Check if process is still alive
            return process.poll() is None
        except:
            return False
    
    def get_process_status(self, name: str) -> Dict[str, Any]:
        """
        Get detailed status information for a named process.
        
        Args:
            name: Name of the process
            
        Returns:
            Dictionary with process status information
        """
        if name not in self.processes:
            return {
                "exists": False,
                "running": False,
                "error": "Process not found"
            }
        
        process_info = self.processes[name]
        process = process_info["process"]
        
        status = {
            "exists": True,
            "name": name,
            "pid": process_info["pid"],
            "command": process_info["command"],
            "cwd": process_info["cwd"],
            "start_time": process_info["start_time"],
            "running": self.is_process_running(name)
        }
        
        if status["running"]:
            try:
                # Get additional process information using psutil
                ps_process = psutil.Process(process_info["pid"])
                status.update({
                    "cpu_percent": ps_process.cpu_percent(),
                    "memory_info": ps_process.memory_info()._asdict(),
                    "status": ps_process.status(),
                    "create_time": ps_process.create_time(),
                    "uptime": time.time() - process_info["start_time"]
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                status["running"] = False
                status["error"] = "Process no longer accessible"
        else:
            # Get exit code if process has terminated
            status["exit_code"] = process.poll()
        
        return status
    
    def stop_all_processes(self, graceful_timeout: int = 10) -> Tuple[bool, Dict[str, Any]]:
        """
        Stop all managed processes.
        
        Args:
            graceful_timeout: Timeout in seconds for graceful shutdown per process
            
        Returns:
            Tuple of (overall_success, stop_results)
        """
        self._update_status("Stopping all managed processes...")
        
        if not self.processes:
            self._update_status("No processes to stop")
            return True, {"processes_stopped": 0}
        
        stop_results = {
            "total_processes": len(self.processes),
            "processes_stopped": 0,
            "processes_failed": 0,
            "stop_details": {}
        }
        
        # Get list of process names to avoid dictionary changing during iteration
        process_names = list(self.processes.keys())
        
        for name in process_names:
            success, error_msg = self.stop_process(name, graceful_timeout)
            
            if success:
                stop_results["processes_stopped"] += 1
                stop_results["stop_details"][name] = {"status": "stopped"}
            else:
                stop_results["processes_failed"] += 1
                stop_results["stop_details"][name] = {
                    "status": "failed",
                    "error": error_msg
                }
        
        self._update_status(
            f"Process shutdown complete: {stop_results['processes_stopped']} stopped, "
            f"{stop_results['processes_failed']} failed"
        )
        
        overall_success = stop_results["processes_failed"] == 0
        return overall_success, stop_results
    
    def restart_process(self, name: str, startup_timeout: int = 30) -> Tuple[bool, str]:
        """
        Restart a named process.
        
        Args:
            name: Name of the process to restart
            startup_timeout: Timeout in seconds for startup wait
            
        Returns:
            Tuple of (success, error_message_if_failed)
        """
        self._update_status(f"Restarting process '{name}'...")
        
        if name not in self.processes:
            return False, f"Process '{name}' is not being tracked"
        
        # Store original process configuration
        process_info = self.processes[name]
        command = process_info["command"]
        cwd = process_info["cwd"]
        env = process_info["env"]
        
        # Stop the process
        success, error_msg = self.stop_process(name)
        if not success:
            return False, f"Failed to stop process for restart: {error_msg}"
        
        # Wait a moment before restarting
        time.sleep(1)
        
        # Start the process again
        return self.start_process(name, command, cwd, env, wait_for_startup=True, 
                                startup_timeout=startup_timeout)
    
    def get_all_process_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status information for all managed processes.
        
        Returns:
            Dictionary mapping process names to their status information
        """
        status_dict = {}
        
        for name in self.processes:
            status_dict[name] = self.get_process_status(name)
        
        return status_dict
    
    def check_port_available(self, port: int, host: str = "localhost") -> bool:
        """
        Check if a port is available for use.
        
        Args:
            port: Port number to check
            host: Host to check (default: localhost)
            
        Returns:
            True if port is available
        """
        import socket
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                return result != 0  # Port is available if connection failed
        except:
            return False
    
    def wait_for_port(self, port: int, host: str = "localhost", 
                     timeout: int = 30) -> bool:
        """
        Wait for a port to become available (service to start).
        
        Args:
            port: Port number to wait for
            host: Host to check (default: localhost)
            timeout: Timeout in seconds
            
        Returns:
            True if port becomes available within timeout
        """
        import socket
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(1)
                    result = sock.connect_ex((host, port))
                    if result == 0:  # Connection successful
                        return True
            except:
                pass
            
            time.sleep(1)
        
        return False
    
    def _wait_for_process_ready(self, name: str, timeout: int) -> bool:
        """
        Wait for a process to be ready (internal method).
        
        Args:
            name: Name of the process
            timeout: Timeout in seconds
            
        Returns:
            True if process appears to be ready
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if not self.is_process_running(name):
                return False  # Process died
            
            # For now, just wait a bit and assume it's ready
            # In a real implementation, you might check specific ports or log files
            time.sleep(2)
            
            # Simple readiness check - if process is still running after 2 seconds, assume ready
            if time.time() - start_time >= 2:
                return True
        
        return False
    
    def cleanup_dead_processes(self) -> int:
        """
        Clean up tracking for processes that are no longer running.
        
        Returns:
            Number of dead processes cleaned up
        """
        dead_processes = []
        
        for name in self.processes:
            if not self.is_process_running(name):
                dead_processes.append(name)
        
        for name in dead_processes:
            del self.processes[name]
            self.logger.debug(f"Cleaned up dead process: {name}")
        
        return len(dead_processes)
    
    def get_process_logs(self, name: str, lines: int = 50) -> Tuple[bool, str, str]:
        """
        Get recent stdout and stderr output from a process.
        
        Args:
            name: Name of the process
            lines: Number of recent lines to retrieve
            
        Returns:
            Tuple of (success, stdout_lines, stderr_lines)
        """
        if name not in self.processes:
            return False, "", "Process not found"
        
        process = self.processes[name]["process"]
        
        try:
            # This is a simplified implementation
            # In practice, you might want to implement proper log file handling
            stdout_data = ""
            stderr_data = ""
            
            if process.stdout:
                # Read available data (non-blocking)
                import select
                import sys
                
                if sys.platform != 'win32':
                    # Unix-like systems
                    ready, _, _ = select.select([process.stdout], [], [], 0)
                    if ready:
                        stdout_data = process.stdout.read()
                
            if process.stderr:
                if sys.platform != 'win32':
                    ready, _, _ = select.select([process.stderr], [], [], 0)
                    if ready:
                        stderr_data = process.stderr.read()
            
            return True, stdout_data, stderr_data

        except Exception as e:
            return False, "", f"Error reading process logs: {str(e)}"
    
    def adopt_orphaned_processes(self) -> int:
        """
        Detect and adopt orphaned BrainDrive processes that are running but not tracked.
        
        Returns:
            Number of processes adopted
        """
        import psutil
        adopted_count = 0
        
        try:
            self._update_status("Scanning for orphaned BrainDrive processes...")
            
            # Look for BrainDrive backend processes (uvicorn)
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                try:
                    cmdline = proc.info['cmdline']
                    if not cmdline:
                        continue
                    
                    cmdline_str = ' '.join(cmdline)
                    
                    # Check for BrainDrive backend (uvicorn main:app)
                    if ('uvicorn' in cmdline_str and
                        'main:app' in cmdline_str and
                        '--port 8005' in cmdline_str and
                        'braindrive_backend' not in self.processes):
                        
                        self._update_status(f"Found orphaned backend process (PID: {proc.info['pid']})")
                        
                        # Create a mock process object to track it
                        mock_process = type('MockProcess', (), {
                            'pid': proc.info['pid'],
                            'poll': lambda: None if psutil.pid_exists(proc.info['pid']) else 0,
                            'terminate': lambda: psutil.Process(proc.info['pid']).terminate(),
                            'kill': lambda: psutil.Process(proc.info['pid']).kill(),
                            'wait': lambda timeout=None: psutil.Process(proc.info['pid']).wait(timeout)
                        })()
                        
                        # Adopt the process
                        self.processes['braindrive_backend'] = {
                            "process": mock_process,
                            "command": cmdline,
                            "cwd": "unknown",
                            "env": {},
                            "start_time": proc.info['create_time'],
                            "pid": proc.info['pid'],
                            "adopted": True
                        }
                        adopted_count += 1
                        
                    # Check for BrainDrive frontend (npm run dev)
                    elif ('npm' in cmdline_str and
                          'run' in cmdline_str and
                          'dev' in cmdline_str and
                          'braindrive_frontend' not in self.processes):
                        
                        # Additional check to see if it's running on port 5173
                        try:
                            import socket
                            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            result = sock.connect_ex(('localhost', 5173))
                            sock.close()
                            
                            if result == 0:  # Port is open
                                self._update_status(f"Found orphaned frontend process (PID: {proc.info['pid']})")
                                
                                # Create a mock process object to track it
                                mock_process = type('MockProcess', (), {
                                    'pid': proc.info['pid'],
                                    'poll': lambda: None if psutil.pid_exists(proc.info['pid']) else 0,
                                    'terminate': lambda: psutil.Process(proc.info['pid']).terminate(),
                                    'kill': lambda: psutil.Process(proc.info['pid']).kill(),
                                    'wait': lambda timeout=None: psutil.Process(proc.info['pid']).wait(timeout)
                                })()
                                
                                # Adopt the process
                                self.processes['braindrive_frontend'] = {
                                    "process": mock_process,
                                    "command": cmdline,
                                    "cwd": "unknown",
                                    "env": {},
                                    "start_time": proc.info['create_time'],
                                    "pid": proc.info['pid'],
                                    "adopted": True
                                }
                                adopted_count += 1
                        except:
                            pass  # Skip if we can't check the port
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                    
            if adopted_count > 0:
                self._update_status(f"Adopted {adopted_count} orphaned BrainDrive processes")
            else:
                self._update_status("No orphaned BrainDrive processes found")
                
        except Exception as e:
            self._update_status(f"Error scanning for orphaned processes: {str(e)}")
            
        return adopted_count
    
    def kill_processes_by_pattern(self, patterns: list, description: str = "processes") -> int:
        """
        Kill all processes matching specific command line patterns.
        This is a backup cleanup method for stubborn processes.
        
        Args:
            patterns: List of strings to match in command lines
            description: Description for logging
            
        Returns:
            Number of processes killed
        """
        import psutil
        killed_count = 0
        
        try:
            self._update_status(f"Scanning for {description} to kill...")
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline']
                    if not cmdline:
                        continue
                    
                    cmdline_str = ' '.join(cmdline)
                    
                    # Check if any pattern matches
                    for pattern in patterns:
                        if pattern in cmdline_str:
                            self._update_status(f"Killing process (PID: {proc.info['pid']}): {pattern}")
                            psutil.Process(proc.info['pid']).kill()
                            killed_count += 1
                            break  # Don't double-kill the same process
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                    
            if killed_count > 0:
                self._update_status(f"Killed {killed_count} {description}")
            else:
                self._update_status(f"No {description} found to kill")
                
        except Exception as e:
            self._update_status(f"Error killing {description}: {str(e)}")
            
        return killed_count
