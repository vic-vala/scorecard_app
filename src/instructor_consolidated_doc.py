"""
Document class for the instructor-level consolidated scorecard layout.
Generates the prof.tex-style tabular scorecard from instructor course data.
"""

import json
import os
import string
from typing import Any, Dict, List, Mapping, Optional

from pylatex import Command, Document, NoEscape, Package

from .latex_sections import instructor_consolidated_tex
from . import compute_metrics
from .utils import (
    GRADE_COLS,
    _is_true,
    _safe_float,
    _safe_int,
    course_to_json_path,
    course_to_stem,
)
from .data_handler import aggregate_for_row


# Ordered grade list for ordinal delta computation
_GRADE_ORDINAL = [
    "A+", "A", "A-", "B+", "B", "B-", "C+", "C", "D", "E",
    "EN", "EU", "I", "NR", "NR.1", "W", "X", "XE", "Y", "Z",
]
_GRADE_TO_ORD = {g: i for i, g in enumerate(_GRADE_ORDINAL)}


def _grade_ordinal_delta(individual_grade: Optional[str], baseline_grade: Optional[str]) -> str:
    """Ordinal step difference between two letter grades (positive = higher grade)."""
    if not individual_grade or not baseline_grade:
        return "0"
    i = _GRADE_TO_ORD.get(individual_grade)
    b = _GRADE_TO_ORD.get(baseline_grade)
    if i is None or b is None:
        return "0"
    delta = b - i  # lower ordinal index = higher grade, so baseline - individual
    if delta == 0:
        return "0"
    return f"+{delta}" if delta > 0 else str(delta)


def _latex_safe(val: Any) -> str:
    """Make a value safe for LaTeX (escape %, handle minus signs)."""
    s = str(val) if val is not None else "N/A"
    # Replace bare minus with LaTeX {-} for proper rendering in commands
    return s


def _pct_str(value: float) -> str:
    """Format a float (0-1) as 'XX%' string."""
    return f"{value * 100:.0f}\\%"


def _delta_pct_str(individual: float, baseline: float) -> str:
    """Format percentage delta as '+X%' or '-X%'."""
    delta = (individual - baseline) * 100
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.0f}\\%"


