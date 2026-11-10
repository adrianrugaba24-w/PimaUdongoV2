"""
tests/test_reliability.py  -  every branch and boundary of `reliability.gate`.

`gate()` takes no model and touches no file, so its rules are tested here
exactly: one test per rule, plus the boundaries where two rules could both
apply and the order decides which one speaks.

The numbers below are INVENTED fixtures chosen to sit clearly inside or
clearly outside a rule.  They are not thresholds, not measurements, and no
number here may be quoted anywhere as a result.
"""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import reliability as REL


# Two cuts, so three thirds of width 0.79.
CUTS = [0.65, 1.44]
LABELS = ["Lower third of the sampled soils",
          "Middle third of the sampled soils",
          "Upper third of the sampled soils"]
BANDS = dict(cuts=CUTS,
             bands=[dict(key="lower_third", label=LABELS[0]),
                    dict(key="middle_third", label=LABELS[1]),
                    dict(key="upper_third", label=LABELS[2])])

# Cuts on an exact binary grid, so "exactly one band wide" is not at the mercy
# of floating-point rounding.
EXACT = dict(cuts=[0.5, 1.5],
             bands=[dict(key="lo", label="Lower third of the sampled soils"),
                    dict(key="mid", label="Middle third of the sampled soils"),
                    dict(key="hi", label="Upper third of the sampled soils")])

RANGES = {"pH_H2O": dict(p5=4.4, p95=8.6),
          "EC": dict(p5=8.0, p95=740.0),
          "Clay percent": dict(p5=4.0, p95=62.0)}

MID = {"pH_H2O": 6.2, "EC": 90.0, "Clay percent": 22.0}


def gate(values=None, prediction=1.00, low=0.90, high=1.00,
         bands=BANDS, ranges=None):
    return REL.gate(values if values is not None else MID, prediction, low, high,
                    feature_ranges=RANGES if ranges is None else ranges,
                    bands=bands)


# ---------------------------------------------------------------------------
# R1 - is there a number to place?
# ---------------------------------------------------------------------------

class TestR1NoInterval:
    def test_missing_prediction(self):
        out = gate(prediction=None)
        assert out["rules"] == ["R1_no_interval"]
        assert out["confidence"] == "Low"
        assert out["message"] == REL.NO_INTERVAL
        assert out["band"] is None

    def test_nan_bound(self):
        out = gate(low=float("nan"))
        assert out["rules"] == ["R1_no_interval"]

    def test_infinite_bound(self):
        out = gate(high=float("inf"))
        assert out["rules"] == ["R1_no_interval"]

    def test_missing_bounds(self):
        out = gate(low=None, high=None)
        assert out["rules"] == ["R1_no_interval"]

    def test_no_placement_is_claimed_without_an_interval(self):
        out = gate(prediction=None)
        assert out["band"] is None and out["band_key"] is None
        assert out["advice_withheld"] is True


# ---------------------------------------------------------------------------
# R2 - is any input outside the range the model was trained on?
# ---------------------------------------------------------------------------

class TestR2OutsideTrainingRange:
    def test_above_p95(self):
        out = gate({"pH_H2O": 12.0, "EC": 90.0, "Clay percent": 22.0})
        assert out["rules"] == ["R2_outside_training_range"]
        assert out["confidence"] == "Low"
        assert [i["feature"] for i in out["out_of_range"]] == ["pH_H2O"]
        assert "outside_training_range:pH_H2O" in out["flags"]
        assert "extrapolated:pH_H2O" in out["flags"]

    def test_below_p5(self):
        out = gate({"pH_H2O": 3.0, "EC": 90.0, "Clay percent": 22.0})
        assert out["rules"] == ["R2_outside_training_range"]

    def test_message_names_the_feature_and_the_lab_line(self):
        out = gate({"pH_H2O": 12.0, "EC": 90.0, "Clay percent": 22.0})
        assert "pH_H2O" in out["message"]
        assert REL.LAB_LINE in out["message"]

    def test_grammar_one_vs_many(self):
        one = gate({"pH_H2O": 12.0, "EC": 90.0, "Clay percent": 22.0})
        two = gate({"pH_H2O": 12.0, "EC": 9000.0, "Clay percent": 22.0})
        assert "pH_H2O is outside" in one["message"]
        assert "pH_H2O, EC are outside" in two["message"]

    def test_out_of_range_beats_missing_bands(self):
        """R2 is checked before R3: the reason given must be the real one."""
        out = gate({"pH_H2O": 12.0, "EC": 90.0, "Clay percent": 22.0}, bands=None)
        assert out["rules"] == ["R2_outside_training_range"]
        assert out["message"] != REL.NO_BANDS

    def test_out_of_range_beats_a_tidy_interval(self):
        """A narrow interval inside one third must not rescue an extrapolation."""
        out = gate({"pH_H2O": 12.0, "EC": 90.0, "Clay percent": 22.0},
                   prediction=1.0, low=0.95, high=1.05)
        assert out["confidence"] == "Low"
        assert "R2" in out["rules"][0]

    def test_value_exactly_on_a_bound_is_inside(self):
        out = gate({"pH_H2O": 8.6, "EC": 90.0, "Clay percent": 22.0})
        assert "R2_outside_training_range" not in out["rules"]

    def test_feature_without_a_range_is_ignored(self):
        out = gate({"pH_H2O": 6.2, "Something new": 1e9})
        assert "R2_outside_training_range" not in out["rules"]

    def test_non_numeric_value_is_skipped_not_fatal(self):
        out = gate({"pH_H2O": None, "EC": "n/a", "Clay percent": 22.0})
        assert "R2_outside_training_range" not in out["rules"]

    def test_reports_the_training_span_it_used(self):
        out = gate({"pH_H2O": 12.0, "EC": 90.0, "Clay percent": 22.0})
        item = out["out_of_range"][0]
        assert item["training_p5"] == 4.4 and item["training_p95"] == 8.6
        assert item["value"] == 12.0


