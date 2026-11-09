"""Thin async client for the Gnani (Vachana) speech API. The key never leaves the server."""
import asyncio
import json

import httpx

from . import config


class GnaniError(Exception):
    pass


def _headers() -> dict:
    key = config.api_key()
    if not key:
        raise GnaniError("no Gnani API key configured (set GNANI_API_KEY or provide api-key.txt)")
    return {"X-API-Key-ID": key, "User-Agent": config.USER_AGENT}


_gates: dict = {}


def _gate() -> asyncio.Semaphore:
    """The API allows ONE active request at a time (HTTP 429 RATE_LIMITED otherwise).
    Serialise every call in this process; one gate per event loop."""
    loop = asyncio.get_running_loop()
    return _gates.setdefault(id(loop), asyncio.Semaphore(1))


async def _post(client: httpx.AsyncClient, url: str, retries: int = 3, **kwargs) -> httpx.Response:
    last = None
    for attempt in range(retries + 1):
        try:
            async with _gate():
                resp = await client.post(url, **kwargs)
            if resp.status_code == 429:                 # another request still active: wait and retry
                last = GnaniError(f"HTTP 429: {resp.text[:200]}")
            elif resp.status_code < 500:
                return resp
            else:
                last = GnaniError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        except httpx.HTTPError as e:
            last = GnaniError(f"network error: {e}")
        await asyncio.sleep(0.5 * (attempt + 1))
    raise last


async def stt(wav_bytes: bytes, language_code: str, model: str = None) -> str:
    """Transcribe a short WAV clip. Always pass an explicit language code (auto-detect is less reliable)."""
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await _post(
            client, f"{config.GNANI_BASE}/stt/v3",
            headers=_headers(),
            files={"audio_file": ("turn.wav", wav_bytes, "audio/wav")},
            data={"model": model or config.STT_MODEL, "language_code": language_code},
        )
    if resp.status_code != 200:
        raise GnaniError(f"STT HTTP {resp.status_code}: {resp.text[:200]}")
    body = resp.json()
    if not body.get("success", True):
        raise GnaniError(f"STT failed: {body}")
    return (body.get("transcript") or "").strip()


async def tts(text: str, voice: str, language: str, model: str = "timbre-v2.5",
              speed: float = 1.0, sample_rate: int = None) -> bytes:
    """Synthesize `text` to WAV bytes. Body is sent as UTF-8 JSON (non-ASCII safe)."""
    payload = {
        "text": text, "voice": voice, "model": model, "language": language, "speed": speed,
        "audio_config": {"sample_rate": sample_rate or config.TTS_SAMPLE_RATE, "num_channels": 1,
                         "sample_width": 2, "encoding": "linear_pcm", "container": "wav"},
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await _post(
            client, f"{config.GNANI_BASE}/api/v1/tts/inference",
            headers={**_headers(), "Content-Type": "application/json"},
            content=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        )
    if resp.status_code != 200 or resp.content[:4] != b"RIFF":
        raise GnaniError(f"TTS HTTP {resp.status_code}: {resp.text[:200]}")
    return resp.content
