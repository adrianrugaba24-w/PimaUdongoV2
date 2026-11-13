# PimaUdongo — predicting soil organic carbon from sensor-type readings

Research prototype for a BSc proposal. The claim under test is **not** "we can
predict SOC well"; it is:

> reported accuracy depends on the validation design, so a soil model must be
> tested for geographic generalisation (spatially blocked CV) and for input
> noise before its score means anything.

The prototype is built to be **valid, not impressive**. Where a number is
unflattering it is printed anyway, and every number in the UI, the API and this
README is read out of the bundle's `results.json` — plus `cv_supplement.json`
and `bands.json` when the additive pass has been run — which one command
regenerates. (The same pass writes `sites.json` for a sample map; no view reads
it yet, and the README does not claim one does.)

There are two interfaces over that one bundle, reached from a single entry page:
a **farmer view** at `/farmer` and a **researcher view** at `/researcher`. They
share the model and every figure and share no vocabulary; §14 of
`UI_UX_REFERENCE.md` governs the first.

---

## STATUS — read this before quoting anything

There are **two bundles** in this repository and they must never be mixed:

| directory | data | what it may be used for |
|---|---|---|
| `export/` | labelled synthetic stand-in (`synthetic_afsis.py`) | testing the pipeline — **do not cite any number from it as a soil result** |
| `export_afsis_real/` | real AfSIS Phase I wet chemistry, 926 rows, 19 countries | the reported run — **still not a Ugandan field validation** |

Neither bundle contains measured sensor error: no low-cost sensor has been used
on anything, and no soil has been sampled by this project. The noise experiment
*simulates* instrument error on laboratory values; see the group label the API
returns (`Laboratory measurements (sensor error simulated)`) and the note
beneath it.

The `export/` bundle describes a **simulation that was designed to contain a
random-vs-spatial gap**, and is evidence about the *pipeline*, not about African
soils. `export/results.json` says so in its own record:

```
"data": { "kind": "synthetic_stand_in", "is_real_data": false, "stand_in_marker": true,
          "licence": "No third-party data in this run: ... that licence is NOT inherited
          by these numbers." }
```

The stand-in directory carries a `SYNTHETIC_STAND_IN.txt` marker, and the
experiment checks for it before it is allowed to label anything `afsis_real`.
Pointing `--root` at a folder is not treated as proof that the folder holds real
AfSIS data; `--synthetic` is the human override for other fake data.

---

## Install

```powershell
cd "c:\Users\HP\pimaUdongo version 2\PimaUdongo"
python -m pip install -r requirements.txt      # pandas numpy scikit-learn matplotlib
                                               # joblib fastapi uvicorn pydantic pytest httpx
```

Verified on Python 3.13.14 with scikit-learn 1.8.0, numpy 2.3.3, pandas 3.0.0
(the exact versions are recorded in `results.json -> package_versions`, and the
API refuses to load a model saved by a different sklearn major/minor).

## Run the experiment (one command, all artefacts)

```powershell
python afsis_experiment.py
```

Takes a few minutes on an 8-core machine. It builds the stand-in if needed,
cleans it, runs every sub-experiment, and writes:

| file | contents |
|---|---|
| `export/results.json` | every number, with provenance (data card, cleaning ledger, hashes, seeds, scope) |
| `export/model.joblib` | the deployed pipeline (imputation, scaling, target transform, learner) |
| `export/model_meta.json` | feature names/order, units, sklearn version, `results_sha256` |
| `export/results_summary.csv` | one row per (experiment, model, CV, noise, arm), mean over seeds |
| `export/results_runs.csv` | the same plus one row per seed |
| `export/results_plot.png` | noise curve, gap bars, block/partition sensitivity, coverage |

Useful flags: `--root <AfSIS dir>` (real data), `--synthetic`, `--countries`,
`--target` / `--features` / `--lat-col` / `--lon-col` (column overrides),
`--list-columns` (inspect a download before trusting the auto-detection),
`--blocks`, `--seeds`, `--seed0`, `--depth-cm`, `--lab-dupes`, `--target-units`,
`--export`, `--out`. `--quick` shrinks the scope for tests and is recorded as
`experiment_scope.quick = true` in the output, so a quick artefact can never be
mistaken for a reported one.

## Part A — simulated sensor survey (`sensor_experiment.py`)