# ---------------------------------------------------------------------------
# R3 - are there thresholds at all?
# ---------------------------------------------------------------------------

class TestR3NoBands:
    def test_absent(self):
        out = gate(bands=None)
        assert out["rules"] == ["R3_no_bands"]
        assert out["message"] == REL.NO_BANDS
        assert out["confidence"] == "Low"

    def test_empty(self):
        assert gate(bands={})["rules"] == ["R3_no_bands"]

    def test_one_cut_is_not_enough(self):
        out = gate(bands=dict(cuts=[0.65], bands=[dict(key="a", label="A"),
                                                 dict(key="b", label="B")]))
        assert out["rules"] == ["R3_no_bands"]

    def test_two_labels_are_not_three_thirds(self):
        out = gate(bands=dict(cuts=CUTS, bands=[dict(key="a", label="A"),
                                               dict(key="b", label="B")]))
        assert out["rules"] == ["R3_no_bands"]

    def test_no_band_is_invented_when_thresholds_are_missing(self):
        out = gate(bands=None)
        assert out["band"] is None and out["band_key"] is None


# ---------------------------------------------------------------------------
# R4 - the interval does not single out one third
# ---------------------------------------------------------------------------

class TestR4TooWide:
    def test_wider_than_a_band(self):
        out = gate(prediction=1.0, low=0.5, high=1.5)      # width 1.00 > 0.79
        assert out["rules"] == ["R4_too_wide"]
        assert out["message"] == REL.TOO_WIDE
        assert out["confidence"] == "Low"
        assert "band_undetermined" in out["flags"]

    def test_exactly_one_band_wide(self):
        """width == inner is not narrower than a band, so it cannot pick one."""
        out = gate(prediction=1.5, low=1.0, high=2.0, bands=EXACT)   # width == 1.0
        assert out["rules"] == ["R4_too_wide"]

    def test_spanning_both_cuts(self):
        out = gate(prediction=3.0, low=-5.0, high=9.0)
        assert out["message"] == REL.TOO_WIDE

    def test_just_under_one_band_is_not_r4(self):
        out = gate(prediction=1.5, low=1.0, high=1.99999, bands=EXACT)
        assert "R4_too_wide" not in out["rules"]
        assert out["confidence"] == "Medium"          # R5: it crosses 1.5

    def test_the_wide_case_is_reported_plainly(self):
        """The required sentence, word for word, when nothing narrower is true."""
        assert gate(prediction=1.0, low=-1.0, high=4.0)["message"] == (
            "The estimate is too wide to place in a band.")


# ---------------------------------------------------------------------------
# R5 - exactly one boundary crossed
# ---------------------------------------------------------------------------

class TestR5CrossesOneCut:
    def test_crosses_lower_cut(self):
        out = gate(prediction=0.70, low=0.55, high=0.85)     # width 0.30
        assert out["rules"] == ["R5_crosses_one_cut"]
        assert out["confidence"] == "Medium"
        assert out["band"] is None
        assert "band_boundary_crossed" in out["flags"]

    def test_message_names_both_thirds(self):
        out = gate(prediction=0.70, low=0.55, high=0.85)
        assert "lower third of the sampled soils" in out["message"]
        assert "middle third of the sampled soils" in out["message"]

    def test_crosses_upper_cut(self):
        out = gate(prediction=1.40, low=1.25, high=1.55)
        assert out["rules"] == ["R5_crosses_one_cut"]

    def test_no_band_is_named_when_a_boundary_is_crossed(self):
        out = gate(prediction=0.70, low=0.55, high=0.85)
        assert out["band"] is None and out["band_key"] is None


