"""BrainDrive Installer auto-updater package entry point."""

from __future__ import annotations

import atexit
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

log = logging.getLogger(__name__)

_TEMP_DIR = getattr(sys, "_MEIPASS", None)

if _TEMP_DIR:
    @atexit.register
    def _cleanup_meipass() -> None:
        temp_path = Path(_TEMP_DIR)
        for _ in range(5):
            try:
                shutil.rmtree(temp_path, ignore_errors=True)
                log.debug("Cleaned temporary directory %s", temp_path)
                break
            except Exception as exc:  # pragma: no cover - best-effort cleanup
                log.warning("Failed to remove temporary directory %s: %s", temp_path, exc)
                time.sleep(1)


class InstallerAutoUpdater:
    """Checks GitHub releases for a newer installer and launches it."""

    DEFAULT_BASE_ENV = "BRAINDRIVE_INSTALLER_HOME"
    DEFAULT_REPO_URL = "https://github.com/BrainDriveAI/BrainDrive-Install-System"

    ASSET_NAMES = {
        "win32": ["BrainDriveInstaller-win-x64.exe", "BrainDriveInstaller.exe", "OpenWebUIInstaller.exe"],
        "darwin": ["BrainDriveInstaller-macos-universal.dmg", "BrainDriveInstaller.dmg"],
        "linux": ["BrainDriveInstaller-linux-x86_64.AppImage", "BrainDriveInstaller.AppImage"],
    }

    def __init__(self, base_path: Optional[Path] = None) -> None:
        self.base_path = Path(base_path or self._default_base_path()).expanduser()
        self.base_path.mkdir(parents=True, exist_ok=True)

        self.config_path = self.base_path / "config.json"
        self.repo_url = os.environ.get("BRAINDRIVE_INSTALLER_REPO", self.DEFAULT_REPO_URL)
        self.release_url = os.environ.get(
            "BRAINDRIVE_INSTALLER_RELEASES",
            f"https://api.github.com/repos/{'/'.join(self.repo_url.split('/')[-2:])}/releases/latest",
        )

        self.binary_name = self._default_binary_name()
        self.binary_path = self.base_path / self.binary_name
        self.current_version: Optional[str] = None
        self.asset_override: Optional[str] = None

        self.load_config()

    # ------------------------------------------------------------------
    def _default_base_path(self) -> Path:
        env_override = os.environ.get(self.DEFAULT_BASE_ENV)
        if env_override:
            return Path(env_override)
        exe_path = Path(sys.argv[0]).resolve()
        exe_dir = exe_path.parent
        if exe_dir.exists():
            return exe_dir
        return Path.home() / "BrainDriveInstaller" / "updater"

    def _default_binary_name(self) -> str:
        platform = sys.platform
        if platform.startswith("win"):
            return "BrainDriveInstaller-win-x64.exe"
        if platform == "darwin":
            return "BrainDriveInstaller-macos-universal.dmg"
        return "BrainDriveInstaller-linux-x86_64.AppImage"

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------
    def load_config(self) -> None:
        if not self.config_path.exists():
            self._write_config(
                {
                    "install_dir": str(self.base_path),
                    "binary_name": self.binary_name,
                    "current_version": None,
                    "last_checked": None,
                    "asset_name": None,
                }
            )

        data = json.loads(self.config_path.read_text(encoding="utf-8"))
        install_dir = Path(data.get("install_dir", self.base_path))
        self.base_path = install_dir.expanduser()
        self.base_path.mkdir(parents=True, exist_ok=True)

        self.binary_name = data.get("binary_name", self.binary_name)
        self.binary_path = self.base_path / self.binary_name
        self.current_version = data.get("current_version")
        self.asset_override = data.get("asset_name")

    def _write_config(self, data: dict) -> None:
        self.config_path.write_text(json.dumps(data, indent=4), encoding="utf-8")

    def save_config(self, **updates: object) -> None:
        data = json.loads(self.config_path.read_text(encoding="utf-8"))
        data.update(updates)
        self._write_config(data)

    # ------------------------------------------------------------------
    # Release handling
    # ------------------------------------------------------------------
    def get_latest_release(self) -> Optional[dict]:
        try:
            response = requests.get(self.release_url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            log.error("Unable to query release metadata: %s", exc)
            return None

    def _candidate_asset_names(self) -> list[str]:
        platform_key = sys.platform
        candidates = self.ASSET_NAMES.get(platform_key, self.ASSET_NAMES.get("linux", []))
        if self.asset_override:
            return [self.asset_override, *[name for name in candidates if name != self.asset_override]]
        return candidates

    def _select_download_url(self, release: dict) -> Optional[str]:
        candidates = self._candidate_asset_names()
        assets = release.get("assets", [])
        for candidate in candidates:
            for asset in assets:
                if asset.get("name") == candidate:
                    return asset.get("browser_download_url")
        log.error("No matching release asset found. Candidates: %s", ", ".join(candidates))
        return None

    def download_file(self, url: str, destination: Path) -> bool:
        log.info("Downloading %s", url)
        try:
            with requests.get(url, stream=True, timeout=60) as response:
                response.raise_for_status()
                with destination.open("wb") as target:
                    for chunk in response.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            target.write(chunk)
        except requests.RequestException as exc:
            log.error("Download failed: %s", exc)
            return False
        return True

    # ------------------------------------------------------------------
    # Update workflow
    # ------------------------------------------------------------------
    def verify_install(self) -> None:
        if not self.base_path.exists():
            self.base_path.mkdir(parents=True, exist_ok=True)
        if not self.binary_path.exists():
            shutil.copy2(Path(sys.argv[0]), self.binary_path)
            if not sys.platform.startswith("win"):
                try:
                    self.binary_path.chmod(self.binary_path.stat().st_mode | 0o111)
                except OSError as exc:
                    log.warning("Failed to set executable permissions on %s: %s", self.binary_path, exc)

    def check_and_update(self) -> None:
        release = self.get_latest_release()
        if not release:
            log.error("Update check failed. Please ensure you have network connectivity.")
            return

        latest_version = release.get("tag_name")
        download_url = self._select_download_url(release)
        if not download_url:
            return

        if self.current_version == latest_version and self.binary_path.exists():
            log.info("Installer already at latest version %s", latest_version)
            self.save_config(last_checked=datetime.now().isoformat())
            self.run_binary(self.binary_path)
            return

        log.info("Fetching installer version %s", latest_version)
        if self.download_file(download_url, self.binary_path):
            if not sys.platform.startswith("win"):
                try:
                    self.binary_path.chmod(self.binary_path.stat().st_mode | 0o111)
                except OSError as exc:
                    log.warning("Failed to set executable permissions on %s: %s", self.binary_path, exc)
            self.save_config(
                current_version=latest_version,
                last_checked=datetime.now().isoformat(),
                binary_name=self.binary_path.name,
            )
            self.run_binary(self.binary_path)
        else:
            log.error("Unable to download the installer. Update aborted.")

    def run_binary(self, binary: Path) -> None:
        if not binary.exists():
            log.error("Installer executable %s does not exist.", binary)
            return

        try:
            log.info("Launching %s", binary)
            if sys.platform == "darwin" and binary.suffix == ".dmg":
                subprocess.Popen(["open", str(binary)])
            else:
                subprocess.Popen([str(binary)], cwd=str(binary.parent))
        except Exception as exc:
            log.error("Failed to launch installer %s: %s", binary, exc)
        finally:
            if _TEMP_DIR:
                shutil.rmtree(_TEMP_DIR, ignore_errors=True)

    def main(self) -> None:
        self.verify_install()
        self.check_and_update()


def configure_logging(level: int = logging.INFO) -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def main() -> None:
    configure_logging()
    try:
        InstallerAutoUpdater().main()
    except Exception as exc:  # pragma: no cover - top-level guard
        log.error("Auto-updater encountered an error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
