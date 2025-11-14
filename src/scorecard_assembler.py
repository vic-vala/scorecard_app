import json
import os
import re
import sys
import pandas as pd
from typing import Any, Dict, Mapping, Optional, List, Tuple
from src.utils import course_to_json_path, course_to_stem, _is_true

from pylatex import(
    Command,
    Document,
    NoEscape,
    Package,
    Section,
)
from src import latex_sections
from src.data_handler import aggregate_for_row, get_courses_by_instructor
from src import compute_metrics

# Organizing all the data necessary for automating the latex, much cleaner containing
#   everything in one class.
class _ScorecardDoc:

    def __init__(
            self, 
            csv_row: Dict[str, Any], 
            pdf_json: str, 
            grade_hist: str, 
            output_filename: str, 
            agg_data: Dict[str, Any],
            config
            ):
        self.csv_row = csv_row
        self.pdf_json = pdf_json
        self.grade_hist = grade_hist
        self.output_filename = output_filename
        self.agg_data = agg_data
        self.config = config

        # Tex related fields
        self.doc = None
        self.show_hdr_overview = False
        self.show_hdr_eval = False
        self.show_hdr_title = True
        self.baseline_text = agg_data['aggregate_name']

        # Compute all metrics on initialization
        self.metrics = self._compute_all_metrics()

    def _compute_all_metrics(self) -> Dict[str, Any]:
        """
        Compute all grade and evaluation metrics when _ScorecardDoc is initialized

        Returns:
            `dict` with nested structure containing all computed metrics (deltas, pcts, counts, gpa, etc.)
        """
        return {
            'grades': {
                'A': compute_metrics.get_grade_metrics(self.csv_row, self.agg_data, 'A'),
                'B': compute_metrics.get_grade_metrics(self.csv_row, self.agg_data, 'B'),
                'C': compute_metrics.get_grade_metrics(self.csv_row, self.agg_data, 'C'),
                'D': compute_metrics.get_grade_metrics(self.csv_row, self.agg_data, 'D'),
                'E': compute_metrics.get_grade_metrics(self.csv_row, self.agg_data, 'E'),
            },
            'pass': compute_metrics.get_pass_metrics(self.csv_row, self.agg_data),
            'fail': compute_metrics.get_fail_metrics(self.csv_row, self.agg_data),
            'drop': compute_metrics.get_drop_metrics(self.csv_row, self.agg_data),
            'withdraw': compute_metrics.get_withdraw_metrics(self.csv_row, self.agg_data),
            'gpa': {
                'value': round(float(self.csv_row['GPA']), 2),
                'delta': compute_metrics.get_gpa_delta(self.csv_row, self.agg_data),
            },
            'median_grade': {
                'baseline': self.agg_data['median_grade'],
                'individual': compute_metrics.calculate_median_grade(self.csv_row) or "N/A"
            },
            'quartiles': compute_metrics.get_quartile_metrics(self.agg_data),
            'course_size': {
                'value': int(self.csv_row['Class Size']),
                'delta': compute_metrics.get_course_size_delta(self.csv_row, self.agg_data),
            },
            'response': {
                'count': self.pdf_json['eval_info']['response_count'],
                'rate': self.pdf_json['eval_info']['response_rate'],
                'delta': compute_metrics.get_response_rate_delta(self.pdf_json, self.agg_data),
            },
            'avg_part1': {
                'value': self.pdf_json['eval_info']['avg1'],
                'delta': compute_metrics.get_avg_part1_delta(self.pdf_json, self.agg_data),
            },
            'avg_part2': {
                'value': self.pdf_json['eval_info']['avg2'],
                'delta': compute_metrics.get_avg_part2_delta(self.pdf_json, self.agg_data),
            },
        }

    # Driver function, setting up the documentclass, packages, preamble
    def doc_setup(self):
        self.doc = Document(documentclass='article', document_options=['11pt'])
        self._add_packages()
        self._add_preamble()
        self.build_sections()
        return self.doc

    def _add_packages(self):
        # {package name}, [{opt1}, {opt2}, etc.]
        packages = [
            ('geometry', ['margin=0.5in']),
            ('lmodern', None),
            ('microtype', None),
            ('xcolor', None),
            ('graphicx', None),
            ('tabularx', None),
            ('booktabs', None),
            ('tcolorbox', ['most']),
            ('array', None),
            ('xstring', None),
        ]

        for package, options in packages:
            self.doc.packages.append(Package(package, options=options))

    # Color palette, commands, everything before \begin{document}
    def _add_preamble(self):

        # Custom columns
        self.doc.preamble.append(NoEscape(
            r'\newcolumntype{M}[1]{>{\centering\arraybackslash}m{#1}}'
        ))
        self.doc.preamble.append(NoEscape(
            r'\newcolumntype{T}[1]{>{\centering\arraybackslash}p{#1}}'
        ))

        # color palette
        self.doc.preamble.append(Command(
            'definecolor',
            arguments=['accent', 'HTML', '1F4E79']
        ))
        # These are set to black currently until we want to add colors to deltas back. 
        # This needs to be dynamic since + doesn't always mean "good", and such
        self.doc.preamble.append(NoEscape(r'\colorlet{pos}{black!60!black}')) 
        self.doc.preamble.append(NoEscape(r'\colorlet{neg}{black!70!black}'))
        self.doc.preamble.append(NoEscape(r'\colorlet{neu}{black!70!black}'))

        # Overview field commands
        self._add_overview_fields()
        self._add_evaluation_metrics_fields()
        self._add_summary_fields()
        self._add_grade_distr_fields()
        
        # Helper commands
        self._define_helper_commands()

        # Layout lengths
        self._define_layout_lengths()

        # Header toggles
        self._define_header_toggles()

        # TCB styling
        self._define_tcb_style()

        # Page style
        self.doc.preamble.append(Command('pagestyle', 'empty'))

    # Assigning values to the fields in the overview section
    def _add_overview_fields(self):

        course_name = f"{self.pdf_json['eval_info']['department']} {self.pdf_json['eval_info']['course']}"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\CourseName'), course_name]))
        course_year = f"{self.pdf_json['eval_info']['year']}"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\CourseYear'), course_year]))

        # Term pulled form json, session pulled from csv row
        course_session = str(self.csv_row['Session Code'])
        course_term = f"{self.pdf_json['eval_info']['term']} {course_session}"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\CourseTerm'), course_term]))

        # Course code (5-digit one) pulled from json
        course_code = f"{self.pdf_json['eval_info']['course_number']}"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\CourseCode'), course_code]))

        instructor = f"{self.pdf_json['eval_info']['professor']}"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\Instructor'), instructor]))

        # Baseline Text
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\BaselineText'), self.baseline_text]))

        # Pulled from csv row
        course_size = int(self.csv_row['Class Size'])
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\CourseSize'), str(course_size)]))

        # Calculate course size delta against aggregate average
        course_size_delta = compute_metrics.get_course_size_delta(self.csv_row, self.agg_data)
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\CourseSizeDelta'), str(course_size_delta)]))

        responses = f"{self.pdf_json['eval_info']['response_count']}"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\Responses'), str(responses)]))

        # May need to add '\\' to escape for the percent
        response_rate = f"{self.pdf_json['eval_info']['response_rate']}"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\ResponseRate'), response_rate]))

        # Calculate response rate delta (currently returns N/A until aggregate tracking is added)
        response_delta = compute_metrics.get_response_rate_delta(self.pdf_json, self.agg_data)
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\ResponseDelta'), response_delta]))

        avg_p1 = f"{self.pdf_json['eval_info']['avg1']}"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\AvgPone'), str(avg_p1)]))

        # Calculate avg1 delta against aggregate baseline
        avg_p1_delta = compute_metrics.get_avg_part1_delta(self.pdf_json, self.agg_data)
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\AvgPoneDelta'), avg_p1_delta]))

        avg_p2 = f"{self.pdf_json['eval_info']['avg2']}"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\AvgPtwo'), str(avg_p2)]))

        # Calculate avg2 delta against aggregate baseline
        avg_p2_delta = compute_metrics.get_avg_part2_delta(self.pdf_json, self.agg_data)
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\AvgPtwoDelta'), avg_p2_delta]))

        # Median grade from aggregate data (baseline)
        median_grade = self.agg_data['median_grade']
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\MedianGrade'), median_grade]))

        # Median grade for course row
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\MedianGradeDelta'), self.metrics['median_grade']['individual']]))

        # GPA and delta calculation using metrics dict
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GPA'), str(self.metrics['gpa']['value'])]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GPADelta'), self.metrics['gpa']['delta']]))

        # Pass metrics
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\PassNum'), str(self.metrics['pass']['count'])]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\PassPct'), self.metrics['pass']['pct']]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\PassDelta'), self.metrics['pass']['delta']]))

        # Fail metrics
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\FailNum'), str(self.metrics['fail']['count'])]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\FailPct'), self.metrics['fail']['pct']]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\FailDelta'), self.metrics['fail']['delta']]))

        # Drop metrics
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\DropNum'), str(self.metrics['drop']['count'])]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\DropPct'), self.metrics['drop']['pct']]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\DropDelta'), self.metrics['drop']['delta']]))

        # Withdraw metrics
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\WithdrawNum'), str(self.metrics['withdraw']['count'])]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\WithdrawPct'), self.metrics['withdraw']['pct']]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\WithdrawDelta'), self.metrics['withdraw']['delta']]))

    # Assigning values to the fields in the evaluation metrics section
    def _add_evaluation_metrics_fields(self):
        # TODO: have some function that dynamically chooses the outliers based on a 
        #   deviation threshold? Hardcoded choices for now, but dynamic values
        #   Could use a dict for the full metric descriptions
        outlier_avg = 4.5   # obsolete, will remove
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\OutlierAvg'), str(outlier_avg)]))   # obsolete

        outlier1_name = f"Textbook/supplementary material in support of the course."
        outlier1_val = self.pdf_json['part_1']['textbook_avg']
        outlier1_delta = -0.43

        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\OutOneName'), outlier1_name]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\OutOneScore'), str(outlier1_val)]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\OutOneDelta'), str(outlier1_delta)]))
        
        outlier2_name = f"Value of assigned homework in support of course topics."
        outlier2_val = self.pdf_json['part_1']['homework_value_avg']
        outlier2_delta = -0.24
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\OutTwoName'), outlier2_name]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\OutTwoScore'), str(outlier2_val)]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\OutTwoDelta'), str(outlier2_delta)]))
        
        outlier3_name = f"Value of laboratory assignments/projects in support of the course topics."
        outlier3_val = self.pdf_json['part_1']['lab_value_avg']
        outlier3_delta = 0.17
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\OutThreeName'), outlier3_name]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\OutThreeScore'), str(outlier3_val)]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\OutThreeDelta'), str(outlier3_delta)]))
    
    # Assigning values used in LLM comment summary section
    def _add_summary_fields(self):

        # TODO: Modify pdf_json schema to also have a count value for the comments maybe
        #   or organized txt file, json might be easier
        comment_count = 4
        self.doc.preamble.append(
            Command('newcommand', [NoEscape(r'\CommentCount'), str(comment_count)])
        )

        llm_summary = self.pdf_json['llm_summary']  
        self.doc.preamble.append(
            Command('newcommand', [NoEscape(r'\LLMSummary'), NoEscape(llm_summary)])
        )

    
    # Assigning values used in grade distribution section
    def _add_grade_distr_fields(self):
        """
        Populate grade distribution metrics from self.metrics dict.
        """

        # Grade A (A+, A, A-)
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeACount'), str(self.metrics['grades']['A']['count'])]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeAPct'), self.metrics['grades']['A']['pct']]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeADelta'), self.metrics['grades']['A']['delta']]))

        # Grade B (B+, B, B-)
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeBCount'), str(self.metrics['grades']['B']['count'])]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeBPct'), self.metrics['grades']['B']['pct']]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeBDelta'), self.metrics['grades']['B']['delta']]))

        # Grade C (C+, C)
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeCCount'), str(self.metrics['grades']['C']['count'])]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeCPct'), self.metrics['grades']['C']['pct']]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeCDelta'), self.metrics['grades']['C']['delta']]))

        # Grade D
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeDCount'), str(self.metrics['grades']['D']['count'])]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeDPct'), self.metrics['grades']['D']['pct']]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeDDelta'), self.metrics['grades']['D']['delta']]))

        # Grade E
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeECount'), str(self.metrics['grades']['E']['count'])]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeEPct'), self.metrics['grades']['E']['pct']]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeEDelta'), self.metrics['grades']['E']['delta']]))

        # Quartile grades from metrics
        q1 = str(self.metrics['quartiles']['q1']) if self.metrics['quartiles']['q1'] else 'N/A'
        q2 = str(self.metrics['quartiles']['q2']) if self.metrics['quartiles']['q2'] else 'N/A'
        q3 = str(self.metrics['quartiles']['q3']) if self.metrics['quartiles']['q3'] else 'N/A'

        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\Qone'), q1]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\Qtwo'), q2]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\Qthree'), q3]))

        # TODO: Calculate quartile deltas if we have historical quartile data
        q1_delta = str(0)
        q2_delta = str(0)
        q3_delta = str(0)
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\QoneDelta'), q1_delta]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\QtwoDelta'), q2_delta]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\QthreeDelta'), q3_delta]))

    def _define_helper_commands(self):
        # Retrieve helper commands
        self.doc.preamble.append(NoEscape(latex_sections.get_helper_commands_template()))
    
    def _define_layout_lengths(self):
        right_col_width = "2.2in"
        self.doc.preamble.append(NoEscape(r'\newlength{\RightColW}'))
        self.doc.preamble.append(NoEscape(f'\\setlength{{\\RightColW}}{{{right_col_width}}}'))
        
        grade_vis_height = "2.2in"
        self.doc.preamble.append(NoEscape(r'\newlength{\GradeVisH}'))
        self.doc.preamble.append(NoEscape(f'\\setlength{{\\GradeVisH}}{{{grade_vis_height}}}'))
        
        delta_col_width = "1.8cm"
        self.doc.preamble.append(NoEscape(r'\newlength{\DeltaColW}'))
        self.doc.preamble.append(NoEscape(f'\\setlength{{\\DeltaColW}}{{{delta_col_width}}}'))
    
    def _define_header_toggles(self):
        # Define boolean toggles for headers
        self.doc.preamble.append(NoEscape(r'\newif\ifShowHdrOverview'))
        self.doc.preamble.append(NoEscape(r'\newif\ifShowHdrEval'))
        self.doc.preamble.append(NoEscape(r'\newif\ifShowHdrTitle'))
        
        overview_val = "true" if self.show_hdr_overview else "false"
        eval_val = "true" if self.show_hdr_eval else "false"
        title_val = "true" if self.show_hdr_title else "false"
        
        self.doc.preamble.append(NoEscape(f'\\ShowHdrOverview{overview_val}'))
        self.doc.preamble.append(NoEscape(f'\\ShowHdrEval{eval_val}'))
        self.doc.preamble.append(NoEscape(f'\\ShowHdrTitle{title_val}'))
    
    def _define_tcb_style(self):
        #Define tcolorbox styling
        self.doc.preamble.append(NoEscape(latex_sections.get_box_style_template()))

    def build_sections(self):
        """
        Build the document content (all sections)
        
        Call order:
        1. Page title
        2. Overview section
        3. Evaluation Metrics section
        4. Comment Summary section
        5. Grade Distribution section
        """
        self._add_page_title()
        self._add_overview_section()
        self._add_evaluation_section()
        if (_is_true(self.config["scorecard_gen_settings"]["include_LLM_insights"])):
            self._add_comment_section()
        self._add_grade_distribution_section()
    
    def _add_page_title(self):
        """Add the page-level title"""
        self.doc.append(NoEscape(latex_sections.get_page_title_template()))
    
    def _add_overview_section(self):
        """Add the Overview tcolorbox section"""
        self.doc.append(NoEscape(latex_sections.get_overview_section_template()))
    
    def _add_evaluation_section(self):
        """Add the Evaluation Metrics tcolorbox section"""
        self.doc.append(NoEscape(latex_sections.get_evaluation_section_template()))
    
    def _add_comment_section(self):
        """Add the Comment Summary tcolorbox section"""
        self.doc.append(NoEscape(latex_sections.get_comment_section_template()))
    
    def _add_grade_distribution_section(self):
        """Add the Grade Distribution tcolorbox section"""
        template = latex_sections.get_grade_distribution_section_template(
            self.grade_hist
        )
        self.doc.append(NoEscape(template))
    
