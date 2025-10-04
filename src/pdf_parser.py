import fitz # PyMuPDF library
import json
import os
import re
from src.schema.parsed_pdf_schema import *

class filename_info:
    def __init__(self, department, course, professor, year, term):
        self.department = department
        self.course = course
        self.professor = professor
        self.year = year
        self.term = term

def extract_filename(filename):
    filename_format = re.search(r"(\w{3})\s+(\d{3})\s+(\w+)\s+Instructor\s+Evaluation\s+(\d{4})\s+([a-zA-Z]{4,7})\w*.pdf", filename)
    if filename_format:
        department = filename_format.group(1).upper()
        course = filename_format.group(2).strip()
        professor = filename_format.group(3).capitalize()
        year = filename_format.group(4).strip()
        term = filename_format.group(5).capitalize()
        return department, course, professor, year, term

    
def parse_graph_avgs(pdf_text, pdf_json, key_map):
    # Regex pattern for matching Q1-18
    reg_pattern = r"(\d*)\.\s(?:(?!Avg)[\s\S])*?Avg (\d+.\d+)[\s\S]*?(?=\d+\.\s|\Z)"

    q_matches = re.finditer(reg_pattern, pdf_text, re.MULTILINE)
    for match in q_matches:
        q_num = int(match.group(1))
        if q_num in range(PART_1_LIMITS["start"], OVERALL_EVAL_LIMITS["end"]+1):
            avg = match.group(2).strip()
            if q_num in key_map:
                part_key, field_key = key_map[q_num]
                pdf_json[part_key][field_key] = avg
                print(f"Match found: Q{q_num} | Part '{part_key}' | Key '{field_key}' set to {avg}")
        else:
            if q_num not in range(19, 23):
                print(f"Skipping Q{q_num}: No average mapping defined for this question number.")
    return pdf_json

def extract_pdf(raw_pdf_path, fi):
    # Json schema from python dict
    pdf_json = initialize_pdf_json()
    key_map = get_key_map()

    pdf_json["eval_info"]["department"] = fi.department
    pdf_json["eval_info"]["course"] = fi.course
    pdf_json["eval_info"]["professor"] = fi.professor
    pdf_json["eval_info"]["year"] = fi.year
    pdf_json["eval_info"]["term"] = fi.term

    try:
        # Open the pdf at given path
        pdf = fitz.open(raw_pdf_path)
        pdf_text = ""

        # Gather all text from the pdf
        for page in pdf:
            pdf_text += page.get_text()
        pdf.close()

        response_rate_match = re.search(r"Response\s+(\d+)/(\d+) \((\d+.\d+\%)\)", pdf_text)
        if response_rate_match:
            response_count = response_rate_match.group(1).strip()
            total_students = response_rate_match.group(2).strip()
            response_rate = response_rate_match.group(3).strip()
            pdf_json['eval_info']['response_count'] = response_count
            pdf_json['eval_info']['total_students'] = total_students
            pdf_json['eval_info']['response_rate'] = response_rate
        # Extract average part 1
        avg_p1_match = re.search(r"Avg\sPart\s1\s+(\d.\d+)", pdf_text)
        if avg_p1_match:
            avg = avg_p1_match.group(1).strip()
            pdf_json["eval_info"]["avg1"] = avg

        # Extract average part 2
        avg_p2_match = re.search(r"Avg\sPart\s2\s+(\d.\d+)", pdf_text)
        if avg_p2_match:
            avg = avg_p2_match.group(1).strip()
            pdf_json["eval_info"]["avg2"] = avg

        # Extract Q1-Q18
        pdf_json = parse_graph_avgs(pdf_text, pdf_json, key_map)
        # TODO: Extract graph data without averages (Q19-22)
        # TODO: Extract Comments programatically with identifies (array might be enough since index separates comments naturally)

    except Exception as e:
        print(f"An error occured while processing {raw_pdf_path}: {e}")
        return None
    
    return pdf_json

def save_json(pdf_json, fi,  parsed_base_dir):

    # Create subdirectories for courses and professors in the output directory
    course_output_dir = os.path.join(parsed_base_dir, "courses_output", f"{fi.department}_{fi.course}")
    professor_output_dir = os.path.join(parsed_base_dir, "professors_output", f"{fi.professor}")
    os.makedirs(course_output_dir, exist_ok=True)
    os.makedirs(professor_output_dir, exist_ok=True)

    # Generate json file name
    course_json_filename = f"{fi.term}_{fi.year}.json"
    professor_json_filename = f"{fi.department}_{fi.course}_{fi.term}_{fi.year}.json"

    # Generate json path for respective report
    course_json_path = os.path.join(course_output_dir, course_json_filename)
    professor_json_path = os.path.join(professor_output_dir, professor_json_filename)
    
    # Save json to the respective path
    with open(course_json_path, 'w') as file:
        json.dump(pdf_json, file, indent=4)
    print(f"Saved json data to {course_json_path}.")
    with open(professor_json_path, 'w') as file:
        json.dump(pdf_json, file, indent=4)
    print(f"Saved json data to {professor_json_path}.")

def run_pdf_parser(pdf_source, parsed_base_dir):
    try:
        # Ensure that the directory holding the pdfs exists
        if not os.path.exists(pdf_source):
            os.makedirs(pdf_source)
            print(f"Directory created. Please add your PDF files to '{pdf_source}' folder.")
        # Iterate through the folder and process each pdf
        else:
            for file in os.listdir(pdf_source):
                if file.endswith(".pdf"):
                    dpt, crs, prof, yr, trm = extract_filename(file)
                    fi = filename_info(dpt, crs, prof, yr, trm)
                    if fi.department and fi.course and fi.professor and fi.year and fi.term:
                        pdf_path = os.path.join(pdf_source, file)
                        print(f"Processing {pdf_path}")
                        print(f"Department: {fi.department}\nCourse: {fi.course}\nProfessor: {fi.professor}\nYear: {fi.year}\nTerm: {fi.term}\n")
                        pdf_json = extract_pdf(pdf_path, fi)
                        if pdf_json:
                            save_json(pdf_json, fi, parsed_base_dir)
                        else:
                            print(f"Could not extract data from {file}")         
                else: 
                    print(f"Skipping {file}. Invalid filename format")
    except Exception as e:
        print(f"An error has occured: {e}")

