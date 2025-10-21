import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from braindrive_installer.core.platform_utils import PlatformUtils


class InstallerState:
    """Persist installer-specific state such as the chosen install directory."""

    STATE_FILENAME = "installer_state.json"
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
            if ensure:
                state_dir.mkdir(parents=True, exist_ok=True)
            return state_dir

        os_type = PlatformUtils.get_os_type()

        if os_type == "windows":
            base = os.getenv("APPDATA")
            if not base:
                base = Path.home() / "AppData" / "Roaming"
            else:
                base = Path(base)
        elif os_type == "macos":
            base = Path.home() / "Library" / "Application Support"
        else:
            base = Path.home() / ".local" / "share"

        state_dir = base / "BrainDriveInstaller"

        if ensure:
            state_dir.mkdir(parents=True, exist_ok=True)

        return state_dir

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
