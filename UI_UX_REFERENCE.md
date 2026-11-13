# UI/UX Decision Reference

Status: describes both interfaces as built, against `soil_api.py`, serving `export_afsis_real/`
(real) or `export/` (synthetic).

There are two views, and they are two audiences, not two themes. Both are reached
from one entry page.

| Route | File | Audience | Payload |
|---|---|---|---|
| `/`, `/login` | `web/login.html` | the entry page | `GET /api/login` |
| `/farmer` | `web/farmer.html` | someone holding a soil sample | `GET /api/farmer`, `POST /api/farmer/predict`, `POST /api/farmer/advice` |
| `/researcher` | `web/index.html` | examiner, supervisor, reviewer | `GET /results`, `/model-info`, `/health`, `/api/metrics` |

`/` is the entry page and is a chooser, not authentication. Every technical chart
and table lives in the researcher view; none of them appear on a farmer screen.
§3–§13 describe the researcher view. §14–§19 describe the farmer side: the view
itself, the session view, the supplied layout as built, readings over time, the
entry gate, and — in §19 — the ranked next steps and the sensor list.

**How to use this.** Before adding, moving or restyling an element, find it in §3 and §4 (researcher)
or §14 (farmer). Every element has a named data source and a defined behaviour when that source is
absent. If an element is not in one of those sections, it does not exist yet and needs a row adding
before it is built.

`REPORT_SCOPE_SHEET.md` governs what the written report may claim. This document governs what the
interface may show. They share one rule: nothing is displayed that is not in a generated artefact.

---

## 1. Hard constraints

These are not stylistic preferences. Eight are enforced by tests and fail the build.

| # | Constraint | Enforced by | Why |
|---|---|---|---|
| C1 | The page contains the exact string `Not validated on field sensors or Ugandan farms` | `tests/test_api.py::test_index_carries_the_banner_and_no_baked_numbers` | The single most likely misreading of the prototype |
| C2 | The page never contains `soil health` (case-insensitive) | same test | The model predicts one variable, not a health index |
| C3 | The page contains `fetch(` | same test | Numbers must be read, never baked in |
| C4 | `GET /` returns `text/html` and 200 | `test_index_200` | The page is served by the API, not by a static host |
| C5 | No result value is a literal in the source | reviewed; see §3 | A hard-coded number survives a re-run and silently becomes false |
| C6 | No external request: no CDN, no font host, no analytics | reviewed | The demo must work on a venue network or no network |
| C7 | Synthetic and real bundles are visually distinct at all times | §3 chip + `#kindbanner` | A synthetic number quoted as a result is the project's worst failure mode |
| C8 | No cost, adoption or farmer framing, in UI copy or in prose about it | `REPORT_SCOPE_SHEET.md` acceptance criteria | Not measured; the claim does not survive it |
| C9 | No word from `farmer_view.BANNED_TERMS` appears on a farmer screen | `tests/test_farmer_view.py` (payload + page block) | A technical word on that screen is the failure this split exists to prevent |
| C10 | Every farmer number comes from `GET /api/farmer`; the page writes no prose and bakes no number | same file, `test_the_page_writes_none_of_its_own_prose` and `test_the_page_fetches_and_bakes_no_numbers` | A typo in a figure is invisible; a figure read from a file is not |
| C11 | The traffic light carries an icon **and** words, never a colour alone | same file, `TestTrafficLight` | Colour on its own is not a signal to every reader |
| C12 | The entry page accepts any name and password, sends and stores nothing, and says so in words | same file, `TestLogin` | A form that looks like a check invites the assumption that it is one |

C5 in practice: literals are permitted only where they are **structural** — axis floors, the
texture-sum threshold that mirrors `afsis_data.clean()`, decimal places, breakpoints. They are never
permitted where they represent a measurement or a model score.

---

## 2. Vocabulary

| Term | Meaning here | Never render as |
|---|---|---|
| Spatial CV | Leave-whole-region-out cross-validation; regions built by KMeans on per-site coordinates | "leave-one-out", "group CV" |
| Random CV | Plain 5-fold over rows, ignoring geography | "standard CV" |
| Validation gap | `r2_random − r2_spatial`, paired per seed | "overfitting gap" |
| Break-even noise | Noise level at which a model stops beating the field-mean baseline | "tolerance" |
| Out of domain | One or more inputs outside the training 5th–95th percentile | "invalid", "unsupported" |
| Refused | Physically impossible input, rejected with 422 | "error" |
| Bundle | One `export*/` directory: model, metadata, results | "model" |

---

## 3. Binding map

Every visible value, its source, and its fallback. `R` = `GET /results`, `MI` = `GET /model-info`,
`H` = `GET /health`.

### Header

| Element | Source | Absent → |
|---|---|---|
| `#h1`, `document.title` | `MI.target` | `"soil carbon"` |
| `#chip` class | `R.data.is_real_data` → `chip-real` / `chip-syn` | `chip` (neutral) |
| `#chip` text | `"REAL DATA"`/`"SYNTHETIC STAND-IN"` · `R.data.dataset_version` · `MI.model_version` · `H.model_dir` | `?` per field |
| `#loaderr` | rejection from `boot()` | shows recovery instructions |
| `.chip-on` link | literal `href="/session"` | always present; the session sheet is reached from here rather than from the entry gate, because it takes the five laboratory values the farmer view never asks for |

The chip is the one element that must never degrade. If `H.model_dir` is missing the chip still
prints, because the bundle name is what distinguishes a synthetic demo from a real one.

### Banners

| Element | Source | Behaviour |
|---|---|---|
| static `.banner.b-warn` | literal, C1 | always present |
| `#kindbanner` | `R.data.kind` | rendered **only** when `is_real_data` is false |
| `#texwarn` | client-side texture arithmetic | shown when clay + sand + silt > `TEXTURE_SUM_MAX` |

### Metric cards (4, never more)

| Card | Value | Sub-line |
|---|---|---|
| Leading model, spatial | `validation_gap[0].r2_spatial` (after sort) | model name · `rmse_spatial` · `MI.units` |
| Validation gap | `gap_mean ± gap_sd` | `r2_random` vs `r2_spatial` |
| Interval coverage | `results.interval.empirical_coverage` | `nominal` · `mean_width` |
| Evidence | `data_card.n_rows` else last `cleaning_log.n_after` | `n_sites` · count of `countries` keys |

Sort order is `r2_spatial` descending, with non-finite last. The "leading model" is therefore
whichever model scored highest under spatial CV — **not** a model chosen by the page.

### Model table and dumbbell

Source: `R.results.validation_gap[]`, fields `model`, `r2_spatial`, `r2_random`, `gap_mean`,
`gap_sd`, `rmse_spatial`, `spatial_beats_baseline`.

- Rows failing `spatial_beats_baseline` get `tr.fail`.
- Baseline line cites `R.results.baseline_rmse.spatial` and `.random`.
- Axis: `lo = min(values, 0) − 0.06` clamped at `−0.55`; `hi = max(values, 1)`.
- A spatial score below `lo` is pinned to the left edge with a `clipmark` triangle and its **true**
  value printed beside it. No model is ever dropped for being bad.

### Cleaning ledger

