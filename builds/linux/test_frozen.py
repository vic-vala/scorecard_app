#!/usr/bin/env python3
"""
Smoke test script for frozen (PyInstaller) application.

This script verifies that the packaged application has all necessary
dependencies and resources properly bundled.

Usage:
    # Copy to dist folder and run:
    cp test_frozen.py dist/ASU_Scorecard_Generator/
    cd dist/ASU_Scorecard_Generator
    python test_frozen.py

    # Or run from project root:
    cd dist/ASU_Scorecard_Generator
    python ../../test_frozen.py
"""

import sys
import os
from pathlib import Path


def print_header(text):
    """Print a formatted section header."""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)


def print_test(name, passed):
    """Print a test result."""
    status = "✓" if passed else "✗"
    color = "\033[92m" if passed else "\033[91m"
    reset = "\033[0m"
    print(f"{color}{status}{reset} {name}")


def test_imports():
    """Test that all critical dependencies can be imported."""
    print_header("Testing Imports")

    all_passed = True
    imports_to_test = [
        ("json", "json"),
        ("os", "os"),
        ("pandas", "pandas"),
        ("numpy", "numpy"),
        ("matplotlib", "matplotlib"),
        ("matplotlib.pyplot", "matplotlib.pyplot"),
        ("seaborn", "seaborn"),
        ("fitz", "PyMuPDF/fitz"),
        ("openpyxl", "openpyxl"),
        ("pylatex", "PyLaTeX"),
        ("requests", "requests"),
        ("tqdm", "tqdm"),
    ]

    # Optional: test llama_cpp if available
    try:
        import llama_cpp
        imports_to_test.append(("llama_cpp", "llama-cpp-python"))
    except ImportError:
        print("  ℹ llama-cpp-python not available (this is expected if not installed)")

    for module_name, display_name in imports_to_test:
        try:
            __import__(module_name)
            print_test(f"Import {display_name}", True)
        except ImportError as e:
            print_test(f"Import {display_name}", False)
            print(f"    Error: {e}")
            all_passed = False

    return all_passed


def test_resource_access():
    """Test that bundled resource files are accessible."""
    print_header("Testing Resource Access")

    all_passed = True

    # Test resource_utils
    try:
        from src.resource_utils import get_resource_path, get_resources_dir
        print_test("Import resource_utils", True)
    except ImportError as e:
        print_test("Import resource_utils", False)
        print(f"    Error: {e}")
        return False

    # Test critical resource files
    resources = [
        'configuration/config.json',
        'src/schema/parsed_pdf_schema.py',
    ]

    for resource in resources:
        try:
            path = get_resource_path(resource)
            exists = os.path.exists(path)
            print_test(f"Resource: {resource}", exists)
            if not exists:
                print(f"    Expected path: {path}")
                all_passed = False
        except Exception as e:
            print_test(f"Resource: {resource}", False)
            print(f"    Error: {e}")
            all_passed = False

    # Test resources directory
    try:
        resources_dir = get_resources_dir()
        print_test(f"Resources dir: {resources_dir}", True)
    except Exception as e:
        print_test("Resources dir", False)
        print(f"    Error: {e}")
        all_passed = False

    return all_passed


def test_src_imports():
    """Test that src modules can be imported."""
    print_header("Testing Source Module Imports")

    all_passed = True
    modules = [
        'src.utils',
        'src.resource_utils',
        'src.first_run_setup',
        'src.setup_wizard',
        'src.pdf_parser',
        'src.excel_parser',
        'src.csv_cleaner',
        'src.data_handler',
        'src.data_vis',
        'src.scorecard_assembler',
        'src.compute_metrics',
        'src.llm_io',
        'src.config_gui',
        'src.select_rows_gui',
    ]

    for module in modules:
        try:
            __import__(module)
            print_test(f"Import {module}", True)
        except ImportError as e:
            print_test(f"Import {module}", False)
            print(f"    Error: {e}")
            all_passed = False

    return all_passed


def test_config_loading():
    """Test that config file can be loaded."""
    print_header("Testing Configuration Loading")

    try:
        from src import utils
        config = utils.load_config()
        print_test("Load config.json", True)

        # Check critical config sections
        has_paths = 'paths' in config
        print_test("Config has 'paths' section", has_paths)

        has_settings = 'scorecard_gen_settings' in config
        print_test("Config has 'scorecard_gen_settings' section", has_settings)

        return has_paths and has_settings
    except Exception as e:
        print_test("Load config.json", False)
        print(f"    Error: {e}")
        return False


def test_gui_available():
    """Test that Tkinter GUI is available."""
    print_header("Testing GUI Availability")

    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()  # Don't show window
        root.destroy()
        print_test("Tkinter GUI available", True)
        return True
    except Exception as e:
        print_test("Tkinter GUI available", False)
        print(f"    Error: {e}")
        return False


def test_frozen_detection():
    """Test PyInstaller frozen state detection."""
    print_header("Testing Frozen State Detection")

    is_frozen = hasattr(sys, '_MEIPASS')
    print_test(f"Running in frozen mode: {is_frozen}", True)

    if is_frozen:
        print(f"    _MEIPASS: {sys._MEIPASS}")
    else:
        print("    Running in development mode")

    return True


def test_first_run_setup():
    """Test first-run setup module."""
    print_header("Testing First-Run Setup")

    try:
        from src.first_run_setup import FirstRunSetup
        setup = FirstRunSetup()
        print_test("Import FirstRunSetup", True)

        # Test resources directory creation
        setup.resources_dir.mkdir(parents=True, exist_ok=True)
        dir_exists = setup.resources_dir.exists()
        print_test("Resources directory accessible", dir_exists)

        # Test setup status check
        is_first = setup.is_first_run()
        print_test(f"First run check works (status: {is_first})", True)

        return dir_exists
    except Exception as e:
        print_test("First-run setup", False)
        print(f"    Error: {e}")
        return False


def main():
    """Run all smoke tests."""
    print_header("ASU SCORECARD GENERATOR - SMOKE TESTS")
    print(f"Python: {sys.version}")
    print(f"Executable: {sys.executable}")
    print(f"Working dir: {os.getcwd()}")

    # Run all tests
    results = {
        "Imports": test_imports(),
        "Source Modules": test_src_imports(),
        "Resource Access": test_resource_access(),
        "Config Loading": test_config_loading(),
        "GUI Availability": test_gui_available(),
        "Frozen Detection": test_frozen_detection(),
        "First-Run Setup": test_first_run_setup(),
    }

    # Print summary
    print_header("TEST SUMMARY")
    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        print_test(test_name, result)

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n✓ All tests passed! The frozen application is ready to use.")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())