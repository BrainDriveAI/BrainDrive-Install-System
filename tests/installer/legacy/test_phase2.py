"""
Test Suite for Phase 2 Components - Core BrainDrive Components
Tests Git Manager, Node Manager, Plugin Builder, and Process Manager
"""

import os
import sys
import tempfile
import shutil
import json
import time
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from git_manager import GitManager
from node_manager import NodeManager
from plugin_builder import PluginBuilder
from process_manager import ProcessManager
from platform_utils import PlatformUtils


class TestGitManager(unittest.TestCase):
    """Test cases for GitManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.status_updater = Mock()
        self.git_manager = GitManager(self.status_updater)
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_git_manager_initialization(self):
        """Test GitManager initialization."""
        self.assertIsNotNone(self.git_manager)
        self.assertEqual(self.git_manager.status_updater, self.status_updater)
    
    @patch('subprocess.run')
    def test_check_git_available_success(self, mock_run):
        """Test successful Git availability check."""
        mock_run.return_value = Mock(returncode=0, stdout="git version 2.34.1", stderr="")
        
        is_available, version = self.git_manager.check_git_available()
        
        self.assertTrue(is_available)
        self.assertIn("git version", version)
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_check_git_available_failure(self, mock_run):
        """Test Git availability check failure."""
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="git: command not found")
        
        is_available, error = self.git_manager.check_git_available()
        
        self.assertFalse(is_available)
        self.assertIn("not found", error)
    
    def test_get_repository_status_invalid_path(self):
        """Test repository status check with invalid path."""
        invalid_path = os.path.join(self.temp_dir, "nonexistent")
        
        is_valid, status_info = self.git_manager.get_repository_status(invalid_path)
        
        self.assertFalse(is_valid)
        self.assertIn("error", status_info)


class TestNodeManager(unittest.TestCase):
    """Test cases for NodeManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.status_updater = Mock()
        self.node_manager = NodeManager(self.status_updater)
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_node_manager_initialization(self):
        """Test NodeManager initialization."""
        self.assertIsNotNone(self.node_manager)
        self.assertEqual(self.node_manager.status_updater, self.status_updater)
    
    @patch('subprocess.run')
    def test_check_node_available_success(self, mock_run):
        """Test successful Node.js availability check."""
        def mock_run_side_effect(command, **kwargs):
            if 'node' in command and '--version' in command:
                return Mock(returncode=0, stdout="v18.17.0", stderr="")
            elif 'npm' in command and '--version' in command:
                return Mock(returncode=0, stdout="9.6.7", stderr="")
            elif 'npx' in command and '--version' in command:
                return Mock(returncode=0, stdout="9.6.7", stderr="")
            return Mock(returncode=1, stdout="", stderr="command not found")
        
        mock_run.side_effect = mock_run_side_effect
        
        is_available, version_info = self.node_manager.check_node_available()
        
        self.assertTrue(is_available)
        self.assertIn('node', version_info)
        self.assertIn('npm', version_info)
    
    def test_check_package_json_exists_missing(self):
        """Test package.json check with missing file."""
        exists, package_info = self.node_manager.check_package_json_exists(self.temp_dir)
        
        self.assertFalse(exists)
        self.assertIn("error", package_info)
    
    def test_check_package_json_exists_valid(self):
        """Test package.json check with valid file."""
        # Create a test package.json
        package_data = {
            "name": "test-package",
            "version": "1.0.2",
            "scripts": {
                "build": "echo 'building'",
                "dev": "echo 'dev server'"
            }
        }
        
        package_json_path = os.path.join(self.temp_dir, "package.json")
        with open(package_json_path, 'w') as f:
            json.dump(package_data, f)
        
        exists, package_info = self.node_manager.check_package_json_exists(self.temp_dir)
        
        self.assertTrue(exists)
        self.assertEqual(package_info["name"], "test-package")
        self.assertEqual(package_info["version"], "1.0.2")
        self.assertIn("build", package_info["scripts"])
    
    def test_check_node_modules_exists_missing(self):
        """Test node_modules check with missing directory."""
        exists = self.node_manager.check_node_modules_exists(self.temp_dir)
        self.assertFalse(exists)
    
    def test_check_node_modules_exists_empty(self):
        """Test node_modules check with empty directory."""
        node_modules_path = os.path.join(self.temp_dir, "node_modules")
        os.makedirs(node_modules_path)
        
        exists = self.node_manager.check_node_modules_exists(self.temp_dir)
        self.assertFalse(exists)
    
    def test_check_node_modules_exists_with_content(self):
        """Test node_modules check with content."""
        node_modules_path = os.path.join(self.temp_dir, "node_modules")
        os.makedirs(node_modules_path)
        
        # Create a dummy package directory
        dummy_package_path = os.path.join(node_modules_path, "dummy-package")
        os.makedirs(dummy_package_path)
        
        exists = self.node_manager.check_node_modules_exists(self.temp_dir)
        self.assertTrue(exists)


