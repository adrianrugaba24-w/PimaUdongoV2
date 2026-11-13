# Poster content pack: PimaUdongo

Status: **draft for researcher approval.** No layout, no rendering, no imagery.
Built against `export_afsis_real/` only. Where a required detail is absent from the
workspace it is marked **NOT FOUND** rather than filled in.

Source of record for every number: `export_afsis_real/results.json` and
`export_afsis_real/model_meta.json`. Anything from a `.md` file is treated as
commentary, not evidence.

---

## 1. Project understanding

The study asks whether the skill reported for a soil-carbon model is an artefact of
how the model was tested. It trains five regression models on 926 AfSIS laboratory
soil samples with five laboratory features, then answers the same question twice:
once with a random split, and once with folds blocked by geography, so that whole
areas are held out. It then repeats the spatial test with Gaussian noise added to
the inputs, at five levels, to represent sensor error, and attaches split-conformal
prediction intervals that a reliability gate can use to refuse an answer.

The investigation is the **comparison of validation designs**; the software is a
demonstration that the comparison can be operated end to end, with provenance
checks and two audience views. The prototype is not the contribution.

What the study is not: it deployed no physical sensor, collected no Ugandan soil,
and measured no sensor error. Sensor error is simulated with parameters marked as
assumed. These are stated in the poster rather than qualified away.

---

## 2. Poster narrative

1. Reported skill for soil-property models is usually produced by random splitting,
   which puts near-duplicate samples on both sides of the split.
2. Holding out whole areas instead of individual rows answers a harder and more
   relevant question: does the model work on ground it has not seen?
3. On this dataset the answer changes from 0.338 to 0.086 measured as R2, with the
   blocked model still only marginally better than guessing the field mean.
4. Adding noise to the inputs erodes what remains: the blocked model stops beating
   the field mean between 0.25 and 0.5 of the training standard deviation.
5. Prediction intervals are the mechanism that lets a system say "not enough
   evidence" instead of printing a number; on this feature set they cover 88.8% of
   unseen blocks at a nominal 90%, but the mean width is 4.21 percentage points on
   a target whose median is 0.93.
6. Conclusion: the validation design, not the model choice, decides what a reported
   score means. A system built on this data must state its interval and refuse when
   the interval is too wide.

---

## 3. Poster content

### A. Title and identity

Proposed title (needs one decision, see section 7):

- As written in the stored preference: *Machine Learning for IoT-Based Soil Health
  Prediction in Sub-Saharan Africa: Spatial Validation and Sensor-Error Robustness*
- Recommended: same, with **Tolerance** in place of **Robustness**, because the
  measured result is a noise threshold (0.5) and a spatial R2 of 0.086, which does
  not support a claim of robustness.

Author: **Adrian Rugaba** (read from the file name
`Adrian_Rugaba_Systematic_Literature_Review_enhanced.pdf`; confirm spelling).
Registration number: **NOT FOUND**.
Department and university: **NOT FOUND** in the workspace; `SMART_AG_BRIEF.md`
refers to Uganda Christian University for the other project, which is not evidence
for this one.
Supervisor: **NOT FOUND**.
Research event and date: **NOT FOUND**.

The title as approved (if approved) is not stored anywhere in the workspace. If the
approved title differs from the line above, the poster must use the approved one.

### B. Research overview

**Background.** Soil-carbon measurement is expensive and slow, so prediction models
are trained on laboratory data and reported with a single performance score. That
score is almost always produced by splitting samples at random. Where samples come
from clustered field campaigns, a random split places near-duplicates of the same
soil on both sides of the test, so the score describes interpolation within known
ground rather than performance on new ground. Field deployment adds a second
problem the score does not capture: a low-cost sensor reports with error, and a
model trained on laboratory values has never seen that error.

**Problem statement.** Reported performance for soil-property models does not
indicate whether the model generalises to new locations or survives realistic
input error. Without those two tests, a high score cannot be distinguished from an
over-optimistic one, and no statement can be made about how much sensor error a
prediction tolerates.

**Research gap.** Published evaluations of soil-property prediction rarely combine
a geographically blocked test with an explicit sensor-error sweep on the same data
and model set, so the size of the difference between validation designs is not
reported as a quantity.

