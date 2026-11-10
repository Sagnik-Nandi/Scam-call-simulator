"""FastAPI app: session API + static frontend + pre-rendered audio.

Run:  uvicorn backend.app:app --reload
"""
import asyncio
import shutil
import time
from typing import Optional

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import audio, config, engine, gnani

app = FastAPI(title="Scam Call Simulator")

SESSIONS: dict = {}
_session_starts: list = []     # timestamps, for the global hourly cap


# ----------------------------------------------------------------- helpers

def _prune():
    now = time.time()
    for sid in [k for k, s in SESSIONS.items() if now - s.created > config.SESSION_TTL_SECONDS]:
        SESSIONS.pop(sid, None)
        shutil.rmtree(config.AUDIO_DIR / "_live" / sid, ignore_errors=True)
    _session_starts[:] = [t for t in _session_starts if now - t < 3600]


def _get(sid: str) -> engine.Session:
    s = SESSIONS.get(sid)
    if not s:
        raise HTTPException(404, "session not found or expired")
    return s


def _audio_url(s: engine.Session, key: str) -> Optional[str]:
    live = config.AUDIO_DIR / "_live" / s.id / f"{key}.wav"
    if s.custom and live.exists():
        return f"/audio/_live/{s.id}/{key}.wav"
    path = config.AUDIO_DIR / s.scenario_id / s.lang / f"{key}.wav"
    return f"/audio/{s.scenario_id}/{s.lang}/{key}.wav" if path.exists() else None


def _public_reply(s: engine.Session, reply: Optional[dict]) -> Optional[dict]:
    if reply is None:
        return None
    out = {"text": reply["text"], "audio_url": _audio_url(s, reply["key"]), "show_otp": reply["show_otp"]}
    if reply["show_otp"]:
        out["otp"] = s.otp
    return out


def _public_debrief(s: engine.Session, deb: Optional[dict]) -> Optional[dict]:
    if deb is None:
        return None
    deb = dict(deb)
    deb["audio"] = [u for u in (_audio_url(s, k) for k in deb.pop("audio_keys")) if u]
    return deb


# ----------------------------------------------------------------- API

@app.get("/api/config")
def get_config():
    langs = engine.list_languages()
    scenario = "digital_arrest"
    return {
        "languages": [{"code": c, "name": l["name"], "review_status": l.get("review_status", ""), "ui": l["ui"],
                       "persona": l["persona"],
                       # the tricks scam callers use, in this language (names only; the debrief has the detail)
                       "tricks": [{"id": tid, "name": tx["name"]}
                                  for tid, tx in engine.load_lines(scenario, c)["debrief"]["tactics"].items()]}
                      for c, l in langs.items()],
        "scenarios": [{"id": scenario, "title": "Digital arrest call"}],
        "helpline": engine.load_lines(scenario, "en")["debrief"].get("helpline", ""),
        "invite_required": bool(config.INVITE_CODE),
        "allow_text": config.ALLOW_TEXT_TURN,
    }


async def _render_custom_name(s: engine.Session) -> bool:
    """Render the few lines that mention the user's practice name. False = fall back to the default persona."""
    lang = engine.load_language(s.lang)
    lines = engine.load_lines(s.scenario_id, s.lang)
    keys = engine.templated_keys(lines)
    out_dir = config.AUDIO_DIR / "_live" / s.id
    out_dir.mkdir(parents=True, exist_ok=True)

    async def one(key):
        text = engine.fill(lines["lines"][key], s.name, s.last4_spoken)
        (out_dir / f"{key}.wav").write_bytes(
            await gnani.tts(text, lang["voice"], lang["tts"], lang["tts_model"]))

    try:
        async def all_lines():
            for k in keys:              # one at a time: the API allows a single active request
                await one(k)
        await asyncio.wait_for(all_lines(), timeout=25)
        return True
    except Exception:
        shutil.rmtree(out_dir, ignore_errors=True)
        return False


