import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
import pandas as pd

# columns in this list will NOT be shown in the GUI
HIDDEN_COLUMNS = [
    "Instructor First",
    "Instructor Middle",
    "Instructor Last",
    "Location",
    "Session Code",
    "A+",
    "A",
    "A-",
    "B+",
    "B",
    "B-",
    "C+",
    "C",
    "D",
    "E",
    "EN",
    "EU",
    "I",
    "NR",
    "NR.1",
    "W",
    "X",
    "XE",
    "Y",
    "Z",
    "Class Size",
]


def select_rows_gui(df: pd.DataFrame, instruction_text:str, title_text:str) -> pd.DataFrame:
    """
    Launches a GUI which allows you to select rows in a dataframe, with search options.

    The returned dataframe is a dataframe of all selected rows. 
    """
    if df is None or df.empty:
        return df.copy()

    selected_row_ids = set()
    result = {"df": None}

    visible_cols = [c for c in df.columns if c not in HIDDEN_COLUMNS]

    # create main window
    root = tk.Tk()
    root.title(title_text)

    instruction_label = ttk.Label(
        root,
        text=instruction_text,
        wraplength=1200,
        justify="left",
    )
    instruction_label.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(10, 0))

    # top frame for search controls
    search_frame = ttk.Frame(root)
    search_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

    ttk.Label(search_frame, text="Column:").pack(side=tk.LEFT, padx=(0, 5))

    col_var = tk.StringVar()
    col_combo = ttk.Combobox(search_frame, textvariable=col_var, state="readonly")
    col_combo["values"] = list(visible_cols)
    if len(visible_cols) > 0:
        col_combo.current(0)
    col_combo.pack(side=tk.LEFT, padx=(0, 10))

    ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))

    search_var = tk.StringVar()
    search_entry = ttk.Entry(search_frame, textvariable=search_var, width=30)
    search_entry.pack(side=tk.LEFT, padx=(0, 10))

    def apply_filter():
        col = col_var.get()
        pattern = search_var.get().strip().lower()
        if not col or pattern == "":
            visible_ids = list(range(len(df)))
        else:
            # filter based on substring match (case-insensitive)
            visible_ids = []
            col_idx = df.columns.get_loc(col)
            for i in range(len(df)):
                value = df.iat[i, col_idx]
                if pattern in str(value).lower():
                    visible_ids.append(i)
        reload_tree(visible_ids)

    def reset_filter():
        search_var.set("")
        if len(visible_cols) > 0:
            col_combo.current(0)
        reload_tree(list(range(len(df))))

    ttk.Button(search_frame, text="Search", command=apply_filter).pack(
        side=tk.LEFT, padx=(0, 5)
    )
    ttk.Button(search_frame, text="Reset", command=reset_filter).pack(side=tk.LEFT)

    # frame for treeview
    tree_frame = ttk.Frame(root)
    tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # add scrollbar
    y_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
    y_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    # treeview columns: one for checkbox, then all visible dataframe columns
    columns = ["__selected__"] + list(visible_cols)

    tree = ttk.Treeview(
        tree_frame,
        columns=columns,
        show="headings",
        yscrollcommand=y_scroll.set,
        selectmode="none",
    )
    tree.pack(fill=tk.BOTH, expand=True)
    y_scroll.config(command=tree.yview)

    # configure headings
    tree.heading("__selected__", text="Selected")
    tree.column("__selected__", width=80, anchor=tk.CENTER)

    for col in visible_cols:
        tree.heading(col, text=str(col))
        tree.column(col, anchor=tk.W, width=100)

    # autosize columns to fit text
    def autosize_columns(row_ids):
        style = ttk.Style()
        font_name = style.lookup("Treeview", "font")
        if not font_name:
            font_name = "TkDefaultFont"
        tree_font = tkfont.nametofont(font_name)

        padding = 20

        # selected checkbox column
        check_heading = "Selected"
        max_sel_width = max(
            tree_font.measure(check_heading),
            tree_font.measure("☑"),
            tree_font.measure("☐"),
        )
        tree.column("__selected__", width=max_sel_width + padding, anchor=tk.CENTER)

        # dataframe columns (only visible ones)
        for col in visible_cols:
            heading = str(col)
            max_width = tree_font.measure(heading)
            col_idx = df.columns.get_loc(col)
            for row_id in row_ids:
                text = str(df.iat[row_id, col_idx])
                w = tree_font.measure(text)
                if w > max_width:
                    max_width = w
            tree.column(col, width=max_width + padding, anchor=tk.W)

    def reload_tree(row_ids):
        # clear and repopulate tree with given positional row_ids.
        tree.delete(*tree.get_children())
        for row_id in row_ids:
            row = df.iloc[row_id]
            check_char = "☑" if row_id in selected_row_ids else "☐"
            values = [check_char] + [row[col] for col in visible_cols]
            # Use row_id as the item ID so we can map back easily
            tree.insert("", "end", iid=str(row_id), values=values)
        autosize_columns(row_ids)

    def toggle_row(row_id):
        # toggle selection state for a given positional row_id.
        if row_id in selected_row_ids:
            selected_row_ids.remove(row_id)
        else:
            selected_row_ids.add(row_id)

        # update display for that row if it is currently visible
        item_id = str(row_id)
        if item_id in tree.get_children():
            vals = list(tree.item(item_id, "values"))
            vals[0] = "☑" if row_id in selected_row_ids else "☐"
            tree.item(item_id, values=vals)

    def on_tree_click(event):
        # determine which row was clicked
        item_id = tree.identify_row(event.y)
        if not item_id:
            return
        try:
            row_id = int(item_id)
        except ValueError:
            return
        col = tree.identify_column(event.x)
        if col == "#1":
            toggle_row(row_id)

    tree.bind("<Button-1>", on_tree_click)

    # Bottom frame for buttons
    bottom_frame = ttk.Frame(root)
    bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

    def on_confirm():
        # build resulting dataframe based on selected_row_ids
        if selected_row_ids:
            ordered_ids = [i for i in range(len(df)) if i in selected_row_ids]
            result["df"] = df.iloc[ordered_ids].copy()
        else:
            # return empty df
            result["df"] = df.iloc[0:0].copy()
        root.destroy()

    def on_select_all():
        visible_items = tree.get_children()
        for item_id in visible_items:
            row_id = int(item_id)
            if row_id not in selected_row_ids:
                selected_row_ids.add(row_id)
                vals = list(tree.item(item_id, "values"))
                vals[0] = "☑"
                tree.item(item_id, values=vals)

    def on_clear_selection():
        visible_items = tree.get_children()
        for item_id in visible_items:
            row_id = int(item_id)
            if row_id in selected_row_ids:
                selected_row_ids.remove(row_id)
                vals = list(tree.item(item_id, "values"))
                vals[0] = "☐"
                tree.item(item_id, values=vals)

    ttk.Button(bottom_frame, text="Select All (visible)", command=on_select_all).pack(
        side=tk.LEFT, padx=(0, 5)
    )
    ttk.Button(
        bottom_frame, text="Clear Selection (visible)", command=on_clear_selection
    ).pack(side=tk.LEFT, padx=(0, 5))

    ttk.Button(bottom_frame, text="Confirm", command=on_confirm).pack(
        side=tk.RIGHT, padx=(5, 0)
    )

    reload_tree(list(range(len(df))))

    root.geometry("720x480")

    root.mainloop()

    # if window closed, result["df"] is none
    if result["df"] is None:
        return df.iloc[0:0].copy()
    return result["df"]
