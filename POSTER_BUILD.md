# Poster build pack: PimaUdongo (A0 landscape, one page)

**Instruction set and filled content in one document.** An agent building the
poster follows this top to bottom. Copy strings verbatim from section 5; do not
paraphrase, add prose, or invent a number.

Geometry and house style are taken from `Poster ref.pdf` (see section 2 and
section 10). Evidence comes from `export_afsis_real/`. Companion file
`POSTER_CONTENT.md` holds the reasoning and the full evidence register; do not edit it.

---

## 1. Status, locks and placeholders

| Item | State | What the builder does |
|---|---|---|
| Orientation | Reference poster is landscape, 353 × 250 mm, ratio 1.41 | Build **A0 landscape, 1189 × 841 mm**. The old portrait layout is withdrawn |
| Title | Two variants, one word apart | `TITLE_MODE = "robustness"` unless told otherwise |
| "Soil health" | Once, inside the title only | Enforce with the scan in section 8.1 |
| Author | Confirmed from the SLR PDF, page 1 | `Adrian Rugaba Asiimwe` |
| Reg no | Confirmed from the SLR PDF | `S24B23/054` |
| Department, university | Confirmed from the SLR PDF | `Department of Computer Science, Uganda Christian University, Mukono` |
| Access number | Format shown in the reference (`B29657` there) | `[ACCESS NO: TO CONFIRM]` |
| Supervisor, event, date | **Not in the repository** | `[TO CONFIRM]`. Never fill from `SMART_AG_BRIEF.md` |
| University logo | The reference carries the UCU crest; no logo file exists here | `[LOGO: supply file]`. Do not redraw, trace, or generate a crest |
| QR destination | Undecided | Build the frame and caption, leave the code as a placeholder |
| Bundle | `export_afsis_real/`, measured laboratory data | Never the synthetic `export/` |

Two prose reports (`PROTOTYPE_REPORT.md`, `REPORT_SCOPE_SHEET.md`) describe the old
407-row synthetic bundle. **Do not read numbers from them.**

---

## 2. Grid, from the reference

Measured off `Poster ref.pdf`: one landscape page, ratio 1.4114, three columns of
roughly 35 / 33 / 31 per cent, identity block across the top, then stacked sections
per column, each under a full-width colour bar.

A0 landscape, 1189 × 841 mm:

| Element | Size and position |
|---|---|
| Outer margin | 20 mm all round |
| Gutter between columns | 12 mm |
| Column 1 | x 20–415, width **395 mm** |
| Column 2 | x 427–797, width **370 mm** |
| Column 3 | x 809–1169, width **360 mm** |
| Identity block | y 20–92, full width; logo 72 × 72 at x 20, crest centred; text block x 110–1169, five lines |
| Section columns | y 96–821 |
| Section bar | full column width, **16 mm** high, 5 mm inner padding, text at left |
| Gap between stacked sections | 10 mm |
| Footer strip | none. Provenance line sits at the foot of column 3 |

Type scale: the reference is 353 mm wide and A0 landscape is 1189 mm, a factor of
**3.37**. Sizes below are that factor applied to the reference; check on a full-size
proof and adjust by ±2 pt only.

| Rank | Size | Use |
|---|---|---|
| Title | 46 pt, semibold | Identity line 1 |
| Metadata | 26 pt | Identity lines 2–5 |
| Section bar | 32 pt caps, letter-spacing 0.08 em, white | Bar text |
| Body | 27 pt, justified, 0.98 line height | Section prose |
| Table | 24 pt | Metrics table |
| Caption, references | 21 pt | Chart captions, reference list |

Colours, sampled from the reference JPEG (JPEG smearing makes them approximate; if
exactness matters, eyedrop the PDF at 300 dpi):

- Maroon bars `#A8444A` — sections that argue (motivation, objectives, results, uncertainty, conclusions)
- Green bars `#2F6D59` — sections that document (method, datasets, platform, deployment, alignment, references)
- Body text `#1A1A1A`, background `#FFFFFF`
- Chart bars: steel blue `#365F8B` (strong) and `#8FA8C4` (light), grey `#B3B3B3` for a baseline

Three images only: the results chart, the interval concept, the interface strip. The
metrics table is data, not an image; the pipeline is a five-icon row inside the
method section, not a strip.

