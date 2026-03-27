import json
import os
import subprocess
import sys
from typing import Any, Mapping, Optional

from pylatex import(
    Command,
    Document,
    NoEscape,
)
from src.scorecard_doc import _ScorecardDoc
from src.consolidated_doc import _ConsolidatedDoc
from src.instructor_consolidated_doc import _InstructorConsolidatedDoc
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


def _compile_pdf(doc, output_path, compiler='pdflatex', clean_tex=True, passes=2):
    """
    Generate .tex and compile to PDF with multiple passes.

    Runs pdflatex multiple times to resolve cross-references (longtable column
    widths, lastpage counters, etc.). Checks for PDF existence rather than
    relying on the exit code, since pdflatex returns non-zero for warnings
    like 'Misplaced \\noalign' even when the PDF is produced successfully.

    Args:
        doc: pylatex Document instance
        output_path: output filepath without extension
        compiler: LaTeX compiler to use
        clean_tex: remove .tex after compilation
        passes: number of pdflatex passes (2 resolves most cross-refs)
    """
    # Strip .pdf extension if caller accidentally included it
    if output_path.endswith('.pdf'):
        output_path = output_path[:-4]

    # Generate .tex file
    doc.generate_tex(output_path)

    tex_file = output_path + '.tex'
    pdf_file = output_path + '.pdf'
    work_dir = os.path.dirname(os.path.abspath(tex_file))
    tex_basename = os.path.basename(tex_file)

    # Run pdflatex N times for cross-references
    last_result = None
    for pass_num in range(1, passes + 1):
        last_result = subprocess.run(
            [compiler, '--interaction=nonstopmode', tex_basename],
            cwd=work_dir,
            capture_output=True,
            timeout=120,
        )

    # Verify PDF was produced (don't rely on exit code — pdflatex returns
    # non-zero for non-fatal warnings like rowcolor/noalign conflicts)
    if not os.path.exists(pdf_file):
        stderr = last_result.stderr.decode('utf-8', errors='replace') if last_result else 'unknown'
        raise RuntimeError(
            f"pdflatex failed to produce {pdf_file}\n"
            f"Compiler stderr:\n{stderr}"
        )

    # Clean auxiliary files
    for ext in ['.aux', '.log', '.out', '.fls', '.fdb_latexmk']:
        aux_file = output_path + ext
        if os.path.exists(aux_file):
            try:
                os.remove(aux_file)
            except OSError:
                pass

    if clean_tex and os.path.exists(tex_file):
        try:
            os.remove(tex_file)
        except OSError:
            pass

    return pdf_file


def assemble_scorecard(
        course: Mapping[str, Any],
        config,
        csv_path,
        short:bool = False,
        newcommand:bool = True,
        consolidated:bool = True,
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

    # Compile to PDF — pass path WITHOUT .pdf extension (_compile_pdf appends it)
    full_scorecard_output_path = os.path.join(scorecard_output_path, latex_doc.output_filename)
    _compile_pdf(latex_doc.doc, full_scorecard_output_path, compiler='pdflatex', clean_tex=True)
    print(f"📝✅ Saved PDF Scorecard to {full_scorecard_output_path}.pdf")

def assemble_instructor_scorecard(
    instructor: Mapping[str, Any],
    config,
    csv_path,
):
    """
    Build a single-page instructor-level consolidated scorecard PDF.

    Uses the tabular layout from _InstructorConsolidatedDoc which shows
    aggregate KPIs, grade distribution, AI summary placeholder, and a
    per-course comparison table with deltas against config-driven baselines.
    """
    paths = config['paths']
    tex_output_path = paths['tex_dir']
    scorecard_output_path = paths['scorecard_dir']

    # Image output directories (parallel to GPA_trend for boxplots)
    temp_dir = paths.get("temp_dir", "temporary_files")
    gpa_trend_dir = os.path.join(temp_dir, "GPA_trend")
    histogram_dir = os.path.join(temp_dir, "instructor_histograms")
    overlay_dir = os.path.join(temp_dir, "instructor_overlays")

    # Get all courses for this instructor (require JSON for eval data)
    instructor_courses = get_courses_by_instructor(instructor, csv_path, require_json=True)

    if instructor_courses.empty:
        print("No courses with evaluations found for instructor; nothing to generate.")
        return

    # Boxplot placeholder path
    boxplot_path = os.path.abspath(
        os.path.join(paths.get('resources_dir', 'resources'), 'boxplot.png')
    )
    if isinstance(boxplot_path, str):
        boxplot_path = boxplot_path.replace('\\', '/')

    # Build the consolidated instructor doc
    doc_builder = _InstructorConsolidatedDoc(
        instructor_row=instructor,
        instructor_courses=instructor_courses,
        config=config,
        csv_path=csv_path,
        boxplot_path=boxplot_path,
    )

    doc = doc_builder.doc_setup()

    # Generate per-course boxplot sparklines into GPA_trend folder
    doc_builder.generate_boxplots(gpa_trend_dir)

    # Generate per-course grade histograms into instructor_histograms folder
    doc_builder.generate_histograms(histogram_dir)

    # Generate per-course-group history overlay graphs into instructor_overlays folder
    doc_builder.generate_course_history_overlays(overlay_dir)

    # Output filename (no .pdf extension — _compile_pdf appends it)
    output_filename = f"{instructor.get('Instructor', 'Unknown')}_Overview"
    output_filename = output_filename.replace(",", "").replace(" ", "_")

    # Save .tex copy to tex dir
    full_output_path = os.path.join(tex_output_path, output_filename)
    doc.generate_tex(full_output_path)
    print(f"  ✅ Saved instructor LaTeX to {full_output_path}")

    # Compile to PDF — pass path WITHOUT .pdf extension (_compile_pdf appends it)
    full_scorecard_output_path = os.path.join(scorecard_output_path, output_filename)
    _compile_pdf(doc, full_scorecard_output_path, compiler='pdflatex', clean_tex=True)
    print(f"📝✅ Saved instructor Scorecard to {full_scorecard_output_path}.pdf")