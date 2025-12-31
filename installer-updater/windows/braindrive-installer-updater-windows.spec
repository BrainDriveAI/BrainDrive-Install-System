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
PACKAGE_NAME = 'installer_updater'
PACKAGE_DIR = SRC_DIR / PACKAGE_NAME

sys.path.append(str(SRC_DIR))
importlib.import_module(PACKAGE_NAME)

datas = []
hiddenimports = []

# Include package data (templates, requirements, etc.)
datas += collect_data_files(PACKAGE_NAME)

datas.append((str(BASE_DIR / 'braindriveai.ico'), '.'))

def add_directory(source: Path, target_root: str) -> None:
    if not source.exists():
        return
    for path in source.rglob('*'):
        if path.is_file():
            relative = path.relative_to(source).as_posix()
            datas.append((str(path), str(Path(target_root) / relative)))

# Provide direct access to templates in common resources
add_directory(COMMON_DIR / 'templates', 'templates')

hiddenimports += collect_submodules(PACKAGE_NAME)

MAIN_SCRIPT = str(PACKAGE_DIR / 'app.py')

analysis = Analysis(
    [MAIN_SCRIPT],
    pathex=[str(SRC_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pytest',
        'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(analysis.pure, analysis.zipped_data, cipher=None)

exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    [],
    name='BrainDriveInstallerUpdater-win-x64',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='braindriveai.ico',
    version=None,
)
