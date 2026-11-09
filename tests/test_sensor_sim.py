"""
tests/test_sensor_sim.py - the simulated sensor survey (Part A) must do what the
proposal says, and must not be able to overstate what it shows.

Each error term is checked in isolation with the others switched off, so a
failure points at one line of the measurement model.
"""
import dataclasses
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import afsis_validation as V
import sensor_experiment as E
import sensor_sim as S


def _params(**overrides):
    """Default parameters with some values replaced (status stays 'assumed')."""
    p = S.default_parameters()
    for k, v in overrides.items():
        p[k] = dataclasses.replace(p[k], value=v)
    return p


# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_same_seed_same_field_and_readings(self):
        a, b = S.make_field(11), S.make_field(11)
        assert np.array_equal(a.ph, b.ph) and np.array_equal(a.soc, b.soc)
        ra, rb = S.sensor_readings(a, 1.0), S.sensor_readings(b, 1.0)
        assert np.array_equal(ra["ph_sensor"], rb["ph_sensor"])

    def test_different_seed_different_field(self):
        assert not np.array_equal(S.make_field(1).ph, S.make_field(2).ph)

    def test_noise_draws_are_shared_across_error_scales(self):
        """Common random numbers: the scale, not a fresh sample, drives the change."""
        f = S.make_field(5)
        p = _params(ph_drift_total=0.0, ph_moist_cross=0.0)
        r1 = S.sensor_readings(f, 1.0, p)["ph_sensor"]
        r2 = S.sensor_readings(f, 2.0, p)["ph_sensor"]
        base = p["ph_gain"].value * f.ph + p["ph_offset"].value
        assert np.allclose(r2 - base, 2.0 * (r1 - base))


# ---------------------------------------------------------------------------
# Each term of the measurement model, in isolation
# ---------------------------------------------------------------------------

class TestMeasurementModel:
    def test_perfect_sensor_returns_truth(self):
        p = _params(ph_gain=1.0, ph_offset=0.0, moist_gain=1.0, moist_offset=0.0)
        f = S.make_field(3, p)
        r = S.sensor_readings(f, 0.0, p)
        assert np.allclose(r["ph_sensor"], f.ph)
        assert np.allclose(r["moisture_sensor"], f.moisture)

    def test_gain_and_offset_are_not_scaled_by_error_scale(self):
        f = S.make_field(3)
        p = S.default_parameters()
        r0 = S.sensor_readings(f, 0.0, p)["ph_sensor"]
        assert np.allclose(r0, p["ph_gain"].value * f.ph + p["ph_offset"].value)

    def test_drift_follows_sampling_order(self):
        p = _params(ph_gain=1.0, ph_offset=0.0, ph_noise_sd=0.0, ph_moist_cross=0.0,
                    ph_drift_total=0.30)
        f = S.make_field(8, p)
        resid = S.sensor_readings(f, 1.0, p)["ph_sensor"] - f.ph
        expect = 0.30 * f.order / (len(f.order) - 1)
        assert np.allclose(resid, expect)

    def test_cross_sensitivity_to_moisture(self):
        p = _params(ph_gain=1.0, ph_offset=0.0, ph_noise_sd=0.0, ph_drift_total=0.0,
                    ph_moist_cross=2.0)
        f = S.make_field(9, p)
        resid = S.sensor_readings(f, 1.0, p)["ph_sensor"] - f.ph
        assert np.allclose(resid, 2.0 * (f.moisture - p["moist_ref"].value))

    def test_random_noise_has_the_stated_sd(self):
        p = _params(ph_gain=1.0, ph_offset=0.0, ph_drift_total=0.0, ph_moist_cross=0.0,
                    ph_noise_sd=0.15)
        f = S.make_field(10, p, n_points=800)
        resid = S.sensor_readings(f, 1.0, p)["ph_sensor"] - f.ph
        assert abs(resid.std() - 0.15) < 0.02


# ---------------------------------------------------------------------------
# The synthetic field
# ---------------------------------------------------------------------------

