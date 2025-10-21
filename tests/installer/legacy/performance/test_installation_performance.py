"""
Performance tests for BrainDrive installation process.
Tests installation time, memory usage, and resource utilization.
"""

import pytest
import os
import sys
import time
import psutil
import threading
import tempfile
from unittest.mock import Mock, patch
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from installer_braindrive import BrainDriveInstaller
from git_manager import GitManager
from node_manager import NodeManager
from plugin_builder import PluginBuilder
from process_manager import ProcessManager


class PerformanceMonitor:
    """Monitor system performance during operations."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.peak_memory = 0
        self.peak_cpu = 0
        self.monitoring = False
        self.monitor_thread = None
        self.process = psutil.Process()
    
    def start_monitoring(self):
        """Start performance monitoring."""
        self.start_time = time.time()
        self.monitoring = True
        self.peak_memory = 0
        self.peak_cpu = 0
        
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop performance monitoring."""
        self.end_time = time.time()
        self.monitoring = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
    
    def _monitor_loop(self):
        """Monitor system resources in background thread."""
        while self.monitoring:
            try:
                # Memory usage
                memory_info = self.process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                self.peak_memory = max(self.peak_memory, memory_mb)
                
                # CPU usage
                cpu_percent = self.process.cpu_percent()
                self.peak_cpu = max(self.peak_cpu, cpu_percent)
                
                time.sleep(0.1)  # Sample every 100ms
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
    
    def get_duration(self):
        """Get operation duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0
    
    def get_peak_memory_mb(self):
        """Get peak memory usage in MB."""
        return self.peak_memory
    
    def get_peak_cpu_percent(self):
        """Get peak CPU usage percentage."""
        return self.peak_cpu
    
    def get_metrics(self):
        """Get all performance metrics."""
        return {
            'duration_seconds': self.get_duration(),
            'peak_memory_mb': self.get_peak_memory_mb(),
            'peak_cpu_percent': self.get_peak_cpu_percent()
        }


@pytest.mark.performance
class TestInstallationPerformance:
    """Performance tests for installation process."""
    
    @pytest.fixture
    def performance_monitor(self):
        """Create performance monitor fixture."""
        monitor = PerformanceMonitor()
        yield monitor
        monitor.stop_monitoring()
    
    @pytest.mark.slow
    def test_installer_initialization_performance(self, performance_monitor):
        """Test installer initialization performance."""
        performance_monitor.start_monitoring()
        
        # Initialize installer multiple times to get average
        installers = []
        for _ in range(10):
            installer = BrainDriveInstaller()
            installers.append(installer)
        
        performance_monitor.stop_monitoring()
        metrics = performance_monitor.get_metrics()
        
        # Performance assertions
        assert metrics['duration_seconds'] < 1.0, f"Initialization took {metrics['duration_seconds']:.2f}s, expected <1.0s"
        assert metrics['peak_memory_mb'] < 100, f"Peak memory {metrics['peak_memory_mb']:.1f}MB, expected <100MB"
        
        print(f"Installer initialization: {metrics['duration_seconds']:.3f}s, {metrics['peak_memory_mb']:.1f}MB peak")
    
    @patch('subprocess.run')
    def test_requirements_check_performance(self, mock_run, performance_monitor):
        """Test requirements checking performance."""
        # Mock subprocess calls to return quickly
        mock_run.return_value = Mock(returncode=0, stdout="version info", stderr="")
        
        installer = BrainDriveInstaller()
        
        performance_monitor.start_monitoring()
        
        # Run requirements check multiple times
        for _ in range(5):
            installer.check_requirements()
        
        performance_monitor.stop_monitoring()
        metrics = performance_monitor.get_metrics()
        
        # Performance assertions
        assert metrics['duration_seconds'] < 2.0, f"Requirements check took {metrics['duration_seconds']:.2f}s, expected <2.0s"
        assert metrics['peak_memory_mb'] < 50, f"Peak memory {metrics['peak_memory_mb']:.1f}MB, expected <50MB"
        
        print(f"Requirements check: {metrics['duration_seconds']:.3f}s, {metrics['peak_memory_mb']:.1f}MB peak")
    
    @patch('subprocess.run')
    def test_git_clone_performance_simulation(self, mock_run, performance_monitor):
        """Test Git clone performance simulation."""
        # Simulate git clone with delay
        def slow_git_clone(*args, **kwargs):
            time.sleep(0.5)  # Simulate network delay
            return Mock(returncode=0, stdout="", stderr="")
        
        mock_run.side_effect = slow_git_clone
        
        git_manager = GitManager()
        
        performance_monitor.start_monitoring()
        
        result = git_manager.clone_repository(
            "https://github.com/test/repo.git",
            "/tmp/test_repo"
        )
        
        performance_monitor.stop_monitoring()
        metrics = performance_monitor.get_metrics()
        
        assert result is True
        assert metrics['duration_seconds'] >= 0.5, "Should include simulated network delay"
        assert metrics['duration_seconds'] < 10.0, f"Git clone took {metrics['duration_seconds']:.2f}s, expected <10.0s"
        
        print(f"Git clone simulation: {metrics['duration_seconds']:.3f}s, {metrics['peak_memory_mb']:.1f}MB peak")
    
    @patch('subprocess.run')
    def test_dependency_installation_performance(self, mock_run, performance_monitor):
        """Test dependency installation performance."""
        # Mock pip/npm install with realistic delay
        def slow_install(*args, **kwargs):
            if 'pip' in args[0] or 'npm' in args[0]:
                time.sleep(0.2)  # Simulate package installation
            return Mock(returncode=0, stdout="", stderr="")
        
        mock_run.side_effect = slow_install
        
        installer = BrainDriveInstaller()
        
        performance_monitor.start_monitoring()
        
        # Mock file operations
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open') as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = "template"
                
                backend_result = installer.setup_backend()
                frontend_result = installer.setup_frontend()
        
        performance_monitor.stop_monitoring()
        metrics = performance_monitor.get_metrics()
        
        assert backend_result is True
        assert frontend_result is True
        assert metrics['duration_seconds'] < 5.0, f"Dependency installation took {metrics['duration_seconds']:.2f}s, expected <5.0s"
        
        print(f"Dependency installation: {metrics['duration_seconds']:.3f}s, {metrics['peak_memory_mb']:.1f}MB peak")
    
    def test_plugin_building_performance(self, performance_monitor, temp_dir):
        """Test plugin building performance."""
        # Create mock plugins
        plugins_dir = os.path.join(temp_dir, "plugins")
        os.makedirs(plugins_dir)
        
        # Create multiple mock plugins
        for i in range(5):
            plugin_dir = os.path.join(plugins_dir, f"plugin-{i}")
            os.makedirs(plugin_dir)
            
            with open(os.path.join(plugin_dir, "package.json"), "w") as f:
                f.write(f'{{"name": "plugin-{i}", "scripts": {{"build": "echo building"}}}}')
        
        plugin_builder = PluginBuilder(plugins_dir)
        
        performance_monitor.start_monitoring()
        
        # Discover plugins
        plugins = plugin_builder.discover_plugins()
        
        # Mock build process
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            
            result = plugin_builder.build_all_plugins()
        
        performance_monitor.stop_monitoring()
        metrics = performance_monitor.get_metrics()
        
        assert len(plugins) == 5
        assert result is True
        assert metrics['duration_seconds'] < 3.0, f"Plugin building took {metrics['duration_seconds']:.2f}s, expected <3.0s"
        
        print(f"Plugin building: {metrics['duration_seconds']:.3f}s, {metrics['peak_memory_mb']:.1f}MB peak")
    
    def test_process_management_performance(self, performance_monitor):
        """Test process management performance."""
        process_manager = ProcessManager()
        
        performance_monitor.start_monitoring()
        
        # Mock process operations
        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process
            
            # Start multiple processes
            for i in range(10):
                result = process_manager.start_process(
                    f"test_process_{i}",
                    ["python", "-c", "import time; time.sleep(1)"]
                )
                assert result is True
            
            # Check process status
            for i in range(10):
                is_running = process_manager.is_process_running(f"test_process_{i}")
                assert is_running is True
            
            # Stop all processes
            process_manager.stop_all_processes()
        
        performance_monitor.stop_monitoring()
        metrics = performance_monitor.get_metrics()
        
        assert metrics['duration_seconds'] < 1.0, f"Process management took {metrics['duration_seconds']:.2f}s, expected <1.0s"
        
        print(f"Process management: {metrics['duration_seconds']:.3f}s, {metrics['peak_memory_mb']:.1f}MB peak")
    
    @patch('installer_braindrive.BrainDriveInstaller.clone_repository')
    @patch('installer_braindrive.BrainDriveInstaller.setup_environment')
    @patch('subprocess.run')
    def test_full_installation_performance(self, mock_run, mock_setup_env, mock_clone, performance_monitor, temp_dir):
        """Test full installation workflow performance."""
        # Mock all external operations
        mock_setup_env.return_value = True
        mock_clone.return_value = True
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        installer = BrainDriveInstaller()
        
        # Override paths to use temp directory
        installer.config.repo_path = os.path.join(temp_dir, "BrainDrive")
        installer.config.backend_path = os.path.join(temp_dir, "BrainDrive", "backend")
        installer.config.frontend_path = os.path.join(temp_dir, "BrainDrive", "frontend")
        
        # Create mock directory structure
        os.makedirs(installer.config.backend_path, exist_ok=True)
        os.makedirs(installer.config.frontend_path, exist_ok=True)
        
        # Mock plugin builder and process manager
        installer.plugin_builder.build_all_plugins = Mock(return_value=True)
        installer.process_manager.start_process = Mock(return_value=True)
        
        performance_monitor.start_monitoring()
        
        # Mock file operations
        with patch('builtins.open') as mock_open:
            with patch('os.path.exists', return_value=True):
                mock_open.return_value.__enter__.return_value.read.return_value = "template"
                
                result = installer.install()
        
        performance_monitor.stop_monitoring()
        metrics = performance_monitor.get_metrics()
        
        assert result is True
        
        # Performance targets based on roadmap
        assert metrics['duration_seconds'] < 900, f"Installation took {metrics['duration_seconds']:.2f}s, expected <900s (15min)"
        assert metrics['peak_memory_mb'] < 200, f"Peak memory {metrics['peak_memory_mb']:.1f}MB, expected <200MB"
        
        print(f"Full installation: {metrics['duration_seconds']:.3f}s, {metrics['peak_memory_mb']:.1f}MB peak")


@pytest.mark.performance
class TestMemoryUsage:
    """Memory usage tests for various operations."""
    
    def test_installer_memory_footprint(self):
        """Test installer memory footprint."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        # Create multiple installers
        installers = []
        for _ in range(10):
            installer = BrainDriveInstaller()
            installers.append(installer)
        
        peak_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = peak_memory - initial_memory
        
        # Each installer should use minimal memory
        assert memory_increase < 50, f"Memory increase {memory_increase:.1f}MB, expected <50MB"
        
        print(f"Installer memory footprint: {memory_increase:.1f}MB for 10 instances")
    
    def test_git_manager_memory_usage(self):
        """Test Git manager memory usage."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        # Create multiple Git managers and perform operations
        managers = []
        for _ in range(5):
            manager = GitManager()
            managers.append(manager)
            
            # Perform memory-intensive operations
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="output" * 1000, stderr="")
                manager.check_git_available()
        
        peak_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = peak_memory - initial_memory
        
        assert memory_increase < 30, f"Git manager memory increase {memory_increase:.1f}MB, expected <30MB"
        
        print(f"Git manager memory usage: {memory_increase:.1f}MB for 5 instances")
    
    def test_process_manager_memory_scaling(self):
        """Test process manager memory scaling with multiple processes."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        process_manager = ProcessManager()
        
        # Mock multiple processes
        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process
            
            # Start many processes
            for i in range(50):
                process_manager.start_process(
                    f"test_process_{i}",
                    ["python", "-c", "print('test')"]
                )
        
        peak_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = peak_memory - initial_memory
        
        # Memory should scale reasonably with process count
        assert memory_increase < 100, f"Process manager memory increase {memory_increase:.1f}MB, expected <100MB"
        
        print(f"Process manager memory scaling: {memory_increase:.1f}MB for 50 processes")


