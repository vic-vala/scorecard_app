import json
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# hard coded display names
PRETTY_NAME_MAP = {
    "sem": "Semester",
    "include_LLM_insights": "Include LLM Insights",
    "overwrite_csv": "Overwrite CSV?",
    "overwrite_json": "Overwrite JSON?",
    "pdf_source": "PDF Source",
    "excel_source": "Excel Source",
    "csv_dir": "CSV Directory",
    "tex_dir": "TeX Directory",
    "parsed_pdf_dir": "Parsed PDF Directory",
    "temp_dir": "Temp Directory",
    "scorecard_dir": "Scorecard Directory",
    "schema_source": "Schema Source",
    "llm_prompt_dir": "LLM Prompt Directory",
    "gguf_path": "GGUF Model Path",
}

# keys hidden from the GUI
HIDDEN_KEYS = {"gguf_path"}

def prettify_key(key: str) -> str:
    if key in PRETTY_NAME_MAP:
        return PRETTY_NAME_MAP[key]
    return key.replace("_", " ").title()

def _looks_like_path(key: str, value) -> bool:
    if not isinstance(value, str):
        return "path" in key.lower() or "dir" in key.lower() or "file" in key.lower() or "source" in key.lower()
    k = key.lower()
    if any(t in k for t in ("path", "dir", "file", "source")):
        return True
    return ("/" in value or "\\" in value) or bool(os.path.splitext(value)[1])

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
    root.title(f"Configuration")
    root.geometry("900x650")

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)

    fields = {} 

    def add_option_row(parent, section_name, key, value):
        if key in HIDDEN_KEYS:
            return

        row = tk.Frame(parent)
        row.pack(fill="x", padx=8, pady=4)

        label = tk.Label(row, text=prettify_key(key), width=26, anchor="w")
        label.pack(side="left")

        # decide control type
        val_type = "str"
        is_bool = isinstance(value, bool)
        is_bool_str = isinstance(value, str) and value.lower() in ("true", "false")
        is_path = _looks_like_path(key, value)
        use_dir = _prefer_directory_chooser(key, value)

        if is_bool or is_bool_str:
            var = tk.BooleanVar(value=(value if is_bool else value.lower() == "true"))
            chk = tk.Checkbutton(row, variable=var)
            chk.pack(side="left", anchor="w")
            fields[(section_name, key)] = {"var": var, "type": ("bool" if is_bool else "bool_str")}
        elif is_path:
            var = tk.StringVar(value=str(value))
            ent = tk.Entry(row, textvariable=var)
            ent.pack(side="left", fill="x", expand=True)

            def choose_path(target_var=var, directory=use_dir):
                if directory:
                    p = filedialog.askdirectory(initialdir=os.path.dirname(target_var.get()) or os.getcwd(), mustexist=False)
                else:
                    p = filedialog.askopenfilename(initialdir=os.path.dirname(target_var.get()) or os.getcwd())
                if p:
                    target_var.set(os.path.normpath(p))

            btn = tk.Button(row, text="Browse", command=choose_path)
            btn.pack(side="left", padx=6)
            fields[(section_name, key)] = {"var": var, "type": "str"}
        else:
            var = tk.StringVar(value=str(value))
            ent = tk.Entry(row, textvariable=var)
            ent.pack(side="left", fill="x", expand=True)
            fields[(section_name, key)] = {"var": var, "type": "str"}

    # build UI per top-level section
    for section_name, section_value in data.items():
        frame = tk.Frame(notebook)
        # make section scrollable for large configs
        canvas = tk.Canvas(frame)
        vsb = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas)

        inner.bind(
            "<Configure>",
            lambda e, c=canvas: c.configure(scrollregion=c.bbox("all"))
        )
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)

        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # render options
        if isinstance(section_value, dict):
            for k in sorted(section_value.keys()):
                add_option_row(inner, section_name, k, section_value[k])
        else:
            add_option_row(inner, section_name, section_name, section_value)

        notebook.add(frame, text=prettify_key(section_name))

    # actions
    def save_and_close():
        # push values back into data
        for (section, key), meta in fields.items():
            var = meta["var"]
            t = meta["type"]
            new_value = var.get()
            if t == "bool":
                pass # already bool
            elif t == "bool_str":
                new_value = "true" if bool(new_value) else "false"
            else:
                # keep as string
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
    tk.Button(btn_bar, text="Save", command=save_and_close).pack(side="right", padx=4)
    tk.Button(btn_bar, text="Cancel", command=root.destroy).pack(side="right", padx=4)

    root.mainloop()

