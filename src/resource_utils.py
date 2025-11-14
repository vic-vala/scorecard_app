"""
Resource path utilities for PyInstaller compatibility.

Provides functions to access bundled resources correctly in both development
and frozen (PyInstaller) environments.
"""

import sys
import os
from pathlib import Path


def get_resource_path(relative_path: str) -> str:
    """
    Get absolute path to resource, works for both dev and PyInstaller.

    When running in a PyInstaller bundle, sys._MEIPASS contains the path to the
    temporary folder where PyInstaller extracts bundled files. In development,
    we use the current working directory.

    Args:
        relative_path: Relative path from project root (e.g., 'configuration/config.json')

    Returns:
        Absolute path to the resource

    Example:
        >>> config_path = get_resource_path('configuration/config.json')
        >>> with open(config_path, 'r') as f:
        >>>     config = json.load(f)
    """
    if hasattr(sys, '_MEIPASS'):
        # Running in PyInstaller bundle
        base_path = sys._MEIPASS
    else:
        # Running in development
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def get_project_root() -> Path:
    """
    Get the project root directory.

    When running in a PyInstaller bundle, returns the directory containing
    the executable. In development, returns the current working directory.

    Returns:
        Path to project root directory
    """
    if hasattr(sys, '_MEIPASS'):
        # Running in PyInstaller bundle - use executable's directory
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).parent
        else:
            return Path(sys._MEIPASS).parent
    else:
        # Running in development - use current working directory
        return Path.cwd()


def get_resources_dir() -> Path:
    """
    Get the resources directory for LaTeX distribution.

    This directory is used for:
    - TinyTeX installation
    - Setup completion markers

    Returns:
        Path to resources directory (./resources)
    """
    return get_project_root() / 'resources'


def ensure_resources_dir() -> Path:
    """
    Ensure resources directory exists and return its path.

    Returns:
        Path to resources directory
    """
    resources_dir = get_resources_dir()
    resources_dir.mkdir(parents=True, exist_ok=True)
    return resources_dir


def get_user_config_path() -> Path:
    """
    Get the path to the user's writable config file.

    In frozen (PyInstaller) mode, this creates a writable config in the
    project root alongside the executable. In development, it returns None
    to use the bundled config directly.

    Returns:
        Path to user config file, or None if using bundled config
    """
    if getattr(sys, 'frozen', False):
        # Frozen mode: use writable config next to executable
        return get_project_root() / 'configuration' / 'config.json'
    else:
        # Development mode: use bundled config directly
        return None


def get_writable_config_path() -> Path:
    """
    Get the path to the writable config.json file.

    This function returns the appropriate config.json path for both frozen
    (PyInstaller) and development environments:
    - Frozen mode: Returns config in dist/Scorecard_Generator/configuration/
    - Development mode: Returns config in project root configuration/

    The returned path is always writable and suitable for storing user settings
    like custom model paths.

    Returns:
        Path to writable config.json file

    Example:
        >>> config_path = get_writable_config_path()
        >>> with open(config_path, 'r') as f:
        >>>     config = json.load(f)
        >>> config['paths']['gguf_path'] = '/path/to/model.gguf'
        >>> with open(config_path, 'w') as f:
        >>>     json.dump(config, f, indent=4)
    """
    config_path = get_project_root() / 'configuration' / 'config.json'

    # Ensure the configuration directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    return config_path