The proposal has two parts that are **never combined**: Part B (the AfSIS
experiment above) and Part A, a *simulated* field survey read through a
low-cost-sensor measurement model.

```bash
python sensor_experiment.py            # full run  -> export/part_a_results.{json,csv}
python sensor_experiment.py --quick    # smoke run (flagged quick, not reportable)
```

* `sensor_sim.py` builds a spatially correlated field of true pH, moisture and
  SOC and reads pH and moisture through sensors with **gain, offset, random
  noise, calibration drift (basis: sampling order) and cross-sensitivity of the
  pH reading to moisture**.
* **No parameter is sourced.** All are marked `assumed` in `parameters[]`
  because no datasheet or bench test has been supplied. The "baseline" error
  setting is therefore exploratory until real values replace them.
* Inputs: the two sensor channels. Targets: true pH and true SOC (standing in for
  laboratory values). Models: mean baseline, ridge, random forest, gradient
  boosting, on the same spatial folds as Part B (hyperparameters fixed, no nested
  tuning, to keep the sweep affordable).
* **The assumptions that could decide the answer are swept, not fixed:** spatial
  correlation length (H1), SOC coupling to pH/moisture (H3) and error scale
  (H2/H3). Read H1 and H3 as functions of those, not as single numbers.
* "Useful skill" for H3 is fixed in advance as spatial R² >= 0.5. A break-even
  error scale is the largest *tested* scale that still meets it; `null` means it
  was never met and nothing is extrapolated.
* Both noise arms are run: fit on clean readings / score on noisy ones, and
  fit and score on noisy ones.
* Output is labelled `kind: "simulation"`, `is_real_data: false`. It says how
  models respond to the stated sensor errors, **not** how any real probe, soil or
  farm behaves.

## pH as a second target

`python afsis_experiment.py --root <AfSIS dir> --target-kind ph`

pH is dimensionless, so there is no unit inference, the bounds are 0-14, it is
**not** log-transformed again, and the pH column is never used as a feature when
it is the target. Moisture is picked up as a covariate only if the table really
has a moisture column; the data card lists exactly which features were chosen
(override with `--features`).

## Start the API and the demo

```powershell
$env:MODEL_DIR = "export_afsis_real"       # the reported run; "export" is the stand-in
python -m uvicorn soil_api:app --port 8000      # then open http://127.0.0.1:8000/
```

### Two views, two audiences, one entry page

`/` serves the **entry page**. It looks like a sign-in and behaves like a door:
it asks for a name and a password, accepts any values, sends nothing anywhere and
stores nothing, and it says so in one sentence above the two buttons. There is no
account list and no check. The two buttons lead to the two views.

| Route | File | Audience |
|---|---|---|
| `GET /`, `GET /login` | `web/login.html` | the entry page: choose a view |
| `GET /farmer` | `web/farmer.html` | the person holding the sample |
| `GET /researcher` | `web/index.html` | examiner, supervisor, reviewer |

The farmer view is the plain-language one: one idea per screen, no technical
word anywhere, and every figure read from the API. Every chart, table, ledger and
score lives in the researcher view, which is the previous front page unchanged.
None of them appear on a farmer screen. Both views link back to `/`, and the
farmer view carries a clearly labelled `For researchers` link in its footer.

Both views read the same bundle, and the same five inputs produce the same
prediction and the same interval through either one. Only the words differ.

### Endpoints

| Endpoint | Returns |
|---|---|
| `GET /health` | bundle path and load state |
| `GET /model-info` | target, units, features, ranges, versions |
| `GET /results` | the raw `results.json` |
| `POST /predict` | prediction, interval, flags (the original route; unchanged) |
| `GET /api/metrics` | every displayed number, composed from the bundle's files |
| `POST /api/predict` | the calibrated interval, unclipped, plus its band placement |
| `GET /api/login` | the entry page's wording and its two destinations |
| `GET /api/farmer` | the farmer view's whole vocabulary and chrome |
| `POST /api/farmer/predict` | one farmer result: headline, bar, light, next step |

The service **refuses to start** if `model.joblib`, `model_meta.json` or
`results.json` is missing, unreadable, incomplete, edited after the run
(`results_sha256` mismatch) or saved by another sklearn version — it raises
`BundleError` at import time rather than serving predictions whose provenance it
cannot vouch for.

Neither page makes an external request, so both work with no network. Every
figure on either page is read from the API for the bundle being served;
`web/index.html` and `web/farmer.html` contain no results of their own. The
entry page quotes no figure at all.

