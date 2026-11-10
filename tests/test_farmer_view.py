"""
tests/test_farmer_view.py  -  the audience split.

The farmer screens are the ones that can go wrong without anyone noticing: a
technical word gets through, a colour carries a meaning on its own, or a
sentence softens an answer that the numbers do not support.  Every one of those
is a test here.

The banned-terms list is config (`farmer_view.BANNED_TERMS`).  Nothing in this
file keeps a second copy of it: the tests import the list and the matcher, so a
word added in `farmer_view.py` is enforced by the next run.
"""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import farmer_view as F

PAGE = ROOT / "web" / "farmer.html"
RESEARCH = ROOT / "web" / "index.html"
LOGIN_PAGE = ROOT / "web" / "login.html"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def farmer_region() -> str:
    html = PAGE.read_text(encoding="utf-8")
    a = html.index("<!-- farmer:begin -->")
    b = html.index("<!-- farmer:end -->")
    return html[a:b]


def login_region() -> str:
    html = LOGIN_PAGE.read_text(encoding="utf-8")
    a = html.index("<!-- login:begin -->")
    b = html.index("<!-- login:end -->")
    return html[a:b]


def payload(meta):
    return {"values": {f: meta["feature_ranges"][f]["median"] for f in meta["features"]}}


def _mini_metrics():
    """A hand-built metrics dict, so every headline branch can be reached."""
    return dict(
        target=dict(name="Total carbon", unit="percent (g/100 g)", unit_short="%",
                    is_sample_data=False),
        features=[dict(name="pH_H2O", training_range=dict(median=6.2),
                       physical_bounds=[0, 14], unit=None),
                  dict(name="EC", training_range=dict(median=90.0),
                       physical_bounds=[0, 50], unit=None)],
        bands=dict(cuts=[0.65, 1.44], observed_range=[0.1, 11.0],
                   bands=[dict(key="lower_third",
                               label="Lower third of the sampled soils"),
                          dict(key="middle_third",
                               label="Middle third of the sampled soils"),
                          dict(key="upper_third",
                               label="Upper third of the sampled soils")]),
        noise=dict(break_even={"train_clean|spatial": 0.5,
                               "train_noisy|spatial": 0.5, "model": "rf"}),
    )


def _pred(rules, confidence="Low", band=None, low=0.9, high=1.1, est=1.0):
    return dict(prediction=est, interval=dict(low=low, high=high),
                band=dict(confidence=confidence, rules=list(rules), band=band))


# ---------------------------------------------------------------------------
# The config: the list, and the matcher that enforces it
# ---------------------------------------------------------------------------

class TestBannedTermsConfig:
    REQUIRED = ("R2", "RMSE", "MAE", "RPIQ", "CV", "fold", "conformal",
                "interval", "coverage", "baseline", "noise", "sweep", "hash",
                "sha256", "pipeline", "spatial CV", "training range")

    def test_every_term_from_the_brief_is_in_the_list(self):
        missing = [t for t in self.REQUIRED if t not in F.BANNED_TERMS]
        assert not missing, f"the banned-terms config is missing {missing}"

    def test_the_target_is_not_called_total_carbon(self):
        for term in ("total carbon", "SOC", "organic carbon"):
            assert term in F.BANNED_TERMS

    @pytest.mark.parametrize("term", REQUIRED)
    def test_the_matcher_finds_each_term(self, term):
        assert F.find_banned(f"a sentence about {term} here")

    def test_the_matcher_is_case_insensitive(self):
        assert F.find_banned("Rmse") and F.find_banned("RMSE")

    def test_the_matcher_catches_plurals_and_inflections(self):
        assert F.find_banned("across all folds")
        assert F.find_banned("the noisy sweeps")
        assert F.find_banned("a modelled answer")

    def test_the_matcher_leaves_plain_english_alone(self):
        for sentence in (
            "This soil sits in the middle third of the sampled soils.",
            "A laboratory measurement from the same spot settles it.",
            "The range we can defend is wide.",
        ):
            assert not F.find_banned(sentence), sentence

    def test_matcher_reads_the_r_squared_symbol(self):
        assert F.find_banned("R\u00b2 = 0.09")

    def test_soft_banned_words_are_tracked_separately(self):
        """A watch list, not a rule: the copy does use "estimate" and "range"."""
        assert "estimate" in F.SOFT_BANNED
        assert "estimate" not in F.BANNED_TERMS


