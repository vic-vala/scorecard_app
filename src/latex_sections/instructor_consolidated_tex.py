"""
LaTeX template sections for the instructor-level consolidated scorecard.
Based on prof.tex — the tabularx balanced-scorecard design with per-course rows.
"""


def get_color_definitions():
    """Color palette (shared with consolidated_tex)."""
    return r'''
\definecolor{catGreen}{HTML}{C6DEA7}%
\definecolor{catTeal}{HTML}{B3E1D4}%
\definecolor{catBlue}{HTML}{C9D3E4}%
\definecolor{catCyan}{HTML}{C4E5E6}%
\definecolor{rowGreenAlt}{HTML}{E7F4E0}%
\definecolor{rowTealAlt}{HTML}{E2F0EC}%
\definecolor{rowBlueAlt}{HTML}{E6EFFB}%
\definecolor{rowCyanAlt}{HTML}{E4F6F7}%
\definecolor{headerBg}{HTML}{595959}%
\definecolor{headerFg}{HTML}{FFFFFF}%
\definecolor{accent}{HTML}{1F4E79}%
\definecolor{ruleGray}{HTML}{BFBFBF}%
\colorlet{pos}{green!50!black}%
\colorlet{neg}{red!60!black}%
\colorlet{neu}{gray!70!black}%
'''


def get_helper_commands(boxplot_path):
    """AutoD, spark, rules, column types, courserow macro."""
    return (r'''
\newcommand{\autoD}[1]{%
    \IfStrEq{#1}{0}{\textcolor{neu}{#1}}{%
    \IfStrEq{#1}{0\%}{\textcolor{neu}{#1}}{%
    \IfStrEq{#1}{+0}{\textcolor{neu}{#1}}{%
    \IfStrEq{#1}{+0\%}{\textcolor{neu}{#1}}{%
    \IfStrEq{#1}{-0}{\textcolor{neu}{#1}}{%
    \IfStrEq{#1}{-0\%}{\textcolor{neu}{#1}}{%
    \IfStrEq{#1}{N/A}{}{%
    \IfBeginWith{#1}{+}{\textcolor{pos}{#1}}{%
    \IfBeginWith{#1}{-}{\textcolor{neg}{#1}}{%
    \IfBeginWith{#1}{{-}}{\textcolor{neg}{#1}}{\textcolor{neu}{#1}}%
    }}}}}}}}}%
}%
%
\newcommand{\spark}{\includegraphics[height=1.2em]{''' + boxplot_path + r'''}}%
%
\newcommand{\thinrule}{%
    \arrayrulecolor{ruleGray}%
    \specialrule{0.3pt}{0pt}{0pt}%
}%
\newcommand{\thickrule}{%
    \arrayrulecolor{headerBg}%
    \specialrule{0.8pt}{1pt}{1pt}%
}%
%
\newcolumntype{C}[1]{>{\centering\arraybackslash}m{#1}}%
\newcolumntype{R}[1]{>{\raggedleft\arraybackslash}m{#1}}%
%
% --- Course-row macro (auto-alternating shading) ---
\newcounter{courserowcnt}%
\setcounter{courserowcnt}{0}%
\newcommand{\courserow}[1]{%
    \stepcounter{courserowcnt}%
    \ifodd\value{courserowcnt}\else\rowcolor{rowBlueAlt}\fi%
    \csname Course#1Name\endcsname &
    \csname Course#1Term\endcsname &
    \csname Course#1Code\endcsname &
    \csname Course#1Size\endcsname &
    \csname Course#1RespRate\endcsname &
    \csname Course#1Overall\endcsname &
    \autoD{\csname Course#1OverallDelta\endcsname} &
    \csname Course#1GPA\endcsname &
    \autoD{\csname Course#1GPADelta\endcsname} &
    \spark &
    \csname Course#1Qone\endcsname &
    \autoD{\csname Course#1QoneDelta\endcsname} &
    \csname Course#1Median\endcsname &
    \autoD{\csname Course#1MedianDelta\endcsname} &
    \csname Course#1Qthree\endcsname &
    \autoD{\csname Course#1QthreeDelta\endcsname} \\
    \thinrule%
}%
''')


