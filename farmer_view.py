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

No rates, and no product names.  The "next step" is a statement about what
would settle the question.  The short-term card goes one step further and pairs
a soil-test word with a reading, but it still never says how much of anything to
put on a field: a figure like that would need a trial this project has not run,
and the tool's own uncertainty is the reason it does not give one.
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

# ---------------------------------------------------------------------------
# The check, in the order a farmer needs it: what it says, how far to trust it,
# what to do next, and what the words mean.  Every string here passes the same
# banned-term scan as the result screen, so none of it can drift technical.
#
# Two deviations from the supplied layout, both because the page cannot honour
# the original: moisture and temperature are not readings this tool receives,
# so they are not shown as ones; and there is no sensor node, so nothing claims
# a device produced these numbers.
# ---------------------------------------------------------------------------

TRUST = dict(
    title="How much can you trust this check?",
    body="Based on tests on soils the check had not seen before.",
)

GLANCE = dict(
    title="Your soil at a glance",
    lead="The readings you entered for this soil.",
    note=("The check uses the acidity and salt readings and the share of clay, "
          "silt and sand. It does not use moisture or temperature."),
)

LAB_DECISION = dict(
    title="Should I get a laboratory test?",
    lead="Yes, if any of these is true:",
    items=[
        "This check says it is not sure.",
        "You are about to spend money on lime, compost or seed.",
        "A reading looks unusual, or jumps around between readings.",
        "Your crops are doing badly and you do not know why.",
    ],
)

SAMPLING = dict(
    title="How to take a good soil sample",
    steps=[
        "Use a clean spade or trowel. Clear away leaves and surface litter.",
        "Dig a small hole about 20 cm deep and cut a thin slice from one side.",
        ("Repeat at 5 to 8 spots across the field. Avoid paths, field edges "
         "and places where compost or animals have been."),
        "Mix the slices in a clean bucket and take about half a kilogram.",
        ("Put it in a clean bag, label it with your name, field and date, and "
         "take it to the laboratory soon."),
    ],
    note="General guidance. Confirm with your extension officer.",
)

READINGS_MEANING = dict(
    title="What your readings mean",
    items=[
        dict(name="Acidity (pH)",
             body=("How acidic or alkaline the soil is. Most crops grow best "
                   "in slightly acidic to neutral soil. Very acidic or very "
                   "alkaline soil can lock up nutrients.")),
        dict(name="Salt level",
             body=("How much dissolved salt is in the soil. Too much stops "
                   "plants taking up water.")),
    ],
    note="Moisture and temperature are not used by this check.",
)

WHO_HELPS = dict(
    title="Who can help",
    items=[
        "Your district agricultural officer",
        "A local extension worker or farmer group",
        "A university or research laboratory that tests soil",
    ],
    ask=("Ask which test suits your crop, and how to collect and send the "
         "sample."),
)

PRACTICES = dict(
    title="General practices that help soil carbon",
    note="Not based on your reading.",
    items=[
        dict(key="residues", name="Leave crop residues on the field",
             body="They feed the soil and hold moisture."),
        dict(key="mulch", name="Mulch between rows",
             body="It protects the surface from sun and rain."),
        dict(key="rotation", name="Rotate with beans or groundnuts",
             body="Their roots and leaves return carbon and nitrogen."),
        dict(key="compost", name="Add compost or manure where you can",
             body="It adds organic matter to the topsoil."),
    ],
    source_note="Sources to be added before wider use.",
)

ABOUT_CARBON = dict(
    title="What is soil carbon?",
    body=("The carbon held in your soil, mostly from plants and animals that "
          "have broken down. More carbon usually means soil that holds water "
          "and nutrients better."),
)

HOW_SURE = dict(
    title="How sure are we?",
    body=("We estimate carbon from your acidity and salt readings and the "
          "texture of your soil. We tested it on soils it had never seen, and "
          "it is often far off. So it tells you when it is not sure, and in "
          "that case a laboratory test is the answer worth keeping."),
)

WHAT_IS_USED = dict(
    title="What this check uses",
    body=("The acidity and salt readings, and the share of clay, silt and sand "
          "in your soil. Soil carbon cannot be read by a simple sensor, which "
          "is why we estimate it."),
)

GUIDE_TAB = "Help and next steps"

