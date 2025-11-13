"""
Unit tests for installer_braindrive.py
Tests the main BrainDrive installer functionality.
"""

import pytest
import os
import sys
import tempfile
import shutil
import json
from unittest.mock import Mock, patch, MagicMock, call, mock_open
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from installer_braindrive import BrainDriveInstaller
from AppConfig import AppConfig
from braindrive_installer.core.port_selector import DEFAULT_PORT_PAIRS

DEFAULT_BACKEND_PORT = DEFAULT_PORT_PAIRS[0][0]
DEFAULT_FRONTEND_PORT = DEFAULT_PORT_PAIRS[0][1]


class TestBrainDriveInstaller:
    """Test suite for BrainDriveInstaller class."""
    
    def test_installer_initialization(self):
        """Test BrainDriveInstaller initialization."""
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        # Test basic properties
        assert installer.name == "BrainDrive"
        assert installer.repo_url == "https://github.com/BrainDriveAI/BrainDrive.git"
        assert installer.backend_port == DEFAULT_BACKEND_PORT
        assert installer.frontend_port == DEFAULT_FRONTEND_PORT
        assert installer.env_name == "BrainDriveDev"
        assert installer.status_updater == status_updater
        
        # Test that managers are initialized
        assert hasattr(installer, 'git_manager')
        assert hasattr(installer, 'node_manager')
        assert hasattr(installer, 'plugin_builder')
        assert hasattr(installer, 'process_manager')
        
        # Test config is set
        assert isinstance(installer.config, AppConfig)

    def test_auto_select_ports_advances_pair(self):
        """Default-managed ports should move to the next free pair."""
        installer = BrainDriveInstaller()
        installer.backend_port = DEFAULT_BACKEND_PORT
        installer.frontend_port = DEFAULT_FRONTEND_PORT
        installer.backend_host = "localhost"
        installer.frontend_host = "localhost"

        next_pair = (8505, 5573)
        with patch('installer_braindrive.select_available_port_pair', return_value=next_pair):
            changed = installer._auto_select_ports_if_default(None)

        assert changed is True
        assert installer.backend_port == next_pair[0]
        assert installer.frontend_port == next_pair[1]

    def test_auto_select_ports_ignores_custom_values(self):
        """Ports outside the managed list should never be auto-updated."""
        installer = BrainDriveInstaller()
        installer.backend_port = 9100
        installer.frontend_port = 9200
        installer.backend_host = "localhost"
        installer.frontend_host = "localhost"

        with patch('installer_braindrive.select_available_port_pair') as mock_select:
            changed = installer._auto_select_ports_if_default(None)

        assert changed is False
        mock_select.assert_not_called()
    
    def test_installer_initialization_no_updater(self):
        """Test BrainDriveInstaller initialization without status updater."""
        installer = BrainDriveInstaller()
        
        assert installer.status_updater is None
        assert installer.name == "BrainDrive"
    
    @patch('installer_braindrive.GitManager')
    @patch('installer_braindrive.NodeManager')
    @patch('installer_braindrive.PluginBuilder')
    @patch('installer_braindrive.ProcessManager')
    def test_check_requirements_all_available(self, mock_process, mock_plugin, mock_node, mock_git):
        """Test requirements check when all tools are available."""
        # Mock all managers to return success
        mock_git_instance = Mock()
        mock_git_instance.check_git_available.return_value = (True, "git version 2.34.1")
        mock_git.return_value = mock_git_instance
        
        mock_node_instance = Mock()
        mock_node_instance.check_node_available.return_value = (True, "v18.17.0")
        mock_node.return_value = mock_node_instance
        
        installer = BrainDriveInstaller()
        
        with patch.object(installer, 'check_conda_available', return_value=(True, "conda 23.7.4")):
            result = installer.check_requirements()
        
        assert result is True
    
    @patch('installer_braindrive.GitManager')
    def test_check_requirements_git_missing(self, mock_git):
        """Test requirements check when Git is missing."""
        mock_git_instance = Mock()
        mock_git_instance.check_git_available.return_value = (False, None)
        mock_git.return_value = mock_git_instance
        
        installer = BrainDriveInstaller()
        
        with patch.object(installer, 'check_conda_available', return_value=(True, "conda 23.7.4")):
            with patch.object(installer, 'node_manager') as mock_node:
                mock_node.check_node_available.return_value = (True, "v18.17.0")
                result = installer.check_requirements()
        
        assert result is False
    
    @patch('subprocess.run')
    def test_setup_environment_success(self, mock_run):
        """Test successful conda environment setup."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        result = installer.setup_environment("TestEnv")
        
        assert result is True
        
        # Verify conda commands were called
        expected_calls = [
            call(['conda', 'create', '-n', 'TestEnv', 'python=3.11', '-y'], 
                 capture_output=True, text=True, timeout=600),
            call(['conda', 'install', '-n', 'TestEnv', 'nodejs', 'git', '-y'], 
                 capture_output=True, text=True, timeout=600)
        ]
        mock_run.assert_has_calls(expected_calls, any_order=False)
        
        # Verify status updates
        status_updater.update_status.assert_called()
    
    @patch('subprocess.run')
    def test_setup_environment_failure(self, mock_run):
        """Test conda environment setup failure."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="CondaError: environment creation failed"
        )
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        result = installer.setup_environment("TestEnv")
        
        assert result is False
        status_updater.set_error.assert_called()
    
    def test_clone_repository_success(self):
        """Test successful repository cloning."""
        installer = BrainDriveInstaller()
        
        # Mock git manager
        installer.git_manager.clone_repository = Mock(return_value=True)
        
        result = installer.clone_repository()
        
        assert result is True
        installer.git_manager.clone_repository.assert_called_once_with(
            installer.repo_url,
            installer.config.repo_path,
            "main"
        )
    
    def test_clone_repository_failure(self):
        """Test repository cloning failure."""
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        # Mock git manager to fail
        installer.git_manager.clone_repository = Mock(return_value=False)
        
        result = installer.clone_repository()
        
        assert result is False
        status_updater.set_error.assert_called()
    
    def test_build_plugins_success(self):
        """Test successful plugin building."""
        installer = BrainDriveInstaller()
        
        # Mock plugin builder
        installer.plugin_builder.build_all_plugins = Mock(return_value=True)
        
        result = installer.build_plugins()
        
        assert result is True
        installer.plugin_builder.build_all_plugins.assert_called_once()
    
    def test_build_plugins_failure(self):
        """Test plugin building failure."""
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        # Mock plugin builder to fail
        installer.plugin_builder.build_all_plugins = Mock(return_value=False)
        
        result = installer.build_plugins()
        
        assert result is False
        status_updater.set_error.assert_called()
    
    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    def test_setup_backend_success(self, mock_file, mock_run):
        """Test successful backend setup."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        # Mock template reading
        template_content = "APP_NAME={APP_NAME}\nPORT={PORT}\nSECRET_KEY={SECRET_KEY}"
        mock_file.return_value.read.return_value = template_content
        
        with patch('os.path.exists', return_value=True):
            result = installer.setup_backend()
        
        assert result is True
        
        # Verify pip install was called
        mock_run.assert_called()
        
        # Verify .env file was written
        mock_file.assert_called()
        status_updater.update_status.assert_called()
    
    @patch('subprocess.run')
    def test_setup_backend_pip_failure(self, mock_run):
        """Test backend setup with pip install failure."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="ERROR: Could not install packages"
        )
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        with patch('os.path.exists', return_value=True):
            result = installer.setup_backend()
        
        assert result is False
        status_updater.set_error.assert_called()
    
    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    def test_setup_frontend_success(self, mock_file, mock_run):
        """Test successful frontend setup."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        # Mock template reading
        template_content = "VITE_API_URL=http://localhost:{BACKEND_PORT}"
        mock_file.return_value.read.return_value = template_content
        
        with patch('os.path.exists', return_value=True):
            result = installer.setup_frontend()
        
        assert result is True
        
        # Verify npm install was called
        mock_run.assert_called()
        
        # Verify .env file was written
        mock_file.assert_called()
        status_updater.update_status.assert_called()
    
    @patch('subprocess.run')
    def test_setup_frontend_npm_failure(self, mock_run):
        """Test frontend setup with npm install failure."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="npm ERR! Failed to install dependencies"
        )
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        with patch('os.path.exists', return_value=True):
            result = installer.setup_frontend()
        
        assert result is False
        status_updater.set_error.assert_called()
    
    def test_start_services_success(self):
        """Test successful service startup."""
        installer = BrainDriveInstaller()
        
        # Mock process manager
        installer.process_manager.start_process = Mock(return_value=True)
        
        result = installer.start_services()
        
        assert result is True
        
        # Verify both services were started
        expected_calls = [
            call('braindrive_backend', installer._get_backend_start_command(), 
                 cwd=installer.config.backend_path, env=None),
            call('braindrive_frontend', installer._get_frontend_start_command(), 
                 cwd=installer.config.frontend_path, env=None)
        ]
        installer.process_manager.start_process.assert_has_calls(expected_calls)
    
    def test_start_services_backend_failure(self):
        """Test service startup with backend failure."""
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        # Mock process manager to fail on backend
        def mock_start_process(name, *args, **kwargs):
            if 'backend' in name:
                return False
            return True
        
        installer.process_manager.start_process = Mock(side_effect=mock_start_process)
        
        result = installer.start_services()
        
        assert result is False
        status_updater.set_error.assert_called()
    
    def test_stop_services_success(self):
        """Test successful service shutdown."""
        installer = BrainDriveInstaller()
        
        # Mock process manager
        installer.process_manager.stop_process = Mock(return_value=True)
        installer.process_manager.is_process_running = Mock(return_value=True)
        
        result = installer.stop_services()
        
        assert result is True
        
        # Verify both services were stopped
        expected_calls = [
            call('braindrive_backend'),
            call('braindrive_frontend')
        ]
        installer.process_manager.stop_process.assert_has_calls(expected_calls)
    
    def test_stop_services_not_running(self):
        """Test service shutdown when services are not running."""
        installer = BrainDriveInstaller()
        
        # Mock process manager - services not running
        installer.process_manager.is_process_running = Mock(return_value=False)
        installer.process_manager.stop_process = Mock()
        
        result = installer.stop_services()
        
        assert result is True
        # stop_process should not be called if services aren't running
        installer.process_manager.stop_process.assert_not_called()
    
    def test_check_installed_success(self):
        """Test installation check when properly installed."""
        installer = BrainDriveInstaller()
        
        with patch('os.path.exists', return_value=True):
            with patch('os.path.isfile', return_value=True):
                result = installer.check_installed()
        
        assert result is True
    
    def test_check_installed_missing_files(self):
        """Test installation check with missing files."""
        installer = BrainDriveInstaller()
        
        with patch('os.path.exists', return_value=False):
            result = installer.check_installed()
        
        assert result is False
    
    def test_update_success(self):
        """Test successful update process."""
        installer = BrainDriveInstaller()
        
        # Mock all update steps to succeed
        installer.git_manager.pull_updates = Mock(return_value=True)
        installer.plugin_builder.build_all_plugins = Mock(return_value=True)
        
        with patch.object(installer, 'setup_backend', return_value=True):
            with patch.object(installer, 'setup_frontend', return_value=True):
                result = installer.update()
        
        assert result is True
        
        # Verify update steps were called
        installer.git_manager.pull_updates.assert_called_once()
        installer.plugin_builder.build_all_plugins.assert_called_once()
    
    def test_update_git_failure(self):
        """Test update process with Git pull failure."""
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        # Mock git pull to fail
        installer.git_manager.pull_updates = Mock(return_value=False)
        
        result = installer.update()
        
        assert result is False
        status_updater.set_error.assert_called()
    
    def test_get_backend_start_command_windows(self):
        """Test backend start command generation on Windows."""
        installer = BrainDriveInstaller()
        
        with patch('platform_utils.PlatformUtils.get_os_type', return_value='windows'):
            command = installer._get_backend_start_command()
        
        expected = ['conda', 'run', '-n', installer.env_name, 'python', '-m', 'uvicorn', 
                   'main:app', '--host', '0.0.0.0', '--port', str(installer.backend_port)]
        assert command == expected
    
    def test_get_backend_start_command_unix(self):
        """Test backend start command generation on Unix systems."""
        installer = BrainDriveInstaller()
        
        with patch('platform_utils.PlatformUtils.get_os_type', return_value='linux'):
            command = installer._get_backend_start_command()
        
        expected = ['conda', 'run', '-n', installer.env_name, 'python', '-m', 'uvicorn', 
                   'main:app', '--host', '0.0.0.0', '--port', str(installer.backend_port)]
        assert command == expected
    
    def test_get_frontend_start_command_windows(self):
        """Test frontend start command generation on Windows."""
        installer = BrainDriveInstaller()
        
        with patch('platform_utils.PlatformUtils.get_os_type', return_value='windows'):
            command = installer._get_frontend_start_command()
        
        expected = ['conda', 'run', '-n', installer.env_name, 'npm', 'run', 'dev', 
                   '--', '--host', '0.0.0.0', '--port', str(installer.frontend_port)]
        assert command == expected
    
    def test_get_frontend_start_command_unix(self):
        """Test frontend start command generation on Unix systems."""
        installer = BrainDriveInstaller()
        
        with patch('platform_utils.PlatformUtils.get_os_type', return_value='linux'):
            command = installer._get_frontend_start_command()
        
        expected = ['conda', 'run', '-n', installer.env_name, 'npm', 'run', 'dev', 
                   '--', '--host', '0.0.0.0', '--port', str(installer.frontend_port)]
        assert command == expected
    
    @patch('builtins.open', new_callable=mock_open)
    def test_create_backend_env_file(self, mock_file):
        """Test backend .env file creation."""
        installer = BrainDriveInstaller()
        
        # Mock template content
        template_content = "APP_NAME={APP_NAME}\nPORT={PORT}\nSECRET_KEY={SECRET_KEY}"
        mock_file.return_value.read.return_value = template_content
        
        with patch('os.path.exists', return_value=True):
            result = installer._create_backend_env_file()
        
        assert result is True
        
        # Verify file operations
        mock_file.assert_called()
        
        # Check that write was called with substituted content
        write_calls = [call for call in mock_file.return_value.write.call_args_list]
        assert len(write_calls) > 0
    
    @patch('builtins.open', new_callable=mock_open)
    def test_create_frontend_env_file(self, mock_file):
        """Test frontend .env file creation."""
        installer = BrainDriveInstaller()
        
        # Mock template content
        template_content = "VITE_API_URL=http://localhost:{BACKEND_PORT}"
        mock_file.return_value.read.return_value = template_content
        
        with patch('os.path.exists', return_value=True):
            result = installer._create_frontend_env_file()
        
        assert result is True
        
        # Verify file operations
        mock_file.assert_called()
        
        # Check that write was called
        write_calls = [call for call in mock_file.return_value.write.call_args_list]
        assert len(write_calls) > 0
    
    def test_generate_secret_key(self):
        """Test secret key generation."""
        installer = BrainDriveInstaller()
        
        secret_key = installer._generate_secret_key()
        
        # Verify secret key properties
        assert isinstance(secret_key, str)
        assert len(secret_key) >= 32  # Should be at least 32 characters
        
        # Generate another key to ensure they're different
        secret_key2 = installer._generate_secret_key()
        assert secret_key != secret_key2
    
    def test_validate_ports_available(self):
        """Test port availability validation."""
        installer = BrainDriveInstaller()
        
        with patch('socket.socket') as mock_socket:
            mock_socket.return_value.__enter__.return_value.bind.return_value = None
            
            result = installer._validate_ports()
        
        assert result is True
    
    def test_validate_ports_unavailable(self):
        """Test port availability validation with ports in use."""
        installer = BrainDriveInstaller()
        
        with patch('socket.socket') as mock_socket:
            mock_socket.return_value.__enter__.return_value.bind.side_effect = OSError("Port in use")
            
            result = installer._validate_ports()
        
        assert result is False
    
    def test_get_service_status_running(self):
        """Test service status check when services are running."""
        installer = BrainDriveInstaller()
        
        installer.process_manager.is_process_running = Mock(return_value=True)
        
        status = installer.get_service_status()
        
        assert status['backend_running'] is True
        assert status['frontend_running'] is True
        assert status['both_running'] is True
    
    def test_get_service_status_not_running(self):
        """Test service status check when services are not running."""
        installer = BrainDriveInstaller()
        
        installer.process_manager.is_process_running = Mock(return_value=False)
        
        status = installer.get_service_status()
        
        assert status['backend_running'] is False
        assert status['frontend_running'] is False
        assert status['both_running'] is False
    
    def test_get_service_status_partial(self):
        """Test service status check when only one service is running."""
        installer = BrainDriveInstaller()
        
        def mock_is_running(name):
            return 'backend' in name
        
        installer.process_manager.is_process_running = Mock(side_effect=mock_is_running)
        
        status = installer.get_service_status()
        
        assert status['backend_running'] is True
        assert status['frontend_running'] is False
        assert status['both_running'] is False


