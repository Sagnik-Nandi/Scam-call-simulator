# Scam Call Simulator

**Live Demo:** [https://scam-call-simulator.onrender.com/](https://scam-call-simulator.onrender.com/)

A safe rehearsal of two common scam calls in Hindi, Bengali and English: a "digital arrest" call and a fake bank "suspicious transaction" call. You talk back by voice. The "caller" is a set of fixed pre-rendered lines chosen by a rule-based call graph. No model writes live dialogue. Built on Gnani Prisma (speech to text) and Timbre (text to speech). Project background: `docs/gnani-challenge-ideas.md`.

**Running the demo, deploying, and submitting:** see `HOW_TO_SUBMIT.md`. The submission text is in `SUBMISSION.md`.

## Layout
```
backend/      FastAPI app, Gnani client, scenario engine, intent classifier, OTP-leak detector, ffmpeg wrapper
data/languages/       per-language: voice, STT/TTS codes, intent keywords, digit words, UI strings   (en, hi, bn)
scenarios/<id>/graph.json   language-independent call graph (nodes, tactics, branch rules)
scenarios/<id>/lines/       per-language scammer lines + debrief text   (ids: digital_arrest, suspicious_transaction)
scripts/      prerender.py (TTS once), smoke_test.py (live API check)
tests/        unit + API tests, labelled utterance set (tests/data/utterances.csv)
frontend/     single page: language, answer call, tap-to-speak, hang up, debrief
docs/SOURCES.md   factual claims and their sources (verification status)
audio/        generated clips (git-ignored)
```

## Run it locally
```
pip install -r requirements.txt
python scripts/prerender.py --scenario all   # renders clips once (skip if audio/ came with the zip)
uvicorn backend.app:app --reload             # open http://127.0.0.1:8000
```
The key is read from `GNANI_API_KEY` (environment or a `.env` file in the project folder), else from `api-key.txt` (both git-ignored). Dev option: `ALLOW_TEXT_TURN=1` shows a text box so you can test the flow without a microphone.

## Tests
```
python -m pytest -q          # no network, no credits
python scripts/smoke_test.py # live TTS->STT round trip per language (a few credits)
```

## How a turn works
mic audio -> ffmpeg (16 kHz wav) -> loudness check (silence skips the paid STT call) -> Prisma STT with the explicit language code
-> OTP-leak check + intent classifier -> graph picks the next node -> the pre-rendered clip is returned. Debrief is built from the session log.

## Adding or improving a language
1. Add `data/languages/<code>.json` (copy `en.json`; set `stt`, `tts`, `voice`, keywords, `digit_words`, UI strings).
2. Add `scenarios/digital_arrest/lines/<code>.json` (same keys as `en.json`).
3. Add rows to `tests/data/utterances.csv` and run the tests.
4. `python scripts/prerender.py --lang <code>`.

## Safety and honesty rules
- Every call screen and the first screen say it is a simulation. The OTP is random and synthetic.
- Only synthetic data. No real numbers or recordings. Nothing the user says is stored.
- Facts shown to users must be verified (see `docs/SOURCES.md`).
- Public deployment: set `INVITE_CODE`, keep `MAX_TURNS` and `MAX_SESSIONS_PER_HOUR`, put the key in host secrets, never in the image.
