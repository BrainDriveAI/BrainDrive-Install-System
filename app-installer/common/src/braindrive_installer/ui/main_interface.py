
import os
import shutil
import sys
import platform
import threading
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from braindrive_installer.ui.card_ollama import Ollama
from braindrive_installer.ui.card_braindrive import BrainDrive

from braindrive_installer.ui.status_display import StatusDisplay
from braindrive_installer.ui.theme import Theme
from braindrive_installer.config.AppConfig import AppConfig
from braindrive_installer.integration.AppDesktopIntegration import AppDesktopIntegration
from braindrive_installer.core.installer_logger import get_installer_logger, get_log_file_path
from braindrive_installer.core.platform_utils import PlatformUtils
from pathlib import Path

# Shared reference so other UI components can reuse the exact same BrainDrive icon
HERO_ICON_IMAGE = None

# Update check deps
import json
import time
import requests
from packaging.version import Version

try:
    import importlib.resources as pkg_resources  # Python 3.9+
except Exception:  # pragma: no cover - fallback for older
    pkg_resources = None


def _resolve_asset_path(filename: str):
    """Return a path to the requested asset without writing into the install directory."""
    candidates = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        meipass_path = Path(meipass)
        candidates.append(meipass_path / filename)
        candidates.append(meipass_path / "assets" / filename)

    if pkg_resources is not None:
        try:
            asset = pkg_resources.files("braindrive_installer") / filename
            candidates.append(asset)
            candidates.append(pkg_resources.files("braindrive_installer") / "assets" / filename)
        except Exception:
            pass

    resolved_file = Path(__file__).resolve()
    base_common = resolved_file.parents[3]
    project_root = resolved_file.parents[4]
    candidates.append(base_common / "assets" / filename)
    candidates.append(project_root / "windows" / filename)
    candidates.append(project_root / "common" / "assets" / filename)

    for candidate in candidates:
        try:
            if candidate and Path(candidate).is_file():
                return str(candidate)
        except Exception:
            continue
    return None


def _ensure_executable_asset(filename: str):
    """Copy the given asset next to the running executable if it is not already present."""
    exe_dir = Path(PlatformUtils.get_executable_directory())
    dest = exe_dir / filename
    if dest.exists():
        return str(dest)

    source = _resolve_asset_path(filename)
    if not source:
        return None

    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        return str(dest)
    except Exception:
        logger = get_installer_logger()
        logger.warning(f"Failed to copy {filename} to executable directory: {source}")
        return source

