# Dengue-Climate Analysis — Florida 2022–2025

## Project Overview

This project analyzes the relationship between weekly climate variables and dengue
case counts in Florida from 2022–2025. The analysis is structured as a Jupyter
Notebook following the conventions of a scientific report with a data science
aesthetic. It serves as both a university course final project and an academic
research document.

**Research question:** Do temperature, relative humidity, and rainfall predict
weekly locally-acquired dengue case counts in Florida, and if so, at what lag?

---

## Folder Structure

```
FinalProject/
│
├── README.md                        ← This file. Project overview and reference.
├── CLAUDE.md                        ← Persistent instructions for Claude Code.
│                                       Read automatically at every session start.
│ 
├── FinalProject.ipynb                    ← Main working notebook. All analysis lives here.
│                                       Structured as: Introduction → Methods →
│                                       Data Import → EDA → Modeling → Conclusions.
│
├── eda_instructions.md              ← Full task prompt for the EDA section.
│                                       Reference when developing EDA steps.
│
├── Data/
│   ├── CountyData/
│   │   ├── dengue_county_cases.csv  ← County-level dengue case counts.
│   │   └── Dengue cases by jurisdiction...csv  ← Travel status breakdown by county.
│   │
│   ├── DailyClimatsCSVs/            ← Raw daily climate data from weather station(s).
│   │   ├── 2022_daily.csv           ← Daily weather: temperature, humidity, rainfall.
│   │   ├── 2023_daily.csv           ← (Same format for each year)
│   │   ├── 2024_daily.csv
│   │   ├── 2025_daily.csv
│   │   └── 2026_daily.csv
│   │
│   ├── WeeklyReports/               ← Location of FL DOH arbovirus surveillance reports.
│   │                                   (Points to ../../WeeklyReports for data extraction)
│   │
│   ├── dengue_cases.csv             ← Extracted weekly dengue case counts from PDF reports.
│   │                                   Columns: year, week, week_date_range,
│   │                                   weekly_travel_cases, cumulative_travel_cases,
│   │                                   weekly_local_cases, cumulative_local_cases.
│   │
│   ├── WorkingData_CombinedDengueAndClimate.csv  ← Merged dengue + climate at weekly level.
│   │                                                ~228 rows (one per epi week, 2022–2025).
│   │
│   ├── edited_combined_data.csv     ← Cleaned/consolidated version ready for analysis.
│   │                                   (Primary dataset used in FinalProject.ipynb)
│   │
│   └── weekly_averages.csv          ← Weekly climate aggregates.
│
├── Scripts/                          ← Data processing and extraction scripts.
│   ├── extract_dengue_cases.py      ← Parse FL DOH weekly PDF reports.
│   │                                   Outputs: Data/dengue_cases.csv
│   │
│   ├── extract_dengue_county_cases.py ← Extract county-level dengue counts.
│   │                                      Outputs: Data/CountyData/dengue_county_cases.csv
│   │
│   ├── scrape_arbovirus_reports.py  ← Fetch/organize weekly PDF reports from DOH website.
│   │                                   Outputs: ../../WeeklyReports/
│   │
│   ├── update_combined_data.py      ← Merge dengue and climate data to weekly level.
│   │                                   Outputs: Data/WorkingData_CombinedDengueAndClimate.csv
│   │
│   └── weekly_averages.py           ← Aggregate daily climate data to weekly means.
│                                       Outputs: Data/weekly_averages.csv
│
├── SecondaryNotebooks/
│   ├── MainProj.IPYNB               ← Backup/archival copy of main notebook.
│   └── WorkingNotebook.ipynb        ← Secondary working notebook (exploration/testing).
│
├── _tmp_climate_stats.py            ← Climate variable summary statistics.
├── _tmp_results_details.py          ← Detailed model results formatting.
└── _tmp_results_headline.py         ← Summary headline findings.
```

---

## Dataset Description

