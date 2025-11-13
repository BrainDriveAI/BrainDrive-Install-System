"""
pytest configuration file for BrainDrive Installer test suite.
Provides common fixtures and test configuration.
"""

import pytest
import os
import sys
import tempfile
import shutil
from unittest.mock import Mock, MagicMock
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    if os.path.exists(temp_path):
        shutil.rmtree(temp_path)

@pytest.fixture
def mock_status_updater():
    """Create a mock status updater for testing."""
    mock = Mock()
    mock.update_status = Mock()
    mock.update_progress = Mock()
    mock.set_error = Mock()
    mock.set_success = Mock()
    return mock

@pytest.fixture
def mock_subprocess():
    """Create a mock subprocess for testing."""
    mock = Mock()
    mock.returncode = 0
    mock.stdout = ""
    mock.stderr = ""
    mock.communicate = Mock(return_value=("", ""))
    return mock

@pytest.fixture
def sample_package_json():
    """Sample package.json content for testing."""
    return {
        "name": "test-plugin",
        "version": "1.0.3",
        "scripts": {
            "build": "npm run build:prod",
            "build:prod": "webpack --mode production"
        },
        "dependencies": {
            "react": "^18.0.0"
        }
    }

@pytest.fixture
def sample_env_template():
    """Sample environment template for testing."""
    return """
# Test Environment Template
APP_NAME="{APP_NAME}"
PORT={PORT}
SECRET_KEY="{SECRET_KEY}"
DEBUG={DEBUG}
"""

@pytest.fixture
def mock_git_repo():
    """Create a mock git repository structure."""
    def _create_mock_repo(base_path):
        repo_path = os.path.join(base_path, "test_repo")
        os.makedirs(repo_path, exist_ok=True)
        
        # Create .git directory
        git_path = os.path.join(repo_path, ".git")
        os.makedirs(git_path, exist_ok=True)
        
        # Create basic files
        with open(os.path.join(repo_path, "README.md"), "w") as f:
            f.write("# Test Repository")
        
        # Create backend and frontend directories
        backend_path = os.path.join(repo_path, "backend")
        frontend_path = os.path.join(repo_path, "frontend")
        os.makedirs(backend_path, exist_ok=True)
        os.makedirs(frontend_path, exist_ok=True)
        
        # Create requirements.txt
        with open(os.path.join(backend_path, "requirements.txt"), "w") as f:
            f.write("fastapi==0.104.1\nuvicorn==0.24.0\n")
        
        # Create package.json
        with open(os.path.join(frontend_path, "package.json"), "w") as f:
            f.write('{"name": "test-frontend", "version": "1.0.3"}')
        
        return repo_path
    
    return _create_mock_repo

# Test configuration
pytest_plugins = []

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "platform: mark test as a platform-specific test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file location."""
    for item in items:
        # Add markers based on test file location
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
        elif "platform" in str(item.fspath):
            item.add_marker(pytest.mark.platform)
