# Modeling Instructions — Dengue Climate Analysis

## Before Starting

1. Read `CLAUDE.md` fully — all conventions defined there apply to every cell you write
2. Read `README.md` to understand the project structure and locate the data file
3. Read the EDA Section 6.4 CCF output cells in `FinalProject.ipynb` to identify the actual
   empirically-derived optimal lag for each climate variable before writing any code
4. Read the EDA Section 6.5.1 output to identify the best travel case lag
5. Read the EDA Section 7 summary to confirm all modeling decisions made there
6. Confirm your understanding before writing any code
7. Set your model to Opus: `/model opus`
8. The working notebook is `FinalProject.ipynb`. All work goes there

The working data is `Data/edited_combined_data.csv`. The modeling section builds directly
on the dataframe `df` loaded in the EDA section — reload it at the top of the modeling
section using the same import and parse arguments.

**Additional imports required for the modeling section** — add these to the existing
imports cell or in a dedicated modeling imports cell at the start of this section:

```python
from statsmodels.discrete.discrete_model import NegativeBinomial, Poisson
from statsmodels.discrete.count_model import ZeroInflatedNegativeBinomialP
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.diagnostic import acorr_ljungbox
import statsmodels.api as sm
from sklearn.metrics import roc_curve, roc_auc_score
from scipy.stats import chi2
```

---

## Task

Build the complete Modeling section of `FinalProject.ipynb`. The section consists of eight
subsections detailed below. Each subsection must be implemented in full — do not skip
or abbreviate any step. Follow the mandatory three-cell structure (description → code →
interpretation) from `CLAUDE.md` for every analysis step.

Work through the sections in order. After completing each major section (1 through 8),
pause and ask for confirmation before proceeding to the next.

**Key decisions carried forward from EDA:**
- Error structure: negative binomial (primary); ZINB evaluated in Section 1
- Missingness: listwise deletion — exclude any row missing a predictor or outcome used in a given model
- Temperature: nonlinear threshold near 18–20°C — both linear and threshold models will be compared
- Rainfall: enter as `log(rainfall + 1)` due to right skew identified in EDA Section 4.3
- Humidity: enter as-is (weekly average, %)
- Travel cases: include at best lag from EDA Section 6.5.1 as a secondary predictor
- Lag windows: determined empirically from EDA Section 6.4 CCF — read these before coding

---

## Section 1 — Distribution Validation

This section formally tests the error structure assumptions that were motivated by the
EDA. State H₀ and Hₐ in a markdown cell before each test, as required by `CLAUDE.md`.

### 1.1 — Data Reload and Analytic Dataset Setup

**Step 1.1.1 — Reload the data**
Reload `Data/edited_combined_data.csv` into a fresh dataframe `df` using `pd.read_csv()`
with `parse_dates=['dengue_week_start', 'dengue_week_end']`. Re-define all column name
constants (`local_col`, `travel_col`, `temp_col`, `humidity_col`, `rainfall_col`,
`year_col`, `week_col`). Drop the 60cm and 10m temperature columns.
Narrative: confirm the reload and state that a clean dataframe is used for modeling
to avoid any EDA-stage mutations.

**Step 1.1.2 — Restrict to complete cases**
Apply listwise deletion: drop all rows where `local_col`, `temp_col`, `humidity_col`,
or `rainfall_col` is null. Store as `df_complete`. Print the original row count,
the row count after deletion, and the number of rows dropped.
Narrative: state how many rows were removed, confirm this matches the ~200–210 complete
rows estimated in EDA Section 7, and explain that listwise deletion is appropriate given
the structurally independent and non-systematic missingness identified in EDA Section 2.

### 1.2 — Overdispersion Test: Poisson vs. Negative Binomial

Write H₀ and Hₐ in a markdown cell before the code:
- H₀: The data are Poisson-distributed (variance = mean; no overdispersion)
- Hₐ: The data are overdispersed (variance > mean), requiring a negative binomial model

**Step 1.2 — Fit and compare**
Using `df_complete`:
- Fit a null Poisson GLM: `Poisson(endog=y, exog=X_const).fit(disp=False)` where
  `X_const` is a constant-only design matrix via `sm.add_constant(np.ones(len(y)))`