**File:** `Data/WorkingData_CombinedDengueAndClimate.csv` (primary working dataset)
**Rows:** 228 (one row per epidemiological week)
**Time range:** 2022–2025
**Missingness:** ~25 rows with partial gaps in dengue and/or climate columns
**Source:** Merged from `Data/dengue_cases.csv` and aggregated daily climate data

### Columns

| Column | Description |
|--------|-------------|
| `dengue_year` | Epidemiological year |
| `dengue_week` | Epidemiological week number |
| `week_date_range` | Human-readable date range string |
| `weekly_travel_cases` | New travel-associated dengue cases that week |
| `cumulative_travel_cases` | Running total of travel cases for the year |
| `weekly_local_cases` | New locally-acquired dengue cases that week (**primary outcome**) |
| `cumulative_local_cases` | Running total of local cases for the year |
| `dengue_week_start` | Start date of the epidemiological week (parse as datetime) |
| `dengue_week_end` | End date of the epidemiological week (parse as datetime) |
| `climate_year` | Year of climate observation |
| `climate_week` | Climate week number (should match `dengue_week`) |
| `Week_Start` | Climate week start date |
| `Week_End` | Climate week end date |
| `Temp @ 60cm (C) Avg (Weekly Avg)` | Temperature at 60cm height — **drop after consolidation** |
| `Temp @ 2m (C) Avg (Weekly Avg)` | Temperature at 2m height — **primary temperature variable** |
| `Temp @ 10m (C) Avg (Weekly Avg)` | Temperature at 10m height — **drop after consolidation** |
| `Relative Humidity (%) Avg (Weekly Avg)` | Weekly average relative humidity |
| `Rainfall Amount (in) Sum (Weekly Avg)` | Weekly average rainfall in inches |

### Key Variable Notes

- **Primary outcome:** `weekly_local_cases` — locally acquired dengue, driven by
  Florida climate and local mosquito populations
- **Secondary outcome:** `weekly_travel_cases` — imported cases, not climate-driven,
  but may serve as a leading indicator of local transmission
- **Temperature:** Three height measures are provided but highly collinear. The 2m
  measure is the biological standard for vector studies. The 60cm and 10m columns
  are dropped in Section 1 of EDA after correlation is confirmed
- **Rainfall:** Measured in inches. Right-skewed — storm weeks produce extreme values

---

## Notebook Structure

The notebook (`FinalProject.ipynb`) is organized as follows:

| Section | Status | Description |
|---------|--------|-------------|
| Introduction | — | Background, motivation, research questions |
| Methods | — | Data sources, analytical approach |
| Data Import & Verification | — | Load, inspect, clean, consolidate temperature |
| EDA | 🔄 In progress | Full exploratory analysis (see `eda_instructions.md`) |
| Modeling | — | Regression and ML analysis (planned) |
| Conclusions | — | Summary, limitations, future directions |

Update the Status column as sections are completed.

---

## Working with Claude Code

### Starting a session
1. Open this folder in VS Code (`File → Open Folder → FinalProject/`)
2. Open the Claude Code panel
3. Run `/model opus` — use Opus for all analytical work
4. Claude Code reads `CLAUDE.md` automatically — no need to restate conventions

### Running the EDA section
Give Claude Code this message:
> "Read `README.md` and `eda_instructions.md`. Then build out the EDA
> section of `FinalProject.ipynb` following all conventions in
> `CLAUDE.md`. The data is in `Data/edited_combined_data.csv`. Confirm your
> understanding before writing any code."

### Resuming a session mid-task
> "Read `README.md` and `eda_instructions.md`. The EDA section is
> partially complete — sections [X] through [Y] are done. Continue from section [Z]
> following all conventions in `CLAUDE.md`."

### If the model drifts from conventions
> "Stop. Re-read `CLAUDE.md`. You missed [specific convention]. Fix the last cell
> and then continue."

---


## Dependencies

All required packages. Install any missing ones with `pip install [package]`:

```
numpy
pandas
scipy
seaborn
matplotlib
missingno
statsmodels
```
