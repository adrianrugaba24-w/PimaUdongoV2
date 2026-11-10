"""
The farmer view: the same result, said without a single technical word.

Why this module exists
----------------------
The dashboard says "spatial CV R2 0.086, 90 % interval 4.21 wide, coverage
0.888".  None of that belongs on a screen for someone holding a soil sample.
The numbers do not change - they are exactly the numbers the researcher view
shows - but the words do, and the words are the part that goes wrong quietly.

So all of the prose lives here, in one file, in Python, attached to the
payload the API returns.  The page renders what it is given and writes none of
its own, which is what makes the test in `tests/test_farmer_view.py` able to
say something true: it walks every string in the payload and every string in
the page's farmer block, and fails on the first banned word it meets.

What is banned
--------------
`BANNED_TERMS` is the list from the brief, plus the words that would leak the
same ideas through a different door ("model", "error", "feature", "metric").
Matching is case-insensitive and prefix-based, so "folds" and "folded" are
caught by "fold".  `find_banned()` is the single implementation; the tests and
the build both use it, so there is no second opinion about what is banned.

What is not here
----------------
No number is typed.  Every figure in the payload is read from `/api/metrics`,
which reads it from a file.  Two figures are arithmetic on published fields
(the position of the estimate inside the range bar) and the payload says so in
`sources`.

No advice, and no imperative verbs.  The "next step" is a statement about what
would settle the question, not an instruction.
"""
from __future__ import annotations

import re
from typing import Iterator

# ---------------------------------------------------------------------------
# The banned-terms list.  This is config: edit it here, not at a call site.
# ---------------------------------------------------------------------------

BANNED_TERMS = (
    # from the brief
    "R2", "RMSE", "MAE", "RPIQ", "CV", "fold", "conformal", "interval",
    "coverage", "baseline", "noise", "sweep", "hash", "sha256", "pipeline",
    "spatial CV", "training range",
    # the same ideas arriving through another word
    "model", "error", "metric", "feature", "regression", "residual",
    "correlation", "quantile", "percentile", "tercile", "calibration",
    "statistical", "significance", "sample size", "variance", "standard deviation",
    # the target must be called soil carbon on these screens
    "total carbon", "SOC", "organic carbon", "carbon stock",
)

# Words that are allowed only because the copy never uses them; kept separately
# so a reviewer can see which list a new word belongs on.
SOFT_BANNED = ("estimate", "range", "average", "measurement", "reading")

_CAMEL_SAFE = {"R2": r"r\s*[²2](?![0-9])"}
_SUFFIX = r"\w*"


def _pattern(term: str) -> re.Pattern:
    if term in _CAMEL_SAFE:
        return re.compile(_CAMEL_SAFE[term], re.IGNORECASE)
    if term == "SOC":
        return re.compile(r"\bsoc\w*", re.IGNORECASE)
    return re.compile(r"\b" + re.escape(term) + _SUFFIX, re.IGNORECASE)


PATTERNS = {t: _pattern(t) for t in BANNED_TERMS}


def find_banned(text: str) -> list[str]:
    """Which banned terms appear in this string. Empty list means clean."""
    if not isinstance(text, str):
        return []
    return [term for term, pat in PATTERNS.items() if pat.search(text)]


