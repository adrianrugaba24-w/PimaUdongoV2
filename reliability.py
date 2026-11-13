"""
Reliability gating for one prediction.

One function, no model calls, no I/O: everything it needs is passed in, so it
can be tested branch by branch without a bundle, a server or a fitted model.

The rule, in order
------------------
1. The prediction or its interval is not a finite number
       -> Low.  There is nothing to place.
2. Any input lies outside the training range (the 5th-95th percentile of the
   training values for that feature)
       -> Low.  A value the model never saw cannot be placed in the observed
          distribution at all, whatever the interval says.
3. No band thresholds are configured for this bundle
       -> Low.  Silence is safer than inventing a placement.
4. The interval is wider than one whole band, or it spans both cuts
       -> Low.  It covers at least one complete third, so it does not single one
          out.  This is the common case when a model is weak: half a band of
          skill and a band of width ~0.79 means the interval is five bands wide.
5. The interval crosses exactly one cut
       -> Medium.  It rules out one third but does not separate the other two.
6. Otherwise the interval lies inside a single third
       -> High, with that third named.

Bands are terciles of the training target, cut once and stored in the bundle's
`bands.json`.  They are POSITION IN THE DISTRIBUTION OF SAMPLED SOILS, not a
quality grade: the upper third is not "good soil", it is the upper third of the
soils in this dataset.  The cuts are never adjusted to make a band reachable.

Crossing is strict: an interval endpoint exactly on a cut does not cross it, so
[1.0, 1.439] with a cut at 1.439 is still the middle third.
"""
from __future__ import annotations

from typing import Iterable

CONFIDENCE_LEVELS = ("High", "Medium", "Low")

LAB_LINE = ("A laboratory measurement is the only way to establish a value "
            "outside the range this model was trained on.")
TOO_WIDE = "The estimate is too wide to place in a band."
NO_BANDS = ("Band thresholds are not available for this bundle, so the estimate "
            "cannot be placed in one.")
NO_INTERVAL = "No calibrated interval is available for this model."


def _finite(x) -> bool:
    try:
        return x is not None and float(x) == float(x) and abs(float(x)) != float("inf")
    except (TypeError, ValueError):
        return False


def band_for(value: float, cuts: Iterable[float], labels: Iterable[str]):
    """Which third a single number falls in.  Cuts are ascending."""
    cuts = list(cuts)
    labels = list(labels)
    for i, cut in enumerate(cuts):
        if value <= cut:
            return i, labels[i]
    return len(cuts), labels[len(cuts)]


def gate(values: dict, prediction, low, high, *, feature_ranges: dict,
         bands: dict | None) -> dict:
    """Place one prediction and say how much the placement can be trusted.

    Parameters
    ----------
    values          the submitted feature values, keyed by feature name
    prediction      the point estimate
    low, high       the calibrated interval bounds (may be None)
    feature_ranges  {feature: {"p5": .., "p95": ..}} from the bundle
    bands           the loaded bands.json, or None

    Returns a dict with `confidence`, `band`, `band_key`, `message`, `flags`,
    `out_of_range` and `rules` (the rules that fired, for traceability).
    """
    out = dict(confidence="Low", band=None, band_key=None, message="",
               flags=[], out_of_range=[], rules=[], advice_withheld=True,
               interval=[low, high], prediction=prediction)

    # R1 - is there a number to place?
    if not _finite(prediction) or not _finite(low) or not _finite(high):
        out["rules"].append("R1_no_interval")
        out["message"] = NO_INTERVAL
        return out

    # R2 - is any input outside the training range?
    for name, value in values.items():
        rng = (feature_ranges or {}).get(name)
        if not rng or not _finite(value):
            continue
        p5, p95 = rng.get("p5"), rng.get("p95")
        if p5 is None or p95 is None:
            continue
        if value < p5 or value > p95:
            out["out_of_range"].append(dict(feature=name, value=float(value),
                                            training_p5=float(p5), training_p95=float(p95)))
            out["flags"].append(f"outside_training_range:{name}")
    if out["out_of_range"]:
        out["rules"].append("R2_outside_training_range")
        for item in out["out_of_range"]:
            out["flags"].append(f"extrapolated:{item['feature']}")
        names = [i["feature"] for i in out["out_of_range"]]
        verb = "is" if len(names) == 1 else "are"
        out["message"] = (f"{', '.join(names)} {verb} outside the range this model "
                          f"was trained on. {LAB_LINE}")
        return out

    # R3 - are there thresholds at all?
    cuts = list((bands or {}).get("cuts") or [])
    labels = [b["label"] for b in (bands or {}).get("bands") or []]
    if len(cuts) != 2 or len(labels) != 3:
        out["rules"].append("R3_no_bands")
        out["message"] = NO_BANDS
        return out

    lo, hi = float(low), float(high)
    width = hi - lo
    inner = cuts[1] - cuts[0]

    # R4 - wider than a whole band, or spanning both cuts
    if width >= inner or (lo <= cuts[0] and hi >= cuts[1]):
        out["rules"].append("R4_too_wide")
        out["message"] = TOO_WIDE
        out["flags"].append("band_undetermined")
        return out

    # R5 - crossing exactly one cut leaves two thirds possible
    crossed = [c for c in cuts if lo < c < hi]
    if len(crossed) == 1:
        below, above = band_for(lo, cuts, labels)[1], band_for(hi, cuts, labels)[1]
        out["rules"].append("R5_crosses_one_cut")
        out["confidence"] = "Medium"
        out["message"] = (f"The interval crosses the boundary between the "
                          f"{below.lower()} and the {above.lower()}, so it does not "
                          f"separate those two.")
        out["flags"].append("band_boundary_crossed")
        return out

    # R6 - a single third
    idx, label = band_for((lo + hi) / 2.0, cuts, labels)
    out["rules"].append("R6_single_band")
    out["confidence"] = "High"
    out["band"] = label
    out["band_key"] = (bands["bands"][idx] or {}).get("key")
    out["message"] = f"The estimate falls in the {label.lower()}."
    return out
