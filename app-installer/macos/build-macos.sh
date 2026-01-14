#!/bin/bash
set -e

echo "========================================"
echo "BrainDrive Installer - macOS Build"
echo "========================================"
echo

# Resolve repo directories relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}/../.."
COMMON_DIR="${SCRIPT_DIR}/../common"
SRC_DIR="${COMMON_DIR}/src"
PKG_DIR="${SRC_DIR}/braindrive_installer"
MAIN_SCRIPT="${PKG_DIR}/ui/main_interface.py"
ENV_FILE="${REPO_ROOT}/environment.macos.yml"

# Validate main script exists
if [ ! -f "${MAIN_SCRIPT}" ]; then
    echo "❌ Error: main_interface.py not found at expected path"
    echo "Looked for: ${MAIN_SCRIPT}"
    echo "Please ensure the repo structure is intact."
    exit 1
fi

echo "✅ Found main_interface.py at ${MAIN_SCRIPT}"

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "❌ Error: conda is not installed"
    echo "Please install Miniconda or Anaconda and try again."
    exit 1
fi

echo "✅ Conda found: $(conda --version)"

# Create or update conda environment
CONDA_ENV_NAME="BrainDriveInstallerBuild"
echo
echo "🔧 Setting up conda environment: ${CONDA_ENV_NAME}..."

# Check if the environment exists
if conda env list | grep -q "^${CONDA_ENV_NAME} "; then
    echo "Updating existing conda environment..."
    conda env update -n "${CONDA_ENV_NAME}" -f "${ENV_FILE}" --prune
else
    echo "Creating new conda environment..."
    conda env create -n "${CONDA_ENV_NAME}" -f "${ENV_FILE}"
fi

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to create/update conda environment"
    exit 1
fi

echo "✅ Conda environment ready"

# Activate conda environment
echo
echo "🔧 Activating conda environment..."
eval "$(conda shell.bash hook)"
conda activate "${CONDA_ENV_NAME}"

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to activate conda environment"
    exit 1
fi

echo "✅ Conda environment activated"
echo "Python: $(python --version)"
echo "Location: $(which python)"

# Verify tkinter is working
echo
echo "🔧 Verifying tkinter..."
python -c "import tkinter; print('tkinter OK')" 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Error: tkinter is not working in this Python installation"
    echo "Please ensure the conda environment has tk installed."
    exit 1
fi
echo "✅ tkinter verified"

# Install PyInstaller (might not be in conda env)
echo
echo "🔧 Installing PyInstaller..."
pip install pyinstaller>=6.0.0
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to install PyInstaller"
    exit 1
fi

echo "✅ PyInstaller installed"

# Clean previous build
echo
echo "🔧 Cleaning previous build..."
rm -rf "${SCRIPT_DIR}/build" "${SCRIPT_DIR}/dist" "${SCRIPT_DIR}/__pycache__"

# Check for macOS icon file in macOS folder
ICON_FILE="${SCRIPT_DIR}/braindriveai.icns"
if [ ! -f "${ICON_FILE}" ]; then
    echo "⚠️  Warning: braindriveai.icns not found, using PNG fallback"
    if [ -f "${COMMON_DIR}/assets/braindrive.png" ]; then
        echo "Using braindrive.png as icon"
    else
        echo "❌ Error: No icon file found (braindriveai.icns or braindrive.png)"
        exit 1
    fi
fi

# Build the executable
echo
echo "🚀 Building executable (universal2)..."
echo "This may take several minutes..."
pushd "${SCRIPT_DIR}" >/dev/null

# Build using the .spec; do not pass makespec-only options like --target-arch
pyinstaller braindrive-installer-macos.spec --clean --noconfirm
BUILD_STATUS=$?
popd >/dev/null
if [ ${BUILD_STATUS} -ne 0 ]; then
    echo "❌ Error: PyInstaller build failed"
    exit 1
fi

# Check if build was successful
APP_BUNDLE="${SCRIPT_DIR}/dist/BrainDriveInstaller.app"
DMG_FILE="${SCRIPT_DIR}/dist/BrainDriveInstaller.dmg"
# Debug: list dist contents to help diagnose missing artifacts
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
            --volname "BrainDrive Installer" \
            $( [ -f "${ICON_FILE}" ] && echo --volicon "${ICON_FILE}" ) \
            --window-pos 200 120 \
            --window-size 600 300 \
            --icon-size 100 \
            --icon "BrainDriveInstaller.app" 175 120 \
            --hide-extension "BrainDriveInstaller.app" \
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
        hdiutil create -volname "BrainDrive Installer" -srcfolder "${APP_BUNDLE}" -ov -format UDZO "${DMG_FILE}"
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
    exit 1
fi

# Cleanup (conda environments persist, just deactivate)
echo
echo "🧹 Deactivating conda environment..."
conda deactivate 2>/dev/null || true

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
