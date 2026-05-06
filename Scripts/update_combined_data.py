"""
Build combined weekly dengue + climate dataset.

Default behavior:
- Reads FinalProject/Data/dengue_cases.csv
- Reads FinalProject/Data/weekly_averages.csv
- Merges on (year, week) with an outer join
- Writes FinalProject/Data/combined_data_test.csv

Usage:
    python update_combined_data.py
    python update_combined_data.py --how inner
    python update_combined_data.py --output Data/combined_data_test.csv
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

import pandas as pd


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Trim whitespace from all column names."""
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    return out


def coerce_join_keys(df: pd.DataFrame, year_col: str = "year", week_col: str = "week") -> pd.DataFrame:
    """Coerce join keys to nullable integer type."""
    out = df.copy()
    out[year_col] = pd.to_numeric(out[year_col], errors="coerce").astype("Int64")
    out[week_col] = pd.to_numeric(out[week_col], errors="coerce").astype("Int64")
    return out


def parse_dengue_week_range(value: object) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Parse a dengue week_date_range string into start/end timestamps."""
    if value is None or pd.isna(value):
        return (pd.NaT, pd.NaT)

    text = str(value).strip()
    if not text:
        return (pd.NaT, pd.NaT)

    pattern = re.compile(
        r"^([A-Za-z]+)\s+(\d{1,2})(?:\s*[-–—]\s*([A-Za-z]+)?\s*(\d{1,2}))?,\s*(\d{4})$"
    )
    match = pattern.match(text)
    if not match:
        return (pd.NaT, pd.NaT)

    start_month_name, start_day, end_month_name, end_day, year = match.groups()
    end_month_name = end_month_name or start_month_name

    try:
        start = datetime.strptime(f"{start_month_name} {start_day} {year}", "%B %d %Y")
        end = datetime.strptime(f"{end_month_name} {end_day} {year}", "%B %d %Y")
    except ValueError:
        return (pd.NaT, pd.NaT)

    return (pd.Timestamp(start), pd.Timestamp(end))


def build_combined(cases_path: Path, climate_path: Path, join_type: str) -> pd.DataFrame:
    """Load source CSVs and return merged combined dataframe."""
    cases = pd.read_csv(cases_path)
    climate = pd.read_csv(climate_path)

    cases = normalize_columns(cases)
    climate = normalize_columns(climate)

    # Standardize dengue and climate keys and parse the actual weekly date ranges.
    cases = cases.rename(columns={"year": "dengue_year", "week": "dengue_week"})
    climate = climate.rename(columns={"Year": "climate_year", "Week": "climate_week"})

    missing_cases = [c for c in ["dengue_year", "dengue_week", "week_date_range"] if c not in cases.columns]
    missing_clim = [c for c in ["climate_year", "climate_week", "Week_Start", "Week_End"] if c not in climate.columns]
    if missing_cases:
        raise ValueError(f"Missing join key(s) in cases file: {missing_cases}")
    if missing_clim:
        raise ValueError(f"Missing join key(s) in climate file: {missing_clim}")

    cases = coerce_join_keys(cases, "dengue_year", "dengue_week")
    climate = coerce_join_keys(climate, "climate_year", "climate_week")

    dengue_dates = cases["week_date_range"].apply(parse_dengue_week_range)
    cases["dengue_week_start"] = dengue_dates.apply(lambda pair: pair[0])
    cases["dengue_week_end"] = dengue_dates.apply(lambda pair: pair[1])

    climate["Week_Start"] = pd.to_datetime(climate["Week_Start"], errors="coerce")
    climate["Week_End"] = pd.to_datetime(climate["Week_End"], errors="coerce")

    cases_with_dates = cases[cases["dengue_week_start"].notna() & cases["dengue_week_end"].notna()].copy()
    cases_without_dates = cases[cases["dengue_week_start"].isna() | cases["dengue_week_end"].isna()].copy()

    date_merged = cases_with_dates.merge(
        climate,
        left_on=["dengue_week_start", "dengue_week_end"],
        right_on=["Week_Start", "Week_End"],
        how=join_type,
        indicator=True,
    )

    fallback = cases_without_dates.merge(
        climate,
        left_on=["dengue_year", "dengue_week"],
        right_on=["climate_year", "climate_week"],
        how="left",
    )

    fallback_keys = {
        (int(row.climate_year), int(row.climate_week))
        for row in fallback.itertuples(index=False)
        if pd.notna(row.climate_year) and pd.notna(row.climate_week)
    }

    if fallback_keys:
        def in_fallback_keys(row: pd.Series) -> bool:
            if pd.isna(row["climate_year"]) or pd.isna(row["climate_week"]):
                return False
            return (int(row["climate_year"]), int(row["climate_week"])) in fallback_keys

        date_merged = date_merged[
            ~(
                (date_merged["_merge"] == "right_only")
                & date_merged.apply(in_fallback_keys, axis=1)
            )
        ].copy()

    combined = pd.concat([date_merged.drop(columns=["_merge"]), fallback], ignore_index=True, sort=False)

    sort_key = combined["dengue_week_start"].combine_first(combined["Week_Start"])
    combined = combined.assign(_sort_key=sort_key)
    combined = combined.sort_values(["_sort_key", "dengue_year", "dengue_week"], na_position="last").drop(columns=["_sort_key"]).reset_index(drop=True)

    return combined


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge dengue and climate weekly CSVs into combined_data_test.csv")
    parser.add_argument(
        "--cases",
        default=None,
        help="Path to dengue_cases.csv (default: FinalProject/Data/dengue_cases.csv)",
    )
    parser.add_argument(
        "--climate",
        default=None,
        help="Path to weekly_averages.csv (default: FinalProject/Data/weekly_averages.csv)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output CSV path (default: FinalProject/Data/combined_data_test.csv)",
    )
    parser.add_argument(
        "--how",
        default="outer",
        choices=["outer", "inner", "left", "right"],
        help="Join type for merge on (year, week). Default: outer",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent
    data_dir = project_dir / "Data"

    cases_path = Path(args.cases) if args.cases else data_dir / "dengue_cases.csv"
    climate_path = Path(args.climate) if args.climate else data_dir / "weekly_averages.csv"
    output_path = Path(args.output) if args.output else data_dir / "combined_data_test.csv"

    if not cases_path.exists():
        raise FileNotFoundError(f"Cases file not found: {cases_path}")
    if not climate_path.exists():
        raise FileNotFoundError(f"Climate file not found: {climate_path}")

    combined = build_combined(cases_path, climate_path, args.how)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output_path, index=False)

    print(f"Wrote: {output_path}")
    print(f"Rows: {len(combined)}")
    print(f"Columns: {len(combined.columns)}")
    print(f"Join type: {args.how}")


if __name__ == "__main__":
    main()
