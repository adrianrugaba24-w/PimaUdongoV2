"""
tests/test_uganda_2025.py  -  the Ugandan dataset as the pipeline will see it.

The field workbook is not a table: 282 rows contain 258 samples, one units row,
12 in-sheet `Average` / `Critical Value` subtotals, two blank rows and a rating
legend.  These tests guard what `prepare_uganda_2025.py` wrote from it, so a
stale rebuild or a hand edit is caught before it reaches a run.

The prepared CSVs are read, never rewritten.  Only the reproducibility test
opens the workbook, and it skips itself when the workbook is absent.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import afsis_data as A
import prepare_uganda_2025 as P

DATA = Path(__file__).parent.parent / P.OUT
GEO = DATA / "Georeferences" / "georeferences.csv"
WET = DATA / "Wet_Chemistry" / P.LAB / f"Wet_Chemistry_{P.LAB}.csv"
MANIFEST = DATA / "COALESCE_MANIFEST.json"

pytestmark = pytest.mark.skipif(not WET.is_file(),
                               reason="data/uganda_2025 not prepared")


@pytest.fixture(scope="module")
def geo():
    return pd.read_csv(GEO)


@pytest.fixture(scope="module")
def wet():
    return pd.read_csv(WET)


@pytest.fixture(scope="module")
def manifest():
    import json
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def loaded():
    return A.load_raw(P.OUT)


@pytest.fixture(scope="module")
def schema(loaded):
    return A.detect_schema(loaded[0], {"target": P.TARGET})


class TestShape:
    def test_one_row_per_sample_and_no_subtotals(self, geo, manifest):
        """The 12 Average/Critical Value rows are gone, not merely unlabelled."""
        assert geo["SSN"].is_unique
        assert sorted(geo["SampleNo"]) == list(range(1, 259))
        assert manifest["quality"]["sample_rows"] == len(geo) == 258

    def test_every_non_sample_row_is_accounted_for(self, manifest):
        """282 = 258 samples + 24 rows that are named, not silently dropped."""
        q = manifest["quality"]
        accounted = q["sample_rows"] + sum(q["rows_dropped_as_not_samples"].values())
        assert accounted == q["rows_in_sheet"] == 282

    def test_the_country_is_uganda_everywhere(self, geo):
        assert set(geo["Country"]) == {"Uganda"}

    def test_hosts_travel_as_names_not_ids(self, geo):
        """A SiteID would become the fold group and clean() would keep one row
        per farm; the group must stay one sample."""
        assert "SiteName" in geo.columns
        assert not [c for c in geo.columns if c.lower() in ("siteid", "site_id",
                                                             "profileid", "profile_id")]


class TestColumns:
    def test_the_canonical_feature_set_is_the_afsis_one(self, wet):
        for f in P.FEATURES:
            assert f in wet.columns, f
        assert P.FEATURES == ["pH_H2O", "EC", "Clay percent", "Sand percent",
                              "Silt percent"]

    def test_the_project_detector_finds_them_without_help(self, schema):
        assert schema.features == P.FEATURES
        assert schema.target == P.TARGET
        assert schema.lat == "Latitude" and schema.lon == "Longitude"
        assert schema.group_key() == "SSN"

    def test_the_provenance_column_is_present(self, wet):
        """The conversion has to be readable in the table, not only in a doc."""
        assert "OM percent" in wet.columns
        assert "carbon_source" in wet.columns


class TestTarget:
    def test_target_is_the_conversion_the_manifest_declares(self, wet, manifest):
        d = manifest["derived_target"]
        assert d["measured"] is False
        expected = wet["OM percent"] / P.OM_TO_C
        pd.testing.assert_series_equal(wet[P.TARGET], expected, check_names=False,
                                       rtol=1e-9)
        assert f"{P.OM_TO_C:.3f}" in d["formula"]

    def test_the_conversion_is_said_to_be_an_assumption(self, manifest):
        text = " ".join(str(v) for v in manifest["derived_target"].values()).lower()
        assert "limitation" in manifest["derived_target"]
        assert "assumed" in text or "not proved" in text

    def test_every_row_has_a_positive_target(self, wet):
        assert wet[P.TARGET].notna().all()
        assert (wet[P.TARGET] > 0).all()


class TestValues:
    def test_nothing_sits_outside_a_physical_bound(self, wet):
        for col, (lo, hi) in P.BOUNDS.items():
            v = pd.to_numeric(wet[col], errors="coerce").dropna()
            assert v.between(lo, hi).all(), f"{col} outside [{lo}, {hi}]"

    def test_texture_parts_add_up(self, wet):
        total = wet[["Clay percent", "Sand percent", "Silt percent"]].sum(axis=1,
                                                                          min_count=3)
        assert total.notna().all()
        assert ((total - 100).abs() <= 5).all()

    def test_ec_is_empty_because_it_was_never_measured(self, wet, manifest):
        """An invented EC would make these rows look scoreable by the shipped
        model; an empty column makes the gap visible instead."""
        assert wet["EC"].isna().all()
        assert "EC" in manifest["absent_at_source"]

    def test_the_stray_apostrophe_was_repaired_not_dropped(self, geo, manifest):
        assert manifest["quality"]["coordinate_defects"][
            "repaired_trailing_apostrophe"] == 1
        assert geo["Latitude"].notna().sum() == 255


class TestCleaningContract:
    def test_clean_keeps_254_rows_and_names_the_four_it_drops(self, loaded, schema,
                                                              manifest):
        cleaned, log = A.clean(loaded[0], schema,
                              {"depth": A.DEPTH_TARGET_CM, "lab_dupes": "first",
                               "target_units": "auto"})
        removed = {e["step"]: e["n_removed"] for e in log if e["n_removed"]}
        assert removed == {"missing_coordinates": 3, "impossible_coordinates": 1}
        assert len(cleaned) == manifest["counts"]["joined_rows"] - 4 == 254

    def test_the_target_units_are_read_as_a_percentage(self, loaded, schema):
        _, log = A.clean(loaded[0], schema,
                         {"depth": A.DEPTH_TARGET_CM, "lab_dupes": "first",
                          "target_units": "auto"})
        final = next(e for e in log if e["step"] == "final")
        assert final["target_units"].startswith("percent")

    def test_no_depth_rule_is_claimed_when_there_is_no_depth(self, loaded, schema):
        _, log = A.clean(loaded[0], schema,
                         {"depth": A.DEPTH_TARGET_CM, "lab_dupes": "first",
                          "target_units": "auto"})
        depth = next(e for e in log if e["step"] == "depth_selection")
        assert depth["applied"] is False


class TestRepeatedRecords:
    """The workbook repeats one block of chemistry values across farms.

    These tests do not demand clean data and they do not freeze the defect at a
    number: they demand that the table and the manifest agree about it, so the
    count cannot drift out of view or be quietly fixed without a rebuild.
    """

    def test_every_row_carries_a_pattern_id(self, wet):
        assert "record_pattern" in wet.columns
        assert wet["record_pattern"].notna().all()

    def test_a_pattern_never_mixes_two_soil_vectors(self, wet):
        """The id is built from the ten chemistry columns other than pH, so one id
        must span exactly one texture-and-carbon vector - and pH is free to vary
        inside it, which is the defect this column exists to expose."""
        cols = ["Clay percent", "Sand percent", "Silt percent", "OM percent"]
        per_pattern = wet.groupby("record_pattern")[cols].nunique()
        assert (per_pattern <= 1).all().all()
        assert wet.groupby("record_pattern")["pH_H2O"].nunique().max() > 1

    def test_the_manifest_and_the_table_count_the_same_patterns(self, wet, manifest):
        rr = manifest["quality"]["repeated_records"]
        assert rr["distinct_patterns"] == wet["record_pattern"].nunique()
        assert rr["rows"] == len(wet)
        assert rr["surplus_rows"] == len(wet) - wet["record_pattern"].nunique()

    def test_the_table_is_not_258_independent_records(self, wet, manifest):
        """If this ever fails, the workbook was corrected and the warning in the
        manifest should be removed deliberately, not silently."""
        rr = manifest["quality"]["repeated_records"]
        assert rr["rows_in_a_repeated_pattern"] > len(wet) / 2
        assert rr["largest_pattern"] > 10
        assert "known_defect" in manifest and "inflate" in manifest["known_defect"]


class TestManifest:
    def test_the_run_command_drops_ec(self, manifest):
        assert "--drop-features EC" in manifest["run"]

    def test_the_source_hash_is_recorded(self, manifest):
        assert len(manifest["source"]["sha256"]) == 64
        assert manifest["source"]["file"].endswith(".xlsx")


class TestReproducible:
    def test_rebuilding_from_the_workbook_gives_the_same_table(self, geo, wet):
        if not P.SRC.is_file():
            pytest.skip(f"{P.SRC.name} not present")
        fresh_geo, fresh_wet, _ = P.build(pd.read_excel(P.SRC, sheet_name=P.SHEET))
        # Compare the bytes the writer would produce, not the in-memory dtypes:
        # a CSV round-trip turns pd.NA into nan, and that is not a data change.
        assert fresh_geo.to_csv(index=False, lineterminator="\n") == \
            GEO.read_text(encoding="utf-8")
        assert fresh_wet.to_csv(index=False, lineterminator="\n") == \
            WET.read_text(encoding="utf-8")
