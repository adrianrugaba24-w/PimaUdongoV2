# Prototype assessment and next best actions

Status at time of writing. Every figure below is read from the repository; nothing is
estimated. Section 10 lists the commands that reproduce each claim.

---

## 0. How to use this document

The prototype demand is a **demo that relates to the final system** — not a toy that
happens to run. So the test applied here is fidelity: does what you can demonstrate
today exercise the same inputs, the same decision rule and the same evidence trail that
the final hardware system will depend on?

Three audiences:
- **You**, to decide what to build next.
- **A supervisor or panel**, to see the state without reading the code.
- **A future session**, to resume without re-deriving anything.

---

## 1. What the final system is, so the demo can be measured against it

> A low-cost soil probe, paired in the field with laboratory values on Ugandan soil,
> feeding the same decision service: report a band, refuse, or refer to a laboratory,
> with the validation design attached.

Four things must therefore survive from demo to final: the **input contract**, the
**decision rule**, the **provenance trail**, and the **audience split**. Anything in the
demo that does not exercise one of those is demonstration dressing.

The project's own phase table (`PIMAUDONGO_CONTEXT.md` §2):

| Phase | Content | Status |
|---|---|---|
| 1 | Software and validation on real AfSIS lab data | Built and run |
| 2 | Evidence base and fixes | Open |
| 3 | Uganda-specific transfer test | Not run |
| 4 | Hardware: probe paired with lab values on Ugandan soils | Not started |

---

## 2. Current state, with evidence

| Component | Where | Evidence it works |
|---|---|---|
| Validation engine | `afsis_validation.py` | `FOLDS = 5`; random `KFold` vs `GroupKFold` over `KMeans(n_clusters=10)` on site coordinates; nested `GridSearchCV`; 5 seeds |
| Noise harness | `afsis_validation.py` | `NOISE_LEVELS = [0.0, 0.1, 0.25, 0.5, 1.0]`; `ARMS = ("train_clean", "train_noisy")` |
| Provenance gate | `load_bundle()` in `soil_api.py` | 6 ordered checks; `model_version` `sha256:57ae8583074e476a`; refuses startup on mismatch |
| Dataset | `export_afsis_real/` | `afsis-2f-ddd215cc66b5`, 926 rows, 58 sites, 16 clusters, 19 countries |
| Decision layer | `reliability.py` | R1–R6 rules, `advice_withheld=True`; R4 fires when interval ≥ band |
| Researcher view | `/researcher`, `/api/metrics` | Numbers read from the bundle, none hard-coded |
| Farmer view | `farmer_view.py`, `/farmer` | Banned-term list enforced by `tests/test_farmer_view.py` |
| Tests | `tests/` | 349 collected |
| HTTP surface | `soil_api.py` | 14 routes |

Measured results, unchanged and reproducible: R² 0.338 random vs 0.086 spatial, gap
0.252; RMSE 1.339 against field mean 1.421; R² 0.039 at 0.25 noise and −0.094 at 0.50;
interval coverage 88.8% against 90% nominal at width 4.21; band width 0.788, so the
interval is 5.3 bands wide and **every prediction is refused**.

---

## 3. Readiness scorecard

Scored 0–3, equal weights, against demo-fidelity rather than against ambition.

| Dimension | Score | Why |
|---|---|---|
| Reproducibility | 3 | Frozen bundle, hash, 349 tests, results regenerate to zero difference |
| Evidence completeness | 3 | Two designs, 5 models, controls, sensitivity, intervals |
| Decision logic | 2 | The gate works; there is no endpoint that explains *why* it refused, in numbers |
| Audience split | 2 | Two views over one payload; no identity, so both share one deployment |
| Input contract | 1 | Form fields only; nothing a probe could post to |
| Audit trail | 0 | Stateless: no database, no log, no record of what was asked |
| Deployment portability | 1 | No Dockerfile, pyproject, Procfile or Makefile; runs from your shell |
| Hardware readiness | 0 | No ingest contract, no calibration protocol, no BOM |
| Honesty controls | 3 | Refusal state, simulated-noise wording, banned-term tests |
| **Total** | **15 / 27** | Strong on evidence and integrity; weak on operation |

The pattern is exact: the prototype is scientifically finished and operationally a
demonstration. That is a coherent state for phase 1 — but it is not yet a demo that
relates to a hardware final.

---

## 4. What the demo can show today

Five minutes, no slides:

1. **Show the answer.** `/researcher`, type five values, submit. The screen returns a
   refusal: *the estimate is too wide to place in a band*. Say: "this is the system
   working, not failing."
2. **Show why.** Coverage 88.8% against 90%; width 4.21 against a band 0.788. Say: "it
   is calibrated and still unusable, because width is the constraint, not coverage."
3. **Show the design effect.** R² 0.086 spatial beside 0.338 random for the same forest
   and the same rows. Say: "the number you quote depends on how you split."
4. **Show the noise result.** R² 0.039 at 0.25 SD, −0.094 at 0.50. Say: "there is a
   measured error level at which this stops beating the field mean."
5. **Show the farmer view.** Same payload, plain words, no numbers invented, and the
   banned-term test that enforces it. Say: "the same answer, and it refuses to advise."
6. **Show the provenance.** `model_version`, dataset id, six checks before serving. Say:
   "every number on those screens traces to a file with a hash."

That is a defensible demo. It is not yet a demo of the *final* system, because steps 1–6
never touch the input path a probe would use.

---

## 5. Gap analysis: demo to final

