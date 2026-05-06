"""
Compute weekly averages (Sunday–Saturday calendar weeks) of selected weather
variables from yearly daily CSV files.

For each calendar week the script:
  1. Averages each variable's daily values per station within that week.
  2. Averages the station-level means to produce a single cross-station value.

Output: a single combined CSV written to the project Data/ folder.

Usage:
    python weekly_averages.py                       # process all *_daily.csv files
    python weekly_averages.py 2024_daily.csv        # process specific file(s)
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TARGET_COLUMNS: Tuple[str, ...] = (
    "Temp @ 60cm (C) Avg",
    "Temp @ 2m (C) Avg",
    "Temp @ 10m (C) Avg",
    "Relative Humidity (%) Avg",
    "Rainfall Amount (in) Sum",
)

# Date formats observed in the data (tried in order)
DATE_FORMATS: Tuple[str, ...] = (
    "%Y-%m-%d %H:%M:%S",   # 2022-01-01 00:00:00
    "%m/%d/%y %H:%M",       # 1/1/24 0:00
    "%m/%d/%Y %H:%M",       # 1/1/2024 0:00
    "%Y-%m-%d",              # bare date
)

OUTPUT_FILENAME = "weekly_averages.csv"

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_date(raw: str) -> Optional[datetime]:
    """Try multiple date formats; return *None* on failure."""
    raw = raw.strip()
    if not raw:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def safe_float(value: str) -> Optional[float]:
    """Convert a string to float, returning *None* for blanks / bad values."""
    value = value.strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def iso_calendar_week_sunday(dt: datetime) -> Tuple[int, int]:
    """Return (year, week_number) for a Sunday–Saturday calendar week.

    Week 1 of a year is the week containing Jan 1.  The week starts on
    Sunday (weekday index 6 in Python's Monday-is-0 scheme).

    We use ``strftime('%U')`` which yields the "week number of the year
    (Sunday as first day)" and is zero-padded.  Week 0 contains any days
    before the first Sunday; we keep it as week 0 so no data is lost.
    """
    week_num = int(dt.strftime("%U"))
    return dt.year, week_num


def mean(values: Sequence[float]) -> Optional[float]:
    """Return the arithmetic mean, or *None* if the sequence is empty."""
    if not values:
        return None
    return sum(values) / len(values)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def validate_header(header: List[str], filepath: str) -> None:
    """Raise if required columns are missing from the header."""
    required = {"StationID", "Date Time"} | set(TARGET_COLUMNS)
    missing = required - set(header)
    if missing:
        raise ValueError(
            f"{filepath}: missing required columns: {', '.join(sorted(missing))}"
        )


def process_file(filepath: str) -> Dict[Tuple[int, int], Dict[str, List[float]]]:
    """Read one CSV and return station-averaged weekly data.

    Returns
    -------
    dict
        {(year, week): {column_name: [station_means]}}
    """
    logger.info("Processing %s …", filepath)

    # --- read rows ---------------------------------------------------------
    with open(filepath, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ValueError(f"{filepath}: file appears empty or has no header")
        validate_header(list(reader.fieldnames), filepath)
        rows = list(reader)

    if not rows:
        logger.warning("%s contains no data rows – skipping.", filepath)
        return {}

    # --- organise by (year, week, station) ---------------------------------
    # {(year, week, station): {col: [values]}}
    bucket: Dict[Tuple[int, int, str], Dict[str, List[float]]] = {}
    skipped_dates = 0
    skipped_header_rows = 0

    for row_num, row in enumerate(rows, start=2):  # row 1 is header
        station = row.get("StationID", "").strip()

        # Guard against duplicate header rows embedded in data
        if station == "StationID":
            skipped_header_rows += 1
            continue

        if not station:
            logger.debug("Row %d: blank StationID – skipping.", row_num)
            continue

        dt = parse_date(row.get("Date Time", ""))
        if dt is None:
            skipped_dates += 1
            logger.debug(
                "Row %d: unparseable date '%s' – skipping.",
                row_num,
                row.get("Date Time", ""),
            )
            continue

        year, week = iso_calendar_week_sunday(dt)
        key = (year, week, station)

        if key not in bucket:
            bucket[key] = {col: [] for col in TARGET_COLUMNS}

        for col in TARGET_COLUMNS:
            val = safe_float(row.get(col, ""))
            if val is not None:
                bucket[key][col].append(val)

    if skipped_dates:
        logger.warning(
            "%s: %d row(s) skipped due to unparseable dates.", filepath, skipped_dates
        )
    if skipped_header_rows:
        logger.info(
            "%s: %d duplicate header row(s) removed.", filepath, skipped_header_rows
        )

    # --- station means per week -------------------------------------------
    # {(year, week): {col: [station_mean, ...]}}
    weekly: Dict[Tuple[int, int], Dict[str, List[float]]] = {}

    for (year, week, _station), col_values in bucket.items():
        wk_key = (year, week)
        if wk_key not in weekly:
            weekly[wk_key] = {col: [] for col in TARGET_COLUMNS}

        for col in TARGET_COLUMNS:
            station_mean = mean(col_values[col])
            if station_mean is not None:
                weekly[wk_key][col].append(station_mean)

    return weekly


def merge_weekly(
    *results: Dict[Tuple[int, int], Dict[str, List[float]]],
) -> Dict[Tuple[int, int], Dict[str, List[float]]]:
    """Merge multiple per-file weekly dicts (should not overlap, but is safe)."""
    merged: Dict[Tuple[int, int], Dict[str, List[float]]] = {}
    for result in results:
        for wk_key, cols in result.items():
            if wk_key not in merged:
                merged[wk_key] = {col: [] for col in TARGET_COLUMNS}
            for col in TARGET_COLUMNS:
                merged[wk_key][col].extend(cols[col])
    return merged


def write_output(
    weekly: Dict[Tuple[int, int], Dict[str, List[float]]],
    output_path: str,
) -> None:
    """Write the final CSV with one row per (year, week)."""
    header = ["Year", "Week", "Week_Start", "Week_End"] + [
        f"{col} (Weekly Avg)" for col in TARGET_COLUMNS
    ]

    sorted_keys = sorted(weekly.keys())

    with open(output_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)

        for year, week in sorted_keys:
            # Compute the Sunday start of this calendar week
            # Jan 1 is in week 0 if it's not a Sunday; week 1 starts on
            # the first Sunday.  We recreate the date from (year, week).
            jan1 = datetime(year, 1, 1)
            jan1_weekday = jan1.weekday()  # Mon=0 … Sun=6
            # Days from Jan 1 to the first Sunday
            days_to_first_sunday = (6 - jan1_weekday) % 7
            if week == 0:
                week_start = jan1
                week_end = jan1 + timedelta(days=max(days_to_first_sunday - 1, 0))
            else:
                week_start = jan1 + __import__("datetime").timedelta(
                    days=days_to_first_sunday + (week - 1) * 7
                )
                week_end = week_start + timedelta(days=6)

            row_data: List = [
                year,
                week,
                week_start.strftime("%Y-%m-%d"),
                week_end.strftime("%Y-%m-%d"),
            ]
            for col in TARGET_COLUMNS:
                avg = mean(weekly[(year, week)][col])
                row_data.append(f"{avg:.4f}" if avg is not None else "")

            writer.writerow(row_data)

    logger.info("Wrote %d weekly rows to %s", len(sorted_keys), output_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def discover_csv_files(data_dir: str) -> List[str]:
    """Return sorted list of *_daily.csv files in *data_dir*."""
    files = sorted(
        str(p)
        for p in Path(data_dir).glob("*_daily.csv")
        if p.is_file()
    )
    return files


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Compute weekly averages from daily weather station CSVs.",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help=(
            "CSV file(s) to process. If omitted, all *_daily.csv files "
            "in the Data/ directory are processed."
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help=f"Output CSV path (default: Data/{OUTPUT_FILENAME}).",
    )
    args = parser.parse_args(argv)

    # Resolve data directory (sibling of Scripts/)
    script_dir = Path(__file__).resolve().parent
    data_dir = script_dir.parent / "Data"

    # Determine input files
    if args.files:
        csv_files = []
        for f in args.files:
            p = Path(f)
            if not p.is_absolute():
                # Try relative to data dir first, then cwd
                candidate = data_dir / p
                if candidate.is_file():
                    p = candidate
                else:
                    p = Path.cwd() / f
            if not p.is_file():
                logger.error("File not found: %s", p)
                sys.exit(1)
            csv_files.append(str(p))
    else:
        csv_files = discover_csv_files(str(data_dir))
        if not csv_files:
            logger.error("No *_daily.csv files found in %s", data_dir)
            sys.exit(1)

    logger.info("Found %d file(s) to process.", len(csv_files))

    # Process each file
    all_results = []
    for filepath in csv_files:
        try:
            result = process_file(filepath)
            all_results.append(result)
        except Exception:
            logger.exception("Failed to process %s – skipping.", filepath)

    if not all_results:
        logger.error("No files were processed successfully.")
        sys.exit(1)

    merged = merge_weekly(*all_results)

    # Write output
    output_path = args.output or str(data_dir / OUTPUT_FILENAME)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    write_output(merged, output_path)

    logger.info("Done.")


if __name__ == "__main__":
    main()
