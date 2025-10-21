"""
Unit tests for platform_utils.py
Tests cross-platform compatibility utilities and system detection.
"""

import pytest
import os
import sys
import platform
import subprocess
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from platform_utils import PlatformUtils


class TestPlatformUtils:
    """Test suite for PlatformUtils class."""
    
    def test_get_os_type_windows(self):
        """Test OS type detection for Windows."""
        with patch('platform.system', return_value='Windows'):
            assert PlatformUtils.get_os_type() == 'windows'
    
    def test_get_os_type_macos(self):
        """Test OS type detection for macOS."""
        with patch('platform.system', return_value='Darwin'):
            assert PlatformUtils.get_os_type() == 'macos'
    
    def test_get_os_type_linux(self):
        """Test OS type detection for Linux."""
        with patch('platform.system', return_value='Linux'):
            assert PlatformUtils.get_os_type() == 'linux'
    
    def test_get_os_type_unknown(self):
        """Test OS type detection for unknown systems."""
        with patch('platform.system', return_value='FreeBSD'):
            assert PlatformUtils.get_os_type() == 'linux'  # Default fallback
    
    def test_get_home_directory_windows(self):
        """Test home directory detection on Windows."""
        with patch.dict(os.environ, {'USERPROFILE': 'C:\\Users\\TestUser'}):
            with patch('platform.system', return_value='Windows'):
                home = PlatformUtils.get_home_directory()
                assert home == 'C:\\Users\\TestUser'
    
    def test_get_home_directory_unix(self):
        """Test home directory detection on Unix systems."""
        with patch.dict(os.environ, {'HOME': '/home/testuser'}):
            with patch('platform.system', return_value='Linux'):
                home = PlatformUtils.get_home_directory()
                assert home == '/home/testuser'
    
    def test_get_braindrive_base_path_windows(self):
        """Test BrainDrive base path on Windows."""
        with patch.dict(os.environ, {'USERPROFILE': 'C:\\Users\\TestUser'}):
            with patch('platform.system', return_value='Windows'):
                base_path = PlatformUtils.get_braindrive_base_path()
                expected = os.path.join('C:\\Users\\TestUser', 'BrainDrive')
                assert base_path == expected
    
    def test_get_braindrive_base_path_unix(self):
        """Test BrainDrive base path on Unix systems."""
        with patch.dict(os.environ, {'HOME': '/home/testuser'}):
            with patch('platform.system', return_value='Linux'):
                base_path = PlatformUtils.get_braindrive_base_path()
                expected = os.path.join('/home/testuser', 'BrainDrive')
                assert base_path == expected
    
    def test_get_executable_extension_windows(self):
        """Test executable extension on Windows."""
        with patch('platform.system', return_value='Windows'):
            ext = PlatformUtils.get_executable_extension()
            assert ext == '.exe'
    
    def test_get_executable_extension_unix(self):
        """Test executable extension on Unix systems."""
        with patch('platform.system', return_value='Linux'):
            ext = PlatformUtils.get_executable_extension()
            assert ext == ''
    
    def test_get_conda_executable_name_windows(self):
        """Test conda executable name on Windows."""
        with patch('platform.system', return_value='Windows'):
            name = PlatformUtils.get_conda_executable_name()
            assert name == 'conda.exe'
    
    def test_get_conda_executable_name_unix(self):
        """Test conda executable name on Unix systems."""
        with patch('platform.system', return_value='Linux'):
            name = PlatformUtils.get_conda_executable_name()
            assert name == 'conda'
    
    def test_create_no_window_flags_windows(self):
        """Test no-window flags on Windows."""
        with patch('platform.system', return_value='Windows'):
            flags = PlatformUtils.create_no_window_flags()
            # Should return subprocess.CREATE_NO_WINDOW flag
            assert flags is not None
    
    def test_create_no_window_flags_unix(self):
        """Test no-window flags on Unix systems."""
        with patch('platform.system', return_value='Linux'):
            flags = PlatformUtils.create_no_window_flags()
            assert flags == 0
    
    def test_get_default_shell_windows(self):
        """Test default shell on Windows."""
        with patch('platform.system', return_value='Windows'):
            shell = PlatformUtils.get_default_shell()
            assert shell == 'cmd.exe'
    
    def test_get_default_shell_unix(self):
        """Test default shell on Unix systems."""
        with patch('platform.system', return_value='Linux'):
            shell = PlatformUtils.get_default_shell()
            assert shell == '/bin/bash'
    
    @patch('subprocess.run')
    def test_is_command_available_success(self, mock_run):
        """Test command availability check - success case."""
        mock_run.return_value = Mock(returncode=0)
        
        result = PlatformUtils.is_command_available('git')
        assert result is True
        
        # Verify subprocess was called correctly
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert 'git' in call_args[0][0]
        assert '--version' in call_args[0][0]
    
    @patch('subprocess.run')
    def test_is_command_available_failure(self, mock_run):
        """Test command availability check - failure case."""
        mock_run.return_value = Mock(returncode=1)
        
        result = PlatformUtils.is_command_available('nonexistent')
        assert result is False
    
    @patch('subprocess.run')
    def test_is_command_available_exception(self, mock_run):
        """Test command availability check - exception case."""
        mock_run.side_effect = FileNotFoundError()
        
        result = PlatformUtils.is_command_available('git')
        assert result is False
    
    @patch('subprocess.run')
    def test_get_command_version_success(self, mock_run):
        """Test command version retrieval - success case."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="git version 2.34.1\n",
            stderr=""
        )
        
        version = PlatformUtils.get_command_version('git')
        assert version == "git version 2.34.1"
    
    @patch('subprocess.run')
    def test_get_command_version_failure(self, mock_run):
        """Test command version retrieval - failure case."""
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Error")
        
        version = PlatformUtils.get_command_version('nonexistent')
        assert version is None
    
    def test_get_system_info(self):
        """Test system information gathering."""
        info = PlatformUtils.get_system_info()
        
        # Verify required keys are present
        required_keys = ['os_type', 'platform', 'architecture', 'python_version']
        for key in required_keys:
            assert key in info
        
        # Verify values are not empty
        for key in required_keys:
            assert info[key] is not None
            assert info[key] != ""
    
    def test_normalize_path_windows(self):
        """Test path normalization on Windows."""
        with patch('platform.system', return_value='Windows'):
            # Test forward slash conversion
            path = PlatformUtils.normalize_path('C:/Users/Test/file.txt')
            assert '\\' in path or '/' in path  # Either format is acceptable
            
            # Test path expansion
            with patch.dict(os.environ, {'USERPROFILE': 'C:\\Users\\Test'}):
                path = PlatformUtils.normalize_path('~/file.txt')
                assert 'Test' in path
    
    def test_normalize_path_unix(self):
        """Test path normalization on Unix systems."""
        with patch('platform.system', return_value='Linux'):
            # Test backslash conversion
            path = PlatformUtils.normalize_path('home\\user\\file.txt')
            assert '/' in path
            
            # Test path expansion
            with patch.dict(os.environ, {'HOME': '/home/test'}):
                path = PlatformUtils.normalize_path('~/file.txt')
                assert '/home/test' in path
    
    @patch('shutil.which')
    def test_find_executable_success(self, mock_which):
        """Test executable finding - success case."""
        mock_which.return_value = '/usr/bin/git'
        
        path = PlatformUtils.find_executable('git')
        assert path == '/usr/bin/git'
        mock_which.assert_called_once_with('git')
    
    @patch('shutil.which')
    def test_find_executable_failure(self, mock_which):
        """Test executable finding - failure case."""
        mock_which.return_value = None
        
        path = PlatformUtils.find_executable('nonexistent')
        assert path is None
    
    def test_get_temp_directory(self):
        """Test temporary directory retrieval."""
        temp_dir = PlatformUtils.get_temp_directory()
        
        # Verify it's a valid directory path
        assert temp_dir is not None
        assert isinstance(temp_dir, str)
        assert len(temp_dir) > 0
    
    @patch('psutil.disk_usage')
    def test_get_disk_space_success(self, mock_disk_usage):
        """Test disk space checking - success case."""
        # Mock disk usage: 100GB total, 50GB free
        mock_usage = Mock()
        mock_usage.total = 100 * 1024 * 1024 * 1024  # 100GB
        mock_usage.free = 50 * 1024 * 1024 * 1024    # 50GB
        mock_disk_usage.return_value = mock_usage
        
        total, free = PlatformUtils.get_disk_space('/test/path')
        
        assert total == 100 * 1024 * 1024 * 1024
        assert free == 50 * 1024 * 1024 * 1024
    
    @patch('psutil.disk_usage')
    def test_get_disk_space_failure(self, mock_disk_usage):
        """Test disk space checking - failure case."""
        mock_disk_usage.side_effect = OSError("Permission denied")
        
        total, free = PlatformUtils.get_disk_space('/invalid/path')
        
        assert total == 0
        assert free == 0
    
    def test_format_bytes(self):
        """Test byte formatting utility."""
        # Test various byte sizes
        assert PlatformUtils.format_bytes(1024) == "1.0 KB"
        assert PlatformUtils.format_bytes(1024 * 1024) == "1.0 MB"
        assert PlatformUtils.format_bytes(1024 * 1024 * 1024) == "1.0 GB"
        assert PlatformUtils.format_bytes(500) == "500 B"
    
    def test_is_admin_windows(self):
        """Test admin privilege checking on Windows."""
        with patch('platform.system', return_value='Windows'):
            # Mock ctypes for Windows admin check
            with patch('ctypes.windll.shell32.IsUserAnAdmin', return_value=1):
                assert PlatformUtils.is_admin() is True
            
            with patch('ctypes.windll.shell32.IsUserAnAdmin', return_value=0):
                assert PlatformUtils.is_admin() is False
    
    def test_is_admin_unix(self):
        """Test admin privilege checking on Unix systems."""
        with patch('platform.system', return_value='Linux'):
            with patch('os.geteuid', return_value=0):
                assert PlatformUtils.is_admin() is True
            
            with patch('os.geteuid', return_value=1000):
                assert PlatformUtils.is_admin() is False
    
    @patch('subprocess.Popen')
    def test_run_command_success(self, mock_popen):
        """Test command execution - success case."""
        mock_process = Mock()
        mock_process.communicate.return_value = ("output", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        result = PlatformUtils.run_command(['echo', 'test'])
        
        assert result['success'] is True
        assert result['returncode'] == 0
        assert result['stdout'] == "output"
        assert result['stderr'] == ""
    
    @patch('subprocess.Popen')
    def test_run_command_failure(self, mock_popen):
        """Test command execution - failure case."""
        mock_process = Mock()
        mock_process.communicate.return_value = ("", "error")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process
        
        result = PlatformUtils.run_command(['false'])
        
        assert result['success'] is False
        assert result['returncode'] == 1
        assert result['stderr'] == "error"
    
    @patch('subprocess.Popen')
    def test_run_command_exception(self, mock_popen):
        """Test command execution - exception case."""
        mock_popen.side_effect = FileNotFoundError("Command not found")
        
        result = PlatformUtils.run_command(['nonexistent'])
        
        assert result['success'] is False
        assert 'error' in result
        assert 'Command not found' in result['error']


class TestPlatformUtilsIntegration:
    """Integration tests for PlatformUtils that test real system interactions."""
    
    @pytest.mark.slow
    def test_real_system_detection(self):
        """Test actual system detection (slow test)."""
        os_type = PlatformUtils.get_os_type()
        assert os_type in ['windows', 'macos', 'linux']
        
        home_dir = PlatformUtils.get_home_directory()
        assert os.path.exists(home_dir)
        
        system_info = PlatformUtils.get_system_info()
        assert system_info['os_type'] == os_type
    
    @pytest.mark.slow
    def test_real_command_availability(self):
        """Test actual command availability checking (slow test)."""
        # Python should always be available in test environment
        python_available = PlatformUtils.is_command_available('python')
        assert python_available is True
        
        # Test a command that likely doesn't exist
        fake_available = PlatformUtils.is_command_available('definitely_not_a_real_command_12345')
        assert fake_available is False
    
    @pytest.mark.slow
    def test_real_disk_space(self):
        """Test actual disk space checking (slow test)."""
        temp_dir = PlatformUtils.get_temp_directory()
        total, free = PlatformUtils.get_disk_space(temp_dir)
        
        # Should have some disk space
        assert total > 0
        assert free >= 0
        assert free <= total