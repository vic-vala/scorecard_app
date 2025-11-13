from __future__ import annotations

import sys
import re
from typing import Optional, Tuple, List
import pandas as pd
import numpy as np


def decode_strm(strm: str | int) -> str:
    """
    Go from strm (4 digit column) to a year and term

    How the strm works:
    - The first 3 digits + 1800 is the year
    - The last digit maps in this way:
        1 = Spring
        4 = Summer
        7 = Fall
    
    This function returns {term} {year} as a string
    Ex: 2257 -> Fall 2025
    """
    try:
        s = int(strm)
    except Exception:
        return f"Unknown term in strm: {strm}"
    year_code = s // 10
    term_code = s % 10
    term_map = {1: "Spring", 4: "Summer", 7: "Fall"}
    term = term_map.get(term_code, f"UnkownTerm({term_code})")
    year = 1800 + year_code
    if term_code == 1:
        year -= 1
    return f"{term} {year}"

gpa_scale = {
    "A+": 4.33, "A": 4.0, "A-": 3.67,
    "B+": 3.33, "B": 3.0, "B-": 2.67,
    "C+": 2.33, "C": 2.0, "D": 1.0, "E": 0.0,
}

def _norm(s: str) -> str:
    """
    Normalize strings for comparison (does nothing if not a string)

    - Strip leading and trailing whitespace
    - Convert to lowercase
    - Collapse any sequence of whitespace characters into a single space
    """
    return re.sub(r"\s+", " ", s.strip().lower()) if isinstance(s, str) else s

def _find_col(df: pd.DataFrame, targets: List[str]) -> Optional[str]:
    """
    Given a list of names, tries to find a column name that matches

    Basically, double checking the column exists, or checking multiple column names
    (Mostly useful in CSV cleaning, since hopefully everything is normalized afterwards)
    """
    tset = {t.strip().lower() for t in targets}
    for col in df.columns:
        if _norm(col) in tset:
            return col
    # loose match
    for col in df.columns:
        c = _norm(col)
        if any(t in c for t in tset):
            return col
    return None

def _is_empty_like(val) -> bool:
    """
    Returns true if a value should be treated as empty

    Basically combines:
    - pd.isna
    - if string, checking that it isn't sometihng like "", "na", "n/a", "null", "none"

    This shouldn't cause issues unless someone's first/last name ends up being "none", "null", or "na"
    """
    if pd.isna(val):
        return True
    if isinstance(val, str):
        v = val.strip().lower()
        if v in {"", "na", "n/a", "null", "none"}:
            return True
        if re.fullmatch(r"-+|—+", v):
            return True
    return False