**Aim.** To measure how much of the reported skill of a soil-carbon prediction model
depends on the validation design, and how much input error it tolerates before the
skill disappears.

**Research question.** For total carbon predicted from five laboratory features,
how far does measured skill fall when test sites are blocked geographically rather
than split at random, and at what level of simulated sensor error does the blocked
model stop outperforming a prediction of the field mean?

### C. Research methodology

- **Dataset.** AfSIS Phase I wet-chemistry values, licenced ODC-By, 926 samples from
  58 named sites in 16 clusters across 19 countries; 32 samples from Uganda
  (3.5%), reported as a focus subset and not used as a separate validation set.
- **Target.** Total carbon, percent. Log-transformed before fitting; all metrics are
  reported after back-transformation. Not soil organic carbon; organic carbon
  exists in the source data and was counted but not used.
- **Features.** pH (water), EC, clay, sand, silt — all laboratory measurements,
  none measured by a field sensor.
- **Preparation.** One row per record; missing values imputed with the training-fold
  median only; scaling fitted inside each training fold; no transform or imputation
  touches a test fold.
- **Models.** Mean baseline, ridge, PLS, random forest (100 trees), gradient
  boosting (100 trees). Tuning by grid search nested inside every training fold.
- **Random validation.** 5-fold shuffled K-fold, repeated over 5 seeds.
- **Spatial validation.** Records grouped by site, KMeans on per-site coordinates
  produces 10 blocks, GroupKFold holds out whole blocks; inner tuning folds blocked
  the same way.
- **Sensor-error experiments.** Gaussian noise added to input features, scaled per
  feature by the training-fold standard deviation, at 0.0, 0.1, 0.25, 0.5 and 1.0.
  Two arms: training on clean inputs only, and training on noisy inputs as well,
  to test whether augmentation rescues the model.
- **Uncertainty and reliability.** Split-conformal intervals calibrated on held-out
  blocks and scored on unseen spatial blocks; a gate refuses to render a judgement
  when the interval is missing, too wide, or crosses a stored band cut.
- **Controls.** A shuffled-target run must collapse to zero; block count and
  partition seed are varied to test the stability of the spatial result.

Pipeline as a sequence for the strip visual:

`AfSIS lab values → 5 features → random split | blocked split → 5 models →
interval + report-or-refuse`

### D. Experimental results

The comparison that carries the poster:

| Comparison | Value | What it measures |
|---|---|---|
| Random split, R2 | 0.338 | Skill when samples are split at random |
| Spatial blocks, R2 | 0.086 | Skill on whole areas held out |
| Difference | 0.252 | How much of the reported skill the split accounts for |
| Field-mean baseline, RMSE | 1.421 | What a single mean prediction achieves spatially |
| Best model, RMSE spatially | 1.339 | Margin over that baseline, about 6% |

Supporting results, each qualified:

| Result | Value | Reading |
|---|---|---|
| Interval coverage | 88.8% against 90% nominal | Calibration close to nominal on unseen blocks |
| Mean interval width | 4.21 percentage points | Wider than 4 times the median target (0.93) |
| Noise level where the blocked R2 crosses zero | 0.5 of the training SD | Between 0.25 (R2 0.039) and 0.5 (R2 −0.095) |
| Training on noisy inputs | No better | 0.106 at 0.10 noise against 0.089 when trained clean; below zero at 0.5 either way |
| Shuffled-target control | −0.005 to −0.078 | Near zero for all five models, as required |
| Block-count variation | 0.079 to 0.153 | The spatial value moves with the number of blocks |
| Partition-seed variation | 0.035 to 0.176 | The spatial value moves with the partition |

The last two rows are the honest footnote to 0.086: the direction of the gap is
stable, the exact spatial value is not. They came from 2-seed runs, so they are not
directly comparable with the 5-seed headline; the poster says "sensitivity runs".

### E. Visual components

