import json
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# hard coded display names
PRETTY_NAME_MAP = {
    "include_LLM_insights": ("Include LLM summary?", "If this setting is enabled, an AI model with generate a short summary of student comments on each course scorecard. This may take a few minutes per scorecard."),
    "overwrite_csv": ("Overwrite CSV?", "[Advanced]\nOverwrites internal CSV files created from Excel sheets.\n(Recommended: False)"),
    "overwrite_json": ("Overwrite JSON?", "[Advanced]\nOverwrites internal JSON files created from Excel sheets.\n(Recommended: False)"),
    "pdf_source": ("PDF Source", "The folder where all Course Evaluation PDF files are located."),
    "excel_source": ("Excel Source", "The course history excel file."),
    "scorecard_dir": ("Scorecard Directory", "The desired folder for finised scorecard PDFs."),

    "match_term": ("Match Term?", "Courses will only be compared against other courses of the same term. (Fall/Spring/Summer)\n(Recommended: True)"),
    "match_year": ("Match Year?", "Courses will only be compared against other courses of the same calendar year.\n(Recommended: True)"),
    "match_subject": ("Match Subject?", "Courses will only be comapred against other courses of the same subject. (CSE, IEE, SER, etc.)\n(Recommended: True)"),
    "match_catalog_number": ("Match Catalog Number?", "Courses will only be comapred against other courses of the same catalog number. \nIf the \"hundred\" option is selected, all courses in the same x00-x99 range will be compared to each other. (100-199, 200-299, 300-399, etc.)\n(Recommended: Hundred)"),
}

# keys shown in the GUI (all others are hidden) and their display order
SHOWN_KEYS = [
    "pdf_source",
    "excel_source",
    "scorecard_dir",
    "include_LLM_insights",
    "match_term",
    "match_year",
    "match_subject",
    "match_catalog_number",
    "overwrite_csv",
    "overwrite_json",
]

def prettify_key(key: str) -> str:
    if key in PRETTY_NAME_MAP:
        return PRETTY_NAME_MAP[key]
    return key.replace("_", " ").title()

def _looks_like_path(key: str, value) -> bool:
    if not isinstance(value, str):
        return (
            "path" in key.lower()
            or "dir" in key.lower()
            or "file" in key.lower()
            or "source" in key.lower()
        )
    k = key.lower()
    if any(t in k for t in ("path", "dir", "file", "source")):
        return True
    return ("/" in value or os.sep in value) or bool(os.path.splitext(value)[1])

def _prefer_directory_chooser(key: str, value) -> bool:
    k = key.lower()
    if "dir" in k:
        return True
    if not isinstance(value, str):
        return False
    root, ext = os.path.splitext(value)
    return ext == ""

