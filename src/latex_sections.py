"""
This file contains all of the raw LaTeX used to generate the scorecards.
Separated for readability & maintainability. Changes made to command names will need
to be reflected here as well. Aside from this, it should be fairly extensible.
"""

def get_page_title_template():
    """Returns the LaTeX template for the page title section"""
    return r'''
\ifShowHdrTitle
	\begin{center}
		{\PageTitle}\\
		{\PageSubtitle}
	\end{center}
\fi
'''


def get_overview_section_template():
    """Returns the LaTeX template for the Overview section"""
    return r'''
\begin{tcolorbox}
	{\Large\bfseries\textcolor{accent}{Overview}}
	\ifShowHdrOverview\hfill\textbf{\CourseHeader}\fi
    \vspace{2pt}

	\renewcommand{\arraystretch}{1.25}
	\begin{tabularx}{\textwidth}{@{} >{\raggedright\arraybackslash}X >{\raggedright\arraybackslash}X @{}}

 	% -------- Left column --------
	\begin{tabular}{@{}l >{\raggedleft\arraybackslash}p{\DeltaColW}@{}}
		\MetricLeft{Course Size}{\CourseSize}{} & \autoD{\CourseSizeDelta}\\
		\MetricLeft{Responses}{\Responses}{\ResponseRate} \\
		\MetricLeft{Avg Part 1}{\AvgPone}{} & \autoD{\AvgPoneDelta}\\
		\MetricLeft{Avg Part 2}{\AvgPtwo}{} & \autoD{\AvgPtwoDelta}\\
		\MetricLeft{Median Grade}{\MedianGrade}{} & \autoD{\MedianGradeDelta}\\
	\end{tabular}
	&
 	% -------- Right column --------
	\begin{tabular}{@{}l >{\raggedleft\arraybackslash}p{\DeltaColW}@{}}
		\MetricLeft{Pass}{\PassNum}{\PassPct} & \autoD{\PassDelta}\\
		\MetricLeft{Fail}{\FailNum}{\FailPct} & \autoD{\FailDelta}\\
		\MetricLeft{Drop}{\DropNum}{\DropPct} & \autoD{\DropDelta}\\
		\MetricLeft{Withdraw}{\WithdrawNum}{\WithdrawPct} & \autoD{\WithdrawDelta}\\
        \MetricLeft{GPA}{\GPA}{} & \autoD{\GPADelta}\\
	\end{tabular}

	\end{tabularx}
\end{tcolorbox}
'''


def get_evaluation_section_template():
    """Returns the LaTeX template for the Evaluation Metrics section"""
    return r'''
\begin{tcolorbox}
	{\Large\bfseries\textcolor{accent}{Lowest Evaluation Metrics}}
	\ifShowHdrEval\hfill\textbf{\CourseHeader}\fi

	\vspace{2pt}
	\renewcommand{\arraystretch}{1.2}
	\begin{tabularx}{\textwidth}{@{} >{\raggedright\arraybackslash}X >{\raggedleft\arraybackslash}p{\DeltaColW}@{}}
		\MetricLeft{\OutOneName} {\OutOneScore/5}{} \\
		\MetricLeft{\OutTwoName} {\OutTwoScore/5}{} \\
		\MetricLeft{\OutThreeName} {\OutThreeScore/5}{} \\
        \MetricLeft{\OutFourName} {\OutFourScore/5}{} \\
        \MetricLeft{\OutFiveName} {\OutFiveScore/5}{} \\
	\end{tabularx}
\end{tcolorbox}
'''


def get_comment_section_template():
    """Returns the LaTeX template for the Comment Summary section"""
    return r'''
\begin{tcolorbox}
	{\Large\bfseries\textcolor{accent}{Comment Summary (AI Generated)}}

	\noindent \LLMSummary
\end{tcolorbox}
'''


