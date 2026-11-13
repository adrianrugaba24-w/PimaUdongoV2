# UI Build Report

**Summary.** The interface is complete enough to demonstrate and to defend: four views, every figure bound to a
generated artefact, every farmer-facing sentence written in one Python file and scanned before it can ship. The
next build is therefore not a redesign from scratch. It is two jobs — closing the honesty gaps recorded but not
yet fixed, and turning four pages that share a look into one system that shares a stylesheet.

---

## 1. The problem

Two audiences with opposite needs are served by one service.

Someone holding a soil sample needs one answer, in plain words, on a phone, without a single technical term.
An examiner needs to audit the same numbers: which validation design produced them, how wide the interval is,
what the model was and was not built on.

The first interface this project shipped failed at exactly that seam. It computed its own prediction in
JavaScript, labelled a spatial score as a random one, and drew a benchmark curve no bundle contains. None of
those were visual faults. Each was a claim the project could not support, dressed as an interface element.

So the interface work since then has not been "make it look better". It has been "make every element
traceable", so that a build can be judged on evidence rather than taste. §11 of `UI_UX_REFERENCE.md` keeps the
rejection list from that review, and it is still the most useful page in the document.

## 2. The solution

A binding contract per element, applied to every view: each displayed value names its source, and each source
states what the element does when it is absent. The rule the four views share is one sentence — *nothing is
displayed that is not in a generated artefact*.

Three decisions make that workable rather than aspirational:

- **The prose lives in Python, not in the page.** Every farmer-facing sentence is written in `farmer_view.py`,
  scanned against a banned-term list, and served as data. The page renders what it is given and writes none of
  its own prose, so a typo cannot appear in a figure and a banned word cannot appear at all.
- **The page bakes no number.** The form, the answer, the advice and the sensor card are all filled from
  `GET /api/farmer` and its two companions. A hard-coded figure survives a re-run and silently becomes false;
  a read figure cannot.
- **Refusal is a rendered state.** When the data cannot support a statement, the interface says so in words —
  a wide interval, an out-of-sample input, a sweep that never reached a break-even. It does not round the
  refusal into an answer.

## 3. Who is affected

| Audience | View | What they need | What must never appear |
|---|---|---|---|
| Someone holding a soil sample | `/farmer` | one answer, a range, a next step, a way to keep the reading | technical words, grades, rates, product names |
| A field session in progress | `/session` | the same numbers in collection order, printable as a sheet | invented sensors, a prediction made in the browser |
| Examiner, supervisor, reviewer | `/researcher` | both validation designs side by side, interval width, noise and sensitivity sweeps | a number that is not in `results.json` |
| Whoever is demonstrating | `/` (entry) | two doors and a plain statement that nothing is checked | a sign-in that looks like security and is not |

## 4. What is under way: the interface as built

### 4.1 The entry gate — `web/login.html`

A landscape drawn as inline SVG behind one translucent panel, two account types on a tab strip, and a single
door. Every sentence on the panel comes from `GET /api/login` except three written into the markup: the
control name on the show/hide button, the standing notice, and the no-script links. Any name and any password
open it, and the page says so above the buttons. It is a door, not a check, and the copy had to be rewritten
once to stop it claiming otherwise.

### 4.2 The farmer view — `web/farmer.html`

One scrolling page in the visual language of the retracted mock: a dark topbar carrying the brand, the
required banner and three pills (for researchers, start again, theme), then panels in a two-column grid that
closes to one column on a phone. The palette is hand-written — the mock's Tailwind and Chart.js are not used —
and none of its computed figures came across.

| Order | Section | What it does | Source |
|---|---|---|---|
| 1 | The soil test | five sliders, each with a value chip, its unit in words, and a typed box | `form.fields[]` |
| 2 | Clay, sand and silt | one bar per share, a total, and a sentence when they miss a hundred | `form.texture`, `form.fields[].share` |
| 3 | The answer | headline, traffic light, range bar, caveat, next step | `result` |
| 4 | Crop question | three cycles; changes what the reading supports | `crop.options[]` |
| 5 | Next steps | a ranked list, asked for on demand | `advice` |
| 6 | Readings over time | keep a reading, compare it with the last one | `strip` |
| 7 | Soil test beside a reading | a nutrient word against a reading | `pairing` |
| 8 | My sensor | the break-even figure, or that it was never found | `sensor` |
| 9 | Guide | ten blocks: what to trust, what to sample, what to do next | `guide.blocks[]` |

Each section is one idea. The traffic light carries an icon and words, never colour alone. The bar's ends read
"Less carbon" and "More carbon" and the figures are spoken in the `aria-label`. Keeping a reading writes one
key to storage and nothing else. The texture panel never fills a field — it is a readout of what was typed,
because a preset texture would be a measurement nobody took.

### 4.3 The session view — `web/session.html`

The same numbers in collection order — session record, five measurements, estimate and its placement, what the
reading can support, and a printable session sheet. It adds no calculation; it arranges the dashboard around a
single submission. It replaced a mock advisor that computed its own answer, kept the mock in `_retired/`, and
records why in §15.1.

### 4.4 The researcher dashboard — `web/index.html`

Headline metric cards, the prediction form with texture-sum validation, the spatial-first score table and
chart, the cleaning ledger, the noise sweep, both block sensitivities, the interval card, the limitations list
and a provenance line. Charts are inline SVG drawn from `results.json`. The synthetic bundle is marked twice —
chip and banner — so a stand-in can never be quoted as a result.

### 4.5 The two later additions

The **ranked next steps** are rule-driven, not model-driven: the engine reads which reliability rules fired and
what the farmer's own record says, ranks uncertainty first and the record last, caps the list and reports what
it held back. The band — a position in a distribution, not a grade — is deliberately not an input, and a test
proves it by handing the engine two placements that differ only in their band.

