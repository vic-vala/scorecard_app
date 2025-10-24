import os
from typing import List
import pandas as pd

def _bool_from_str(val, *, default=False) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        v = val.strip().lower()
        if v in {"true", "t", "1", "yes", "y"}:
            return True
        if v in {"false", "f", "0", "no", "n"}:
            return False
    return bool(default)

def run_excel_parser(excel_path: str, output_dir: str = "./parsed_csvs", *, overwrite_csv: bool = False) -> List[str]:
    if not excel_path:
        raise ValueError("excel_path is required")
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    os.makedirs(output_dir, exist_ok=True)

    written = []
    base_name = os.path.splitext(os.path.basename(excel_path))[0]

    # Load workbook once
    xls = pd.ExcelFile(excel_path)
    multiple = len(xls.sheet_names) > 1

    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)

        # Normalize column names a bit: strip spaces
        df.columns = [str(c).strip() for c in df.columns]

        # Build output csv path
        if multiple:
            safe_sheet = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in sheet_name).strip("_")
            csv_name = f"{base_name}__{safe_sheet}.csv"
        else:
            csv_name = f"{base_name}.csv"

        out_path = os.path.join(output_dir, csv_name)

        if not overwrite_csv and os.path.exists(out_path):
            print(f"  ⏭️ Skip existing CSV: {out_path}")
            continue

        df.to_csv(out_path, index=False)
        written.append(out_path)
        print(f"  ✅ Wrote CSV: {out_path}")

    return written
