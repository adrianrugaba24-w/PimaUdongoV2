"""
Part A - simulated field survey with a low-cost sensor measurement model.

Implements Step 2 of the SLR (Section IX): a synthetic field with spatially
correlated pH, SOC and moisture is surveyed at a fixed number of points, and each
sensor reading is the TRUE value passed through a measurement model with gain,
offset, random noise, calibration drift and cross-sensitivity to moisture.

What this module can and cannot show
------------------------------------
* The truth is known, so the size and spatial pattern of sensor error can be
  controlled and its effect isolated.
* Every result depends on the assumptions below.  It is evidence about how models
  respond to STATED sensor errors - not about any real probe, soil or farm.
* No parameter here comes from a datasheet or a bench test: the proposal wants
  those, and none have been supplied.  Every parameter is therefore marked
  "assumed".  Replace a value and flip its status to "sourced" (with a citation)
  only when a real document supports it.

The one assumption that decides the SOC result
----------------------------------------------
SOC is built from a latent field that is partly a function of true pH and true
moisture, with a single tunable `coupling` (0 = unrelated, 1 = fully determined
by them).  "SOC cannot be predicted from pH and moisture channels" (H3) is then a
statement about that coupling, so the experiment SWEEPS it instead of hiding it.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

import numpy as np

SCHEMA_VERSION = 1
AREA_KM = 20.0                      # side of the square survey area (assumed)

# Weights that tie the SOC latent field to the pH and moisture latent fields.
# The signs are an assumption (SOC rises with moisture, falls with pH).
_SOC_W_PH, _SOC_W_MOIST = -0.5, 0.5


# ---------------------------------------------------------------------------
# Parameters (every one is marked sourced | assumed)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Param:
    value: float
    unit: str
    meaning: str
    status: str = "assumed"        # "assumed" | "sourced"
    source: str = "no datasheet or bench test supplied"


def default_parameters() -> dict[str, Param]:
    """The simulation's parameter table (Table 3.4 of the proposal)."""
    A = Param
    return {
        # ---- true soil values and how they relate --------------------------
        "ph_mean": A(6.0, "pH", "mean true soil pH"),
        "ph_sd": A(0.6, "pH", "SD of true pH across the field"),
        "moist_mean": A(0.25, "m3/m3", "mean true volumetric moisture"),
        "moist_sd": A(0.06, "m3/m3", "SD of true moisture across the field"),
        "soc_median": A(1.5, "%", "median true soil organic carbon"),
        "soc_log_sd": A(0.4, "ln-units", "SD of ln(SOC) across the field"),
        # ---- pH channel -----------------------------------------------------
        "ph_gain": A(0.97, "-", "systematic gain error of the pH probe"),
        "ph_offset": A(0.10, "pH", "systematic offset of the pH probe"),
        "ph_noise_sd": A(0.15, "pH", "reading-to-reading random noise"),
        "ph_drift_total": A(0.20, "pH", "drift accumulated over the whole survey "
                                          "(basis: sampling order)"),
        "ph_moist_cross": A(2.0, "pH per m3/m3", "cross-sensitivity of the pH reading "
                                                  "to moisture, about the reference"),
        "moist_ref": A(0.25, "m3/m3", "moisture at which cross-sensitivity is zero"),
        # ---- moisture channel ----------------------------------------------
        "moist_gain": A(1.0, "-", "systematic gain error of the moisture probe"),
        "moist_offset": A(0.01, "m3/m3", "systematic offset of the moisture probe"),
        "moist_noise_sd": A(0.02, "m3/m3", "reading-to-reading random noise"),
        "moist_drift_total": A(0.01, "m3/m3", "drift over the whole survey"),
        # ---- field geometry -------------------------------------------------
        "corr_length_km": A(6.0, "km", "spatial correlation length (exponential model); "
                                        "varied in the experiment"),
        "coupling": A(0.5, "correlation", "how strongly SOC follows true pH and "
                                          "moisture; varied in the experiment"),
        "n_points": A(250, "points", "number of surveyed locations"),
    }


def parameter_table(params: dict[str, Param]) -> list[dict]:
    return [dict(name=k, **asdict(v)) for k, v in params.items()]


# ---------------------------------------------------------------------------
# The synthetic field
# ---------------------------------------------------------------------------

