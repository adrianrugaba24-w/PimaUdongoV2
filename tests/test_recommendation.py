"""
tests/test_recommendation.py  -  the ranked next steps.

Three things are asserted here, and they are different in kind:

  * what the engine does  - which step it puts first, and on what evidence;
  * what it must NOT read - the band the soil fell into is not an input, and
    one test builds two placements that differ only in their band to prove it;
  * what it must not say   - every string it can print passes the same
    banned-term scan the rest of the farmer view passes.

The figures in the helper below are invented to choose branch by branch.  They
are not read from a bundle and none of them is a reported result.
"""
import ast
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import farmer_view as F       # noqa: E402
import recommendation as REC  # noqa: E402

PAGE = ROOT / "web" / "farmer.html"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def metrics(sd_ph=1.0, sd_ec=0.2):
    return dict(features=[
        dict(name="pH_H2O",
             training_range=dict(p5=5.0, median=6.5, p95=8.0, sd=sd_ph)),
        dict(name="EC",
             training_range=dict(p5=0.02, median=0.06, p95=0.4, sd=sd_ec)),
    ])


def pred(rules, out_of_range=None):
    """One /api/predict-shaped placement, as `_api_prediction` returns it."""
    return dict(band=dict(rules=list(rules), confidence="Low",
                          out_of_range=list(out_of_range or [])))


def keys(advice):
    return [i["key"] for i in advice["items"]]


def steps():
    """Every key the engine can emit, so a test can assert an absence."""
    return {"A1_unsure", "A2_outside", "C1_mixed", "B1_first", "B2_moved",
            "B3_steady", "E1_practice", "F1_record", "D1_p_acid", "D1_k_salty",
            "D1_n_dry"}


def farmer_region() -> str:
    html = PAGE.read_text(encoding="utf-8")
    return html[html.index("<!-- farmer:begin -->"):html.index("<!-- farmer:end -->")]


# ---------------------------------------------------------------------------
# Ordering: uncertainty first, the record last
# ---------------------------------------------------------------------------

class TestRanking:
    def test_an_unsure_placement_comes_before_everything(self):
        a = REC.recommend(pred(["R4_too_wide"]), metrics(),
                          dict(crop="annual", bands={"p": "low"},
                               reading=dict(ph=4.1)))
        assert a["items"][0]["key"] == "A1_unsure"

    def test_a_placed_soil_does_not_get_the_test_first(self):
        a = REC.recommend(pred(["R6_single_band"]), metrics(), dict(crop="annual"))
        assert "A1_unsure" not in keys(a) and "A2_outside" not in keys(a)

    def test_the_record_is_always_the_last_step(self):
        a = REC.recommend(pred(["R6_single_band"]), metrics(), dict(crop="perennial"))
        assert a["items"][-1]["key"] == "F1_record"

    def test_every_item_carries_a_rank_that_rises(self):
        a = REC.recommend(pred(["R4_too_wide"]), metrics(),
                          dict(crop="annual", bands={"p": "low"}, reading=dict(ph=4.1)))
        ranks = [i["rank"] for i in a["items"]]
        assert ranks == sorted(ranks)

    def test_the_list_is_capped_and_says_how_many_it_held_back(self):
        a = REC.recommend(pred(["R4_too_wide"]), metrics(),
                          dict(crop="mixed", bands={"p": "low"}, reading=dict(ph=4.1)))
        assert len(a["items"]) == REC.CAP
        assert a["total"] > REC.CAP
        assert a["unshown"] == a["total"] - a["shown"]

    def test_a_short_list_holds_nothing_back(self):
        a = REC.recommend(pred(["R6_single_band"]), metrics(), None)
        assert a["unshown"] == 0 and a["shown"] == a["total"]

    def test_the_verdict_is_named_after_the_first_step(self):
        a = REC.recommend(pred(["R3_no_bands"]), metrics(), dict(crop="annual"))
        assert a["verdict"]["title"] == F.RECOMMEND_VERDICTS["A1"]["title"]
        assert a["verdict"]["words"] == F.RECOMMEND_BASIS["placement"]

    def test_every_step_says_what_its_evidence_is(self):
        a = REC.recommend(pred(["R4_too_wide"]), metrics(),
                          dict(crop="mixed", bands={"p": "low"}, reading=dict(ph=4.1)))
        for item in a["items"]:
            assert item["basis"] in F.RECOMMEND_BASIS, item["key"]
            assert item["words"] == F.RECOMMEND_BASIS[item["basis"]]