class _InstructorConsolidatedDoc:
    """
    Builds the instructor-level consolidated scorecard PDF.

    Workflow:
        1. Receives instructor_courses DataFrame (all courses for this instructor)
        2. For each course: loads JSON, computes per-course metrics + baseline
        3. Aggregates instructor-level KPIs
        4. Emits LaTeX commands and body sections
    """

    # Letters used as per-course prefixes in LaTeX commands
    PREFIXES = list(string.ascii_uppercase) + [
        f"{a}{b}" for a in string.ascii_uppercase for b in string.ascii_uppercase
    ]  # A-Z, then AA-ZZ (702 total, way more than needed)

    def __init__(
        self,
        instructor_row: Mapping[str, Any],
        instructor_courses,  # pd.DataFrame
        config: Dict[str, Any],
        csv_path: str,
        boxplot_path: str,
    ):
        self.instructor_row = instructor_row
        self.instructor_courses = instructor_courses
        self.config = config
        self.csv_path = csv_path
        self.boxplot_path = boxplot_path
        self.paths = config["paths"]

        self.doc: Optional[Document] = None

        # Computed in _compute_all()
        self.per_course_metrics: List[Dict[str, Any]] = []
        self.agg: Dict[str, Any] = {}

        self._compute_all()

    # ------------------------------------------------------------------ #
    #  Computation
    # ------------------------------------------------------------------ #

    def _compute_all(self):
        """Compute per-course and instructor-level aggregate metrics."""
        per_course = []

        for _, course in self.instructor_courses.iterrows():
            # Baseline for this specific course
            agg_data = aggregate_for_row(
                comparison=self.config["comparison"],
                row=course,
                json_dir=self.paths["parsed_pdf_dir"],
                csv_path=self.csv_path,
            )

            # Load parsed PDF JSON (may be None if no eval)
            pdf_json = self._load_json(course)

            # Per-course metrics dict
            cm = self._compute_course_metrics(course, pdf_json, agg_data)
            per_course.append(cm)

        self.per_course_metrics = per_course
        self.agg = self._compute_instructor_agg(per_course)

    def _load_json(self, course) -> Optional[Dict]:
        path = course_to_json_path(course)
        if not path or not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _compute_course_metrics(
        self,
        course: Mapping[str, Any],
        pdf_json: Optional[Dict],
        agg_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build per-course metric dict for one course row."""
        subject = str(course.get("Subject", "")).strip()
        catalog = str(course.get("Catalog Nbr", "")).strip()
        term = str(course.get("Term", "")).strip()
        year = str(course.get("Year", "")).strip()
        session = str(course.get("Session Code", "")).strip()
        class_nbr = str(course.get("Class Nbr", "")).strip()
        class_size = _safe_int(course.get("Class Size")) or 0
        gpa = _safe_float(course.get("GPA")) or 0.0

        # Eval data (from JSON)
        has_eval = pdf_json is not None
        avg1 = avg2 = overall = None
        resp_rate_str = "N/A"
        resp_count = 0

        if has_eval:
            info = pdf_json.get("eval_info", {})
            avg1 = _safe_float(info.get("avg1"))
            avg2 = _safe_float(info.get("avg2"))
            if avg1 is not None and avg2 is not None:
                overall = round((avg1 + avg2) / 2, 2)
            resp_rate_str = str(info.get("response_rate", "N/A"))
            resp_count = _safe_int(info.get("response_count")) or 0

        # Overall delta
        overall_delta = "N/A"
        if overall is not None:
            bl_avg1 = _safe_float(agg_data.get("avg_part1"))
            bl_avg2 = _safe_float(agg_data.get("avg_part2"))
            if bl_avg1 is not None and bl_avg2 is not None:
                bl_overall = (bl_avg1 + bl_avg2) / 2
                d = overall - bl_overall
                overall_delta = f"{d:+.2f}" if d != 0 else "0"

        # GPA delta
        gpa_delta = compute_metrics.get_gpa_delta(course, agg_data)

        # Quartiles (individual course)
        median = compute_metrics.calculate_median_grade(course) or "N/A"
        # For Q1/Q3 of individual course, replicate percentile logic
        q1 = self._percentile_grade(course, 0.75)  # Q1 = 75th from top
        q3 = self._percentile_grade(course, 0.25)  # Q3 = 25th from top

        # Quartile deltas (ordinal vs baseline)
        bl_q1 = agg_data.get("q1_grade")
        bl_median = agg_data.get("median_grade")
        bl_q3 = agg_data.get("q3_grade")

        return {
            "name": f"{subject} {catalog}",
            "term": f"{term} {year} {session}".strip(),
            "code": class_nbr,
            "size": class_size,
            "resp_rate": resp_rate_str,
            "resp_count": resp_count,
            "overall": overall,
            "overall_delta": overall_delta,
            "gpa": round(gpa, 2),
            "gpa_delta": gpa_delta,
            "q1": q1 or "N/A",
            "q1_delta": _grade_ordinal_delta(q1, bl_q1),
            "median": median,
            "median_delta": _grade_ordinal_delta(median, bl_median),
            "q3": q3 or "N/A",
            "q3_delta": _grade_ordinal_delta(q3, bl_q3),
            # Raw values for aggregation
            "avg1": avg1,
            "avg2": avg2,
            "has_eval": has_eval,
            "class_size": class_size,
            # Keep agg_data ref for grade distribution
            "agg_data": agg_data,
            "course": course,
        }

    @staticmethod
    def _percentile_grade(course: Mapping[str, Any], q: float) -> Optional[str]:
        """Find grade at percentile q (0-1) for a single course row."""
        total = 0
        for g in GRADE_COLS:
            try:
                total += int(course.get(g, 0))
            except (ValueError, TypeError):
                continue
        if total == 0:
            return None
        threshold = q * total
        cumulative = 0
        for g in GRADE_COLS:
            try:
                cumulative += int(course.get(g, 0))
            except (ValueError, TypeError):
                continue
            if cumulative >= threshold:
                return g
        return None

    def _compute_instructor_agg(self, per_course: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute instructor-level aggregate metrics from per-course data."""
        if not per_course:
            return {}

        courses_with_eval = [c for c in per_course if c["has_eval"]]
        all_courses = per_course

        # Term range
        terms = [c["term"] for c in all_courses if c["term"]]
        # Unique courses
        unique_names = set(c["name"] for c in all_courses)

        total_enrollment = sum(c["size"] for c in all_courses)
        total_sessions = len(all_courses)

        # Averages (only over courses with eval data)
        def _mean(values):
            valid = [v for v in values if v is not None]
            return round(sum(valid) / len(valid), 2) if valid else None

        avg_avg1 = _mean([c["avg1"] for c in courses_with_eval])
        avg_avg2 = _mean([c["avg2"] for c in courses_with_eval])
        avg_overall = round((avg_avg1 + avg_avg2) / 2, 2) if avg_avg1 and avg_avg2 else None
        avg_gpa = _mean([c["gpa"] for c in all_courses])

        # Response rate: average of numeric response rates
        resp_rates = []
        for c in courses_with_eval:
            rr = c["resp_rate"]
            try:
                # Parse "0.7045" or "70%" etc.
                rr_str = str(rr).replace("%", "").strip()
                rr_val = float(rr_str)
                if rr_val <= 1:
                    rr_val *= 100
                resp_rates.append(rr_val)
            except (ValueError, TypeError):
                continue
        avg_resp_rate = round(sum(resp_rates) / len(resp_rates), 0) if resp_rates else None

        # Aggregate quartiles and median from combined grade distribution
        combined_grades = {g: 0 for g in GRADE_COLS}
        for c in all_courses:
            course = c["course"]
            for g in GRADE_COLS:
                try:
                    combined_grades[g] += int(course.get(g, 0))
                except (ValueError, TypeError):
                    continue

        total_grades = sum(combined_grades.values())

        def _combined_percentile(q):
            if total_grades == 0:
                return None
            threshold = q * total_grades
            cumul = 0
            for g in GRADE_COLS:
                cumul += combined_grades[g]
                if cumul >= threshold:
                    return g
            return None

        agg_q1 = _combined_percentile(0.75)
        agg_median = _combined_percentile(0.50)
        agg_q3 = _combined_percentile(0.25)

        # Grade distribution percentages (instructor's combined)
        grade_pcts = {}
        grade_mapping = {
            "A": ["A+", "A", "A-"],
            "B": ["B+", "B", "B-"],
            "C": ["C+", "C"],
            "D": ["D"],
            "E": ["E"],
        }
        for letter, keys in grade_mapping.items():
            count = sum(combined_grades.get(k, 0) for k in keys)
            grade_pcts[letter] = count / total_grades if total_grades > 0 else 0.0

        # Compute baseline aggregates for delta computation
        # Average the per-course baselines (weighted would be better but this is simpler)
        bl_gpas = [_safe_float(c["agg_data"].get("gpa")) for c in all_courses]
        bl_gpa = _mean(bl_gpas)

        bl_avg1s = [_safe_float(c["agg_data"].get("avg_part1")) for c in courses_with_eval]
        bl_avg2s = [_safe_float(c["agg_data"].get("avg_part2")) for c in courses_with_eval]
        bl_avg1 = _mean(bl_avg1s)
        bl_avg2 = _mean(bl_avg2s)
        bl_overall = round((bl_avg1 + bl_avg2) / 2, 2) if bl_avg1 and bl_avg2 else None

        # Baseline response rate (from JSON agg data)
        # Not tracked in current agg_data, leave as N/A
        bl_resp_rate = None

        # Baseline quartiles: average the baselines (use first baseline as representative)
        # For simplicity, use the combined baseline from the largest matching set
        bl_q1 = all_courses[0]["agg_data"].get("q1_grade") if all_courses else None
        bl_median = all_courses[0]["agg_data"].get("median_grade") if all_courses else None
        bl_q3 = all_courses[0]["agg_data"].get("q3_grade") if all_courses else None

        # Baseline grade percentages (average across per-course baselines)
        bl_grade_pcts = {}
        for letter, keys in grade_mapping.items():
            pct_sum = 0.0
            count = 0
            for c in all_courses:
                gp = c["agg_data"].get("grade_percentages", {})
                pct_sum += sum(gp.get(k, 0.0) for k in keys)
                count += 1
            bl_grade_pcts[letter] = pct_sum / count if count > 0 else 0.0

        # Compute deltas
        def _num_delta(ind, bl):
            if ind is None or bl is None:
                return "N/A"
            d = ind - bl
            return f"{d:+.2f}" if d != 0 else "0"

        # Baseline text from comparison config
        baseline_text = self._build_baseline_text()

        return {
            "instructor_name": self.instructor_row.get("Instructor", "N/A"),
            "term_range": self._build_term_range(terms),
            "total_unique_courses": len(unique_names),
            "total_sessions": total_sessions,
            "total_enrollment": total_enrollment,
            "baseline_text": baseline_text,
            # Eval aggregates
            "overall": avg_overall,
            "overall_delta": _num_delta(avg_overall, bl_overall),
            "avg1": avg_avg1,
            "avg1_delta": _num_delta(avg_avg1, bl_avg1),
            "avg2": avg_avg2,
            "avg2_delta": _num_delta(avg_avg2, bl_avg2),
            # GPA
            "gpa": avg_gpa,
            "gpa_delta": _num_delta(avg_gpa, bl_gpa),
            # Quartiles
            "q1": agg_q1 or "N/A",
            "q1_delta": _grade_ordinal_delta(agg_q1, bl_q1),
            "median": agg_median or "N/A",
            "median_delta": _grade_ordinal_delta(agg_median, bl_median),
            "q3": agg_q3 or "N/A",
            "q3_delta": _grade_ordinal_delta(agg_q3, bl_q3),
            # Response
            "resp_rate": f"{int(avg_resp_rate)}\\%" if avg_resp_rate is not None else "N/A",
            "resp_delta": "N/A",  # baseline response rate not tracked
            # Grade distribution
            "grade_pcts": grade_pcts,
            "grade_deltas": {
                letter: _delta_pct_str(grade_pcts[letter], bl_grade_pcts.get(letter, 0.0))
                for letter in grade_pcts
            },
        }

    def _build_term_range(self, terms: List[str]) -> str:
        """Build 'Fall 2022 -- Fall 2023' style range string."""
        if not terms:
            return "N/A"
        if len(terms) == 1:
            return terms[0]
        # Sort by year then term
        def _sort_key(t):
            parts = t.split()
            year = 0
            for p in parts:
                try:
                    year = int(p)
                    break
                except ValueError:
                    continue
            term_order = {"Spring": 0, "Spr": 0, "Summer": 1, "Sum": 1, "Fall": 2}
            t_ord = term_order.get(parts[0], 1) if parts else 1
            return (year, t_ord)

        sorted_terms = sorted(terms, key=_sort_key)
        return f"{sorted_terms[0]} -- {sorted_terms[-1]}"

    def _build_baseline_text(self) -> str:
        """Build baseline description from comparison config."""
        comp = self.config.get("comparison", {})
        parts = []

        match_subject = _is_true(comp.get("match_subject"))
        match_catalog = str(comp.get("match_catalog_number", "false")).lower()
        match_term = _is_true(comp.get("match_term"))
        match_year = _is_true(comp.get("match_year"))

        if match_subject:
            parts.append("Same Subject")
        if match_catalog == "true":
            parts.append("Same Catalog")
        elif match_catalog == "hundred":
            parts.append("Same Hundred-Level")
        if match_term:
            parts.append("Same Term")
        if match_year:
            parts.append("Same Year")

        if parts:
            return f"Per-Course Baselines ({', '.join(parts)})"
        return "All Available Courses"

    # ------------------------------------------------------------------ #
    #  Document generation
    # ------------------------------------------------------------------ #

    def doc_setup(self) -> Document:
        self.doc = Document(documentclass="article", document_options=["11pt"])
        self._add_packages()
        self._add_preamble()
        self._build_body()
        return self.doc

    def _add_packages(self):
        pkgs = [
            ("geometry", ["margin=0.5in"]),
            ("fontenc", ["T1"]),
            ("inputenc", ["utf8"]),
            ("textcomp", None),
            ("lastpage", None),
            ("xcolor", ["table"]),
            ("graphicx", None),
            ("tabularx", None),
            ("booktabs", None),
            ("colortbl", None),
            ("multirow", None),
            ("array", None),
            ("xstring", None),
            ("calc", None),
            ("ragged2e", None),
            ("amsmath", None),
            ("etoolbox", None),
        ]
        for pkg, opts in pkgs:
            self.doc.packages.append(Package(pkg, options=opts))

    def _add_preamble(self):
        p = self.doc.preamble

        # Colors
        p.append(NoEscape(instructor_consolidated_tex.get_color_definitions()))

        # Instructor-level commands
        self._add_instructor_commands()

        # Per-course commands
        self._add_per_course_commands()

        # LLM summary placeholder
        p.append(Command("newcommand", [
            NoEscape(r"\LLMInstructorSummary"),
            NoEscape("AI instructor summary placeholder — not yet implemented."),
        ]))

        # Helper commands (autoD, spark, rules, courserow macro)
        boxplot = self.boxplot_path.replace("\\", "/") if self.boxplot_path else "boxplot.png"
        p.append(NoEscape(instructor_consolidated_tex.get_helper_commands(boxplot)))

        # Page style
        p.append(Command("pagestyle", "empty"))

    def _add_instructor_commands(self):
        p = self.doc.preamble
        agg = self.agg

        def cmd(name, val):
            p.append(Command("newcommand", [NoEscape(rf"\{name}"), NoEscape(str(val))]))

        cmd("Instructor", agg.get("instructor_name", "N/A"))
        cmd("TermRange", agg.get("term_range", "N/A"))
        cmd("TotalUniqueCourses", agg.get("total_unique_courses", 0))
        cmd("TotalSessions", agg.get("total_sessions", 0))
        cmd("TotalEnrollment", agg.get("total_enrollment", 0))
        cmd("BaselineText", agg.get("baseline_text", "All Available Courses"))

        # Eval KPIs
        cmd("AggOverall", agg["overall"] if agg.get("overall") is not None else "N/A")
        cmd("AggOverallDelta", agg.get("overall_delta", "N/A"))
        cmd("AggPone", agg["avg1"] if agg.get("avg1") is not None else "N/A")
        cmd("AggPoneDelta", agg.get("avg1_delta", "N/A"))
        cmd("AggPtwo", agg["avg2"] if agg.get("avg2") is not None else "N/A")
        cmd("AggPtwoDelta", agg.get("avg2_delta", "N/A"))

        # GPA
        cmd("AggGPA", agg["gpa"] if agg.get("gpa") is not None else "N/A")
        cmd("AggGPADelta", agg.get("gpa_delta", "N/A"))

        # Quartiles
        cmd("AggQone", agg.get("q1", "N/A"))
        cmd("AggQoneDelta", agg.get("q1_delta", "0"))
        cmd("AggMedianGrade", agg.get("median", "N/A"))
        cmd("AggMedianDelta", agg.get("median_delta", "0"))
        cmd("AggQthree", agg.get("q3", "N/A"))
        cmd("AggQthreeDelta", agg.get("q3_delta", "0"))

        # Response rate
        cmd("AggResponseRate", agg.get("resp_rate", "N/A"))
        cmd("AggResponseDelta", agg.get("resp_delta", "N/A"))

        # Grade distribution
        grade_pcts = agg.get("grade_pcts", {})
        grade_deltas = agg.get("grade_deltas", {})
        for letter in ["A", "B", "C", "D", "E"]:
            pct = grade_pcts.get(letter, 0.0)
            cmd(f"AggGrade{letter}Pct", f"{pct * 100:.0f}\\%")
            cmd(f"AggGrade{letter}Delta", grade_deltas.get(letter, "0\\%"))

    def _add_per_course_commands(self):
        p = self.doc.preamble

        for i, cm in enumerate(self.per_course_metrics):
            prefix = self.PREFIXES[i]

            def cmd(suffix, val):
                p.append(Command("newcommand", [
                    NoEscape(rf"\Course{prefix}{suffix}"),
                    NoEscape(str(val)),
                ]))

            cmd("Name", cm["name"])
            cmd("Term", cm["term"])
            cmd("Code", cm["code"])
            cmd("Size", cm["size"])

            # Response rate — format for display
            rr = cm["resp_rate"]
            try:
                rr_str = str(rr).replace("%", "").strip()
                rr_val = float(rr_str)
                if rr_val <= 1:
                    rr_val *= 100
                cmd("RespRate", f"{int(rr_val)}\\%")
            except (ValueError, TypeError):
                cmd("RespRate", "N/A")

            cmd("Overall", cm["overall"] if cm["overall"] is not None else "N/A")
            cmd("OverallDelta", cm["overall_delta"])
            cmd("GPA", cm["gpa"])
            cmd("GPADelta", cm["gpa_delta"])
            cmd("Qone", cm["q1"])
            cmd("QoneDelta", cm["q1_delta"])
            cmd("Median", cm["median"])
            cmd("MedianDelta", cm["median_delta"])
            cmd("Qthree", cm["q3"])
            cmd("QthreeDelta", cm["q3_delta"])

    def _build_body(self):
        d = self.doc
        d.append(NoEscape(r"\normalsize"))

        # Title
        d.append(NoEscape(instructor_consolidated_tex.get_title_section()))

        # Aggregate KPI dashboard
        d.append(NoEscape(instructor_consolidated_tex.get_aggregate_kpi_table()))

        # Grade distribution + AI summary
        d.append(NoEscape(instructor_consolidated_tex.get_grade_and_summary_section()))

        # Per-course table
        d.append(NoEscape(instructor_consolidated_tex.get_per_course_table_header()))
        for i in range(len(self.per_course_metrics)):
            prefix = self.PREFIXES[i]
            d.append(NoEscape(rf"\courserow{{{prefix}}}%"))
        d.append(NoEscape(instructor_consolidated_tex.get_per_course_table_footer()))
