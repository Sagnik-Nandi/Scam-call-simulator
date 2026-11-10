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
    for _ in range(4):
        engine.step(s, "yes")
        seen.append(s.node)
    assert seen == ["greet", "parcel", "isolate", "verify", "otp_demand"]


def test_full_compliance_leaks_otp():
    s = advance_to(new(), "otp_demand")
    res = engine.step(s, f"it is {s.otp}")
    assert res["outcome"] == "lose" and res["done"]
    assert res["debrief"]["outcome"] == "lose"
    assert any(t["worked"] for t in res["debrief"]["tactics"])


def test_no_pressure_lines_before_the_user_doubts():
    pressure = {"warn_station", "warn_case", "pushback", "final_early", "otp_pressure", "final_warning"}
    s = new()
    for _ in range(5):
        engine.step(s, "yes")
        assert s.node not in pressure


# ---------------------------------------------------------------- doubt -> pressure (never soft reassurance)

def test_first_doubt_gets_a_warning_and_then_resumes_where_it_left_off():
    s = advance_to(new(), "isolate")
    engine.step(s, "no I don't trust this")
    assert s.node == "warn_station"
    engine.step(s, "okay fine")
    assert s.node == "verify", "should continue with the step after the one that was interrupted"


def test_repeated_doubt_escalates_through_two_warnings_then_pressure_then_the_end():
    s = advance_to(new(), "isolate")
    path = []
    for _ in range(5):
        res = engine.step(s, "no")
        path.append(s.node)
        if res["done"]:
            break
    assert path == ["warn_station", "warn_case", "pushback", "final_early", "end_win"]
    assert s.outcome == "win"


def test_giving_in_after_pressure_resumes_the_script():
    s = advance_to(new(), "isolate")
    for _ in range(3):
        engine.step(s, "no")
    assert s.node == "pushback"
    engine.step(s, "okay okay")
    assert s.node == "verify"


def test_doubt_at_the_very_start_piles_on_the_parcel_story():
    s = new()
    engine.step(s, "no this is fake")
    assert s.node == "parcel", "a doubting user gets more of the story, not a threat"
    engine.step(s, "okay go on")
    assert s.node == "isolate"


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
    assert s.node == "greet" and res["reply"]["key"] == "greet.clarify"
    assert "put it simply" not in res["reply"]["text"]


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
    engine.step(s, "prove it")          # 4th question -> counted as a refusal; at the greeting that means the parcel story
    assert s.node == "parcel"


def test_a_normal_reply_in_between_still_advances_the_script():
    s = new()
    for q in ["who are you", "where are you from"]:
        engine.step(s, q)
    engine.step(s, "yes")
    assert s.node == "parcel"


def test_a_garbled_one_or_two_word_reply_is_reasked_once_then_the_script_moves_on():
    s = new()
    res = engine.step(s, "mm hm")
    assert s.node == "greet" and res["reply"]["text"] == "Sorry, I did not catch that."
    engine.step(s, "mm hm")
    assert s.node == "parcel"


@pytest.mark.parametrize("text", ["the weather is nice", "my son lives in pune and works there", "i was not at home yesterday"])
def test_a_real_sentence_without_a_rule_is_never_answered_with_did_not_catch(text):
    s = new()
    res = engine.step(s, text)
    assert res["reply"]["key"] != "generic.unknown", "the ultimate fallback must be rare"
    assert s.node == "parcel", "the caller carries on with the script"


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
    engine.step(s, "no")                 # doubt at greet -> the parcel story
    assert s.node == "parcel"
    engine.step(s, "yes")                # -> isolate
    engine.step(s, "yes")                # -> verify
    engine.step(s, "no")                 # doubt at verify -> first warning
    assert s.node == "warn_station"
    engine.step(s, "okay")
    assert s.node == "otp_demand", "must continue after verify, not replay earlier steps"


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


# ---------------------------------------------------------------- reassurance only for a scared user

SOFT_NODES = {"reassure", "reassure_doubt"}


@pytest.mark.parametrize("lang", LANGS)
def test_the_graph_has_no_scripted_reassurance_nodes(lang):
    graph = engine.load_graph("digital_arrest")
    lines = engine.load_lines("digital_arrest", lang)["lines"]
    assert not SOFT_NODES & set(graph["nodes"]) and not SOFT_NODES & set(lines)


@pytest.mark.parametrize("replies", [
    ["yes"] * 5,
    ["ok", "what should i do", "what do you want from me", "yes", "yes"],
    ["it cannot be mine, i did not order any package", "okay", "no", "okay", "yes", "yes"],
    ["no", "no", "no"],
    ["who are you", "where are you from", "prove it", "yes", "what do you mean", "yes"],
])
def test_no_reassuring_reply_unless_the_user_said_they_are_scared(replies):
    s = new()
    reassuring = {"scared.1", "scared.2"}
    for r in replies:
        res = engine.step(s, r)
        if res["reply"]:
            assert res["reply"]["key"] not in reassuring
        if res["done"]:
            break


