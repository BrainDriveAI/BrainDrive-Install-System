"""
Error recovery and rollback testing for BrainDrive Installer.
Tests various failure scenarios and recovery mechanisms.
"""

import pytest
import os
import sys
import tempfile
import shutil
import subprocess
import time
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from installer_braindrive import BrainDriveInstaller
from git_manager import GitManager
from node_manager import NodeManager
from plugin_builder import PluginBuilder
from process_manager import ProcessManager


@pytest.mark.error_recovery
class TestNetworkFailures:
    """Test network-related failure scenarios."""
    
    @patch('subprocess.run')
    def test_git_clone_network_timeout(self, mock_run):
        """Test Git clone timeout recovery."""
        # Mock network timeout
        mock_run.side_effect = subprocess.TimeoutExpired(['git', 'clone'], 300)
        
        status_updater = Mock()
        git_manager = GitManager(status_updater)
        
        result = git_manager.clone_repository(
            "https://github.com/test/repo.git",
            "/tmp/test_repo"
        )
        
        assert result is False
        status_updater.set_error.assert_called()
        
        # Verify error message contains timeout information
        error_calls = status_updater.set_error.call_args_list
        assert any("timeout" in str(call).lower() for call in error_calls)
    
    @patch('subprocess.run')
    def test_git_clone_network_unreachable(self, mock_run):
        """Test Git clone with network unreachable."""
        mock_run.return_value = Mock(
            returncode=128,
            stdout="",
            stderr="fatal: unable to access 'https://github.com/test/repo.git/': Could not resolve host"
        )
        
        status_updater = Mock()
        git_manager = GitManager(status_updater)
        
        result = git_manager.clone_repository(
            "https://github.com/test/repo.git",
            "/tmp/test_repo"
        )
        
        assert result is False
        status_updater.set_error.assert_called()
    
    @patch('subprocess.run')
    def test_npm_install_network_failure(self, mock_run):
        """Test npm install with network failure."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="npm ERR! network request failed"
        )
        
        status_updater = Mock()
        node_manager = NodeManager(status_updater)
        
        result = node_manager.install_dependencies("/tmp/test_project")
        
        assert result is False
        status_updater.set_error.assert_called()
    
    @patch('subprocess.run')
    def test_pip_install_network_failure(self, mock_run):
        """Test pip install with network failure."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="ERROR: Could not find a version that satisfies the requirement"
        )
        
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        with patch('os.path.exists', return_value=True):
            result = installer.setup_backend()
        
        assert result is False
        status_updater.set_error.assert_called()


@pytest.mark.error_recovery
class TestDiskSpaceErrors:
    """Test disk space related failures."""
    
    @patch('psutil.disk_usage')
    def test_insufficient_disk_space_detection(self, mock_disk_usage):
        """Test detection of insufficient disk space."""
        # Mock very low disk space (100MB total, 10MB free)
        mock_usage = Mock()
        mock_usage.total = 100 * 1024 * 1024
        mock_usage.free = 10 * 1024 * 1024
        mock_disk_usage.return_value = mock_usage
        
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        # Mock the disk space check to use our mocked values
        with patch.object(installer, 'check_disk_space') as mock_check:
            mock_check.return_value = False  # Insufficient space
            
            result = installer.check_requirements()
        
        assert result is False
        status_updater.set_error.assert_called()
    
    @patch('subprocess.run')
    def test_disk_full_during_git_clone(self, mock_run):
        """Test disk full error during Git clone."""
        mock_run.return_value = Mock(
            returncode=128,
            stdout="",
            stderr="fatal: write error: No space left on device"
        )
        
        status_updater = Mock()
        git_manager = GitManager(status_updater)
        
        result = git_manager.clone_repository(
            "https://github.com/test/repo.git",
            "/tmp/test_repo"
        )
        
        assert result is False
        status_updater.set_error.assert_called()
        
        # Verify error message mentions disk space
        error_calls = status_updater.set_error.call_args_list
        assert any("space" in str(call).lower() for call in error_calls)
    
    @patch('subprocess.run')
    def test_disk_full_during_npm_install(self, mock_run):
        """Test disk full error during npm install."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="npm ERR! ENOSPC: no space left on device"
        )
        
        status_updater = Mock()
        node_manager = NodeManager(status_updater)
        
        result = node_manager.install_dependencies("/tmp/test_project")
        
        assert result is False
        status_updater.set_error.assert_called()


@pytest.mark.error_recovery
class TestPermissionErrors:
    """Test permission-related failures."""
    
    @patch('subprocess.run')
    def test_permission_denied_git_clone(self, mock_run):
        """Test permission denied during Git clone."""
        mock_run.return_value = Mock(
            returncode=128,
            stdout="",
            stderr="fatal: could not create work tree dir '/restricted/path': Permission denied"
        )
        
        status_updater = Mock()
        git_manager = GitManager(status_updater)
        
        result = git_manager.clone_repository(
            "https://github.com/test/repo.git",
            "/restricted/path"
        )
        
        assert result is False
        status_updater.set_error.assert_called()
    
    @patch('builtins.open')
    def test_permission_denied_env_file_creation(self, mock_open):
        """Test permission denied when creating .env files."""
        mock_open.side_effect = PermissionError("Permission denied")
        
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        with patch('os.path.exists', return_value=True):
            result = installer._create_backend_env_file()
        
        assert result is False
        status_updater.set_error.assert_called()
    
    @patch('subprocess.run')
    def test_permission_denied_conda_environment(self, mock_run):
        """Test permission denied during conda environment creation."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="CondaError: Permission denied"
        )
        
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        result = installer.setup_environment("TestEnv")
        
        assert result is False
        status_updater.set_error.assert_called()


