import json
import os
import re
import sys


from pylatex import(
    Command,
    Document,
    NoEscape,
    Package,
    Section,
)
from src import latex_sections

# Organizing all the data necessary for automating the latex, much cleaner containing
#   everything in one class.
class _ScorecardDoc:

    def __init__(self, csv_row, pdf_json, grade_hist, output_filename):
        self.csv_row = csv_row
        self.pdf_json = pdf_json
        self.grade_hist = grade_hist
        self.output_filename = output_filename

        # Tex related fields
        self.doc = None
        self.show_hdr_overview = False
        self.show_hdr_eval = False
        self.show_hdr_title = True
        self.baseline_text = "Compared to baseline: Average of all CSE100 courses"

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
        self.doc.preamble.append(NoEscape(r'\colorlet{pos}{green!60!black}'))
        self.doc.preamble.append(NoEscape(r'\colorlet{neg}{red!70!black}'))
        self.doc.preamble.append(NoEscape(r'\colorlet{neu}{gray!70!black}'))

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

        # TODO: Add functionality for including session for the term (A|B|C)
        #   probably pull from a temp csv? Just having the term here in the meantime
        course_term = f"{self.pdf_json['eval_info']['term']}"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\CourseTerm'), course_term]))

        course_code = f"{self.pdf_json['eval_info']['course_number']}"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\CourseCode'), course_code]))
        
        instructor = f"{self.pdf_json['eval_info']['professor']}"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\Instructor'), instructor]))

        # TODO: Probably want to pull this from the data frame as well? Once we get
        #   to clearly organizing the csvs, but just pulling from the json for now
        course_size = f"{self.pdf_json['eval_info']['total_students']}"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\CourseSize'), str(course_size)]))

        # TODO: Just a place holder number for now. Will need to calculate the pop. 
        #   mean for course size to get the avg course size across a given course
        course_size_delta = 10
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\CourseSizeDelta'), str(course_size_delta)]))

        responses = f"{self.pdf_json['eval_info']['response_count']}"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\Responses'), str(responses)]))

        # May need to add '\\' to escape for the percent
        response_rate = f"{self.pdf_json['eval_info']['response_rate']}"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\ResponseRate'), response_rate]))

        # TODO: Calculating the delta will involve calculating the avg response rate
        #   across all .json 'response_rate' key values. Placeholder for now
        response_delta = f"-10%"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\ResponseDelta'), response_delta]))

        avg_p1 = f"{self.pdf_json['eval_info']['avg1']}"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\AvgPone'), str(avg_p1)]))

        # TODO: Calculating the avg1 delta across all .json 'avg1' key values.
        #   placeholder for now
        avg_p1_delta = f"-0.10"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\AvgPoneDelta'), avg_p1_delta]))

        avg_p2 = f"{self.pdf_json['eval_info']['avg2']}"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\AvgPtwo'), str(avg_p2)]))

        # TODO: Calculating the avg2 delta across all .json 'avg2' key values.
        #   placeholder for now
        avg_p2_delta = f"+0.30"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\AvgPtwoDelta'), avg_p2_delta]))

        # TODO: Calculating the median grade across all given course occurences
        median_grade = f"C-"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\MedianGrade'), median_grade]))

        median_grade_delta = f"+1"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\MedianGradeDelta'), median_grade_delta]))
        median_grade = f"C-"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\MedianGrade'), median_grade]))
        
        # TODO: Calculate GPA (figure out what baseline the given course's GPA is being
        #   compared to)
        gpa = 3.13
        gpa_delta = -0.09
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GPA'), str(gpa)]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GPADelta'), str(gpa_delta)]))
        
        # TODO: Fill in data frame info for passing, failing, drops, & withdrawals
        #   and compute their respective deltas using a baseline. Place holders for now
        pass_count = 41
        pass_pct = f"88%"
        pass_delta = f"-3%"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\PassNum'), str(pass_count)]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\PassPct'), pass_pct]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\PassDelta'), pass_delta]))
        
        fail_count = 8
        fail_pct = f"8%"
        fail_delta = f"+2%"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\FailNum'), str(fail_count)]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\FailPct'), fail_pct]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\FailDelta'), fail_delta]))
        
        drop_count = 2
        drop_pct = f"2%"
        drop_delta = f"+2%"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\DropNum'), str(drop_count)]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\DropPct'), drop_pct]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\DropDelta'), drop_delta]))

        withdraw_count = 2
        withdraw_pct = f"2%"
        withdraw_delta = f"+2%"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\WithdrawNum'), str(withdraw_count)]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\WithdrawPct'), withdraw_pct]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\WithdrawDelta'), withdraw_delta]))

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
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\CommentCount'), str(comment_count)]))

        llm_summary = f"Placeholder LLM summary. Pending latest LLM integration."
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\LLMSummary'), llm_summary]))
    
    # Assigning values used in grade distribution section
    def _add_grade_distr_fields(self):

        """TODO: Once we are able to dynamically select the CSV, we can update all these
           UPDATE: We have the csv row functionality, so now we just need to populate these fields
           - if accessing a column's value, use .iloc[0] to avoid any depreciated functionality in the future
        """
        grade_a_count = int(self.csv_row['A'].iloc[0]) + int(self.csv_row['A+'].iloc[0]) + int(self.csv_row['A-'].iloc[0])
        grade_a_pct = f"10%"
        grade_a_delta = f"-2%"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeACount'), str(grade_a_count)]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeAPct'), grade_a_pct]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeADelta'), grade_a_delta]))
        
        grade_b_count = str(46)
        grade_b_pct = f"72%"
        grade_b_delta = f"+1%"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeBCount'), grade_b_count]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeBPct'), grade_b_pct]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeBDelta'), grade_b_delta]))
        
        grade_c_count = str(17)
        grade_c_pct = f"14%"
        grade_c_delta = f"-1%"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeCCount'), grade_c_count]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeCPct'), grade_c_pct]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeCDelta'), grade_c_delta]))
        
        grade_d_count = str(4)
        grade_d_pct = f"2%"
        grade_d_delta = f"+0%"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeDCount'), grade_d_count]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeDPct'), grade_d_pct]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeDDelta'), grade_d_delta]))
        
        grade_f_count = str(4)
        grade_f_pct = f"2%"
        grade_f_delta = f"+1%"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeFCount'), grade_f_count]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeFPct'), grade_f_pct]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\GradeFDelta'), grade_f_delta]))

        # TODO: Clearly define what we are trying to show here for the quarters
        q1 = str(4)
        q2 = str(4)
        q3 = str(4)
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\Qone'), q1]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\Qtwo'), q2]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\Qthree'), q3]))
        
        q1_delta = str(-2)
        q2_delta = str(-2)
        q3_delta = str(-2)
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

