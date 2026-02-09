import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
import pandas as pd
from src.theme import apply_theme

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
    "GPA",
]

GUI_TEXT = {
    "session": {
        "name": "Select Course Sessions",
        "text": (
            "Select course sessions for Scorecard creation.\n"
            "Every row selected will create one Scorecard PDF, with a full page of summary information about the course.\n"
            "When finished selecting all desired course sessions, press Confirm."
        ),
    },
    "course": {
        "name": "Select Courses",
        "text": (
            "Select courses for Course History Graph creation.\n"
            "Every row selected will create one Course History Graph PNG image, with a GPA over time for all course sessions, \ngrouped by instructor.\n"
            "When finished selecting all desired courses, press Confirm."
        ),
    },
    "instructor": {
        "name": "Select Instructors",
        "text": (
            "Select instructors for Instructor Scorecard creation.\n"
            "Every row selected will create one Instructor Scorecard PDF, with a short summary of key information about every \ncourse from the instructor on file.\n"
            "When finished selecting all desired instructors, press Confirm."
        ),
    },
}


class _SelectionTab:
    """
    Internal helper encapsulating the row UI for a single dataframe inside one tab
    """

    def __init__(self, notebook: ttk.Notebook, df: pd.DataFrame, instruction_text: str, tab_title: str):
        self.df = df if df is not None else pd.DataFrame()
        self.instruction_text = instruction_text
        self.tab_title = tab_title
        self.selected_row_ids = set()
        self.visible_cols = [c for c in self.df.columns if c not in HIDDEN_COLUMNS]

        # create tab frame and add to notebook
        self.frame = ttk.Frame(notebook)
        notebook.add(self.frame, text=self.tab_title)

        # build UI within this frame
        self._build_widgets()

        # initial load of all rows
        if not self.df.empty:
            self._reload_tree(list(range(len(self.df))))

    # UI construction #################################

    def _build_widgets(self):
        # instruction label
        instruction_label = ttk.Label(
            self.frame,
            text=self.instruction_text,
            wraplength=1200,
            justify="left",
        )
        instruction_label.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(10, 0))

        # search controls
        search_frame = ttk.Frame(self.frame)
        search_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        ttk.Label(search_frame, text="Column:").pack(side=tk.LEFT, padx=(0, 5))

        self.col_var = tk.StringVar()
        self.col_combo = ttk.Combobox(search_frame, textvariable=self.col_var, state="readonly")
        self.col_combo["values"] = list(self.visible_cols)
        if len(self.visible_cols) > 0:
            self.col_combo.current(0)
        self.col_combo.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))

        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(search_frame, text="Search", style="Accent.TButton", command=self._apply_filter).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(search_frame, text="Reset", command=self._reset_filter).pack(
            side=tk.LEFT
        )

        # treeview
        tree_frame = ttk.Frame(self.frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        y_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        columns = ["__selected__"] + list(self.visible_cols)

        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            yscrollcommand=y_scroll.set,
            selectmode="none",
        )
        self.tree.pack(fill=tk.BOTH, expand=True)
        y_scroll.config(command=self.tree.yview)

        # configure headings
        self.tree.heading("__selected__", text="Selected")
        self.tree.column("__selected__", width=80, anchor=tk.CENTER)

        for col in self.visible_cols:
            self.tree.heading(col, text=str(col))
            self.tree.column(col, anchor=tk.W, width=100)

        self.tree.bind("<Button-1>", self._on_tree_click)

        # bottom per tab controls (selection buttons)
        bottom_frame = ttk.Frame(self.frame)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

        ttk.Button(bottom_frame, text="Select All (visible)", command=self._on_select_all).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(
            bottom_frame, text="Clear Selection (visible)", command=self._on_clear_selection
        ).pack(side=tk.LEFT, padx=(0, 5))

    # filtering / tree management #################################

    def _apply_filter(self):
        if self.df is None or self.df.empty or not self.visible_cols:
            self._reload_tree([])
            return

        col = self.col_var.get()
        pattern = self.search_var.get().strip().lower()
        if not col or pattern == "":
            visible_ids = list(range(len(self.df)))
        else:
            visible_ids = []
            col_idx = self.df.columns.get_loc(col)
            for i in range(len(self.df)):
                value = self.df.iat[i, col_idx]
                if pattern in str(value).lower():
                    visible_ids.append(i)
        self._reload_tree(visible_ids)

    def _reset_filter(self):
        self.search_var.set("")
        if len(self.visible_cols) > 0:
            self.col_combo.current(0)
        if self.df is None or self.df.empty:
            self._reload_tree([])
        else:
            self._reload_tree(list(range(len(self.df))))

    def _autosize_columns(self, row_ids):
        style = ttk.Style(self.tree)
        font_spec = style.lookup("Treeview", "font")
        if not font_spec:
            font_spec = "TkDefaultFont"

        try:
            tree_font = tkfont.Font(self.tree, font=font_spec)
        except tk.TclError:
            tree_font = tkfont.nametofont("TkDefaultFont")

        padding = 20

        # "Selected" checkbox column
        check_heading = "Selected"
        max_sel_width = max(
            tree_font.measure(check_heading),
            tree_font.measure("☑"),
            tree_font.measure("☐"),
        )
        self.tree.column("__selected__", width=max_sel_width + padding, anchor=tk.CENTER)

        # Dataframe columns (only visible ones)
        for col in self.visible_cols:
            heading = str(col)
            max_width = tree_font.measure(heading)
            if self.df is not None and not self.df.empty:
                col_idx = self.df.columns.get_loc(col)
                for row_id in row_ids:
                    value = self.df.iat[row_id, col_idx]
                    w = tree_font.measure(str(value))
                    if w > max_width:
                        max_width = w
            self.tree.column(col, width=max_width + padding, anchor=tk.W)

    def _reload_tree(self, row_ids):
        # clear and repopulate tree with given ids
        self.tree.delete(*self.tree.get_children())
        if self.df is None or self.df.empty:
            self._autosize_columns([])
            return

        for row_id in row_ids:
            row = self.df.iloc[row_id]
            check_char = "☑" if row_id in self.selected_row_ids else "☐"
            values = [check_char] + [row[col] for col in self.visible_cols]
            # use row_id as the item id so we can map back easily
            self.tree.insert("", "end", iid=str(row_id), values=values)
        self._autosize_columns(row_ids)

    # selection handling #################################

    def _toggle_row(self, row_id: int):
        if row_id in self.selected_row_ids:
            self.selected_row_ids.remove(row_id)
        else:
            self.selected_row_ids.add(row_id)

        # update display for that row if it is currently visible
        item_id = str(row_id)
        if item_id in self.tree.get_children():
            vals = list(self.tree.item(item_id, "values"))
            vals[0] = "☑" if row_id in self.selected_row_ids else "☐"
            self.tree.item(item_id, values=vals)

    def _on_tree_click(self, event):
        # determine which row was clicked
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        try:
            row_id = int(item_id)
        except ValueError:
            return
        col = self.tree.identify_column(event.x)
        if col == "#1":
            self._toggle_row(row_id)

    def _on_select_all(self):
        visible_items = self.tree.get_children()
        for item_id in visible_items:
            try:
                row_id = int(item_id)
            except ValueError:
                continue
            if row_id not in self.selected_row_ids:
                self.selected_row_ids.add(row_id)
                vals = list(self.tree.item(item_id, "values"))
                if vals:
                    vals[0] = "☑"
                    self.tree.item(item_id, values=vals)

    def _on_clear_selection(self):
        visible_items = self.tree.get_children()
        for item_id in visible_items:
            try:
                row_id = int(item_id)
            except ValueError:
                continue
            if row_id in self.selected_row_ids:
                self.selected_row_ids.remove(row_id)
                vals = list(self.tree.item(item_id, "values"))
                if vals:
                    vals[0] = "☐"
                    self.tree.item(item_id, values=vals)

    # result helpers #################################

    def get_selected_dataframe(self) -> pd.DataFrame:
        """
        Returns a dataframe of all selected rows (in original order).
        """
        if not isinstance(self.df, pd.DataFrame) or self.df.empty:
            if isinstance(self.df, pd.DataFrame):
                return self.df.iloc[0:0].copy()
            return pd.DataFrame()

        if self.selected_row_ids:
            ordered_ids = [i for i in range(len(self.df)) if i in self.selected_row_ids]
            return self.df.iloc[ordered_ids].copy()
        else:
            return self.df.iloc[0:0].copy()


