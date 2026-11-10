# Teammate brief: Scam Call Simulator

Read this first, then `README.md`. About 10 minutes.

## 1. The challenge (constraints that matter)
- Gnani AI Internship Challenge. **Final submission closes Tue 10 Nov 2026, 11:59 PM IST.** One entry per team.
- Deliverables: working app on a Gnani API, public demo video, written explanation (problem, users, APIs used, each member's contribution), and a **public LinkedIn/X post** tagged `#GreatIndianAIInternshipChallenge #GnaniAI` and tagging Gnani AI. The post must be live before submitting, and engagement counts, so post early.
- **Synthetic data only.** No real phone numbers, Aadhaar, PAN, account numbers or recorded calls. The demo must not mislead (the caller is clearly a simulation).
- Full notes: `docs/gnani-challenge-ideas.md`.

## 2. What the app is
A safe rehearsal of a scam phone call in **Hindi, Bengali and English**. The user "answers" the call and talks; a fake officer pressures them and demands a (synthetic, on-screen) OTP. At the end they get a debrief: which tactics were used, which worked on them, what to do instead.

- **The caller never uses a live LLM.** Every caller line is a fixed pre-written line, pre-rendered once to WAV with Gnani **Timbre** TTS. A rule-based call graph picks the next line.
- Gnani **Prisma** STT transcribes the user's reply. Intent is classified by keyword rules (comply / refuse / confused / question types / hangup / silence / unknown). A regex detector catches an OTP leak (Latin digits, Devanagari/Bengali digits, spoken digit words).
- Currently one scenario is built: **`digital_arrest`** ("parcel with drugs, you are under digital arrest, don't tell anyone, read me the OTP").

### Turn flow
mic audio -> ffmpeg (16 kHz wav) -> loudness check (silence skips paid STT) -> Prisma STT (explicit language code) -> OTP-leak check + intent classifier -> graph picks next node -> pre-rendered clip returned. Debrief is built from the session log.

### Gnani API facts
- REST base `https://api.vachana.ai`, header `X-API-Key-ID`. STT `POST /stt/v3` (model `prisma-v3.0`), TTS `POST /api/v1/tts/inference` (model `timbre-v2.5`).
- Needs a `User-Agent` that isn't python-urllib (Cloudflare error 1010); already handled in `backend/config.py`.
- The API allows one active request at a time (render sequentially).
- Credits: 5,000 programme credits. TTS about 0.6 credit per request; pre-rendering one language is about 7 credits. STT is about a tenth of that. **Don't burn credits in loops.**

## 3. Setup
```
pip install -r requirements.txt
cp .env.example .env            # or put the key in api-key.txt (git-ignored), or set GNANI_API_KEY
python scripts/prerender.py --lang en      # audio/ is git-ignored, so each machine renders its own clips
uvicorn backend.app:app --reload           # http://127.0.0.1:8000
python -m pytest -q                        # 103 tests, no network, no credits
```
Dev flag: `ALLOW_TEXT_TURN=1` shows a text box so you can test without a microphone. The browser only allows the mic on `localhost` or HTTPS.
Ask Sagnik for the API key privately. **Never commit it.** `api-key.txt`, `.env`, `audio/` are in `.gitignore`.

## 4. Repo map
```
backend/app.py          FastAPI routes: /api/config, /api/session, /api/session/{id}/turn, hangup, health, serves frontend
backend/engine.py       Session + graph walking (step()), debrief building. Scenario-agnostic except the OTP ending
backend/classifier.py   keyword intent classifier (per-language keywords from data/languages/*.json)
backend/otp.py          OTP-leak detector (digit runs, digit words, partial matches)
backend/gnani.py        STT/TTS client       backend/audio.py  ffmpeg wrapper       backend/config.py  env + paths
data/languages/*.json   per language: voice, STT/TTS codes, intent keywords, digit words, UI strings, persona
scenarios/<id>/graph.json        language-independent call graph (nodes, tactics, branch rules, interrupts)
scenarios/<id>/lines/<lang>.json scammer lines + debrief text per language
frontend/index.html     single page UI (language, answer call, tap-to-speak, hang up, debrief)
scripts/                prerender.py (TTS once), smoke_test.py (live API check), graph_diagram.py
tests/                  unit + API tests; tests/data/utterances.csv = labelled utterances for the classifier
docs/                   SCAM_PLAYBOOKS.md (research for new scenarios), SOURCES.md (fact verification), call graph diagram
```

## 5. Your task: add another scenario
Recommended order from `docs/SCAM_PLAYBOOKS.md`: **2. suspicious transaction** (almost no new engine work), then **1. bank KYC expiry**, then 5. card reward points, then 7/8 (need a "will pay" ending, so later). Pick one and ship it end to end for **at least English**, then Hindi/Bengali if time allows.

### Files to add (no code changes needed for an OTP-ending scenario)
| File | What to do |
|---|---|
| `scenarios/<new_id>/graph.json` | Copy `scenarios/digital_arrest/graph.json`. Keep node/interrupt structure; change `id`, `title`, node names, `tactics` per node, and `on` branch targets. Exactly one node has `show_otp` (where the OTP is demanded) and terminal nodes have `"terminal": "win"` or `"lose"`. |
| `scenarios/<new_id>/lines/en.json` (+ `hi.json`, `bn.json`) | Same keys as the graph nodes plus the generic ones (`generic.silence`, `generic.unknown`, `generic.clarify`, `otp.clarify`, per-step recaps `<node>.clarify`, interrupt variants like `ask_identity.1`/`.2`, `debrief.*`, `end_win`, `end_lose`). Include the `debrief` block (summary, worked, resisted, tactics, facts, help, disclaimer). Copy `digital_arrest/lines/en.json` as a template, keep every key. |

### Files to modify
| File | Change |
|---|---|
| `backend/app.py:73` | `get_config()` returns a hard-coded `"scenarios"` list. Add `{"id": "<new_id>", "title": "..."}`. |
| `frontend/index.html:173` | Session start hard-codes `scenario: "digital_arrest"`. Add a scenario picker (read `scenarios` from `/api/config`) and send the chosen id. Also adjust the intro copy near line 97 if it mentions only the arrest call. |
| `scripts/prerender.py`, `scripts/smoke_test.py`, `scripts/graph_diagram.py` | Already take `--scenario`; smoke_test.py hard-codes `digital_arrest` on line 17, make it a parameter or loop. |
| `tests/test_engine.py`, `tests/test_api.py` | Tests are written against `digital_arrest`. Parametrise over scenarios or copy the structural tests (every node has a line, every `on` target exists, no dead ends, no `{placeholder}` leaks, all languages have the same keys) for the new id. |
| `docs/SOURCES.md` | Add every factual claim in your debrief with a source URL and status. **Open the official page and read it** before marking it verified. |

### Files to modify only if the scenario needs new behaviour
| Need | Where |
|---|---|
| New tactic (e.g. `greed`, `install_app`, `emotional`) | add the tactic name to node `tactics` in the graph and a `debrief.tactics.<name>` text plus `debrief.tactic.<name>` audio line in every language's lines file |
| Different ending than "said the OTP" (card number/CVV, "agrees to pay/install") | `backend/otp.py` (new detector), `backend/engine.py` `step()` (leak/ending logic around the `check_leak` call), `data/languages/*.json` (new keywords/digit words), `tests/` |
| New intent keywords (e.g. "will pay") | `data/languages/*.json` `keywords`, then add labelled rows to `tests/data/utterances.csv` |
| Different persona/voice | `persona` and `voice` in `data/languages/*.json` (shared by all scenarios, so coordinate before changing) |

### Definition of done
1. `python scripts/prerender.py --scenario <new_id> --lang en --dry-run` shows a sane character count, then render for real.
2. `python -m pytest -q` is green.
3. Play it through in the browser: win path (refuse/hang up), lose path (leak the OTP), silence, and a question ("who are you?").
4. Debrief facts are sourced in `docs/SOURCES.md`.

## 6. Rules of the road
- Never put model-written dialogue in the live call. Lines are fixed and reviewed.
- Every call screen must say it is a simulation. Don't weaken `disclaimer` text.
- Don't invent statistics or legal claims. If a source isn't opened and read, don't state it as fact.
- Hindi and Bengali lines are machine-drafted from English and need a native reader (see `docs/translation_notes.txt` for glossary notes).
- Don't edit shared files (`engine.py`, `data/languages/*.json`, `index.html`) at the same time as Sagnik without telling them. Work on a branch: `git checkout -b scenario-<name>` and open a PR.
- Public deployment: set `INVITE_CODE`, keep `MAX_TURNS` / `MAX_SESSIONS_PER_HOUR`, put the key in host secrets, never in the image. See `Dockerfile` (audio must be pre-rendered before building).

## 7. Open items for the team
- Deploy somewhere public (Dockerfile targets port 7860, e.g. Hugging Face Spaces) and test on a phone (mic needs HTTPS or `localhost`).
- Demo video, written explanation, LinkedIn/X post (see section 1).
- Native-speaker review of Hindi/Bengali lines; verify the `UNVERIFIED` rows in `docs/SOURCES.md`.
