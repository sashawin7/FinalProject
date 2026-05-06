# EDA Instructions — Dengue Climate Analysis

## Before Starting

1. Read `CLAUDE.md` fully — all conventions defined there apply to every cell you write
2. Read `README.md` to understand the project structure and locate the data file
3. Confirm your understanding of both files before writing any code
4. Set your model to Opus: `/model opus`
5. The working notebook is `FinalProject.ipynb`. All work goes there

The working data is `data\WorkingData_CombinedDengueAndClimate.csv`. Parse `dengue_week_start` and
`dengue_week_end` as datetime columns at import.

---

## Task

Build the complete EDA section of `FinalProject.ipynb`. The EDA section consists
of seven subsections detailed below. Each subsection must be implemented in full —
do not skip or abbreviate any step. Follow the mandatory three-cell structure
(description → code → interpretation) from `CLAUDE.md` for every analysis step.

Work through the sections in order. After completing each major section (1 through 7),
pause and ask for confirmation before proceeding to the next. This allows for review
and course correction.

---

## Section 1 — Data Import and Verification

**Step 1.1 — Load the data**
Load the CSV from the `/data` folder into a dataframe `df` using `pd.read_csv()`.
Parse `dengue_week_start` and `dengue_week_end` as datetime using `parse_dates=[]`.
Immediately define all column name variables as specified in `CLAUDE.md`.

**Step 1.2 — Dataset shape**
Display `df.shape`. Narrative: state the number of rows (epidemiological weeks) and
columns, and briefly describe what the dataset represents.

**Step 1.3 — Data types and structure**
Display `df.info()`. Narrative: note the dtypes of each column and identify where
non-null counts reveal gaps before the formal missingness section.

**Step 1.4 — First rows**
Display `df.head()` — first 5 rows. Narrative: briefly orient the reader to the
structure of the data.

**Step 1.5 — Week alignment check**
Verify that `dengue_week` and `climate_week` columns match across all rows. Print
any rows where they differ. Narrative: confirm alignment or flag discrepancies and
explain their implications.

**Step 1.6 — Temperature consolidation**
Compute a Pearson correlation table of all three temperature columns:
`Temp @ 60cm (C) Avg (Weekly Avg)`, `Temp @ 2m (C) Avg (Weekly Avg)`, and
`Temp @ 10m (C) Avg (Weekly Avg)`. Display it as a formatted dataframe.
Then drop the 60cm and 10m columns from the working dataframe `df`.
Set `temp_col = 'Temp @ 2m (C) Avg (Weekly Avg)'`.
Narrative: explain the biological rationale — 2m air temperature is the standard
measure in vector-borne disease climate studies because it best reflects conditions
at the height where adult Aedes mosquitoes are active. The correlation table confirms
the three measures are redundant, justifying consolidation.

---

## Section 2 — Missingness Assessment

**Step 2.1 — Missingness table**
Compute `df.isnull().sum()`. Display as a clean table showing both count and
percentage missing per column. Format it clearly — not just a raw series output.

**Step 2.2 — Missingness matrix**
Plot `msno.matrix(df)`. Title: "Missingness Matrix". Narrative: describe where
gaps fall — are they clustered in a particular time window or randomly distributed?

**Step 2.3 — Completeness bar chart**
Plot `msno.bar(df)`. Title: "Variable Completeness". Narrative: identify which
variables are most affected by missingness.

**Step 2.4 — Deferral statement**
Write a narrative-only markdown cell (no code) explicitly stating: the decision of
whether to impute or exclude missing rows is deferred to the modeling section, where
it will be made based on the specific requirements of each method. Note whether
missingness appears to be co-occurring across dengue and climate columns (suggesting
a shared data collection gap) or independent (suggesting different source failures).

---

## Section 3 — Dengue Case Distributions

### 3.1 — Weekly Local Cases

**Step 3.1.1** — `df[local_col].describe()` and `stats.iqr(df[local_col])`.
Display together. Narrative: report mean, median, SD, IQR, min, max in prose.

**Step 3.1.2** — `df[local_col].value_counts()` and
`df[local_col].value_counts(normalize=True) * 100`.
Compute and explicitly state the percentage of weeks with zero local cases.

**Step 3.1.3** — `df.groupby(year_col)[local_col].describe()`.
Year-grouped summary table. Narrative: compare distributions across years.

