# Canva prompt v2 — editing your existing template, not rebuilding it

Your file `Soil-Health Research Poster.pdf` is A2 portrait, 420 × 594 mm, one page, no
images, Inter 18pt, three columns at roughly x 10–130, 130–250 and 250–410 mm. It already
has the right architecture. So this is an **edit brief**, not a design brief: keep the
template, keep the bars and logo, replace the text that is wrong, and leave three frames
empty for your diagrams.

Start a fresh chat with Canva AI from inside that design, and paste section 2.

---

## 1. What the template already gets right — do not touch

| Column | Sections, top to bottom |
|---|---|
| Left | BACKGROUND · PROBLEM · RESEARCH GAP · AIM · RESEARCH QUESTION · SCOPE |
| Middle | RESEARCH OBJECTIVES · METHODOLOGY (Assemble, Split, Train, Evaluate, Calibrate) · KEY FINDING 0.252 |
| Right | SYSTEM PIPELINE · MAIN RESULTS · ERROR TOLERANCE · LIMITATIONS · CONCLUSION |

That is a stronger narrative than my earlier draft: it argues left to right — why it
matters, what is missing, what was asked, how it was tested, what came out, what it cannot
claim. Keep the order, the labels, the header band, the logo and the palette.

Nine figures in it are already correct and must not be retyped from memory:
`926 · 58 · 16 · 19`, `0.338`, `0.086`, `0.252`, `1.339` vs `1.421`, `0.039`,
`4.21`, `88.8%` vs `90%`.

---

## 2. The prompt (paste into Canva AI with this design open)

```text
Do not redesign this poster. Keep the existing layout, the header band, the logo, the
section bars, the colours and the Inter font exactly as they are. Do not generate,
insert or suggest any image, illustration, icon or photograph. Make only the text edits
listed below, and add the three empty frames described at the end.

Replace the following strings exactly, wherever they appear.

1. "The University of Africa" - delete this line. It is a leftover from the original
template and names the wrong institution.

2. "Adrian Rugaba · [REG NO: TO CONFIRM]" - replace with
   "Adrian Rugaba Asiimwe · S24B23/054"

3. "Department of [TO CONFIRM]" - replace with "Department of Computer Science"

4. "Machine Learning for IoT-Based Soil Health Prediction" - replace with
   "Machine Learning for IoT-Based Soil Health Prediction in Sub-Saharan Africa:
   Spatial Validation and Sensor-Error Tolerance"

5. "-0.095" - replace with "-0.094". The correct value is -0.094.

6. Every occurrence of the word "accuracy" - replace with "skill".

7. "Coverage of 88.8% against a 90% target, with a mean interval width of 4.21. Not
   validated on field sensors or Ugandan farms."
   Replace with:
   "Coverage of 88.8% against a 90% target, but mean interval width of 4.21 against a
   band 0.788 wide: every prediction is refused as too wide. Sensor error is simulated,
   not measured. Not validated on field sensors or Ugandan farms."

8. "Adding noise at 0.25 of the training standard deviation leaves R2 at 0.039; at 0.50
   it falls to -0.094. The model is fragile to sensor error."
   Append: "Noise is simulated on the inputs; sensor error was not measured."

9. In SYSTEM PIPELINE, add a sixth step after "Conformal intervals", labelled
   "Refusal gate".

10. In CONCLUSION, after "...state uncertainty explicitly." append:
    "On this feature set the interval is never narrow enough to name a band, so the
    service declines rather than guessing."

Then add these three empty frames. Each is an outlined rectangle with a caption above
it, and nothing drawn inside. Size each to its column width, about 110 mm, with the
height noted.

a. Under RESEARCH OBJECTIVES in the middle column: 110 x 85 mm, caption
   "Figure 1 - pipeline (to be inserted)"
b. Under MAIN RESULTS in the right column: 110 x 90 mm, caption
   "Figure 2 - interval against bands (to be inserted)"
c. Under METHODOLOGY in the middle column: 110 x 70 mm, caption
   "Figure 3 - model comparison (to be inserted)"

Finally add a reference strip along the bottom of the page, in small type, three lines:
"Breiman, Random forests, Machine Learning 45(1):5-32, 2001."
"Roberts et al., Ecography 40(8):913-929, 2017."
"Ploton et al., Nature Communications 11:4540, 2020."
Beneath them, one line: "Measured AfSIS Phase I data, ODC-By. Sensor error simulated,
not measured."
```

If Canva refuses to edit in place — likely, since its AI prefers to generate a new
design — do it by hand. There are ten replacements; the file takes twenty minutes and
nothing can be silently rewritten.

---

## 3. Section text, corrected, in your template's order

Use these where the edit above needs a whole block rather than a phrase. Line breaks are
part of the layout.

### Left column