# ---------------------------------------------------------------------------
# Every farmer string, from the API
# ---------------------------------------------------------------------------

class TestFarmerPayloadStrings:
    def test_chrome_200(self, client):
        assert client.get("/api/farmer").status_code == 200

    def test_no_banned_term_anywhere_in_the_chrome(self, client):
        body = client.get("/api/farmer").json()
        bad = [(p, t, F.find_banned(t)) for p, t in F.iter_strings(body)
               if F.find_banned(t)]
        assert not bad, f"banned terms reached the farmer payload: {bad}"

    def test_no_banned_term_anywhere_in_a_result(self, client, meta):
        r = client.post("/api/farmer/predict", json=payload(meta))
        assert r.status_code == 200, r.text
        bad = [(p, t, F.find_banned(t)) for p, t in F.iter_strings(r.json())
               if F.find_banned(t)]
        assert not bad, f"banned terms reached the farmer result: {bad}"

    def test_the_scan_reaches_a_real_number_of_strings(self, client):
        """A scanner that inspects nothing passes everything."""
        strings = list(F.iter_strings(client.get("/api/farmer").json()))
        assert len(strings) >= 40

    def test_the_target_is_called_soil_carbon(self, client):
        t = client.get("/api/farmer").json()["target"]
        assert t["label"] == "Soil carbon"

    def test_the_explainer_is_one_short_idea(self, client):
        text = client.get("/api/farmer").json()["target"]["explainer"]
        assert len(text.split()) <= 22
        assert text.count(".") <= 2

    def test_every_field_label_is_plain(self, client, meta):
        fields = client.get("/api/farmer").json()["form"]["fields"]
        assert [f["name"] for f in fields] == list(meta["features"])
        for f in fields:
            assert f["label"] and not F.find_banned(f["label"])
            assert f["hint"] and not F.find_banned(f["hint"])
            assert f["handbook"] is True, f"no plain wording for {f['name']}"


# ---------------------------------------------------------------------------
# The page
# ---------------------------------------------------------------------------

class TestFarmerPage:
    def test_the_page_is_marked_for_the_scanner(self):
        assert "<!-- farmer:begin -->" in PAGE.read_text(encoding="utf-8")
        assert "<!-- farmer:end -->" in PAGE.read_text(encoding="utf-8")

    def test_no_banned_term_in_the_farmer_block(self):
        region = farmer_region()
        bad = {t: F.PATTERNS[t].search(region).group(0)
               for t in F.BANNED_TERMS if F.PATTERNS[t].search(region)}
        assert not bad, f"banned terms written into the page: {bad}"

    def test_the_page_writes_none_of_its_own_prose(self):
        """Every sentence on the farmer screens arrives from the API."""
        region = farmer_region()
        copy = re.findall(r"textContent\s*=\s*[\"']([^\"']{4,})[\"']", region)
        assert not copy, f"hard-coded copy in the page: {copy[:5]}"

    def test_the_required_banner_survives(self):
        assert "Not validated on field sensors or Ugandan farms" in \
            PAGE.read_text(encoding="utf-8")

    def test_the_page_fetches_and_bakes_no_numbers(self):
        html = PAGE.read_text(encoding="utf-8")
        assert "fetch(" in html
        assert not re.search(r"\b0\.\d{2,}", re.sub(r"<style>.*?</style>", "",
                                                     html, flags=re.S)), \
            "a result-like decimal is written into the page"

    def test_technical_words_moved_to_the_research_view(self):
        research = RESEARCH.read_text(encoding="utf-8")
        assert "RMSE" in research
        assert "coverage" in research.lower()

    def test_both_views_are_served(self, client):
        assert client.get("/").status_code == 200              # the entry gate
        assert client.get("/login").status_code == 200
        assert client.get("/farmer").status_code == 200
        assert client.get("/researcher").status_code == 200

    def test_the_root_is_the_entry_gate_not_a_view(self, client):
        """`/` is the login page; `/farmer` is the farmer page."""
        assert "login:begin" in client.get("/").text
        assert "farmer:begin" in client.get("/farmer").text
        assert "login:begin" not in client.get("/farmer").text
        assert "farmer:begin" not in client.get("/researcher").text

    def test_the_researcher_link_is_labelled(self, client):
        nav = client.get("/api/farmer").json()["nav"]
        assert nav["researcher"] == "For researchers"
        assert nav["researcher_href"] == "/researcher"


