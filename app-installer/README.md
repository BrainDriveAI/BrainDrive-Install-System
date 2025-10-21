# BrainDrive App Installer

Windows support has been migrated from `OldCode/BrainDriveInstaller` into the unified repo layout. Shared Python sources now live in the package tree `app-installer/common/src/braindrive_installer`, while Windows build artifacts stay under `app-installer/windows` alongside the PyInstaller spec.

## Directory Layout

- `common/` - shared assets/templates plus the `src/braindrive_installer/` package containing all cross-platform Python code.
- `windows/` – Windows-only build scripts, spec file, and installer metadata (version marker, icon, helper BATs).
- `macos/` – placeholder for future macOS build scripts/spec.
- `ubuntu/` – placeholder for future Linux build scripts/spec.
- `README-legacy.md` – original project README retained for reference during refactor.

## Running the Windows build

1. Install dependencies with `pip install -r app-installer/common/src/braindrive_installer/requirements.txt` and `pip install -r app-installer/windows/requirements-windows.txt` if needed.
2. From the repo root, run `app-installer/windows/build-windows.bat` to execute the existing PyInstaller recipe (`app-installer/windows/braindrive-installer-windows.spec`). The script reuses an active Conda environment (such as `BrainDriveInstaller`) when present, otherwise it spawns a temporary `build_env` virtual environment.
3. The Windows build produces `dist/BrainDriveInstaller-win-x64.exe`; the CI pipeline will be updated to publish platform builds via GitHub Releases.
4. Runtime logs are emitted to a `logs/` folder located beside the running executable (e.g., `app-installer/windows/dist/logs/BrainDriveInstaller_*.log`).

## Next Steps

- Fold the migrated legacy tests under `tests/installer/legacy` into pytest suites.
- Strip obsolete assets/logs from `OldCode/BrainDriveInstaller` once parity verification is complete.
- Add packaging automation for macOS and Linux before enabling those targets.

