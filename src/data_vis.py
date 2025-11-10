import os
import json
import math
import re
from typing import Any, Dict, Mapping, Optional
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from src import data_handler

_GRADE_ORDER = ["E", "D", "C", "C+", "B-", "B", "B+", "A-", "A", "A+"]

def generate_data_visualization(
        config, 
        selected_scorecard_courses, 
        selected_scorecard_instructors,
        csv_path
):
    print ("  🏫 Generating Course Data Visualizations")
    for index, course in selected_scorecard_courses.iterrows():
        generate_course_grade_histogram(config, course, csv_path)
        generate_course_history_graph(config, course, csv_path)
    
    print ("  👨‍🏫 Generating Instructor Data Visualizations")
    for index, instructor in selected_scorecard_instructors.iterrows():
        generate_instructor_course_gpa_graph(config, instructor, csv_path)

def _slug(value: Any, fallback: str = "NA") -> str:
    # Turn text into filename safe stuff
    if value is None:
        return fallback
    s = str(value).strip()
    if not s:
        return fallback
    s = s.replace(" ", "_")
    s = re.sub(r"[^A-Za-z0-9_]+", "", s)
    return s or fallback

def _get_numeric(course: Mapping[str, Any], key: str) -> float:
    # get numeric grade count from course row
    raw = course.get(key)
    if raw is None or raw == "":
        return 0.0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0

