@echo off
echo ========================================
echo Force Delete BrainDrive Directory
echo ========================================

set BRAINDRIVE_DIR=C:\Users\david\BrainDrive

echo Checking if BrainDrive directory exists...
if not exist "%BRAINDRIVE_DIR%" (
    echo ✅ BrainDrive directory does not exist
    goto :end
)

echo 🔍 Found BrainDrive directory at: %BRAINDRIVE_DIR%

echo.
echo 🛑 Step 1: Removing read-only attributes recursively...
attrib -R "%BRAINDRIVE_DIR%\*" /S /D 2>nul

echo.
echo 🛑 Step 2: Taking ownership of all files and folders...
takeown /F "%BRAINDRIVE_DIR%" /R /D Y >nul 2>&1

echo.
echo 🛑 Step 3: Granting full control permissions...
icacls "%BRAINDRIVE_DIR%" /grant "%USERNAME%":F /T /C /Q >nul 2>&1

echo.
echo 🛑 Step 4: Force deleting with rmdir...
rmdir /S /Q "%BRAINDRIVE_DIR%" 2>nul

echo.
echo 🔍 Checking if deletion was successful...
if exist "%BRAINDRIVE_DIR%" (
    echo ⚠️  Directory still exists, trying alternative methods...
    
    echo.
    echo 🛑 Step 5: Using PowerShell Remove-Item with Force...
    powershell -Command "Remove-Item -Path '%BRAINDRIVE_DIR%' -Recurse -Force -ErrorAction SilentlyContinue"
    
    echo.
    echo 🔍 Final check...
    if exist "%BRAINDRIVE_DIR%" (
        echo ❌ Directory still exists. Manual intervention may be required.
        echo.
        echo Possible causes:
        echo - Files are still in use by hidden processes
        echo - System file locks
        echo - Antivirus interference
        echo.
        echo Try:
        echo 1. Restart your computer
        echo 2. Run this script as Administrator
        echo 3. Temporarily disable antivirus
        dir "%BRAINDRIVE_DIR%" /A /S
    ) else (
        echo ✅ Directory successfully deleted with PowerShell!
    )
) else (
    echo ✅ Directory successfully deleted with rmdir!
)

:end
echo.
echo ========================================
echo Force Delete Complete
echo ========================================
pause