@app.post("/api/session")
async def start_session(payload: dict, x_invite_code: str = Header(default="")):
    if config.INVITE_CODE and x_invite_code != config.INVITE_CODE:
        raise HTTPException(403, "invite code required")
    _prune()
    if len(_session_starts) >= config.MAX_SESSIONS_PER_HOUR:
        raise HTTPException(429, "too many calls right now, try again later")
    lang = payload.get("language", "en")
    scenario = payload.get("scenario", "digital_arrest")
    if lang not in engine.list_languages():
        raise HTTPException(400, "unknown language")
    s = engine.new_session(scenario, lang, payload.get("nickname", ""))
    if s.custom and not await _render_custom_name(s):
        persona = engine.load_language(lang)["persona"]      # could not render: use the default fictional name
        s.name, s.custom = persona["name"], False
    SESSIONS[s.id] = s
    _session_starts.append(time.time())
    return {"session_id": s.id, "persona": {"name": s.name, "last4": s.last4},
            "reply": _public_reply(s, engine.first_reply(s))}


@app.post("/api/session/{sid}/turn")
async def turn(sid: str,
               audio_file: Optional[UploadFile] = File(default=None),
               text: Optional[str] = Form(default=None)):
    s = _get(sid)
    if s.done:
        raise HTTPException(409, "call already ended")
    if s.turns >= config.MAX_TURNS_PER_SESSION:       # too long: end the call politely with the normal debrief
        return {"transcript": "", "intent": "limit", "leak": "none", "reply": None, "done": True,
                "outcome": "idle", "debrief": _public_debrief(s, engine.force_end(s)), "timings": {}}

    transcript, timings = "", {}
    if text is not None and config.ALLOW_TEXT_TURN:
        transcript = text
    elif audio_file is not None:
        t0 = time.time()
        raw = await audio_file.read()
        if len(raw) > 2_000_000:
            raise HTTPException(413, "audio too large")
        try:
            wav = audio.to_wav16k(raw)
        except audio.AudioError as e:
            raise HTTPException(400, str(e))
        timings["convert_ms"] = int((time.time() - t0) * 1000)
        st = audio.stats(wav)
        if st["seconds"] < 0.3 or st["rms"] < config.SILENCE_RMS:
            transcript = ""            # too short or too quiet: treat as silence, skip the paid STT call
        else:
            lang = engine.load_language(s.lang)
            t1 = time.time()
            try:
                transcript = await gnani.stt(wav, lang["stt"])
            except gnani.GnaniError as e:
                raise HTTPException(502, f"speech service error: {e}")
            timings["stt_ms"] = int((time.time() - t1) * 1000)
    # no audio and no text means the user stayed silent

    result = engine.step(s, transcript)
    return {
        "transcript": transcript,
        "intent": result["intent"],
        "leak": result["leak"],
        "reply": _public_reply(s, result["reply"]),
        "done": result["done"],
        "outcome": result["outcome"],
        "debrief": _public_debrief(s, result["debrief"]),
        "timings": timings,
    }


@app.post("/api/session/{sid}/hangup")
def hangup(sid: str):
    s = _get(sid)
    if not s.done:
        result = engine.step(s, "hang up")      # same path as saying it aloud
        return {"done": True, "debrief": _public_debrief(s, result["debrief"])}
    graph, lines = engine.load_graph(s.scenario_id), engine.load_lines(s.scenario_id, s.lang)
    return {"done": True, "debrief": _public_debrief(s, engine.build_debrief(s, graph, lines))}


@app.get("/api/health")
def health():
    return {"ok": True, "key_configured": bool(config.api_key()), "ffmpeg": config.ffmpeg_path()}


# ----------------------------------------------------------------- static

config.AUDIO_DIR.mkdir(exist_ok=True)
app.mount("/audio", StaticFiles(directory=config.AUDIO_DIR), name="audio")


@app.get("/")
def index():
    return FileResponse(config.FRONTEND_DIR / "index.html")


app.mount("/static", StaticFiles(directory=config.FRONTEND_DIR), name="static")
