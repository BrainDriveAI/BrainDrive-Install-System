# BrainDrive Installer Assets

This directory contains platform-specific assets for the BrainDrive Installer PyInstaller builds.

## Icon Requirements

### Windows
- **braindriveai.ico** - Windows icon file (ICO format)
- **braindrive.png** - Main logo (PNG format, 256x256 recommended)
- **braindrive_small.png** - Small logo variant (PNG format, 64x64 recommended)

### macOS
- **braindriveai.icns** - macOS icon file (ICNS format)
- **braindrive.png** - Main logo (PNG format, 256x256 recommended)
- **braindrive_small.png** - Small logo variant (PNG format, 64x64 recommended)

### Linux
- **braindrive.png** - Main logo (PNG format, 256x256 recommended)
- **braindrive_small.png** - Small logo variant (PNG format, 64x64 recommended)

## Current Assets

The following assets are currently available in the root directory:
- `braindriveai.ico` (4,286 bytes) - Windows icon
- `braindrive.png` (4,101 bytes) - Main BrainDrive logo
- `braindrive_small.png` (2,318 bytes) - Small BrainDrive logo

## Asset Creation Notes

### Creating macOS ICNS from PNG
To create the macOS ICNS file from the PNG logo:

```bash
# On macOS
mkdir braindrive.iconset
sips -z 16 16     braindrive.png --out braindrive.iconset/icon_16x16.png
sips -z 32 32     braindrive.png --out braindrive.iconset/icon_16x16@2x.png
sips -z 32 32     braindrive.png --out braindrive.iconset/icon_32x32.png
sips -z 64 64     braindrive.png --out braindrive.iconset/icon_32x32@2x.png
sips -z 128 128   braindrive.png --out braindrive.iconset/icon_128x128.png
sips -z 256 256   braindrive.png --out braindrive.iconset/icon_128x128@2x.png
sips -z 256 256   braindrive.png --out braindrive.iconset/icon_256x256.png
sips -z 512 512   braindrive.png --out braindrive.iconset/icon_256x256@2x.png
sips -z 512 512   braindrive.png --out braindrive.iconset/icon_512x512.png
sips -z 1024 1024 braindrive.png --out braindrive.iconset/icon_512x512@2x.png
iconutil -c icns braindrive.iconset
```

### Creating Windows ICO from PNG
To create or update the Windows ICO file:

```bash
# Using ImageMagick
convert braindrive.png -define icon:auto-resize=256,128,64,48,32,16 braindriveai.ico
```

## PyInstaller Integration

These assets are automatically included in the PyInstaller builds through the specification files:

- **Windows**: `braindrive-installer-windows.spec`
- **macOS**: `braindrive-installer-macos.spec`  
- **Linux**: `braindrive-installer-linux.spec`

The build scripts will automatically detect and include available assets.

## Asset Guidelines

### Design Consistency
- Use the BrainDrive blue gradient design
- Maintain "BD" branding elements
- Ensure professional appearance across all sizes
- Optimize file sizes for distribution

### Technical Requirements
- **PNG**: Use PNG-24 with transparency
- **ICO**: Include multiple sizes (16, 32, 48, 64, 128, 256)
- **ICNS**: Include all required macOS sizes
- **Quality**: Maintain crisp edges at all sizes

### File Naming
- Use consistent naming across platforms
- Follow platform conventions (ico, icns, png)
- Include size variants where needed

## Build Integration

The PyInstaller specification files reference these assets:

```python
# Windows
datas += [
    ('braindriveai.ico', '.'),
    ('braindrive.png', '.'),
    ('braindrive_small.png', '.'),
    ('assets/*', 'assets'),
]

# macOS  
datas += [
    ('braindriveai.icns', '.'),
    ('braindrive.png', '.'),
    ('braindrive_small.png', '.'),
    ('assets/*', 'assets'),
]

# Linux
datas += [
    ('braindrive.png', '.'),
    ('braindrive_small.png', '.'),
    ('assets/*', 'assets'),
]
```

## Troubleshooting

### Missing Icons
If icons are missing during build:
1. Check file paths in specification files
2. Verify icon files exist in expected locations
3. Check file permissions and accessibility
4. Review build script output for warnings

### Icon Quality Issues
If icons appear blurry or pixelated:
1. Ensure source PNG is high resolution (256x256 minimum)
2. Recreate ICO/ICNS files from high-quality source
3. Test icons at various system scaling levels
4. Verify transparency is preserved

### Platform-Specific Issues
- **Windows**: Ensure ICO file includes multiple sizes
- **macOS**: Verify ICNS file follows Apple guidelines
- **Linux**: Test PNG icons in various desktop environments