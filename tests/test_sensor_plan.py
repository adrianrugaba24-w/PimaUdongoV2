"""
tests/test_sensor_plan.py  -  the sensor list is derived, not asserted.

Three failures this file exists to catch:

  * a figure typed into `SENSORS.md` by hand that no longer matches the bundle
    it claims to come from - the `--check` round-trip at the bottom;
  * a requirement rounded UP, which is a requirement an instrument may just
    miss - `TestFloor`;
  * a ceiling printed when the bundle recorded no break-even at all - the
    synthetic stand-in, which has none, is the case that proves it.

Nothing here reads a raw AfSIS file.  `export_afsis_real` is the hash-checked
bundle that `sensor_plan.py` derives from, and the synthetic stand-in is used
wherever the point is that a figure is missing rather than present.
"""
import json
import math
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import sensor_plan as SP  # noqa: E402

REAL = ROOT / "export_afsis_real"
DOCUMENT = ROOT / "SENSORS.md"

needs_bundle = pytest.mark.skipif(
    not (REAL / "results.json").is_file(),
    reason="the real-data bundle is not in this checkout")


# ---------------------------------------------------------------------------
# helpers: a bundle made of the two stored fields a ceiling comes from
# ---------------------------------------------------------------------------

SPREADS = {"pH_H2O": 1.0, "EC": 0.2, "Clay percent": 10.0}


def results(arms=None, spreads=None, units=None):
    spreads = SPREADS if spreads is None else spreads
    return dict(
        headline=dict(break_even_noise=(
            {"train_clean|spatial": 0.5, "train_noisy|spatial": 0.5,
             "model": "random_forest"} if arms is None else arms)),
        feature_ranges={k: dict(p5=0.1, median=1.0, p95=2.0, sd=v)
                        for k, v in spreads.items()},
        feature_units=units or {},
    )


def meta(names=("pH_H2O", "EC", "Clay percent")):
    return dict(feature_names=list(names), model_version="sha256:test",
                training_data_version="test-data", n_rows=3,
                target_name="Total carbon", target_units="g/kg")


def doc_text(p) -> str:
    return SP.render(p)


# ---------------------------------------------------------------------------
# The rounding rule: down, always
# ---------------------------------------------------------------------------

class TestFloor:
    @pytest.mark.parametrize("raw,floored", [
        (0.5076855, 0.507),
        (4.858651, 4.85),
        (0.13409367, 0.134),
        (3.2092875, 3.2),
        (12.3456, 12.3),
        (0.0078901, 0.00789),
    ])
    def test_it_rounds_down_and_never_to_nearest(self, raw, floored):
        assert SP.floor_sig(raw) == pytest.approx(floored)

    @pytest.mark.parametrize("raw", [0.5076855, 9.6487, 0.0001234, 987.65])
    def test_a_ceiling_is_never_above_the_arithmetic(self, raw):
        assert SP.floor_sig(raw) <= raw

    @pytest.mark.parametrize("raw", [0.5076855, 12.3456, 0.0078901])
    def test_it_always_leaves_three_figures(self, raw):
        figures = f"{SP.floor_sig(raw):g}".replace(".", "").lstrip("0")
        assert len(figures) == SP.SIG

    def test_flooring_twice_changes_nothing(self):
        assert SP.floor_sig(SP.floor_sig(9.6487)) == SP.floor_sig(9.6487)

    @pytest.mark.parametrize("raw", [None, 0, 0.0, -1.0,
                                     float("nan"), float("inf"), float("-inf")])
    def test_nothing_is_invented_where_there_is_no_number(self, raw):
        assert SP.floor_sig(raw) is None


# ---------------------------------------------------------------------------
# The break-even: the smallest arm, and None when there is none
# ---------------------------------------------------------------------------

class TestBreakEven:
    def test_the_smallest_arm_is_the_one_a_requirement_must_satisfy(self):
        assert SP.break_even(results({"a|spatial": 0.5, "b|spatial": 0.25})) == 0.25

    def test_the_model_name_is_not_an_arm(self):
        assert SP.break_even(results({"model": "random_forest"})) is None

    def test_a_sweep_that_never_broke_even_derives_nothing(self):
        assert SP.break_even(results({"a|spatial": None, "b|spatial": None})) is None

    def test_an_arm_that_never_failed_does_not_hold_the_other_one_back(self):
        assert SP.break_even(results({"a|spatial": None, "b|spatial": 0.5})) == 0.5

    def test_a_zero_is_not_a_break_even(self):
        assert SP.break_even(results({"a|spatial": 0.0})) is None

    def test_a_results_file_without_a_headline_derives_nothing(self):
        assert SP.break_even(dict(feature_ranges={})) is None