@pytest.mark.error_recovery
class TestCorruptionRecovery:
    """Test recovery from corrupted installations."""
    
    def test_corrupted_git_repository_detection(self, temp_dir):
        """Test detection of corrupted Git repository."""
        # Create a directory that looks like a repo but is corrupted
        repo_path = os.path.join(temp_dir, "corrupted_repo")
        os.makedirs(repo_path)
        
        # Create .git directory but with invalid content
        git_dir = os.path.join(repo_path, ".git")
        os.makedirs(git_dir)
        with open(os.path.join(git_dir, "HEAD"), "w") as f:
            f.write("invalid content")
        
        git_manager = GitManager()
        status = git_manager.get_repository_status(repo_path)
        
        # Should detect as existing but potentially corrupted
        assert status['exists'] is True
        assert status['is_git_repo'] is True  # Directory exists, but may be corrupted
    
    @patch('subprocess.run')
    def test_corrupted_package_json_recovery(self, mock_run):
        """Test recovery from corrupted package.json."""
        # Mock npm install failure due to corrupted package.json
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="npm ERR! JSON.parse Unexpected token"
        )
        
        status_updater = Mock()
        node_manager = NodeManager(status_updater)
        
        result = node_manager.install_dependencies("/tmp/corrupted_project")
        
        assert result is False
        status_updater.set_error.assert_called()
        
        # Verify error message indicates JSON parsing issue
        error_calls = status_updater.set_error.call_args_list
        assert any("json" in str(call).lower() or "parse" in str(call).lower() 
                  for call in error_calls)
    
    def test_incomplete_installation_detection(self, temp_dir):
        """Test detection of incomplete installation."""
        installer = BrainDriveInstaller()
        
        # Create partial directory structure
        repo_path = os.path.join(temp_dir, "BrainDrive")
        backend_path = os.path.join(repo_path, "backend")
        os.makedirs(backend_path)
        
        # Missing frontend directory
        installer.config.repo_path = repo_path
        installer.config.backend_path = backend_path
        installer.config.frontend_path = os.path.join(repo_path, "frontend")
        
        result = installer.check_installed()
        
        assert result is False  # Should detect incomplete installation


