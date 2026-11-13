"""
The recommendation engine: which steps apply, in what order, and on what.

What this is not
----------------
It is not agronomic advice.  Nothing here names an input, a rate or a quantity,
because a rate would need a field trial this project has not run - and the
tool's own uncertainty is the reason it cannot stand in for one.  What it does
is rank the moves that would strengthen or settle the answer: get the soil
tested, read it again before acting on a change, sample a field the way the
field actually is, keep the record straight, and the general practice that
belongs to the crop the farmer chose.

Every step travels with the evidence it rests on (`basis`), so a screen can
print the reason and not just the instruction.  A step with no evidence behind
it is not in this file.

Why the band is not an input
----------------------------
`reliability.gate` places the soil in a tercile of the sampled soils.  That is a
POSITION in a distribution, not a grade: the upper third is the upper third of
the soils in this dataset, not "good soil".  A step recommended because of it
would be a step recommended for a reason this project does not have, so the
rules below read only

    * whether the gate withheld a placement, and which rule did it,
    * what the last two kept readings say against each other,
    * what the laboratory said, read beside a reading,
    * which crop cycle was chosen,

and never `band` or `band_key`.  There is a test for exactly that.

Ordering
--------
Fixed, and written down rather than scored.  A score invites tuning, and there
is nothing in this project to tune it against.  The order is:

    A  the tool could not place the soil at all
    C  the field cannot be read as one field
    D  the one place where two measured things meet
    B  the state of the record: a move, no move, or no second reading yet
    E  a practice that belongs to the chosen crop
    F  the record itself, always last

Uncertainty comes first because everything downstream is an answer about this
soil; if the tool cannot place the soil, the useful step is the one that ends
the uncertainty, not one that builds on it.  The list is capped at `CAP` and
the payload says how many were held back.

Where the words are
-------------------
Every sentence this module prints is written in `farmer_view.py` and passed
through that module's banned-term guard before it leaves here.  Two of them are
templates that this module fills with figures it read from the bundle; the
figures are arithmetic on stored fields, which is why they can be printed at
all, and the sentences that carry them are guarded after filling.
"""
from __future__ import annotations

import farmer_view as F

# How many steps a screen shows.  Three is what fits under one answer before
# the list stops reading as a list and starts reading as a lecture.
CAP = 3

# The two kept readings that carry a number.  Moisture is not an input of this
# build, so it is compared as a word, exactly as the page compares it.
NUMERIC = (("ph", "pH_H2O"), ("ec", "EC"))

# The gate rules that mean "no placement was established".  R2 is handled
# separately because it has its own sentence: the soil is outside the training
# range, which is a different statement from "the estimate is too wide".
WITHHOLDING = ("R1_no_interval", "R3_no_bands", "R4_too_wide", "R5_crosses_one_cut")

WORD = {c["key"]: str(c["label"]).lower() for c in F.TRACK["choices"]}
CROP_KEYS = tuple(o["key"] for o in F.CROPS["options"])
NUTRIENTS = tuple(n["key"] for n in F.PAIRING["nutrients"])
BAND_KEYS = tuple(b["key"] for b in F.PAIRING["bands"])


# ---------------------------------------------------------------------------
# Small readers of the payload - no copy, no judgement
# ---------------------------------------------------------------------------

def _finite(x) -> bool:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return False
    return v == v and abs(v) != float("inf")


def _num(x) -> str:
    """A figure as short as it can be said: 0.508 -> "0.508", 5.0 -> "5"."""
    if not _finite(x):
        return ""
    return f"{float(x):.3f}".rstrip("0").rstrip(".") or "0"


def _feature(metrics, name: str) -> dict:
    for f in (metrics or {}).get("features") or []:
        if f.get("name") == name:
            return f
    return {}


def _drift(metrics, name: str):
    """
    Half the spread of one reading, or None.

    The same figure the readings card prints, computed the same way, so a step
    that says "more than the drift" quotes the number the farmer was already
    shown.  None when the bundle carries no spread: a missing figure must not
    become a borrowed one.
    """
    sd = ((_feature(metrics, name).get("training_range") or {}).get("sd"))
    return float(sd) / 2.0 if _finite(sd) else None


def _label(name: str) -> str:
    return (F.FIELD_COPY.get(name) or {}).get("label") or F.FALLBACK_FIELD["label"]


def _option(crop_key):
    for o in F.CROPS["options"]:
        if o["key"] == crop_key:
            return o
    return None