Interface decisions — the element-to-field binding map, the chart rules, the
rejected patterns, the pre-change checklist, and §14 for the farmer view — are
recorded in `UI_UX_REFERENCE.md`. Read that first before changing anything in
`web/`.

How the pieces fit — module ownership, the route map, the payload contracts, the
provenance gates, the test inventory, and a change map of what moves if a
requirement changes — is in `IMPLEMENTATION_REPORT.md`. That document also records
the open decisions and the two prose reports that still describe the previous
bundle.

## Run the tests

```powershell
python -m pytest -q
```

The session fixture runs the real experiment (quick scope) on a small stand-in
in a temp directory, so the API tests are checking a genuinely produced bundle,
not a mock. `tests/test_reliability.py` covers every branch and boundary of the
band gate without a bundle at all, and `tests/test_metrics_api.py` checks the
`/api` payload against the artefacts and walks every number in it back to a
file. The `/predict` tests are untouched by the `/api` work and pass unchanged.

`tests/test_farmer_view.py` is the audience split's guard. It imports the banned
list from `farmer_view.BANNED_TERMS` — so a word added there is enforced by the
next run — and then scans every string in `GET /api/farmer`, every string in a
`POST /api/farmer/predict` result, every string in `GET /api/login`, and the
`<!-- farmer:begin -->` … `<!-- farmer:end -->` and `<!-- login:begin -->` …
`<!-- login:end -->` blocks of the two pages. It also checks that a traffic
light carries an icon and words rather than a colour, that no headline quotes a
digit, that a wide or boundary-crossing interval gets the one fixed sentence,
that the sensor figure matches the metrics file rather than a constant, and that
`/` serves the entry page while `/farmer` and `/researcher` serve the two views.

---

## Data

**Intended data.** AfSIS Phase I (`s3://afsis`, AWS Open Data registry). The
pipeline expects `<root>/Georeferences/*` and `<root>/Wet_Chemistry/<LAB>/*`:

```powershell
aws s3 sync s3://afsis/2009-2013/Georeferences   afsis/2009-2013/Georeferences  --no-sign-request
aws s3 sync s3://afsis/2009-2013/Wet_Chemistry   afsis/2009-2013/Wet_Chemistry  --no-sign-request
python afsis_experiment.py --root afsis/2009-2013 --list-columns     # check the guess
python afsis_experiment.py --root afsis/2009-2013 --target <col> --features <c1> <c2> ...
```

**Licence.** The AWS registry describes AfSIS Phase I as ODbL, the dataset
README as ODC-By; read the `LICENSE` in the download and credit *Africa Soil
Information Service (AfSIS) and partners*. That licence applies to the real
download only — `results.json -> data.licence` states which of the two applies
to the run you are looking at, and for a stand-in run it explicitly disclaims
inheritance.

**What the synthetic run used** (`export/results.json -> data`, `dataset_version
afsis-3f-296718c140e3`, sha256 of each input file recorded in `data.files`):

- Target `SOC`, units **percent (g/100 g)** — inferred, and the inference is
  printed (`"median 2.16 < 15, read as a percentage"`). Features: `pH_H2O`
  (dimensionless), `EC` (dS/m), `Clay`, `Sand`, `Silt` percent. Any
  carbon-derived column (SOC sum, TOC, C:N) is *blocked* from the features and
  listed in `blocked_as_features` — a target-derived feature is the classic
  accidental leak.
- Depth rule: one **0–5 cm** record per site; deeper increments dropped.
- Cleaning ledger with a count and a reason for every removal (2152 merged rows
  → 407 usable):

| step | before | removed | after | reason |
|---|---|---|---|---|
| loaded | 2152 | 0 | 2152 | Georeferences × Wet_Chemistry merge |
| exact_duplicate_rows | 2152 | 12 | 2140 | rows identical in every column |
| missing_identifier | 2140 | 0 | 2140 | no profile/site/SSN id → cannot group folds |
| missing_coordinates | 2140 | 40 | 2100 | latitude or longitude absent |
| impossible_coordinates | 2100 | 21 | 2079 | out of range, non-numeric, or a 0/0 placeholder |
| same_record_same_lab | 2079 | 0 | 2079 | repeats within one lab after cleaning |
| depth_selection | 2079 | 1632 | 447 | kept one 0–5 cm record per site and lab |
| multi_lab_replicates | 447 | 39 | 408 | same site/depth in >1 lab; kept the alphabetically first |
| missing_target | 408 | 0 | 408 | no SOC label → cannot train on it |
| impossible_target | 408 | 1 | 407 | target outside (0, 100] for percent |
| impossible_value (pH, clay) | 407 | 0 | 407 | 2 readings set to NaN, imputed **inside** training folds |
| impossible_texture_sum | 407 | 2 | 407 | clay+sand > 100.5 → both set to NaN |
| final | 407 | 0 | **407** | usable rows (NaN may remain; imputation is per fold) |

