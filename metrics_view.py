"""
The single payload the interface reads.

`/api/metrics` composes this from artefacts that already exist:

    results.json        reported CV, noise sweep, interval, folds, limitations
    cv_supplement.json  train-fold scores and per-fold SDs (optional, additive)
    bands.json          terciles of the training target (optional, additive)
    model_meta.json     target name, unit, model version, dataset version

Nothing here recomputes an experiment, re-fits a model or fills a gap with a
guess.  Where an artefact is absent the field is null and `sources` says why, so
the interface can print "Not available" instead of a number it made up.
"""
from __future__ import annotations

FEATURE_GROUP = "laboratory_measurements"
FEATURE_GROUP_LABEL = "Laboratory measurements (sensor error simulated)"
FEATURE_GROUP_NOTE = (
    "The noise experiment perturbs every feature in proportion to its own "
    "training-fold spread, so no feature is treated as a sensor reading and no "
    "feature is exempt. The five inputs are laboratory measurements; the "
    "simulation asks what would happen if a field instrument read them with that "
    "much error. No instrument was used.")

METRICS = ("r2", "rmse", "mae", "rpiq")


def _short_unit(unit):
    """
    A display form of the unit the bundle records.

    The label on every screen is composed from `target_name` and this, so the
    wording follows the bundle instead of being typed into the page.  Only
    units that unambiguously mean "per cent" are shortened; anything else is
    shown exactly as recorded, because guessing a shorter form of an unfamiliar
    unit is how a screen ends up mislabelling a measurement.
    """
    if not isinstance(unit, str) or not unit.strip():
        return None
    key = unit.strip().lower()
    if key.startswith("percent") or "g/100 g" in key or key == "%":
        return "%"
    return unit.strip()


