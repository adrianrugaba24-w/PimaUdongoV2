# Texture ablation — what the three texture fractions actually carry

Status: **measured, paired, reproducible.** Bundle `export_afsis_notexture/`, model
`sha256:123a6d79f883e2b5`. The headline bundle is untouched at `sha256:57ae8583074e476a`.

---

## 1. Question

The headline model uses five features: `pH_H2O`, `EC`, and the three texture fractions.
Texture is not a sensor reading in the planned probe, so the question is whether the
reported skill depends on a variable the device cannot measure.

---

## 2. Protocol

Nothing changed except the feature list. Same root, same target, same blocks, same seeds,
same models, same grids, same conformal calibration:

```bash
python afsis_experiment.py --root data/afsis_real --export export_afsis_notexture \
  --target "Total carbon" \
  --features pH_H2O EC "Clay percent" "Sand percent" "Silt percent" \
  --drop-features "Clay percent" "Sand percent" "Silt percent" \
  --blocks 10 --seeds 5
```

The ablation is recorded inside the bundle (`feature_ablation` in both `results.json` and
`model_meta.json`), so an ablated run can never be mistaken for the headline run.

---

## 3. Results

| Model | R² random (5 feat → 2) | R² spatial (5 → 2) | Gap (5 → 2) | RMSE spatial (5 → 2) |
|---|---|---|---|---|
| **random forest** | 0.338 → **0.194** | 0.086 → **0.028** | 0.252 → **0.167** | 1.339 → **1.380** |
| **gradient boosting** | 0.295 → **0.197** | 0.078 → **0.026** | 0.217 → **0.170** | 1.344 → **1.381** |
| PLS | −0.112 → −0.235 | −0.333 → −2.565 | 0.221 → 2.330 | 1.616 → 2.643 |
| ridge | −0.187 → −0.227 | −8.190 → −10.294 | 8.003 → 10.067 | 4.244 → 4.705 |
| field mean | −0.002 → −0.002 | −0.030 → −0.030 | 0.028 → 0.028 | 1.421 → 1.421 |

Interval unchanged in character: coverage 0.888 → 0.883, width 4.215 → 4.256 g/100 g.

---

## 4. What it means

**1. About a third of the validation gap is texture.** The gap falls 0.252 → 0.167 under
random forest and 0.217 → 0.170 under gradient boosting. Texture contributes 0.058 of the
0.086 spatial R², but 0.144 of the 0.338 random R² — in absolute terms random CV rewards
texture two and a half times more than spatial CV does. The gap is therefore not an
artefact of one variable, but it is inflated by it.

**2. The headline finding survives without texture.** A 0.167 gap remains, and the model
still beats the field mean on ground it has never seen: 1.380 against 1.421 g/100 g.
A 0.041 improvement is small, and it should be described as small.

**3. The refusal is robust.** The interval stays 5.4 bands wide (band = 0.788), so the
reliability gate refuses exactly as before. Removing a feature does not buy a reportable
number.

**4. The linear models are not a fair ablation here.** PLS fails three of nine grid fits
because `n_components = 3` exceeds the two available features, and ridge with two
collinear-ish inputs degrades further. Report only the tree models in this comparison; the
PLS and ridge rows say something about linear models with a 2-feature budget, not about
texture.

---

## 5. Limits

- Still AfSIS Phase I, still 926 rows, still 19 countries, 32 of them Ugandan.
- This says nothing about whether a field probe can measure texture by another route
  (laser diffraction is not in scope here).
- The ablation was run once at the reported seeds; the ±SD in the bundle applies to
  seeds, not to this comparison.

---

## 6. One line for the poster

> Dropping the three texture fractions, which no field probe in this design measures,
> removes a third of the validation gap but leaves the model better than the field mean
> (1.380 vs 1.421 g/100 g) and the interval still far too wide to report.

---

## 7. Reproduce

```bash
python afsis_experiment.py --root data/afsis_real --export export_afsis_notexture \
  --target "Total carbon" \
  --features pH_H2O EC "Clay percent" "Sand percent" "Silt percent" \
  --drop-features "Clay percent" "Sand percent" "Silt percent" \
  --blocks 10 --seeds 5
```

Runtime 166 s. `export_afsis_real/` is not modified by this command.
