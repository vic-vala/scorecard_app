"""
PyInstaller hook for llama-cpp-python

This hook ensures that llama-cpp-python's shared libraries and data files
are correctly bundled in the PyInstaller executable.

llama-cpp-python has native dependencies (libllama.so/dylib/dll) that need
to be explicitly collected for the frozen application to work.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

# Collect all data files from llama_cpp package
datas = collect_data_files('llama_cpp')

# Collect all dynamic libraries (.so, .dll, .dylib)
binaries = collect_dynamic_libs('llama_cpp')

# Ensure the main llama_cpp module is imported
hiddenimports = ['llama_cpp.llama_cpp']