def _context(raw) -> dict:
    """
    The farmer's side of the conversation, made safe to read.

    Junk is dropped rather than guessed at: an unknown crop becomes None, an
    unknown nutrient or band word is discarded, and a block that is not an
    object becomes None.  Nothing here raises, because a malformed context must
    never cost a farmer the steps that do apply.
    """
    raw = raw if isinstance(raw, dict) else {}
    bands = raw.get("bands") if isinstance(raw.get("bands"), dict) else {}
    crop = raw.get("crop")
    return dict(
        crop=crop if crop in CROP_KEYS else None,
        bands={k: v for k, v in bands.items() if k in NUTRIENTS and v in BAND_KEYS},
        reading=raw.get("reading") if isinstance(raw.get("reading"), dict) else None,
        previous=raw.get("previous") if isinstance(raw.get("previous"), dict) else None,
    )


def _condition(key: str, reading, marks: dict):
    """
    Is this reading low, high, middle, dry - the same test the page runs.

    Returns None when it cannot be decided, which is different from "normal":
    a missing mark means the sentence "the reading is in the middle" would be
    inventing a comparison the bundle does not support.
    """
    if not isinstance(reading, dict):
        return None
    value = reading.get(key)
    if key == "moisture":
        return value if value in WORD else None
    if not _finite(value):
        return None
    v = float(value)
    if key == "ph":
        lo, hi = marks.get("ph_low"), marks.get("ph_high")
        if not (_finite(lo) and _finite(hi)):
            return None
        if v < float(lo):
            return "low"
        return "high" if v > float(hi) else "middle"
    if key == "ec":
        hi = marks.get("ec_high")
        if not _finite(hi):
            return None
        return "high" if v > float(hi) else "normal"
    return None


def _compare(ctx: dict, metrics) -> tuple[list, int]:
    """
    (what moved, how many pairs could be compared at all).

    A pair that cannot be compared is not "no change" - it is silence, and the
    second number is what keeps silence from being reported as calm.
    """
    now, was = ctx.get("reading"), ctx.get("previous")
    if not isinstance(now, dict) or not isinstance(was, dict):
        return [], 0

    moved, compared = [], 0
    for key, name in NUMERIC:
        before, after = was.get(key), now.get(key)
        if not (_finite(before) and _finite(after)):
            continue
        drift = _drift(metrics, name)
        if drift is None:
            continue
        compared += 1
        delta = abs(float(after) - float(before))
        if delta > drift:
            moved.append(dict(key=key, feature=name, label=_label(name),
                              kind="number", moved=delta, drift=drift))

    a, b = was.get("moisture"), now.get("moisture")
    if a in WORD and b in WORD:
        compared += 1
        if a != b:
            moved.append(dict(key="moisture", label="Moisture", kind="word",
                              before=WORD[a], now=WORD[b]))

    return moved, compared


# ---------------------------------------------------------------------------
# The steps
# ---------------------------------------------------------------------------

def _item(key: str, rank: int, basis: str, copy: dict, *, why=None, now=None,
          ask=None, **extra) -> dict:
    """One step, in the shape a page renders blind."""
    item = dict(key=key, rank=rank, basis=basis, title=copy["title"],
                why=why if why is not None else copy.get("why"),
                now=now if now is not None else copy.get("now"),
                ask=ask)
    item.update(extra)
    return item


def _placement(gate: dict) -> dict:
    """A, in one of its two forms: outside the sample, or not placeable in it."""
    if "R2_outside_training_range" in (gate.get("rules") or []):
        names = [_label(i.get("feature"))
                 for i in gate.get("out_of_range") or [] if i.get("feature")]
        names = names or [_label("")]
        copy = F.RECOMMEND_ITEMS["outside_one" if len(names) == 1 else "outside_many"]
        return _item("A2_outside", 1, "placement", copy,
                     why=copy["why"].format(names=" and ".join(names)))
    return _item("A1_unsure", 1, "placement", F.RECOMMEND_ITEMS["unsure"])


def _pair_step(metrics, ctx: dict) -> dict | None:
    """
    D: a soil-test word and a reading pointing at the same question.

    The first rule that matches wins, in the order `PAIR_RULES` is written, so
    the ranking of the pairings stays in the one place it was decided.
    """
    reading = ctx.get("reading")
    marks = F.marks(metrics)
    for rule in F.PAIR_RULES:
        if (ctx.get("bands") or {}).get(rule["nutrient"]) != rule["band"]:
            continue
        if _condition(rule["reading"], reading, marks) != rule["side"]:
            continue
        return _item("D1_" + rule["key"], 3, "soil_test",
                     dict(title=rule["title"], why=rule["says"], now=rule["practice"]),
                     ask=rule["ask"])
    return None


