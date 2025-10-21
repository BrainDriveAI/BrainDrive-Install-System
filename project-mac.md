# BrainDrive macOS Build Plan

## 1. Goals
- Produce unsigned macOS DMG packages for both the BrainDrive installer and the installer updater.
- Maintain parity with the Windows build outputs (naming conventions, logging, packaging structure).
- Prepare groundwork for future signing/notarization once Developer ID assets are available.

## 2. Environment Setup (macOS)
- macOS 12 or later (Intel or Apple Silicon) with Xcode Command Line Tools.
- Python 3.11.x matching the Windows builds (pyenv or Homebrew Python is acceptable).
- Required CLI tools: python3, pip, hdiutil, pkgbuild (optional), codesign (present but unused until signing), 	ar.
- Optional: conda environment mirroring BrainDriveInstaller if using conda-based workflows.

## 3. Packaging Strategy (unsigned)
### App Installer
- Create pp-installer/macos/braindrive-installer-macos.spec targeting universal2 binaries.
- Build the .app bundle via PyInstaller (--target-arch universal2 when available).
- Wrap .app into a DMG using hdiutil create.
- Naming convention: BrainDriveInstaller-macos-universal.dmg.
- Skip signing/notarization; document Gatekeeper bypass (Right-click → Open).

### Installer Updater
- Mirror the structure with installer-updater/macos/braindrive-installer-updater-macos.spec and a corresponding build script.
- DMG output: BrainDriveInstallerUpdater-macos-universal.dmg.
- Ensure installer_updater.app adjusts default asset names for mac (BrainDriveInstaller-macos-universal.dmg).

## 4. Build Scripts
- Create pp-installer/macos/build-macos.sh:
  1. Activate conda env or create Python venv.
  2. Install shared requirements (pp-installer/common/src/braindrive_installer/requirements.txt).
  3. Run PyInstaller spec.
  4. Create DMG: hdiutil create -volname BrainDriveInstaller -srcfolder dist/BrainDriveInstaller.app -ov -format UDZO dist/BrainDriveInstaller-macos-universal.dmg.
  5. Emit prominent warning: "Unsigned build – Gatekeeper will prompt.".
- Similar script at installer-updater/macos/build-macos.sh.
- Ensure scripts clean previous builds and set executable permissions on the .app contents if required.

## 5. Code Updates
- Audit platform-specific logic in raindrive_installer and installer_updater to ensure mac paths use POSIX style (e.g., Path.home() instead of %USERPROFILE%).
- Confirm subprocess calls provide shell-compatible commands for macOS (e.g., open, ash -lc).
- Ensure asset loading functions account for app bundle structure (check _MEIPASS vs Resources paths).

## 6. Documentation
- Update project.md, pp-installer/README.md, installer-updater/README.md with macOS sections referencing the unsigned DMGs.
- Add Gatekeeper bypass instructions and test notes.
- Record TODO for future signing/notarization.

## 7. CI/CD Preparation
- Extend .github/workflows/release-installers.yml with macOS jobs:
  - Matrix entry os: macos-latest, 	arget: app-installer/installer-updater.
  - Steps: checkout → setup Python → rew install create-dmg (optional) → run uild-macos.sh.
  - Upload DMGs directly; mark release notes as unsigned.
- Add TODO comments placeholder for codesign/notarize steps.

## 8. QA & Testing
- Manual checklist:
  - Mount DMG and drag .app to /Applications.
  - Right-click → Open to bypass Gatekeeper; confirm app launches.
  - Validate logging under dist/logs/ equivalent structure.
  - Verify update workflow on macOS (updater DMG downloads latest installer DMG and opens it).
- Optional automation: simple smoke script using osascript to open the DMG and check mount.

## 9. Future Work (Signing/Notarization)
- Obtain Apple Developer ID Application certificate and notarization credentials.
- Integrate codesign --force --deep --sign "Developer ID Application: ..." and xcrun notarytool submit into build scripts once credentials are available.
- Update release notes and README to reflect signed builds when ready.

## 10. Open Questions
- Which DMG background/theme (if any) should be used for installer presentation?
- Will we need a .pkg variant for enterprise deployment?
- Do we ship a universal binary or separate Intel/ARM DMGs? (Current plan: universal2.)
