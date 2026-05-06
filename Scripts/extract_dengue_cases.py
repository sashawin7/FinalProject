"""
Extract dengue case counts from Florida DOH Arbovirus Surveillance Weekly Reports.

Parses each weekly PDF report and extracts:
  - Weekly travel-associated dengue cases reported that week
  - Cumulative travel-associated dengue cases (year-to-date)
  - Weekly locally acquired dengue cases reported that week
  - Cumulative locally acquired dengue cases (year-to-date)

Outputs a CSV file: dengue_cases.csv
"""

import csv
import re
from pathlib import Path

import pdfplumber

# === Configuration ===
# WeeklyReports lives at HealthDataScience/WeeklyReports
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "WeeklyReports"
# Output CSV goes into the Project/Data folder
OUTPUT_CSV = Path(__file__).resolve().parent.parent / "Data" / "dengue_cases.csv"

# Word-to-number mapping for written-out numbers in the reports
WORD_TO_NUM = {
    "zero": 0, "no": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "twenty-one": 21, "twenty-two": 22, "twenty-three": 23, "twenty-four": 24,
    "twenty-five": 25, "twenty-six": 26, "twenty-seven": 27, "twenty-eight": 28,
    "twenty-nine": 29, "thirty": 30, "thirty-one": 31, "thirty-two": 32,
    "thirty-three": 33, "thirty-four": 34, "thirty-five": 35, "thirty-six": 36,
    "thirty-seven": 37, "thirty-eight": 38, "thirty-nine": 39, "forty": 40,
    "forty-one": 41, "forty-two": 42, "forty-three": 43, "forty-four": 44,
    "forty-five": 45, "forty-six": 46, "forty-seven": 47, "forty-eight": 48,
    "forty-nine": 49, "fifty": 50, "fifty-one": 51, "fifty-two": 52,
    "fifty-three": 53, "fifty-four": 54, "fifty-five": 55, "fifty-six": 56,
    "fifty-seven": 57, "fifty-eight": 58, "fifty-nine": 59, "sixty": 60,
    "sixty-one": 61, "sixty-two": 62, "sixty-three": 63, "sixty-four": 64,
    "sixty-five": 65, "sixty-six": 66, "sixty-seven": 67, "sixty-eight": 68,
    "sixty-nine": 69, "seventy": 70, "seventy-one": 71, "seventy-two": 72,
    "seventy-three": 73, "seventy-four": 74, "seventy-five": 75,
    "seventy-six": 76, "seventy-seven": 77, "seventy-eight": 78,
    "seventy-nine": 79, "eighty": 80, "eighty-one": 81, "eighty-two": 82,
    "eighty-three": 83, "eighty-four": 84, "eighty-five": 85, "eighty-six": 86,
    "eighty-seven": 87, "eighty-eight": 88, "eighty-nine": 89, "ninety": 90,
    "ninety-one": 91, "ninety-two": 92, "ninety-three": 93, "ninety-four": 94,
    "ninety-five": 95, "ninety-six": 96, "ninety-seven": 97,
    "ninety-eight": 98, "ninety-nine": 99,
    # Hundreds are rarely written out, but just in case
    "one hundred": 100,
}


def parse_number(text):
    """
    Parse a number from text that may be a digit string or a written-out number.
    Returns int or None if not parseable.
    """
    text = text.strip().lower()

    # Try direct numeric parse (handles "303", "1,234", etc.)
    numeric = text.replace(",", "")
    try:
        return int(numeric)
    except ValueError:
        pass

    # Try word-to-number lookup
    if text in WORD_TO_NUM:
        return WORD_TO_NUM[text]

    return None


