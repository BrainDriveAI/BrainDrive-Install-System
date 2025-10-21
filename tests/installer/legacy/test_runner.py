"""
Automated test runner for BrainDrive Installer test suite.
Provides comprehensive test execution, reporting, and CI/CD integration.
"""

import os
import sys
import time
import json
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestRunner:
    """Automated test runner with comprehensive reporting."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.tests_dir = project_root / "tests"
        self.reports_dir = project_root / "test_reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        self.test_categories = {
            'unit': self.tests_dir / "unit",
            'integration': self.tests_dir / "integration", 
            'performance': self.tests_dir / "performance",
            'platform': self.tests_dir / "platform",
            'error_recovery': self.tests_dir / "error_recovery"
        }
    
    def run_all_tests(self, verbose: bool = True, generate_reports: bool = True) -> Dict:
        """Run all test categories and generate comprehensive report."""
        print("🚀 Starting BrainDrive Installer Test Suite")
        print("=" * 60)
        
        start_time = time.time()
        results = {}
        
        # Run each test category
        for category, test_path in self.test_categories.items():
            if test_path.exists():
                print(f"\n📋 Running {category.upper()} tests...")
                results[category] = self.run_test_category(category, test_path, verbose)
            else:
                print(f"⚠️  {category.upper()} test directory not found: {test_path}")
                results[category] = {'status': 'skipped', 'reason': 'directory not found'}
        
        # Run legacy phase tests
        print(f"\n📋 Running LEGACY PHASE tests...")
        results['legacy'] = self.run_legacy_tests(verbose)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Generate comprehensive report
        if generate_reports:
            report = self.generate_comprehensive_report(results, total_duration)
            self.save_report(report)
            self.print_summary(report)
        
        return results
    
    def run_test_category(self, category: str, test_path: Path, verbose: bool = True) -> Dict:
        """Run tests for a specific category."""
        if not test_path.exists():
            return {'status': 'skipped', 'reason': 'path not found'}
        
        start_time = time.time()
        
        # Prepare pytest arguments
        pytest_args = [
            str(test_path),
            '-v' if verbose else '-q',
            '--tb=short',
            f'--junit-xml={self.reports_dir}/junit_{category}.xml',
            f'--html={self.reports_dir}/report_{category}.html',
            '--self-contained-html',
            f'-m={category}' if category in ['unit', 'integration', 'performance', 'platform'] else ''
        ]
        
        # Remove empty arguments
        pytest_args = [arg for arg in pytest_args if arg]
        
        try:
            # Run pytest
            result = pytest.main(pytest_args)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Determine status
            if result == 0:
                status = 'passed'
            elif result == 1:
                status = 'failed'
            elif result == 2:
                status = 'interrupted'
            elif result == 3:
                status = 'internal_error'
            elif result == 4:
                status = 'usage_error'
            elif result == 5:
                status = 'no_tests'
            else:
                status = 'unknown'
            
            return {
                'status': status,
                'exit_code': result,
                'duration': duration,
                'test_path': str(test_path)
            }
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            return {
                'status': 'error',
                'error': str(e),
                'duration': duration,
                'test_path': str(test_path)
            }
    
    def run_legacy_tests(self, verbose: bool = True) -> Dict:
        """Run legacy phase tests (test_phase1.py, etc.)."""
        legacy_tests = []
        for i in range(1, 6):  # test_phase1.py through test_phase5.py
            test_file = self.project_root / f"test_phase{i}.py"
            if test_file.exists():
                legacy_tests.append(test_file)
        
        if not legacy_tests:
            return {'status': 'skipped', 'reason': 'no legacy tests found'}
        
        start_time = time.time()
        results = {}
        
        for test_file in legacy_tests:
            print(f"  Running {test_file.name}...")
            try:
                # Run the test file directly
                result = subprocess.run([
                    sys.executable, str(test_file)
                ], capture_output=True, text=True, timeout=300)
                
                results[test_file.name] = {
                    'exit_code': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'status': 'passed' if result.returncode == 0 else 'failed'
                }
                
            except subprocess.TimeoutExpired:
                results[test_file.name] = {
                    'status': 'timeout',
                    'error': 'Test execution timed out'
                }
            except Exception as e:
                results[test_file.name] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Determine overall status
        statuses = [r['status'] for r in results.values()]
        if all(s == 'passed' for s in statuses):
            overall_status = 'passed'
        elif any(s == 'error' for s in statuses):
            overall_status = 'error'
        else:
            overall_status = 'failed'
        
        return {
            'status': overall_status,
            'duration': duration,
            'individual_results': results
        }
    
    def run_specific_tests(self, test_patterns: List[str], verbose: bool = True) -> Dict:
        """Run specific tests matching patterns."""
        print(f"🎯 Running specific tests: {', '.join(test_patterns)}")
        
        start_time = time.time()
        
        pytest_args = [
            '-v' if verbose else '-q',
            '--tb=short',
            f'--junit-xml={self.reports_dir}/junit_specific.xml',
            f'--html={self.reports_dir}/report_specific.html',
            '--self-contained-html'
        ]
        
        # Add test patterns
        for pattern in test_patterns:
            if '::' in pattern:  # Specific test method
                pytest_args.append(pattern)
            else:  # File or directory pattern
                pytest_args.append(f"*{pattern}*")
        
        try:
            result = pytest.main(pytest_args)
            
            end_time = time.time()
            duration = end_time - start_time
            
            return {
                'status': 'passed' if result == 0 else 'failed',
                'exit_code': result,
                'duration': duration,
                'patterns': test_patterns
            }
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            return {
                'status': 'error',
                'error': str(e),
                'duration': duration,
                'patterns': test_patterns
            }
    
    def generate_comprehensive_report(self, results: Dict, total_duration: float) -> Dict:
        """Generate comprehensive test report."""
        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_duration': total_duration,
            'project_root': str(self.project_root),
            'python_version': sys.version,
            'platform': sys.platform,
            'results': results,
            'summary': self.calculate_summary(results),
            'recommendations': self.generate_recommendations(results)
        }
        
        return report
    
    def calculate_summary(self, results: Dict) -> Dict:
        """Calculate test summary statistics."""
        total_categories = len(results)
        passed_categories = sum(1 for r in results.values() 
                              if isinstance(r, dict) and r.get('status') == 'passed')
        failed_categories = sum(1 for r in results.values() 
                              if isinstance(r, dict) and r.get('status') == 'failed')
        error_categories = sum(1 for r in results.values() 
                             if isinstance(r, dict) and r.get('status') == 'error')
        skipped_categories = sum(1 for r in results.values() 
                               if isinstance(r, dict) and r.get('status') == 'skipped')
        
        total_duration = sum(r.get('duration', 0) for r in results.values() 
                           if isinstance(r, dict))
        
        return {
            'total_categories': total_categories,
            'passed_categories': passed_categories,
            'failed_categories': failed_categories,
            'error_categories': error_categories,
            'skipped_categories': skipped_categories,
            'success_rate': (passed_categories / total_categories * 100) if total_categories > 0 else 0,
            'total_duration': total_duration
        }
    
    def generate_recommendations(self, results: Dict) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        # Check for failed categories
        failed_categories = [cat for cat, result in results.items() 
                           if isinstance(result, dict) and result.get('status') == 'failed']
        
        if failed_categories:
            recommendations.append(f"❌ Fix failing tests in: {', '.join(failed_categories)}")
        
        # Check for missing test categories
        missing_categories = [cat for cat, path in self.test_categories.items() 
                            if not path.exists()]
        
        if missing_categories:
            recommendations.append(f"📁 Create missing test directories: {', '.join(missing_categories)}")
        
        # Check performance
        perf_result = results.get('performance', {})
        if perf_result.get('status') == 'failed':
            recommendations.append("⚡ Performance tests failing - check resource usage and timing")
        
        # Check platform compatibility
        platform_result = results.get('platform', {})
        if platform_result.get('status') == 'failed':
            recommendations.append("🖥️  Platform compatibility issues detected")
        
        # General recommendations
        if not recommendations:
            recommendations.append("✅ All tests passing - ready for production")
        
        return recommendations
    
    def save_report(self, report: Dict) -> Path:
        """Save comprehensive report to file."""
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        report_file = self.reports_dir / f"comprehensive_report_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Also save as latest
        latest_file = self.reports_dir / "latest_report.json"
        with open(latest_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"📊 Report saved to: {report_file}")
        return report_file
    
    def print_summary(self, report: Dict):
        """Print test summary to console."""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        summary = report['summary']
        
        print(f"Total Duration: {summary['total_duration']:.2f}s")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print(f"Categories: {summary['total_categories']} total")
        print(f"  ✅ Passed: {summary['passed_categories']}")
        print(f"  ❌ Failed: {summary['failed_categories']}")
        print(f"  ⚠️  Errors: {summary['error_categories']}")
        print(f"  ⏭️  Skipped: {summary['skipped_categories']}")
        
        print("\n📋 RECOMMENDATIONS:")
        for rec in report['recommendations']:
            print(f"  {rec}")
        
        print("\n📁 REPORTS GENERATED:")
        print(f"  📊 Comprehensive: {self.reports_dir}/latest_report.json")
        for category in self.test_categories.keys():
            junit_file = self.reports_dir / f"junit_{category}.xml"
            html_file = self.reports_dir / f"report_{category}.html"
            if junit_file.exists():
                print(f"  📄 {category.title()}: {html_file}")
    
    def run_ci_pipeline(self) -> bool:
        """Run CI/CD pipeline with appropriate exit codes."""
        print("🔄 Running CI/CD Pipeline")
        
        results = self.run_all_tests(verbose=False, generate_reports=True)
        
        # Determine if pipeline should pass
        critical_categories = ['unit', 'integration']
        critical_passed = all(
            results.get(cat, {}).get('status') == 'passed' 
            for cat in critical_categories
        )
        
        # Legacy tests should also pass
        legacy_passed = results.get('legacy', {}).get('status') == 'passed'
        
        pipeline_success = critical_passed and legacy_passed
        
        if pipeline_success:
            print("✅ CI/CD Pipeline PASSED")
            return True
        else:
            print("❌ CI/CD Pipeline FAILED")
            return False


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(description="BrainDrive Installer Test Runner")
    parser.add_argument('--category', choices=['unit', 'integration', 'performance', 'platform', 'error_recovery', 'legacy'], 
                       help='Run specific test category')
    parser.add_argument('--pattern', nargs='+', help='Run tests matching patterns')
    parser.add_argument('--ci', action='store_true', help='Run in CI/CD mode')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--no-reports', action='store_true', help='Skip report generation')
    
    args = parser.parse_args()
    
    # Initialize test runner
    runner = TestRunner(project_root)
    
    try:
        if args.ci:
            # CI/CD mode
            success = runner.run_ci_pipeline()
            sys.exit(0 if success else 1)
        
        elif args.category:
            # Run specific category
            test_path = runner.test_categories.get(args.category)
            if args.category == 'legacy':
                results = runner.run_legacy_tests(args.verbose)
            elif test_path:
                results = runner.run_test_category(args.category, test_path, args.verbose)
            else:
                print(f"❌ Unknown category: {args.category}")
                sys.exit(1)
            
            print(f"\n📊 {args.category.upper()} Results: {results}")
        
        elif args.pattern:
            # Run specific patterns
            results = runner.run_specific_tests(args.pattern, args.verbose)
            print(f"\n📊 Pattern Results: {results}")
        
        else:
            # Run all tests
            results = runner.run_all_tests(args.verbose, not args.no_reports)
        
    except KeyboardInterrupt:
        print("\n⚠️  Test execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Test runner error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()