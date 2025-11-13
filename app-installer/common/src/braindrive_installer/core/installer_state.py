import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from braindrive_installer.core.platform_utils import PlatformUtils


class InstallerState:
    """Persist installer-specific state such as the chosen install directory."""

    STATE_FILENAME = "installer_state.json"
    SETTINGS_FILENAME = "braindrive_settings.json"
    STATE_KEY_INSTALL_PATH = "install_path"
    STATE_KEY_INSTALLER_DIR = "installer_dir"

    @classmethod
    def _get_state_dir(cls, ensure: bool = False) -> Path:
        """
        Resolve the directory where the installer should persist its state.

        Args:
            ensure: When True, create the directory if it does not exist.

        Returns:
            Path to the state directory.
        """
        override_dir = os.getenv("BRAINDRIVE_INSTALLER_STATE_DIR")
        if override_dir:
            state_dir = Path(override_dir)
            state_dir.mkdir(parents=True, exist_ok=True)
            return state_dir

        executable_dir = PlatformUtils.get_executable_directory()
        preferred_path = Path(PlatformUtils.get_installer_data_dir(executable_dir=executable_dir))
        preferred_path.mkdir(parents=True, exist_ok=True)

        legacy_dir = cls._get_legacy_state_dir()
        cls._migrate_legacy_state(preferred_path, legacy_dir)

        return preferred_path

    @classmethod
    def get_data_directory(cls, ensure: bool = False) -> str:
        """Return the directory currently used for installer data."""
        return str(cls._get_state_dir(ensure=ensure))

    @classmethod
    def _get_legacy_state_dir(cls) -> Path:
        """Location used by legacy builds (AppData/Application Support)."""
        os_type = PlatformUtils.get_os_type()
        if os_type == "windows":
            base = os.getenv("APPDATA")
            base_path = Path(base) if base else PlatformUtils.get_home_directory() / "AppData" / "Roaming"
        elif os_type == "macos":
            base_path = PlatformUtils.get_home_directory() / "Library" / "Application Support"
        else:
            base_path = PlatformUtils.get_home_directory() / ".local" / "share"
        return base_path / "BrainDriveInstaller"

    @classmethod
    def _migrate_legacy_state(cls, target_dir: Path, legacy_dir: Path) -> None:
        """Copy legacy AppData files into the new installer-scoped directory."""
        if not legacy_dir or not legacy_dir.exists():
            return
        try:
            if legacy_dir.resolve() == target_dir.resolve():
                return
        except OSError:
            pass

        files_to_migrate = [cls.STATE_FILENAME, cls.SETTINGS_FILENAME]
        migrated_any = False

        for filename in files_to_migrate:
            src = legacy_dir / filename
            dst = target_dir / filename
            if src.exists() and not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                migrated_any = True

        if not migrated_any:
            return

        for filename in files_to_migrate:
            src = legacy_dir / filename
            if src.exists():
                try:
                    src.unlink()
                except OSError:
                    pass

        try:
            legacy_dir.rmdir()
        except OSError:
            pass

    @classmethod
    def _get_state_file(cls) -> Path:
        """Return full path to the installer state file."""
        return cls._get_state_dir(ensure=False) / cls.STATE_FILENAME

    @classmethod
    def load_state(cls) -> Dict[str, Any]:
        """
        Load persisted installer state.

        Returns:
            Dictionary of saved state values. Empty dict if state file missing or invalid.
        """
        state_file = cls._get_state_file()

        if not state_file.exists():
            return {}

        try:
            with state_file.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            return {}

    @classmethod
    def save_state(cls, state: Dict[str, Any]) -> bool:
        """
        Persist installer state to disk.

        Args:
            state: State dictionary to persist.

        Returns:
            True when state is saved successfully, False otherwise.
        """
        state_file = cls._get_state_dir(ensure=True) / cls.STATE_FILENAME

        try:
            with state_file.open("w", encoding="utf-8") as fh:
                json.dump(state, fh, indent=2)
            return True
        except OSError:
            return False

    @classmethod
    def get_install_path(cls, current_installer_dir: Optional[str] = None) -> Optional[str]:
        """
        Fetch the persisted install path, if available.

        Returns:
            Install path string or None when missing.
        """
        state = cls.load_state()
        path = state.get(cls.STATE_KEY_INSTALL_PATH)
        recorded_installer_dir = state.get(cls.STATE_KEY_INSTALLER_DIR)

        if isinstance(path, str) and path.strip():
            normalized = os.path.abspath(path.strip())

            if current_installer_dir:
                current_installer_dir = os.path.abspath(current_installer_dir)
                if recorded_installer_dir:
                    recorded_installer_dir = os.path.abspath(recorded_installer_dir)
                    if os.path.normcase(recorded_installer_dir) != os.path.normcase(current_installer_dir):
                        return None
                else:
                    # Legacy state without installer_dir information.
                    # Only trust the saved path if it matches the current executable directory.
                    if os.path.normcase(normalized) != os.path.normcase(current_installer_dir):
                        return None

            temp_root = os.path.abspath(tempfile.gettempdir())
            try:
                under_temp = os.path.commonpath([normalized, temp_root]) == temp_root
            except ValueError:
                under_temp = False

            if under_temp and not os.path.isdir(normalized):
                return None
            return normalized
        return None

    @classmethod
    def set_install_path(cls, path: str) -> bool:
        """
        Persist the provided install path.

        Args:
            path: Filesystem path to save.

        Returns:
            True if the path was written, False otherwise.
        """
        if not path:
            return False

        normalized = os.path.abspath(path)
        current = cls.load_state()
        current[cls.STATE_KEY_INSTALL_PATH] = normalized
        current[cls.STATE_KEY_INSTALLER_DIR] = PlatformUtils.get_executable_directory()
        return cls.save_state(current)