def get_grade_distribution_section_template(grade_dist_image):
    return r'''
\begin{tcolorbox}
	{\Large\bfseries\textcolor{accent}{Grade Distribution}}

	\vspace{2pt}
	\noindent\textbf{Pass/Fail Totals:}~\PassNum~(\PassPct)~pass~\autoD{\PassDelta}~/~\FailNum~(\FailPct)~fail~\autoD{\FailDelta}\hfill\textbf{GPA:}~\GPA~\autoD{\GPADelta}

	\vspace{2pt}
	\begin{tabularx}{\textwidth}{@{} X T{\RightColW} @{}}

        % ---- Histogram WITHOUT outline ----
		\begin{minipage}[c][\GradeVisH][c]{\linewidth}\centering
			\includegraphics[width=\linewidth, height=\GradeVisH, keepaspectratio]{''' + grade_dist_image + r'''}
		\end{minipage}

		&
		\begingroup\centering
			\renewcommand{\arraystretch}{1.1}
			\begin{tabular}{@{}l r r r@{}}
				\toprule
				\textbf{Grade} & \textbf{\#} & \textbf{\%} & $\boldsymbol{\Delta}$ \\
				\midrule
				A & \GradeACount & \GradeAPct & \autoD{\GradeADelta} \\
				B & \GradeBCount & \GradeBPct & \autoD{\GradeBDelta} \\
				C & \GradeCCount & \GradeCPct & \autoD{\GradeCDelta} \\
				D & \GradeDCount & \GradeDPct & \autoD{\GradeDDelta} \\
				E & \GradeECount & \GradeEPct & \autoD{\GradeEDelta} \\
				\bottomrule
			\end{tabular}
		\par\endgroup
	\end{tabularx}

	\vspace{2pt}
	\noindent\makebox[\dimexpr\linewidth-\RightColW\relax][c]{\textbf{Q1:}~\Qone~\autoD{\QoneDelta}\quad\textbf{Median:}~\Qtwo~\autoD{\QtwoDelta}\quad\textbf{Q3:}~\Qthree~\autoD{\QthreeDelta}}

\end{tcolorbox}
'''



def get_helper_commands_template():
    #Returns the LaTeX template for helper commands
    return r'''
\newcommand{\CourseHeader}{\CourseName\ (\CourseYear\ \CourseTerm) \CourseCode\ \textendash\ \Instructor}

\newcommand{\PageTitle}{\LARGE\bfseries\textcolor{accent}{\CourseHeader}}

\newcommand{\PageSubtitle}{\footnotesize\textcolor{neu}{Compared Against: \BaselineText}}

\newcommand{\posD}[1]{\textcolor{pos}{(#1)}}

\newcommand{\negD}[1]{\textcolor{neg}{(#1)}}

\newcommand{\neuD}[1]{\textcolor{neu}{(#1)}}

\newcommand{\autoD}[1]{%
	\IfStrEq{#1}{0}{\neuD{#1}}{%
	\IfStrEq{#1}{0\%}{\neuD{#1}}{%
	\IfStrEq{#1}{+0}{\neuD{#1}}{%
	\IfStrEq{#1}{+0\%}{\neuD{#1}}{%
	\IfStrEq{#1}{-0}{\neuD{#1}}{%
	\IfStrEq{#1}{-0\%}{\neuD{#1}}{%
	\IfBeginWith{#1}{+}{\posD{#1}}{%
	\IfBeginWith{#1}{-}{\negD{#1}}{\neuD{#1}}%
	}}}}}}}%
}

\newcommand{\MetricLeft}[3]{%
	\textbf{#1:}~#2\if\relax\detokenize{#3}\relax\else~(#3)\fi
}
'''

def get_box_style_template():
    """Returns the LaTeX template for tcolorbox styling"""
    return r'''
% ---------- Box style (fixed: enable enhanced so frame exists) ----------
\tcbset{
	enhanced,
	frame style={draw=black!35, line width=.6pt},
	interior style={left color=black!2,right color=black!0},
	arc=2mm,
	boxsep=5pt, left=8pt, right=8pt, top=8pt, bottom=8pt,
}
'''