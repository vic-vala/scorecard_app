import os
from tkinter import ttk


def apply_theme(root, theme: str = "light") -> None:
    """
    Apply the ttk theme to the given Tk root window
    Looks for 'azure.tcl' in the same directory as this file
    https://github.com/rdbende/Azure-ttk-theme
    """
    here = os.path.dirname(os.path.abspath(__file__))
    theme_file = os.path.join(here, "azure.tcl")

    if os.path.exists(theme_file):
        root.tk.call("source", theme_file)
        root.tk.call("set_theme", theme)
    else:
        # fall back to a standard ttk theme
        style = ttk.Style(root)
        try:
            style.theme_use("clam")
        except Exception:
            pass