Source: `R.data.cleaning_log[]` with `step`, `n_before`, `n_removed`, `n_after`, `reason`.

Cards show: first `n_before` → each step with `n_removed > 0` → last `n_after`. When no step removed
a row, exactly one card replaces them all: `0 rows removed`, followed by the number of steps that
ran. The full list is behind `<details>`.

### Noise small multiples

Source: `R.results.noise_sweep[]` (`model`, `cv`, `arm`, `noise`, `r2_mean`) and
`R.validation.noise_levels[]`.

One panel per `model × cv` pair. Panels are grouped in threes, collapsing to one column below 820px.
Each panel computes **its own** vertical span from its own points, plus zero, with the extremes
printed as tick labels. A shared axis is forbidden: with the real bundle the sweep spans −8.6 to
+0.1, and a shared scale flattens every model except the worst.

Break-even line reads `R.headline.break_even_noise["train_clean|spatial"]`. A `null` there means the
sweep never reached break-even and is stated in words, never rendered as a zero.

### Block and partition tables

- `R.results.block_sensitivity[]` pivoted to blocks × models.
- `R.results.partition_sensitivity[]` listed with `r2_mean ± r2_sd`, `r2_min – r2_max`,
  `distinct_partitions / n_partitions`.

### Interval panel

Source: `R.results.interval` — `nominal`, `empirical_coverage`, `coverage_sd`, `mean_width`,
`median_target`, `method`.

`width ÷ median` is the one ratio the page derives itself; it is arithmetic on two published fields,
not a new result. Coverage below nominal raises `b-warn`.

### Prediction panel

Form fields from `MI.features[]`; per field `MI.feature_ranges[name]` (`p5`, `p95`, `median`) and
`R.feature_units[name]`.

- Inputs pre-fill with the training median so the form is usable on first load. The note under the
  panel says these are example values, not a measurement.
- Each field's hint prints the training p5–p95 range **and** the training median. The median is both
  the pre-filled value and a printed statistic, and is labelled as such so the two cannot be confused
  with a measurement.
- The EC unit toggle appears only when the unit string is exactly `dS/m`. The button converts the
  displayed number and divides by the stored factor at submit; the API always receives dS/m.
- Texture sum recalculates on every keystroke and turns the chip `chip-bad` above
  `TEXTURE_SUM_MAX = 100.5`, mirroring `afsis_data.clean()`.

