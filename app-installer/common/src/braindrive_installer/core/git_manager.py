"""
Git Manager for BrainDrive Installer
Handles Git repository operations including cloning, status checking, and updates.
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from braindrive_installer.core.platform_utils import PlatformUtils
from braindrive_installer.core.installer_logger import get_installer_logger


class GitManager:
    """Manages Git repository operations for BrainDrive installation."""
    
    def __init__(self, status_updater=None):
        """
        Initialize Git Manager.
        
        Args:
            status_updater: Optional status updater for progress tracking
        """
        self.status_updater = status_updater
        self.logger = get_installer_logger()
        
    def _update_status(self, message: str, progress: Optional[int] = None):
        """Update status if status_updater is available."""
        if self.status_updater:
            self.status_updater.update_status(message, "", progress or 0)
        self.logger.info(message)
    
    def _run_git_command(self, command: list, cwd: Optional[str] = None, 
                        capture_output: bool = True) -> Tuple[bool, str, str]:
        """
        Run a Git command and return success status and output.
        
        Args:
            command: Git command as list of strings
            cwd: Working directory for the command
            capture_output: Whether to capture stdout/stderr
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            # Ensure git is the first command
            if command[0] != 'git':
                command.insert(0, 'git')
            
            # Get platform-specific process creation flags
            flags_dict = PlatformUtils.create_no_window_flags()
            
            # Prepare subprocess arguments
            subprocess_args = {
                'cwd': cwd,
                'capture_output': capture_output,
                'text': True,
                'timeout': 300  # 5 minute timeout
            }
            
            # Add platform-specific flags
            if PlatformUtils.get_os_type() == 'windows':
                subprocess_args['creationflags'] = flags_dict.get('creationflags', 0)
                subprocess_args['startupinfo'] = flags_dict.get('startupinfo')
            
            result = subprocess.run(command, **subprocess_args)
            
            return result.returncode == 0, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            error_msg = f"Git command timed out: {' '.join(command)}"
            self.logger.error(error_msg)
            return False, "", error_msg
        except Exception as e:
            error_msg = f"Error running git command {' '.join(command)}: {str(e)}"
            self.logger.error(error_msg)
            return False, "", error_msg
    
    def check_git_available(self) -> Tuple[bool, str]:
        """
        Check if Git is installed and accessible.
        
        Returns:
            Tuple of (is_available, version_or_error)
        """
        self._update_status("Checking Git availability...")
        
        success, stdout, stderr = self._run_git_command(['--version'])
        
        if success:
            version = stdout.strip()
            self._update_status(f"Git found: {version}")
            return True, version
        else:
            error_msg = f"Git not found or not accessible: {stderr}"
            self._update_status(error_msg)
            return False, error_msg
    
    def clone_repository(self, repo_url: str, target_path: str,
                        branch: str = "main") -> Tuple[bool, str]:
        """
        Clone a Git repository with progress tracking.
        
        Args:
            repo_url: URL of the repository to clone
            target_path: Local path where repository should be cloned
            branch: Branch to clone (default: main)
            
        Returns:
            Tuple of (success, error_message_if_failed)
        """
        self.logger.info(f"Starting clone_repository: {repo_url} -> {target_path} (branch: {branch})")
        self._update_status(f"Cloning repository from {repo_url}...")
        
        # Check if target directory already exists
        if os.path.exists(target_path):
            self.logger.info(f"Target path already exists: {target_path}")
            if os.path.isdir(target_path) and os.listdir(target_path):
                # Directory exists and is not empty
                self.logger.info("Target directory is not empty, checking if it's a git repo")
                is_git_repo, _ = self.get_repository_status(target_path)
                if is_git_repo:
                    self.logger.info("Target directory is already a git repository, skipping clone")
                    self._update_status("Repository already exists, checking status...")
                    return True, ""
                else:
                    error_msg = f"Target directory {target_path} exists but is not a Git repository"
                    self.logger.error(error_msg)
                    self._update_status(error_msg)
                    return False, error_msg
        
        # Create parent directory if it doesn't exist
        parent_dir = os.path.dirname(target_path)
        if parent_dir:
            self.logger.info(f"Creating parent directory: {parent_dir}")
            os.makedirs(parent_dir, exist_ok=True)
        
        # Clone the repository
        clone_command = ['clone', '--progress', '--branch', branch, repo_url, target_path]
        self.logger.info(f"Executing git command: {' '.join(clone_command)}")
        success, stdout, stderr = self._run_git_command(clone_command)
        
        self.logger.info(f"Git clone result - Success: {success}")
        if stdout:
            self.logger.info(f"Git clone stdout: {stdout}")
        if stderr:
            self.logger.info(f"Git clone stderr: {stderr}")
        
        if success:
            self.logger.info(f"Repository cloned successfully to {target_path}")
            self._update_status(f"Repository cloned successfully to {target_path}")
            return True, ""
        else:
            error_msg = f"Failed to clone repository: {stderr}"
            self.logger.error(error_msg)
            self._update_status(error_msg)
            return False, error_msg
    
    def get_repository_status(self, repo_path: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if directory is a valid Git repository and get status information.
        
        Args:
            repo_path: Path to the repository directory
            
        Returns:
            Tuple of (is_valid_repo, status_info)
        """
        if not os.path.exists(repo_path):
            return False, {"error": "Directory does not exist"}
        
        # Check if it's a git repository
        success, stdout, stderr = self._run_git_command(['rev-parse', '--git-dir'], cwd=repo_path)
        
        if not success:
            return False, {"error": "Not a Git repository"}
        
        status_info = {
            "is_git_repo": True,
            "path": repo_path,
            "git_dir": stdout.strip()
        }
        
        # Get current branch
        success, stdout, stderr = self._run_git_command(['branch', '--show-current'], cwd=repo_path)
        if success:
            status_info["current_branch"] = stdout.strip()
        
        # Get remote URL
        success, stdout, stderr = self._run_git_command(['remote', 'get-url', 'origin'], cwd=repo_path)
        if success:
            status_info["remote_url"] = stdout.strip()
        
        # Check if working directory is clean
        success, stdout, stderr = self._run_git_command(['status', '--porcelain'], cwd=repo_path)
        if success:
            status_info["is_clean"] = len(stdout.strip()) == 0
            status_info["modified_files"] = stdout.strip().split('\n') if stdout.strip() else []
        
        # Get last commit info
        success, stdout, stderr = self._run_git_command(['log', '-1', '--pretty=format:%H|%s|%an|%ad'], cwd=repo_path)
        if success and stdout:
            commit_parts = stdout.split('|')
            if len(commit_parts) >= 4:
                status_info["last_commit"] = {
                    "hash": commit_parts[0],
                    "message": commit_parts[1],
                    "author": commit_parts[2],
                    "date": commit_parts[3]
                }
        
        return True, status_info
    
    def pull_updates(self, repo_path: str) -> Tuple[bool, str]:
        """
        Pull latest changes from the remote repository.
        
        Args:
            repo_path: Path to the repository directory
            
        Returns:
            Tuple of (success, error_message_if_failed)
        """
        self._update_status("Pulling latest changes from repository...")
        
        # Check if it's a valid repository
        is_valid, status_info = self.get_repository_status(repo_path)
        if not is_valid:
            error_msg = f"Invalid repository: {status_info.get('error', 'Unknown error')}"
            self._update_status(error_msg)
            return False, error_msg
        
        # Check if working directory is clean
        if not status_info.get("is_clean", False):
            error_msg = "Working directory has uncommitted changes. Cannot pull updates."
            self._update_status(error_msg)
            return False, error_msg
        
        # Pull changes
        success, stdout, stderr = self._run_git_command(['pull'], cwd=repo_path)
        
        if success:
            self._update_status("Repository updated successfully")
            return True, ""
        else:
            error_msg = f"Failed to pull updates: {stderr}"
            self._update_status(error_msg)
            return False, error_msg
    
    def pull_with_rebase(self, repo_path: str) -> Tuple[bool, str]:
        """
        Pull updates using --rebase to keep history linear.

        Args:
            repo_path: Path to the repository directory

        Returns:
            Tuple of (success, error_message_if_failed)
        """
        self._update_status("Pulling latest changes with rebase...")

        # Validate repository
        is_valid, status_info = self.get_repository_status(repo_path)
        if not is_valid:
            error_msg = f"Invalid repository: {status_info.get('error', 'Unknown error')}"
            self._update_status(error_msg)
            return False, error_msg

        success, stdout, stderr = self._run_git_command(['pull', '--rebase'], cwd=repo_path)

        if success:
            self._update_status("Repository rebased successfully")
            return True, ""

        error_msg = stderr or stdout or "Unknown git pull --rebase error"
        self._update_status(f"Failed to rebase repository: {error_msg}")
        return False, error_msg

    def checkout_branch(self, repo_path: str, branch: str) -> Tuple[bool, str]:
        """
        Checkout a specific branch.
        
        Args:
            repo_path: Path to the repository directory
            branch: Branch name to checkout
            
        Returns:
            Tuple of (success, error_message_if_failed)
        """
        self._update_status(f"Checking out branch: {branch}")
        
        # Check if it's a valid repository
        is_valid, status_info = self.get_repository_status(repo_path)
        if not is_valid:
            error_msg = f"Invalid repository: {status_info.get('error', 'Unknown error')}"
            self._update_status(error_msg)
            return False, error_msg
        
        # Checkout branch
        success, stdout, stderr = self._run_git_command(['checkout', branch], cwd=repo_path)
        
        if success:
            self._update_status(f"Successfully checked out branch: {branch}")
            return True, ""
        else:
            error_msg = f"Failed to checkout branch {branch}: {stderr}"
            self._update_status(error_msg)
            return False, error_msg
    
    def get_available_branches(self, repo_path: str) -> Tuple[bool, list]:
        """
        Get list of available branches.
        
        Args:
            repo_path: Path to the repository directory
            
        Returns:
            Tuple of (success, list_of_branches)
        """
        # Check if it's a valid repository
        is_valid, status_info = self.get_repository_status(repo_path)
        if not is_valid:
            return False, []
        
        # Get local branches
        success, stdout, stderr = self._run_git_command(['branch'], cwd=repo_path)
        
        if success:
            branches = []
            for line in stdout.strip().split('\n'):
                branch = line.strip().lstrip('* ')
                if branch:
                    branches.append(branch)
            return True, branches
        else:
            return False, []
    
    def reset_repository(self, repo_path: str, hard: bool = False) -> Tuple[bool, str]:
        """
        Reset repository to clean state.
        
        Args:
            repo_path: Path to the repository directory
            hard: Whether to perform hard reset (discards all changes)
            
        Returns:
            Tuple of (success, error_message_if_failed)
        """
        reset_type = "hard" if hard else "mixed"
        self._update_status(f"Performing {reset_type} reset...")
        
        # Check if it's a valid repository
        is_valid, status_info = self.get_repository_status(repo_path)
        if not is_valid:
            error_msg = f"Invalid repository: {status_info.get('error', 'Unknown error')}"
            self._update_status(error_msg)
            return False, error_msg
        
        # Reset repository
        reset_command = ['reset', f'--{reset_type}', 'HEAD']
        success, stdout, stderr = self._run_git_command(reset_command, cwd=repo_path)
        
        if success:
            self._update_status(f"Repository reset successfully ({reset_type})")
            return True, ""
        else:
            error_msg = f"Failed to reset repository: {stderr}"
            self._update_status(error_msg)
            return False, error_msg
    
    def get_commit_count(self, repo_path: str) -> Tuple[bool, int]:
        """
        Get total number of commits in the repository.
        
        Args:
            repo_path: Path to the repository directory
            
        Returns:
            Tuple of (success, commit_count)
        """
        # Check if it's a valid repository
        is_valid, status_info = self.get_repository_status(repo_path)
        if not is_valid:
            return False, 0
        
        # Get commit count
        success, stdout, stderr = self._run_git_command(['rev-list', '--count', 'HEAD'], cwd=repo_path)
        
        if success:
            try:
                count = int(stdout.strip())
                return True, count
            except ValueError:
                return False, 0
        else:
            return False, 0