**V1 — Main results (hero).**
Message: the same model, the same data, two validation designs, two different answers.
Data: `validation_gap` (random forest, random and spatial), `baseline_rmse.spatial`.
Form: two bars in one panel, R2 on the vertical axis from −0.1 to 0.4, a horizontal
reference line at 0 labelled "field mean", and a bracket between the bars labelled
with the 0.252 difference. Lightness variation only (0.338 bar light, 0.086 bar
dark) so it survives greyscale and colour blindness. Caption: *Random forest, 926
samples, 5 seeds. Random splitting reports 0.338; holding out whole areas reports
0.086. The bar heights are measured values; the baseline is a mean prediction.*
Do not place ridge or PLS on this axis: their spatial R2 (−8.19 and −0.33) would
flatten everything. State in the caption that they are omitted and why.

**V2 — Methodology pipeline.**
Message: the study is one dataset asked the same question under two designs.
Data: none beyond the design; no numbers in the graphic.
Form: five icons, left to right, thick 6 px arrows, one caption line each, no
paragraphs. Caption: *The only difference between the two lanes is how the fold
boundary is drawn.*

**V3 — Uncertainty as a decision.**
Message: an interval is what lets a system refuse.
Data: `interval.mean_width`, `interval.empirical_coverage`, `interval.nominal`, and
the stored band cuts from `bands.json` (0.651 and 1.439 percentage points).
Form: one horizontal axis in percent, 0 to 5; the three bands drawn from the cuts
0.651 and 1.439; **one** interval bar of the measured mean width 4.21, spanning all
three bands. A reportable interval is not drawn, because this model cannot produce
one: 4.21 is 5.3 times the 0.788-wide band, so the gate declines every prediction.
Caption: *Width measured; position illustrative. Coverage 88.8% against a nominal 90%
on unseen blocks; every prediction declined, because no interval fits inside a band.*

No other imagery. No decorative icons, no stock photographs, no generated sensor
renderings.

### F. Research contribution

- **What the study demonstrates.** On one dataset and one model family, the
  validation design accounts for 0.252 of a 0.338 R2. The same model that looks
  useful under a random split looks barely better than a mean prediction when whole
  areas are held out — 1.339 against 1.421 RMSE.
- **Why spatial validation matters.** It answers the question a user actually has:
  will this work on ground we have not sampled? A random split cannot answer it,
  because clustered sampling makes the test set a near-copy of the training set.
- **What the error experiments show.** The blocked model tolerates error up to about
  0.25 of the training standard deviation and has stopped outperforming the field
  mean by 0.5. Training on noisy inputs does not repair this, so augmentation is not
  a substitute for a quieter sensor or a smaller feature set.
- **How uncertainty assessment contributes.** A calibrated interval with a gate turns
  a prediction into a decision: report a band, or refuse. Coverage is close to
  nominal (88.8% against 90%), and the width is the honest cost of that guarantee.
- **What the prototype demonstrates.** That the method can be operated: a bundle
  whose hashes are checked before serving, a gate that refuses rather than guesses,
  and two audience views fed by one set of measured values.

Proportionality: the study measures one dataset, one target, five models — it does
not establish that soil-carbon prediction is impossible, only that reported skill
is design-dependent. Say so.

### G. Limitations and scope

| Question | Answer on the poster |
|---|---|
| Physical sensors used? | No. Features are laboratory wet-chemistry values that a sensor could in principle proxy. |
| Sensor errors measured or simulated? | Simulated, Gaussian, scaled to the training SD, with parameters marked as assumed. |
| Ugandan field samples? | Not collected. 32 Ugandan samples appear in the AfSIS data; none were sampled for this study. |
| Field validation? | No. No prediction has been checked against soil sampled for this project. |
| Practitioners evaluated the prototype? | No. There was no farmer or agronomist evaluation. |

Also state: laboratory values carry lab-to-lab bias and replicate records were
collapsed, so measurement error is under-represented relative to a real sensor;
intervals are marginal (one width for all inputs), not conditional on feature
values; no agronomic recommendation of any kind follows from this work.

### H. Conclusion and future work

**Conclusion.** Reported skill for this soil-carbon model is largely a property of
the validation design: 0.338 under random splitting, 0.086 with whole areas held
out, a difference of 0.252. The blocked model remains about 6% better than a mean
prediction in RMSE and stops being better than it once input error reaches roughly
half the training standard deviation.

**Takeaways.**
1. Report the split, or the score is not interpretable.
2. State the error level at which a model stops working; it is more useful than a
   single R2.
