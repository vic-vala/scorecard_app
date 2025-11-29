# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Scorecard Generator

This spec file configures PyInstaller to create a cross-platform executable
with all necessary dependencies bundled.

Usage (from project root):
    pyinstaller builds/shared/scorecard.spec

Note: This spec file is located in builds/shared/ and expects to be run
from the project root directory. The build scripts handle this automatically.
"""

import os
import sys

# Get the project root directory
# The build scripts cd to project root before running PyInstaller,
# so we should already be in the project root directory
project_root = os.getcwd()

# Debug output to verify paths
print(f"Current working directory: {os.getcwd()}")
print(f"project_root: {project_root}")

# Verify main.py exists in current directory
main_py_path = os.path.join(project_root, 'main.py')
if not os.path.exists(main_py_path):
    raise FileNotFoundError(
        f"main.py not found at {main_py_path}\n"
        f"Current directory: {os.getcwd()}\n"
        f"Directory contents: {os.listdir(project_root)}"
    )
print(f"✓ main.py found at: {main_py_path}")


block_cipher = None

a = Analysis(
    [main_py_path],  # Use absolute path to main.py
    pathex=[project_root],
    binaries=[],
    datas=[
        # Configuration files (but not the large GGUF model)
        (os.path.join(project_root, 'configuration/config.json'), 'configuration'),
        (os.path.join(project_root, 'configuration/LLM/*.txt'), 'configuration/LLM'),  # Prompt files only

        # Schema files
        (os.path.join(project_root, 'src/schema/*.py'), 'src/schema'),

        # Azure ttk theme files
        (os.path.join(project_root, 'src/azure.tcl'), 'src'),
        (os.path.join(project_root, 'src/theme'), 'src/theme'),
    ],
    hiddenimports=[
        # Tkinter and GUI
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',

        # PIL/Pillow tkinter support
        'PIL._tkinter_finder',
        'PIL.Image',
        'PIL.ImageTk',

        # Data processing
        'pandas._libs.tslibs.timedeltas',
        'pandas._libs.tslibs.np_datetime',
        'pandas._libs.tslibs.nattype',
        'pandas._libs.skiplist',

        # Plotting
        'matplotlib.backends.backend_tkagg',
        'seaborn',

        # LLM
        'llama_cpp',
        'llama_cpp.llama_cpp',

        # Other
        'scipy.special._ufuncs_cxx',
        'openpyxl',
        'pymupdf',
        'fitz',

        # Setup utilities
        'requests',
        'tqdm',
        'pytinytex',
    ],
    hookspath=[os.path.join(project_root, 'hooks')],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'pytest',
        'setuptools',
        'wheel',
        'pip',
        'IPython',
        'jupyter',
        'notebook',
        'sphinx',
        'tornado',
        'zmq',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove MKL from numpy to reduce size (optional optimization)
# Uncomment if you want to reduce size by ~200-400MB
# a.binaries = [x for x in a.binaries if not x[0].startswith('mkl')]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # Use --onedir mode (faster startup than --onefile)
    name='Scorecard_Generator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Enable UPX compression to reduce file size
    console=True,  # Set to False if you want GUI-only mode (no console window)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='assets/icon.ico'  # Uncomment and add your icon file
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Scorecard_Generator'
)
