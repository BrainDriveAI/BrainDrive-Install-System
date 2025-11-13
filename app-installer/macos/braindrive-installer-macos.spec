# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import importlib
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Resolve key paths relative to this spec file
SPEC_PATH = Path(globals().get("__file__", sys.argv[0])).resolve()
BASE_DIR = SPEC_PATH.parent
REPO_ROOT = BASE_DIR.parent
COMMON_DIR = REPO_ROOT / 'common'
SRC_DIR = COMMON_DIR / 'src'
PACKAGE_NAME = 'braindrive_installer'
PACKAGE_DIR = SRC_DIR / PACKAGE_NAME

# Ensure the package is importable during analysis
sys.path.append(str(SRC_DIR))
importlib.import_module(PACKAGE_NAME)

datas = []
hiddenimports = []

# Tkinter / Pillow runtime assets
datas += collect_data_files('tkinter')
datas += collect_data_files('PIL')

# Helper to add full directory trees (assets, templates, etc.)
def add_directory(source: Path, target_root: str) -> None:
    if not source.exists():
        return
    for file_path in source.rglob('*'):
        if file_path.is_file():
            relative = file_path.relative_to(source)
            # Destination in PyInstaller 'datas' must be a DIRECTORY, not a filename.
            # Place each file under '<target_root>/<relative.parent>' so assets aren't
            # turned into directories named like the file (which breaks lookups).
            dest_dir = str((Path(target_root) / relative.parent).as_posix())
            datas.append((str(file_path), dest_dir))

# Package-specific assets
ICNS_PATH = BASE_DIR / 'braindriveai.icns'
PNG_ICON = COMMON_DIR / 'assets' / 'braindrive.png'
SMALL_PNG = COMMON_DIR / 'assets' / 'braindrive_small.png'

if PNG_ICON.exists():
    datas.append((str(PNG_ICON), '.'))
if SMALL_PNG.exists():
    datas.append((str(SMALL_PNG), '.'))

add_directory(COMMON_DIR / 'assets', 'assets')
add_directory(COMMON_DIR / 'templates', 'templates')
# Include package-local templates used at runtime
add_directory(PACKAGE_DIR / 'templates', f'{PACKAGE_NAME}/templates')

# Include VERSION file for runtime version detection
VERSION_FILE = PACKAGE_DIR / 'VERSION'
if VERSION_FILE.exists():
    datas.append((str(VERSION_FILE), f'{PACKAGE_NAME}'))

# Templates are included by add_directory above; avoid duplicate/conflicting
# datas entries that target a filename as a directory.

# Hidden imports routinely required at runtime
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
hiddenimports = list(dict.fromkeys(hiddenimports + collect_submodules(PACKAGE_NAME)))

# Application package modules that PyInstaller must bundle
package_modules = [
    'core.platform_utils',
    'core.base_installer',
    'core.git_manager',
    'core.installer_logger',
    'core.installer_state',
    'core.node_manager',
    'core.plugin_builder',
    'core.process_manager',
    'config.AppConfig',
    'integration.AppDesktopIntegration',
    'ui.base_card',
    'ui.ButtonStateManager',
    'ui.card_braindrive',
    'ui.card_ollama',
    'ui.main_interface',
    'ui.settings_dialog',
    'ui.settings_manager',
    'ui.status_display',
    'ui.status_spinner',
    'ui.status_updater',
    'utils.DiskSpaceChecker',
    'utils.helper_image',
]
hiddenimports += [f'{PACKAGE_NAME}.{module}' for module in package_modules]

MAIN_SCRIPT = str(PACKAGE_DIR / 'ui' / 'main_interface.py')

a = Analysis(
    [MAIN_SCRIPT],
    pathex=[str(SRC_DIR)],
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

ICON_FILE = str(ICNS_PATH) if ICNS_PATH.exists() else None
TARGET_ARCH = os.environ.get('PYI_TARGET_ARCH') or None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BrainDriveInstaller',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=TARGET_ARCH,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BrainDriveInstaller_collected',
)

app = BUNDLE(
    coll,
    name='BrainDriveInstaller.app',
    icon=ICON_FILE,
    bundle_identifier='ai.braindrive.installer',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
        'CFBundleDocumentTypes': [],
        'NSHighResolutionCapable': 'True',
        'LSMinimumSystemVersion': '10.14.0',
        'NSRequiresAquaSystemAppearance': 'No',
        'CFBundleShortVersionString': '1.0.3',
        'CFBundleVersion': '1.0.3',
        'CFBundleDisplayName': 'BrainDrive Installer',
        'CFBundleName': 'BrainDriveInstaller',
        'CFBundleExecutable': 'BrainDriveInstaller',
        'CFBundlePackageType': 'APPL',
        'CFBundleSignature': 'BDAI',
        'LSApplicationCategoryType': 'public.app-category.utilities',
        'NSHumanReadableCopyright': 'Copyright © 2025 BrainDrive.ai. All rights reserved.',
    },
)
