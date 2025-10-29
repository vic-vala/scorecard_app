from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict

from jinja2 import Environment, FileSystemLoader

_ROOT_DIR = Path(__file__).resolve().parent.parent
_TEMPLATE_DIR = _ROOT_DIR / "latex"
_TEMPLATE_NAME = "professor_scorecard.tex"
_OUTPUT_DIR = _TEMPLATE_DIR / "out"

_LATEX_SPECIALS = {
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    "\\": r"\textbackslash{}",
}

def _tex_escape(value: str) -> str:
    return "".join(_LATEX_SPECIALS.get(ch, ch) for ch in value)

def _environment() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=False,
        block_start_string="<<%",
        block_end_string="%>>",
        variable_start_string="<<",
        variable_end_string=">>",
        comment_start_string="<<#",
        comment_end_string="#>>",
    )
    env.filters["tex_escape"] = _tex_escape
    return env

def render_scorecard(context: Dict, output_basename: str) -> Path:
    """Render the LaTeX professor scorecard to PDF and return the PDF path."""
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    env = _environment()
    tex_source = env.get_template(_TEMPLATE_NAME).render(**context)
    tex_path = _OUTPUT_DIR / f"{output_basename}.tex"
    tex_path.write_text(tex_source, encoding="utf-8")

    try:
        result = subprocess.run(
            ["xelatex", "-interaction=nonstopmode", tex_path.name],
            cwd=_OUTPUT_DIR,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or b"").decode("utf-8", errors="ignore").strip()
        stdout = (exc.stdout or b"").decode("utf-8", errors="ignore").strip()
        details = [part for part in (stderr, stdout) if part]
        if not details:
            log_hint = tex_path.with_suffix(".log")
            details.append(
                f"xelatex exited with code {exc.returncode}. "
                f"Check the log file at {log_hint} for details."
            )
        raise RuntimeError("\n".join(details)) from exc
    else:
        for suffix in (".aux", ".log", ".out"):
            extra = tex_path.with_suffix(suffix)
            if extra.exists():
                extra.unlink()

    pdf_path = tex_path.with_suffix(".pdf")
    if not pdf_path.exists():
        raise FileNotFoundError("Expected PDF not produced by xelatex")
    return pdf_path