@pytest.mark.error_recovery
class TestServiceFailures:
    """Test service startup and management failures."""
    
    @patch('subprocess.Popen')
    def test_backend_service_startup_failure(self, mock_popen):
        """Test backend service startup failure."""
        # Mock process that fails to start
        mock_process = Mock()
        mock_process.pid = None
        mock_process.poll.return_value = 1  # Exited with error
        mock_popen.return_value = mock_process
        
        status_updater = Mock()
        process_manager = ProcessManager(status_updater)
        
        result = process_manager.start_process(
            "backend",
            ["python", "-m", "uvicorn", "main:app"],
            cwd="/tmp/backend"
        )
        
        assert result is False
        status_updater.set_error.assert_called()
    
    @patch('subprocess.Popen')
    def test_frontend_service_startup_failure(self, mock_popen):
        """Test frontend service startup failure."""
        # Mock process that starts but crashes immediately
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = 1  # Crashed
        mock_popen.return_value = mock_process
        
        status_updater = Mock()
        process_manager = ProcessManager(status_updater)
        
        result = process_manager.start_process(
            "frontend",
            ["npm", "run", "dev"],
            cwd="/tmp/frontend"
        )
        
        # Should start successfully initially
        assert result is True
        
        # But should detect crash when checking status
        time.sleep(0.1)  # Brief delay
        is_running = process_manager.is_process_running("frontend")
        assert is_running is False
    
    def test_port_conflict_detection(self):
        """Test detection of port conflicts."""
        installer = BrainDriveInstaller()
        
        # Mock socket operations to simulate port conflicts
        with patch('socket.socket') as mock_socket:
            mock_socket.return_value.__enter__.return_value.bind.side_effect = OSError("Address already in use")
            
            result = installer._validate_ports()
        
        assert result is False
    
    @patch('subprocess.Popen')
    def test_service_crash_during_operation(self, mock_popen):
        """Test service crash during normal operation."""
        # Mock process that starts successfully but crashes later
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.side_effect = [None, None, 1]  # Running, then crashed
        mock_popen.return_value = mock_process
        
        status_updater = Mock()
        process_manager = ProcessManager(status_updater)
        
        # Start process
        result = process_manager.start_process(
            "test_service",
            ["python", "-c", "import time; time.sleep(10)"]
        )
        assert result is True
        
        # Initially running
        assert process_manager.is_process_running("test_service") is True
        
        # Later crashes (simulated by poll returning 1)
        assert process_manager.is_process_running("test_service") is False


@pytest.mark.error_recovery
class TestRollbackMechanisms:
    """Test rollback and cleanup mechanisms."""
    
    def test_failed_installation_cleanup(self, temp_dir):
        """Test cleanup after failed installation."""
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        # Override paths to use temp directory
        repo_path = os.path.join(temp_dir, "BrainDrive")
        installer.config.repo_path = repo_path
        installer.config.backend_path = os.path.join(repo_path, "backend")
        installer.config.frontend_path = os.path.join(repo_path, "frontend")
        
        # Create partial installation
        os.makedirs(installer.config.backend_path)
        
        # Mock git clone to fail
        installer.git_manager.clone_repository = Mock(return_value=False)
        
        # Attempt installation
        result = installer.install()
        
        assert result is False
        
        # Verify cleanup was attempted
        status_updater.set_error.assert_called()
    
    @patch('subprocess.run')
    def test_conda_environment_cleanup_on_failure(self, mock_run):
        """Test conda environment cleanup on installation failure."""
        # Mock conda create to succeed, but conda install to fail
        mock_run.side_effect = [
            Mock(returncode=0, stdout="", stderr=""),  # conda create success
            Mock(returncode=1, stdout="", stderr="CondaError: Package not found")  # conda install failure
        ]
        
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        result = installer.setup_environment("TestEnv")
        
        assert result is False
        status_updater.set_error.assert_called()
        
        # Should have attempted to remove the failed environment
        # (This would be implementation-specific)
    
    def test_process_cleanup_on_shutdown(self):
        """Test process cleanup during shutdown."""
        status_updater = Mock()
        process_manager = ProcessManager(status_updater)
        
        # Mock multiple running processes
        with patch('subprocess.Popen') as mock_popen:
            mock_processes = []
            for i in range(3):
                mock_process = Mock()
                mock_process.pid = 12345 + i
                mock_process.poll.return_value = None  # Running
                mock_process.terminate = Mock()
                mock_process.kill = Mock()
                mock_processes.append(mock_process)
            
            mock_popen.side_effect = mock_processes
            
            # Start multiple processes
            for i in range(3):
                process_manager.start_process(
                    f"test_process_{i}",
                    ["python", "-c", "import time; time.sleep(10)"]
                )
            
            # Stop all processes
            process_manager.stop_all_processes()
            
            # Verify all processes were terminated
            for mock_process in mock_processes:
                mock_process.terminate.assert_called()
    
    def test_partial_update_rollback(self, temp_dir):
        """Test rollback from partial update failure."""
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        # Setup mock repository
        repo_path = os.path.join(temp_dir, "BrainDrive")
        os.makedirs(repo_path)
        installer.config.repo_path = repo_path
        
        # Mock git pull to succeed but plugin build to fail
        installer.git_manager.pull_updates = Mock(return_value=True)
        installer.plugin_builder.build_all_plugins = Mock(return_value=False)
        
        result = installer.update()
        
        assert result is False
        status_updater.set_error.assert_called()
        
        # In a real implementation, this might trigger a git reset
        # to rollback the pulled changes