class TestField:
    def test_values_are_physically_plausible(self):
        f = S.make_field(2)
        assert (f.soc > 0).all()
        assert (f.moisture >= 0.02).all() and (f.moisture <= 0.60).all()

    def test_nearby_points_are_more_alike_than_distant_ones(self):
        """The field is spatially structured: semivariance rises with distance."""
        f = S.make_field(4, corr_length_km=6.0, n_points=250)
        d = np.sqrt(((f.coords[:, None] - f.coords[None]) ** 2).sum(-1))
        sq = (f.ph[:, None] - f.ph[None]) ** 2
        iu = np.triu_indices(len(f.ph), 1)
        near = sq[iu][d[iu] < 2.0].mean()
        far = sq[iu][d[iu] > 10.0].mean()
        assert near < 0.6 * far

    @pytest.mark.parametrize("c", [0.0, 0.8])
    def test_coupling_sets_the_soc_correlation_with_ph_and_moisture(self, c):
        p = S.default_parameters()
        f = S.make_field(6, p, corr_length_km=0.3, coupling=c, n_points=600)
        zph = (f.ph - p["ph_mean"].value) / p["ph_sd"].value
        zm = (f.moisture - p["moist_mean"].value) / p["moist_sd"].value
        combo = (S._SOC_W_PH * zph + S._SOC_W_MOIST * zm) / math.hypot(S._SOC_W_PH, S._SOC_W_MOIST)
        r = np.corrcoef(f.z_soc, combo)[0, 1]
        assert abs(r - c) < 0.15

    @pytest.mark.parametrize("bad", [-0.1, 1.5])
    def test_coupling_out_of_range_is_rejected(self, bad):
        with pytest.raises(ValueError):
            S.make_field(1, coupling=bad)


# ---------------------------------------------------------------------------
# Honest labelling
# ---------------------------------------------------------------------------

class TestParameterTable:
    def test_every_parameter_is_labelled_sourced_or_assumed(self):
        for row in S.parameter_table(S.default_parameters()):
            assert row["status"] in {"assumed", "sourced"}, row

    def test_a_sourced_parameter_must_name_its_source(self):
        placeholder = S.Param(0, "", "").source
        for row in S.parameter_table(S.default_parameters()):
            if row["status"] == "sourced":
                assert row["source"] and row["source"] != placeholder, row

    def test_no_parameter_claims_a_datasheet_without_one(self):
        """Nothing is 'sourced' until a real document is supplied."""
        rows = S.parameter_table(S.default_parameters())
        assert all(r["status"] == "assumed" for r in rows)


# ---------------------------------------------------------------------------
# Validation hygiene
# ---------------------------------------------------------------------------

class TestNoLeakage:
    def _inputs(self):
        f = S.make_field(21, n_points=120)
        X = np.column_stack([*S.sensor_readings(f, 1.0).values()])
        grp, _ = V.spatial_groups(f.coords, np.arange(len(X)), 6, 21)
        return f, X, grp

    def test_no_fit_ever_sees_all_rows(self, monkeypatch):
        from sklearn.pipeline import Pipeline
        f, X, grp = self._inputs()
        seen = []
        real = Pipeline.fit

        def spy(self, Xf, y=None, **kw):
            seen.append(len(Xf))
            return real(self, Xf, y, **kw)

        monkeypatch.setattr(Pipeline, "fit", spy)
        E.cv_two_inputs(X, X, f.soc, grp, V.model_specs()["ridge"], "spatial", 1, True)
        assert seen and max(seen) < len(X)

    def test_whole_blocks_are_held_out_together(self):
        f, X, grp = self._inputs()
        for tr, te in V.outer_splits("spatial", X, f.ph, grp, 1):
            assert not set(grp[tr]) & set(grp[te])

    def test_folds_do_not_depend_on_noise_level(self):
        f = S.make_field(21, n_points=120)
        grp, _ = V.spatial_groups(f.coords, np.arange(120), 6, 21)
        a = V.outer_splits("spatial", np.zeros((120, 2)), f.ph, grp, 1)
        b = V.outer_splits("spatial", np.ones((120, 2)), f.ph, grp, 1)
        assert all(np.array_equal(x[1], y[1]) for x, y in zip(a, b))

    def test_train_clean_arm_is_fitted_on_clean_inputs(self):
        """Fit on clean, score on noisy must differ from noisy/noisy at scale > 0
        and match it at scale 0."""
        f = S.make_field(31, n_points=150)
        grp, _ = V.spatial_groups(f.coords, np.arange(150), 6, 31)
        spec = V.model_specs()["ridge"]
        clean = np.column_stack([*S.sensor_readings(f, 0.0).values()])
        noisy = np.column_stack([*S.sensor_readings(f, 4.0).values()])
        r_clean = E.cv_two_inputs(clean, noisy, f.ph, grp, spec, "spatial", 1, False)["r2"]
        r_noisy = E.cv_two_inputs(noisy, noisy, f.ph, grp, spec, "spatial", 1, False)["r2"]
        r_same0 = E.cv_two_inputs(clean, clean, f.ph, grp, spec, "spatial", 1, False)["r2"]
        assert r_clean != pytest.approx(r_noisy)
        assert r_same0 > r_noisy        # more error cannot help on this field


