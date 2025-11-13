import sys

class Theme:
    """Dark theme helpers tuned to the BrainDrive dark runner reference."""

    # Core palette pulled from dark UI reference
    bg = "#050c18"
    panel_bg = "#0e1522"
    panel_bg_alt = "#111b2a"
    header_bg = "#111b2a"
    sidebar_bg = "#0a111c"
    border = "#1e2a3f"
    border_soft = "#162133"
    text = "#f4f7fb"
    muted = "#94a2c5"
    accent = "#42a5ff"
    accent_soft = "#2f7ad9"

    button_bg = "#111c2c"
    button_active = "#1b2940"
    button_text = "#eff6ff"
    button_disabled_bg = "#0b121f"
    button_disabled_text = "#4b5a75"
    success = "#43e6b2"
    warning = "#ffc474"
    danger = "#ff7b7b"

    # Always run with the custom theme
    active = True

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
            "DarkRaised.TFrame",
            background=Theme.panel_bg_alt,
            bordercolor=Theme.border,
            relief="flat",
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
            darkcolor=Theme.accent_soft,
            thickness=14,
        )
        style.configure(
            "Indeterminate.Horizontal.TProgressbar",
            troughcolor=Theme.panel_bg_alt,
            background=Theme.accent,
        )

        # Buttons
        style.configure(
            "Dark.TButton",
            background=Theme.button_bg,
            foreground=Theme.button_text,
            bordercolor=Theme.border,
            focusthickness=2,
            focuscolor=Theme.accent_soft,
            padding=(16, 8),
            relief="flat",
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
            fieldbackground=Theme.panel_bg_alt,
            foreground=Theme.text,
            background=Theme.panel_bg,
            bordercolor=Theme.border,
            lightcolor=Theme.border,
            darkcolor=Theme.border,
        )
        style.configure(
            "Dark.TCombobox",
            fieldbackground=Theme.panel_bg_alt,
            foreground=Theme.text,
            background=Theme.panel_bg,
            arrowcolor=Theme.text,
        )
        style.map(
            "Dark.TCombobox",
            fieldbackground=[("readonly", Theme.panel_bg_alt)],
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
        root.option_add("*TCombobox*Listbox*background", Theme.panel_bg_alt)
        root.option_add("*TCombobox*Listbox*foreground", Theme.text)
