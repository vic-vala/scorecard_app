import json
import os

from pylatex import(
    Command,
    Document,
    NoEscape,
    Package,
    Section,
)

# Organizing all the data necessary for automating the latex, much cleaner containing
#   everything in one class.
class _ScorecardDoc:

    def __init__(self, pdf_json, output_filename):
        self.doc = None
        self.pdf_json = pdf_json
        self.output_filename = output_filename

        # Driver function, setting up the documentclass, packages, preamble
    def doc_setup(self):
        self.doc = Document(documentclass='article', document_options=['11pt'])
        self._add_packages()
        self._add_preamble()
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

    # Color palette, commands, & other macros
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
        response_delta = f"-10\\%"
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
        pass_pct = f"88\\%"
        pass_delta = f"-3\\%"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\PassNum'), str(pass_count)]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\PassPct'), pass_pct]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\PassDelta'), pass_delta]))
        
        fail_count = 8
        fail_pct = f"8\\%"
        fail_delta = f"+2\\%"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\FailNum'), str(fail_count)]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\FailPct'), fail_pct]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\FailDelta'), fail_delta]))
        
        drop_count = 2
        drop_pct = f"2\\%"
        drop_delta = f"+2\\%"
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\DropNum'), str(drop_count)]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\DropPct'), drop_pct]))
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\DropDelta'), drop_delta]))

        withdraw_count = 2
        withdraw_pct = f"2\\%"
        withdraw_delta = f"+2\\%"
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
    
    def _add_summary_fields(self):

        # TODO: Modify pdf_json schema to also have a count value for the comments maybe
        comment_count = 4
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\CommentCount'), str(comment_count)]))

        llm_summary = f"Placeholder LLM summary. Pending latest LLM integration."
        self.doc.preamble.append(Command('newcommand', [NoEscape(r'\LLMSummary'), llm_summary]))

def assemble_scorecard(pdf_json, data_visx, output_path):
        
    # Generate the latex doc
    latex_doc = _ScorecardDoc(pdf_json=pdf_json, output_filename="test")
    latex_doc.doc_setup()

    # Save the latex doc to the temp folder in its subdirectory
    full_output_path = os.path.join(output_path, latex_doc.output_filename)
    latex_doc.doc.generate_tex(full_output_path)

    print(f"📝✅ Saved LaTeX to {full_output_path}")

