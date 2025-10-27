# BrainDrive Installer Updater

The legacy `InstallerAutoUpdater` sources have been migrated into the unified repo layout. Shared Python modules now live in the package tree `installer-updater/common/src/installer_updater`, while platform-specific build assets sit beneath `installer-updater/<platform>/`.

## Directory Layout

- `common/` - shared Python package (`src/installer_updater/`) and configuration templates.
- `windows/` – Windows-only PyInstaller spec, icon, and build script.
- `macos/` / `ubuntu/` – placeholders for future platform builds.
- `README-legacy.md` – original project documentation retained for reference during refactor.

## Running the Windows build

1. Ensure dependencies are available with `pip install -r installer-updater/windows/requirements-windows.txt` (from your active `BrainDriveInstaller` Conda environment). Use the per-platform files in `installer-updater/macos/` or `installer-updater/ubuntu/` when building on those systems.
2. From the repo root, execute `installer-updater/windows/build-windows.bat`. The script reuses an active Conda environment when present, otherwise it spins up a temporary `build_env` virtual environment and runs the `braindrive-installer-updater-windows.spec` recipe.
3. The generated binary is emitted to `installer-updater/windows/dist/BrainDriveInstallerUpdater-win-x64.exe` alongside a `logs/` directory that captures runtime diagnostics.

## Notes

- Package templates are embedded via `importlib.resources`, so PyInstaller bundles include the `.env` skeletons automatically.
- Adjust `BRAINDRIVE_INSTALLER_HOME`, `BRAINDRIVE_INSTALLER_REPO`, or `BRAINDRIVE_INSTALLER_RELEASES` environment variables to override the default install location and GitHub release endpoints.
- Additional platform builds (macOS, Linux) can be added by mirroring the Windows spec and extending the asset-name mappings in `installer_updater.app`.

## Running the macOS build

1. Activate the `BrainDriveInstaller` Conda environment if available: `conda activate BrainDriveInstaller`.
2. From the repo root, run `bash installer-updater/macos/build-macos.sh`.
   - The script reuses the active Conda environment when present; otherwise, it creates a temporary `build_env` virtual environment.
   - It installs `installer-updater/macos/requirements-macos.txt`, builds the `.app` via the `braindrive-installer-updater-macos.spec`, and then creates a DMG named `BrainDriveInstallerUpdater-macos-universal.dmg`.
3. Artifacts are emitted under `installer-updater/macos/dist/`:
   - `BrainDriveInstallerUpdater.app`
   - `BrainDriveInstallerUpdater-macos-universal.dmg`

Notes:
- Builds are unsigned. Gatekeeper may prompt on first run; use Right-click → Open to launch.
- Optional code signing can be enabled by setting `CODESIGN_IDENTITY` in the environment.
