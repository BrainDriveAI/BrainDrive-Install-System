import os
import shutil
import sys
from pathlib import Path

import requests
from braindrive_installer.config.AppConfig import AppConfig

# Optional Windows-only imports
IS_WINDOWS = sys.platform == "win32"
if IS_WINDOWS:
    import pythoncom  # type: ignore
    from win32com.shell import shell, shellcon  # type: ignore
    from win32com.client import Dispatch  # type: ignore


class AppDesktopIntegration:
    def __init__(self):
        """
        Initializes the DesktopIntegration class.
        Automatically fetches the base path from the existing AppConfig singleton.
        """
        # Importing here to avoid circular imports
        app_config = AppConfig()
        
        self.base_path = app_config.base_path

        # Platform-specific settings
        if IS_WINDOWS:
            # New unified updater binary and repo location
            self.exe_name = "BrainDriveInstallerUpdater-win-x64.exe"
            self.icon_name = "braindriveai.ico"
            self.desktop_path = shell.SHGetFolderPath(0, shellcon.CSIDL_DESKTOP, None, 0)
            self.shortcut_name = "BrainDrive.lnk"
            self.repo_url = (
                "https://github.com/BrainDriveAI/BrainDrive-Install-System/releases/latest/download/BrainDriveInstallerUpdater-win-x64.exe"
            )
        else:
            # macOS/Linux: no Windows updater exe or .lnk shortcuts
            self.exe_name = "InstallerAutoUpdater.exe"  # unused on non-Windows
            # Prefer PNG at runtime (bundled via PyInstaller datas)
            self.icon_name = "braindrive.png"
            self.desktop_path = os.path.expanduser("~/Desktop")
            # Use .app suffix so Finder treats the symlink as an application
            self.shortcut_name = "BrainDrive.app"
            self.repo_url = ""

        self.shortcut_path = os.path.join(self.desktop_path, self.shortcut_name)
        self.exe_path = os.path.join(self.base_path, self.exe_name)
        self.icon_path = os.path.join(self.base_path, self.icon_name)

    def verify_exe_exists(self):
        """
        Verifies if the required executable exists in the base path.
        If not, downloads it from the repository.
        """
        # Only relevant on Windows; macOS uses the bundled .app instead.
        if not IS_WINDOWS:
            return
        try:
            if not os.path.exists(self.exe_path):
                print("Executable not found. Downloading...")
                response = requests.get(self.repo_url, stream=True)
                if response.status_code == 200:
                    with open(self.exe_path, "wb") as exe_file:
                        shutil.copyfileobj(response.raw, exe_file)
                    print("Executable downloaded successfully.")
                else:
                    raise Exception(
                        f"Failed to download the executable. HTTP Code: {response.status_code}"
                    )
            else:
                print("Executable already exists.")
        except Exception as e:
            print(f"Error verifying executable: {e}")
            raise
    
    def check_desktop_icon_exists(self):
        """
        Checks if the desktop icon exists.
        :return: True if the desktop shortcut exists, False otherwise.
        """
        return os.path.exists(self.shortcut_path)
    
    def create_desktop_icon(self):
        """
        Creates a desktop shortcut to the InstallerAutoUpdater.exe with the correct icon.
        """
        # Windows-only functionality
        if not IS_WINDOWS:
            return
        try:
            if not os.path.exists(self.exe_path):
                raise FileNotFoundError(f"{self.exe_name} not found at {self.base_path}")
            if not os.path.exists(self.icon_path):
                self.setup_application_icon()

            shell_instance = Dispatch('WScript.Shell')
            shortcut = shell_instance.CreateShortCut(self.shortcut_path)
            shortcut.TargetPath = self.exe_path
            shortcut.WorkingDirectory = self.base_path
            shortcut.IconLocation = self.icon_path
            shortcut.save()

            print("Desktop shortcut created successfully.")
        except Exception as e:
            print(f"Failed to create desktop shortcut: {e}")
            raise

    def verify_and_update_icon(self):
        """
        Checks if the existing desktop shortcut points to the correct executable.
        If not, updates it to point to the correct executable.
        """
        # Windows: maintain legacy .lnk handling.
        if IS_WINDOWS:
            try:
                # Initialize COM library
                pythoncom.CoInitialize()

                shortcut_exists = os.path.exists(self.shortcut_path)
                if not shortcut_exists:
                    print("Shortcut does not exist. Creating a new one...")
                    self.create_desktop_icon()
                    return

                shell_instance = Dispatch('WScript.Shell')
                shortcut = shell_instance.CreateShortCut(self.shortcut_path)
                current_target = shortcut.TargetPath

                if current_target != self.exe_path:
                    print(
                        f"Incorrect shortcut target found: {current_target}. Updating shortcut..."
                    )
                    shortcut.TargetPath = self.exe_path
                    shortcut.IconLocation = self.icon_path
                    shortcut.save()
                    print("Shortcut updated successfully.")
                else:
                    print("Shortcut is already up-to-date.")
            except Exception as e:
                print(f"Error verifying or updating desktop shortcut: {e}")
                raise
            finally:
                # Uninitialize COM library
                pythoncom.CoUninitialize()
            return

        # macOS: create/update a Desktop symlink to the running .app bundle.
        if sys.platform == "darwin":
            try:
                self._ensure_macos_desktop_alias()
            except Exception as exc:
                # Best-effort only; do not fail the installer on macOS.
                print(f"Warning: could not create macOS desktop alias: {exc}")
            return

        # Other platforms: nothing to do.
        return


    def setup_application_icon(self):
        """
        Ensures the application icon exists in the base path.
        Copies it from the source directory if necessary and returns its path.
        """
        try:
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            source_icon_path = os.path.join(base_path, self.icon_name)

            # Copy the icon if it does not exist in the destination
            if not os.path.exists(self.icon_path):
                if os.path.exists(source_icon_path):
                    shutil.copy2(source_icon_path, self.icon_path)
                    print(f"Icon copied to {self.icon_path}")
                else:
                    # On macOS, the .icns might be embedded in the app bundle and not available here.
                    # Fall back silently; Tk will still use default app icon.
                    print(f"Icon not found at {source_icon_path}; using default app icon")
            else:
                print(f"Icon already exists at {self.icon_path}")

            return self.icon_path
        except Exception as e:
            print(f"Failed to set up application icon: {e}")
            # Do not raise on non-Windows; icon setup is best-effort
            if IS_WINDOWS:
                raise
            return self.icon_path

    # ------------------------
    # macOS helper functionality
    # ------------------------

    def _get_macos_app_bundle(self) -> Path:
        """
        Resolve the .app bundle for the running installer on macOS.

        Returns:
            Path to the .app bundle, or an empty Path if not running from a bundle.
        """
        if sys.platform != "darwin":
            return Path()

        exe = Path(sys.executable).resolve()
        # When frozen, sys.executable is .../BrainDriveInstaller.app/Contents/MacOS/BrainDriveInstaller
        try:
            parents = list(exe.parents)
        except Exception:
            return Path()

        for parent in parents:
            if parent.suffix == ".app" and parent.exists():
                return parent
        return Path()

    def _ensure_macos_desktop_alias(self) -> None:
        """
        Create or update a Desktop symlink that launches the BrainDrive Installer app.
        Intended to mirror the Windows desktop shortcut experience.
        """
        app_bundle = self._get_macos_app_bundle()
        if not app_bundle:
            # Running from source or non-bundled environment; skip alias creation.
            return

        desktop_dir = Path(self.desktop_path).expanduser()
        try:
            desktop_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            # If the Desktop directory cannot be created, bail out quietly.
            return

        alias_path = desktop_dir / self.shortcut_name
        target = app_bundle.resolve()

        if alias_path.exists() or alias_path.is_symlink():
            # If it's already a symlink pointing to the correct bundle, we're done.
            if alias_path.is_symlink():
                try:
                    if alias_path.resolve() == target:
                        return
                except Exception:
                    pass
            # Otherwise, avoid clobbering unexpected files/directories.
            if not alias_path.is_symlink():
                print(f"Desktop entry {alias_path} already exists and is not a symlink; skipping alias creation.")
                return
            try:
                alias_path.unlink()
            except Exception:
                return

        try:
            alias_path.symlink_to(target)
            print(f"Created macOS Desktop alias: {alias_path} -> {target}")
        except Exception as exc:
            print(f"Failed to create macOS Desktop alias at {alias_path}: {exc}")
