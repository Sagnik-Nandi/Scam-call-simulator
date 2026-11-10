"""Live API check: TTS -> STT round trip with timings, in every configured language.

    python scripts/smoke_test.py            # costs a few credits
Prints only ASCII-safe summaries (match / mismatch and latency), so it is safe in any terminal.
"""
import argparse
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend import engine, gnani  # noqa: E402


async def main(scenario: str):
    for code, lang in engine.list_languages().items():
        text = engine.load_lines(scenario, code)["lines"]["verify"]
        t0 = time.time()
        wav = await gnani.tts(text, lang["voice"], lang["tts"], lang["tts_model"])
        t1 = time.time()
        heard = await gnani.stt(wav, lang["stt"])
        t2 = time.time()
        # crude similarity: share of the original's words that appear in the transcript
        want, got = set(text.split()), set(heard.split())
        overlap = len(want & got) / max(1, len(want))
        print(f"{code}: tts {t1 - t0:.2f}s  stt {t2 - t1:.2f}s  word-overlap {overlap:.0%}  ({len(wav)} bytes)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="digital_arrest")
    asyncio.run(main(ap.parse_args().scenario))
