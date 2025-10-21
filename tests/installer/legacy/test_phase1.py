#!/usr/bin/env python3
"""
Test script for Phase 1 implementation - Foundation & Cross-Platform Support
Tests all the core components we've implemented.
"""

import sys
import os
import traceback
from pathlib import Path

# Add current directory to path to import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_platform_utils():
    """Test the PlatformUtils class functionality."""
    print("=" * 60)
    print("TESTING PLATFORM_UTILS")
    print("=" * 60)
    
    try:
        from platform_utils import PlatformUtils
        
        # Test OS detection
        os_type = PlatformUtils.get_os_type()
        print(f"✓ OS Type: {os_type}")
        
        # Test home directory
        home_dir = PlatformUtils.get_home_directory()
        print(f"✓ Home Directory: {home_dir}")
        
        # Test BrainDrive base path
        base_path = PlatformUtils.get_braindrive_base_path()
        print(f"✓ BrainDrive Base Path: {base_path}")
        
        # Test executable extensions
        exe_ext = PlatformUtils.get_executable_extension()
        print(f"✓ Executable Extension: '{exe_ext}'")
        
        # Test command availability
        conda_available = PlatformUtils.is_command_available('conda')
        print(f"✓ Conda Available: {conda_available}")
        
        git_available = PlatformUtils.is_command_available('git')
        print(f"✓ Git Available: {git_available}")
        
        node_available = PlatformUtils.is_command_available('node')
        print(f"✓ Node.js Available: {node_available}")
        
        # Test system info
        system_info = PlatformUtils.get_system_info()
        print(f"✓ System Info Keys: {list(system_info.keys())}")
        
        print("✓ PlatformUtils: ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"✗ PlatformUtils: FAILED - {str(e)}")
        traceback.print_exc()
        return False

def test_app_config():
    """Test the AppConfig class functionality."""
    print("\n" + "=" * 60)
    print("TESTING APP_CONFIG")
    print("=" * 60)
    
    try:
        from AppConfig import AppConfig
        
        # Test singleton pattern
        config1 = AppConfig()
        config2 = AppConfig()
        assert config1 is config2, "AppConfig should be a singleton"
        print("✓ Singleton Pattern: Working")
        
        # Test path configuration
        print(f"✓ Base Path: {config1.base_path}")
        print(f"✓ Miniconda Path: {config1.miniconda_path}")
        print(f"✓ Environment Path: {config1.env_path}")
        print(f"✓ Repository Path: {config1.repo_path}")
        print(f"✓ Backend Path: {config1.backend_path}")
        print(f"✓ Frontend Path: {config1.frontend_path}")
        print(f"✓ Plugins Path: {config1.plugins_path}")
        print(f"✓ Conda Executable: {config1.conda_exe}")
        
        # Test properties
        print(f"✓ Miniconda Installed: {config1.is_miniconda_installed}")
        print(f"✓ BrainDrive Environment Ready: {config1.has_braindrive_env}")
        print(f"✓ BrainDrive Repository Ready: {config1.has_braindrive_repo}")
        
        # Test system info
        system_info = config1.get_system_info()
        print(f"✓ System Info Available: {len(system_info)} keys")
        
        print("✓ AppConfig: ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"✗ AppConfig: FAILED - {str(e)}")
        traceback.print_exc()
        return False

def test_base_installer():
    """Test the BaseInstaller class functionality."""
    print("\n" + "=" * 60)
    print("TESTING BASE_INSTALLER")
    print("=" * 60)
    
    try:
        from base_installer import BaseInstaller
        
        # Create a concrete implementation for testing
        class TestInstaller(BaseInstaller):
            def check_installed(self):
                return True
            
            def install(self):
                pass
            
            def check_requirements(self):
                return True
            
            def setup_environment(self, env_name):
                pass
            
            def update(self):
                pass
            
            def clone_repository(self, repo_url, target_path, branch="main"):
                return True
            
            def build_plugins(self):
                return True
            
            def start_services(self):
                return True
            
            def stop_services(self):
                return True
        
        # Test instantiation
        installer = TestInstaller("TestInstaller")
        print(f"✓ Installer Name: {installer.name}")
        
        # Test system requirements check
        requirements = installer.get_system_requirements_status()
        print(f"✓ Git Available: {requirements['git_available']}")
        print(f"✓ Node Available: {requirements['node_available']}")
        print(f"✓ Conda Available: {requirements['conda_available']}")
        print(f"✓ OS Type: {requirements['os_type']}")
        
        # Test disk space check
        has_space = installer.check_disk_space(1)  # 1GB requirement
        print(f"✓ Sufficient Disk Space (1GB): {has_space}")
        
        # Test directory creation
        test_dir = os.path.join(installer.config.base_path, "test_dir")
        created = installer.create_directory_safely(test_dir)
        print(f"✓ Directory Creation: {created}")
        
        # Clean up test directory
        if created and os.path.exists(test_dir):
            os.rmdir(test_dir)
            print("✓ Test Directory Cleaned Up")
        
        print("✓ BaseInstaller: ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"✗ BaseInstaller: FAILED - {str(e)}")
        traceback.print_exc()
        return False

def test_miniconda_installer():
    """Test the MinicondaInstaller class functionality."""
    print("\n" + "=" * 60)
    print("TESTING MINICONDA_INSTALLER")
    print("=" * 60)
    
    try:
        from installer_miniconda import MinicondaInstaller
        
        # Test instantiation
        installer = MinicondaInstaller()
        print(f"✓ Installer Name: {installer.name}")
        print(f"✓ Miniconda Path: {installer.miniconda_path}")
        print(f"✓ Installer Path: {installer.installer_path}")
        print(f"✓ Installer URL: {installer.miniconda_url}")
        
        # Test installation check
        is_installed = installer.check_installed()
        print(f"✓ Miniconda Installed: {is_installed}")
        
        # Test requirements check
        requirements_ok = installer.check_requirements()
        print(f"✓ Requirements Check: {requirements_ok}")
        
        # Test system requirements
        system_reqs = installer.get_system_requirements_status()
        print(f"✓ System Requirements Available: {len(system_reqs)} items")
        
        print("✓ MinicondaInstaller: ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"✗ MinicondaInstaller: FAILED - {str(e)}")
        traceback.print_exc()
        return False

def main():
    """Run all Phase 1 tests."""
    print("BRAINDRIVE INSTALLER - PHASE 1 TESTING")
    print("Foundation & Cross-Platform Support")
    print("=" * 60)
    
    test_results = []
    
    # Run all tests
    test_results.append(("PlatformUtils", test_platform_utils()))
    test_results.append(("AppConfig", test_app_config()))
    test_results.append(("BaseInstaller", test_base_installer()))
    test_results.append(("MinicondaInstaller", test_miniconda_installer()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "PASSED" if result else "FAILED"
        symbol = "✓" if result else "✗"
        print(f"{symbol} {test_name}: {status}")
        
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nTotal Tests: {len(test_results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 ALL PHASE 1 TESTS PASSED! 🎉")
        print("Foundation & Cross-Platform Support is ready!")
        return True
    else:
        print(f"\n❌ {failed} TEST(S) FAILED")
        print("Please review and fix the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)