def select_rows_gui(df: pd.DataFrame, instruction_text: str, title_text: str) -> pd.DataFrame:
    """
    backwards-compatible single-dataframe selection window
    """
    if df is None or df.empty:
        return df.copy()

    root = tk.Tk()
    root.title(title_text)

    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    tab = _SelectionTab(notebook, df, instruction_text, title_text)

    result = {"df": None}

    bottom_frame = ttk.Frame(root)
    bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

    def on_confirm():
        result["df"] = tab.get_selected_dataframe()
        root.destroy()

    ttk.Button(bottom_frame, text="Confirm", command=on_confirm).pack(
        side=tk.RIGHT, padx=(5, 0)
    )

    root.geometry("1280x720")
    root.mainloop()

    if result["df"] is None:
        # user closed the window; match previous behaviour by returning an empty df with same columns
        return df.iloc[0:0].copy()
    return result["df"]


def select_rows_gui_with_tabs(
    scorecard_sessions_df: pd.DataFrame,
    course_history_df: pd.DataFrame,
    instructor_df: pd.DataFrame,
):
    """
    combined selection window with three tabs:

    - Course Sessions
    - Courses (Unique Courses)
    - Instructors

    Returns a tuple of three dataframes:
        (selected_scorecard_courses, selected_history_courses, selected_scorecard_instructors)
    """

    def _normalize(df: pd.DataFrame) -> pd.DataFrame:
        if df is None:
            return pd.DataFrame()
        if not isinstance(df, pd.DataFrame):
            raise TypeError("select_rows_gui_with_tabs expects pandas.DataFrame objects.")
        return df

    scorecard_sessions_df = _normalize(scorecard_sessions_df)
    course_history_df = _normalize(course_history_df)
    instructor_df = _normalize(instructor_df)

    root = tk.Tk()
    apply_theme(root, theme="light")
    root.title("Scorecard / History / Instructor Selection")

    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    session_tab = _SelectionTab(
        notebook,
        scorecard_sessions_df,
        GUI_TEXT["session"]["text"],
        GUI_TEXT["session"]["name"],
    )
    course_tab = _SelectionTab(
        notebook,
        course_history_df,
        GUI_TEXT["course"]["text"],
        GUI_TEXT["course"]["name"],
    )
    instructor_tab = _SelectionTab(
        notebook,
        instructor_df,
        GUI_TEXT["instructor"]["text"],
        GUI_TEXT["instructor"]["name"],
    )

    results = {
        "scorecard": None,
        "history": None,
        "instructor": None,
    }

    bottom_frame = ttk.Frame(root)
    bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

    def on_confirm():
        results["scorecard"] = session_tab.get_selected_dataframe()
        results["history"] = course_tab.get_selected_dataframe()
        results["instructor"] = instructor_tab.get_selected_dataframe()
        root.destroy()

    ttk.Button(bottom_frame, text="Confirm", style="Accent.TButton", command=on_confirm).pack(
        side=tk.RIGHT, padx=(5, 0)
    )

    root.geometry("1280x720")
    root.mainloop()

    # if the user closes the window without confirming, return empty dfs with matching columns
    if results["scorecard"] is None:
        results["scorecard"] = scorecard_sessions_df.iloc[0:0].copy()
    if results["history"] is None:
        results["history"] = course_history_df.iloc[0:0].copy()
    if results["instructor"] is None:
        results["instructor"] = instructor_df.iloc[0:0].copy()

    return results["scorecard"], results["history"], results["instructor"]