---

## 3. Build order

1. Lay out the identity block, three columns, and empty section bars. Screenshot.
2. Paste section 5 text into the bars. Nothing else.
3. Build the three images from section 6. No text or numerals inside generated
   imagery; type every label yourself.
4. Write `poster-text.md` — every string, one per line, in reading order.
5. Write `numbers.md` — value, file, JSON path, one row per printed figure.
6. Run the checks in section 8, including the arithmetic assertion in 8.2. Attach
   its output to the build report.
7. Write the build report (section 9). Do not claim a check passed unless it ran.

---

## 4. Column contents, in order

| Column | Sections | Bar colour |
|---|---|---|
| 1 | BRIEF SUMMARY AND MOTIVATION · RESEARCH OBJECTIVES · METHODOLOGY AND AUDIT PROTOCOL · BENCHMARK DATASETS | maroon, maroon, green, green |
| 2 | RESULTS AND BENCHMARKING · MODEL COMPARISON (table) · UNCERTAINTY AND REFUSAL | maroon, none, maroon |
| 3 | PIMADONGO PROTOTYPE · COMPUTE AND DEPLOYMENT · CONCLUSIONS AND IMPACT · ALIGNMENT: SDGs, NDP IV AND VISION 2040 · KEY REFERENCES | green, green, maroon, green, green |

---

## 5. Content, verbatim

### 5.1 Identity block

```
Title:  Machine Learning for IoT-Based Soil Health Prediction in Sub-Saharan Africa:
        Spatial Validation and Sensor-Error Robustness
Application:  Total carbon prediction from soil measurements; comparison of random
        against geographically blocked validation
Faculty: Engineering and Technology  |  Department: Computer Science
Specialisation: Machine Learning
Researcher: Adrian Rugaba Asiimwe  |  S24B23/054  |  [ACCESS NO: TO CONFIRM]
Supervisor: [TO CONFIRM]  ·  Uganda Christian University, Mukono  ·  [EVENT AND DATE: TO CONFIRM]
```

`TITLE_MODE = "tolerance"` swaps **Robustness** for **Tolerance** in line 1. Nothing
else changes.

### 5.2 Column 1

**BRIEF SUMMARY AND MOTIVATION** (maroon)

```
Why?  Soil-carbon measurement is slow and expensive, so models predict it from cheaper
measurements. Those models are usually scored after splitting samples at random, which
places near-duplicates from the same field on both sides of the test, so the score
describes interpolation within known ground rather than performance on ground the model
has not seen.

How?  Train five regressors on 926 measured AfSIS samples, then answer the same question
twice: once with a shuffled 5-fold split, and once with folds blocked by geography, so
whole areas are held out. Repeat the blocked test with Gaussian noise on the inputs at
five levels, and attach split-conformal intervals calibrated on held-out blocks.

What?  A measured difference between the two designs, a stated error level at which the
blocked model stops beating a mean prediction, and a provenance-checked service that
refuses to report when its interval is too wide.
```

**RESEARCH OBJECTIVES** (maroon)

```
General Objective:  Measure how much of the reported skill of a soil-carbon model depends
on the validation design, and how much input error it tolerates before that skill
disappears.

· SO1  Build the pipeline on measured AfSIS laboratory data rather than a synthetic
  stand-in.  (Completed)
· SO2  Quantify the fall in skill when whole areas are held out instead of samples split
  at random.  (Completed)
· SO3  Establish the simulated error level at which the blocked model stops outperforming
  a mean prediction.  (Completed)
· SO4  Attach calibrated prediction intervals and gate the output on interval width.
  (Completed)
· SO5  Test a spatial R² of at least 0.50 for soil pH under simulated sensor error.
  (Not run — the reported run used total carbon)
· SO6  Test transfer to Uganda by leave-one-country-out.  (Not run)
· SO7  Validate against soil measured with the planned sensor hardware.  (Not started)
```

**METHODOLOGY AND AUDIT PROTOCOL** (green)

