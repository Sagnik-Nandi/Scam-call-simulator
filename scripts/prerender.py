"""Pre-render every scammer/debrief line to a WAV file, once.

    python scripts/prerender.py                    # all languages
    python scripts/prerender.py --lang en          # one language
    python scripts/prerender.py --force            # re-render everything
    python scripts/prerender.py --dry-run          # list what would be rendered and the character count

Output: audio/<scenario>/<lang>/<key>.wav, with a manifest.json that stores a hash of each line's text,
so unchanged lines are skipped and edited lines are re-rendered automatically.
"""
import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend import config, engine, gnani  # noqa: E402


def digest(text: str, voice: str, model: str) -> str:
    return hashlib.sha256(f"{model}|{voice}|{text}".encode("utf-8")).hexdigest()[:16]


async def render(scenario: str, lang_code: str, force: bool, dry: bool) -> int:
    lang = engine.load_language(lang_code)
    items = engine.audio_keys(engine.load_lines(scenario, lang_code), lang["persona"])
    out_dir = config.AUDIO_DIR / scenario / lang_code
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}

    chars = 0
    for key, text in items.items():
        h = digest(text, lang["voice"], lang["tts_model"])
        target = out_dir / f"{key}.wav"
        if not force and target.exists() and manifest.get(key) == h:
            continue
        chars += len(text)
        print(f"  {'would render' if dry else 'rendering'} {lang_code}/{key} ({len(text)} chars)")
        if dry:
            continue
        wav = await gnani.tts(text, lang["voice"], lang["tts"], lang["tts_model"])
        target.write_bytes(wav)
        manifest[key] = h
        manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return chars


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="digital_arrest", help="scenario id, or 'all'")
    ap.add_argument("--lang", default="all")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    langs = list(engine.list_languages()) if a.lang == "all" else [a.lang]
    scenarios = [s["id"] for s in engine.list_scenarios()] if a.scenario == "all" else [a.scenario]
    total = 0
    for scenario in scenarios:
        for code in langs:
            if not (config.SCENARIO_DIR / scenario / "lines" / f"{code}.json").exists():
                print(f"[{scenario}/{code}] no lines file, skipped")
                continue
            print(f"[{scenario}/{code}]")
            total += await render(scenario, code, a.force, a.dry_run)
    print(f"done. {total} characters {'would be ' if a.dry_run else ''}sent to TTS "
          f"(~{total * 0.002:.1f} credits at about 0.002 per character)")


if __name__ == "__main__":
    asyncio.run(main())
