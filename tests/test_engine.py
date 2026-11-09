"""Walk the call graph with typed replies. No audio, no network, no credits."""
import pytest

from backend import engine

LANGS = ["en", "hi", "bn"]


def new(lang="en"):
    return engine.new_session("digital_arrest", lang)


def advance_to(s, node, reply="yes"):
    """Cooperate until the caller reaches `node`."""
    for _ in range(12):
        if s.node == node:
            return s
        engine.step(s, reply)
    raise AssertionError(f"never reached {node}, stuck at {s.node}")


# ---------------------------------------------------------------- the soft path

def test_cooperating_walks_the_helper_script_in_order():
    s = new()
    seen = [s.node]
    for _ in range(5):
        engine.step(s, "yes")
        seen.append(s.node)
    assert seen == ["greet", "parcel", "reassure", "isolate", "verify", "otp_demand"]


def test_full_compliance_leaks_otp():
    s = advance_to(new(), "otp_demand")
    res = engine.step(s, f"it is {s.otp}")
    assert res["outcome"] == "lose" and res["done"]
    assert res["debrief"]["outcome"] == "lose"
    assert any(t["worked"] for t in res["debrief"]["tactics"])


def test_no_pressure_lines_before_the_user_doubts():
    pressure = {"pushback", "final_early", "otp_pressure", "final_warning"}
    s = new()
    for _ in range(5):
        engine.step(s, "yes")
        assert s.node not in pressure


# ---------------------------------------------------------------- doubt -> reassurance -> pressure

def test_first_doubt_gets_reassurance_and_then_resumes_where_it_left_off():
    s = advance_to(new(), "isolate")
    engine.step(s, "no I don't trust this")
    assert s.node == "reassure_doubt"
    engine.step(s, "okay fine")
    assert s.node == "verify", "should continue with the step after the one that was interrupted"


def test_second_doubt_brings_pressure():
    s = advance_to(new(), "isolate")
    engine.step(s, "no")
    assert s.node == "reassure_doubt"
    engine.step(s, "no I am not doing this")
    assert s.node == "pushback"
    engine.step(s, "no")
    assert s.node == "final_early"
    res = engine.step(s, "no")
    assert res["outcome"] == "win"


def test_giving_in_after_pressure_resumes_the_script():
    s = advance_to(new(), "isolate")
    engine.step(s, "no")
    engine.step(s, "no")
    assert s.node == "pushback"
    engine.step(s, "okay okay")
    assert s.node == "verify"


def test_doubt_at_the_very_start_resumes_to_the_parcel_story():
    s = new()
    engine.step(s, "no this is fake")
    assert s.node == "reassure_doubt"
    engine.step(s, "okay go on")
    assert s.node == "parcel"


def test_code_ladder_is_soft_then_pressure_then_end():
    s = advance_to(new(), "otp_demand")
    engine.step(s, "no, this is a scam")
    assert s.node == "otp_soft"
    engine.step(s, "never")
    assert s.node == "otp_pressure"
    engine.step(s, "I am not telling you")
    assert s.node == "final_warning"
    res = engine.step(s, "I said no, I am hanging up and calling 1930")
    assert res["outcome"] == "win"


def test_saying_yes_without_digits_is_re_asked_once_then_treated_as_a_refusal():
    s = advance_to(new(), "otp_demand")
    first = engine.step(s, "yes")
    assert s.node == "otp_demand" and first["reply"]["text"].startswith("The OTP that came")   # re-asked once
    second = engine.step(s, "okay")                     # still no digits: never the same line twice
    assert s.node == "otp_soft" and second["reply"]["text"] != first["reply"]["text"]


def test_the_caller_never_repeats_the_same_clarify_line_back_to_back():
    s = new()
    seen = []
    for _ in range(12):
        res = engine.step(s, "what do you mean")
        if res["done"] or not res["reply"]:
            break
        seen.append(res["reply"]["text"])
    assert all(a != b for a, b in zip(seen, seen[1:])), "same line twice in a row"