```
Every experiment ran from one frozen dataset and one seed set; folds were decided in a
single function, and nothing was fitted on a test fold.

· E1  Coalesce: one row per record; CROPNUTS pH and EC joined with ICRAF texture and total
  carbon; RRES organic carbon counted, not used. 926 rows, 58 sites, 16 clusters.
· E2  Transform: total carbon in percent, log-transformed; imputation and scaling fitted
  on training folds only.
· E3  Split twice: 5-fold shuffled K-fold, and GroupKFold over 10 blocks from KMeans on
  site coordinates.
· E4  Tune inside folds: grid search nested in every training fold; inner folds blocked
  the same way as the outer scheme.
· E5  Perturb: Gaussian noise at 0, 0.1, 0.25, 0.5 and 1.0 of the training SD, in two
  arms — trained clean and trained noisy.
· E6  Calibrate and serve: split-conformal intervals scored on unseen blocks; a gate that
  refuses when the interval is missing, too wide, or crosses a band cut.
```

Icon row at the foot of this section, five icons, no numerals:
`data → features → two designs → five models → interval and decision`

**BENCHMARK DATASETS** (green)

```
· AfSIS Phase I wet chemistry (real): 926 samples, 58 sites, 16 clusters, 19 countries;
  32 Ugandan rows, 3.5%. Licence ODC-By. All reported results.
· Synthetic stand-in: 160 sites, 8 clusters. Test fixture and smoke run only; excluded
  from every quoted result.
```

### 5.3 Column 2

**RESULTS AND BENCHMARKING** (maroon)

```
1. The split decides the score. The same random forest on the same 926 samples reports
   R² 0.338 when samples are split at random and 0.086 when whole areas are held out.
   The difference, 0.252, is a property of the design, not of the model.

2. The margin over a mean prediction is small. Spatially, the best model reaches RMSE
   1.339 and MAE 0.864 against 1.421 and 1.000 for predicting the field mean. It is
   better, and only just.

3. Skill ends at 0.5 of the training standard deviation. R² falls to 0.039 at 0.25 noise
   and to −0.094 at 0.5, where the model has stopped beating the field mean. Training on
   noisy inputs as well does not repair it: 0.106 against 0.088 at 0.10 noise.
```

**MODEL COMPARISON** (no bar; table sits directly under the findings)

| Model | R² random | R² spatial | RMSE spatial | MAE spatial | RPIQ spatial |
|---|---|---|---|---|---|
| Random forest | 0.338 | 0.086 | 1.339 | 0.864 | 0.888 |
| Gradient boosting | 0.295 | 0.078 | 1.344 | 0.858 | 0.885 |
| PLS | −0.112 | −0.333 | 1.616 | 0.955 | 0.736 |
| Ridge | −0.187 | −8.190 | 4.244 | 1.101 | 0.280 |
| Mean baseline | −0.002 | −0.030 | 1.421 | 1.000 | 0.837 |

Caption: `5 seeds; spatially blocked scores on unseen blocks. Ridge collapses spatially and the cause is not yet diagnosed. Target: total carbon, percent.`

**UNCERTAINTY AND REFUSAL** (maroon)

```
· Coverage is close to nominal: 88.8% against a nominal 90% on unseen blocks.
· Width is the limit, not coverage: mean 4.21 percentage points on a target whose median
  is 0.93, and against a band 0.788 wide. The interval is 5.3 bands wide.
· So the system refuses. The gate declines whenever an interval is wider than one band,
  and here every prediction is: it returns "too wide to place in a band" for every input
  on this feature set. That is the result, not a defect.
```

### 5.4 Column 3

**PIMADONGO PROTOTYPE** (green)

```
A FastAPI service over a hash-checked bundle. Six checks run before the model loads, and
a mismatch stops startup rather than serving a stale model. Two views are fed by one set
of measured values: a researcher dashboard and a field view that reads its numbers from
the same endpoints.
```

Interface strip beneath: `[SCREENSHOT: researcher dashboard, and field view]` — one
image, two panels, from the existing `screenshot_*.png` set. No mock-ups.

**COMPUTE AND DEPLOYMENT** (green)

```
· Model format: joblib bundle, hash-verified at load, sha256:57ae8583074e476a, requiring
  scikit-learn 1.8.0.
· Compute: CPU only. Five models, 5 seeds, nested tuning over 10 spatial blocks. No GPU,
  no edge device, no accelerator.
· Not measured: latency, throughput, memory. This study reports no serving benchmark, so
  none is claimed.
· Planned, not built: a low-cost probe paired with laboratory values on Ugandan soil.
  That phase must measure sensor error against a reference, which is what this study
  simulates.
```

