#!/usr/bin/env python3
"""
Create version information file for Windows executable.
This script generates version_info.txt used by PyInstaller for Windows builds.
"""

import os
import sys
from datetime import datetime

def create_version_info():
    """Create version_info.txt file for Windows executable metadata."""
    
    # Version information
    version_major = 1
    version_minor = 0
    version_patch = 4
    version_build = 0
    
    version_string = f"{version_major}.{version_minor}.{version_patch}.{version_build}"
    
    # Current year for copyright
    current_year = datetime.now().year
    
    version_info_content = f'''# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    # filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
    # Set not needed items to zero 0.
    filevers=({version_major}, {version_minor}, {version_patch}, {version_build}),
    prodvers=({version_major}, {version_minor}, {version_patch}, {version_build}),
    # Contains a bitmask that specifies the valid bits 'flags'r
    mask=0x3f,
    # Contains a bitmask that specifies the Boolean attributes of the file.
    flags=0x0,
    # The operating system for which this file was designed.
    # 0x4 - NT and there is no need to change it.
    OS=0x4,
    # The general type of file.
    # 0x1 - the file is an application.
    fileType=0x1,
    # The function of the file.
    # 0x0 - the function is not defined for this fileType
    subtype=0x0,
    # Creation date and time stamp.
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'BrainDrive.ai'),
        StringStruct(u'FileDescription', u'BrainDrive Installer - Advanced AI Platform Installer'),
        StringStruct(u'FileVersion', u'{version_string}'),
        StringStruct(u'InternalName', u'BrainDriveInstaller'),
        StringStruct(u'LegalCopyright', u'Copyright © {current_year} BrainDrive.ai. All rights reserved.'),
        StringStruct(u'OriginalFilename', u'BrainDriveInstaller-win-x64.exe'),
        StringStruct(u'ProductName', u'BrainDrive Installer'),
        StringStruct(u'ProductVersion', u'{version_string}'),
        StringStruct(u'Comments', u'Cross-platform installer for BrainDrive AI platform with React frontend and FastAPI backend')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)'''
    
    # Write version info file
    with open('version_info.txt', 'w', encoding='utf-8') as f:
        f.write(version_info_content)
    
    print(f"✅ Created version_info.txt with version {version_string}")
    return version_string

def get_version_info():
    """Get current version information."""
    return {
        'major': 1,
        'minor': 0,
        'patch': 4,
        'build': 0,
        'string': '1.0.4.0'
    }

def update_version(major=None, minor=None, patch=None, build=None):
    """Update version numbers and regenerate version_info.txt."""
    current = get_version_info()
    
    if major is not None:
        current['major'] = major
    if minor is not None:
        current['minor'] = minor
    if patch is not None:
        current['patch'] = patch
    if build is not None:
        current['build'] = build
    
    current['string'] = f"{current['major']}.{current['minor']}.{current['patch']}.{current['build']}"
    
    print(f"🔄 Updating version to {current['string']}")
    return create_version_info()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        # Command line version update
        if sys.argv[1] == '--update':
            if len(sys.argv) >= 6:
                major, minor, patch, build = map(int, sys.argv[2:6])
                update_version(major, minor, patch, build)
            else:
                print("Usage: python create_version_info.py --update <major> <minor> <patch> <build>")
                sys.exit(1)
        elif sys.argv[1] == '--help':
            print("BrainDrive Installer Version Info Generator")
            print("Usage:")
            print("  python create_version_info.py                    # Create version_info.txt with default version")
            print("  python create_version_info.py --update 1 0 1 0   # Update to specific version")
            print("  python create_version_info.py --help             # Show this help")
        else:
            print("Unknown argument. Use --help for usage information.")
            sys.exit(1)
    else:
        # Default: create version info file
        create_version_info()
