import json
import os
import sys

CONFIG_PATH = "./configuration/config.json"

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
