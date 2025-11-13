import datetime
import os
import re
import subprocess
import sys
import textwrap
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import font as tkfont, ttk

from braindrive_installer.ui.status_spinner import StatusSpinner
from braindrive_installer.ui.theme import Theme


class StatusDisplay:
    """Right-rail status column that mirrors the redesigned BrainDrive installer spec."""

    IDLE_HEADLINE_INSTALLED = "BrainDrive is installed."
    IDLE_HEADLINE_NOT_INSTALLED = "BrainDrive is currently not installed."
    IDLE_STATUS_INSTALLED = "BrainDrive is installed. Press Start on the BrainDrive card to launch services."
    IDLE_STATUS_NOT_INSTALLED = (
        "BrainDrive needs to be installed. Use the Install button on the BrainDrive card."
    )
    IDLE_CARD_INSTALLED = "BrainDrive is installed. Press Start on the BrainDrive card to launch services."
    IDLE_CARD_NOT_INSTALLED = "Estimated Install Time: 5-10 Minutes."

    STARTING_KEYWORDS = (
        "starting",
        "launching",
        "starting backend",
        "starting frontend",
        "start services",
        "starting brain",
    )
    STOPPING_KEYWORDS = (
        "stopping",
        "stop",
        "stop services",
        "shutting down",
        "shutdown",
    )

    STEP_ORDER = [
        {"key": "checking", "label": "Check system", "subtitle": "Validate disk space, permissions, and ports."},
        {"key": "dependencies", "label": "Install prerequisites", "subtitle": "Install Miniconda and base tooling."},
        {"key": "installing", "label": "Clone BrainDrive", "subtitle": "Download the latest BrainDrive repository."},
        {"key": "plugins", "label": "Build plugins", "subtitle": "Compile optional BrainDrive plugins."},
        {"key": "backend", "label": "Setup backend", "subtitle": "Install Python packages and services."},
        {"key": "frontend", "label": "Setup frontend", "subtitle": "Install dashboard/UI dependencies."},
        {"key": "verify", "label": "Verify installation", "subtitle": "Run final checks and create shortcuts."},
    ]
    STEP_KEYS = [step["key"] for step in STEP_ORDER]

    EXEC_EXTENSIONS = (".exe", ".bat", ".cmd", ".ps1", ".sh", ".py")
    FRIENDLY_COMMAND_PATTERNS = [
        (re.compile(r"miniconda", re.IGNORECASE), "Installing MiniConda"),
    ]

    STATE_STYLES = {
        "pending": {"icon": "\u25cb", "fg": Theme.muted},
        "active": {"icon": "\u25cf", "fg": Theme.accent},
        "complete": {"icon": "\u2713", "fg": Theme.success},
        "error": {"icon": "\u26a0", "fg": Theme.warning},
        "paused": {"icon": "\u23f8", "fg": Theme.warning},
    }

    STATE_COPY = {
        "idle": {
            "headline": "BrainDrive is not installed. Use the Install button on the BrainDrive card to begin.",
            "card_primary": "Estimated time 5-10 minutes.",
            "card_secondary": "",
            "cta": None,
            "secondary_link": None,
            "open_logs": False,
            "auto_dismiss": None,
        },
        "installing": {
            "headline": "Installing BrainDrive",
            "card_primary": "Keep this window open. Progress will update below.",
            "card_secondary": "",
            "cta": None,
            "secondary_link": None,
            "open_logs": False,
            "auto_dismiss": None,
        },
        "paused": {
            "headline": "Install paused. Free up space then resume.",
            "card_primary": "Progress is saved; you can close this window.",
            "card_secondary": "",
            "cta": {"label": "Resume", "action": "resume", "tone": "primary"},
            "secondary_link": None,
            "open_logs": False,
            "auto_dismiss": None,
        },
        "starting": {
            "headline": "Starting BrainDrive services...",
            "card_primary": "Launching backend and frontend services.",
            "card_secondary": "",
            "cta": None,
            "secondary_link": None,
            "open_logs": False,
            "auto_dismiss": None,
        },
        "stopping": {
            "headline": "Stopping BrainDrive services...",
            "card_primary": "Stopping backend and frontend services.",
            "card_secondary": "",
            "cta": None,
            "secondary_link": None,
            "open_logs": False,
            "auto_dismiss": None,
        },
        "complete": {
            "headline": "Install complete. BrainDrive is ready.",
            "card_primary": "Launch BrainDrive from your desktop icon.",
            "card_secondary": "Your local AI is now ready to use.",
            "cta": None,
            "secondary_link": {"label": "View detailed log", "action": "viewLog"},
            "open_logs": False,
            "auto_dismiss": 5000,
        },
        "error": {
            "headline": "Install needs attention.",
            "card_primary": "Something went wrong. Copy the log or retry.",
            "card_secondary": "Log opened to the most recent error.",
            "cta": {"label": "Retry", "action": "retry", "tone": "danger"},
            "secondary_link": {"label": "Report issue", "action": "reportIssue"},
            "open_logs": True,
            "auto_dismiss": None,
        },
    }

    BELOW_HINTS = {
        "idle": "Below: Installation status, step tracker, and technical log.",
        "installing": "Below: Live progress bar, step tracker, and streaming logs.",
        "paused": "Below: Resume instructions, paused step, and log details.",
        "complete": "Below: Install log and system metadata.",
        "error": "Below: Error log, retry controls, and system metadata.",
    }

    STEP_PREFIX_PATTERN = re.compile(
        r"^\s*step\s*(?:\[\s*\d+\s*/\s*\d+\s*\]|\d+\s*/\s*\d+|\d+\s+of\s+\d+|\d+)\s*[:\-]?\s*",
        re.IGNORECASE,
    )

    LOG_ENTRY_LIMIT = 400
    PROGRESS_META_MIN_WIDTH = 200
    OPERATION_LABEL_FALLBACK_WIDTH = 360
    OPERATION_DETAILS_FALLBACK_WIDTH = 520
    SUPPORT_URL = "https://github.com/BrainDriveAI/BrainDrive-Install-System/issues/new/choose"

    def __init__(self, parent, inset=0, metadata=None, log_file_path=None, min_width=340, lock_width=True):
        self.parent = parent
        self.log_file_path = log_file_path
        self.metadata_values = metadata or {}
        self.action_handlers = {}
        self.current_state = "idle"
        self.log_open = False
        self.log_entries = []
        self.external_log_cache = []
        self._success_timer_id = None
        self._elapsed_job = None
        self._progress_visible = False
        self._install_started_at = None
        self._installed_status = False
        self._stop_flow_active = False
        self._operation_details_full_text = ""
        self._operation_label_full_text = ""
        self._operation_label_last_width = None

        self.colors = self._resolve_colors()
        frame_kwargs = {
            "bg": self.colors["bg"],
            "highlightbackground": self.colors["border"],
            "highlightthickness": 1,
            "bd": 0,
        }
        self.frame = tk.Frame(parent, **frame_kwargs)
        if lock_width:
            self.frame.configure(width=max(min_width, 320))
            self.frame.pack_propagate(False)
        else:
            self.frame.pack_propagate(True)

        self._build_layout(inset=inset)
        self.spinner = StatusSpinner(self.progress_header, self.operation_label)
        self.reset_step_states()
        self.reset_for_idle()
        self.set_metadata(self.metadata_values)
        self.register_action("viewLog", lambda: self.toggle_log_drawer(open_only=True))
        self.register_action("reportIssue", lambda: webbrowser.open(self.SUPPORT_URL))

        if self.log_file_path:
            self.set_log_file(self.log_file_path)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _resolve_colors(self):
        if Theme.active:
            return {
                "bg": Theme.panel_bg,
                "alt_bg": Theme.panel_bg_alt,
                "border": Theme.border_soft,
                "text": Theme.text,
                "muted": Theme.muted,
                "divider": Theme.border_soft,
            }
        return {
            "bg": "#f4f6fb",
            "alt_bg": "#ffffff",
            "border": "#d7dbe7",
            "text": "#0f172a",
            "muted": "#4a4f63",
            "divider": "#d7dbe7",
        }

    def _build_layout(self, inset=0):
        body = tk.Frame(self.frame, bg=self.colors["bg"])
        body.pack(fill=tk.BOTH, expand=True, padx=inset, pady=(12, 12))

        self._build_header(body)
        top_columns = tk.Frame(body, bg=self.colors["bg"])
        top_columns.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 12))
        left_width = 800
        right_width = 200
        top_columns.grid_columnconfigure(0, weight=5, uniform="status", minsize=left_width)
        top_columns.grid_columnconfigure(1, weight=4, uniform="status", minsize=right_width)
        top_columns.grid_rowconfigure(0, weight=1)

        left_column = tk.Frame(top_columns, bg=self.colors["bg"], width=left_width)
        left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left_column.grid_propagate(False)
        right_column = tk.Frame(top_columns, bg=self.colors["bg"], width=right_width)
        right_column.grid(row=0, column=1, sticky="nsew")
        right_column.grid_propagate(False)

        self._build_guidance_card(left_column)
        self._build_step_list(right_column)
        self._build_log_section(body)
        self._build_metadata_strip(body)
        self._build_shutdown_overlay()

    def _build_header(self, parent):
        header = tk.Frame(parent, bg=self.colors["bg"])
        header.pack(fill=tk.X, padx=20, pady=(8, 12))
        self.header_icon = tk.Label(
            header,
            text="\u25cf",
            font=("Segoe UI Symbol", 16),
            bg=self.colors["bg"],
            fg=Theme.accent if Theme.active else "#2563eb",
        )
        self.header_icon.pack(side=tk.LEFT, padx=(0, 8))

        self.headline_var = tk.StringVar(value=self.STATE_COPY["idle"]["headline"])
        self.headline_label = tk.Label(
            header,
            textvariable=self.headline_var,
            font=("Segoe UI", 14, "bold"),
            bg=self.colors["bg"],
            fg=self.colors["text"],
        )
        self.headline_label.pack(side=tk.LEFT, anchor="w")

    def _build_guidance_card(self, parent):
        card = tk.Frame(
            parent,
            bg=self.colors["alt_bg"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
            bd=0,
        )
        card.pack(fill=tk.X, expand=False, padx=0, pady=(0, 12))
        self.guidance_card = card

        self.card_primary_var = tk.StringVar()
        self.card_primary_label = tk.Label(
            card,
            textvariable=self.card_primary_var,
            font=("Segoe UI", 12, "bold"),
            wraplength=760,
            justify="center",
            anchor="center",
            bg=self.colors["alt_bg"],
            fg=self.colors["text"],
        )
        self.card_primary_label.pack(fill=tk.X, padx=16, pady=(16, 4))
        card.bind("<Configure>", self._handle_guidance_resize)

        self.card_secondary_var = tk.StringVar()
        tk.Label(
            card,
            textvariable=self.card_secondary_var,
            font=("Segoe UI", 10),
            wraplength=520,
            justify="left",
            bg=self.colors["alt_bg"],
            fg=self.colors["muted"],
        ).pack(fill=tk.X, padx=16, pady=(0, 12))

        self._build_progress_region(card)

        buttons = tk.Frame(card, bg=self.colors["alt_bg"])
        buttons.pack(fill=tk.X, padx=16, pady=(12, 8))

        self.cta_button = tk.Button(
            buttons,
            text="Install",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            padx=14,
            pady=6,
            command=self._handle_primary_cta,
        )
        self.cta_button.pack(side=tk.LEFT)

        self.secondary_link_button = tk.Button(
            buttons,
            text="View detailed log",
            font=("Segoe UI", 10, "underline"),
            fg=self.colors["muted"],
            bg=self.colors["alt_bg"],
            bd=0,
            relief=tk.FLAT,
            cursor="hand2",
            command=self._handle_secondary_link,
        )
        self.secondary_link_button.pack(side=tk.LEFT, padx=(12, 0))

        self.sections_hint_var = tk.StringVar(
            value="Below: Installation status, step tracker, and technical log."
        )
        tk.Label(
            card,
            textvariable=self.sections_hint_var,
            font=("Segoe UI", 9, "italic"),
            wraplength=520,
            justify="left",
            bg=self.colors["alt_bg"],
            fg=self.colors["muted"],
        ).pack(fill=tk.X, padx=16, pady=(4, 12))

        self._cta_action_key = None
        self._secondary_action_key = None

    def _handle_guidance_resize(self, event):
        """Keep the guidance text centered and on a single line when space allows."""
        if not getattr(self, "card_primary_label", None):
            return

        available_width = max(event.width - 32, 200)
        self.card_primary_label.configure(wraplength=available_width)

    def _build_progress_region(self, parent):
        region = tk.Frame(parent, bg=self.colors["alt_bg"])
        region.pack(fill=tk.X, padx=16, pady=(0, 12))
        self.progress_region = region

        self.progress_header = tk.Frame(region, bg=self.colors["alt_bg"])
        self.progress_header.pack(fill=tk.X)
        self.progress_header.grid_columnconfigure(0, weight=1)
        self.progress_header.grid_columnconfigure(1, weight=0, minsize=0)
        self._progress_meta_column_reserved = False

        self._operation_label_grid = {"row": 0, "column": 0, "sticky": "w", "padx": (0, 12)}
        self.operation_label = tk.Label(
            self.progress_header,
            text="",
            font=("Segoe UI", 11, "bold"),
            bg=self.colors["alt_bg"],
            fg=self.colors["text"],
            anchor="w",
            justify="left",
            wraplength=0,
        )
        self.operation_label.grid(**self._operation_label_grid)

        self.progress_meta_var = tk.StringVar(value="")
        self.progress_meta_label_inline = tk.Label(
            self.progress_header,
            textvariable=self.progress_meta_var,
            font=("Segoe UI", 9),
            bg=self.colors["alt_bg"],
            fg=self.colors["muted"],
            width=24,
            anchor="e",
            justify="right",
        )
        self._progress_meta_grid = {"row": 0, "column": 1, "sticky": "e"}
        self.progress_meta_label_inline.grid_remove()
        self.progress_header.bind("<Configure>", self._handle_progress_header_resize)
        self._set_progress_meta_column_enabled(False)
        self.progress_header.after(0, self._handle_progress_header_resize)

        self.operation_details_label = tk.Label(
            region,
            text="",
            font=("Segoe UI", 10, "italic"),
            justify="left",
            anchor="w",
            bg=self.colors["alt_bg"],
            fg=self.colors["muted"],
            wraplength=0,
            height=1,
        )
        self.operation_details_label.pack(anchor="w", fill=tk.X, pady=(2, 8))
        self.operation_details_label.bind("<Configure>", self._handle_operation_details_resize)

        self.activity_bar = ttk.Progressbar(
            region,
            mode="indeterminate",
            style="Indeterminate.Horizontal.TProgressbar",
        )
        self.progress_bar = ttk.Progressbar(region, maximum=100, mode="determinate")

        self._activity_running = False
        self._set_progress_visibility(False)

    def _build_step_list(self, parent):
        container = tk.Frame(parent, bg=self.colors["bg"])
        container.pack(fill=tk.BOTH, expand=True, padx=0, pady=(0, 8))

        tk.Label(
            container,
            text="Install steps",
            font=("Segoe UI", 11, "bold"),
            bg=self.colors["bg"],
            fg=self.colors["text"],
        ).pack(anchor="w", pady=(0, 8))

        self.step_rows = {}
        for step in self.STEP_ORDER:
            self.step_rows[step["key"]] = {
                "label": step["label"],
                "subtitle": step["subtitle"],
                "state": "pending",
            }

        self.step_ticker_slots = []
        for _ in range(2):
            row_frame = tk.Frame(container, bg=self.colors["bg"])
            row_frame.pack(fill=tk.X, pady=(0, 6))

            icon_label = tk.Label(
                row_frame,
                text=self.STATE_STYLES["pending"]["icon"],
                font=("Segoe UI Symbol", 14),
                width=2,
                bg=self.colors["bg"],
                fg=self.colors["muted"],
            )
            icon_label.pack(side=tk.LEFT, anchor="n", pady=(2, 0))

            text_frame = tk.Frame(row_frame, bg=self.colors["bg"])
            text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            title_label = tk.Label(
                text_frame,
                text="Waiting for updates",
                font=("Segoe UI", 11, "bold"),
                bg=self.colors["bg"],
                fg=self.colors["muted"],
            )
            title_label.pack(anchor="w")
            subtitle_label = tk.Label(
                text_frame,
                text="Installer will show recent steps here.",
                font=("Segoe UI", 9),
                bg=self.colors["bg"],
                fg=self.colors["muted"],
            )
            subtitle_label.pack(anchor="w")

            self.step_ticker_slots.append(
                {
                    "frame": row_frame,
                    "icon": icon_label,
                    "title": title_label,
                    "subtitle": subtitle_label,
                }
            )

        self._refresh_step_ticker()

    def _mark_step_progress(self, step_index, total_expected=None):
        total = len(self.STEP_KEYS)
        if total == 0:
            return
        if step_index >= total:
            for key in self.STEP_KEYS:
                self.step_rows[key]["state"] = "complete"
            self._refresh_step_ticker()
            return
        step_index = max(0, step_index)
        for idx, key in enumerate(self.STEP_KEYS):
            if idx < step_index:
                state = "complete"
            elif idx == step_index:
                state = "active"
            else:
                state = "pending"
            if key in self.step_rows:
                self.step_rows[key]["state"] = state
        self._refresh_step_ticker()

    def _refresh_step_ticker(self):
        order = [step["key"] for step in self.STEP_ORDER]
        previous_key = next(
            (key for key in reversed(order) if self.step_rows[key]["state"] in ("complete", "error")),
            None,
        )
        current_key = next(
            (key for key in order if self.step_rows[key]["state"] in ("active", "paused")),
            None,
        )
        if current_key is None:
            current_key = next((key for key in order if self.step_rows[key]["state"] == "pending"), None)

        entries = []
        if previous_key:
            entries.append(previous_key)
        if current_key and current_key not in entries:
            entries.append(current_key)
        if len(entries) < 2:
            for key in order:
                if key not in entries:
                    entries.append(key)
                if len(entries) == 2:
                    break

        for idx, slot in enumerate(self.step_ticker_slots):
            if idx < len(entries):
                key = entries[idx]
                data = self.step_rows[key]
                state = data["state"]
                display_state = state
                if key == current_key and display_state == "pending":
                    display_state = "active"
                style = self.STATE_STYLES.get(display_state, self.STATE_STYLES["pending"])
                slot["icon"].config(text=style["icon"], fg=style["fg"])
                slot["title"].config(text=data["label"], fg=style["fg"])
                slot["subtitle"].config(
                    text=self._format_step_subtitle(
                        data["subtitle"], display_state, key == previous_key, key == current_key
                    ),
                    fg=self.colors["muted"],
                )
            else:
                slot["icon"].config(text=self.STATE_STYLES["pending"]["icon"], fg=self.colors["muted"])
                slot["title"].config(text="Waiting for updates", fg=self.colors["muted"])
                slot["subtitle"].config(text="Installer will show recent steps here.", fg=self.colors["muted"])

    def _format_step_subtitle(self, subtitle, state, is_previous, is_current):
        if state == "complete" or is_previous:
            return f"Finished · {subtitle}"
        if state == "error":
            return f"Error · {subtitle}"
        if state == "paused":
            return f"Paused · {subtitle}"
        if state == "active" or is_current:
            return f"In progress · {subtitle}"
        return f"Up next · {subtitle}"

    def _build_log_section(self, parent):
        toggle_frame = tk.Frame(parent, bg=self.colors["bg"])
        toggle_frame.pack(fill=tk.X, padx=20)
        self.log_toggle_button = tk.Button(
            toggle_frame,
            text="Show technical details",
            font=("Segoe UI", 10, "underline"),
            bg=self.colors["bg"],
            fg=Theme.accent if Theme.active else "#2563eb",
            bd=0,
            relief=tk.FLAT,
            cursor="hand2",
            command=self.toggle_log_drawer,
        )
        self.log_toggle_button.pack(anchor="w", pady=(6, 0))

        self.log_frame = tk.Frame(
            parent,
            bg=self.colors["alt_bg"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
            bd=0,
        )
        self.log_text = tk.Text(
            self.log_frame,
            height=12,
            wrap="word",
            bg=Theme.sidebar_bg if Theme.active else "#0f172a",
            fg=Theme.text if Theme.active else "#f4f4f9",
            insertbackground=Theme.text if Theme.active else "#f4f4f9",
            relief=tk.FLAT,
            state="disabled",
        )
        scrollbar = ttk.Scrollbar(self.log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12, 0), pady=12)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 12), pady=12)

        controls = tk.Frame(self.log_frame, bg=self.colors["alt_bg"])
        controls.pack(fill=tk.X, padx=12, pady=(0, 12))
        button_style = "Dark.TButton" if Theme.active else None
        copy_kwargs = {"text": "Copy log", "command": self.copy_logs_to_clipboard}
        open_kwargs = {"text": "Open log file", "command": self.open_log_file}
        if button_style:
            copy_kwargs["style"] = button_style
            open_kwargs["style"] = button_style
        ttk.Button(controls, **copy_kwargs).pack(side=tk.LEFT)
        ttk.Button(controls, **open_kwargs).pack(side=tk.LEFT, padx=(12, 0))

        self.log_frame.pack_forget()

    def _build_metadata_strip(self, parent):
        strip = tk.Frame(parent, bg=self.colors["alt_bg"])
        strip.pack(fill=tk.X, padx=20, pady=(8, 0))
        self.metadata_container = strip
        self._metadata_pack = {"fill": tk.X, "padx": 20, "pady": (8, 0)}
        self.metadata_visible = True
        self.metadata_labels = {}
        for key, label in [("os", "OS"), ("disk", "Storage"), ("installPath", "Install path"), ("version", "Version")]:
            text_var = tk.StringVar(value="")
            tk.Label(
                strip,
                textvariable=text_var,
                font=("Segoe UI", 9),
                bg=self.colors["alt_bg"],
                fg=self.colors["muted"],
                anchor="w",
                justify="left",
                wraplength=360,
            ).pack(anchor="w")
            self.metadata_labels[key] = text_var

    def _build_shutdown_overlay(self):
        overlay_kwargs = {"bg": Theme.panel_bg_alt if Theme.active else "#f8fafc", "bd": 0}
        self.shutdown_overlay = tk.Frame(self.frame, **overlay_kwargs)
        self.shutdown_overlay.place(relwidth=1, relheight=1)
        self.shutdown_overlay.lower()

        label_kwargs = {
            "text": "Shutting down BrainDrive...",
            "font": ("Segoe UI", 12, "bold"),
            "bg": overlay_kwargs["bg"],
            "fg": Theme.text if Theme.active else "#111827",
        }
        self.shutdown_label = tk.Label(self.shutdown_overlay, **label_kwargs)
        self.shutdown_label.pack(pady=(32, 12))
        self.shutdown_bar = ttk.Progressbar(
            self.shutdown_overlay,
            mode="indeterminate",
            length=280,
            style="Indeterminate.Horizontal.TProgressbar",
        )
        self.shutdown_bar.pack()
        self.shutdown_overlay.lower()

    # ------------------------------------------------------------------
    # Public API consumed by the installer
    # ------------------------------------------------------------------

    def get_components(self):
        """Return widgets consumed by StatusUpdater (step label, detail label, progress bar)."""
        return self.operation_label, self.operation_details_label, self.progress_bar

    def set_installed_status(self, installed: bool):
        """Update idle headline to reflect whether BrainDrive is installed."""
        prev = self._installed_status
        self._installed_status = bool(installed)
        if self.current_state == "idle":
            self.headline_var.set(self._idle_headline())
            self.card_primary_var.set(self._idle_card_message())
            self._set_operation_label(self._idle_status_message())
            self._stop_flow_active = False
        elif installed and not self._progress_visible and self.current_state in {"complete"}:
            self.set_primary_state("idle")

    def register_action(self, action_key, handler):
        """Expose CTA callbacks."""
        if action_key:
            self.action_handlers[action_key] = handler

    def apply_status_update(self, step_text, details_text, progress_value, eta_seconds=None):
        """Mirror StatusUpdater events inside the redesigned view."""
        raw_step = (step_text or "").strip()
        raw_details = (details_text or "").strip()
        clean_step = self._strip_step_prefix(raw_step)
        display_step = self._summarize_text(clean_step)
        display_details = self._summarize_text(raw_details, width=110)
        match = re.search(r"Step\s+(\d+)\s*/\s*(\d+)", raw_step, re.IGNORECASE)

        try:
            numeric_progress = float(progress_value)
        except (TypeError, ValueError):
            numeric_progress = 0.0
        inferred_state = self._infer_state(raw_step, raw_details, numeric_progress)
        if inferred_state == "stopping":
            self._stop_flow_active = True
        elif inferred_state in {"starting", "idle", "complete", "error"}:
            self._stop_flow_active = False

        # If we are in the middle of a stop flow, keep treating updates as stopping
        if self._stop_flow_active and inferred_state not in {"stopping"}:
            inferred_state = "stopping"

        show_bar = inferred_state in {"installing", "paused"} and not self._stop_flow_active

        if match:
            try:
                step_num = max(1, int(match.group(1)))
                self._mark_step_progress(step_num - 1, int(match.group(2)))
            except Exception:
                pass

        if inferred_state == "idle":
            self._set_operation_label(self._idle_status_message())
            self._set_operation_details_text(self._idle_card_message())
        elif inferred_state == "starting":
            self._set_operation_label("Starting BrainDrive")
            self._set_operation_details_text(display_details or "Launching backend and frontend services.")
        elif inferred_state == "stopping":
            self._set_operation_label("Stopping BrainDrive")
            self._set_operation_details_text(display_details or "Stopping backend and frontend services.")
        else:
            self._set_operation_label(display_step or self.headline_var.get())
            self._set_operation_details_text(display_details or self.card_primary_var.get())
        self._set_progress_visibility(show_bar)
        self._update_progress_meta_text(numeric_progress, eta_seconds)
        self._append_log_entry(raw_step, raw_details)
        self.set_primary_state(inferred_state)
        if numeric_progress >= 100:
            self._mark_step_progress(len(self.STEP_KEYS))

    def reset_step_states(self):
        """Reset all steps to pending."""
        for key in self.step_rows:
            self.step_rows[key]["state"] = "pending"
        self._refresh_step_ticker()

    def reset_for_idle(self):
        """Restore idle copy and progress placeholders."""
        self._cancel_success_auto_dismiss()
        self.progress_bar.config(value=0)
        self._set_progress_visibility(False)
        self._set_operation_details_text(self._idle_card_message())
        self._set_operation_label(self._idle_status_message())
        if hasattr(self, "spinner"):
            self.spinner.stop()
        self.set_primary_state("idle")

    def set_step_state(self, key, state):
        """Update icon + color for a given step."""
        if key not in self.step_rows:
            return
        self.step_rows[key]["state"] = state
        self._refresh_step_ticker()

    def set_metadata(self, metadata):
        """Populate OS / disk / path / version in the footer strip."""
        if not metadata:
            return
        self.metadata_values.update(metadata)
        label_map = {
            "os": "OS",
            "disk": "Storage",
            "installPath": "Install path",
            "version": "Version",
        }
        for key, var in self.metadata_labels.items():
            value = self.metadata_values.get(key)
            if not value:
                var.set("")
            else:
                label = label_map.get(key, key.title())
                var.set(f"{label}: {value}")

    def set_log_file(self, path):
        self.log_file_path = path
        if self.log_open:
            self._refresh_log_from_file()

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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _set_progress_visibility(self, show_bar):
        if show_bar:
            if not self.activity_bar.winfo_ismapped():
                self.activity_bar.pack(fill=tk.X, pady=(0, 4))
            if not self._activity_running:
                try:
                    self.activity_bar.start(12)
                except Exception:
                    pass
                self._activity_running = True
            if not self.progress_bar.winfo_ismapped():
                self.progress_bar.pack(fill=tk.X, pady=(0, 4))
            if not self.progress_meta_label_inline.winfo_ismapped():
                self.progress_meta_label_inline.grid(**self._progress_meta_grid)
            self._set_progress_meta_column_enabled(True)
        else:
            if self._activity_running:
                try:
                    self.activity_bar.stop()
                except Exception:
                    pass
                self._activity_running = False
            if self.activity_bar.winfo_ismapped():
                self.activity_bar.pack_forget()
            if self.progress_bar.winfo_ismapped():
                self.progress_bar.pack_forget()
            if self.progress_meta_label_inline.winfo_ismapped():
                self.progress_meta_label_inline.grid_remove()
            self._set_progress_meta_column_enabled(False)
        self._progress_visible = show_bar

    def _handle_progress_header_resize(self, _event=None):
        if (
            not hasattr(self, "progress_header")
            or not hasattr(self, "operation_label")
            or not hasattr(self, "progress_meta_label_inline")
        ):
            return
        try:
            header_width = self.progress_header.winfo_width()
        except Exception:
            return
        if header_width <= 1:
            return
        reserved = 0
        if getattr(self, "_progress_meta_column_reserved", False):
            try:
                reserved = max(
                    self.PROGRESS_META_MIN_WIDTH,
                    self.progress_meta_label_inline.winfo_width() or 0,
                )
            except Exception:
                reserved = self.PROGRESS_META_MIN_WIDTH
        padding = 16
        available = max(140, header_width - reserved - padding)
        self._apply_operation_label_truncation(available)

    def _apply_operation_label_truncation(self, max_width=None):
        if not hasattr(self, "operation_label"):
            return
        text = getattr(self, "_operation_label_full_text", "")
        if not text:
            self.operation_label.config(text="")
            return
        width = max_width or self._operation_label_last_width
        if not width or width <= 0:
            try:
                width = self.operation_label.winfo_width()
            except Exception:
                width = None
        if not width or width <= 0:
            width = self.OPERATION_LABEL_FALLBACK_WIDTH
        truncated = self._truncate_text_to_width(text, self.operation_label, width)
        self.operation_label.config(text=truncated)
        self._operation_label_last_width = width

    def _set_progress_meta_column_enabled(self, enabled):
        if not hasattr(self, "progress_header"):
            return
        if getattr(self, "_progress_meta_column_reserved", False) == enabled:
            return
        minsize = self.PROGRESS_META_MIN_WIDTH if enabled else 0
        self.progress_header.grid_columnconfigure(1, minsize=minsize)
        self._progress_meta_column_reserved = enabled
        self._handle_progress_header_resize()

    def _handle_operation_details_resize(self, event):
        self._apply_operation_details_truncation(event.width if event else None)

    def _set_operation_details_text(self, text):
        sanitized = re.sub(r"\s+", " ", (text or ""))
        self._operation_details_full_text = sanitized.strip()
        self._apply_operation_details_truncation()

    def _apply_operation_details_truncation(self, max_width=None):
        if not hasattr(self, "operation_details_label"):
            return
        text = self._operation_details_full_text
        if not text:
            self.operation_details_label.config(text="")
            return
        width = max_width
        if not width or width <= 0:
            try:
                width = self.operation_details_label.winfo_width()
            except Exception:
                width = None
        if not width or width <= 0:
            width = self.OPERATION_DETAILS_FALLBACK_WIDTH
        truncated = self._truncate_text_to_width(text, self.operation_details_label, width)
        self.operation_details_label.config(text=truncated)

    @staticmethod
    def _truncate_text_to_width(text, widget, max_width):
        text = (text or "").strip()
        if not text:
            return ""
        ellipsis = "..."
        try:
            font = tkfont.Font(font=widget.cget("font"))
        except tk.TclError:
            return textwrap.shorten(text, width=90, placeholder=ellipsis)
        if font.measure(text) <= max_width:
            return text
        low, high = 0, len(text)
        best = ellipsis
        while low <= high:
            mid = (low + high) // 2
            candidate = text[:mid].rstrip()
            if candidate:
                candidate = f"{candidate}{ellipsis}"
            else:
                candidate = ellipsis
            if font.measure(candidate) <= max_width:
                best = candidate
                low = mid + 1
            else:
                high = mid - 1
        return best

    def _schedule_elapsed_update(self):
        if self._install_started_at is None:
            return

        if self._elapsed_job is not None:
            return

        def _tick():
            if self._install_started_at is None:
                self._cancel_elapsed_update()
                return
            self._update_progress_meta_text(float(self.progress_bar["value"]))
            self._elapsed_job = self.progress_bar.after(1000, _tick)

        self._elapsed_job = self.progress_bar.after(1000, _tick)

    def _cancel_elapsed_update(self):
        if self._elapsed_job is not None:
            try:
                self.progress_bar.after_cancel(self._elapsed_job)
            except Exception:
                pass
            self._elapsed_job = None

    def _idle_headline(self):
        return (
            self.IDLE_HEADLINE_INSTALLED
            if self._installed_status
            else self.IDLE_HEADLINE_NOT_INSTALLED
        )

    def _idle_card_message(self):
        return (
            self.IDLE_CARD_INSTALLED
            if self._installed_status
            else self.IDLE_CARD_NOT_INSTALLED
        )

    def _idle_status_message(self):
        return (
            self.IDLE_STATUS_INSTALLED
            if self._installed_status
            else self.IDLE_STATUS_NOT_INSTALLED
        )

    def _set_operation_label(self, text):
        sanitized = re.sub(r"\s+", " ", (text or "")).strip()
        self._operation_label_full_text = sanitized
        if sanitized:
            if not self.operation_label.winfo_ismapped():
                self.operation_label.grid(**self._operation_label_grid)
            self._apply_operation_label_truncation()
        else:
            if self.operation_label.winfo_ismapped():
                self.operation_label.grid_remove()
            self.operation_label.config(text="")
        self._handle_progress_header_resize()

    def _strip_step_prefix(self, text):
        sanitized = (text or "").strip()
        if not sanitized:
            return ""
        stripped = self.STEP_PREFIX_PATTERN.sub("", sanitized, count=1).strip()
        return stripped or sanitized

    def _summarize_text(self, text, width=96):
        text = re.sub(r"\s+", " ", (text or "")).strip()
        if not text:
            return ""
        command_candidate = None
        command_match = re.search(r"running\s+command:\s*\"?([^\s\"]+)", text, re.IGNORECASE)
        if command_match:
            command_candidate = command_match.group(1).strip().strip('"')
        else:
            tokens = text.split()
            if tokens:
                token = tokens[0].strip('"')
                token_lower = token.lower()
                if any(token_lower.endswith(ext) for ext in self.EXEC_EXTENSIONS):
                    command_candidate = token
        if command_candidate:
            base = Path(command_candidate).name or command_candidate
            friendly = self._friendly_command_title(command_candidate)
            if friendly:
                return friendly
            return f"Running {base}"
        if len(text) <= width:
            return text
        return textwrap.shorten(text, width=width, placeholder="...")

    @classmethod
    def _friendly_command_title(cls, command_path):
        for pattern, label in cls.FRIENDLY_COMMAND_PATTERNS:
            if pattern.search(command_path):
                return label
        return None

    def _update_progress_meta_text(self, progress_value, eta_seconds=None):
        total = len(self.STEP_ORDER)
        states = [self.step_rows[step["key"]]["state"] for step in self.STEP_ORDER]
        completed = sum(1 for state in states if state == "complete")
        current_index = next(
            (idx for idx, state in enumerate(states) if state in ("active", "paused")), None
        )
        if current_index is None:
            if completed >= total and total:
                current_index = total - 1
            else:
                current_index = completed
        step_number = min(total, current_index + 1) if total else 0
        parts = []
        if total:
            parts.append(f"Step {step_number} of {total}")
        if self._install_started_at:
            elapsed = max(0.0, time.monotonic() - self._install_started_at)
            parts.append(self._format_elapsed(elapsed))
        self.progress_meta_var.set(" \u2022 ".join(parts))

    def _format_eta(self, seconds):
        try:
            seconds = max(0, int(seconds))
        except (TypeError, ValueError):
            return "--:--"
        minutes, remainder = divmod(seconds, 60)
        if minutes > 99:
            return "99:59+"
        return f"{minutes:02d}:{remainder:02d}"

    def _format_elapsed(self, seconds):
        seconds = int(seconds)
        minutes, remainder = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}h {minutes:02d}m {remainder:02d}s"
        if minutes:
            return f"{minutes}m {remainder:02d}s"
        return f"{remainder}s"

    def _infer_state(self, step_text, details_text, progress_value):
        text_blob = f"{step_text} {details_text}".lower()
        if "services stopped" in text_blob:
            self._stop_flow_active = False
            return "idle"
        if any(keyword in text_blob for keyword in self.STARTING_KEYWORDS):
            return "starting"
        if any(keyword in text_blob for keyword in self.STOPPING_KEYWORDS):
            return "stopping"
        if "error" in text_blob or "fail" in text_blob:
            return "error"
        if "paused" in text_blob or "resume" in text_blob:
            return "paused"
        if "complete" in text_blob or progress_value >= 100:
            return "complete"
        if progress_value > 0:
            return "installing"
        return "idle"

    def set_primary_state(self, state):
        copy = self.STATE_COPY.get(state, self.STATE_COPY["idle"])
        self.current_state = state
        if state == "stopping":
            self._stop_flow_active = True
        elif state == "idle" or state not in {"installing", "paused"}:
            self._stop_flow_active = False
        if state == "idle":
            self.headline_var.set(self._idle_headline())
            self.card_primary_var.set(self._idle_card_message())
            self._set_operation_label(self._idle_status_message())
        elif state in {"starting", "stopping"}:
            self.headline_var.set(copy["headline"])
            self.card_primary_var.set(copy["card_primary"])
            self._set_operation_label(self.headline_var.get())
        else:
            self.headline_var.set(copy["headline"])
            self.card_primary_var.set(copy["card_primary"])
        self.card_secondary_var.set(copy.get("card_secondary", ""))
        if hasattr(self, "sections_hint_var"):
            self.sections_hint_var.set(self.BELOW_HINTS.get(state, self.BELOW_HINTS["idle"]))
        self._configure_cta(copy.get("cta"))
        self._configure_secondary_link(copy.get("secondary_link"))
        if copy.get("open_logs"):
            self.toggle_log_drawer(open_only=True)
        if copy.get("auto_dismiss"):
            self._schedule_success_auto_dismiss(copy["auto_dismiss"])
        else:
            self._cancel_success_auto_dismiss()
        self._set_metadata_visibility(state not in {"idle", "complete"})
        if state == "idle":
            self._set_operation_label(self._idle_status_message())
            self._install_started_at = None
            self._cancel_elapsed_update()
        elif state in {"installing", "paused"}:
            if self._install_started_at is None:
                self._install_started_at = time.monotonic()
            self._schedule_elapsed_update()
        else:
            # complete / error / starting / stopping states keep final elapsed time hidden
            self._cancel_elapsed_update()
            self._set_progress_visibility(False)

    def _configure_cta(self, cta):
        self.cta_button.pack_forget()
        if not cta:
            self._cta_action_key = None
            return
        self.cta_button.pack(side=tk.LEFT)
        tone = cta.get("tone", "primary")
        if tone == "danger":
            self.cta_button.config(bg=Theme.danger, fg="#0f172a")
        else:
            accent = Theme.accent if Theme.active else "#2563eb"
            self.cta_button.config(bg=accent, fg="#020617")
        self.cta_button.config(text=cta["label"], state=tk.NORMAL)
        self._cta_action_key = cta.get("action")

    def _configure_secondary_link(self, config):
        self.secondary_link_button.pack_forget()
        if not config:
            self._secondary_action_key = None
            return
        self.secondary_link_button.config(text=config["label"])
        self.secondary_link_button.pack(side=tk.LEFT, padx=(12, 0))
        self._secondary_action_key = config.get("action")

    def _handle_primary_cta(self):
        if self._cta_action_key:
            handler = self.action_handlers.get(self._cta_action_key)
            if handler:
                handler()

    def _handle_secondary_link(self):
        if self._secondary_action_key:
            handler = self.action_handlers.get(self._secondary_action_key)
            if handler:
                handler()

    def toggle_log_drawer(self, open_only=False):
        if self.log_open and open_only:
            self._refresh_log_from_file()
            return

        if not self.log_open:
            self.log_frame.pack(fill=tk.BOTH, expand=False, padx=20, pady=(8, 16))
            self.log_open = True
            self.log_toggle_button.config(text="Hide technical details")
            self._refresh_log_from_file()
        else:
            if open_only:
                return
            self.log_frame.pack_forget()
            self.log_open = False
            self.log_toggle_button.config(text="Show technical details")

    def _refresh_log_from_file(self):
        if not self.log_file_path or not os.path.exists(self.log_file_path):
            self.external_log_cache = []
        else:
            try:
                with open(self.log_file_path, "r", encoding="utf-8", errors="ignore") as handle:
                    lines = handle.readlines()
                self.external_log_cache = [line.rstrip("\n") for line in lines[-self.LOG_ENTRY_LIMIT :]]
            except Exception:
                self.external_log_cache = []
        self._write_log_text()

    def _append_log_entry(self, headline, details):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {headline}"
        if details:
            entry += f" — {details}"
        self.log_entries.append(entry)
        if len(self.log_entries) > self.LOG_ENTRY_LIMIT:
            self.log_entries = self.log_entries[-self.LOG_ENTRY_LIMIT :]
        if self.log_open:
            self._write_log_text()

    def _write_log_text(self):
        lines = self.external_log_cache + self.log_entries
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        if lines:
            self.log_text.insert(tk.END, "\n".join(lines) + "\n")
        self.log_text.configure(state="disabled")
        self.log_text.see(tk.END)

    def copy_logs_to_clipboard(self):
        content = self.log_text.get("1.0", tk.END).strip()
        if not content:
            return
        try:
            self.frame.clipboard_clear()
            self.frame.clipboard_append(content)
        except Exception:
            pass

    def open_log_file(self):
        if not self.log_file_path or not os.path.exists(self.log_file_path):
            return
        try:
            if os.name == "nt":
                os.startfile(self.log_file_path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", self.log_file_path])
            else:
                subprocess.Popen(["xdg-open", self.log_file_path])
        except Exception:
            pass

    def _schedule_success_auto_dismiss(self, delay_ms):
        self._cancel_success_auto_dismiss()
        self._success_timer_id = self.frame.after(delay_ms, self._on_success_dismiss)

    def _cancel_success_auto_dismiss(self):
        if self._success_timer_id:
            try:
                self.frame.after_cancel(self._success_timer_id)
            except Exception:
                pass
            self._success_timer_id = None

    def _on_success_dismiss(self):
        self.headline_var.set("BrainDrive installed successfully.")
        self.card_primary_var.set("Click start above to launch BrainDrive.")
        self._success_timer_id = None
        self._set_metadata_visibility(True)

    def _set_metadata_visibility(self, visible):
        if not hasattr(self, "metadata_container"):
            return
        if visible and not self.metadata_visible:
            self.metadata_container.pack(**self._metadata_pack)
            self.metadata_visible = True
        elif not visible and self.metadata_visible:
            self.metadata_container.pack_forget()
            self.metadata_visible = False