# ---------------------------------------------------------------------------
# The crop question.  A crop cycle changes what a single reading can support,
# not what the tool predicts: the estimate is the same either way.  Nothing
# here rates the soil or names an input to buy, because neither the data nor
# the reliability gate can carry that claim.
# ---------------------------------------------------------------------------

CROPS = dict(
    title="What are you growing?",
    lead=("The answer above is the same either way. What it means for your "
          "next step is not."),
    health_note=("This tool places carbon in our sample. It does not rate the "
                 "soil, and it does not say which crop will do well."),
    practices_note="General practices for this kind of crop, not based on your reading.",
    options=[
        dict(key="annual",
             button="A crop I replant each season",
             name="A crop replanted each season",
             reading=("Each season starts again. One reading shows where this "
                      "soil sits now; it cannot show whether the soil is "
                      "getting better or worse. That needs the same field "
                      "sampled again, at the same point in another season."),
             step=("Take a laboratory sample before changing how the field is "
                   "managed. One reading from this tool is not grounds for a "
                   "change on its own."),
             practices=["residues", "rotation"]),
        dict(key="perennial",
             button="A crop that stays for years",
             name="A crop that stays in the ground for years",
             reading=("A perennial holds the same soil for years, and that soil "
                      "changes slowly. One reading is a starting point. The "
                      "useful comparison is the same field, a year apart, "
                      "sampled the same way."),
             step=("Take a laboratory sample before a decision that is hard to "
                   "undo, such as replanting. Keep the field name and the date "
                   "so the next reading can be set against this one."),
             practices=["mulch", "compost"]),
        dict(key="mixed",
             button="Both, on the same field",
             name="Both, on one field",
             reading=("Where two crops share a field, one reading stands for "
                      "the whole field. It cannot separate the strips, so "
                      "sample like for like if you measure again."),
             step=("Take a laboratory sample for the part of the field you are "
                   "about to change, rather than for the field as a whole."),
             practices=["residues", "mulch", "rotation", "compost"]),
    ],
    idle="Choose one of the three. Nothing is sent until you do.",
)


