
import os
import shutil
import sys
import platform
import tkinter as tk
from tkinter import ttk
from braindrive_installer.ui.card_ollama import Ollama
from braindrive_installer.ui.card_braindrive import BrainDrive

from braindrive_installer.ui.status_display import StatusDisplay
from braindrive_installer.ui.status_updater import StatusUpdater
from braindrive_installer.ui.theme import Theme
import threading
from braindrive_installer.config.AppConfig import AppConfig
from braindrive_installer.utils.helper_image import HelperImage
from braindrive_installer.integration.AppDesktopIntegration import AppDesktopIntegration
from braindrive_installer.core.installer_logger import get_installer_logger, get_log_file_path

def main():
    # Initialize logging first
    logger = get_installer_logger()
    logger.info("Starting BrainDrive Installer application")
    
    # Create the main window
    root = tk.Tk()
    root.title("BrainDrive Installer [v1.0.0]")
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
