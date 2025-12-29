import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "app-installer" / "common" / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from braindrive_installer.core.platform_utils import PlatformUtils
from braindrive_installer.core.installer_state import InstallerState
from braindrive_installer.ui.settings_manager import BrainDriveSettingsManager
from braindrive_installer.utils.installer_bundle import sync_installer_bundle


@pytest.fixture(autouse=True)
def reset_override_env(monkeypatch):
    """Ensure custom override env vars don't leak between tests."""
    monkeypatch.delenv("BRAINDRIVE_INSTALLER_STATE_DIR", raising=False)
    return


def _mock_home(monkeypatch, path: Path):
    path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(PlatformUtils, "get_home_directory", lambda: path)


def _mock_os_type(monkeypatch, os_type: str):
    monkeypatch.setattr(PlatformUtils, "get_os_type", lambda: os_type)


def test_installer_data_dir_unique_per_executable_dir(monkeypatch, tmp_path):
    _mock_os_type(monkeypatch, "windows")
    _mock_home(monkeypatch, tmp_path / "home")

    exe_a = tmp_path / "distA"
    exe_b = tmp_path / "distB"
    exe_a.mkdir()
    exe_b.mkdir()

    path_a = Path(PlatformUtils.get_installer_data_dir(str(exe_a)))
    path_b = Path(PlatformUtils.get_installer_data_dir(str(exe_b)))

    assert path_a != path_b
    assert path_a.exists()
    assert path_b.exists()


def test_legacy_state_migrates_from_appdata(monkeypatch, tmp_path):
    _mock_os_type(monkeypatch, "windows")
    home = tmp_path / "home"
    _mock_home(monkeypatch, home)
    appdata_root = home / "AppData" / "Roaming"
    monkeypatch.setenv("APPDATA", str(appdata_root))

    exe_dir = tmp_path / "portable"
    exe_dir.mkdir()
    monkeypatch.setattr(PlatformUtils, "get_executable_directory", lambda: str(exe_dir))

    legacy_dir = appdata_root / "BrainDriveInstaller"
    legacy_dir.mkdir(parents=True)
    legacy_data = {"install_path": "C:/BrainDrive", "installer_dir": str(exe_dir)}
    (legacy_dir / InstallerState.STATE_FILENAME).write_text(json.dumps(legacy_data), encoding="utf-8")

    data_dir = Path(InstallerState.get_data_directory(ensure=True))

    migrated_file = data_dir / InstallerState.STATE_FILENAME
    assert migrated_file.exists()
    assert json.loads(migrated_file.read_text(encoding="utf-8")) == legacy_data
    assert not (legacy_dir / InstallerState.STATE_FILENAME).exists()


def test_settings_manager_uses_shared_data_dir(monkeypatch, tmp_path):
    _mock_os_type(monkeypatch, "windows")
    _mock_home(monkeypatch, tmp_path / "home")

    exe_dir = tmp_path / "portable-settings"
    exe_dir.mkdir()
    monkeypatch.setattr(PlatformUtils, "get_executable_directory", lambda: str(exe_dir))

    install_root = tmp_path / "install-root"
    install_root.mkdir()

    manager = BrainDriveSettingsManager(str(install_root))
    data_dir = Path(InstallerState.get_data_directory())

    assert Path(manager.settings_file).parent == data_dir


def test_sync_installer_bundle_copies_bundle_and_state(monkeypatch, tmp_path):
    _mock_os_type(monkeypatch, "windows")
    _mock_home(monkeypatch, tmp_path / "home")

    current_dir = tmp_path / "dist"
    current_dir.mkdir()
    (current_dir / "BrainDriveInstaller-win-x64.exe").write_text("exe", encoding="utf-8")
    monkeypatch.setattr(PlatformUtils, "get_executable_directory", lambda: str(current_dir))

    source_state_dir = Path(PlatformUtils.get_installer_data_dir(executable_dir=str(current_dir)))
    source_state_dir.mkdir(parents=True, exist_ok=True)
    state_data = {
        InstallerState.STATE_KEY_INSTALL_PATH: "C:/BrainDrive",
        InstallerState.STATE_KEY_INSTALLER_DIR: str(current_dir),
    }
    (source_state_dir / InstallerState.STATE_FILENAME).write_text(json.dumps(state_data), encoding="utf-8")
    (source_state_dir / InstallerState.SETTINGS_FILENAME).write_text("{}", encoding="utf-8")

    install_base = tmp_path / "install-root"
    install_base.mkdir()

    bundle_path = sync_installer_bundle(str(install_base))
    assert bundle_path
    bundle_dir = Path(bundle_path)
    assert bundle_dir == install_base.resolve()
    assert (bundle_dir / "BrainDriveInstaller-win-x64.exe").exists()

    target_state_dir = Path(PlatformUtils.get_installer_data_dir(executable_dir=str(bundle_dir)))
    state_file = target_state_dir / InstallerState.STATE_FILENAME
    assert state_file.exists()
    new_state = json.loads(state_file.read_text(encoding="utf-8"))
    assert new_state[InstallerState.STATE_KEY_INSTALL_PATH] == "C:/BrainDrive"
    assert new_state[InstallerState.STATE_KEY_INSTALLER_DIR] == str(bundle_dir)


def test_sync_installer_bundle_skips_non_allowlisted_entries(monkeypatch, tmp_path):
    _mock_os_type(monkeypatch, "windows")
    _mock_home(monkeypatch, tmp_path / "home")

    current_dir = tmp_path / "dist"
    current_dir.mkdir()
    (current_dir / "BrainDriveInstaller-win-x64.exe").write_text("exe", encoding="utf-8")
    (current_dir / "braindriveai.ico").write_text("ico", encoding="utf-8")
    installer_dir = current_dir / "BrainDriveInstaller"
    installer_dir.mkdir()
    (installer_dir / "payload.txt").write_text("payload", encoding="utf-8")
    logs_dir = current_dir / "logs"
    logs_dir.mkdir()
    (logs_dir / "log.txt").write_text("log", encoding="utf-8")

    (current_dir / "extra.txt").write_text("extra", encoding="utf-8")
    extra_dir = current_dir / "extra-dir"
    extra_dir.mkdir()
    (extra_dir / "extra.log").write_text("extra", encoding="utf-8")

    monkeypatch.setattr(PlatformUtils, "get_executable_directory", lambda: str(current_dir))

    install_base = tmp_path / "install-root"
    install_base.mkdir()

    bundle_path = sync_installer_bundle(str(install_base))
    assert bundle_path
    bundle_dir = Path(bundle_path)

    assert (bundle_dir / "BrainDriveInstaller-win-x64.exe").exists()
    assert (bundle_dir / "braindriveai.ico").exists()
    assert (bundle_dir / "BrainDriveInstaller" / "payload.txt").exists()
    assert (bundle_dir / "logs" / "log.txt").exists()

    assert not (bundle_dir / "extra.txt").exists()
    assert not (bundle_dir / "extra-dir").exists()