# ---------------------------------------------------------------------------
# The traffic light: never colour on its own
# ---------------------------------------------------------------------------

class TestTrafficLight:
    @pytest.mark.parametrize("confidence", ["High", "Medium", "Low"])
    def test_icon_and_words_travel_together(self, confidence):
        light = F.LIGHTS[confidence]
        assert light["icon"].strip()
        assert light["words"].strip()
        assert light["icon"] != light["words"]

    @pytest.mark.parametrize("confidence", ["High", "Medium", "Low"])
    def test_the_words_are_not_a_colour(self, confidence):
        words = F.LIGHTS[confidence]["words"].lower()
        for colour in ("green", "amber", "red"):
            assert colour not in words

    @pytest.mark.parametrize("confidence", ["High", "Medium", "Low"])
    def test_the_words_carry_no_banned_term(self, confidence):
        assert not F.find_banned(F.LIGHTS[confidence]["words"])

    def test_a_result_always_carries_both(self):
        for rules, conf, band in ((["R6_single_band"], "High", "Middle third"),
                                  (["R5_crosses_one_cut"], "Medium", None),
                                  (["R4_too_wide"], "Low", None)):
            light = F.result_block(_mini_metrics(), _pred(rules, conf, band))["light"]
            assert light["icon"] and light["words"]

    def test_the_page_renders_the_icon_and_the_words(self):
        region = farmer_region()
        assert "L.icon" in region and "L.words" in region

    def test_an_unknown_confidence_falls_back_to_the_quietest_light(self):
        out = F.result_block(_mini_metrics(), _pred(["R4_too_wide"], "nonsense"))
        assert out["light"]["key"] == "red"


# ---------------------------------------------------------------------------
# The headline: never a confident sentence for an unusable answer
# ---------------------------------------------------------------------------

class TestHeadline:
    def test_a_range_wider_than_a_band_is_too_uncertain(self):
        out = F.result_block(_mini_metrics(), _pred(["R4_too_wide"]))
        assert out["headline"] == "This estimate is too uncertain to place the soil."

    def test_a_range_crossing_one_boundary_is_too_uncertain(self):
        out = F.result_block(_mini_metrics(), _pred(["R5_crosses_one_cut"], "Medium"))
        assert out["headline"] == "This estimate is too uncertain to place the soil."

    def test_the_two_wide_cases_use_the_same_sentence(self):
        a = F.result_block(_mini_metrics(), _pred(["R4_too_wide"]))
        b = F.result_block(_mini_metrics(), _pred(["R5_crosses_one_cut"], "Medium"))
        assert a["headline"] == b["headline"] == F.TOO_UNCERTAIN

    def test_no_headline_quotes_a_number(self):
        cases = ((["R4_too_wide"], "Low", None), (["R5_crosses_one_cut"], "Medium", None),
                 (["R2_outside_training_range"], "Low", None),
                 (["R3_no_bands"], "Low", None), (["R1_no_interval"], "Low", None),
                 (["R6_single_band"], "High", "Upper third of the sampled soils"))
        for rules, conf, band in cases:
            headline = F.result_block(_mini_metrics(), _pred(rules, conf, band))["headline"]
            assert not re.search(r"\d", headline), headline

    def test_a_placed_answer_names_the_third(self):
        out = F.result_block(_mini_metrics(),
                             _pred(["R6_single_band"], "High",
                                   "Middle third of the sampled soils"))
        assert "middle third of the sampled soils" in out["headline"]

    def test_an_unknown_rule_degrades_to_no_answer(self):
        out = F.result_block(_mini_metrics(), _pred(["R9_something_new"]))
        assert out["headline"] == F.HEADLINES["R1_no_interval"][0]

    def test_a_bundle_without_bands_says_so(self, client, meta):
        r = client.post("/api/farmer/predict", json=payload(meta)).json()
        assert r["result"]["headline"] == F.HEADLINES["R3_no_bands"][0]


# ---------------------------------------------------------------------------
# One result screen: headline, bar, light, one next step
# ---------------------------------------------------------------------------

