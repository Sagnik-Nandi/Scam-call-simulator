"""API flow with typed turns (ALLOW_TEXT_TURN=1 in conftest). No Gnani calls."""
from fastapi.testclient import TestClient

from backend.app import SESSIONS, app

client = TestClient(app)


def start(lang="en"):
    r = client.post("/api/session", json={"language": lang, "scenario": "digital_arrest"})
    assert r.status_code == 200, r.text
    return r.json()


def test_config_lists_three_languages():
    langs = {l["code"] for l in client.get("/api/config").json()["languages"]}
    assert {"en", "hi", "bn"} <= langs


def test_full_call_flow_and_otp_exposure():
    body = start()
    sid = body["session_id"]
    assert body["reply"]["text"] and "otp" not in body["reply"]
    seen_otp = None
    for _ in range(8):
        r = client.post(f"/api/session/{sid}/turn", data={"text": "yes"}).json()
        if r["reply"] and r["reply"].get("otp"):
            seen_otp = r["reply"]["otp"]
            break
    assert seen_otp and len(seen_otp) == 6
    r = client.post(f"/api/session/{sid}/turn", data={"text": f"it is {seen_otp}"}).json()
    assert r["done"] and r["outcome"] == "lose" and r["debrief"]["tactics"]


def test_hangup_returns_debrief():
    sid = start()["session_id"]
    r = client.post(f"/api/session/{sid}/hangup").json()
    assert r["done"] and r["debrief"]["outcome"] == "win"


def test_turn_after_end_is_rejected():
    sid = start()["session_id"]
    client.post(f"/api/session/{sid}/hangup")
    assert client.post(f"/api/session/{sid}/turn", data={"text": "hello"}).status_code == 409


def test_unknown_session_404():
    assert client.post("/api/session/nope/turn", data={"text": "x"}).status_code == 404


def test_unknown_language_rejected():
    assert client.post("/api/session", json={"language": "xx"}).status_code == 400


def test_invite_code_enforced(monkeypatch):
    from backend import config
    monkeypatch.setattr(config, "INVITE_CODE", "secret")
    assert client.post("/api/session", json={"language": "en"}).status_code == 403
    ok = client.post("/api/session", json={"language": "en"}, headers={"X-Invite-Code": "secret"})
    assert ok.status_code == 200


def test_turn_limit(monkeypatch):
    from backend import config
    monkeypatch.setattr(config, "MAX_TURNS_PER_SESSION", 1)
    sid = start()["session_id"]
    assert client.post(f"/api/session/{sid}/turn", data={"text": "I don't understand"}).status_code == 200
    over = client.post(f"/api/session/{sid}/turn", data={"text": "I don't understand"})
    assert over.status_code == 200, "hitting the reply limit must end the call politely, not error"
    body = over.json()
    assert body["done"] and body["debrief"]["tactics"] and body["reply"] is None


# ---------------------------------------------------------------- practice name

def test_default_persona_needs_no_live_tts(monkeypatch):
    from backend import gnani

    async def boom(*a, **k):
        raise AssertionError("live TTS must not run for the default persona")
    monkeypatch.setattr(gnani, "tts", boom)
    body = start()
    assert body["persona"]["name"] == "Rohit Sharma" and "Rohit Sharma" in body["reply"]["text"]


def test_custom_name_is_spoken_and_rendered_live(monkeypatch):
    from backend import gnani
    calls = []

    async def fake_tts(text, *a, **k):
        calls.append(text)
        return b"RIFF0000WAVEfake"
    monkeypatch.setattr(gnani, "tts", fake_tts)
    body = client.post("/api/session", json={"language": "en", "nickname": "Anita"}).json()
    assert "Anita" in body["reply"]["text"] and "Rohit" not in body["reply"]["text"]
    assert body["reply"]["audio_url"].startswith("/audio/_live/")
    assert len(calls) >= 3 and all("Anita" in c for c in calls)     # greet, parcel, final_warning
    assert client.get(body["reply"]["audio_url"]).status_code == 200


def test_live_render_failure_falls_back_to_default_name(monkeypatch):
    from backend import gnani

    async def fail(*a, **k):
        raise gnani.GnaniError("down")
    monkeypatch.setattr(gnani, "tts", fail)
    body = client.post("/api/session", json={"language": "en", "nickname": "Anita"}).json()
    assert body["persona"]["name"] == "Rohit Sharma" and "Anita" not in body["reply"]["text"]


def test_nickname_sanitizing():
    from backend.engine import sanitize_nickname as s
    assert s("Anita") == "Anita" and s("  Anita   Das ") == "Anita Das"
    assert s("") == "" and s("9876543210") == "" and s("ab<script>") == "" and s("http://x.com") == ""
    assert s("x" * 50) == "x" * 20
    assert s("अनिता") != ""             # Devanagari name survives (combining marks kept)
