import os
import pandas as pd


def _parse_filename(filename: str):
    """
    Parse filenames of the form:
        Subject_CatalogNbr_InstructorLast_Term_Year_ClassNbr.json

    Returns a dict with keys:
        subject, catalog_nbr, instructor_last, term,
        year, class_nbr
    """
    base = os.path.basename(filename)
    if base.lower().endswith(".json"):
        base = base[:-5]

    parts = base.split("_")

    if len(parts) != 6:
        raise ValueError(
            f"Unexpected JSON filename format: {filename}. "
            "Expected 6 underscore-separated parts."
        )

    subject, catalog_nbr, instructor_last, term, year, class_nbr = parts

    return {
        "subject": subject,
        "catalog_nbr": catalog_nbr,
        "instructor_last": instructor_last,
        "term": term,
        "year": year,
        "class_nbr": class_nbr,
    }

def viable_scorecards(json_dir: str, csv_path: str) -> pd.DataFrame:
    """
    This function looks through the name of each of the json files one at a time.

    For each of these json files, if the info in the file name matches one of the 
    rows in the csv, that row of the csv is added to the dataframe that is eventually returned.

    The eventually returned dataframe is the overlap in courses found between the CSV and json
    directory folder. 
    """
    # Read CSV as strings for reliable matching
    df = pd.read_csv(csv_path, dtype=str)

    # normalize columns
    for col in ["Subject", "Catalog Nbr", "Instructor Last", "Term", "Year", "Class Nbr"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    matched_rows = []

    # scan directory
    for fname in os.listdir(json_dir):
        if not fname.lower().endswith(".json"):
            continue

        full_path = os.path.join(json_dir, fname)

        try:
            info = _parse_filename(fname)
        except ValueError as e:
            print(f"Warning: {e}")
            continue

        subject = info["subject"]
        catalog_nbr = info["catalog_nbr"]
        instructor_last = info["instructor_last"]
        term = info["term"]
        year = info["year"]
        class_nbr = info["class_nbr"]

        mask = (
            (df["Subject"] == subject) &
            (df["Catalog Nbr"] == catalog_nbr) &
            (df["Instructor Last"] == instructor_last) &
            (df["Year"] == year) &
            (df["Class Nbr"] == class_nbr)
        )

        if term is not None and "Term" in df.columns:
            mask = mask & (df["Term"].str.casefold() == term.casefold())

        rows = df[mask]

        if rows.empty:
            print(f"  ⛔ No row found in CSV for JSON file '{fname}'")
        else:
            print(f"  ✅ Matching JSON and CSV found for '{fname}'")
            matched_rows.append(rows)
    
    if matched_rows:
        result = pd.concat(matched_rows, ignore_index=True)
    else:
        result = df.iloc[0:0].copy()

    return result
