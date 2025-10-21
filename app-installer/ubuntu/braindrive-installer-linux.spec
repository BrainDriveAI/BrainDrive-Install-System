# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect all data files and hidden imports
datas = []
hiddenimports = []

# Add Tkinter data files
datas += collect_data_files('tkinter')

# Add PIL/Pillow data files
datas += collect_data_files('PIL')

# Add application assets
datas += [
    ('braindrive.png', '.'),
    ('braindrive_small.png', '.'),
    ('templates/*', 'templates'),
]

# Add assets directory if it exists
if os.path.exists('assets'):
    datas += [('assets/*', 'assets')]

# Hidden imports for common issues
hiddenimports += [
    'tkinter',
    'tkinter.ttk',
    'tkinter.messagebox',
    'tkinter.filedialog',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'psutil',
    'requests',
    'urllib3',
    'dulwich',
    'subprocess',
    'threading',
    'json',
    'sqlite3',
    'platform',
    'pathlib',
    'shutil',
    'tempfile',
    'webbrowser',
    'os',
    'sys',
    'time',
    'datetime',
    'logging',
    'configparser',
    'zipfile',
    'tarfile',
    'hashlib',
    'base64',
    'uuid',
    'socket',
    'ssl',
    'http.client',
    'urllib.parse',
    'urllib.request',
    'urllib.error',
]

# Hidden imports for conda/git operations
hiddenimports += collect_submodules('dulwich')
hiddenimports += collect_submodules('git')

# Add our application modules
hiddenimports += [
    'platform_utils',
    'AppConfig',
    'base_installer',
    'base_card',
    'git_manager',
    'node_manager',
    'plugin_builder',
    'process_manager',
    'installer_braindrive',
    'card_braindrive',
    'card_ollama',
    'ButtonStateManager',
    'status_display',
    'status_spinner',
    'status_updater',
    'DiskSpaceChecker',
    'AppDesktopIntegration',
]

a = Analysis(
    ['main_interface.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'jupyter',
        'IPython',
        'pytest',
        'sphinx',
        'setuptools',
        'wheel',
        'pip',
        'distutils',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BrainDriveInstaller',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)