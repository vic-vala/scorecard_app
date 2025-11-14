#!/bin/bash
#
# Copy input files from development environment to dist folder for testing.
#
# This script copies PDF evaluation forms and Excel grade data to the
# built executable's input directories for testing purposes.
#
# Usage (from project root):
#   ./builds/shared/copy_input_files.sh
#
# ** RUN AFTER BUILDING, BEFORE TESTING THE FROZEN EXECUTABLE **

set -e  # Exit on error

# Change to project root directory
cd "$(dirname "$0")/../.."
PROJECT_ROOT=$(pwd)

echo "========================================"
echo "  COPYING INPUT FILES TO DIST"
echo "========================================"
echo ""
echo "Project root: $PROJECT_ROOT"
echo ""

# Source paths (from project input_files)
source_pdfs="$PROJECT_ROOT/input_files/pdfs/*.pdf"
source_excel="$PROJECT_ROOT/input_files/excel/placeholder_excelname.xlsx"

# Target paths (in dist folder)
target_pdf_dir="$PROJECT_ROOT/dist/Scorecard_Generator/input_files/pdfs/"
target_excel_dir="$PROJECT_ROOT/dist/Scorecard_Generator/input_files/excel/"

# Create target directories if they don't exist
mkdir -p "$target_pdf_dir"
mkdir -p "$target_excel_dir"

# Copy PDFs
echo "Copying PDF files..."
if ls $source_pdfs 1> /dev/null 2>&1; then
    cp $source_pdfs "$target_pdf_dir"
    pdf_count=$(ls $source_pdfs | wc -l)
    echo "  ✓ Copied $pdf_count PDF file(s)"
else
    echo "  ⚠️  No PDF files found in input_files/pdfs/"
fi

# Copy Excel
echo "Copying Excel file..."
if [ -f "$source_excel" ]; then
    cp "$source_excel" "$target_excel_dir"
    echo "  ✓ Copied Excel file"
else
    echo "  ⚠️  Excel file not found: $source_excel"
fi

echo ""
echo "========================================"
echo "  COPY COMPLETE"
echo "========================================"
echo ""
echo "Input files are now available in:"
echo "  - $target_pdf_dir"
echo "  - $target_excel_dir"
echo ""