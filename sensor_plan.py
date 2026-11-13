"""
What sensors this project needs, and how good each one has to be.

Why this module and not a hand-written list
-------------------------------------------
"How accurate does the pH meter have to be?" has an answer in the artefact
already on disk, and a hand-written list would not carry it.  The bundle
records a noise sweep: error was added to every input, as a fraction of that
input's spread, and the model was re-scored at each level.  The break-even is
the level at which the model stopped beating a field mean.  Multiply that
fraction by each input's own spread and the result is a ceiling on the error
that input may carry - in the input's own units.

So every tolerance in `SENSORS.md` is arithmetic on two stored fields, and the
document names both.  Change the model and the document changes with it; a
figure edited by hand into the text would survive the change and be wrong.

What this module deliberately does not do
-----------------------------------------
It does not rank the inputs.  The bundle records no importance ordering, and a
budget allocated by guesswork would look exactly like a budget allocated by
evidence.  It also does not measure anything: `results.json` carries no
measured instrument error, and the document says so in the section where a
reader would expect a measurement.

    python sensor_plan.py                # the document, to stdout
    python sensor_plan.py --write        # write SENSORS.md
    python sensor_plan.py --check        # exit 1 if SENSORS.md is out of date
    python sensor_plan.py --json         # the derived figures, for a test

The default bundle is `export_afsis_real`, not `MODEL_DIR`: this document is
about the project's real-data bundle, and a tolerance derived from the
synthetic stand-in would be a number about a generated dataset.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

DEFAULT_MODEL_DIR = Path("export_afsis_real")
DOCUMENT = Path("SENSORS.md")
BEGIN = "<!-- sensors:begin -->"
END = "<!-- sensors:end -->"

SIG = 3          # significant figures the tolerance is floored to
SPREAD_SIG = 4   # significant figures the sample spread is printed to
DASH = "\u2014"   # what a table cell says when the bundle has no figure


# ---------------------------------------------------------------------------
# The judgement: which quantity, which instrument, and whether a field probe
# can deliver it at all.  These are engineering claims, not derivations; every
# figure beside them is derived and printed separately.
# ---------------------------------------------------------------------------

FIELD_ROWS = (
    dict(feature="pH_H2O",
         quantity="Soil reaction (pH)",
         instrument="Glass electrode pH meter with temperature compensation",
         requirement=("Read in a 1:2.5 soil:water suspension, stirred and then "
                      "settled, at the same depth and the same settling time "
                      "every visit."),
         note=("A meter read straight into moist soil measures something else. "
               "The suspension is what makes two readings comparable.")),
    dict(feature="EC",
         quantity="Electrical conductivity",
         instrument="Conductivity cell, temperature-compensated to 25 \u00b0C",
         requirement=("Read in the same suspension as pH, at the same soil:water "
                      "ratio. Conductivity scales with the ratio, so a different "
                      "ratio is a different measurement."),
         note=("Reported per length of extract (dS/m). A reading in \u00b5S/cm is "
               "the same quantity at another scale - check it before entering it.")),
)

LAB_ROWS = (
    dict(features=("Clay percent", "Sand percent", "Silt percent"),
         quantity="Particle-size distribution (clay, sand, silt)",
         instrument=("Particle-size analysis in a laboratory: hydrometer or "
                     "pipette, on dispersed soil"),
         requirement=("One analysis reports all three as shares of the same "
                      "sample, and they should sum to about 100."),
         note=("A hand texture estimate in the field is a description, not a "
               "share in per cent, and cannot be entered as one.")),
)

# The rows that make the list worth trusting: what is deliberately absent, and
# why.  A list of what to buy that does not say what not to buy invites both.
ABSENT_ROWS = (
    dict(quantity="Soil moisture",
         why=("The check does not take moisture. The farmer card compares it as a "
              "word between visits, which needs a judgement, not an instrument.")),
    dict(quantity="Soil temperature",
         why="Not an input of this build, and not needed to read the five that are."),
    dict(quantity="Soil carbon",
         why=("No field instrument in this build measures it. Carbon is estimated "
              "from the five inputs, and a laboratory measurement is the only "
              "direct value - which is why the check sends a farmer to one "
              "whenever it is unsure.")),
)


# ---------------------------------------------------------------------------
# Reading the artefacts
# ---------------------------------------------------------------------------

def _f(x):
    """float or None - never NaN, never a string."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v and abs(v) != float("inf") else None


