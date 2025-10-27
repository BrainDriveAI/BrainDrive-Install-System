# -*- mode: python ; coding: utf-8 -*-

import sys
import importlib
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

SPEC_PATH = Path(globals().get("__file__", sys.argv[0])).resolve()
BASE_DIR = SPEC_PATH.parent
REPO_ROOT = BASE_DIR.parent
COMMON_DIR = REPO_ROOT / 'common'
SRC_DIR = COMMON_DIR / 'src'
PACKAGE_NAME = 'braindrive_installer'
PACKAGE_DIR = SRC_DIR / PACKAGE_NAME

# Ensure the package is discoverable during the build
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
            relative = file_path.relative_to(source).as_posix()
            datas.append((str(file_path), str(Path(target_root) / relative)))

# Package-specific assets
datas.append((str(BASE_DIR / 'braindriveai.ico'), '.'))
add_directory(COMMON_DIR / 'assets', 'assets')
add_directory(COMMON_DIR / 'templates', 'templates')
datas.append((str(PACKAGE_DIR), PACKAGE_NAME))

# Include VERSION file for runtime version detection
VERSION_FILE = PACKAGE_DIR / 'VERSION'
if VERSION_FILE.exists():
    datas.append((str(VERSION_FILE), PACKAGE_NAME))

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
    'installers.installer_braindrive',
    'installers.installer_miniconda',
    'installers.installer_openwebui',
    'installers.installer_pipelines',
    'installers.cleanup_braindrive',
    'installers.cleanup_processes',
    'installers.create_braindrive_image',
    'installers.create_version_info',
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

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BrainDriveInstaller-win-x64',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Windows GUI application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='braindriveai.ico',
    version='version_info.txt',
)
