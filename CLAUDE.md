# CLAUDE.md — Persistent Project Instructions

This file is read automatically by Claude Code at the start of every session.
Follow all instructions here for every task in this project unless explicitly told otherwise.

---

## Project Identity

This is a Jupyter Notebook project analyzing the relationship between weekly climate
variables and dengue case counts in Florida from 2022–2025. The notebook functions as
both a university course final project and valid academic research. The intended audience
is general scientific — assume a reader with a biology background but not a statistics
background. The tone should be precise, clear, and accessible throughout.

The project structure is documented in `README.md`. Read it to understand what every
file in this directory is and where outputs belong.

---

## Notebook Formatting Conventions

These apply to every markdown and code cell written in this project. No exceptions.

### Header Color Scheme
Use HTML span tags for all headers — never plain markdown headers inside notebook cells:
- H1 sections: `# <span style="color:#ffa500">Section Title</span>`
- H2 subsections: `## <span style="color:#0096FF">Subsection Title</span>`
- H3 sub-subsections: `### <span style="color:#FFD700">Sub-subsection Title</span>`

### Mandatory Cell Structure
Every single analysis step must follow this three-cell pattern — never collapse these:
1. **Markdown cell** — name the step and briefly describe what the following code does
2. **Code cell** — perform the analysis
3. **Markdown cell** — interpret the output in plain language for a general scientific audience

Never write a code cell without both a preceding description cell and a following
interpretation cell. Never combine two analysis steps into one code cell if they would
each warrant their own interpretation.

### Imports and Config
Always include the following at the top of the notebook in the first code cell:
```python
import numpy as np
import pandas as pd
from scipy import stats
import seaborn as sns
import matplotlib.pyplot as plt
import missingno as msno
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.graphics.tsaplots import plot_acf
from statsmodels.nonparametric.smoothers_lowess import lowess
import warnings
warnings.filterwarnings('ignore')

%config InlineBackend.figure_format = 'retina'
```

### Column Name Variables
Define these near the top of the notebook immediately after import and use them
throughout — never hardcode column name strings in analysis cells:
```python
local_col    = 'weekly_local_cases'
travel_col   = 'weekly_travel_cases'
temp_col     = 'Temp @ 2m (C) Avg (Weekly Avg)'
humidity_col = 'Relative Humidity (%) Avg (Weekly Avg)'
rainfall_col = 'Rainfall Amount (in) Sum (Weekly Avg)'
year_col     = 'dengue_year'
week_col     = 'dengue_week'
```

---

## Plot Conventions

Apply these to every plot without exception:

- Use `seaborn` as the primary plotting library with `matplotlib` for figure-level control
- Apply `sns.despine()` to every plot
- Apply `plt.grid(axis='y')` to all bar plots, box plots, and line plots
- Every plot must have: a descriptive title (`plt.title()`), a labeled x-axis (`plt.xlabel()`), and a labeled y-axis (`plt.ylabel()`)
- Use `plt.tight_layout()` before `plt.show()` on all multi-panel figures
- End all plot cells with `plt.show();` (semicolon suppresses extra output)
- Use `%config InlineBackend.figure_format = 'retina'` (set once in the imports cell)
- For multi-panel figures, use `fig, axes = plt.subplots(nrows, ncols, figsize=(w, h))`
- Choose figure sizes deliberately — single plots: `figsize=(10, 5)`, multi-panel: scale accordingly

---

## Statistical Conventions

- Use `scipy.stats` for all statistical calculations
- Always report IQR alongside standard deviation: use `stats.iqr()` for every continuous variable
- Use `df.groupby()` for all year-grouped summaries
- Use `df.describe()` as the standard summary statistics call
- When computing and reporting Pearson r values, always append a verbal strength descriptor
  using this scale (apply the same scale to negative values):
  - 0.00–0.19 → *very weak*
  - 0.20–0.39 → *weak*
  - 0.40–0.59 → *moderate*
  - 0.60–0.79 → *strong*
  - 0.80–1.00 → *very strong*
- When stating hypothesis test results, always write out H₀ and Hₐ explicitly in a
  markdown cell before running the test

---

## Code Style

- Begin every code cell with comments — one comment per logical step
- Use descriptive variable names throughout; never use single letters except for
  loop indices
- Do not put two conceptually distinct analyses in the same code cell if they
  each require their own interpretation
- When a finding from EDA directly informs a modeling decision (e.g. lag window
  choice, distribution selection, variable inclusion), the interpretation markdown
  cell must make that connection explicit — never leave it implicit

---

## Narrative Writing Style

All interpretation markdown cells should:
- Be written in complete sentences and paragraphs, not bullet points
- Explain what the output shows, not just restate the numbers
- Connect findings to the biological or epidemiological context where relevant
- Flag any modeling implications directly (e.g. "This right-skewed, zero-inflated
  distribution motivates the use of a negative binomial error structure in modeling")
- Use the verbal correlation scale (defined above) whenever describing r values
- Never use jargon without a brief plain-language explanation

---

## Session Management

- At the start of each session, re-read `README.md` and `eda_instructions.md`
  to orient to the current state of the project
- Before writing any code, confirm understanding of the current task
- Use `/model opus` for all EDA and modeling work — this is a complex analytical task
- Use `/clear` when starting a new session to avoid stale context
- If picking up a task mid-way, state which section was last completed and confirm
  the next step before proceeding
