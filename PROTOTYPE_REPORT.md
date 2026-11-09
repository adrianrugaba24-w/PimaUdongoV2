# PimaUdongo — Prototype Report

**What this document is.** A plain-language description of the prototype: what it is, what it
can do, what it cannot do, and how to run it. Written to be reused in a presentation, a
supervision meeting or a handover, not read once and discarded.

**Every number here is read from the committed bundle.** Model `sha256:062d36c53a562f80`,
dataset version `afsis-3f-296718c140e3`, 407 training rows. Full precision lives in
`export/results.json`; figures below are rounded to three decimals for reading only.

---

## Status first

The committed bundle was produced on a **synthetic stand-in dataset**, not on real soils.
The API reports this as `data_is_real: false`, and the demo page shows a red banner saying so.

The pipeline, the validation logic, the interval method and the serving layer are all real and
executed. The *numbers* describe a simulation. They test the machinery; they are not
measurements of any soil, and must not be quoted as findings about African soils.

---

## 1. In one paragraph

PimaUdongo estimates the organic carbon content of a soil sample from five routine measurements
— pH, electrical conductivity, and clay, sand and silt percentages — and, more importantly, it
measures how much of its apparent accuracy survives when it is tested on ground it has never
seen. Carbon models are usually scored by random cross-validation, which allows a model to be
tested on samples taken from the same places it was trained on. This prototype scores the same
models both ways — randomly and with whole geographic blocks held out — and reports the
difference between the two as a result in its own right.

## 2. The question it answers

> Does the reported accuracy of a soil carbon model depend on how it was validated?

Not rhetorically: it measures both scores from the same folds, the same seeds and the same
tuning, and reports the gap per model. The gap is therefore an observed quantity, not an
argument.

## 3. How it works

1. **Load and clean.** Records are joined, duplicate and impossible values are removed, and
   every removal is written to a ledger (rows before, rows after, reason).
2. **Split geographically.** Sites are clustered into spatial blocks, and whole blocks are held
   out for testing. A random split is generated alongside it for comparison.
3. **Train, tune and score.** Each model is tuned by nested cross-validation, so nothing —
   imputer, scaler, log transform, hyperparameters — is ever fitted on data outside its own
   training fold.
4. **Attack it.** The run is repeated with a shuffled target, with different numbers of spatial
   blocks, with redrawn block boundaries, and with known levels of input noise.
5. **Attach an interval and a receipt.** A conformal prediction interval is calibrated on
   held-out blocks, and the artefacts are stamped with a model hash, a dataset version and a
   hash linking model to results.

## 4. What it can do

| Capability | Evidence |
|---|---|
| Predict soil organic carbon from five inputs | `POST /predict` returns a value, a 90 % interval and the measured coverage of that interval |
| Report the random-vs-spatial gap for five models | Random forest 0.761 → 0.611; the gap is 0.151 |
| Show what happens with no skill at all | The field-mean baseline scores −0.005 random and −0.361 spatial |
| Detect a leaky or fake result | A shuffled-target control scores near zero, as it must |
| Show the score is sensitive to the split design | Block-count and boundary-redraw sweeps are both reported |
| Refuse impossible inputs | Out-of-range values return 422 with the offending field named |
| Flag extrapolation | Inputs outside the training 5–95 % range are served but flagged |
| Refuse to serve a mismatched artefact | The API will not start if the model and results hashes disagree |
| Prove which artefact produced a number | Every response carries the model version and dataset version |
| Survive scrutiny of its own test suite | 151 tests pass, including a spy that fails if any model fit is ever handed the full dataset |

## 5. What it cannot do

- **Use real soils yet.** The committed bundle is synthetic. The data is downloaded and
  committed; the loader changes are not written (section 7).
- **Read field sensors.** Three of the five inputs are laboratory texture measurements. pH and
  EC are field-measurable; clay, sand and silt are not, without a lab or an alternative method.