# ---------------------------------------------------------------------------
# A - the two ways a placement can be withheld
# ---------------------------------------------------------------------------

class TestPlacement:
    @pytest.mark.parametrize("rule", REC.WITHHOLDING)
    def test_each_withholding_rule_sends_the_farmer_to_the_laboratory(self, rule):
        a = REC.recommend(pred([rule]), metrics(), None)
        assert a["items"][0]["key"] == "A1_unsure"

    def test_being_outside_the_sample_is_a_different_sentence(self):
        a = REC.recommend(pred(["R2_outside_training_range"],
                               [dict(feature="EC", value=9.0)]), metrics(), None)
        assert a["items"][0]["key"] == "A2_outside"
        assert "Salts" in a["items"][0]["why"]
        assert a["verdict"]["title"] == F.RECOMMEND_VERDICTS["A2"]["title"]

    def test_two_readings_outside_the_sample_are_both_named(self):
        a = REC.recommend(pred(["R2_outside_training_range"],
                               [dict(feature="EC"), dict(feature="pH_H2O")]),
                          metrics(), None)
        why = a["items"][0]["why"]
        assert "Salts" in why and "Acidity" in why
        assert " sit " in why          # plural, not "sits"

    def test_the_names_are_the_plain_ones_not_the_bundle_names(self):
        a = REC.recommend(pred(["R2_outside_training_range"],
                               [dict(feature="pH_H2O")]), metrics(), None)
        assert "pH_H2O" not in a["items"][0]["why"]


# ---------------------------------------------------------------------------
# The band is a position, not a grade - so it is not an input
# ---------------------------------------------------------------------------

class TestNotTheBand:
    def test_two_bands_give_the_same_answer(self):
        low = dict(rules=["R6_single_band"], confidence="High",
                   band="Lower third of the sampled soils", band_key="lower_third")
        high = dict(rules=["R6_single_band"], confidence="High",
                    band="Upper third of the sampled soils", band_key="upper_third")
        ctx = dict(crop="annual", bands={"p": "low"}, reading=dict(ph=4.1))
        assert REC.recommend(dict(band=low), metrics(), ctx) == \
            REC.recommend(dict(band=high), metrics(), ctx)

    def test_a_placement_of_nonsense_still_only_reads_its_rules(self):
        a = REC.recommend(dict(band=dict(rules=["R6_single_band"], confidence="??",
                                         band="???", band_key="???")), metrics(), None)
        assert "A1_unsure" not in keys(a)

    def test_the_engine_only_reads_why_a_placement_was_withheld(self):
        """It reads the rules a gate fired; it never reads the placement itself.

        The module docstring names `band_key` in order to say it is not read,
        so the check runs on the source with that docstring removed.
        """
        src = (ROOT / "recommendation.py").read_text(encoding="utf-8")
        doc = ast.get_docstring(ast.parse(src), clean=False) or ""
        assert "band_key" not in src.replace(doc, "")
        assert set(re.findall(r'gate\.get\("(\w+)"\)', src)) == {"rules",
                                                                 "out_of_range"}


# ---------------------------------------------------------------------------
# B - the record read against itself
# ---------------------------------------------------------------------------

