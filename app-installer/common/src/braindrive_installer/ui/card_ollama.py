import os
import sys
import threading
import time
import urllib.request
import subprocess
from tkinter import messagebox
from braindrive_installer.ui.base_card import BaseCard
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from braindrive_installer.ui.theme import Theme
import socket
from braindrive_installer.ui.ButtonStateManager import ButtonStateManager
from braindrive_installer.utils.DiskSpaceChecker import DiskSpaceChecker
from braindrive_installer.utils.helper_image import HelperImage
from pathlib import Path
from importlib import resources
from io import BytesIO
from braindrive_installer.core.installer_logger import get_installer_logger

class Ollama(BaseCard):
    def __init__(self):
        super().__init__(
            name="Ollama",
            description="Ollama enables you to download and run open source AI models in your BrainDrive directly from your computer. Once you download a model, you don't even need an internet connection to run it. Ollama is free to use with your BrainDrive.",
            size="3.5"
        )
        self.installed = False
        self.logger = get_installer_logger()

    def is_port_open(self, port=11434):
        """
        Check if a specific port is open.
        :param port: Port number to check (default is 11434).
        :return: True if the port is open, False otherwise.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)  # Timeout for the connection attempt
            result = sock.connect_ex(('127.0.0.1', port))
            return result == 0  # 0 means the port is open

    def install(self, status_updater=None):
        """Handle the installation of Ollama."""
        def ollama_install_task():
            try:
                self.config.status_updater.update_status(
                    "Step: [1/3] Downloading Ollama...",
                    "Downloading the Ollama installer. Please wait.",
                    0,
                )

                # Define the URL and target path for the installer
                ollama_url = "https://ollama.com/download/OllamaSetup.exe"
                installer_name = "OllamaSetup.exe"
                installer_path = os.path.join(os.getcwd(), installer_name)  # Save in current directory

                # Download the installer
                with urllib.request.urlopen(ollama_url) as response, open(installer_path, 'wb') as out_file:
                    data = response.read()
                    out_file.write(data)

                self.config.status_updater.update_status(
                        "Step: [2/3] Running Installer...",
                        "Running the Ollama installer. Follow the on-screen instructions.",
                        50,
                    )

                # Run the installer
                subprocess.Popen(installer_path, shell=True)

                self.config.status_updater.update_status(
                        "Step: [3/3] Ollama Installation Started",
                        "The Ollama install inferface should be visible soon.",
                        100,
                    )
                self.installed = True

            except Exception as e:
                self.config.status_updater.update_status(
                        "Error: Installation Failed",
                        f"Failed to install Ollama: {e}",
                        0,
                    )
                messagebox.showerror("Error", f"Failed to install Ollama: {e}")

        # Run the installation task in a separate thread
        threading.Thread(target=ollama_install_task, daemon=True).start()


    def uninstall(self):
        """
        Implements the uninstallation logic for Ollama.
        """
        if self.installed:
            print(f"Uninstalling {self.name}...")
            import time
            time.sleep(2)  # Simulate uninstallation time
            self.installed = False
            print(f"{self.name} uninstallation complete.")
        else:
            print(f"{self.name} is not installed.")

    def get_status(self):
        """
        Returns the installation status of Ollama.
        """
        return f"{self.name} is {'installed' if self.installed else 'not installed'}."

    def monitor_port_and_update_button(self, button_name):
        """
        Continuously checks the port status and updates the button state.
        :param button_name: The unique name of the button in the ButtonStateManager.
        """
        def task():
            button_manager = ButtonStateManager()
            disk_checker = DiskSpaceChecker()
            while True:
                if self.is_port_open():
                    # Port is open, disable the install button
                    button_manager.disable_buttons(button_name)
                else:
                    if disk_checker.has_enough_space(self.size):
                        button_manager.enable_buttons(button_name)
                    else:
                        button_manager.disable_buttons(button_name)
                time.sleep(1)  # Check every second

        threading.Thread(target=task, daemon=True).start()
        

    def display(self, parent_frame, status_updater):
        """
        Displays the card UI within the given Tkinter frame.
        """
        button_manager = ButtonStateManager()

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

        header = tk.Frame(card_frame, bg=card_bg)
        header.pack(fill=tk.X, padx=18, pady=(18, 8))

        def _resolve_icon(name: str):
            candidates = []
            try:
                helpers = HelperImage.get_image_path(name)
                candidates.append(Path(helpers))
            except Exception:
                pass
            base_path = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
            candidates.extend(
                [
                    base_path / name,
                    base_path / "assets" / name,
                    Path(__file__).resolve().parents[4] / "assets" / name,
                ]
            )
            for candidate in candidates:
                if candidate and candidate.exists():
                    return candidate
            return None

        card_image = None
        try:
            data = (resources.files("braindrive_installer") / "assets" / "ollama.png").read_bytes()
            card_image = Image.open(BytesIO(data)).convert("RGBA")
            self.logger.debug("Loaded Ollama icon from packaged assets.")
        except Exception as exc:
            self.logger.debug(f"Packaged Ollama icon load failed: {exc}")

        if card_image is None:
            icon_path = _resolve_icon("ollama.png")
            if icon_path:
                try:
                    card_image = Image.open(icon_path).convert("RGBA")
                    self.logger.debug(f"Loaded Ollama icon from {icon_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to load Ollama icon at {icon_path}: {e}")

        if card_image is None:
            self.logger.warning("Falling back to placeholder Ollama icon.")
            card_image = Image.new("RGBA", (48, 48), color=Theme.accent if Theme.active else "#4a90e2")
        card_image.thumbnail((48, 48))
        card_photo = ImageTk.PhotoImage(card_image)
        icon_label = tk.Label(header, image=card_photo, bg=card_bg)
        icon_label.image = card_photo
        icon_label.pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(
            header,
            text=self.name,
            font=("Arial", 18, "bold"),
            bg=card_bg,
            fg=text_color,
        ).pack(side=tk.LEFT, anchor="w")

        copy_frame = tk.Frame(card_frame, bg=card_bg)
        copy_frame.pack(fill=tk.X, padx=26, pady=(0, 8))
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

        def _update_wrap(event=None):
            inner_width = max(280, copy_frame.winfo_width() - 4)
            try:
                description_label.config(wraplength=inner_width)
            except Exception:
                pass

        copy_frame.bind("<Configure>", _update_wrap)
        _update_wrap()

        spacer = tk.Frame(card_frame, bg=card_bg)
        spacer.pack(fill=tk.BOTH, expand=True)

        meta = tk.Frame(card_frame, bg=card_bg)
        meta.pack(fill=tk.X, padx=26, pady=(4, 0))
        tk.Label(
            meta,
            text=f"Size: {self.size} GB",
            font=("Arial", 10, "bold"),
            bg=card_bg,
            fg=muted_color,
        ).pack(side=tk.LEFT)

        button_frame = tk.Frame(card_frame, bg=card_bg)
        button_frame.pack(fill=tk.X, padx=26, pady=(10, 18))
        if Theme.active:
            install_button = ttk.Button(
                button_frame,
                text="Install Ollama",
                command=lambda: self.install(status_updater),
                style="Dark.TButton",
                width=14,
            )
        else:
            install_button = tk.Button(
                button_frame,
                text="Install Ollama",
                command=lambda: self.install(status_updater),
                width=14,
            )
        install_button.pack(anchor="e")

        button_manager.register_button("install_ollama", install_button)
        self.monitor_port_and_update_button("install_ollama")

        # uninstall_button = tk.Button(card_frame, text="Uninstall", command=self.uninstall)
        # uninstall_button.place(relx=1.0, rely=1.0, anchor="se", x=-10, y=-10)

        status_button = tk.Button(
            card_frame,
            text="Status",
            command=lambda: print(self.get_status())
        )
        # status_button.place(relx=0.0, rely=1.0, anchor="sw", x=10, y=-10)    