`POST /predict` body: `{"values": {feature: number}}`. Response fields rendered: `target`,
`prediction`, `units`, `low`, `high`, `interval_level`, `interval_empirical_coverage`,
`model_version`, `training_data_version`, `out_of_domain`, `out_of_domain_features[]`, `data_is_real`,
`interval_warning`, and `model_name` (used to look up that model's CV row).

422 body: `detail.error`, `detail.message`, `detail.offending[].{feature}.{given, physically_valid_range}`.
The page prints the given value beside the physical range for each offending field.

### Provenance line

`dataset_version | model_version | rows | target | units | model_dir | licence`. Monospace, wraps on
word boundaries, never truncated.

---

## 4. Component inventory

| Class | Use | Rule |
|---|---|---|
| `.card` | every section | one idea per card |
| `.metric` | headline numbers only | exactly four; a fifth means one is not a headline |
| `.chip` + `-real/-syn/-ok/-bad` | state at a glance | `-bad` is reserved for physical impossibility and synthetic data |
| `.banner.b-warn` | caveat that does not block use | one per card maximum |
| `.banner.b-bad` | the number below is not usable as evidence | includes synthetic, out of domain, load failure |
| `.step` + `.cut/.fin` | ledger | `-cut` for removals, `-fin` for the final count |
| `.mini-wrap/.minicap` | small multiple | caption states model, CV type and line meaning |
| `.num` | numeric cell | always `tabular-nums`, always right-aligned |
| `details > summary` | anything longer than 6 rows | collapsed by default |

SVG classes: `.ax` axis, `.grid` dashed gridline, `.zero` zero reference, `.tk` tick, `.lab` row
label, `.vk` value label, `.conn` dumbbell connector, `.dot-r` hollow random, `.dot-s` filled
spatial, `.clipmark` off-axis marker, `.s` series line, `.dash` noisy-train arm.

---

## 5. Visual system

Tokens are CSS custom properties on `:root`, overridden by `[data-theme=dark]` and by
`prefers-color-scheme` when no theme is set explicitly.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `#f4f6f3` | `#111713` | page |
| `--card` | `#fff` | `#1b231e` | surface |
| `--ink` | `#1c2a22` | `#eef5ee` | primary text |
| `--muted` | `#66756c` | `#a3b1a6` | secondary text |
| `--line` | `#dde4df` | `#344238` | borders, gridlines |
| `--a` (accent) | `#26734d` | `#79d39c` | primary action, spatial series |
| `--o` (ochre) | `#c5671a` | `#f0a34b` | warning, noisy arm, clip marks |
| `--bad` | `#a12b1f` | `#ff8f7a` | refusal, synthetic |
| `--slate` | `#5a6b60` | `#9aa8a0` | zero line |

Type: 15px/1.5 body; h1 20; h2 14.5; h3 12 uppercase tracked; metric value 26; prediction 32; note
12.5; hint 11.5; all numerics monospace. Layout: 1100px max, 4 cards → 2 at 920px → 1 at 520px;
two-column grids collapse to one at 920px.

Colour never carries meaning alone: the two CV arms differ by fill **and** the caption names them;
warnings carry text, not just tint.

---

## 6. Chart contract

Any chart added to this page satisfies all six.

1. **Own scale or an explicit reason.** Series that differ by more than an order of magnitude get
   separate panels or separate axes. A shared axis that flattens a series is a bug, not a choice.
2. **Extremes printed.** The top and bottom tick of every axis is a real data value, not a rounded
   bound, so a reader can read the range without hovering.
3. **No silent clipping.** A point outside the drawn range is pinned with `clipmark` and its true
   value printed. Points are never dropped, and never drawn at the boundary as if they were there.
4. **Zero is drawn when it is in range**, as a dashed `--slate` line, because the field-mean baseline
   is the reference the whole page argues against.
5. **No reference line on an axis the experiment did not vary.** A flat baseline across an unswept
   dimension is a fabrication.
6. **Every series traces to an array in `results.json`.** No interpolated, smoothed or illustrative
   curves.

---

## 7. Numbers and units

- `fmt(v, d)` → `n/a` for null, undefined or non-finite. Never `0`, never `—`, never blank.
- `pct(v, d)` multiplies by 100 and appends `%`; default one decimal. A nominal level renders at
  zero decimals.
- R² and gap: 3 decimals. RMSE and MAE: 3 decimals. Interval width: 2. Prediction: 2.
- Units always follow the number and come from `MI.units` or `R.feature_units`, never typed.
- Negative R² is displayed as negative. It is a finding, not an error state, and is never clipped to
  zero or hidden behind a tooltip.
- Percent-difference and ratio language is permitted only where both operands are published fields.

---

## 8. Interaction contracts

| Situation | Required behaviour |
|---|---|
| Load | Parallel `fetch` of `/results`, `/model-info`, `/health`. `/health` failure is non-fatal. Any other failure replaces the body with recovery instructions. |
| Bundle degraded (`--quick`: no noise sweep, reduced blocks) | Each section renders its own "No … in this run" note. The page never shows an empty card and never invents a substitute. |
| Synthetic bundle | Chip turns `chip-syn`, `#kindbanner` appears, and every prediction carries a second synthetic warning. |
| Impossible input | 422 rendered as a refusal naming the offending field, the value given and the physically valid range. No prediction is shown. |
| Extrapolated input | 200 with a result **and** a `b-bad` banner listing each out-of-domain feature with its training p5–p95. The number is shown so the reader can see how the model fails, not withheld. |
| Texture sum > 100.5 | Inline warning before submit; the request is still sent, and the API is the authority. |
| Missing field | Client-side check lists the missing fields by label; no request is sent. |
| Prediction rendered | Value, interval, measured coverage, spatial and random CV scores, both version hashes, the one-sentence reading of what that spatial score means, and `interval_warning` when the API returns one. The panel is `role="status"` with `aria-live="polite"` and `aria-atomic="true"`, so the result is announced and not only drawn. |
| Theme | Button toggles `data-theme` between `light` and `dark`; absence follows the OS. |
| Print | Actions hidden, sticky header released, cards avoid page breaks, all `<details>` expanded. |

---

## 9. Copy rules

**Banned.** `soil health` (C2). Cost, adoption, affordability, farmer, smallholder framing (C8).
Unqualified `accurate`, `reliable`, `precise`, `validated`. Agronomic advice, ratings, thresholds,
or any sentence that tells a reader what to do with their soil. `predicted SOC` when the target is
total carbon.

**Required.** Every comparison names both CV designs. Every prediction states its target as a
laboratory measurement, not a stock and not a quality rating. Every coverage figure states the level
it is measured against. Every synthetic surface says so twice — chip and banner.

**Tone.** State the number, then state what limits it. A sentence that only reassures does not belong
on the page; neither does one that only alarms. The model's weakness is content, not a disclaimer.

These rules govern the researcher view. The farmer view has its own, stricter rules in §14, and a
word that is merely discouraged here is banned outright there.

---

## 10. Accessibility and print

Present: semantic landmarks, `role="img"` with a descriptive `aria-label` on every SVG, visible
`:focus-visible` outlines at 2px in ochre, labels bound to inputs, tables with `<th>`, colour never
sole-carrier, `prefers-color-scheme` honoured, `<main>` carrying `aria-busy` until the first render
settles, and the prediction panel as a polite live region. The theme button names the mode it will
switch to and carries `aria-pressed`.

Print (`@media print`): white background, static header, buttons hidden, `break-inside: avoid` on
cards and steps, `<details>` forced open. The page is designed to survive being printed once and
read on paper.

---

## 11. Rejected patterns

Recorded from the review of an externally produced dashboard, kept as a rejection list.

| Pattern | Why it is banned here |
|---|---|
| Computing a prediction in JavaScript | The accepted draft recomputed the generator's own answer key, minus its region terms, and presented that as the model's prediction |
| Simulating a prediction (animation, ring, spinner that resolves to a fixed value) | It is a claim about the model with nothing behind it |
| Drawing a curve not present in `results.json` | The draft's noise curves disagreed with the real sweep in every row |
| A flat reference line across a dimension the experiment never swept | Invents an experiment |
| A static "all tests passing" badge | Goes stale silently; state it in the report with a date instead |
| Invalid utility class names | Fail silently and leave the layout broken in a way nobody notices |
| Unsynchronised slider and numeric display | Two sources of truth for one input |
| Loading fonts or scripts from a CDN | Breaks the offline guarantee |
| A dashboard that ships its own predictor | The retracted mock (§15.1) computed SOC in JavaScript, printed a spatial R² of 0.338 labelled as random, invented a 0.590, and drew a benchmark curve no bundle contains. Five bans above, in one file |
| A confidence band narrower than the calibrated one | It shows the opposite of the finding: 0.24 against a measured half-width of 2.11 |

---

## 12. Change checklist

`UI_BUILD_REPORT.md` records the interface as it stands and the gap list behind this checklist; this
section is the gate a change has to pass.

Before any UI change is merged:

- [ ] `python -m pytest tests/test_api.py -q` — all pass
- [ ] `python -m pytest tests/test_farmer_view.py -q` — all pass, for any change that touches copy
- [ ] Script block extracted and `node --check` — syntax clean
- [ ] `soil health` absent; C1 banner string present; `fetch(` present
- [ ] Every new rendered number traced to a field in §3 or §14, no literal results
- [ ] New field added to §3 or §14 with its absent-value behaviour
- [ ] Re-checked against the `--quick` fixture (sections degrade, none vanish)
- [ ] Print preview at A4, and at 520px width
- [ ] No new network request
- [ ] Neither view links to a route that does not exist

---

## 13. Open decisions

Not yet resolved, then what this pass closed. Listed so they are decided once, deliberately, rather
than drifting.

1. **Negative predictions are clamped to zero by the API** (`max(0.0, raw)`) and the raw value is not
   returned. A clamped value renders as `0.00`, which reads as a precise measurement of zero. Either
   return the raw value and display both, or state in the panel that a negative fit is reported as zero.
2. **The interval floor is clamped the same way** (`max(0, pred − half)`), and the page cannot tell a
   clamp from a quantile. Seen live on the real bundle: a prediction of 0.96 is rendered as
   `90% interval: 0.00 to 3.06` while the calibrated mean width is 4.21, so the band on screen is
   ~3.07 wide, not 4.21, and the lower bound reads as a physical zero rather than a truncation.
   Fix is a sentence plus the distance above the prediction; how to word it is still open.
3. **The Evidence card counts countries**, while the unit of spatial generalisation is the cluster
   (16 on the real bundle). Clusters next to row count is arguably the more honest denominator.
4. **Interval width is 4.53× the median measured value on the real bundle.** Currently a note inside
   the interval card. It may belong in the metric cards, since it is the single most decision-relevant
   number on the page after the gap.
5. **Theme choice is not persisted** across reloads. The button now opens naming the mode it will
   switch to and carries `aria-pressed`; persistence is still absent.
6. **Feature–target correlation is absent from the page.** The audit found |r| ≤ 0.17 for every input
   against total carbon, which explains the spatial score better than anything currently displayed.
   A single strip of correlation values would be the most informative addition available.
7. **The farmer range bar can show a negative lower end.** On the real bundle the median input gives
   `-1.15 to 3.06 per cent`, and the bar draws it, because clamping it to zero would hide how wide
   the range is. A negative percentage is not physically meaningful to a reader, though, and the
   section has no note explaining it yet. The bar is honest and unexplained - the fix is one
   sentence, and its wording is still open.
8. **`sites.json` is written but no view reads it.** Decision 11 (a real plot of sample locations
   coloured by spatial fold, no basemap, no "your field" pin) is not built. The file and its
   fold-alignment assertion exist; the panel does not.

Closed during the implementation pass:

- `interval_warning` was returned by `/predict` and dropped by the page. It now renders as an "About
  the interval" note beneath the score interpretation.
- The prediction output had no live region. `#out` is now `role="status"`, polite and atomic, and
  `<main>` carries `aria-busy` until the first render settles.

---

## 14. The farmer view (`web/farmer.html`)

The same model, the same numbers, a different reader. Nothing here is a simplified calculation: a
farmer answer and a researcher answer for the same five inputs come from the same prediction and the
same interval. Only the words change.

### 14.1 Where the words live

Every sentence on a farmer screen is written in `farmer_view.py` and arrives in the JSON. The page
holds markup and no prose of its own. That is not tidiness - it is what makes the banned-term test
able to say something true, because the scanner walks the payload and the page block separately, and
the page block has no sentences left to fail on.

| Element | Source | Absent → |
|---|---|---|
| `#brand` | `target.label` (`"Soil carbon"`, fixed) | never absent |
| `#explainer` | `target.explainer` | never absent |
| `#data-notice` | `target.notice`, branched on `target.is_sample_data` from the bundle | the real-data wording |
| `#signin-*` | removed: the gate is its own page (`/`), not an overlay (§14.6) | n/a |
| `#form-title`, `#form-hint`, `#go` | `form.title` / `.hint` / `.submit` | never absent |
| form fields | `form.fields[]` ← `/api/metrics` `features[]` | a field with no handbook wording renders `handbook: false` on a neutral label |
| `#r-headline`, `#r-sub` | `result.headline` / `.sub` | see §14.3 |
| `#light` | `result.light.{key,icon,words}` | unknown confidence falls back to the red light |
| `#track`, `#fill`, `#pin`, `#end-*` | `result.bar` (`§14.4`) | `result.bar` is null and the bar is not drawn |
| `#track[aria-label]` | `result.bar.aria_template`, filled by the page | the template is written in Python so it is scanned |
| `#bar-caption` | `result.bar.caption` | with the bar |
| `#step-*` | `result.next_step` (`title`, `body`, `how_to_read`, `lab_note`) | never absent |
| `#r-caveat` | `result.caveat` | never absent |
| `#s-title`, `#s-headline`, `#s-body`, `#s-value` | `sensor` (`§14.5`) | `value` null renders an empty figure, never a zero |
| `#learn` | `learn_more.visible` | hidden, and it is `false` until sourced references exist |
| `#researcher-link` | `nav.researcher` / `.researcher_href` | never absent |
| `#start-link` | `nav.start` / `.start_href` | never absent |

### 14.2 The banned-terms config

`farmer_view.BANNED_TERMS` is the single list. It carries the brief's seventeen terms - `R2`,
`RMSE`, `MAE`, `RPIQ`, `CV`, `fold`, `conformal`, `interval`, `coverage`, `baseline`, `noise`,
`sweep`, `hash`, `sha256`, `pipeline`, `spatial CV`, `training range` - plus the words that smuggle
the same ideas in through a different door (`model`, `error`, `metric`, `feature`, `regression`,
`residual`, `correlation`, `quantile`, `percentile`, `tercile`, `calibration`, `statistical`,
`significance`, `sample size`, `variance`, `standard deviation`) and the four names the target must
never be given here (`total carbon`, `SOC`, `organic carbon`, `carbon stock`).

Matching is case-insensitive and prefix-based, so `folds` is caught by `fold`. `R2` is matched as
`r²` or `r2` with no trailing digit and no leading word boundary, and `SOC` as a word start that may
run on. Both err towards flagging: a token like `super2` or the word "soccer" is caught rather than
let through. Over-blocking is a copy edit; under-blocking is the failure this list exists to stop.

`SOFT_BANNED` is a second, shorter list: ordinary English that a technical sentence would lean on
(`estimate`, `range`, `average`, `measurement`, `reading`). It is tracked, not enforced. These words
survive in the copy - "this estimate is too uncertain", "the range we can defend" - because no
plainer word says the same thing, and because the fixed sentences must not be rephrased. The list
exists so a reviewer can see the difference between a word that is banned and a word that is on a
watch list, and so a new one is added to the right list.

Enforcement is three deep, and the first two are tests:

1. `farmer_view.build()` walks its own payload with `iter_strings` and **raises** on a banned term,
   so a bad string cannot be served at all.
2. `tests/test_farmer_view.py` scans `GET /api/farmer`, `POST /api/farmer/predict`, and the
   `<!-- farmer:begin -->` … `<!-- farmer:end -->` region of the page.
3. The page renders from the payload, so there is no third place for a word to get in.

### 14.3 Headline rules

One sentence, and it is chosen by the rule the reliability gate fired, never by the numbers.

| Gate | Headline |
|---|---|
| `R6_single_band` | `This soil sits in the {lower, middle or upper} third of the sampled soils.` |
| `R5_crosses_one_cut` | `This estimate is too uncertain to place the soil.` |
| `R4_too_wide` | `This estimate is too uncertain to place the soil.` |
| `R2_outside_training_range` | `This soil is outside the soils this tool was built from.` |
| `R3_no_bands` | `The tool cannot place this soil today.` |
| `R1_no_interval` | `We cannot give a range for these readings.` |
| unknown gate | falls back to the `R1` sentence |

**The one rule that has no exceptions.** An interval that crosses a band boundary, or that is wider
than the middle band, produces exactly one sentence: *this estimate is too uncertain to place the
soil.* It is not softened with "about", it is not rounded into a band, and it is not given a
confident neighbour. `TOO_UNCERTAIN` is a single constant, used by both branches, so the two cases
cannot drift apart.

No headline quotes a digit. That is a test, not a convention: the numbers belong in the bar, where
their width is visible, not in a sentence that reads as a verdict.

### 14.4 The range bar

The bar draws three things: the low end, the high end, and the single best answer, positioned on an
axis from `bands.observed_range`, widened when the interval runs past it. The three positions are
arithmetic on numbers the payload already carries, and `bar.source` says so in the payload.

The caption states that the shaded part is the whole range we can defend and the line is one answer.
The `aria-label` says the same thing with the numbers spoken, and the sentence is assembled from a
template written in `farmer_view.py` so the scanner sees it.

### 14.5 "Is my sensor good enough?"

The figure is `results.json → headline.break_even_noise`, surfaced as `/api/metrics →
noise.break_even`, written in `farmer_view._sensor()`. No copy in the module quotes a number, and
the synthetic `--quick` bundle stores `null` there, so the card has three states and no fourth:

| Finding | When | What the card says |
|---|---|---|
| `found` | both arms reached a break-even point | one figure when the arms agree; a low–high pair when they do not |
| `never_reached` | the arms ran but never lost to the plain average | says the test never found the point, and that the test says nothing beyond the largest amount it tried |
| `not_recorded` | the bundle carries no sweep at all | says the test is not stored for this version |

The card is titled with the question because that is the question a reader has. It never answers
the question with a verdict: this project has measured no sensor, so "your sensor is adequate" is a
claim it cannot make, and the tests forbid it.

### 14.6 Screens, the entry page, and what is stored

Three screens on the farmer view, one idea each: **the soil test** (the five numbers), **the
answer** (headline, bar, light, next step), **my sensor**. Only one is visible at a time; the tabs
are `role="tab"` buttons with `aria-selected`.

The gate is a **separate page** at `/` (`web/login.html`), not an overlay on the farmer view.
It asks for a **name** and a **password**, and then offers two buttons - `Sign in to the farmer
view` to `/farmer` and `Sign in to the researcher view` to `/researcher` - each with a one-line
note saying what is behind it.

Any name and any password open it. The form is intercepted in the browser: `preventDefault()` and
then `location.assign()`, so no request is made, no body is built and no header is set. That is not
an oversight, it is the claim, and the page states it above the buttons: *any name and any password
will let you in; nothing is stored and no sign-in is checked*. A test forbids `method="post"`,
`FormData`, `Authorization`, `XMLHttpRequest` and `sendBeacon` in the block, so the sentence cannot
drift away from the behaviour.

There is no `localStorage`, no `sessionStorage`, no `document.cookie` and no `indexedDB` on the
entry page or on the farmer page - all four are tested on both. The entry page holds no number of
any kind: there is nothing on it to keep in step with a bundle.

Its wording is served by `GET /api/login` and scanned for banned terms like every other
farmer-facing string. The one sentence written into the markup is the required warning,
`Not validated on field sensors or Ugandan farms`, which must survive a failed request; a test
asserts it verbatim. A `<noscript>` block carries two plain links, because the form needs scripts
and the routes do not.

### 14.7 Copy rules, in addition to §9

- Short sentences, one idea per screen, about a grade-6 reading level.
- No abbreviations. "Per cent" on screen, never "%". `target.unit_short` is used to *choose* the
  words, never printed.
- The target is "Soil carbon", with a one-line explainer. Never "total carbon (%)", never "SOC".
- No agronomic advice, and no imperative that touches the soil. The next-step card is a statement
  about what would settle the question - a laboratory measurement. §19.3 records the one deliberate
  exception: the ranked steps are written as imperatives, and every one of them is about measuring,
  sampling or keeping a record - never about putting something on a field.
- No sentence that only reassures, and none that only alarms. The uncertainty is the content.

### 14.8 Rejected on this view

| Pattern | Why |
|---|---|
| A colour-only traffic light | Not a signal to every reader; every light carries icon and words |
| Rounding a wide interval into a band | It converts "we cannot say" into "we said" |
| Quoting a break-even figure the bundle does not contain | The card says the test never found it instead |
| A model-driven recommendation | The model records no ordering of its inputs, so it has none to give. The ranked steps in §19 are rule-driven, and name no input, rate or product |
| Hard-coding a sentence in the page | It escapes the banned-term scan and drifts from the numbers |
| Linking to a route that is not served | `/`, `/login`, `/farmer`, `/researcher` and `/session` are each tested to return 200 |
| A password field checked against a stored list | There are no accounts; the field is a door, and the page says so in words |

---

## 15. The session view (`web/session.html`, `GET /session`)

The same numbers as the researcher dashboard, in the order a field session collects them: one
sample, five measurements, one estimate, its placement, and a printable sheet. It adds no new
calculation — it arranges the panels of §3 around a single submission.

### 15.1 What this replaced

A mock supplied as `web/pimaudongo_field_soil_health_agronomic_advisor.html` computed its own SOC
in JavaScript from invented texture constants, printed `Spatial Block CV R²: 0.338` beside an
invented `0.590`, showed feature weights of 42/28/18/12 with moisture among them (moisture is not
a feature), a 0–100 fertility index, lime and manure rates per acre, a crop list, and a conformal
half-width of 0.24 where the calibrated one is 2.11. It loaded Tailwind and Chart.js from CDNs.
That is five entries of §11 in one file, plus C5, C6 and C8.

The file is retained unchanged in `_retired/` as a layout reference. It is not served and not
linked; its appearance is the only thing drawn on, and §16 records exactly which parts were taken
and which were refused. Nothing it computed is quoted here or in the report.

### 15.2 Binding map

`R` = `GET /results`, `MI` = `GET /model-info`, `H` = `GET /health`, `P` = `POST /api/predict`.

| Element | Source | Absent → |
|---|---|---|
| `#h1sub` | `MI.target`, `MI.units`, `MI.n_training_rows` | `"soil carbon"`, `?` per field |
| `#chip` | `R.data.is_real_data` → `chip-real`/`chip-syn`; text `REAL DATA`/`SYNTHETIC STAND-IN` · `R.data.dataset_version` · `MI.model_version` · `H.model_dir` | `?` per field; the chip always prints |
| `#kindbanner` | `R.data.is_real_data` | hidden when real |
| `#s-label`, `#s-site` | operator input, printed only | `not recorded` on the sheet |
| `#fields` | `MI.features[]`, `R.feature_units[name]`, `MI.feature_ranges[name].{p5,p95,median}` | field omitted; hints print `n/a` |
| `#texchip` | sum of features whose unit string contains `percent` | `texture sum: not used` |
| `#est` | `P.prediction`, `P.interval.{low,high,half_width,nominal,empirical_coverage,coverage_sd,mean_width,method,note}`, `P.band.{confidence,band,message,rules,flags,out_of_range}`, `P.accuracy.spatial_rmse` | `No sample submitted yet.` |
| `#est` refusal | 422 `detail.{error,message,offending[].{feature}.{given,physically_valid_range}}` | no estimate is shown |
| `#est` context | `R.results.validation_gap[]` (leading = highest `r2_spatial`), `R.results.interval` | rows omitted |
| `#evidence` noise | `R.results.noise_sweep[]`, `R.results.baseline_rmse.spatial`, `R.headline.break_even_noise["train_clean|spatial"]` | `No noise sweep in this run.` |
| `#evidence` gain | `R.results.gain_sweep[]`, `R.validation.gain_levels` | `No gain sweep in this run. It is opt-in.` |
| `#evidence` ablation | `R.feature_ablation` (top level, written only by `--drop-features`) | no banner |
| `#sheet` | exactly the values already rendered in `#est`, plus labels, print time, provenance | `Complete a reading to fill the sheet.` |
| Provenance | `dataset_version` · `model_version` · rows · target · units · `model_dir` | `?` per field |

The noise chart obeys §6: its own vertical span including zero, extremes printed as tick labels,
no series that is not in `noise_sweep`, no reference line on an axis the run did not sweep.

### 15.3 Interaction

Values are typed; the page states that no instrument is connected and that a browser cannot read
one. Estimation goes to `/api/predict`, which returns the §1 gate placement, so the page never
computes a result and never invents a band. The texture chip warns above `100.5` and still sends
the request. An out-of-range input shows the estimate **and** a `b-bad` banner listing each
feature's training p5–p95, per §8. Print is the page itself: actions hidden, cards kept whole.

Navigation is one link each way: the researcher header carries `href="/session"`, and this page
carries `href="/researcher"`. The entry gate is unchanged, so the two-audience split stays
readable and neither route is a dead end. Both directions are asserted in `test_api.py`.

### 15.4 Copy rules

The word is **placement**, never rating, grade or score. Band names are terciles of the training
target and are printed as such. The target is named from `MI.target` ("Total carbon"), never
"SOC". No advice, no crop list, no index, no cost or adoption language.

### 15.5 Tests

`tests/test_api.py::TestSessionPage` — five tests: the four endpoints appear in the source, no
external request, no baked result literal, no banned vocabulary, and the placement is read from
`band`. The page is also included in the all-pages C1/C2/C3 loop.

## 16. The farmer check: the supplied layout, built

`Pima_ soil carbon check.md` is the intended low-friction farmer interface. It is a *layout
preview*, so its figures were placeholders; the layout and the reading order are what it fixes,
and this section records how that order is served from real payload only.

The visual language comes from the second supplied file, the mock retained at
`_retired/pimaudongo_field_soil_health_agronomic_advisor.mock.html` (§15.1). Only its appearance
was taken: the dark topbar, the card grid, the value chips and the composition bars. Its Tailwind
and Chart.js are gone — the tokens are hand-written in the page's own `<style>` — and none of its
computed figures, weights, index or rates came across. What it showed and this page refuses to
show is recorded in §16.3.

### 16.1 Shape

One scrolling page, no tabs. A dark topbar carries the brand, the required banner and three pills
(for researchers, start again, theme). The body is a wrap of panels on a soft off-white ground, in
a two-column grid that closes to one column below 900 px. Teal marks what can be pressed; no
colour means anything about a soil.

In order: the soil test (five sliders, each with a value chip) beside the texture panel; the
one-line explainer; the answer card (headline, traffic light, track with **words** at the ends,
caption, caveat) beside the next step; the crop card and the advice card (§19); the readings card
(§17) and the soil-test card beside it; the sensor card; then ten guide blocks in the same grid:
how far to trust the check, your soil at a glance, should I get a laboratory test, how to take a
good soil sample, what your readings mean, who can help, general practices (marked "Not based on
your reading"), what is soil carbon, how sure are we, what this check uses. The footer keeps the
data notice.

Each measurement is a label, a value chip and a foot row. The chip prints the number the control
holds and, after it, the field's unit in words (`per cent` for a share, nothing for a bare index).
The foot row holds an exact number box and the hint. Either control writes the same value to both
and to the chip, so the chip cannot disagree with the input it describes.

The texture panel (`#texture`) opens when the payload marks two or more fields as shares —
`form.fields[].share`, set from a `percent` unit. It draws one bar per share, sized by that share's
part of the total entered so far, then a total row, then, if the three do not add to a hundred, one
sentence saying so. It is a readout of what was typed, never a calculator: it fills no field, and
the request still carries exactly the numbers the farmer entered.

Two controls the earlier build did not have. A theme pill in the topbar flips `data-theme` on
`<html>`, starting from `prefers-color-scheme`, so the page follows the device and can be
overridden. A print sheet drops the topbar, the form, the buttons and the choice rows and keeps
each card whole, so the answer can leave the screen as one page.

Once an answer arrives, the crop card appears beside the advice card, between the next step and
the guide. It asks one question with three buttons (replanted each season, stays for years, both
on one field), and each answer changes what the reading supports, the next step, and which of the
four general practices apply. The crop answer never re-runs the estimate and never produces a
rating: `crop.health_note` says the tool places carbon in a sample and does not rate the soil.

Beside the crop card sits the advice card (§19): a button that asks
`POST /api/farmer/advice` for the ranked steps, and the steps themselves once an answer arrives.
It is hidden until a result exists, and the API is not called until the button is pressed.

The track ends read "Less carbon" and "More carbon". The numbers moved into the spoken label,
which is assembled from `bar.aria_template`, so a screen reader still hears the low, the high and
the single best answer.

### 16.2 Binding map (farmer)

| Element | Source | If absent |
| --- | --- | --- |
| `#form-fields` | `form.fields[]`: label, hint, `lowest`, `highest`, `placeholder` (training median) | a field with no median starts empty and the slider cannot open |
| value chip `.chipval` | the field's own control, plus `form.fields[].unit_words` | unit omitted when the payload sends none |
| `#texture`, `#texture-bars`, `#texture-note` | `form.texture.{title,lead,total,off}` and the fields marked `share` | panel hidden unless two or more shares |
| `#form-start` | `form.start_note` | paragraph omitted |
| `#light` | `result.light.icon` + `.words` | never absent; build() raises |
| `#end-low`, `#end-high` | `bar.low_words`, `bar.high_words` | track hidden when `bar` is null |
| `#guide-blocks` | `guide.blocks[]`: `kind` (`para`/`list`/`steps`/`pairs`), `title`, `intro`, `items[]`, `note` | section omitted |
| `#crop-choices`, `#crop-answer` | `crop.options[]`: `button`, `name`, `reading`, `step`, `practices[]` | card stays hidden until a result exists |
| `#crop-health` | `crop.health_note` | paragraph omitted |
| `#advice-title`, `#advice-lead`, `#advice-limits` | `advice.title`, `.lead`, `.limits` | card stays hidden until a result exists |
| `#advice-body` | `advice.verdict`, `advice.items[]`, `advice.cap_note` (when `advice.unshown`) | `advice.empty` |
| `#s-value` | `sensor.value` else `sensor.low` | line left empty |
| `#theme` | `nav.theme` | pill stays blank; the label is never written in the page |

Every guide string is built inside `farmer_view.build()` and therefore passes `_banned_guard`:
a technical word in the guide fails the build, not just a test.

### 16.3 Deviations from the supplied layout

Five, each because the page cannot honour the original without inventing something:

1. **No sensor readings.** The tool receives five typed or dragged numbers; there is no node, so
   nothing is labelled "readings from your sensor".
2. **Moisture and temperature are not shown as readings.** The guide says they are not used,
   instead of displaying values no endpoint returns.
3. **The sliders open at the sample's median**, and `form.start_note` says so in words. A
   starting point that looked like a measurement would be the one lie a slider can tell.
4. **The soil-type presets became a readout.** The mock offered four buttons — clay, loam, sandy,
   silty — that filled the texture fields with fixed percentages. A preset is a measurement nobody
   took, which is the fault that retired the mock (§15.1). The panel instead shows the shares that
   were typed, their total, and a sentence when the three do not come to a hundred. It fills
   nothing: a farmer with a texture result from a laboratory types it, and those same numbers reach
   the estimate unchanged.
5. **None of the mock's computed figures came across.** Its carbon estimate, feature weights,
   fertility index, lime and manure rates, half-width and its Chart.js benchmark are all absent, and
   so are its district presets and the simulated sensor burst. Every number on this page arrives in
   `result`, `advice` or `strip`.

One line of the supplied copy is kept but is the only place this project departs from the
ban on cost framing: "You are about to spend money on lime, compost or seed" (a trigger for
paying a laboratory, not a claim about this tool). The general practices list is carried under
"Not based on your reading" and "Sources to be added before wider use".

### 16.4 Tests

`tests/test_farmer_view.py::TestGuide` — eight tests: the guide opens on trust, every block has a
title and a shape, the laboratory decision has its four cases, sampling is a five-step numbered
sequence, the practices block carries its two disclaimers, no block quotes a figure, the guide is
inside the build scan, and the page is one page rather than four tabs.

`TestFarmerPage` holds the shell invariants: the farmer region is marked for the scanner, no
banned term survives in it, the page writes none of its own prose (`textContent = "…"` is absent),
the required banner is present, the page fetches and bakes no number outside `<style>`, and no
`role="tablist"` turns it into tabs. `test_the_farmer_page_keeps_readings_on_the_device_only`
counts `localStorage.setItem` once and proves `saveReading` and `clearReadings` reach no network.

`TestCropQuestion` — nine tests: three cycles in a fixed order, each with a reading and a next
step, the two cycles do not share their wording, each uses only the four practices already
written, the health note says the tool does not rate the soil, no crop string carries a digit, no
cycle names an input or promises an outcome, the card is hidden until an answer exists, and the
page renders the cycles from the payload rather than writing them.

---

## 17. The short end: readings over time, and the soil test beside them

Two cards sit between the crop question and the guide. Neither asks the tool for
a new answer, and neither can move the carbon estimate.

### 17.1 Readings over time

Three readings are kept per field: acidity, salts and moisture, each with the
date it was taken. The page keeps them in `localStorage` under one key
(`pima.readings.v1`), never sends them, and never folds them into a request.
Saving and clearing are the only two functions that touch the store, and a test
asserts that neither contains `fetch(`.

A second reading is compared with the one before it against a drift figure: half
the spread of that reading in the training sample (`0.5 * sd`, from
`feature_ranges`). That is the same point the sensor test already uses, past
which added drift stops the reading carrying the answer. For the headline
bundle the live figures are 0.508 pH units for acidity and 0.134 dS/m for salts.

Moisture has no figure, because it is not an input of this build. The card says
so and compares it as a word (dry, damp, wet) instead. A bundle without an `sd`
also yields no figure; the card falls back to the same sentence rather than
borrowing a number from a neighbouring input.

### 17.2 The soil test beside a reading

The farmer picks the word the laboratory printed for nitrogen, phosphorus and
potassium (low, medium, high). No threshold is chosen in this project: the
classification belongs to the laboratory that ran the sample.

A rule fires when a soil-test word and a reading condition both hold:

| key | word | reading condition | what it says |
|---|---|---|---|
| `p_acid` | phosphorus low | acidity below the sample 5th percentile | acid soil binds phosphorus, so a low number can mean held rather than missing |
| `k_salty` | potassium low | salts above the 95th percentile | potassium moves with soil water, so the number partly describes the sampling day |
| `n_dry` | nitrogen low | moisture recorded as dry | nitrogen needs water to reach roots, so the number describes the day it was taken |

Each rule carries four things: what the pair means, what to ask the laboratory,
one general practice, and a line for each crop cycle (replanted each season,
stays for years, both on one field). The crop line is the only place the crop
answer changes anything; it re-renders when a crop button is pressed and does not
re-run the estimate. When nothing matches, the fallback says the two numbers do
not disagree and points at a second reading rather than another input.

### 17.3 What it deliberately does not say

No rule names a quantity, a product or a rate. A test scans every rule string for
a digit and for the verbs `apply`, `spread`, `increase`, `reduce`, `best` and
`recommended`. The reason is in the numbers already on the page: spatial R2 is
0.086, and the interval is 4.215 g/100 g wide against a sample sd of 1.40. A tool
that cannot place one field inside its own interval has no basis for telling
anyone how much of anything to put on it. What it can do is say what two
measurements mean side by side, and what would settle the question.

### 17.4 The storage rule changed

The old rule was that the farmer page stored nothing. It now stores the readings
a farmer chooses to keep, in that browser only, so the rule was rewritten to say
what it actually protects: no credential is stored, and no reading ever becomes a
request body. `LOGIN.body` moved from "Nothing is stored" to "What you type here
is not stored", which is the true statement about the sign-in form.

### 17.5 Tests

`TestReadingStrip` - seven tests: the three readings in order, both sensor
readings carry a drift figure, moisture says it has no figure and offers three
words, the drift is half the `sd`, a bundle without one gets no figure, the card
is inside the build scan, and the page has a place for each reading.

`TestPairing` - nine tests: every rule pairs a nutrient word with a reading, no
rule quotes a figure, no rule names what to apply, every rule speaks to all three
crop cycles, every rule carries an ask and a practice, the marks come from the
sample percentiles in order, the fallback still points somewhere, the card is
inside the build scan, and the page picks the rule from the payload.

`TestLogin` changed with 17.4: the storage ban now applies to the sign-in alone,
and a new test holds the farmer page to one key with no path from it to a
request.

## 18. The entry gate (`web/login.html`, `GET /` and `GET /login`)

Rebuilt from the supplied screen (`web/Pima_ soil carbon check.html`): a
landscape behind one translucent panel, two account types on a tab strip, and a
single door. It replaces the previous gate, which offered two buttons and
checked nothing.

### 18.1 What it is made of

A fixed full-viewport panel over an inline SVG — sky gradient, four hill
shapes — with no image file, no font and no script from outside the app. The
backdrop is decoration and is hidden from assistive technology. The panel is a
rounded card with a translucent green fill and a blur, so the landscape reads
through it without ever competing with the text.

Every sentence on the panel comes from `/api/login`: the demo badge, title,
lead, tab labels, field labels, placeholders, hint, note and button text. Three
strings are written into the page: the control name on the show/hide button, the
standing notice under the panel, and the no-script fallback links.

### 18.2 Two account types, one door

The tabs are `role="tab"` buttons marked `type="button"`, so pressing one can
never submit the form. Choosing a type swaps four things and nothing else: the
username label (phone number or username, or username or email), its
placeholder, the hint that prints that account's demo name and password, and
the button text. Both types carry the same six payload fields — label, action,
username, placeholder, hint, href — and a test fails if either is blank, so a
missing key shows up as an empty control rather than an invented sentence.

### 18.3 A door, not a check

The gate requires both fields to be filled — pressing the button should be a
deliberate act — but neither is compared with anything. The chosen account type
decides which view opens, and any name and any password open it. The password is
cleared as the page leaves, nothing is sent and nothing is stored.

The first build of this gate compared the two fields with the demo account
printed under each type and refused everything else. That made the page a check,
and a check a person cannot pass reads as a broken page rather than a strict
one: the first thing typed into it was refused. The demo account is now an
example to type, `LOGIN.body` says plainly that any name and any password will
do, and a test refuses to let a comparison with a printed password reappear.
The only refusals left are for an empty field, and they are payload strings.

### 18.4 What the panel no longer claims

The supplied screen said "Farmer accounts cannot open researcher pages". No
session exists in this app — the two views are separate addresses and either
can be opened directly — so that sentence was replaced with one that is true: an
account decides where you land, not what you may see. Enforcing the stronger
claim would need a server-side session, which this demo does not have; a test
fails if the word "cannot" returns to the note.

### 18.5 Tests

`TestLogin` keeps what survived the rebuild: the demo label, both destinations
served, the two field labels in the markup, the ban on any request carrying what
is typed, the ban on storage, the banner, the no-figure rule, and the payload's
wording being rendered rather than written. Two of its tests follow the gate's
behaviour: the body must still say that any name and any password will do, and
that what is typed is not stored.

`TestEntryGate` — seven tests: both types carry six non-empty fields, the types
share neither a name nor a destination, the tabs cannot submit, the password can
be read back, every refusal is written in the payload, nothing typed is compared
with anything, and the page does not claim the views are walled off.

---

## 19. The ranked next steps, and the sensor list

Two things that share one rule: neither may state a fact the artefacts do not carry. The steps rank
what a farmer could do next from evidence already on the page; the sensor list says how good an
instrument has to be, and derives every ceiling it prints from the bundle.

### 19.1 The engine is rules, not the model

`recommendation.py` returns a ranked list from three dictionaries: one `/api/predict`-shaped answer,
the `/api/metrics` payload, and the farmer's side — crop cycle, soil-test words, the last two kept
readings. It fits nothing, fetches nothing and reads no clock, so a whole ranking is testable by
handing it three dicts.

The order is written down rather than scored, because a score invites tuning and this project has
nothing to tune it against:

| Rank | Head | What it is |
|---|---|---|
| 1 | A | the tool could not place the soil: a laboratory test is the only way out |
| 2 | C | two crops on one field, so one reading cannot be the field's reading |
| 3 | D | a soil-test word and a reading pointing at the same question |
| 4 | B | the record read against itself: a move, no move, or no second reading yet |
| 5 | E | one general practice that belongs to the chosen crop |
| 6 | F | the record itself, always last, always true |

Uncertainty comes first because everything under it is an answer about *this* soil: if the tool
cannot place the soil, the useful next step is the one that ends the uncertainty, not one built on
it. The list is capped at three, and `advice.cap_note` says how many were held back — a step past the
cap still counts in `total`, so nothing is dropped in silence.

### 19.2 The endpoint and the payload

`POST /api/farmer/advice` takes `{values, context}` and answers with the card. The placement is
**re-derived server-side** from `values`, through the same `_api_prediction` path
`/api/farmer/predict` uses, so the page cannot hand back a band it chose and the steps cannot
disagree with the answer printed above them.

The payload:

| Field | Meaning |
|---|---|
| `items[]` | `key`, `rank`, `basis`, `title`, `why`, `now`, `words`, and `moves` on a move |
| `verdict` | the situation, said once: `title`, `body`, `basis`, `words` — `null` when the list is empty |
| `total`, `shown`, `unshown`, `cap` | how much was found, how much is printed, how much was held back |
| `context_used` | `crop`, `bands`, `has_reading`, `has_previous` — what the ranking was allowed to see |

`context_used` carries no band, so a reviewer can check the claim in §19.4 without reading the
source. `words` is always one of the five phrases in `RECOMMEND_BASIS`, printed beside the step, so
a step arrives with its evidence rather than on trust.

### 19.3 The one place imperatives are allowed

§14.7 bans imperative verbs on this view, and this card writes five of them. The ban exists to keep a
rate, an input or a product off a farmer's screen; these stay on the evidence side — get this soil
tested, sample two parts separately, read the same spot again, keep the reading, write down the field
and the day. None names a material, a rate or an outcome. The one step that is about the land rather
than the record is the practice, and it is printed with `advice.practice_note`: a general practice for
that kind of crop, not a reading of this soil.

The card also states its own boundary. `advice.limits` says that none of it says what to buy or how
much to put on a field; what it says is what would make the answer firmer.

### 19.4 The band is not an input, and three things say so

The gate places the soil in a tercile of the sampled soils. That is a position in a distribution, not
a grade: the upper third is the upper third of the soils in this dataset, not a good soil. A step
recommended because of the tercile would be recommended for a reason this project does not have, so
the engine reads only which rules the gate fired:

1. **By construction.** It reads `gate.rules` and `gate.out_of_range`, and nothing else.
2. **By behaviour.** Two placements that differ only in their band, and in nothing else, produce
   byte-identical output — `test_two_bands_give_the_same_answer`.
3. **By source.** `band_key` appears in the module only inside the docstring that says it is not
   read, and the only keys taken from the gate are `rules` and `out_of_range`.

### 19.5 Where the sentences live

Every sentence is in `farmer_view.py` — `RECOMMEND`, `RECOMMEND_ITEMS`, `RECOMMEND_VERDICTS`,
`RECOMMEND_BASIS` — and `build_advice()` passes each one through `_banned_guard`, so a technical word
in a step fails the build, not just a test. Two of the sentences are templates and are filled with
figures the engine read from `metrics`: the drift a move is set against, which is the same half-spread
the readings card prints, and the plain names of inputs that fell outside the sampled soils.

### 19.6 The sensor list (`SENSORS.md`, `sensor_plan.py`)

Two field instruments and one laboratory method cover the five quantities the check takes. Soil
carbon is not among them: it is estimated from the five, which is why each has to be good enough to
be worth carrying.

| Obtained with | Covers |
|---|---|
| pH meter with temperature compensation | soil reaction |
| conductivity cell, compensated to 25 °C | electrical conductivity |
| particle-size analysis in a laboratory | clay, sand and silt as one sample |

The ceilings are **derived, never typed**. The bundle records a noise sweep; its break-even is the
level at which the check stopped beating a field mean. Multiply that fraction by each input's own
spread and the result is a ceiling in that input's own units:

```
ceiling = break-even fraction x spread(feature)
```

Three consequences are printed beside the figures, because each one changes how a requirement is
read:

- **A shared budget, not five separate limits.** Error was added to every input at once, so being
  well inside one ceiling buys no headroom on another.
- **A floor for usefulness, not a target.** At the ceiling the check is no better than an average of
  the soils it was built on; comfortably below it is the requirement.
- **Rounded down, never up.** A requirement rounded up is one an instrument may just miss.

The default bundle is `export_afsis_real`, deliberately not `MODEL_DIR`: a tolerance derived from the
synthetic stand-in would be a number about a generated dataset. Where a bundle recorded no break-even
— which is exactly the synthetic case — the document prints `not derived` and says the sweep never
reached one, rather than borrowing a figure.

```
python sensor_plan.py            # the document, to stdout
python sensor_plan.py --write    # regenerate SENSORS.md
python sensor_plan.py --check    # exit 1 when the document is out of date
python sensor_plan.py --json     # the derived figures
```

`--check` runs in the suite, so a figure edited by hand into the document fails the build. The
document is generated between `<!-- sensors:begin -->` and `<!-- sensors:end -->`, carries no date
and no clock, and renders identically twice from the same bundle.

It refuses three things on purpose: to rank the inputs (the bundle records no ordering, and a budget
allocated by guesswork would look exactly like a budget allocated by evidence); to call a ceiling an
accuracy (it is measured against a field mean, not a laboratory value); and to say anything about
cost, availability or robustness, which decide what is bought rather than what is adequate.

### 19.7 Tests

`tests/test_recommendation.py` — 63 tests in three kinds: what the engine does (ordering, the cap,
the verdict named after the first step, every step carrying its basis); what it must not read (the
band, by behaviour and by source); and what it must not say (every printable sentence passes the
banned-term scan, and a poisoned template raises instead of shipping).

`tests/test_sensor_plan.py` — 61 tests: the rounding rule floors and never rounds to nearest, no
figure is invented for a value that is missing or not finite, the smallest arm is the break-even and
the model name is not an arm, one row per input in the bundle's order, a ceiling is never above the
arithmetic it came from, the document is deterministic and clockless and names its provenance, a
bundle without a break-even produces `not derived` rather than a number, and the committed
`SENSORS.md` is byte-equal to a fresh render of the committed bundle.