def extract_dengue_data(pdf_path):
    """
    Extract dengue case data from a single weekly report PDF.

    Returns a dict with:
        - weekly_travel: cases reported that week (travel-associated)
        - cumulative_travel: year-to-date travel cases
        - weekly_local: cases reported that week (locally acquired)
        - cumulative_local: year-to-date local cases
        - week_date_range: the date range string from the header
    """
    result = {
        "weekly_travel": None,
        "cumulative_travel": None,
        "weekly_local": None,
        "cumulative_local": None,
        "week_date_range": None,
    }

    # Prefer cumulative counts for the same year as the report file.
    report_year = None
    m_year = re.search(r"(\d{4})_Week\d+", pdf_path.stem)
    if m_year:
        report_year = int(m_year.group(1))

    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Get text from page 1 (dengue summary is always on page 1)
            text = pdf.pages[0].extract_text()
            if not text:
                return result

            # Normalize whitespace (PDF text can have odd line breaks)
            text = " ".join(text.split())

            # Extract date range from header: "Week N: Month D-D, YYYY"
            date_match = re.search(
                r"Week\s+\d+:\s+([\w\s]+\d+[\s,\-–]+[\w\s]*\d+,?\s*\d{4})", text
            )
            if date_match:
                result["week_date_range"] = date_match.group(1).strip()

            # --- Weekly travel-associated dengue ---
            # Pattern: "X cases of dengue (fever) were reported this week"
            # Also handles "No cases of dengue were reported this week"
            # Note: early 2022 reports use "Dengue Fever" instead of "Dengue"
            weekly_travel_match = re.search(
                r"Travel-Associated Dengue(?:\s+Fever)?:\s*"
                r"([\w,\-]+(?:\s+[\w,\-]+)?)\s+cases?\s+of\s+dengue(?:\s+fever)?\s+(?:were|was)\s+reported\s+this\s+week",
                text, re.IGNORECASE
            )
            if weekly_travel_match:
                result["weekly_travel"] = parse_number(weekly_travel_match.group(1))
            elif re.search(r"Travel-Associated Dengue(?:\s+Fever)?:.*?No cases.*?reported this week", text, re.IGNORECASE):
                result["weekly_travel"] = 0

            # --- Cumulative travel-associated dengue ---
            # Pattern: "In YYYY, NNN travel-associated dengue (fever) cases have been reported"
            cum_travel_matches = list(re.finditer(
                r"In\s+(\d{4}),\s*([\d,]+)\s+travel(?:\s*-\s*|\s+)associated\s+dengue(?:\s+fever)?\s+cases?\s+have\s+been\s+reported",
                text,
                re.IGNORECASE,
            ))
            if cum_travel_matches:
                chosen = None
                if report_year is not None:
                    for match in cum_travel_matches:
                        if int(match.group(1)) == report_year:
                            chosen = match
                            break
                if chosen is None:
                    # Fallback: use the last match in the text (usually the most recent year).
                    chosen = cum_travel_matches[-1]
                result["cumulative_travel"] = parse_number(chosen.group(2))

            # --- Weekly locally acquired dengue ---
            # Pattern: "X case(s) of locally acquired dengue (fever) were/was reported this week"
            # Note: early 2022 uses "Dengue Fever Cases Acquired in Florida"
            weekly_local_match = re.search(
                r"Dengue(?:\s+Fever)?\s+Cases Acquired in Florida:\s*"
                r"([\w,\-]+(?:\s+[\w,\-]+)?)\s+cases?\s+of\s+locally(?:\s*-\s*|\s+)acquired\s+dengue(?:\s+fever)?\s+(?:were|was)\s+reported\s+this\s+week",
                text, re.IGNORECASE
            )
            if weekly_local_match:
                result["weekly_local"] = parse_number(weekly_local_match.group(1))
            elif re.search(r"Dengue(?:\s+Fever)?\s+Cases Acquired in Florida:.*?No cases.*?reported this week", text, re.IGNORECASE):
                result["weekly_local"] = 0

            # --- Cumulative locally acquired dengue ---
            # Multiple patterns observed:
            # "In YYYY, NNN cases of locally acquired dengue (fever) have been reported"
            # "positive samples from NNN humans"
            cum_local_matches = list(re.finditer(
                r"Dengue(?:\s+Fever)?\s+Cases Acquired in Florida:.*?In\s+(\d{4}),\s*"
                r"([\d,]+|[a-z\-]+(?:\s+[a-z\-]+)?)\s+cases?\s+of\s+locally(?:\s*-\s*|\s+)acquired\s+dengue(?:\s+fever)?\s+have\s+been\s+reported",
                text,
                re.IGNORECASE,
            ))
            if cum_local_matches:
                chosen = None
                if report_year is not None:
                    for match in cum_local_matches:
                        if int(match.group(1)) == report_year:
                            chosen = match
                            break
                if chosen is None:
                    chosen = cum_local_matches[-1]
                result["cumulative_local"] = parse_number(chosen.group(2))
            else:
                # Some reports say "no cases of locally acquired dengue (fever) have been reported"
                no_local_match = re.search(
                    r"Dengue(?:\s+Fever)?\s+Cases Acquired in Florida:.*?no cases of locally(?:\s*-\s*|\s+)acquired dengue(?:\s+fever)? have been reported",
                    text, re.IGNORECASE
                )
                if no_local_match:
                    result["cumulative_local"] = 0

    except Exception as e:
        print(f"  ERROR reading {pdf_path.name}: {e}")

    return result


