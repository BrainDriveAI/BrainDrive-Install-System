import tkinter as tk
from tkinter import ttk

from braindrive_installer.ui.status_spinner import StatusSpinner
from braindrive_installer.ui.theme import Theme


class StatusDisplay:
    """Progress + step stack widget that mirrors the new BrainDrive Runner layout."""

    STEP_ORDER = [
        ("checking", "Checking system"),
        ("dependencies", "Installing dependencies"),
        ("installing", "Installing BrainDrive"),
    ]

    STATE_STYLES = {
        "pending": {"icon": "\u25b3", "fg": Theme.muted},
        "active": {"icon": "\u25cc", "fg": Theme.accent},
        "complete": {"icon": "\u2713", "fg": Theme.success},
        "error": {"icon": "\u26a0", "fg": Theme.warning},
    }

    def __init__(self, parent, inset=0):
        frame_kwargs = {"height": 150}
        if Theme.active:
            frame_kwargs.update(
                bg=Theme.panel_bg,
                highlightbackground=Theme.border_soft,
                highlightthickness=1,
            )
        else:
            frame_kwargs.update(bg="lightgrey")
        self.frame = tk.Frame(parent, **frame_kwargs)
        self.frame.pack(fill=tk.X, padx=inset, pady=(12, 18))

        # Temporarily hide step indicators during text inspection.
        self.step_stack_hidden = True
        self.step_rows = {}
        self._build_step_stack()
        self._build_message_region()
        self._build_progress_bar()
        self._build_shutdown_overlay()
        self.reset_for_idle()

    def _build_step_stack(self):
        stack_kwargs = {"bg": Theme.panel_bg} if Theme.active else {"bg": "lightgrey"}
        self.step_stack = tk.Frame(self.frame, **stack_kwargs)
        self.step_stack.pack(fill=tk.X, padx=16, pady=(12, 6))
        self.step_rows = {}
        for key, label in self.STEP_ORDER:
            row = tk.Frame(self.step_stack, **stack_kwargs)
            row.pack(side=tk.LEFT, padx=(0, 32))
            icon_kwargs = {
                "text": "",
                "font": ("Segoe UI Symbol", 16),
                "width": 2,
            }
            text_kwargs = {
                "text": label,
                "font": ("Arial", 11, "bold"),
            }
            if Theme.active:
                icon_kwargs.update(bg=Theme.panel_bg, fg=Theme.muted)
                text_kwargs.update(bg=Theme.panel_bg, fg=Theme.muted)
            else:
                icon_kwargs.update(bg="lightgrey", fg="black")
                text_kwargs.update(bg="lightgrey", fg="black")
            icon_label = tk.Label(row, **icon_kwargs)
            icon_label.pack(side=tk.LEFT)
            text_label = tk.Label(row, **text_kwargs)
            text_label.pack(side=tk.LEFT)
            self.step_rows[key] = {"icon": icon_label, "text": text_label}

    def _build_message_region(self):
        region_kwargs = {"bg": Theme.panel_bg} if Theme.active else {"bg": "lightgrey"}
        self.message_frame = tk.Frame(self.frame, **region_kwargs)
        self.message_frame.pack(fill=tk.X, padx=16, pady=(4, 6))

        step_kwargs = {"text": "Ready to install BrainDrive", "font": ("Arial", 13, "bold")}
        details_kwargs = {
            "text": "Review settings, then click Install to begin.",
            "font": ("Arial", 10),
            "wraplength": 720,
            "justify": "left",
        }
        if Theme.active:
            step_kwargs.update(bg=Theme.panel_bg, fg=Theme.text)
            details_kwargs.update(bg=Theme.panel_bg, fg=Theme.muted)
        else:
            step_kwargs.update(bg="lightgrey")
            details_kwargs.update(bg="lightgrey")

        self.step_label = tk.Label(self.message_frame, **step_kwargs)
        self.step_label.pack(anchor="w")

        self.spinner = StatusSpinner(self.message_frame, self.step_label)

        self.details_label = tk.Label(self.message_frame, **details_kwargs)
        self.details_label.pack(anchor="w", pady=(4, 0))

    def _build_progress_bar(self):
        bar_frame_kwargs = {"bg": Theme.panel_bg} if Theme.active else {"bg": "lightgrey"}
        bar_frame = tk.Frame(self.frame, **bar_frame_kwargs)
        bar_frame.pack(fill=tk.X, padx=16, pady=(8, 16))
        self.progress_bar = ttk.Progressbar(bar_frame, length=720, mode="determinate")
        self.progress_bar.pack(fill=tk.X)
        self.progress_bar["value"] = 0

    def _build_shutdown_overlay(self):
        overlay_kwargs = {"bg": Theme.panel_bg_alt} if Theme.active else {"bg": "white"}
        self.shutdown_overlay = tk.Frame(self.frame, **overlay_kwargs)
        self.shutdown_overlay.place(relwidth=1, relheight=1)
        self.shutdown_overlay.lower()
        label_kwargs = {"text": "Shutting down BrainDrive...", "font": ("Arial", 12, "bold")}
        
        if Theme.active:
            label_kwargs.update(bg=Theme.panel_bg_alt, fg=Theme.text)
        else:
            label_kwargs.update(bg="white")
        self.shutdown_label = tk.Label(self.shutdown_overlay, **label_kwargs)
        self.shutdown_label.pack(pady=(32, 12))
        self.shutdown_bar = ttk.Progressbar(
            self.shutdown_overlay,
            mode="indeterminate",
            length=320,
            style="Indeterminate.Horizontal.TProgressbar",
        )
        self.shutdown_bar.pack(pady=(0, 16))
        self.shutdown_overlay.lower()  # Hide by default

    def get_components(self):
        """Return tuple consumed by StatusUpdater."""
        return self.step_label, self.details_label, self.progress_bar

    def reset_step_states(self):
        """Set all indicators to pending."""
        for key in self.step_rows:
            self.set_step_state(key, "pending")

    def reset_for_idle(self):
        """Restore idle copy and reset indicators."""
        if not getattr(self, "step_stack_hidden", False):
            self.reset_step_states()
        self.progress_bar["value"] = 0
        self.step_label.config(text="Ready to install BrainDrive")
        self.details_label.config(
            text="Click Install to provision BrainDrive, or open Settings to review ports and paths."
        )
        self.spinner.stop()

    def set_step_state(self, key, state):
        """Update icon + color for a given step."""
        if key not in self.step_rows:
            return
        style = self.STATE_STYLES.get(state, self.STATE_STYLES["pending"])
        icon_label = self.step_rows[key]["icon"]
        text_label = self.step_rows[key]["text"]
        icon_label.config(text=style["icon"], fg=style["fg"])
        text_label.config(fg=style["fg"])

    def show_shutdown(self, message="Closing BrainDrive Runner..."):
        """Display blocking overlay with hourglass effect."""
        self.shutdown_label.config(text=message)
        self.shutdown_overlay.lift()
        try:
            self.shutdown_bar.start(10)
        except Exception:
            pass

    def hide_shutdown(self):
        """Hide shutdown overlay once cleanup finished."""
        try:
            self.shutdown_bar.stop()
        except Exception:
            pass
        self.shutdown_overlay.lower()
