#!/bin/bash
set -e

echo "========================================"
echo "BrainDrive Installer - macOS Build"
echo "========================================"
echo

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    echo "Please install Python 3.11 or later and try again."
    exit 1
fi

echo "✅ Python found"
python3 --version

# Check if we're in the correct directory
if [ ! -f "main_interface.py" ]; then
    echo "❌ Error: main_interface.py not found"
    echo "Please run this script from the BrainDriveInstaller directory"
    exit 1
fi

echo "✅ Found main_interface.py"

# Create build environment
echo
echo "🔧 Creating build environment..."
if [ -d "build_env" ]; then
    echo "Removing existing build environment..."
    rm -rf build_env
fi

python3 -m venv build_env
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to create virtual environment"
    exit 1
fi

echo "✅ Virtual environment created"

# Activate virtual environment
echo
echo "🔧 Activating build environment..."
source build_env/bin/activate
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to activate virtual environment"
    exit 1
fi

echo "✅ Build environment activated"

# Upgrade pip
echo
echo "🔧 Upgrading pip..."
python -m pip install --upgrade pip

# Install PyInstaller and dependencies
echo
echo "🔧 Installing build dependencies..."
pip install pyinstaller>=6.0.0
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to install PyInstaller"
    cleanup_and_exit 1
fi

echo "✅ PyInstaller installed"

# Install project requirements
echo
echo "🔧 Installing project requirements..."
pip install -r requirements-macos.txt
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to install project requirements"
    cleanup_and_exit 1
fi

echo "✅ Project requirements installed"

# Clean previous build
echo
echo "🔧 Cleaning previous build..."
rm -rf build dist __pycache__

# Check for macOS icon file
if [ ! -f "braindriveai.icns" ]; then
    echo "⚠️  Warning: braindriveai.icns not found, using PNG fallback"
    if [ -f "braindrive.png" ]; then
        echo "Using braindrive.png as icon"
    else
        echo "❌ Error: No icon file found (braindriveai.icns or braindrive.png)"
        cleanup_and_exit 1
    fi
fi

# Build the executable
echo
echo "🚀 Building executable..."
echo "This may take several minutes..."
pyinstaller braindrive-installer-macos.spec --clean --noconfirm
if [ $? -ne 0 ]; then
    echo "❌ Error: PyInstaller build failed"
    cleanup_and_exit 1
fi

# Check if build was successful
if [ -d "dist/BrainDriveInstaller.app" ]; then
    echo
    echo "✅ Build successful!"
    echo "📁 App bundle created at: dist/BrainDriveInstaller.app"
    
    # Get bundle size
    size=$(du -sh "dist/BrainDriveInstaller.app" | cut -f1)
    echo "📊 App bundle size: $size"
    
    # Code signing (if certificates are available)
    if [ -n "$CODESIGN_IDENTITY" ]; then
        echo
        echo "🔐 Code signing the application..."
        codesign --force --verify --verbose --sign "$CODESIGN_IDENTITY" "dist/BrainDriveInstaller.app"
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
            --volicon "braindriveai.icns" \
            --window-pos 200 120 \
            --window-size 600 300 \
            --icon-size 100 \
            --icon "BrainDriveInstaller.app" 175 120 \
            --hide-extension "BrainDriveInstaller.app" \
            --app-drop-link 425 120 \
            "dist/BrainDriveInstaller.dmg" \
            "dist/"
        
        if [ $? -eq 0 ]; then
            echo "✅ DMG package created!"
            dmg_size=$(du -sh "dist/BrainDriveInstaller.dmg" | cut -f1)
            echo "📊 DMG size: $dmg_size"
        else
            echo "⚠️  Warning: DMG creation failed, but app bundle is available"
        fi
    else
        echo "ℹ️  create-dmg not found. Creating simple DMG..."
        hdiutil create -volname "BrainDrive Installer" -srcfolder "dist/BrainDriveInstaller.app" -ov -format UDZO "dist/BrainDriveInstaller.dmg"
        if [ $? -eq 0 ]; then
            echo "✅ Simple DMG created!"
        else
            echo "⚠️  Warning: DMG creation failed, but app bundle is available"
        fi
    fi
    
    echo
    echo "🎉 Build completed successfully!"
    echo "📁 App bundle: dist/BrainDriveInstaller.app"
    if [ -f "dist/BrainDriveInstaller.dmg" ]; then
        echo "📁 DMG package: dist/BrainDriveInstaller.dmg"
    fi
    
else
    echo "❌ Build failed! App bundle not found."
    cleanup_and_exit 1
fi

# Cleanup function
cleanup_and_exit() {
    echo
    echo "🧹 Cleaning up build environment..."
    deactivate 2>/dev/null || true
    rm -rf build_env
    exit $1
}

# Cleanup
echo
echo "🧹 Cleaning up build environment..."
deactivate
rm -rf build_env

echo
echo "========================================"
echo "✅ BUILD COMPLETED SUCCESSFULLY!"
echo "========================================"
echo "📁 App bundle: dist/BrainDriveInstaller.app"
if [ -f "dist/BrainDriveInstaller.dmg" ]; then
    echo "📁 DMG package: dist/BrainDriveInstaller.dmg"
fi
echo "🚀 Ready for distribution!"
echo "========================================"