def main():
    print(f"Scanning PDFs in: {REPORTS_DIR.resolve()}")

    # Collect all weekly report PDFs
    pdf_files = []
    for year_dir in sorted(REPORTS_DIR.iterdir()):
        if year_dir.is_dir() and year_dir.name.isdigit():
            for pdf in sorted(year_dir.glob("*.pdf")):
                # Parse year and week from filename: YYYY_WeekNN.pdf
                m = re.match(r"(\d{4})_Week(\d+)\.pdf", pdf.name)
                if m:
                    pdf_files.append((int(m.group(1)), int(m.group(2)), pdf))

    pdf_files.sort(key=lambda x: (x[0], x[1]))
    print(f"Found {len(pdf_files)} weekly report PDFs.\n")

    # Extract dengue data from each PDF
    rows = []
    for year, week, pdf_path in pdf_files:
        print(f"  Processing {year} Week {week:02d}...", end="")
        data = extract_dengue_data(pdf_path)
        row = {
            "year": year,
            "week": week,
            "week_date_range": data["week_date_range"] or "",
            "weekly_travel_cases": data["weekly_travel"] if data["weekly_travel"] is not None else "",
            "cumulative_travel_cases": data["cumulative_travel"] if data["cumulative_travel"] is not None else "",
            "weekly_local_cases": data["weekly_local"] if data["weekly_local"] is not None else "",
            "cumulative_local_cases": data["cumulative_local"] if data["cumulative_local"] is not None else "",
        }
        rows.append(row)

        # Show extracted values
        wt = data["weekly_travel"]
        ct = data["cumulative_travel"]
        wl = data["weekly_local"]
        cl = data["cumulative_local"]
        print(f"  travel: {wt} (cum: {ct}), local: {wl} (cum: {cl})")

    # Write CSV
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "year", "week", "week_date_range",
        "weekly_travel_cases", "cumulative_travel_cases",
        "weekly_local_cases", "cumulative_local_cases",
    ]

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nCSV written to: {OUTPUT_CSV.resolve()}")
    print(f"Total rows: {len(rows)}")

    # Summary of any missing data
    missing_travel = sum(1 for r in rows if r["weekly_travel_cases"] == "")
    missing_local = sum(1 for r in rows if r["weekly_local_cases"] == "")
    if missing_travel or missing_local:
        print(f"\nWarning: Could not extract weekly travel cases for {missing_travel} reports")
        print(f"Warning: Could not extract weekly local cases for {missing_local} reports")


if __name__ == "__main__":
    main()