**Step 3.1.4** — Histogram with KDE overlay using `sns.histplot(df[local_col], kde=True)`.
Title: "Distribution of Weekly Local Dengue Cases". Narrative: describe the shape —
note skew and zero-inflation explicitly.

**Step 3.1.5** — Box-and-whisker plot by year:
`sns.boxplot(x=year_col, y=local_col, data=df)`.
Title: "Weekly Local Cases by Year". Narrative: compare interannual spread and medians.

**Step 3.1.6** — Zero-week bar chart: for each year compute the proportion of weeks
with zero local cases and plot as a bar chart with year on x-axis and proportion on
y-axis. This is a dedicated visualization — do not infer it from the boxplot.
Title: "Proportion of Zero-Case Weeks by Year (Local Cases)".
Narrative: discuss what high zero-proportions imply for modeling.

**Step 3.1.7** — Write a consolidated interpretation markdown cell connecting all
3.1 findings: characterize the overall distribution, state the zero percentage
explicitly, and name the appropriate modeling error structure
(negative binomial or zero-inflated negative binomial).

### 3.2 — Weekly Travel-Associated Cases

Repeat the exact same steps 3.1.1 through 3.1.7 for `travel_col`.
Narrative cells must compare travel case findings to local case findings where
relevant, and discuss travel cases as a potential leading indicator of local
transmission.

### 3.3 — Side-by-Side Distribution Comparison

Create a single two-panel figure (side by side):
- Left panel: histogram of weekly local cases
- Right panel: histogram of weekly travel cases
- Use the same x-axis scale on both panels for direct comparison
- Title each panel and the overall figure

Narrative: directly compare the shapes, ranges, and zero-inflation between the two
outcome variables in a single paragraph.

---

## Section 4 — Climate Variable Distributions

For each of the three climate variables below, produce the following identical
five-step structure. Label each subsection clearly (4.1, 4.2, 4.3).

**Variables:**
- 4.1: 2m Air Temperature (`temp_col`)
- 4.2: Relative Humidity (`humidity_col`)
- 4.3: Rainfall (`rainfall_col`)

**Repeated structure for each variable:**

**Step A** — `.describe()` and `stats.iqr()`. Display together.
Narrative: report key statistics in prose.

**Step B** — `df.groupby(year_col)[variable].describe()`.
Narrative: compare distributions across years.

**Step C** — `sns.histplot(kde=True)`.
Title: "Distribution of [Variable Name]".
Narrative: describe the shape. For rainfall specifically, address right skew
explicitly and note that extreme values may represent storm events.

**Step D** — `sns.boxplot(x=year_col, y=variable)`.
Title: "[Variable Name] by Year".
Narrative specific to each variable:
- Temperature: confirm expected Florida range (~18–32°C), flag anomalous readings
- Humidity: note seasonal behavior, flag anomalously dry or humid years
- Rainfall: identify any extreme outliers, discuss whether they represent real storm
  events or potential data quality issues

### 4.4 — Climate Intercorrelation

Compute a Pearson correlation matrix of all three climate variables.
Display as a `sns.heatmap` with `annot=True`, `fmt='.2f'`, and a diverging colormap
(`coolwarm` or `RdBu_r`). Title: "Climate Variable Correlation Matrix".

Narrative: state each pairwise r value with verbal strength descriptor. Flag any
collinearity concerns to carry into the modeling section. Note that temperature and
humidity are expected to be correlated in a subtropical climate.

---

## Section 5 — Time Series Visualization

### 5.1 — Full Time Series: Cases

Create a two-panel figure, stacked vertically:
- Top panel: weekly local cases as a line plot with shaded area under the curve
- Bottom panel: weekly travel cases as a line plot with shaded area
- x-axis on both panels: `dengue_week_start` (datetime)
- Use `fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)`

Title: "Weekly Dengue Cases — Florida 2022–2025".
Narrative: identify outbreak periods, quiet periods, and any visual co-movement
between the two series.

### 5.2 — Full Time Series: Climate Variables

Create a three-panel figure, stacked vertically, one panel each for temperature,
humidity, and rainfall across the full time period. Same datetime x-axis.
Use `sharex=True`.

Title: "Weekly Climate Variables — Florida 2022–2025".
Narrative: describe seasonal oscillation for each variable. Note any anomalous
periods that align with outbreak periods identified in 5.1.

