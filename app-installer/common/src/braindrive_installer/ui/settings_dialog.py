import os
import socket
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from braindrive_installer.ui.theme import Theme
from typing import Callable
from braindrive_installer.ui.settings_manager import BrainDriveSettingsManager

class BrainDriveSettingsDialog:
    """Settings configuration dialog for BrainDrive."""
    
    def __init__(self, parent, settings_manager: BrainDriveSettingsManager, on_apply: Callable = None):
        self.parent = parent
        self.settings_manager = settings_manager
        self.on_apply = on_apply
        self.dialog = None
        self.widgets = {}
        self.port_indicators = {}
        self._port_update_job = None
        
    def show(self):
        """Show the settings dialog"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("BrainDrive Configuration Settings")
        self.dialog.geometry("600x500")
        self.dialog.resizable(True, True)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # Apply mac dark theme to match main UI
        if Theme.active:
            try:
                Theme.apply(self.dialog)
                self.dialog.configure(bg=Theme.bg)
            except Exception:
                pass
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (500 // 2)
        self.dialog.geometry(f"600x500+{x}+{y}")
        
        self._create_widgets()
        self._load_current_settings()
        
    def _create_widgets(self):
        """Create all dialog widgets"""
        # Main content frame
        main_frame = ttk.Frame(self.dialog) if not Theme.active else ttk.Frame(self.dialog, style="Dark.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))
        
        # Button frame at the bottom of dialog (not inside main_frame)
        button_frame = ttk.Frame(self.dialog) if not Theme.active else ttk.Frame(self.dialog, style="Dark.TFrame")
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Add buttons with better spacing
        reset_btn = ttk.Button(button_frame, text="Reset to Defaults", command=self._reset_defaults,
                               style=("Dark.TButton" if Theme.active else None))
        reset_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        cancel_btn = ttk.Button(button_frame, text="Cancel", command=self._cancel,
                                style=("Dark.TButton" if Theme.active else None))
        cancel_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        apply_btn = ttk.Button(button_frame, text="Apply & Save", command=self._apply_settings,
                               style=("Dark.TButton" if Theme.active else None))
        apply_btn.pack(side=tk.RIGHT, padx=(5, 5))
        
        # Notebook for tabbed sections
        notebook = ttk.Notebook(main_frame) if not Theme.active else ttk.Notebook(main_frame, style="Dark.TNotebook")
        notebook.pack(fill=tk.BOTH, expand=True)

        if Theme.active:
            install_tab = ttk.Frame(notebook, padding=10, style="Dark.TFrame")
            network_tab = ttk.Frame(notebook, padding=10, style="Dark.TFrame")
            security_tab = ttk.Frame(notebook, padding=10, style="Dark.TFrame")
            advanced_tab = ttk.Frame(notebook, padding=10, style="Dark.TFrame")
        else:
            install_tab = ttk.Frame(notebook, padding=10)
            network_tab = ttk.Frame(notebook, padding=10)
            security_tab = ttk.Frame(notebook, padding=10)
            advanced_tab = ttk.Frame(notebook, padding=10)

        notebook.add(install_tab, text="Installation")
        notebook.add(network_tab, text="Network")
        notebook.add(security_tab, text="Security")
        notebook.add(advanced_tab, text="Advanced")

        # Installation tab
        (ttk.Label(install_tab, text="Install Location:",
                   style=("Dark.TLabel" if Theme.active else None))
         .grid(row=0, column=0, sticky=tk.W, padx=(0, 5), pady=(0, 5)))
        self.widgets['install_path'] = ttk.Entry(install_tab, width=45,
                                                 style=("Dark.TEntry" if Theme.active else None))
        self.widgets['install_path'].grid(row=0, column=1, sticky=tk.W+tk.E, padx=(0, 5), pady=(0, 5))

        browse_btn = ttk.Button(install_tab, text="Browse…", command=self._browse_install_path,
                                style=("Dark.TButton" if Theme.active else None))
        browse_btn.grid(row=0, column=2, sticky=tk.E, pady=(0, 5))
        self.widgets['install_browse'] = browse_btn

        install_help = ttk.Label(
            install_tab,
            text="Used when installing BrainDrive. Changes apply on the next installation.",
            foreground=(Theme.muted if Theme.active else "gray"),
            style=("Dark.TLabel" if Theme.active else None)
        )
        install_help.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))

        install_tab.columnconfigure(1, weight=1)

        # Network tab
        (ttk.Label(network_tab, text="Backend Host:", style=("Dark.TLabel" if Theme.active else None))
         .grid(row=0, column=0, sticky=tk.W, padx=(0, 5)))
        self.widgets['backend_host'] = ttk.Entry(network_tab, width=20,
                                                 style=("Dark.TEntry" if Theme.active else None))
        self.widgets['backend_host'].grid(row=0, column=1, padx=(0, 20))
        
        (ttk.Label(network_tab, text="Port:", style=("Dark.TLabel" if Theme.active else None))
         .grid(row=0, column=2, sticky=tk.W, padx=(0, 5)))
        self.widgets['backend_port'] = ttk.Entry(network_tab, width=8,
                                                 style=("Dark.TEntry" if Theme.active else None))
        self.widgets['backend_port'].grid(row=0, column=3)
        
        (ttk.Label(network_tab, text="Frontend Host:", style=("Dark.TLabel" if Theme.active else None))
         .grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0)))
        self.widgets['frontend_host'] = ttk.Entry(network_tab, width=20,
                                                  style=("Dark.TEntry" if Theme.active else None))
        self.widgets['frontend_host'].grid(row=1, column=1, padx=(0, 20), pady=(5, 0))
        
        (ttk.Label(network_tab, text="Port:", style=("Dark.TLabel" if Theme.active else None))
         .grid(row=1, column=2, sticky=tk.W, padx=(0, 5), pady=(5, 0)))
        self.widgets['frontend_port'] = ttk.Entry(network_tab, width=8,
                                                  style=("Dark.TEntry" if Theme.active else None))
        self.widgets['frontend_port'].grid(row=1, column=3, pady=(5, 0))

        # Port status indicators
        backend_status = ttk.Frame(network_tab) if not Theme.active else ttk.Frame(network_tab, style="Dark.TFrame")
        backend_status.grid(row=0, column=4, sticky=tk.W)
        backend_canvas = tk.Canvas(backend_status, width=14, height=14, highlightthickness=0,
                                   bg=(Theme.panel_bg if Theme.active else None))
        backend_canvas.pack(side=tk.LEFT)
        backend_circle = backend_canvas.create_oval(2, 2, 12, 12, fill="#9e9e9e", outline="")
        backend_label = ttk.Label(backend_status, text="Checking...", width=10,
                                  style=("Dark.TLabel" if Theme.active else None))
        backend_label.pack(side=tk.LEFT, padx=(4, 0))
        self.port_indicators['backend'] = {
            'canvas': backend_canvas,
            'circle': backend_circle,
            'label': backend_label,
        }

        frontend_status = ttk.Frame(network_tab) if not Theme.active else ttk.Frame(network_tab, style="Dark.TFrame")
        frontend_status.grid(row=1, column=4, sticky=tk.W, pady=(5, 0))
        frontend_canvas = tk.Canvas(frontend_status, width=14, height=14, highlightthickness=0,
                                    bg=(Theme.panel_bg if Theme.active else None))
        frontend_canvas.pack(side=tk.LEFT)
        frontend_circle = frontend_canvas.create_oval(2, 2, 12, 12, fill="#9e9e9e", outline="")
        frontend_label = ttk.Label(frontend_status, text="Checking...", width=10,
                                   style=("Dark.TLabel" if Theme.active else None))
        frontend_label.pack(side=tk.LEFT, padx=(4, 0))
        self.port_indicators['frontend'] = {
            'canvas': frontend_canvas,
            'circle': frontend_circle,
            'label': frontend_label,
        }
        
        for col in range(5):
            network_tab.columnconfigure(col, weight=0)
        network_tab.columnconfigure(1, weight=1)

        # Security tab
        self.widgets['enable_registration'] = tk.BooleanVar()
        ttk.Checkbutton(security_tab, text="Enable Registration", variable=self.widgets['enable_registration'],
                        style=("Dark.TCheckbutton" if Theme.active else None)).grid(row=0, column=0, sticky=tk.W)
        
        self.widgets['enable_api_docs'] = tk.BooleanVar()
        ttk.Checkbutton(security_tab, text="Enable API Docs", variable=self.widgets['enable_api_docs'],
                        style=("Dark.TCheckbutton" if Theme.active else None)).grid(row=0, column=1, sticky=tk.W, padx=(20, 0))
        
        self.widgets['enable_metrics'] = tk.BooleanVar()
        ttk.Checkbutton(security_tab, text="Enable Metrics", variable=self.widgets['enable_metrics'],
                        style=("Dark.TCheckbutton" if Theme.active else None)).grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        self.widgets['debug_mode'] = tk.BooleanVar()
        ttk.Checkbutton(security_tab, text="Debug Mode", variable=self.widgets['debug_mode'],
                        style=("Dark.TCheckbutton" if Theme.active else None)).grid(row=1, column=1, sticky=tk.W, padx=(20, 0), pady=(5, 0))
        
        # Advanced tab
        (ttk.Label(advanced_tab, text="Database Path:", style=("Dark.TLabel" if Theme.active else None))
         .grid(row=0, column=0, sticky=tk.W, padx=(0, 5)))
        self.widgets['database_path'] = ttk.Entry(advanced_tab, width=40,
                                                  style=("Dark.TEntry" if Theme.active else None))
        self.widgets['database_path'].grid(row=0, column=1, columnspan=2, sticky=tk.W+tk.E, padx=(0, 5))
        
        (ttk.Label(advanced_tab, text="Log Level:", style=("Dark.TLabel" if Theme.active else None))
         .grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0)))
        self.widgets['log_level'] = ttk.Combobox(advanced_tab, width=15,
                                                 values=["debug", "info", "warning", "error"], state="readonly",
                                                 style=("Dark.TCombobox" if Theme.active else None))
        self.widgets['log_level'].grid(row=1, column=1, pady=(5, 0))
        
        advanced_tab.columnconfigure(1, weight=1)
        
        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding=10,
                                      style=("Dark.TLabelframe" if Theme.active else None))
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        if Theme.active:
            self.widgets['status_label'] = ttk.Label(status_frame, text="✓ Settings valid", style="DarkSuccess.TLabel")
        else:
            self.widgets['status_label'] = ttk.Label(status_frame, text="✓ Settings valid", foreground="green")
        self.widgets['status_label'].pack(anchor=tk.W)
        
        # Warning label
        if Theme.active:
            self.widgets['warning_label'] = ttk.Label(status_frame, text="⚠ Warning: Changing ports requires restart", style="DarkWarning.TLabel")
        else:
            self.widgets['warning_label'] = ttk.Label(status_frame, text="⚠ Warning: Changing ports requires restart", foreground="orange")
        self.widgets['warning_label'].pack(anchor=tk.W)
        
        
        # Bind validation
        for widget_name, widget in self.widgets.items():
            if isinstance(widget, ttk.Entry):
                widget.bind('<KeyRelease>', self._validate_settings)
            elif isinstance(widget, ttk.Combobox):
                widget.bind('<<ComboboxSelected>>', self._validate_settings)
    
    def _load_current_settings(self):
        """Load current settings into dialog widgets"""
        settings = self.settings_manager.settings

        # Installation settings
        install_path = settings.get('installation', {}).get('path', '')
        install_entry = self.widgets.get('install_path')
        if install_entry:
            install_entry.config(state=tk.NORMAL)
            install_entry.delete(0, tk.END)
            install_entry.insert(0, install_path)

        browse_btn = self.widgets.get('install_browse')
        backend_dir = os.path.join(self.settings_manager.installation_path, 'backend')
        frontend_dir = os.path.join(self.settings_manager.installation_path, 'frontend')
        install_locked = os.path.exists(backend_dir) and os.path.exists(frontend_dir)
        if install_locked:
            if install_entry:
                install_entry.config(state=tk.DISABLED)
            if browse_btn:
                browse_btn.config(state=tk.DISABLED)
        else:
            if browse_btn:
                browse_btn.config(state=tk.NORMAL)
        
        # Network settings
        self.widgets['backend_host'].insert(0, settings['network']['backend_host'])
        self.widgets['backend_port'].insert(0, str(settings['network']['backend_port']))
        self.widgets['frontend_host'].insert(0, settings['network']['frontend_host'])
        self.widgets['frontend_port'].insert(0, str(settings['network']['frontend_port']))
        
        # Security settings
        self.widgets['enable_registration'].set(settings['security']['enable_registration'])
        self.widgets['enable_api_docs'].set(settings['security']['enable_api_docs'])
        self.widgets['enable_metrics'].set(settings['security']['enable_metrics'])
        self.widgets['debug_mode'].set(settings['security']['debug_mode'])
        
        
        # Advanced settings
        self.widgets['database_path'].insert(0, settings['advanced']['database_path'])
        self.widgets['log_level'].set(settings['advanced']['log_level'])
        
        # Initial validation
        self._validate_settings()
    
    def _validate_settings(self, event=None):
        """Validate current settings and update status"""
        try:
            # Create temporary settings for validation
            temp_settings = self.settings_manager.settings.copy()
            
            # Update with current values
            temp_settings.setdefault('installation', {})
            temp_settings['installation']['path'] = self.widgets['install_path'].get().strip()
            temp_settings['network']['backend_host'] = self.widgets['backend_host'].get().strip()
            temp_settings['network']['backend_port'] = int(self.widgets['backend_port'].get())
            temp_settings['network']['frontend_host'] = self.widgets['frontend_host'].get().strip()
            temp_settings['network']['frontend_port'] = int(self.widgets['frontend_port'].get())
            
            # Create temporary manager for validation
            temp_manager = BrainDriveSettingsManager("")
            temp_manager.settings = temp_settings
            
            issues = temp_manager.validate_settings()
            
            if issues:
                self.widgets['status_label'].config(text=f"⚠ Issues: {'; '.join(issues[:2])}", foreground="orange")
            else:
                self.widgets['status_label'].config(text="✓ Settings valid", foreground="green")
                
        except ValueError:
            self.widgets['status_label'].config(text="⚠ Invalid numeric values", foreground="red")
        except Exception as e:
            self.widgets['status_label'].config(text=f"⚠ Validation error: {str(e)}", foreground="red")
        finally:
            self._schedule_port_indicator_update()

    def _check_port_usage(self, host: str, port_value) -> str:
        """Return 'open', 'closed', or 'unknown' depending on port availability."""
        host = (host or "").strip()
        if not host:
            return "unknown"
        try:
            port = int(port_value)
            if port <= 0 or port > 65535:
                return "unknown"
        except (TypeError, ValueError):
            return "unknown"

        probe_host = host
        if host in {"0.0.0.0", "::", "[::]"}:
            probe_host = "127.0.0.1"

        try:
            with socket.create_connection((probe_host, port), timeout=0.5):
                return "open"
        except socket.timeout:
            return "closed"
        except OSError:
            return "closed"

    def _set_port_indicator(self, name: str, status: str) -> None:
        indicator = self.port_indicators.get(name)
        if not indicator:
            return

        colors = {
            "open": "#d93025",      # Port responding -> in use
            "closed": "#2da44e",    # Connection refused -> available
            "unknown": "#9e9e9e",
        }
        labels = {
            "open": "In Use",
            "closed": "Available",
            "unknown": "Unknown",
        }

        color = colors.get(status, "#9e9e9e")
        text = labels.get(status, "Unknown")
        indicator['canvas'].itemconfig(indicator['circle'], fill=color)
        indicator['label'].config(text=text, foreground=color)

    def _update_port_indicators(self) -> None:
        self._port_update_job = None
        backend_status = self._check_port_usage(
            self.widgets['backend_host'].get(),
            self.widgets['backend_port'].get()
        )
        frontend_status = self._check_port_usage(
            self.widgets['frontend_host'].get(),
            self.widgets['frontend_port'].get()
        )
        self._set_port_indicator('backend', backend_status)
        self._set_port_indicator('frontend', frontend_status)

    def _schedule_port_indicator_update(self):
        if not self.dialog:
            return
        if self._port_update_job:
            self.dialog.after_cancel(self._port_update_job)
        self._port_update_job = self.dialog.after(200, self._update_port_indicators)
    
    def _reset_defaults(self):
        """Reset all settings to defaults"""
        if messagebox.askyesno("Reset Settings", "Reset all settings to defaults?"):
            defaults = self.settings_manager._get_default_settings()
            self.settings_manager.settings = defaults
            
            # Clear and reload widgets
            for widget_name, widget in self.widgets.items():
                if isinstance(widget, ttk.Entry):
                    previous_state = widget.cget('state')
                    if previous_state == tk.DISABLED:
                        widget.config(state=tk.NORMAL)
                        widget.delete(0, tk.END)
                        widget.config(state=previous_state)
                    else:
                        widget.delete(0, tk.END)
                elif isinstance(widget, tk.BooleanVar):
                    widget.set(False)
                elif isinstance(widget, ttk.Combobox):
                    widget.set("")
            
            self._load_current_settings()
            self._validate_settings()
    
    def _apply_settings(self):
        """Apply and save current settings"""
        # Validate first
        self._validate_settings()
        if "Issues:" in self.widgets['status_label'].cget("text") or "Invalid" in self.widgets['status_label'].cget("text"):
            messagebox.showerror("Invalid Settings", "Please fix validation issues before applying.")
            return
        
        try:
            # Update settings manager
            self.settings_manager.update_setting('network', 'backend_host', self.widgets['backend_host'].get().strip())
            self.settings_manager.update_setting('network', 'backend_port', int(self.widgets['backend_port'].get()))
            self.settings_manager.update_setting('network', 'frontend_host', self.widgets['frontend_host'].get().strip())
            self.settings_manager.update_setting('network', 'frontend_port', int(self.widgets['frontend_port'].get()))
            
            self.settings_manager.update_setting('security', 'enable_registration', self.widgets['enable_registration'].get())
            self.settings_manager.update_setting('security', 'enable_api_docs', self.widgets['enable_api_docs'].get())
            self.settings_manager.update_setting('security', 'enable_metrics', self.widgets['enable_metrics'].get())
            self.settings_manager.update_setting('security', 'debug_mode', self.widgets['debug_mode'].get())
            
            
            self.settings_manager.update_setting('advanced', 'database_path', self.widgets['database_path'].get().strip())
            self.settings_manager.update_setting('advanced', 'log_level', self.widgets['log_level'].get())
            self.settings_manager.update_setting('installation', 'path', self.widgets['install_path'].get().strip())
            
            # Save settings, and regenerate env files only if BrainDrive is installed
            install_path = getattr(self.settings_manager, 'installation_path', '') or ''
            backend_dir = os.path.join(install_path, 'backend')
            frontend_dir = os.path.join(install_path, 'frontend')

            saved = self.settings_manager.save_settings()
            if os.path.exists(backend_dir) and os.path.exists(frontend_dir):
                # Installed: regenerate env files now
                if saved and self.settings_manager.regenerate_env_files():
                    messagebox.showinfo("Settings Applied", "Settings saved and environment files updated successfully.\n\nRestart BrainDrive for changes to take effect.")
                    if self.on_apply:
                        self.on_apply()
                    self.dialog.destroy()
                else:
                    messagebox.showerror("Error", "Failed to save settings or update environment files.")
            else:
                # Pre-install: only save JSON; installer will apply during setup
                if saved:
                    messagebox.showinfo("Settings Saved", "Settings saved. They will be applied during installation to generate environment files.")
                    if self.on_apply:
                        self.on_apply()
                    self.dialog.destroy()
                else:
                    messagebox.showerror("Error", "Failed to save settings.")
                
        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Please check your input values: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while applying settings: {str(e)}")
    
    def _browse_install_path(self):
        """Open a folder picker for the install path."""
        initial_dir = self.widgets['install_path'].get().strip()
        if not initial_dir or not os.path.isdir(initial_dir):
            initial_dir = os.path.expanduser("~")

        selected = filedialog.askdirectory(parent=self.dialog, title="Select BrainDrive Install Location", initialdir=initial_dir)
        if selected:
            selected_path = os.path.abspath(selected)
            self.widgets['install_path'].config(state=tk.NORMAL)
            self.widgets['install_path'].delete(0, tk.END)
            self.widgets['install_path'].insert(0, selected_path)
            self._validate_settings()
            # Re-disable if it was originally disabled (installed scenario)
            if os.path.exists(os.path.join(self.settings_manager.installation_path, 'backend')) and \
               os.path.exists(os.path.join(self.settings_manager.installation_path, 'frontend')):
                self.widgets['install_path'].config(state=tk.DISABLED)
                browse_btn = self.widgets.get('install_browse')
                if browse_btn:
                    browse_btn.config(state=tk.DISABLED)

    def _cancel(self):
        """Cancel and close dialog"""
        self.dialog.destroy()
