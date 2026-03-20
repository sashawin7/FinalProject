"""
Extract county-level locally acquired dengue case counts from Florida DOH
Arbovirus Surveillance Weekly Reports.

Strategy:
  Each report lists cumulative year-to-date (YTD) locally acquired dengue cases
  per county in a prose paragraph under "Dengue Cases Acquired in Florida".
  Example:
    "In 2023, 186 cases of locally acquired dengue have been reported in
     Broward (4), Hardee (19), Miami-Dade (161), Palm Beach, and Polk counties
     with onsets in January, ..."

  We extract those cumulative totals from every weekly report, then compute
  week-over-week differences to infer where new cases appeared each week.
  The inferred new cases are cross-validated against the statewide weekly counts
  in dengue_cases.csv.

  Edge cases handled:
    - Early-year reports contain a PREVIOUS-year paragraph alongside the
      current-year paragraph; the regex is anchored on the current year to
      skip it automatically.
    - Counties listed without a parenthetical count (e.g. "Palm Beach") are
      assigned a count of 1 (validated: 4+19+161+1+1 = 186 for 2023 example).
    - Weeks where cumulative parsing returns empty but prior weeks had counted
      cases are treated as parse failures; the previous baseline is preserved
      and a warning is printed.

Output:
  dengue_county_cases.csv — long format, one row per (year, week, county)
    year | week | county | cumulative_cases | inferred_new_cases
"""

import csv
import re
from collections import defaultdict
from pathlib import Path

import pdfplumber

# === Configuration ===
# WeeklyReports lives at HealthDataScience/WeeklyReports (4 levels up from this script)
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "WeeklyReports"
OUTPUT_CSV = Path(__file__).resolve().parent.parent / "Data" / "dengue_county_cases.csv"
DENGUE_CASES_CSV = Path(__file__).resolve().parent.parent / "Data" / "dengue_cases.csv"


def parse_county_segment(segment):
    """
    Parse a county list segment extracted from the locally acquired paragraph.

    Examples of input:
      "Broward (4), Hardee (19), Miami-Dade (161), Palm Beach, and Polk"
      "Miami-Dade and Pasco"
      "Miami-Dade"

    Returns dict: {county_name: cumulative_count}
    Counties without a parenthetical count are assigned count = 1.
    """
    # Normalize: replace ", and " and bare " and " with ", " to unify separators
    segment = re.sub(r",?\s+and\s+", ", ", segment.strip())

    result = {}
    for token in [t.strip() for t in segment.split(",") if t.strip()]:
        # Match optional trailing count: "Miami-Dade (161)" or "Broward (4)"
        m = re.match(r"^(.+?)\s*\((\d+)\)\s*$", token)
        if m:
            county = m.group(1).strip().title()
            count = int(m.group(2))
        else:
            county = token.strip().title()
            count = 1
        if county:
            result[county] = count
    return result


def extract_cumulative_county_counts(text, year):
    """
    Extract cumulative YTD locally acquired dengue county counts for `year`
    from normalized (whitespace-collapsed) PDF page text.

    Returns dict {county: count}, or {} if no locally acquired cases are found
    (either truly zero cases or paragraph not matched).
    """
    # Pattern anchored on the current year so early-year PDFs that still show
    # the previous year's paragraph are not mistakenly parsed.
    #
    # [^.]*? for the count expression: prevents crossing a period (sentence
    # boundary) to reach a different paragraph. Case counts never contain
    # periods (e.g. "186", "two", "twenty-three").
    #
    # .{0,250}? for the county list: length-capped non-greedy match that
    # still allows "St. Johns"-style names with internal periods.
    pattern = re.compile(
        r"\bIn\s+" + str(year) + r",\s+"
        r"[^.]*?"  # count expression — stays within one sentence
        r"\s+cases?\s+of\s+locally\s+acquired\s+"
        r"dengue(?:\s+fever)?\s+(?:have|has)\s+been\s+reported\s+in\s+"
        r"(.{0,250}?)"  # county list — capped at 250 chars
        r"\s+count(?:y|ies)\b",
        re.IGNORECASE,
    )
    m = pattern.search(text)
    if m:
        return parse_county_segment(m.group(1))
    return {}


