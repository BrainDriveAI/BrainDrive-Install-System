#!/usr/bin/env python3
"""
Phase 3 Testing Suite - BrainDrive Installer Implementation
Tests for installer_braindrive.py, card_braindrive.py, and related components.
"""

import os
import sys
import unittest
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
import threading
import time

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from installer_braindrive import BrainDriveInstaller
from card_braindrive import BrainDrive
from AppConfig import AppConfig
from platform_utils import PlatformUtils

class TestBrainDriveInstaller(unittest.TestCase):
    """Test suite for BrainDriveInstaller class."""
    
    def setUp(self):
        """Set up test environment."""
        self.mock_status_updater = Mock()
        self.installer = BrainDriveInstaller(self.mock_status_updater)
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_installer_initialization(self):
        """Test BrainDriveInstaller initialization."""
        self.assertEqual(self.installer.name, "BrainDrive")
        self.assertEqual(self.installer.repo_url, "https://github.com/BrainDriveAI/BrainDrive.git")
        self.assertEqual(self.installer.backend_port, 8005)
        self.assertEqual(self.installer.frontend_port, 5173)
        self.assertEqual(self.installer.env_name, "BrainDriveDev")
        
        # Check that managers are initialized
        self.assertIsNotNone(self.installer.git_manager)
        self.assertIsNotNone(self.installer.node_manager)
        self.assertIsNotNone(self.installer.plugin_builder)
        self.assertIsNotNone(self.installer.process_manager)
    
    def test_check_requirements_missing_git(self):
        """Test requirements checking when Git is missing."""
        with patch.object(self.installer, 'check_git_available', return_value=False):
            with patch.object(self.installer, 'check_node_available', return_value=True):
                with patch.object(self.installer, 'check_conda_available', return_value=True):
                    with patch.object(self.installer, 'check_disk_space', return_value=True):
                        result = self.installer.check_requirements()
                        self.assertFalse(result)
    
    def test_check_requirements_missing_node(self):
        """Test requirements checking when Node.js is missing."""
        with patch.object(self.installer, 'check_git_available', return_value=True):
            with patch.object(self.installer, 'check_node_available', return_value=False):
                with patch.object(self.installer, 'check_conda_available', return_value=True):
                    with patch.object(self.installer, 'check_disk_space', return_value=True):
                        result = self.installer.check_requirements()
                        self.assertFalse(result)
    
    def test_check_requirements_missing_conda(self):
        """Test requirements checking when Conda is missing."""
        with patch.object(self.installer, 'check_git_available', return_value=True):
            with patch.object(self.installer, 'check_node_available', return_value=True):
                with patch.object(self.installer, 'check_conda_available', return_value=False):
                    with patch.object(self.installer, 'check_disk_space', return_value=True):
                        result = self.installer.check_requirements()
                        self.assertFalse(result)
    
    def test_check_requirements_insufficient_disk_space(self):
        """Test requirements checking with insufficient disk space."""
        with patch.object(self.installer, 'check_git_available', return_value=True):
            with patch.object(self.installer, 'check_node_available', return_value=True):
                with patch.object(self.installer, 'check_conda_available', return_value=True):
                    with patch.object(self.installer, 'check_disk_space', return_value=False):
                        result = self.installer.check_requirements()
                        self.assertFalse(result)
    
    def test_check_requirements_all_satisfied(self):
        """Test requirements checking when all requirements are satisfied."""
        with patch.object(self.installer, 'check_git_available', return_value=True):
            with patch.object(self.installer, 'check_node_available', return_value=True):
                with patch.object(self.installer, 'check_conda_available', return_value=True):
                    with patch.object(self.installer, 'check_disk_space', return_value=True):
                        result = self.installer.check_requirements()
                        self.assertTrue(result)
    
    def test_check_installed_no_repo(self):
        """Test installation check when repository doesn't exist."""
        with patch.object(os.path, 'exists', return_value=False):
            result = self.installer.check_installed()
            self.assertFalse(result)
    
    def test_check_installed_invalid_repo(self):
        """Test installation check when repository is invalid."""
        with patch.object(os.path, 'exists', return_value=True):
            with patch.object(self.installer.git_manager, 'get_repository_status', return_value=False):
                result = self.installer.check_installed()
                self.assertFalse(result)
    
    def test_check_installed_missing_backend_files(self):
        """Test installation check when backend files are missing."""
        with patch.object(os.path, 'exists') as mock_exists:
            # Repository exists, but backend files don't
            mock_exists.side_effect = lambda path: 'BrainDrive' in path and 'backend' not in path
            with patch.object(self.installer.git_manager, 'get_repository_status', return_value=True):
                result = self.installer.check_installed()
                self.assertFalse(result)
    
    @patch('subprocess.run')
    def test_setup_environment_success(self, mock_run):
        """Test successful conda environment setup."""
        # Mock conda env list (environment doesn't exist) and create success
        mock_run.side_effect = [
            Mock(stdout="base\nother_env", returncode=0),  # env list
            Mock(stdout="", returncode=0)  # create success
        ]
        
        result = self.installer.setup_environment("test_env")
        self.assertTrue(result)
        
        # Verify conda commands were called
        self.assertEqual(mock_run.call_count, 2)  # env list + create
    
    @patch('subprocess.run')
    def test_setup_environment_already_exists(self, mock_run):
        """Test environment setup when environment already exists."""
        # Mock conda env list (environment exists)
        mock_run.return_value = Mock(stdout="base\ntest_env\nother_env", returncode=0)
        
        result = self.installer.setup_environment("test_env")
        self.assertTrue(result)
        
        # Verify only env list was called
        self.assertEqual(mock_run.call_count, 1)
    
    @patch('subprocess.run')
    def test_setup_environment_failure(self, mock_run):
        """Test environment setup failure."""
        # Mock conda env list (environment doesn't exist)
        mock_run.side_effect = [
            Mock(stdout="base\nother_env", returncode=0),  # env list
            Mock(stderr="Error creating environment", returncode=1)  # create fails
        ]
        
        result = self.installer.setup_environment("test_env")
        self.assertFalse(result)
    
    def test_clone_repository_success(self):
        """Test successful repository cloning."""
        with patch.object(self.installer.git_manager, 'clone_repository', return_value=True):
            with patch.object(self.installer, 'create_directory_safely'):
                result = self.installer.clone_repository()
                self.assertTrue(result)
    
    def test_clone_repository_failure(self):
        """Test repository cloning failure."""
        with patch.object(self.installer.git_manager, 'clone_repository', return_value=False):
            with patch.object(self.installer, 'create_directory_safely'):
                result = self.installer.clone_repository()
                self.assertFalse(result)
    
    def test_build_plugins_no_directory(self):
        """Test plugin building when plugins directory doesn't exist."""
        with patch.object(os.path, 'exists', return_value=False):
            result = self.installer.build_plugins()
            self.assertTrue(result)  # Should succeed with warning
    
    def test_build_plugins_success(self):
        """Test successful plugin building."""
        with patch.object(os.path, 'exists', return_value=True):
            with patch.object(self.installer.plugin_builder, 'build_all_plugins', return_value=True):
                result = self.installer.build_plugins()
                self.assertTrue(result)
    
    def test_build_plugins_failure(self):
        """Test plugin building failure."""
        with patch.object(os.path, 'exists', return_value=True):
            with patch.object(self.installer.plugin_builder, 'build_all_plugins', return_value=False):
                result = self.installer.build_plugins()
                self.assertFalse(result)
    
    def test_create_backend_env_file(self):
        """Test backend .env file creation."""
        test_file = os.path.join(self.test_dir, "backend.env")
        result = self.installer._create_backend_env_file(test_file)
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(test_file))
        
        # Check file contents
        with open(test_file, 'r') as f:
            content = f.read()
            self.assertIn('APP_NAME="BrainDrive"', content)
            self.assertIn(f'PORT={self.installer.backend_port}', content)
            self.assertIn('SECRET_KEY=', content)
    
    def test_create_frontend_env_file(self):
        """Test frontend .env file creation."""
        test_file = os.path.join(self.test_dir, "frontend.env")
        result = self.installer._create_frontend_env_file(test_file)
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(test_file))
        
        # Check file contents
        with open(test_file, 'r') as f:
            content = f.read()
            self.assertIn(f'VITE_API_BASE_URL=http://localhost:{self.installer.backend_port}', content)
            self.assertIn(f'VITE_DEV_SERVER_PORT={self.installer.frontend_port}', content)
            self.assertIn('VITE_APP_NAME="BrainDrive"', content)
    
    def test_get_service_status(self):
        """Test service status retrieval."""
        with patch.object(self.installer.process_manager, 'is_process_running') as mock_running:
            with patch.object(self.installer, 'check_installed', return_value=True):
                mock_running.side_effect = lambda name: name == "braindrive_backend"
                
                status = self.installer.get_service_status()
                
                self.assertTrue(status['installed'])
                self.assertTrue(status['backend_running'])
                self.assertFalse(status['frontend_running'])
                self.assertEqual(status['backend_url'], f"http://{self.installer.backend_host}:{self.installer.backend_port}")
                self.assertEqual(status['frontend_url'], f"http://{self.installer.frontend_host}:{self.installer.frontend_port}")


