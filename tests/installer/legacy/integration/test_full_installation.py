"""
Integration tests for full BrainDrive installation workflow.
Tests end-to-end installation process with real system interactions.
"""

import pytest
import os
import sys
import tempfile
import shutil
import time
import subprocess
from unittest.mock import Mock, patch
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from installer_braindrive import BrainDriveInstaller
from git_manager import GitManager
from node_manager import NodeManager
from plugin_builder import PluginBuilder
from process_manager import ProcessManager
from platform_utils import PlatformUtils


@pytest.mark.integration
class TestFullInstallation:
    """Integration tests for complete installation workflow."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self, temp_dir):
        """Set up test environment for integration tests."""
        self.test_dir = temp_dir
        self.mock_repo_path = os.path.join(self.test_dir, "BrainDrive")
        self.mock_backend_path = os.path.join(self.mock_repo_path, "backend")
        self.mock_frontend_path = os.path.join(self.mock_repo_path, "frontend")
        
        # Create mock repository structure
        os.makedirs(self.mock_backend_path, exist_ok=True)
        os.makedirs(self.mock_frontend_path, exist_ok=True)
        
        # Create mock files
        self._create_mock_files()
        
        yield
        
        # Cleanup is handled by temp_dir fixture
    
    def _create_mock_files(self):
        """Create mock files for testing."""
        # Backend files
        with open(os.path.join(self.mock_backend_path, "requirements.txt"), "w") as f:
            f.write("fastapi==0.104.1\nuvicorn==0.24.0\npydantic==2.5.0\n")
        
        with open(os.path.join(self.mock_backend_path, "main.py"), "w") as f:
            f.write("""
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "BrainDrive Backend"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
""")
        
        # Frontend files
        with open(os.path.join(self.mock_frontend_path, "package.json"), "w") as f:
            f.write("""{
  "name": "braindrive-frontend",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite --host 0.0.0.0 --port 5173",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "vite": "^5.0.0"
  }
}""")
        
        # Create plugins directory with mock plugin
        plugins_path = os.path.join(self.mock_repo_path, "plugins", "test-plugin")
        os.makedirs(plugins_path, exist_ok=True)
        
        with open(os.path.join(plugins_path, "package.json"), "w") as f:
            f.write("""{
  "name": "test-plugin",
  "version": "1.0.0",
  "scripts": {
    "build": "echo 'Building plugin'"
  }
}""")
    
    @pytest.mark.slow
    def test_requirements_check_integration(self):
        """Test requirements checking with real system."""
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        # This will check actual system requirements
        result = installer.check_requirements()
        
        # Result depends on actual system state
        # At minimum, Python should be available
        assert isinstance(result, bool)
        
        # Verify status updates were called
        status_updater.update_status.assert_called()
    
    @patch('installer_braindrive.BrainDriveInstaller.clone_repository')
    @patch('installer_braindrive.BrainDriveInstaller.setup_environment')
    def test_installation_workflow_mocked(self, mock_setup_env, mock_clone):
        """Test installation workflow with mocked external dependencies."""
        # Mock external operations to succeed
        mock_setup_env.return_value = True
        mock_clone.return_value = True
        
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        # Override paths to use test directory
        installer.config.repo_path = self.mock_repo_path
        installer.config.backend_path = self.mock_backend_path
        installer.config.frontend_path = self.mock_frontend_path
        
        # Mock plugin builder and process manager
        installer.plugin_builder.build_all_plugins = Mock(return_value=True)
        installer.process_manager.start_process = Mock(return_value=True)
        
        # Mock file operations for .env creation
        with patch('builtins.open') as mock_open:
            with patch('os.path.exists', return_value=True):
                # Mock template files
                mock_open.return_value.__enter__.return_value.read.return_value = "TEMPLATE_CONTENT"
                
                result = installer.install()
        
        assert result is True
        
        # Verify workflow steps
        mock_setup_env.assert_called_once()
        mock_clone.assert_called_once()
        installer.plugin_builder.build_all_plugins.assert_called_once()
        
        # Verify status updates
        status_updater.set_success.assert_called_once()
    
    def test_git_manager_integration(self):
        """Test Git manager with mock repository."""
        status_updater = Mock()
        git_manager = GitManager(status_updater)
        
        # Test repository status check
        status = git_manager.get_repository_status(self.mock_repo_path)
        
        assert status['exists'] is True
        assert status['is_git_repo'] is False  # No .git directory in mock
        assert status['path'] == self.mock_repo_path
    
    @patch('subprocess.run')
    def test_node_manager_integration(self, mock_run):
        """Test Node manager with mocked npm operations."""
        # Mock npm install success
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        status_updater = Mock()
        node_manager = NodeManager(status_updater)
        
        # Test npm install
        result = node_manager.install_dependencies(self.mock_frontend_path)
        
        assert result is True
        
        # Verify npm install was called
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert 'npm' in call_args[0][0]
        assert 'install' in call_args[0][0]
    
    def test_plugin_builder_integration(self):
        """Test plugin builder with mock plugins."""
        status_updater = Mock()
        plugins_path = os.path.join(self.mock_repo_path, "plugins")
        plugin_builder = PluginBuilder(plugins_path, status_updater)
        
        # Test plugin discovery
        plugins = plugin_builder.discover_plugins()
        
        assert len(plugins) >= 1  # Should find our test plugin
        assert any("test-plugin" in plugin for plugin in plugins)
    
    @patch('subprocess.Popen')
    def test_process_manager_integration(self, mock_popen):
        """Test process manager with mock processes."""
        # Mock process
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Process running
        mock_popen.return_value = mock_process
        
        status_updater = Mock()
        process_manager = ProcessManager(status_updater)
        
        # Test process start
        result = process_manager.start_process(
            "test_process",
            ["python", "-c", "import time; time.sleep(1)"],
            cwd=self.test_dir
        )
        
        assert result is True
        
        # Test process status
        is_running = process_manager.is_process_running("test_process")
        assert is_running is True
        
        # Test process stop
        stop_result = process_manager.stop_process("test_process")
        assert stop_result is True
    
    @pytest.mark.slow
    def test_service_startup_simulation(self):
        """Test service startup simulation without actual servers."""
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        # Override paths
        installer.config.backend_path = self.mock_backend_path
        installer.config.frontend_path = self.mock_frontend_path
        
        # Mock process manager to simulate successful startup
        installer.process_manager.start_process = Mock(return_value=True)
        installer.process_manager.is_process_running = Mock(return_value=True)
        
        # Test service startup
        result = installer.start_services()
        assert result is True
        
        # Test service status
        status = installer.get_service_status()
        assert status['backend_running'] is True
        assert status['frontend_running'] is True
        assert status['both_running'] is True
        
        # Test service shutdown
        installer.process_manager.stop_process = Mock(return_value=True)
        installer.process_manager.is_process_running = Mock(return_value=False)
        
        stop_result = installer.stop_services()
        assert stop_result is True
    
    def test_configuration_file_generation(self):
        """Test configuration file generation."""
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        # Override paths
        installer.config.backend_path = self.mock_backend_path
        installer.config.frontend_path = self.mock_frontend_path
        
        # Mock template files
        backend_template = """