def test_a_scared_user_still_gets_the_reassurance_and_the_node_stays():
    s = advance_to(new(), "isolate")
    res = engine.step(s, "i am scared")
    assert res["reply"]["key"] == "scared.1" and s.node == "isolate"
    assert engine.step(s, "i am scared")["reply"]["key"] == "scared.2"


def test_denying_the_parcel_gets_pressure_not_comfort():
    s = advance_to(new(), "parcel")
    res = engine.step(s, "it cannot be mine, i did not order any package")
    assert res["intent"] == "refuse" and s.node == "warn_station"
    assert engine.step(s, "what do you want from me")["intent"] == "comply"
    assert s.node == "isolate", "after giving in, resume the script at the step after the interrupted one"


# ---------------------------------------------------------------- proceed, don't replay

def test_after_a_warning_a_no_match_proceeds_like_agreeing_would_have():
    s = advance_to(new(), "isolate")
    engine.step(s, "no")                                  # -> warn_station (interrupts isolate)
    engine.step(s, "blah blah")                           # first unclear reply: asked again, same node
    assert s.node == "warn_station"
    engine.step(s, "blah blah")                           # second unclear reply -> proceeds to what follows isolate
    assert s.node == "verify"


def test_final_warning_early_with_no_match_proceeds_instead_of_ending_the_call():
    s = advance_to(new(), "isolate")
    for _ in range(4):                                    # warn_station, warn_case, pushback, final_early
        engine.step(s, "no")
    assert s.node == "final_early"
    engine.step(s, "blah blah")
    res = engine.step(s, "blah blah")
    assert not res["done"] and s.node == "verify"


def test_isolate_ends_with_a_short_assurance():
    assert engine.load_lines("digital_arrest", "en")["lines"]["isolate"].endswith("There is no need to worry.")


# ---------------------------------------------------------------- caps for the whole call: questions 3, stall 2, scared 2

def test_question_cap_counts_the_whole_call_not_a_streak():
    s = new()
    for q in ["who are you", "where are you from", "prove it"]:
        res = engine.step(s, q)
        assert res["intent"].startswith("ask_")
        engine.step(s, "yes")                    # a normal reply in between must NOT reset the allowance
    assert s.node == "verify"
    res = engine.step(s, "how did you get my number")
    assert res["intent"] == "refuse"      # over the cap: counted as a refusal
    assert s.node == "warn_station"


def test_stall_is_capped_at_two_and_does_not_use_up_the_question_allowance():
    s = advance_to(new(), "parcel")
    assert engine.step(s, "wait a minute")["reply"]["key"] == "stall.1"
    assert engine.step(s, "hold on")["reply"]["key"] == "stall.2"
    for q in ["who are you", "where are you from", "prove it"]:      # all three questions still answered
        assert engine.step(s, q)["reply"]["key"].startswith("ask_") and s.node == "parcel"
    engine.step(s, "give me a second")                               # third stall: over the cap
    assert s.node == "warn_station"


def test_scared_is_capped_at_two_and_is_not_a_question():
    s = advance_to(new(), "parcel")
    assert engine.step(s, "i am scared")["reply"]["key"] == "scared.1"
    assert engine.step(s, "i am scared")["reply"]["key"] == "scared.2"
    for q in ["who are you", "where are you from", "prove it"]:
        assert engine.step(s, q)["reply"]["key"].startswith("ask_")
    engine.step(s, "oh god i am so scared")
    assert s.node == "warn_station"


def test_over_the_cap_at_the_code_stage_escalates_the_code_ladder_instead_of_pushback():
    s = advance_to(new(), "otp_demand")
    for q in ["who are you", "where are you from", "prove it"]:
        engine.step(s, q)
    engine.step(s, "how did you get my number")
    assert s.node == "otp_soft"


def test_a_warning_after_going_over_the_cap_still_proceeds_when_the_user_gives_in():
    s = advance_to(new(), "isolate")
    for q in ["who are you", "where are you from", "prove it", "how did you get my number"]:
        engine.step(s, q)
    assert s.node == "warn_station"
    engine.step(s, "okay")
    assert s.node == "verify"

# ---------------------------------------------------------------- refusal paths: more story, then warnings, then pressure

