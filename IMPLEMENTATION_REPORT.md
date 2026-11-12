# Implementation report — the audience split, the entry gate, and the structure behind them

**Status:** describes the working tree as it stands, not a plan. Every claim below can be
re-derived from a file, a route or a test named in it.
**Purpose:** this document exists to be reviewed for change. §9 lists the open decisions as
decisions with consequences, and §10 maps each likely change request to the files and tests it
would move. Nothing here is a proposal.

| Item | Value at the time of writing |
|---|---|
| Test suite | `349 passed`, 9 test files, 4–5 minutes (the session fixture runs the experiment once) |
| Bundle served | `export_afsis_real/` (`MODEL_DIR`), real AfSIS Phase I |
| `model_version` | `sha256:57ae8583074e476a` |
| `dataset_version` | `afsis-2f-ddd215cc66b5` |
| `results.json` sha256 | `c84dcdee75bb68f3551995c7181dfbb89c45020cf472370772acd1b2a98ba6cd` |
| Python / sklearn | 3.13.14 / 1.8.0 (the API refuses a bundle from another sklearn minor) |

---

## 0. Where this document sits

Five documents describe this project and they do not overlap cleanly. A reviewer needs to know
which one is authoritative for what before proposing a change.

| Document | Authoritative for |
|---|---|
| `README.md` | How to run it: install, data, commands, endpoints, artefacts, tests |
| `UI_UX_REFERENCE.md` | What the interface must do: constraints C1–C12, §13 open decisions, §14 the farmer specification |
| `IMPLEMENTATION_REPORT.md` (this) | **What is built and how**: modules, payloads, routes, tests, change map |
| `PROTOTYPE_REPORT.md` | The plain-language account for a presentation or a supervisor |
| `REPORT_SCOPE_SHEET.md` | What the prototype report may and may not claim |

**One discrepancy, recorded here because it is the kind of thing this report exists to surface.**
`PROTOTYPE_REPORT.md` and `REPORT_SCOPE_SHEET.md` both pin the bundle as
`sha256:062d36c53a562f80`, dataset `afsis-3f-296718c140e3`, 407 rows, synthetic stand-in. That is
`export/`, which is still on disk. The bundle this workspace actually serves is `export/…`'s
successor: `export_afsis_real/`, model `sha256:57ae8583074e476a`, dataset `afsis-2f-ddd215cc66b5`,
926 rows, `data_is_real: true`. The two reports therefore quote a synthetic run's figures while the
served API states figures from real soils. See §9.7.

---

## 1. What was asked, and where each part lives

The requirement had eight clauses. Each is traced to an artifact and to the test that would fail
if it were undone. This table is the shortest route to judging whether the build matches the brief.