def floor_sig(x, sig: int = SIG):
    """
    Round DOWN to `sig` significant figures.

    Down, not nearest: a requirement rounded up is a requirement an instrument
    may just miss, and this document exists to say what an instrument must
    clear.  0.5076855 -> 0.507, 4.858651 -> 4.85.
    """
    if x is None or not math.isfinite(x) or x <= 0:
        return None
    step = 10.0 ** (math.floor(math.log10(x)) - (sig - 1))
    return round(math.floor(round(x / step, 9)) * step, 12)


def load(model_dir: Path) -> tuple[dict, dict]:
    """(results, meta) - the two files a tolerance can be derived from."""
    results = json.loads((model_dir / "results.json").read_text())
    meta = json.loads((model_dir / "model_meta.json").read_text())
    return results, meta


def break_even(results: dict):
    """
    The lowest added-error level at which the model was no better than a mean.

    The sweep reports one figure per arm.  Either arm failing is enough to fail,
    so the smallest is the one a requirement has to satisfy.  None when the
    sweep never reached a break-even - at which point no ceiling can be derived
    and the document says so rather than borrowing one.
    """
    figs = (results.get("headline") or {}).get("break_even_noise") or {}
    values = [_f(v) for k, v in figs.items() if k != "model"]
    values = [v for v in values if v is not None and v > 0]
    return min(values) if values else None


def tolerances(results: dict, meta: dict) -> list[dict]:
    """
    One row per input the tool takes: its spread, and the ceiling on its error.

    `tolerance_exact` is the arithmetic; `tolerance` is the figure printed, which
    is `tolerance_exact` floored.  Both are kept so a test can hold the document
    to the rounding rule rather than to a number.
    """
    fraction = break_even(results)
    rows = []
    for name in meta.get("feature_names") or results.get("features") or []:
        rng = (results.get("feature_ranges") or {}).get(name) or {}
        sd = _f(rng.get("sd"))
        exact = fraction * sd if (fraction is not None and sd is not None) else None
        rows.append(dict(
            feature=name,
            unit=(results.get("feature_units") or {}).get(name),
            bounds=(results.get("feature_bounds") or {}).get(name),
            p5=_f(rng.get("p5")), median=_f(rng.get("median")), p95=_f(rng.get("p95")),
            sd=sd,
            fraction=fraction,
            tolerance_exact=exact,
            tolerance=floor_sig(exact),
            has_ceiling=exact is not None,
        ))
    return rows


def plan(results: dict, meta: dict) -> dict:
    """Everything the document is built from, in one dict."""
    rows = tolerances(results, meta)
    by_feature = {r["feature"]: r for r in rows}
    return dict(
        model_version=meta.get("model_version"),
        data_version=meta.get("training_data_version"),
        n_rows=meta.get("n_rows"),
        target_name=meta.get("target_name"),
        target_units=meta.get("target_units"),
        fraction=break_even(results),
        sig=SIG,
        rows=rows,
        field=[dict(row, ceiling=by_feature.get(row["feature"])) for row in FIELD_ROWS
               if row["feature"] in by_feature],
        lab=[dict(row, ceilings=[by_feature[f] for f in row["features"]
                                 if f in by_feature]) for row in LAB_ROWS
             if any(f in by_feature for f in row["features"])],
        absent=[dict(r) for r in ABSENT_ROWS],
        instruments=len(FIELD_ROWS) + len(LAB_ROWS),
        quantities=len(rows),
        measured_sensor_error=(results.get("results") or {}).get("measured_sensor_error"),
    )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _g(x, sig: int = SPREAD_SIG) -> str:
    """A stored figure, at a fixed number of significant figures."""
    return "" if x is None else f"{float(x):.{sig}g}"