The **sensor list** is the other side of the same rule. `SENSORS.md` is generated from the bundle: the
break-even fraction multiplied by each input's spread gives a ceiling in that input's own units. Two field
instruments and one laboratory method cover the five quantities; soil carbon is not among them, and the
document says why. Where a bundle recorded no break-even, the document prints that nothing can be derived
rather than borrowing a figure.

## 5. Results so far

**The contract is enforced, not reviewed.** Each of these fails a build rather than a review:

| Guarantee | Held by |
|---|---|
| No banned term on a farmer screen | the payload is scanned as it is built, and the page block is scanned as text |
| No number written into a farmer page | literal-prose and literal-number checks over the page block |
| No colour-only signal | the traffic light test: icon, words, and a class |
| Every route served | a request per address, including the session view, which is one chip on the dashboard away and nowhere else |
| The bundle is the one it claims | hash check at start-up; a mismatched bundle stops the service |
| The sensor document is current | a render-and-compare check against the committed bundle |
| The band is not an input | three tests: by construction, by behaviour, by source |

**Degradation works.** Point the service at a bundle that never reached a break-even and the cards do not go
blank or invent; each says what it could not find. That is the case the synthetic stand-in exists to prove.

**Accessibility was built in, not audited later.** A skip link, live regions on every region that changes,
`aria-busy` while the first render settles, reduced-motion support on the gate, and a print stylesheet on all
three working views. The theme control is on three of the four pages, and each one follows the operating system
until it is pressed.

**What has not been verified: how any of it renders.** The tests assert strings, identifiers and bindings.
No test opens a browser, so layout, focus order under a keyboard, contrast in the dark theme and the behaviour
of the sliders on a real phone are reviewed by hand or not at all. That is the largest gap in this report and
it is the first item in the plan below.

## 6. What comes next

| Priority | Work | Why it matters | Depends on |
|---|---|---|---|
| P0 | One browser pass over all four views at phone and desktop width; record console errors and a screenshot each | the only guarantee currently missing is that it renders | nothing |
| P0 | Close the display-honesty gaps in §13: the clamped prediction, the clamped interval floor, the unexplained negative lower end on the farmer bar | each is a place where a limit is hidden by the way a number is printed | wording decisions for the interval and the negative bound |
| P1 | One shared token sheet, served by the app itself, replacing the copy in each page | four pages carry four copies of the palette; a change made in one drifts in three | nothing |
| P2 | A sample-map panel reading `sites.json` | the only artefact no view reads, and the clearest picture of what spatial validation means | the placement decision in §13 |
| P2 | Print the advice card's basis on screen, from the context the engine already computes | the ranking records what it was allowed to read; the page currently has nothing to show | `build_advice()` forwarding `context_used` |
| P3 | A copy pass with an actual reader of the target level | the reading level is a rule, not a measurement; it has never been tested on a person | access to a reader |

### Gaps found while writing this report

- **Four copies of the design tokens.** Each page carries its own palette, and the farmer palette is not the
  dashboard palette. Nothing enforces that they stay related.
- **The advice card has no state line.** It re-ranks when the crop or the reading changes, but nothing on
  screen says what the current list was worked out from. The engine returns that context as `context_used`,
  and `build_advice()` drops it, so the page has nothing to print.
- **`sites.json` is written and unread**, and the panel that would use it is still an open decision.

Closed since this report was first written: the farmer page now has a print sheet and a theme control, and the
dead tab styles are gone with the shell rebuild. §16.3 of the reference records the one deviation that rebuild
required — the mock's four soil-type presets were not ported, because a preset is a texture nobody measured.

## 7. What the next build must not lose

These are not preferences. Each one exists because removing it produced a specific failure that is written
down in the reference document.

1. **No network beyond the app.** No CDN, no font host, no analytics. The demo has to work on a venue network
   or none.
2. **No number typed into a page.** Structural literals only — axis floors, decimal places, breakpoints.
3. **Farmer prose stays in `farmer_view.py`.** A sentence moved into the markup escapes the scan.
4. **A band is a position, not a grade.** The upper third is the upper third of this dataset, not good soil.
5. **Refuse rather than invent.** If an artefact is missing, the screen says what is missing.
6. **One storage key on the farmer page**, holding the readings and nothing else.
7. **The target is soil carbon.** Never total carbon, never the other abbreviation.
8. **No agronomic advice.** The ranked steps stay on the evidence side: test, sample, re-read, keep, record.

## 8. Where the work lives

| Concern | File |
|---|---|
| The governing document — constraints, binding map, copy rules, open decisions | `UI_UX_REFERENCE.md` |
| All farmer-facing prose and the payload builder | `farmer_view.py` |
| The ranking engine | `recommendation.py` |
| The sensor requirement derivation and the generated list | `sensor_plan.py`, `SENSORS.md` |
| The service and every route | `soil_api.py` |
| The four views | `web/login.html`, `web/farmer.html`, `web/session.html`, `web/index.html` |
| The supplied layout the farmer view was built from | `web/Pima_ soil carbon check.html` |
| The visual language it was restyled to | `_retired/pimaudongo_field_soil_health_agronomic_advisor.mock.html` |
| The retracted mock, kept as evidence | `_retired/` |
| Enforcement | `tests/test_farmer_view.py`, `tests/test_api.py`, `tests/test_recommendation.py`, `tests/test_sensor_plan.py` |

Before any change is merged, §12 of the reference document is the checklist, and the full suite is the gate. A
change that alters copy also needs the farmer-view file; a change that alters a figure needs the document's
binding map updated in the same commit, with the absent-value behaviour stated.