class TestPluginBuilder(unittest.TestCase):
    """Test cases for PluginBuilder class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.status_updater = Mock()
        self.temp_dir = tempfile.mkdtemp()
        self.plugins_dir = os.path.join(self.temp_dir, "plugins")
        os.makedirs(self.plugins_dir)
        self.plugin_builder = PluginBuilder(self.plugins_dir, self.status_updater)
        
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_plugin_builder_initialization(self):
        """Test PluginBuilder initialization."""
        self.assertIsNotNone(self.plugin_builder)
        self.assertEqual(self.plugin_builder.plugins_path, self.plugins_dir)
        self.assertEqual(self.plugin_builder.status_updater, self.status_updater)
    
    def test_validate_plugins_directory_missing(self):
        """Test plugins directory validation with missing directory."""
        invalid_path = os.path.join(self.temp_dir, "nonexistent")
        plugin_builder = PluginBuilder(invalid_path, self.status_updater)
        
        is_valid, error_msg = plugin_builder.validate_plugins_directory()
        
        self.assertFalse(is_valid)
        self.assertIn("does not exist", error_msg)
    
    def test_validate_plugins_directory_valid(self):
        """Test plugins directory validation with valid directory."""
        is_valid, error_msg = self.plugin_builder.validate_plugins_directory()
        
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_discover_plugins_empty_directory(self):
        """Test plugin discovery with empty plugins directory."""
        success, plugins = self.plugin_builder.discover_plugins()
        
        self.assertTrue(success)
        self.assertEqual(len(plugins), 0)
    
    def test_discover_plugins_with_valid_plugin(self):
        """Test plugin discovery with valid plugin."""
        # Create a test plugin directory
        plugin_dir = os.path.join(self.plugins_dir, "test-plugin")
        os.makedirs(plugin_dir)
        
        # Create package.json for the plugin
        package_data = {
            "name": "test-plugin",
            "version": "1.0.2",
            "scripts": {
                "build": "echo 'building plugin'"
            }
        }
        
        package_json_path = os.path.join(plugin_dir, "package.json")
        with open(package_json_path, 'w') as f:
            json.dump(package_data, f)
        
        success, plugins = self.plugin_builder.discover_plugins()
        
        self.assertTrue(success)
        self.assertEqual(len(plugins), 1)
        self.assertEqual(plugins[0]["name"], "test-plugin")
        self.assertTrue(plugins[0]["has_build_script"])
    
    def test_check_plugin_built_not_built(self):
        """Test plugin build status check for unbuilt plugin."""
        plugin_dir = os.path.join(self.plugins_dir, "test-plugin")
        os.makedirs(plugin_dir)
        
        is_built, build_info = self.plugin_builder.check_plugin_built(plugin_dir)
        
        self.assertFalse(is_built)
        self.assertFalse(build_info["has_node_modules"])
        self.assertEqual(len(build_info["build_artifacts"]), 0)


class TestProcessManager(unittest.TestCase):
    """Test cases for ProcessManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.status_updater = Mock()
        self.process_manager = ProcessManager(self.status_updater)
        
    def tearDown(self):
        """Clean up any running processes."""
        self.process_manager.stop_all_processes()
    
    def test_process_manager_initialization(self):
        """Test ProcessManager initialization."""
        self.assertIsNotNone(self.process_manager)
        self.assertEqual(self.process_manager.status_updater, self.status_updater)
        self.assertEqual(len(self.process_manager.processes), 0)
    
    def test_check_port_available_free_port(self):
        """Test port availability check with free port."""
        # Use a high port number that's likely to be free
        is_available = self.process_manager.check_port_available(65432)
        self.assertTrue(is_available)
    
    def test_start_simple_process(self):
        """Test starting a simple process."""
        if PlatformUtils.get_os_type() == 'windows':
            command = ['ping', 'localhost', '-n', '1']
        else:
            command = ['ping', 'localhost', '-c', '1']
        
        success, error_msg = self.process_manager.start_process("test_ping", command)
        
        self.assertTrue(success)
        self.assertEqual(error_msg, "")
        self.assertIn("test_ping", self.process_manager.processes)
        
        # Clean up
        self.process_manager.stop_process("test_ping")
    
    def test_process_status_nonexistent(self):
        """Test getting status of non-existent process."""
        status = self.process_manager.get_process_status("nonexistent")
        
        self.assertFalse(status["exists"])
        self.assertFalse(status["running"])
        self.assertIn("error", status)
    
    def test_stop_nonexistent_process(self):
        """Test stopping non-existent process."""
        success, error_msg = self.process_manager.stop_process("nonexistent")
        
        self.assertTrue(success)  # Should succeed (no-op)
    
    def test_get_all_process_status_empty(self):
        """Test getting all process status when no processes are running."""
        status_dict = self.process_manager.get_all_process_status()
        
        self.assertEqual(len(status_dict), 0)
    
    def test_cleanup_dead_processes(self):
        """Test cleanup of dead processes."""
        # Initially no processes
        cleaned = self.process_manager.cleanup_dead_processes()
        self.assertEqual(cleaned, 0)