def test_each_warning_is_used_once_per_call_so_later_doubts_keep_escalating():
    s = advance_to(new(), "parcel")
    engine.step(s, "no")
    assert s.node == "warn_station"
    engine.step(s, "okay")
    assert s.node == "isolate"
    engine.step(s, "no")                              # the station warning is used up -> the case warning
    assert s.node == "warn_case"
    engine.step(s, "okay")
    assert s.node == "verify"
    engine.step(s, "no")                              # both warnings used -> straight to pushback
    assert s.node == "pushback"


@pytest.mark.parametrize("step_node", ["parcel", "isolate", "verify"])
def test_a_refusal_after_the_greeting_gets_the_station_warning_first(step_node):
    s = advance_to(new(), step_node)
    res = engine.step(s, "no")
    assert s.node == "warn_station" and res["reply"]["key"] == "warn_station"


@pytest.mark.parametrize("lang", LANGS)
def test_the_parcel_story_does_not_drag_in_the_bank_account(lang):
    text = engine.load_lines("digital_arrest", lang)["lines"]["parcel"].lower()
    for word in ("bank", "\u092c\u0948\u0902\u0915", "\u09ac\u09cd\u09af\u09be\u0982\u0995"):
        assert word not in text


# ---------------------------------------------------------------- clarify recaps, merged silence, shorter fallback

@pytest.mark.parametrize("node", ["greet", "parcel", "isolate", "verify"])
def test_confusion_gets_a_recap_written_for_that_step(node):
    s = advance_to(new(), node)
    res = engine.step(s, "what do you mean")
    assert res["reply"]["key"] == f"{node}.clarify" and s.node == node


def test_the_recaps_build_on_what_has_been_said_so_far():
    lines = engine.load_lines("digital_arrest", "en")["lines"]
    assert "Inspector Verma" in lines["greet.clarify"]
    assert "passports" in lines["parcel.clarify"]
    assert "confidential" in lines["isolate.clarify"]
    assert "OTP" in lines["verify.clarify"] and "parcel" in lines["verify.clarify"]


def test_confusion_during_a_warning_recaps_the_step_that_was_interrupted():
    s = advance_to(new(), "isolate")
    engine.step(s, "no")
    assert s.node == "warn_station"
    res = engine.step(s, "what do you mean")
    assert res["reply"]["key"] == "isolate.clarify"


def test_confusion_at_the_code_stage_still_uses_the_code_reminder():
    s = advance_to(new(), "otp_demand")
    assert engine.step(s, "what do you mean")["reply"]["key"] == "otp.clarify"


def test_silence_has_its_own_line_and_two_in_a_row_ends_the_call():
    s = advance_to(new(), "parcel")
    res = engine.step(s, "")
    assert res["reply"]["key"] == "generic.silence" and not res["done"]
    res = engine.step(s, "")
    assert res["done"] and res["outcome"] == "idle"


def test_silence_does_not_count_as_a_stall():
    s = advance_to(new(), "parcel")
    engine.step(s, "")
    engine.step(s, "mm hm")
    assert s.group_counts.get("stall", 0) == 0


@pytest.mark.parametrize("greeting", ["hello", "hi", "hello sir"])
def test_a_plain_greeting_is_an_answer_not_unclear(greeting):
    s = new()
    res = engine.step(s, greeting)
    assert res["intent"] == "comply" and s.node == "parcel"


def test_pushback_no_longer_opens_with_listen_carefully_and_the_parcel_does():
    lines = {c: engine.load_lines("digital_arrest", c)["lines"] for c in LANGS}
    assert lines["en"]["parcel"].startswith("Please listen carefully.")
    assert "isten carefully" not in lines["en"]["pushback"]
    for c in ("hi", "bn"):                  # the moved sentence opens the parcel and is gone from the pushback
        opener = lines[c]["parcel"].split("\u0964")[0] + "\u0964"
        assert opener not in lines[c]["pushback"] and len(opener) < 40


@pytest.mark.parametrize("lang", LANGS)
def test_the_debrief_does_not_claim_the_caller_mentioned_a_bank_account(lang):
    d = engine.load_lines("digital_arrest", lang)["debrief"]
    text = (d["tactics"]["fear"]["what"] + " " + d["tactics"]["fear"]["instead"]).lower()
    for word in ("bank account", "\u092c\u0948\u0902\u0915 \u0916\u093e\u0924\u093e", "\u09ac\u09cd\u09af\u09be\u0982\u0995 \u0985\u09cd\u09af\u09be\u0995\u09be\u0989\u09a8\u09cd\u099f"):
        assert word not in text


def test_the_debrief_carries_the_helpline_number_for_every_language():
    for lang in LANGS:
        s = engine.new_session("digital_arrest", lang)
        res = engine.step(s, "i am hanging up")
        assert res["debrief"]["helpline"] == "1930"
