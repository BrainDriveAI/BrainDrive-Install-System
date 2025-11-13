import tkinter as tk
from threading import Thread
import time

from braindrive_installer.ui.theme import Theme

class StatusSpinner:
    def __init__(self, parent, step_label):
        """
        Initializes the spinner with a label to display the spinning animation.
        :param parent: The parent frame to attach the spinner.
        :param step_label: The label next to which the spinner appears.
        """
        self.parent = parent
        self.step_label = step_label
        label_kwargs = {"text": "", "font": ("Arial", 12, "bold")}
        if Theme.active:
            label_kwargs.update(bg=Theme.panel_bg, fg=Theme.accent)
        else:
            label_kwargs.update(bg="lightgrey", fg="black")
        self.spinner_label = tk.Label(parent, **label_kwargs)
        self.active = False
        self.symbols = ["|", "/", "-", "\\"]
        self.colors = [Theme.accent, Theme.accent_soft, Theme.accent, Theme.accent_soft] if Theme.active else ["black"] * 4
        self._original_padx = self._get_current_padx()

    def start(self):
        """Starts the spinner animation and repositions the step label."""
        if not self.active:
            if not self._original_padx or self._original_padx == (0, 0):
                self._original_padx = self._get_current_padx()
            self.active = True
            # Move the step label to the right irrespective of geometry manager
            self._apply_padx((25, 10))

            # Center the spinner vertically with respect to the step label
            self.parent.update_idletasks()  # Ensure geometry info is updated
            step_label_y = self.step_label.winfo_y()
            step_label_height = self.step_label.winfo_height()
            spinner_label_height = self.spinner_label.winfo_reqheight()  # Requested height of spinner
            spinner_y = step_label_y + (step_label_height - spinner_label_height) // 2

            # Position spinner near the step label
            self.spinner_label.place(x=10, y=spinner_y)

            Thread(target=self._animate, daemon=True).start()

    def stop(self):
        """Stops the spinner animation and resets the step label position."""
        self.active = False
        # Reset the step label position
        self._apply_padx(self._original_padx or (10, 10))
        self.spinner_label.place_forget()  # Hide the spinner label

    def _animate(self):
        """Handles the spinner animation loop."""
        idx = 0
        while self.active:
            # Update the spinner symbol and color on the main thread
            self.spinner_label.after(
                0,
                lambda symbol=self.symbols[idx % len(self.symbols)],
                color=self.colors[idx % len(self.colors)]:  # Correctly closed with )
                self.spinner_label.config(text=symbol, fg=color)
            )
            idx += 1
            time.sleep(0.1)

    def _apply_padx(self, value):
        manager = self.step_label.winfo_manager()
        try:
            if manager == "pack":
                self.step_label.pack_configure(padx=value)
            elif manager == "grid":
                self.step_label.grid_configure(padx=value)
        except tk.TclError:
            pass

    def _get_current_padx(self):
        manager = self.step_label.winfo_manager()
        try:
            if manager == "pack":
                info = self.step_label.pack_info()
            elif manager == "grid":
                info = self.step_label.grid_info()
            else:
                return (0, 0)
        except tk.TclError:
            return (0, 0)
        raw = info.get("padx", 0)
        return self._normalize_pad_value(raw)

    @staticmethod
    def _normalize_pad_value(value):
        if isinstance(value, (tuple, list)):
            if len(value) == 2:
                return tuple(int(v) for v in value)
            if len(value) == 1:
                val = int(value[0])
                return (val, val)
        if isinstance(value, str):
            parts = value.split()
            if len(parts) == 2:
                try:
                    return tuple(int(part) for part in parts)
                except ValueError:
                    return (0, 0)
            if len(parts) == 1:
                try:
                    val = int(parts[0])
                    return (val, val)
                except ValueError:
                    return (0, 0)
        try:
            val = int(value)
            return (val, val)
        except Exception:
            return (0, 0)