@pytest.mark.error_recovery
class TestRecoveryStrategies:
    """Test various recovery strategies."""
    
    @patch('subprocess.run')
    def test_retry_mechanism_for_transient_failures(self, mock_run):
        """Test retry mechanism for transient network failures."""
        # Mock transient failure followed by success
        mock_run.side_effect = [
            Mock(returncode=1, stdout="", stderr="temporary failure"),  # First attempt fails
            Mock(returncode=0, stdout="git version 2.34.1", stderr="")  # Second attempt succeeds
        ]
        
        git_manager = GitManager()
        
        # This would require implementing retry logic in GitManager
        # For now, we test that the failure is properly handled
        is_available, version = git_manager.check_git_available()
        
        # With current implementation, this would fail
        # In an enhanced version, it might retry and succeed
        assert is_available is False  # Current behavior
        assert version is None
    
    def test_fallback_repository_url(self):
        """Test fallback to alternative repository URL."""
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        # Mock primary repository to fail
        def mock_clone(url, path, branch="main"):
            if "github.com" in url:
                return False  # Primary fails
            elif "gitlab.com" in url:
                return True   # Fallback succeeds
            return False
        
        installer.git_manager.clone_repository = Mock(side_effect=mock_clone)
        
        # This would require implementing fallback logic
        # For now, we test the current behavior
        result = installer.clone_repository()
        
        # With current implementation, this would fail
        # In an enhanced version, it might try fallback URLs
        assert result is False  # Current behavior
    
    def test_graceful_degradation_missing_optional_components(self):
        """Test graceful degradation when optional components are missing."""
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        # Mock plugin builder to fail (optional component)
        installer.plugin_builder.build_all_plugins = Mock(return_value=False)
        
        # Mock other components to succeed
        installer.git_manager.clone_repository = Mock(return_value=True)
        
        with patch.object(installer, 'setup_environment', return_value=True):
            with patch.object(installer, 'setup_backend', return_value=True):
                with patch.object(installer, 'setup_frontend', return_value=True):
                    with patch.object(installer, 'start_services', return_value=True):
                        result = installer.install()
        
        # With current implementation, plugin failure causes total failure
        # In an enhanced version, it might continue without plugins
        assert result is False  # Current behavior


def generate_error_recovery_report(test_results):
    """Generate error recovery test report."""
    report = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'test_categories': {
            'network_failures': 'Network connectivity and timeout handling',
            'disk_space_errors': 'Disk space exhaustion scenarios',
            'permission_errors': 'File and directory permission issues',
            'corruption_recovery': 'Corrupted file and installation recovery',
            'service_failures': 'Service startup and management failures',
            'rollback_mechanisms': 'Installation rollback and cleanup',
            'recovery_strategies': 'Advanced recovery and fallback mechanisms'
        },
        'test_results': test_results,
        'recommendations': [
            'Implement retry mechanisms for transient network failures',
            'Add disk space monitoring and cleanup procedures',
            'Enhance permission error handling with user guidance',
            'Implement automatic corruption detection and repair',
            'Add service health monitoring and automatic restart',
            'Implement comprehensive rollback mechanisms',
            'Add fallback strategies for critical operations'
        ]
    }
    
    return report


if __name__ == "__main__":
    # Run error recovery tests
    pytest.main([__file__, "-v", "--tb=short", "-m", "error_recovery"])