"""
LaTeX template sections for the consolidated scorecard layout.
This file mirrors the structure of per_session.py but implements the
tabularx-based balanced-scorecard design from new_mockup.txt.
"""

import os


def get_color_definitions():
    """Returns color palette definitions for the consolidated scorecard."""
    return r'''
% Category sidebar fills
\definecolor{catGreen}{HTML}{C6DEA7}
\definecolor{catTeal}{HTML}{B3E1D4}
\definecolor{catBlue}{HTML}{C9D3E4}
\definecolor{catCyan}{HTML}{C4E5E6}
% Alternating row tints
\definecolor{rowGreenAlt}{HTML}{E7F4E0}
\definecolor{rowTealAlt}{HTML}{E2F0EC}
\definecolor{rowBlueAlt}{HTML}{E6EFFB}
\definecolor{rowCyanAlt}{HTML}{E4F6F7}
% Structural colours
\definecolor{headerBg}{HTML}{595959}
\definecolor{headerFg}{HTML}{FFFFFF}
\definecolor{accent}{HTML}{1F4E79}
\definecolor{ruleGray}{HTML}{BFBFBF}
% Delta colours
\colorlet{pos}{green!50!black}
\colorlet{neg}{red!60!black}
\colorlet{neu}{gray!70!black}
'''


def get_helper_commands(boxplot_path):
    """Returns helper commands for the consolidated scorecard.

    Args:
        boxplot_path: Absolute path to the boxplot image for sparklines.
    """
    return (r'''
\newcommand{\CourseHeader}{\CourseName\ (\CourseYear\ \CourseTerm) \CourseCode\ \textendash\ \Instructor}

\newcommand{\autoD}[1]{%
    \IfStrEq{#1}{0}{\textcolor{neu}{#1}}{%
    \IfStrEq{#1}{0\%}{\textcolor{neu}{#1}}{%
    \IfStrEq{#1}{+0}{\textcolor{neu}{#1}}{%
    \IfStrEq{#1}{+0\%}{\textcolor{neu}{#1}}{%
    \IfStrEq{#1}{-0}{\textcolor{neu}{#1}}{%
    \IfStrEq{#1}{-0\%}{\textcolor{neu}{#1}}{%
    \IfStrEq{#1}{N/A}{}{%
    \IfBeginWith{#1}{+}{\textcolor{pos}{#1}}{%
    \IfBeginWith{#1}{-}{\textcolor{neg}{#1}}{\textcolor{neu}{#1}}%
    }}}}}}}}%
}

\newcommand{\spark}{\includegraphics[height=1.2em]{''' + boxplot_path + r'''}}

\newcommand{\thinrule}{%
    \arrayrulecolor{ruleGray}%
    \specialrule{0.3pt}{0pt}{0pt}%
}
\newcommand{\thickrule}{%
    \arrayrulecolor{headerBg}%
    \specialrule{0.8pt}{1pt}{1pt}%
}
''')


def get_column_definitions():
    """Returns column dimension and type definitions."""
    return r'''
\newlength{\CatW}\setlength{\CatW}{0.70cm}
\newlength{\ValW}\setlength{\ValW}{1.4cm}
\newlength{\NumW}\setlength{\NumW}{0.7cm}
\newlength{\PctW}\setlength{\PctW}{0.85cm}
\newlength{\DelW}\setlength{\DelW}{1.4cm}
\newlength{\SpkW}\setlength{\SpkW}{1.0cm}

\newcolumntype{C}[1]{>{\centering\arraybackslash}m{#1}}
\newcolumntype{R}[1]{>{\raggedleft\arraybackslash}m{#1}}
'''


def get_title_section():
    """Returns the title/header section of the consolidated scorecard."""
    return r'''
\begin{center}
    {\LARGE\bfseries\sffamily\textcolor{accent}{\CourseHeader}}\\[2pt]
    {\footnotesize\textcolor{neu}{Compared Against: \BaselineText}}
\end{center}
\vspace{4pt}
'''