# ---------------------------------------------------------------------------
# One row per input, spread x fraction
# ---------------------------------------------------------------------------

class TestTolerances:
    def test_one_row_per_input_in_the_order_the_bundle_lists_them(self):
        rows = SP.tolerances(results(), meta())
        assert [r["feature"] for r in rows] == ["pH_H2O", "EC", "Clay percent"]

    def test_a_ceiling_is_the_fraction_times_the_spread(self):
        rows = {r["feature"]: r for r in SP.tolerances(results(), meta())}
        assert rows["pH_H2O"]["tolerance_exact"] == pytest.approx(0.5)
        assert rows["EC"]["tolerance_exact"] == pytest.approx(0.1)

    def test_the_printed_ceiling_is_the_exact_one_floored(self):
        for r in SP.tolerances(results(), meta()):
            assert r["tolerance"] == SP.floor_sig(r["tolerance_exact"])
            assert r["tolerance"] <= r["tolerance_exact"]

    def test_both_figures_are_kept_so_a_test_can_hold_the_rounding_rule(self):
        r = SP.tolerances(results(spreads={"pH_H2O": 1.0154}),
                          meta(names=("pH_H2O",)))[0]
        assert r["tolerance_exact"] == pytest.approx(0.5077)
        assert r["tolerance"] == pytest.approx(0.507)
        assert r["tolerance"] != r["tolerance_exact"]

    def test_no_fraction_means_no_ceiling_on_any_row(self):
        rows = SP.tolerances(results({"a|spatial": None}), meta())
        assert all(r["tolerance"] is None and not r["has_ceiling"] for r in rows)

    def test_the_features_come_from_meta_so_the_order_is_the_model_s(self):
        rows = SP.tolerances(results(), meta(names=("EC", "pH_H2O")))
        assert [r["feature"] for r in rows] == ["EC", "pH_H2O"]


# ---------------------------------------------------------------------------
# The plan, on the bundle that is actually committed
# ---------------------------------------------------------------------------

@needs_bundle
class TestPlan:
    @pytest.fixture()
    def p(self):
        return SP.plan(*SP.load(REAL))

    def test_it_derives_from_the_real_data_bundle_not_the_stand_in(self):
        assert SP.DEFAULT_MODEL_DIR == Path("export_afsis_real")

    def test_every_input_the_check_takes_gets_a_row(self, p):
        assert len(p["rows"]) == 5
        assert p["quantities"] == len(p["rows"])

    def test_the_field_and_lab_rows_cover_the_quantities_without_overlap(self, p):
        covered = [r["feature"] for r in p["field"]]
        covered += [f for r in p["lab"] for f in (c["feature"] for c in r["ceilings"])]
        assert sorted(covered) == sorted(r["feature"] for r in p["rows"])

    def test_the_borrowed_instrument_rows_are_the_ones_that_have_a_ceiling(self, p):
        for row in p["field"]:
            assert row["ceiling"]["has_ceiling"], row["feature"]

    def test_what_is_absent_is_named_and_carbon_is_one_of_them(self, p):
        named = " ".join(r["quantity"] for r in p["absent"])
        assert "Soil carbon" in named and "moisture" in named.lower()

    def test_no_measured_instrument_error_is_claimed(self, p):
        assert p["measured_sensor_error"] is None


# ---------------------------------------------------------------------------
# Rendering: deterministic, complete, and silent where the bundle is silent
# ---------------------------------------------------------------------------

