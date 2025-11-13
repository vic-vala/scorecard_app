import os
import json
import math
import re
import itertools
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
        csv_path,
        selected_history_courses,
):
    """
    This function automates the creation of all data vis images
    from a list of courses, sessions, and professors

    It takes in the config and csv path as well
    """

    def _generate(df, start_msg, skip_msg, func, path):
        print(start_msg)
        if df is None or df.empty:
            print(skip_msg)
            return
        for _, item in df.iterrows():
            func(config, item, path)

    _generate(
        selected_scorecard_courses,
        "  🏫 Generating Course Data Visualizations", 
        "  ⛔ No courses selected for course data visualizations. Skipping course data visualization generation.",
        generate_course_grade_histogram,
        csv_path,
    )

    _generate(
        selected_history_courses,
        "  🕰️ Generating Course History Graphs", 
        "  ⛔ No courses selected for history graphs. Skipping course history generation.",
        generate_course_history_graph,
        csv_path,
    )

    _generate(
        selected_scorecard_instructors,
        "  👨‍🏫 Generating Instructor Data Visualizations", 
        "  ⛔ No instructors selected for instructor visualizations. Skipping instructor data visualization generation.",
        generate_instructor_course_gpa_graph,
        csv_path,
    )

def _slug(value: Any, fallback: str = "NA") -> str:
    """
    Convery an arbitrary value to a filename safe string
    - Replaces space with underscores
    - Convert to a string
    - Strip leading/trailing whitespace
    - Remove all non letter/digit/underscores
    """
    if value is None:
        return fallback
    s = str(value).strip()
    if not s:
        return fallback
    s = s.replace(" ", "_")
    s = re.sub(r"[^A-Za-z0-9_]+", "", s)
    return s or fallback