def get_fname_from_json_path(json_path):
    fname_match = re.match((r".*/(.*)(?=\.json)"), json_path)

    if fname_match:
        return fname_match.group(1)
    else:
        print(f"Couldn't capture file name from json path for grade histogram sourcing.")
        return None
    
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
     

def assemble_scorecard(scorecard_set, histogram_dir, tex_output_path, scorecard_output_path):
    # Source the grade histogram from the json path (similar naming structure)
    histrogram_name = get_fname_from_json_path(scorecard_set[1])
    histogram_full_path = os.path.join(histogram_dir, f"{histrogram_name}.png")

    # Load the pdf json representation
    pdf_json = load_pdf_json(scorecard_set[1])
    
    # Generate the latex doc
    latex_doc = _ScorecardDoc(csv_row=scorecard_set[0], pdf_json=pdf_json, grade_hist=histogram_full_path, output_filename=histrogram_name)
    latex_doc.doc_setup()

    # Save the latex doc to the temp folder in its subdirectory
    full_output_path = os.path.join(tex_output_path, latex_doc.output_filename)
    latex_doc.doc.generate_tex(full_output_path)
    print(f"📝✅ Saved LaTeX to {full_output_path}")

    # Save the latex as a pdf now
    #pdf_filename = latex_doc.output_filename
    #full_scorecard_output_path = os.path.join(scorecard_output_path, pdf_filename)
    #latex_doc.doc.generate_pdf(pdf_filename, clean_tex=False, compiler='pdflatex')
   # print(f"📝✅ Saved PDF Scorecard to {full_scorecard_output_path}")



