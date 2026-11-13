"""
tests/test_bundle_hash.py - the results hash must survive a change of line
endings (Windows <-> git <-> Linux) but must still catch a changed number.
"""
import os
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def API(synthetic_export):
    """soil_api verifies the default bundle at import time, so import it with
    MODEL_DIR pointed at the freshly produced synthetic export (as test_api does)."""
    os.environ["MODEL_DIR"] = str(synthetic_export)
    sys.modules.pop("soil_api", None)
    import soil_api
    yield soil_api
    sys.modules.pop("soil_api", None)


def _copy(export, tmp_path):
    dst = tmp_path / "bundle"
    shutil.copytree(export, dst)
    return dst


def test_freshly_written_results_are_lf_only(synthetic_export):
    raw = (Path(synthetic_export) / "results.json").read_bytes()
    assert b"\r\n" not in raw


@pytest.mark.parametrize("to", ["crlf", "lf"])
def test_bundle_loads_after_line_ending_change(API, synthetic_export, tmp_path, to):
    dst = _copy(synthetic_export, tmp_path)
    p = dst / "results.json"
    lf = p.read_bytes().replace(b"\r\n", b"\n")
    p.write_bytes(lf.replace(b"\n", b"\r\n") if to == "crlf" else lf)
    assert API.load_bundle(dst)["meta"]["results_sha256"]


def test_changed_content_is_still_refused(API, synthetic_export, tmp_path):
    dst = _copy(synthetic_export, tmp_path)
    p = dst / "results.json"
    p.write_bytes(p.read_bytes().replace(b'"is_real_data"', b'"is_real_data_"', 1))
    with pytest.raises(API.BundleError, match="does not match the hash"):
        API.load_bundle(dst)


def test_git_version_flags_uncommitted_changes(tmp_path, monkeypatch):
    """A result must not claim a clean commit when the tree has local edits."""
    import subprocess
    import afsis_data as A
    run = lambda *a: subprocess.run(a, cwd=tmp_path, check=True, capture_output=True)
    run("git", "init", "-q")
    run("git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q",
        "--allow-empty", "-m", "x")
    monkeypatch.chdir(tmp_path)
    assert A.git_version() and not A.git_version().endswith("-dirty")
    (tmp_path / "new.py").write_text("x = 1\n")
    assert A.git_version().endswith("-dirty")
