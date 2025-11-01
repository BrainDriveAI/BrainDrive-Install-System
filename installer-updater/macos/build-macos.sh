#!/bin/bash
set -e

echo "========================================"
echo "BrainDrive Installer Updater - macOS Build"
echo "========================================"
echo

# Resolve preferred Python (favor active conda env)
PYTHON_EXEC="$(command -v python || true)"
if [ -n "$CONDA_PREFIX" ] && [ -x "$CONDA_PREFIX/bin/python" ]; then
  PYTHON_EXEC="$CONDA_PREFIX/bin/python"
fi
if [ -z "$PYTHON_EXEC" ]; then
  PYTHON_EXEC="$(command -v python3 || true)"
fi
if [ -z "$PYTHON_EXEC" ]; then
    echo "❌ Error: Python 3 is not installed"
    echo "Please install Python 3.11 or later and try again."
    exit 1
fi

echo "✅ Python found"
"$PYTHON_EXEC" --version

# Resolve repo directories relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}/.."
COMMON_DIR="${REPO_ROOT}/common"
SRC_DIR="${COMMON_DIR}/src"
PKG_DIR="${SRC_DIR}/installer_updater"
MAIN_SCRIPT="${PKG_DIR}/app.py"

# Validate main script exists
if [ ! -f "${MAIN_SCRIPT}" ]; then
    echo "❌ Error: app.py not found at expected path"
    echo "Looked for: ${MAIN_SCRIPT}"
    echo "Please ensure the repo structure is intact."
    exit 1
fi

echo "✅ Found app.py at ${MAIN_SCRIPT}"

USING_CONDA=0
if [ -n "$CONDA_DEFAULT_ENV" ]; then
  USING_CONDA=1
  echo "🧪 Using active Conda environment: $CONDA_DEFAULT_ENV"
else
  echo "🔧 No Conda environment detected; a temporary virtual environment will be created."
fi

# Create build environment (if not using conda)
if [ "$USING_CONDA" -eq 0 ]; then
  echo
  echo "🔧 Creating build environment..."
  if [ -d "${SCRIPT_DIR}/build_env" ]; then
      echo "Removing existing build environment..."
      rm -rf "${SCRIPT_DIR}/build_env"
  fi
  "$PYTHON_EXEC" -m venv "${SCRIPT_DIR}/build_env"
  if [ $? -ne 0 ]; then
      echo "❌ Error: Failed to create virtual environment"
      exit 1
  fi
  echo "✅ Virtual environment created"
  echo
  echo "🔧 Activating build environment..."
  # shellcheck disable=SC1091
  source "${SCRIPT_DIR}/build_env/bin/activate"
  if [ $? -ne 0 ]; then
      echo "❌ Error: Failed to activate virtual environment"
      exit 1
  fi
  echo "✅ Build environment activated"
fi

# Upgrade pip
echo
echo "🔧 Upgrading pip..."
python -m pip install --upgrade pip

# Install build dependencies and project requirements
echo
echo "🔧 Installing build dependencies..."
pip install -r "${SCRIPT_DIR}/requirements-macos.txt"
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to install project requirements"
    cleanup_and_exit 1
fi
echo "✅ Dependencies installed"

# Clean previous build
echo
echo "🔧 Cleaning previous build..."
rm -rf "${SCRIPT_DIR}/build" "${SCRIPT_DIR}/dist" "${SCRIPT_DIR}/__pycache__"

# Icon (optional)
ICON_FILE="${SCRIPT_DIR}/braindriveai.icns"
if [ ! -f "${ICON_FILE}" ]; then
    echo "ℹ️  No .icns icon found; proceeding without app icon"
fi

# Build the executable
echo
# shellcheck disable=SC2034
echo "🚀 Building executable (universal2)..."
echo "This may take several minutes..."
pushd "${SCRIPT_DIR}" >/dev/null
pyinstaller braindrive-installer-updater-macos.spec --clean --noconfirm
BUILD_STATUS=$?
popd >/dev/null
if [ ${BUILD_STATUS} -ne 0 ]; then
    echo "❌ Error: PyInstaller build failed"
    cleanup_and_exit 1
