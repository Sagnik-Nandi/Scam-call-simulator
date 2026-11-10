"""Scenario engine: loads the call graph and language data, advances a session one turn at a time.

No model writes any scammer dialogue. Every line the "caller" says is a fixed, pre-written,
pre-rendered clip chosen by the graph's branch rules.
"""
import json
import secrets
import unicodedata
import time
import uuid
from dataclasses import dataclass, field

from . import config
from .classifier import classify
from .otp import check_leak

LEAK_LEVELS = ("full", "partial")


# ----------------------------------------------------------------- loading

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def list_languages() -> dict:
    return {p.stem: load_json(p) for p in sorted(config.LANG_DIR.glob("*.json"))}


def load_language(code: str) -> dict:
    return load_json(config.LANG_DIR / f"{code}.json")


def load_graph(scenario_id: str) -> dict:
    return load_json(config.SCENARIO_DIR / scenario_id / "graph.json")


def load_lines(scenario_id: str, lang: str) -> dict:
    return load_json(config.SCENARIO_DIR / scenario_id / "lines" / f"{lang}.json")


def sanitize_nickname(raw) -> str:
    """Keep a short practice name: letters (any script) and spaces only, max 20 chars. Else empty."""
    raw = " ".join(str(raw or "").split())[:20]
    if not raw or not all(ch.isalpha() or ch in " .'" or unicodedata.category(ch).startswith("M") for ch in raw):
        return ""
    return raw.strip(" .'")


def fill(text: str, name: str, last4_spoken: str) -> str:
    return text.replace("{name}", name).replace("{last4}", last4_spoken)


def templated_keys(lines: dict) -> list:
    """Line keys whose text mentions the user's practice identity ({name} / {last4})."""
    return [k for k, v in lines["lines"].items() if "{" in v]


def audio_keys(lines: dict, persona: dict = None) -> dict:
    """Every phrase that needs a pre-rendered clip: {key: text}. Shared with scripts/prerender.py.
    Templated lines are filled with the default persona, so the default experience needs no live TTS."""
    out = dict(lines["lines"])
    if persona:
        out = {k: fill(v, persona["name"], persona["last4_spoken"]) for k, v in out.items()}
    deb = lines["debrief"]
    for k, text in deb["summary"].items():
        out[f"debrief.{k}"] = text
    for tid, t in deb["tactics"].items():
        out[f"debrief.tactic.{tid}"] = f"{t['name']}. {t['instead']}"
    out["debrief.help"] = deb["help"]
    return out


# ----------------------------------------------------------------- session

@dataclass
class Session:
    id: str
    scenario_id: str
    lang: str
    otp: str
    node: str
    created: float = field(default_factory=time.time)
    visits: dict = field(default_factory=dict)
    delivered: list = field(default_factory=list)   # node ids the caller has "spoken", in order
    log: list = field(default_factory=list)
    silences: int = 0
    turns: int = 0
    outcome: str = ""          # "", "win", "lose", "idle"
    hung_up: bool = False
    name: str = ""             # practice identity the caller uses (fictional by default)
    last4_spoken: str = ""
    last4: str = ""
    doubt_from: str = ""       # node where the user first doubted; the script resumes after it
    clarify_counts: dict = field(default_factory=dict)
    stalls: int = 0            # replies since the last step change that did not move the call forward
    interrupt_counts: dict = field(default_factory=dict)   # per question type: which variant line to play next
    group_counts: dict = field(default_factory=dict)       # per cap group, whole call: question / stall / scared
    unknown_in_row: int = 0
    extra_tactics: list = field(default_factory=list)   # tactics used by in-character answers to the user's questions
    custom: bool = False       # user typed their own practice name -> templated lines are rendered live

    @property
    def done(self) -> bool:
        return bool(self.outcome)


def new_session(scenario_id: str, lang: str, nickname: str = "") -> Session:
    graph = load_graph(scenario_id)
    persona = load_language(lang)["persona"]
    nick = sanitize_nickname(nickname)
    otp = "".join(str(secrets.randbelow(10)) for _ in range(6))   # synthetic, never a real code
    s = Session(id=uuid.uuid4().hex, scenario_id=scenario_id, lang=lang, otp=otp, node=graph["start"],
                name=nick or persona["name"], last4=persona["last4"], last4_spoken=persona["last4_spoken"],
                custom=bool(nick) and nick != persona["name"])
    s.delivered.append(graph["start"])
    s.visits[graph["start"]] = 1
    return s