WORDS = {0: "no", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
         6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}


def _word(n) -> str:
    """'five quantities' reads better than '5 quantities' in a sentence."""
    return WORDS.get(n, str(n))


def _shopping(p: dict) -> list[str]:
    """The list itself: one line per thing that has to be obtained."""
    out = ["| # | What | Covers | Ceiling on its error |",
           "| --- | --- | --- | --- |"]
    for i, row in enumerate(p["field"], start=1):
        out.append(f"| {i} | {row['instrument']} | {row['quantity']} | "
                   f"{_ceil(row['ceiling'])} |")
    for j, row in enumerate(p["lab"], start=len(p["field"]) + 1):
        ceilings = " / ".join(_tol_num(c["tolerance"]) for c in row["ceilings"]
                              if c.get("tolerance") is not None) or "not derived"
        unit = _unit(row["ceilings"][0]) if row["ceilings"] else ""
        out.append(f"| {j} | {row['instrument']} | {row['quantity']} | "
                   f"{ceilings}" + (f" {unit}" if unit else "") + " |")
    return out


# A unit the bundle records, said in the words a requirement is written in.
# Only the two that would otherwise be misread are renamed: "dimensionless"
# beside a ceiling of 0.507 says nothing to anyone, "pH units" does, and a
# texture share is a share of a sample, not a per-cent of anything measured.
UNIT_WORDS = {"dimensionless": "pH units",
              "percent (g/100 g)": "percentage points"}


def _unit(row) -> str:
    """The unit of one row, in words."""
    unit = (row or {}).get("unit") or ""
    return UNIT_WORDS.get(unit, unit)


def _tol_num(x) -> str:
    """
    A floored ceiling at the number of places its three figures occupy.

    3.2 and 3.20 are the same number; the second says the figure is three
    significant figures and not one, which is the whole point of the column.
    """
    if x is None or x <= 0:
        return "not derived"
    dp = max(0, -(math.floor(math.log10(x)) - (SIG - 1)))
    return f"{float(x):.{dp}f}"


def _ceil(row) -> str:
    """The printed ceiling with its unit: '0.507 pH units', '4.85 percentage points'."""
    if not row or row.get("tolerance") is None:
        return "not derived"
    unit = _unit(row)
    return _tol_num(row["tolerance"]) + (f" {unit}" if unit else "")


def _table(rows: list[dict]) -> list[str]:
    head = ["| Quantity | Unit | Sampled soils (5th \u2013 95th) | Spread | Ceiling on error |",
            "| --- | --- | --- | --- | --- |"]
    body = []
    for r in rows:
        span = (f"{_g(r['p5'])} \u2013 {_g(r['p95'])} (median {_g(r['median'])})"
                if r["p5"] is not None else "not recorded")
        body.append(f"| {r['feature']} | {r['unit'] or DASH} | {span} | "
                    f"{_g(r['sd'])} | {_ceil(r)} |")
    return head + body