# The entry gate.  It looks like a sign-in and, for the two accounts printed on
# it, behaves like one: the demo name for a view and the word "demo".  Anything
# else is refused, and the page prints what it accepts before anything is typed,
# so the comparison is against a visible constant rather than a secret.  Nothing
# typed is stored and nothing is sent anywhere.  (The farmer page does keep the
# readings a farmer chooses to keep, in that browser only; this is about the
# sign-in, and says so.)
LOGIN = dict(
    label="Demo only",
    title="Pima",
    lead="Sign in to check your soil.",
    body=("This is a demonstration. The two demo accounts are printed under each "
          "account type below and anything else is refused, so this is a "
          "comparison against a visible name, not a real sign-in. What you type "
          "here is not stored."),
    note=("An account opens one of the two views. Both views also answer at "
          "their own address, so the choice here decides where you land, not "
          "what you may see."),
    role_label="Account type",
    password_label="Password",
    show="Show",
    hide="Hide",
    demo_password="demo",
    farmer_label="Farmer",
    farmer_action="Open the farmer view",
    farmer_username="Phone number or username",
    farmer_placeholder="e.g. farmer",
    farmer_hint='Demo account: username "farmer", password "demo".',
    farmer_href="/farmer",
    researcher_label="Researcher",
    researcher_action="Open the researcher view",
    researcher_username="Username or email",
    researcher_placeholder="e.g. researcher",
    researcher_hint='Demo account: username "researcher", password "demo".',
    researcher_href="/researcher",
    err_both="Enter your username and password.",
    err_user="Enter your username.",
    err_pass="Enter your password.",
    err_wrong="That username or password does not match a {role} account.",
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


# ---------------------------------------------------------------------------
# The short end: readings taken now, and the soil test read beside them
# ---------------------------------------------------------------------------
# Two cards live here, and neither asks the tool for a new answer.
#
# The first keeps a reading per visit.  A single reading is a snapshot of one
# day; a reading only becomes information about change when there is a second
# one taken the same way to set it against.
#
# The second reads a soil-test word next to that reading.  It is the one place
# on a farmer's screen where two measured things are deliberately put together,
# so the rule it follows is written down here: it says what the two numbers mean
# side by side, what to ask the laboratory, and one general practice.  It names
# no quantity and no product.

TRACK = dict(
    title="Your readings over time",
    lead=("One reading shows one day. The same field read again, the same way, "
          "is what shows a change."),
    note="These numbers stay in this browser. Nothing is sent to a server.",
    save="Keep this reading",
    clear="Forget the saved readings",
    saved="Kept for this field.",
    empty="No reading has been kept yet.",
    first=("This is the first reading kept for this field. A second one, taken "
           "the same way, is what it can be set against."),
    since="Since the last saved reading",
    value_template="was {before}, now {now}",
    moved="has moved by more than the drift this tool was tested against.",
    still="has not moved by more than that drift.",
    date_label="The day the reading was taken",
    date_hint="Two readings need two dates before they can be compared.",
    drift_words="Half the usual spread of this reading in our sample: {value}.",
    no_drift="The tool has no figure for how much a change here matters.",
    choices=(dict(key="dry", label="Dry"),
             dict(key="damp", label="Damp"),
             dict(key="wet", label="Wet")),
)

TRACK_FIELDS = (
    dict(key="ph", name="pH_H2O", label="Acidity", unit="", kind="number",
         hint="The acidity number from your meter."),
    dict(key="ec", name="EC", label="Salts", unit="dS/m", kind="number",
         hint="The salt number from your meter."),
    dict(key="moisture", name=None, label="Moisture", unit="", kind="choice",
         hint=("How wet the soil was. The tool was not built on moisture, so "
               "this one is compared as a word.")),
)

PAIRING = dict(
    title="Your soil test and your readings together",
    lead=("The soil test says what is in the soil. A reading says what state "
          "the soil is in. The two say more side by side than either says "
          "alone."),
    band_note="Use the word your laboratory printed. Do not guess it.",
    bands=(dict(key="low", label="Low"), dict(key="medium", label="Medium"),
           dict(key="high", label="High")),
    nutrients=(dict(key="n", label="Nitrogen"),
               dict(key="p", label="Phosphorus"),
               dict(key="k", label="Potassium")),
    idle=("Choose a word for each number, and keep a reading above. The two "
          "are then read together."),
    need_readings=("Keep a reading above first. A soil test word on its own "
                   "has nothing to be read against."),
    marks_words=("Low means in the lowest tenth of the soils this tool was "
                 "built on; high means in the highest tenth."),
    horizon_title="What this means for your crop",
    horizon_idle=("Say what you are growing above and this line changes with "
                  "the answer."),
    ask_label="What to ask",
    practice_label="One practice that applies",
)

PAIR_FALLBACK = dict(
    title="The soil test word and the reading do not disagree",
    says=("None of the pairings below applies to these numbers. Nothing here "
          "points to a shortage that the reading can confirm."),
    ask="The next useful step is a second reading later, not another input.",
    practice="Keep the crop residues on the field and keep reading the same soil.",
)

PAIR_RULES = (
    dict(key="p_acid", nutrient="p", band="low", reading="ph", side="low",
         title="Low phosphorus, acid soil",
         says=("In acid soil phosphorus binds to the soil and stays bound. A "
               "low phosphorus number can mean the soil is holding it, not "
               "that it is missing."),
         ask=("Ask the laboratory whether the acidity was measured on the "
              "same sample."),
         practice=("Compost and manure carry phosphorus in a form the soil "
                   "holds less tightly than a bag of phosphorus does."),
         annual=("A season passes before the acidity is settled, so the "
                 "phosphorus put on this year may be held rather than taken "
                 "up."),
         perennial=("A perennial draws on the same soil for years, so the "
                    "acidity is worth settling before planting rather than "
                    "after."),
         mixed=("Both on one field: the acidity question belongs to the whole "
                "field, so settle it before any part is planted again.")),
    dict(key="k_salty", nutrient="k", band="low", reading="ec", side="high",
         title="Low potassium, salty soil",
         says=("Potassium moves with the soil water. When the salt reading is "
               "high, a low potassium number says as much about the water in "
               "the soil as about the potassium."),
         ask="Ask whether the sample was taken wet or dry, and on what date.",
         practice="Crop residues left on the field return potassium as they break down.",
         annual=("One season of residue is one season of potassium, so the "
                 "reading is worth repeating before the next planting."),
         perennial=("A perennial keeps the ground covered, and what falls under "
                    "it keeps returning potassium to the surface."),
         mixed=("Both on one field: the part under the perennial is the part "
                "returning potassium, so read the two parts separately.")),
    dict(key="n_dry", nutrient="n", band="low", reading="moisture", side="dry",
         title="Low nitrogen, dry soil",
         says=("Nitrogen in the topsoil only reaches the roots if there is "
               "water to carry it. A low nitrogen number from dry soil "
               "describes the day the sample was taken."),
         ask=("Ask on what date the sample was taken, and take the next one in "
              "the same month."),
         practice="Mulch between rows to keep the surface from drying out.",
         annual=("A replanted crop starts each season on whatever nitrogen the "
                 "soil holds at that moment."),
         perennial=("A perennial's roots reach deeper, but the surface still "
                    "has to stay covered for nitrogen to build under it."),
         mixed=("Both on one field: the surface is what dries first, so the "
                "mulched part is the part worth reading again.")),
)


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
        # The sliders open at the middle of the sample the tool was built on,
        # so the first answer needs no typing.  The sentence says so, because
        # a starting point read as a reading is the one lie a slider can tell.
        start_note=("The sliders start at the typical soil in our sample, not "
                    "at your soil. Move them to the numbers on your soil test."),
        submit="Show the answer",
        fields=fields,
    )


