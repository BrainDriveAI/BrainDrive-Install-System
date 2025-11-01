
import os
import shutil
import sys
import platform
import threading
import tkinter as tk
from tkinter import ttk
from braindrive_installer.ui.card_ollama import Ollama
from braindrive_installer.ui.card_braindrive import BrainDrive

from braindrive_installer.ui.status_display import StatusDisplay
from braindrive_installer.ui.status_updater import StatusUpdater
from braindrive_installer.ui.theme import Theme
from braindrive_installer.config.AppConfig import AppConfig
from braindrive_installer.utils.helper_image import HelperImage
from braindrive_installer.integration.AppDesktopIntegration import AppDesktopIntegration
from braindrive_installer.core.installer_logger import get_installer_logger, get_log_file_path
from pathlib import Path

# Update check deps
import json
import time
import requests
from packaging.version import Version

try:
    import importlib.resources as pkg_resources  # Python 3.9+
except Exception:  # pragma: no cover - fallback for older
    pkg_resources = None

def main():
    # Initialize logging first
    logger = get_installer_logger()
    logger.info("Starting BrainDrive Installer application")
    
    # Create the main window
    root = tk.Tk()
    root.title("BrainDrive Installer [v1.0.1]")
    Theme.apply(root)
    config = AppConfig()

    try:
        desktop_integration = AppDesktopIntegration()
        icon_path = desktop_integration.setup_application_icon()

        # On Windows, Tk expects .ico; on macOS use iconphoto with PNG
        if platform.system() == "Windows":
            try:
                root.iconbitmap(icon_path)
            except Exception:
                pass
        else:
            try:
                # Prefer PNG from assets for mac/Linux
                from braindrive_installer.utils.helper_image import HelperImage
                png_path = HelperImage.get_image_path("braindrive.png")
                photo = tk.PhotoImage(file=png_path)
                root.iconphoto(True, photo)
            except Exception:
                pass

        def background_task():
            try:
                desktop_integration.verify_exe_exists()
                desktop_integration.verify_and_update_icon()
            except Exception:
                pass

        threading.Thread(target=background_task, daemon=True).start()

    except Exception as e:
        logger.error(f"Failed to set application icon: {e}")
        print(f"Failed to set application icon: {e}")

 
    root.geometry("800x600")
    root.resizable(False, False)

    # Detect the OS and set the label text accordingly
    os_name = platform.system()
    if os_name == "Windows":
        version = platform.version()  # Example: '10.0.22000'
        major, minor, build = map(int, version.split('.'))
        if major == 10 and build >= 22000:
            os_text = "Using Windows 11"
        else:
            os_text = f"Using Windows {platform.release()}"
    elif os_name == "Darwin":
        os_text = "Using macOS"
    else:
        os_text = f"Using {os_name}"

    # Top section
    if Theme.active:
        top_frame = tk.Frame(root, height=90, bg=Theme.header_bg)
    else:
        top_frame = tk.Frame(root, height=80, bg="lightgrey")
    top_frame.pack(fill=tk.X)

    title_kwargs = {"text": "AI System Installer by BrainDrive.ai", "font": ("Arial", 24)}
    if Theme.active:
        title_kwargs.update(bg=Theme.header_bg, fg=Theme.text)
    else:
        title_kwargs.update(bg="lightgrey")
    title_label = tk.Label(top_frame, **title_kwargs)
    title_label.place(relx=0.5, rely=0.45, anchor="center")

    # New label for "Using Windows 10"
    os_label_kwargs = {"text": os_text, "font": ("Arial", 10)}
    if Theme.active:
        os_label_kwargs.update(bg=Theme.header_bg, fg=Theme.muted)
    else:
        os_label_kwargs.update(bg="lightgrey")
    os_label = tk.Label(top_frame, **os_label_kwargs)
    os_label.place(relx=0.5, rely=0.8, anchor="center")

    # Prepare an Update button (initially hidden); shown only if newer installer exists
    update_button = ttk.Button(top_frame, text="Update Available", command=lambda: _launch_updater_and_quit(root))
    # We'll place it on the top-right when needed

    # Create card instances
    ollama_instance = Ollama()
    braindrive_instance = BrainDrive()

    # Middle section
    middle_kwargs = {"height": 340, "width": 600}
    if Theme.active:
        middle_kwargs.update(bg=Theme.bg)
    middle_frame = tk.Frame(root, **middle_kwargs)
    middle_frame.pack(fill=tk.BOTH, expand=True)

    # Left group
    left_kwargs = {"width": 400, "height": 320, "relief": tk.RIDGE, "bd": 2}
    if Theme.active:
        left_kwargs.update(bg=Theme.bg)
    left_group = tk.Frame(middle_frame, **left_kwargs)
    left_group.pack_propagate(False)
    left_group.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Right group
    right_kwargs = {"width": 400, "height": 320, "relief": tk.RIDGE, "bd": 2}
    if Theme.active:
        right_kwargs.update(bg=Theme.bg)
    right_group = tk.Frame(middle_frame, **right_kwargs)
    right_group.pack_propagate(False)
    right_group.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)


    # Bottom status section
    status_display = StatusDisplay(root)
    step_label, details_label, progress_bar = status_display.get_components()
    status_updater = StatusUpdater(step_label, details_label, progress_bar)
    config.status_display = status_display
    # Display cards with status_updater
    braindrive_instance.display(left_group, status_updater)
    ollama_instance.display(right_group, status_updater)

    # Setup cleanup handler for proper shutdown
    def cleanup_on_exit():
        """Clean up all running processes when the application exits."""
        logger.info("Cleaning up running processes before exit...")
        try:
            # Stop BrainDrive services if running
            if hasattr(braindrive_instance, 'braindrive_installer'):
                logger.info("Stopping BrainDrive services...")
                braindrive_instance.braindrive_installer.stop_services()
                logger.info("BrainDrive services stopped")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        logger.info("Cleanup completed")

    # Register cleanup handler for window close event
    root.protocol("WM_DELETE_WINDOW", lambda: (cleanup_on_exit(), root.destroy()))

    # Add log file info to status display
    log_file_path = get_log_file_path()
    logger.info(f"Log file location: {log_file_path}")
    
    # Background: check for updates and toggle button visibility
    def _toggle_update_if_available():
        try:
            current = _get_current_installer_version()
            latest = _get_latest_release_version()
            if latest and current:
                try:
                    if Version(_normalize_version(latest)) > Version(_normalize_version(current)):
                        # Show button on UI thread
                        root.after(0, lambda: update_button.place(relx=0.95, rely=0.2, anchor="ne"))
                except Exception:
                    pass
        except Exception:
            pass

    threading.Thread(target=_toggle_update_if_available, daemon=True).start()

    # Run the main loop
    logger.info("Starting main GUI loop")
    try:
        root.mainloop()
    except Exception as e:
        logger.exception("Error in main GUI loop")
        raise
    finally:
        logger.info("BrainDrive Installer application shutting down")
        cleanup_on_exit()


