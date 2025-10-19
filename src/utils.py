import json
import os
import sys

CONFIG_PATH = "config.json"

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

# TODO: Handle code map conversion
def get_pdf_json(parsed_pdf_dir, type, department, cata_num, sem, year, prof_name=""):
    base_dir = None
    sub_dir = None
    json_filename = None

    if type.lower() == "course":
        base_dir = "courses_output"
        sub_dir = f"{department}_{cata_num}"
        json_filename = f"{sem}_{year}.json"
    elif type.lower() == "professor":
        base_dir = "professors_output"
        sub_dir = f"{prof_name}"
        json_filename = f"{department}_{cata_num}_{sem}_{year}.json"
    else:
        print(f"Error: Invalid type '{type}'. Must be 'course' or 'professor'.", file=sys.stderr)
        return None
    
    report_path = os.path.join(
        parsed_pdf_dir,
        base_dir,
        sub_dir,
        json_filename
    )

    # 3. Attempt to load the file
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            pdf_json = json.load(f)
            print(f"Successfully loaded report: {report_path}")
            return pdf_json
    except FileNotFoundError:
        print(f"Error: json file not found at: {report_path}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode json from {report_path}. Details: {e}", file=sys.stderr)
        return None