def _block(title, kind="para", intro=None, items=None, note=None) -> dict:
    """One section of the guide, in a shape the page can render blind.

    `kind` tells the page which element to use: a paragraph, a bulleted list,
    a numbered sequence of steps, or a list where each entry has a name.
    """
    return dict(
        kind=kind,
        title=title,
        intro=intro,
        items=[dict(name=i.get("name"), body=i["body"])
               if isinstance(i, dict) else dict(name=None, body=i)
               for i in (items or [])],
        note=note,
    )


def _guide(metrics: dict) -> dict:
    """
    Everything below the answer, in the order a worried farmer reads it.

    One list of blocks with one shape each, so the page renders whatever
    arrives and writes none of it: title, an opening sentence, items, a closing
    note.  A block with no items is a paragraph.
    """
    return dict(
        tab=GUIDE_TAB,
        blocks=[
            _block(TRUST["title"], intro=TRUST["body"]),
            _block(GLANCE["title"], intro=GLANCE["lead"],
                   note=GLANCE["note"]),
            _block(LAB_DECISION["title"], kind="list",
                   intro=LAB_DECISION["lead"], items=LAB_DECISION["items"]),
            _block(SAMPLING["title"], kind="steps", items=SAMPLING["steps"],
                   note=SAMPLING["note"]),
            _block(READINGS_MEANING["title"], kind="pairs",
                   items=READINGS_MEANING["items"],
                   note=READINGS_MEANING["note"]),
            _block(WHO_HELPS["title"], kind="list", items=WHO_HELPS["items"],
                   note=WHO_HELPS["ask"]),
            _block(PRACTICES["title"], kind="pairs", intro=PRACTICES["note"],
                   items=PRACTICES["items"], note=PRACTICES["source_note"]),
            _block(ABOUT_CARBON["title"], intro=ABOUT_CARBON["body"]),
            _block(HOW_SURE["title"], intro=HOW_SURE["body"]),
            _block(WHAT_IS_USED["title"], intro=WHAT_IS_USED["body"]),
        ],
    )


def _crop() -> dict:
    """
    The crop question, and what each answer changes.

    The estimate is computed before this question is asked and is not touched
    by it, so no answer here can move the number.  Each option carries what the
    reading supports, the next step that follows, and the general practices
    that apply to that kind of crop.
    """
    by_key = {i["key"]: i for i in PRACTICES["items"]}
    options = []
    for o in CROPS["options"]:
        options.append(dict(
            key=o["key"],
            button=o["button"],
            name=o["name"],
            reading=o["reading"],
            step=o["step"],
            practices=[dict(name=by_key[k]["name"], body=by_key[k]["body"])
                       for k in o["practices"] if k in by_key],
        ))
    return dict(
        title=CROPS["title"],
        lead=CROPS["lead"],
        health_note=CROPS["health_note"],
        practices_note=CROPS["practices_note"],
        idle=CROPS["idle"],
        options=options,
    )