def load_pdf_json(pdf_json_path):
    # Attempt to load the file
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

def assemble_scorecard(
        course: Mapping[str, Any],
        config,
        csv_path,
    ):
    """
    Generates the .tex for the scorecard & saves it as a pdf.

    Args:
        scorecard_set (`tuple` of (`dict`, `str`)):
            - The first element [0] is a dict of the matched csv row
            - The second element [1] is the path to the json file of the parsed pdf.
    Todo:
        Implement the aggregate data metrics
    """
    paths = config['paths']
    
    agg_data = aggregate_for_row(
        comparison=config['comparison'],
        row=course,
        json_dir=paths['parsed_pdf_dir'],
        csv_path=csv_path
    )

    histogram_dir=paths['grade_histogram_dir']
    tex_output_path=paths['tex_dir']
    scorecard_output_path=paths['scorecard_dir']

    # Source the grade histogram from the json path (similar naming structure)
    histrogram_name = course_to_stem(course)
    histogram_full_path = os.path.join(histogram_dir, f"{histrogram_name}.png")

    # Load the pdf json representation
    pdf_json = load_pdf_json(course_to_json_path(course))
    
    # Generate the latex doc
    latex_doc = _ScorecardDoc(
        csv_row=course,
        pdf_json=pdf_json,
        grade_hist=histogram_full_path,
        output_filename=histrogram_name,
        agg_data=agg_data,
        config=config,
        )
    
    latex_doc.doc_setup()

    # Save the latex doc to the temp folder in its subdirectory
    full_output_path = os.path.join(tex_output_path, latex_doc.output_filename)
    latex_doc.doc.generate_tex(full_output_path)
    print(f"  ✅ Saved LaTeX to {full_output_path}")

    # Save the latex as a pdf now
    #pdf_filename = latex_doc.output_filename
    #full_scorecard_output_path = os.path.join(scorecard_output_path, pdf_filename)
    #latex_doc.doc.generate_pdf(pdf_filename, clean_tex=False, compiler='pdflatex')
   # print(f"📝✅ Saved PDF Scorecard to {full_scorecard_output_path}")