APP_NAME={APP_NAME}
PORT={PORT}
SECRET_KEY={SECRET_KEY}
DEBUG={DEBUG}
"""
        
        frontend_template = """
VITE_API_URL=http://localhost:{BACKEND_PORT}
VITE_APP_NAME={APP_NAME}
"""
        
        # Test backend .env creation
        with patch('builtins.open') as mock_open:
            with patch('os.path.exists', return_value=True):
                mock_open.return_value.__enter__.return_value.read.return_value = backend_template
                
                result = installer._create_backend_env_file()
                assert result is True
                
                # Verify file was written
                mock_open.assert_called()
        
        # Test frontend .env creation
        with patch('builtins.open') as mock_open:
            with patch('os.path.exists', return_value=True):
                mock_open.return_value.__enter__.return_value.read.return_value = frontend_template
                
                result = installer._create_frontend_env_file()
                assert result is True
                
                # Verify file was written
                mock_open.assert_called()
    
    def test_port_validation_integration(self):
        """Test port validation with real socket operations."""
        installer = BrainDriveInstaller()
        
        # Test port validation (should work on most systems)
        result = installer._validate_ports()
        
        # Result depends on system state, but should be boolean
        assert isinstance(result, bool)
    
    @patch('subprocess.run')
    def test_update_workflow_integration(self, mock_run):
        """Test update workflow integration."""
        # Mock all subprocess calls to succeed
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        # Override paths
        installer.config.repo_path = self.mock_repo_path
        installer.config.backend_path = self.mock_backend_path
        installer.config.frontend_path = self.mock_frontend_path
        
        # Mock git operations
        installer.git_manager.pull_updates = Mock(return_value=True)
        installer.plugin_builder.build_all_plugins = Mock(return_value=True)
        
        # Mock file operations
        with patch('builtins.open') as mock_open:
            with patch('os.path.exists', return_value=True):
                mock_open.return_value.__enter__.return_value.read.return_value = "TEMPLATE"
                
                result = installer.update()
        
        assert result is True
        
        # Verify update steps
        installer.git_manager.pull_updates.assert_called_once()
        installer.plugin_builder.build_all_plugins.assert_called_once()
        
        # Verify status updates
        status_updater.set_success.assert_called_once()
    
    def test_installation_validation_integration(self):
        """Test installation validation."""
        installer = BrainDriveInstaller()
        
        # Override paths to test directory
        installer.config.repo_path = self.mock_repo_path
        installer.config.backend_path = self.mock_backend_path
        installer.config.frontend_path = self.mock_frontend_path
        
        # Test with existing files
        result = installer.check_installed()
        assert result is True  # Files exist in mock structure
        
        # Test with missing files
        installer.config.repo_path = "/nonexistent/path"
        result = installer.check_installed()
        assert result is False


@pytest.mark.integration
class TestErrorRecoveryIntegration:
    """Integration tests for error recovery scenarios."""
    
    def test_git_clone_failure_recovery(self):
        """Test recovery from Git clone failure."""
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        # Mock git manager to fail
        installer.git_manager.clone_repository = Mock(return_value=False)
        
        result = installer.install()
        
        assert result is False
        status_updater.set_error.assert_called()
    
    @patch('subprocess.run')
    def test_dependency_installation_failure_recovery(self, mock_run):
        """Test recovery from dependency installation failure."""
        # Mock pip/npm to fail
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Installation failed"
        )
        
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        # Override paths
        installer.config.backend_path = "/tmp/test_backend"
        
        with patch('os.path.exists', return_value=True):
            result = installer.setup_backend()
        
        assert result is False
        status_updater.set_error.assert_called()
    
    def test_service_startup_failure_recovery(self):
        """Test recovery from service startup failure."""
        status_updater = Mock()
        installer = BrainDriveInstaller(status_updater)
        
        # Mock process manager to fail on backend startup
        def mock_start_process(name, *args, **kwargs):
            if 'backend' in name:
                return False
            return True
        
        installer.process_manager.start_process = Mock(side_effect=mock_start_process)
        
        result = installer.start_services()
        
        assert result is False
        status_updater.set_error.assert_called()
    
    def test_port_conflict_recovery(self):
        """Test recovery from port conflicts."""
        installer = BrainDriveInstaller()
        
        # Mock socket operations to simulate port conflicts
        with patch('socket.socket') as mock_socket:
            mock_socket.return_value.__enter__.return_value.bind.side_effect = OSError("Port in use")
            
            result = installer._validate_ports()
        
        assert result is False


@pytest.mark.integration
@pytest.mark.slow
class TestRealSystemIntegration:
    """Integration tests that interact with real system components."""
    
    def test_real_platform_detection(self):
        """Test real platform detection."""
        os_type = PlatformUtils.get_os_type()
        assert os_type in ['windows', 'macos', 'linux']
        
        home_dir = PlatformUtils.get_home_directory()
        assert os.path.exists(home_dir)
        
        system_info = PlatformUtils.get_system_info()
        assert 'os_type' in system_info
        assert 'python_version' in system_info
    
    def test_real_command_availability(self):
        """Test real command availability checking."""
        # Python should always be available in test environment
        python_available = PlatformUtils.is_command_available('python')
        assert python_available is True
        
        # Test version retrieval
        python_version = PlatformUtils.get_command_version('python')
        assert python_version is not None
        assert 'Python' in python_version or 'python' in python_version.lower()
    
    def test_real_disk_space_check(self):
        """Test real disk space checking."""
        temp_dir = PlatformUtils.get_temp_directory()
        total, free = PlatformUtils.get_disk_space(temp_dir)
        
        assert total > 0
        assert free >= 0
        assert free <= total
        
        # Test formatting
        formatted_total = PlatformUtils.format_bytes(total)
        formatted_free = PlatformUtils.format_bytes(free)
        
        assert isinstance(formatted_total, str)
        assert isinstance(formatted_free, str)
        assert any(unit in formatted_total for unit in ['B', 'KB', 'MB', 'GB', 'TB'])