def _strip(metrics: dict) -> dict:
    """
    The readings the farmer keeps, and how much of a change is a change.

    The drift figure is half the spread of that reading in the training sample,
    which is the point the sensor test already uses: past that much added drift
    the reading stops carrying the answer.  It is arithmetic on `sd`, so a
    bundle without an `sd` (or without the feature at all) yields no figure and
    the card says exactly that rather than borrowing one from a neighbour.
    Moisture is not an input of this build, so it never has a figure - it is
    compared as a word, and the card says why.
    """
    by_name = {f.get("name"): f for f in metrics.get("features") or []}
    fields = []
    for spec in TRACK_FIELDS:
        rng = ((by_name.get(spec["name"]) or {}).get("training_range") or {})
        drift = None
        try:
            if rng.get("sd") is not None:
                drift = round(float(rng["sd"]) / 2.0, 3)
        except (TypeError, ValueError):
            drift = None
        fields.append(dict(
            key=spec["key"], label=spec["label"], hint=spec["hint"],
            unit=spec["unit"], kind=spec["kind"],
            choices=([dict(c) for c in TRACK["choices"]]
                     if spec["kind"] == "choice" else []),
            drift=drift,
            drift_words=(TRACK["drift_words"] if drift is not None
                         else TRACK["no_drift"]),
        ))
    return dict(
        title=TRACK["title"], lead=TRACK["lead"], note=TRACK["note"],
        save=TRACK["save"], clear=TRACK["clear"], saved=TRACK["saved"],
        empty=TRACK["empty"], first=TRACK["first"], since=TRACK["since"],
        value_template=TRACK["value_template"], moved=TRACK["moved"],
        still=TRACK["still"], date_label=TRACK["date_label"],
        date_hint=TRACK["date_hint"], fields=fields,
    )


def _pairing(metrics: dict) -> dict:
    """
    A soil-test word read beside a reading.

    The two marks that decide whether a reading counts as low or high are read
    from the bundle's own sample percentiles, not chosen here, so the sentence
    a farmer reads describes the soils the tool was built on and nothing wider.
    The page picks the first rule whose word and reading both match; when none
    matches it renders the fallback rather than inventing a verdict.
    """
    by_name = {f.get("name"): f for f in metrics.get("features") or []}

    def mark(name, which):
        rng = ((by_name.get(name) or {}).get("training_range") or {})
        return rng.get(which)

    return dict(
        title=PAIRING["title"], lead=PAIRING["lead"],
        band_note=PAIRING["band_note"],
        bands=[dict(b) for b in PAIRING["bands"]],
        nutrients=[dict(n) for n in PAIRING["nutrients"]],
        idle=PAIRING["idle"], need_readings=PAIRING["need_readings"],
        marks=dict(ph_low=mark("pH_H2O", "p5"), ph_high=mark("pH_H2O", "p95"),
                   ec_high=mark("EC", "p95"), words=PAIRING["marks_words"]),
        horizon_title=PAIRING["horizon_title"],
        horizon_idle=PAIRING["horizon_idle"],
        ask_label=PAIRING["ask_label"],
        practice_label=PAIRING["practice_label"],
        fallback=dict(PAIR_FALLBACK),
        rules=[dict(key=r["key"], title=r["title"], says=r["says"],
                    ask=r["ask"], practice=r["practice"],
                    needs=dict(nutrient=r["nutrient"], band=r["band"],
                               reading=r["reading"], side=r["side"]),
                    horizon=dict(annual=r["annual"], perennial=r["perennial"],
                                 mixed=r["mixed"]))
               for r in PAIR_RULES],
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
        # The two ends of the bar, in words.  A farmer reads where the soil
        # sits; the numbers travel in the spoken description below, not on the
        # track, so the track carries one idea at a time.
        low_words="Less carbon",
        high_words="More carbon",
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
        strip=_strip(metrics),
        pairing=_pairing(metrics),
        sensor=_sensor(metrics),
        guide=_guide(metrics),
        crop=_crop(),
        next_step=dict(NEXT_STEP),
        learn_more=dict(LEARN_MORE),
        failure=dict(FAILURE),
        screens=["form", "result", "crop", "strip", "pairing", "sensor",
                 "guide"],
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
