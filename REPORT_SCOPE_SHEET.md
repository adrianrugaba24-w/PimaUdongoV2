# Report Scope Sheet — PimaUdongo Prototype Report

Governs: `PROTOTYPE_REPORT.md`
This sheet defines what the report may cover, what it must not claim, and what counts as
acceptable before it is issued. Change this sheet before changing the report's boundaries.

| Control | Value |
|---|---|
| Document ID | PUD-RSS-001 |
| Version | 1.0 (Draft, for review) |
| Describes bundle | model `sha256:062d36c53a562f80`, dataset `afsis-3f-296718c140e3`, 407 rows |
| Governs | `PROTOTYPE_REPORT.md` (`PUD-REP-001`) |
| Owner | Project author |
| Approver | Supervisor |
| Status | Draft — not yet issued |

---

## 1. Purpose of this sheet

To fix the report's boundaries before the report is circulated, so that scope is a decision
rather than something a reader infers. It answers three questions: what the report covers, what
it is forbidden to claim, and how anyone can tell a compliant report from a non-compliant one.

## 2. Purpose of the report

A plain-language description of the prototype: what it is, what it can do, what it cannot do,
and how to run it — written to be reusable in a presentation, a supervision meeting or a
handover, and to remain accurate without its author present.

## 3. Audience

| Reader | Takes away | Depth they are owed |
|---|---|---|
| Panel / examiner | The research question, the measured answer, the limits | Sections 1, 2, 6 |
| Supervisor | Status, known gaps, what to authorise next | All sections |
| Technical reader | How it works, how to reproduce it | Sections 3, 8 |
| Future student | What is done, what is not, where the seams are | Sections 5, 7, 9 |
| Non-specialist | One paragraph and one caution | Section 1 and the status note |

## 4. In scope

- What the prototype is and the question it measures.
- The validation logic: random versus spatially blocked scoring, and the gap between them.
- Results from the committed bundle, stated with their artefact versions.
- The limits of the prototype, given equal prominence to the capabilities.
- The state of the real AfSIS data and what still blocks a real run.
- Reproduction instructions sufficient to rebuild the bundle and run the tests.
- Known defects found during development.

## 5. Out of scope

| Excluded | Reason |
|---|---|
| Any claim about African, East African or Ugandan soils | The committed bundle is synthetic (`data_is_real: false`) |
| Accuracy on field sensors or on farms | No sensor data exists; the model has never seen one |
| Cost, affordability or economic argument | No cost data was collected, so no economic claim is defensible |
| Smallholder or farmer-impact claims | Not measured, not surveyed, not validated |
| Agronomic recommendations | The model has no action layer; thresholds are soil- and region-specific |
| Soil quality grading or ranking | Would require published local thresholds that the project does not hold |
| Spatial maps or predicted surfaces | Out-of-domain checks are per-input, not spatial |
| Sensor hardware design, calibration or deployment | Separate project phase |
| Literature review, methodology justification, ethics | Belong to the dissertation, not this report |
| Comparison with published SOC models | Not performed; no benchmark run exists |

## 6. Evidence basis

Authoritative sources, in order. A figure that cannot be traced to one of these does not enter
the report.

| Source | Supplies |
|---|---|
| `export/results.json` | All scores, intervals, sweeps, cleaning ledger, limitations |
| `export/model_meta.json` | Model version, `results_sha256`, feature order |
| `afsis/LICENSE.txt`, `afsis/README.md` | Licence and attribution wording |
| `afsis/` CSVs | Real-data counts in section 7 |
| Live test run | Test count in section 4 |

Rules:
1. No number is written from memory, a summary, or an earlier report version.
2. Rounding is for readability only, three decimals, and never in a direction that flatters.
3. Every results section states the bundle it describes.
4. Where a figure is a proxy rather than a measurement, it is labelled as one at first use.

## 7. Structure map

| Report section | Serves | Evidence column sourced from |
|---|---|---|
| Status first | All readers | `model_meta.json` |
| 1. In one paragraph | Non-specialist, panel | none (no figures) |
| 2. The question it answers | Panel | none (no figures) |
| 3. How it works | Technical reader | `afsis_validation.py` behaviour |
| 4. What it can do | Panel, technical | `results.json`, API contract, test run |
| 5. What it cannot do | All readers | `results.json` limitations, data audit |
| 6. Headline results | Panel | `results.json` validation gap, interval |
| 7. Real-data status | Supervisor, future student | `afsis/` CSVs, audit notes |
| 8. How to run it | Technical reader | `requirements.txt`, CLI |
| 9. Known gaps | Supervisor | Development audit |

## 8. Claim boundaries

| The report may assert | The report must not assert |
|---|---|
| The pipeline is implemented, executed and tested (151 tests) | That the model predicts SOC in real soils |
| A gap of 0.151 was measured **under this simulation** | That African soil data shows a gap of 0.151 |
| The interval under-covers: 82.4 % against a 90 % target | That the interval is decision-grade |
| Impossible inputs are refused; extrapolation is flagged | That the tool is safe for unattended field use |
| Real AfSIS data is downloaded: 1,839 samples with total carbon | That a real-data run has been completed |
| Total carbon is a defensible proxy (r = 0.917) **if declared** | That total carbon and organic carbon are equivalent |
| The data licence is ODC-By and requires attribution | That redistribution is unrestricted |

## 9. Acceptance criteria

The report is issuable only when every line below holds.

- [ ] The synthetic caveat appears before section 1 and names `data_is_real: false`.
- [ ] Model and dataset versions appear in the report header and this sheet.
- [ ] Every figure traces to a listed evidence source at the stated bundle version.
- [ ] The cannot-do list is present and is not shorter than in this version.
- [ ] No economic, cost, affordable, smallholder or farmer-impact terminology appears.
- [ ] No agronomic recommendation, grading or scoring appears.
- [ ] The licence wording matches `afsis/LICENSE.txt` exactly (ODC-By, no ODbL).
- [ ] The test count matches the most recent complete test run.
- [ ] Commands in section 8 are copy-paste runnable on a clean environment.
- [ ] No prediction, figure or date is carried over from an earlier bundle.

## 10. Assumptions and constraints

- The report describes the artefact at the stated hash. A different bundle is a different report.
- `scikit-learn==1.8.0` is fixed by the pickle; the report cannot describe a version-flexible run.
- The report is written in English only; translation is a separate deliverable.
- The report contains no screenshots, so it cannot become stale against the user interface.
- Length target: readable in ten minutes; no section longer than one page.

## 11. Change control

| Trigger | Action |
|---|---|
| `afsis_experiment.py` is re-run | Reissue: new version of this sheet and the report; re-verify every figure |
| A real-data bundle replaces the synthetic one | New scope version; synthetic results become a historical baseline, not the headline |
| `AFSIS_LICENCE` is corrected in code | Update section 9 of the report and the evidence table here |
| `/predict` contract changes | Update the evidence column for section 4 |
| A new input feature is added | Re-scope: the five-input description and the out-of-domain ranges change |
| Scope is widened to advice or economics | Requires a new sheet and supervisor approval; cannot be done by editing the report |

## 12. Sign-off

| Role | Name | Decision | Signature | Date |
|---|---|---|---|---|
| Author | | Prepared | | |
| Supervisor | | Approved / Returned | | |
| Second reader | | Approved / Returned | | |

---

**Boundary in one line.** The report describes and evidences a working validation pipeline on
simulated data; it makes no claim about real soils, real farmers or economic value, and any
version that does is out of scope by definition.