**CONCLUSIONS AND IMPACT** (maroon)

```
· Report the split, or the score is not interpretable. On this data the design accounts
  for 0.252 of a 0.338 R².
· State the error level at which a model stops working. It is more useful to a user than
  a single score: here, 0.5 of the training standard deviation.
· Report interval width beside coverage. Here the width makes the answer a refusal: the
  gate declines every prediction, because a 4.21-point interval cannot fit inside a 0.788
  band.
```

**ALIGNMENT: SDGs, NDP IV AND VISION 2040** (green)

```
SDG 2 — Zero Hunger; SDG 15 — Life on Land: subject alignment only. This study measured
no yield, no farm outcome and no field impact.

NDP IV and Vision 2040: subject alignment with national priorities on agriculture and
digital capability. No economic or adoption impact is claimed or measured.
```

**KEY REFERENCES** (green)

```
· L. Breiman. Random forests. Machine Learning, 45(1):5–32, 2001.
· D. R. Roberts et al. Cross-validation strategies for data with temporal, spatial,
  hierarchical or phylogenetic structure. Ecography, 40(8):913–929, 2017.
· P. Ploton et al. Spatial validation reveals poor predictive performance of large-scale
  ecological mapping models. Nature Communications, 11:4540, 2020.
```

These are real works, but verify volume and page numbers against the library copy
before printing; the builder must not silently renumber them.

Foot of column 3, 21 pt:

```
Measured laboratory data, AfSIS Phase I, ODC-By. Sensor error simulated, not measured.
Results reproduced from export_afsis_real/results.json.
```

QR frame, 60 × 60 mm, beside the provenance line: `Scan for the prototype demonstration`.

---

## 6. The three images

### 6.1 V1 — validation-design comparison

- Message: same model, same data, two designs, two answers.
- Data: `results.validation_gap[model=random_forest]` → `r2_random` 0.33752,
  `r2_spatial` 0.08550, `gap_mean` 0.25202; `results.baseline_rmse.spatial`.
- Form, following the reference chart: horizontal bars, value printed at each bar end,
  a vertical dashed line at the reference value labelled "field mean, R² 0", two bars
  only. Strong `#365F8B` for the random split, light `#8FA8C4` for the spatial split,
  grey `#B3B3B3` for the baseline. Axis "R²", ticks −0.1 to 0.4.
- Do not plot ridge or PLS: −8.19 and −0.33 flatten the axis. Say so in the caption.
- Caption: `Random forest, 5 seeds. Random splitting 0.338; whole areas held out 0.086.
  Ridge and PLS are below the axis floor and are omitted here, not from the results.`

### 6.2 V2 — interval concept

- Message: an interval is what lets a system refuse.
- Data: `results.interval.mean_width` 4.21450, `.empirical_coverage` 0.88762,
  `.nominal` 0.9; band cuts from `bands.json`: 0.650820752 and 1.439275861.
- **Form:** one horizontal axis "Total carbon (%)" 0–5; three bands drawn between the
  cuts 0.651 and 1.439 and the axis ends; **one** interval bar, length equal to the measured
  mean width 4.21, shown once. It swallows all three bands, which is the point. Do not draw
  a second, reportable interval: with this model no reportable interval exists.
- **Caption:** `Measured width 4.21 points against a band 0.788 wide. Every prediction is
  therefore declined. Coverage on unseen blocks: 88.8% against a nominal 90%.`

### 6.3 V3 — interface strip

- Message: the method is operable, and it says no.
- Data: existing `screenshot_*.png` from the repository; crop to the numbers area.
  If a fresh capture is taken, it must be from the running service with
  `MODEL_DIR=export_afsis_real` so the real-bundle banner shows.
- Form: one strip, two panels, captions under each: "researcher view" and "field view".
- Rule: no invented interface, no mock-up, no re-drawn chart screenshot.

---

## 7. Filled data object

Machine-readable copy for any generated table. It agrees with section 5.

