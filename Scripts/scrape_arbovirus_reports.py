"""
Webscraper for Florida Department of Health Arbovirus Surveillance Weekly Reports.
Downloads all weekly report PDFs from:
https://www.floridahealth.gov/statistics-data/population-surveillance/arbovirus-surveillance/

PDFs are organized into year subfolders inside the WeeklyReports directory.
"""

import os
import re
import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path

# === Configuration ===
BASE_URL = "https://www.floridahealth.gov/statistics-data/population-surveillance/arbovirus-surveillance/"
OUTPUT_DIR = Path(__file__).parent / "WeeklyReports"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
DELAY_BETWEEN_DOWNLOADS = 0.5  # seconds between requests (be polite to the server)


def fetch_pdf_links():
    """Scrape the page and return a list of (link_text, url) for all weekly report PDFs."""
    print(f"Fetching page: {BASE_URL}")
    response = requests.get(BASE_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    pdf_links = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if href.lower().endswith(".pdf"):
            # Filter to arbovirus-related PDFs only (weekly reports)
            if any(kw in href.lower() for kw in ["arbovirus", "arbbovirus", "arbo"]):
                text = a_tag.get_text(strip=True)
                pdf_links.append((text, href))

    # Deduplicate while preserving order
    seen = set()
    unique_links = []
    for text, url in pdf_links:
        if url not in seen:
            seen.add(url)
            unique_links.append((text, url))

    return unique_links


def classify_link(url):
    """
    Determine the year and week number from a PDF URL.
    Returns (year, week_number) or None if it's not a weekly report.
    
    Handles multiple URL naming conventions:
      - 2024-52-arbovirus-surveillance.pdf         (2024 format)
      - 2025Week32ArbovirusReport_8-9-25.pdf        (2025 format)
      - fl-arbovirus-report_w5-2026.pdf             (2026 format)
      - 2023-w50-arbovirus-surveillance-report.pdf  (2023 format with 'w' prefix)
      - 2023-week20-arbovirus-surveillance-report.pdf (2023 format with 'week' prefix)
      - 2022-week-20-arbovirus-surveillance-report.pdf (2022 format with 'week-' prefix)
      - fl-arbbovirus-report-1-10-26.pdf            (typo variant)
    """
    filename = url.split("/")[-1].lower()

    # Pattern: fl-arb(b)ovirus-report_wN-YYYY.pdf  (2026 format)
    m = re.search(r"fl-arb+ovirus-report_w(\d+)-(\d{4})", filename)
    if m:
        return (m.group(2), int(m.group(1)))

    # Pattern: fl-arbbovirus-report-M-D-YY.pdf (typo variant, 2026 week 1)
    m = re.search(r"fl-arb+ovirus-report-(\d+)-(\d+)-(\d{2})", filename)
    if m:
        return ("2026", 1)  # This is Week 1 of 2026

    # Pattern: YYYYWeekNNArbovirusReport_M-D-YY.pdf  (2025 format)
    m = re.search(r"(\d{4})week(\d+)arbovirusreport", filename)
    if m:
        return (m.group(1), int(m.group(2)))

    # Pattern: YYYY-wNN-arbovirus  (2023 format with 'w' prefix)
    m = re.search(r"(\d{4})-w(\d+)-arbo", filename)
    if m:
        return (m.group(1), int(m.group(2)))

    # Pattern: YYYY-weekNN-arbovirus  (2023/2022 format with 'week' prefix, no extra dash)
    m = re.search(r"(\d{4})-week(\d+)-arbo", filename)
    if m:
        return (m.group(1), int(m.group(2)))

    # Pattern: YYYY-week-NN-arbovirus  (2022 format with 'week-' prefix)
    m = re.search(r"(\d{4})-week-(\d+)-arbo", filename)
    if m:
        return (m.group(1), int(m.group(2)))

    # Pattern: YYYY-NN-arbovirus  (2024/2025 format, simple)
    m = re.search(r"(\d{4})-(\d+)-arbo", filename)
    if m:
        return (m.group(1), int(m.group(2)))

    # Not a weekly report (guidebook, appendix, etc.)
    return None


def make_filename(year, week, url):
    """Create a standardized filename: Year_WeekNN.pdf"""
    return f"{year}_Week{week:02d}.pdf"


def download_pdf(url, filepath):
    """Download a PDF file from url to filepath. Returns True on success."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=60, stream=True)
        response.raise_for_status()

        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except requests.RequestException as e:
        print(f"  ERROR downloading {url}: {e}")
        return False


def main():
    # Step 1: Fetch all PDF links
    all_links = fetch_pdf_links()
    print(f"Found {len(all_links)} unique arbovirus PDF links on the page.\n")

    # Step 2: Classify into weekly reports
    weekly_reports = []
    skipped = []
    for text, url in all_links:
        result = classify_link(url)
        if result:
            year, week = result
            weekly_reports.append((year, week, text, url))
        else:
            skipped.append((text, url))

    print(f"Weekly reports to download: {len(weekly_reports)}")
    if skipped:
        print(f"Skipped (non-weekly PDFs): {len(skipped)}")
        for text, url in skipped:
            print(f"  - {text}: {url.split('/')[-1]}")
    print()

    # Step 3: Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Step 4: Download all weekly reports, organized by year
    success_count = 0
    skip_count = 0
    fail_count = 0

    # Sort by year (descending) then week (descending) for nice output
    weekly_reports.sort(key=lambda x: (x[0], x[1]), reverse=True)

    for year, week, text, url in weekly_reports:
        year_dir = OUTPUT_DIR / str(year)
        year_dir.mkdir(parents=True, exist_ok=True)

        filename = make_filename(year, week, url)
        filepath = year_dir / filename

        if filepath.exists():
            print(f"  [SKIP] {year}/{filename} (already exists)")
            skip_count += 1
            continue

        print(f"  [DOWNLOADING] {year}/{filename} ...")
        if download_pdf(url, filepath):
            size_kb = filepath.stat().st_size / 1024
            print(f"    -> Saved ({size_kb:.0f} KB)")
            success_count += 1
        else:
            fail_count += 1

        time.sleep(DELAY_BETWEEN_DOWNLOADS)

    # Step 5: Summary
    print("\n" + "=" * 50)
    print("DOWNLOAD SUMMARY")
    print("=" * 50)
    print(f"  Downloaded:    {success_count}")
    print(f"  Already exist: {skip_count}")
    print(f"  Failed:        {fail_count}")
    print(f"  Total weekly:  {len(weekly_reports)}")
    print(f"  Output folder: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
