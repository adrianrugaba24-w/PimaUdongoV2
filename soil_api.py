"""
Prediction service for the PimaUdongo SOC prototype.

Run:
    uvicorn soil_api:app --reload          # then open http://127.0.0.1:8000/
    MODEL_DIR=export uvicorn soil_api:app  # if the export lives elsewhere

Behaviour this module is responsible for:
  * it REFUSES to start unless model.joblib, model_meta.json and results.json
    are all present and mutually consistent (hash-checked, not assumed);
  * every number it returns is read out of results.json - the API contains no
    hard-coded metric;
  * an input that is physically impossible is a 422, while an input that is
    merely outside the training range is a 200 with out_of_domain set;
  * the interval is reported together with the coverage it actually achieved
    under spatial CV, because a nominal 90% band is not a 90% guarantee in a
    new area.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

import farmer_view
import metrics_view
import reliability

MODEL_DIR = Path(os.environ.get("MODEL_DIR", "export"))
WEB_DIR = Path(__file__).parent / "web"


class BundleError(RuntimeError):
    """Raised when the exported model bundle is missing or inconsistent."""


# ---------------------------------------------------------------------------
# Bundle loading - runs at import time on purpose: a broken bundle must stop
# the process before it can serve a single prediction.
# ---------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _text_hashes(path: Path) -> set[str]:
    """
    Hashes of a TEXT file under every common newline convention.

    results.json is plain text, and git/Windows can rewrite its line endings
    (LF <-> CRLF) without changing a single number.  A hash that only matches one
    convention makes a fresh clone refuse to start.  Any change to the CONTENT
    still changes all three hashes, so tamper detection is unaffected.
    """
    raw = path.read_bytes()
    lf = raw.replace(b"\r\n", b"\n")
    crlf = lf.replace(b"\n", b"\r\n")
    return {hashlib.sha256(b).hexdigest() for b in (raw, lf, crlf)}


def load_bundle(model_dir: Path) -> dict:
    files = {n: model_dir / n for n in ("model.joblib", "model_meta.json", "results.json")}
    missing = [n for n, p in files.items() if not p.is_file()]
    if missing:
        raise BundleError(
            f"Cannot start: {', '.join(missing)} missing from {model_dir}. "
            f"Run `python afsis_experiment.py` first (add --root <AfSIS dir> for "
            f"real data).")

    try:
        meta = json.loads(files["model_meta.json"].read_text())
        results = json.loads(files["results.json"].read_text())
    except json.JSONDecodeError as ex:
        raise BundleError(f"Cannot start: unreadable metadata in {model_dir}: {ex}")

    required = ("model_version", "feature_names", "target_name", "target_units",
                "log_target", "training_data_version", "results_sha256",
                "sklearn_version")
    absent = [k for k in required if k not in meta]
    if absent:
        raise BundleError(f"Cannot start: model_meta.json is missing {absent}. "
                          f"The bundle is from an older/incomplete run; regenerate it.")

    if meta["results_sha256"] not in _text_hashes(files["results.json"]):
        raise BundleError(
            "Cannot start: results.json does not match the hash recorded in "
            "model_meta.json. The model and the reported metrics are out of "
            "sync - regenerate both together.")

    model = joblib.load(files["model.joblib"])
    version = "sha256:" + _sha256(files["model.joblib"])[:16]
    if version != meta["model_version"]:
        raise BundleError("Cannot start: model.joblib hash differs from "
                          "model_meta.json (the model file was edited or swapped).")

    if list(meta["feature_names"]) != list(results.get("features", [])):
        raise BundleError(
            f"Cannot start: the model was fitted on {list(meta['feature_names'])} "
            f"but results.json advertises {list(results.get('features', []))}. "
            f"Feature order is positional; refusing to guess.")

    import sklearn
    got = tuple(int(x) for x in re.findall(r"\d+", sklearn.__version__)[:2])
    want = tuple(int(x) for x in re.findall(r"\d+", meta["sklearn_version"])[:2])
    if got != want:
        raise BundleError(
            f"Cannot start: model.joblib was pickled with scikit-learn "
            f"{meta['sklearn_version']} but {sklearn.__version__} is installed. "
            f"Cross-version unpickling can silently change predictions; "
            f"regenerate the export with this environment.")

    return dict(model=model, meta=meta, results=results,
                model_path=files["model.joblib"])


def _optional_json(path: Path) -> dict | None:
    """
    An additive artefact, or None.

    cv_supplement.json and bands.json are written by cv_supplement.py, which is
    a separate pass.  A bundle that predates that pass is still a valid bundle,
    so a missing or unreadable file must never stop the service: the /api
    routes report the gap instead.  The hashes above still gate the three files
    the model's numbers actually come from.
    """
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


BUNDLE = load_bundle(MODEL_DIR)
MODEL, META, R = BUNDLE["model"], BUNDLE["meta"], BUNDLE["results"]
FEATURES = list(META["feature_names"])
UNITS = META["target_units"]
RANGES = R.get("feature_ranges", {})
BOUNDS = R.get("feature_bounds", {})          # physical limits -> 422 when violated
INTERVAL = R.get("results", {}).get("interval", {})
SUPPLEMENT = _optional_json(MODEL_DIR / "cv_supplement.json")
BANDS = _optional_json(MODEL_DIR / "bands.json")

# The /api views are composed once at start-up, from files that are already on
# disk.  If composition fails, /predict must still serve, so the error is kept
# and returned by /api/metrics rather than raised here.
try:
    METRICS = metrics_view.build_metrics(R, META, supplement=SUPPLEMENT,
                                         bands=BANDS, model_dir=str(MODEL_DIR))
    METRICS_ERROR = None
except Exception as _ex:                                        # pragma: no cover
    METRICS, METRICS_ERROR = None, f"{type(_ex).__name__}: {_ex}"

app = FastAPI(
    title="PimaUdongo SOC prototype",
    description="Research prototype. Not validated on field sensors or Ugandan "
                "farms. Not for agronomic decisions.",
    version=META["model_version"],
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])


class Query(BaseModel):
    values: dict = Field(..., description="One entry per training feature")


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def _validate(values: dict) -> np.ndarray:
    if not isinstance(values, dict):
        raise HTTPException(422, detail={"error": "body_not_object",
                                         "message": "`values` must be a JSON object "
                                                    "mapping feature name to number."})
    unknown = [k for k in values if k not in FEATURES]
    if unknown:
        raise HTTPException(422, detail={
            "error": "unknown_features", "features": unknown,
            "message": f"Unrecognised input(s) {unknown}. This model accepts exactly: "
                       f"{FEATURES}. A typo would otherwise be silently ignored.",
            "expected": FEATURES})
    missing = [f for f in FEATURES if f not in values]
    if missing:
        raise HTTPException(422, detail={
            "error": "missing_features", "features": missing,
            "message": f"Missing required input(s): {missing}. The model cannot "
                       f"predict from a partial feature vector.",
            "expected": FEATURES})

    bad_type, impossible = [], []
    for f in FEATURES:
        v = values[f]
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            bad_type.append({f: {"given": repr(v), "needs": "number"}})
            continue
        x = float(v)
        if not np.isfinite(x):
            bad_type.append({f: {"given": repr(v), "needs": "finite number"}})
            continue
        lo, hi = BOUNDS.get(f, [None, None])
        if lo is not None and not (lo <= x <= hi):
            impossible.append({f: {"given": x, "physically_valid_range": [lo, hi],
                                   "units": R.get("feature_units", {}).get(f)}})
    if bad_type:
        raise HTTPException(422, detail={
            "error": "invalid_type", "offending": bad_type,
            "message": "Every feature must be a finite JSON number (not a string, "
                       "null, or boolean)."})
    if impossible:
        raise HTTPException(422, detail={
            "error": "impossible_value", "offending": impossible,
            "message": "These values cannot occur in a soil sample, so the reading "
                       "or its units are wrong. No prediction is returned for "
                       "impossible input.",
            "units_note": f"Target units are {UNITS}; check whether your sensor "
                          f"reports the same unit before resubmitting."})
    return np.array([[float(values[f]) for f in FEATURES]], dtype=float)


def _out_of_domain(x: np.ndarray) -> list[dict]:
    """Values inside the physical range but outside what the model was trained on."""
    flags = []
    for j, f in enumerate(FEATURES):
        rng = RANGES.get(f)
        if not rng:
            continue
        lo, hi = rng["p5"], rng["p95"]
        v = float(x[0, j])
        if v < lo or v > hi:
            span = max(hi - lo, 1e-9)
            flags.append(dict(feature=f, value=v, training_p5=lo, training_p95=hi,
                              distance_outside=float(max(lo - v, v - hi)),
                              relative_to_training_spread=float(max(lo - v, v - hi) / span)))
    return flags


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.exception_handler(BundleError)
async def _bundle_error_handler(_: Request, ex: BundleError):        # pragma: no cover
    return JSONResponse(500, {"error": "bundle_unavailable", "message": str(ex)})


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": MODEL is not None,
        "model_version": META["model_version"],
        "training_data_version": META["training_data_version"],
        "model_dir": str(MODEL_DIR),
        "expects_features": FEATURES,
        "data_is_real": bool(R.get("data", {}).get("is_real_data", False)),
    }


@app.post("/predict")
def predict(q: Query):
    x = _validate(q.values)
    raw = float(MODEL.predict(x)[0])
    pred = max(0.0, raw)                      # SOC cannot be negative
    half = INTERVAL.get("half_width")
    low = max(0.0, pred - half) if half is not None else None
    high = pred + half if half is not None else None
    ood = _out_of_domain(x)
    return {
        "target": META["target_name"],
        "model_name": R.get("headline", {}).get("model"),
        "prediction": pred,
        "units": UNITS,
        "low": low,
        "high": high,
        "interval_level": INTERVAL.get("nominal"),
        "interval_empirical_coverage": INTERVAL.get("empirical_coverage"),
        "interval_method": INTERVAL.get("method"),
        "interval_warning": (
            "Coverage is measured under spatial CV. If it is below the nominal "
            "level, this band is optimistic for new areas."
            if INTERVAL.get("empirical_coverage") is not None else
            "No calibrated interval is available for this model."),
        "model_version": META["model_version"],
        "training_data_version": META["training_data_version"],
        "data_is_real": bool(R.get("data", {}).get("is_real_data", False)),
        "out_of_domain": bool(ood),
        "out_of_domain_features": ood,
        "out_of_domain_note": (
            "At least one input is outside the 5th-95th percentile of the training "
            "data. The prediction is an extrapolation; treat it as unverified."
            if ood else None),
        "accuracy_context": _model_info_metrics()["spatial_cv_first"],
    }


def _model_info_metrics() -> dict:
    """Metrics pulled straight from results.json, spatial CV listed first."""
    gap = R.get("results", {}).get("validation_gap", [])
    ordered = sorted(gap, key=lambda r: -(r.get("r2_spatial")
                                          if r.get("r2_spatial") is not None else -9))
    return {
        "spatial_cv_first": [{k: r.get(k) for k in
                              ("model", "r2_spatial", "rmse_spatial", "r2_random",
                               "gap_mean", "gap_sd", "spatial_beats_baseline")}
                             for r in ordered],
        "headline": R.get("headline"),
        "baseline_rmse": R.get("results", {}).get("baseline_rmse"),
        "interval": R.get("results", {}).get("interval"),
        "shuffled_control": R.get("results", {}).get("shuffled_control"),
        "n_seeds": R.get("validation", {}).get("n_seeds"),
        "units": UNITS,
    }


@app.get("/model-info")
def model_info():
    v = R.get("validation", {})
    return {
        "model_version": META["model_version"],
        "training_data_version": META["training_data_version"],
        "trained_at_utc": META.get("fitted_at_utc"),
        "n_training_rows": META.get("n_rows"),
        "target": META["target_name"], "units": UNITS,
        "features": FEATURES,
        "feature_ranges": RANGES,
        "data_is_real": bool(R.get("data", {}).get("is_real_data", False)),
        "data_kind": R.get("data", {}).get("kind"),
        "licence": R.get("data", {}).get("licence"),
        "validation_design": {
            "folds": v.get("folds"), "inner_folds": v.get("inner_folds"),
            "n_seeds": v.get("n_seeds"), "blocks": v.get("blocks"),
            "spatial_grouping": v.get("spatial_grouping"),
            "tuning": v.get("tuning"), "metrics": v.get("metrics"),
            # A spatial-CV SD of 0.000 is a property of the design, not a missing
            # calculation: say so where the design is described.
            "spatial_partition_note": v.get("spatial_partition_note"),
            "experiment_scope": v.get("experiment_scope"),
        },
        "partition_sensitivity": R.get("results", {}).get("partition_sensitivity", []),
        "metrics": _model_info_metrics(),
        "limitations": R.get("limitations", []),
        "disclaimer": ("Research prototype. Not validated on field sensors or "
                       "Ugandan farms. Not for agronomic decisions."),
    }


@app.get("/results")
def results():
    """Full results.json, kept for the web page and the existing tests."""
    return R


@app.get("/results.json")
def results_json():
    return R


# ---------------------------------------------------------------------------
# /api/* - additive views for the dashboard.  /predict above is unchanged.
# ---------------------------------------------------------------------------

@app.get("/api/metrics")
def api_metrics():
    """Every number the interface displays, copied from files already on disk."""
    if METRICS is None:                                         # pragma: no cover
        raise HTTPException(500, {"error": "metrics_unavailable",
                                 "message": METRICS_ERROR})
    return METRICS


@app.post("/api/predict")
def api_predict(q: Query):
    """The same prediction as /predict, with the band placement attached.

    The interval here is the split-conformal band exactly as calibrated: it is
    not re-derived from the RMSE, and the spatial RMSE is reported beside it as
    an accuracy figure rather than folded into the width.  `low` is left
    unclamped at zero - clipping an endpoint would shorten the band without
    changing the coverage that was measured for the unclipped one.
    """
    return _api_prediction(q.values)


def _api_prediction(values: dict) -> dict:
    x = _validate(values)
    raw = float(MODEL.predict(x)[0])
    pred = max(0.0, raw)                      # SOC cannot be negative
    half = INTERVAL.get("half_width")
    low = pred - half if half is not None else None
    high = pred + half if half is not None else None

    bands = (METRICS or {}).get("bands")
    placement = reliability.gate(values, pred, low, high,
                                 feature_ranges=RANGES, bands=bands)
    interval_model = INTERVAL.get("model")
    spatial_rmse = next(
        (row.get("rmse_spatial") for row in R.get("results", {}).get("validation_gap", [])
         if row.get("model") == interval_model), None)

    return {
        "schema_version": 1,
        "target": {"name": META["target_name"], "unit": UNITS},
        "prediction": pred,
        "prediction_unclamped": raw,
        "interval": {
            "low": low, "high": high,
            "below_zero": bool(low is not None and low < 0.0),
            "nominal": INTERVAL.get("nominal"),
            "empirical_coverage": INTERVAL.get("empirical_coverage"),
            "coverage_sd": INTERVAL.get("coverage_sd"),
            "mean_width": INTERVAL.get("mean_width"),
            "half_width": half,
            "method": INTERVAL.get("method"),
            "model": interval_model,
            "note": INTERVAL.get("honest_note"),
        },
        "band": placement,
        # Reported separately on purpose: an RMSE is not a width to add and
        # subtract, and the calibrated band already carries its own coverage.
        "accuracy": {
            "spatial_rmse": spatial_rmse,
            "interval_model": interval_model,
        },
        "model_version": META["model_version"],
        "training_data_version": META["training_data_version"],
        "data_is_real": bool(R.get("data", {}).get("is_real_data", False)),
    }


# ---------------------------------------------------------------------------
# /api/farmer - the same answer, said in plain words.  Every string in this
# payload is written in farmer_view.py and checked there against a banned-terms
# list, so the page renders words it was given rather than words it chose.
# ---------------------------------------------------------------------------

@app.get("/api/farmer")
def api_farmer():
    """The farmer screens that do not depend on a submitted sample."""
    if METRICS is None:                                         # pragma: no cover
        raise HTTPException(500, {"error": "metrics_unavailable",
                                 "message": METRICS_ERROR})
    return farmer_view.build(METRICS)


@app.post("/api/farmer/predict")
def api_farmer_predict(q: Query):
    """One farmer result screen for one submitted sample."""
    if METRICS is None:                                         # pragma: no cover
        raise HTTPException(500, {"error": "metrics_unavailable",
                                 "message": METRICS_ERROR})
    return farmer_view.build(METRICS, _api_prediction(q.values))


@app.get("/api/login")
def api_login():
    """The entry gate's wording.  It is a chooser: nothing is stored or checked."""
    return farmer_view.build_login()


@app.get("/")
def index():
    """The entry gate: one choice for a soil sample, one for the research view."""
    return _page(WEB_DIR / "login.html")


@app.get("/login")
def login_page():
    return _page(WEB_DIR / "login.html")


@app.get("/farmer")
def farmer_page():
    """The plain-language view for someone holding a soil sample."""
    return _page(WEB_DIR / "farmer.html")


@app.get("/researcher")
def researcher_page():
    """The technical view: every chart and table from the previous front page."""
    return _page(WEB_DIR / "index.html")


def _page(path: Path):
    if not path.is_file():
        raise HTTPException(404, f"{path.name} not found")
    return FileResponse(path)