def get_title_section():
    """Title bar with instructor name, term range, totals, baseline."""
    return r'''
\begin{center}%
    {\LARGE\bfseries\sffamily\textcolor{accent}{Instructor Summary \textendash\ \Instructor}}\\[2pt]%
    {\footnotesize\textcolor{neu}{\TermRange\ ~\textbar~ \TotalUniqueCourses\ Unique Courses, \TotalSessions\ Sessions, \TotalEnrollment\ Students ~\textbar~ Compared Against: \BaselineText}}%
\end{center}%
\vspace{4pt}%
'''


def get_aggregate_kpi_table():
    """Two-column aggregate KPI dashboard."""
    return r'''
{%
\sffamily\small%
\renewcommand{\arraystretch}{1.35}%
\arrayrulecolor{ruleGray}%
\setlength{\arrayrulewidth}{0.3pt}%
\setlength{\tabcolsep}{4pt}%
%
\noindent%
\begin{tabularx}{\textwidth}{%
    C{0.70cm}%
    >{\raggedright\arraybackslash}X%
    R{1.2cm}%
    R{1.0cm}%
    C{0.70cm}%
    >{\raggedright\arraybackslash}X%
    R{1.2cm}%
    R{1.0cm}%
}%
\thickrule%
\rowcolor{headerBg}%
\textcolor{headerFg}{\textbf{}} &
\textcolor{headerFg}{\textbf{Metric}} &
\textcolor{headerFg}{\textbf{Value}} &
\textcolor{headerFg}{\textbf{$\boldsymbol{\Delta}$}} &
\textcolor{headerFg}{\textbf{}} &
\textcolor{headerFg}{\textbf{Metric}} &
\textcolor{headerFg}{\textbf{Value}} &
\textcolor{headerFg}{\textbf{$\boldsymbol{\Delta}$}} \\
\thickrule%
%
\cellcolor{catTeal} &
Overall Eval &
\AggOverall{} / 5 &
\autoD{\AggOverallDelta} &
\cellcolor{catBlue} &
GPA &
\AggGPA &
\autoD{\AggGPADelta} \\
\thinrule%
\cellcolor{catTeal} &
\cellcolor{rowTealAlt} Part 1 (Instructor) &
\cellcolor{rowTealAlt} \AggPone{} / 5 &
\cellcolor{rowTealAlt} \autoD{\AggPoneDelta} &
\cellcolor{catBlue} &
\cellcolor{rowBlueAlt} Q1 (25th) &
\cellcolor{rowBlueAlt} \AggQone &
\cellcolor{rowBlueAlt} \autoD{\AggQoneDelta} \\
\thinrule%
\multirow{-3}{*}{\cellcolor{catTeal}\makebox[0pt]{\rotatebox[origin=c]{90}{\bfseries\tiny EVALS}}} &
Part 2 (Course) &
\AggPtwo{} / 5 &
\autoD{\AggPtwoDelta} &
\cellcolor{catBlue} &
Median &
\AggMedianGrade &
\autoD{\AggMedianDelta} \\
\thinrule%
\cellcolor{catGreen} &
\cellcolor{rowGreenAlt} Response Rate &
\cellcolor{rowGreenAlt} \AggResponseRate &
\cellcolor{rowGreenAlt} \autoD{\AggResponseDelta} &
\multirow{-4}{*}{\cellcolor{catBlue}\makebox[0pt]{\rotatebox[origin=c]{90}{\bfseries\tiny OUTCOMES}}} &
\cellcolor{rowBlueAlt} Q3 (75th) &
\cellcolor{rowBlueAlt} \AggQthree &
\cellcolor{rowBlueAlt} \autoD{\AggQthreeDelta} \\
\thickrule%
\end{tabularx}%
}% end group
'''


