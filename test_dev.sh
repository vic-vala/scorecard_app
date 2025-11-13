#!/bin/bash
# Development test script for ASU Scorecard Generator
#
# This script runs the application in development mode (without PyInstaller)
# to quickly test functionality without building.
#
# Useful for:
# - Testing first-run setup without rebuilding
# - Rapid iteration during development
# - Verifying changes before building
#
# Prerequisites:
# - Python 3.12+ installed
# - All dependencies installed (pip install -r requirements.txt)

set -e  # Exit on error

# Use the provided PYTHON_BIN, or fall back to the system's python3
# The execution command will be: PYTHON_BIN="./.venv/bin/python3" ./test_dev.sh
PYTHON_CMD=${PYTHON_BIN:-python3}

echo "========================================"
echo "  ASU SCORECARD GENERATOR - DEV TEST"
echo "========================================"
echo ""

# Check if Python is available
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo "ERROR: $PYTHON_CMD not found!"
    echo "Please install Python 3.12 or higher."
    exit 1
fi

echo "Python version:"
$PYTHON_CMD --version
echo ""

# Optional: Check if running in virtual environment
#if [ -z "$VIRTUAL_ENV" ]; then
#    echo "⚠️  Warning: Not running in a virtual environment"
#    echo "   Consider activating a venv:"
#   echo "   $PYTHON_CMD -m venv venv"
#    echo "   source venv/bin/activate"
#    echo ""
#    read -p "Continue anyway? (y/n) " -n 1 -r
#    echo ""
#    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
#        exit 1
#    fi
#fi

# Check for required dependencies
echo "Checking dependencies..."
$PYTHON_CMD -c "import pandas, matplotlib, seaborn, fitz, openpyxl, pylatex, requests, tqdm" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "ERROR: Some dependencies are missing!"
    echo "Please install them with:"
    echo "  pip install -r requirements.txt"
    exit 1
fi
echo "  ✓ All critical dependencies found"
echo ""

# Option to skip first-run setup for testing
echo "Testing options:"
echo "  1) Run normally (with first-run setup if needed)"
echo "  2) Skip first-run setup (for faster testing)"
echo "  3) Force first-run setup (delete .setup_complete)"
echo "  4) Run smoke tests only (no application launch)"
read -p "Choose option (1-4): " -n 1 -r option
echo ""
echo ""

case $option in
    1)
        echo "Running application normally..."
        $PYTHON_CMD main.py
        ;;
    2)
        echo "Skipping first-run setup..."
        # Create marker file to skip setup
        mkdir -p ~/.asu_scorecard
        touch ~/.asu_scorecard/.setup_complete
        echo "  ✓ Setup marker created"
        echo ""
        $PYTHON_CMD main.py
        ;;
    3)
        echo "Forcing first-run setup..."
        rm -f ~/.asu_scorecard/.setup_complete
        echo "  ✓ Setup marker removed"
        echo ""
        $PYTHON_CMD main.py
        ;;
    4)
        echo "Running smoke tests..."
        $PYTHON_CMD test_frozen.py
        ;;
    *)
        echo "Invalid option. Exiting."
        exit 1
        ;;
esac

echo ""
echo "========================================"
echo "  TEST COMPLETE"
echo "========================================"