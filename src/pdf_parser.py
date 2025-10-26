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
        else:
            if q_num not in range(19, 23):
                print(f"Skipping Q{q_num}: No average mapping defined for this question number.")
    return pdf_json


def extract_comments(pdf_text, pdf_path, expected_n=None):
    comments = _collect_blocks_between(pdf_path, r"^25\.\s*Comments", None)
    if isinstance(expected_n, int) and expected_n > 0 and len(comments) > expected_n:
        comments = comments[:expected_n-1] + [" ".join(comments[expected_n-1:]).strip()]
    return comments


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
        # Q19-Q22
        pdf_json = extract_general_info(pdf_text, pdf_json)
        # Free responses
        try:
            expected_n = int(pdf_json["eval_info"].get("response_count") or 0)
        except Exception:
            expected_n = None
        likes, dislikes = extract_free_response(pdf_text, raw_pdf_path, expected_n)
        pdf_json["free_response"]["liked"] = likes
        pdf_json["free_response"]["disliked"] = dislikes
        pdf_json["free_response"]["comments"] = extract_comments(pdf_text, raw_pdf_path, expected_n)


    except Exception as e:
        print(f"An error occured while processing {raw_pdf_path}: {e}")
        return None
    
    return pdf_json

def save_json(pdf_json, fi,  parsed_base_dir):
    course_json_filename = f"{fi.department}_{fi.course}_{fi.professor}_{fi.term}_{fi.year}.json"
    with open(os.path.join(parsed_base_dir, course_json_filename), 'w') as file:
        json.dump(pdf_json, file, indent=4)
    print(f"  ✅ Saved json data to {os.path.join(parsed_base_dir, course_json_filename)}")

def _expected_json_paths(fi, parsed_base_dir):
    course_output_dir = os.path.join(parsed_base_dir, "courses_output", f"{fi.department}_{fi.course}")
    professor_output_dir = os.path.join(parsed_base_dir, "professors_output", f"{fi.professor}")
    course_json_path = os.path.join(course_output_dir, f"{fi.term}_{fi.year}.json")
    professor_json_path = os.path.join(professor_output_dir, f"{fi.department}_{fi.course}_{fi.term}_{fi.year}.json")
    return course_json_path, professor_json_path

def run_pdf_parser(pdf_source, parsed_base_dir, overwrite_json=False):
    try:
        if not os.path.exists(pdf_source):
            os.makedirs(pdf_source)
            print(f"Directory created. Please add your PDF files to '{pdf_source}' folder.")
        else:
            for file in os.listdir(pdf_source):
                if file.endswith(".pdf"):
                    extracted = extract_filename(file)
                    if not extracted:
                        print(f"  ⛔ Skipping {file}. Invalid filename format")
                        continue
                    dpt, crs, prof, yr, trm = extracted
                    fi = filename_info(dpt, crs, prof, yr, trm)

                    pdf_path = os.path.join(pdf_source, file)
                    course_json_path, professor_json_path = _expected_json_paths(fi, parsed_base_dir)

                    # Skip if JSON already exists and overwrite_json is False
                    if not overwrite_json and os.path.exists(course_json_path) and os.path.exists(professor_json_path):
                        print(f"  ⏭️ Skipping {file}: JSON already exists")
                        continue

                    print(f"  ⏳ Processing {pdf_path}")
                    print(f"  Department: {fi.department:<10} Course: {fi.course:<10} Professor: {fi.professor:<15} Year: {fi.year:<10} Term: {fi.term:<10}")
                    pdf_json = extract_pdf(pdf_path, fi)
                    if pdf_json:
                        save_json(pdf_json, fi, parsed_base_dir)
                    else:
                        print(f"  ⛔ Could not extract data from {file}")
                else:
                    print(f"  ⛔ Skipping {file}. Invalid filename format")
    except Exception as e:
        print(f"An error has occured: {e}")

def _clean_text(s: str) -> str:
    return re.sub(r"[ \t]+", " ", s.strip())

def _parse_table_block(block_text: str, rows_regex):
    results = {}
    for label, key in rows_regex:
        lab = re.escape(label)
        r = re.compile(rf"(?mi)^\s*{lab}\s+(\d+)\s+(\d+\.\d+%)\s*$")
        m = r.search(block_text)
        if m:
            results[key] = [m.group(1), m.group(2)]
        else:
            results[key] = [None, None]
    return results

def extract_general_info(pdf_text, pdf_json):
    q19 = re.search(r"19\.\s+Is this a required course.*?\n([\s\S]*?)\n\s*20\.", pdf_text, re.IGNORECASE)
    if q19:
        rows = [("Yes", "yes"), ("No", "no")]
        pdf_json["general_info"]["req_course_avg"] = _parse_table_block(q19.group(1), rows)
    q20 = re.search(r"20\.\s+What are the average hours/week.*?\n([\s\S]*?)\n\s*21\.", pdf_text, re.IGNORECASE)
    if q20:
        rows = [("16", "16hr"), ("8", "8hr"), ("4", "4hr"), ("2", "2hr"), ("1", "1hr")]
        pdf_json["general_info"]["hrs_per_wk_avg"] = _parse_table_block(q20.group(1), rows)
    q21 = re.search(r"21\.\s+What is your class standing\?\s*\n([\s\S]*?)\n\s*22\.", pdf_text, re.IGNORECASE)
    if q21:
        rows = [("Freshman", "freshman"), ("Sophomore", "sophomore"), ("Junior", "junior"), ("Senior", "senior"), ("Graduate Student", "grad")]
        pdf_json["general_info"]["class_standing_avg"] = _parse_table_block(q21.group(1), rows)
    q22 = re.search(r"22\.\s+What % of the class meetings have you attended\?\s*\n([\s\S]*?)\n\s*23\.", pdf_text, re.IGNORECASE)
    if q22:
        rows = [("90 to 100", "90_to_100"), ("70 to 89", "70_to_89"), ("50 to 69", "50_to_69"), ("30 to 49", "30_to_49"), ("10 to 29", "10_to_29")]
        pdf_json["general_info"]["attended_avg"] = _parse_table_block(q22.group(1), rows)
    return pdf_json

def extract_free_response(pdf_text, pdf_path, expected_n=None):
    likes = _collect_blocks_between(
        pdf_path,
        r"^23\.\s*What did you like most about this course\?",
        r"^\s*24\."
    )
    dislikes = _collect_blocks_between(
        pdf_path,
        r"^24\.\s*What did you like least about this course\?",
        r"^\s*25\."
    )

    if isinstance(expected_n, int) and expected_n > 0:
        if len(likes) > expected_n:
            likes = likes[:expected_n-1] + [" ".join(likes[expected_n-1:]).strip()]
        if len(dislikes) > expected_n:
            dislikes = dislikes[:expected_n-1] + [" ".join(dislikes[expected_n-1:]).strip()]
    return likes, dislikes

def _collect_blocks_between(pdf_path, start_pat: str, end_pat: str | None):
    start_re = re.compile(start_pat, re.M)
    end_re = re.compile(end_pat, re.M) if end_pat else None

    items: list[str] = []
    started = False
    with fitz.open(pdf_path) as doc:
        for page in doc:
            for x0, y0, x1, y1, text, *rest in page.get_text("blocks"):
                if not started:
                    if start_re.search(text):
                        started = True
                    continue
                if end_re and end_re.search(text):
                    return [_clean_text(t.replace("\n", " ")) for t in items if t.strip()]
                if text.strip():
                    items.append(text)
    return [_clean_text(t.replace("\n", " ")) for t in items if t.strip()]
