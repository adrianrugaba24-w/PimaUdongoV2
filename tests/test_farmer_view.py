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


def function_body(region: str, name: str) -> str:
    """One function's text, from its name to the next function in the page."""
    i = region.index("function " + name + "(")
    j = region.index("\n  function ", i + len(name) + 10)
    return region[i:j]


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
        assert "not stored" in body
        assert "any name and any password" in body

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
        assert lg["farmer_username"] and lg["researcher_username"]
        assert lg["password_label"]
        region = login_region()
        assert 'id="username"' in region
        assert 'type="password"' in region
        assert 'for="username"' in region and 'for="password"' in region

    def test_it_prints_an_example_account(self, client):
        """The hint is one that works, not the only one that works."""
        lg = client.get("/api/login").json()["login"]
        for role in ("farmer", "researcher"):
            hint = lg[f"{role}_hint"].lower()
            assert role in hint
            assert "demo" in hint

    def test_the_form_never_sends_what_is_typed(self):
        """Nothing typed leaves the browser: no request, no body, no header."""
        region = login_region()
        assert "preventDefault" in region
        assert "location.assign" in region
        for forbidden in ("method=\"post\"", "method='post'", "FormData",
                          "Authorization", "XMLHttpRequest", "sendBeacon"):
            assert forbidden not in region, forbidden

    def test_the_sign_in_stores_nothing(self):
        """A password field that remembers what was typed is a lie."""
        region = login_region()
        for forbidden in ("localStorage", "sessionStorage", "document.cookie",
                          "indexedDB"):
            assert forbidden not in region, forbidden

    def test_the_farmer_page_keeps_readings_on_the_device_only(self):
        """One browser key, and no path from it to a request."""
        region = farmer_region()
        assert region.count("localStorage.setItem") == 1
        assert "pima.readings.v1" in region
        for name in ("saveReading", "clearReadings"):
            body = function_body(region, name)
            for forbidden in ("fetch(", "XMLHttpRequest", "sendBeacon"):
                assert forbidden not in body, (name, forbidden)

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


# ---------------------------------------------------------------------------
# The gate as rebuilt: two account types, one door, and a check that is printed
# ---------------------------------------------------------------------------

class TestEntryGate:
    def _login(self, client):
        return client.get("/api/login").json()["login"]

    def test_both_types_carry_the_same_six_fields(self, client):
        lg = self._login(client)
        for field in ("label", "action", "username", "placeholder", "hint",
                      "href"):
            for role in ("farmer", "researcher"):
                assert lg[f"{role}_{field}"], (role, field)

    def test_every_payload_string_reaches_the_page(self, client):
        """A key the page never reads is a sentence nobody ever sees."""
        region = login_region()
        for key in self._login(client):
            assert key in region, key

    def test_the_types_share_neither_a_name_nor_a_destination(self, client):
        lg = self._login(client)
        assert lg["farmer_label"] != lg["researcher_label"]
        assert lg["farmer_hint"] != lg["researcher_hint"]
        assert lg["farmer_href"] != lg["researcher_href"]

    def test_the_type_is_chosen_by_a_tab_that_cannot_submit(self):
        region = login_region()
        assert 'role="tablist"' in region
        assert region.count('role="tab"') == 2
        assert 'type="button"' in region
        assert "aria-selected" in region

    def test_the_password_can_be_read_back(self, client):
        """Typed on a phone in daylight, a password must be readable."""
        lg = self._login(client)
        assert lg["show"] and lg["hide"] and lg["show"] != lg["hide"]
        assert 'q.type = masked ? "text" : "password"' in login_region()

    def test_every_refusal_is_written_in_the_payload(self):
        region = login_region()
        for key in ("err_both", "err_user", "err_pass"):
            assert "L." + key in region, key

    def test_nothing_typed_is_compared_with_anything(self, client):
        """A door, not a check: the tab decides, the fields are not judged."""
        body = self._login(client)["body"].lower()
        assert "any name and any password" in body
        region = login_region()
        assert "demo_password" not in region
        assert "err_wrong" not in region

    def test_it_does_not_claim_the_two_views_are_walled_off(self, client):
        """No session exists, so the page must not promise one."""
        note = self._login(client)["note"].lower()
        assert "not what you may see" in note
        assert "cannot" not in note


class TestLearnMore:
    def test_it_is_hidden_until_sources_exist(self, client):
        panel = client.get("/api/farmer").json()["learn_more"]
        assert panel["visible"] is False
        assert "reference" in panel["reason"].lower()

    def test_the_page_respects_the_flag(self):
        region = farmer_region()
        assert 'id="learn" hidden' in region
        assert "!l.visible" in region or "l.visible" in region


