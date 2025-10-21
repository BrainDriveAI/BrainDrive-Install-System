"""
Cross-platform compatibility tests for BrainDrive Installer.
Tests functionality across Windows, macOS, and Linux platforms.
"""

import pytest
import os
import sys
import platform
import tempfile
import subprocess
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from platform_utils import PlatformUtils
from installer_braindrive import BrainDriveInstaller
from git_manager import GitManager
from node_manager import NodeManager
from process_manager import ProcessManager


@pytest.mark.platform
class TestCrossPlatformPaths:
    """Test cross-platform path handling."""
    
    def test_path_normalization_windows(self):
        """Test path normalization on Windows."""
        with patch('platform.system', return_value='Windows'):
            # Test forward slash conversion
            path = PlatformUtils.normalize_path('C:/Users/Test/file.txt')
            assert isinstance(path, str)
            
            # Test tilde expansion
            with patch.dict(os.environ, {'USERPROFILE': 'C:\\Users\\Test'}):
                expanded = PlatformUtils.normalize_path('~/file.txt')
                assert 'Test' in expanded
    
    def test_path_normalization_macos(self):
        """Test path normalization on macOS."""
        with patch('platform.system', return_value='Darwin'):
            # Test backslash conversion
            path = PlatformUtils.normalize_path('home\\user\\file.txt')
            assert '/' in path
            
            # Test tilde expansion
            with patch.dict(os.environ, {'HOME': '/Users/test'}):
                expanded = PlatformUtils.normalize_path('~/file.txt')
                assert '/Users/test' in expanded
    
    def test_path_normalization_linux(self):
        """Test path normalization on Linux."""
        with patch('platform.system', return_value='Linux'):
            # Test backslash conversion
            path = PlatformUtils.normalize_path('home\\user\\file.txt')
            assert '/' in path
            
            # Test tilde expansion
            with patch.dict(os.environ, {'HOME': '/home/test'}):
                expanded = PlatformUtils.normalize_path('~/file.txt')
                assert '/home/test' in expanded
    
    def test_braindrive_base_path_all_platforms(self):
        """Test BrainDrive base path on all platforms."""
        platforms = [
            ('Windows', {'USERPROFILE': 'C:\\Users\\Test'}),
            ('Darwin', {'HOME': '/Users/test'}),
            ('Linux', {'HOME': '/home/test'})
        ]
        
        for platform_name, env_vars in platforms:
            with patch('platform.system', return_value=platform_name):
                with patch.dict(os.environ, env_vars):
                    base_path = PlatformUtils.get_braindrive_base_path()
                    
                    assert isinstance(base_path, str)
                    assert len(base_path) > 0
                    assert 'BrainDrive' in base_path
    
    def test_executable_extensions_all_platforms(self):
        """Test executable extensions on all platforms."""
        test_cases = [
            ('Windows', '.exe'),
            ('Darwin', ''),
            ('Linux', '')
        ]
        
        for platform_name, expected_ext in test_cases:
            with patch('platform.system', return_value=platform_name):
                ext = PlatformUtils.get_executable_extension()
                assert ext == expected_ext
    
    def test_conda_executable_names_all_platforms(self):
        """Test conda executable names on all platforms."""
        test_cases = [
            ('Windows', 'conda.exe'),
            ('Darwin', 'conda'),
            ('Linux', 'conda')
        ]
        
        for platform_name, expected_name in test_cases:
            with patch('platform.system', return_value=platform_name):
                name = PlatformUtils.get_conda_executable_name()
                assert name == expected_name
    
    def test_default_shells_all_platforms(self):
        """Test default shells on all platforms."""
        test_cases = [
            ('Windows', 'cmd.exe'),
            ('Darwin', '/bin/bash'),
            ('Linux', '/bin/bash')
        ]
        
        for platform_name, expected_shell in test_cases:
            with patch('platform.system', return_value=platform_name):
                shell = PlatformUtils.get_default_shell()
                assert shell == expected_shell