```json
{
  "header": {
    "title": "Machine Learning for IoT-Based Soil Health Prediction in Sub-Saharan Africa: Spatial Validation and Sensor-Error Robustness",
    "application": "Total carbon prediction from soil measurements; comparison of random against geographically blocked validation",
    "faculty_department": "Faculty of Engineering and Technology | Department of Computer Science",
    "specialization": "Machine Learning",
    "researcher": { "name": "Adrian Rugaba Asiimwe", "reg_id": "S24B23/054", "access_no": "" }
  },
  "concept_triad": {
    "why_problem": "Reported skill is produced by random splitting, which puts near-duplicate samples from the same field on both sides of the test, so the score describes interpolation within known ground rather than performance on new ground.",
    "how_technique": "Five regressors on 926 measured samples under two designs: 5-fold shuffled K-fold, and GroupKFold over 10 blocks from KMeans on site coordinates, repeated with Gaussian noise at five levels, with split-conformal intervals scored on unseen blocks.",
    "what_artifacts": "A measured difference between designs, a stated error level at which the model stops beating a mean prediction, and a hash-verified service that refuses to report when its interval is too wide."
  },
  "objectives": [
    { "description": "Run the pipeline on measured AfSIS laboratory data rather than a synthetic stand-in", "status": "Completed" },
    { "description": "Quantify the fall in skill when whole areas are held out", "status": "Completed; 0.252 in R2" },
    { "description": "Find the simulated error level at which the model stops beating a mean prediction", "status": "Completed; 0.5 of the training SD" },
    { "description": "Attach calibrated intervals and gate the output on width", "status": "Completed; 88.8% against 90%" },
    { "description": "Test a spatial R2 of at least 0.50 for pH under simulated sensor error", "status": "Not run; the run used total carbon" },
    { "description": "Test transfer to Uganda by leave-one-country-out", "status": "Not run; Uganda is 32 rows, 3.5%" },
    { "description": "Validate against soil measured with the planned sensor hardware", "status": "Not started; no sensor deployed" }
  ],
  "methodology_pipeline": [
    { "step_name": "Coalesce", "details": "One row per record; CROPNUTS pH and EC joined with ICRAF texture and total carbon; RRES organic carbon counted, not used" },
    { "step_name": "Transform", "details": "Total carbon in percent, log-transformed; imputation and scaling fitted on training folds only" },
    { "step_name": "Split twice", "details": "5-fold shuffled K-fold; GroupKFold over 10 spatial blocks from KMeans on site coordinates" },
    { "step_name": "Tune inside folds", "details": "Grid search nested in every training fold; inner folds blocked the same way" },
    { "step_name": "Perturb", "details": "Gaussian noise at 0, 0.1, 0.25, 0.5, 1.0 of the training SD; arms trained clean and trained noisy" },
    { "step_name": "Calibrate and serve", "details": "Split-conformal intervals scored on unseen blocks; refusal when missing, too wide, or crossing a cut" }
  ],
  "datasets": [
    { "name": "AfSIS Phase I wet chemistry (real)", "size_specs": "926 samples, 58 sites, 16 clusters, 19 countries; 32 Ugandan rows (3.5%); ODC-By", "role": "All reported results" },
    { "name": "Synthetic stand-in", "size_specs": "160 sites, 8 clusters", "role": "Test fixture and smoke run only; excluded from every quoted result" }
  ],
  "results": {
    "benchmark_leaderboard": [
      { "model_name": "Random forest", "metric_val": 0.0855 },
      { "model_name": "Gradient boosting", "metric_val": 0.0781 },
      { "model_name": "Mean baseline", "metric_val": -0.0303 },
      { "model_name": "PLS", "metric_val": -0.3327 },
      { "model_name": "Ridge", "metric_val": -8.1899 }
    ],
    "performance_table": [
      { "model": "Random forest", "size": "100 trees", "latency": "not measured", "precision": "n/a (regression)", "recall": "n/a (regression)", "score": "R2 0.338 random / 0.086 spatial; RMSE 1.339; MAE 0.864; RPIQ 0.888" },
      { "model": "Gradient boosting", "size": "100 trees", "latency": "not measured", "precision": "n/a (regression)", "recall": "n/a (regression)", "score": "R2 0.295 / 0.078; RMSE 1.344; MAE 0.858; RPIQ 0.885" },
      { "model": "PLS", "size": "3 components", "latency": "not measured", "precision": "n/a (regression)", "recall": "n/a (regression)", "score": "R2 -0.112 / -0.333; RMSE 1.616; MAE 0.955; RPIQ 0.736" },
      { "model": "Ridge", "size": "alpha 0.3 to 10", "latency": "not measured", "precision": "n/a (regression)", "recall": "n/a (regression)", "score": "R2 -0.187 / -8.190; RMSE 4.244; MAE 1.101; RPIQ 0.280" },
      { "model": "Mean baseline", "size": "no parameters", "latency": "not measured", "precision": "n/a (regression)", "recall": "n/a (regression)", "score": "R2 -0.002 / -0.030; RMSE 1.421; MAE 1.000; RPIQ 0.837" }
    ]
  },
  "explainability_and_deployment": {
    "key_insights": [
      "The design accounts for 0.252 of a 0.338 R2 on the same model and data.",
      "Spatially, random forest reaches RMSE 1.339 against 1.421 for the field mean; MAE 0.864 against 1.000.",
      "R2 falls to 0.039 at 0.25 of the training SD and to -0.094 at 0.5, where the model stops beating the mean.",
      "Training on noisy inputs does not repair the loss: 0.106 against 0.088 at 0.10 noise.",
      "Intervals: 88.8% coverage against 90% nominal, mean width 4.21 points on a 0.93 median; 5.3 bands wide, so every prediction is declined.",
      "Shuffled-target control collapses to between -0.005 and -0.078 for all five models.",
      "The spatial value moves with the blocking (0.079 to 0.153 across 5 to 50 blocks), so it is reported with its sensitivity, not as a constant."
    ],
    "hardware_acceleration": { "hardware": "CPU only; no GPU, no edge device, no accelerator deployed", "throughput": "", "engine_format": "joblib bundle, hash-verified at load (sha256:57ae8583074e476a), scikit-learn 1.8.0" },
    "alignment": { "sdgs": ["SDG 2 - Zero Hunger (subject alignment only)", "SDG 15 - Life on Land (subject alignment only)"], "national_vision": ["NDP IV - subject alignment only", "Vision 2040 - subject alignment only"] }
  }
}
```