# ---------------------------------------------------------------------------
# The guide: everything below the answer, in the order a worried farmer reads
# ---------------------------------------------------------------------------

class TestGuide:
    def _blocks(self, client):
        return client.get("/api/farmer").json()["guide"]["blocks"]

    def test_it_opens_on_how_far_to_trust_the_check(self, client):
        assert self._blocks(client)[0]["title"] == \
            "How much can you trust this check?"

    def test_every_block_carries_a_title_and_something_to_read(self, client):
        for b in self._blocks(client):
            assert b["title"], b
            assert b["kind"] in {"para", "list", "steps", "pairs"}, b
            assert b["intro"] or b["items"] or b["note"], b

    def test_the_lab_decision_covers_the_four_cases(self, client):
        block = next(b for b in self._blocks(client)
                     if "laboratory test" in b["title"].lower())
        assert len(block["items"]) == 4
        assert any("not sure" in i["body"] for i in block["items"])

    def test_sampling_is_a_numbered_sequence(self, client):
        block = next(b for b in self._blocks(client)
                     if "soil sample" in b["title"].lower())
        assert block["kind"] == "steps"
        assert len(block["items"]) == 5
        assert "extension officer" in block["note"].lower()

    def test_general_practices_say_they_are_not_about_this_reading(self, client):
        block = next(b for b in self._blocks(client)
                     if "practices" in b["title"].lower())
        assert "not based on your reading" in block["intro"].lower()
        assert "sources" in block["note"].lower()

    def test_no_block_quotes_a_figure(self, client):
        """The guide explains; every number a farmer sees comes from the result."""
        for b in self._blocks(client):
            for path, text in F.iter_strings(b):
                assert not re.search(r"\d\.\d", text), (path, text)

    def test_the_guide_is_scanned_like_every_other_string(self):
        """build() raises on a banned term; this proves the blocks are inside it."""
        assert "guide=_guide(metrics)" in \
            (ROOT / "farmer_view.py").read_text(encoding="utf-8")

    def test_the_page_is_one_page_not_four_tabs(self):
        region = farmer_region()
        assert 'role="tablist"' not in region
        assert 'id="screen-guide"' in region
        assert 'id="screen-result" hidden' in region


# ---------------------------------------------------------------------------
# The crop question: what one reading supports, annual against perennial
# ---------------------------------------------------------------------------

class TestCropQuestion:
    def _crop(self, client):
        return client.get("/api/farmer").json()["crop"]

    def test_it_offers_three_cycles(self, client):
        assert [o["key"] for o in self._crop(client)["options"]] == \
            ["annual", "perennial", "mixed"]

    def test_each_cycle_carries_a_reading_and_a_next_step(self, client):
        for o in self._crop(client)["options"]:
            assert o["button"] and o["name"], o["key"]
            assert o["reading"] and o["step"], o["key"]

    def test_the_two_cycles_do_not_share_their_wording(self, client):
        annual, perennial = self._crop(client)["options"][:2]
        assert annual["reading"] != perennial["reading"]
        assert annual["step"] != perennial["step"]

    def test_each_cycle_uses_only_the_practices_already_written(self, client):
        allowed = {i["name"] for i in F.PRACTICES["items"]}
        for o in self._crop(client)["options"]:
            assert o["practices"], o["key"]
            for p in o["practices"]:
                assert p["name"] in allowed

    def test_it_says_the_tool_does_not_rate_the_soil(self, client):
        note = self._crop(client)["health_note"]
        assert "does not rate" in note

    def test_no_crop_string_quotes_a_figure(self, client):
        for path, text in F.iter_strings(self._crop(client)):
            assert not re.search(r"\d", text), (path, text)

    def test_choosing_a_cycle_names_no_input_and_promises_no_outcome(self):
        banned = re.compile(r"\b(apply|spread|increase|reduce|you should|will "
                            r"improve|will increase|best|recommended)\b", re.I)
        for o in F.CROPS["options"]:
            for key in ("button", "name", "reading", "step"):
                assert not banned.search(o[key]), (o["key"], key, o[key])

    def test_the_page_asks_only_after_an_answer(self):
        region = farmer_region()
        assert 'id="screen-crop" hidden' in region
        assert '$("screen-crop").hidden = false' in region

    def test_the_page_renders_the_cycles_from_the_payload(self):
        region = farmer_region()
        assert "var c = V.crop;" in region
        assert "(c.options || [])" in region
        assert "V.crop.idle" in region


# ---------------------------------------------------------------------------
# Readings kept over time
# ---------------------------------------------------------------------------

