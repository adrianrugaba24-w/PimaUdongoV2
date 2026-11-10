"""
tests/test_metrics_api.py  -  the /api/* views.

Two things are checked here and nothing else:

  * the payload's SHAPE and PROVENANCE - every label, unit and metric comes from
    a file, never from a literal in the code;
  * the COVERAGE test - every number in the payload is walked and matched back
    to a number that exists in results.json, model_meta.json (or the additive
    files when they are present).  A number that cannot be traced is a number
    somebody typed, and this suite refuses those.

These run on the SYNTHETIC export from conftest.py, which has no
cv_supplement.json and no bands.json.  That is deliberate: the absent-file
behaviour (null, plus a note saying why) is the behaviour a freshly generated
bundle will meet.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import reliability

REAL_EXPORT = ROOT / "export_afsis_real"

FEATURE_GROUP_LABEL = "Laboratory measurements (sensor error simulated)"
BREAK_EVEN_LABEL = "Break-even with the field-mean baseline"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _numbers(obj, path="$"):
    """Yield (path, float) for every real number in a JSON-shaped object."""
    if isinstance(obj, bool) or obj is None:
        return
    if isinstance(obj, (int, float)):
        yield path, float(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _numbers(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _numbers(v, f"{path}[{i}]")


def _load(path):
    return json.loads(Path(path).read_text())


def _model_meta(export_dir):
    return _load(Path(export_dir) / "model_meta.json")


def _allowed_numbers(results, meta, export_dir):
    """
    Every number that exists in a source file, plus the two counts the payload
    derives by arithmetic on a structure (a dict length and a dict key).  Those
    two are computed here from results.json, not written down.
    """
    allowed = set()
    for source in (results, meta):
        allowed.update(v for _, v in _numbers(source))
    card = (results.get("data") or {}).get("data_card") or {}
    allowed.add(float(len(card.get("countries") or {})))
    for k in ((results.get("validation") or {}).get("blocking_diagnostics") or {}) \
            .get("cluster_sizes") or {}:
        allowed.add(float(k))
    for name in ("cv_supplement.json", "bands.json"):
        p = Path(export_dir) / name
        if p.is_file():
            allowed.update(v for _, v in _numbers(_load(p)))
    return allowed


# Constants that are not measurements.
NOT_A_MEASUREMENT = {"$", "$.schema_version", "$.band.schema_version"}


# ---------------------------------------------------------------------------
# /api/metrics - shape and provenance
# ---------------------------------------------------------------------------

class TestMetricsShape:
    def test_200(self, client):
        assert client.get("/api/metrics").status_code == 200

    def test_top_level_keys(self, client):
        body = client.get("/api/metrics").json()
        for key in ("schema_version", "target", "features", "feature_group",
                    "models", "baseline_rmse", "interval", "bands", "bands_note",
                    "noise", "folds", "measured_sensor_error", "limitations",
                    "sources", "train_scores_available"):
            assert key in body, f"/api/metrics is missing {key}"

    def test_target_label_and_unit_come_from_the_metadata(self, client,
                                                          synthetic_export, meta):
        """2a: the screen reads its wording from the bundle, it does not spell it."""
        body = client.get("/api/metrics").json()
        m = _model_meta(synthetic_export)
        assert body["target"]["name"] == m["target_name"]
        assert body["target"]["name"] == meta["target"]["name"]
        assert body["target"]["unit"] == m["target_units"]
        assert body["target"]["unit"], "the target unit may not be blank"

    def test_target_is_marked_synthetic_when_it_is(self, client, meta):
        t = client.get("/api/metrics").json()["target"]
        assert t["is_sample_data"] == (not meta["data"]["is_real_data"])

    def test_display_label_is_composed_from_the_metadata(self, client, synthetic_export):
        """2a: the wording on every screen follows the bundle, it is not typed."""
        t = client.get("/api/metrics").json()["target"]
        m = _model_meta(synthetic_export)
        assert t["unit_short"] == "%"
        assert t["display_label"] == f"{m['target_name']} (%)"
        assert t["display_label"].startswith(m["target_name"])

    def test_the_label_carries_no_word_the_bundle_does_not_use(self, client,
                                                              synthetic_export):
        t = client.get("/api/metrics").json()["target"]
        m = _model_meta(synthetic_export)
        assert m["target_name"].lower() in t["display_label"].lower()

    def test_a_document_naming_the_target_differently_must_follow(self, client):
        note = client.get("/api/metrics").json()["target"]["naming_note"]
        assert "brought into line" in note

    def test_versions_match_the_bundle(self, client, synthetic_export, meta):
        t = client.get("/api/metrics").json()["target"]
        m = _model_meta(synthetic_export)
        assert t["model_version"] == m["model_version"]
        assert t["dataset_version"] == m["training_data_version"]


class TestFeatures:
    def test_the_model_s_features_and_no_others(self, client, meta):
        body = client.get("/api/metrics").json()
        assert [f["name"] for f in body["features"]] == list(meta["features"])

    def test_one_group_labelled_as_laboratory_measurements(self, client):
        body = client.get("/api/metrics").json()
        assert {f["group"] for f in body["features"]} == {"laboratory_measurements"}
        assert body["feature_group"]["label"] == FEATURE_GROUP_LABEL

    def test_grouping_rule_says_why_there_is_no_sensor_split(self, client):
        rule = client.get("/api/metrics").json()["feature_group"]["grouping_rule"]
        assert "sensor" in rule.lower()
        assert "every feature" in rule.lower()

    def test_the_sweep_perturbation_is_stated_per_feature(self, client):
        feats = client.get("/api/metrics").json()["features"]
        assert all(f["perturbed_by_noise_sweep"] is True for f in feats)

    def test_ranges_come_from_results_json(self, client, meta):
        feats = {f["name"]: f for f in client.get("/api/metrics").json()["features"]}
        for name, rng in meta["feature_ranges"].items():
            assert feats[name]["training_range"]["median"] == rng["median"]
            assert feats[name]["training_range"]["p5"] == rng["p5"]
            assert feats[name]["training_range"]["p95"] == rng["p95"]

    def test_physical_bounds_come_from_results_json(self, client, meta):
        feats = {f["name"]: f for f in client.get("/api/metrics").json()["features"]}
        for name, bounds in meta["feature_bounds"].items():
            assert feats[name]["physical_bounds"] == bounds


class TestModels:
    def test_every_cv_model_is_present(self, client, meta):
        body = client.get("/api/metrics").json()
        assert [m["name"] for m in body["models"]] == \
            [r["model"] for r in meta["results"]["validation_gap"]]

    def test_spatial_r2_matches_results_json(self, client, meta):
        by_name = {m["name"]: m for m in client.get("/api/metrics").json()["models"]}
        for row in meta["results"]["validation_gap"]:
            assert by_name[row["model"]]["spatial"]["r2"] == row["r2_spatial"]
            assert by_name[row["model"]]["random"]["r2"] == row["r2_random"]

    def test_gap_and_baseline_flag_are_carried(self, client, meta):
        by_name = {m["name"]: m for m in client.get("/api/metrics").json()["models"]}
        for row in meta["results"]["validation_gap"]:
            got = by_name[row["model"]]
            assert got["gap"]["mean"] == row["gap_mean"]
            assert got["beats_field_mean"] == row["spatial_beats_baseline"]

    def test_baseline_rmse_is_carried(self, client, meta):
        body = client.get("/api/metrics").json()
        assert body["baseline_rmse"]["spatial"] == \
            meta["results"]["baseline_rmse"]["spatial"]


class TestInterval:
    def test_split_conformal_band_is_kept_as_reported(self, client, meta):
        iv = client.get("/api/metrics").json()["interval"]
        src = meta["results"]["interval"]
        assert iv["nominal"] == src["nominal"]
        assert iv["empirical_coverage"] == src["empirical_coverage"]
        assert iv["coverage_sd"] == src["coverage_sd"]
        assert iv["mean_width"] == src["mean_width"]
        assert iv["half_width"] == src["half_width"]
        assert iv["method"] == src["method"]

    def test_mean_width_is_twice_the_half_width(self, client, meta):
        iv = client.get("/api/metrics").json()["interval"]
        assert iv["mean_width"] == pytest.approx(2 * iv["half_width"], rel=1e-12)

    def test_spatial_rmse_is_a_separate_field(self, client, meta):
        """6a: the band is the interval; the RMSE is accuracy, never a width."""
        body = client.get("/api/metrics").json()
        iv = body["interval"]
        row = next(r for r in meta["results"]["validation_gap"]
                   if r["model"] == iv["model"])
        assert iv["spatial_rmse_of_interval_model"] == row["rmse_spatial"]
        assert iv["spatial_rmse_of_interval_model"] != iv["half_width"]


class TestNoise:
    def test_levels_and_arms_match(self, client, meta):
        noise = client.get("/api/metrics").json()["noise"]
        assert noise["levels"] == meta["validation"]["noise_levels"]
        assert noise["arms"] == meta["validation"]["noise_arms"]

    def test_break_even_label_is_the_agreed_wording(self, client):
        assert client.get("/api/metrics").json()["noise"]["break_even_label"] == \
            BREAK_EVEN_LABEL

    def test_break_even_values_match_headline(self, client, meta):
        noise = client.get("/api/metrics").json()["noise"]
        assert noise["break_even"] == meta["headline"]["break_even_noise"]

    def test_every_sweep_point_is_carried(self, client, meta):
        got = client.get("/api/metrics").json()["noise"]["points"]
        assert len(got) == len(meta["results"]["noise_sweep"])
        src = {(r["model"], r["cv"], r["arm"], r["noise"])
               for r in meta["results"]["noise_sweep"]}
        assert {(p["model"], p["cv"], p["arm"], p["noise"]) for p in got} == src


class TestAbsentArtefacts:
    def test_no_bands_file_means_no_bands(self, client, synthetic_export):
        assert not (Path(synthetic_export) / "bands.json").is_file()
        body = client.get("/api/metrics").json()
        assert body["bands"] is None
        assert "no band thresholds" in body["bands_note"]

    def test_no_supplement_means_no_train_scores(self, client, synthetic_export):
        assert not (Path(synthetic_export) / "cv_supplement.json").is_file()
        body = client.get("/api/metrics").json()
        assert body["train_scores_available"] is False
        for m in body["models"]:
            for scheme in ("random", "spatial"):
                assert m[scheme]["train_r2"] is None
                assert m[scheme]["train_rmse"] is None

    def test_sources_say_what_is_missing(self, client):
        src = client.get("/api/metrics").json()["sources"]
        assert src["results"] == "results.json"
        assert src["bands"] is None
        assert src["supplement"] is None

    def test_sensor_error_is_not_invented(self, client):
        body = client.get("/api/metrics").json()
        assert body["measured_sensor_error"] is None
        assert body["measured_sensor_error_note"] == "Not measured yet"


class TestLimitations:
    def test_limitations_are_relayed_verbatim(self, client, meta):
        assert client.get("/api/metrics").json()["limitations"] == \
            list(meta["limitations"])


# ---------------------------------------------------------------------------
# Coverage: no displayed number may be untraceable
# ---------------------------------------------------------------------------

class TestDisplayedNumbersAreTraceable:
    def test_every_number_in_the_payload_exists_in_a_source_file(
            self, client, synthetic_export, meta):
        body = client.get("/api/metrics").json()
        allowed = _allowed_numbers(meta, _model_meta(synthetic_export), synthetic_export)
        untraceable = [(path, value) for path, value in _numbers(body)
                       if path not in NOT_A_MEASUREMENT and value not in allowed]
        assert not untraceable, (
            "these numbers appear in /api/metrics but in no source file, so "
            f"somebody typed them: {untraceable[:8]}")

    def test_the_walk_actually_walks(self, client):
        """A coverage test that inspects nothing always passes."""
        found = list(_numbers(client.get("/api/metrics").json()))
        assert len(found) > 50

    def test_predict_interval_is_the_reported_width(self, client, meta):
        """The one arithmetic the API does is pred +/- half_width, and it shows."""
        from tests.test_api import median_payload
        body = client.post("/api/predict", json=median_payload(meta)).json()
        assert body["interval"]["high"] - body["interval"]["low"] == \
            pytest.approx(meta["results"]["interval"]["mean_width"], rel=1e-9)


# ---------------------------------------------------------------------------
# /api/predict
# ---------------------------------------------------------------------------

class TestApiPredict:
    @staticmethod
    def payload(meta):
        from tests.test_api import median_payload
        return median_payload(meta)

    def test_200(self, client, meta):
        assert client.post("/api/predict", json=self.payload(meta)).status_code == 200

    def test_same_point_estimate_as_predict(self, client, meta):
        old = client.post("/predict", json=self.payload(meta)).json()
        new = client.post("/api/predict", json=self.payload(meta)).json()
        assert new["prediction"] == old["prediction"]
        assert new["prediction_unclamped"] is not None

    def test_bounds_are_the_conformal_band_unclipped(self, client, meta):
        body = client.post("/api/predict", json=self.payload(meta)).json()
        half = meta["results"]["interval"]["half_width"]
        assert body["interval"]["low"] == pytest.approx(body["prediction"] - half)
        assert body["interval"]["high"] == pytest.approx(body["prediction"] + half)
        assert body["interval"]["below_zero"] == (body["interval"]["low"] < 0)

    def test_spatial_rmse_is_reported_separately(self, client, meta):
        body = client.post("/api/predict", json=self.payload(meta)).json()
        iv = meta["results"]["interval"]
        row = next(r for r in meta["results"]["validation_gap"]
                   if r["model"] == iv["model"])
        assert body["accuracy"]["spatial_rmse"] == row["rmse_spatial"]
        assert body["accuracy"]["interval_model"] == iv["model"]

    def test_carries_the_wording_the_screen_shows(self, client, meta):
        body = client.post("/api/predict", json=self.payload(meta)).json()
        assert body["target"]["name"] == meta["target"]["name"]
        assert body["target"]["unit"] == meta["target"]["units"]

    def test_no_bands_means_no_band_claimed(self, client, meta):
        """Without bands.json the placement is withheld, not guessed."""
        band = client.post("/api/predict", json=self.payload(meta)).json()["band"]
        assert band["confidence"] == "Low"
        assert band["band"] is None
        assert band["message"] == reliability.NO_BANDS
        assert band["rules"] == ["R3_no_bands"]

    def test_with_bands_the_placement_appears(self, client, meta, api, monkeypatch):
        """
        Plumbing only: this fixture band is deliberately wide, so the narrow
        synthetic interval falls inside one third and the R6 path is exercised
        end to end.  It is not a threshold for any real bundle and nothing from
        this test appears in a result.
        """
        plumbing = dict(cuts=[-50.0, 50.0],
                        bands=[dict(key="lower_third",
                                    label="Lower third of the sampled soils"),
                               dict(key="middle_third",
                                    label="Middle third of the sampled soils"),
                               dict(key="upper_third",
                                    label="Upper third of the sampled soils")])
        monkeypatch.setitem(api.METRICS, "bands", plumbing)
        band = client.post("/api/predict", json=self.payload(meta)).json()["band"]
        assert band["confidence"] == "High"
        assert band["band"] in {b["label"] for b in plumbing["bands"]}
        assert band["band_key"] in {"lower_third", "middle_third", "upper_third"}

    def test_out_of_domain_input_is_not_placed_in_a_band(self, client, meta):
        from tests.test_api import _ood_case
        feat, value = _ood_case(meta)
        p = self.payload(meta)
        p["values"][feat] = value
        body = client.post("/api/predict", json=p).json()
        assert body["band"]["confidence"] == "Low"
        assert body["band"]["out_of_range"][0]["feature"] == feat
        assert reliability.LAB_LINE in body["band"]["message"]

    def test_impossible_value_is_still_422(self, client, meta):
        clay = next(f for f in meta["features"]
                    if "clay" in f.lower() and meta["feature_bounds"][f][1] == 100.0)
        p = self.payload(meta)
        p["values"][clay] = 140.0
        r = client.post("/api/predict", json=p)
        assert r.status_code == 422
        assert r.json()["detail"]["error"] == "impossible_value"

    def test_missing_feature_is_still_422(self, client, meta):
        r = client.post("/api/predict", json={"values": {meta["features"][0]: 6.0}})
        assert r.status_code == 422
        assert r.json()["detail"]["error"] == "missing_features"


class TestPredictIsUntouched:
    def test_predict_did_not_grow_a_band_block(self, client, meta):
        from tests.test_api import median_payload
        body = client.post("/predict", json=median_payload(meta)).json()
        assert "band" not in body
        assert "accuracy" not in body

    def test_predict_still_clips_its_lower_bound(self, client, meta):
        """The old behaviour stays as it was; only /api/predict differs."""
        from tests.test_api import median_payload
        body = client.post("/predict", json=median_payload(meta)).json()
        assert body["low"] >= 0.0
        assert body["low"] == max(0.0, body["prediction"] -
                                  meta["results"]["interval"]["half_width"])


# ---------------------------------------------------------------------------
# The real bundle, when it is on disk: the honest sentence must be the one
# that will actually be shown.
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not (REAL_EXPORT / "bands.json").is_file(),
                    reason="export_afsis_real has not been through cv_supplement.py")
def test_real_interval_is_wider_than_one_third():
    """
    5a, checked against the shipped artefacts: with cuts from the training
    target and the calibrated half-width, R4 fires for every prediction, so the
    screen must say "The estimate is too wide to place in a band."  If this ever
    fails, a band has become reachable and the copy needs revisiting - not the
    cuts.
    """
    bands = _load(REAL_EXPORT / "bands.json")
    results = _load(REAL_EXPORT / "results.json")
    half = results["results"]["interval"]["half_width"]
    inner = bands["cuts"][1] - bands["cuts"][0]
    assert 2 * half >= inner
    out = reliability.gate(
        {f: results["feature_ranges"][f]["median"] for f in results["features"]},
        1.0, 1.0 - half, 1.0 + half,
        feature_ranges=results["feature_ranges"], bands=bands)
    assert out["message"] == "The estimate is too wide to place in a band."