def get_main_scorecard_table():
    """Returns the main scorecard table with enrollment, evaluations,
    outcomes, and AI summary sections."""
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
    C{\CatW}%
    >{\raggedright\arraybackslash}X%
    R{1.2cm}%
    R{1.0cm}%
    R{1.4cm}%
    C{2.5cm}%
}%
%
% ──────────────── HEADER ────────────────
\thickrule%
\rowcolor{headerBg}%
\textcolor{headerFg}{\textbf{}} &
\textcolor{headerFg}{\textbf{Metric}} &
\textcolor{headerFg}{\textbf{Value}} &
\textcolor{headerFg}{\textbf{\%}} &
\textcolor{headerFg}{\textbf{$\boldsymbol{\Delta}$ Baseline}} &
\textcolor{headerFg}{\textbf{Trend}} \\
\thickrule%
%
% ═══════════════ ENROLLMENT (green, 3 rows) ═══════════════
\cellcolor{catGreen} &
Course Size &
\CourseSize & &
\autoD{\CourseSizeDelta} &
\spark \\
\thinrule%
\cellcolor{catGreen} &
\cellcolor{rowGreenAlt} Responses &
\cellcolor{rowGreenAlt} \Responses &
\cellcolor{rowGreenAlt} \ResponseRate &
\cellcolor{rowGreenAlt} \autoD{\ResponseDelta} &
\cellcolor{rowGreenAlt} \spark \\
\thinrule%
\multirow{-3}{*}{\cellcolor{catGreen}\makebox[0pt]{\rotatebox[origin=c]{90}{\bfseries\tiny ENROLLMENT}}} &
Response Rate &
& \ResponseRate &
\autoD{\ResponseDelta} &
\spark \\
\thickrule%
%
% ═══════════════ EVALUATIONS (teal, 3 rows) ═══════════════
\cellcolor{catTeal} &
Overall &
\AvgOverall{} / 5 & &
\autoD{\AvgOverallDelta} &
\spark \\
\thinrule%
\cellcolor{catTeal} &
\cellcolor{rowTealAlt} Avg Part 1 (Instructor) &
\cellcolor{rowTealAlt} \AvgPone{} / 5 &
\cellcolor{rowTealAlt} &
\cellcolor{rowTealAlt} \autoD{\AvgPoneDelta} &
\cellcolor{rowTealAlt} \spark \\
\thinrule%
\multirow{-3}{*}{\cellcolor{catTeal}\makebox[0pt]{\rotatebox[origin=c]{90}{\bfseries\tiny EVALUATIONS}}} &
Avg Part 2 (Course) &
\AvgPtwo{} / 5 & &
\autoD{\AvgPtwoDelta} &
\spark \\
\thickrule%
%
% ═══════════════ OUTCOMES (blue, 9 rows) ═══════════════
\cellcolor{catBlue} &
Median Grade &
\MedianGrade & &
\autoD{\MedianGradeDelta} &
\spark \\
\thinrule%
\cellcolor{catBlue} &
\cellcolor{rowBlueAlt} GPA &
\cellcolor{rowBlueAlt} \GPA &
\cellcolor{rowBlueAlt} &
\cellcolor{rowBlueAlt} \autoD{\GPADelta} &
\cellcolor{rowBlueAlt} \spark \\
\thinrule%
\cellcolor{catBlue} &
Pass &
\PassNum & \PassPct &
\autoD{\PassDelta} &
\spark \\
\thinrule%
\cellcolor{catBlue} &
\cellcolor{rowBlueAlt} Fail &
\cellcolor{rowBlueAlt} \FailNum &
\cellcolor{rowBlueAlt} \FailPct &
\cellcolor{rowBlueAlt} \autoD{\FailDelta} &
\cellcolor{rowBlueAlt} \spark \\
\thinrule%
\cellcolor{catBlue} &
Drop &
\DropNum & \DropPct &
\autoD{\DropDelta} &
\spark \\
\thinrule%
\cellcolor{catBlue} &
\cellcolor{rowBlueAlt} Withdraw &
\cellcolor{rowBlueAlt} \WithdrawNum &
\cellcolor{rowBlueAlt} \WithdrawPct &
\cellcolor{rowBlueAlt} \autoD{\WithdrawDelta} &
\cellcolor{rowBlueAlt} \spark \\
\thinrule%
\cellcolor{catBlue} &
Q1 (25th Percentile) &
\Qone & &
\autoD{\QoneDelta} &
\spark \\
\thinrule%
\cellcolor{catBlue} &
\cellcolor{rowBlueAlt} Median (50th Percentile) &
\cellcolor{rowBlueAlt} \Qtwo &
\cellcolor{rowBlueAlt} &
\cellcolor{rowBlueAlt} \autoD{\QtwoDelta} &
\cellcolor{rowBlueAlt} \spark \\
\thinrule%
\multirow{-9}{*}{\cellcolor{catBlue}\makebox[0pt]{\rotatebox[origin=c]{90}{\bfseries\tiny OUTCOMES}}} &
\cellcolor{rowBlueAlt} Q3 (75th Percentile) &
\cellcolor{rowBlueAlt} \Qthree &
\cellcolor{rowBlueAlt} &
\cellcolor{rowBlueAlt} \autoD{\QthreeDelta} &
\cellcolor{rowBlueAlt} \spark \\
\thickrule%
%
% ═══════════════ AI SUMMARY (cyan, merged) ═══════════════
\multirow{1}{*}{\cellcolor{catCyan}\makebox[0pt]{\rotatebox[origin=c]{90}{\bfseries\tiny AI SUMMARY}}} &
\multicolumn{5}{l}{%
    \parbox[t]{\dimexpr\textwidth - \CatW - 4\tabcolsep - 2pt\relax}{%
        \RaggedRight\rmfamily\small%
        \LLMSummary%
        \vspace{3pt}%
    }%
} \\
\thickrule%
%
\end{tabularx}%
}% end group
'''


def get_grade_distribution_section(grade_hist_image):
    """Returns the grade distribution bottom section.

    Args:
        grade_hist_image: Absolute path to the histogram PNG.
    """
    return r'''
