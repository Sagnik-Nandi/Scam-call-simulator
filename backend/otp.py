"""OTP leak detection over an STT transcript.

Prisma returns spoken digits in different shapes depending on model and mode:
Latin digits ("472910"), native digits, or spoken words ("four seven two nine one zero").
We normalise all of them to one digit string and compare with the session's synthetic OTP.
"""
import re
import unicodedata

_SPLIT = re.compile(r"[\s,.;:!?()\[\]\"'‘’“”\-–—।|/]+")

# A run made only of spoken words must be at least this long to count as digits.
# This keeps "do not", "one thing", "ek minute" from being read as numbers.
MIN_WORD_RUN = 3

# Numbers a user may legitimately say while resisting (the cybercrime helpline). Never an OTP attempt.
EXEMPT_NUMBERS = {"1930"}


def _to_ascii_digits(token: str):
    """Return ASCII digits if the token is entirely numeric (any script), else None."""
    if not token:
        return None
    out = []
    for ch in token:
        if ch.isdigit():
            try:
                out.append(str(unicodedata.digit(ch)))
            except ValueError:
                return None
        else:
            return None
    return "".join(out)


def digit_runs(text: str, digit_words: dict) -> list:
    """Return the list of digit strings found in `text` (consecutive numeric tokens form one run)."""
    tokens = [t for t in _SPLIT.split(unicodedata.normalize("NFKC", text).lower()) if t]
    runs, current, kinds = [], [], []

    def flush():
        if current:
            if "num" in kinds or len(current) >= MIN_WORD_RUN:
                runs.append("".join(current))
        current.clear()
        kinds.clear()

    for tok in tokens:
        num = _to_ascii_digits(tok)
        if num is not None:
            current.append(num)
            kinds.append("num")
        elif tok in digit_words:
            current.append(digit_words[tok])
            kinds.append("word")
        else:
            flush()
    flush()
    return runs


def _longest_common_substring(a: str, b: str) -> int:
    best = 0
    for i in range(len(a)):
        for j in range(len(b)):
            k = 0
            while i + k < len(a) and j + k < len(b) and a[i + k] == b[j + k]:
                k += 1
            best = max(best, k)
    return best


def check_leak(text: str, otp: str, digit_words: dict) -> dict:
    """Classify how much of the OTP the user said.

    level: "full"    the whole OTP appears
           "partial" a stretch of >= 3 correct digits appears
           "attempt" the user read out some other 4-8 digit number (they tried to comply)
           "none"
    """
    runs = [r for r in digit_runs(text, digit_words) if r not in EXEMPT_NUMBERS]
    if not runs:
        return {"level": "none", "digits": ""}
    joined = "".join(runs)
    if any(otp in r for r in runs) or otp in joined:
        return {"level": "full", "digits": joined}
    if max(_longest_common_substring(otp, r) for r in runs + [joined]) >= 3:
        return {"level": "partial", "digits": joined}
    if any(4 <= len(r) <= 8 for r in runs):
        return {"level": "attempt", "digits": joined}
    return {"level": "none", "digits": joined}
