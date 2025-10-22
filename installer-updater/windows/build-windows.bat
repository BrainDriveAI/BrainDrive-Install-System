@echo off
setlocal EnableDelayedExpansion

set "EXIT_CODE=0"

echo ========================================
echo BrainDrive Installer Updater - Windows Build
echo ========================================
echo.

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%" >nul
for %%I in (.) do set "WINDOWS_DIR=%%~fI"
for %%I in ("%WINDOWS_DIR%\..") do set "REPO_ROOT=%%~fI"
set "COMMON_DIR=%REPO_ROOT%\common"
set "SRC_DIR=%COMMON_DIR%\src"
set "PACKAGE_DIR=%SRC_DIR%\installer_updater"
set "WINDOWS_REQUIREMENTS=%WINDOWS_DIR%\requirements-windows.txt"
set "PYTHON_EXEC=python"
set "USING_CONDA=0"

python --version >nul 2>&1
if errorlevel 1 (
    echo ? Error: Python is not installed or not in PATH
    set "EXIT_CODE=1"
    goto cleanup
)

echo ? Python found
python --version

echo.
if defined CONDA_DEFAULT_ENV (
    set "USING_CONDA=1"
    echo ?? Using active Conda environment: %CONDA_DEFAULT_ENV%
    if defined CONDA_PREFIX set "PYTHON_EXEC=%CONDA_PREFIX%\python.exe"
) else (
    echo ?? No Conda environment detected; a temporary virtual environment will be created.
)

if "%USING_CONDA%"=="0" (
    echo.
    echo ?? Creating build environment...
    if exist "build_env" rmdir /s /q build_env
    "%PYTHON_EXEC%" -m venv build_env
    if errorlevel 1 (
        echo ? Error: Failed to create virtual environment
        set "EXIT_CODE=1"
        goto cleanup
    )
    call build_env\Scripts\activate.bat || goto cleanup
    set "PYTHON_EXEC=%WINDOWS_DIR%\build_env\Scripts\python.exe"
    echo ? Build environment activated
) else (
    echo.
    echo ?? Using current environment for build.
)

set "PYTHONPATH=%SRC_DIR%;%PYTHONPATH%"

"%PYTHON_EXEC%" -m pip install --upgrade pip
if errorlevel 1 (
    echo ? Error: Failed to upgrade pip
    set "EXIT_CODE=1"
    goto cleanup
)

if exist "%WINDOWS_REQUIREMENTS%" (
    echo.
    echo ?? Installing Windows-specific requirements...
    "%PYTHON_EXEC%" -m pip install -r "%WINDOWS_REQUIREMENTS%"
    if errorlevel 1 (
        echo ? Error: Failed to install Windows requirements
        set "EXIT_CODE=1"
        goto cleanup
    )
)

echo.
echo ?? Cleaning previous build artifacts...
if exist "dist\BrainDriveInstallerUpdater-win-x64.exe" del /f /q "dist\BrainDriveInstallerUpdater-win-x64.exe"
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
if exist "__pycache__" rmdir /s /q __pycache__

echo.
echo ?? Building executable...
"%PYTHON_EXEC%" -m PyInstaller braindrive-installer-updater-windows.spec --clean --noconfirm
if errorlevel 1 (
    echo ? Error: PyInstaller build failed
    set "EXIT_CODE=1"
    goto cleanup
)

echo.
if exist "dist\BrainDriveInstallerUpdater-win-x64.exe" (
    echo ? Build successful! Executable located at dist\BrainDriveInstallerUpdater-win-x64.exe
) else (
    echo ? Build failed. Executable not found.
    set "EXIT_CODE=1"
)

:cleanup
echo.
if defined VIRTUAL_ENV deactivate
if "%USING_CONDA%"=="0" (
    if exist "build_env" rmdir /s /q build_env
)

if "%EXIT_CODE%"=="0" (
    echo ========================================
    echo ? BUILD COMPLETED SUCCESSFULLY!
    echo ========================================
) else (
    echo ========================================
    echo ? BUILD FAILED!
    echo ========================================
)

echo.
pause

popd >nul
endlocal
exit /b %EXIT_CODE%