```text
BACKGROUND
Laboratory analysis of total carbon from five soil
properties is the standard, but it cannot keep pace
with the number of sites IoT soil-health monitoring
now demands.

PROBLEM
Random splitting mixes nearby sites into training
and test, so the reported skill can be optimistic.

RESEARCH GAP
Evaluations rarely combine a geographically
blocked hold-out with an uncertainty statement
about the prediction. Both are needed before a
model can be trusted on a sensor network.

AIM
Measure how much of the reported skill depends
on spatial structure, and whether the model can
say when it does not have enough evidence.

RESEARCH QUESTION
For total carbon predicted from five laboratory
soil properties, how much skill is lost when
whole areas are held out, and can the model flag
low-confidence predictions?

SCOPE
Random forest, five seeds. Spatial hold-out by
cluster, plus split-conformal intervals.
926 samples · 58 sites · 16 clusters · 19 countries.
```

### Middle column

```text
RESEARCH OBJECTIVES
Quantify the loss under a spatial hold-out.
Compare random and cluster-blocked evaluation.
Calibrate prediction intervals on held-out data.
Test tolerance to simulated sensor error.
State the limits of the evidence clearly.

METHODOLOGY
1 Assemble   926 soil samples from 58 sites across 16
             clusters and 19 countries.
2 Split      Random split for the baseline; whole clusters
             held out for the spatial test.
3 Train      Random forest, five seeds, tuned on the training
             folds only.
4 Evaluate   R2 and RMSE under both splits; RMSE against
             the field mean.
5 Calibrate  Split-conformal intervals on a held-out
             calibration set.

KEY FINDING
0.252        drop in R2 when whole clusters are held out:
             0.338 random → 0.086 spatial.
```

### Right column

```text
SYSTEM PIPELINE
IoT soil sensors → 5 laboratory properties → Random forest model
→ Spatial hold-out test → Conformal intervals → Refusal gate

MAIN RESULTS
R2 by evaluation split
0.338   Random split
0.086   Spatial hold-out
Spatial RMSE 1.339 against 1.421 for predicting the field mean — the model still beats
the naive baseline, but by less than half the margin the random split suggested.

ERROR TOLERANCE
Adding noise at 0.25 of the training standard deviation leaves R2 at 0.039; at 0.50 it
falls to -0.094. The model is fragile to sensor error. Noise is simulated on the inputs;
sensor error was not measured.

LIMITATIONS
Coverage of 88.8% against a 90% target, but mean interval width of 4.21 against a band
0.788 wide: every prediction is refused as too wide. Sensor error is simulated, not
measured. Not validated on field sensors or Ugandan farms.

CONCLUSION
Reported skill is strongly spatially dependent. Before IoT soil-health prediction can be
measured in the field, evaluation must hold out whole regions and state uncertainty
explicitly. On this feature set the interval is never narrow enough to name a band, so
the service declines rather than guessing.
```

---

## 4. What each empty frame is for

| Frame | Column | Size | Contents when you fill it |
|---|---|---|---|
| Figure 1 | Middle, under methodology | 110 × 70 mm | Five linked boxes: data → features → two designs → five models → interval and gate |
| Figure 2 | Right, under main results | 110 × 90 mm | Axis 0–5; band cuts at 0.651 and 1.439; one bar 4.21 long that swallows all three bands |
| Figure 3 | Middle, under objectives | 110 × 85 mm | Bar chart or small table of R² by model under both splits |

They are deliberately empty. Canva AI will want to fill them with stock imagery; the
prompt forbids that, and if it happens, delete and leave the outlined box.

Figure 2 is the one worth drawing by hand, because the arithmetic has to be honest: with
the axis 0 to 5 spanning the frame, the interval bar is 84% of the axis length and the
two cut lines sit at 13% and 29%. Anything shorter would misrepresent the result.

---

## 5. After Canva finishes — five checks

1. **Ten replacements.** Count them. Any survivor is a visible error, especially
   `The University of Africa` and `-0.095`.
2. **No images.** Layers panel should show the logo, the bars, the chart, and three
   empty frames. Nothing else.
3. **The refusal sentence appears twice** — once in LIMITATIONS, once in CONCLUSION. If
   a reviewer asks "what does the system output", those two lines are the answer.
4. **"Simulated, not measured"** appears at least once. This is the single claim most
   likely to be challenged.
5. **References present.** Your template has none; a poster with eight numbers and no
   citations invites the question of where they come from.

---

## 6. Judgement calls I made, and why

- **Tolerance over Robustness.** Your subtitle says "Robustness of reported skill". The
  measured result is a threshold at 0.5 SD and a refusal for every input, which supports
  "tolerance" and not "robustness". If you keep Robustness in the title, keep it out of
  the claims.
- **"Skill" not "accuracy".** For a regression, accuracy is not a defined quantity; the
  poster reports R² and RMSE. Swapping the word costs nothing and removes a soft target
  at question time.
- **No synthetic-data banner.** Your template has none, and you need none: every number
  comes from the measured AfSIS wet chemistry. The only synthetic element is the
  simulated sensor noise, and that is stated twice.
- **The 4.21 width became a headline, not a limitation.** It reads like a weak result
  buried in LIMITATIONS. It is the strongest finding on the page: the system knows when
  to refuse.