def test_hangup_ends_call_immediately():
    s = new()
    res = engine.step(s, "I am hanging up")
    assert res["done"] and res["outcome"] == "win" and s.hung_up
    assert res["reply"] is None


def test_confused_repeats_same_node_with_clarification():
    s = new()
    res = engine.step(s, "I don't understand")
    assert s.node == "greet" and "put it simply" in res["reply"]["text"]


def test_otp_node_clarify_is_specific():
    s = advance_to(new(), "otp_demand")
    res = engine.step(s, "which code?")
    assert s.node == "otp_demand" and "OTP" in res["reply"]["text"]


def test_two_silences_end_the_call():
    s = new()
    assert not engine.step(s, "")["done"]
    res = engine.step(s, "")
    assert res["done"] and res["outcome"] == "idle"


def test_loop_is_bounded():
    # Always saying "yes" must not loop forever.
    s = new()
    for _ in range(40):
        res = engine.step(s, "yes")
        if res["done"]:
            break
    assert s.done


def test_wrong_number_at_otp_node_still_counts_as_leak():
    s = advance_to(new(), "otp_demand")
    res = engine.step(s, "one two three four five six")
    assert res["outcome"] == "lose"


def test_code_can_be_given_after_being_pressured():
    s = advance_to(new(), "otp_demand")
    engine.step(s, "no")
    engine.step(s, "no")
    assert s.node == "otp_pressure"
    res = engine.step(s, f"fine, {' '.join(s.otp)}")
    assert res["outcome"] == "lose"


# ---------------------------------------------------------------- content integrity

@pytest.mark.parametrize("lang", LANGS)
def test_every_line_and_debrief_key_exists(lang):
    graph = engine.load_graph("digital_arrest")
    lines = engine.load_lines("digital_arrest", lang)
    for node_id, node in graph["nodes"].items():
        assert node_id in lines["lines"], f"{lang}: missing line for node {node_id}"
        for t in node.get("tactics", []):
            assert t in lines["debrief"]["tactics"], f"{lang}: missing tactic text {t}"
    for key in ("generic.clarify", "generic.silence", "generic.unknown", "otp.clarify"):
        assert key in lines["lines"], f"{lang}: missing {key}"
    assert set(lines["debrief"]["summary"]) == {"win", "win_passive", "lose", "idle"}


@pytest.mark.parametrize("lang", LANGS)
def test_graph_targets_exist(lang):
    graph = engine.load_graph("digital_arrest")
    special = {"@clarify", "@resume"}
    for node_id, node in graph["nodes"].items():
        for intent, target in node.get("on", {}).items():
            assert target in special or target in graph["nodes"], f"{node_id}.{intent} -> {target}"
        if "on_exhausted" in node:
            assert node["on_exhausted"] in graph["nodes"]


@pytest.mark.parametrize("lang", ["hi", "bn"])
def test_regional_language_leak_via_digit_words(lang):
    s = engine.new_session("digital_arrest", lang)
    s.node = "otp_demand"
    res = engine.step(s, " ".join(s.otp))
    assert res["outcome"] == "lose"


@pytest.mark.parametrize("lang", LANGS)
def test_scripts_are_plain_not_theatrical(lang):
    """Guard against the filmy phrasing we removed."""
    banned = ["of course i know you", "do you think i would", "protected unit", "regret this"]
    text = " ".join(engine.load_lines("digital_arrest", lang)["lines"].values()).lower()
    for phrase in banned:
        assert phrase not in text


# ---------------------------------------------------------------- the caller answers questions in character

@pytest.mark.parametrize("lang", LANGS)
def test_every_interrupt_has_lines(lang):
    graph = engine.load_graph("digital_arrest")
    lines = engine.load_lines("digital_arrest", lang)
    for intent, spec in graph["interrupts"].items():
        assert f"{intent}.1" in lines["lines"] and f"{intent}.2" in lines["lines"], f"{lang}: missing {intent} lines"
        for t in spec["tactics"]:
            assert t in lines["debrief"]["tactics"]


