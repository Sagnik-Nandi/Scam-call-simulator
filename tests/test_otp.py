import pytest

from backend import engine
from backend.otp import check_leak, digit_runs

OTP = "472910"
WORDS = {**engine.load_language("en")["digit_words"], **engine.load_language("hi")["digit_words"],
         **engine.load_language("bn")["digit_words"]}


def level(text):
    return check_leak(text, OTP, WORDS)["level"]


@pytest.mark.parametrize("text", [
    "472910",
    "the code is 472910",
    "4 7 2 9 1 0",
    "4-7-2-9-1-0",
    "47 29 10",
    "four seven two nine one zero",
    "four seven two, nine one zero",
    "4 7 2 nine 1 zero",
    "४७२९१०",                                  # Devanagari digits
    "৪৭২৯১০",                                  # Bengali digits
    "चार सात दो नौ एक शून्य",  # char saat do nau ek shunya in Devanagari
    "char saat do nau ek shunya",
    "ok sir it is 472910 please",
])
def test_full_leak_detected(text):
    assert level(text) == "full"


def test_partial_leak():
    assert level("4 7 2 9") == "partial"


def test_other_number_is_an_attempt():
    assert level("123456") == "attempt"


@pytest.mark.parametrize("text", [
    "I do not want to share anything",
    "give me one minute",
    "ek minute ruko",
    "my age is 65",
    "call 1930",
    "",
])
def test_no_false_positive(text):
    assert level(text) == "none"


def test_phone_number_is_not_an_otp_attempt():
    # ten digits: neither a match nor in the 4-8 digit "attempt" window
    assert level("9876543210") == "none"


def test_word_runs_need_three_tokens():
    assert digit_runs("do teen", WORDS) == []
    assert digit_runs("do teen char", WORDS) == ["234"]


@pytest.mark.parametrize("otp", ["193456", "456930", "219301", "719300"])
def test_helpline_number_never_matches_an_otp(otp):
    # "1930" shares 3 digits with these OTPs; saying the helpline must not count as a leak
    assert check_leak("I will call 1930", otp, WORDS)["level"] == "none"