def _get_numeric(course: Mapping[str, Any], key: str) -> float:
    """
    Go from a course (row in the CSV) and a key to a float safely
    """
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
        config: Mapping[str, Any],
        course: Mapping[str, Any],
        csv_path,
):
    """
    (This function (and the documentation) is pretty vibe coded. If any changes are needed to this, just look at 
    matplotlib docs and try to look for the specific thing you need, since this is a bit messy)

    GPA-over-time history graph for a single course.

    For the given (Subject, Catalog Nbr), this plots:
      - per-instructor average GPA over time as lines with markers
      - the aggregate mean GPA per term
      - a shaded band representing ±1 standard deviation around the mean

    Output file:
      {Subject}_{Catalog Nbr}.png
    written into course_history_graph_dir.
    """
    # paths and config options #######################################################
    paths = config.get("paths", {}) or config.get("PATHS", {})

    course_hist_dir = (
        config.get("course_history_graph_dir")
        or paths.get("course_history_graph_dir")
        or paths.get("course_history_dir")
    )
    if not course_hist_dir:
        raise KeyError(
            "course_history_graph_dir not found in config or config['paths']."
        )

    os.makedirs(course_hist_dir, exist_ok=True)

    plot_cfg = (
        config.get("plots", {}).get("course_history_graph", {})
        or config.get("course_history_graph", {})
        or {}
    )

    dpi = int(plot_cfg.get("dpi", 100))
    width_px = int(plot_cfg.get("width_px", 1920))
    height_px = int(plot_cfg.get("height_px", 1080))
    fig_width = width_px / dpi
    fig_height = height_px / dpi

    mean_color = plot_cfg.get("mean_color", "#ff8800")
    band_color = plot_cfg.get("std_fill_color", "#cccccc")
    band_alpha = float(plot_cfg.get("std_alpha", 0.3))

    mean_linewidth = float(plot_cfg.get("mean_linewidth", 4.0))
    mean_markersize = float(plot_cfg.get("mean_marker_size", 7.0))

    # per-instructor line and marker sizes
    instructor_markersize = float(
        plot_cfg.get("instructor_marker_size", plot_cfg.get("marker_size", 7.0))
    )
    instructor_linewidth = float(
        plot_cfg.get("instructor_linewidth", plot_cfg.get("marker_edge_width", 2.0))
    )

    instructor_connect_points = str(
        plot_cfg.get("course_history_connect_points", "true")
    ).lower() == "true"

    # Marker / linestyle options for instructors
    marker_options = plot_cfg.get(
        "instructor_markers",
        ["o", "^", "s", "D", "P", "X"],
    )
    linestyle_options = plot_cfg.get(
        "instructor_linestyles",
        ["-", "--", "-.", ":"],
    )

    # Normalize csv_path ###########################################################
    if isinstance(csv_path, (list, tuple)):
        if not csv_path:
            raise ValueError("csv_path list/tuple is empty.")
        csv_path_use = csv_path[0]
    else:
        csv_path_use = csv_path

    # Load CSV and use precomputed GPA ###########################################
    df = pd.read_csv(csv_path_use)
    df["Average_GPA"] = pd.to_numeric(df["GPA"], errors="coerce")

    # Filter for the requested course #############################################
    subject = str(course.get("Subject") or "").strip()
    catalog = str(course.get("Catalog Nbr") or "").strip()

    if not subject or not catalog:
        print("    ⚠️ Skipping course history graph for row with missing Subject/Catalog Nbr")
        return None

    mask = (
        df["Subject"].astype(str).str.strip().eq(subject)
        & df["Catalog Nbr"].astype(str).str.strip().eq(catalog)
    )
    df_course = df[mask].copy()

    if df_course.empty:
        print(f"    ⚠️ No rows found for course {subject} {catalog} in CSV. Skipping history graph.")
        return None

    # Decode semester from STRM or (Term, Year) ###################################
    def _decode_strm(val):
        try:
            strm = int(val)
        except (TypeError, ValueError):
            return None
        year_code = strm // 10
        term_code = strm % 10
        year = 1800 + year_code
        term_map = {1: "Spring", 4: "Summer", 7: "Fall"}
        term = term_map.get(term_code)
        if term is None:
            return None
        return f"{term} {year}"

    if "Strm" in df_course.columns:
        df_course["Semester"] = df_course["Strm"].map(_decode_strm)
    else:
        df_course["Semester"] = None

    # Fallback to explicit term/year labels
    if df_course["Semester"].isna().all():
        if "Term" in df_course.columns and "Year" in df_course.columns:
            def _term_year(row):
                term = str(row.get("Term") or "").strip()
                year = str(row.get("Year") or "").strip()
                if not term or not year:
                    return None
                return f"{term} {year}"
            df_course["Semester"] = df_course.apply(_term_year, axis=1)

    df_course = df_course[df_course["Semester"].notna()].copy()
    if df_course.empty:
        print(f"    ⚠️ No semester information for course {subject} {catalog}. Skipping history graph.")
        return None

    # normalise instructor names
    if "Instructor" in df_course.columns:
        df_course["Instructor"] = (
            df_course["Instructor"].fillna("(no data)").astype(str).str.strip()
        )
    else:
        df_course["Instructor"] = "(no data)"

    # drop rows without GPA
    df_course = df_course[df_course["Average_GPA"].notna()].copy()
    if df_course.empty:
        print(f"    ⚠️ No GPA data for course {subject} {catalog}. Skipping history graph.")
        return None

    # determine semester order ###################################################
    term_order = {"Spring": 1, "Summer": 2, "Fall": 3}

    def _semester_key(sem_str: str):
        try:
            term, year = sem_str.split()
            year_int = int(year)
        except Exception:
            return (9999, 99)
        return (year_int, term_order.get(term, 99))

    semester_order = sorted(
        df_course["Semester"].dropna().unique(),
        key=_semester_key,
    )

    # aggregate GPA by semester and instructor ###################################
    grouped = (
        df_course.groupby(["Semester", "Instructor"], as_index=False)
        .agg({"Average_GPA": "mean"})
    )

    instructors = [i for i in grouped["Instructor"].unique() if i != "(no data)"]

    stats = (
        grouped[grouped["Instructor"] != "(no data)"]
        .groupby("Semester", as_index=False)
        .agg(mean_gpa=("Average_GPA", "mean"), std_gpa=("Average_GPA", "std"))
    )

    if stats.empty:
        print(f"    ⚠️ Not enough data to compute aggregate stats for {subject} {catalog}. Skipping history graph.")
        return None

    stats["std_gpa"] = stats["std_gpa"].fillna(0.0)

    # Map semesters to numeric positions for plotting ############################
    x_positions = np.arange(len(semester_order))
    sem_to_x = {sem: idx for idx, sem in enumerate(semester_order)}

    stats["x"] = stats["Semester"].map(sem_to_x)
    stats = stats.sort_values("x")

    all_gpas = grouped["Average_GPA"].dropna()
    if all_gpas.empty:
        y_min, y_max = 0.0, 4.33
    else:
        y_min = max(0.0, float(all_gpas.min()) - 0.1)
        y_max = min(4.33, float(all_gpas.max()) + 0.1)

    # Plotting ###################################################################
    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=dpi)

    # Shaded ±1 standard deviation band (grey zone)
    upper = stats["mean_gpa"] + stats["std_gpa"]
    lower = stats["mean_gpa"] - stats["std_gpa"]

    x_vals = stats["x"].astype(float).values
    upper_vals = upper.astype(float).values
    lower_vals = lower.astype(float).values

    ax.fill_between(
        x_vals,
        lower_vals,
        upper_vals,
        color=band_color,
        alpha=band_alpha,
        label="±1 SD",
        zorder=1,
    )

    # Mean GPA line (thick)
    ax.plot(
        x_vals,
        stats["mean_gpa"],
        color=mean_color,
        linewidth=mean_linewidth,
        marker="D",
        markersize=mean_markersize,
        label="Average GPA",
        zorder=3,
    )

    # Instructor lines with distinct color + marker + linestyle combinations
    base_colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    color_cycle = itertools.cycle(base_colors)
    style_cycle = itertools.cycle(
        [(m, ls) for m in marker_options for ls in linestyle_options]
    )

    instructor_styles = {}
    for inst in instructors:
        marker, linestyle = next(style_cycle)
        color = next(color_cycle)
        instructor_styles[inst] = (marker, linestyle, color)

    for inst in instructors:
        sub = grouped[grouped["Instructor"] == inst].copy()
        if sub.empty:
            continue
        # Ensure chronological order
        sub["x"] = sub["Semester"].map(sem_to_x)
        sub = sub.sort_values("x")

        xs = sub["x"].astype(float).values
        ys = sub["Average_GPA"].astype(float).values

        marker, linestyle, color = instructor_styles[inst]
        
        line_style = linestyle if instructor_connect_points else "None"

        ax.plot(
            xs,
            ys,
            marker=marker,
            linestyle=line_style,
            color=color,
            markersize=instructor_markersize,
            linewidth=instructor_linewidth,
            label=inst,
            zorder=4,
        )

    # Axes and layout ###########################################################
    ax.set_xticks(x_positions)
    ax.set_xticklabels(semester_order, rotation=45, ha="right")
    ax.set_ylim(y_min, y_max)
    ax.set_xlim(-0.5, len(semester_order) - 0.5)
    ax.set_ylabel("Average GPA")
    ax.set_xlabel("Semester")

    title_text = f"{subject} {catalog} Average GPA Over Time"
    ax.set_title(title_text)

    # Legend below the entire graph
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ncol = min(4, len(labels))

        # First lay out the axes, leaving room at the bottom
        fig.tight_layout(rect=(0.0, 0.18, 1.0, 1.0))

        # Then put the legend inside the reserved bottom band
        fig.legend(
            handles,
            labels,
            loc="lower center",           # bottom of legend
            bbox_to_anchor=(0.5, 0.02),   # slightly above figure bottom
            ncol=ncol,
            frameon=False,
            fontsize=8,
        )
    else:
        fig.tight_layout()

    # Save figure ###############################################################
    subject_slug = _slug(subject)
    catalog_slug = _slug(catalog)
    filename = f"{subject_slug}_{catalog_slug}.png"
    out_path = os.path.join(course_hist_dir, filename)

    fig.savefig(out_path)
    plt.close(fig)

    print(f"    ✅ Generated course history graph: {out_path}")
    
    return out_path