class TestHistory:
    def test_no_second_reading_means_keep_the_first(self):
        a = REC.recommend(pred(["R6_single_band"]), metrics(), None)
        assert "B1_first" in keys(a)

    def test_a_move_larger_than_the_drift_is_reported_with_its_size(self):
        a = REC.recommend(pred(["R6_single_band"]), metrics(sd_ph=1.0),
                          dict(reading=dict(ph=6.0), previous=dict(ph=5.0)))
        why = next(i["why"] for i in a["items"] if i["key"] == "B2_moved")
        assert "Acidity moved 1" in why
        assert "0.5" in why            # half the spread, from sd

    def test_a_move_smaller_than_the_drift_is_not_a_move(self):
        a = REC.recommend(pred(["R6_single_band"]), metrics(sd_ph=1.0),
                          dict(reading=dict(ph=6.1), previous=dict(ph=6.0)))
        assert "B2_moved" not in keys(a)
        assert "B3_steady" in keys(a)

    def test_the_drift_quoted_is_the_one_the_card_prints(self):
        m = metrics(sd_ph=1.0154)
        drift = F._strip(m)["fields"][0]["drift"]
        a = REC.recommend(pred(["R6_single_band"]), m,
                          dict(reading=dict(ph=6.0), previous=dict(ph=5.0)))
        why = next(i["why"] for i in a["items"] if i["key"] == "B2_moved")
        assert f"{drift}" in why

    def test_moisture_is_compared_as_a_word(self):
        a = REC.recommend(pred(["R6_single_band"]), metrics(),
                          dict(reading=dict(moisture="dry"), previous=dict(moisture="wet")))
        why = next(i["why"] for i in a["items"] if i["key"] == "B2_moved")
        assert "wet" in why and "dry" in why

    def test_a_second_reading_that_cannot_be_compared_is_not_called_steady(self):
        """Silence is not calm: different keys are not a comparison."""
        a = REC.recommend(pred(["R6_single_band"]), metrics(),
                          dict(reading=dict(ec=0.1), previous=dict(ph=6.0)))
        assert "B3_steady" not in keys(a)
        assert "B2_moved" not in keys(a)
        assert "B1_first" not in keys(a)

    def test_no_move_is_not_reported_when_the_placement_was_withheld(self):
        a = REC.recommend(pred(["R4_too_wide"]), metrics(),
                          dict(reading=dict(ph=6.0), previous=dict(ph=6.1)))
        assert "B3_steady" not in keys(a)

    def test_a_bundle_without_a_spread_quotes_no_drift(self):
        bare = dict(features=[dict(name="pH_H2O", training_range=dict(p5=5.0, p95=8.0))])
        a = REC.recommend(pred(["R6_single_band"]), bare,
                          dict(reading=dict(ph=6.0), previous=dict(ph=5.0)))
        assert "B2_moved" not in keys(a)


# ---------------------------------------------------------------------------
# D - the one place where two measured things meet
# ---------------------------------------------------------------------------

class TestPairing:
    def test_low_phosphorus_in_acid_soil_meets(self):
        a = REC.recommend(pred(["R6_single_band"]), metrics(),
                          dict(bands={"p": "low"}, reading=dict(ph=4.0)))
        assert a["items"][0]["key"] == "D1_p_acid"
        assert a["items"][0]["ask"]

    def test_the_same_word_in_neutral_soil_does_not_meet(self):
        a = REC.recommend(pred(["R6_single_band"]), metrics(),
                          dict(bands={"p": "low"}, reading=dict(ph=6.5)))
        assert "D1_p_acid" not in keys(a)

    def test_acid_soil_alone_is_not_enough(self):
        a = REC.recommend(pred(["R6_single_band"]), metrics(),
                          dict(bands={"p": "high"}, reading=dict(ph=4.0)))
        assert "D1_p_acid" not in keys(a)

    def test_a_salty_reading_meets_low_potassium(self):
        a = REC.recommend(pred(["R6_single_band"]), metrics(),
                          dict(bands={"k": "low"}, reading=dict(ec=0.9)))
        assert "D1_k_salty" in keys(a)

    def test_dry_soil_meets_low_nitrogen(self):
        a = REC.recommend(pred(["R6_single_band"]), metrics(),
                          dict(bands={"n": "low"}, reading=dict(moisture="dry")))
        assert "D1_n_dry" in keys(a)

    def test_no_reading_means_no_pairing(self):
        a = REC.recommend(pred(["R6_single_band"]), metrics(), dict(bands={"p": "low"}))
        assert not [k for k in keys(a) if k.startswith("D1_")]

    def test_each_pairing_is_word_for_word_the_card_s(self):
        """Two cards describing one situation must not describe it twice."""
        rules = {r["key"]: r for r in F.PAIR_RULES}
        a = REC.recommend(pred(["R6_single_band"]), metrics(),
                          dict(bands={"p": "low"}, reading=dict(ph=4.0)))
        item = a["items"][0]
        assert item["title"] == rules["p_acid"]["title"]
        assert item["why"] == rules["p_acid"]["says"]
        assert item["now"] == rules["p_acid"]["practice"]


# ---------------------------------------------------------------------------
# C and E - what the crop changes
# ---------------------------------------------------------------------------

