"""
LaTeX template sections for the instructor-level consolidated scorecard.
Based on prof3.tex — xltabular layout with per-course detail rows
(histogram + AI summary) and course-history rows between course groups.
"""


def get_color_definitions():
    """Color palette (unchanged from previous version)."""
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


def get_helper_commands():
    """AutoD, spark, rules, column types, courserow macro with detail sub-row, coursehistoryrow macro."""
    return r'''
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
% --- Sparkline (per-course GPA boxplot) ---
\newcommand{\spark}[1]{\smash{\raisebox{-0.25\height}{\includegraphics[height=0.4cm,width=6cm]{\BoxplotDir/boxplot_\BoxplotStem_#1.png}}}}%
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
% --- Course-row macro (data row + detail row with histogram + AI summary) ---
% NOTE: Alternating \rowcolor removed — \rowcolor uses \noalign internally,
% which is incompatible with \ifodd conditionals inside xltabular/longtable.
% Rows are visually separated by \thinrule instead.
\newcommand{\courserow}[1]{%
    \csname Course#1Name\endcsname &
    \csname Course#1Term\endcsname &
    \csname Course#1Code\endcsname &
    \csname Course#1Size\endcsname &
    \csname Course#1RespRate\endcsname &
    \csname Course#1Overall\endcsname &
    \autoD{\csname Course#1OverallDelta\endcsname} &
    \csname Course#1GPA\endcsname &
    \autoD{\csname Course#1GPADelta\endcsname} &
    \multicolumn{3}{c}{\spark{#1}} &
    \csname Course#1Qone\endcsname &
    \autoD{\csname Course#1QoneDelta\endcsname} &
    \csname Course#1Median\endcsname &
    \autoD{\csname Course#1MedianDelta\endcsname} &
    \csname Course#1Qthree\endcsname &
    \autoD{\csname Course#1QthreeDelta\endcsname} \\*
    \noalign{\penalty10000}%
    % --- Detail row: histogram + AI overview ---
    \multicolumn{18}{@{\hspace{\tabcolsep}}l@{\hspace{\tabcolsep}}}{%
        \begin{minipage}[t]{\dimexpr\linewidth-2\tabcolsep\relax}%
        \vspace{1pt}%
        \noindent%
        \begin{minipage}[t]{0.20\linewidth}%
            \vspace{0pt}%
            \includegraphics[width=\linewidth]{\HistDir/histogram_\BoxplotStem_#1.png}%
        \end{minipage}%
        \hfill%
        \begin{minipage}[t]{0.76\linewidth}%
            \vspace{0pt}%
            \rmfamily\scriptsize\RaggedRight%
            \csname Course#1AISummary\endcsname%
        \end{minipage}%
        \vspace{1pt}%
        \end{minipage}%
    } \\
    \thinrule%
}%
%
% --- Course history row macro ---
\newcommand{\coursehistoryrow}[1]{%
    \multicolumn{18}{@{\hspace{\tabcolsep}}c@{\hspace{\tabcolsep}}}{%
        \begin{minipage}[c]{\dimexpr\linewidth-2\tabcolsep\relax}%
        \vspace{4pt}%
        \centering%
        \includegraphics[width=\linewidth]{\OverlayDir/coursehistory_\BoxplotStem_#1.png}%
        \vspace{4pt}%
        \end{minipage}%
    } \\
    \thinrule%
}%
'''


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
    """Two-column aggregate KPI dashboard (unchanged)."""
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
%
\par\vspace{6pt}%
'''


def get_per_course_table_header():
    """Opening of the per-course xltabular (18 columns with spacers around Trend)."""
    return r'''
{%
\sffamily\footnotesize%
\renewcommand{\arraystretch}{1.30}%
\arrayrulecolor{ruleGray}%
\setlength{\arrayrulewidth}{0.3pt}%
\setlength{\tabcolsep}{3pt}%
%
\noindent%
\begin{xltabular}{\textwidth}{%
    l%              Course
    l%              Term
    l%              Code
    l%              Size
    l%              Resp
    l%              Eval
    l%              Δ Eval
    l%              GPA
    l%              Δ GPA
    X%              (spacer)
    C{1.8cm}%       Trend (centered)
    X%              (spacer)
    r%              Q1
    r%              Δ
    r%              Med
    r%              Δ
    r%              Q3
    r%              Δ
}%
% --- Header (first page) ---
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
\multicolumn{3}{c}{\textcolor{headerFg}{\textbf{GPA Trend}}} &
\textcolor{headerFg}{\textbf{Q1}} &
\textcolor{headerFg}{\textbf{$\boldsymbol{\Delta}$}} &
\textcolor{headerFg}{\textbf{Med}} &
\textcolor{headerFg}{\textbf{$\boldsymbol{\Delta}$}} &
\textcolor{headerFg}{\textbf{Q3}} &
\textcolor{headerFg}{\textbf{$\boldsymbol{\Delta}$}} \\
\thickrule%
\endfirsthead%
% --- Header (continuation pages) ---
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
\multicolumn{3}{c}{\textcolor{headerFg}{\textbf{GPA Trend}}} &
\textcolor{headerFg}{\textbf{Q1}} &
\textcolor{headerFg}{\textbf{$\boldsymbol{\Delta}$}} &
\textcolor{headerFg}{\textbf{Med}} &
\textcolor{headerFg}{\textbf{$\boldsymbol{\Delta}$}} &
\textcolor{headerFg}{\textbf{Q3}} &
\textcolor{headerFg}{\textbf{$\boldsymbol{\Delta}$}} \\
\thickrule%
\endhead%
% --- Footer (continuation pages) ---
\thickrule%
\endfoot%
% --- Footer (last page) ---
\thickrule%
\endlastfoot%
'''


def get_per_course_table_footer():
    """Closing of the per-course xltabular."""
    return r'''
\end{xltabular}%
}% end group
'''