- Rows and sites after cleaning: **407 / 407**. Countries: Nigeria 124,
  **Uganda 119**, Tanzania 103, Kenya 61. The proposal's country is reported
  separately, not blended: **Uganda subset 119 rows = 29.2 % of the African set**
  (subset SOC mean 2.184 %, SD 1.400; whole-set median 2.164 %).

---

## Results — random CV and spatial CV side by side (synthetic stand-in, `export/`)

From `export/results.json` of this run (`model_version sha256:062d36c53a562f80`,
5 seeds `20261104`–`20261108`, 5 outer folds, 3 inner folds, 10 spatial blocks,
nested tuning on). **Synthetic stand-in — do not cite these as soil results.**
Spatial CV is listed first because it is the number the proposal cares about.
`RMSE`/`MAE` are in percent (g/100 g).

| model | R² spatial | R² random | gap (random − spatial) | RMSE spat | RMSE rnd | MAE spat | RPIQ spat | beats field mean (spatial) |
|---|---|---|---|---|---|---|---|---|
| random forest | **+0.611** | +0.761 | **+0.151 ± 0.006** | 0.729 | 0.571 | 0.573 | 2.29 | yes |
| gradient boosting | +0.590 | +0.750 | +0.159 ± 0.009 | 0.748 | 0.585 | 0.583 | 2.23 | yes |
| ridge | +0.428 | +0.648 | +0.220 ± 0.009 | 0.883 | 0.693 | 0.624 | 1.89 | yes |
| PLS | +0.393 | +0.625 | +0.232 ± 0.008 | 0.910 | 0.715 | 0.646 | 1.84 | yes |
| mean baseline | −0.361 | −0.005 | +0.356 ± 0.003 | 1.363 | 1.171 | 1.124 | 1.23 | **no** |

Field-mean baseline RMSE: 1.363 (spatial), 1.171 (random). Modes of the
nested-tuned hyperparameters: random forest `max_features=0.5,
min_samples_leaf=1`; gradient boosting `learning_rate=0.05, max_depth=2`;
ridge `alpha=10.0`; PLS `n_components=3`.

**Reading it honestly.** The gap is the point of the exercise: the same model,
same data, same folds for every model, scored 0.15–0.23 R² lower when whole
regions are held out instead of random rows. In this stand-in that gap is
*largely a designed property of the simulation* (the generator's relationship is
non-stationary by construction), which is exactly why the real AfSIS run has to
be done before any of this is claimed about soils.

### Controls

- **Shuffled-target R²** (must be ≈ 0): mean baseline −0.016, ridge −0.086,
  PLS −0.093, random forest −0.179, gradient boosting −0.140. No skill found in
  noise, so the pipeline is not reading signal out of the split design.
- **Block-size sensitivity** (spatial R², 5 → 10 → 20 → 50 blocks): random
  forest 0.638 → 0.610 → 0.680 → 0.771; ridge 0.472 → 0.457 → 0.495 → 0.588.
  More, smaller blocks make the task easier and drift toward random CV — with
  10 blocks the estimate sits near its most conservative value, and the reported
  spatial number should be read together with this curve.