def _f(x):
    """float or None - never NaN, never a string."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v and abs(v) != float("inf") else None


def _stale(artifact: dict | None, meta: dict) -> bool:
    """Does this additive artefact describe the bundle now loaded?"""
    if not artifact:
        return False
    got = (artifact.get("derived_from") or {}).get("model_version")
    return bool(got) and got != meta.get("model_version")


def _noise_zero_lookup(results: dict) -> dict:
    """MAE/RPIQ per (model, CV) at zero added noise: the clean-noise cell."""
    out = {}
    for row in (results.get("results") or {}).get("noise_sweep") or []:
        if _f(row.get("noise")) == 0.0 and row.get("arm") == "train_clean":
            out[(row.get("model"), row.get("cv"))] = row
    return out


def _fold_counts(results: dict) -> list[dict]:
    diag = (results.get("validation") or {}).get("blocking_diagnostics") or {}
    sizes = diag.get("cluster_sizes") or {}
    try:
        items = sorted(((int(k), int(v)) for k, v in sizes.items()), key=lambda kv: kv[0])
    except (TypeError, ValueError):
        return []
    return [dict(fold=k, n=n) for k, v in items for n in [v]]


def build_metrics(results: dict, meta: dict, *, supplement: dict | None = None,
                  bands: dict | None = None, model_dir: str = "") -> dict:
    res = results.get("results") or {}
    card = (results.get("data") or {}).get("data_card") or {}
    valley = results.get("validation") or {}
    zero = _noise_zero_lookup(results)
    sup_models = (supplement or {}).get("models") or {}
    # Present AND written against the model now loaded.  An absent file is not
    # "not stale": it is absent, and the interface has to say so.
    sup_ok = bool(supplement) and not _stale(supplement, meta)
    bands_ok = bool(bands) and not _stale(bands, meta)

    features = []
    for name in meta.get("feature_names") or results.get("features") or []:
        rng = (results.get("feature_ranges") or {}).get(name) or {}
        features.append(dict(
            name=name,
            unit=(results.get("feature_units") or {}).get(name),
            group=FEATURE_GROUP,
            training_range=dict(p5=_f(rng.get("p5")), median=_f(rng.get("median")),
                                p95=_f(rng.get("p95"))),
            physical_bounds=(results.get("feature_bounds") or {}).get(name),
            perturbed_by_noise_sweep=True,
        ))

    models = []
    for row in res.get("validation_gap") or []:
        name = row.get("model")
        entry = dict(name=name,
                     beats_field_mean=row.get("spatial_beats_baseline"),
                     gap=dict(mean=_f(row.get("gap_mean")), sd=_f(row.get("gap_sd"))),
                     tuned_params=row.get("tuned_params"))
        for scheme in ("random", "spatial"):
            block = dict(
                r2=_f(row.get(f"r2_{scheme}")), r2_sd=None,
                rmse=_f(row.get(f"rmse_{scheme}")), rmse_sd=None,
                mae=None, mae_sd=None, rpiq=None, rpiq_sd=None,
                train_r2=None, train_rmse=None, train_mae=None, train_rpiq=None,
                train_r2_sd=None, source="results.validation_gap")
            z = zero.get((name, scheme))
            if z:
                for m in ("mae", "rpiq"):
                    block[m] = _f(z.get(f"{m}_mean"))
                    block[f"{m}_sd"] = _f(z.get(f"{m}_sd"))
                block["rmse_sd"] = _f(z.get("rmse_sd"))
                block["r2_sd"] = _f(z.get("r2_sd"))
                block["source"] = "results.validation_gap + noise_sweep@0"
            s = (sup_models.get(name) or {}).get(scheme)
            if s and sup_ok:
                for m in METRICS:
                    cell = s.get(m) or {}
                    block[m] = _f(cell.get("mean")) if _f(cell.get("mean")) is not None else block[m]
                    block[f"{m}_sd"] = _f(cell.get("sd"))
                    block[f"train_{m}"] = _f(cell.get("train_mean"))
                    block[f"train_{m}_sd"] = _f(cell.get("train_sd"))
                block["source"] = "cv_supplement.json (train and test)"
            entry[scheme] = block
        models.append(entry)

    interval = dict(res.get("interval") or {})
    interval_block = dict(
        nominal=_f(interval.get("nominal")),
        empirical_coverage=_f(interval.get("empirical_coverage")),
        coverage_sd=_f(interval.get("coverage_sd")),
        mean_width=_f(interval.get("mean_width")),
        half_width=_f(interval.get("half_width")),
        median_target=_f(interval.get("median_target")),
        model=interval.get("model"),
        method=interval.get("method"),
        note=interval.get("honest_note"),
        # Kept separate on purpose: the calibrated band is the interval; the
        # spatial RMSE is an accuracy figure and is NOT a width to add and
        # subtract.  Mixing them would make the stated coverage describe a band
        # nobody is showing.
        spatial_rmse_of_interval_model=_f(next(
            (m["spatial"].get("rmse") for m in models if m["name"] == interval.get("model")),
            None)),
    )

    noise_points = []
    for row in res.get("noise_sweep") or []:
        noise_points.append(dict(
            model=row.get("model"), cv=row.get("cv"), arm=row.get("arm"),
            noise=_f(row.get("noise")),
            r2=_f(row.get("r2_mean")), r2_sd=_f(row.get("r2_sd")),
            rmse=_f(row.get("rmse_mean")), rmse_sd=_f(row.get("rmse_sd")),
            mae=_f(row.get("mae_mean")), rpiq=_f(row.get("rpiq_mean"))))

    return dict(
        schema_version=1,
        target=dict(
            name=meta.get("target_name"),
            unit=meta.get("target_units"),
            unit_short=_short_unit(meta.get("target_units")),
            # "Total carbon (%)", built from the bundle.  A page may render this
            # or compose its own from name + unit_short; it may not spell it.
            display_label=(
                f"{meta.get('target_name')} ({_short_unit(meta.get('target_units'))})"
                if meta.get("target_name") and _short_unit(meta.get("target_units"))
                else meta.get("target_name")),
            naming_note=("The displayed label is composed from target_name and "
                         "target_units in model_meta.json. Any document that still "
                         "names the target differently has to be brought into line "
                         "with the bundle before it is published."),
            log_transformed=bool(meta.get("log_target")),
            is_sample_data=not bool((results.get("data") or {}).get("is_real_data")),
            data_kind=(results.get("data") or {}).get("kind"),
            dataset_version=meta.get("training_data_version"),
            model_version=meta.get("model_version"),
            model_dir=model_dir,
            n_rows=meta.get("n_rows"),
            n_sites=card.get("n_sites"),
            n_countries=len(card.get("countries") or {}) or None,
            licence=(results.get("data") or {}).get("licence"),
        ),
        features=features,
        feature_group=dict(key=FEATURE_GROUP, label=FEATURE_GROUP_LABEL,
                           note=FEATURE_GROUP_NOTE,
                           grouping_rule="one group, because the sweep perturbs "
                                          "every feature; a sensor/laboratory split "
                                          "would have no member on the sensor side"),
        models=models,
        baseline_rmse=dict(random=_f((res.get("baseline_rmse") or {}).get("random")),
                           spatial=_f((res.get("baseline_rmse") or {}).get("spatial"))),
        interval=interval_block,
        bands=bands if bands_ok else None,
        bands_note=("terciles of the training target, stored in the model's unit"
                    if bands_ok else
                    "no band thresholds for this bundle (bands.json absent, or derived "
                    "from a different model version)"),
        noise=dict(
            levels=[_f(v) for v in valley.get("noise_levels") or []],
            arms=list(valley.get("noise_arms") or []),
            points=noise_points,
            break_even=(results.get("headline") or {}).get("break_even_noise") or {},
            break_even_label="Break-even with the field-mean baseline",
            note="Gaussian error added as a fraction of each feature's training-fold "
                 "spread. Two arms: clean-train/noisy-test, and noisy-train/noisy-test.",
        ),
        folds=dict(
            n_folds=(valley.get("folds")),
            inner_folds=valley.get("inner_folds"),
            n_seeds=valley.get("n_seeds"),
            seeds=list(valley.get("seeds") or []),
            blocks=valley.get("blocks"),
            grouping=valley.get("spatial_grouping"),
            counts=_fold_counts(results),
            partition_note=valley.get("spatial_partition_note"),
        ),
        measured_sensor_error=None,
        measured_sensor_error_note="Not measured yet",
        train_scores_available=bool(sup_ok and sup_models),
        limitations=list(results.get("limitations") or []),
        sources=dict(
            results="results.json",
            supplement=("cv_supplement.json" if sup_ok and sup_models else None),
            bands=("bands.json" if bands_ok else None),
            note="Every number above is copied from one of these files. Ratios the "
                 "interface derives (for example width / median) are arithmetic on "
                 "two published fields, not new measurements."),
    )