@pytest.mark.performance
class TestStartupPerformance:
    """Startup performance tests."""
    
    def test_application_startup_time(self):
        """Test application startup time."""
        start_time = time.time()
        
        # Import and initialize main components
        from main_interface import MainInterface
        
        # Mock tkinter to avoid GUI creation
        with patch('tkinter.Tk'):
            with patch('tkinter.ttk.Style'):
                interface = MainInterface()
        
        end_time = time.time()
        startup_time = end_time - start_time
        
        # Startup should be fast
        assert startup_time < 5.0, f"Application startup took {startup_time:.2f}s, expected <5.0s"
        
        print(f"Application startup time: {startup_time:.3f}s")
    
    def test_component_initialization_time(self):
        """Test individual component initialization times."""
        components = [
            ('BrainDriveInstaller', BrainDriveInstaller),
            ('GitManager', GitManager),
            ('NodeManager', NodeManager),
            ('ProcessManager', ProcessManager)
        ]
        
        for name, component_class in components:
            start_time = time.time()
            
            # Initialize component
            component = component_class()
            
            end_time = time.time()
            init_time = end_time - start_time
            
            # Each component should initialize quickly
            assert init_time < 1.0, f"{name} initialization took {init_time:.3f}s, expected <1.0s"
            
            print(f"{name} initialization: {init_time:.3f}s")


