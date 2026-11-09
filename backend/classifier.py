"""Rule-based intent classifier: comply / refuse / confused / hangup / silence, plus the question
intents the caller answers in character (ask_identity, ask_location, ask_proof, ask_info, stall, scared).

Each language file supplies keyword phrases per intent. The longest matched phrases win
(by token count), so "what should I do" (comply) beats a bare "what" (confused) and
"samajh nahi" (confused) beats a bare "nahi" (refuse). Ties go to the safer reading:
hangup > refuse > questions > confused > comply.
"""
import re
import unicodedata

INTENTS = ("hangup", "refuse", "ask_identity", "ask_location", "ask_proof", "ask_info",
           "stall", "scared", "confused", "comply")  # tie-break order: safest reading first
_STRIP = re.compile(r"[,.;:!?()\[\]\"'‘’“”\-–—।|/]+")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    text = _STRIP.sub(" ", text)
    return " " + " ".join(text.split()) + " "


def _phrase_score(padded: str, phrase: str) -> int:
    p = normalize(phrase)
    return len(p.split()) if p in padded else 0


def classify(text: str, keywords: dict, fallback_keywords: dict = None) -> dict:
    """Return {"intent": ..., "scores": {...}}. Empty text is silence."""
    if not text or not text.strip():
        return {"intent": "silence", "scores": {}}
    padded = normalize(text)
    scores = {i: 0 for i in INTENTS}
    for source in (keywords, fallback_keywords or {}):
        for intent in INTENTS:
            for phrase in source.get(intent, []):
                scores[intent] += _phrase_score(padded, phrase)
    best = max(scores.values())
    if best == 0:
        return {"intent": "unknown", "scores": scores}
    for intent in INTENTS:  # priority order resolves ties
        if scores[intent] == best:
            return {"intent": intent, "scores": scores}
    return {"intent": "unknown", "scores": scores}
