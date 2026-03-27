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
from .latex_sections import consolidated_tex
from src import compute_metrics
from src.utils import _is_true


class _ConsolidatedDoc:
    """
    Document class for the consolidated tabular scorecard layout.
    Mirrors _ScorecardDoc's interface
    """

    def __init__(
            self,
            csv_row: Dict[str, Any],
            pdf_json: str,
            grade_hist: str,
            output_filename: str,
            agg_data: Dict[str, Any],
            config,
            newcommand: bool,
            boxplot_path: str,
            ):
        self.csv_row = csv_row
        self.pdf_json = pdf_json
        self.grade_hist = grade_hist
        self.output_filename = output_filename
        self.agg_data = agg_data
        self.config = config
        self.newcommand = newcommand
        self.boxplot_path = boxplot_path

        # Tex related fields
        self.doc = None
        self.baseline_text = agg_data['aggregate_name']

        self.write_course_cmds_to_preamble = True

        # Compute all metrics on initialization
        self.metrics = self._compute_all_metrics()

    def _course_cmd_container(self):
        """
        Where to put course-specific \\newcommand/\\renewcommand definitions.

        - preamble (default) for single-course docs
        - body for multi-course instructor docs
        """
        if self.doc is None:
            raise ValueError("Document has not been initialized")
        return self.doc.preamble if self.write_course_cmds_to_preamble else self.doc

    def _latex_command_name(self) -> str:
        """Return 'newcommand' or 'renewcommand' based on self.newcommand."""
        return "newcommand" if self.newcommand else "renewcommand"

    def _compute_all_metrics(self) -> Dict[str, Any]:
        """
        Compute all grade and evaluation metrics when _ConsolidatedDoc is initialized.

        Returns:
            dict with nested structure containing all computed metrics.
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


    def doc_setup(self):
        self.doc = Document(documentclass='article', document_options=['11pt'])
        self._add_packages()
        self._add_preamble()
        self.build_sections()
        return self.doc

    def _add_packages(self):
        packages = [
            ('geometry', ['margin=0.5in']),
            ('fontenc', ['T1']),
            ('inputenc', ['utf8']),
            ('textcomp', None),
            ('lastpage', None),
            ('xcolor', ['table']),
            ('graphicx', None),
            ('tabularx', None),
            ('booktabs', None),
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

    def _add_preamble(self):
        # Colors
        self.doc.preamble.append(NoEscape(consolidated_tex.get_color_definitions()))

        # Data commands
        self._add_overview_fields()
        self._add_summary_fields()
        self._add_grade_distr_fields()

        # Helper commands (autoD, spark, rules)
        self.doc.preamble.append(NoEscape(
            consolidated_tex.get_helper_commands(self.boxplot_path)
        ))

        # Column dimensions and types
        self.doc.preamble.append(NoEscape(consolidated_tex.get_column_definitions()))

        # Page style
        self.doc.preamble.append(Command('pagestyle', 'empty'))

    # Field definitions (LaTeX \newcommand/\renewcommand) 

    def _add_overview_fields(self):
        cmd = self._latex_command_name()
        container = self._course_cmd_container()

        course_name = f"{self.pdf_json['eval_info']['department']} {self.pdf_json['eval_info']['course']}"
        container.append(Command(cmd, [NoEscape(r'\CourseName'), course_name]))

        course_year = f"{self.pdf_json['eval_info']['year']}"
        container.append(Command(cmd, [NoEscape(r'\CourseYear'), course_year]))

        course_session = str(self.csv_row['Session Code'])
        course_term = f"{self.pdf_json['eval_info']['term']} {course_session}"
        container.append(Command(cmd, [NoEscape(r'\CourseTerm'), course_term]))

        course_code = f"{self.pdf_json['eval_info']['course_number']}"
        container.append(Command(cmd, [NoEscape(r'\CourseCode'), course_code]))

        instructor = f"{self.pdf_json['eval_info']['instructor_first_name']} {self.pdf_json['eval_info']['professor']}"
        container.append(Command(cmd, [NoEscape(r'\Instructor'), instructor]))

        container.append(Command(cmd, [NoEscape(r'\BaselineText'), self.baseline_text]))

        container.append(Command(cmd, [NoEscape(r'\CourseSize'), str(self.metrics['course_size']['value'])]))
        container.append(Command(cmd, [NoEscape(r'\CourseSizeDelta'), str(self.metrics['course_size']['delta'])]))

        container.append(Command(cmd, [NoEscape(r'\Responses'), str(self.metrics['response']['count'])]))
        container.append(Command(cmd, [NoEscape(r'\ResponseRate'), self.metrics['response']['rate']]))
        container.append(Command(cmd, [NoEscape(r'\ResponseDelta'), self.metrics['response']['delta']]))

        container.append(Command(cmd, [NoEscape(r'\AvgPone'), str(self.metrics['avg_part1']['value'])]))
        container.append(Command(cmd, [NoEscape(r'\AvgPoneDelta'), self.metrics['avg_part1']['delta']]))

        container.append(Command(cmd, [NoEscape(r'\AvgPtwo'), str(self.metrics['avg_part2']['value'])]))
        container.append(Command(cmd, [NoEscape(r'\AvgPtwoDelta'), self.metrics['avg_part2']['delta']]))

        # Overall average (average of avg1 and avg2)
        avg1_val = float(self.pdf_json['eval_info']['avg1'])
        avg2_val = float(self.pdf_json['eval_info']['avg2'])
        avg_overall = round((avg1_val + avg2_val) / 2, 2)
        container.append(Command(cmd, [NoEscape(r'\AvgOverall'), str(avg_overall)]))

        # Overall average delta
        avg_overall_delta = "N/A"
        if self.agg_data.get('avg1') and self.agg_data.get('avg2'):
            baseline_avg1 = float(self.agg_data['avg1'])
            baseline_avg2 = float(self.agg_data['avg2'])
            baseline_overall = (baseline_avg1 + baseline_avg2) / 2
            delta_val = avg_overall - baseline_overall
            avg_overall_delta = f"{delta_val:+.2f}" if delta_val != 0 else "0"
        container.append(Command(cmd, [NoEscape(r'\AvgOverallDelta'), avg_overall_delta]))

        # Median grade
        container.append(Command(cmd, [NoEscape(r'\MedianGrade'), self.metrics['median_grade']['individual']]))
        container.append(Command(cmd, [NoEscape(r'\MedianGradeDelta'), self.metrics['median_grade']['baseline']]))

        # GPA
        container.append(Command(cmd, [NoEscape(r'\GPA'), str(self.metrics['gpa']['value'])]))
        container.append(Command(cmd, [NoEscape(r'\GPADelta'), self.metrics['gpa']['delta']]))

        # Pass/Fail/Drop/Withdraw
        container.append(Command(cmd, [NoEscape(r'\PassNum'), str(self.metrics['pass']['count'])]))
        container.append(Command(cmd, [NoEscape(r'\PassPct'), self.metrics['pass']['pct']]))
        container.append(Command(cmd, [NoEscape(r'\PassDelta'), self.metrics['pass']['delta']]))

        container.append(Command(cmd, [NoEscape(r'\FailNum'), str(self.metrics['fail']['count'])]))
        container.append(Command(cmd, [NoEscape(r'\FailPct'), self.metrics['fail']['pct']]))
        container.append(Command(cmd, [NoEscape(r'\FailDelta'), self.metrics['fail']['delta']]))

        container.append(Command(cmd, [NoEscape(r'\DropNum'), str(self.metrics['drop']['count'])]))
        container.append(Command(cmd, [NoEscape(r'\DropPct'), self.metrics['drop']['pct']]))
        container.append(Command(cmd, [NoEscape(r'\DropDelta'), self.metrics['drop']['delta']]))

        container.append(Command(cmd, [NoEscape(r'\WithdrawNum'), str(self.metrics['withdraw']['count'])]))
        container.append(Command(cmd, [NoEscape(r'\WithdrawPct'), self.metrics['withdraw']['pct']]))
        container.append(Command(cmd, [NoEscape(r'\WithdrawDelta'), self.metrics['withdraw']['delta']]))

    def _add_summary_fields(self):
        cmd = self._latex_command_name()
        container = self._course_cmd_container()

        # NOTE: Comment count is hardcoded; should come from data
        comment_count = 4
        container.append(Command(cmd, [NoEscape(r'\CommentCount'), str(comment_count)]))

        llm_summary = self.pdf_json['llm_summary']
        container.append(Command(cmd, [NoEscape(r'\LLMSummary'), NoEscape(llm_summary)]))

    def _add_grade_distr_fields(self):
        cmd = self._latex_command_name()
        container = self._course_cmd_container()

        for letter in ['A', 'B', 'C', 'D', 'E']:
            container.append(Command(cmd, [NoEscape(rf'\Grade{letter}Count'), str(self.metrics['grades'][letter]['count'])]))
            container.append(Command(cmd, [NoEscape(rf'\Grade{letter}Pct'), self.metrics['grades'][letter]['pct']]))
            container.append(Command(cmd, [NoEscape(rf'\Grade{letter}Delta'), self.metrics['grades'][letter]['delta']]))

        # Quartiles
        q1 = str(self.metrics['quartiles']['q1']) if self.metrics['quartiles']['q1'] else 'N/A'
        q2 = str(self.metrics['quartiles']['q2']) if self.metrics['quartiles']['q2'] else 'N/A'
        q3 = str(self.metrics['quartiles']['q3']) if self.metrics['quartiles']['q3'] else 'N/A'

        container.append(Command(cmd, [NoEscape(r'\Qone'), q1]))
        container.append(Command(cmd, [NoEscape(r'\Qtwo'), q2]))
        container.append(Command(cmd, [NoEscape(r'\Qthree'), q3]))

        # TODO: Quartile deltas not implemented yet
        container.append(Command(cmd, [NoEscape(r'\QoneDelta'), str(0)]))
        container.append(Command(cmd, [NoEscape(r'\QtwoDelta'), str(0)]))
        container.append(Command(cmd, [NoEscape(r'\QthreeDelta'), str(0)]))

    # Section builders

    def build_sections(self):
        """Build all document body sections."""
        self._add_title_section()
        self._add_main_table()
        if _is_true(self.config["scorecard_gen_settings"]["include_LLM_insights"]):
            pass  # LLM summary is embedded in the main table
        self._add_grade_distribution_section()

    def _add_title_section(self):
        self.doc.append(NoEscape(consolidated_tex.get_title_section()))

    def _add_main_table(self):
        self.doc.append(NoEscape(consolidated_tex.get_main_scorecard_table()))

    def _add_grade_distribution_section(self):
        template = consolidated_tex.get_grade_distribution_section(self.grade_hist)
        self.doc.append(NoEscape(template))