# UI/UX Decision Reference

Status: describes both interfaces as built, against `soil_api.py`, serving `export_afsis_real/`
(real) or `export/` (synthetic).

There are two views, and they are two audiences, not two themes. Both are reached
from one entry page.

| Route | File | Audience | Payload |
|---|---|---|---|
| `/`, `/login` | `web/login.html` | the entry page | `GET /api/login` |
| `/farmer` | `web/farmer.html` | someone holding a soil sample | `GET /api/farmer`, `POST /api/farmer/predict` |
| `/researcher` | `web/index.html` | examiner, supervisor, reviewer | `GET /results`, `/model-info`, `/health`, `/api/metrics` |

`/` is the entry page and is a chooser, not authentication. Every technical chart
and table lives in the researcher view; none of them appear on a farmer screen.
§3–§13 describe the researcher view. §14 describes the farmer view and the entry
page, and governs anything added to either.

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

---

## 12. Change checklist

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
- No advice and no imperative verbs. The next-step card is a statement about what would settle the
  question - a laboratory measurement - not an instruction to do anything to the soil.
- No sentence that only reassures, and none that only alarms. The uncertainty is the content.

### 14.8 Rejected on this view

| Pattern | Why |
|---|---|
| A colour-only traffic light | Not a signal to every reader; every light carries icon and words |
| Rounding a wide interval into a band | It converts "we cannot say" into "we said" |
| Quoting a break-even figure the bundle does not contain | The card says the test never found it instead |
| A model-driven recommendation | The experiment supports no such claim, and §9 forbids advice |
| Hard-coding a sentence in the page | It escapes the banned-term scan and drifts from the numbers |
| Linking to a route that is not served | `/`, `/login`, `/farmer` and `/researcher` are each tested to return 200 |
| A password field checked against a stored list | There are no accounts; the field is a door, and the page says so in words |