# ---------------------------------------------------------------------------
# R6 - inside a single third
# ---------------------------------------------------------------------------

class TestR6SingleBand:
    def test_middle_third(self):
        out = gate(prediction=1.00, low=0.90, high=1.10)
        assert out["rules"] == ["R6_single_band"]
        assert out["confidence"] == "High"
        assert out["band"] == LABELS[1]
        assert out["band_key"] == "middle_third"

    def test_lower_third(self):
        out = gate(prediction=0.30, low=0.20, high=0.40)
        assert out["band"] == LABELS[0] and out["band_key"] == "lower_third"

    def test_upper_third(self):
        out = gate(prediction=2.00, low=1.90, high=2.10)
        assert out["band"] == LABELS[2] and out["band_key"] == "upper_third"

    def test_label_comes_from_the_bands_file_not_from_this_module(self):
        rename = dict(cuts=CUTS,
                      bands=[dict(key="a", label="One"), dict(key="b", label="Two"),
                             dict(key="c", label="Three")])
        out = gate(prediction=1.0, low=0.9, high=1.1, bands=rename)
        assert out["band"] == "Two"

    def test_endpoint_sitting_on_a_cut_does_not_cross_it(self):
        """[1.44, 1.52] touches the upper cut but stays inside one span."""
        out = gate(prediction=1.48, low=1.44, high=1.52)
        assert out["rules"] == ["R6_single_band"]
        assert out["confidence"] == "High"

    def test_negative_lower_bound_still_places(self):
        """A bound below zero is an honest consequence of a symmetric band."""
        out = gate(prediction=0.30, low=-0.05, high=0.65)
        assert out["rules"] == ["R6_single_band"]
        assert out["band"] == LABELS[0]


# ---------------------------------------------------------------------------
# band_for
# ---------------------------------------------------------------------------

class TestBandFor:
    def test_below_all_cuts(self):
        assert REL.band_for(0.10, CUTS, LABELS) == (0, LABELS[0])

    def test_on_a_cut_belongs_to_the_lower_third(self):
        assert REL.band_for(0.65, CUTS, LABELS) == (0, LABELS[0])

    def test_between_cuts(self):
        assert REL.band_for(1.00, CUTS, LABELS) == (1, LABELS[1])

    def test_above_all_cuts(self):
        assert REL.band_for(9.99, CUTS, LABELS) == (2, LABELS[2])


# ---------------------------------------------------------------------------
# The output contract itself
# ---------------------------------------------------------------------------

class TestOutputContract:
    CASES = [
        dict(prediction=None),
        dict(values={"pH_H2O": 12.0, "EC": 90.0, "Clay percent": 22.0}),
        dict(bands=None),
        dict(prediction=1.0, low=-1.0, high=4.0),
        dict(prediction=0.70, low=0.55, high=0.85),
        dict(prediction=1.00, low=0.90, high=1.10),
    ]

    @pytest.mark.parametrize("case", CASES)
    def test_every_outcome_has_the_same_shape(self, case):
        out = gate(**case)
        for key in ("confidence", "band", "band_key", "message", "flags",
                    "out_of_range", "rules", "advice_withheld",
                    "interval", "prediction"):
            assert key in out
        assert out["confidence"] in REL.CONFIDENCE_LEVELS
        assert isinstance(out["rules"], list) and out["rules"]
        assert isinstance(out["message"], str) and out["message"]

    @pytest.mark.parametrize("case", CASES)
    def test_no_advice_is_ever_offered(self, case):
        out = gate(**case)
        assert out["advice_withheld"] is True

    @pytest.mark.parametrize("case", CASES)
    def test_messages_use_no_imperative_verbs(self, case):
        """The project does not tell anyone what to do with a prediction."""
        banned = re.compile(r"\b(apply|add|increase|reduce|spread|incorporate|"
                            r"plant|irrigate|fertilis|fertiliz|consider|"
                            r"you should|we recommend|recommended)\b", re.I)
        assert not banned.search(gate(**case)["message"])

    @pytest.mark.parametrize("case", CASES)
    def test_messages_never_grade_the_soil(self, case):
        """A third of the distribution is not a verdict on the soil."""
        banned = re.compile(r"\b(poor|good|excellent|healthy|degraded|"
                            r"fertile|infertile|risk)\b", re.I)
        assert not banned.search(gate(**case)["message"])
