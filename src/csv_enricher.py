import os
import json
import pandas as pd
from src.utils import course_to_json_path, _safe_int, _safe_float

def enrich_csv_with_evals(csv_path: str, json_dir: str, config: dict) -> None:
    """
    For every row in the CSV, check if a corresponding JSON (evaluation) file exists
    If so, pull eval_info fields and write them as new columns
    Overwrites the CSV in place

    Args:
        csv_path: Path to the CSV
        json_dir: Directory containing the JSON files
        config:   Application config dict
    """
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)

    has_eval = []
    response_counts = []
    response_rates = []
    avg1_vals = []
    avg2_vals = []
    overall_vals = []

    for _, row in df.iterrows():
        try:
            json_path = course_to_json_path(row, json_dir=json_dir, config=config)
        except Exception:
            json_path = None

        if json_path and os.path.isfile(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                _append_empty(has_eval, response_counts, response_rates, avg1_vals, avg2_vals, overall_vals)
                continue

            info = data.get("eval_info", {})

            has_eval.append(True)
            response_counts.append(_safe_int(info.get("response_count")))
            response_rates.append(_parse_rate(info.get("response_rate"), info.get("response_count"), info.get("total_students")))
            a1 = _safe_float(info.get("avg1"))
            a2 = _safe_float(info.get("avg2"))
            avg1_vals.append(a1)
            avg2_vals.append(a2)
            overall_vals.append(_compute_overall(a1, a2))
        else:
            _append_empty(has_eval, response_counts, response_rates, avg1_vals, avg2_vals, overall_vals)

    # insert new columns at the end
    df["Has Evaluation"] = has_eval
    df["Response Count"] = pd.array(response_counts, dtype=pd.Int64Dtype())
    df["Response Rate"] = response_rates
    df["Avg 1"] = avg1_vals
    df["Avg 2"] = avg2_vals
    df["Overall"] = overall_vals

    df.to_csv(csv_path, index=False)

    eval_count = sum(1 for v in has_eval if v)
    print(f"  ✅ Enriched CSV with evaluation data. {eval_count} of {len(df)} rows have evaluations.")

def _append_empty(has_eval, response_counts, response_rates, avg1_vals, avg2_vals, overall_vals):
    """Append None/False for a row with no matching JSON."""
    has_eval.append(False)
    response_counts.append(None)
    response_rates.append(None)
    avg1_vals.append(None)
    avg2_vals.append(None)
    overall_vals.append(None)

def _parse_rate(rate_str, response_count, total_students) -> float | None:
    """
    Parse response rate. Tries the percentage string first
    Falls back to computing response_count / total_students
    Returns a float in [0.0, 1.0] or None
    """
    if rate_str is not None:
        s = str(rate_str).strip().rstrip("%")
        try:
            return round(float(s) / 100.0, 4)
        except (TypeError, ValueError):
            pass

    # fallback: compute from counts
    rc = _safe_int(response_count)
    ts = _safe_int(total_students)
    if rc is not None and ts is not None and ts > 0:
        return round(rc / ts, 4)

    return None

def _compute_overall(avg1: float | None, avg2: float | None) -> float | None:
    """Average of avg1 and avg2. If only one exists, return that one."""
    vals = [v for v in (avg1, avg2) if v is not None]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 3)