| # | Requirement | Where it is implemented | What enforces it |
|---|---|---|---|
| 1 | Two views; Farmer is the default after sign-in; "For researchers" is a clearly labelled link; all technical charts and tables move to the researcher view | `web/login.html`, `web/farmer.html`, `web/index.html`; routes in `soil_api.py` | `tests/test_farmer_view.py::TestFarmerPage` (`test_both_views_are_served`, `test_the_root_is_the_entry_gate_not_a_view`, `test_the_researcher_link_is_labelled`, `test_technical_words_moved_to_the_research_view`), `tests/test_api.py::TestIndexPage` |
| 2 | No technical term on a farmer screen; a banned-terms list in config; a test scans every farmer string and template | `farmer_view.BANNED_TERMS`, `farmer_view.find_banned`, `farmer_view.iter_strings` | `TestBannedTermsConfig`, `TestFarmerPayloadStrings`, `TestFarmerPage`, `TestLogin` |
| 3 | Farmer copy: short sentences, grade-6, no abbreviations, one idea per screen; "soil carbon" with a one-line explainer; never "total carbon (%)" or "SOC" | `farmer_view.TARGET_LABEL`, `TARGET_EXPLAINER`, `_unit_words`, `FIELD_COPY` | `test_the_target_is_called_soil_carbon`, `test_the_explainer_is_one_short_idea`, `test_the_target_is_not_called_total_carbon` |
| 4 | Every result screen: headline, range bar, traffic light that is never colour-only, one next step | `farmer_view.result_block`, `LIGHTS`, `NEXT_STEP`, `_bar`; `web/farmer.html#screen-result` | `TestTrafficLight`, `TestResultScreen`, `test_the_page_renders_the_icon_and_the_words` |
| 5 | A boundary-crossing or too-wide interval must say the estimate is too uncertain to place the soil; never rounded into a confident sentence | `farmer_view.TOO_UNCERTAIN` used by both `R4` and `R5` branches | `TestHeadline` (five tests, including `test_the_two_wide_cases_use_the_same_sentence` and `test_no_headline_quotes_a_number`) |
| 6 | An "Is my sensor good enough?" card stating the break-even error in plain words, computed from the metrics file | `farmer_view._sensor`, fed by `metrics.noise.break_even` ← `results.json → headline.break_even_noise` | `TestSensorCard` (including `test_the_number_changes_when_the_file_changes`, which monkeypatches the figure) |
| 7 | All farmer-facing numbers come from the API; no hard-coded copy quoting a figure | `farmer_view.build()` payload; page renders only | `test_the_page_writes_none_of_its_own_prose`, `test_the_page_fetches_and_bakes_no_numbers`, `test_the_entry_page_bakes_no_numbers`, `test_the_pages_wording_comes_from_the_api` |
| 8 | A login that leads to both views, with the past UI kept and a separate page | `web/login.html` at `/` and `/login`; `GET /api/login`; `web/index.html` unchanged in content | `TestLogin` (11 tests), `tests/test_api.py::TestIndexPage` |

**Carried forward from the earlier brief** (still in force, still tested): split-conformal interval
kept separate from spatial RMSE, terciles stored in the bundle's unit and never tuned, additive
artefact passes that leave `results.json`, `model_meta.json` and `model.joblib` byte-identical,
`/predict` untouched, no cost or smallholder framing, no agronomic advice.

---

## 2. File map

Ownership, so a reviewer knows which file a change belongs to. Lines as counted by
`(Get-Content <file>).Count`; two bundles sit on disk (`export/` synthetic, `export_afsis_real/` real)
and only the second is served.

| File | Lines | Owns |
|---|---|---|
| `soil_api.py` | 495 | Bundle loading and the provenance gate; every route; `_api_prediction` (the single prediction path) |
| `metrics_view.py` | 243 | `build_metrics()` — the one payload every interface reads; staleness rules |
| `reliability.py` | 150 | `gate()` — rules R1–R6, no I/O, no model calls |
| `farmer_view.py` | 453 | All farmer vocabulary, the banned-terms config, the matcher, the payload builders, the build-time guard |
| `cv_supplement.py` | 310 | The additive pass writing `cv_supplement.json`, `bands.json`, `sites.json` |
| `web/login.html` | 122 | The entry gate: name, password, two destinations |
| `web/farmer.html` | 279 | The farmer screens; markup only, no prose |
| `web/index.html` | 814 | The researcher view (the previous dashboard, content unchanged) |
| `tests/test_farmer_view.py` | 516 | The audience split, the gate, the banned list |
| `tests/test_metrics_api.py` | 439 | Every number in `/api/metrics` traced to a file |
| `tests/test_reliability.py` | 332 | Every branch and boundary of R1–R6 |
| `tests/test_api.py` | 301 | The original API and page contract |
| `tests/test_pipeline.py` | 481 | The experiment itself |
| `tests/test_validity.py` | 248 | Leakage: nothing is fitted before splitting |
| `tests/test_sensor_sim.py` | 278 | The Part A sensor simulation |
| `tests/test_bundle_hash.py` | 65 | Bundle immutability |
| `tests/test_ph_target.py` | 82 | pH as a second target |

---

## 3. Route map