def assemble_instructor_scorecard(
    instructor: Mapping[str, Any],
    config,
    csv_path,
):
    """
    Basic implementation that finds courses by instructor and saves to DataFrame.
    This is the equivalent of assemble_scorecard but for professors.
    """
    print(f" Starting instructor scorecard for: {instructor.get('Instructor', 'N/A')}")

    # Get all courses for this instructor
    instructor_courses = data_handler.get_courses_by_instructor(instructor, csv_path)

    if instructor_courses.empty:
        print(f" No courses found for instructor: {instructor.get('Instructor', 'N/A')}")
        return None

    # Print summary of what was found
    print(f"✅ Instructor {instructor.get('Instructor', 'N/A')} teaches {len(instructor_courses)} courses:")
    for _, course in instructor_courses.head(5).iterrows():  # Show first 5 as sample
        subject = course.get('Subject', 'UNKN')
        catalog = course.get('Catalog Nbr', '000')
        class_nbr = course.get('Class Nbr', '')
        print(f"   - {subject} {catalog} (Class {class_nbr})")

    if len(instructor_courses) > 5:
        print(f"   ... and {len(instructor_courses) - 5} more courses")

    # TODO: Add LaTeX generation for instructor scorecard here
    # For now, just return the DataFrame as requested
    return instructor_courses