def _split_instructor(name: str) -> Tuple[str, str, str]:
    """
    This function goes from a full instructor name to a Tuple of their first/middle/last
    """

    if name is None or str(name).strip() == "":
        return "", "", ""
    s = str(name)

    # remove suffixes and such
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"\b(Jr\.?|Sr\.?|II|III|IV|Esq\.?)\b", " ", s, flags=re.I)
    s = re.sub(r"\b(Ph\.?\s*D\.?|M\.?\s*D\.?|Ed\.?\s*D\.?|D\.?\s*Phil\.?|MBA|MS|MA|BA|BS)\b", " ", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip(", ").strip()

    if "," in s:
        # last, first middle
        last, rest = [part.strip() for part in s.split(",", 1)]
        tokens = rest.split()
        first = tokens[0] if tokens else ""
        middle = " ".join(tokens[1:]) if len(tokens) > 1 else ""
        return first, middle, last

    # first middle last
    tokens = s.split()
    if len(tokens) == 1:
        return tokens[0], "", ""
    first = tokens[0]
    last = tokens[-1]
    middle = " ".join(tokens[1:-1]) if len(tokens) > 2 else ""
    return first, middle, last

def clean_csv(csv_path: str) -> None:
    """
    1. Get rid of "total" rows with no actual course info
    2. Semester/Term columns (go from Strm column to year and term/semester)
    3. First/middle/last name columns from instructor column
    4. Handling of empty cels where numbers are expected (replace with 0)
    5. Finding any rows that are still invalid after all of that (just prints them for now)
    6. Compute GPA as a new column
    """
    # read as strings to preserve raw values
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False, na_values=["", " "])
    original_len = len(df)

    # 1. Get rid of "total" rows with no actual course info
    # aka if any course-identity columns exist and are blank OR equal 'total'
    candidate_keys = []
    for col in df.columns:
        c = _norm(col)
        if any(k in c for k in ["course", "subject", "catalog", "class nbr", "class number", "course id", "title", "descr", "section"]):
            candidate_keys.append(col)

    mask_total_label = pd.Series(False, index=df.index)
    mask_all_course_blanks = pd.Series(False, index=df.index)

    if candidate_keys:
        # exact 'total' or 'grand total' in any key-like column
        mask_total_label = df[candidate_keys].apply(
            lambda s: s.astype(str)
            .str.strip()
            .str.fullmatch(r"(?i)(grand\s+)?total"), axis=0
        ).any(axis=1)

        # all key-like columns empty
        empties = df[candidate_keys].map(_is_empty_like)
        mask_all_course_blanks = empties.all(axis=1)

    else:
        # fallback: any cell equals 'total'
        mask_total_label = df.apply(
            lambda r: any(
                isinstance(v, str) and re.fullmatch(r"(?i)(grand\s+)?total", v.strip() or "")
                for v in r.values
            ),
            axis=1,
        )

    drop_mask = mask_total_label | mask_all_course_blanks
    df = df.loc[~drop_mask].copy()

    # 2. strm -> year, term
    strm_col = _find_col(df, ["strm"])
    if strm_col:
        decoded = df[strm_col].apply(decode_strm)
        term_out = decoded.str.extract(r"^(Spring|Summer|Fall|UnknownTerm\(\d+\))", expand=False)
        year_out = decoded.str.extract(r"(\d{4})$", expand=False)
        insert_at = list(df.columns).index(strm_col) + 1
        df.insert(insert_at, "Term", term_out.fillna("Unknown"))
        df.insert(insert_at + 1, "Year", pd.to_numeric(year_out, errors="coerce"))

    # 3. First/middle/last name columns from instructor column
    instr_col = _find_col(df, ["instructor", "primary instructor", "instructor name"])
    if instr_col:
        df[instr_col] = (
            df[instr_col]
            .astype(str)
            .str.strip()
            .str.replace(r"\s*,\s*", ",", regex=True)
        )

        splits = df[instr_col].apply(_split_instructor)
        first = splits.apply(lambda t: t[0])
        middle = splits.apply(lambda t: t[1])
        last = splits.apply(lambda t: t[2])
        base_idx = list(df.columns).index(instr_col) + 1
        df.insert(base_idx, "Instructor First", first)
        df.insert(base_idx + 1, "Instructor Middle", middle)
        df.insert(base_idx + 2, "Instructor Last", last)

    # 4. Handling of empty cels where numbers are expected (replace with 0)
    sess_col = _find_col(df, ["session code"])
    grade_cols: List[str] = []
    if sess_col:
        start_idx = list(df.columns).index(sess_col) + 1
        grade_cols = list(df.columns[start_idx:])
    else:
        # fallback: if no 'session code', try columns after 'session'
        sess2 = _find_col(df, ["session"])
        if sess2:
            start_idx = list(df.columns).index(sess2) + 1
            grade_cols = list(df.columns[start_idx:])
        else:
            # if still not found, do nothing numeric-specific
            pass

    invalid_rows_idx = set()
    if grade_cols:
        # 5. Finding any rows that are still invalid after all of that (just prints them for now)
        for col in grade_cols:
            col_series = df[col].astype(str)

            def _is_invalid_token(x: str) -> bool:
                if _is_empty_like(x):
                    return False
                # allow digits with commas or decimals
                try:
                    float(str(x).replace(",", ""))
                    return False
                except Exception:
                    return True

            invalid_mask = col_series.apply(_is_invalid_token)
            invalid_rows_idx.update(df.index[invalid_mask].tolist())

        if invalid_rows_idx:
            print("rows with non-numeric values in grade/code columns:", file=sys.stdout)
            preview_cols = ([strm_col] if strm_col else []) + ([instr_col] if instr_col else []) + grade_cols[:10]
            to_show = df.loc[sorted(invalid_rows_idx), [c for c in preview_cols if c is not None and c in df.columns]]
            with pd.option_context("display.max_columns", 20, "display.width", 140):
                print(to_show.to_string(index=False), file=sys.stdout)

        # replace empties with 0 and coerce to integers
        for col in grade_cols:
            s = df[col].apply(lambda x: None if _is_empty_like(x) else x)
            s = s.astype(str).str.replace(",", "", regex=False)
            numeric = pd.to_numeric(s, errors="coerce").fillna(0)
            # cast to Int64 to preserve integers and null-safety
            df[col] = numeric.astype("Int64")
        
        # 6. compute GPA
        letter_grade_cols = [c for c in grade_cols if c in gpa_scale]

        if letter_grade_cols:
            grade_counts = df[letter_grade_cols].astype("float64")

            # (exclude W, I, NR, etc)
            total_counts = grade_counts.sum(axis=1)
            total_points = pd.Series(0.0, index=df.index)
            for col in letter_grade_cols:
                total_points += grade_counts[col] * gpa_scale[col]

            total_counts_safe = total_counts.replace({0: np.nan})
            gpa = (total_points / total_counts_safe).round(3)

            if "Class Size" in df.columns:
                insert_at = df.columns.get_loc("Class Size")
                df.insert(insert_at, "GPA", gpa)
            else:
                df["GPA"] = gpa

    df.to_csv(csv_path, index=False)

    removed = original_len - len(df)
    print(f"  ✅ Cleaned '{csv_path}'. Dropped {removed} rows, wrote {len(df)}.", file=sys.stdout)