def render(p: dict) -> str:
    """The document, from the plan.  Deterministic: no date, no clock."""
    out: list[str] = []
    add = out.append

    add(BEGIN)
    add("<!-- Generated by sensor_plan.py from the model bundle. Do not edit")
    add("     between these markers: run `python sensor_plan.py --write` and")
    add("     review the diff. Every figure below is derived. -->")
    add("")
    add("# Sensors this project needs")
    add("")
    add("## The short answer")
    add("")
    add(f"{_word(len(p['field'])).capitalize()} field instruments and "
        f"{_word(len(p['lab']))} laboratory method cover the "
        f"{_word(p['quantities'])} quantities the check takes. Soil carbon itself has "
        f"no sensor here: it is estimated from those quantities, which is why "
        f"each one has to be good enough to be worth carrying.")
    add("")
    add("| | |")
    add("| --- | --- |")
    add(f"| Field instruments | {len(p['field'])} |")
    add(f"| Laboratory methods | {len(p['lab'])} |")
    add(f"| Quantities covered | {p['quantities']} |")
    add("")
    add(f"{_word(p['instruments']).capitalize()} things have to be obtained:")
    add("")
    out.extend(_shopping(p))
    add("")

    add("## 1. The quantities, and the ceiling on the error each may carry")
    add("")
    out.extend(_table(p["rows"]))
    add("")
    if p["fraction"] is None:
        add("> No ceiling is printed because the noise sweep never reached a "
            "break-even for this bundle: even at the largest error it tried, the "
            "check still beat a field mean. That says nothing about error beyond "
            "that point, so no requirement can be derived from it.")
        add("")

    add("## 2. Where a ceiling comes from")
    add("")
    add("The bundle records a noise sweep. Error was added to every input at "
        "once, as a fraction of that input's spread, and the check was re-scored "
        "on soils it had not seen at each level. The break-even is the lowest "
        "level at which it was no better than a field mean - the level at which "
        "it stopped adding anything.")
    add("")
    if p["fraction"] is not None:
        add(f"For this bundle that level is **{p['fraction']:g}** of the spread. "
            f"Multiplied by each input's own spread it gives a ceiling in that "
            f"input's own units:")
        add("")
        add("```")
        add("ceiling = break-even fraction x spread(feature)")
        add("```")
        add("")
        add("Three things follow, and all three matter:")
        add("")
        add("1. **The ceilings are a shared budget, not five separate limits.** "
            "The sweep added error to every input at the same time. An instrument "
            "well inside its ceiling on one quantity buys no headroom on another, "
            "and sitting every instrument exactly on its ceiling puts the check "
            "at the point where it has nothing left to say.")
        add("2. **A ceiling is a floor for usefulness, not a target.** Above it the "
            "check is no better than the average of the soils it was built on. "
            "Comfortably below it is the requirement; at it is a failure.")
        add("3. **These figures are rounded down** to three significant figures, "
            "never up, because a requirement rounded up is one an instrument may "
            "just miss. The farmer card prints the same half-spread figure "
            "rounded to the nearest digit, so the two can differ in the last "
            "place; the tighter of the two is the requirement.")
        add("")

    add("## 3. How each one is used")
    add("")
    add("### 3.1 Field instruments")
    add("")
    for row in p["field"]:
        add(f"**{row['quantity']}** - {row['instrument']}")
        add("")
        add(f"- Ceiling: {_ceil(row['ceiling'])}")
        add(f"- How it is read: {row['requirement']}")
        add(f"- Note: {row['note']}")
        add("")
    add("### 3.2 Laboratory methods")
    add("")
    for row in p["lab"]:
        add(f"**{row['quantity']}** - {row['instrument']}")
        add("")
        ceilings = ", ".join(_ceil(c) for c in row["ceilings"]) or "not derived"
        add(f"- Ceilings: {ceilings}")
        add(f"- How it is read: {row['requirement']}")
        add(f"- Note: {row['note']}")
        add("")
    add("### 3.3 Not on the list")
    add("")
    for row in p["absent"]:
        add(f"- **{row['quantity']}** - {row['why']}")
    add("")

    add("## 4. What the instrument choice forces on the protocol")
    add("")
    add("A ceiling says how good an instrument has to be. It does not stop a good "
        "instrument being used two ways, which would read as a change in the soil. "
        "The requirements above therefore carry four conditions:")
    add("")
    add("1. **One suspension, one ratio.** pH and conductivity are read in the same "
        "soil:water suspension at the same ratio. Changing the ratio changes both "
        "readings, and conductivity changes by more.")
    add("2. **Calibrate before a session, not after a problem.** Buffer solutions "
        "for pH, a standard solution for conductivity, at the temperature the "
        "instrument compensates to.")
    add("3. **Record the field, the spot and the date with every reading.** The "
        "check compares a reading with the previous one on the same soil; a "
        "reading with no field and no date cannot be compared with anything.")
    add("4. **Sample the field the way it is.** Five to eight spots, mixed, away "
        "from paths and edges. One probe reading at one spot is one spot.")
    add("")

    add("## 5. What this list does not establish")
    add("")
    add("- **No instrument was used.** The ceilings come from a simulation on "
        "laboratory measurements. `results.json` carries no measured instrument "
        "error, and nothing here should be read as one.")
    add("- **The spread is the spread of the soils, not of repeat readings.** A "
        "sensor that is consistent but offset reads inside these ceilings and "
        "still shifts every reading. Nothing here catches that; a calibration "
        "check does.")
    add("- **The inputs are not ranked.** The bundle records no ordering of how "
        "much each input carries, so this document does not spend the budget for "
        "you.")
    add("- **It says nothing about cost, availability in the field, or robustness.** "
        "Those decide what is bought; these figures only decide what is adequate.")
    add("- **A ceiling is measured against a field mean, not against a laboratory "
        "value.** Staying inside it keeps the check better than an average. It is "
        "not a promise of accuracy, and it is not a substitute for a laboratory "
        "test when one is called for.")
    add("")

    add("## 6. Where the figures came from")
    add("")
    add("| | |")
    add("| --- | --- |")
    add(f"| Bundle | `{p['model_version']}` |")
    add(f"| Training data | `{p['data_version']}` |")
    add(f"| Rows | {p['n_rows'] if p['n_rows'] is not None else 'not recorded'} |")
    add(f"| Target | {p['target_name']} ({p['target_units']}) |")
    add("| Spread | `results.json` \u2192 `feature_ranges.<feature>.sd` |")
    add("| Break-even | `results.json` \u2192 `headline.break_even_noise`, smallest arm |")
    add("| Measured instrument error | "
        + ("recorded" if p["measured_sensor_error"] else "**not measured**") + " |")
    add("")
    add(END)
    return "\n".join(out).rstrip("\n") + "\n"


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def _normalise(text: str) -> str:
    """Newline convention is not content: LF and CRLF compare equal."""
    return text.replace("\r\n", "\n").strip()


