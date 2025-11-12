import json
import os
import secrets
import tempfile
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from braindrive_installer.core.installer_state import InstallerState
from braindrive_installer.core.platform_utils import PlatformUtils
from braindrive_installer.core.installer_logger import get_installer_logger
from braindrive_installer.core.port_selector import (
    DEFAULT_PORT_PAIRS,
    select_available_port_pair,
)

class BrainDriveSettingsManager:
    """Manages BrainDrive configuration settings with JSON persistence and template generation."""
    
    def __init__(self, installation_path: str):
        self.installation_path = installation_path
        self.settings_file = os.path.join(installation_path, "braindrive_settings.json")
        # On macOS, avoid writing into the app bundle. Prefer Application Support.
        try:
            import sys
            from pathlib import Path
            abs_install = os.path.abspath(self.installation_path or "")
            if sys.platform == "darwin" and ".app/Contents/MacOS" in abs_install:
                app_support = os.path.join(Path.home(), "Library", "Application Support", "BrainDriveInstaller")
                os.makedirs(app_support, exist_ok=True)
                self.settings_file = os.path.join(app_support, "braindrive_settings.json")
        except Exception:
            # Best-effort fallback; keep original path
            pass
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
    
    def _choose_default_ports(self) -> Tuple[int, int]:
        """
        Detect the best default port pair using the preferred list.
        """
        try:
            backend_port, frontend_port = select_available_port_pair()
            return backend_port, frontend_port
        except Exception:
            # Fall back to the first configured pair if probing fails.
            return DEFAULT_PORT_PAIRS[0]

    def _get_default_settings(self) -> Dict[str, Any]:
        """Get default settings configuration"""
        backend_port, frontend_port = self._choose_default_ports()
        return {
            "version": "1.0.2",
            "last_modified": datetime.utcnow().isoformat() + "Z",
            "network": {
                "backend_host": "localhost",
                "backend_port": backend_port,
                "frontend_host": "localhost",
                "frontend_port": frontend_port
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
        except Exception as e:
            print(f"Error saving settings: {e}")
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
        """Regenerate .env files using our templates and current settings.

        Behavior:
        - Prefer generating from braindrive_installer/templates/* to incorporate user settings
        - Write backend/.env and backend/app/.env; write frontend/.env
        - If templates cannot be read (e.g., packaging issue), fall back to copying
          backend/.env-dev -> .env (+ app/.env) and frontend/.env.example -> .env
        """
        from pathlib import Path
        import importlib.resources as ir
        logger = get_installer_logger()

        def _load_template(name: str) -> tuple[str, str]:
            """Return (content, error). Try multiple locations robustly under PyInstaller."""
            candidates_tried = []
            # 1) importlib.resources from the package
            try:
                tpl_pkg = 'braindrive_installer.templates'
                path = ir.files(tpl_pkg).joinpath(name)
                # path may be a traversable object; get a filesystem path if possible
                if hasattr(path, 'is_file') and path.is_file():
                    content = path.read_text(encoding='utf-8')
                    if content:
                        return content, ''
                else:
                    fs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates', name))
                    candidates_tried.append(fs_path)
                    if os.path.isfile(fs_path):
                        with open(fs_path, 'r', encoding='utf-8') as f:
                            return f.read(), ''
            except Exception as e:
                candidates_tried.append(f"importlib.resources error: {e}")

            # 2) Relative to package root on filesystem
            try:
                from pathlib import Path as _P
                pkg_root = _P(__file__).resolve().parents[1]  # braindrive_installer/
                fs_path2 = str(pkg_root / 'templates' / name)
                candidates_tried.append(fs_path2)
                if os.path.isfile(fs_path2):
                    with open(fs_path2, 'r', encoding='utf-8') as f:
                        return f.read(), ''
            except Exception as e:
                candidates_tried.append(f"pkg_root error: {e}")

            # 3) PyInstaller resource locations for macOS app bundles
            try:
                exe_dir = PlatformUtils.get_executable_directory()
                if exe_dir:
                    res_dir = os.path.normpath(os.path.join(exe_dir, '..', 'Resources'))
                    for rel in [
                        os.path.join('braindrive_installer', 'templates', name),
                        os.path.join('templates', name),
                    ]:
                        p = os.path.join(res_dir, rel)
                        candidates_tried.append(p)
                        if os.path.exists(p):
                            # Handle previous packaging bug where a directory with the filename was created
                            if os.path.isdir(p):
                                nested = os.path.join(p, os.path.basename(p))
                                if os.path.isfile(nested):
                                    with open(nested, 'r', encoding='utf-8') as f:
                                        return f.read(), ''
                            elif os.path.isfile(p):
                                with open(p, 'r', encoding='utf-8') as f:
                                    return f.read(), ''
                    # Some bundlers keep datas alongside the executable under MacOS/
                    for rel in [
                        os.path.join('braindrive_installer', 'templates', name),
                        os.path.join('templates', name),
                    ]:
                        p = os.path.join(exe_dir, rel)
                        candidates_tried.append(p)
                        if os.path.exists(p):
                            if os.path.isdir(p):
                                nested = os.path.join(p, os.path.basename(p))
                                if os.path.isfile(nested):
                                    with open(nested, 'r', encoding='utf-8') as f:
                                        return f.read(), ''
                            elif os.path.isfile(p):
                                with open(p, 'r', encoding='utf-8') as f:
                                    return f.read(), ''
            except Exception as e:
                candidates_tried.append(f"resources error: {e}")

            # 4) PyInstaller MEIPASS search (onefile mode)
            try:
                import sys as _sys
                meipass = getattr(_sys, '_MEIPASS', '')
                if meipass:
                    for rel in [
                        os.path.join('braindrive_installer', 'templates', name),
                        os.path.join('templates', name),
                    ]:
                        p = os.path.join(meipass, rel)
                        candidates_tried.append(p)
                        if os.path.isfile(p):
                            with open(p, 'r', encoding='utf-8') as f:
                                return f.read(), ''
            except Exception as e:
                candidates_tried.append(f"MEIPASS error: {e}")

            return '', f"template {name} not found; tried: {candidates_tried}"

        try:
            install_path = Path(self.installation_path)
            logger.info(f"Regenerating env files at: {install_path}")
            backend_dir = install_path / 'backend'
            frontend_dir = install_path / 'frontend'

            backend_env = backend_dir / '.env'
            frontend_env = frontend_dir / '.env'

            variables = self._generate_template_variables()

            # Try templates first
            backend_tpl, backend_err = _load_template('backend_env_template.txt')
            frontend_tpl, frontend_err = _load_template('frontend_env_template.txt')
            wrote_backend = False
            wrote_frontend = False

            if backend_tpl:
                for k, v in variables.items():
                    backend_tpl = backend_tpl.replace(f'{{{k}}}', str(v))
                backend_dir.mkdir(parents=True, exist_ok=True)
                backend_env.write_text(backend_tpl, encoding='utf-8')
                wrote_backend = True
                logger.info(f"Created backend .env from template: {backend_env}")
            else:
                logger.warning(f"Backend template not used; {backend_err}. Falling back to repo examples/synthesis.")

            if frontend_tpl:
                for k, v in variables.items():
                    frontend_tpl = frontend_tpl.replace(f'{{{k}}}', str(v))
                frontend_dir.mkdir(parents=True, exist_ok=True)
                frontend_env.write_text(frontend_tpl, encoding='utf-8')
                wrote_frontend = True
                logger.info(f"Created frontend .env from template: {frontend_env}")
            else:
                logger.warning(f"Frontend template not used; {frontend_err}. Falling back to repo examples/synthesis.")

            # Fallback copy if templates missing/unreadable
            if not wrote_backend:
                backend_dev = backend_dir / '.env-dev'
                if backend_dev.exists():
                    backend_env.write_text(backend_dev.read_text(encoding='utf-8'), encoding='utf-8')
                    logger.info(f"Created backend .env by copying .env-dev: {backend_env}")
                else:
                    # Minimal synthesized backend env
                    logger.warning("backend/.env-dev not found; synthesizing backend .env from settings.")
                    backend_content = (
                        f"HOST=\"{variables['BACKEND_HOST']}\"\n"
                        f"PORT={variables['BACKEND_PORT']}\n"
                        f"LOG_LEVEL=\"{variables['LOG_LEVEL']}\"\n"
                        f"SECRET_KEY=\"{variables['SECRET_KEY']}\"\n"
                        f"ENCRYPTION_MASTER_KEY=\"{variables['ENCRYPTION_MASTER_KEY']}\"\n"
                    )
                    backend_env.write_text(backend_content, encoding='utf-8')
                    logger.info(f"Created backend .env by synthesizing from settings: {backend_env}")

            if not wrote_frontend:
                frontend_example = frontend_dir / '.env.example'
                if frontend_example.exists():
                    frontend_env.write_text(frontend_example.read_text(encoding='utf-8'), encoding='utf-8')
                    logger.info(f"Created frontend .env by copying .env.example: {frontend_env}")
                else:
                    logger.warning("frontend/.env.example not found; synthesizing frontend .env from settings.")
                    api = f"http://{variables['BACKEND_HOST']}:{variables['BACKEND_PORT']}"
                    frontend_content = (
                        f"VITE_API_URL={api}\n"
                        f"VITE_DEV_SERVER_PORT={variables['FRONTEND_PORT']}\n"
                        f"VITE_DEV_SERVER_HOST={variables['FRONTEND_HOST']}\n"
                    )
                    frontend_env.write_text(frontend_content, encoding='utf-8')
                    logger.info(f"Created frontend .env by synthesizing from settings: {frontend_env}")

            return True
        except Exception as e:
            logger.error(f"Error regenerating env files: {e}")
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