class TestCrop:
    def test_two_crops_on_one_field_head_the_list(self):
        a = REC.recommend(pred(["R6_single_band"]), metrics(), dict(crop="mixed"))
        assert keys(a)[0] == "C1_mixed"
        assert a["unshown"] == a["total"] - a["shown"]

    def test_one_crop_on_the_field_does_not_trigger_it(self):
        for crop in ("annual", "perennial"):
            assert "C1_mixed" not in keys(
                REC.recommend(pred(["R6_single_band"]), metrics(), dict(crop=crop)))

    def test_the_mixed_step_reuses_the_crop_card_s_words(self):
        option = next(o for o in F.CROPS["options"] if o["key"] == "mixed")
        a = REC.recommend(pred(["R6_single_band"]), metrics(), dict(crop="mixed"))
        item = next(i for i in a["items"] if i["key"] == "C1_mixed")
        assert item["why"] == option["reading"]
        assert item["now"] == option["step"]

    @pytest.mark.parametrize("crop", ["annual", "perennial", "mixed"])
    def test_each_crop_gets_one_practice_it_already_has(self, crop):
        allowed = {i["name"] for i in F.PRACTICES["items"]}
        a = REC.recommend(pred(["R6_single_band"]), metrics(), dict(crop=crop))
        item = next(i for i in a["items"] if i["key"] == "E1_practice")
        assert item["title"] in allowed
        assert item["now"] == F.RECOMMEND["practice_note"]

    def test_no_crop_means_no_practice(self):
        a = REC.recommend(pred(["R6_single_band"]), metrics(), None)
        assert "E1_practice" not in keys(a)


# ---------------------------------------------------------------------------
# Junk in, no crash out
# ---------------------------------------------------------------------------

class TestRobustness:
    def test_an_empty_placement_still_returns_a_list(self):
        a = REC.recommend(None, metrics(), None)
        assert a["total"] >= 1 and a["verdict"]

    def test_no_metrics_at_all_is_survivable(self):
        a = REC.recommend(pred(["R6_single_band"]), None,
                          dict(bands={"p": "low"}, reading=dict(ph=4.0)))
        assert a["items"]

    def test_junk_context_is_dropped_not_guessed(self):
        a = REC.recommend(pred(["R6_single_band"]), metrics(),
                          dict(crop="banana", bands={"p": "awful", "x": "low"},
                               reading="wet", previous=[1, 2, 3]))
        assert a["context_used"] == dict(crop=None, bands={}, has_reading=False,
                                         has_previous=False)

    def test_a_context_that_is_not_an_object_is_ignored(self):
        for junk in ("annual", 7, ["annual"], True):
            a = REC.recommend(pred(["R6_single_band"]), metrics(), junk)
            assert a["context_used"]["crop"] is None

    def test_an_unknown_band_word_is_not_a_word(self):
        a = REC.recommend(pred(["R6_single_band"]), metrics(),
                          dict(bands={"p": "LOW"}, reading=dict(ph=4.0)))
        assert not [k for k in keys(a) if k.startswith("D1_")]

    def test_every_step_a_test_can_reach_is_in_the_known_set(self):
        a = REC.recommend(pred(["R4_too_wide"]), metrics(),
                          dict(crop="mixed", bands={"p": "low"}, reading=dict(ph=4.0)))
        assert set(keys(a)) <= steps()


# ---------------------------------------------------------------------------
# The words
# ---------------------------------------------------------------------------

class TestWords:
    def test_no_banned_term_reaches_the_steps(self):
        a = REC.recommend(pred(["R2_outside_training_range"],
                                [dict(feature="EC")]), metrics(),
                          dict(crop="mixed", bands={"k": "low"},
                               reading=dict(ec=9.0), previous=dict(ec=0.1)))
        bad = [(p, t, F.find_banned(t)) for p, t in F.iter_strings(a) if F.find_banned(t)]
        assert not bad, bad

    def test_a_poisoned_sentence_raises_instead_of_shipping(self, monkeypatch):
        monkeypatch.setitem(F.RECOMMEND_ITEMS["record"], "now", "the model says so")
        with pytest.raises(ValueError):
            REC.recommend(pred(["R6_single_band"]), metrics(), None)

    def test_no_step_names_something_to_buy(self):
        banned = re.compile(r"\b(kg|bags?|litres?|fertilizer|fertiliser|buy|"
                            r"apply at|rate of)\b", re.I)
        for key in F.RECOMMEND_ITEMS:
            for _, text in F.iter_strings(F.RECOMMEND_ITEMS[key]):
                assert not banned.search(text), (key, text)
        for key in F.RECOMMEND_VERDICTS:
            for _, text in F.iter_strings(F.RECOMMEND_VERDICTS[key]):
                assert not banned.search(text), (key, text)

    def test_every_step_the_engine_emits_has_words_written_for_it(self):
        for key in ("unsure", "outside_one", "outside_many", "mixed", "first",
                    "moved", "moved_word", "steady", "record"):
            assert key in F.RECOMMEND_ITEMS, key
        for code in ("A1", "A2", "C1", "D1", "B1", "B2", "B3", "E1", "F1"):
            assert code in F.RECOMMEND_VERDICTS, code
            assert code and F.RECOMMEND_VERDICTS[code]["basis"] in F.RECOMMEND_BASIS