def _history(metrics, ctx: dict, placement_withheld: bool) -> list[dict]:
    """B1, B2 or B3 - at most one, and only when the answer can carry it."""
    moved, compared = _compare(ctx, metrics)
    if moved:
        first = moved[0]
        copy = F.RECOMMEND_ITEMS["moved"]
        if first["kind"] == "number":
            why = copy["why"].format(label=first["label"],
                                     moved=_num(first["moved"]),
                                     drift=_num(first["drift"]))
        else:
            why = F.RECOMMEND_ITEMS["moved_word"]["why"].format(
                before=first["before"], now=first["now"])
        return [_item("B2_moved", 4, "previous", copy, why=why, moves=moved)]

    if compared and not placement_withheld:
        # Only after a comparison was actually made: silence about a pair that
        # could not be compared is not the same finding as "nothing changed".
        return [_item("B3_steady", 4, "previous", F.RECOMMEND_ITEMS["steady"])]

    if ctx.get("previous") is None:
        return [_item("B1_first", 4, "previous", F.RECOMMEND_ITEMS["first"])]
    return []


def _mixed(ctx: dict) -> dict | None:
    """
    C: two crops on one field, where one reading cannot be the field's reading.

    Uses the crop card's own sentences rather than a second description of the
    same situation, so the two cards cannot drift apart.
    """
    if ctx.get("crop") != "mixed":
        return None
    option = _option("mixed")
    return _item("C1_mixed", 2, "crop", F.RECOMMEND_ITEMS["mixed"],
                 why=option["reading"], now=option["step"])


def _practice(ctx: dict) -> dict | None:
    """
    E: one practice that belongs to the chosen crop.

    One, not the whole list: the crop card already shows all of them, and a
    step that repeats four practices buries the step above it.  The first is
    taken because the crop option's own order is the order it was written in.
    """
    option = _option(ctx.get("crop"))
    if not option:
        return None
    by_key = {i["key"]: i for i in F.PRACTICES["items"]}
    for key in option["practices"]:
        if key in by_key:
            practice = by_key[key]
            return _item("E1_practice", 5, "crop",
                         dict(title=practice["name"], why=practice["body"],
                              now=F.RECOMMEND["practice_note"]))
    return None


def _verdict(top: dict) -> dict:
    """The situation, said once, before the steps that follow from it."""
    code = (top["key"].split("_")[0] if top else "F1")
    out = dict(F.RECOMMEND_VERDICTS.get(code) or F.RECOMMEND_VERDICTS["F1"])
    out["words"] = F.RECOMMEND_BASIS.get(out.get("basis"), "")
    return out


# ---------------------------------------------------------------------------
# The engine
# ---------------------------------------------------------------------------

def recommend(prediction, metrics, context=None) -> dict:
    """
    Rank the next steps for one submitted sample.

    `prediction` is one `/api/predict`-shaped dict (the gate's `rules` are what
    this reads), `metrics` is the `/api/metrics` payload, and `context` is the
    farmer's side: crop, soil-test words, the last two kept readings.  Nothing
    is fetched, fitted or guessed at, so the whole ranking is testable by
    handing it three dicts.
    """
    ctx = _context(context)
    gate = (prediction or {}).get("band") or {}
    rules = list(gate.get("rules") or [])
    items: list[dict] = []

    withheld = any(r in WITHHOLDING for r in rules) or \
        "R2_outside_training_range" in rules

    # A - can the tool say anything about this soil?
    if withheld:
        items.append(_placement(gate))

    # C - is the field one field?
    mixed = _mixed(ctx)
    if mixed:
        items.append(mixed)

    # D - do a soil-test word and a reading meet?
    pair = _pair_step(metrics, ctx)
    if pair:
        items.append(pair)

    # B - the record, read against itself.
    items.extend(_history(metrics, ctx, placement_withheld=withheld))

    # E - one practice for the chosen crop.
    practice = _practice(ctx)
    if practice:
        items.append(practice)

    # F - always last, and always true.
    items.append(_item("F1_record", 6, "record", F.RECOMMEND_ITEMS["record"]))

    total = len(items)
    shown = items[:CAP]
    if not total:
        top = None
    else:
        top = shown[0]

    for item in shown:
        item["words"] = F.RECOMMEND_BASIS.get(item.get("basis"), "")

    out = dict(
        schema_version=1,
        cap=CAP,
        total=total,
        shown=len(shown),
        unshown=max(0, total - len(shown)),
        items=shown,
        verdict=_verdict(top) if total else None,
        # What the ranking was allowed to see, so a reviewer can check the claim
        # that the band was not among its inputs.
        context_used=dict(crop=ctx.get("crop"),
                          bands=dict(ctx.get("bands") or {}),
                          has_reading=isinstance(ctx.get("reading"), dict),
                          has_previous=isinstance(ctx.get("previous"), dict)),
    )
    # The guard runs here as well as in `build()`, because these sentences are
    # assembled from templates and figures and this is the last point at which a
    # bad one can be stopped.
    for _, text in F.iter_strings(out):
        F._banned_guard(text)
    return out
