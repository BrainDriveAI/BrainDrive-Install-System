"""
Unit tests for git_manager.py
Tests Git repository operations and version control functionality.
"""

import pytest
import os
import sys
import tempfile
import shutil
import subprocess
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from git_manager import GitManager


class TestGitManager:
    """Test suite for GitManager class."""
    
    def test_git_manager_initialization(self):
        """Test GitManager initialization."""
        status_updater = Mock()
        git_manager = GitManager(status_updater)
        
        assert git_manager.status_updater == status_updater
        assert hasattr(git_manager, 'status_updater')
    
    def test_git_manager_initialization_no_updater(self):
        """Test GitManager initialization without status updater."""
        git_manager = GitManager()
        
        assert git_manager.status_updater is None
    
    @patch('subprocess.run')
    def test_check_git_available_success(self, mock_run):
        """Test successful Git availability check."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="git version 2.34.1\n",
            stderr=""
        )
        
        git_manager = GitManager()
        is_available, version = git_manager.check_git_available()
        
        assert is_available is True
        assert version == "git version 2.34.1"
        
        # Verify subprocess call
        mock_run.assert_called_once_with(
            ['git', '--version'],
            capture_output=True,
            text=True,
            timeout=30
        )
    
    @patch('subprocess.run')
    def test_check_git_available_failure(self, mock_run):
        """Test Git availability check when Git is not available."""
        mock_run.side_effect = FileNotFoundError()
        
        git_manager = GitManager()
        is_available, version = git_manager.check_git_available()
        
        assert is_available is False
        assert version is None
    
    @patch('subprocess.run')
    def test_check_git_available_error(self, mock_run):
        """Test Git availability check with command error."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="git: command not found"
        )
        
        git_manager = GitManager()
        is_available, version = git_manager.check_git_available()
        
        assert is_available is False
        assert version is None
    
    @patch('subprocess.run')
    def test_clone_repository_success(self, mock_run):
        """Test successful repository cloning."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        status_updater = Mock()
        git_manager = GitManager(status_updater)
        
        repo_url = "https://github.com/test/repo.git"
        target_path = "/tmp/test_repo"
        
        result = git_manager.clone_repository(repo_url, target_path)
        
        assert result is True
        
        # Verify subprocess call
        expected_cmd = ['git', 'clone', repo_url, target_path]
        mock_run.assert_called_once_with(
            expected_cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        # Verify status updates
        status_updater.update_status.assert_called()
    
    @patch('subprocess.run')
    def test_clone_repository_with_branch(self, mock_run):
        """Test repository cloning with specific branch."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        git_manager = GitManager()
        
        repo_url = "https://github.com/test/repo.git"
        target_path = "/tmp/test_repo"
        branch = "develop"
        
        result = git_manager.clone_repository(repo_url, target_path, branch)
        
        assert result is True
        
        # Verify subprocess call with branch
        expected_cmd = ['git', 'clone', '-b', branch, repo_url, target_path]
        mock_run.assert_called_once_with(
            expected_cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
    
    @patch('subprocess.run')
    def test_clone_repository_failure(self, mock_run):
        """Test repository cloning failure."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="fatal: repository not found"
        )
        status_updater = Mock()
        git_manager = GitManager(status_updater)
        
        repo_url = "https://github.com/invalid/repo.git"
        target_path = "/tmp/test_repo"
        
        result = git_manager.clone_repository(repo_url, target_path)
        
        assert result is False
        
        # Verify error status update
        status_updater.set_error.assert_called()
    
    @patch('subprocess.run')
    def test_clone_repository_timeout(self, mock_run):
        """Test repository cloning timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(['git', 'clone'], 300)
        git_manager = GitManager()
        
        repo_url = "https://github.com/test/repo.git"
        target_path = "/tmp/test_repo"
        
        result = git_manager.clone_repository(repo_url, target_path)
        
        assert result is False
    
    def test_get_repository_status_valid_repo(self, temp_dir, mock_git_repo):
        """Test repository status check for valid repository."""
        repo_path = mock_git_repo(temp_dir)
        git_manager = GitManager()
        
        status = git_manager.get_repository_status(repo_path)
        
        assert status['exists'] is True
        assert status['is_git_repo'] is True
        assert status['path'] == repo_path
    
    def test_get_repository_status_invalid_path(self):
        """Test repository status check for invalid path."""
        git_manager = GitManager()
        invalid_path = "/nonexistent/path"
        
        status = git_manager.get_repository_status(invalid_path)
        
        assert status['exists'] is False
        assert status['is_git_repo'] is False
        assert status['path'] == invalid_path
    
    def test_get_repository_status_not_git_repo(self, temp_dir):
        """Test repository status check for non-Git directory."""
        git_manager = GitManager()
        
        status = git_manager.get_repository_status(temp_dir)
        
        assert status['exists'] is True
        assert status['is_git_repo'] is False
        assert status['path'] == temp_dir
    
    @patch('subprocess.run')
    def test_pull_updates_success(self, mock_run):
        """Test successful repository update."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Already up to date.\n",
            stderr=""
        )
        status_updater = Mock()
        git_manager = GitManager(status_updater)
        
        repo_path = "/tmp/test_repo"
        result = git_manager.pull_updates(repo_path)
        
        assert result is True
        
        # Verify subprocess call
        expected_cmd = ['git', 'pull', 'origin', 'main']
        mock_run.assert_called_once_with(
            expected_cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        # Verify status updates
        status_updater.update_status.assert_called()
    
    @patch('subprocess.run')
    def test_pull_updates_with_branch(self, mock_run):
        """Test repository update with specific branch."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        git_manager = GitManager()
        
        repo_path = "/tmp/test_repo"
        branch = "develop"
        
        result = git_manager.pull_updates(repo_path, branch)
        
        assert result is True
        
        # Verify subprocess call with branch
        expected_cmd = ['git', 'pull', 'origin', branch]
        mock_run.assert_called_once_with(
            expected_cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=300
        )
    
    @patch('subprocess.run')
    def test_pull_updates_failure(self, mock_run):
        """Test repository update failure."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="fatal: not a git repository"
        )
        status_updater = Mock()
        git_manager = GitManager(status_updater)
        
        repo_path = "/tmp/not_a_repo"
        result = git_manager.pull_updates(repo_path)
        
        assert result is False
        
        # Verify error status update
        status_updater.set_error.assert_called()
    
    @patch('subprocess.run')
    def test_get_current_branch_success(self, mock_run):
        """Test getting current branch name."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="main\n",
            stderr=""
        )
        git_manager = GitManager()
        
        repo_path = "/tmp/test_repo"
        branch = git_manager.get_current_branch(repo_path)
        
        assert branch == "main"
        
        # Verify subprocess call
        expected_cmd = ['git', 'rev-parse', '--abbrev-ref', 'HEAD']
        mock_run.assert_called_once_with(
            expected_cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )
    
    @patch('subprocess.run')
    def test_get_current_branch_failure(self, mock_run):
        """Test getting current branch name failure."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="fatal: not a git repository"
        )
        git_manager = GitManager()
        
        repo_path = "/tmp/not_a_repo"
        branch = git_manager.get_current_branch(repo_path)
        
        assert branch is None
    
    @patch('subprocess.run')
    def test_get_commit_hash_success(self, mock_run):
        """Test getting current commit hash."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="abc123def456\n",
            stderr=""
        )
        git_manager = GitManager()
        
        repo_path = "/tmp/test_repo"
        commit_hash = git_manager.get_commit_hash(repo_path)
        
        assert commit_hash == "abc123def456"
        
        # Verify subprocess call
        expected_cmd = ['git', 'rev-parse', 'HEAD']
        mock_run.assert_called_once_with(
            expected_cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )
    
    @patch('subprocess.run')
    def test_get_commit_hash_short(self, mock_run):
        """Test getting short commit hash."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="abc123d\n",
            stderr=""
        )
        git_manager = GitManager()
        
        repo_path = "/tmp/test_repo"
        commit_hash = git_manager.get_commit_hash(repo_path, short=True)
        
        assert commit_hash == "abc123d"
        
        # Verify subprocess call with --short flag
        expected_cmd = ['git', 'rev-parse', '--short', 'HEAD']
        mock_run.assert_called_once_with(
            expected_cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )
    
    @patch('subprocess.run')
    def test_check_for_updates_available(self, mock_run):
        """Test checking for available updates."""
        # Mock git fetch and git status calls
        mock_run.side_effect = [
            Mock(returncode=0, stdout="", stderr=""),  # git fetch
            Mock(returncode=0, stdout="Your branch is behind 'origin/main' by 2 commits.\n", stderr="")  # git status
        ]
        git_manager = GitManager()
        
        repo_path = "/tmp/test_repo"
        has_updates = git_manager.check_for_updates(repo_path)
        
        assert has_updates is True
        
        # Verify both subprocess calls
        expected_calls = [
            call(['git', 'fetch'], cwd=repo_path, capture_output=True, text=True, timeout=60),
            call(['git', 'status', '-uno'], cwd=repo_path, capture_output=True, text=True, timeout=30)
        ]
        mock_run.assert_has_calls(expected_calls)
    
    @patch('subprocess.run')
    def test_check_for_updates_up_to_date(self, mock_run):
        """Test checking for updates when up to date."""
        # Mock git fetch and git status calls
        mock_run.side_effect = [
            Mock(returncode=0, stdout="", stderr=""),  # git fetch
            Mock(returncode=0, stdout="Your branch is up to date with 'origin/main'.\n", stderr="")  # git status
        ]
        git_manager = GitManager()
        
        repo_path = "/tmp/test_repo"
        has_updates = git_manager.check_for_updates(repo_path)
        
        assert has_updates is False
    
    @patch('subprocess.run')
    def test_check_for_updates_failure(self, mock_run):
        """Test checking for updates with failure."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="fatal: not a git repository"
        )
        git_manager = GitManager()
        
        repo_path = "/tmp/not_a_repo"
        has_updates = git_manager.check_for_updates(repo_path)
        
        assert has_updates is False
    
    @patch('subprocess.run')
    def test_reset_repository_success(self, mock_run):
        """Test successful repository reset."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        status_updater = Mock()
        git_manager = GitManager(status_updater)
        
        repo_path = "/tmp/test_repo"
        result = git_manager.reset_repository(repo_path)
        
        assert result is True
        
        # Verify subprocess call
        expected_cmd = ['git', 'reset', '--hard', 'HEAD']
        mock_run.assert_called_once_with(
            expected_cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Verify status updates
        status_updater.update_status.assert_called()
    
    @patch('subprocess.run')
    def test_reset_repository_to_commit(self, mock_run):
        """Test repository reset to specific commit."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        git_manager = GitManager()
        
        repo_path = "/tmp/test_repo"
        commit_hash = "abc123def456"
        
        result = git_manager.reset_repository(repo_path, commit_hash)
        
        assert result is True
        
        # Verify subprocess call with commit hash
        expected_cmd = ['git', 'reset', '--hard', commit_hash]
        mock_run.assert_called_once_with(
            expected_cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=60
        )
    
    @patch('subprocess.run')
    def test_clean_repository_success(self, mock_run):
        """Test successful repository cleaning."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        git_manager = GitManager()
        
        repo_path = "/tmp/test_repo"
        result = git_manager.clean_repository(repo_path)
        
        assert result is True
        
        # Verify subprocess call
        expected_cmd = ['git', 'clean', '-fd']
        mock_run.assert_called_once_with(
            expected_cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=60
        )
    
    def test_validate_repository_url_valid_https(self):
        """Test repository URL validation for HTTPS URLs."""
        git_manager = GitManager()
        
        valid_urls = [
            "https://github.com/user/repo.git",
            "https://gitlab.com/user/repo.git",
            "https://bitbucket.org/user/repo.git"
        ]
        
        for url in valid_urls:
            assert git_manager.validate_repository_url(url) is True
    
    def test_validate_repository_url_valid_ssh(self):
        """Test repository URL validation for SSH URLs."""
        git_manager = GitManager()
        
        valid_urls = [
            "git@github.com:user/repo.git",
            "git@gitlab.com:user/repo.git",
            "ssh://git@bitbucket.org/user/repo.git"
        ]
        
        for url in valid_urls:
            assert git_manager.validate_repository_url(url) is True
    
    def test_validate_repository_url_invalid(self):
        """Test repository URL validation for invalid URLs."""
        git_manager = GitManager()
        
        invalid_urls = [
            "not_a_url",
            "http://example.com",  # Not a Git URL
            "ftp://example.com/repo.git",  # Wrong protocol
            "",  # Empty string
            None  # None value
        ]
        
        for url in invalid_urls:
            assert git_manager.validate_repository_url(url) is False
    
    @patch('subprocess.run')
    def test_get_repository_info_success(self, mock_run):
        """Test getting repository information."""
        # Mock multiple git commands
        mock_run.side_effect = [
            Mock(returncode=0, stdout="main\n", stderr=""),  # current branch
            Mock(returncode=0, stdout="abc123def456\n", stderr=""),  # commit hash
            Mock(returncode=0, stdout="origin\thttps://github.com/user/repo.git (fetch)\n", stderr=""),  # remote URL
            Mock(returncode=0, stdout="Your branch is up to date with 'origin/main'.\n", stderr="")  # status
        ]
        
        git_manager = GitManager()
        repo_path = "/tmp/test_repo"
        
        info = git_manager.get_repository_info(repo_path)
        
        assert info['branch'] == "main"
        assert info['commit_hash'] == "abc123def456"
        assert info['remote_url'] == "https://github.com/user/repo.git"
        assert info['status'] == "up to date"
        assert info['path'] == repo_path
    
    @patch('subprocess.run')
    def test_get_repository_info_failure(self, mock_run):
        """Test getting repository information with failure."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="fatal: not a git repository"
        )
        
        git_manager = GitManager()
        repo_path = "/tmp/not_a_repo"
        
        info = git_manager.get_repository_info(repo_path)
        
        assert info['branch'] is None
        assert info['commit_hash'] is None
        assert info['remote_url'] is None
        assert info['status'] is None
        assert info['path'] == repo_path


