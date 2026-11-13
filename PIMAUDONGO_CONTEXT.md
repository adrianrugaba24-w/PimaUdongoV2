# PimaUdongo: project context for the agent

Purpose: tell the agent what stage the project is at, how it relates to SMART-AG, and what must and must not be claimed. Facts come from the project's own documents and the SMART-AG PDF. Items marked INFERENCE are readings, not stated facts. Verify any figure against the files before quoting it.

## 1. What the project is

A soil-carbon prediction pipeline whose central claim is a measurement, not a model:

> Reported accuracy depends on the validation design, so a soil model must be tested for geographic generalisation and for input noise before its score means anything.

Two layers:
- Dissertation: a systematic literature review plus a validation and sensor-robustness framework for ML soil prediction in sub-Saharan Africa.
- Prototype: validation engine, noise harness, provenance-checked API, researcher view, farmer view.

## 2. Stage

| Phase | Content | Status |
|---|---|---|
| 1 | Software and validation on real AfSIS lab data | Built and run |
| 2 | Evidence base and fixes (SLR `\TBC` cells, open checks in section 6) | Open |
| 3 | Uganda-specific transfer test | Not run |
| 4 | Hardware: low-cost sensor paired with lab values on Ugandan soils | Planned, not started |

The end goal is a hardware aspect similar in spirit to SMART-AG. Today there is no hardware, and sensor noise is simulated with parameters marked `assumed`.

## 3. Real-data results (bundle `export_afsis_real/`)

- Dataset `afsis-2f-ddd215cc66b5`: 926 rows, 58 named sites, 16 clusters, 19 countries (Uganda 32 rows). Model version `sha256:57ae8583074e476a`.
- Target: total carbon (%). Organic carbon exists for 498 rows and was not used.
- Features: pH (water), EC (dS/m), clay, sand, silt.
- Random forest: R2 spatial 0.086, R2 random 0.338, RMSE spatial 1.339 against field-mean 1.421.
- Ridge: R2 spatial -8.19. Cause not yet diagnosed.
- Shuffled-target control passes (all near zero).
- Interval: 0.888 coverage against 0.90 nominal, width 4.21 (about 4.5 times the median value).
- H1 (spatial below random) is supported. H3 as written (R2 >= 0.50) is stated for pH, so it has not been tested on the real data, because the run used total carbon.

## 4. SMART-AG (reference system, not this project)

Source: "SMART-AG: A Precision Agriculture AI-Powered Edge Computing System", T. K. Bushenyula, UCU BSc project report, April 2025. Only the PDF has been seen, not the code or data.

What it is: a built offline device. An NPK 7-in-1 sensor (N, P, K, pH, EC, temperature, moisture) feeds a Raspberry Pi 4 through an RS485-to-TTL converter. Two classifiers run on the Pi: soil quality (Poor/Average/Good, LGBMClassifier) and crop recommendation. A SIM800L module sends a daily SMS at 6:30 AM. Target users: smallholder farmers. Tested for about two weeks and informally by a small group of agriculture students.

What it reports: score 1.0 train and 1.0 test for soil quality, 0.9987 and 0.9909 for crop. Data are foreign datasets adapted to Africa. The report admits this produced crops uncommon in Africa.

Reviewer observations (INFERENCE, my reading): a score of 1.0 on both splits with a single held-out split says nothing about new fields. No baseline, spatial split, or sensor-error figure is reported. The humidity chart rises but its caption says "drop". The advice text appears to be fixed per class (INFERENCE from the flow diagram).

## 5. How the two relate

SMART-AG is a completed build with light evaluation. PimaUdongo is validation-first, with hardware to be added later and judged against a measured baseline. The difference is the order of work and the standard of evidence, not only whether hardware exists.

Fair framing for the paper: SMART-AG shows the pipeline can be built. PimaUdongo's hardware phase adds what it did not report: sensor error measured against laboratory values, and spatially validated skill.

Direct links:
1. pH and EC appear in both input sets.
2. A cheap field sensor feeding a model with unmeasured sensor accuracy is a real instance of research gap (iii).
3. A single-split score near 1.0 illustrates H1's concern.
4. SMART-AG's foreign-data problem supports using AfSIS.
5. SMART-AG lists organic-content sensing as future work. PimaUdongo's target is carbon.

Mismatches the hardware phase must solve:
- Inputs: the model uses pH, EC, clay, sand, silt. An NPK probe measures N, P, K, pH, EC, temperature, moisture. Only pH and EC overlap, and texture cannot come from that sensor. The sensor choice dictates the model: retrain on measurable features or supply texture from the lab.
- Target: a standard NPK probe does not measure carbon, so carbon would remain a prediction from proxies.
- Units: SMART-AG's sample SMS shows EC 876 with no unit. If it is uS/cm that equals 0.876 dS/m, above the training p95 of 0.32 (INFERENCE). In-soil probe EC and laboratory-extract EC are not interchangeable without calibration.
- Gap (i) wording: SMART-AG was built at a Ugandan university. Check the SLR inclusion criteria for grey literature and state the decision.

## 6. Open checks and decisions (do not silently resolve)

1. Confirm scaling, imputation and the log transform are fit inside training folds only (a test reportedly enforces this).
2. Confirm whether inner tuning folds are spatially grouped.
3. The data card says 926 sites but the group key was `SSN`, so that is 926 rows. Physical grouping is 58 sites and 16 clusters. Relabel in the card and UI.
4. Confirm whether `n_estimators` is fixed or tuned for gradient boosting.
5. Run a pH-target version on real data to test H3 as written.
6. Run leave-one-country-out for Uganda against the field-mean baseline.
7. Check total carbon against organic carbon on the 498 paired rows, split by pH (below and above about 7.5).
8. Diagnose the ridge collapse by looking at which rows drive the error and testing without the log transform.
9. Reissue `REPORT_SCOPE_SHEET.md` and `PROTOTYPE_REPORT.md` against the real bundle. They still describe the synthetic `export/` bundle.
10. Fill the SLR `\TBC` cells from the extraction forms.
11. Decide the farmer audience: `UI_UX_REFERENCE.md` constraint C8 bans farmer framing while the implementation report adds a farmer view. State which phase each document describes.
12. UI: promote interval width to a headline, show clusters beside rows, return and display raw negative predictions, render `interval_warning`.

## 7. Rules for the agent

- Keep every displayed or quoted number traceable to a generated file. Do not retype figures from older reports.
- Do not use "soil health", and do not use unqualified "accurate", "reliable", "precise" or "validated". Do not give agronomic advice.
- Do not call the target SOC when it is total carbon.
- Do not describe SMART-AG as wrong or fake. Cite it factually: single-split reporting, no spatial validation, no sensor-error analysis.
- Do not compare SMART-AG's accuracy with PimaUdongo's R2. The tasks differ (classification against regression) and so does the validation.
- Do not assume SMART-AG's code, data or hardware are available.
- Report weak results as weak. A spatial R2 of 0.086 is a finding.
- Do not move the band cuts or tune thresholds to make a result look better.