| Route | Serves | Audience | Notes |
|---|---|---|---|
| `GET /health` | JSON | — | bundle path, `model_version`, `data_is_real` |
| `GET /model-info` | JSON | — | target, units, features, ranges, versions |
| `GET /results` | JSON | — | the raw `results.json` |
| `GET /results.json` | JSON | — | alias |
| `POST /predict` | JSON | — | **unchanged from before the split**; clamps at zero; 11 tests in `TestPredictEndpoint` |
| `GET /api/metrics` | JSON | researcher | the composed payload (§5.2) |
| `POST /api/predict` | JSON | researcher | interval **unclipped**, band placement, RMSE reported separately |
| `GET /api/login` | JSON | both | the gate's wording and its two destinations |
| `GET /api/farmer` | JSON | farmer | the whole farmer vocabulary and chrome |
| `POST /api/farmer/predict` | JSON | farmer | headline, bar, light, next step for one sample |
| `GET /`, `GET /login` | `web/login.html` | — | the entry gate |
| `GET /farmer` | `web/farmer.html` | farmer | 279 lines, no prose of its own |
| `GET /researcher` | `web/index.html` | researcher | the previous front page |

Every page route goes through `_page(path)`, which returns 404 with the missing filename rather than
a template error. There is no catch-all route and no static mount, so an unknown path is a 404.

---

## 4. Data flow

```
export_afsis_real/
  model.joblib, model_meta.json, results.json
      └─► load_bundle(): six provenance checks, else BundleError
          (no server starts in a bad state) ─► META, MODEL, R

  cv_supplement.json ─┐
  bands.json ─────────┴─► _optional_json() ─► build_metrics() ─► METRICS ─► GET /api/metrics
                          (absent or stale ⇒ None)

  sites.json ─► written by the supplement pass, read by nothing (§8.1)


POST /api/predict ─► _validate ─► MODEL.predict ─► pred, low, high
                                        │
                         reliability.gate(…, bands)  ─► placement
                                        │
        ┌───────────────────────────────┴────────────────────┐
POST /api/farmer/predict                            GET /api/farmer
build(METRICS, placement)                           build(METRICS), no result
        │                                                    │
        └────────────► banned-term guard ◄───────────────────┘
                       raises rather than serve a payload
                       that contains a word it forbids
```

Two properties matter for review:

1. **One prediction path.** `/predict` and `/api/predict` and `/api/farmer/predict` all reach
   `MODEL.predict` through the same `_validate`. `/api/predict` and `/api/farmer/predict` share
   `_api_prediction`, so a farmer answer and a researcher answer for the same inputs cannot disagree
   about the number or the interval. Only the words differ.