@pytest.mark.platform
class TestCrossPlatformCommands:
    """Test cross-platform command execution."""
    
    @patch('subprocess.run')
    def test_git_commands_all_platforms(self, mock_run):
        """Test Git commands on all platforms."""
        mock_run.return_value = Mock(returncode=0, stdout="git version 2.34.1", stderr="")
        
        platforms = ['Windows', 'Darwin', 'Linux']
        
        for platform_name in platforms:
            with patch('platform.system', return_value=platform_name):
                git_manager = GitManager()
                is_available, version = git_manager.check_git_available()
                
                assert is_available is True
                assert version == "git version 2.34.1"
                
                # Verify git command was called
                mock_run.assert_called_with(
                    ['git', '--version'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
        
        # Should have been called once per platform
        assert mock_run.call_count == len(platforms)
    
    @patch('subprocess.run')
    def test_node_commands_all_platforms(self, mock_run):
        """Test Node.js commands on all platforms."""
        mock_run.return_value = Mock(returncode=0, stdout="v18.17.0", stderr="")
        
        platforms = ['Windows', 'Darwin', 'Linux']
        
        for platform_name in platforms:
            with patch('platform.system', return_value=platform_name):
                node_manager = NodeManager()
                is_available, version = node_manager.check_node_available()
                
                assert is_available is True
                assert version == "v18.17.0"
    
    @patch('subprocess.run')
    def test_conda_commands_all_platforms(self, mock_run):
        """Test Conda commands on all platforms."""
        mock_run.return_value = Mock(returncode=0, stdout="conda 23.7.4", stderr="")
        
        platforms = ['Windows', 'Darwin', 'Linux']
        
        for platform_name in platforms:
            with patch('platform.system', return_value=platform_name):
                installer = BrainDriveInstaller()
                is_available, version = installer.check_conda_available()
                
                assert is_available is True
                assert version == "conda 23.7.4"


@pytest.mark.platform
class TestCrossPlatformProcessManagement:
    """Test cross-platform process management."""
    
    @patch('subprocess.Popen')
    def test_process_creation_all_platforms(self, mock_popen):
        """Test process creation on all platforms."""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        platforms = ['Windows', 'Darwin', 'Linux']
        
        for platform_name in platforms:
            with patch('platform.system', return_value=platform_name):
                process_manager = ProcessManager()
                
                result = process_manager.start_process(
                    "test_process",
                    ["python", "-c", "print('test')"]
                )
                
                assert result is True
                
                # Verify process was started
                mock_popen.assert_called()
                
                # Check process status
                is_running = process_manager.is_process_running("test_process")
                assert is_running is True
    
    def test_no_window_flags_all_platforms(self):
        """Test no-window flags on all platforms."""
        test_cases = [
            ('Windows', lambda flags: flags is not None),
            ('Darwin', lambda flags: flags == 0),
            ('Linux', lambda flags: flags == 0)
        ]
        
        for platform_name, validator in test_cases:
            with patch('platform.system', return_value=platform_name):
                flags = PlatformUtils.create_no_window_flags()
                assert validator(flags), f"Invalid flags for {platform_name}: {flags}"


@pytest.mark.platform
class TestCrossPlatformFileOperations:
    """Test cross-platform file operations."""
    
    def test_temp_directory_all_platforms(self):
        """Test temporary directory access on all platforms."""
        platforms = ['Windows', 'Darwin', 'Linux']
        
        for platform_name in platforms:
            with patch('platform.system', return_value=platform_name):
                temp_dir = PlatformUtils.get_temp_directory()
                
                assert isinstance(temp_dir, str)
                assert len(temp_dir) > 0
    
    @patch('psutil.disk_usage')
    def test_disk_space_check_all_platforms(self, mock_disk_usage):
        """Test disk space checking on all platforms."""
        mock_usage = Mock()
        mock_usage.total = 100 * 1024 * 1024 * 1024  # 100GB
        mock_usage.free = 50 * 1024 * 1024 * 1024    # 50GB
        mock_disk_usage.return_value = mock_usage
        
        platforms = ['Windows', 'Darwin', 'Linux']
        test_paths = ['C:\\', '/Users', '/home']
        
        for platform_name, test_path in zip(platforms, test_paths):
            with patch('platform.system', return_value=platform_name):
                total, free = PlatformUtils.get_disk_space(test_path)
                
                assert total == 100 * 1024 * 1024 * 1024
                assert free == 50 * 1024 * 1024 * 1024
    
    def test_file_permissions_all_platforms(self, temp_dir):
        """Test file permission handling on all platforms."""
        test_file = os.path.join(temp_dir, "test_file.txt")
        
        # Create test file
        with open(test_file, "w") as f:
            f.write("test content")
        
        platforms = ['Windows', 'Darwin', 'Linux']
        
        for platform_name in platforms:
            with patch('platform.system', return_value=platform_name):
                # Test file existence
                assert os.path.exists(test_file)
                
                # Test file reading
                with open(test_file, "r") as f:
                    content = f.read()
                    assert content == "test content"


@pytest.mark.platform
class TestCrossPlatformInstallation:
    """Test cross-platform installation workflow."""
    
    @patch('subprocess.run')
    def test_environment_setup_all_platforms(self, mock_run):
        """Test environment setup on all platforms."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        platforms = ['Windows', 'Darwin', 'Linux']
        
        for platform_name in platforms:
            with patch('platform.system', return_value=platform_name):
                installer = BrainDriveInstaller()
                
                result = installer.setup_environment("TestEnv")
                
                assert result is True
                
                # Verify conda commands were called
                assert mock_run.call_count >= 2  # At least create and install commands
        
        mock_run.reset_mock()
    
    @patch('subprocess.run')
    def test_backend_setup_all_platforms(self, mock_run):
        """Test backend setup on all platforms."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        platforms = ['Windows', 'Darwin', 'Linux']
        
        for platform_name in platforms:
            with patch('platform.system', return_value=platform_name):
                installer = BrainDriveInstaller()
                
                with patch('os.path.exists', return_value=True):
                    with patch('builtins.open') as mock_open:
                        mock_open.return_value.__enter__.return_value.read.return_value = "template"
                        
                        result = installer.setup_backend()
                
                assert result is True
                
                # Verify pip install was called
                mock_run.assert_called()
        
        mock_run.reset_mock()
    
    @patch('subprocess.run')
    def test_frontend_setup_all_platforms(self, mock_run):
        """Test frontend setup on all platforms."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        platforms = ['Windows', 'Darwin', 'Linux']
        
        for platform_name in platforms:
            with patch('platform.system', return_value=platform_name):
                installer = BrainDriveInstaller()
                
                with patch('os.path.exists', return_value=True):
                    with patch('builtins.open') as mock_open:
                        mock_open.return_value.__enter__.return_value.read.return_value = "template"
                        
                        result = installer.setup_frontend()
                
                assert result is True
                
                # Verify npm install was called
                mock_run.assert_called()
        
        mock_run.reset_mock()
    
    def test_service_commands_all_platforms(self):
        """Test service start commands on all platforms."""
        platforms = ['Windows', 'Darwin', 'Linux']
        
        for platform_name in platforms:
            with patch('platform.system', return_value=platform_name):
                installer = BrainDriveInstaller()
                
                backend_cmd = installer._get_backend_start_command()
                frontend_cmd = installer._get_frontend_start_command()
                
                # Commands should be lists
                assert isinstance(backend_cmd, list)
                assert isinstance(frontend_cmd, list)
                
                # Should contain expected components
                assert 'conda' in backend_cmd
                assert 'uvicorn' in backend_cmd
                assert 'conda' in frontend_cmd
                assert 'npm' in frontend_cmd


@pytest.mark.platform
class TestCrossPlatformSystemInfo:
    """Test cross-platform system information gathering."""
    
    def test_os_detection_all_platforms(self):
        """Test OS detection on all platforms."""
        test_cases = [
            ('Windows', 'windows'),
            ('Darwin', 'macos'),
            ('Linux', 'linux')
        ]
        
        for system_name, expected_os in test_cases:
            with patch('platform.system', return_value=system_name):
                detected_os = PlatformUtils.get_os_type()
                assert detected_os == expected_os
    
    def test_system_info_all_platforms(self):
        """Test system information gathering on all platforms."""
        platforms = ['Windows', 'Darwin', 'Linux']
        
        for platform_name in platforms:
            with patch('platform.system', return_value=platform_name):
                info = PlatformUtils.get_system_info()
                
                # Verify required fields
                required_fields = ['os_type', 'platform', 'architecture', 'python_version']
                for field in required_fields:
                    assert field in info
                    assert info[field] is not None
                    assert info[field] != ""
    
    def test_admin_privilege_check_all_platforms(self):
        """Test admin privilege checking on all platforms."""
        # Windows test
        with patch('platform.system', return_value='Windows'):
            with patch('ctypes.windll.shell32.IsUserAnAdmin', return_value=1):
                assert PlatformUtils.is_admin() is True
            
            with patch('ctypes.windll.shell32.IsUserAnAdmin', return_value=0):
                assert PlatformUtils.is_admin() is False
        
        # Unix systems test
        for platform_name in ['Darwin', 'Linux']:
            with patch('platform.system', return_value=platform_name):
                with patch('os.geteuid', return_value=0):
                    assert PlatformUtils.is_admin() is True
                
                with patch('os.geteuid', return_value=1000):
                    assert PlatformUtils.is_admin() is False


@pytest.mark.platform
class TestCrossPlatformErrorHandling:
    """Test cross-platform error handling."""
    
    @patch('subprocess.run')
    def test_command_failure_handling_all_platforms(self, mock_run):
        """Test command failure handling on all platforms."""
        # Mock command failure
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Command failed"
        )
        
        platforms = ['Windows', 'Darwin', 'Linux']
        
        for platform_name in platforms:
            with patch('platform.system', return_value=platform_name):
                git_manager = GitManager()
                is_available, version = git_manager.check_git_available()
                
                assert is_available is False
                assert version is None
    
    @patch('subprocess.run')
    def test_timeout_handling_all_platforms(self, mock_run):
        """Test timeout handling on all platforms."""
        # Mock timeout
        mock_run.side_effect = subprocess.TimeoutExpired(['git', 'clone'], 300)
        
        platforms = ['Windows', 'Darwin', 'Linux']
        
        for platform_name in platforms:
            with patch('platform.system', return_value=platform_name):
                git_manager = GitManager()
                result = git_manager.clone_repository(
                    "https://github.com/test/repo.git",
                    "/tmp/test_repo"
                )
                
                assert result is False
    
    def test_permission_error_handling_all_platforms(self):
        """Test permission error handling on all platforms."""
        platforms = ['Windows', 'Darwin', 'Linux']
        
        for platform_name in platforms:
            with patch('platform.system', return_value=platform_name):
                with patch('psutil.disk_usage', side_effect=PermissionError("Access denied")):
                    total, free = PlatformUtils.get_disk_space("/restricted/path")
                    
                    assert total == 0
                    assert free == 0


@pytest.mark.platform
@pytest.mark.slow
class TestRealCrossPlatformCompatibility:
    """Real cross-platform compatibility tests (slow)."""
    
    def test_current_platform_detection(self):
        """Test detection of current platform."""
        current_os = PlatformUtils.get_os_type()
        system_name = platform.system()
        
        # Verify mapping is correct
        expected_mapping = {
            'Windows': 'windows',
            'Darwin': 'macos',
            'Linux': 'linux'
        }
        
        if system_name in expected_mapping:
            assert current_os == expected_mapping[system_name]
        else:
            # Unknown system should default to linux
            assert current_os == 'linux'
    
    def test_real_home_directory(self):
        """Test real home directory detection."""
        home_dir = PlatformUtils.get_home_directory()
        
        # Home directory should exist
        assert os.path.exists(home_dir)
        assert os.path.isdir(home_dir)
        
        # Should match expected environment variable
        current_os = PlatformUtils.get_os_type()
        if current_os == 'windows':
            expected = os.environ.get('USERPROFILE')
        else:
            expected = os.environ.get('HOME')
        
        if expected:
            assert home_dir == expected
    
    def test_real_temp_directory(self):
        """Test real temporary directory access."""
        temp_dir = PlatformUtils.get_temp_directory()
        
        # Temp directory should exist and be writable
        assert os.path.exists(temp_dir)
        assert os.path.isdir(temp_dir)
        
        # Test write access
        test_file = os.path.join(temp_dir, "test_write_access.txt")
        try:
            with open(test_file, "w") as f:
                f.write("test")
            
            assert os.path.exists(test_file)
            
            # Cleanup
            os.remove(test_file)
        except (PermissionError, OSError):
            pytest.skip("No write access to temp directory")
    
    def test_real_executable_finding(self):
        """Test real executable finding."""
        # Python should be findable
        python_path = PlatformUtils.find_executable('python')
        
        if python_path:
            assert os.path.exists(python_path)
            assert os.path.isfile(python_path)
        else:
            # Try python3 on Unix systems
            python3_path = PlatformUtils.find_executable('python3')
            if python3_path:
                assert os.path.exists(python3_path)
                assert os.path.isfile(python3_path)


def generate_platform_compatibility_report():
    """Generate cross-platform compatibility report."""
    current_platform = platform.system()
    current_os = PlatformUtils.get_os_type()
    
    report = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'current_platform': {
            'system': current_platform,
            'os_type': current_os,
            'architecture': platform.architecture(),
            'python_version': sys.version,
            'home_directory': PlatformUtils.get_home_directory(),
            'temp_directory': PlatformUtils.get_temp_directory()
        },
        'compatibility_matrix': {
            'windows': {
                'executable_extension': '.exe',
                'conda_executable': 'conda.exe',
                'default_shell': 'cmd.exe',
                'path_separator': '\\'
            },
            'macos': {
                'executable_extension': '',
                'conda_executable': 'conda',
                'default_shell': '/bin/bash',
                'path_separator': '/'
            },
            'linux': {
                'executable_extension': '',
                'conda_executable': 'conda',
                'default_shell': '/bin/bash',
                'path_separator': '/'
            }
        },
        'tested_features': [
            'Path normalization',
            'Command execution',
            'Process management',
            'File operations',
            'System information',
            'Error handling'
        ]
    }
    
    return report


if __name__ == "__main__":
    # Run platform compatibility tests
    pytest.main([__file__, "-v", "--tb=short", "-m", "platform"])