class TestResultScreen:
    def test_all_four_parts_are_present(self, client, meta):
        r = client.post("/api/farmer/predict", json=payload(meta)).json()["result"]
        assert r["headline"]
        assert r["bar"] is not None
        assert r["light"]["icon"] and r["light"]["words"]
        assert r["next_step"]["title"] and r["next_step"]["body"]

    def test_there_is_exactly_one_next_step(self):
        step = F.NEXT_STEP
        assert set(step) == {"title", "body", "how_to_read", "lab_note"}
        assert "laboratory" in step["body"].lower()

    def test_the_next_step_uses_no_imperative_verb(self):
        banned = re.compile(r"\b(apply|add|increase|reduce|spread|incorporate|"
                            r"plant|irrigate|fertilis|fertiliz|consider|"
                            r"you should|we recommend|recommended)\b", re.I)
        for key in ("title", "body", "how_to_read", "lab_note"):
            assert not banned.search(F.NEXT_STEP[key]), F.NEXT_STEP[key]

    def test_the_bar_matches_the_numbers_it_came_from(self, client, meta):
        body = client.post("/api/farmer/predict", json=payload(meta)).json()
        bar = body["result"]["bar"]
        src = client.post("/api/predict", json=payload(meta)).json()
        assert bar["low"] == src["interval"]["low"]
        assert bar["high"] == src["interval"]["high"]
        assert bar["estimate"] == src["prediction"]

    def test_the_bar_positions_are_inside_the_track(self, client, meta):
        bar = client.post("/api/farmer/predict", json=payload(meta)).json()["result"]["bar"]
        for key in ("low_pct", "high_pct", "estimate_pct"):
            assert 0.0 <= bar[key] <= 100.0, (key, bar[key])
        assert bar["low_pct"] <= bar["estimate_pct"] <= bar["high_pct"]

    def test_the_bar_says_it_is_arithmetic(self, client, meta):
        bar = client.post("/api/farmer/predict", json=payload(meta)).json()["result"]["bar"]
        assert "arithmetic" in bar["source"]

    def test_the_estimate_is_not_dressed_up_as_a_soil_test(self, client, meta):
        caveat = client.post("/api/farmer/predict", json=payload(meta)).json()["result"]["caveat"]
        assert "not a soil test" in caveat


# ---------------------------------------------------------------------------
# "Is my sensor good enough?"
# ---------------------------------------------------------------------------

class TestSensorCard:
    def test_the_card_exists_and_asks_the_question(self, client):
        assert client.get("/api/farmer").json()["sensor"]["title"] == \
            "Is my sensor good enough?"

    def test_the_number_is_the_one_in_the_metrics_file(self, client):
        card = client.get("/api/farmer").json()["sensor"]
        metrics = client.get("/api/metrics").json()
        published = [float(v) for k, v in metrics["noise"]["break_even"].items()
                     if k != "model" and isinstance(v, (int, float))]
        assert card["values"] == published
        if not published:
            # A run that never reached a break-even point stores nulls, not a
            # figure.  The card must say that instead of quoting a number.
            assert card["finding"] == "never_reached"
            assert card["value"] is None
            assert card["available"] is False
            return
        if len(set(published)) == 1:
            assert card["value"] == published[0]
        else:
            # Two arms disagree, so no single figure is shown as *the* number.
            assert card["value"] is None
            assert (card["low"], card["high"]) == (min(published), max(published))

    def test_the_number_changes_when_the_file_changes(self, api, client, monkeypatch):
        """Proves the figure is read, not typed."""
        monkeypatch.setitem(api.METRICS["noise"]["break_even"],
                            "train_clean|spatial", 0.75)
        card = client.get("/api/farmer").json()["sensor"]
        assert card["value"] == 0.75

    def test_it_never_calls_a_sensor_adequate(self, client):
        """
        This project has measured no sensor, so the card cannot bless one.

        The card's `title` is the question itself - "Is my sensor good
        enough?" - and is checked by the test above.  The claim scan therefore
        runs over the sentences that answer it, never over the question.
        """
        card = client.get("/api/farmer").json()["sensor"]
        assert card["title"] == "Is my sensor good enough?"
        prose = " ".join(str(card.get(k) or "") for k in
                          ("headline", "body", "unit_words")).lower()
        for claim in ("your sensor is", "good enough", "sufficient", "adequate"):
            assert claim not in prose, claim

    def test_a_test_that_never_reached_a_point_says_so(self):
        m = _mini_metrics()
        m["noise"]["break_even"] = {"train_clean|spatial": None,
                                    "train_noisy|spatial": None}
        card = F.build(m)["sensor"]
        assert card["finding"] == "never_reached"
        assert card["value"] is None
        assert card["available"] is False

    def test_an_absent_test_is_not_an_invented_one(self):
        m = _mini_metrics()
        m["noise"]["break_even"] = {}
        card = F.build(m)["sensor"]
        assert card["finding"] == "not_recorded"
        assert card["value"] is None
        assert not F.find_banned(card["headline"])