def _reply(graph, lines, key, node_id, s):
    return {"key": key, "text": fill(lines["lines"].get(key, ""), s.name, s.last4_spoken), "node": node_id,
            "show_otp": bool(graph["nodes"].get(node_id, {}).get("show_otp"))}


def first_reply(s: Session) -> dict:
    graph, lines = load_graph(s.scenario_id), load_lines(s.scenario_id, s.lang)
    return _reply(graph, lines, s.node, s.node, s)


# ----------------------------------------------------------------- one turn

def step(s: Session, transcript: str) -> dict:
    """Advance the session with the user's transcribed reply ("" means they said nothing)."""
    graph, lines = load_graph(s.scenario_id), load_lines(s.scenario_id, s.lang)
    lang = load_language(s.lang)
    en = load_language("en")
    nodes = graph["nodes"]
    node = nodes[s.node]
    s.turns += 1

    words = {**en.get("digit_words", {}), **lang.get("digit_words", {})}
    leak = check_leak(transcript or "", s.otp, words)
    verdict = classify(transcript, lang["keywords"], en["keywords"] if s.lang != "en" else None)
    intent = verdict["intent"]
    if leak["level"] in LEAK_LEVELS or (leak["level"] == "attempt" and node.get("show_otp")):
        intent = "leak"

    entry = {"turn": s.turns, "node": s.node, "tactics": node.get("tactics", []),
             "transcript": transcript or "", "intent": intent, "leak": leak["level"]}
    s.log.append(entry)

    # --- loop guard: questions, nonsense, silence and "what?" can only stall so long, then it counts as a refusal
    stalling = set(graph.get("interrupts", {})) | {"silence", "unknown", "confused"}
    if intent in stalling:
        if s.stalls >= graph.get("stall_limit", 6):
            intent = "refuse"
            s.silences = 0
        else:
            s.stalls += 1

    # --- the user ended the call
    if intent == "hangup":
        s.hung_up = True
        s.outcome = "win"
        return _finish(s, graph, lines, reply=None, intent=intent, leak=leak)

    # --- the user said nothing
    if intent == "silence":
        s.silences += 1
        if s.silences >= graph.get("silence_limit", 2):
            s.outcome = "idle"
            return _finish(s, graph, lines, reply=None, intent=intent, leak=leak)
        return _result(s, intent, leak, _reply(graph, lines, "generic.silence", s.node, s))
    s.silences = 0

    # --- the user asked a question (who are you, where from, prove it, ...), stalled or said they are scared:
    #     answer in character, same node. Each group has a cap for the WHOLE call (graph "interrupt_limits");
    #     once it is used up, the next one counts as a refusal and the caller loses patience.
    interrupts = graph.get("interrupts", {})
    if intent in interrupts:
        s.unknown_in_row = 0
        group = interrupts[intent].get("group", intent)
        s.group_counts[group] = s.group_counts.get(group, 0) + 1
        if s.group_counts[group] <= graph.get("interrupt_limits", {}).get(group, 99):
            n = s.interrupt_counts[intent] = s.interrupt_counts.get(intent, 0) + 1
            variants = [k for k in lines["lines"] if k.startswith(intent + ".")]
            key = f"{intent}.{(n - 1) % len(variants) + 1}"
            for tac in interrupts[intent].get("tactics", []):
                if tac not in s.extra_tactics:
                    s.extra_tactics.append(tac)
            return _result(s, intent, leak, _reply(graph, lines, key, s.node, s))
        intent = "refuse"                  # over the cap: follows this step's refusal branch (pushback in the early script)

    # --- nothing recognised. A real sentence we have no rule for is not "unclear": the caller just carries on with
    #     the script. Only a very short or garbled reply is asked again, once ("Sorry, I did not catch that").
    if intent == "unknown":
        words = len((transcript or "").split())
        if words < graph.get("unknown_min_words", 3) and s.unknown_in_row < graph.get("unknown_retries", 1):
            s.unknown_in_row += 1
            return _result(s, intent, leak, _reply(graph, lines, "generic.unknown", s.node, s))
    s.unknown_in_row = 0

    target = node["on"].get(intent, node["on"].get("default"))

    # --- ask-again branch: same node, explanatory variant line (a few times, then treat as a refusal)
    if target == "@clarify":
        n = s.clarify_counts[s.node] = s.clarify_counts.get(s.node, 0) + 1
        if n <= graph.get("clarify_limit", 2):
            if f"{s.node}.clarify" in lines["lines"]:
                key = f"{s.node}.clarify"
            elif node.get("show_otp") and "otp.clarify" in lines["lines"]:
                key = "otp.clarify"
            elif node.get("remember") and f"{s.doubt_from}.clarify" in lines["lines"]:
                key = f"{s.doubt_from}.clarify"      # a warning/pressure step: recap the step that was interrupted
            else:
                key = "generic.clarify"
            return _result(s, intent, leak, _reply(graph, lines, key, s.node, s))
        target = node["on"]["refuse"]

    # --- go back to the step the user interrupted with a doubt
    if target == "@resume":
        # Proceed, don't replay: take the branch the interrupted step would have taken for this same kind of
        # reply (agree -> its "comply" target, anything else -> its "default" target).
        prev_on = nodes[s.doubt_from or graph["start"]]["on"]
        target = prev_on.get("comply" if intent == "comply" else "default")
        if not target or target.startswith("@"):
            target = prev_on["comply"]

    # Follow on_exhausted redirects until we land on a node that still has visits left.
    while True:
        s.visits[target] = s.visits.get(target, 0) + 1
        tnode = nodes[target]
        if s.visits[target] <= tnode.get("max_visits", 99):
            break
        target = tnode["on_exhausted"]

    s.stalls = 0
    if tnode.get("remember") and not node.get("remember"):
        s.doubt_from = s.node          # remember the normal step the doubt interrupted (not another doubt/pressure step)
    s.node = target
    s.delivered.append(target)
    reply = _reply(graph, lines, target, target, s)
    if "terminal" in tnode:
        s.outcome = tnode["terminal"]
        return _finish(s, graph, lines, reply=reply, intent=intent, leak=leak)
    return _result(s, intent, leak, reply)