class TestGitManagerIntegration:
    """Integration tests for GitManager with real Git operations."""
    
    @pytest.mark.slow
    @patch('subprocess.run')
    def test_full_clone_workflow(self, mock_run):
        """Test complete clone workflow."""
        # Mock successful Git operations
        mock_run.side_effect = [
            Mock(returncode=0, stdout="git version 2.34.1\n", stderr=""),  # check availability
            Mock(returncode=0, stdout="", stderr=""),  # clone
            Mock(returncode=0, stdout="main\n", stderr=""),  # get branch
            Mock(returncode=0, stdout="abc123\n", stderr="")  # get commit
        ]
        
        status_updater = Mock()
        git_manager = GitManager(status_updater)
        
        # Check Git availability
        is_available, version = git_manager.check_git_available()
        assert is_available is True
        
        # Clone repository
        repo_url = "https://github.com/test/repo.git"
        target_path = "/tmp/test_repo"
        clone_success = git_manager.clone_repository(repo_url, target_path)
        assert clone_success is True
        
        # Get repository info
        branch = git_manager.get_current_branch(target_path)
        commit = git_manager.get_commit_hash(target_path, short=True)
        
        assert branch == "main"
        assert commit == "abc123"
        
        # Verify status updates were called
        assert status_updater.update_status.call_count >= 2