\par\vspace{10pt}
%
\begingroup%
\sffamily\small%
\renewcommand{\arraystretch}{1.0}%
\arrayrulecolor{ruleGray}%
%
% --- Section header bar ---
\fboxsep=4pt%
\noindent\colorbox{headerBg}{%
    \parbox[c]{\dimexpr\textwidth-2\fboxsep\relax}{%
        \textcolor{headerFg}{\bfseries Grade Distribution}%
        \hfill%
        \textcolor{headerFg}{\footnotesize%
            Pass:~\PassNum\ (\PassPct)%
            ~\textbar~Fail:~\FailNum\ (\FailPct)%
            ~\textbar~GPA:~\GPA%
        }%
    }%
}\par\vspace{4pt}%
%
% --- Histogram + grade breakdown side by side ---
\noindent%
\begin{minipage}[t]{0.58\textwidth}%
    \centering%
    \includegraphics[width=\linewidth, height=2.0in, keepaspectratio]{''' + grade_hist_image + r'''}%
    \par\vspace{2pt}%
    {\footnotesize%
    \textbf{Q1:}~\Qone~\autoD{\QoneDelta}%
    \qquad\textbf{Median:}~\Qtwo~\autoD{\QtwoDelta}%
    \qquad\textbf{Q3:}~\Qthree~\autoD{\QthreeDelta}}%
\end{minipage}%
\hfill%
\begin{minipage}[t]{0.38\textwidth}%
    \centering%
    \renewcommand{\arraystretch}{1.35}%
    \arrayrulecolor{ruleGray}%
    \begin{tabular}{@{} l r r r @{}}%
        \toprule%
        \textbf{Grade} & \textbf{\#} & \textbf{\%} & $\boldsymbol{\Delta}$ \\%
        \midrule%
        \rowcolor{rowBlueAlt} A & \GradeACount & \GradeAPct & \autoD{\GradeADelta} \\%
        B & \GradeBCount & \GradeBPct & \autoD{\GradeBDelta} \\%
        \rowcolor{rowBlueAlt} C & \GradeCCount & \GradeCPct & \autoD{\GradeCDelta} \\%
        D & \GradeDCount & \GradeDPct & \autoD{\GradeDDelta} \\%
        \rowcolor{rowBlueAlt} E & \GradeECount & \GradeEPct & \autoD{\GradeEDelta} \\%
        \bottomrule%
    \end{tabular}%
\end{minipage}%
\endgroup%
'''