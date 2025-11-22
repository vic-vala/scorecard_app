import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# === Load CSV ===
file_path = "SCAI Grade Distribution Fall 22- Spring 25(Sheet1).csv"
df_all = pd.read_csv(file_path)
df_all['Strm'] = df_all['Strm'].astype(int)

# === CONFIG ===
INSTRUCTOR_FILTER = "Meuth,Ryan"  # <--- change as needed

# === GPA SCALE ===
gpa_scale = {
    "A+": 4.33, "A": 4.0, "A-": 3.67,
    "B+": 3.33, "B": 3.0, "B-": 2.67,
    "C+": 2.33, "C": 2.0, "D": 1.0, "E": 0.0
}
grade_cols = list(gpa_scale.keys())

# === Compute GPA ===
def compute_gpa(row):
    total_points, total_students = 0.0, 0
    for g in grade_cols:
        cnt = row.get(g, 0)
        cnt = 0 if pd.isna(cnt) else int(cnt)
        total_points += cnt * gpa_scale[g]
        total_students += cnt
    return total_points / total_students if total_students > 0 else None

df_all["Average_GPA"] = df_all.apply(compute_gpa, axis=1)
df_all["Course"] = df_all["Subject"].astype(str).str.strip() + " " + df_all["Catalog Nbr"].astype(str).str.strip()

# === Decode STRM to semester ===
def decode_strm(strm):
    strm = int(strm)
    year_code = strm // 10
    term_code = strm % 10
    year = 1800 + year_code
    term_map = {1: "Spring", 4: "Summer", 7: "Fall"}
    term = term_map.get(term_code, f"Unknown({term_code})")
    return f"{term} {year}"

df_all["Semester"] = df_all["Strm"].map(decode_strm)

term_order = {"Spring": 1, "Summer": 2, "Fall": 3}
semester_order = sorted(
    df_all["Semester"].dropna().unique(),
    key=lambda x: (int(x.split()[1]), term_order.get(x.split()[0], 99))
)

# === Filter by instructor ===
df_prof = df_all[df_all["Instructor"] == INSTRUCTOR_FILTER].copy()
if df_prof.empty:
    raise ValueError(f"No data found for instructor: {INSTRUCTOR_FILTER}")

# === Aggregate GPA by course & semester ===
grouped = (
    df_prof.groupby(["Course", "Strm"], as_index=False)
    .agg(Average_GPA=("Average_GPA", "mean"))
)
grouped["Semester"] = grouped["Strm"].map(decode_strm)
grouped["Semester"] = pd.Categorical(grouped["Semester"], categories=semester_order, ordered=True)
grouped = grouped.sort_values("Strm")

# === Compute course-level stats (mean and std across all instructors) ===
course_stats = (
    df_all.groupby("Course", as_index=False)
    .agg(
        Overall_Avg_GPA=("Average_GPA", "mean"),
        Overall_SD_GPA=("Average_GPA", "std")
    )
)

# Only keep courses the instructor taught
course_stats = course_stats[course_stats["Course"].isin(df_prof["Course"].unique())]
course_stats["Plus1SD"] = course_stats["Overall_Avg_GPA"] + course_stats["Overall_SD_GPA"]
course_stats["Minus1SD"] = course_stats["Overall_Avg_GPA"] - course_stats["Overall_SD_GPA"]

# Reversed fade: newest bright, oldest faded

def fade_color(hex_color, fade_factor):
    hex_color = hex_color.lstrip("#")
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    r = int(r + (255 - r) * fade_factor)
    g = int(g + (255 - g) * fade_factor)
    b = int(b + (255 - b) * fade_factor)
    return f"rgb({r},{g},{b})"

base_color = "#1f77b4"
fade_levels = {
    sem: 1 - (i / (len(semester_order) - 1)) if len(semester_order) > 1 else 0
    for i, sem in enumerate(semester_order)
}
grouped["Color"] = grouped["Semester"].map(lambda s: fade_color(base_color, fade_levels[s]))

#  Dynamic Y-Axis
all_gpas = grouped["Average_GPA"].dropna()
if not all_gpas.empty:
    y_min = max(0, all_gpas.min() - 0.025)
    y_max = min(4.33, all_gpas.max() + 0.025)
else:
    y_min, y_max = 0, 4.33

#  PLOT
fig = go.Figure()

#  Instructor GPA Dots by Semester
for sem in semester_order:
    sub = grouped[grouped["Semester"] == sem]
    if sub.empty:
        continue
    fig.add_trace(go.Scatter(
        x=sub["Course"],
        y=sub["Average_GPA"],
        mode="markers",
        name=str(sem),
        marker=dict(size=12, color=sub["Color"], line=dict(width=1, color="white")),
        showlegend=True
    ))

#  Mean GPA
fig.add_trace(go.Scatter(
    x=course_stats["Course"],
    y=course_stats["Overall_Avg_GPA"],
    mode="markers",
    name="Average (All Instructors)",
    marker=dict(size=12, color="orange", symbol="diamond", line=dict(width=1, color="black")),
    showlegend=True
))

#  +1 SD
fig.add_trace(go.Scatter(
    x=course_stats["Course"],
    y=course_stats["Plus1SD"],
    mode="markers",
    name="+1 SD (All Instructors)",
    marker=dict(size=12, color="darkgray", symbol="diamond", line=dict(width=2, color="black")),
    showlegend=True
))

#  -1 SD
fig.add_trace(go.Scatter(
    x=course_stats["Course"],
    y=course_stats["Minus1SD"],
    mode="markers",
    name="-1 SD (All Instructors)",
    marker=dict(size=12, color="darkgray", symbol="diamond", line=dict(width=2, color="black")),
    showlegend=True
))

#  Layout
fig.update_layout(
    template="plotly_dark",
    title=f"{INSTRUCTOR_FILTER} — Average GPA by Course ",
    xaxis_title="Course",
    yaxis_title="Average GPA",
    height=700,
    margin=dict(l=80, r=180, t=80, b=100),
    showlegend=True,
    legend=dict(
        title="Legend",
        orientation="v",
        yanchor="top",
        y=1,
        xanchor="left",
        x=1.02,
        font=dict(size=12)
    )
)

fig.update_yaxes(range=[y_min, y_max], fixedrange=True)
fig.update_xaxes(fixedrange=True, tickangle=-45)

# Render Static
fig.show(config={
    "staticPlot": True,
    "displayModeBar": False,
    "editable": False
})