- **Partition sensitivity** — *two* blocking families, redrawn once per seed with
  the learner seed fixed at `20261104` and the modal E1 hyperparameters held
  constant, so only the partition moves. Partitions are compared up to cluster
  renumbering (`partition_signature`), because cluster labels are arbitrary:
  - `kmeans_seed` (the reported blocking, 10 blocks, 5 KMeans seeds) →
    **1 distinct partition**: random forest 0.608 ± 0.000, ridge 0.457 ± 0.000.
    The KMeans seed renumbers the blocks but never moves a boundary, so the
    **0.000 SD in the model table is a measured null** — the estimate did not
    move — and not evidence that fold placement cannot matter.
  - `grid_offset` (rotated rectangular blocks: random rotation + random grid
    origin, grain resolved from the data to 7×7 cells, 10–13 non-empty cells per
    partition, 5 seeds) → **5 distinct partitions**: random forest
    **0.676 ± 0.034** (range 0.644–0.729), ridge **0.496 ± 0.022** (range
    0.478–0.534).
  - Reported as is, including the uncomfortable part: the grid family scores
    *higher* than the k-means blocking the headline uses (+0.068 R² for random
    forest, +0.039 for ridge), so the spatial number depends on the blocking
    **scheme**, not only on its seed — the reported KMeans/10-block choice is the
    more conservative of the two. And the boundary-placement SD (±0.034) is about
    a fifth of the validation gap (+0.151): the gap is larger than fold-placement
    noise, but not by a wide margin. Fixed modal hyperparameters are why these
    rows differ slightly from the fully nested-tuned table above.
  - **E4b runs the spatial arm only.** These are therefore *not* validation gaps:
    the `R² random` column above comes from the fully tuned E1 run and must not be
    differenced against a grid number. The gap under grid blocking is not
    measured anywhere in this prototype and must not be quoted.
- **Prediction interval**: split-conformal, calibrated on held-out spatial
  blocks and scored on test blocks never seen. Nominal **90 %** →
  **measured empirical coverage 0.824** (SD 0.076) under spatial CV, mean width
  **2.29** percentage points (±1.145). The interval is **under-covering in new
  areas** and is reported that way; the API returns it together with the
  achieved coverage, not with the nominal level.
