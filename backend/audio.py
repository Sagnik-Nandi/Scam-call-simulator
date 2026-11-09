"""Browser audio (webm/ogg/mp4) -> 16 kHz mono WAV, plus a cheap loudness check."""
import array
import subprocess
import wave
import io

from . import config


class AudioError(Exception):
    pass


def to_wav16k(data: bytes) -> bytes:
    """Convert whatever the browser recorded into 16 kHz mono 16-bit WAV using ffmpeg."""
    cmd = [config.ffmpeg_path(), "-hide_banner", "-loglevel", "error", "-i", "pipe:0",
           "-ac", "1", "-ar", "16000", "-f", "wav", "pipe:1"]
    try:
        proc = subprocess.run(cmd, input=data, capture_output=True, timeout=20)
    except FileNotFoundError as e:
        raise AudioError("ffmpeg not found") from e
    except subprocess.TimeoutExpired as e:
        raise AudioError("ffmpeg timed out") from e
    if proc.returncode != 0 or not proc.stdout:
        raise AudioError("could not decode audio: " + proc.stderr.decode(errors="replace")[:200])
    return proc.stdout


def stats(wav_bytes: bytes) -> dict:
    """Duration (s) and RMS loudness of a 16-bit mono WAV."""
    with wave.open(io.BytesIO(wav_bytes)) as w:
        frames = w.readframes(w.getnframes())
        rate = w.getframerate()
    samples = array.array("h")
    samples.frombytes(frames[: len(frames) // 2 * 2])
    if not samples:
        return {"seconds": 0.0, "rms": 0}
    rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
    return {"seconds": len(samples) / rate, "rms": int(rms)}
