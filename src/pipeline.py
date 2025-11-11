from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any, Callable, List, Mapping, Optional, Sequence, Union

import pandas as pd

from src import data_vis, llm_io, scorecard_assembler, utils


_PLACEHOLDER_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/xcAAxUBgQ3BMVsAAAAASUVORK5CYII="
)


@dataclass
class PipelineModules:
    """Dependency injection container for the pipeline."""

    llm_runner: Callable[..., Optional[str]] = llm_io.run_llm
    scorecard_builder: Callable[..., None] = scorecard_assembler.assemble_scorecard
    data_vis_generator: Callable[..., None] = data_vis.generate_data_visualization


@dataclass
class ScorecardJob:
    """Represents a single course scorecard generation task."""

    slug: str
    json_path: str
    histogram_path: Optional[str]
    llm_json_path: Optional[str]
    llm_text_path: Optional[str]
    row: Mapping[str, Any]


class ScorecardPipeline:
    """Coordinates multi-course scorecard generation."""

    def __init__(
        self,
        config: Mapping[str, Any],
        csv_path: Union[Sequence[str], str],
        *,
        modules: Optional[PipelineModules] = None,
    ) -> None:
        if not config:
            raise ValueError("config is required")

        self.config = config
        self.paths = config.get("paths", {})
        self.modules = modules or PipelineModules()

        if isinstance(csv_path, (list, tuple)):
            if not csv_path:
                raise ValueError("csv_path sequence is empty")
            self.csv_path = csv_path[0]
        else:
            self.csv_path = csv_path

        self.grade_hist_dir = self.paths.get("grade_histogram_dir")
        self.tex_dir = self.paths.get("tex_dir", "./temporary_files/tex")
        self.scorecard_dir = self.paths.get("scorecard_dir", "./scorecards")
        self.temp_dir = self.paths.get("temp_dir", "./temporary_files/images")

        scorecard_settings = config.get("scorecard_gen_settings", {})
        include_llm_flag = scorecard_settings.get("include_LLM_insights", "false")
        self.include_llm = str(include_llm_flag).lower() == "true"

        os.makedirs(self.temp_dir, exist_ok=True)

    def run(
        self,
        selected_scorecard_courses: pd.DataFrame,
        selected_scorecard_instructors: Optional[pd.DataFrame] = None,
        selected_history_courses: Optional[pd.DataFrame] = None,
    ) -> List[str]:
        """
        Generate scorecards for all selected courses.

        Returns a list of PDF file paths that were generated.
        """
        course_df = self._ensure_dataframe(selected_scorecard_courses)
        instructors_df = self._ensure_dataframe(selected_scorecard_instructors)
        history_df = self._ensure_dataframe(selected_history_courses)

        if course_df.empty:
            print("[pipeline] No course selections provided. Nothing to do.")
            return []

        self.modules.data_vis_generator(
            self.config,
            course_df,
            instructors_df,
            self.csv_path,
            history_df,
        )

        jobs = self._build_jobs(course_df)
        if not jobs:
            print("[pipeline] No viable scorecard jobs were queued.")
            return []

        generated_paths: List[str] = []
        for job in jobs:
            result = self._process_job(job)
            if result:
                generated_paths.append(result)

        return generated_paths

    def _ensure_dataframe(self, value: Optional[pd.DataFrame]) -> pd.DataFrame:
        if value is None:
            return pd.DataFrame()
        if not isinstance(value, pd.DataFrame):
            raise TypeError("Expected a pandas DataFrame for selections.")
        return value

    def _build_jobs(self, df: pd.DataFrame) -> List[ScorecardJob]:
        jobs: List[ScorecardJob] = []
        parsed_dir = self.paths.get("parsed_pdf_dir")
        if not parsed_dir:
            print("[pipeline] parsed_pdf_dir missing in config; cannot locate JSON files.")
            return jobs

        for _, row in df.iterrows():
            try:
                json_path = utils.resolve_course_json_path(row, parsed_dir)
            except FileNotFoundError as exc:
                print(f"[pipeline] Skipping selection: {exc}")
                continue

            slug = utils.build_course_slug(row)
            histogram_path = (
                os.path.join(self.grade_hist_dir, f"{slug}.png")
                if self.grade_hist_dir
                else None
            )
            llm_json_path = os.path.join(self.temp_dir, f"{slug}_llm.json")
            llm_text_path = os.path.join(self.temp_dir, f"{slug}_llm.txt")
            jobs.append(
                ScorecardJob(
                    slug=slug,
                    json_path=json_path,
                    histogram_path=histogram_path,
                    llm_json_path=llm_json_path,
                    llm_text_path=llm_text_path,
                    row=row,
                )
            )

        return jobs

    def _process_job(self, job: ScorecardJob) -> Optional[str]:
        pdf_json = self._load_pdf_json(job.json_path)
        if pdf_json is None:
            print(f"[pipeline] Could not load JSON for {job.slug}; skipping.")
            return None

        if self.include_llm:
            summary = self._run_llm(job, pdf_json)
            if summary:
                pdf_json["llm_summary"] = summary

        asset_path = self._resolve_asset(job)
        self.modules.scorecard_builder(
            pdf_json,
            asset_path,
            tex_output_path=self.tex_dir,
            scorecard_output_path=self.scorecard_dir,
            output_filename=job.slug,
        )
        return os.path.join(self.scorecard_dir, f"{job.slug}.pdf")

    def _load_pdf_json(self, path: str) -> Optional[Mapping[str, Any]]:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[pipeline] Failed to read {path}: {exc}")
            return None

    def _run_llm(self, job: ScorecardJob, pdf_json: Mapping[str, Any]) -> Optional[str]:
        gguf_path = self.paths.get("gguf_path")
        llm_prompt_dir = self.paths.get("llm_prompt_dir")
        if not gguf_path or not llm_prompt_dir:
            print("[pipeline] LLM assets not configured; skipping summary generation.")
            return None

        summary = self.modules.llm_runner(
            gguf_path=gguf_path,
            pdf_json=pdf_json,
            llm_dir=llm_prompt_dir,
            temp_dir=self.temp_dir,
            output_json_path=job.llm_json_path,
        )
        if summary:
            self._write_text_file(job.llm_text_path, summary)
        return summary

    def _write_text_file(self, path: str, content: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content.strip() + "\n")

    def _resolve_asset(self, job: ScorecardJob) -> str:
        if job.histogram_path:
            abs_path = os.path.abspath(job.histogram_path)
            if os.path.exists(abs_path):
                return abs_path
            print(f"[pipeline] Histogram missing at {abs_path}; using placeholder.")
        return self._placeholder_asset()

    def _placeholder_asset(self) -> str:
        placeholder = os.path.join(self.temp_dir, "scorecard_placeholder.png")
        if not os.path.exists(placeholder):
            with open(placeholder, "wb") as handle:
                handle.write(_PLACEHOLDER_PNG)
        return os.path.abspath(placeholder)


def run_scorecard_pipeline(
    config: Mapping[str, Any],
    csv_path: Union[Sequence[str], str],
    selected_scorecard_courses: pd.DataFrame,
    selected_scorecard_instructors: Optional[pd.DataFrame] = None,
    selected_history_courses: Optional[pd.DataFrame] = None,
    *,
    modules: Optional[PipelineModules] = None,
) -> List[str]:
    """
    Functional wrapper around ScorecardPipeline for convenience.
    """
    pipeline = ScorecardPipeline(config, csv_path, modules=modules)
    return pipeline.run(
        selected_scorecard_courses,
        selected_scorecard_instructors,
        selected_history_courses,
    )
