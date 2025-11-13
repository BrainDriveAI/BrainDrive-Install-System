import json
import shutil
from pathlib import Path
from typing import Optional

from braindrive_installer.core.platform_utils import PlatformUtils
from braindrive_installer.core.installer_logger import get_installer_logger
from braindrive_installer.core.installer_state import InstallerState


_logger = get_installer_logger()


def _safe_copytree(src: Path, dst: Path) -> None:
    """Copy a directory tree, allowing the destination to exist."""
    shutil.copytree(src, dst, dirs_exist_ok=True)


def _sync_state_payload(current_dir: Path, target_dir: Path) -> None:
    """Copy installer state/settings to the new bundle directory."""
    try:
        source_state = Path(PlatformUtils.get_installer_data_dir(executable_dir=str(current_dir)))
        target_state = Path(PlatformUtils.get_installer_data_dir(executable_dir=str(target_dir)))
    except Exception as exc:
        _logger.warning(f"Unable to resolve installer data directories: {exc}")
        return

    if not source_state.exists():
        return

    try:
        _safe_copytree(source_state, target_state)
    except Exception as exc:
        _logger.warning(f"Failed to replicate installer state directory: {exc}")
        return

    state_file = target_state / InstallerState.STATE_FILENAME
    if state_file.exists():
        try:
            with state_file.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            data[InstallerState.STATE_KEY_INSTALLER_DIR] = str(target_dir)
            with state_file.open("w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
        except Exception as exc:
            _logger.warning(f"Failed to update installer_dir metadata: {exc}")


def sync_installer_bundle(target_base_path: str) -> Optional[str]:
    """
    Copy the currently running installer bundle into the provided installation directory.

    Returns:
        The absolute path to the synced bundle directory or None if skipped.
    """
    if not target_base_path:
        return None

    current_dir = Path(PlatformUtils.get_executable_directory()).resolve()
    target_dir = Path(target_base_path).resolve()

    try:
        if current_dir.samefile(target_dir):
            _logger.info("Installer bundle already resides in the install directory.")
            return str(target_dir)
    except FileNotFoundError:
        # samefile may fail if files are missing; fall back to path comparison
        if current_dir == target_dir:
            return str(target_dir)

    if str(target_dir).startswith(str(current_dir)):
        _logger.warning("Target installer bundle path is nested under the running executable; skipping copy.")
        return None

    target_dir.mkdir(parents=True, exist_ok=True)

    _logger.info(f"Copying installer bundle contents from {current_dir} to {target_dir}")
    try:
        for entry in current_dir.iterdir():
            destination = target_dir / entry.name
            if entry.is_dir():
                _safe_copytree(entry, destination)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(entry, destination)
    except Exception as exc:
        _logger.error(f"Failed to copy installer bundle contents: {exc}")
        return None

    _sync_state_payload(current_dir, target_dir)

    return str(target_dir)