def iter_strings(obj, path: str = "$") -> Iterator[tuple[str, str]]:
    """Every string value in a JSON-shaped object, with the path it sits at."""
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from iter_strings(v, f"{path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            yield from iter_strings(v, f"{path}[{i}]")


# ---------------------------------------------------------------------------
# The words.  Plain, short, one idea at a time.
# ---------------------------------------------------------------------------

TARGET_LABEL = "Soil carbon"
TARGET_EXPLAINER = ("Soil carbon is the carbon held inside the soil. Darker "
                    "soils usually hold more of it.")

TOO_UNCERTAIN = "This estimate is too uncertain to place the soil."

# Traffic light.  Every entry carries an icon AND words, because a colour on
# its own is not a signal to everyone who has to read it.
LIGHTS = {
    "High": dict(key="green", icon="\u2714",
                 words="Clear enough to place the soil",
                 plain="The answer points to one part of our sample."),
    "Medium": dict(key="amber", icon="\u25d0",
                   words="Only partly clear",
                   plain="The answer could sit in more than one part of our sample."),
    "Low": dict(key="red", icon="\u2716",
                words="Not clear enough to place the soil",
                plain="The answer does not point to one part of our sample."),
}

HEADLINES = {
    "R1_no_interval": ("We cannot give a range for these readings.",
                       "The tool did not return a range, so there is nothing to show."),
    "R2_outside_training_range": (
        "This soil is outside the soils this tool was built from.",
        "One of the readings is far from anything in the soil sample behind "
        "this tool, so it cannot say where this soil sits."),
    "R3_no_bands": ("The tool cannot place this soil today.",
                    "The three parts of the sample are not stored for this "
                    "version of the tool, so there is nothing to place it "
                    "against."),
    "R4_too_wide": (TOO_UNCERTAIN,
                    "The range we can defend is wider than a third of the soil "
                    "sample, so it does not point to one part of it."),
    "R5_crosses_one_cut": (TOO_UNCERTAIN,
                           "The range we can defend reaches into two parts of "
                           "the soil sample, so it does not separate them."),
}

NEXT_STEP = dict(
    title="What would settle this",
    body=("A laboratory measurement of a sample from the same spot is the only "
          "way to know the carbon in this soil. That result is the number worth "
          "keeping, whatever this estimate says."),
    how_to_read=("The bar shows the whole range we can defend, not a single "
                 "answer. A wider bar means the tool is less sure."),
    lab_note=("A soil test from a recognised laboratory reports soil carbon as "
              "per cent of the sample."),
)

LEARN_MORE = dict(
    title="Learn more",
    visible=False,
    reason=("This panel stays hidden until published references are supplied. "
            "It will name its sources or it will stay shut."),
)

# Shown when the request itself fails.  It lives here rather than in the page so
# that the failure message is scanned for banned terms like every other string.
FAILURE = dict(
    headline="The answer could not be worked out for this soil.",
    sub=("The tool did not return an answer. The readings are unchanged and "
         "nothing was saved."),
)

# The entry gate.  It looks like a sign-in and behaves like a door: any name and
# any password opens it, nothing is sent anywhere, nothing is stored and there is
# no check.  The page says exactly that above the two buttons.
LOGIN = dict(
    label="Demo only",
    title="Soil carbon demo",
    lead="This tool gives one answer about the carbon in one soil sample.",
    body=("This is a demonstration. Any name and any password will let you in. "
          "Nothing is stored and no sign-in is checked."),
    username_label="Name",
    password_label="Password",
    farmer_action="Sign in to the farmer view",
    farmer_note=("One answer, one bar and one next step, with no technical "
                 "words."),
    farmer_href="/farmer",
    researcher_action="Sign in to the researcher view",
    researcher_note=("Every chart, table and number that sits behind that "
                     "answer."),
    researcher_href="/researcher",
)

NAV = dict(back_to_farmer="Farmer",
           researcher="For researchers",
           researcher_href="/researcher",
           start="Start again",
           start_href="/")

# Field labels.  Keyed by the bundle's own feature names; anything unknown
# falls back to a neutral label and is marked, rather than inventing a meaning.
FIELD_COPY = {
    "pH_H2O": dict(label="Acidity",
                   hint="The acidity number from a soil test."),
    "EC": dict(label="Salts",
               hint="The salt reading from a soil test."),
    "Clay percent": dict(label="Clay",
                         hint="The clay share of the soil."),
    "Sand percent": dict(label="Sand",
                         hint="The sand share of the soil."),
    "Silt percent": dict(label="Silt",
                         hint="The silt share of the soil."),
}
FALLBACK_FIELD = dict(label="A soil measurement",
                      hint="One of the numbers the tool needs.")


def _pct(value, lo, hi):
    span = (hi - lo) or 1.0
    return round(100.0 * (value - lo) / span, 1)


def _banned_guard(text: str) -> str:
    """
    Last line of defence: if a string somehow carries a banned term, this raises
    at build time instead of shipping the word to a farmer's screen.
    """
    hits = find_banned(text)
    if hits:
        raise ValueError(f"farmer copy contains banned terms {hits}: {text!r}")
    return text

def _unit_words(metrics: dict) -> str:
    """
    The unit said out loud.

    The bundle records "percent (g/100 g)"; a farmer screen says "per cent".
    Nothing is converted: this is the same measurement under a readable name,
    and the researcher view still prints the full unit.
    """
    target = metrics.get("target") or {}
    if target.get("unit_short") == "%":
        return "per cent"
    return target.get("unit") or ""


def _form(metrics: dict) -> dict:
    """
    The five real inputs, under plain names.

    A feature the copy does not know is labelled neutrally and flagged, so a
    future bundle adds an input instead of silently borrowing another one's
    meaning.
    """
    fields = []
    for f in metrics.get("features") or []:
        name = f.get("name")
        copy = FIELD_COPY.get(name) or FALLBACK_FIELD
        rng = f.get("training_range") or {}
        bounds = f.get("physical_bounds") or [None, None]
        fields.append(dict(
            name=name,
            label=copy["label"],
            hint=copy["hint"],
            # A hint of the usual value, not a default.
            placeholder=rng.get("median"),
            lowest=bounds[0] if len(bounds) > 0 else None,
            highest=bounds[1] if len(bounds) > 1 else None,
            handbook=name in FIELD_COPY,
        ))
    return dict(
        title="The soil test numbers",
        hint=("These are the numbers a soil test gives. The tool needs all of "
              "them, and reads them only for this one answer."),
        submit="Show the answer",
        fields=fields,
    )


def _break_even_values(metrics: dict) -> list[float]:
    """Finite break-even figures, one per arm of the test, from the metrics."""
    be = (metrics.get("noise") or {}).get("break_even") or {}
    out = []
    for key, value in be.items():
        if key == "model":
            continue
        try:
            f = float(value)
        except (TypeError, ValueError):
            continue
        if f == f and abs(f) != float("inf"):
            out.append(f)
    return out


def _sensor(metrics: dict) -> dict:
    """
    "Is my sensor good enough?" in plain words.

    The figure is read from the metrics payload, which reads it from the
    results file; no copy in this module quotes a number.  If the test never
    reached a break-even point, the card says exactly that rather than
    implying a sensor is or is not adequate - adequacy depends on the
    instrument, and this project has not measured one.
    """
    be = (metrics.get("noise") or {}).get("break_even") or {}
    arms = [k for k in be if k != "model"]
    values = _break_even_values(metrics)
    card = dict(
        title="Is my sensor good enough?",
        value=None,
        values=values,
        unit_words="of the normal spread of a reading",
        available=False,
        tests_run=len(arms),
    )
    if not arms:
        card.update(
            headline="This card has nothing to show for this version.",
            body=("The sensor test is not stored for the version of the tool "
                  "you are using."),
            finding="not_recorded")
        return card
    if not values:
        card.update(
            available=False,
            headline="Our test never found the point where the tool stopped working.",
            body=("Even at the largest amount of added mistakes we tried, the "
                  "tool still beat a plain average. The test says nothing about "
                  "amounts beyond that point."),
            finding="never_reached")
        return card
    lo, hi = min(values), max(values)
    same = len({round(v, 12) for v in values}) == 1
    card.update(
        available=True,
        value=hi if same else None,
        low=lo,
        high=hi,
        same=same,
        headline="Our test found the point where the readings stop being useful.",
        body=("We added mistakes to the readings on purpose and watched what "
              "happened. The tool still beat a plain average until the mistakes "
              "reached the amount below."),
        finding="found",
    )
    return card


def _bar(metrics: dict, prediction: dict) -> dict | None:
    """
    The range bar, in percentages of a fixed axis.

    The axis is the observed range of the target in this bundle, widened to
    include the interval when the interval runs past it.  Every position is
    arithmetic on two numbers the payload already carries.
    """
    iv = prediction.get("interval") or {}
    lo, hi = iv.get("low"), iv.get("high")
    est = prediction.get("prediction")
    for v in (lo, hi, est):
        if v is None:
            return None
    obs = (metrics.get("bands") or {}).get("observed_range") or [lo, hi]
    scale_min = min(float(obs[0]), float(lo))
    scale_max = max(float(obs[1]), float(hi))
    if scale_max <= scale_min:
        scale_max = scale_min + 1.0
    return dict(
        low=float(lo), high=float(hi), estimate=float(est),
        scale_min=scale_min, scale_max=scale_max,
        low_pct=_pct(float(lo), scale_min, scale_max),
        high_pct=_pct(float(hi), scale_min, scale_max),
        estimate_pct=_pct(float(est), scale_min, scale_max),
        caption=("The shaded part is the whole range we can defend. The line "
                 "is our single best answer."),
        # Spoken description, assembled by the page from these fragments so the
        # sentence itself is written and scanned here.
        aria_template=("Our range runs from {low} to {high} {unit}. "
                        "Our single best answer is {estimate}."),
        source=("positions are arithmetic on the range and the lowest and "
                "highest soil carbon in the sample"),
    )


def result_block(metrics: dict, prediction: dict) -> dict:
    """
    One result screen: headline, bar, light, next step.

    The headline for a range that crosses a boundary, or that is wider than one
    third of the sample, is fixed: the estimate is too uncertain to place the
    soil.  It is not softened, and it is not rounded into something that sounds
    like an answer.
    """
    band = prediction.get("band") or {}
    rules = list(band.get("rules") or [])
    confidence = band.get("confidence") or "Low"
    light = dict(LIGHTS.get(confidence) or LIGHTS["Low"])

    if "R6_single_band" in rules:
        label = band.get("band") or ""
        headline = (f"This soil sits in the {label.lower()}."
                    if label else
                    "This soil sits in one part of our soil sample.")
        sub = ("Our soil sample is split into three equal parts. This soil sits "
               "in one of them.")
    else:
        key = next((r for r in rules if r in HEADLINES), "R1_no_interval")
        headline, sub = HEADLINES[key]

    return dict(
        headline=headline,
        sub=sub,
        bar=_bar(metrics, prediction),
        light=light,
        unit_words=_unit_words(metrics),
        next_step=dict(NEXT_STEP),
        caveat=("This is an estimate from five numbers. It is not a soil test "
                "and it is not a rating of the soil."),
    )


def build(metrics: dict, prediction: dict | None = None) -> dict:
    """The whole farmer payload. Raises if any string carries a banned term."""
    target = metrics.get("target") or {}
    view = dict(
        schema_version=1,
        view="farmer",
        target=dict(
            label=TARGET_LABEL,
            explainer=TARGET_EXPLAINER,
            unit_words=_unit_words(metrics),
            notice=("This is a test version of the tool, built on stored soil "
                    "data rather than soil from your farm."
                    if target.get("is_sample_data") else
                    "This tool was built on stored soil data from across "
                    "Africa. It has not seen soil from your farm."),
        ),
        nav=dict(NAV),
        form=_form(metrics),
        sensor=_sensor(metrics),
        next_step=dict(NEXT_STEP),
        learn_more=dict(LEARN_MORE),
        failure=dict(FAILURE),
        screens=["form", "result", "sensor"],
        sources=dict(
            note=("Every number on this screen is read from the same files the "
                  "research view uses. Nothing here is typed into the page.")),
    )
    view["result"] = result_block(metrics, prediction) if prediction else None
    # Build-time guard: a banned term never reaches a farmer's screen.
    for _, text in iter_strings(view):
        _banned_guard(text)
    return view


def build_login() -> dict:
    """The entry gate's whole vocabulary. No numbers, so no metrics needed."""
    view = dict(schema_version=1, view="login", login=dict(LOGIN))
    for _, text in iter_strings(view):
        _banned_guard(text)
    return view
