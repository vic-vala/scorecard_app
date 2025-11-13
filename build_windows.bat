@echo off
REM Build script for Scorecard Generator (Windows)
REM
REM This script:
REM 1. Cleans previous builds
REM 2. Runs PyInstaller with the spec file
REM 3. Creates a distributable package
REM
REM Prerequisites:
REM - Python 3.12+ installed
REM - All dependencies installed (pip install -r requirements.txt)
REM - PyInstaller installed (pip install pyinstaller)

echo ========================================
echo   SCORECARD GENERATOR BUILD SCRIPT
echo ========================================
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>NUL
if errorlevel 1 (
    echo ERROR: PyInstaller not found!
    echo Please install it with: pip install pyinstaller
    pause
    exit /b 1
)

echo [1/4] Cleaning previous builds...
if exist build rmdir /S /Q build
if exist dist rmdir /S /Q dist
echo   Done.
echo.

echo [2/4] Running PyInstaller...
echo   This may take several minutes...
pyinstaller scorecard.spec
if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed!
    echo Check the output above for error details.
    pause
    exit /b 1
)
echo   Done.
echo.

echo [3/4] Verifying build...
if not exist "dist\Scorecard_Generator\Scorecard_Generator.exe" (
    echo ERROR: Executable not found in dist folder!
    pause
    exit /b 1
)
echo   Executable found: dist\Scorecard_Generator\Scorecard_Generator.exe
echo.

echo [4/4] Creating distributable package...
REM Create a timestamped zip file for distribution
powershell -Command "Compress-Archive -Path 'dist\Scorecard_Generator' -DestinationPath 'Scorecard_Generator_Windows.zip' -Force"
if errorlevel 1 (
    echo   Warning: Could not create zip file (PowerShell may not be available)
    echo   You can manually zip the dist\ASU_Scorecard_Generator folder
) else (
    echo   Created: Scorecard_Generator_Windows.zip
)
echo.

echo ========================================
echo   BUILD COMPLETE!
echo ========================================
echo.
echo Distribution files:
echo   - Folder: dist\Scorecard_Generator\
echo   - Zip:    Scorecard_Generator_Windows.zip
echo.
echo To distribute:
echo   1. Share the entire dist\ASU_Scorecard_Generator folder, or
echo   2. Share the Scorecard_Generator_Windows.zip file
echo.
echo Users should:
echo   1. Extract the zip (if using zip)
echo   2. Run Scorecard_Generator.exe
echo   3. Complete first-run setup wizard
echo.

pause