if __name__ == "__main__":
    main()


# -----------------------
# Update helper functions
# -----------------------

def _normalize_version(ver: str) -> str:
    if ver.lower().startswith("v"):
        return ver[1:]
    return ver


def _get_current_installer_version() -> str:
    """Read current version from bundled VERSION file or platform metadata."""
    # Try packaged VERSION file within braindrive_installer package
    try:
        if pkg_resources is not None:
            try:
                text = (pkg_resources.files("braindrive_installer") / "VERSION").read_text(encoding="utf-8")
                v = (text or "").strip()
                if v:
                    return v
            except Exception:
                pass
    except Exception:
        pass

    # macOS fallback: read from Info.plist
    try:
        if sys.platform == "darwin":
            exe = Path(sys.executable)
            app_root = exe
            # If frozen, sys.executable inside app bundle: <.app>/Contents/MacOS/BrainDriveInstaller
            if getattr(sys, "frozen", False):
                info_plist = exe.parent.parent / "Info.plist"
                if info_plist.exists():
                    import plistlib
                    with info_plist.open("rb") as f:
                        info = plistlib.load(f)
                    v = info.get("CFBundleShortVersionString") or info.get("CFBundleVersion")
                    if v:
                        return str(v)
    except Exception:
        pass

    # Windows: as a simple cross-platform fallback, return default embedded string
    return "1.0.1"


def _get_latest_release_version() -> str:
    url = os.environ.get("BRAINDRIVE_INSTALLER_RELEASES")
    if not url:
        repo = os.environ.get("BRAINDRIVE_INSTALLER_REPO", "https://github.com/DJJones66/BrainDrive-Install-System")
        parts = repo.rstrip("/").split("/")
        owner_repo = "/".join(parts[-2:]) if len(parts) >= 2 else "DJJones66/BrainDrive-Install-System"
        url = f"https://api.github.com/repos/{owner_repo}/releases/latest"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return str(data.get("tag_name") or "")
    except Exception:
        return ""


def _launch_updater_and_quit(root: tk.Tk) -> None:
    """Locate and launch the platform updater; then quit the installer."""
    try:
        if sys.platform == "win32":
            _launch_windows_updater()
        elif sys.platform == "darwin":
            _launch_macos_updater()
        else:
            _launch_linux_updater()
    except Exception:
        pass
    finally:
        try:
            root.after(100, root.destroy)
        except Exception:
            pass


def _launch_windows_updater() -> None:
    candidates = [
        Path.home() / "BrainDriveInstaller" / "updater" / "BrainDriveInstallerUpdater-win-x64.exe",
        Path(os.getcwd()) / "BrainDriveInstallerUpdater-win-x64.exe",
    ]
    exe = next((p for p in candidates if p.exists()), None)
    if exe:
        try:
            import subprocess
            subprocess.Popen([str(exe)], cwd=str(exe.parent))
            return
        except Exception:
            pass
    # Fallback: open releases page for manual download
    _open_releases_page()


def _launch_macos_updater() -> None:
    candidates = [
        Path("/Applications/BrainDriveInstallerUpdater.app"),
        Path.home() / "Applications" / "BrainDriveInstallerUpdater.app",
        Path.home() / "BrainDriveInstaller" / "updater" / "BrainDriveInstallerUpdater.app",
    ]
    app = next((p for p in candidates if p.exists()), None)
    try:
        import subprocess
        if app and app.exists():
            subprocess.Popen(["open", "-n", str(app)])
            return
    except Exception:
        pass
    _open_releases_page()


def _launch_linux_updater() -> None:
    candidates = [
        Path.home() / "BrainDriveInstaller" / "updater" / "BrainDriveInstallerUpdater.AppImage",
    ]
    app = next((p for p in candidates if p.exists()), None)
    if app:
        try:
            import subprocess
            app.chmod(app.stat().st_mode | 0o111)
            subprocess.Popen([str(app)], cwd=str(app.parent))
            return
        except Exception:
            pass
    _open_releases_page()


def _open_releases_page() -> None:
    repo = os.environ.get("BRAINDRIVE_INSTALLER_REPO", "https://github.com/DJJones66/BrainDrive-Install-System")
    url = repo.rstrip("/") + "/releases/latest"
    try:
        import webbrowser
        webbrowser.open(url)
    except Exception:
        pass
