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
from src.utils import _slug, _get_numeric

_GRADE_ORDER = ["E", "D", "C", "C+", "B-", "B", "B+", "A-", "A", "A+"]

_GRADE_GRADIENTS = {
    "A": ("#ff3b19", "#f6b644"),  
    "B": ("#0e7300", "#6be002"),  
    "C": ("#1d38a1", "#0067f3"),  
    "D": ("#930008", "#d90014"),  
    "E": ("#930008", "#d90014"),  
}

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

    # Active visualization scope: histogram + course history + instructor overlay + instructor histograms.
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
        "  Generating Instructor Course History Overlay Graphs",
        "  No instructors selected for course overlay graphs. Skipping overlay graph generation.",
        generate_instructor_course_history_overlay_graphs,
        csv_path,
    )

    _generate(
        selected_scorecard_instructors,
        "  Generating Instructor Course Histograms",
        "  No instructors selected for course histograms. Skipping histogram generation.",
        generate_instructor_course_histograms,
        csv_path,
    )

def generate_course_grade_histogram(
    config: Mapping[str, Any],
    course: Mapping[str, Any],
    csv_path,
    output_override: Optional[str] = None,
):
    """
    Render a grade histogram PNG for a single course

    Outputs
    {department}_{course}_{professor}_{term}_{year}_{course_number}.png
    into grade_histogram_dir.

    If output_override is provided, saves to that exact path instead.
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

    # figure size defaults; slightly higher dpi improves readability when image is tiny.
    dpi = int(plot_cfg.get("dpi", 140))
    width_px = int(plot_cfg.get("width_px", 750))
    height_px = int(plot_cfg.get("height_px", 750))
    fig_width = width_px / dpi
    fig_height = height_px / dpi

    course_color = plot_cfg.get("course_color", "#cc6600")
    # fallback gradient if a grade has no entry in _GRADE_GRADIENTS
    course_bottom_color = plot_cfg.get("course_bottom_color", "#ffa64c")

    baseline_color = plot_cfg.get("baseline_color", "#000000")
    baseline_linewidth = float(plot_cfg.get("baseline_linewidth", 2.6))
    baseline_label_text = str(plot_cfg.get("baseline_label", "Baseline"))

    x_tick_fontsize = float(plot_cfg.get("x_tick_fontsize", 16))
    y_tick_fontsize = float(plot_cfg.get("y_tick_fontsize", 15))
    title_fontsize = float(plot_cfg.get("title_fontsize", 10))
    legend_fontsize = float(plot_cfg.get("legend_fontsize", 8.5))
    show_legend = str(plot_cfg.get("show_legend", "false")).lower() == "true"
    annotate_counts = str(plot_cfg.get("annotate_counts", "true")).lower() == "true"
    count_fontsize = float(plot_cfg.get("count_fontsize", 14))
    count_min_fraction = float(plot_cfg.get("count_min_fraction_of_max", 0.08))

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

    # Keep legend text concise for very small embeds.
    baseline_label = baseline_label_text

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
    scorecard_dir = paths.get("scorecard_dir")
    scorecard_out_path = os.path.join(scorecard_dir, filename) if scorecard_dir else None

    # plotting ####################################################
    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=dpi)

    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")

    x = np.arange(len(_GRADE_ORDER))

    # Course bars with vertical gradients, connected (no gaps)
    # Each base letter grade (A/B/C/D/E) gets its own gradient.
    bars = ax.bar(
        x,
        course_counts,
        width=bar_width,
        color="none",
        align="center",
        edgecolor="none",
    )

    # Vertical gradient image 0..1, reused for all bars
    grad = np.linspace(0.0, 1.0, 256).reshape(256, 1)

    # Precompute colormaps per grade label using the base letter (ignoring +/-)
    grade_cmaps: dict[str, mcolors.Colormap] = {}
    for grade_label in _GRADE_ORDER:
        base_grade = (grade_label or "")[:1].upper()
        bottom_hex, top_hex = _GRADE_GRADIENTS.get(
            base_grade,
            (course_bottom_color, course_color),
        )
        grade_cmaps[grade_label] = mcolors.LinearSegmentedColormap.from_list(
            f"course_grad_{base_grade}", [bottom_hex, top_hex]
        )

    for grade_label, bar in zip(_GRADE_ORDER, bars):
        height = bar.get_height()
        if height <= 0:
            continue

        x_left = bar.get_x()
        x_right = x_left + bar.get_width()
        y_bottom = 0.0
        y_top = height

        cmap = grade_cmaps[grade_label]

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

    # Optional count labels for readability at small display sizes.
    if annotate_counts and len(course_counts) == len(_GRADE_ORDER):
        max_count = max(course_counts) if course_counts else 0
        min_label_height = max(1.0, float(max_count) * max(0.0, count_min_fraction))
        for xi, cnt in zip(x, course_counts):
            if cnt <= 0 or cnt < min_label_height:
                continue
            ax.text(
                xi,
                cnt + max(0.05 * max_count, 0.35),
                f"{int(cnt)}",
                ha="center",
                va="bottom",
                fontsize=count_fontsize,
                color="#222222",
                zorder=6,
            )

    # legend is off by default for tiny embeds to keep only axes readable
    if show_legend:
        ax.legend(loc="upper left", fontsize=legend_fontsize, frameon=False, handlelength=1.8)

    # only grade labels at the bottom
    ax.set_xticks(x)
    ax.set_xticklabels(_GRADE_ORDER, fontsize=x_tick_fontsize)

    # remove everything else textual
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_title("")
    ax.tick_params(axis="y", which="major", left=True, labelleft=True, labelsize=y_tick_fontsize)

    # Keep y-axis readable with light horizontal guides.
    y_max_data = max([0.0] + [float(v) for v in course_counts] + [float(v) for v in baseline_values])
    y_top = max(1.0, y_max_data * 1.12)
    y_step = max(1, int(plot_cfg.get("y_tick_step", 5)))
    y_top_rounded = int(math.ceil(y_top / y_step) * y_step)
    ax.set_ylim(0.0, float(y_top_rounded))
    y_ticks = np.arange(0, y_top_rounded + y_step, y_step)
    ax.set_yticks(y_ticks)
    ax.set_yticklabels([str(int(v)) for v in y_ticks])
    ax.grid(axis="y", linestyle=":", linewidth=0.6, alpha=0.35, color="#666666")

    # clean spines
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    # no x margin
    ax.margins(x=0.0)

    fig.tight_layout(pad=0.65)

    # Save to the requested location
    if output_override:
        os.makedirs(os.path.dirname(output_override), exist_ok=True)
        fig.savefig(output_override, facecolor="#ffffff")
        plt.close(fig)
        print(f"    ✅ Generated course grade histogram: {output_override}")
        return output_override

    fig.savefig(out_path, facecolor="#ffffff")
    if scorecard_out_path:
        os.makedirs(scorecard_dir, exist_ok=True)
        fig.savefig(scorecard_out_path, facecolor="#ffffff")
    plt.close(fig)

    if scorecard_out_path:
        print(f"    ✅ Generated course grade histogram: {scorecard_out_path}")
        return scorecard_out_path

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
    delta_color_threshold_small = float(
        plot_cfg.get("delta_color_threshold_small", 0.10)
    )
    delta_color_threshold_large = float(
        plot_cfg.get("delta_color_threshold_large", 0.25)
    )
    delta_color_small = plot_cfg.get("delta_color_small", "#2ca02c")
    delta_color_medium = plot_cfg.get("delta_color_medium", "#ffbf00")
    delta_color_large = plot_cfg.get("delta_color_large", "#d62728")
    delta_label_fontsize = float(plot_cfg.get("delta_label_fontsize", 7))
    delta_sparkline_enabled = str(
        plot_cfg.get("delta_sparkline_enabled", "true")
    ).lower() == "true"
    delta_sparkline_width = float(plot_cfg.get("delta_sparkline_width", 0.22))
    delta_sparkline_height = float(plot_cfg.get("delta_sparkline_height", 0.18))
    delta_sparkline_right = float(plot_cfg.get("delta_sparkline_right", 0.98))
    delta_sparkline_top = float(plot_cfg.get("delta_sparkline_top", 0.96))

    if delta_color_threshold_large < delta_color_threshold_small:
        delta_color_threshold_large = delta_color_threshold_small

    def _delta_color(delta_val: float) -> str:
        abs_delta = abs(float(delta_val))
        if abs_delta <= delta_color_threshold_small:
            return delta_color_small
        if abs_delta <= delta_color_threshold_large:
            return delta_color_medium
        return delta_color_large

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
    stats = stats.reset_index(drop=True)

    mean_vals = stats["mean_gpa"].astype(float)
    mean_x_vals = stats["x"].astype(float)
    diffs = mean_vals.diff()

    delta_annotations = []
    for i in range(1, len(stats)):
        dy = diffs.iloc[i]
        if pd.isna(dy):
            continue

        x0 = float(stats.loc[i - 1, "x"])
        x1 = float(stats.loc[i, "x"])
        y0 = float(stats.loc[i - 1, "mean_gpa"])
        y1 = float(stats.loc[i, "mean_gpa"])

        delta_annotations.append(
            {
                "delta": float(dy),
                "midx": (x0 + x1) / 2.0,
                "midy": (y0 + y1) / 2.0,
            }
        )

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
        mean_vals.values,
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

    # Overlay a dashed copy of the mean line to keep it visually distinct.
    ax.plot(
        mean_x_vals.values,
        mean_vals.values,
        color="black",
        linestyle=":",
        linewidth=1,
        zorder=2,
    )

    # Annotate the change between each consecutive mean point with magnitude-based color.
    for ann in delta_annotations:
        dy = ann["delta"]
        ax.text(
            ann["midx"],
            ann["midy"],
            f"{dy:+.2f}",
            fontsize=delta_label_fontsize,
            color=_delta_color(dy),
            ha="center",
            va="bottom",
            zorder=5,
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

    sparkline_drawn = delta_sparkline_enabled and len(delta_annotations) > 0
    bottom_reserved = 0.18

    def _draw_delta_sparkline():
        delta_series = np.array([d["delta"] for d in delta_annotations], dtype=float)
        x_delta = np.arange(len(delta_series), dtype=float)
        spark_colors = [_delta_color(v) for v in delta_series]

        spark_width = min(max(delta_sparkline_width, 0.10), 0.45)
        spark_height = min(max(delta_sparkline_height, 0.10), 0.35)
        spark_left = min(max(delta_sparkline_right - spark_width, 0.52), 0.98 - spark_width)
        spark_bottom = min(max(delta_sparkline_top - spark_height, 0.55), 0.98 - spark_height)
        spark_ax = ax.inset_axes(
            [spark_left, spark_bottom, spark_width, spark_height],
            transform=ax.transAxes,
            facecolor="#ffffffcc",
            zorder=6,
        )
        spark_ax.axhline(0.0, color="#777777", linewidth=0.8, linestyle=":", zorder=1)
        spark_ax.plot(x_delta, delta_series, color="#666666", linewidth=0.9, zorder=2)
        spark_ax.scatter(
            x_delta,
            delta_series,
            c=spark_colors,
            s=16,
            edgecolors="none",
            zorder=3,
        )

        if len(delta_series) == 1:
            spark_ax.set_xlim(-0.5, 0.5)
        else:
            spark_ax.set_xlim(0.0, len(delta_series) - 1)

        spark_extent = max(float(np.max(np.abs(delta_series))), 0.05)
        spark_ax.set_ylim(-spark_extent * 1.15, spark_extent * 1.15)
        spark_ax.set_xticks([])
        spark_ax.set_yticks([])
        for spine in ["top", "right", "left", "bottom"]:
            spark_ax.spines[spine].set_visible(False)

    # Legend below the entire graph
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ncol = min(4, len(labels))
        fig.tight_layout(rect=(0.0, bottom_reserved, 1.0, 1.0))
        if sparkline_drawn:
            _draw_delta_sparkline()

        fig.legend(
            handles,
            labels,
            loc="lower center",
            bbox_to_anchor=(0.5, 0.02),
            ncol=ncol,
            frameon=False,
            fontsize=8,
        )
    else:
        fig.tight_layout(rect=(0.0, bottom_reserved, 1.0, 1.0))
        if sparkline_drawn:
            _draw_delta_sparkline()

    # Save figure ###############################################################
    subject_slug = _slug(subject)
    catalog_slug = _slug(catalog)
    filename = f"{subject_slug}_{catalog_slug}.png"
    out_path = os.path.join(course_hist_dir, filename)

    fig.savefig(out_path)
    plt.close(fig)

    print(f"    ✅ Generated course history graph: {out_path}")
    
    return out_path


def generate_instructor_course_history_overlay_graph(
    config: Mapping[str, Any],
    course: Mapping[str, Any],
    csv_path,
    instructor: Optional[Mapping[str, Any]] = None,
    output_override: Optional[str] = None,
):
    """
    Generate a compact course-history graph for scorecards with:
    - same-level course mean GPA over time
    - +/- 1 SD band
    - current instructor GPA line for the selected course in purple

    If output_override is provided, saves to that exact path instead of scorecard_dir.
    """
    paths = config.get("paths", {}) or config.get("PATHS", {})
    output_dir = paths.get("instructor_overlay_dir") or paths.get("scorecard_dir")
    if not output_dir:
        raise KeyError("instructor_overlay_dir/scorecard_dir not found in config['paths'].")
    os.makedirs(output_dir, exist_ok=True)

    # Compact defaults for small image embedding in instructor short cards.
    plot_cfg = (
        config.get("plots", {}).get("instructor_course_history_overlay", {})
        or {}
    )
    dpi = int(plot_cfg.get("dpi", 130))
    width_px = int(plot_cfg.get("width_px", 1335))
    height_px = int(plot_cfg.get("height_px", 571))
    fig_width = width_px / dpi
    fig_height = height_px / dpi

    mean_color = plot_cfg.get("mean_color", "#ff8800")
    band_color = plot_cfg.get("std_fill_color", "#d9d9d9")
    band_alpha = float(plot_cfg.get("std_alpha", 0.28))
    instructor_color = plot_cfg.get("instructor_color", "#7B2CBF")

    if isinstance(csv_path, (list, tuple)):
        if not csv_path:
            print("    ⚠️ csv_path list/tuple is empty. Skipping instructor overlay history graph.")
            return None
        csv_path_use = csv_path[0]
    else:
        csv_path_use = csv_path

    df = pd.read_csv(csv_path_use)
    df["Average_GPA"] = pd.to_numeric(df.get("GPA"), errors="coerce")

    subject = str(course.get("Subject") or "").strip()
    catalog = str(course.get("Catalog Nbr") or "").strip()
    if not subject or not catalog:
        print("    ⚠️ Missing Subject/Catalog Nbr. Skipping instructor overlay history graph.")
        return None

    # Target course rows are used for the instructor-specific line.
    mask_exact_course = (
        df["Subject"].astype(str).str.strip().eq(subject)
        & df["Catalog Nbr"].astype(str).str.strip().eq(catalog)
    )
    if not mask_exact_course.any():
        print(f"    ⚠️ No rows found for course {subject} {catalog}. Skipping instructor overlay history graph.")
        return None

    def _course_level(catalog_value):
        match = re.search(r"\d+", str(catalog_value or ""))
        if not match:
            return None
        try:
            return (int(match.group(0)) // 100) * 100
        except (TypeError, ValueError):
            return None

    course_level = _course_level(catalog)
    if course_level is None:
        print(f"    ⚠️ Could not parse course level for {subject} {catalog}. Skipping instructor overlay history graph.")
        return None

    df["Course Level"] = df["Catalog Nbr"].map(_course_level)

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
        return f"{term} {year}" if term else None

    if "Strm" in df.columns:
        df["Semester"] = df["Strm"].map(_decode_strm)
    else:
        df["Semester"] = None

    if df["Semester"].isna().all():
        if "Term" in df.columns and "Year" in df.columns:
            def _term_year(row):
                term = str(row.get("Term") or "").strip()
                year = str(row.get("Year") or "").strip()
                return f"{term} {year}" if term and year else None
            df["Semester"] = df.apply(_term_year, axis=1)

    # Baseline rows are all same-subject courses in the same 100-level bucket.
    baseline_mask = (
        df["Subject"].astype(str).str.strip().eq(subject)
        & df["Course Level"].eq(course_level)
    )
    df_baseline = df[baseline_mask].copy()
    df_baseline = df_baseline[df_baseline["Semester"].notna()].copy()
    df_baseline = df_baseline[df_baseline["Average_GPA"].notna()].copy()
    if df_baseline.empty:
        print(
            f"    ⚠️ No semester/GPA baseline data for {subject} {course_level}-level courses. "
            "Skipping instructor overlay history graph."
        )
        return None

    # Instructor line still tracks this selected exact course.
    df_exact_course = df[mask_exact_course].copy()
    df_exact_course = df_exact_course[df_exact_course["Semester"].notna()].copy()
    df_exact_course = df_exact_course[df_exact_course["Average_GPA"].notna()].copy()
    if df_exact_course.empty:
        print(f"    ⚠️ No semester/GPA data for {subject} {catalog}. Skipping instructor overlay history graph.")
        return None

    if "Instructor" in df_baseline.columns:
        df_baseline["Instructor"] = (
            df_baseline["Instructor"].fillna("(no data)").astype(str).str.strip()
        )
    else:
        df_baseline["Instructor"] = "(no data)"

    if "Instructor" in df_exact_course.columns:
        df_exact_course["Instructor"] = (
            df_exact_course["Instructor"].fillna("(no data)").astype(str).str.strip()
        )
    else:
        df_exact_course["Instructor"] = "(no data)"

    term_order = {"Spring": 1, "Summer": 2, "Fall": 3}

    def _semester_key(sem_str: str):
        try:
            term, year = sem_str.split()
            return (int(year), term_order.get(term, 99))
        except Exception:
            return (9999, 99)

    semester_values = sorted(
        set(df_baseline["Semester"].dropna().unique()) | set(df_exact_course["Semester"].dropna().unique()),
        key=_semester_key,
    )
    semester_order = semester_values
    sem_to_x = {sem: idx for idx, sem in enumerate(semester_order)}

    grouped = (
        df_baseline.groupby(["Semester", "Instructor"], as_index=False)
        .agg({"Average_GPA": "mean"})
    )

    stats = (
        grouped[grouped["Instructor"] != "(no data)"]
        .groupby("Semester", as_index=False)
        .agg(mean_gpa=("Average_GPA", "mean"), std_gpa=("Average_GPA", "std"))
    )
    if stats.empty:
        print(f"    ⚠️ Not enough aggregate history for {subject} {catalog}. Skipping instructor overlay history graph.")
        return None

    stats["std_gpa"] = stats["std_gpa"].fillna(0.0)
    stats["x"] = stats["Semester"].map(sem_to_x)
    stats = stats.sort_values("x").reset_index(drop=True)

    def _norm_text(value):
        return re.sub(r"\s+", " ", str(value or "").strip().lower())

    if instructor is None:
        inst_get = lambda key: None
    else:
        inst_get = lambda key: instructor.get(key)

    target_first = str(inst_get("Instructor First") or course.get("Instructor First") or "").strip()
    target_last = str(inst_get("Instructor Last") or course.get("Instructor Last") or "").strip()
    target_full = str(inst_get("Instructor") or course.get("Instructor") or "").strip()
    target_candidates = {
        _norm_text(target_full),
        _norm_text(f"{target_first} {target_last}"),
        _norm_text(f"{target_last}, {target_first}"),
    }
    target_candidates.discard("")

    norm_instructors = df_exact_course["Instructor"].map(_norm_text)
    target_mask = norm_instructors.isin(target_candidates) if target_candidates else pd.Series(False, index=df_exact_course.index)

    # Last-name fallback for inconsistent instructor formatting in CSV exports.
    if not target_mask.any() and target_last:
        target_mask = df_exact_course["Instructor"].astype(str).str.contains(
            rf"\b{re.escape(target_last)}\b",
            regex=True,
            case=False,
            na=False,
        )

    df_target = df_exact_course[target_mask].copy()
    if df_target.empty:
        print(f"    ⚠️ No instructor-specific points found for {subject} {catalog}. Skipping instructor overlay history graph.")
        return None

    target_grouped = (
        df_target.groupby("Semester", as_index=False)
        .agg(instructor_gpa=("Average_GPA", "mean"))
    )
    target_grouped["x"] = target_grouped["Semester"].map(sem_to_x)
    target_grouped = target_grouped.dropna(subset=["x"]).sort_values("x")
    if target_grouped.empty:
        print(f"    ⚠️ Instructor points could not be mapped to semesters for {subject} {catalog}.")
        return None

    all_gpas = pd.concat(
        [
            grouped["Average_GPA"].dropna(),
            target_grouped["instructor_gpa"].dropna(),
        ],
        ignore_index=True,
    )
    y_min = max(0.0, float(all_gpas.min()) - 0.12) if not all_gpas.empty else 0.0
    y_max = min(4.33, float(all_gpas.max()) + 0.12) if not all_gpas.empty else 4.33

    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=dpi)
    ax.set_facecolor("#fcfcfc")
    fig.patch.set_facecolor("#fcfcfc")

    x_vals = stats["x"].astype(float).values
    mean_vals = stats["mean_gpa"].astype(float).values
    upper_vals = (stats["mean_gpa"] + stats["std_gpa"]).astype(float).values
    lower_vals = (stats["mean_gpa"] - stats["std_gpa"]).astype(float).values

    ax.fill_between(
        x_vals,
        lower_vals,
        upper_vals,
        color=band_color,
        alpha=band_alpha,
        label=f"{subject} {course_level}-level Avg +/-1 SD",
        zorder=1,
    )

    ax.plot(
        x_vals,
        mean_vals,
        color=mean_color,
        linewidth=2.6,
        marker="D",
        markersize=5.2,
        label=f"{subject} {course_level}-level Avg GPA",
        zorder=3,
    )

    ax.plot(
        target_grouped["x"].astype(float).values,
        target_grouped["instructor_gpa"].astype(float).values,
        color=instructor_color,
        linewidth=3.1,
        marker="o",
        markersize=6.2,
        label="Instructor GPA",
        zorder=4,
    )

    ax.set_xticks(np.arange(len(semester_order)))
    ax.set_xticklabels(semester_order, rotation=28, ha="right", fontsize=10)
    ax.set_ylim(y_min, y_max)
    ax.set_xlim(-0.5, len(semester_order) - 0.5)
    ax.set_ylabel("GPA", fontsize=11.5)
    ax.set_xlabel("Semester", fontsize=11)
    display_instructor = target_full or " ".join([p for p in [target_first, target_last] if p]).strip() or "Instructor"
    ax.set_title(f"{subject} {catalog} GPA History - {display_instructor}", fontsize=13, pad=8)
    ax.grid(axis="y", linestyle=":", linewidth=0.7, alpha=0.38)
    ax.tick_params(axis="y", labelsize=10)

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    ax.legend(loc="upper left", fontsize=9.5, frameon=False)
    fig.tight_layout(pad=1.0)

    # Save
    if output_override:
        os.makedirs(os.path.dirname(output_override), exist_ok=True)
        fig.savefig(output_override)
        plt.close(fig)
        print(f"    ✅ Generated instructor overlay history graph: {output_override}")
        return output_override

    subject_slug = _slug(subject)
    catalog_slug = _slug(catalog)
    inst_slug = _slug(target_last or target_full or "instructor")
    filename = f"{subject_slug}_{catalog_slug}_{inst_slug}_history_overlay.png"
    out_path = os.path.join(output_dir, filename)

    fig.savefig(out_path)
    plt.close(fig)

    print(f"    ✅ Generated instructor overlay history graph: {out_path}")
    return out_path


def generate_instructor_course_history_overlay_graphs(
    config: Mapping[str, Any],
    instructor: Mapping[str, Any],
    csv_path,
):
    """
    Generate one overlay graph per course taught by a selected instructor.
    """
    # Do not require parsed JSON for visualization-only generation.
    instructor_courses = data_handler.get_courses_by_instructor(instructor, csv_path, False)
    if instructor_courses is None or instructor_courses.empty:
        inst_name = str(instructor.get("Instructor", "")).strip() or "Unknown instructor"
        print(f"    ⚠️ No courses found for {inst_name}. Skipping overlay graphs.")
        return None

    out_paths = []
    seen_courses: set = set()
    for _, course in instructor_courses.iterrows():
        subject = str(course.get("Subject") or "").strip()
        catalog = str(course.get("Catalog Nbr") or "").strip()
        course_key = (subject, catalog)
        if not subject or not catalog or course_key in seen_courses:
            continue
        seen_courses.add(course_key)

        out_path = generate_instructor_course_history_overlay_graph(
            config=config,
            course=course,
            csv_path=csv_path,
            instructor=instructor,
        )
        if out_path:
            out_paths.append(out_path)

    return out_paths


def generate_instructor_course_histograms(
    config: Mapping[str, Any],
    instructor: Mapping[str, Any],
    csv_path,
):
    """
    Generate one existing course histogram per course taught by a selected instructor.
    """
    instructor_courses = data_handler.get_courses_by_instructor(instructor, csv_path, False)
    if instructor_courses is None or instructor_courses.empty:
        inst_name = str(instructor.get("Instructor", "")).strip() or "Unknown instructor"
        print(f"    ⚠️ No courses found for {inst_name}. Skipping histogram generation.")
        return None

    out_paths = []
    for _, course in instructor_courses.iterrows():
        out_path = generate_course_grade_histogram(
            config=config,
            course=course,
            csv_path=csv_path,
        )
        if out_path:
            out_paths.append(out_path)
    return out_paths