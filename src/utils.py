import json
import os
import sys
import re
from typing import Any, Dict, Mapping, Optional, List, Tuple

CONFIG_PATH = "./configuration/config.json"

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

def load_config(path=CONFIG_PATH):
    """
    Loads the config file used to drive the application

    Args:
        path (`str`): The path to the config file

    Returns: Deserialized json as Python object (`Dict`)
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found at: {path}")
    with open(path, 'r', encoding="utf-8") as f:
       return  json.load(f)

def verify_directories(paths):
    print("Initializing file structure")
    # Check input directories
    input_dirs = [paths['pdf_source'], os.path.dirname(paths['excel_source']), paths['llm_prompt_dir']]
    for input_dir in input_dirs:
        if not os.path.exists(input_dir):
            print(f"MISSING INPUT DIRECTORY: {input_dir}")
            os.makedirs(input_dir, exist_ok=True)
            print(f"Created missing input directory: {input_dir}. Please populate it before running the pipeline.")

    # Create dutput directories
    output_dirs = [
        paths['parsed_pdf_dir'],
        paths['temp_dir'],
        paths['scorecard_dir']
    ]
    
    for output_dir in output_dirs:
        # Using exist_ok=True to ensure it creates the directory structure without error
        os.makedirs(output_dir, exist_ok=True)
        print(f"Output directory is set: {output_dir}")

    print("Directory initialization complete\n")

def load_pdf_json(pdf_json_path):
    """
    Loads json from a given path

    Args:
        pdf_json_path (`str`):
    
    Returns:
        Deserialized json as Python object (`Dict`)
    """
    try:
        with open(pdf_json_path, 'r', encoding='utf-8') as f:
            pdf_json = json.load(f)
            return pdf_json
    except FileNotFoundError:
        print(f"Error: json file not found at: {pdf_json_path}.", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode json from {pdf_json_path}. Details: {e}", file=sys.stderr)
        return None

def _slug(value: Any, fallback: str = "NA") -> str:
    """
    Convery an arbitrary value to a filename safe string
    - Replaces space with underscores
    - Convert to a string
    - Strip leading/trailing whitespace
    - Remove all non letter/digit/underscores
    """
    if value is None:
        return fallback
    s = str(value).strip()
    if not s:
        return fallback
    s = s.replace(" ", "_")
    s = re.sub(r"[^A-Za-z0-9_]+", "", s)
    return s or fallback

def course_to_stem(course):
    """
    From a course row build the stem used for filenames
        CSE_470_Maciejewski_Fall_2011_71428
    """
    subject = _slug(course.get("Subject"))
    catalog = _slug(course.get("Catalog Nbr"))
    instructor_last = _slug(
        course.get("Instructor Last")
        or course.get("Instructor_Last")
        or course.get("InstructorLast")
    )
    term = _slug(course.get("Term"))
    year = _slug(course.get("Year"))

    class_nbr = _slug(
        course.get("Class Nbr")
        or course.get("Course Nbr")
        or course.get("Section")
        or course.get("course_number")
    )

    return f"{subject}_{catalog}_{instructor_last}_{term}_{year}_{class_nbr}"

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

def course_to_json_path(course, json_dir=None, config=None):
    """
    From a course row, return the full JSON path where that course's JSON should be

    If `json_dir` is not provided, it gets it from
        config['paths']['parsed_pdf_dir'] (or config['paths']['json_dir'])

    Example:
        {config.paths.parsed_pdf_dir}/CSE_470_Maciejewski_Fall_2011_71428.json
    """
    if json_dir is None:
        if config is None:
            config = load_config()

        paths = config.get("paths", {}) or config.get("PATHS", {})
        json_dir = paths.get("parsed_pdf_dir") or paths.get("json_dir")
        if not json_dir:
            raise KeyError("parsed_pdf_dir/json_dir not found in config['paths'].")

    stem = course_to_stem(course)
    return os.path.join(json_dir, f"{stem}.json")

def _get_numeric(course: Mapping[str, Any], key: str) -> float:
    """
    Go from a course (row in the CSV) and a key to a float safely
    """
    raw = course.get(key)
    if raw is None or raw == "":
        return 0.0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0

def _is_true(val: Any) -> bool:
    """
    True if str(val).lower() == "true"

    Use this for .json config stuff
    """
    return str(val).lower() == "true"

def _is_hundred(val: Any) -> bool:
    """
    True if str(val).lower() == "hundred"
    
    This is for reading match_catalog_number in the config.json, since it can be "true", "false", or "hundred"
    """
    return str(val).lower() == "hundred"