2. **Numbers have one origin.** No module computes a metric. `metrics_view` copies fields; `farmer_view`
   copies or positions them. The one derived group (the bar's three percentages) is arithmetic on
   published fields, and `bar.caption` says so in the payload.

---

## 5. Modules in detail

### 5.1 `reliability.py` — the gate

Pure function, no I/O, so every branch is testable without a bundle. Rules fire in order and the
first match wins:

| Rule | Condition | Confidence | Message |
|---|---|---|---|
| R1 | prediction or interval not finite | Low | `No calibrated interval is available for this model.` |
| R2 | any input outside the training p5–p95 | Low | names the features; appends `LAB_LINE` |
| R3 | `bands.json` absent or not 2 cuts / 3 labels | Low | `Band thresholds are not available…` |
| R4 | width ≥ one inner band, **or** interval spans both cuts | Low | `The estimate is too wide to place in a band.` |
| R5 | interval crosses exactly one cut | Medium | names both thirds; `band_boundary_crossed` |
| R6 | interval inside one third | High | band named, `band_key` set |

Crossing is strict (`lo < cut < hi`), so an endpoint exactly on a cut does not cross it. Returns
`rules` and `flags` on every path for traceability, and `advice_withheld=True` always — the gate never
produces a recommendation.

### 5.2 `metrics_view.build_metrics()` — the payload contract

Top-level keys: `schema_version`, `target`, `features`, `feature_group`, `models`, `baseline_rmse`,
`interval`, `bands`, `bands_note`, `noise`, `folds`, `measured_sensor_error`,
`measured_sensor_error_note`, `train_scores_available`, `limitations`, `sources`.

Points that were decided deliberately and are worth re-examining:

- `target.display_label` is **composed** from `target_name` + `_short_unit(target_units)`, so
  "Total carbon (%)" is derived, not typed. `target.naming_note` says which documents must follow.
- `sup_ok` / `bands_ok` require the file to be **present** as well as fresh; a missing file is
  reported absent, not "current". (This was a real bug, caught by `test_metrics_api.py`, fixed.)
- `interval.spatial_rmse_of_interval_model` is a separate field from `mean_width`, on purpose.
- `features[].perturbed_by_noise_sweep = True` for every feature, and `feature_group.grouping_rule`
  explains why there is one group: a sensor/laboratory split would have no member on the sensor side.
- `bands` is `None` when absent, and `bands_note` says which of the two reasons applies.

### 5.3 `farmer_view.py` — the vocabulary

Four parts:

1. **Config.** `BANNED_TERMS` — 37 entries in three groups: the brief's own list, the same ideas
   under other words (`model`, `error`, `metric`, `feature`, `residual`, `correlation`, `quantile`,
   `percentile`, `tercile`, `calibration`, `statistical`, `significance`, `sample size`, `variance`,
   `standard deviation`), and the four names the target must never be given (`total carbon`, `SOC`,
   `organic carbon`, `carbon stock`). `SOFT_BANNED` is a five-word watch list
   (`estimate`, `range`, `average`, `measurement`, `reading`), not enforced.
2. **Matcher.** `find_banned(text)` is the only implementation; the tests import it, so there is no
   second opinion. Case-insensitive, prefix-based. `R2` matches `r²`/`r2`; `SOC` matches at a word
   start. It errs towards flagging: `super2` and "soccer" are caught.
3. **Copy.** `TARGET_LABEL`, `TARGET_EXPLAINER`, `TOO_UNCERTAIN`, `LIGHTS`, `HEADLINES`,
   `NEXT_STEP`, `LEARN_MORE`, `FAILURE`, `LOGIN`, `NAV`, `FIELD_COPY`, `FALLBACK_FIELD`.
4. **Builders.** `_form`, `_sensor`, `_bar`, `result_block`, `build`, `build_login`. Both `build`
   functions end with a guard that walks their own payload and **raises** on a banned term.

Decisions inside this file that a reviewer may want to overturn:

| Decision | Where | Consequence of changing it |
|---|---|---|
| Two headline branches share `TOO_UNCERTAIN` | `result_block` | Splitting them lets the two cases drift; `test_the_two_wide_cases_use_the_same_sentence` would need deleting |
| No headline contains a digit | `HEADLINES` | Quoting the estimate in the headline makes `test_no_headline_quotes_a_number` fail, by design |
| The unit is spoken ("per cent") from `unit_short`, not converted | `_unit_words` | A conversion would break the "same number as the researcher view" property |
| Unknown confidence falls back to the red light | `result_block` | The quietest signal is chosen when the payload is malformed |
| An unknown feature gets a neutral label and `handbook: false` | `_form` | A new bundle adds an input rather than borrowing another's meaning |
| The sensor card never says a sensor is adequate | `_sensor` | The claim would be unsupported; four phrases are forbidden by test |

### 5.4 `cv_supplement.py` — the additive pass

Runs the shipped model's procedure again against an existing bundle and writes three files beside
it. Before writing anything it asserts:

1. every recomputed out-of-fold R² and RMSE matches `results.validation_gap` within 1e-9. Recorded in
   `verification`: `n_checks: 20`, `max_abs_diff_vs_results_json: 0.0`;
2. the sha256 of `results.json`, `model_meta.json` and `model.joblib` is identical before and after
   (`bundle_files_sha256` stores all three);
3. the recomputed row groups equal the recorded `blocking_diagnostics.cluster_label` **element for
   element**, so a coordinate can never be paired with the wrong fold.

**What the three files contain**

| File | Shape |
|---|---|
| `cv_supplement.json` | `derived_from` (dataset_version, model_version, results_sha256, target, unit, seeds, blocks) + `models` → 5 models (`mean_baseline`, `ridge`, `pls`, `random_forest`, `gradient_boosting`) × 2 schemes (`random`, `spatial`) × 4 metrics (`r2`, `rmse`, `mae`, `rpiq`), each cell `mean / sd / train_mean / train_sd / n_seeds / fold_n_test / fold_n_train` + `verification` |
| `bands.json` | `method`, `label_source`, `not_tuned`, `target`, `unit`, `n`, `observed_range`, `cuts` (2), `bands` (3, with `key` and `label`), `derived_from` |
| `sites.json` | `n = 926`, four parallel arrays `site`, `lon`, `lat`, `fold`; `fold_labels 0–9`, `fold_sizes`, plus `purpose` (location is not an input) and `alignment` (the element-for-element check) |

`sites.json` is columnar on purpose: a future panel can read `lon`, `lat` and `fold` without
transposing, and the arrays cannot get out of step because there is only one index space. Nothing in
the serving tree reads it today — `grep sites.json` over `soil_api.py`, `metrics_view.py`,
`farmer_view.py` and both pages returns nothing.

### 5.5 The pages

- `web/login.html` — name, password, two submit buttons. The submit handler calls
  `preventDefault()` and then `location.assign()`, so nothing typed leaves the browser. A test
  forbids `method="post"`, `FormData`, `Authorization`, `XMLHttpRequest` and `sendBeacon` in the
  block, and both storage APIs plus cookies and `indexedDB`. A `<noscript>` carries two plain links.
- `web/farmer.html` — three screens (the soil test, the answer, my sensor), one visible at a time,
  `role="tab"` buttons with `aria-selected`. The `<!-- farmer:begin -->` … `<!-- farmer:end -->`
  region holds no prose: every sentence is assigned from the payload. The light is written as
  `<span class="ico">` plus `<span class="word">`, so the icon and the words are two DOM nodes from
  one payload field and neither can be dropped without the other noticing; the bar's `aria-label`
  is assembled from `bar.aria_template`, a sentence written in Python so it is scanned like the rest.
- `web/index.html` — unchanged in content except a footer link. It still reads `/results`,
  `/model-info` and `/health`, **not** `/api/metrics` (see §9.1).

---

## 6. Provenance and integrity gates

Import-time, in `soil_api.load_bundle()`. Six checks, in order, each raising `BundleError` with a
sentence a reader can act on:

1. `model.joblib`, `model_meta.json`, `results.json` all present — the message names the missing
   files and the command that produces them;
2. both JSON files parse;
3. `model_meta.json` carries the eight required keys (`model_version`, `feature_names`,
   `target_name`, `target_units`, `log_target`, `training_data_version`, `results_sha256`,
   `sklearn_version`);
4. `meta.results_sha256` matches `results.json`. The comparison is **line-ending tolerant**: the
   file is hashed raw, as LF, and as CRLF, and any of the three matches. A CRLF checkout of a fresh
   clone must not refuse to start; a content change still fails all three;
5. `"sha256:" + sha256(model.joblib)[:16]` equals `meta.model_version` — so a swapped or edited model
   file is caught;
6. `meta.feature_names` equals `results.features`, in order — feature order is positional, and the
   loader refuses to guess.

Then the sklearn major/minor of the pickling environment must equal the running one; a mismatch is a
refusal rather than a warning, because cross-version unpickling can silently move predictions.

`BundleError` is rendered by an exception handler as a 500 carrying `bundle_unavailable` and the same
sentence. The service therefore **cannot start** in a state where its provenance is unvouched-for,
which is stronger than a runtime check.

Additive artefacts are treated differently on purpose. `_optional_json()` returns `None` for a
missing or unparseable `cv_supplement.json` or `bands.json`, because a bundle that predates the
supplement pass is still a valid bundle; the `/api` routes report the gap
(`sources.supplement: null`, `bands: null`, `bands_note`) instead of refusing to serve. On top of
that, `metrics_view` marks an artefact **stale** when its `derived_from.model_version` disagrees with
the loaded model, and treats stale as absent.

---

## 7. Test inventory

| File | Tests | Protects |
|---|---|---|
| `test_api.py` | 33 | The original contract: `TestResultsEndpoint` (5), `TestPredictEndpoint` (11), `TestHealthAndInfo` (8), `TestBundleRefusal` (6), `TestIndexPage` (3) |
| `test_farmer_view.py` | 88 | The split, in nine classes: `TestBannedTermsConfig`, `TestFarmerPayloadStrings`, `TestFarmerPage`, `TestTrafficLight`, `TestHeadline`, `TestResultScreen`, `TestSensorCard`, `TestLogin`, `TestLearnMore` |
| `test_reliability.py` | 63 | R1–R6 branch by branch, including exact-boundary cases on a binary-exact fixture |
| `test_pipeline.py` | 56 | The experiment: cleaning ledger, folds, schemes, artefacts |
| `test_metrics_api.py` | 46 | Every number in `/api/metrics` walked back to a file; derived allowances computed from those files; label composition; `TestApiPredict` (10); `TestPredictIsUntouched` (2) |
| `test_sensor_sim.py` | 30 | Part A simulation |
| `test_validity.py` | 20 | No fit before split; nested tuning; fold integrity |
| `test_ph_target.py` | 8 | The second target |
| `test_bundle_hash.py` | 5 | Bundle immutability across the additive pass |

The session fixture runs the real experiment in quick scope against a temp stand-in — 160 sites, 8
clusters, 2 seeds, 6 blocks, `--quick`, written to a `tmp_path_factory` directory and imported as a
subprocess — so the API tests exercise a produced bundle rather than a mock. Nothing in the suite
touches `data/afsis_real`, and `conftest.py` says so at the top: no number produced by a test may
appear in a reported result. `test_farmer_view.py` imports its list from
`farmer_view.BANNED_TERMS`, so adding a word to the config is enforced by the next run without
touching the test file.

---

## 8. What is deliberately not built

| # | Not built | Where it is recorded | Why it matters |
|---|---|---|---|
| 1 | The sample map (decision 11) | `UI_UX_REFERENCE.md` §13.8 | `sites.json` exists and is fold-verified, but no panel reads it. The researcher view still has the schematic |
| 2 | The researcher view reading `/api/metrics` | §9.1 below | Bands, train-vs-test scores, the composed label and the break-even label are served and tested but not displayed |
| 3 | A real login | `UI_UX_REFERENCE.md` §14.6 | Any credentials open it; no accounts, no session, no check |
| 4 | Monotonic constraints and sensor calibration in the model | earlier brief, marked out of scope | Neither can be evaluated here: no sensor has been characterised, so there is nothing to calibrate against |
| 5 | The `sites.json` fold-coloured plot legend/basemap | `UI_UX_REFERENCE.md` §13.8 | No basemap by decision; the pin was rejected because the model does not use location |

---

## 9. Open decisions, stated as decisions

### 9.1 The researcher view does not show the new payload

`/api/metrics` carries train-fold scores, out-of-fold scores, terciles, the composed display label
and the break-even label. `web/index.html` still reads the older endpoints, so the dashboard shows
the pre-split set: pooled validation gap, the sweep, the tables, the interval panel.

*Consequence if unchanged:* the report's claim that "every displayed number has one origin" holds,
but two interfaces exist and only one is fully backed by the new payload.
*Change cost:* a new rendering pass over `index.html` (~610 lines of script), plus tests binding each
new value. This is the single largest outstanding item.

### 9.2 The farmer range bar can show a negative lower end

Median inputs on the real bundle give `-1.15 to 3.06 per cent`, and the bar draws it, because
clamping would hide the width. A negative percentage is not physically meaningful to a reader and
no note explains it.

*Options:* one sentence of explanation; or clamp with a marker saying "cut off at zero"; or leave it.
*Recommendation:* the sentence, because the clamp contradicts the reason `/api/predict` returns an
unclipped interval.

### 9.3 `/predict` still clamps at zero and its interval floor is truncated

`/predict` returns `max(0.0, pred)` and `max(0, pred − half)`. On the real bundle that renders
`90% interval: 0.00 to 3.06` for a prediction of `0.96` and a calibrated mean width of `4.21`. The
new `/api/predict` reports the unclipped interval and `below_zero: true`.

*Consequence if unchanged:* two routes tell different stories about the same model. `/predict` is
protected by `TestPredictEndpoint` (11 tests) and `TestPredictIsUntouched` (2 tests), which pin the
clamped interval deliberately rather than by drift.

### 9.4 The gate accepts anything

Any name and any password open it. A test forbids sending, storing or checking them, so the page's
sentence and the behaviour cannot drift. If a reviewer wants the researcher view genuinely gated,
that is a new subsystem (user store, hashing, session, route guard) and it contradicts the "nothing
is stored" claim that is currently true.

### 9.5 Band reachability

On the real bundle the cuts are `0.650820752` and `1.439275861` — terciles of the 926 training values,
so three near-equal thirds. The calibrated interval is 4.21 wide, so most real inputs land on R4 and
read "too uncertain". That is the honest result, and the cuts were not moved to make a band
reachable.

*Consequence for a demo:* most live predictions show the too-uncertain headline. If that is judged
bad for a presentation, the fix is a different dataset or a better model, not a different cut.
An explicit, labelled "example inputs that do place" button would be the only acceptable softener.

### 9.6 `measured_sensor_error` is `null`

`metrics.measured_sensor_error = None` with the note "Not measured yet", and the farmer sensor card
is built to handle the absence (`never_reached`, `not_recorded`). No sensor has been characterised by
this project.

### 9.7 The two prose documents describe the previous bundle

`PROTOTYPE_REPORT.md` and `REPORT_SCOPE_SHEET.md` are pinned to `export/` (model
`sha256:062d36c53a562f80`, dataset `afsis-3f-296718c140e3`, 407 rows, synthetic). The workspace now
serves `export_afsis_real/` (model `sha256:57ae8583074e476a`, dataset `afsis-2f-ddd215cc66b5`, 926
rows, real).

*Consequence if unchanged:* a reader holding the report and opening the demo sees different numbers,
row counts and `data_is_real` values, and the report's central figures (gap, break-even, bands) are
not the ones the interface states. This is the most consequential known defect in the document set,
because it is a factual mismatch rather than a missing feature.

*Options:* (a) add a short "which bundle this describes" block to both documents and regenerate their
figures from `export_afsis_real/results.json`; (b) point them at `export/` explicitly and label the
demo as running a different bundle; (c) make `export/` the served bundle again. (a) is the honest one
if the real-data run is the headline result.
*Change cost:* the scope sheet's control table plus every quoted figure in `PROTOTYPE_REPORT.md`; the
scaffolding (status paragraph, data-is-real banner wording) is already correct for either bundle.

---

## 10. Change map

What moves if a requirement changes. Intended to make an evaluation concrete rather than a mood.

| If you want to change… | Files that change | Tests that must change | Risk |
|---|---|---|---|
| The wording of any farmer sentence | `farmer_view.py` only | none — the scan re-runs automatically | Low, unless a digit or a banned word enters |
| A new banned word | `farmer_view.BANNED_TERMS` | none — `TestBannedTermsConfig` reads the list | Low; may require copy edits |
| The tint or shape of a traffic light | `web/farmer.html` CSS, `farmer_view.LIGHTS` | none, unless `icon` or `words` empties | Low |
| The reading of the result screen | `farmer_view.result_block`, page markup | `TestResultScreen`, `TestHeadline` | Medium — the four-part contract is what makes the screen evaluable |
| Where the sign-in leads | `farmer_view.LOGIN`, `web/login.html`, routes | `TestLogin` | Low |
| Real authentication | new module + `soil_api.py` + `web/login.html` | new tests; C12 in `UI_UX_REFERENCE.md` must be rewritten | High — changes what the project claims |
| The researcher view consuming `/api/metrics` | `web/index.html` (script), possibly new tests | none existing | Medium — the payload is already tested |
| Adding the sample map | `web/index.html`, a new panel; `sites.json` already exists | new tests for fold↔coordinate alignment | Medium — the alignment guard already exists |
| Changing the bands | `cv_supplement.py`, re-run, `reliability.py` unchanged | `test_reliability` uses its own fixtures | High — a tuned cut is the one thing the brief forbids |
| Making the farmer page show numbers in the headline | `farmer_view.HEADLINES` | `test_no_headline_quotes_a_number` must be deleted | High — directly contradicts clause 5 of the brief |
| Re-pinning the prose documents to the served bundle | `PROTOTYPE_REPORT.md`, `REPORT_SCOPE_SHEET.md` | none (prose only) | Medium — every quoted figure must be re-read from `results.json`, not retyped from the old one |
| Changing the model or data | `afsis_experiment.py`, re-run, then `cv_supplement.py` | `test_pipeline`, `test_validity`, `test_bundle_hash` | High — hashes and every displayed figure change |

---

## 11. How to verify this document

```powershell
cd "c:\Users\HP\pimaUdongo version 2\PimaUdongo"
python -m pytest -q                                   # 349 passed

$env:MODEL_DIR = "export_afsis_real"                  # only for the server
python -m uvicorn soil_api:app --host 127.0.0.1 --port 8000
#   /            the entry gate
#   /farmer      the farmer view
#   /researcher  the dashboard
#   /api/login   the gate's wording
#   /api/metrics every researcher number
#   /api/farmer  every farmer word

python cv_supplement.py --export export_afsis_real    # additive; asserts byte-identity
```

Spot checks that each take one line: `GET /api/login` must contain the sentence "Any name and any
password will let you in"; `GET /api/farmer` must contain no banned term; `POST /api/farmer/predict`
with the training medians must return `This estimate is too uncertain to place the soil.` on the real
bundle; `POST /predict` with the same inputs must still return the old clamped interval.

---

## 12. Honest appraisal

**What is solid.** The banned-terms mechanism is real rather than decorative: one list, one matcher, a
guard that trips before a payload is served, and a scan of the page region — and the page holds no
sentences of its own to escape them. The gate makes one prediction path so the two audiences cannot
disagree about a number. The additive pass proves itself by reproducing `results.json` to `0.000e+00`
and by refusing to write when the bundle would change. Every displayed figure traces to a file, and
`test_metrics_api.py` walks them.

**What is weak.** The researcher view is half-migrated (§9.1): the payload exists, the dashboard
does not use it. Two routes disagree about clamping (§9.3). The gate is theatre by design, and its
honesty depends on a test that forbids the very plumbing an actual login would need. The sample map
is described in the brief, provisioned in the data, and absent from the screen (§8.1). `SOFT_BANNED`
is documentation of intent with no teeth. And the two prose documents still describe the bundle
before this one (§9.7) — the only defect here that a reader could mistake for a result.

**What has not been checked.** No real user has read a farmer screen. The "grade-6" requirement is
enforced only by sentence length and by the absence of jargon — not by a readability measure. The
new login has been exercised in a browser; the researcher dashboard has not been re-checked since the
split beyond a load test.

---

*Generated from the working tree on 10 November 2026. If a claim here disagrees with a file, the
file is right and this document should be corrected.*