3. Report interval width beside interval coverage; a 90% interval that is 4.21
   points wide on a 0.93 median is a refusal, not an answer.

**Future work.** Measure sensor error with the actual hardware rather than assuming
it; conditional rather than marginal intervals; a leave-one-country-out test for
Uganda; run the pH target so the sensor-feasibility hypothesis can be tested.

---

## 4. Evidence register

| Displayed value | Source file | JSON path | Measures | Interpretation |
|---|---|---|---|---|
| 926 samples | results.json | `data.data_card.n_rows` (= `model_meta.n_rows`) | Row count | One row per record after coalescing |
| 58 sites, 16 clusters | georeferences.csv | `SiteName.nunique()` = 58, `ClusterCode.nunique()` = 16 | Physical grouping | **Not in the JSON**; counted from the raw file. The card's `n_sites` = 926 is the row count and must not be shown as sites |
| 19 countries | results.json | `data.data_card.countries` (19 keys) | Coverage | Includes 32 Ugandan samples (3.5%) |
| 32 Uganda | results.json | `data.data_card.focus_subset.n_rows` | Focus subset | Descriptive only, not a validation set |
| Total carbon, % | results.json | `target.name`, `target.units` | Target | Log-transformed before fitting |
| 5 features | results.json | `features` = `model_meta.feature_names` | Inputs | pH, EC, clay, sand, silt |
| 0.338 | results.json | `results.validation_gap[model=random_forest].r2_random` = 0.33752 | Random-split R2 | 5 seeds |
| 0.086 | results.json | same row, `r2_spatial` = 0.08550 | Blocked R2 | 5 seeds |
| 0.252 | results.json | same row, `gap_mean`; also `headline.validation_gap` | Difference | The poster's central quantity |
| 1.339 | results.json | same row, `rmse_spatial` = 1.33876 | Blocked RMSE | Best model |
| 1.421 | results.json | `results.baseline_rmse.spatial` = 1.42100 | Mean-prediction RMSE | Baseline for the 6% margin |
| 88.8% / 90% | results.json | `results.interval.empirical_coverage` = 0.88762; `.nominal` = 0.9 | Coverage | Scored on unseen blocks |
| 4.21 | results.json | `results.interval.mean_width` = 4.21450 | Interval width | Against `median_target` 0.93105 |
| 0.5 | results.json | `headline.break_even_noise["train_clean\|spatial"]` | Error tolerance | Between 0.25 (0.039) and 0.5 (−0.095) in `results.noise_sweep` |
| 0.079–0.153 | results.json | `results.block_sensitivity` (5, 10, 20, 50 blocks) | Stability | 2-seed runs; 10 blocks reproduces 0.0999 |
| 0.035–0.176 | results.json | `results.partition_sensitivity[random_forest]` | Stability | 2-seed runs, 5 partitions |
| −0.005 to −0.078 | results.json | `results.shuffled_control[*].r2_mean` | Control | All five models near zero |
| −8.19 | results.json | `results.validation_gap[model=ridge].r2_spatial` | Ridge collapse | Undiagnosed; do not display on the hero axis |
| sha256:57ae8583074e476a | model_meta.json | `model_version` | Bundle identity | Print in the lower band |
| afsis-2f-ddd215cc66b5 | model_meta.json | `training_data_version` | Data identity | Print in the lower band |
| ODC-By | results.json | `data.licence` | Licence | Credit AfSIS |

Rules for whoever builds the poster: read each value from the path above at build
time; do not retype from this table; if a path is missing, leave the slot empty.

---

## 5. Limitations register

Claims that must be qualified or removed:

| Claim | Status | Required handling |
|---|---|---|
| "Sensor error was validated" | False | Say "simulated at five levels with assumed parameters" |
| "Validated on Ugandan soils" | False | 32 AfSIS samples only; no Ugandan data collected |
| "Field-tested" | False | No hardware, no field deployment |
| "Reliable / accurate / precise predictions" | Unsupported qualifier | Give the number and the condition, e.g. "R2 0.086 with whole areas held out" |
| "Robust to sensor noise" | Not supported | The R2 crosses zero at 0.5 of the training SD |
| "Improves yields / saves cost / is affordable" | Not measured | Excluded entirely |
| "Framework for validation" | Wording ban | Say "method", "design", "study" |
| "SOC" | Wrong term | Total carbon |
| "926 sites" | Wrong label | 926 samples, 58 sites, 16 clusters |
| "Synthetic dataset" (the old poster disclaimer) | Now false | Say "measured laboratory data; sensor error simulated" |