def load_known_weekly_local_cases():
    """
    Load statewide weekly locally acquired case counts from dengue_cases.csv.
    Returns {(year, week): int}.
    """
    known = {}
    try:
        with open(DENGUE_CASES_CSV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                val = row.get("weekly_local_cases", "").strip()
                if val:
                    known[(int(row["year"]), int(row["week"]))] = int(val)
    except FileNotFoundError:
        print(f"  Note: {DENGUE_CASES_CSV.name} not found; skipping validation.")
    return known


def main():
    print(f"Scanning PDFs in: {REPORTS_DIR.resolve()}\n")

    # Collect all weekly report PDFs
    pdf_files = []
    for year_dir in sorted(REPORTS_DIR.iterdir()):
        if year_dir.is_dir() and year_dir.name.isdigit():
            for pdf in sorted(year_dir.glob("*.pdf")):
                m = re.match(r"(\d{4})_Week(\d+)\.pdf", pdf.name)
                if m:
                    pdf_files.append((int(m.group(1)), int(m.group(2)), pdf))

    pdf_files.sort(key=lambda x: (x[0], x[1]))
    print(f"Found {len(pdf_files)} weekly report PDFs.\n")

    # --- Phase 1: extract cumulative county counts from each PDF ---
    cumulative_data = {}  # {(year, week): {county: cumulative_count}}

    for year, week, pdf_path in pdf_files:
        print(f"  {year} Week {week:02d} ... ", end="")
        try:
            with pdfplumber.open(pdf_path) as pdf:
                raw = " ".join(
                    (page.extract_text() or "") for page in pdf.pages
                )
            # Normalize whitespace: collapse newlines and extra spaces
            text = " ".join(raw.split())
            # Fix PDF hyphen line-break artifacts (e.g. "Miami- Dade" -> "Miami-Dade")
            text = re.sub(r"(\w)-\s+(\w)", r"\1-\2", text)
            counts = extract_cumulative_county_counts(text, year)
            cumulative_data[(year, week)] = counts
            if counts:
                print(", ".join(f"{c}: {n}" for c, n in sorted(counts.items())))
            else:
                print("(no locally acquired cases)")
        except Exception as e:
            print(f"ERROR: {e}")
            cumulative_data[(year, week)] = {}

    # --- Phase 2: compute week-over-week diffs to infer new cases per county ---
    print("\nComputing week-over-week diffs...")
    output_rows = []
    years = sorted({y for y, _, _ in pdf_files})

    for year in years:
        weeks = sorted(w for y, w, _ in pdf_files if y == year)
        prev = {}  # {county: cumulative_count} from previous week

        for week in weeks:
            curr = cumulative_data.get((year, week), {})

            # Detect likely parse failure: cumulative total dropped to zero
            # mid-year when previous week had counted cases.
            prev_total = sum(prev.values())
            curr_total = sum(curr.values())
            if prev_total > 0 and curr_total == 0:
                print(
                    f"  WARNING: {year} Week {week:02d} — county parse returned empty "
                    f"but prior week had {prev_total} cumulative cases (possible parse "
                    f"failure). Preserving previous baseline; no rows emitted this week."
                )
                # Don't update prev; skip row emission for this week
                continue

            for county in sorted(curr.keys()):
                cum = curr[county]
                inferred = cum - prev.get(county, 0)

                if inferred < 0:
                    print(
                        f"  WARNING: Negative diff — {county} {year} W{week:02d}: "
                        f"prev={prev.get(county, 0)}, curr={cum} → inferred={inferred}"
                    )

                if cum > 0:
                    output_rows.append(
                        {
                            "year": year,
                            "week": week,
                            "county": county,
                            "cumulative_cases": cum,
                            "inferred_new_cases": inferred,
                        }
                    )

            prev = curr

    # --- Phase 3: write output CSV ---
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["year", "week", "county", "cumulative_cases", "inferred_new_cases"]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"\nCSV written to: {OUTPUT_CSV.resolve()}")
    print(f"Total rows: {len(output_rows)}")

    # --- Phase 4: validate inferred county sums against statewide weekly counts ---
    known = load_known_weekly_local_cases()
    if not known:
        return

    print("\n=== Validation: sum of inferred county new cases vs statewide weekly count ===")

    # Sum inferred_new_cases per (year, week); ignore negatives to avoid double-counting
    inferred_sums = defaultdict(int)
    for row in output_rows:
        inferred_sums[(row["year"], row["week"])] += max(0, row["inferred_new_cases"])

    mismatches = []
    for (year, week), statewide in sorted(known.items()):
        inferred = inferred_sums.get((year, week), 0)
        if inferred != statewide:
            mismatches.append((year, week, statewide, inferred))

    if mismatches:
        print(f"\n{len(mismatches)} mismatch(es) found:")
        print(f"  {'Year':>4}  {'Week':>4}  {'Statewide':>9}  {'Inferred':>8}")
        for year, week, statewide, inferred in mismatches:
            print(f"  {year:>4}  {week:>4}  {statewide:>9}  {inferred:>8}")
    else:
        print("All weekly county sums match the statewide counts.")


if __name__ == "__main__":
    main()
