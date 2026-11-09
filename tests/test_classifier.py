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
