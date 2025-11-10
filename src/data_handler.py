import os
import json
import math
import re
from typing import Any, Dict, Mapping, Optional
import pandas as pd


def _parse_filename(filename: str):
    """
    Parse filenames of the form:
        Subject_CatalogNbr_InstructorLast_Term_Year_ClassNbr.json

    Returns a dict with keys:
        subject, catalog_nbr, instructor_last, term,
        year, class_nbr
    """
    base = os.path.basename(filename)
    if base.lower().endswith(".json"):
        base = base[:-5]

    parts = base.split("_")

    if len(parts) != 6:
        raise ValueError(
            f"Unexpected JSON filename format: {filename}. "
            "Expected 6 underscore-separated parts."
        )

    subject, catalog_nbr, instructor_last, term, year, class_nbr = parts

    return {
        "subject": subject,
        "catalog_nbr": catalog_nbr,
        "instructor_last": instructor_last,
        "term": term,
        "year": year,
        "class_nbr": class_nbr,
    }

def viable_scorecards(json_dir: str, csv_path: str) -> pd.DataFrame:
    """
    This function looks through the name of each of the json files one at a time.

    For each of these json files, if the info in the file name matches one of the 
    rows in the csv, that row of the csv is added to the dataframe that is eventually returned.

    The eventually returned dataframe is the overlap in courses found between the CSV and json
    directory folder. 
    """
    # Read CSV as strings for reliable matching
    df = pd.read_csv(csv_path, dtype=str)

    # normalize columns
    for col in ["Subject", "Catalog Nbr", "Instructor Last", "Term", "Year", "Class Nbr"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    matched_rows = []

    # scan directory
    for fname in os.listdir(json_dir):
        if not fname.lower().endswith(".json"):
            continue

        full_path = os.path.join(json_dir, fname)

        try:
            info = _parse_filename(fname)
        except ValueError as e:
            print(f"Warning: {e}")
            continue

        subject = info["subject"]
        catalog_nbr = info["catalog_nbr"]
        instructor_last = info["instructor_last"]
        term = info["term"]
        year = info["year"]
        class_nbr = info["class_nbr"]

        mask = (
            (df["Subject"] == subject) &
            (df["Catalog Nbr"] == catalog_nbr) &
            (df["Instructor Last"] == instructor_last) &
            (df["Year"] == year) &
            (df["Class Nbr"] == class_nbr)
        )

        if term is not None and "Term" in df.columns:
            mask = mask & (df["Term"].str.casefold() == term.casefold())

        rows = df[mask]

        if rows.empty:
            print(f"  ⛔ No row found in CSV for JSON file '{fname}'")
        else:
            print(f"  ✅ Matching JSON and CSV found for '{fname}'")
            matched_rows.append(rows)
    
    if matched_rows:
        result = pd.concat(matched_rows, ignore_index=True)
    else:
        result = df.iloc[0:0].copy()

    return result

def get_instructors(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, dtype=str)

    cols = ["Instructor", "Instructor First", "Instructor Middle", "Instructor Last"]
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise KeyError(f"Missing expected columns in CSV: {', '.join(missing)}")

    for c in cols:
        df[c] = df[c].fillna("").astype(str).str.strip()

    result = (
        df.groupby(cols, dropna=False)
          .size()
          .reset_index(name="Number of Courses")
    )

    return result

gpa_scale = {
    "A+": 4.33, "A": 4.0, "A-": 3.67,
    "B+": 3.33, "B": 3.0, "B-": 2.67,
    "C+": 2.33, "C": 2.0, "D": 1.0, "E": 0.0,
}

GRADE_COLS = [
    "A+", "A", "A-", "B+", "B", "B-",
    "C+", "C", "D", "E",
    "EN", "EU", "I", "NR", "NR.1",
    "W", "X", "XE", "Y", "Z",
]

def _is_true(val: Any) -> bool:
    return str(val).lower() == "true"

def _is_hundred(val: Any) -> bool:
    return str(val).lower() == "hundred"

def _parse_catalog_int(value: Any) -> Optional[int]:
    """extract leading integer from a catalog string, like '470' or '4DE'."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    s = str(value).strip()
    m = re.match(r"\d+", s)
    if not m:
        return None
    try:
        return int(m.group(0))
    except ValueError:
        return None

def _same_hundred_level(cat1: Any, cat2: Any) -> bool:
    """return True if two catalog numbers are in the same x00 x99 band"""
    n1 = _parse_catalog_int(cat1)
    n2 = _parse_catalog_int(cat2)
    if n1 is None or n2 is None:
        return False
    return (n1 // 100) == (n2 // 100)

def compute_course_gpa(row_like: Mapping[str, Any], scale: Dict[str, float]) -> Optional[float]:
    """
    compute GPA for a single course row from CSV data
    uses gpa_scale and only A+ through E, ignores EN EU W I etc.
    """
    total_points = 0.0
    total_count = 0

    for grade, weight in scale.items():
        if grade in row_like:
            count = row_like[grade]
            if pd.isna(count):
                continue
            cnt = int(count)
            total_points += cnt * weight
            total_count += cnt

    if total_count == 0:
        return None
    return total_points / total_count


def describe_aggregate(
    comparison: Dict[str, Any],
    row: Mapping[str, Any],
) -> str:
    """
    Goes from a comparison config to a readable name for the baseline/aggregate

    Examples:
      "All Available CSE 400-499 Fall 2011 Courses"
      "All Available CSE 470 Fall 2011 Courses"
      "All Available Courses"
    """
    subject = str(row.get("Subject", "")).strip()
    catalog = str(row.get("Catalog Nbr", "")).strip()
    term = str(row.get("Term", "")).strip()

    raw_year = row.get("Year", "")
    year_str = ""
    if raw_year is not None and raw_year != "":
        try:
            year_str = str(int(raw_year))
        except Exception:
            year_str = str(raw_year).strip()

    match_term = _is_true(comparison.get("match_term"))
    match_year = _is_true(comparison.get("match_year"))
    match_subject = _is_true(comparison.get("match_subject"))
    match_catalog = str(comparison.get("match_catalog_number", "false")).lower()

    parts = []

    # subject + catalog logic
    subject_catalog = ""
    if match_subject and subject:
        if match_catalog == "true" and catalog:
            subject_catalog = f"{subject} {catalog}"
        elif match_catalog == "hundred" and catalog:
            n = _parse_catalog_int(catalog)
            if n is not None:
                start = (n // 100) * 100
                end = start + 99
                subject_catalog = f"{subject} {start}-{end}"
            else:
                subject_catalog = subject
        else:
            subject_catalog = subject
    elif (not match_subject) and catalog and match_catalog in ("true", "hundred"):
        if match_catalog == "true":
            subject_catalog = f"{catalog}"
        else:
            n = _parse_catalog_int(catalog)
            if n is not None:
                start = (n // 100) * 100
                end = start + 99
                subject_catalog = f"{start}-{end}"

    if subject_catalog:
        parts.append(subject_catalog)

    if match_term and term:
        parts.append(term)

    if match_year and year_str:
        parts.append(year_str)

    if parts:
        main = " ".join(parts)
        return f"All Available {main} Courses"
    else:
        return "All Available Courses"


def aggregate_for_row(
    comparison: Dict[str, Any],
    row: Mapping[str, Any],
    json_dir: str,
    csv_path: str,
) -> Dict[str, Any]:
    """
    (This documentation (and some comments) are LLM generated, 
    reach out to Joey if any of this doesn't make sense/needs clarification)

    Aggregate metrics over all courses that match `row` according to `comparison`.

    comparison keys:
      - 'match_term'           in {'true', 'false'}
      - 'match_year'           in {'true', 'false'}
      - 'match_subject'        in {'true', 'false'}
      - 'match_catalog_number' in {'true', 'false', 'hundred'}

    row must have at least:
      'Subject', 'Catalog Nbr', 'Term', 'Year'

    Matching rules:
      * term subject year filtered only if the corresponding match_* is 'true'
      * match_catalog_number
          'true'   exact Catalog Nbr
          'hundred' same x00 x99 band, for example 400 499
          'false'  ignore catalog number

    Returns a dict with:
      gpa                mean GPA over matched CSV rows
      median_grade       median letter grade over all students in matched CSV rows
      q1_grade           first quartile grade
      q3_grade           third quartile grade
      grade_percentages  dict grade -> percent of students
      course_size_avg    average JSON course size (total_students)
      num_responses      total JSON responses across matches
      total_students     total JSON students across matches
      avg_part1          mean eval_info['avg1'] over JSON matches
      avg_part2          mean eval_info['avg2'] over JSON matches
      num_courses_csv    count of matched CSV rows
      num_courses_json   count of matched JSON eval files
    """
    # Target values from the given row
    subject_val = row["Subject"]
    term_val = row["Term"]
    year_val = int(row["Year"])
    catalog_val = row["Catalog Nbr"]

    match_term = _is_true(comparison.get("match_term"))
    match_year = _is_true(comparison.get("match_year"))
    match_subject = _is_true(comparison.get("match_subject"))
    match_catalog = comparison.get("match_catalog_number", "false")

    aggregate_name = describe_aggregate(comparison, row)

    # CSV section
    df = pd.read_csv(csv_path)

    mask = pd.Series(True, index=df.index)
    if match_subject:
        mask &= df["Subject"] == subject_val
    if match_term:
        mask &= df["Term"] == term_val
    if match_year:
        mask &= df["Year"].astype(int) == year_val

    if str(match_catalog).lower() == "true":
        mask &= df["Catalog Nbr"] == catalog_val
    elif _is_hundred(match_catalog):
        target_cat = catalog_val
        mask &= df["Catalog Nbr"].apply(
            lambda x: _same_hundred_level(x, target_cat)
        )

    matched_df = df[mask].copy()
    num_courses_csv = len(matched_df)

    # GPA across matched CSV rows
    gpas = []
    for _, r in matched_df.iterrows():
        g = compute_course_gpa(r, gpa_scale)
        if g is not None:
            gpas.append(g)
    gpa_value: Optional[float] = (
        sum(gpas) / len(gpas) if gpas else None
    )

    # Grade distribution and quartiles from CSV
    grade_percentages = {g: 0.0 for g in GRADE_COLS}
    q1_grade = median_grade = q3_grade = None

    if num_courses_csv > 0:
        grade_counts = matched_df[GRADE_COLS].sum()
        total_grades = int(grade_counts.sum())

        if total_grades > 0:
            for g in GRADE_COLS:
                grade_percentages[g] = (
                    float(grade_counts[g]) / total_grades
                )

            def percentile_grade(q: float) -> Optional[str]:
                # q in [0,1]
                threshold = q * total_grades
                cumulative = 0
                for grade in GRADE_COLS:  # ordered from A+ down to Z
                    cumulative += int(grade_counts[grade])
                    if cumulative >= threshold:
                        return grade
                return None
            
            # caveat: i dont know why q1 is 0.75 and why q3 is 0.25 and why it works
            q1_grade = percentile_grade(0.75) 
            median_grade = percentile_grade(0.50)
            q3_grade = percentile_grade(0.25)

    # JSON part
    json_course_sizes = []
    json_responses = []
    json_avg1 = []
    json_avg2 = []

    if os.path.isdir(json_dir):
        for fname in os.listdir(json_dir):
            if not fname.lower().endswith(".json"):
                continue
            fpath = os.path.join(json_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue

            info = data.get("eval_info", {})
            dept = info.get("department")
            course = info.get("course")
            term_j = info.get("term")
            year_j_raw = info.get("year")

            try:
                year_j = int(year_j_raw)
            except Exception:
                continue

            # Apply the same matching logic
            if match_subject and dept != subject_val:
                continue
            if match_term and term_j != term_val:
                continue
            if match_year and year_j != year_val:
                continue

            if str(match_catalog).lower() == "true":
                if course != str(catalog_val):
                    continue
            elif _is_hundred(match_catalog):
                if not _same_hundred_level(course, catalog_val):
                    continue

            # Collect JSON metrics
            try:
                total_students = int(info.get("total_students"))
            except Exception:
                total_students = None
            try:
                response_count = int(info.get("response_count"))
            except Exception:
                response_count = None
            try:
                avg1 = float(info.get("avg1"))
            except Exception:
                avg1 = None
            try:
                avg2 = float(info.get("avg2"))
            except Exception:
                avg2 = None

            if total_students is not None:
                json_course_sizes.append(total_students)
            if response_count is not None:
                json_responses.append(response_count)
            if avg1 is not None:
                json_avg1.append(avg1)
            if avg2 is not None:
                json_avg2.append(avg2)

    num_courses_json = len(json_course_sizes)

    course_size_avg = (
        float(sum(json_course_sizes)) / len(json_course_sizes)
        if json_course_sizes else None
    )
    num_responses = int(sum(json_responses)) if json_responses else None
    total_students = int(sum(json_course_sizes)) if json_course_sizes else None
    avg_part1 = (
        float(sum(json_avg1)) / len(json_avg1) if json_avg1 else None
    )
    avg_part2 = (
        float(sum(json_avg2)) / len(json_avg2) if json_avg2 else None
    )

    return {
        "aggregate_name": aggregate_name,
        "gpa": gpa_value,
        "median_grade": median_grade,
        "q1_grade": q1_grade,
        "q3_grade": q3_grade,
        "grade_percentages": grade_percentages,
        "course_size_avg": course_size_avg,
        "num_responses": num_responses,
        "total_students": total_students,
        "avg_part1": avg_part1,
        "avg_part2": avg_part2,
        "num_courses_csv": num_courses_csv,
        "num_courses_json": num_courses_json,
    }

def get_unique_courses(csv_path):
    """
    return a dataframe of unique courses in the CSV

    The df has four columns:
        'Subject'
        'Catalog Nbr'
        'Unique Instructors'
        'Unique Class Sessions'
    """
    if isinstance(csv_path, (list, tuple)):
        if not csv_path:
            raise ValueError("csv_path list/tuple is empty.")
        csv_path_use = csv_path[0]
    else:
        csv_path_use = csv_path

    df = pd.read_csv(csv_path_use, dtype=str)

    base_cols = ["Subject", "Catalog Nbr"]
    extra_cols = ["Instructor", "Class Nbr"]

    missing_base = [c for c in base_cols if c not in df.columns]
    if missing_base:
        raise KeyError(f"Missing expected columns in CSV: {', '.join(missing_base)}")

    missing_extra = [c for c in extra_cols if c not in df.columns]
    if missing_extra:
        raise KeyError(f"Missing expected columns in CSV: {', '.join(missing_extra)}")

    use_cols = base_cols + extra_cols
    tmp = df[use_cols].copy()

    # normalize
    for c in use_cols:
        tmp[c] = tmp[c].fillna("").astype(str).str.strip()

    # group by course and count unique instructors and class numbers
    result = (
        tmp.groupby(base_cols, as_index=False)
           .agg(
               **{
                   "Unique Instructors": ("Instructor", lambda x: x[x != ""].nunique()),
                   "Unique Class Sessions": ("Class Nbr", lambda x: x[x != ""].nunique()),
               }
           )
           .sort_values(base_cols)
           .reset_index(drop=True)
    )

    return result