`hardware_acceleration.throughput` stays empty: nothing was measured. Do not print a
latency, throughput or memory figure anywhere.

---

## 8. Checks before delivery

### 8.1 Wording

Banned, any case: `framework`, `accuracy`, `accurate`, `reliable`, `reliability`,
`precise`, `precision`, `validated`, `robust`, `robustness`, `actionable`, `yield`,
`cost`, `affordable`, `adoption`, `smallholder`, `SOC`, `926 sites`.

Allowed and expected: `validation`, `validation design`, `spatial validation`, `random
split`, `tolerance`, `interval`, `coverage`, `RPIQ`, `RMSE`, `MAE`.

Two narrow exceptions: `Robustness` may appear once, in the title, only under
`TITLE_MODE = "robustness"`; `Soil health` may appear once, in the title, and nowhere
else.

```powershell
Select-String -Path poster-text.md -Pattern "framework|accuracy|accurate|reliab|precis|validated|actionable|smallholder|SOC|926 sites" -CaseSensitive:$false
```

Must return nothing.

### 8.2 Arithmetic

Run from the repository root. Every printed figure is checked against the bundle at
the precision printed. A new printed figure requires a new assertion.

```python
import json
r = json.load(open("export_afsis_real/results.json"))
s = json.load(open("export_afsis_real/cv_supplement.json"))
g = {x["model"]: x for x in r["results"]["validation_gap"]}
rf, iv = g["random_forest"], r["results"]["interval"]
sweep = {(x["arm"], x["noise"]): x["r2_mean"]
         for x in r["results"]["noise_sweep"] if x["model"] == "random_forest"}
want = [
    (f'{rf["r2_random"]:.3f}', "0.338"),
    (f'{rf["r2_spatial"]:.3f}', "0.086"),
    (f'{rf["gap_mean"]:.3f}', "0.252"),
    (f'{rf["rmse_spatial"]:.3f}', "1.339"),
    (f'{r["results"]["baseline_rmse"]["spatial"]:.3f}', "1.421"),
    (f'{iv["empirical_coverage"] * 100:.1f}', "88.8"),
    (f'{iv["mean_width"]:.2f}', "4.21"),
    (f'{sweep[("train_clean", 0.25)]:.3f}', "0.039"),
    (f'{sweep[("train_clean", 0.5)]:.3f}', "-0.094"),
    (f'{sweep[("train_noisy", 0.1)]:.3f}', "0.106"),
    (f'{sweep[("train_clean", 0.1)]:.3f}', "0.088"),
    (f'{s["models"]["random_forest"]["spatial"]["mae"]["mean"]:.3f}', "0.864"),
    (f'{s["models"]["random_forest"]["spatial"]["rpiq"]["mean"]:.3f}', "0.888"),
]
for got, expected in want:
    assert got == expected, f"bundle says {got}, poster expects {expected}"
print("all printed figures match the bundle")
```

