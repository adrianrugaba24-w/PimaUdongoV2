"""
Additive pass: train-fold scores and target terciles for an existing bundle.

Why this exists
---------------
`afsis_experiment.py` reports out-of-fold scores only.  A model that memorises
the places it was trained on and a model that underfits everywhere can produce
the same spatial R2; the train-fold score is what tells them apart.  That
number has to come from the same folds, the same seeds and the same tuned
parameters as the reported run, so it cannot be computed after the fact from
results.json alone.

What it writes
--------------
  <export>/cv_supplement.json   per model, per CV design:
                                train-fold and out-of-fold r2/rmse/mae/rpiq,
                                mean and SD across seeds and across folds
  <export>/bands.json           terciles of the training target, in the
                                model's own unit, with their provenance
  <export>/sites.json           longitude, latitude and spatial fold for every
                                sampled site, so the partition can be plotted.
                                results.json records the fold of each site but
                                never the coordinate, and a map cannot be drawn
                                from a fold label alone.

What it does NOT write
----------------------
results.json, model_meta.json and model.joblib.  Their sha256 is taken before
and after and must be unchanged; the run aborts if it is not.  Nothing here
retrains or re-tunes the SHIPPED model: the shipped pipeline is not touched, and
the folds re-fit in memory are discarded when the process exits.

Verification
------------
Rebuilding the data and the folds independently could silently disagree with
the reported run, so every recomputed out-of-fold R2 and RMSE is diffed against
`results.validation_gap`.  A mismatch above 1e-9 means the reconstruction is
wrong and the train scores cannot be trusted, so the pass fails instead of
writing a plausible-looking file.

The same guard covers the map: `sites.json` pairs each coordinate with a fold
label, and a pair is only meaningful if the rows are in the order the recorded
`cluster_label` array assumes.  The recomputed row groups must equal that array
element for element, or the pass exits.

Run:
    python cv_supplement.py --root data/afsis_real --export export_afsis_real \
        --target "Total carbon" --features pH_H2O EC "Clay percent" "Sand percent" "Silt percent"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

import afsis_data as A
import afsis_validation as V

BUNDLE_FILES = ("results.json", "model_meta.json", "model.joblib")
TOLERANCE = 1e-9


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _num(x):
    """JSON-safe float: NaN/inf become None rather than an invalid JSON literal."""
    x = float(x)
    return x if np.isfinite(x) else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default="data/afsis_real")
    ap.add_argument("--export", default="export_afsis_real")
    ap.add_argument("--target", default="Total carbon")
    ap.add_argument("--features", nargs="+",
                    default=["pH_H2O", "EC", "Clay percent", "Sand percent", "Silt percent"])
    ap.add_argument("--blocks", type=int, default=10)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--seed0", type=int, default=20261104)
    ap.add_argument("--target-kind", dest="target_kind", default="soc", choices=["soc", "ph"])
    a = ap.parse_args(argv)

    t0 = time.time()
    export = Path(a.export)
    if not export.is_dir():
        sys.exit(f"--export {export} does not exist.")

    # The bundle must be untouched by this script.  Take the hashes first.
    before = {n: sha256(export / n) for n in BUNDLE_FILES}
    meta = json.loads((export / "model_meta.json").read_text())
    reported = json.loads((export / "results.json").read_text())
    if meta["results_sha256"] not in {
            before["results.json"],
            hashlib.sha256((export / "results.json").read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
            hashlib.sha256((export / "results.json").read_bytes().replace(b"\r\n", b"\n")
                           .replace(b"\n", b"\r\n")).hexdigest()}:
        sys.exit("results.json already disagrees with model_meta.json - fix the bundle first.")

    # ---------- rebuild exactly what the recorded run used -------------------
    df, manifest = A.load_raw(Path(a.root))
    overrides = {"target": a.target, "features": a.features, "target_kind": a.target_kind}
    schema = A.detect_schema(df, overrides)
    d, log = A.clean(df, schema, dict(depth=A.DEPTH_TARGET_CM, target_units="auto",
                                      lab_dupes="first"))
    units = A.data_card(d, schema, log, "Uganda")["target_units"]

    if list(schema.features) != list(reported["features"]):
        sys.exit(f"feature list mismatch: rebuilt {schema.features} vs bundle "
                 f"{reported['features']}. Pass the same --features as the original run.")
    if int(len(d)) != int(meta["n_rows"]):
        sys.exit(f"row count mismatch: rebuilt {len(d)} vs bundle {meta['n_rows']}.")

    X0 = d[schema.features].to_numpy(float)
    y = d[schema.target].to_numpy(float)
    ids = d[schema.group_key()].to_numpy()
    coords = d[[schema.lat, schema.lon]].to_numpy(float)
    log_target = bool(np.all(y > 0)) and schema.target_kind == "soc"

    seeds = list(range(a.seed0, a.seed0 + max(1, a.seeds)))
    row_groups, gdiag = V.spatial_groups(coords, ids, a.blocks, seeds[0])
    print(f"[setup] {len(d)} rows x {len(schema.features)} features | target={a.target} "
          f"({units}) | log-target={log_target} | {gdiag['blocks']} blocks | "
          f"{len(seeds)} seeds")

    if seeds != list(reported["validation"]["seeds"]) or \
            int(gdiag["blocks"]) != int(reported["validation"]["blocks"]):
        sys.exit("fold configuration differs from the bundle (seeds/blocks). "
                 "Pass the same --seeds/--seed0/--blocks as the original run.")

    # ---------- recompute E1 with train-fold scores --------------------------
    specs = V.model_specs()
    models, worst = {}, 0.0
    for name in specs:
        spec = specs[name]
        entry = {}
        for scheme in ("random", "spatial"):
            per_seed = []
            for seed in seeds:
                print(f"  [E1] {name:18s} {scheme:7s} seed {seed} ...", end="", flush=True)
                r = V.run_cv(X0, y, row_groups, spec, scheme, seed, log_target,
                             tune=True, collect_train=True)
                per_seed.append(r)
                print(f" R2 test={r['metrics']['r2']:+.4f} "
                      f"train={r['train']['r2_mean']:+.4f}")
            entry[scheme] = _aggregate(per_seed)
        models[name] = entry

    # ---------- verify against the reported run ------------------------------
    checks = []
    for g in reported["results"]["validation_gap"]:
        name = g["model"]
        for scheme, field in (("random", "r2_random"), ("spatial", "r2_spatial"),
                              ("random", "rmse_random"), ("spatial", "rmse_spatial")):
            metric = "r2" if field.startswith("r2") else "rmse"
            got = models[name][scheme][metric]["mean"]
            diff = abs(float(g[field]) - got)
            worst = max(worst, diff)
            checks.append(dict(model=name, field=field, reported=float(g[field]),
                               recomputed=got, abs_diff=diff))
    if worst > TOLERANCE:
        bad = max(checks, key=lambda c: c["abs_diff"])
        sys.exit(f"reconstruction does not match the reported run: {bad}. "
                 f"Refusing to write train scores derived from different folds.")

    # ---------- terciles of the training target ------------------------------
    lo, hi = float(np.min(y)), float(np.max(y))
    c1, c2 = (float(v) for v in np.percentile(y, [100.0 / 3.0, 200.0 / 3.0]))
    bands = dict(
        schema_version=1,
        method="terciles of the training target distribution",
        label_source="position in the distribution of sampled soils, not a quality grade",
        not_tuned="The cuts are the 33.3rd and 66.7th percentiles of the training "
                  "targets. They were not adjusted to make any band reachable.",
        target=reported["target"]["name"], unit=units,
        n=int(len(y)), observed_range=[lo, hi], cuts=[c1, c2],
        bands=[dict(key="lower_third", label="Lower third of the sampled soils",
                    range=[lo, c1], n=int(np.sum(y <= c1))),
               dict(key="middle_third", label="Middle third of the sampled soils",
                    range=[c1, c2], n=int(np.sum((y > c1) & (y <= c2)))),
               dict(key="upper_third", label="Upper third of the sampled soils",
                    range=[c2, hi], n=int(np.sum(y > c2)))],
        derived_from=dict(dataset_version=meta["training_data_version"],
                          model_version=meta["model_version"],
                          results_sha256=meta["results_sha256"]),
    )

    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    derived = dict(dataset_version=meta["training_data_version"],
                   model_version=meta["model_version"],
                   results_sha256=meta["results_sha256"])

    # ---------- sample locations, paired with the RECORDED fold labels -------
    # The coordinates come from the rebuilt frame, so the only thing standing
    # between them and a plotted fold is row order.  That is not assumed: the
    # row groups recomputed here must equal the array results.json already
    # stores, or nothing is written.
    recorded = (((reported.get("validation") or {}).get("blocking_diagnostics")
                 or {}).get("cluster_label"))
    row_fold = [int(v) for v in row_groups]
    if recorded is not None and [int(v) for v in recorded] != row_fold:
        sys.exit("recomputed row groups differ from "
                 "results.validation.blocking_diagnostics.cluster_label, so "
                 "coordinates cannot be paired with the recorded folds.")
    sites = dict(
        schema_version=1,
        purpose=("Sample locations for the partition map. Latitude and longitude "
                 "are NOT model inputs: this file exists so the spatial split can "
                 "be inspected, not to imply that location predicts carbon."),
        caption=("Sample locations from the source georeferences, coloured by the "
                 "spatial fold the site was held out in. No basemap and no marker "
                 "for a hypothetical field."),
        fold_source="results.validation.blocking_diagnostics.cluster_label",
        alignment=("recomputed row groups are identical, element for element, to "
                   "the cluster_label array already stored in results.json"),
        n=int(len(d)),
        fold_labels=sorted({int(v) for v in row_fold}),
        fold_sizes={str(k): int(row_fold.count(k)) for k in sorted(set(row_fold))},
        site=[str(v) for v in ids],
        lon=[float(v) for v in coords[:, 1]],
        lat=[float(v) for v in coords[:, 0]],
        fold=row_fold,
        derived_from=derived,
    )
    supplement = dict(
        schema_version=1,
        generated_at_utc=stamp,
        purpose="Train-fold scores and out-of-fold mean/SD for every model and CV "
                "design. Additive: results.json and model.joblib are not modified.",
        command="python cv_supplement.py " + " ".join(sys.argv[1:]),
        derived_from=dict(dataset_version=meta["training_data_version"],
                          model_version=meta["model_version"],
                          results_sha256=meta["results_sha256"],
                          target=reported["target"]["name"], unit=units,
                          seeds=seeds, blocks=int(gdiag["blocks"]),
                          folds=int(V.FOLDS), nested_tuning=True, log_target=log_target),
        bundle_files_sha256=before,
        models=models,
        verification=dict(tolerance=TOLERANCE, max_abs_diff_vs_results_json=worst,
                          n_checks=len(checks), checks=checks,
                          note="Out-of-fold R2 and RMSE were recomputed here and "
                               "diffed against results.validation_gap. Train-fold "
                               "scores come from the same folds and the same fitted "
                               "objects as those out-of-fold scores."),
    )

    (export / "cv_supplement.json").write_text(
        json.dumps(supplement, indent=1, default=str) + "\n", encoding="utf-8", newline="\n")
    (export / "bands.json").write_text(
        json.dumps(bands, indent=1, default=str) + "\n", encoding="utf-8", newline="\n")
    (export / "sites.json").write_text(
        json.dumps(sites, indent=1, default=str) + "\n", encoding="utf-8", newline="\n")

    # ---------- the bundle must be byte-identical ---------------------------
    after = {n: sha256(export / n) for n in BUNDLE_FILES}
    if after != before:
        changed = [n for n in BUNDLE_FILES if after[n] != before[n]]
        sys.exit(f"BUNDLE MODIFIED: {changed}. The pass is not additive; "
                 f"results.json/model.joblib must never change here.")
    print(f"[bundle] unchanged and hash-identical: {', '.join(BUNDLE_FILES)}")

    print(f"\n=== train vs out-of-fold (spatial) ===")
    for name, m in models.items():
        print(f"  {name:18s} R2 train={m['spatial']['r2']['train_mean']:+.3f} -> "
              f"test={m['spatial']['r2']['mean']:+.3f}   RMSE train="
              f"{m['spatial']['rmse']['train_mean']:.3f} -> test={m['spatial']['rmse']['mean']:.3f}")
    print(f"\n[bands] terciles at {c1:.3f} and {c2:.3f} {units} "
          f"(n={bands['bands'][0]['n']}/{bands['bands'][1]['n']}/{bands['bands'][2]['n']})")
    print(f"[sites] {sites['n']} locations x {len(sites['fold_labels'])} folds "
          f"{sites['fold_sizes']}")
    print(f"[verify] max |diff| vs results.json = {worst:.3e} over {len(checks)} checks")
    print(f"[written] {export/'cv_supplement.json'}, {export/'bands.json'} and "
          f"{export/'sites.json'} in {time.time() - t0:.1f}s")
    return 0


def _aggregate(per_seed: list[dict]) -> dict:
    """Mean/SD across seeds for test and train metrics of one (model, CV) cell."""
    out = {}
    for m in ("r2", "rmse", "mae", "rpiq"):
        test = np.array([r["metrics"][m] for r in per_seed], float)
        train = np.array([r["train"][f"{m}_mean"] for r in per_seed], float)
        train_sd = np.array([r["train"][f"{m}_sd"] for r in per_seed], float)
        test = test[np.isfinite(test)]
        train = train[np.isfinite(train)]
        out[m] = dict(
            mean=_num(test.mean()) if len(test) else None,
            sd=_num(test.std(ddof=1)) if len(test) > 1 else (0.0 if len(test) else None),
            train_mean=_num(train.mean()) if len(train) else None,
            train_sd=_num((np.nanmean(train_sd) if len(train_sd) else None)) if len(train) else None,
            n_seeds=int(len(per_seed)),
            fold_n_test=[int(f["n_test"]) for f in per_seed[0]["per_fold"]],
            fold_n_train=[int(f["n_train"]) for f in per_seed[0]["train"]["per_fold"]],
            train_per_fold_mean=_num(float(np.mean(
                [f["r2"] for f in per_seed[0]["train"]["per_fold"]]))),
        )
    return out


if __name__ == "__main__":
    raise SystemExit(main())