def open_config_editor(json_path: str) -> None:
    # load
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # tk
    root = tk.Tk()
    root.title("Configuration")
    root.geometry("900x650")

    fields = {}

    def add_option_row(parent, section_name, key, value):
        row = tk.Frame(parent)
        row.pack(fill="x", padx=8, pady=4)

        # description above the option
        desc_text = get_description(key)
        if desc_text:
            desc_label = tk.Label(row, text=desc_text, anchor="w", justify="left")
            desc_label.pack(fill="x")

        # line that contains label + control
        line = tk.Frame(row)
        line.pack(fill="x")

        label = tk.Label(line, text=prettify_key(key), width=26, anchor="w")
        label.pack(side="left")

        # decide control type
        is_bool = isinstance(value, bool)
        is_bool_str = isinstance(value, str) and value.lower() in ("true", "false")
        is_path = _looks_like_path(key, value)
        use_dir = _prefer_directory_chooser(key, value)

        # special tri-state for match_catalog_number
        if key == "match_catalog_number":
            var = tk.StringVar(value=str(value))
            combo = ttk.Combobox(
                line,
                textvariable=var,
                values=["true", "false", "hundred"],
                state="readonly",
            )
            combo.pack(side="left", fill="x", expand=True)
            fields[(section_name, key)] = {"var": var, "type": "str"}

        elif is_bool or is_bool_str:
            var = tk.BooleanVar(value=(value if is_bool else value.lower() == "true"))
            chk = tk.Checkbutton(line, variable=var)
            chk.pack(side="left", anchor="w")
            fields[(section_name, key)] = {
                "var": var,
                "type": ("bool" if is_bool else "bool_str"),
            }

        elif is_path:
            var = tk.StringVar(value=str(value))
            ent = tk.Entry(line, textvariable=var)
            ent.pack(side="left", fill="x", expand=True)

            def choose_path(target_var=var, directory=use_dir):
                if directory:
                    p = filedialog.askdirectory(
                        initialdir=os.path.dirname(target_var.get()) or os.getcwd(),
                        mustexist=False,
                    )
                else:
                    p = filedialog.askopenfilename(
                        initialdir=os.path.dirname(target_var.get()) or os.getcwd()
                    )
                if p:
                    target_var.set(os.path.normpath(p))

            btn = tk.Button(line, text="Browse", command=choose_path)
            btn.pack(side="left", padx=6)
            fields[(section_name, key)] = {"var": var, "type": "str"}

        else:
            var = tk.StringVar(value=str(value))
            ent = tk.Entry(line, textvariable=var)
            ent.pack(side="left", fill="x", expand=True)
            fields[(section_name, key)] = {"var": var, "type": "str"}


    # main scrollable area (single page, no tabs)
    frame = tk.Frame(root)
    canvas = tk.Canvas(frame)
    vsb = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
    inner = tk.Frame(canvas)

    inner.bind(
        "<Configure>",
        lambda e, c=canvas: c.configure(scrollregion=c.bbox("all")),
    )
    canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=vsb.set)

    canvas.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")
    frame.pack(fill="both", expand=True)

    # collect all config items, indexed by key
    items_by_key = {}
    for section_name, section_value in data.items():
        if isinstance(section_value, dict):
            for k, v in section_value.items():
                items_by_key.setdefault(k, []).append((section_name, v))
        else:
            items_by_key.setdefault(section_name, []).append(
                (section_name, section_value)
            )

    # render only SHOWN_KEYS, in the given order
    for key in SHOWN_KEYS:
        if key in items_by_key:
            section_name, value = items_by_key[key][0]
            add_option_row(inner, section_name, key, value)

    # actions
    def save_and_close():
        # push values back into data
        for (section, key), meta in fields.items():
            var = meta["var"]
            t = meta["type"]
            new_value = var.get()
            if t == "bool":
                # already bool
                pass
            elif t == "bool_str":
                new_value = "true" if bool(new_value) else "false"
            else:
                new_value = str(new_value)

            if isinstance(data.get(section), dict):
                data[section][key] = new_value
            else:
                data[section] = new_value

        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            messagebox.showinfo("Saved", "Configuration saved")
            root.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save:\n{e}")

    btn_bar = tk.Frame(root)
    btn_bar.pack(fill="x", padx=8, pady=8)
    tk.Button(btn_bar, text="Save", command=save_and_close).pack(
        side="right", padx=4
    )
    tk.Button(btn_bar, text="Cancel", command=root.destroy).pack(
        side="right", padx=4
    )

    root.mainloop()

def _label_and_description_for_key(key: str) -> tuple[str, str]:
    if key in PRETTY_NAME_MAP:
        val = PRETTY_NAME_MAP[key]
        if isinstance(val, tuple):
            if len(val) == 2:
                return str(val[0]), str(val[1])
            if len(val) == 1:
                return str(val[0]), "TODO placeholder"
        else:
            return str(val), "TODO placeholder"
    # fallback for unknown keys
    label = key.replace("_", " ").title()
    return label, "TODO placeholder"


def prettify_key(key: str) -> str:
    label, _ = _label_and_description_for_key(key)
    return label


def get_description(key: str) -> str:
    _, desc = _label_and_description_for_key(key)
    return desc
