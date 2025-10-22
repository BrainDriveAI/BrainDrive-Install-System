#!/bin/bash
set -e

echo "========================================"
echo "BrainDrive Installer - Linux Build"
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
pip install -r requirements-ubuntu.txt
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to install project requirements"
    cleanup_and_exit 1
fi

echo "✅ Project requirements installed"

# Clean previous build
echo
echo "🔧 Cleaning previous build..."
rm -rf build dist __pycache__

# Build the executable
echo
echo "🚀 Building executable..."
echo "This may take several minutes..."
pyinstaller braindrive-installer-linux.spec --clean --noconfirm
if [ $? -ne 0 ]; then
    echo "❌ Error: PyInstaller build failed"
    cleanup_and_exit 1
fi

# Check if build was successful
if [ -f "dist/BrainDriveInstaller" ]; then
    echo
    echo "✅ Build successful!"
    echo "📁 Executable created at: dist/BrainDriveInstaller"
    
    # Make executable
    chmod +x "dist/BrainDriveInstaller"
    echo "✅ Executable permissions set"
    
    # Get file size
    size=$(du -sh "dist/BrainDriveInstaller" | cut -f1)
    echo "📊 Executable size: $size"
    
    # Test the executable
    echo
    echo "🧪 Testing executable..."
    if "./dist/BrainDriveInstaller" --version &>/dev/null; then
        echo "✅ Executable test passed"
    else
        echo "⚠️  Warning: Executable test failed, but file was created"
    fi
    
    # Create AppImage (if tools are available)
    echo
    echo "📦 Creating AppImage..."
    if command -v appimagetool &> /dev/null; then
        echo "Creating AppImage structure..."
        
        # Create AppDir structure
        mkdir -p "dist/BrainDriveInstaller.AppDir/usr/bin"
        mkdir -p "dist/BrainDriveInstaller.AppDir/usr/share/applications"
        mkdir -p "dist/BrainDriveInstaller.AppDir/usr/share/icons/hicolor/256x256/apps"
        
        # Copy executable and assets
        cp "dist/BrainDriveInstaller" "dist/BrainDriveInstaller.AppDir/usr/bin/"
        
        # Copy icon
        if [ -f "braindrive.png" ]; then
            cp "braindrive.png" "dist/BrainDriveInstaller.AppDir/usr/share/icons/hicolor/256x256/apps/braindriveai.png"
            cp "braindrive.png" "dist/BrainDriveInstaller.AppDir/braindriveai.png"
        else
            echo "⚠️  Warning: braindrive.png not found for AppImage icon"
        fi
        
        # Create desktop file
        cat > "dist/BrainDriveInstaller.AppDir/BrainDriveInstaller.desktop" << EOF
[Desktop Entry]
Type=Application
Name=BrainDrive Installer
Exec=BrainDriveInstaller
Icon=braindriveai
Categories=Utility;System;
Comment=Advanced AI Platform Installer
StartupNotify=true
EOF
        
        # Copy desktop file to applications
        cp "dist/BrainDriveInstaller.AppDir/BrainDriveInstaller.desktop" "dist/BrainDriveInstaller.AppDir/usr/share/applications/"
        
        # Create AppRun
        cat > "dist/BrainDriveInstaller.AppDir/AppRun" << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"
exec "${HERE}/usr/bin/BrainDriveInstaller" "$@"
EOF
        
        chmod +x "dist/BrainDriveInstaller.AppDir/AppRun"
        
        # Build AppImage
        appimagetool "dist/BrainDriveInstaller.AppDir" "dist/BrainDriveInstaller.AppImage"
        
        if [ $? -eq 0 ]; then
            echo "✅ AppImage created!"
            chmod +x "dist/BrainDriveInstaller.AppImage"
            appimage_size=$(du -sh "dist/BrainDriveInstaller.AppImage" | cut -f1)
            echo "📊 AppImage size: $appimage_size"
        else
            echo "⚠️  Warning: AppImage creation failed, but executable is available"
        fi
    else
        echo "ℹ️  appimagetool not found. Skipping AppImage creation."
        echo "   Install appimagetool to enable AppImage packaging."
    fi
    
    # Create tar.gz package
    echo
    echo "📦 Creating tar.gz package..."
    cd dist
    tar -czf BrainDriveInstaller-linux.tar.gz BrainDriveInstaller
    if [ $? -eq 0 ]; then
        echo "✅ tar.gz package created!"
        tar_size=$(du -sh "BrainDriveInstaller-linux.tar.gz" | cut -f1)
        echo "📊 tar.gz size: $tar_size"
    else
        echo "⚠️  Warning: tar.gz creation failed"
    fi
    cd ..
    
    echo
    echo "🎉 Build completed successfully!"
    echo "📁 Executable: dist/BrainDriveInstaller"
    if [ -f "dist/BrainDriveInstaller.AppImage" ]; then
        echo "📁 AppImage: dist/BrainDriveInstaller.AppImage"
    fi
    if [ -f "dist/BrainDriveInstaller-linux.tar.gz" ]; then
        echo "📁 Package: dist/BrainDriveInstaller-linux.tar.gz"
    fi
    
else
    echo "❌ Build failed! Executable not found."
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
echo "📁 Executable: dist/BrainDriveInstaller"
if [ -f "dist/BrainDriveInstaller.AppImage" ]; then
    echo "📁 AppImage: dist/BrainDriveInstaller.AppImage"
fi
if [ -f "dist/BrainDriveInstaller-linux.tar.gz" ]; then
    echo "📁 Package: dist/BrainDriveInstaller-linux.tar.gz"
fi
echo "🚀 Ready for distribution!"
echo "========================================"