class TestPhase2Integration(unittest.TestCase):
    """Integration tests for Phase 2 components."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.status_updater = Mock()
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up integration test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_components_initialization(self):
        """Test that all Phase 2 components can be initialized together."""
        git_manager = GitManager(self.status_updater)
        node_manager = NodeManager(self.status_updater)
        plugins_dir = os.path.join(self.temp_dir, "plugins")
        os.makedirs(plugins_dir)
        plugin_builder = PluginBuilder(plugins_dir, self.status_updater)
        process_manager = ProcessManager(self.status_updater)
        
        self.assertIsNotNone(git_manager)
        self.assertIsNotNone(node_manager)
        self.assertIsNotNone(plugin_builder)
        self.assertIsNotNone(process_manager)
    
    def test_status_updater_integration(self):
        """Test that all components properly use the status updater."""
        git_manager = GitManager(self.status_updater)
        node_manager = NodeManager(self.status_updater)
        
        # Test that status updater is called
        git_manager._update_status("Test message")
        node_manager._update_status("Test message")
        
        # Verify status updater was called
        self.assertTrue(self.status_updater.update_status.called)


def run_phase2_tests():
    """Run all Phase 2 tests and return results."""
    print("=" * 60)
    print("PHASE 2 COMPONENT TESTING")
    print("=" * 60)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestGitManager,
        TestNodeManager,
        TestPluginBuilder,
        TestProcessManager,
        TestPhase2Integration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("PHASE 2 TEST SUMMARY")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            error_msg = traceback.split('AssertionError: ')[-1].split('\n')[0]
            print(f"- {test}: {error_msg}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            error_msg = traceback.split('\n')[-2]
            print(f"- {test}: {error_msg}")
    
    # Return success status
    return len(result.failures) == 0 and len(result.errors) == 0


def test_system_requirements():
    """Test system requirements for Phase 2 components."""
    print("\n" + "=" * 60)
    print("SYSTEM REQUIREMENTS CHECK")
    print("=" * 60)
    
    requirements_met = True
    
    # Test platform utilities
    try:
        os_type = PlatformUtils.get_os_type()
        print(f"✅ Operating System: {os_type}")
    except Exception as e:
        print(f"❌ Platform detection failed: {e}")
        requirements_met = False
    
    # Test Git availability (if installed)
    git_manager = GitManager()
    is_available, version_or_error = git_manager.check_git_available()
    if is_available:
        print(f"✅ Git: {version_or_error}")
    else:
        print(f"⚠️  Git: {version_or_error}")
    
    # Test Node.js availability (if installed)
    node_manager = NodeManager()
    is_available, version_info = node_manager.check_node_available()
    if is_available:
        print(f"✅ Node.js: {version_info.get('node', 'N/A')}")
        print(f"✅ npm: {version_info.get('npm', 'N/A')}")
    else:
        print(f"⚠️  Node.js/npm: {version_info.get('error', 'Not available')}")
    
    # Test process management
    try:
        process_manager = ProcessManager()
        print("✅ Process Manager: Initialized successfully")
    except Exception as e:
        print(f"❌ Process Manager: {e}")
        requirements_met = False
    
    return requirements_met


if __name__ == "__main__":
    print("BrainDrive Installer - Phase 2 Component Testing")
    print("Testing Git Manager, Node Manager, Plugin Builder, and Process Manager")
    
    # Test system requirements first
    requirements_ok = test_system_requirements()
    
    # Run component tests
    tests_passed = run_phase2_tests()
    
    # Final result
    print("\n" + "=" * 60)
    print("OVERALL PHASE 2 STATUS")
    print("=" * 60)
    
    if requirements_ok and tests_passed:
        print("🎉 Phase 2 implementation: SUCCESS")
        print("All core BrainDrive components are working correctly!")
        exit_code = 0
    else:
        print("❌ Phase 2 implementation: ISSUES DETECTED")
        if not requirements_ok:
            print("- System requirements not fully met")
        if not tests_passed:
            print("- Some component tests failed")
        exit_code = 1
    
    sys.exit(exit_code)
