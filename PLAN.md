# Completion plan (drafted 10 Nov 2026, ~18:00 IST)

Deadline: **Tue 10 Nov 2026, 11:59 PM IST** (same day). Scope is cut to what can ship and be demoed tonight.

## Where things stand
- Working: digital-arrest scenario in en/hi/bn, engine, classifier, OTP-leak detector, FastAPI app, frontend, 165 passing tests.
- Not done: second scenario, scenario picker, `.env` loading (the app only read `GNANI_API_KEY` / `api-key.txt`), pre-rendered audio (needs the key), Spaces Dockerfile fix, deployment, submission write-up, demo video, LinkedIn/X post.

## Work packages (run in parallel, no shared files)

| # | Package | Files owned |
|---|---|---|
| A | Backend + infra: `.env` loading in `config.py`; `engine.list_scenarios()`; `/api/config` returns every scenario with per-language title and tricks; reject unknown scenario ids; `prerender.py --scenario all`; `smoke_test.py --scenario`; Dockerfile non-root user + writable `audio/_live`; `.venv` in `.gitignore`; API tests; `meta.title` in digital_arrest lines | `backend/config.py`, `backend/engine.py`, `backend/app.py`, `scripts/*.py`, `Dockerfile`, `.gitignore`, `tests/test_api.py`, `scenarios/digital_arrest/lines/*.json` (meta only) |
| B | New scenario `suspicious_transaction` ("a debit was just made, read me the OTP to cancel it"): graph + en/hi/bn lines + debrief; structural tests parametrised over all scenarios; walkthrough tests; sources rows | `scenarios/suspicious_transaction/**`, `tests/test_engine.py`, `docs/SOURCES.md` |
| C | Frontend scenario picker, per-scenario trick chips, sends chosen id; new UI strings in all three languages | `frontend/index.html`, `data/languages/*.json` (`ui` only) |
| D | Submission pack: written explanation, demo-video script, LinkedIn/X post draft | `SUBMISSION.md` (new) |

### `/api/config` contract (A produces, C consumes)
```json
{
  "languages": [{"code": "en", "name": "...", "ui": {}, "persona": {}, "review_status": "",
                 "tricks": [{"id": "authority", "name": "..."}],
                 "scenarios": {"digital_arrest": {"title": "Digital arrest call", "tricks": [{"id": "...", "name": "..."}]},
                               "suspicious_transaction": {"title": "...", "tricks": []}}}],
  "scenarios": [{"id": "digital_arrest", "title": "Digital arrest call"}, {"id": "suspicious_transaction", "title": "..."}],
  "helpline": "1930", "invite_required": false, "allow_text": false
}
```
`languages[].tricks` stays (digital_arrest) for backward compatibility. Localised title comes from `lines/<lang>.json` → `meta.title`, falling back to `graph.json` → `title`.

## Status (~19:00 IST)
Packages A–D landed and were reviewed. 237 tests pass. Both scenarios were played in the browser with typed replies (lose path; refuse path in en/hi/bn). Review fixes: the scenario picker now refreshes the landing trick chips, and "I will call my bank" now counts as a refusal in all three languages (it was classified as comply). Rows were added to `tests/data/utterances.csv`.

Key added (~19:15 IST): the smoke test passed in bn/en/hi. All 270 clips were rendered (2 scenarios × 3 languages × 45; script estimate ~70 credits; `audio/` is 91 MB). Live STT turn checked: a spoken refusal → `refuse`, spoken OTP digits → `leak`/`lose`.

## Needs the API key (after the packages land)
1. Put `GNANI_API_KEY=...` in `.env` (one Gnani key covers both Prisma STT and Timbre TTS).
2. `python scripts/smoke_test.py` (a few credits).
3. `python scripts/prerender.py --scenario all --dry-run`, then for real (~7 credits per scenario per language, ~42 total).
4. Play both scenarios in the browser: win, lose, silence, a question.

## Human-only (cannot be delegated)
- Deploy to Hugging Face Spaces (TEAMMATE.md section 8) and set secrets there.
- Record the demo video; publish the LinkedIn/X post (must be live before submitting); submit.
- Native-speaker pass on hi/bn lines; open and verify `UNVERIFIED` rows in `docs/SOURCES.md`.

## Out of scope tonight
Scenarios 1, 5, 7, 8 from `docs/SCAM_PLAYBOOKS.md` (5/7/8 need new detectors and endings).