@needs_bundle
class TestRender:
    @pytest.fixture()
    def text(self):
        return SP.render(SP.plan(*SP.load(REAL)))

    def test_the_same_bundle_renders_the_same_document_twice(self):
        a = SP.render(SP.plan(*SP.load(REAL)))
        b = SP.render(SP.plan(*SP.load(REAL)))
        assert a == b

    def test_it_carries_no_clock(self, text):
        assert not re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)
        assert "UTC" not in text and "generated on" not in text.lower()

    def test_the_markers_wrap_the_whole_document(self, text):
        assert text.startswith(SP.BEGIN)
        assert text.rstrip().endswith(SP.END)

    def test_every_field_instrument_reaches_the_shopping_table(self, text):
        for row in SP.FIELD_ROWS:
            assert row["instrument"] in text

    def test_every_laboratory_method_reaches_it_too(self, text):
        for row in SP.LAB_ROWS:
            assert row["instrument"] in text

    def test_the_provenance_names_the_bundle_the_figures_came_from(self, text):
        p = SP.plan(*SP.load(REAL))
        assert p["model_version"] in text
        assert p["data_version"] in text
        assert str(p["n_rows"]) in text

    def test_it_says_the_ceilings_are_a_shared_budget(self, text):
        assert "shared budget" in text

    def test_it_refuses_to_rank_the_inputs(self, text):
        assert "not ranked" in text
        assert "priority" not in text.lower()

    def test_every_ceiling_it_prints_is_the_floored_one(self, text):
        p = SP.plan(*SP.load(REAL))
        for row in p["rows"]:
            assert SP._ceil(row) in text, row["feature"]


# ---------------------------------------------------------------------------
# The case the synthetic stand-in exists to prove: no break-even at all
# ---------------------------------------------------------------------------

class TestWithoutABreakEven:
    @pytest.fixture()
    def p(self, synthetic_export):
        return SP.plan(*SP.load(synthetic_export))

    def test_the_stand_in_really_has_no_break_even(self, p):
        assert p["fraction"] is None

    def test_no_row_carries_a_ceiling(self, p):
        assert all(r["tolerance"] is None and r["tolerance_exact"] is None
                   for r in p["rows"])

    def test_the_document_says_why_rather_than_borrowing_a_number(self, p):
        text = doc_text(p)
        assert "never reached a" in text
        assert "not derived" in text
        assert not re.search(r"ceiling = \d", text)

    def test_the_instruments_are_still_named(self, p):
        text = doc_text(p)
        for row in SP.FIELD_ROWS:
            assert row["instrument"] in text


# ---------------------------------------------------------------------------
# The committed document is the one this bundle renders
# ---------------------------------------------------------------------------

@needs_bundle
class TestTheCommittedDocument:
    def test_it_exists(self):
        assert DOCUMENT.is_file(), "SENSORS.md is missing; run --write"

    def test_it_matches_the_bundle_it_claims_to_come_from(self):
        assert SP.main(["--check"]) == 0

    def test_every_printable_figure_in_it_is_a_derived_one(self):
        text = DOCUMENT.read_text(encoding="utf-8")
        p = SP.plan(*SP.load(REAL))
        for row in p["rows"]:
            assert SP._ceil(row) in text, row["feature"]


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

@needs_bundle
class TestCli:
    def test_stdout_is_the_document(self, capsys):
        assert SP.main([]) == 0
        out = capsys.readouterr().out
        assert out.startswith(SP.BEGIN) and out.rstrip().endswith(SP.END)

    def test_a_missing_bundle_is_an_error_not_an_empty_document(self, tmp_path,
                                                               capsys):
        assert SP.main(["--model-dir", str(tmp_path / "nowhere")]) == 2
        assert SP.BEGIN not in capsys.readouterr().out

    def test_json_gives_a_test_the_figures_without_parsing_markdown(self, capsys):
        assert SP.main(["--json"]) == 0
        p = json.loads(capsys.readouterr().out)
        assert len(p["rows"]) == 5 and p["fraction"] is not None
        assert all(math.isfinite(r["tolerance_exact"]) for r in p["rows"])

    def test_write_then_check_round_trips(self, tmp_path, monkeypatch, capsys):
        target = tmp_path / "SENSORS.md"
        monkeypatch.setattr(SP, "DOCUMENT", target)
        assert SP.main(["--write"]) == 0
        assert SP.main(["--check"]) == 0
        capsys.readouterr()

    def test_check_fails_when_the_document_is_out_of_date(self, tmp_path,
                                                          monkeypatch, capsys):
        target = tmp_path / "SENSORS.md"
        monkeypatch.setattr(SP, "DOCUMENT", target)
        assert SP.main(["--check"]) == 1
        target.write_text(SP.BEGIN + "\nhand-edited\n" + SP.END + "\n",
                          encoding="utf-8")
        assert SP.main(["--check"]) == 1
        capsys.readouterr()

    def test_a_newline_convention_is_not_a_difference(self):
        lf = SP.render(SP.plan(*SP.load(REAL)))
        assert SP._normalise(lf) == SP._normalise(lf.replace("\n", "\r\n"))
