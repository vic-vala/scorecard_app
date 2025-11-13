# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for ASU Scorecard Generator

This spec file configures PyInstaller to create a Windows executable
with all necessary dependencies bundled.

Usage:
    pyinstaller scorecard.spec
"""

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Configuration files (but not the large GGUF model)
        ('configuration/config.json', 'configuration'),
        ('configuration/LLM/*.txt', 'configuration/LLM'),  # Prompt files only

        # Schema files
        ('src/schema/*.py', 'src/schema'),
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
    hookspath=['./hooks'],
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