def main():
    # Initialize logging first
    logger = get_installer_logger()
    logger.info("Starting BrainDrive Installer application")
    
    # Create the main window
    root = tk.Tk()
    braindrive_instance = BrainDrive()
    braindrive_installed = False
    try:
        braindrive_installed = braindrive_instance.braindrive_installer.check_installed()
    except Exception:
        braindrive_installed = False
    runner_name = "BrainDrive Manager" if braindrive_installed else "BrainDrive Installer"
    root.title(f"{runner_name} [v1.0.6]")
    Theme.apply(root)
    config = AppConfig()
    base_bg = Theme.bg if Theme.active else "lightgrey"
    root.configure(bg=base_bg)

    if braindrive_installed:
        try:
            desktop_integration = AppDesktopIntegration()
            icon_path = desktop_integration.setup_application_icon()

            if platform.system() == "Windows":
                local_icon = _ensure_executable_asset("braindriveai.ico") or icon_path
                if local_icon:
                    try:
                        root.iconbitmap(local_icon)
                    except Exception:
                        pass
            else:
                png_path = _ensure_executable_asset("braindrive.png") or _resolve_asset_path("braindrive.png")
                if png_path:
                    try:
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
    else:
        if platform.system() == "Windows":
            ico_path = (
                _ensure_executable_asset("braindriveai.ico")
                or _ensure_executable_asset("braindrive.ico")
                or _resolve_asset_path("braindriveai.ico")
                or _resolve_asset_path("braindrive.ico")
            )
            if ico_path:
                try:
                    root.iconbitmap(ico_path)
                except Exception:
                    pass
        else:
            png_path = _ensure_executable_asset("braindrive.png") or _resolve_asset_path("braindrive.png")
            if png_path:
                try:
                    photo = tk.PhotoImage(file=png_path)
                    root.iconphoto(True, photo)
                except Exception:
                    pass

 
    root.geometry("1220x720")
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

    disk_text = _format_disk_summary(config.base_path)
    version_text = f"Version: {_get_current_installer_version()}"

    ui_images = []

    def _load_image(filename: str, size=(48, 48)):
        path = _resolve_asset_path(filename)
        if not path:
            return None
        try:
            image = Image.open(path).convert("RGBA")
            image.thumbnail(size, Image.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            ui_images.append(photo)
            return photo
        except Exception:
            return None

    shell = tk.Frame(root, bg=base_bg)
    shell.pack(fill=tk.BOTH, expand=True)

    header_bg = Theme.header_bg if Theme.active else base_bg
    header = tk.Frame(shell, bg=header_bg, height=76)
    header.pack(fill=tk.X, side=tk.TOP)
    header.pack_propagate(False)

    hero_frame = tk.Frame(header, bg=header_bg)
    hero_frame.pack(side=tk.LEFT, padx=24)
    hero_icon = _load_image("braindrive.png", (48, 48))
    # Expose the hero icon so other UI components (e.g., the BrainDrive card)
    # can reuse the exact same image instance for visual consistency.
    global HERO_ICON_IMAGE
    HERO_ICON_IMAGE = hero_icon
    if hero_icon:
        tk.Label(hero_frame, image=hero_icon, bg=header_bg).pack(side=tk.LEFT, padx=(0, 12))
    title_block = tk.Frame(hero_frame, bg=header_bg)
    title_block.pack(side=tk.LEFT)
    title_text = tk.Label(
        title_block,
        text=runner_name,
        font=("Arial", 18, "bold"),
        bg=header_bg,
        fg=Theme.text if Theme.active else "black",
    )
    title_text.pack(anchor="w")
    tk.Label(
        title_block,
        text="ChatGPT alternative you fully own and control",
        font=("Arial", 11),
        bg=header_bg,
        fg=Theme.muted if Theme.active else "black",
    ).pack(anchor="w")

    header_actions = tk.Frame(header, bg=header_bg)
    header_actions.pack(side=tk.RIGHT, padx=24)

    os_controls = tk.Frame(header_actions, bg=header_bg)
    os_controls.pack(side=tk.RIGHT, padx=(0, 12))

    def _open_settings_from_header():
        try:
            braindrive_instance.open_settings_dialog()
        except Exception as exc:
            logger.error(f"Failed to open settings dialog: {exc}")

    if sys.platform == "win32":
        settings_font = ("Segoe UI Symbol", 16, "bold")
    else:
        settings_font = ("Arial", 16, "bold")

    settings_button = tk.Label(
        os_controls,
        text="⚙",
        font=settings_font,
        bg=header_bg,
        fg=Theme.text if Theme.active else "black",
        cursor="hand2",
    )

    def _on_settings_hover(_event):
        try:
            settings_button.config(fg=Theme.accent if Theme.active else "black")
        except Exception:
            pass

    def _on_settings_leave(_event):
        try:
            settings_button.config(fg=Theme.text if Theme.active else "black")
        except Exception:
            pass

    settings_button.bind("<Button-1>", lambda e: _open_settings_from_header())
    settings_button.bind("<Enter>", _on_settings_hover)
    settings_button.bind("<Leave>", _on_settings_leave)
    settings_button.pack(side=tk.RIGHT, padx=(8, 0), pady=2)

    os_label = tk.Label(
        os_controls,
        text=os_text,
        font=("Arial", 10),
        bg=header_bg,
        fg=Theme.muted if Theme.active else "black",
    )
    os_label.pack(side=tk.RIGHT, padx=(0, 6))

    update_button = ttk.Button(
        header_actions,
        text="Update available",
        command=lambda: _launch_updater_and_quit(root),
        style="Dark.TButton",
    )
    update_button.pack(side=tk.RIGHT, padx=(0, 12))
    update_button.pack_forget()

    def _reveal_update_button(label_text: str):
        def _show():
            update_button.config(text=label_text)
            update_button.pack(side=tk.RIGHT, padx=(0, 12))
        root.after(0, _show)

    # Create card instances
    ollama_instance = Ollama()

    body = tk.Frame(shell, bg=base_bg)
    body.pack(fill=tk.BOTH, expand=True)

    content = tk.Frame(body, bg=base_bg)
    content.pack(fill=tk.BOTH, expand=True, padx=24, pady=(12, 20))

    cards_wrapper = tk.Frame(content, bg=base_bg)
    cards_wrapper.pack(fill=tk.BOTH, expand=True)
    cards_wrapper.grid_columnconfigure(0, weight=1, uniform="card")
    cards_wrapper.grid_columnconfigure(1, weight=1, uniform="card")
    cards_wrapper.grid_rowconfigure(0, weight=1)

    card_kwargs = {
        "bg": Theme.panel_bg_alt if Theme.active else "white",
        "highlightbackground": Theme.border_soft if Theme.active else "grey80",
        "highlightthickness": 1,
        "bd": 0,
    }
    left_group = tk.Frame(cards_wrapper, height=360, **card_kwargs)
    left_group.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
    left_group.pack_propagate(False)
    right_group = tk.Frame(cards_wrapper, height=360, **card_kwargs)
    right_group.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
    right_group.pack_propagate(False)

    metadata_values = {
        "os": os_text,
        "disk": disk_text.replace("Disk space:", "").strip(),
        "installPath": _format_install_path(config.base_path),
        "version": version_text.replace("Version:", "").strip(),
    }
    status_section = tk.Frame(content, bg=base_bg)
    status_section.pack(fill=tk.X, expand=False, pady=(20, 0))
    status_display = StatusDisplay(status_section, inset=0, metadata=metadata_values, lock_width=False)
    status_display.frame.pack(fill=tk.BOTH, expand=True)
    config.status_display = status_display
    status_updater = config.status_updater

    status_display.register_action("install", lambda: braindrive_instance.install(status_updater))
    status_display.register_action("resume", lambda: braindrive_instance.install(status_updater))
    status_display.register_action("retry", lambda: braindrive_instance.install(status_updater))

    braindrive_instance.display(left_group, status_updater)
    ollama_instance.display(right_group, status_updater)
    status_display.set_installed_status(braindrive_installed)

    # Setup cleanup handler for proper shutdown
    _cleanup_state = {"ran": False}

    def cleanup_on_exit():
        """Clean up all running processes when the application exits."""
        if _cleanup_state["ran"]:
            return
        _cleanup_state["ran"] = True
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

    _closing_state = {"active": False}

    def _handle_window_close():
        if _closing_state["active"]:
            return
        _closing_state["active"] = True
        try:
            status_display.show_shutdown("Shutting down BrainDrive...")
        except Exception:
            pass

        def _do_cleanup():
            try:
                cleanup_on_exit()
            finally:
                root.after(0, lambda: (status_display.hide_shutdown(), root.destroy()))

        threading.Thread(target=_do_cleanup, daemon=True).start()

    # Register cleanup handler for window close event
    root.protocol("WM_DELETE_WINDOW", _handle_window_close)

    # Add log file info to status display
    log_file_path = get_log_file_path()
    logger.info(f"Log file location: {log_file_path}")
    status_display.set_log_file(log_file_path)
    
    # Background: check for updates and toggle button visibility
    def _toggle_update_if_available():
        try:
            current = _get_current_installer_version()
            latest = _get_latest_release_version()
            if latest and current:
                try:
                    if Version(_normalize_version(latest)) > Version(_normalize_version(current)):
                        label = f"Update available ({latest})"
                        _reveal_update_button(label)
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


# -----------------------
# Update helper functions
# -----------------------

def _format_disk_summary(target_path: str) -> str:
    """Return formatted disk space string for footer."""
    try:
        path = target_path if target_path and os.path.exists(target_path) else str(Path.home())
        total, used, free = shutil.disk_usage(path)
        free_gb = free / (1024 ** 3)
        return f"Disk space: {free_gb:.0f} GB free"
    except Exception:
        return "Disk space: calculating..."

def _format_install_path(path: str) -> str:
    """Shorten install path for footer display."""
    if not path:
        return "Not set"
    try:
        resolved = Path(path)
        display = str(resolved)
        if len(display) <= 48:
            return display
        return f"{display[:18]}…{display[-24:]}"
    except Exception:
        return path

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
    return "1.0.6"


def _get_latest_release_version() -> str:
    url = os.environ.get("BRAINDRIVE_INSTALLER_RELEASES")
    if not url:
        repo = os.environ.get("BRAINDRIVE_INSTALLER_REPO", "https://github.com/BrainDriveAI/BrainDrive-Install-System")
        parts = repo.rstrip("/").split("/")
        owner_repo = "/".join(parts[-2:]) if len(parts) >= 2 else "BrainDriveAI/BrainDrive-Install-System"
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
    repo = os.environ.get("BRAINDRIVE_INSTALLER_REPO", "https://github.com/BrainDriveAI/BrainDrive-Install-System")
    url = repo.rstrip("/") + "/releases/latest"
    try:
        import webbrowser
        webbrowser.open(url)
    except Exception:
        pass


if __name__ == "__main__":
    main()
