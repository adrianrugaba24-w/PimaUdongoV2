"""
Part A experiment - how validation design and sensor error affect model skill
on a SIMULATED survey (SLR Section IX, Steps 2-6; hypotheses H1-H3).

    python sensor_experiment.py            # full run
    python sensor_experiment.py --quick    # small run (tests, smoke checks)

Inputs : two simulated sensor channels - pH and moisture - read through the
         measurement model in sensor_sim.py.
Targets: TRUE pH and TRUE SOC (standing in for laboratory values).

The result of this experiment is conditional on the assumptions in
sensor_sim.py.  To stop one assumption deciding the answer silently, the three
that matter most are SWEPT, not fixed:

  * spatial correlation length  -> controls how big the random-vs-spatial gap is (H1)
  * SOC coupling to pH/moisture -> controls whether SOC is predictable at all   (H3)
  * error scale                 -> controls the noise curve                     (H2, H3)

Nothing here is a claim about a real sensor, soil or farm.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import afsis_data as A
import afsis_validation as V
import sensor_sim as S

# ---- design (stated, not tuned) --------------------------------------------
USEFUL_R2 = 0.5            # "useful skill" threshold for H3, fixed before any run
ERROR_SCALES = [0.0, 0.5, 1.0, 2.0, 4.0]
CORR_LENGTHS_KM = [2.0, 6.0, 15.0]
COUPLINGS = [0.0, 0.5, 0.9]
DEFAULT_L, DEFAULT_C = 6.0, 0.5       # the single setting used for the noise sweep
MODELS = ("mean_baseline", "ridge", "random_forest", "gradient_boosting")
TARGETS = ("ph", "soc")
FEATURES = ["ph_sensor", "moisture_sensor"]
BASELINE_SCALE = 1.0       # the "baseline" error setting; 0.5 / 2.0 are low / high

LIMITATIONS = [
    "Simulation under stated assumptions: results describe how models respond to "
    "the sensor errors and field structure defined in sensor_sim.py, not how any "
    "real probe or soil behaves.",
    "No parameter is sourced from a datasheet or bench test; all are marked "
    "'assumed' in parameters[]. The 'baseline' error setting is therefore "
    "exploratory until real specifications replace those values.",
    "SOC is built to depend on true pH and moisture with a tunable coupling; "
    "whether SOC is 'predictable' from the sensor channels is a function of that "
    "coupling, which is why it is swept.",
    "One device and one survey geometry per replicate; gain and offset are fixed "
    "per run, so device-to-device variation is not modelled.",
    "Hyperparameters are fixed at the learners' defaults here (no nested tuning), "
    "to keep the sweep affordable; the public-data experiment tunes by nested CV.",
]


# ---------------------------------------------------------------------------
# One scored run
# ---------------------------------------------------------------------------

def cv_two_inputs(X_fit, X_eval, y, groups, spec, scheme, seed, log_target):
    """
    Cross-validated predictions where the model is FITTED on X_fit and SCORED on
    X_eval (same rows, possibly different noise).  Passing the same array for
    both gives ordinary CV.  Folds come from V.outer_splits, so they depend only
    on (scheme, seed, groups) - never on the model or on the noise level.
    """
    X_fit, X_eval = np.asarray(X_fit, float), np.asarray(X_eval, float)
    y = np.asarray(y, float)
    oof = np.full(len(y), np.nan)
    for tr, te in V.outer_splits(scheme, X_fit, y, groups, seed):
        pipe = V.apply_params(V.build_pipeline(spec, log_target, seed), spec.default_params)
        pipe.fit(X_fit[tr], y[tr])
        oof[te] = pipe.predict(X_eval[te])
    return V.metrics(y, oof)


def _log_target(target: str) -> bool:
    # SOC is positive and right-skewed; pH is already a logarithmic scale, so a
    # further log transform would be wrong for it.
    return target == "soc"


def _target_values(f: S.Field, target: str) -> np.ndarray:
    return f.ph if target == "ph" else f.soc


def _matrix(f: S.Field, scale: float, params) -> np.ndarray:
    r = S.sensor_readings(f, scale, params)
    return np.column_stack([r["ph_sensor"], r["moisture_sensor"]])


# ---------------------------------------------------------------------------
# The experiment
# ---------------------------------------------------------------------------

def run(reps: int, seed0: int, blocks: int, scales, corr_lengths, couplings,
        n_points: int | None, progress: bool = True):
    specs = V.model_specs()
    params = S.default_parameters()
    rows: list[dict] = []

    def add(**kw):
        rows.append(kw)

    # ---- core grid: random vs spatial, at the baseline error scale ----------
    for L in corr_lengths:
        for c in couplings:
            for rep in range(reps):
                seed = seed0 + rep
                f = S.make_field(seed, params, corr_length_km=L, coupling=c, n_points=n_points)
                X = _matrix(f, BASELINE_SCALE, params)
                grp, _ = V.spatial_groups(f.coords, np.arange(len(X)), blocks, seed)
                for target in TARGETS:
                    if target == "ph" and c != couplings[0]:
                        continue            # pH does not depend on coupling: run once
                    y = _target_values(f, target)
                    for m in MODELS:
                        for scheme in ("random", "spatial"):
                            mt = cv_two_inputs(X, X, y, grp, specs[m], scheme, seed,
                                               _log_target(target))
                            add(experiment="core", corr_length_km=L,
                                coupling=(None if target == "ph" else c),
                                rep=rep, target=target, model=m, scheme=scheme,
                                error_scale=BASELINE_SCALE, arm="train_noisy", **mt)
        if progress:
            print(f"  core: corr_length={L} km done", flush=True)

    # ---- noise sweep: spatial CV, two arms ----------------------------------
    for rep in range(reps):
        seed = seed0 + rep
        f = S.make_field(seed, params, corr_length_km=DEFAULT_L, coupling=DEFAULT_C,
                         n_points=n_points)
        grp, _ = V.spatial_groups(f.coords, np.arange(len(f.ph)), blocks, seed)
        X_clean = _matrix(f, 0.0, params)
        for s in scales:
            X_s = _matrix(f, s, params)
            for target in TARGETS:
                y = _target_values(f, target)
                for m in MODELS:
                    for arm, (Xf, Xe) in dict(train_clean=(X_clean, X_s),
                                              train_noisy=(X_s, X_s)).items():
                        mt = cv_two_inputs(Xf, Xe, y, grp, specs[m], "spatial", seed,
                                           _log_target(target))
                        add(experiment="noise", corr_length_km=DEFAULT_L,
                            coupling=(None if target == "ph" else DEFAULT_C), rep=rep,
                            target=target, model=m, scheme="spatial", error_scale=s,
                            arm=arm, **mt)
        if progress:
            print(f"  noise: replicate {rep + 1}/{reps} done", flush=True)

    # ---- control: shuffled target must collapse to ~0 ------------------------
    for rep in range(reps):
        seed = seed0 + rep
        f = S.make_field(seed, params, corr_length_km=DEFAULT_L, coupling=DEFAULT_C,
                         n_points=n_points)
        X = _matrix(f, BASELINE_SCALE, params)
        grp, _ = V.spatial_groups(f.coords, np.arange(len(X)), blocks, seed)
        rng = np.random.default_rng([seed, 99])
        for target in TARGETS:
            y = rng.permutation(_target_values(f, target))
            for m in MODELS:
                mt = cv_two_inputs(X, X, y, grp, specs[m], "spatial", seed, _log_target(target))
                add(experiment="shuffled_control", corr_length_km=DEFAULT_L,
                    coupling=(None if target == "ph" else DEFAULT_C), rep=rep,
                    target=target, model=m, scheme="spatial", error_scale=BASELINE_SCALE,
                    arm="train_noisy", **mt)

    return pd.DataFrame(rows), params


# ---------------------------------------------------------------------------
# Summaries and hypothesis statements (computed, never asserted)
# ---------------------------------------------------------------------------

def _agg(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    g = df.groupby(by, dropna=False)["r2"]
    out = g.agg(r2_mean="mean", r2_sd="std", n_reps="count").reset_index()
    return out


def evaluate_hypotheses(df: pd.DataFrame) -> dict:
    learners = [m for m in MODELS if m != "mean_baseline"]
    out: dict = dict(useful_r2_threshold=USEFUL_R2)

    # H1: random R2 minus spatial R2, paired by replicate, SOC target
    core = df[(df.experiment == "core") & (df.target == "soc") & df.model.isin(learners)]
    wide = core.pivot_table(index=["corr_length_km", "coupling", "model", "rep"],
                            columns="scheme", values="r2").reset_index()
    wide["gap"] = wide["random"] - wide["spatial"]
    h1 = (wide.groupby(["corr_length_km", "coupling", "model"])["gap"]
          .agg(gap_mean="mean", gap_sd="std").reset_index())
    out["H1_validation_gap_soc"] = dict(
        definition="R2(random 5-fold) - R2(spatial blocks), SOC target, paired by replicate",
        by_setting=h1.round(4).to_dict("records"),
        share_of_settings_with_positive_gap=float((h1.gap_mean > 0).mean()),
        gap_mean_by_corr_length=h1.groupby("corr_length_km").gap_mean.mean().round(4).to_dict(),
    )

    # H2: skill vs error scale, by model and arm
    nz = df[(df.experiment == "noise") & df.model.isin(learners)]
    curve = _agg(nz, ["target", "model", "arm", "error_scale"])
    out["H2_noise_curves"] = curve.round(4).to_dict("records")
    top = curve[(curve.error_scale == curve.error_scale.max()) & (curve.arm == "train_noisy")]
    out["H2_spread_between_models_at_max_error"] = {
        t: float(top[top.target == t].r2_mean.max() - top[top.target == t].r2_mean.min())
        for t in TARGETS}

    # H3: largest tested error scale at which spatial R2 stays above the threshold
    be: dict = {}
    for t in TARGETS:
        for m in learners:
            for arm in ("train_clean", "train_noisy"):
                c = curve[(curve.target == t) & (curve.model == m) & (curve.arm == arm)]
                ok = c[c.r2_mean >= USEFUL_R2].error_scale
                be[f"{t}|{m}|{arm}"] = (None if ok.empty else float(ok.max()))
    out["H3_break_even_error_scale"] = dict(
        definition=f"largest tested error scale with mean spatial R2 >= {USEFUL_R2}; "
                   "null = never reached; the maximum tested scale = not exceeded "
                   "(no extrapolation)",
        tested_scales=sorted(float(x) for x in nz.error_scale.unique()),
        values=be)

    soc_by_c = (core[(core.scheme == "spatial") & (core.model == "random_forest")]
                .groupby(["corr_length_km", "coupling"]).r2.mean().round(4).reset_index())
    out["H3_soc_skill_vs_coupling"] = dict(
        note="SOC skill from the sensor channels as a function of the assumed "
             "coupling; this is the assumption, made visible.",
        spatial_r2_random_forest=soc_by_c.to_dict("records"))

    ctrl = df[df.experiment == "shuffled_control"]
    out["control_shuffled_target_r2_mean"] = ctrl.groupby("model").r2.mean().round(4).to_dict()
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--reps", type=int, default=5, help="replicate surveys (>=5 for SDs)")
    ap.add_argument("--seed0", type=int, default=20261104)
    ap.add_argument("--blocks", type=int, default=10)
    ap.add_argument("--n-points", type=int, default=None)
    ap.add_argument("--export", default="export")
    ap.add_argument("--quick", action="store_true",
                    help="small run for tests; results are flagged quick and not reportable")
    a = ap.parse_args(argv)

    reps, scales, Ls, Cs = a.reps, ERROR_SCALES, CORR_LENGTHS_KM, COUPLINGS
    n_points = a.n_points
    if a.quick:
        reps, scales, Ls, Cs = 2, [0.0, 1.0, 4.0], [2.0, 15.0], [0.0, 0.9]
        n_points = n_points or 120

    print(f"Part A: simulated survey, reps={reps}, quick={a.quick}")
    df, params = run(reps, a.seed0, a.blocks, scales, Ls, Cs, n_points)
    hyp = evaluate_hypotheses(df)

    out_dir = Path(a.export); out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "part_a_results.csv", index=False)
    result = dict(
        kind="simulation",
        is_real_data=False,
        part="A (sensor simulation)",
        schema_version=S.SCHEMA_VERSION,
        experiment_scope=dict(quick=bool(a.quick), reps=reps, seed0=a.seed0,
                              blocks=a.blocks, n_points=n_points or int(params["n_points"].value),
                              error_scales=list(scales), corr_lengths_km=list(Ls),
                              couplings=list(Cs), models=list(MODELS),
                              features=FEATURES, targets=list(TARGETS),
                              hyperparameters="fixed defaults (no nested tuning)"),
        parameters=S.parameter_table(params),
        n_parameters_assumed=sum(p.status == "assumed" for p in params.values()),
        n_parameters_sourced=sum(p.status == "sourced" for p in params.values()),
        hypotheses=hyp,
        limitations=LIMITATIONS,
        code_version=A.git_version(),
        package_versions=A.package_versions(),
    )
    (out_dir / "part_a_results.json").write_text(json.dumps(result, indent=2, default=float))
    print(f"wrote {out_dir / 'part_a_results.json'} and part_a_results.csv "
          f"({len(df)} scored runs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