def _result(s, intent, leak, reply, debrief_data=None):
    return {"intent": intent, "leak": leak["level"], "reply": reply,
            "done": s.done, "outcome": s.outcome, "debrief": debrief_data}


def _finish(s, graph, lines, reply, intent, leak):
    return _result(s, intent, leak, reply, debrief_data=build_debrief(s, graph, lines))


# ----------------------------------------------------------------- debrief

def build_debrief(s: Session, graph: dict, lines: dict) -> dict:
    deb = lines["debrief"]
    nodes = graph["nodes"]

    heard, worked = [], set()
    for node_id in s.delivered:
        for t in nodes[node_id].get("tactics", []):
            if t not in heard:
                heard.append(t)
    for tac in s.extra_tactics:
        if tac not in heard:
            heard.append(tac)
    for e in s.log:
        if e["intent"] in ("comply", "leak"):
            worked.update(e["tactics"])

    tactics = [{"id": t, "name": deb["tactics"][t]["name"], "what": deb["tactics"][t]["what"],
                "instead": deb["tactics"][t]["instead"], "worked": t in worked} for t in heard]
    tactics.sort(key=lambda t: not t["worked"])   # the ones that fooled the user come first

    # A "win" where the user never said no and never hung up (only agreed, or only mumbled) gets a gentler,
    # more accurate summary than "ending the call was the right move".
    variant = s.outcome
    if s.outcome == "win" and not s.hung_up and not any(e["intent"] in ("refuse", "hangup") for e in s.log):
        variant = "win_passive"
    audio = [f"debrief.{variant}"] + [f"debrief.tactic.{t['id']}" for t in tactics[:3]] + ["debrief.help"]
    return {"outcome": s.outcome, "variant": variant, "hung_up": s.hung_up, "summary": deb["summary"][variant],
            "tactics": tactics, "facts": deb["facts"], "help": deb["help"], "helpline": deb.get("helpline", ""),
            "disclaimer": deb["disclaimer"], "audio_keys": audio,
            "labels": {"worked": deb["worked"], "resisted": deb["resisted"]}}


def force_end(s: Session, outcome: str = "idle") -> dict:
    """End the call from the outside (reply limit reached) and return the usual debrief."""
    s.outcome = s.outcome or outcome
    graph, lines = load_graph(s.scenario_id), load_lines(s.scenario_id, s.lang)
    return build_debrief(s, graph, lines)