### 5.3 — Dual-Axis Co-visualization

Produce two separate figures using `fig, ax1 = plt.subplots()` and
`ax2 = ax1.twinx()`:

**Figure 1:** Weekly local cases (left axis) + 2m temperature (right axis).
Use contrasting colors. Add a combined legend identifying both series.
Title: "Weekly Local Cases and Temperature — Florida 2022–2025".

**Figure 2:** Weekly local cases (left axis) + rainfall (right axis).
Same approach.
Title: "Weekly Local Cases and Rainfall — Florida 2022–2025".

Narrative for each: describe the apparent visual lag between climate peaks and case
peaks. This is the intuitive illustration of the core research question of the project.

### 5.4 — Heat Calendar

Build a heat calendar (contribution heatmap):
- Reshape the data so rows = years, columns = epidemiological weeks (1–52)
- Use `df.pivot_table(index=year_col, columns=week_col, values=local_col)`
- Plot using `sns.heatmap` with `cmap='YlOrRd'`, `annot=False`, `linewidths=0.5`
- x-axis label: "Epidemiological Week", y-axis label: "Year"
- Add a colorbar label: "Weekly Local Cases"

Title: "Heat Calendar of Weekly Local Dengue Cases — Florida 2022–2025".
Narrative: describe the transmission season (which weeks cases cluster in), any
outbreak clustering, and interannual variation in timing and intensity.

### 5.5 — Overlaid Seasonal Pattern

Create a two-panel figure:
- Top panel: weekly local cases for each year overlaid on a single week-of-year
  (1–52) x-axis. Each year a distinct color. Include a legend.
- Bottom panel: 2m temperature for each year overlaid on the same x-axis.

Use `df.groupby([year_col, week_col])` to aggregate to week-of-year.
Title: "Seasonal Patterns by Year — Cases and Temperature".
Narrative: compare seasonal timing across years. Note whether case peaks align
consistently with temperature peaks, and whether any year deviated in timing
or intensity.

### 5.6 — Seasonal Decomposition

Apply `seasonal_decompose` with `model='additive'` and `period=52` to:
1. Weekly local cases
2. 2m temperature
3. Rainfall

Before running, interpolate missing values in each series using
`df[col].interpolate(method='linear')` — decomposition requires a complete series.

For each variable, plot the four components (observed, trend, seasonal, residual)
in a 4-panel stacked figure. Title each overall figure clearly.

Narrative per variable: separate the seasonal signal from interannual trend and
residual noise. For climate variables specifically, address whether meaningful
interannual variation exists beyond the seasonal cycle — this directly affects
how much predictive power they carry year-to-year in modeling.

---

## Section 6 — Climate–Outcome Relationships

### 6.1 — Zero-Lag Correlation Table

Compute Pearson r between each climate variable and (a) weekly local cases and
(b) weekly travel cases at zero lag. Use `scipy.stats.pearsonr()` to get both
r and p-value. Display as a clean formatted table with columns: Variable, r (local),
p (local), strength (local), r (travel), p (travel), strength (travel).

Apply the verbal strength scale from `CLAUDE.md`.

Narrative: explain why zero-lag correlations are expected to be modest — climate
affects dengue through a biological process (mosquito lifecycle + viral incubation)
with a multi-week delay. This motivates the cross-correlation analysis in 6.4.

### 6.2 — LOWESS Scatter Plots

Create a three-panel figure (one panel per climate variable vs. weekly local cases):
- Scatter points with `alpha=0.4` to handle overplotting
- LOWESS smoother using `statsmodels.nonparametric.smoothers_lowess.lowess`
  with `frac=0.4`
- Do NOT add a linear fit line — LOWESS only
- Label each panel with the climate variable name

Title: "LOWESS Relationships Between Climate Variables and Weekly Local Cases".
Narrative: for each variable, describe the shape of the relationship. Specifically
look for: a temperature threshold below which cases are near zero; a possible
inverted-U in rainfall (moderate rain promotes Aedes breeding habitat, extreme
rain may cause larval washout); any humidity threshold effects. Flag any nonlinear
patterns that a linear model would fail to capture.

### 6.3 — Binned Mean Plots

