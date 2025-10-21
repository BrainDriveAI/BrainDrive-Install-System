@echo off
setlocal EnableDelayedExpansion

set "EXIT_CODE=0"

echo ========================================
echo BrainDrive Installer - Windows Build
echo ========================================
echo.

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%" >nul
for %%I in (.) do set "WINDOWS_DIR=%%~fI"
for %%I in ("%WINDOWS_DIR%\..") do set "REPO_ROOT=%%~fI"
set "COMMON_DIR=%REPO_ROOT%\common"
set "SRC_DIR=%COMMON_DIR%\src"
set "PACKAGE_DIR=%SRC_DIR%\braindrive_installer"
set "MAIN_UI=%PACKAGE_DIR%\ui\main_interface.py"
set "CREATE_VERSION=%PACKAGE_DIR%\installers\create_version_info.py"
set "SHARED_REQUIREMENTS=%PACKAGE_DIR%\requirements.txt"
set "PYTHON_EXEC=python"
set "USING_CONDA=0"

REM ---------------------------------------------------------------------------
REM Environment validation
REM ---------------------------------------------------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo ? Error: Python is not installed or not in PATH
    echo Please install Python 3.11 or later and try again.
    set "EXIT_CODE=1"
    goto cleanup
)

echo ? Python found
python --version

if defined CONDA_DEFAULT_ENV (
    set "USING_CONDA=1"
    echo ? Using active Conda environment: %CONDA_DEFAULT_ENV%
    if defined CONDA_PREFIX (
        set "PYTHON_EXEC=%CONDA_PREFIX%\python.exe"
    )
)

if not exist "%MAIN_UI%" (
    echo ? Error: BrainDrive UI entry point not found.
    echo Expected file: %MAIN_UI%
    set "EXIT_CODE=1"
    goto cleanup
)

echo ? Found BrainDrive main UI at:
echo     %MAIN_UI%

REM ---------------------------------------------------------------------------
REM Virtual environment setup
REM ---------------------------------------------------------------------------
if "%USING_CONDA%"=="0" (
    echo.
    echo ?? Creating build environment...
    if exist "build_env" (
        echo Removing existing build environment...
        rmdir /s /q build_env
    )

    "%PYTHON_EXEC%" -m venv build_env
    if errorlevel 1 (
        echo ? Error: Failed to create virtual environment
        set "EXIT_CODE=1"
        goto cleanup
    )

    echo ? Virtual environment created

    echo.
    echo ?? Activating build environment...
    call build_env\Scripts\activate.bat
    if errorlevel 1 (
        echo ? Error: Failed to activate virtual environment
        set "EXIT_CODE=1"
        goto cleanup
    )

    set "PYTHON_EXEC=%WINDOWS_DIR%\build_env\Scripts\python.exe"
    echo ? Build environment activated
) else (
    echo.
    echo ?? Skipping virtual environment creation; using active Conda environment.
)

set "PYTHONPATH=%SRC_DIR%;%PYTHONPATH%"

REM ---------------------------------------------------------------------------
REM Dependency installation
REM ---------------------------------------------------------------------------
echo.
echo ?? Upgrading pip...
"%PYTHON_EXEC%" -m pip install --upgrade pip
if errorlevel 1 (
    echo ? Error: Failed to upgrade pip
    set "EXIT_CODE=1"
    goto cleanup
)

if exist "%SHARED_REQUIREMENTS%" (
    echo.
    echo ?? Installing shared BrainDrive installer requirements...
    "%PYTHON_EXEC%" -m pip install -r "%SHARED_REQUIREMENTS%"
    if errorlevel 1 (
        echo ? Error: Failed to install shared requirements
        set "EXIT_CODE=1"
        goto cleanup
    )
    echo ? Shared requirements installed
)

echo.
echo ?? Installing project requirements...
"%PYTHON_EXEC%" -m pip install -r requirements-windows.txt
if errorlevel 1 (
    echo ? Error: Failed to install project requirements
    set "EXIT_CODE=1"
    goto cleanup
)

echo ? Project requirements installed

REM ---------------------------------------------------------------------------
REM Version metadata
REM ---------------------------------------------------------------------------
echo.
echo ?? Creating version info...
"%PYTHON_EXEC%" "%CREATE_VERSION%"
if errorlevel 1 (
    echo ? Error: Failed to create version info
    set "EXIT_CODE=1"
    goto cleanup
)

echo ? Version info created

REM ---------------------------------------------------------------------------
REM Build clean-up
REM ---------------------------------------------------------------------------
echo.
echo ?? Cleaning previous build...
if exist "dist\BrainDriveInstaller-win-x64.exe" (
    echo ?? Removing previous installer executable...
    del /f /q "dist\BrainDriveInstaller-win-x64.exe" >nul 2>&1
    if exist "dist\BrainDriveInstaller-win-x64.exe" (
        echo ? Error: Unable to delete dist\BrainDriveInstaller-win-x64.exe. Please ensure it is not running and rerun the build.
        set "EXIT_CODE=1"
        goto cleanup
    )
)
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
if exist "__pycache__" rmdir /s /q __pycache__

REM ---------------------------------------------------------------------------
REM PyInstaller execution
REM ---------------------------------------------------------------------------
echo.
echo ?? Building executable...
echo This may take several minutes...
"%PYTHON_EXEC%" -m PyInstaller braindrive-installer-windows.spec --clean --noconfirm
if errorlevel 1 (
    echo ? Error: PyInstaller build failed
    set "EXIT_CODE=1"
    goto cleanup
)

REM ---------------------------------------------------------------------------
REM Build verification
REM ---------------------------------------------------------------------------
if exist "dist\BrainDriveInstaller-win-x64.exe" (
    echo.
    echo ? Build successful!
    echo ?? Executable created at: dist\BrainDriveInstaller-win-x64.exe
    
    for %%A in ("dist\BrainDriveInstaller-win-x64.exe") do (
        set size=%%~zA
        set /a sizeMB=!size!/1024/1024
    )
    
    echo ?? Executable size: !sizeMB! MB
    
    echo.
    echo ?? Testing executable...
    "dist\BrainDriveInstaller-win-x64.exe" --version >nul 2>&1
    if errorlevel 1 (
        echo ??  Warning: Executable test failed, but file was created
    ) else (
        echo ? Executable test passed
    )
    
    echo.
    echo ?? Build completed successfully!
    echo ?? You can find the installer at: dist\BrainDriveInstaller-win-x64.exe
) else (
    echo ? Build failed! Executable not found.
    set "EXIT_CODE=1"
    goto cleanup
)

REM ---------------------------------------------------------------------------
REM Cleanup phase
REM ---------------------------------------------------------------------------
:cleanup
echo.
echo ?? Cleaning up build environment...
if defined VIRTUAL_ENV (
    deactivate
)
if "%USING_CONDA%"=="0" (
    if exist "build_env" rmdir /s /q build_env
)

if "%EXIT_CODE%"=="0" (
    echo.
    echo ========================================
    echo ? BUILD COMPLETED SUCCESSFULLY!
    echo ========================================
    echo ?? Executable: dist\BrainDriveInstaller-win-x64.exe
    echo ?? Ready for distribution!
    echo ========================================
) else (
    echo.
    echo ========================================
    echo ? BUILD FAILED!
    echo ========================================
    echo Please check the error messages above.
    echo ========================================
)

echo.
pause

:end
popd >nul
endlocal
exit /b %EXIT_CODE%