class TestBrainDriveInstallerIntegration:
    """Integration tests for BrainDriveInstaller."""
    
    @patch('installer_braindrive.GitManager')
    @patch('installer_braindrive.NodeManager')
    @patch('installer_braindrive.PluginBuilder')
    @patch('installer_braindrive.ProcessManager')
    @patch('subprocess.run')
    def test_full_installation_workflow(self, mock_run, mock_process, mock_plugin, mock_node, mock_git):
        """Test complete installation workflow."""
        # Mock all subprocess calls to succeed
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        # Mock all managers
        mock_git_instance = Mock()
        mock_git_instance.check_git_available.return_value = (True, "git version 2.34.1")
        mock_git_instance.clone_repository.return_value = True
        mock_git.return_value = mock_git_instance
        
        mock_node_instance = Mock()
        mock_node_instance.check_node_available.return_value = (True, "v18.17.0")
        mock_node.return_value = mock_node_instance
        
        mock_plugin_instance = Mock()
        mock_plugin_instance.build_all_plugins.return_value = True
        mock_plugin.return_value = mock_plugin_instance
        
        mock_process_instance = Mock()
        mock_process_instance.start_process.return_value = True
        mock_process.return_value = mock_process_instance
        
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        # Mock file operations
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data="template content")):
                with patch.object(installer, 'check_conda_available', return_value=(True, "conda 23.7.4")):
                    # Run full installation
                    result = installer.install()
        
        assert result is True
        
        # Verify all steps were called
        mock_git_instance.check_git_available.assert_called()
        mock_git_instance.clone_repository.assert_called()
        mock_plugin_instance.build_all_plugins.assert_called()
        
        # Verify status updates
        assert status_updater.update_status.call_count > 0
        status_updater.set_success.assert_called()
    
    @patch('installer_braindrive.GitManager')
    def test_installation_failure_rollback(self, mock_git):
        """Test installation failure and rollback."""
        # Mock git manager to fail
        mock_git_instance = Mock()
        mock_git_instance.check_git_available.return_value = (False, None)
        mock_git.return_value = mock_git_instance
        
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        with patch.object(installer, 'check_conda_available', return_value=(True, "conda 23.7.4")):
            result = installer.install()
        
        assert result is False
        status_updater.set_error.assert_called()