For each climate variable:
1. Bin into quartiles using `pd.qcut()`, labeling bins with their actual value ranges
2. Compute mean weekly local cases per bin
3. Compute 95% confidence intervals using `stats.sem()` and `stats.t.ppf(0.975, df=n-1)`
4. Plot as a bar chart with error bars using `plt.bar()` and `plt.errorbar()`

Produce three separate plots, one per variable.
Title each: "Mean Weekly Local Cases by [Variable] Quartile".
x-axis labels must show the actual value ranges of each quartile bin, not "Q1–Q4".

Narrative per plot: describe threshold effects in plain language. This is the most
accessible version of the relationship explored in 6.2 and should be written for
a reader unfamiliar with LOWESS smoothing.

### 6.4 — Cross-Correlation Analysis

For each of the three climate variables vs. weekly local cases:

1. Compute cross-correlation at lags 0–8 weeks using a loop with `df[col].shift(lag)`
   and `scipy.stats.pearsonr()` at each lag
2. Store results in a dataframe: columns = lag, r, p_value
3. Plot as a bar chart with:
   - Lag (weeks) on x-axis
   - Pearson r on y-axis
   - A horizontal dashed line at r = 0
   - Significance bands at ±1.96/√n as horizontal dotted lines
   - Bars colored by whether they exceed the significance threshold

Produce three separate plots, one per climate variable.
Title each: "Cross-Correlation: [Variable] vs. Weekly Local Cases (Lags 0–8 Weeks)".

Narrative per variable: explicitly state which lag window shows the strongest
correlation and its verbal strength descriptor. State this finding as a direct
empirical justification for the lag features that will be constructed in the
modeling section. This is the most analytically important finding of the entire EDA.

### 6.5 — Travel vs. Local Case Relationship

**Step 6.5.1** — Compute Pearson r between lagged travel cases and weekly local cases
at lags 1, 2, and 3 weeks. Use `df[travel_col].shift(lag)`. Display as a table
with columns: lag (weeks), r, p-value, verbal strength.

**Step 6.5.2** — Scatter plot of travel cases at the best-performing lag vs. local
cases, with a LOWESS smoother. Label axes with units. Include the lag value in the title.
Title: "Travel Cases (Lag [X] Weeks) vs. Weekly Local Cases".

**Step 6.5.3** — Dual-axis time series of weekly local cases and travel cases
(at the best-performing lag) across the full time period.
Title: "Local vs. Travel Cases — Florida 2022–2025".

**Step 6.5.4** — Write a dedicated interpretation markdown cell making an explicit
decision: based on the correlation table and plots, will travel cases be included as
a predictor in the modeling section? State the justification clearly.

---

## Section 7 — EDA Summary and Modeling Implications

This section is markdown only — no new code cells. Write 6 paragraphs, one per topic:

1. **Outcome distribution** — summarize the local and travel case distributions.
   State the zero-inflation percentage quantitatively. Name the appropriate error
   distribution for modeling and briefly explain why.

2. **Missingness** — state the explicit decision made for handling missing rows.
   Reference what was observed in Section 2 (clustered vs. random, which variables
   affected). Note how this decision will be implemented.

3. **Climate variable structure** — summarize which variables are collinear,
   whether seasonal decomposition revealed meaningful interannual variation beyond
   the seasonal cycle, and any data quality observations worth carrying forward.

4. **Lag structure** — state the specific lag windows identified by the CCF as
   strongest for each climate variable. These are the empirical basis for lag
   feature engineering in the modeling section. Be specific: name the lag and
   the r value for each variable.

5. **Relationship shape** — summarize whether LOWESS plots and binned mean plots
   suggested nonlinear thresholds worth capturing in the model. Name any specific
   thresholds observed (e.g. "cases were near zero below approximately X°C").

6. **Travel cases** — restate the inclusion/exclusion decision from 6.5.4 and
   its justification.

Close with a single transitional sentence explicitly leading into the Research
Questions and modeling section.

---

## Completion Checklist

Before declaring the EDA section complete, verify:

- [ ] Every subsection listed above has been implemented
- [ ] Every code cell has a preceding description cell and a following interpretation cell
- [ ] All headers use the HTML color span format from `CLAUDE.md`
- [ ] All plots have titles, axis labels, `sns.despine()`, and `plt.grid(axis='y')`
- [ ] All r values are accompanied by verbal strength descriptors
- [ ] Section 7 makes explicit, quantitative modeling decisions based on EDA findings
- [ ] No subsections were skipped or abbreviated
