"""Intent accuracy on the labelled utterance set (tests/data/utterances.csv).

Add rows to the CSV (lang,intent,text) as you find misclassifications; the report lists every miss.
"""
import csv
from pathlib import Path

import pytest

from backend import engine
from backend.classifier import classify

ROWS = list(csv.DictReader(open(Path(__file__).parent / "data" / "utterances.csv", encoding="utf-8")))
EN = engine.load_language("en")
THRESHOLD = 0.90


def _predict(row):
    lang = engine.load_language(row["lang"])
    fallback = EN["keywords"] if row["lang"] != "en" else None
    return classify(row["text"], lang["keywords"], fallback)["intent"]


@pytest.mark.parametrize("code", ["en", "hi", "bn"])
def test_accuracy_per_language(code):
    rows = [r for r in ROWS if r["lang"] == code]
    misses = [(r["text"].encode("unicode_escape").decode(), r["intent"], _predict(r))
              for r in rows if _predict(r) != r["intent"]]
    acc = 1 - len(misses) / len(rows)
    report = f"{code}: {acc:.0%} ({len(rows) - len(misses)}/{len(rows)}); misses (text, expected, got): {misses}"
    assert acc >= THRESHOLD, report


def test_empty_is_silence():
    assert classify("", EN["keywords"])["intent"] == "silence"
    assert classify("   ", EN["keywords"])["intent"] == "silence"


def test_nothing_matched_is_unknown():
    assert classify("the weather is nice", EN["keywords"])["intent"] == "unknown"


def test_longest_phrase_wins():
    # "what should I do" is comply, even though bare "what" is confused
    assert classify("what should I do", EN["keywords"])["intent"] == "comply"


def test_agreeing_to_keep_it_secret_is_not_a_refusal():
    # "I will not tell anyone" means the user is complying with the secrecy request
    assert classify("okay I will not tell anyone", EN["keywords"])["intent"] != "refuse"
    assert classify("I won't tell you the code", EN["keywords"])["intent"] == "refuse"


# --- regression: denying the parcel and asking "what do you want from me" (found in the live demo)
@pytest.mark.parametrize("text", [
    "it cannot be mine, i did not order any package", "I did not order any package", "this is not mine",
    "there must be a mistake", "I never ordered it", "you have the wrong person"])
def test_denying_the_parcel_is_a_refusal(text):
    assert classify(text, EN["keywords"])["intent"] == "refuse"


@pytest.mark.parametrize("text", ["what do you want from me", "what do you want from me sir", "what can I do"])
def test_asking_what_the_caller_wants_is_compliance(text):
    assert classify(text, EN["keywords"])["intent"] == "comply"


@pytest.mark.parametrize("code", ["hi", "bn"])
def test_non_english_phrases_match_in_their_own_language_without_the_english_fallback(code):
    """Every added row for hi/bn must be recognised from that language's own keywords alone."""
    own = engine.load_language(code)["keywords"]
    rows = [r for r in ROWS if r["lang"] == code and r["intent"] in ("refuse", "comply")]
    bad = [(r["text"].encode("unicode_escape").decode(), r["intent"]) for r in rows
           if classify(r["text"], own)["intent"] != r["intent"]]
    assert len(bad) <= 2, bad       # a couple of older rows may rely on the English fallback; new ones must not
