# Systematic gain error — the failure mode random noise does not model

Status: **measured, paired, reproducible.** Bundle `export_afsis_gain/`, 30 sweep cells,
665 s. The deployed model is byte-identical to the headline (`sha256:57ae8583074e476a`):
the sweep added evidence without changing the trained artefact.

---

## 1. Why this is not the noise sweep

The existing sweep adds Gaussian noise drawn per row. A mis-calibrated probe does not do
that: it reads high by the same proportion on every sample, so averaging does not remove
it and a model cannot learn it away if it only appears after training.

Two arms, because the failure differs:

| Arm | Fit sees | Deployment sees | Real situation |
|---|---|---|---|
| `train_gain` ("same device") | gain | gain | one instrument throughout |
| `train_clean` ("drift") | clean | gain | laboratory-trained model, field device |

Each channel gets its own signed factor for the whole fold:
`factor_j = 1 + m · u_j`, with `u_j ~ Uniform(−1, 1)`, drawn from the seed alone so no
training statistic enters. `m = 0.5` therefore means factors between 0.5 and 1.5.

---

## 2. Command

```bash
python afsis_experiment.py --root data/afsis_real --export export_afsis_gain \
  --target 'Total carbon' \
  --features pH_H2O EC 'Clay percent' 'Sand percent' 'Silt percent' \
  --blocks 10 --seeds 5 --gain-sweep
```

---

## 3. Results

Random forest, R² / RMSE (g/100 g), spatial CV, field-mean RMSE 1.421:

| gain m | same device | drift |
|---|---|---|
| 0.00 | 0.100 / 1.328 | 0.100 / 1.328 |
| 0.10 | 0.100 / 1.328 | 0.071 / 1.349 |
| 0.25 | 0.100 / 1.328 | 0.049 / 1.365 |
| 0.50 | 0.100 / 1.328 | −0.006 / 1.404 |
| 1.00 | 0.100 / 1.328 | −0.108 / 1.473 |

Gradient boosting, same layout:

| gain m | same device | drift |
|---|---|---|
| 0.00 | 0.071 / 1.349 | 0.071 / 1.349 |
| 0.10 | 0.071 / 1.349 | 0.044 / 1.369 |
| 0.25 | 0.071 / 1.349 | 0.014 / 1.390 |
| 0.50 | 0.071 / 1.349 | −0.048 / 1.433 |
| 1.00 | 0.071 / 1.349 | −0.191 / 1.528 |

Ridge, drift only (it is the case that moves): −8.190 / 4.244 → −5.275 / 3.505 →
−2.744 / 2.702 → −0.963 / 1.953 → −0.294 / 1.592. Consistent arm flat at −8.190.

---

## 4. What it means

**1. A gain present in training is free.** Every "same device" row is identical to four
decimal places across the whole sweep. A monotone per-channel scaling is absorbed by the
trees and cancelled by the scaler for ridge. This is the useful negative result: the
damage does not come from a badly calibrated probe as such, it comes from a calibration
that changes between fitting and deployment.

**2. Drift is the failure mode, and it is steep.** Under random forest, a 10% per-channel
drift costs 29% of the spatial R² (0.100 → 0.071) and the model stops beating the field
mean between 50% (1.404) and 100% (1.473). The gradient booster crosses over earlier,
between 25% (1.390) and 50% (1.433).

**3. A model that improves under corruption is broken.** Ridge's R² rises from −8.190 to
−0.294 as drift grows. That is not robustness: its predictions are so badly scaled that
any distortion pulls them toward the field mean. Treat "score improves as error increases"
as a diagnostic that the model was mis-specified, never as a result.

**4. Do not put gain and noise on the same axis.** Noise is additive, per row, in units of
feature SD; gain is multiplicative, constant per fold. `0.25 noise` and `0.25 gain` are
different quantities, and the two sweeps must be reported separately.

---

## 5. Limits

- AfSIS Phase I, 926 rows; spatial CV only; fixed hyperparameters (`tune=False`), matching
  the noise sweep so the two are comparable within themselves.
- Per-channel factors are drawn independently, so nothing here models a device whose
  channels drift together.
- The gain sweep uses its own seed set, so its `gain = 0` row is not the headline number
  (0.100 vs 0.086). Compare within the sweep, not across it.
- Real probes also drift over time, not only between sites. That is a third case, still
  unmeasured.

---

## 6. One line for the poster

> A calibration error carried through training and deployment costs nothing; one that
> appears only in the field costs the random forest its advantage over the field mean
> somewhere between 50% and 100% per-channel scale error.

---

## 7. Reproduce

As in section 2. `export_afsis_real/` and `export_afsis_notexture/` are not touched by it.