- **Noise** (random forest, spatial CV; noise = Gaussian, scaled by each
  feature's SD *inside the training fold*): R² 0.610 → 0.603 → 0.590 → 0.518 →
  0.365 for clean-train/noisy-test at 0 / 0.1 / 0.25 / 0.5 / 1.0 SD, and 0.610 →
  0.615 → 0.586 → 0.524 → 0.310 for noisy-train/noisy-test. RMSE at 1.0 SD is
  0.931 / 0.970, still below the field mean (1.363), so **no break-even noise
  level was reached within the swept range** — reported as `null` rather than
  extrapolated.

---

## Results — the real AfSIS run (`export_afsis_real/`)

```powershell
python afsis_experiment.py --root data/afsis_real --export export_afsis_real `
    --target "Total carbon" --features pH_H2O EC "Clay percent" "Sand percent" "Silt percent" `
    --blocks 10 --seeds 5
python cv_supplement.py --root data/afsis_real --export export_afsis_real
```

`model_version sha256:57ae8583074e476a`, `dataset_version afsis-2f-ddd215cc66b5`,
5 seeds `20261104`–`20261108`, 5 outer folds, 3 inner folds, 10 spatial blocks,
nested tuning on. Inputs: `Georeferences/georeferences.csv` and
`Wet_Chemistry/COALESCED/Wet_Chemistry_COALESCED.csv` (sha256 of both in
`data.files`).

- Target **Total carbon**, unit **percent (g/100 g)** — inferred, and the
  inference is printed (`median 0.93 < 15, read as a percentage`).
- Every screen is labelled **Total carbon (%)**, composed at runtime from
  `model_meta.json -> target_name` and `target_units` (`/api/metrics ->
  target.display_label`). Nothing spells the label into the page. **The
  proposal's wording has to follow the bundle**: where it names the target
  something else, that text has to be brought into line before it is published.
- **926 rows / 926 sites / 19 countries.** The rows carry one identifier (`SSN`)
  and one coordinate pair each, so a site can never straddle two folds.
- Uganda subset: **32 rows = 3.5 %** of the set. Quoted because the proposal
  names Uganda, and a 32-row subset cannot support a country-level claim.
- `data.depth_rule` records `applied: false`: the coalesced table has no depth
  column, so the 0–5 cm rule **could not be enforced** and the rows are whatever
  depth the source provides. Recorded, not papered over.

| model | R² spatial | R² random | gap (random − spatial) | RMSE spat | RMSE rnd | beats field mean (spatial) |
|---|---|---|---|---|---|---|
| random forest | **+0.086** | +0.338 | **+0.252 ± 0.011** | 1.339 | 1.139 | yes |
| gradient boosting | +0.078 | +0.295 | +0.217 ± 0.017 | 1.344 | 1.175 | yes |
| mean baseline | −0.030 | −0.002 | +0.028 ± 0.001 | 1.421 | 1.402 | **no** |
| PLS | −0.333 | −0.112 | +0.221 ± 0.069 | 1.616 | 1.476 | no |
| ridge | −8.190 | −0.187 | +8.003 ± 0.073 | 4.244 | 1.525 | no |

Field-mean baseline RMSE: 1.421 (spatial) / 1.402 (random). RMSE is in percent
(g/100 g).

**Reading it honestly.** The headline spatial R² is **0.086**. Under a random
split the same model reports 0.338, so roughly three quarters of the apparent
skill is location-specific and does not survive holding out whole regions. The
model does beat the field mean spatially (RMSE 1.339 against 1.421), which is
the weakest honest claim available and the only one the numbers support: it is
better than guessing the average, and it is a long way from a usable predictor.
The gap itself (+0.252) is larger here than in the stand-in, and the validation
SD (±0.011) is small next to it, so the gap is not a fold-placement artefact.

**Overfitting check** (`cv_supplement.json`, same folds, same seeds, same tuned
parameters as the table above):

| model | train R² | test R² (spatial) | train RMSE | test RMSE |
|---|---|---|---|---|
| random forest | +0.701 | **+0.086** | 0.756 | 1.339 |
| gradient boosting | +0.459 | **+0.078** | 1.026 | 1.344 |
| PLS | −0.001 | −0.333 | 1.395 | 1.616 |
| ridge | −0.016 | −8.190 | 1.406 | 4.244 |
| mean baseline | +0.000 | −0.030 | 1.394 | 1.421 |

The random forest explains 70 % of the variance in the folds it was trained on
and 9 % in regions it never saw. That is not a tuning problem to be squeezed
away; it is the same statement as the gap, made from the other side. Ridge is
the opposite failure and is kept in the table for that reason: it does not even
fit its own training folds (train R² −0.016) and then extrapolates badly on
test (RMSE 4.244). A table that only shows the winner is not a comparison.

**Prediction interval** — split-conformal, calibrated on held-out spatial
blocks and scored on test blocks never seen: nominal **0.90**, measured
empirical coverage **0.888** (SD 0.012). The band is honest about its level and
enormous in its width: **4.215** percentage points, against a target whose
median is **0.931**. One typical interval spans the whole lower half of the
observed distribution and then some.

The spatial RMSE of the same model (1.339) is reported **beside** the interval
as an accuracy figure. It is never used to build the band: an RMSE is not a
width to add and subtract, and swapping them would leave the measured 0.888
describing a band nobody is showing.

**Break-even noise**: 0.5 of one training-fold SD, in both arms (fit clean /
score noisy, and fit noisy / score noisy), against the field-mean baseline.

**Distribution bands** (`bands.json`) — terciles of the training target, cut
once at **0.651** and **1.439** percent (g/100 g), n = 309 / 308 / 309. They are
*position in the distribution of sampled soils*, not a quality grade, and they
were not adjusted to make any band reachable (the file says so in `not_tuned`).
Because the middle third is 0.788 wide and the interval is 4.215 wide, **every
prediction this model makes is reported as "The estimate is too wide to place
in a band."** That is the true answer for this bundle, and it is the answer the
interface must show.

---

## Additive artefacts and the `/api` views

`cv_supplement.py` produces three extra files for an existing bundle **without
touching it**:

| file | contents |
|---|---|
| `cv_supplement.json` | train-fold and out-of-fold `r2`/`rmse`/`mae`/`rpiq` per model and CV design, mean and SD across seeds and folds |
| `bands.json` | terciles of the training target, in the model's own unit, with provenance |
| `sites.json` | one row per sampled site: longitude, latitude, and the spatial fold it fell in |

The pass re-runs the same folds and asserts two things before it writes
anything: every recomputed out-of-fold R² and RMSE must match
`results.validation_gap` to within `1e-9` (measured: `0.000e+00` over 20 checks),
and the sha256 of `results.json`, `model_meta.json` and `model.joblib` must be
**identical before and after**. If either check fails it exits without writing,
so a train score derived from different folds can never be filed next to a
metric it does not belong to.

`sites.json` exists because `results.json` records each row's fold label but no
coordinates, which makes a map of the sample impossible from the bundle alone.
The pass therefore also asserts that its recomputed row groups equal the recorded
`blocking_diagnostics.cluster_label` **element for element** before it pairs a
coordinate with a fold — a map whose colours do not match the folds the scores
were computed on would be a picture of a different experiment.

`GET /api/metrics` composes one payload from those files, and
`POST /api/predict` returns the calibrated interval plus its band placement.
Both are **additive**: `/predict`, `/health`, `/model-info`, `/results` and
`/results.json` are unchanged, and the 32 tests that cover `/predict` still pass.
Two things the new routes do differently, on purpose:

- `/api/predict` returns the conformal interval **unclipped** (`low` may be
  negative, with `below_zero: true`) and reports the spatial RMSE in a separate
  `accuracy` field. `/predict` keeps its old `max(0, pred − half)` behaviour so
  nothing that depends on it moves.
- When `bands.json` is absent, or was derived from a different model version, the
  band fields are `null` and the payload says which file is missing. Silence is
  treated as a gap, never as a placement.

`tests/test_metrics_api.py` walks every number in the payload and fails if one
of them does not exist in `results.json`, `model_meta.json`, `cv_supplement.json`
or `bands.json`. A number in the interface that cannot be traced to a file is a
number somebody typed, and the suite refuses those.

### The farmer view's vocabulary

`farmer_view.py` turns `/api/metrics` and one prediction into the farmer payload.
It holds the banned-terms list, the banned-term matcher, and every sentence a
farmer screen can show — so the test that enforces the list has something finite
to scan. `build()` walks its own output and raises if a banned term survived, so
a bad string cannot reach a browser at all.

Two rules in that module are worth knowing before editing it:

- **No sentence quotes a figure.** The numbers live in the range bar, where
  their width is visible. A headline that says "about 0.9 per cent" would round
  a wide, boundary-crossing interval into something that sounds like a verdict,
  so the headline is chosen by the reliability gate instead and never varies
  with the value.
- **Two gates share one sentence.** `R4_too_wide` and `R5_crosses_one_cut` both
  produce `TOO_UNCERTAIN`, the same constant, so the two cases cannot drift
  apart or be softened one at a time.

The sensor card's figure is read from the metrics file, and the synthetic
`--quick` bundle stores `null` there. The card therefore has a state for "the
test never reached that point" and one for "this bundle has no sweep", and it
uses them instead of inventing a number.

---

## How the numbers are produced

- **Folds.** Random 5-fold KFold vs spatially blocked CV: KMeans on one point
  per site (its coordinate centroid), then GroupKFold over those clusters, so
  whole regions are held out and **records of one site/profile can never appear
  in two folds**. The same folds are used for every model and every scheme
  comparison.
- **Nothing is fitted before splitting.** Imputation, scaling, the log1p target
  transform and hyperparameter tuning all happen inside each training fold.
  `tests/test_validity.py` instruments `Pipeline.fit` and fails if any fit ever
  sees all rows. Tuning is a `GridSearchCV` with an inner GroupKFold *inside*
  the outer training fold (nested CV); no test-fold row is used for tuning.
- **Metrics.** Pooled out-of-fold R², RMSE and MAE on the **original target
  scale** (the log transform is inverted before scoring, so R² is not computed
  on a rescaled target). RPIQ = IQR(y)/RMSE (Bellon-Maurel et al. 2010).
- **Why some SDs are 0.000.** The main comparison deliberately fixes one spatial
  partition across seeds, which makes `R²_random − R²_spatial` a paired
  comparison; the cost is that a spatial cell's SD across seeds measures learner
  randomness only and is exactly 0.000 for deterministic models (ridge, PLS).
  Redrawing the k-means partition does not escape this, because the k-means seed
  turns out not to move any boundary (5 seeds → 1 distinct partition). The
  uncertainty that hides is measured instead in
  `results.partition_sensitivity` (where the boundaries fall, family
  `grid_offset`) and `results.block_sensitivity` (how many blocks). `results.json`
  records this explanation in `validation.spatial_partition_note`.
- **No hard-coded numbers.** The API and the web page read `results.json`; the
  noise series plotted in the demo is discovered from whatever the run actually
  swept. If a cell fails, the run prints `!! FAILED cell …` and leaves the
  number absent (`null` / `NaN`) rather than substituting anything.

## Provenance and reproducibility

`results.json` stores the command line, UTC timestamp, runtime, git commit (if
any), package versions, per-file sha256 manifest and `dataset_version`, the
seed list, the experiment scope, and a `model_version` that is the sha256 of the
exported model bytes. `model_meta.json` stores a `results_sha256` binding the
model to the metrics reported beside it, so editing `results.json` after the run
makes the API refuse to start. Re-running
`python afsis_experiment.py` with the same inputs reproduces every metric
exactly (checked: identical `model_version` and R² values across runs; a test
asserts same-seed → same metrics). Parallel grid search affects wall-clock only.

---

## Limitations — what this prototype does **not** show

- **The real run's target label is not homogeneous.** The column is *Total
  carbon*, but **498 of the 926 rows carry an organic-carbon value** in that
  column, and those rows are pooled with total-carbon rows into a single target.
  Every metric in the real-run section is therefore an average over a mixture of
  two measurements, and the column name overstates how uniform the target is.
  This count comes from inspecting the download; it is **not** in
  `results.json -> limitations` yet, because recording it there means a re-run
  and this pass did not re-run the experiment. Until then it is documented here
  and nowhere else.
- **The 0–5 cm depth rule could not be applied to the real run.** The coalesced
  wet-chemistry table has no depth column (`data.depth_rule.applied = false`), so
  the rows are whatever depth the source provides and the depth scope below does
  not hold for `export_afsis_real/`.
- **The synthetic numbers are not soil results.** Everything in the `export/`
  section comes from a stand-in whose spatial structure and non-stationarity were
  written into the generator so the pipeline could be tested end to end. The gap
  it shows is a property of the simulation, and the earlier version of the
  stand-in produced a gap of ≈ 0 — a bug in the generator, not a finding, fixed
  before these numbers were reported. The real run in `export_afsis_real/`
  replaces those numbers; it does not validate them.
- **No low-cost sensor data.** The features are laboratory wet-chemistry values
  that a sensor could in principle proxy. Nothing has been measured with the
  planned hardware, so the noise sweep is a *model of* sensor error, not a
  measurement of it.
- **No Ugandan field validation.** No soil has been sampled, digested, or dried
  by this project. The Uganda subset of the stand-in (119 rows) is a count of
  simulated records, not evidence about Ugandan farms.
- **Not validated for agronomic decisions.** No rates, timing, carbon-credit or
  certification claim may be made from this prototype. The output is
  **predicted SOC** — an estimate of carbon content in percent — and is not a
  soil-quality rating, not a "soil health" index, and not a carbon stock.
- **Lab-to-lab bias is under-represented.** Replicate records from a second lab
  are collapsed rather than modelled, so measurement error is understated
  relative to a real field sensor.
- **The spatial score depends on the blocking scheme, and one scheme is
  reported.** Rotated rectangular blocks gave spatial R² 0.03–0.07 *higher* than
  the k-means blocks used for the headline, and moving the rectangular boundaries
  from seed to seed costs ±0.034 R² (random forest). The headline is one
  defensible choice, not a scheme-averaged estimate; `results.partition_sensitivity`
  and `results.block_sensitivity` hold the spread and should be quoted beside any
  spatial number.
- **The interval is marginal.** One width for all inputs, not conditional on the
  feature values, and its measured coverage (0.824) is below its nominal level
  (0.90) under spatial CV.
- **Physical bounds are heuristic.** The impossible-value ranges the API
  enforces (pH 0–14, EC 0–50 dS/m, texture 0–100 %) are physical limits, not
  AfSIS QC rules.
- **Depth scope.** Only the 0–5 cm band is modelled; nothing here extrapolates
  to subsoil.
- **Unit inference is a guess until checked.** Units are inferred from the
  distribution and printed; a real run must confirm them (g/kg vs % changes RMSE
  by 100×).

## What the first real-data run must check

1. `--list-columns` output: confirm target, features, coordinate and id columns
   before trusting anything.
2. The cleaning ledger: the Uganda row count, and that removals are the count
   you expect from the AfSIS QC notes.
3. Whether the spatial gap survives contact with real data. If `R²_spatial` is
   *not* below `R²_random`, that is a result, not a failure — report it as is
   and check whether the blocking is actually holding out distinct regions.
4. The empirical coverage of the interval, and whether the break-even noise
   level falls inside 0–100 % of feature SD once real sensor error is measured.
5. The two partition families again: on real coordinates the k-means blocking may
   become seed-sensitive (the stand-in's compact country clusters are why it was
   not), and the rectangular family may no longer score above it. Both are
   printed by `[E4b]` and written to `results.json`, so nothing has to be assumed.