---

## 6. Missing information

| Item | Why it matters | Where it should come from |
|---|---|---|
| Registration number | Identity block | Researcher |
| Department, university | Identity block | Researcher |
| Supervisor name | Identity block | Researcher |
| Event name and date | Title band | Researcher |
| Final title, and whether it is approved | Identity block; **and whether "soil health" is permitted at all**, because the project's own UI constraint C2 and agent rule 7 ban the phrase | Researcher / supervisor |
| QR destination | Lower band | Researcher: live demo, recording, or repository |
| Proposal document | Phase 1 asked for it | **NOT FOUND**: only `SLR_improved.tex` and its PDF exist |
| Dissertation / final report | Phase 1 asked for it | **NOT FOUND** in the workspace |
| Part A sensor-experiment outputs | The hypothesis about sensor feasibility is untested without them | **NOT FOUND**: no Part A results file exists |

---

## 7. Scientific consistency review

1. **Two prose reports describe a bundle that is no longer served.**
   `PROTOTYPE_REPORT.md` and `REPORT_SCOPE_SHEET.md` cite `sha256:062d36c53a562f80`,
   `afsis-3f-296718c140e3` and 407 rows — the synthetic `export/`. The served bundle
   is `export_afsis_real/`: `sha256:57ae8583074e476a`, `afsis-2f-ddd215cc66b5`,
   926 rows, `data.is_real_data = true`. Do not take poster numbers from either
   report.

2. **The review paper still says the results are synthetic.** Abstract (lines 68–70)
   and the status paragraph (909–912) say Part B results come from a synthetic
   stand-in. That is false for the served bundle. It is a paper defect, not a poster
   defect, but the poster and the paper will be read side by side.

3. **The word "framework" appears 12 times in the paper**, including the title and
   the objectives sentence at 169–170. The poster must not use it, which will read
   as inconsistent with the paper until the paper is edited.

4. **The data card mislabels rows as sites.** `data.data_card.n_sites` = 926 while
   `georeferences.csv` has 58 `SiteName` values. The researcher dashboard prints
   "926 rows · 926 sites · 19 countries" because it reads that field. The poster must
   not repeat it.

5. **The spatial R2 is reported at three different values in three experiment
   blocks** — 0.086 (5 seeds, `validation_gap`), 0.0999 (2 seeds, `block_sensitivity`
   at 10 blocks), and 0.091/0.100 (partition runs). They are not comparable because
   the seed counts differ. The poster uses 0.086 as the headline and presents the
   others as sensitivity, never side by side as if they measured the same thing.

6. **The sensor-feasibility hypothesis is untested.** It is stated for pH with an R2
   threshold of 0.50 (`SLR_improved.tex` 885–886); the run used total carbon and no
   Part A results exist. The poster must not claim sensor feasibility.

7. **Correction to earlier advice.** The real-data flag is **not** in
   `model_meta.json`, where I previously said to look. It is `data.is_real_data` in
   `results.json`, surfaced by the API as `data_is_real`
   (`soil_api.py` 264, 294, 335, 435). The conclusion is unchanged — the bundle is
   real laboratory data — but the path in the earlier instruction was wrong.

8. **The stored poster rule still mandates a "synthetic data" disclaimer.** That
   rule predates the current bundle. The lower band must instead read: *measured
   laboratory data (AfSIS, ODC-By); sensor error simulated, not measured.*

9. **The author's name is known only from a file name.** Confirm before it is
   printed.

---

## 8. Next step

Approval on four points unblocks layout:

1. Title: as stored, or with "Tolerance" for "Robustness".
2. Whether "soil health" may appear in the title at all, given C2 and rule 7.
3. Identity block details from section 6.
4. Whether the hero visual carries the sensitivity range (0.079–0.153) as a
   footnote or leaves it to the speaker notes.

Until those are answered, no layout work starts.