- Fit a null NB GLM: `NegativeBinomial(endog=y, exog=X_const).fit(disp=False)`
- Compute the likelihood ratio statistic: `lr_stat = 2 * (nb_result.llf - poisson_result.llf)`
- Compute p-value: `p_val = chi2.sf(lr_stat, df=1)`
- Display: a table with model name, log-likelihood, AIC, LR statistic, p-value, and decision

Narrative: interpret the test result. If p < 0.05, Poisson is rejected and NB is adopted.
Connect explicitly to the EDA finding: the variance (≈10.5) substantially exceeded the
mean (1.83), making this result expected. Name the NB model as the primary modeling
framework going forward.

### 1.3 — Zero-Inflation Test: NB vs. ZINB

Write H₀ and Hₐ before the code:
- H₀: The excess zeros are adequately captured by the NB dispersion parameter alone
- Hₐ: A separate zero-generating process is required (zero-inflated model)

**Step 1.3 — Fit and compare**
- Fit a null ZINB: `ZeroInflatedNegativeBinomialP(endog=y, exog=X_const, exog_infl=X_const).fit(disp=False)`
- Compare AIC(NB null) vs. AIC(ZINB null)
- Note: a formal Vuong test is not available in statsmodels; use AIC/BIC difference as the criterion.
  Report: ΔAIC = AIC(ZINB) − AIC(NB). If ΔAIC < −2, prefer ZINB; if ΔAIC > −2, NB suffices.
- Display: a two-row table with model, log-likelihood, AIC, BIC, and the ΔAIC conclusion

Narrative: state which model is selected and why. If NB is sufficient (expected given 54.1%
zeros is within typical NB range), confirm NB as the primary error structure and note that
ZINB will be revisited in residual diagnostics if the NB under-fits. If ZINB wins, state
that all subsequent models will use ZINB.

---

## Section 2 — Lag Feature Engineering

All lagged predictors are constructed here in a single dedicated section before any
models are fit. This makes the feature construction transparent and reproducible.

### 2.1 — Read CCF Results and Define Optimal Lags

**Step 2.1 — Define lag constants (code cell)**
Read the CCF output from EDA Section 6.4 and define the following constants at the
top of this code cell with explicit comments citing the EDA source:

```python
# Optimal lags identified from EDA Section 6.4 cross-correlation functions
temp_best_lag     = N   # replace N with the lag at which temperature CCF peaked
humidity_best_lag = N   # replace N with the lag at which humidity CCF peaked
rainfall_best_lag = N   # replace N with the lag at which rainfall CCF peaked

# Best travel case lag identified from EDA Section 6.5.1
travel_best_lag   = N   # replace N with the best lag from 6.5.1 (likely 1 or 2)
```

Narrative: for each variable, state the chosen lag, the Pearson r at that lag, and
the verbal strength descriptor. Explain the biological mechanism that corresponds to the
temperature lag (mosquito development time + extrinsic incubation period).

### 2.2 — Construct Lag Features

**Step 2.2 — Build the modeling dataframe**
Starting from `df_complete`, create the following new columns using `.shift()`:

```python
df_model = df_complete.copy()
df_model['temp_lagged']          = df_model[temp_col].shift(temp_best_lag)
df_model['humidity_lagged']      = df_model[humidity_col].shift(humidity_best_lag)
df_model['log_rainfall_lagged']  = np.log1p(df_model[rainfall_col].shift(rainfall_best_lag))
df_model['travel_lagged']        = df_model[travel_col].shift(travel_best_lag)
df_model['temp_above_threshold'] = (df_model[temp_col].shift(temp_best_lag) >= 20.0).astype(int)
```

Then drop rows with NaN introduced by shifting. Print the final shape of `df_model`.

Narrative: explain that `.shift(N)` aligns each climate observation with the dengue
outcome that occurred N weeks later, operationalizing the biological lag. Note how many
rows were lost to lag-induced NaN and confirm the final analytic sample size. Explain
`np.log1p()` (equivalent to log(x+1)) as the appropriate transformation for a
right-skewed, zero-inclusive variable.

### 2.3 — Feature Summary Table

