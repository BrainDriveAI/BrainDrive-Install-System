"""
Logging configuration for the BrainDrive Installer.
Provides both console and file logging for debugging installation issues.
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from braindrive_installer.core.platform_utils import PlatformUtils

class InstallerLogger:
    """Centralized logging for the BrainDrive Installer."""
    
    def __init__(self, log_dir=None):
        # Default log directory sits alongside the running executable/script.
        if log_dir is None:
            base_dir = Path(PlatformUtils.get_executable_directory())
            log_dir = base_dir / "logs"

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"braindrive_installer_{timestamp}.log"
        
        self.setup_logging()
    
    def setup_logging(self):
        """Configure logging with both file and console handlers."""
        # Create logger
        self.logger = logging.getLogger('BrainDriveInstaller')
        self.logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        simple_formatter = logging.Formatter('%(levelname)s: %(message)s')
        
        # File handler (detailed logging)
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler (simple logging)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        self.logger.addHandler(console_handler)
        
        # Log the start of logging
        self.logger.info(f"BrainDrive Installer logging started - Log file: {self.log_file}")
    
    def get_logger(self):
        """Get the configured logger instance."""
        return self.logger
    
    def log_system_info(self):
        """Log system information for debugging."""
        import platform
        import psutil
        
        self.logger.info("=== SYSTEM INFORMATION ===")
        self.logger.info(f"Platform: {platform.platform()}")
        self.logger.info(f"Python: {sys.version}")
        self.logger.info(f"Architecture: {platform.architecture()}")
        self.logger.info(f"CPU Count: {psutil.cpu_count()}")
        self.logger.info(f"Memory: {psutil.virtual_memory().total / (1024**3):.1f} GB")
        
        # Log current working directory
        self.logger.info(f"Current working directory: {os.getcwd()}")
        
        # Log environment variables (selected ones)
        env_vars = ['PATH', 'PYTHONPATH', 'CONDA_DEFAULT_ENV', 'VIRTUAL_ENV']
        for var in env_vars:
            value = os.environ.get(var, 'Not set')
            self.logger.info(f"Environment {var}: {value}")
        
        self.logger.info("=== END SYSTEM INFORMATION ===")

    def log_bundle_resources(self):
        """Best‑effort dump of where bundled data files live in a macOS app.

        Lists candidate directories for templates and whether env template files
        are present. Safe to call on any platform.
        """
        try:
            exe_dir = PlatformUtils.get_executable_directory()
            res_dir = os.path.normpath(os.path.join(exe_dir, '..', 'Resources'))
            fw_dir = os.path.normpath(os.path.join(exe_dir, '..', 'Frameworks'))

            candidates = [
                # Next to the executable
                os.path.join(exe_dir, 'braindrive_installer', 'templates'),
                os.path.join(exe_dir, 'templates'),
                # In the Resources subtree
                os.path.join(res_dir, 'braindrive_installer', 'templates'),
                os.path.join(res_dir, 'templates'),
                # Some builds put datas under Frameworks
                os.path.join(fw_dir, 'braindrive_installer', 'templates'),
                os.path.join(fw_dir, 'templates'),
            ]

            self.logger.info("=== BUNDLE DATA SEARCH ===")
            self.logger.info(f"Executable dir: {exe_dir}")
            self.logger.info(f"Resources dir:  {res_dir}")
            self.logger.info(f"Frameworks dir: {fw_dir}")

            target_files = [
                'backend_env_template.txt',
                'frontend_env_template.txt',
            ]

            for d in candidates:
                if os.path.isdir(d):
                    try:
                        entries = sorted(os.listdir(d))
                        present = [f for f in entries if f in target_files]
                        self.logger.info(f"FOUND dir: {d} | files: {present}")
                    except OSError as e:
                        self.logger.info(f"FOUND dir (unlistable): {d} | error: {e}")
                else:
                    self.logger.info(f"MISSING dir: {d}")

            # Also log specific paths we try at runtime
            for base in [exe_dir, res_dir, fw_dir]:
                for sub in ('braindrive_installer/templates', 'templates'):
                    for fname in target_files:
                        p = os.path.join(base, sub, fname)
                        self.logger.info(f"CHECK file: {p} | exists={os.path.isfile(p)}")

            self.logger.info("=== END BUNDLE DATA SEARCH ===")
        except Exception as e:
            self.logger.info(f"Bundle data probe skipped due to error: {e}")
    
    def log_exception(self, exc_info=None):
        """Log exception with full traceback."""
        self.logger.exception("Exception occurred:", exc_info=exc_info)
    
    def get_log_file_path(self):
        """Get the path to the current log file."""
        return str(self.log_file)

# Global logger instance
_installer_logger = None

def get_installer_logger():
    """Get the global installer logger instance."""
    global _installer_logger
    if _installer_logger is None:
        _installer_logger = InstallerLogger()
        _installer_logger.log_system_info()
        # Emit a one‑time bundle data report to help debug packaged paths
        _installer_logger.log_bundle_resources()
    return _installer_logger.get_logger()

def get_log_file_path():
    """Get the path to the current log file."""
    global _installer_logger
    if _installer_logger is None:
        _installer_logger = InstallerLogger()
    return _installer_logger.get_log_file_path()