### 8.3 Physical

- A0 landscape, 1189 × 841 mm, all six sections inside the 20 mm margin.
- Three images, no fourth. Zoom to 100% to confirm no text below 20 pt.
- No generated image contains a letter or a digit; inspect each asset.
- Greyscale proof: the two chart bars must remain distinguishable in black and white.
- QR frame at least 60 × 60 mm.
- Read at 1.5 m: bars, findings, table and conclusions legible without leaning in.

---

## 9. Do not do these things

1. Do not take a number from `PROTOTYPE_REPORT.md` or `REPORT_SCOPE_SHEET.md`.
2. Do not add a "synthetic data" disclaimer; the correct line is "sensor error
   simulated, not measured".
3. Do not present simulated noise experiments as sensor validation.
4. Do not print precision, recall, latency, throughput or memory. None were measured;
   the task is regression.
5. Do not print SMART-AG's scores or characterise it as wrong. It is mentioned at most
   in one sentence, as the closest built system.
6. Do not add an agronomic recommendation, a yield claim or a cost claim.
7. Do not invent a citation. The three in 5.4 are real works to be verified, not to be
   replaced by guessed ones.
8. Do not copy any content, figure, wording or claim from `Poster ref.pdf`. Only the
   grid, bar colours, metadata labels and section order are adopted.
9. Do not redraw or generate the university crest.

---

## 10. What was taken from the reference, and what was not

| Adopted | Rejected or adapted |
|---|---|
| Landscape 1.41 ratio, three columns at 35/33/31 | Portrait A0 and the six-zone map: withdrawn |
| Identity block: crest left, five labelled metadata lines | Portrait title band: not used |
| Maroon bar for argument sections, green for documentation | Exact hues: sampled approximately, re-eyedrop at 300 dpi |
| Why / How / What triad | Its content: not copied |
| SO-numbering with status in italics | Its objectives |
| E-numbering for method steps | Its experiments |
| Numbered findings with bold lead-ins | Its findings |
| Metrics table under the findings | Its columns (Size, Latency, Prec., Rec., F1): replaced by R², RMSE, MAE, RPIQ |
| "Hardware Architecture & Acceleration" section | Its GPU, ONNX and throughput claims: replaced by CPU-only compute and an explicit "not measured" |
| Alignment block with SDGs and national plan | Its SDG choices: SDG 2 and 15 with "subject alignment only" |
| Numbered reference list of three | Its references |
| Steel-blue chart palette | Its chart |

---

## 11. Deliverables and build report

Deliver: `poster.pdf` (A0 landscape), `poster-source.*`, `assets/` with the three
images at vector or 300 dpi, `poster-text.md`, `numbers.md`, `build-report.md`.

```
CHECKS
wording scan        PASS/FAIL  (output attached)
arithmetic check    PASS/FAIL  (output attached)
three images only   PASS/FAIL
no text in images   PASS/FAIL (per asset)
grid and margins    PASS/FAIL
greyscale proof     PASS/FAIL

CONFIRM WITH RESEARCHER
- title: robustness or tolerance
- whether "soil health" may stay in the title
- access number, supervisor, event and date
- logo file
- QR destination

FIGURES SHOWN
<value> <file> <json path>   (one line each)
```

Do not report a check as PASS unless the command or inspection actually ran.
