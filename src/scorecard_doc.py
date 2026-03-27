import json
import os
import sys
from typing import Any, Dict

from pylatex import(
    Command,
    Document,
    NoEscape,
    Package,
)
from .latex_sections import per_session
from src import compute_metrics
from src.utils import _is_true


class _ScorecardDoc:
    """
    Organizing all the data necessary for automating the latex, much cleaner containing
    everything in one class.
    """

    def __init__(
            self,
            csv_row: Dict[str, Any],
            pdf_json: str,
            grade_hist: str,
            output_filename: str,
            agg_data: Dict[str, Any],
            config,
            short:bool,
            newcommand:bool,
            ):
        self.csv_row = csv_row
        self.pdf_json = pdf_json
        self.grade_hist = grade_hist
        self.output_filename = output_filename
        self.agg_data = agg_data
        self.config = config
        self.short = short
        self.newcommand = newcommand

        # Tex related fields
        self.doc = None
        self.show_hdr_overview = False
        self.show_hdr_eval = False
        self.show_hdr_title = True
        self.baseline_text = agg_data['aggregate_name']

        self.write_course_cmds_to_preamble = True

        # Compute all metrics on initialization
        self.metrics = self._compute_all_metrics()

    def _course_cmd_container(self):
        """
        where to put course-specific \\newcommand/\\renewcommand definitions.

        - preamble (default) for single-course docs
        - body for multi-course instructor docs
        """
        if self.doc is None:
            raise ValueError("Document has not been initialized")
        return self.doc.preamble if self.write_course_cmds_to_preamble else self.doc


    def _latex_command_name(self) -> str:
        """
        Return 'newcommand' or 'renewcommand' based on self.newcommand.
        """
        return "newcommand" if self.newcommand else "renewcommand"

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
            ('colortbl', None),
            ('multirow', None),
            ('array', None),
            ('xstring', None),
            ('calc', None),
            ('ragged2e', None),
            ('amsmath', None),
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
        self.doc.preamble.append(NoEscape(r'\colorlet{pos}{gray!60!black}'))
        self.doc.preamble.append(NoEscape(r'\colorlet{neg}{gray!70!black}'))
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

        cmd = self._latex_command_name()
        container = self._course_cmd_container()

        course_name = f"{self.pdf_json['eval_info']['department']} {self.pdf_json['eval_info']['course']}"
        container.append(Command(cmd, [NoEscape(r'\CourseName'), course_name]))
        course_year = f"{self.pdf_json['eval_info']['year']}"
        container.append(Command(cmd, [NoEscape(r'\CourseYear'), course_year]))

        # Term pulled form json, session pulled from csv row
        course_session = str(self.csv_row['Session Code'])
        course_term = f"{self.pdf_json['eval_info']['term']} {course_session}"
        container.append(Command(cmd, [NoEscape(r'\CourseTerm'), course_term]))

        # Course code (5-digit one) pulled from json
        course_code = f"{self.pdf_json['eval_info']['course_number']}"
        container.append(Command(cmd, [NoEscape(r'\CourseCode'), course_code]))

        # Instructor first and last name
        instructor = f"{self.pdf_json['eval_info']['instructor_first_name']} {self.pdf_json['eval_info']['professor']}"
        container.append(Command(cmd, [NoEscape(r'\Instructor'), instructor]))

        # Baseline Text
        container.append(Command(cmd, [NoEscape(r'\BaselineText'), self.baseline_text]))

        # Pulled from csv row
        course_size = int(self.csv_row['Class Size'])
        container.append(Command(cmd, [NoEscape(r'\CourseSize'), str(course_size)]))

        # Calculate course size delta against aggregate average
        course_size_delta = compute_metrics.get_course_size_delta(self.csv_row, self.agg_data)
        container.append(Command(cmd, [NoEscape(r'\CourseSizeDelta'), str(course_size_delta)]))

        responses = f"{self.pdf_json['eval_info']['response_count']}"
        container.append(Command(cmd, [NoEscape(r'\Responses'), str(responses)]))

        # May need to add '\\' to escape for the percent
        response_rate = f"{self.pdf_json['eval_info']['response_rate']}"
        container.append(Command(cmd, [NoEscape(r'\ResponseRate'), response_rate]))

        # Calculate response rate delta (currently returns N/A until aggregate tracking is added)
        response_delta = compute_metrics.get_response_rate_delta(self.pdf_json, self.agg_data)
        container.append(Command(cmd, [NoEscape(r'\ResponseDelta'), response_delta]))

        avg_p1 = f"{self.pdf_json['eval_info']['avg1']}"
        container.append(Command(cmd, [NoEscape(r'\AvgPone'), str(avg_p1)]))

        # Calculate avg1 delta against aggregate baseline
        avg_p1_delta = compute_metrics.get_avg_part1_delta(self.pdf_json, self.agg_data)
        container.append(Command(cmd, [NoEscape(r'\AvgPoneDelta'), avg_p1_delta]))

        avg_p2 = f"{self.pdf_json['eval_info']['avg2']}"
        container.append(Command(cmd, [NoEscape(r'\AvgPtwo'), str(avg_p2)]))

        # Calculate avg2 delta against aggregate baseline
        avg_p2_delta = compute_metrics.get_avg_part2_delta(self.pdf_json, self.agg_data)
        container.append(Command(cmd, [NoEscape(r'\AvgPtwoDelta'), avg_p2_delta]))

        # Overall average (average of avg1 and avg2)
        avg1_val = float(self.pdf_json['eval_info']['avg1'])
        avg2_val = float(self.pdf_json['eval_info']['avg2'])
        avg_overall = round((avg1_val + avg2_val) / 2, 2)
        container.append(Command(cmd, [NoEscape(r'\AvgOverall'), str(avg_overall)]))

        # Calculate overall average delta (average of the two deltas)
        avg_overall_delta = "N/A"
        if self.agg_data.get('avg1') and self.agg_data.get('avg2'):
            baseline_avg1 = float(self.agg_data['avg1'])
            baseline_avg2 = float(self.agg_data['avg2'])
            baseline_overall = (baseline_avg1 + baseline_avg2) / 2
            delta_val = avg_overall - baseline_overall
            avg_overall_delta = f"{delta_val:+.2f}" if delta_val != 0 else "0"
        container.append(Command(cmd, [NoEscape(r'\AvgOverallDelta'), avg_overall_delta]))

        # Median grade from aggregate data (baseline)
        median_grade = self.agg_data['median_grade']
        container.append(Command(cmd, [NoEscape(r'\MedianGrade'), median_grade]))

        # Median grade for course row
        container.append(Command(cmd, [NoEscape(r'\MedianGradeDelta'), self.metrics['median_grade']['individual']]))

        # GPA and delta calculation using metrics dict
        container.append(Command(cmd, [NoEscape(r'\GPA'), str(self.metrics['gpa']['value'])]))
        container.append(Command(cmd, [NoEscape(r'\GPADelta'), self.metrics['gpa']['delta']]))

        # Pass metrics
        container.append(Command(cmd, [NoEscape(r'\PassNum'), str(self.metrics['pass']['count'])]))
        container.append(Command(cmd, [NoEscape(r'\PassPct'), self.metrics['pass']['pct']]))
        container.append(Command(cmd, [NoEscape(r'\PassDelta'), self.metrics['pass']['delta']]))

        # Fail metrics
        container.append(Command(cmd, [NoEscape(r'\FailNum'), str(self.metrics['fail']['count'])]))
        container.append(Command(cmd, [NoEscape(r'\FailPct'), self.metrics['fail']['pct']]))
        container.append(Command(cmd, [NoEscape(r'\FailDelta'), self.metrics['fail']['delta']]))

        # Drop metrics
        container.append(Command(cmd, [NoEscape(r'\DropNum'), str(self.metrics['drop']['count'])]))
        container.append(Command(cmd, [NoEscape(r'\DropPct'), self.metrics['drop']['pct']]))
        container.append(Command(cmd, [NoEscape(r'\DropDelta'), self.metrics['drop']['delta']]))

        # Withdraw metrics
        container.append(Command(cmd, [NoEscape(r'\WithdrawNum'), str(self.metrics['withdraw']['count'])]))
        container.append(Command(cmd, [NoEscape(r'\WithdrawPct'), self.metrics['withdraw']['pct']]))
        container.append(Command(cmd, [NoEscape(r'\WithdrawDelta'), self.metrics['withdraw']['delta']]))

    # Assigning values to the fields in the evaluation metrics section
    def _add_evaluation_metrics_fields(self):
        """
        Build LaTeX commands for the 5 lowest scoring evaluation metrics across part_1 and part_2
        """

        cmd = self._latex_command_name()
        container = self._course_cmd_container()

        part_1 = self.pdf_json.get("part_1", {})
        part_2 = self.pdf_json.get("part_2", {})

        metric_descriptions = {
            # part_1
            "textbook_avg": "Textbook supplementary material in support of the course",
            "homework_value_avg": "Value of assigned homework in support of course topics",
            "lab_value_avg": "Value of laboratory assignments projects in support of the course topics",
            "exam_reason_avg": "Reasonableness of exams and quizzes in covering course material",
            "lab_weight_avg": "Weight given to labs or projects relative to exams and quizzes",
            "homework_weight_avg": "Weight given to homework assignments relative to exams and quizzes",
            "grade_crit_avg": "Definition and application of criteria for grading",

            # part_2
            "instr_prep_avg": "The instructor was well prepared",
            "instr_comm_idea_avg": "The instructor communicated ideas clearly",
            "availability_avg": "The instructor or assistants were available for outside assistance",
            "enthus_avg": "The instructor exhibited enthusiasm for and interest in the subject",
            "instr_approach_avg": "The instructors approach stimulated student thinking",
            "course_mat_application_avg": "The instructor related course material to its applications",
            "present_methods_avg": "The instructors methods of presentation supported student learning",
            "fair_grading_avg": "The instructors grading was fair impartial and adequate",
            "timely_grading_avg": "The instructor returned graded materials within a reasonable period",
        }

        # collect all numeric metrics as (metric_key, score_float, score_original_str)
        all_metrics = []

        for key, val in part_1.items():
            try:
                score_float = float(val)
            except (TypeError, ValueError):
                continue
            all_metrics.append((key, score_float, val))

        for key, val in part_2.items():
            try:
                score_float = float(val)
            except (TypeError, ValueError):
                continue
            all_metrics.append((key, score_float, val))

        # sort by score (ascending: lowest scores first)
        all_metrics.sort(key=lambda item: item[1])

        # mapping from rank to word for latex command names
        # \OutOneName, \OutTwoName, ..., \OutFiveScore
        index_to_word = {
            1: "One",
            2: "Two",
            3: "Three",
            4: "Four",
            5: "Five",
        }

        # take the 5 lowest scores and create latex commands for each
        for idx, (metric_key, _score_float, score_str) in enumerate(all_metrics[:5], start=1):
            word = index_to_word.get(idx)
            if not word:
                break

            metric_name = metric_descriptions.get(metric_key, metric_key)

            container.append(
                Command(cmd, [NoEscape(f"\\Out{word}Name"), metric_name])
            )

            container.append(
                Command(cmd, [NoEscape(f"\\Out{word}Score"), str(score_str)])
            )

    # Assigning values used in LLM comment summary section
    def _add_summary_fields(self):

        cmd = self._latex_command_name()
        container = self._course_cmd_container()

        # TODO: Modify pdf_json schema to also have a count value for the comments maybe
        comment_count = 4
        container.append(
            Command(cmd, [NoEscape(r'\CommentCount'), str(comment_count)])
        )

        llm_summary = self.pdf_json['llm_summary']
        container.append(
            Command(cmd, [NoEscape(r'\LLMSummary'), NoEscape(llm_summary)])
        )


    # Assigning values used in grade distribution section
    def _add_grade_distr_fields(self):
        """
        Populate grade distribution metrics from self.metrics dict.
        """

        cmd = self._latex_command_name()
        container = self._course_cmd_container()

        # Grade A (A+, A, A-)
        container.append(Command(cmd, [NoEscape(r'\GradeACount'), str(self.metrics['grades']['A']['count'])]))
        container.append(Command(cmd, [NoEscape(r'\GradeAPct'), self.metrics['grades']['A']['pct']]))
        container.append(Command(cmd, [NoEscape(r'\GradeADelta'), self.metrics['grades']['A']['delta']]))

        # Grade B (B+, B, B-)
        container.append(Command(cmd, [NoEscape(r'\GradeBCount'), str(self.metrics['grades']['B']['count'])]))
        container.append(Command(cmd, [NoEscape(r'\GradeBPct'), self.metrics['grades']['B']['pct']]))
        container.append(Command(cmd, [NoEscape(r'\GradeBDelta'), self.metrics['grades']['B']['delta']]))

        # Grade C (C+, C)
        container.append(Command(cmd, [NoEscape(r'\GradeCCount'), str(self.metrics['grades']['C']['count'])]))
        container.append(Command(cmd, [NoEscape(r'\GradeCPct'), self.metrics['grades']['C']['pct']]))
        container.append(Command(cmd, [NoEscape(r'\GradeCDelta'), self.metrics['grades']['C']['delta']]))

        # Grade D
        container.append(Command(cmd, [NoEscape(r'\GradeDCount'), str(self.metrics['grades']['D']['count'])]))
        container.append(Command(cmd, [NoEscape(r'\GradeDPct'), self.metrics['grades']['D']['pct']]))
        container.append(Command(cmd, [NoEscape(r'\GradeDDelta'), self.metrics['grades']['D']['delta']]))

        # Grade E
        container.append(Command(cmd, [NoEscape(r'\GradeECount'), str(self.metrics['grades']['E']['count'])]))
        container.append(Command(cmd, [NoEscape(r'\GradeEPct'), self.metrics['grades']['E']['pct']]))
        container.append(Command(cmd, [NoEscape(r'\GradeEDelta'), self.metrics['grades']['E']['delta']]))

        # Quartile grades from metrics
        q1 = str(self.metrics['quartiles']['q1']) if self.metrics['quartiles']['q1'] else 'N/A'
        q2 = str(self.metrics['quartiles']['q2']) if self.metrics['quartiles']['q2'] else 'N/A'
        q3 = str(self.metrics['quartiles']['q3']) if self.metrics['quartiles']['q3'] else 'N/A'

        container.append(Command(cmd, [NoEscape(r'\Qone'), q1]))
        container.append(Command(cmd, [NoEscape(r'\Qtwo'), q2]))
        container.append(Command(cmd, [NoEscape(r'\Qthree'), q3]))

        # TODO: Calculate quartile deltas if we have historical quartile data
        q1_delta = str(0)
        q2_delta = str(0)
        q3_delta = str(0)
        container.append(Command(cmd, [NoEscape(r'\QoneDelta'), q1_delta]))
        container.append(Command(cmd, [NoEscape(r'\QtwoDelta'), q2_delta]))
        container.append(Command(cmd, [NoEscape(r'\QthreeDelta'), q3_delta]))

    def _define_helper_commands(self):
        # Retrieve helper commands
        self.doc.preamble.append(NoEscape(per_session.get_helper_commands_template()))

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
        self.doc.preamble.append(NoEscape(per_session.get_box_style_template()))

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
        if self.short:
            self.add_short_section()
        else:
            self._add_page_title()
            self._add_overview_section()
            self._add_evaluation_section()
            if (_is_true(self.config["scorecard_gen_settings"]["include_LLM_insights"])):
                self._add_comment_section()
            self._add_grade_distribution_section()

    def add_short_section(self):
        """Add the short coursecard"""
        self.doc.append(NoEscape(per_session.get_short_course_card()))

    def _add_page_title(self):
        """Add the page-level title"""
        self.doc.append(NoEscape(per_session.get_page_title_template()))

    def _add_overview_section(self):
        """Add the Overview tcolorbox section"""
        self.doc.append(NoEscape(per_session.get_overview_section_template()))

    def _add_evaluation_section(self):
        """Add the Evaluation Metrics tcolorbox section"""
        self.doc.append(NoEscape(per_session.get_evaluation_section_template()))

    def _add_comment_section(self):
        """Add the Comment Summary tcolorbox section"""
        self.doc.append(NoEscape(per_session.get_comment_section_template()))

    def _add_grade_distribution_section(self):
        """Add the Grade Distribution tcolorbox section"""
        template = per_session.get_grade_distribution_section_template(
            self.grade_hist
        )
        self.doc.append(NoEscape(template))