def generate_instructor_course_gpa_graph(
        config: Mapping[str, Any],
        instructor: Mapping[str, Any],
        csv_path,
):
    """
    GPA difference versus aggregate baseline graph for each course for a given professor

    X axis = Course sessions, sorted by Strm (functionally, by time)
    Y axis = delta against aggregate

    Output file:
      {Instructor Last}_{Instructor First}.png
    written into instructor_course_gpa_graph_dir.

    TODO: Split this into multiple pages
    Expect this output file to end in _1, _2, etc. later, when this is done
    Talk to Joey before integrating these files into LaTeX!!!
    """
    # paths and config options ###################################################
    paths = config.get("paths", {}) or config.get("PATHS", {})

    instr_dir = (
        config.get("instructor_course_gpa_graph_dir")
        or paths.get("instructor_course_gpa_graph_dir")
        or paths.get("instructor_course_gpa_dir")
    )
    if not instr_dir:
        raise KeyError(
            "instructor_course_gpa_graph_dir not found in config or config['paths']."
        )
    os.makedirs(instr_dir, exist_ok=True)

    json_dir = paths.get("parsed_pdf_dir") or paths.get("json_dir")
    if not json_dir:
        raise KeyError("parsed_pdf_dir/json_dir not found in config['paths'].")

    comparison = (
        config.get("comparison")
        or config.get("baseline_comparison")
        or {}
    )

    plot_cfg = (
        config.get("plots", {}).get("instructor_course_gpa_graph", {})
        or config.get("instructor_course_gpa_graph", {})
        or {}
    )

    # try to fit into typical 8.5x11 inches paper
    dpi = int(plot_cfg.get("dpi", 100))
    width_px = int(plot_cfg.get("width_px", 850))
    height_px = int(plot_cfg.get("height_px", 1100))
    fig_width = width_px / dpi
    fig_height = height_px / dpi

    # colors
    positive_color = plot_cfg.get("positive_color", "#51A058")   # above baseline
    negative_color = plot_cfg.get("negative_color", "#d7263d")   # below baseline

    zero_line_color = plot_cfg.get("zero_line_color", "#000000")
    zero_linewidth = float(plot_cfg.get("zero_linewidth", 1.5))
    bar_height = float(plot_cfg.get("bar_height", 0.8))
    x_margin = float(plot_cfg.get("x_margin", 0.05))

    # normalize csv_path #########################################################
    if isinstance(csv_path, (list, tuple)):
        if not csv_path:
            print("    ⚠️ csv_path list/tuple is empty. Skipping instructor GPA graph.")
            return None
        csv_path_use = csv_path[0]
    else:
        csv_path_use = csv_path

    # load CSV and filter to this instructor #####################################
    df = pd.read_csv(csv_path_use)

    inst_name = str(instructor.get("Instructor", "")).strip()
    inst_first = str(instructor.get("Instructor First", "")).strip()
    inst_middle = str(instructor.get("Instructor Middle", "")).strip()
    inst_last = str(instructor.get("Instructor Last", "")).strip()

    # normalize instructor columns in CSV
    for col in ["Instructor", "Instructor First", "Instructor Middle", "Instructor Last"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()
        else:
            df[col] = ""

    mask = (
        df["Instructor"].eq(inst_name)
        & df["Instructor First"].eq(inst_first)
        & df["Instructor Middle"].eq(inst_middle)
        & df["Instructor Last"].eq(inst_last)
    )
    df_inst = df[mask].copy()

    if df_inst.empty:
        print(f"    ⚠️ No rows found in CSV for instructor {inst_name}. Skipping GPA graph.")
        return None

    # sort by Strm
    if "Strm" in df_inst.columns:
        df_inst["_Strm_int"] = pd.to_numeric(df_inst["Strm"], errors="coerce")
        df_inst = df_inst.sort_values("_Strm_int", ascending=False, kind="mergesort")
        df_inst = df_inst.drop(columns=["_Strm_int"])
    else:
        print("    ⚠️ Column 'Strm' not found. Using original row order for instructor courses.")

    # compute per-session gpa deltas vs baseline ##########################################
    labels = []
    diffs = []

    for _, row in df_inst.iterrows():
        # actual GPA for this section
        try:
            actual_gpa = float(row.get("GPA"))
        except (TypeError, ValueError):
            continue
        if math.isnan(actual_gpa):
            continue

        # baseline GPA for this course row
        baseline_info = data_handler.aggregate_for_row(
            comparison=comparison,
            row=row,
            json_dir=json_dir,
            csv_path=csv_path_use,
        )
        baseline_gpa = baseline_info.get("gpa")
        if baseline_gpa is None:
            continue
        try:
            baseline_gpa_f = float(baseline_gpa)
        except (TypeError, ValueError):
            continue
        if math.isnan(baseline_gpa_f):
            continue

        diff = actual_gpa - baseline_gpa_f

        # build course label: SUBJECTCATALOG Term YY (ClassNbr)
        subject = str(row.get("Subject") or "").strip()
        catalog = str(row.get("Catalog Nbr") or "").strip()
        term = str(row.get("Term") or "").strip()
        year = str(row.get("Year") or "").strip()
        class_nbr = str(row.get("Class Nbr") or "").strip()

        # shorten 4-digit year to last two digits
        year_short = year[-2:] if len(year) == 4 and year.isdigit() else year

        # remove space between subject and catalog
        subject_catalog = f"{subject}{catalog}" if (subject or catalog) else ""

        parts = [p for p in [subject_catalog, term, year_short] if p]
        course_label = " ".join(parts) if parts else "(unknown)"
        if class_nbr:
            course_label = f"{course_label} ({class_nbr})"

        aggregate_name = (
            baseline_info.get("aggregate_name")
            or baseline_info.get("baseline")
            or "baseline"
        )
        aggregate_name = str(aggregate_name)
        if aggregate_name.startswith("All Available "):
            aggregate_name = aggregate_name[len("All Available "):]

        label = f"{course_label} vs. {aggregate_name}"

        labels.append(label)
        diffs.append(diff)

    if not labels:
        print(f"    ⚠️ No GPA/baseline data for instructor {inst_name}. Skipping GPA graph.")
        return None

    diffs_arr = np.asarray(diffs, dtype=float)
    y = np.arange(len(diffs_arr))
    n_courses = len(labels)

    max_abs = float(np.nanmax(np.abs(diffs_arr)))
    if not math.isfinite(max_abs) or max_abs <= 0.0:
        max_abs = 0.5
    xlim = max_abs * (1.0 + x_margin)

    # plotting ###################################################################
    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=dpi)

    # zero line in the middle (vertical)
    ax.axvline(0.0, color=zero_line_color, linewidth=zero_linewidth)

    colors = [positive_color if v >= 0.0 else negative_color for v in diffs_arr]
    ax.barh(y, diffs_arr, color=colors, height=bar_height)

    ax.set_yticks(y)
    if n_courses >= 40:
        tick_fs = 6
    elif n_courses >= 30:
        tick_fs = 7
    elif n_courses >= 20:
        tick_fs = 8
    else:
        tick_fs = 9
    ax.set_yticklabels(labels, fontsize=tick_fs)

    ax.set_xlim(-xlim, xlim)
    ax.set_xlabel("GPA difference vs baseline")
    ax.set_ylabel("Course vs aggregate")

    display_name_parts = [inst_first, inst_middle, inst_last]
    display_name = " ".join([p for p in display_name_parts if p]) or inst_name or "Unknown instructor"
    ax.set_title(f"GPA vs aggregate by course for {display_name}")

    fig.tight_layout()

    # filename ###################################################################
    instructor_last_slug = _slug(inst_last)
    instructor_first_slug = _slug(inst_first)
    if instructor_last_slug and instructor_first_slug:
        filename = f"{instructor_last_slug}_{instructor_first_slug}.png"
    elif inst_name:
        filename = f"{_slug(inst_name)}.png"
    else:
        filename = "instructor.png"

    out_path = os.path.join(instr_dir, filename)
    fig.savefig(out_path)
    plt.close(fig)

    print(f"    ✅ Generated instructor course GPA graph: {out_path}")
    return out_path