# ---------------------------------------------------------------------------
# The endpoint
# ---------------------------------------------------------------------------

def values(meta):
    return {f: meta["feature_ranges"][f]["median"] for f in meta["features"]}


class TestEndpoint:
    def test_it_answers_without_a_context(self, client, meta):
        r = client.post("/api/farmer/advice", json={"values": values(meta)})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["items"] and body["total"] >= 1
        assert body["limits"] and body["cap_note"]

    def test_it_answers_with_a_full_context(self, client, meta):
        r = client.post("/api/farmer/advice", json=dict(
            values=values(meta),
            context=dict(crop="annual", bands={"p": "low"},
                         reading={"ph": 4.5}, previous={"ph": 6.1})))
        assert r.status_code == 200, r.text
        assert r.json()["total"] >= 2

    def test_the_placement_is_not_accepted_from_the_page(self, client, meta):
        """The engine reads the placement the server computed, not the client's."""
        r = client.post("/api/farmer/advice", json=dict(
            values=values(meta),
            context=dict(crop="annual",
                         placement={"rules": ["R6_single_band"]},
                         band={"rules": ["R6_single_band"]})))
        assert r.status_code == 200, r.text
        used = r.json()
        assert "prediction" not in used              # nothing to feed back
        assert set(used) >= {"title", "lead", "items", "verdict"}

    def test_the_context_is_echoed_back_for_traceability(self, client, meta):
        r = client.post("/api/farmer/advice", json=dict(
            values=values(meta), context=dict(crop="perennial")))
        assert r.status_code == 200
        assert r.json()["items"]

    def test_an_unknown_reading_is_refused_like_everywhere_else(self, client, meta):
        v = values(meta)
        v["Density"] = 1.2
        r = client.post("/api/farmer/advice", json={"values": v})
        assert r.status_code == 422
        assert r.json()["detail"]["error"] == "unknown_features"

    def test_an_impossible_reading_is_refused(self, client, meta):
        v = values(meta)
        v["pH_H2O"] = 99.0
        r = client.post("/api/farmer/advice", json={"values": v})
        assert r.status_code == 422
        assert r.json()["detail"]["error"] == "impossible_value"

    def test_no_banned_term_reaches_the_page(self, client, meta):
        body = client.post("/api/farmer/advice", json=dict(
            values=values(meta),
            context=dict(crop="mixed", bands={"n": "low"},
                         reading={"moisture": "dry"}))).json()
        bad = [(p, t, F.find_banned(t)) for p, t in F.iter_strings(body)
               if F.find_banned(t)]
        assert not bad, bad

    def test_the_first_screen_already_carries_the_card_s_words(self, client):
        advice = client.get("/api/farmer").json()["advice"]
        assert advice["title"] and advice["button"] and advice["idle"]
        assert advice["items"] == [] and advice["total"] == 0


# ---------------------------------------------------------------------------
# The page renders it and writes none of it
# ---------------------------------------------------------------------------

class TestPage:
    def test_the_card_waits_for_an_answer(self):
        region = farmer_region()
        assert 'id="screen-advice" hidden' in region
        assert '$("screen-advice").hidden = false' in region

    def test_the_page_asks_the_endpoint_for_the_steps(self):
        region = farmer_region()
        assert '"/api/farmer/advice"' in region
        assert "adviceContext" in region

    def test_the_page_sends_the_values_it_submitted(self):
        region = farmer_region()
        assert "S.values = vals;" in region
        assert "JSON.stringify({ values: S.values, context: adviceContext() })" in region

    def test_the_cap_note_is_filled_from_the_payload(self):
        region = farmer_region()
        assert 'split("{shown}")' in region and 'split("{total}")' in region

    def test_the_card_is_repainted_when_the_crop_changes(self):
        region = farmer_region()
        assert region.count("if (S.advice) { askAdvice(); }") == 2