# ---------------------------------------------------------------------------
# The entry gate: a chooser that leads to both views
# ---------------------------------------------------------------------------

class TestLogin:
    def test_the_label_is_demo_only(self, client):
        assert client.get("/api/login").json()["login"]["label"] == "Demo only"

    def test_it_says_what_it_does_not_do(self, client):
        body = client.get("/api/login").json()["login"]["body"].lower()
        assert "nothing is stored" in body
        assert "no sign-in is checked" in body

    def test_it_offers_both_destinations(self, client):
        lg = client.get("/api/login").json()["login"]
        assert lg["farmer_href"] == "/farmer"
        assert lg["researcher_href"] == "/researcher"
        assert lg["farmer_action"] and lg["researcher_action"]
        assert lg["farmer_action"] != lg["researcher_action"]

    def test_both_destinations_are_served(self, client):
        lg = client.get("/api/login").json()["login"]
        for href in (lg["farmer_href"], lg["researcher_href"]):
            assert client.get(href).status_code == 200, href

    def test_it_has_a_name_and_a_password_field(self, client):
        lg = client.get("/api/login").json()["login"]
        assert lg["username_label"] and lg["password_label"]
        region = login_region()
        assert 'id="username"' in region
        assert 'type="password"' in region
        assert 'for="username"' in region and 'for="password"' in region

    def test_it_says_any_password_will_do(self, client):
        """A form that looks like a check must say that it is not one."""
        body = client.get("/api/login").json()["login"]["body"].lower()
        assert "any name and any password" in body

    def test_the_form_never_sends_what_is_typed(self):
        """Nothing typed leaves the browser: no request, no body, no header."""
        region = login_region()
        assert "preventDefault" in region
        assert "location.assign" in region
        for forbidden in ("method=\"post\"", "method='post'", "FormData",
                          "Authorization", "XMLHttpRequest", "sendBeacon"):
            assert forbidden not in region, forbidden

    def test_nothing_is_stored(self):
        for region in (farmer_region(), login_region()):
            assert "localStorage" not in region
            assert "sessionStorage" not in region
            assert "document.cookie" not in region
            assert "indexedDB" not in region

    def test_the_farmer_page_no_longer_carries_its_own_gate(self):
        """One gate, at `/`; the farmer page is a destination, not a sign-in."""
        assert 'id="signin"' not in farmer_region()
        assert 'id="start-link"' in farmer_region()

    def test_no_banned_term_in_the_login_payload(self, client):
        bad = [(p, t, F.find_banned(t)) for p, t in F.iter_strings(client.get("/api/login").json())
               if F.find_banned(t)]
        assert not bad, f"banned terms reached the entry gate: {bad}"

    def test_no_banned_term_in_the_login_block(self):
        region = login_region()
        bad = {t: F.PATTERNS[t].search(region).group(0)
               for t in F.BANNED_TERMS if F.PATTERNS[t].search(region)}
        assert not bad, f"banned terms written into the entry page: {bad}"

    def test_the_entry_page_carries_the_banner(self):
        assert "Not validated on field sensors or Ugandan farms" in \
            LOGIN_PAGE.read_text(encoding="utf-8")

    def test_the_entry_page_bakes_no_numbers(self):
        html = re.sub(r"<style>.*?</style>", "",
                      LOGIN_PAGE.read_text(encoding="utf-8"), flags=re.S)
        assert "fetch(" in html
        assert not re.search(r"\b0\.\d{2,}", html), "a figure is written into the page"

    def test_the_pages_wording_comes_from_the_api(self):
        """The two labels are rendered, not written into the markup."""
        region = login_region()
        assert "L.farmer_action" in region and "L.researcher_action" in region
        copy = re.findall(r"textContent\s*=\s*[\"']([^\"']{4,})[\"']", region)
        assert not copy, f"hard-coded copy in the entry page: {copy[:5]}"


class TestLearnMore:
    def test_it_is_hidden_until_sources_exist(self, client):
        panel = client.get("/api/farmer").json()["learn_more"]
        assert panel["visible"] is False
        assert "reference" in panel["reason"].lower()

    def test_the_page_respects_the_flag(self):
        region = farmer_region()
        assert 'id="learn" hidden' in region
        assert "!l.visible" in region or "l.visible" in region
