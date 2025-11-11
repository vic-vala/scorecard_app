import json
import os
import sys
from typing import Any, Mapping

CONFIG_PATH = "./configuration/config.json"

def load_config(path=CONFIG_PATH):
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

def get_pdf_json(parsed_pdf_dir, s):
    json_filename = None

    json_filename = f"{s['department']}_{s['cata']}_{s['professor1']}_{s['sem']}_{s['year']}_{s['course_num']}.json"
    
    report_path = os.path.join(parsed_pdf_dir, json_filename)

    # 3. Attempt to load the file
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            pdf_json = json.load(f)
            print(f"Successfully loaded report: {report_path}")
            return pdf_json
    except FileNotFoundError:
        print(f"Error: json file not found at: {report_path}.\nTry changing 'professor1' in the config file.", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode json from {report_path}. Details: {e}", file=sys.stderr)
        return None


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def _slugify_token(token: str) -> str:
    cleaned = []
    for ch in token:
        if ch.isalnum():
            cleaned.append(ch)
        elif ch in (" ", "-", "_"):
            cleaned.append("_")
    slug = "".join(cleaned).strip("_")
    return slug


def _extract_instructor_last(row: Mapping[str, Any]) -> str:
    last = _stringify(row.get("Instructor Last"))
    if last:
        return last
    instructor = _stringify(row.get("Instructor"))
    if not instructor:
        return ""
    if "," in instructor:
        return instructor.split(",", 1)[0]
    tokens = instructor.split()
    return tokens[-1] if tokens else ""


def build_course_slug(row: Mapping[str, Any]) -> str:
    """
    Build the canonical identifier used for JSON, image, and PDF filenames.
    """
    subject = _slugify_token(_stringify(row.get("Subject")).upper())
    catalog = _slugify_token(_stringify(row.get("Catalog Nbr")))
    instructor_last = _slugify_token(_extract_instructor_last(row).capitalize())
    term = _slugify_token(_stringify(row.get("Term")).capitalize())
    year = _slugify_token(_stringify(row.get("Year")))
    class_nbr = (
        _stringify(row.get("Class Nbr"))
        or _stringify(row.get("Course Nbr"))
        or _stringify(row.get("Section"))
    )
    class_nbr = _slugify_token(class_nbr)
    parts = [p for p in (subject, catalog, instructor_last, term, year, class_nbr) if p]
    return "_".join(parts) or "scorecard"


def build_course_json_filename(row: Mapping[str, Any]) -> str:
    """
    Returns the expected JSON filename for a course selection row.
    """
    return f"{build_course_slug(row)}.json"


def resolve_course_json_path(row: Mapping[str, Any], parsed_pdf_dir: str) -> str:
    """
    Resolves and validates the JSON path for a selected course row.
    """
    filename = build_course_json_filename(row)
    path = os.path.join(parsed_pdf_dir, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Could not locate JSON for course selection: {path}")
    return path