fi

# Check if build was successful
APP_BUNDLE="${SCRIPT_DIR}/dist/BrainDriveInstallerUpdater.app"
DMG_FILE="${SCRIPT_DIR}/dist/BrainDriveInstallerUpdater-macos-universal.dmg"

echo
echo "📂 Dist contents:"
ls -la "${SCRIPT_DIR}/dist" || true

if [ -d "${APP_BUNDLE}" ]; then
    echo
    echo "✅ Build successful!"
    echo "📁 App bundle created at: ${APP_BUNDLE}"

    # Get bundle size
    size=$(du -sh "${APP_BUNDLE}" | cut -f1)
    echo "📊 App bundle size: $size"

    # Code signing (if certificates are available)
    if [ -n "$CODESIGN_IDENTITY" ]; then
        echo
        echo "🔐 Code signing the application..."
        codesign --force --verify --verbose --sign "$CODESIGN_IDENTITY" "${APP_BUNDLE}"
        if [ $? -eq 0 ]; then
            echo "✅ Code signing completed!"
        else
            echo "⚠️  Warning: Code signing failed, but app was created"
        fi
    else
        echo "ℹ️  No code signing identity provided. Skipping code signing."
        echo "   Set CODESIGN_IDENTITY environment variable to enable code signing."
    fi

    # Create DMG package
    echo
    echo "📦 Creating DMG package..."
    if command -v create-dmg &> /dev/null; then
        create-dmg \
            --volname "BrainDrive Installer Updater" \
            $( [ -f "${ICON_FILE}" ] && echo --volicon "${ICON_FILE}" ) \
            --window-pos 200 120 \
            --window-size 600 300 \
            --icon-size 100 \
            --icon "BrainDriveInstallerUpdater.app" 175 120 \
            --hide-extension "BrainDriveInstallerUpdater.app" \
            --app-drop-link 425 120 \
            "${DMG_FILE}" \
            "${SCRIPT_DIR}/dist/"

        if [ $? -eq 0 ]; then
            echo "✅ DMG package created!"
            dmg_size=$(du -sh "${DMG_FILE}" | cut -f1)
            echo "📊 DMG size: $dmg_size"
        else
            echo "⚠️  Warning: DMG creation failed, but app bundle is available"
        fi
    else
        echo "ℹ️  create-dmg not found. Creating simple DMG..."
        hdiutil create -volname "BrainDrive Installer Updater" -srcfolder "${APP_BUNDLE}" -ov -format UDZO "${DMG_FILE}"
        if [ $? -eq 0 ]; then
            echo "✅ Simple DMG created!"
        else
            echo "⚠️  Warning: DMG creation failed, but app bundle is available"
        fi
    fi

    echo
    echo "🎉 Build completed successfully!"
    echo "📁 App bundle: ${APP_BUNDLE}"
    if [ -f "${DMG_FILE}" ]; then
        echo "📁 DMG package: ${DMG_FILE}"
    fi
else
    echo "❌ Build failed! App bundle not found."
    cleanup_and_exit 1
fi

# Cleanup function
cleanup_and_exit() {
    echo
    echo "🧹 Cleaning up build environment..."
    if [ "$USING_CONDA" -eq 0 ]; then
      deactivate 2>/dev/null || true
      rm -rf "${SCRIPT_DIR}/build_env"
    fi
    exit $1
}

# Cleanup
echo
echo "🧹 Cleaning up build environment..."
if [ "$USING_CONDA" -eq 0 ]; then
  deactivate || true
  rm -rf "${SCRIPT_DIR}/build_env"
fi

echo
echo "========================================"
echo "✅ BUILD COMPLETED SUCCESSFULLY!"
echo "========================================"
echo "📁 App bundle: ${APP_BUNDLE}"
if [ -f "${DMG_FILE}" ]; then
  echo "📁 DMG package: ${DMG_FILE}"
fi
echo "🚀 Ready for distribution!"
echo "========================================"