@pytest.mark.parametrize("text,key", [
    ("where are you from", "ask_location.1"),
    ("which police station are you calling from", "ask_location.1"),
    ("who are you", "ask_identity.1"),
    ("can I see your ID", None),                      # not required to match; must simply not crash
    ("show me your id", "ask_identity.1"),
    ("can you prove it", "ask_proof.1"),
    ("do you know my name", "ask_info.1"),
    ("wait a minute", "stall.1"),
    ("i am scared", "scared.1"),
])
def test_questions_get_an_in_character_answer_and_the_node_stays(text, key):
    s = new()
    res = engine.step(s, text)
    assert not res["done"]
    if key:
        assert s.node == "greet", "node must not advance on a question"
        assert res["intent"] == key.split(".")[0]
        assert res["reply"]["text"] == engine.fill(
            engine.load_lines("digital_arrest", "en")["lines"][key], s.name, s.last4_spoken)


def test_repeated_question_uses_second_variant_then_loses_patience():
    s = new()
    lines = engine.load_lines("digital_arrest", "en")["lines"]
    assert engine.step(s, "who are you")["reply"]["text"] == lines["ask_identity.1"]
    assert engine.step(s, "who are you")["reply"]["text"] == lines["ask_identity.2"]
    assert engine.step(s, "where are you from")["reply"]["text"] == lines["ask_location.1"]
    engine.step(s, "prove it")          # 4th question in a row -> treated as a refusal -> first reassurance
    assert s.node == "reassure_doubt"


def test_a_normal_reply_resets_the_question_streak():
    s = new()
    for q in ["who are you", "where are you from"]:
        engine.step(s, q)
    engine.step(s, "yes")
    assert s.interrupts_in_row == 0 and s.node == "parcel"


def test_unrecognised_reply_is_reasked_once_then_script_moves_on():
    s = new()
    res = engine.step(s, "the weather is nice")
    assert s.node == "greet" and res["reply"]["text"].startswith("Sorry, I did not catch")
    engine.step(s, "the weather is nice")
    assert s.node == "parcel"


def test_questions_add_tactics_to_the_debrief():
    s = new()
    engine.step(s, "do you know my name")
    res = engine.step(s, "I am hanging up")
    ids = [t["id"] for t in res["debrief"]["tactics"]]
    assert "fear" in ids and "authority" in ids


def test_scared_user_gets_the_helper_line_and_it_is_in_the_debrief():
    s = new()
    res = engine.step(s, "i am scared")
    assert res["reply"]["text"].startswith("Please don't be scared. I am here to help you")
    out = engine.step(s, "bye")
    assert "false_help" in [t["id"] for t in out["debrief"]["tactics"]]


def test_otp_still_detected_inside_a_question():
    s = advance_to(new(), "otp_demand")
    res = engine.step(s, f"{' '.join(s.otp)} is that enough, who are you")
    assert res["outcome"] == "lose"


# ---------------------------------------------------------------- wording rules requested for the script

@pytest.mark.parametrize("lang", LANGS)
def test_no_trailing_lets_continue_prompts(lang):
    text = " ".join(engine.load_lines("digital_arrest", lang)["lines"].values())
    for phrase in ["Shall we continue", "let us continue", "Let us continue", "क्या हम आगे बढ़ें", "आगे बढ़ते हैं",
                   "আমরা কি এগোব", "এগোই"]:
        assert phrase not in text, phrase


def test_english_says_otp_not_code_and_names_the_city():
    lines = engine.load_lines("digital_arrest", "en")["lines"]
    import re
    for key, text in lines.items():
        assert not re.search(r"code", text, re.I), f"{key} still says 'code'"
    assert "New Delhi" in lines["greet"] and "Are you still there" not in " ".join(lines.values())
    assert "Can you hear me" in lines["generic.silence"]