class TestReadingStrip:
    def _strip(self, client):
        return client.get("/api/farmer").json()["strip"]

    def test_it_tracks_three_readings(self, client):
        keys = [x["key"] for x in self._strip(client)["fields"]]
        assert keys == ["ph", "ec", "moisture"]

    def test_the_two_sensor_readings_carry_a_drift_figure(self, client):
        f = {x["key"]: x for x in self._strip(client)["fields"]}
        assert f["ph"]["drift"] is not None
        assert f["ec"]["drift"] is not None

    def test_moisture_says_it_has_no_figure_of_its_own(self, client):
        """It is not an input of this build, so it is compared as a word."""
        f = {x["key"]: x for x in self._strip(client)["fields"]}
        assert f["moisture"]["drift"] is None
        assert "no figure" in f["moisture"]["drift_words"]
        assert [c["key"] for c in f["moisture"]["choices"]] == \
            ["dry", "damp", "wet"]

    def test_the_drift_is_half_the_spread_of_that_reading(self):
        metrics = _mini_metrics()
        metrics["features"][0]["training_range"]["sd"] = 1.02
        f = {x["key"]: x for x in F._strip(metrics)["fields"]}
        assert f["ph"]["drift"] == pytest.approx(0.51)

    def test_a_bundle_without_a_spread_gets_no_figure(self):
        """A missing figure must not become a borrowed one."""
        f = {x["key"]: x for x in F._strip(_mini_metrics())["fields"]}
        assert f["ph"]["drift"] is None
        assert "no figure" in f["ph"]["drift_words"]

    def test_the_strip_is_inside_the_build_scan(self):
        src = (ROOT / "farmer_view.py").read_text(encoding="utf-8")
        assert "strip=_strip(metrics)" in src

    def test_the_page_gives_each_reading_a_place(self):
        region = farmer_region()
        for anchor in ('id="strip-fields"', 'id="strip-compare"',
                       'id="strip-save"', 'id="strip-date"'):
            assert anchor in region, anchor


# ---------------------------------------------------------------------------
# The soil test read beside a reading
# ---------------------------------------------------------------------------

class TestPairing:
    def _pair(self, client):
        return client.get("/api/farmer").json()["pairing"]

    def test_every_rule_pairs_a_soil_test_word_with_a_reading(self, client):
        for r in self._pair(client)["rules"]:
            assert r["needs"]["nutrient"] in ("n", "p", "k"), r["key"]
            assert r["needs"]["band"] in ("low", "medium", "high"), r["key"]
            assert r["needs"]["reading"] in ("ph", "ec", "moisture"), r["key"]

    def test_no_rule_quotes_a_figure(self, client):
        """A rate would need a trial this project has not run."""
        for r in self._pair(client)["rules"]:
            for path, text in F.iter_strings(r):
                assert not re.search(r"\d", text), (r["key"], path, text)

    def test_no_rule_tells_the_farmer_what_to_apply(self, client):
        banned = re.compile(r"\b(apply|spread|increase|reduce|you should|will "
                            r"improve|will increase|best|recommended)\b", re.I)
        for r in self._pair(client)["rules"]:
            for path, text in F.iter_strings(r):
                assert not banned.search(text), (r["key"], path, text)

    def test_each_rule_speaks_to_every_crop_cycle(self, client):
        for r in self._pair(client)["rules"]:
            for key in ("annual", "perennial", "mixed"):
                assert r["horizon"][key], (r["key"], key)

    def test_every_rule_says_what_to_ask_and_one_practice(self, client):
        for r in self._pair(client)["rules"]:
            assert r["ask"], r["key"]
            assert r["practice"], r["key"]

    def test_the_marks_come_from_the_sample(self, client):
        p = self._pair(client)
        assert p["marks"]["ph_low"] is not None
        assert p["marks"]["ph_high"] is not None
        assert p["marks"]["ec_high"] is not None
        assert p["marks"]["ph_low"] < p["marks"]["ph_high"]

    def test_the_fallback_still_says_what_comes_next(self, client):
        f = self._pair(client)["fallback"]
        assert f["title"] and f["says"] and f["ask"] and f["practice"]

    def test_the_pairing_is_inside_the_build_scan(self):
        src = (ROOT / "farmer_view.py").read_text(encoding="utf-8")
        assert "pairing=_pairing(metrics)" in src

    def test_the_page_picks_the_rule_from_the_payload(self):
        region = farmer_region()
        assert '"data-nutrient"' in region.replace("'", '"')
        assert "p.rules" in region
        assert "p.fallback" in region