- **Give agronomic advice.** The model returns a percentage. It has no action layer, and the
  thresholds for "low" carbon are soil- and region-specific. Any such advice would be invented.
- **Grade or rank soil quality.** Not supported, and deliberately not implemented.
- **Draw maps.** Spatial R² is 0.611 and out-of-domain checks are per-input, not spatial. A map
  would imply an extrapolation ability the model does not have.
- **Process many samples at once.** There is no batch endpoint; requests are one record at a time.
- **Claim validation on farms.** It has never seen a field sensor or a Ugandan farm.

## 6. Headline results (synthetic)

Trained on 407 synthetic rows; 5 outer folds, 10 spatial blocks, 5 seeds.

| Model | R² random | R² spatial | Gap | RMSE spatial |
|---|---|---|---|---|
| Random forest | 0.761 | **0.611** | **0.151** | 0.729 |
| Gradient boosting | 0.750 | 0.590 | 0.159 | 0.748 |
| Ridge | 0.648 | 0.428 | 0.220 | 0.883 |
| PLS | 0.625 | 0.393 | 0.232 | 0.910 |
| Field-mean baseline | −0.005 | −0.361 | 0.356 | 1.363 |

Reading: every learned model looks better under random validation than under spatial
validation, and the best model loses about a fifth of a point of R² when whole regions are held
out. The baseline losing 0.356 is the same effect with no learning in it at all — which is why
the baseline is included.

**Interval honesty.** A 90 % interval achieved **82.4 %** coverage on unseen blocks (SD 7.6
points), with a mean width of 2.29 % carbon. It under-covers, and the prototype reports that
rather than widening the interval until the number looks right.

**Noise.** No break-even was reached: at every noise level tested (0, 0.1, 0.25, 0.5, 1.0 ×
feature spread), the leading model still beat the field mean.

## 7. Where the real-data work stands

The AfSIS Phase I files are downloaded and committed under `afsis/` (1.35 MB, ODC-By licence,
attribution required).

| Item | Verified value |
|---|---|
| Georeferenced samples | 1,843 |
| Samples with total carbon | 1,839 (926 topsoil) |
| Samples with organic carbon | 467 (229 topsoil) |
| Countries | 19 |
| Ugandan samples | 64 (32 topsoil) |

Three things block a real run, all loader changes rather than data problems:

1. The three laboratory tables hold **disjoint** measurement sets, so one row per sample must be
   coalesced before a feature vector exists.
2. Depth is recorded as `top`/`sub`, not as a depth in cm, so the current depth rule removes
   every row.
3. No column matches the target pattern automatically; the target must be named explicitly.

Total carbon is the practical target (1,839 samples) but must be **declared** as a proxy:
it correlates 0.917 with organic carbon in the 467 samples where both exist, differs by more
than 0.5 % in 37 of those, and inorganic carbon exceeds 1 % in 7.

## 8. How to run it

```
python afsis_experiment.py --quick          # regenerate the bundle
python -m pytest -q                         # 151 tests
python -m uvicorn soil_api:app --port 8000  # serve the demo
```

Open `http://127.0.0.1:8000/`. Requirement: `scikit-learn==1.8.0` exactly, because the saved
model is a pickle and the API refuses to start on a version mismatch.

## 9. Known gaps before submission

- `AFSIS_LICENCE` in `afsis_experiment.py` still reads "ODbL / ODC-By"; `afsis/LICENSE.txt`
  shows **ODC-By only**. The string is written into `results.json` on every run.
- `clean()` raises `KeyError: None` when no target column is detected, instead of a clear error.
- The demo page presents the research dashboard directly, with no plain-language entry point
  and no unit conversion, so a user can enter EC in µS/cm and be off by 1000×.
- The limitation text rendered on the demo page still uses the earlier framing about absent
  sensor data; check it against the terminology used in the submission.

---

**One-line summary.** A working, tested pipeline that measures how much a soil-carbon model's
reported accuracy depends on how it was validated, demonstrated end to end on simulated data,
with real-data wiring one small step away and no claims made about real soils.