class TestBrainDriveCard(unittest.TestCase):
    """Test suite for BrainDrive UI card class."""
    
    def setUp(self):
        """Set up test environment."""
        self.card = BrainDrive()
        self.mock_status_updater = Mock()
    
    def test_card_initialization(self):
        """Test BrainDrive card initialization."""
        self.assertEqual(self.card.name, "BrainDrive")
        self.assertIn("Advanced AI platform", self.card.description)
        self.assertEqual(self.card.size, "8.5")
        self.assertEqual(self.card.backend_port, 8005)
        self.assertEqual(self.card.frontend_port, 5173)
        self.assertFalse(self.card.backend_running)
        self.assertFalse(self.card.frontend_running)
    
    def test_get_status(self):
        """Test status retrieval from card."""
        with patch('card_braindrive.BrainDriveInstaller') as mock_installer_class:
            mock_installer = Mock()
            mock_installer_class.return_value = mock_installer
            mock_installer.get_service_status.return_value = {
                'installed': True,
                'backend_running': True,
                'frontend_running': False,
                'backend_url': 'http://localhost:8005',
                'frontend_url': 'http://localhost:5173'
            }
            
            status = self.card.get_status()
            
            self.assertTrue(status['installed'])
            self.assertTrue(status['backend_running'])
            self.assertFalse(status['frontend_running'])
    
    def test_check_port_available_free_port(self):
        """Test port availability check for free port."""
        # Use a high port number that's likely to be free
        result = self.card._check_port_available(65432)
        self.assertTrue(result)
    
    def test_check_port_available_used_port(self):
        """Test port availability check for used port."""
        import socket
        # Create a socket to occupy a port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('localhost', 0))  # Bind to any available port
            port = sock.getsockname()[1]
            
            # Now test that port
            result = self.card._check_port_available(port)
            self.assertFalse(result)
        finally:
            sock.close()