def get_grade_and_summary_section():
    """Grade distribution table + AI summary side-by-side."""
    return r'''
\par\vspace{6pt}%
\noindent%
\begin{minipage}[t]{0.15\textwidth}%
\sffamily\small%
\fboxsep=3pt%
\noindent\colorbox{headerBg}{%
    \parbox[c]{\dimexpr\linewidth-2\fboxsep\relax}{%
        \textcolor{headerFg}{\bfseries\footnotesize Grades}%
    }%
}\par\vspace{3pt}%
\renewcommand{\arraystretch}{1.25}%
\arrayrulecolor{ruleGray}%
{\footnotesize%
\begin{tabular}{@{} l r r @{}}%
    \toprule%
    & \textbf{\%} & $\boldsymbol{\Delta}$ \\%
    \midrule%
    \rowcolor{rowBlueAlt} A & \AggGradeAPct & \autoD{\AggGradeADelta} \\%
    B & \AggGradeBPct & \autoD{\AggGradeBDelta} \\%
    \rowcolor{rowBlueAlt} C & \AggGradeCPct & \autoD{\AggGradeCDelta} \\%
    D & \AggGradeDPct & \autoD{\AggGradeDDelta} \\%
    \rowcolor{rowBlueAlt} E & \AggGradeEPct & \autoD{\AggGradeEDelta} \\%
    \bottomrule%
\end{tabular}%
}%
\end{minipage}%
\hfill%
\begin{minipage}[t]{0.83\textwidth}%
\sffamily\small%
\fboxsep=3pt%
\noindent\colorbox{headerBg}{%
    \parbox[c]{\dimexpr\linewidth-2\fboxsep\relax}{%
        \textcolor{headerFg}{\bfseries\footnotesize AI Instructor Summary}%
    }%
}\par\vspace{3pt}%
{\rmfamily\small%
\RaggedRight%
\LLMInstructorSummary%
}%
\end{minipage}%
\par\vspace{6pt}%
'''


def get_per_course_table_header():
    """Opening of the per-course table (header row). Body rows added via \\courserow."""
    return r'''
{%
\sffamily\footnotesize%
\renewcommand{\arraystretch}{1.30}%
\arrayrulecolor{ruleGray}%
\setlength{\arrayrulewidth}{0.3pt}%
\setlength{\tabcolsep}{3pt}%
%
\setcounter{courserowcnt}{0}%
\noindent%
\begin{tabularx}{\textwidth}{%
    l%
    >{\raggedright\arraybackslash}X%
    r%
    r%
    r%
    r%
    r%
    r%
    r%
    C{1.8cm}%
    r%
    r%
    r%
    r%
    r%
    r%
}%
\thickrule%
\rowcolor{headerBg}%
\textcolor{headerFg}{\textbf{Course}} &
\textcolor{headerFg}{\textbf{Term}} &
\textcolor{headerFg}{\textbf{Code}} &
\textcolor{headerFg}{\textbf{Size}} &
\textcolor{headerFg}{\textbf{Resp}} &
\textcolor{headerFg}{\textbf{Eval}} &
\textcolor{headerFg}{\textbf{$\boldsymbol{\Delta}$}} &
\textcolor{headerFg}{\textbf{GPA}} &
\textcolor{headerFg}{\textbf{$\boldsymbol{\Delta}$}} &
\textcolor{headerFg}{\textbf{Trend}} &
\textcolor{headerFg}{\textbf{Q1}} &
\textcolor{headerFg}{\textbf{$\boldsymbol{\Delta}$}} &
\textcolor{headerFg}{\textbf{Med}} &
\textcolor{headerFg}{\textbf{$\boldsymbol{\Delta}$}} &
\textcolor{headerFg}{\textbf{Q3}} &
\textcolor{headerFg}{\textbf{$\boldsymbol{\Delta}$}} \\
\thickrule%
'''


def get_per_course_table_footer():
    """Closing of the per-course table."""
    return r'''
\thickrule%
\end{tabularx}%
}% end group
'''
