#!/usr/bin/env python3
"""
Phase 4 Testing - User Interface Updates
Tests the BrainDrive UI components and main interface integration.
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestPhase4Components(unittest.TestCase):
    """Test Phase 4 User Interface Updates"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_passed = 0
        self.test_total = 0
    
    def test_braindrive_card_import(self):
        """Test BrainDrive card can be imported"""
        self.test_total += 1
        try:
            from card_braindrive import BrainDrive
            self.test_passed += 1
            print("[PASS] BrainDrive card import successful")
        except ImportError as e:
            self.fail(f"Failed to import BrainDrive card: {e}")
    
    def test_braindrive_card_instantiation(self):
        """Test BrainDrive card can be instantiated"""
        self.test_total += 1
        try:
            from card_braindrive import BrainDrive
            braindrive = BrainDrive()
            
            # Verify basic properties
            self.assertEqual(braindrive.name, "BrainDrive")
            self.assertIn("Advanced AI platform", braindrive.description)
            self.assertEqual(braindrive.size, "8.5")
            self.assertEqual(braindrive.backend_port, 8005)
            self.assertEqual(braindrive.frontend_port, 5173)
            
            self.test_passed += 1
            print("[PASS] BrainDrive card instantiation successful")
            print(f"   Name: {braindrive.name}")
            print(f"   Description: {braindrive.description[:50]}...")
            print(f"   Backend Port: {braindrive.backend_port}")
            print(f"   Frontend Port: {braindrive.frontend_port}")
            
        except Exception as e:
            self.fail(f"Failed to instantiate BrainDrive card: {e}")
    
    def test_main_interface_import(self):
        """Test main interface can be imported"""
        self.test_total += 1
        try:
            import main_interface
            self.test_passed += 1
            print("[PASS] Main interface import successful")
        except ImportError as e:
            self.fail(f"Failed to import main interface: {e}")
    
    def test_assets_exist(self):
        """Test that required assets exist"""
        self.test_total += 1
        assets = ['braindrive.png', 'braindrive_small.png', 'braindriveai.ico']
        missing_assets = []
        
        for asset in assets:
            if os.path.exists(asset):
                size = os.path.getsize(asset)
                print(f"[PASS] Asset found: {asset} ({size} bytes)")
            else:
                missing_assets.append(asset)
                print(f"[FAIL] Asset missing: {asset}")
        
        if not missing_assets:
            self.test_passed += 1
        else:
            self.fail(f"Missing assets: {missing_assets}")
    
    @patch('tkinter.Tk')
    def test_braindrive_card_methods(self, mock_tk):
        """Test BrainDrive card has required methods"""
        self.test_total += 1
        try:
            from card_braindrive import BrainDrive
            braindrive = BrainDrive()
            
            # Check required methods exist
            required_methods = ['install', 'start_server', 'stop_server', 'update', 'display']
            for method in required_methods:
                self.assertTrue(hasattr(braindrive, method), f"Missing method: {method}")
                self.assertTrue(callable(getattr(braindrive, method)), f"Method not callable: {method}")
            
            self.test_passed += 1
            print("[PASS] BrainDrive card has all required methods")
            print(f"   Methods: {', '.join(required_methods)}")
            
        except Exception as e:
            self.fail(f"Failed to verify BrainDrive card methods: {e}")
    
    def test_main_interface_braindrive_integration(self):
        """Test main interface integrates BrainDrive correctly"""
        self.test_total += 1
        try:
            # Read main_interface.py content
            with open('main_interface.py', 'r') as f:
                content = f.read()
            
            # Check for BrainDrive integration
            self.assertIn('from card_braindrive import BrainDrive', content)
            self.assertIn('braindrive_instance = BrainDrive()', content)
            self.assertIn('BrainDrive Installer', content)
            self.assertIn('BrainDrive.ai', content)
            
            # Check OpenWebUI components are removed
            self.assertNotIn('from card_open_webui import', content)
            self.assertNotIn('from card_open_webui_pipelines import', content)
            
            self.test_passed += 1
            print("[PASS] Main interface properly integrates BrainDrive")
            print("[PASS] OpenWebUI components removed")
            
        except Exception as e:
            self.fail(f"Failed to verify main interface integration: {e}")

def run_phase4_tests():
    """Run all Phase 4 tests and return results"""
    print("=" * 50)
    print("PHASE 4 TESTING - User Interface Updates")
    print("=" * 50)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhase4Components)
    
    # Run tests with custom result handler
    class TestResult(unittest.TextTestResult):
        def __init__(self, stream, descriptions, verbosity):
            super().__init__(stream, descriptions, verbosity)
            self.test_results = []
        
        def addSuccess(self, test):
            super().addSuccess(test)
            self.test_results.append(('PASS', test._testMethodName))
        
        def addError(self, test, err):
            super().addError(test, err)
            self.test_results.append(('ERROR', test._testMethodName, err))
        
        def addFailure(self, test, err):
            super().addFailure(test, err)
            self.test_results.append(('FAIL', test._testMethodName, err))
    
    # Run tests
    runner = unittest.TextTestRunner(resultclass=TestResult, verbosity=0)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print("PHASE 4 TEST SUMMARY")
    print("=" * 50)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    if success:
        print("\n[SUCCESS] ALL PHASE 4 TESTS PASSED!")
        print("[SUCCESS] User Interface Updates completed successfully")
        print("[SUCCESS] Ready for Phase 5: PyInstaller Integration")
    else:
        print("\n[ERROR] Some Phase 4 tests failed")
    
    return success, result.testsRun, len(result.failures), len(result.errors)

if __name__ == "__main__":
    success, total, failures, errors = run_phase4_tests()
    sys.exit(0 if success else 1)