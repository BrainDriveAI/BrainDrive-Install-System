import json
import os
import secrets
import tempfile
from datetime import datetime
from typing import Dict, Any, List, Optional

from braindrive_installer.core.installer_state import InstallerState
from braindrive_installer.core.platform_utils import PlatformUtils

class BrainDriveSettingsManager:
    """Manages BrainDrive configuration settings with JSON persistence and template generation."""
    
    def __init__(self, installation_path: str):
        self.installation_path = installation_path
        self.settings_file = os.path.join(installation_path, "braindrive_settings.json")
        self.backend_env_file = os.path.join(installation_path, "backend", ".env")
        self.frontend_env_file = os.path.join(installation_path, "frontend", ".env")
        self.settings = self._load_settings()
    
    def _get_default_install_path(self) -> str:
        """Determine the default install path preference."""
        current_dir = PlatformUtils.get_executable_directory()
        saved_path = InstallerState.get_install_path(current_installer_dir=current_dir)
        if saved_path and isinstance(saved_path, str) and saved_path.strip():
            normalized_saved = os.path.abspath(saved_path.strip())
            if os.path.isdir(normalized_saved):
                return normalized_saved
            temp_root = os.path.abspath(tempfile.gettempdir())
            try:
                if os.path.commonpath([normalized_saved, temp_root]) != temp_root:
                    return normalized_saved
            except ValueError:
                return normalized_saved
        executable_dir = PlatformUtils.get_executable_directory()
        if executable_dir:
            return executable_dir
        return PlatformUtils.get_braindrive_base_path()
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """Get default settings configuration"""
        return {
            "version": "1.0.0",
            "last_modified": datetime.utcnow().isoformat() + "Z",
            "network": {
                "backend_host": "localhost",
                "backend_port": 8005,
                "frontend_host": "localhost",
                "frontend_port": 5173
            },
            "security": {
                "enable_registration": True,
                "enable_api_docs": True,
                "enable_metrics": False,
                "debug_mode": False
            },
            "performance": {
                "worker_count": 1,
                "max_upload_size_mb": 100,
                "enable_lazy_loading": True
            },
            "ui": {
                "default_theme": "light",
                "enable_pwa": True,
                "enable_analytics": False,
                "allow_theme_toggle": True
            },
            "advanced": {
                "custom_cors_origins": [],
                "database_path": "sqlite:///braindrive.db",
                "log_level": "info"
            },
            "installation": {
                "path": self._get_default_install_path()
            }
        }
    
    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from JSON file or create defaults"""
        settings_data = None
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                settings_data = None
        
        if not isinstance(settings_data, dict):
            settings_data = self._get_default_settings()
        
        settings_data.setdefault("installation", {})
        current_dir = PlatformUtils.get_executable_directory()
        persisted_path = InstallerState.get_install_path(current_installer_dir=current_dir)

        if persisted_path:
            install_path = settings_data["installation"].get("path") or persisted_path
        else:
            install_path = self._get_default_install_path()
        normalized_install = os.path.abspath(install_path)
        temp_root = os.path.abspath(tempfile.gettempdir())
        try:
            in_temp = os.path.commonpath([normalized_install, temp_root]) == temp_root
        except ValueError:
            in_temp = False

        if in_temp:
            normalized_install = os.path.abspath(self._get_default_install_path())

        settings_data["installation"]["path"] = normalized_install
        
        return settings_data
    
    def save_settings(self) -> bool:
        """Save current settings to JSON file"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            
            self.settings["last_modified"] = datetime.utcnow().isoformat() + "Z"
            installation_path = self.settings.setdefault("installation", {}).get("path", "").strip()
            if installation_path:
                normalized_install_path = os.path.abspath(installation_path)
                self.settings["installation"]["path"] = normalized_install_path
                InstallerState.set_install_path(normalized_install_path)
            else:
                # Ensure we persist at least the default path if field empty
                default_path = self._get_default_install_path()
                self.settings["installation"]["path"] = default_path
                InstallerState.set_install_path(default_path)
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
            return True
        except IOError:
            return False
    
    def update_setting(self, category: str, key: str, value: Any) -> bool:
        """Update a specific setting"""
        if category not in self.settings or not isinstance(self.settings[category], dict):
            self.settings[category] = {}
        self.settings[category][key] = value
        return True
    
    def get_setting(self, category: str, key: str, default=None):
        """Get a specific setting value"""
        return self.settings.get(category, {}).get(key, default)
    
    def validate_settings(self) -> List[str]:
        """Validate current settings and return list of issues"""
        issues = []
        
        # Validate ports
        backend_port = self.get_setting("network", "backend_port")
        frontend_port = self.get_setting("network", "frontend_port")
        
        if not isinstance(backend_port, int) or not (1024 <= backend_port <= 65535):
            issues.append("Backend port must be between 1024-65535")
        if not isinstance(frontend_port, int) or not (1024 <= frontend_port <= 65535):
            issues.append("Frontend port must be between 1024-65535")
        if backend_port == frontend_port:
            issues.append("Backend and frontend ports cannot be the same")
        
        # Validate hosts
        backend_host = self.get_setting("network", "backend_host")
        frontend_host = self.get_setting("network", "frontend_host")
        
        if not backend_host or not isinstance(backend_host, str) or not backend_host.strip():
            issues.append("Backend host cannot be empty")
        if not frontend_host or not isinstance(frontend_host, str) or not frontend_host.strip():
            issues.append("Frontend host cannot be empty")
        for label, host_value in (("Backend", backend_host), ("Frontend", frontend_host)):
            if isinstance(host_value, str):
                if "://" in host_value:
                    issues.append(f"{label} host must be a hostname or IP, not a URL")
                if any(ch.isspace() for ch in host_value):
                    issues.append(f"{label} host cannot contain whitespace")
        
        # Validate performance settings
        worker_count = self.get_setting("performance", "worker_count")
        if not isinstance(worker_count, int) or worker_count < 1:
            issues.append("Worker count must be a positive integer")
        
        max_upload = self.get_setting("performance", "max_upload_size_mb")
        if not isinstance(max_upload, int) or max_upload < 1:
            issues.append("Max upload size must be a positive integer")

        install_path = self.get_setting("installation", "path", "")
        if not install_path or not isinstance(install_path, str):
            issues.append("Install path cannot be empty")
        elif not os.path.isabs(install_path):
            issues.append("Install path must be an absolute path")
        
        return issues
    
    def regenerate_env_files(self) -> bool:
        """Regenerate .env files from current settings and templates"""
        try:
            # Load templates
            backend_template_path = os.path.join(os.path.dirname(__file__), "templates", "backend_env_template.txt")
            frontend_template_path = os.path.join(os.path.dirname(__file__), "templates", "frontend_env_template.txt")
            
            # Generate template variables from settings
            variables = self._generate_template_variables()
            
            # Process backend template
            if os.path.exists(backend_template_path):
                with open(backend_template_path, 'r', encoding='utf-8') as f:
                    backend_content = f.read()
                
                for key, value in variables.items():
                    backend_content = backend_content.replace(f'{{{key}}}', str(value))
                
                # Ensure backend directory exists
                os.makedirs(os.path.dirname(self.backend_env_file), exist_ok=True)
                with open(self.backend_env_file, 'w', encoding='utf-8') as f:
                    f.write(backend_content)
            
            # Process frontend template
            if os.path.exists(frontend_template_path):
                with open(frontend_template_path, 'r', encoding='utf-8') as f:
                    frontend_content = f.read()
                
                for key, value in variables.items():
                    frontend_content = frontend_content.replace(f'{{{key}}}', str(value))
                
                # Ensure frontend directory exists
                os.makedirs(os.path.dirname(self.frontend_env_file), exist_ok=True)
                with open(self.frontend_env_file, 'w', encoding='utf-8') as f:
                    f.write(frontend_content)
            
            return True
        except Exception as e:
            print(f"Error regenerating env files: {e}")
            return False

    def _get_existing_env_value(self, env_path: str, key: str) -> Optional[str]:
        """Return an existing value from an env file, stripping surrounding quotes when present."""
        if not os.path.exists(env_path):
            return None

        try:
            with open(env_path, 'r', encoding='utf-8') as env_file:
                for line in env_file:
                    stripped = line.strip()
                    if not stripped or stripped.startswith('#') or '=' not in stripped:
                        continue

                    name, raw_value = stripped.split('=', 1)
                    if name.strip() != key:
                        continue

                    value = raw_value.strip()
                    if value.startswith('"') and value.endswith('"') and len(value) >= 2:
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'") and len(value) >= 2:
                        value = value[1:-1]
                    return value or None
        except OSError:
            return None

        return None
    
    def _generate_template_variables(self) -> Dict[str, str]:
        """Generate template variables from current settings"""
        
        # Generate CORS origins
        cors_origins = [
            f"http://{self.get_setting('network', 'frontend_host')}:{self.get_setting('network', 'frontend_port')}",
            f"http://127.0.0.1:{self.get_setting('network', 'frontend_port')}",
            f"http://localhost:{self.get_setting('network', 'frontend_port')}"
        ]
        cors_origins.extend(self.get_setting('advanced', 'custom_cors_origins', []))
        
        # Generate allowed hosts
        allowed_hosts = [
            self.get_setting('network', 'backend_host'),
            self.get_setting('network', 'frontend_host'),
            "localhost",
            "127.0.0.1"
        ]

        existing_secret_key = self._get_existing_env_value(self.backend_env_file, "SECRET_KEY")
        secret_key = existing_secret_key or secrets.token_urlsafe(32)

        existing_encryption_key = self._get_existing_env_value(self.backend_env_file, "ENCRYPTION_MASTER_KEY")
        if existing_encryption_key and len(existing_encryption_key) < 32:
            existing_encryption_key = None
        encryption_key = existing_encryption_key or secrets.token_urlsafe(48)
        
        return {
            'BACKEND_HOST': self.get_setting('network', 'backend_host'),
            'BACKEND_PORT': str(self.get_setting('network', 'backend_port')),
            'FRONTEND_HOST': self.get_setting('network', 'frontend_host'),
            'FRONTEND_PORT': str(self.get_setting('network', 'frontend_port')),
            'SECRET_KEY': secret_key,
            'ENCRYPTION_MASTER_KEY': encryption_key,
            'ENABLE_REGISTRATION': str(self.get_setting('security', 'enable_registration')).lower(),
            'ENABLE_API_DOCS': str(self.get_setting('security', 'enable_api_docs')).lower(),
            'ENABLE_METRICS': str(self.get_setting('security', 'enable_metrics')).lower(),
            'DEBUG_MODE': str(self.get_setting('security', 'debug_mode')).lower(),
            'ENABLE_PWA': str(self.get_setting('ui', 'enable_pwa')).lower(),
            'ENABLE_ANALYTICS': str(self.get_setting('ui', 'enable_analytics')).lower(),
            'DEFAULT_THEME': self.get_setting('ui', 'default_theme'),
            'WORKER_COUNT': str(self.get_setting('performance', 'worker_count')),
            'MAX_UPLOAD_SIZE': str(self.get_setting('performance', 'max_upload_size_mb') * 1000000),
            'DATABASE_PATH': self.get_setting('advanced', 'database_path'),
            'LOG_LEVEL': self.get_setting('advanced', 'log_level'),
            'CORS_ORIGINS': str(list(set(cors_origins))).replace("'", '"'),
            'ALLOWED_HOSTS': str(list(set(allowed_hosts))).replace("'", '"')
        }
    
    def load_from_env_files(self) -> bool:
        """Load settings from existing .env files (for migration)"""
        try:
            # Try to extract settings from existing env files
            if os.path.exists(self.backend_env_file):
                with open(self.backend_env_file, 'r', encoding='utf-8') as f:
                    backend_content = f.read()
                
                # Parse basic settings from backend env
                for line in backend_content.split('\n'):
                    if line.startswith('PORT='):
                        try:
                            port = int(line.split('=')[1])
                            self.update_setting('network', 'backend_port', port)
                        except (ValueError, IndexError):
                            pass
                    elif line.startswith('HOST='):
                        try:
                            host = line.split('=')[1].strip('"')
                            if host != "0.0.0.0":  # Don't use 0.0.0.0 as default
                                self.update_setting('network', 'backend_host', host)
                        except IndexError:
                            pass
            
            if os.path.exists(self.frontend_env_file):
                with open(self.frontend_env_file, 'r', encoding='utf-8') as f:
                    frontend_content = f.read()
                
                # Parse basic settings from frontend env
                for line in frontend_content.split('\n'):
                    if line.startswith('VITE_DEV_SERVER_PORT='):
                        try:
                            port = int(line.split('=')[1])
                            self.update_setting('network', 'frontend_port', port)
                        except (ValueError, IndexError):
                            pass
                    elif line.startswith('VITE_DEV_SERVER_HOST='):
                        try:
                            host = line.split('=')[1].strip()
                            self.update_setting('network', 'frontend_host', host)
                        except IndexError:
                            pass
            
            return True
        except Exception:
            return False