def test_bengali_uses_kolkata_and_avoids_the_flagged_formal_words():
    d = engine.load_lines("digital_arrest", "bn")
    text = " ".join(d["lines"].values()) + " " + json_text(d["debrief"])
    assert "কলকাতা" in d["lines"]["greet"]
    flagged = ["পরোয়ানা", "সংখ্যা", "শাখা", "তথ্য", "ধাপ", "দুঃখিত", "সতর্কবার্তা", "স্থানীয়", "নথিভুক্ত", "বিমানবন্দর"]
    assert [w for w in flagged if w in text] == []
    assert "কোড" not in text, "say ওটিপি, not কোড"


def json_text(obj):
    import json
    return json.dumps(obj, ensure_ascii=False)


def test_hindi_says_otp_and_delhi():
    d = engine.load_lines("digital_arrest", "hi")
    assert "दिल्ली" in d["lines"]["greet"] and "ओटीपी" in d["lines"]["otp_demand"]
    assert "कोड" not in " ".join(d["lines"].values())


def test_resume_returns_to_the_step_that_was_interrupted_not_the_first_doubt():
    s = new()
    engine.step(s, "no")                 # first doubt at greet -> reassurance
    engine.step(s, "okay")               # -> parcel
    engine.step(s, "yes")                # -> reassure
    engine.step(s, "yes")                # -> isolate
    engine.step(s, "no")                 # second doubt, at isolate -> pressure
    assert s.node == "pushback"
    engine.step(s, "okay")
    assert s.node == "verify", "must continue after isolate, not replay the parcel story"


def test_doubting_and_giving_in_repeatedly_still_moves_forward():
    s = new()
    seen = []
    for reply in ["no", "okay"] + ["no", "okay"] * 6:
        res = engine.step(s, reply)
        seen.append(s.node)
        if res["done"]:
            break
    assert s.done or seen.count("parcel") <= 1, seen


def test_alternating_evasions_cannot_stall_forever():
    s = new()
    evasions = ["who are you", "the weather is nice", "", "where are you from", "what do you mean", "wait a minute"]
    for i in range(60):
        res = engine.step(s, evasions[i % len(evasions)])
        if res["done"]:
            break
    assert s.done, "the stall guard should have ended or advanced the call"
    assert i < 30, f"took {i} replies"


def test_nonsense_only_ends_as_a_win_and_bare_yes_never_leaks():
    s = new()
    for _ in range(40):
        res = engine.step(s, "the weather is nice")
        if res["done"]:
            break
    assert res["outcome"] == "win"
    s = new()
    for _ in range(40):
        res = engine.step(s, "yes")
        if res["done"]:
            break
    assert res["outcome"] == "win"
    # but the debrief still shows where they went along with it (red), not a clean sheet
    assert any(t["worked"] for t in res["debrief"]["tactics"])


def test_win_summary_depends_on_how_the_user_won():
    deb = engine.load_lines("digital_arrest", "en")["debrief"]["summary"]
    # said no and hung up: the normal win line
    s = new()
    assert engine.step(s, "no, I am hanging up")["debrief"]["summary"] == deb["win"]
    # refused to the end without hanging up: still the normal win line
    s = advance_to(new(), "otp_demand")
    for _ in range(6):
        res = engine.step(s, "no")
        if res["done"]:
            break
    assert res["debrief"]["summary"] == deb["win"]
    # only ever said yes, never gave digits: the gentler line
    s = new()
    for _ in range(40):
        res = engine.step(s, "yes")
        if res["done"]:
            break
    assert res["outcome"] == "win" and res["debrief"]["variant"] == "win_passive"
    assert res["debrief"]["summary"] == deb["win_passive"] and "right move" not in deb["win_passive"]
    # only nonsense: same
    s = new()
    for _ in range(40):
        res = engine.step(s, "the weather is nice")
        if res["done"]:
            break
    assert res["debrief"]["variant"] == "win_passive"