@dataclass
class Field:
    coords: np.ndarray             # (n, 2) in km
    order: np.ndarray              # sampling order, 0..n-1 (the drift clock)
    ph: np.ndarray                 # TRUE pH
    moisture: np.ndarray           # TRUE volumetric moisture
    soc: np.ndarray                # TRUE SOC, percent
    z_soc: np.ndarray              # latent SOC field (for tests)
    eps: dict = field(default_factory=dict)   # standard-normal noise draws, reused
                                              # across error scales (common random numbers)


def _correlated_fields(coords: np.ndarray, corr_length_km: float, rng, k: int = 3):
    """k independent unit-variance Gaussian fields, exponential covariance."""
    d = np.sqrt(((coords[:, None, :] - coords[None, :, :]) ** 2).sum(-1))
    cov = np.exp(-d / max(corr_length_km, 1e-6)) + 1e-8 * np.eye(len(coords))
    chol = np.linalg.cholesky(cov)
    return [chol @ rng.standard_normal(len(coords)) for _ in range(k)]


def make_field(seed: int, params: dict[str, Param] | None = None,
               corr_length_km: float | None = None,
               coupling: float | None = None,
               n_points: int | None = None) -> Field:
    """Build one survey.  Pure function of (seed, parameters)."""
    p = params or default_parameters()
    L = p["corr_length_km"].value if corr_length_km is None else corr_length_km
    c = p["coupling"].value if coupling is None else coupling
    if not 0.0 <= c <= 1.0:
        raise ValueError("coupling must be in [0, 1]")
    n = int(p["n_points"].value if n_points is None else n_points)

    rng = np.random.default_rng([SCHEMA_VERSION, int(seed)])
    coords = rng.uniform(0.0, AREA_KM, size=(n, 2))
    g_ph, g_moist, g_res = _correlated_fields(coords, L, rng)

    # SOC latent: a unit-variance mix whose correlation with the (pH, moisture)
    # combination equals `coupling`, plus an independent spatial remainder.
    combo = (_SOC_W_PH * g_ph + _SOC_W_MOIST * g_moist) / np.hypot(_SOC_W_PH, _SOC_W_MOIST)
    z_soc = c * combo + np.sqrt(1.0 - c ** 2) * g_res

    ph = p["ph_mean"].value + p["ph_sd"].value * g_ph
    moisture = np.clip(p["moist_mean"].value + p["moist_sd"].value * g_moist, 0.02, 0.60)
    soc = p["soc_median"].value * np.exp(p["soc_log_sd"].value * z_soc)

    order = rng.permutation(n)                     # when each point was visited
    eps = dict(ph=rng.standard_normal(n), moist=rng.standard_normal(n))
    return Field(coords, order, ph, moisture, soc, z_soc, eps)


# ---------------------------------------------------------------------------
# The measurement model
# ---------------------------------------------------------------------------

def sensor_readings(f: Field, error_scale: float = 1.0,
                    params: dict[str, Param] | None = None) -> dict[str, np.ndarray]:
    """
    Pass TRUE pH and moisture through the sensors.

    error_scale multiplies every *error* term that can vary between readings or
    over time - random noise, drift and cross-sensitivity - and leaves the fixed
    gain and offset alone.  error_scale=0 therefore returns the true values
    distorted only by a constant bias, which a model can learn away.

    The noise draws are stored on the Field, so a sweep over error_scale reuses
    the same draws (common random numbers): differences between scales are caused
    by the scale, not by a new random sample.
    """
    p = params or default_parameters()
    s = float(error_scale)
    t = f.order / max(len(f.order) - 1, 1)        # 0..1 through the survey

    ph_read = (p["ph_gain"].value * f.ph + p["ph_offset"].value
               + s * p["ph_drift_total"].value * t
               + s * p["ph_moist_cross"].value * (f.moisture - p["moist_ref"].value)
               + s * p["ph_noise_sd"].value * f.eps["ph"])
    moist_read = (p["moist_gain"].value * f.moisture + p["moist_offset"].value
                  + s * p["moist_drift_total"].value * t
                  + s * p["moist_noise_sd"].value * f.eps["moist"])
    return dict(ph_sensor=ph_read, moisture_sensor=moist_read)
