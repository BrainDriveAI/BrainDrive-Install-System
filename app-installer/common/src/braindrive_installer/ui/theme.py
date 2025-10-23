import sys

class Theme:
    """Simple dark theme helpers for Tk widgets and ttk styles."""

    # Core palette
    bg = "#2b2b2b"
    panel_bg = "#333333"
    header_bg = "#3a3a3a"
    border = "#555555"
    text = "#e8e8e8"
    muted = "#c8c8c8"
    accent = "#4a90e2"

    button_bg = "#454545"
    button_active = "#555555"
    button_text = "#ffffff"
    button_disabled_bg = "#4a4a4a"
    button_disabled_text = "#9aa0a6"
    success = "#34d058"
    warning = "#f5a623"

    # Only turn theme on for macOS by default
    active = sys.platform == "darwin"

    @staticmethod
    def apply(root):
        if not Theme.active:
            return
        import tkinter as tk
        from tkinter import ttk

        root.configure(bg=Theme.bg)

        # Ttk styles (progress bar, etc.)
        style = ttk.Style(root)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "Dark.TFrame",
            background=Theme.panel_bg,
        )
        style.configure(
            "Dark.TLabel",
            background=Theme.panel_bg,
            foreground=Theme.text,
        )
        style.configure(
            "DarkSuccess.TLabel",
            background=Theme.panel_bg,
            foreground=Theme.success,
        )
        style.configure(
            "DarkWarning.TLabel",
            background=Theme.panel_bg,
            foreground=Theme.warning,
        )
        style.configure(
            "Dark.TLabelframe",
            background=Theme.panel_bg,
            foreground=Theme.text,
            bordercolor=Theme.border,
        )
        style.configure(
            "Dark.TLabelframe.Label",
            background=Theme.panel_bg,
            foreground=Theme.text,
        )
        style.configure(
            "Header.TFrame",
            background=Theme.header_bg,
        )
        style.configure(
            "Header.TLabel",
            background=Theme.header_bg,
            foreground=Theme.text,
        )
        style.configure(
            "Horizontal.TProgressbar",
            troughcolor=Theme.panel_bg,
            background=Theme.accent,
            bordercolor=Theme.border,
            lightcolor=Theme.accent,
            darkcolor=Theme.accent,
        )

        # Buttons
        style.configure(
            "Dark.TButton",
            background=Theme.button_bg,
            foreground=Theme.button_text,
            bordercolor=Theme.border,
            focusthickness=0,
            focuscolor=Theme.button_bg,
            padding=(6, 3),
        )
        style.map(
            "Dark.TButton",
            background=[
                ("active", Theme.button_active),
                ("disabled", Theme.button_disabled_bg),
            ],
            foreground=[
                ("disabled", Theme.button_disabled_text),
            ],
        )

        # Checkbuttons
        style.configure(
            "Dark.TCheckbutton",
            background=Theme.panel_bg,
            foreground=Theme.text,
            bordercolor=Theme.border,
            focuscolor=Theme.panel_bg,
            indicatormargin=4,
        )
        style.map(
            "Dark.TCheckbutton",
            background=[
                ("active", Theme.panel_bg),
                ("selected", Theme.panel_bg),
            ],
            foreground=[
                ("disabled", Theme.muted),
            ],
        )

        # Entry / Combobox fields
        style.configure(
            "Dark.TEntry",
            fieldbackground="#3b3b3b",
            foreground=Theme.text,
            background=Theme.panel_bg,
            bordercolor=Theme.border,
            lightcolor=Theme.border,
            darkcolor=Theme.border,
        )
        style.configure(
            "Dark.TCombobox",
            fieldbackground="#3b3b3b",
            foreground=Theme.text,
            background=Theme.panel_bg,
            arrowcolor=Theme.text,
        )
        style.map(
            "Dark.TCombobox",
            fieldbackground=[("readonly", "#3b3b3b")],
        )

        # Notebook (tabs)
        style.configure(
            "Dark.TNotebook",
            background=Theme.panel_bg,
            bordercolor=Theme.border,
        )
        style.configure(
            "Dark.TNotebook.Tab",
            background=Theme.header_bg,
            foreground=Theme.text,
            padding=(10, 6),
        )
        style.map(
            "Dark.TNotebook.Tab",
            background=[("selected", Theme.panel_bg)],
            foreground=[("selected", Theme.text)],
        )

        # Basic tk defaults for dark bg
        root.configure(bg=Theme.bg)
        root.option_add("*TCombobox*Listbox*background", "#3b3b3b")
        root.option_add("*TCombobox*Listbox*foreground", Theme.text)
