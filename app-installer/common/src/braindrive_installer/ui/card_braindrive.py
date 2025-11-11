import os
import sys
import psutil
import socket
import subprocess
import time
import webbrowser
from tkinter import messagebox
from braindrive_installer.integration.AppDesktopIntegration import AppDesktopIntegration
from braindrive_installer.ui.ButtonStateManager import ButtonStateManager
from braindrive_installer.ui.base_card import BaseCard
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, Image
from io import BytesIO
import threading
from importlib import resources
from braindrive_installer.installers.installer_miniconda import MinicondaInstaller
from braindrive_installer.installers.installer_braindrive import BrainDriveInstaller
from braindrive_installer.utils.DiskSpaceChecker import DiskSpaceChecker
from braindrive_installer.core.installer_logger import get_installer_logger
from braindrive_installer.ui.settings_manager import BrainDriveSettingsManager
from braindrive_installer.ui.settings_dialog import BrainDriveSettingsDialog
from braindrive_installer.ui.theme import Theme
from braindrive_installer.utils.helper_image import HelperImage
from urllib.parse import urlparse
from pathlib import Path

class BrainDrive(BaseCard):
    """
    BrainDrive UI card component for managing BrainDrive installation and services.
    Handles dual server architecture (backend + frontend) with proper status monitoring.
    """
    
    def __init__(self):
        super().__init__(
            name="BrainDrive",
            description="BrainDrive is the MIT Licensed open source AI System you own, control, and build on.",
            size="8.5"
        )
        self.backend_running = False
        self.frontend_running = False
        self.logger = get_installer_logger()
        # Create a single shared BrainDriveInstaller instance
        self.braindrive_installer = BrainDriveInstaller()
        
        # Get port and host values from the installer (which loads from settings)
        self.backend_port = self.braindrive_installer.backend_port
        self.frontend_port = self.braindrive_installer.frontend_port
        self.backend_host = self.braindrive_installer.backend_host
        self.frontend_host = self.braindrive_installer.frontend_host
        self.helper_text = (
            "Once installed, the BrainDrive icon will be added to your desktop. "
            "Click the icon to start, stop, and update your BrainDrive."
        )

    def install(self, status_updater=None):
        """
        Install BrainDrive, ensuring prerequisites like Miniconda are installed.
        """
        status_display = getattr(self.config, "status_display", None)

        def _set_step_state(step_key, state):
            try:
                if status_display:
                    status_display.set_step_state(step_key, state)
            except Exception:
                pass

        if status_display:
            status_display.reset_step_states()

        def installation_task():
            self.logger.info("Starting BrainDrive installation process")
            button_manager = ButtonStateManager()
            button_manager.disable_buttons([
                "start_braindrive",
                "install_braindrive",
                "update_braindrive"
            ])

            disk_checker = DiskSpaceChecker()
            
            try:
                has_space = disk_checker.has_enough_space(self.size)
                if status_updater:
                    status_updater.update_status(
                        "Checking system prerequisites",
                        "Validating install path, disk space, and required permissions.",
                        5 if has_space else 0,
                    )
                _set_step_state("checking", "active")
                if not has_space:
                    _set_step_state("checking", "error")
                    if status_updater:
                        status_updater.update_status(
                            "Not enough free space",
                            f"BrainDrive needs {self.size} GB of free space before installation can begin.",
                            0,
                        )
                    return

                # Ensure Miniconda is installed first
                self.logger.info("Checking Miniconda prerequisite")
                _set_step_state("dependencies", "active")
                if status_updater:
                    status_updater.update_status(
                        "Installing dependencies",
                        "Setting up Miniconda and the BrainDrive runtime environment.",
                        35,
                    )
                
                miniconda_installer = MinicondaInstaller(status_updater)
                self.logger.info("Starting Miniconda installation")
                miniconda_installer.install()

                # Check if Miniconda installation is successful
                if not miniconda_installer.check_installed():
                    self.logger.error("Miniconda installation failed - cannot proceed with BrainDrive installation")
                    _set_step_state("dependencies", "error")
                    if status_updater:
                        status_updater.update_status(
                            "Dependency installation failed",
                            "Miniconda could not be installed. Check your connection and try again.",
                            0,
                        )
                    return
                else:
                    self.logger.info("Miniconda installation successful")
                    _set_step_state("checking", "complete")
                    _set_step_state("dependencies", "complete")

                # Proceed with BrainDrive installation
                self.logger.info("Starting BrainDrive installation")
                _set_step_state("installing", "active")
                if status_updater:
                    status_updater.update_status(
                        "Installing BrainDrive",
                        "Cloning BrainDrive Core, installing services, and generating shortcuts.",
                        75,
                    )
                
                self.braindrive_installer.set_status_updater(status_updater)

                # Use BrainDriveInstaller to perform complete installation
                try:
                    self.logger.info("Calling BrainDriveInstaller.install()")
                    success = self.braindrive_installer.install()
                    self.logger.info(f"BrainDriveInstaller.install() returned: {success}")
                    
                    if success:
                        self.logger.info("BrainDrive installation completed successfully")
                        _set_step_state("installing", "complete")
                        if status_updater:
                            status_updater.update_status(
                                "Installation complete",
                                "BrainDrive installed successfully. Use Start to launch services or Settings to tweak ports.",
                                100,
                            )
                    else:
                        self.logger.error("BrainDrive installation failed - installer returned False")
                        _set_step_state("installing", "error")
                        if status_updater:
                            status_updater.update_status(
                                "Error: Installation Failed.",
                                "BrainDrive installation encountered errors. Check logs for details.",
                                0,
                            )
                        return
                        
                except Exception as e:
                    error_msg = str(e)
                    self.logger.exception(f"Exception during BrainDrive installation: {error_msg}")
                    _set_step_state("installing", "error")
                    if status_updater:
                        status_updater.update_status(
                            "Error: Installation Failed.",
                            f"Installation error: {error_msg}",
                            0,
                        )
                    print(f"BrainDrive installation exception: {e}")
                    return

            except Exception as e:
                error_msg = str(e)
                self.logger.exception(f"Unexpected error in installation task: {error_msg}")
                if status_updater:
                    status_updater.update_status(
                        "Error: Installation Failed.",
                        f"Unexpected error: {error_msg}",
                        0,
                    )
                print(f"Installation task exception: {e}")
            finally:
                # Re-enable appropriate buttons based on installation status
                try:
                    self.braindrive_installer.set_status_updater(status_updater)
                    if self.braindrive_installer.check_installed():
                        button_manager.enable_buttons("start_braindrive")
                        button_manager.enable_buttons("update_braindrive")
                    else:
                        button_manager.enable_buttons("install_braindrive")
                except Exception as e:
                    print(f"Error re-enabling buttons: {e}")
                    button_manager.enable_buttons("install_braindrive")

                try:
                    # Handle desktop integration
                    desktop_integration = AppDesktopIntegration()

                    def background_task():
                        try:
                            desktop_integration.verify_exe_exists()
                            desktop_integration.verify_and_update_icon()
                        except Exception:
                            pass

                    threading.Thread(target=background_task, daemon=True).start()

                except Exception as e:
                    print(f"Failed to set application icon: {e}")

                try:
                    self.config.stop_spinner()
                except Exception as e:
                    print(f"Failed to stop spinner: {e}")

        # Run installation in a separate thread
        try:
            self.config.start_spinner()
        except Exception as e:
            print(f"Failed to start spinner: {e}")
        
        threading.Thread(target=installation_task, daemon=True).start()

    def start_server(self, status_updater=None):
        """
        Start BrainDrive backend and frontend servers.
        """
        def start_servers_task():
            button_manager = ButtonStateManager()
            button_manager.disable_buttons([
                "start_braindrive",
                "update_braindrive",
            ])
            
            try:
                # Refresh runtime settings from installer in case ports or hosts changed
                self._refresh_runtime_settings()
                self.braindrive_installer.set_status_updater(status_updater)
                
                if not self.braindrive_installer.check_installed():
                    if status_updater:
                        status_updater.update_status(
                            "Error: BrainDrive Not Installed.",
                            "Cannot start servers because BrainDrive is not installed.",
                            0,
                        )
                    return

                if status_updater:
                    status_updater.update_status(
                        "Step: Starting BrainDrive Services...",
                        "Launching backend and frontend servers. Please wait...",
                        25,
                    )

                # Start both servers
                success = self.braindrive_installer.start_services()
                
                if success:
                    self.backend_running = True
                    self.frontend_running = True
                    
                    if status_updater:
                        status_updater.update_status(
                            "BrainDrive Services Started",
                            f"Backend: {self._build_service_url(self.backend_host, self.backend_port)} | "
                            f"Frontend: {self._build_browser_url(self.frontend_host, self.frontend_port)}",
                            100,
                        )
                    
                    # Wait a moment then open browser
                    time.sleep(3)
                    try:
                        webbrowser.open(self._build_browser_url(self.frontend_host, self.frontend_port))
                    except Exception as e:
                        print(f"Failed to open browser: {e}")
                        
                else:
                    if status_updater:
                        status_updater.update_status(
                            "Error: Failed to Start Services",
                            "Could not start BrainDrive services. Check logs for details.",
                            0,
                        )

            except Exception as e:
                if status_updater:
                    status_updater.update_status(
                        "Error: Failed to Start BrainDrive.",
                        f"An error occurred: {e}",
                        0,
                    )
            finally:
                # Wait a moment for services to be fully detected, then update button states
                time.sleep(1)  # Give services time to be detected as running
                self._update_button_states()

        # Run in background thread
        threading.Thread(target=start_servers_task, daemon=True).start()

    def stop_server(self, status_updater=None):
        """
        Stop BrainDrive backend and frontend servers.
        """
        def stop_servers_task():
            try:
                self.logger.info("Stop server task started")
                if status_updater:
                    status_updater.update_status(
                        "Stopping BrainDrive Services...",
                        "Shutting down backend and frontend servers.",
                        50,
                    )

                self.braindrive_installer.set_status_updater(status_updater)
                self.logger.info("Calling braindrive_installer.stop_services()")
                success = self.braindrive_installer.stop_services()
                self.logger.info(f"Stop services result: {success}")
                
                if success:
                    self.backend_running = False
                    self.frontend_running = False
                    self.logger.info("Services stopped successfully, updating status")
                    
                    if status_updater:
                        status_updater.update_status(
                            "Services Stopped",
                            "BrainDrive services have been stopped successfully.",
                            100,
                        )
                else:
                    self.logger.warning("Stop services returned False")
                    if status_updater:
                        status_updater.update_status(
                            "Warning: Stop Issues",
                            "Some services may still be running. Check task manager if needed.",
                            75,
                        )

                # Wait a moment for processes to fully terminate
                self.logger.info("Waiting 3 seconds for processes to fully terminate")
                time.sleep(3)

            except Exception as e:
                self.logger.exception(f"Exception in stop_servers_task: {e}")
                if status_updater:
                    status_updater.update_status(
                        "Error: Failed to Stop Services",
                        f"An error occurred: {e}",
                        0,
                    )
            finally:
                # Update button states after a delay
                self.logger.info("Updating button states after stop")
                self._update_button_states()

        # Run in background thread
        threading.Thread(target=stop_servers_task, daemon=True).start()

    def update(self, status_updater=None):
        """
        Update BrainDrive to the latest version.
        """
        def update_task():
            button_manager = ButtonStateManager()
            button_manager.disable_buttons(["update_braindrive", "start_braindrive"])
            
            try:
                if status_updater:
                    status_updater.update_status(
                        "Step: [1/2] Updating BrainDrive...",
                        "Fetching latest code from the repository.",
                        50,
                    )
                
                # Perform update
                self.braindrive_installer.set_status_updater(status_updater)
                success = self.braindrive_installer.update()

                if success:
                    if status_updater:
                        status_updater.update_status(
                            "Step: [2/2] Update Complete",
                            "BrainDrive has been updated successfully.",
                            100,
                        )
                else:
                    if status_updater:
                        status_updater.update_status(
                            "Error: Update Failed",
                            "Failed to update BrainDrive. Check logs for details.",
                            0,
                        )

            except Exception as e:
                if status_updater:
                    status_updater.update_status(
                        "Error: Update Failed",
                        f"An error occurred during update: {e}",
                        0,
                    )
            finally:
                # Refresh button states based on current service status
                self._update_button_states()
                
        # Run update in background thread
        threading.Thread(target=update_task, daemon=True).start()

    def uninstall(self):
        """
        Uninstall BrainDrive (placeholder - not implemented).
        """
        # This would require implementing uninstall logic
        # For now, we'll leave this as a placeholder
        pass

    def get_status(self):
        """
        Get the current status of BrainDrive services.
        """
        self.logger.info("get_status called - using shared BrainDriveInstaller instance")
        self.logger.info("Calling get_service_status")
        service_status = self.braindrive_installer.get_service_status()
        self.logger.info(f"Service status from installer: {service_status}")
        
        # Handle case where service_status might be None
        if service_status is None:
            self.logger.warning("get_service_status returned None, using defaults")
            service_status = {
                'installed': False,
                'backend_running': False,
                'frontend_running': False,
                'backend_url': f"http://{self.backend_host}:{self.backend_port}",
                'frontend_url': f"http://{self.frontend_host}:{self.frontend_port}"
            }
        
        result = {
            'installed': service_status.get('installed', False),
            'backend_running': service_status.get('backend_running', False),
            'frontend_running': service_status.get('frontend_running', False),
            'backend_url': service_status.get('backend_url', self._build_service_url(self.backend_host, self.backend_port)),
            'frontend_url': service_status.get('frontend_url', self._build_browser_url(self.frontend_host, self.frontend_port))
        }
        self.logger.info(f"Returning status: {result}")
        return result

    def _update_button_states(self):
        """
        Update button states based on current service status.
        """
        self.logger.info("_update_button_states called")
        button_manager = ButtonStateManager()
        status = self.get_status()
        
        self.logger.info(f"Service status: {status}")
        services_running = status['backend_running'] or status['frontend_running']
        
        if status['installed']:
            # Installed: hide Install button; allow Update
            button_manager.disable_buttons("install_braindrive")
            button_manager.enable_buttons("update_braindrive")
            if services_running:
                # Services are running - enable the toggle button as "Stop BrainDrive"
                self.logger.info("Services are running - enabling start button as 'Stop BrainDrive', disabling separate stop button")
                button_manager.enable_buttons(["start_braindrive"])  # Keep the toggle button enabled
                button_manager.disable_buttons(["stop_braindrive"])  # Disable separate stop button
                
                # Update toggle button text to compact label on macOS
                try:
                    button_manager.set_button_text("start_braindrive", "Stop" if Theme.active else "Stop BrainDrive")
                except Exception as e:
                    self.logger.warning(f"Could not update start button text: {e}")

                button_manager.disable_buttons("update_braindrive")
            else:
                # Services are stopped - enable the toggle button as "Start BrainDrive"
                self.logger.info("Services are stopped - enabling start button as 'Start BrainDrive', disabling separate stop button")
                button_manager.enable_buttons(["start_braindrive"])  # Enable toggle button
                button_manager.disable_buttons("stop_braindrive")  # Disable separate stop button
                
                # Update toggle button text
                try:
                    button_manager.set_button_text("start_braindrive", "Start" if Theme.active else "Start BrainDrive")
                except Exception as e:
                    self.logger.warning(f"Could not update start button text: {e}")
            
            # Update stays enabled for installed scenario
        else:
            # Not installed
            self.logger.info("BrainDrive not installed - enabling install and settings buttons")
            button_manager.enable_buttons(["install_braindrive"])
            button_manager.disable_buttons(["start_braindrive", "stop_braindrive", "update_braindrive"])

    def _refresh_runtime_settings(self):
        """Reload connection settings from the installer."""
        try:
            self.braindrive_installer._load_settings()
            self.backend_port = self.braindrive_installer.backend_port
            self.frontend_port = self.braindrive_installer.frontend_port
            backend_host = self._extract_host(self.braindrive_installer.backend_host, allow_wildcard=True, default="0.0.0.0")
            self.backend_host = backend_host
            self.braindrive_installer.backend_host = backend_host
            frontend_host = self._extract_host(self.braindrive_installer.frontend_host, allow_wildcard=True, default="localhost")
            self.frontend_host = frontend_host
            self.braindrive_installer.frontend_host = frontend_host
        except Exception as exc:
            self.logger.warning(f"Unable to refresh runtime settings: {exc}")

    def _extract_host(self, value, allow_wildcard=False, default="localhost"):
        """Sanitize host values used for process launches."""
        if not value:
            return default
        value = value.strip()
        parsed = urlparse(value if "://" in value else f"http://{value}")
        host = parsed.hostname or value
        if not host:
            return default
        if not allow_wildcard and host in ("0.0.0.0", "*"):
            return default
        return host

    def _get_browser_host(self, host):
        """Convert binding hosts into something browser-friendly."""
        if not host or host in ("0.0.0.0", "*"):
            return "127.0.0.1"
        return host

    def _build_service_url(self, host, port):
        host_for_link = self._get_browser_host(host or "localhost")
        port_part = f":{port}" if port else ""
        return f"http://{host_for_link}{port_part}"

    def _build_browser_url(self, host, port):
        if not host:
            host = "localhost"
        host = host.strip()
        if "://" in host:
            parsed = urlparse(host)
            browse_host = parsed.hostname or self._get_browser_host(host)
            scheme = parsed.scheme or "http"
            effective_port = parsed.port or port
            port_part = f":{effective_port}" if effective_port else ""
            path = parsed.path or ""
            return f"{scheme}://{browse_host}{port_part}{path}"
        else:
            browse_host = self._get_browser_host(host)
            port_part = f":{port}" if port else ""
            return f"http://{browse_host}{port_part}"

    def _check_port_available(self, port):
        """
        Check if a port is available.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return True
        except OSError:
            return False

    def display(self, parent_frame, status_updater):
        """
        Display the BrainDrive card UI within the given Tkinter frame.
        """
        self.set_parent_frame(parent_frame)
        card_bg = Theme.panel_bg_alt if Theme.active else "white"
        border_color = Theme.border if Theme.active else "#d9d9d9"
        text_color = Theme.text if Theme.active else "black"
        muted_color = Theme.muted if Theme.active else "#4a4a4a"

        card_frame = tk.Frame(
            parent_frame,
            bg=card_bg,
            highlightbackground=border_color,
            highlightthickness=1,
            bd=0,
            relief=tk.FLAT,
        )
        card_frame.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)
        card_frame.pack_propagate(False)

        def _resolve_icon_path(name: str):
            try:
                data_path = resources.files("braindrive_installer") / "assets" / name
                with resources.as_file(data_path) as handle:
                    return handle
            except Exception:
                pass
            candidates = []
            try:
                helper_path = HelperImage.get_image_path(name)
                candidates.append(Path(helper_path))
            except Exception:
                pass
            base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
            candidates.extend(
                [
                    base_dir / name,
                    base_dir / "assets" / name,
                    Path(__file__).resolve().parents[4] / "assets" / name,
                ]
            )
            for candidate in candidates:
                if candidate and candidate.exists():
                    return candidate
            return None

        def _load_icon():
            img = None
            try:
                asset_path = resources.files("braindrive_installer") / "assets" / "braindrive.png"
                with asset_path.open("rb") as data:
                    img = Image.open(BytesIO(data.read())).convert("RGBA")
                self.logger.debug(f"Loaded BrainDrive icon from packaged assets: {asset_path}")
            except Exception as exc:
                self.logger.debug(f"Packaged BrainDrive icon load failed: {exc}")

            if img is None:
                path = _resolve_icon_path("braindrive.png")
                if path:
                    try:
                        img = Image.open(path).convert("RGBA")
                        self.logger.debug(f"Loaded BrainDrive icon from {path}")
                    except Exception as exc:
                        self.logger.warning(f"BrainDrive icon at {path} failed to load: {exc}")

            if img is None:
                placeholder_path = Path(__file__).resolve().parents[4] / "common" / "assets" / "braindrive.png"
                if placeholder_path.exists():
                    try:
                        img = Image.open(placeholder_path).convert("RGBA")
                        self.logger.debug(f"Loaded fallback icon from common assets: {placeholder_path}")
                    except Exception as exc:
                        self.logger.warning(f"Fallback BrainDrive icon load failed: {exc}")

            if img is None:
                self.logger.warning("Falling back to generated placeholder BrainDrive icon.")
                img = Image.new("RGBA", (64, 64), color=Theme.accent if Theme.active else "#4a90e2")

            img.thumbnail((64, 64), Image.LANCZOS)
            return ImageTk.PhotoImage(img)

        header = tk.Frame(card_frame, bg=card_bg)
        header.pack(fill=tk.X, padx=22, pady=(18, 10))
        card_photo = _load_icon()
        icon_label = tk.Label(header, image=card_photo, bg=card_bg)
        icon_label.image = card_photo
        icon_label.pack(side=tk.LEFT, padx=(0, 14))

        title_block = tk.Frame(header, bg=card_bg)
        title_block.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(
            title_block,
            text=self.name,
            font=("Arial", 20, "bold"),
            bg=card_bg,
            fg=text_color,
        ).pack(anchor="w")
        tk.Label(
            title_block,
            text="MIT Self-Hosted Local AI",
            font=("Arial", 11),
            bg=card_bg,
            fg=muted_color,
        ).pack(anchor="w")

        copy_frame = tk.Frame(card_frame, bg=card_bg)
        copy_frame.pack(fill=tk.X, padx=30, pady=(0, 8))
        description_label = tk.Label(
            copy_frame,
            text=self.description,
            font=("Arial", 11),
            justify="left",
            bg=card_bg,
            fg=text_color,
            anchor="w",
        )
        description_label.pack(fill=tk.X, anchor="w")
        helper_label = tk.Label(
            copy_frame,
            text=self.helper_text,
            font=("Arial", 10),
            justify="left",
            bg=card_bg,
            fg=muted_color,
            anchor="w",
        )
        helper_label.pack(fill=tk.X, anchor="w", pady=(8, 0))

        def _update_wrap(event=None):
            try:
                available = max(320, card_frame.winfo_width() - 60)
                description_label.config(wraplength=available)
                helper_label.config(wraplength=available)
            except Exception:
                pass

        card_frame.bind("<Configure>", _update_wrap)
        copy_frame.bind("<Configure>", _update_wrap)
        card_frame.after(0, _update_wrap)

        spacer = tk.Frame(card_frame, bg=card_bg)
        spacer.pack(fill=tk.BOTH, expand=True)

        meta_frame = tk.Frame(card_frame, bg=card_bg)
        meta_frame.pack(fill=tk.X, padx=30, pady=(10, 4))
        tk.Label(
            meta_frame,
            text=f"Size: {self.size} GB",
            font=("Arial", 10, "bold"),
            bg=card_bg,
            fg=muted_color,
        ).pack(side=tk.LEFT)

        # Bottom button bar
        button_container = tk.Frame(card_frame, bg=card_bg)
        button_container.pack(side=tk.BOTTOM, fill=tk.X, padx=30, pady=10)
        button_row = tk.Frame(button_container, bg=card_bg)
        button_row.pack(fill=tk.X, anchor="w", pady=(6, 0))

        # Initialize components
        disk_checker = DiskSpaceChecker()
        button_manager = ButtonStateManager()
        # Use shared installer instance
        self.braindrive_installer.set_status_updater(status_updater)

        def mkbtn(text, cmd):
            if Theme.active:
                return ttk.Button(
                    button_row,
                    text=text,
                    command=cmd,
                    style="Dark.TButton",
                )
            else:
                return tk.Button(button_row, text=text, command=cmd)

        update_button = mkbtn("Update", lambda: self.update(status_updater))
        update_button.pack(side=tk.LEFT, padx=6)
        update_button.config(state="disabled")
        button_manager.register_button("update_braindrive", update_button)

        # Start/Stop button with toggle functionality
        def toggle_server():
            status = self.get_status()
            if status['backend_running'] or status['frontend_running']:
                self.stop_server(status_updater)
            else:
                self.start_server(status_updater)
            
            # Update button states after operation completes
            # Note: The actual button text update happens in _update_button_states()
            # which is called at the end of start_server() and stop_server()

        start_label = "Start" if Theme.active else "Start BrainDrive"
        start_stop_button = mkbtn(start_label, toggle_server)
        start_stop_button.pack(side=tk.LEFT, padx=6)
        start_stop_button.config(state="disabled")
        button_manager.register_button("start_braindrive", start_stop_button)

        # Install button
        install_button = mkbtn("Install", lambda: self.install(status_updater))
        install_button.pack(side=tk.LEFT, padx=6)
        install_button.config(state="disabled")
        button_manager.register_button("install_braindrive", install_button)

        # Stop button (separate from start for clarity)
        stop_button = mkbtn("Stop", lambda: self.stop_server(status_updater))
        stop_button.pack_forget()
        stop_button.place_forget()
        stop_button.config(state="disabled")
        button_manager.register_button("stop_braindrive", stop_button)

        # Set initial button states based on installation status
        if self.braindrive_installer.check_installed():
            status = self.get_status()
            if status['backend_running'] or status['frontend_running']:
                start_stop_button.config(text=("Stop" if Theme.active else "Stop BrainDrive"))
                # Update status display with current service URLs
                status_updater.update_status(
                    "BrainDrive Services Started",
                    f"Backend: {status['backend_url']} | Frontend: {status['frontend_url']}",
                    100
                )
            else:
                start_stop_button.config(text=("Start" if Theme.active else "Start BrainDrive"))
                # Update status display
                status_updater.update_status(
                    "BrainDrive Ready",
                    "BrainDrive is installed and ready to use.",
                    100
                )
            
            # Use the proper button state management method
            self._update_button_states()
        else:
            # Not installed - check disk space and enable install button
            disk_checker = DiskSpaceChecker()
            if disk_checker.has_enough_space(self.size):
                button_manager.enable_buttons("install_braindrive")
                # Allow configuring settings prior to installation
                status_updater.update_status(
                    "Installation Required",
                    "BrainDrive is not installed. Click Install to begin setup.",
                    0
                )
            else:
                button_manager.disable_buttons("install_braindrive")
                status_updater.update_status(
                    "Insufficient Space",
                    f"Need {self.size}GB free space to install BrainDrive.",
                    0
                )
    
    def open_settings_dialog(self):
        """Open the settings configuration dialog"""
        try:
            # Determine where to store/load settings:
            # - If installed, use the BrainDrive repo path
            # - If not installed yet, use the installer environment path to preconfigure
            if self.braindrive_installer.check_installed():
                installation_path = self.braindrive_installer.get_installation_path()
            else:
                installation_path = self.config.env_path
            
            # Create settings manager
            settings_manager = BrainDriveSettingsManager(installation_path)
            
            # If installed but no JSON exists, try to load from existing env files
            # This migrates current env into JSON for editing
            if self.braindrive_installer.check_installed() and not os.path.exists(settings_manager.settings_file):
                settings_manager.load_from_env_files()
                settings_manager.save_settings()
            
            # Show dialog
            dialog = BrainDriveSettingsDialog(
                parent=self.parent_frame,
                settings_manager=settings_manager,
                on_apply=self._on_settings_applied
            )
            dialog.show()
            
        except Exception as e:
            self.logger.error(f"Error opening settings dialog: {e}")
            messagebox.showerror("Settings Error", f"Failed to open settings dialog: {e}")

    def _on_settings_applied(self):
        """Callback when settings are applied - reload settings and update UI"""
        try:
            # Reload settings in the installer
            self.braindrive_installer._load_settings()
            
            # Update card's port values from the installer
            self.backend_port = self.braindrive_installer.backend_port
            self.frontend_port = self.braindrive_installer.frontend_port
            self.backend_host = self.braindrive_installer.backend_host
            self.frontend_host = self.braindrive_installer.frontend_host
            
            # Update button states based on new settings
            self._update_button_states()
            
            self.logger.info(f"Settings applied - Updated to Backend: {self.backend_host}:{self.backend_port}, Frontend: {self.frontend_host}:{self.frontend_port}")
            
        except Exception as e:
            self.logger.error(f"Error applying settings: {e}")
            messagebox.showerror("Settings Error", f"Failed to apply settings: {e}")
            messagebox.showerror("Error", f"Failed to open settings dialog: {str(e)}")

    def _on_settings_applied(self):
        """Called when settings are applied"""
        # Update button states or refresh status
        self._update_button_states()
        
        # Show restart warning if services are running
        status = self.get_status()
        if status['backend_running'] or status['frontend_running']:
            messagebox.showinfo(
                "Restart Required",
                "Settings have been applied. Please restart BrainDrive services for changes to take effect."
            )