class TestConfigurationTemplates(unittest.TestCase):
    """Test suite for configuration templates."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_backend_template_exists(self):
        """Test that backend template file exists."""
        template_path = os.path.join("templates", "backend_env_template.txt")
        self.assertTrue(os.path.exists(template_path))
    
    def test_frontend_template_exists(self):
        """Test that frontend template file exists."""
        template_path = os.path.join("templates", "frontend_env_template.txt")
        self.assertTrue(os.path.exists(template_path))
    
    def test_backend_template_content(self):
        """Test backend template content."""
        template_path = os.path.join("templates", "backend_env_template.txt")
        with open(template_path, 'r') as f:
            content = f.read()
            
        self.assertIn('APP_NAME="BrainDrive"', content)
        self.assertIn('PORT={BACKEND_PORT}', content)
        self.assertIn('SECRET_KEY="{SECRET_KEY}"', content)
        self.assertIn('CORS_ORIGINS=', content)
    
    def test_frontend_template_content(self):
        """Test frontend template content."""
        template_path = os.path.join("templates", "frontend_env_template.txt")
        with open(template_path, 'r') as f:
            content = f.read()
            
        self.assertIn('VITE_API_BASE_URL=http://localhost:{BACKEND_PORT}', content)
        self.assertIn('VITE_DEV_SERVER_PORT={FRONTEND_PORT}', content)
        self.assertIn('VITE_APP_NAME="BrainDrive"', content)


class TestMainInterfaceIntegration(unittest.TestCase):
    """Test suite for main interface integration."""
    
    def test_main_interface_imports(self):
        """Test that main interface can import BrainDrive card."""
        try:
            from main_interface import main
            # If we can import without error, the integration is working
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Main interface import failed: {e}")
    
    def test_braindrive_card_import_in_main(self):
        """Test that BrainDrive card is properly imported in main interface."""
        with open('main_interface.py', 'r') as f:
            content = f.read()
        
        self.assertIn('from card_braindrive import BrainDrive', content)
        self.assertNotIn('from card_open_webui import OpenWebUI', content)
        self.assertNotIn('from card_open_webui_pipelines import OpenWebUIPipelines', content)


class TestAssetFiles(unittest.TestCase):
    """Test suite for asset files."""
    
    def test_braindrive_images_exist(self):
        """Test that BrainDrive image files exist."""
        self.assertTrue(os.path.exists('braindrive.png'))
        self.assertTrue(os.path.exists('braindrive_small.png'))
    
    def test_braindrive_ico_exists(self):
        """Test that BrainDrive icon file exists."""
        self.assertTrue(os.path.exists('braindriveai.ico'))


def run_phase3_tests():
    """Run all Phase 3 tests and return results."""
    print("=" * 60)
    print("PHASE 3 TESTING SUITE - BrainDrive Installer Implementation")
    print("=" * 60)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestBrainDriveInstaller,
        TestBrainDriveCard,
        TestConfigurationTemplates,
        TestMainInterfaceIntegration,
        TestAssetFiles
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("PHASE 3 TEST SUMMARY")
    print("=" * 60)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFAILURES ({len(result.failures)}):")
        for test, traceback in result.failures:
            if 'AssertionError:' in traceback:
                error_msg = traceback.split('AssertionError: ')[-1].split('\n')[0]
            else:
                error_msg = 'Unknown failure'
            print(f"- {test}: {error_msg}")
    
    if result.errors:
        print(f"\nERRORS ({len(result.errors)}):")
        for test, traceback in result.errors:
            lines = traceback.split('\n')
            error_msg = lines[-2] if len(lines) > 1 else 'Unknown error'
            print(f"- {test}: {error_msg}")
    
    # Overall status
    if len(result.failures) == 0 and len(result.errors) == 0:
        print(f"\n✅ ALL TESTS PASSED! Phase 3 implementation is ready.")
        return True
    else:
        print(f"\n⚠️  Some tests failed. Review and fix issues before proceeding.")
        return False


if __name__ == "__main__":
    success = run_phase3_tests()
    sys.exit(0 if success else 1)