**Step 2.3 — Display descriptive statistics for all model features**
Call `.describe()` on `df_model[['temp_lagged', 'humidity_lagged', 'log_rainfall_lagged',
'travel_lagged', 'temp_above_threshold', local_col]]`.
Narrative: confirm that all features are on reasonable scales and that no extreme values
or unexpected nulls remain before fitting.

---

## Section 3 — Negative Binomial GLMs

Use `statsmodels.discrete.discrete_model.NegativeBinomial` with `method='bfgs'` for
all models in this section. Use `sm.add_constant()` for all design matrices. The outcome
variable is `df_model[local_col]` throughout.

For every model, report: coefficient, IRR (= `np.exp(coef)`), 95% CI for IRR
(= `np.exp(conf_int)`), p-value, AIC, BIC, and pseudo-R² (McFadden's).

### 3.1 — Univariate Models

Run four separate NB models, each with a single predictor plus intercept.
Each model is its own three-cell block (description → code → interpretation).

**Model A — Temperature:**
`local_cases ~ const + temp_lagged`
Narrative: report the IRR for temperature. An IRR > 1 indicates that each additional
degree Celsius (at the lagged week) is associated with multiplicatively higher expected
case counts. Interpret in biological terms.

**Model B — Relative Humidity:**
`local_cases ~ const + humidity_lagged`
Narrative: report IRR. Given the weaker CCF signal found in EDA, an attenuated or
non-significant result is expected; discuss this explicitly.

**Model C — Log Rainfall:**
`local_cases ~ const + log_rainfall_lagged`
Narrative: report IRR. Note that the IRR here applies to a log-transformed predictor —
interpret accordingly (a one-unit increase in log(rainfall+1) corresponds to a
multiplicative shift in expected cases).

**Model D — Travel Cases:**
`local_cases ~ const + travel_lagged`
Narrative: report IRR for lagged travel cases. Discuss the mechanistic interpretation:
each additional imported case at the lag week is associated with a multiplicative
increase in expected local cases, conditional on climate being favorable.

### 3.2 — Multivariate Full Model

**Step 3.2 — Fit the full model**
`local_cases ~ const + temp_lagged + humidity_lagged + log_rainfall_lagged + travel_lagged`

- Display the full `results.summary()` output
- Compute and display VIF for each predictor:

```python
X_vif = df_model[['temp_lagged', 'humidity_lagged', 'log_rainfall_lagged', 'travel_lagged']]
X_vif = sm.add_constant(X_vif)
vif_data = pd.DataFrame({
    'feature': X_vif.columns,
    'VIF': [variance_inflation_factor(X_vif.values, i) for i in range(X_vif.shape[1])]
})
```

Display `vif_data` as a formatted table.
Narrative: interpret each coefficient's IRR. Flag any predictors that lose significance
in the multivariate context compared to univariate models (suppression or confounding).
Interpret VIF: values < 5 indicate acceptable collinearity; values ≥ 5 warrant concern.
This is the primary model of the analysis — introduce it as such.

### 3.3 — Temperature Threshold Model

**Step 3.3 — Fit the threshold model**
Replace the continuous `temp_lagged` with `temp_above_threshold` (binary: 1 if lagged
temperature ≥ 20°C, 0 otherwise):
`local_cases ~ const + temp_above_threshold + humidity_lagged + log_rainfall_lagged + travel_lagged`

Narrative: report the IRR for `temp_above_threshold`. An IRR substantially > 1 indicates
that weeks following temperatures above the threshold are associated with markedly higher
expected case counts, consistent with the threshold pattern identified in EDA Sections 6.2
and 6.3. Compare AIC to Model 3.2 to determine whether the threshold operationalization
captures the relationship as well as or better than the continuous linear term.

### 3.4 — Model Comparison Table

**Step 3.4 — AIC/BIC summary table**
Build a single formatted dataframe comparing all six models (3.1A, 3.1B, 3.1C, 3.1D,
3.2, 3.3) with columns:

| Model | Predictors | N | Log-Likelihood | AIC | BIC | Pseudo-R² |
|-------|-----------|---|----------------|-----|-----|-----------|

Sort by AIC ascending. Highlight the best model (lowest AIC) in the narrative.
Narrative: state which model is selected as the best-fitting specification and explain
what that selection implies. Carry the best model forward to Sections 4 and 5.

---

## Section 4 — Lag Selection Sensitivity

This section empirically validates the CCF-derived temperature lag choice using
model fit rather than correlation.

### 4.1 — AIC Profile Across Temperature Lags

**Step 4.1 — Lag sensitivity loop**
For each temperature lag N in range(1, 9) (lags 1 through 8):
- Construct `temp_lag_N = df_complete[temp_col].shift(N)` alongside all other predictors
  at their chosen lags
- Drop NaN rows
- Fit the full multivariate NB model using that lag for temperature
- Record: lag, AIC, BIC, N_obs

Store results in a dataframe `lag_sensitivity`. Display it as a formatted table.

**Step 4.1 (plot) — AIC vs. lag bar chart**
Plot AIC on the y-axis and lag (weeks) on the x-axis as a bar chart.
Add a vertical dashed line at `temp_best_lag` (the CCF-derived lag).
Title: "AIC by Temperature Lag — Multivariate NB Model".
x-axis label: "Temperature Lag (Weeks)". y-axis label: "AIC".

Narrative: state whether the AIC-minimizing lag matches the CCF-derived lag. If they
differ, discuss which to prefer and why. A close match validates the CCF approach;
a divergence would suggest the model-fit criterion should take precedence. Either way,
state the final adopted lag explicitly — this closes the lag selection question before
residual diagnostics.

---

## Section 5 — Residual Diagnostics

Apply all diagnostics to the best model identified in Section 3.4. Refit that model
if needed and store its Pearson residuals: `pearson_resid = results.resid_pearson`.

### 5.1 — Temporal Autocorrelation of Residuals

Write H₀ and Hₐ before the code:
- H₀: Residuals are independently distributed (no temporal autocorrelation)
- Hₐ: Residuals exhibit significant autocorrelation at one or more lags

**Step 5.1.1 — ACF plot of residuals**
Plot the autocorrelation function of `pearson_resid` using `plot_acf(pearson_resid, lags=20)`.
Title: "Autocorrelation Function of Model Residuals".
Narrative: identify any lags where the ACF significantly exceeds the 95% confidence band.

**Step 5.1.2 — Ljung-Box test**
Run `acorr_ljungbox(pearson_resid, lags=[4, 8, 12], return_df=True)`.
Display the result table (lag, lb_stat, lb_pvalue).
Narrative: interpret the Ljung-Box p-values. If any p < 0.05, significant residual
autocorrelation is present — name this as a model limitation and note that a
time-series regression framework (e.g., SARIMAX or a negative binomial model with
AR terms) could address this in future work.

### 5.2 — Predicted vs. Observed Plot

**Step 5.2 — Scatter: fitted values vs. observed counts**
Extract `fitted = results.predict()` and `observed = df_model[local_col]`.
Create a scatter plot with observed on the x-axis and fitted on the y-axis.
Color points by `df_model[year_col].astype(int)`. Add a 45° reference line (`y = x`)
in black dashed. Use `alpha=0.5` on scatter points.
Title: "Predicted vs. Observed Weekly Local Cases".
x-axis: "Observed Cases". y-axis: "Model-Predicted Cases".

Narrative: describe the overall calibration. Identify whether the model systematically
over- or under-predicts outbreak-level weeks (high-count observations). Note any
year-specific clustering that would indicate interannual confounding not captured
by the climate predictors.

### 5.3 — Residual vs. Fitted Plot

**Step 5.3 — Scatter: Pearson residuals vs. fitted values**
Scatter `fitted` on the x-axis and `pearson_resid` on the y-axis.
Add a horizontal dashed line at residual = 0.
Add a LOWESS smoother using `lowess(pearson_resid, fitted, frac=0.4, return_sorted=True)`.
Use `alpha=0.4` on scatter points.
Title: "Pearson Residuals vs. Fitted Values".
x-axis: "Fitted Values (Expected Cases)". y-axis: "Pearson Residual".

Narrative: a well-specified model should show residuals scattered randomly around zero
with no systematic pattern. A U-shape or fan-shape in the LOWESS smoother indicates
misspecified functional form or heteroscedasticity. Discuss what any observed pattern
implies for model adequacy.

---

## Section 6 — Leave-One-Year-Out Cross-Validation

This section evaluates whether the model generalizes beyond the training years.
Because the dataset spans only four years, leave-one-year-out (LOYO) CV is the
appropriate temporal validation strategy — random k-fold splits must not be used,
as they would allow future observations to inform past predictions.

Use the best model specification identified in Section 3.4 for all LOYO folds.

### 6.1 — LOYO Cross-Validation Loop

**Step 6.1 — Fit and predict**

```python
loyo_results = []
years = sorted(df_model[year_col].dropna().astype(int).unique())

for held_out_year in years:
    train = df_model[df_model[year_col].astype(int) != held_out_year]
    test  = df_model[df_model[year_col].astype(int) == held_out_year]

    # Build design matrices using the same predictors as the best model
    X_train = sm.add_constant(train[predictor_cols])
    y_train = train[local_col]
    X_test  = sm.add_constant(test[predictor_cols])
    y_test  = test[local_col]

    fold_model = NegativeBinomial(endog=y_train, exog=X_train).fit(disp=False)
    y_pred = fold_model.predict(X_test)

    mae  = np.mean(np.abs(y_test - y_pred))
    rmse = np.sqrt(np.mean((y_test - y_pred) ** 2))
    r, _ = stats.pearsonr(y_test, y_pred)

    loyo_results.append({
        'held_out_year': held_out_year,
        'n_test': len(y_test),
        'MAE': round(mae, 3),
        'RMSE': round(rmse, 3),
        'Pearson_r': round(r, 3)
    })

loyo_df = pd.DataFrame(loyo_results)
```

Define `predictor_cols` as the list of feature columns from the best model before running.
Display `loyo_df` as a formatted table.

Narrative: interpret each fold. Identify whether any year is systematically harder
to predict (higher MAE/RMSE, lower r). The 2023 outbreak year is a critical test case —
discuss explicitly whether the model anticipated the elevated case counts or missed
the outbreak entirely. Discuss what a missed outbreak would imply about the model's
reliance on climate predictors vs. other drivers.

### 6.2 — LOYO Predicted vs. Observed Time Series

**Step 6.2 — Stitch predictions and plot**
Collect all LOYO predictions into a single series aligned to `dengue_week_start`.
Plot as two overlaid series:
- Observed local cases: scatter points (`alpha=0.6`, labeled "Observed")
- LOYO predicted cases: line plot (`linewidth=1.5`, labeled "LOYO Predicted")

Use `fig, ax = plt.subplots(figsize=(14, 5))`.
Title: "Leave-One-Year-Out Cross-Validation — Predicted vs. Observed Cases".
x-axis: "Week". y-axis: "Weekly Local Dengue Cases".

Narrative: describe where the model tracks the observed series well and where it
diverges. A model that captures the seasonal rise and fall but misses outbreak peaks
indicates that the climate predictors explain transmission seasonality but not the
stochastic intensity of individual outbreaks.

---

## Section 7 — Outbreak Prediction (Binary Logistic Regression)

This section reframes the prediction problem as a binary classification task,
which is more directly actionable for public health surveillance: instead of
predicting case counts, the model predicts whether a given week will be an
"outbreak week." This is a complementary analysis to the NB count model —
both answer the research question but from different angles.

### 7.1 — Define the Outbreak Threshold

**Step 7.1 — Create binary outcome**
Define an outbreak week as any week with ≥ 3 locally-acquired cases.
(`outbreak = (df_model[local_col] >= 3).astype(int)`)
Compute and display: total weeks, outbreak weeks, proportion of outbreak weeks.
If the proportion is very low (< 10%) or very high (> 50%), flag this and discuss
whether the threshold should be adjusted before proceeding. Justify the chosen threshold
with reference to the case distribution summary from EDA Section 3.1.

Narrative: state the threshold chosen, the resulting class proportions, and why this
threshold is epidemiologically meaningful.

### 7.2 — Logistic Regression Model

**Step 7.2.1 — Fit the model**
Fit a logistic regression using `sm.Logit`:
`outbreak ~ const + temp_lagged + log_rainfall_lagged + travel_lagged`

(Humidity is excluded here — it was the weakest predictor in the NB models.
Justify this exclusion explicitly in the narrative based on the NB results from Section 3.)

Display `results.summary()`.
Compute and display odds ratios and 95% CIs:
```python
odds_ratios = np.exp(results.params)
ci = np.exp(results.conf_int())
or_table = pd.concat([odds_ratios, ci], axis=1)
or_table.columns = ['OR', '2.5%', '97.5%']
```

Narrative: interpret each odds ratio. An OR > 1 means elevated odds of an outbreak week;
an OR < 1 means protective. Compare the direction and significance of predictors here
to the NB IRRs from Section 3 — they should be broadly consistent.

**Step 7.2.2 — ROC Curve and AUC**
Use `df_model` and the fitted logistic model to generate predicted probabilities.
Compute the ROC curve using `roc_curve(y_true, y_score)` and AUC using
`roc_auc_score(y_true, y_score)`.

Plot the ROC curve:
- x-axis: False Positive Rate. y-axis: True Positive Rate
- Add a diagonal dashed reference line (AUC = 0.5)
- Annotate the plot with the AUC value
Title: "ROC Curve — Logistic Model for Outbreak Week Prediction".

Narrative: interpret AUC. AUC = 0.5 is no better than chance; AUC = 1.0 is perfect
discrimination. An AUC of 0.7–0.8 would indicate useful but imperfect discrimination.
Compare the logistic model's predictive performance (AUC) to the NB model's LOYO
cross-validation performance (r) — note that they measure different things and
are complementary rather than competing.

---

## Section 8 — Modeling Summary

This section is markdown only — no new code cells. Write 6 paragraphs, one per topic.

1. **Error structure** — state which distribution was selected (NB or ZINB) based on the
   formal tests in Section 1. Report the LR statistic and p-value for the overdispersion
   test and the ΔAIC from the zero-inflation test. Explain in plain language what
   "negative binomial" means for a reader without a statistics background.

2. **Final model specification** — state the exact predictors, their lags, and any
   transformations used in the best-fitting model from Section 3.4. Report AIC, BIC,
   and pseudo-R². This paragraph should read as a complete, standalone description of
   the model that could appear in a Methods section of a scientific paper.

3. **Key findings** — for each predictor in the best model, report the IRR and 95% CI
   and interpret it in plain biological language. State which predictors reached
   statistical significance (p < 0.05) and which did not. Connect these findings
   directly to the research question stated in the Introduction.

4. **Model validation** — summarize the LOYO cross-validation results (mean MAE, RMSE,
   and r across folds). Describe how the model performed on the 2023 outbreak year
   specifically. Report the logistic model AUC. Discuss what these validation metrics
   collectively say about the model's practical utility for dengue surveillance.

5. **Limitations** — address: (a) whether residual temporal autocorrelation was detected
   and what that implies; (b) the single weather station as a proxy for statewide climate;
   (c) the small sample size (~200 weeks) limiting statistical power; (d) the absence of
   serotype and vector population data that would strengthen causal inference.

6. **Future directions** — propose 2–3 specific methodological extensions: e.g.,
   SARIMAX or a negative binomial model with autoregressive terms to address temporal
   autocorrelation; multi-station spatial averaging; incorporation of *Aedes aegypti*
   surveillance trap data; a distributed lag non-linear model (DLNM) to capture both
   the lag dimension and the nonlinear temperature threshold simultaneously.

Close with a single sentence leading into the Conclusions section.

---

## Completion Checklist

Before declaring the Modeling section complete, verify:

- [ ] Every subsection listed above has been implemented
- [ ] Every code cell has a preceding description cell and a following interpretation cell
- [ ] All headers use the HTML color span format from `CLAUDE.md`
- [ ] All plots have titles, axis labels, `sns.despine()`, and `plt.grid(axis='y')`
- [ ] H₀ and Hₐ are written out before every hypothesis test (Sections 1.2, 1.3, 5.1)
- [ ] All IRR values are accompanied by 95% CIs and verbal interpretation
- [ ] VIF table is included in Section 3.2
- [ ] Lag constants in Section 2.1 are populated from actual EDA CCF output — not assumed
- [ ] LOYO loop uses only training data to fit and held-out data to predict — no leakage
- [ ] Section 8 is self-contained enough to serve as a Methods + Results summary
- [ ] No subsections were skipped or abbreviated