def generate_course_grade_histogram(
    config: Mapping[str, Any],
    course: Mapping[str, Any],
    csv_path,
):
    """
    Render a grade histogram PNG for a single course

    Outputs
    {department}_{course}_{professor}_{term}_{year}_{course_number}.png
    into grade_histogram_dir.
    """
    # get paths and config options ####################################################
    paths = config.get("paths", {}) or config.get("PATHS", {})

    grade_hist_dir = (
        config.get("grade_histogram_dir")
        or paths.get("grade_histogram_dir")
        or paths.get("grade_hist_dir")
    )
    if not grade_hist_dir:
        raise KeyError("grade_histogram_dir not found in config or config['paths'].")

    json_dir = paths.get("parsed_pdf_dir") or paths.get("json_dir")
    if not json_dir:
        raise KeyError("parsed_pdf_dir/json_dir not found in config['paths'].")

    comparison = (
        config.get("comparison")
        or config.get("baseline_comparison")
        or {}
    )

    plot_cfg = (
        config.get("plots", {})
        .get("grade_histogram", {})
        or config.get("grade_histogram", {})
        or {}
    )

    # figure size default 760 x 360
    dpi = int(plot_cfg.get("dpi", 100))
    width_px = int(plot_cfg.get("width_px", 760))
    height_px = int(plot_cfg.get("height_px", 360))
    fig_width = width_px / dpi
    fig_height = height_px / dpi

    course_color = plot_cfg.get("course_color", "#cc6600")
    baseline_color = plot_cfg.get("baseline_color", "#000000")
    baseline_linewidth = float(plot_cfg.get("baseline_linewidth", 2.0))

    bar_width = float(plot_cfg.get("bar_width", 1.0))

    os.makedirs(grade_hist_dir, exist_ok=True)

    # get baseline from data_handler ####################################################
    if isinstance(csv_path, (list, tuple)):
        csv_path_for_baseline = csv_path[0]
    else:
        csv_path_for_baseline = csv_path

    baseline = data_handler.aggregate_for_row(
        comparison=comparison,
        row=course,
        json_dir=json_dir,
        csv_path=csv_path_for_baseline,
    )
    baseline_percentages = baseline.get("grade_percentages", {}) or {}

    # Legend label text
    baseline_label_source = (
        baseline.get("baseline")
        or baseline.get("aggregate_name")
        or "baseline"
    )
    baseline_label = f"Average for {baseline_label_source}"

    # course grade counts ####################################################
    course_counts = [_get_numeric(course, g) for g in _GRADE_ORDER]
    total_students = sum(course_counts)

    if total_students <= 0:
        total_students = float(baseline.get("total_students", 0) or 0)
        if total_students <= 0:
            total_students = 1.0

    # scale baseline to total students
    baseline_values = [
        float(baseline_percentages.get(g, 0.0)) * total_students
        for g in _GRADE_ORDER
    ]

    # build filename ####################################################
    department = _slug(course.get("Subject"))
    course_code = _slug(course.get("Catalog Nbr"))
    professor = _slug(course.get("Instructor Last"))
    term = _slug(course.get("Term"))
    year = _slug(course.get("Year"))

    course_number = _slug(
        course.get("Course Nbr")
        or course.get("Class Nbr")
        or course.get("Section")
        or course.get("course_number")
    )

    filename = f"{department}_{course_code}_{professor}_{term}_{year}_{course_number}.png"
    out_path = os.path.join(grade_hist_dir, filename)

    # plotting ####################################################
    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=dpi)

    fig.patch.set_facecolor("#fdfdfd")
    ax.set_facecolor("#fdfdfd")

    x = np.arange(len(_GRADE_ORDER))

    # This gradient is vibe coded. If this causes issues go tell Joey to remove it
    # Course bars with vertical gradient, connected (no gaps)
    # Top color stays course_color (#1f4e79), bottom is #8fa6bc (configurable)
    bottom_color = plot_cfg.get("course_bottom_color", "#ffa64c")
    top_color = course_color  # "#1f4e79"

    # Create bars with no solid facecolor
    bars = ax.bar(
        x,
        course_counts,
        width=bar_width,
        color="none",
        align="center",
        edgecolor="none",
    )

    # Vertical gradient image 0..1, mapped bottom -> top color
    grad = np.linspace(0.0, 1.0, 256).reshape(256, 1)
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "course_grad", [bottom_color, top_color]
    )

    for bar in bars:
        height = bar.get_height()
        if height <= 0:
            continue

        x_left = bar.get_x()
        x_right = x_left + bar.get_width()
        y_bottom = 0.0
        y_top = height

        ax.imshow(
            grad,
            extent=(x_left, x_right, y_bottom, y_top),
            origin="lower",
            aspect="auto",
            cmap=cmap,
            interpolation="bicubic",
            zorder=bar.get_zorder(),  # bars under the baseline outline
        )

    # baseline histogram outline using a step function
    if baseline_values:
        edges = np.arange(len(_GRADE_ORDER) + 1) - 0.5
        # For where='post': segment [edges[i], edges[i+1]] gets y[i]
        y = np.concatenate(
            [np.asarray(baseline_values, dtype=float), [baseline_values[-1]]]
        )
        ax.step(
            edges,
            y,
            where="post",
            color=baseline_color,
            linewidth=baseline_linewidth,
            label=baseline_label,
        )

    # legend
    ax.legend(loc="upper left", fontsize=8, frameon=False)

    # only grade labels at the bottom
    ax.set_xticks(x)
    ax.set_xticklabels(_GRADE_ORDER)

    # remove everything else textual
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_title("")
    ax.tick_params(axis="y", which="both", left=False, labelleft=False)

    # clean spines
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)

    # no x margin
    ax.margins(x=0.0)

    fig.tight_layout(pad=0.5)
    fig.savefig(out_path, facecolor="#fdfdfd")
    plt.close(fig)

    print(f"    ✅ Generated course grade histogram: {out_path}") 

    return out_path

def generate_course_history_graph(
        config, 
        course: Mapping[str, Any],
        csv_path
):
    
    subject = str(course.get("Subject", "")).strip()
    catalog = str(course.get("Catalog Nbr", "")).strip()
    term = str(course.get("Term", "")).strip()
    year = str(course.get("Year", "")).strip()
    instructor = str(course.get("Instructor", "")).strip()

    print(f"    🟧 Placeholder - Generate course history graph for {subject} {catalog}, {term} {year} ({instructor})") 
    
    #TODO

def generate_instructor_course_gpa_graph(
        config, 
        instructor: Mapping[str, Any],
        csv_path
):
    
    name = str(instructor.get("Instructor", "")).strip()

    print(f"    🟧 Placeholder - Generate instructor course GPA graph for {name}") 
    
    #TODO