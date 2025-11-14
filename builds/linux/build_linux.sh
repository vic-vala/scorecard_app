#!/bin/bash
# Build script for our app (Linux/WSL)
#
# This script creates a Linux executable for testing the packaging setup.
# Use this for development/testing in WSL. For Windows distribution, use build_windows.bat
#
# Prerequisites:
# - Python 3.12+ installed
# - All dependencies installed (pip install -r requirements.txt)
# - PyInstaller installed (pip install pyinstaller)

set -e  # Exit on error

# Change to project root directory
cd "$(dirname "$0")/../.."
PROJECT_ROOT=$(pwd)

# Use the provided PYTHON_BIN, or fall back to the system's python3
# FOLLOW THIS EXECUTION COMMAND: PYTHON_BIN="./.venv/bin/python3" ./builds/linux/build_linux.sh
PYTHON_CMD=${PYTHON_BIN:-python3}

echo "========================================"
echo "  SCORECARD GENERATOR BUILD SCRIPT"
echo "  (Linux/WSL)"
echo "========================================"
echo ""
echo "Project root: $PROJECT_ROOT"
echo ""

# Check if PyInstaller is installed
if ! $PYTHON_CMD -c "import PyInstaller" 2>/dev/null; then
    echo "ERROR: PyInstaller not found!"
    echo "Please install it with: pip install pyinstaller"
    exit 1
fi

echo "[1/4] Cleaning previous builds..."
rm -rf build dist
echo "  Done."
echo ""

echo "[2/4] Running PyInstaller..."
echo "  This may take several minutes..."
pyinstaller builds/shared/scorecard.spec
if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: PyInstaller build failed!"
    echo "Check the output above for error details."
    exit 1
fi
echo "  Done."
echo ""

echo "[3/4] Verifying build..."
if [ ! -f "dist/Scorecard_Generator/Scorecard_Generator" ]; then
    echo "ERROR: Executable not found in dist folder!"
    exit 1
fi
chmod +x dist/Scorecard_Generator/Scorecard_Generator
echo "  Executable found: dist/Scorecard_Generator/Scorecard_Generator"
echo ""

echo "[4/4] Creating distributable package..."
if command -v zip &> /dev/null; then
    cd dist
    zip -r ../Scorecard_Generator_Linux.zip Scorecard_Generator/
    cd ..
    echo "  Created: Scorecard_Generator_Linux.zip"
else
    echo "  Warning: 'zip' command not found, skipping zip creation"
    echo "  You can manually create a tarball:"
    echo "    tar -czf Scorecard_Generator_Linux.tar.gz dist/Scorecard_Generator/"
fi
echo ""

echo "========================================"
echo "  BUILD COMPLETE!"
echo "========================================"
echo ""
echo "Distribution files:"
echo "  - Folder: dist/ASU_Scorecard_Generator/"
echo "  - Zip:    ASU_Scorecard_Generator_Linux.zip"
echo ""
echo "To test the build:"
echo "  cd dist/Scorecard_Generator"
echo "  ./Scorecard_Generator"
echo ""
echo "To run automated tests:"
echo "  ($PYTHON_CMD) builds/linux/test_frozen.py"
echo ""
echo "Note: This Linux build is for testing only."
echo "For Windows distribution, use builds/windows/build_windows.bat"
echo ""