| Dimension | Today | Final needs | Distance |
|---|---|---|---|
| Input contract | HTML form | Probe posts five values plus a source tag | 1 endpoint, 1 test |
| Decision rule | Refuses all | Same rule, driven by real width | No change needed |
| Audit trail | None | A record per decision, replayable | 1 log file, 1 test |
| Provenance | Model + dataset hash | Also sensor serial and calibration date | Field added to the contract |
| Hardware | None | Probe, reference lab values, paired sampling protocol | Phase 4 |
| Uganda evidence | 32 of 926 rows | Transfer test, then field data | Phase 3, then 4 |

Four of the six rows are small software changes. The last two are the actual research.

---

## 6. Next best actions, ranked

Effort: **S** ≤ half a day, **M** 1–2 days, **L** a week or more.

### A1 — Ingest contract stub · S · do first

`POST /api/ingest` accepting the five properties plus `source: "form" | "sensor"` and an
optional `device_id`, returning exactly what `/api/predict` returns.
**Why first:** it is the one thing that makes the demo a precursor of the final rather
than a sibling of it. It also forces the provenance question early.
**Done when** a test posts a sensor-source payload and the decision is byte-identical to
the form path for the same five values.

### A2 — Append-only decision log · S

One JSONL line per decision: timestamp, model version, input hash, band, decision,
rule that fired. No personal data, no free text.
**Why:** the claim "auditable" is currently unproven, and the panel will ask for a record.
**Done when** a test asserts the file grows by exactly one parseable line per request and
that no raw input value is stored.

### A3 — Refusal explanation endpoint · S

`GET /api/why-refused` returning width 4.21, band 0.788, the required reduction (81%
narrower), and the rule id that fired, all computed from the bundle.
**Why:** turns "it refuses" into "it refuses, and here is the number that would change
it" — the strongest five seconds of the demo.

### A4 — Per-feature noise sweep · M, new run

Repeat the sweep one feature at a time: 5 features × 5 levels × 2 arms × 5 seeds.
Output to a **new** file, never merged into `noise_sweep`.
**Why:** converts a limitation into a specification — which sensor needs to be better.
**Done when** the run is separate, labelled, reproducible, and the poster is unchanged.

### A5 — One-command run · S

Dockerfile, or a `run.ps1` that sets `MODEL_DIR` and starts the server.
**Why:** only matters if the demo runs on someone else's machine. Check that first.
**Done when** a clean shell on a second machine reaches `/researcher` in one command.

### A6 — Seeded demo cases · S

Three inputs chosen to exercise three distinct screens: refused-by-width, out-of-range,
and missing-interval.
**Why:** a live demo with typed numbers is where demos fail.

### A7 — Poster completion · S

The open edits in `POSTER_BUILD.md` and `POSTER_CANVA_PROMPT.md`: title word, −0.094,
"Institute" line removal, simulated-noise wording, references.

### A8 — Uganda transfer test · L · only with time

Leave-one-country-out on the 32 Ugandan rows. Phase 3.
**Why deferred:** it cannot be claimed until run, and a badly powered result is worse
than no result. Run it if the schedule allows; otherwise say plainly it is not run.

---

## 7. What not to build

| Temptation | Why not |
|---|---|
| A sixth model | Five were compared; ridge and PLS scored −8.19 and −0.33 spatially. The refusal is an information problem, not a model-selection one |
| Agronomic recommendations | Nothing agronomic was measured; the gate emits no number to advise on; `advice_withheld=True` is the honest default |
| Real authentication | Two audiences, one operator, a demo room. Auth adds a failure mode and protects nothing |
| A database | A JSONL log delivers the audit value at a fraction of the risk |
| More UI polish | The evidence is the product. Polish without A1–A3 buys nothing at assessment |

---

## 8. Decisions required from you

1. **Does the final include hardware?** If yes, A1 is mandatory and phase 4 needs a BOM
   and a sampling protocol before any code. If no, the final is a decision service and
   the poster should stop implying a probe.
2. **Per-feature sweep (A4) — run it?** It is the cheapest new evidence available and the
   only one that yields a sensor requirement.
3. **Uganda test (A8) — attempt or defer?** Deferring is defensible; a thin result is not.
4. **Title word** — Robustness or Tolerance. This is now blocking the poster, not the
   prototype.
5. **Demo machine** — yours, or the panel's? Determines whether A5 jumps the queue.

---

## 9. Risks and prepared answers

| Question you will be asked | Answer that holds |
|---|---|
| "So it does not work?" | It works and refuses: 88.8% coverage, and width 4.21 against a 0.788 band. It declines rather than guesses |
| "Where is the hardware?" | Phase 4. This prototype defines the contract that probe will post to, which is why the ingest path exists before the probe does |
| "Why not give farmers advice?" | Nothing agronomic was measured, and there is no number to advise on. The referral to a laboratory is the recommendation |
| "Isn't one model enough?" | Five were compared; the spread is small and the failure is shared, so the model is not the lever — the input information is |
| "Can I reproduce this?" | `python -m pytest` (349 tests) and the bundle hash; results regenerate to zero difference |

---

## 10. Reproduction

```text
python -m pytest -q
python -c "import json;d=json.load(open('export_afsis_real/results.json'));print(d['model_version'])"
python afsis_experiment.py --help
MODEL_DIR=export_afsis_real python soil_api.py --host 0.0.0.0
```

Figures quoted in this document come from `export_afsis_real/results.json`,
`cv_supplement.json`, `bands.json` and `model_meta.json`. The scorecard in section 3 is a
judgement, not a measurement, and is scored equally across dimensions.

---

## Verdict

**The prototype meets its own five-part definition and does not yet meet the demo-to-final
demand.** The scientific half is finished and reproducible; the operational half is a
running demonstration with no input contract, no audit trail and no packaging.

Three actions close most of the distance — A1, A2, A3 — and all three are small. Nothing
on that list requires a new model, new data or a new claim.