@pytest.mark.performance
class TestScalabilityPerformance:
    """Scalability performance tests."""
    
    def test_concurrent_operations_performance(self):
        """Test performance with concurrent operations."""
        import concurrent.futures
        
        def create_installer():
            installer = BrainDriveInstaller()
            # Mock a quick operation
            with patch.object(installer, 'check_requirements', return_value=True):
                return installer.check_requirements()
        
        start_time = time.time()
        
        # Run concurrent operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_installer) for _ in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # All operations should succeed
        assert all(results)
        
        # Concurrent operations should be reasonably fast
        assert total_time < 10.0, f"Concurrent operations took {total_time:.2f}s, expected <10.0s"
        
        print(f"Concurrent operations: {total_time:.3f}s for 10 operations")
    
    def test_large_plugin_set_performance(self, temp_dir):
        """Test performance with large number of plugins."""
        plugins_dir = os.path.join(temp_dir, "plugins")
        os.makedirs(plugins_dir)
        
        # Create many mock plugins
        plugin_count = 50
        for i in range(plugin_count):
            plugin_dir = os.path.join(plugins_dir, f"plugin-{i:03d}")
            os.makedirs(plugin_dir)
            
            with open(os.path.join(plugin_dir, "package.json"), "w") as f:
                f.write(f'{{"name": "plugin-{i:03d}", "scripts": {{"build": "echo building"}}}}')
        
        plugin_builder = PluginBuilder(plugins_dir)
        
        start_time = time.time()
        
        # Discover plugins
        plugins = plugin_builder.discover_plugins()
        
        end_time = time.time()
        discovery_time = end_time - start_time
        
        assert len(plugins) == plugin_count
        assert discovery_time < 5.0, f"Plugin discovery took {discovery_time:.2f}s for {plugin_count} plugins, expected <5.0s"
        
        print(f"Plugin discovery: {discovery_time:.3f}s for {plugin_count} plugins")


def generate_performance_report(test_results):
    """Generate performance test report."""
    report = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'system_info': {
            'cpu_count': psutil.cpu_count(),
            'memory_total_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024,
            'python_version': sys.version
        },
        'test_results': test_results,
        'performance_targets': {
            'installation_time_max_seconds': 900,  # 15 minutes
            'memory_usage_max_mb': 200,
            'startup_time_max_seconds': 30,
            'executable_size_max_mb': 100
        }
    }
    
    return report


if __name__ == "__main__":
    # Run performance tests and generate report
    pytest.main([__file__, "-v", "--tb=short"])