def main(argv=None) -> int:
    # The document carries an en dash and a degree sign.  A Windows console
    # still defaults to a legacy code page, and printing must not be the thing
    # that fails when the document is fine.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):                        # pragma: no cover
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--model-dir", default=str(DEFAULT_MODEL_DIR),
                    help=f"bundle to derive from (default: {DEFAULT_MODEL_DIR})")
    ap.add_argument("--write", action="store_true", help=f"write {DOCUMENT}")
    ap.add_argument("--check", action="store_true",
                    help=f"exit 1 if {DOCUMENT} differs from a fresh render")
    ap.add_argument("--json", action="store_true", help="print the derived figures")
    args = ap.parse_args(argv)

    model_dir = Path(args.model_dir)
    if not (model_dir / "results.json").is_file():
        print(f"no bundle at {model_dir} (results.json missing)", file=sys.stderr)
        return 2

    p = plan(*load(model_dir))
    text = render(p)

    if args.json:
        print(json.dumps({k: v for k, v in p.items() if k != "rows"} |
                         {"rows": p["rows"]}, indent=2, default=str))
        return 0

    if args.write:
        DOCUMENT.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {DOCUMENT} from {model_dir}")
        return 0

    if args.check:
        if not DOCUMENT.is_file():
            print(f"{DOCUMENT} is missing; run --write", file=sys.stderr)
            return 1
        if _normalise(DOCUMENT.read_text(encoding="utf-8")) != _normalise(text):
            print(f"{DOCUMENT} is out of date with {model_dir}; run --write "
                  f"and review the diff", file=sys.stderr)
            return 1
        print(f"{DOCUMENT} matches {model_dir}")
        return 0

    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
