import tkinter as tk
from tkinter import ttk

from braindrive_installer.ui.status_spinner import StatusSpinner
from braindrive_installer.ui.theme import Theme

class StatusDisplay:
    def __init__(self, parent):
        """
        Initializes the StatusDisplay and creates its components.
        """
        frame_kwargs = {"height": 110}
        if Theme.active:
            frame_kwargs.update(bg=Theme.panel_bg, highlightbackground=Theme.border, highlightthickness=1)
        else:
            frame_kwargs.update(bg="lightgrey")
        self.frame = tk.Frame(parent, **frame_kwargs)
        self.frame.pack(fill=tk.X, padx=10, pady=(8, 10))

        step_kwargs = {"text": "Initializing...", "font": ("Arial", 12)}
        if Theme.active:
            step_kwargs.update(bg=Theme.panel_bg, fg=Theme.text)
        else:
            step_kwargs.update(bg="lightgrey")
        self.step_label = tk.Label(self.frame, **step_kwargs)
        self.step_label.pack(anchor="w", padx=12, pady=(8, 4))

        self.spinner = StatusSpinner(self.frame, self.step_label)  # Pass step_label to the spinner

        details_kwargs = {
            "text": "Gathering information about current setup.",
            "font": ("Arial", 10),
            "wraplength": 580,
            "justify": "left",
        }
        if Theme.active:
            details_kwargs.update(bg=Theme.panel_bg, fg=Theme.muted)
        else:
            details_kwargs.update(bg="lightgrey")
        self.details_label = tk.Label(self.frame, **details_kwargs)
        self.details_label.pack(anchor="w", padx=12)

        self.progress_bar = ttk.Progressbar(self.frame, length=580, mode="determinate")
        self.progress_bar.pack(padx=12, pady=(8, 12), fill=tk.X)
        self.progress_bar['value'] = 50  # Initial progress value

    def get_components(self):
        """
        Returns the components needed for the StatusUpdater.

        :return: A tuple (step_label, details_label, progress_bar)
        """
        return self.step_label, self.details_label, self.progress_bar
