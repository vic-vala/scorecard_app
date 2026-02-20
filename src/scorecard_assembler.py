import json
import os
import sys
from typing import Any, Mapping, Optional

from pylatex import(
    Command,
    Document,
    NoEscape,
)
from src.scorecard_doc import _ScorecardDoc
from src.consolidated_doc import _ConsolidatedDoc
from src.utils import course_to_json_path, course_to_stem, course_to_output_filename, instructor_to_stem
from src.data_handler import aggregate_for_row, get_courses_by_instructor

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
        short:bool = False,
        newcommand:bool = True,
        consolidated:bool = False,
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
    histogram_full_path = os.path.abspath(os.path.join(histogram_dir, f"{histrogram_name}.png"))

    # Convert backslashes to forward slashes for LaTeX compatibility on Windows
    # LaTeX treats backslashes as escape characters, so we need to use forward slashes
    if isinstance(histogram_full_path, str):
        histogram_full_path = histogram_full_path.replace('\\', '/')

    # Load the pdf json representation
    pdf_json = load_pdf_json(course_to_json_path(course))

    # Generate output filename with instructor first name (Used to differentiate instructors with same last name)
    output_filename = course_to_output_filename(course)

    # Generate the latex doc
    if consolidated:
        boxplot_path = os.path.abspath(os.path.join(paths.get('resources_dir', 'resources'), 'boxplot.png'))
        if isinstance(boxplot_path, str):
            boxplot_path = boxplot_path.replace('\\', '/')
        latex_doc = _ConsolidatedDoc(
            csv_row=course,
            pdf_json=pdf_json,
            grade_hist=histogram_full_path,
            output_filename=output_filename,
            agg_data=agg_data,
            config=config,
            newcommand=newcommand,
            boxplot_path=boxplot_path,
        )
    else:
        latex_doc = _ScorecardDoc(
            csv_row=course,
            pdf_json=pdf_json,
            grade_hist=histogram_full_path,
            output_filename=output_filename,
            agg_data=agg_data,
            config=config,
            short=short,
            newcommand=newcommand,
        )

    latex_doc.doc_setup()

    # Save the latex doc to the temp folder in its subdirectory
    full_output_path = os.path.join(tex_output_path, latex_doc.output_filename)
    latex_doc.doc.generate_tex(full_output_path)
    print(f"  ✅ Saved LaTeX to {full_output_path}")

    # Save the latex as a pdf now
    pdf_filename = f"{latex_doc.output_filename}.pdf"
    full_scorecard_output_path = os.path.join(scorecard_output_path, pdf_filename)
    latex_doc.doc.generate_pdf(full_scorecard_output_path, clean_tex=True, compiler='pdflatex')
    print(f"📝✅ Saved PDF Scorecard to {full_scorecard_output_path}")

def assemble_instructor_scorecard(
    instructor: Mapping[str, Any],
    config,
    csv_path,
):
    """
    Build a single LaTeX file for an instructor, containing one short
    course card per course.
    """

    paths = config['paths']
    histogram_dir = paths['grade_histogram_dir']
    tex_output_path = paths['tex_dir']
    scorecard_output_path = paths['scorecard_dir']

    # Get all courses for this instructor
    instructor_courses = get_courses_by_instructor(instructor, csv_path, True)

    if instructor_courses.empty:
        print("No courses found for instructor; nothing to generate.")
        return

    master_doc: Optional[Document] = None
    is_first = True

    for _, course in instructor_courses.iterrows():
        # aggregate data for this specific course
        agg_data = aggregate_for_row(
            comparison=config['comparison'],
            row=course,
            json_dir=paths['parsed_pdf_dir'],
            csv_path=csv_path,
        )

        histrogram_name = course_to_stem(course)
        histogram_full_path = os.path.join(histogram_dir, f"{histrogram_name}.png")

        pdf_json = load_pdf_json(course_to_json_path(course))

        scorecard = _ScorecardDoc(
            csv_row=course,
            pdf_json=pdf_json,
            grade_hist=histogram_full_path,
            output_filename="placeholder",  # not used here for per-course files
            agg_data=agg_data,
            config=config,
            short=True,
            newcommand=is_first,
        )

        if is_first:
            master_doc = Document(documentclass='article', document_options=['11pt'])
            scorecard.doc = master_doc

            scorecard._add_packages()
            scorecard._add_preamble()

            master_doc.append(NoEscape(r'{\LARGE\bfseries\textcolor{accent}{\Instructor} \\}'))

            scorecard.add_short_section()

            is_first = False
        else:
            if master_doc is None:
                raise RuntimeError("master_doc was not initialized for instructor scorecard")

            scorecard.doc = master_doc

            scorecard.write_course_cmds_to_preamble = False
            scorecard.newcommand = False

            scorecard._add_overview_fields()
            scorecard._add_evaluation_metrics_fields()
            scorecard._add_summary_fields()
            scorecard._add_grade_distr_fields()

            scorecard.add_short_section()

    if master_doc is None:
        print("Unexpected error: master_doc was not created.")
        return

    first_course = instructor_courses.iloc[0]
    gpa_graph_dir = paths['instructor_course_gpa_graph_dir']
    gpa_graph_name = instructor_to_stem(first_course)
    gpa_graph_full_path = os.path.abspath(os.path.join(gpa_graph_dir, f"{gpa_graph_name}.png"))

    # Convert backslashes to forward slashes for LaTeX compatibility on Windows
    if isinstance(gpa_graph_full_path, str):
        gpa_graph_full_path = gpa_graph_full_path.replace('\\', '/')

    master_doc.append(NoEscape(
        rf'\includegraphics[width=\textwidth,height=1\textheight,keepaspectratio]{{{gpa_graph_full_path}}}'
    ))
    master_doc.append(Command('newpage'))

    output_filename = f"{instructor.get('Instructor')}_Overview"
    full_output_path = os.path.join(tex_output_path, output_filename)
    master_doc.generate_tex(full_output_path)
    print(f"  ✅ Saved instructor LaTeX to {full_output_path}")

    # Save the latex as a pdf now
    pdf_filename = f"{output_filename}.pdf"
    full_scorecard_output_path = os.path.join(scorecard_output_path, pdf_filename)
    master_doc.generate_pdf(full_scorecard_output_path, clean_tex=True, compiler='pdflatex')
    print(f"📝✅ Saved instructor Scorecard to {full_scorecard_output_path}")