# ---------------------------------------------------------------------------
# The whole experiment, small
# ---------------------------------------------------------------------------

def _has_nan(o):
    if isinstance(o, float):
        return math.isnan(o)
    if isinstance(o, dict):
        return any(_has_nan(v) for v in o.values())
    if isinstance(o, list):
        return any(_has_nan(v) for v in o)
    return False


@pytest.fixture(scope="module")
def quick_result(tmp_path_factory):
    out = tmp_path_factory.mktemp("part_a")
    assert E.main(["--quick", "--n-points", "70", "--blocks", "6", "--export", str(out)]) == 0
    return json.loads((out / "part_a_results.json").read_text()), out


class TestExperimentOutput:
    def test_labelled_as_simulation_and_quick(self, quick_result):
        r, _ = quick_result
        assert r["kind"] == "simulation" and r["is_real_data"] is False
        assert r["experiment_scope"]["quick"] is True

    def test_no_parameter_is_reported_as_sourced(self, quick_result):
        r, _ = quick_result
        assert r["n_parameters_sourced"] == 0
        assert r["n_parameters_assumed"] == len(r["parameters"])

    def test_limitations_are_exported(self, quick_result):
        r, _ = quick_result
        text = " ".join(r["limitations"]).lower()
        assert "assumed" in text and "not how any real" in text

    def test_no_unfilled_nulls_or_nans_in_metrics(self, quick_result):
        r, _ = quick_result
        h = dict(r["hypotheses"])
        h.pop("H3_break_even_error_scale")       # null here means "never reached"
        assert not _has_nan(h)

    def test_all_three_hypotheses_are_evaluated(self, quick_result):
        h = quick_result[0]["hypotheses"]
        for key in ("H1_validation_gap_soc", "H2_noise_curves",
                    "H3_break_even_error_scale", "H3_soc_skill_vs_coupling"):
            assert key in h

    def test_break_even_is_never_extrapolated(self, quick_result):
        be = quick_result[0]["hypotheses"]["H3_break_even_error_scale"]
        tested = set(be["tested_scales"])
        assert all(v is None or v in tested for v in be["values"].values())

    def test_shuffled_target_has_no_skill(self, quick_result):
        ctrl = quick_result[0]["hypotheses"]["control_shuffled_target_r2_mean"]
        for model, r2 in ctrl.items():
            assert r2 < 0.15, (model, r2)

    def test_csv_is_written_and_complete(self, quick_result):
        import pandas as pd
        _, out = quick_result
        df = pd.read_csv(out / "part_a_results.csv")
        assert {"experiment", "target", "model", "scheme", "error_scale", "r2"} <= set(df.columns)
        assert set(df.experiment) == {"core", "noise", "shuffled_control"}

    def test_same_seed_reproduces_exactly(self, tmp_path):
        a, b = tmp_path / "a", tmp_path / "b"
        for d in (a, b):
            E.main(["--quick", "--n-points", "60", "--blocks", "6", "--export", str(d)])
        ja = json.loads((a / "part_a_results.json").read_text())["hypotheses"]
        jb = json.loads((b / "part_a_results.json").read_text())["hypotheses"]
        assert ja == jb
