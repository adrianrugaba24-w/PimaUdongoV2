"""
tests/test_ph_target.py - pH as a second target (SLR Step 1).

pH must never be its own feature, must not be treated as carbon (no unit
inference, no carbon bounds), and must not be log-transformed again.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import afsis_data as A

CFG = dict(depth=A.DEPTH_TARGET_CM, target_units="auto", lab_dupes="first")


@pytest.fixture(scope="module")
def frame(synthetic_afsis_root):
    return A.load(synthetic_afsis_root)


class TestSchema:
    def test_default_target_is_still_carbon(self, frame):
        s = A.detect_schema(frame)
        assert s.target_kind == "soc"
        assert "ph" not in s.target.lower().replace("soc", "")

    def test_ph_target_is_a_ph_column(self, frame):
        s = A.detect_schema(frame, {"target_kind": "ph"})
        assert s.target_kind == "ph"
        assert A.find([s.target], r"(^|[^a-z])ph([^a-z]|$)")

    def test_ph_is_never_its_own_feature(self, frame):
        s = A.detect_schema(frame, {"target_kind": "ph"})
        assert s.target not in s.features
        assert not any(A.find([f], r"(^|[^a-z])ph([^a-z]|$)") for f in s.features)

    def test_other_sensor_proxies_remain_features(self, frame):
        s = A.detect_schema(frame, {"target_kind": "ph"})
        assert len(s.features) >= 3

    def test_unknown_kind_is_rejected(self, frame):
        with pytest.raises(ValueError):
            A.detect_schema(frame, {"target_kind": "nitrogen"})


class TestCleaning:
    def test_ph_target_uses_ph_bounds_and_units(self, frame):
        s = A.detect_schema(frame, {"target_kind": "ph"})
        d, log = A.clean(frame, s, CFG)
        assert len(d) > 0
        assert d[s.target].between(0, 14).all() and (d[s.target] > 0).all()
        used = next(l for l in log if "target_units" in l)
        assert used["target_units"] == "pH units"
        assert "dimensionless" in used["units_basis"]

    def test_default_cleaning_is_unchanged_for_carbon(self, frame):
        s = A.detect_schema(frame)
        _, log = A.clean(frame, s, CFG)
        used = next(l for l in log if "target_units" in l)
        assert used["target_units"].startswith(("percent", "g/kg"))


class TestEndToEnd:
    def test_quick_run_on_ph(self, synthetic_afsis_root, tmp_path):
        res = subprocess.run(
            [sys.executable, "afsis_experiment.py", "--root", str(synthetic_afsis_root),
             "--target-kind", "ph", "--quick", "--seeds", "2", "--blocks", "6",
             "--export", str(tmp_path), "--out", str(tmp_path / "results")],
            capture_output=True, text=True, cwd=str(ROOT))
        assert res.returncode == 0, res.stderr[-1500:]
        r = json.loads((tmp_path / "results.json").read_text())
        assert r["target"]["kind"] == "ph"
        assert r["target"]["units"] == "pH units"
        assert r["target"]["log_transform"] is False
        assert not any(f.lower().startswith("ph") or " ph" in f.lower() for f in r["features"])
