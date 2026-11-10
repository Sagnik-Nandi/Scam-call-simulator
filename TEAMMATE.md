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
- Deploy somewhere public and test on a phone (mic needs HTTPS or `localhost`). Steps for Hugging Face Spaces and Vercel are in section 8.
- Demo video, written explanation, LinkedIn/X post (see section 1).
- Native-speaker review of Hindi/Bengali lines; verify the `UNVERIFIED` rows in `docs/SOURCES.md`.

## 8. Deploying

**Status: neither route below has been run yet. The steps are written from how these platforms normally work, so treat them as a checklist to confirm, not a tested recipe.** Challenge deadline is Tue 10 Nov 2026, 11:59 PM IST, so pick the Spaces route unless there is a strong reason not to.

### Why a container host, not serverless
The app keeps call sessions in memory (`SESSIONS` in `backend/app.py`), needs ffmpeg, writes custom-name clips to `audio/_live/` while running, and serves about 45 MB of pre-rendered clips. One always-on container runs all of that unchanged. Serverless platforms do not.

### A. Hugging Face Spaces (Docker Space). Recommended
The `Dockerfile` already installs ffmpeg and listens on port 7860, which is the Spaces default.

Before you start:
- A Hugging Face account and a write access token (Settings > Access Tokens).
- Render the clips locally: `python scripts/prerender.py`. `audio/` is git-ignored and the Dockerfile does `COPY audio ./audio`, so the clips must be in what you push.

Steps:
1. Go to huggingface.co/new-space. Pick a name, set SDK to **Docker** (blank template) and free CPU hardware.
2. In the Space, open Settings > Variables and secrets and add:
   - secret `GNANI_API_KEY` (your Gnani key, never commit it)
   - secret `INVITE_CODE` (stops strangers spending Gnani credits; share it only with judges and testers)
   - variables `MAX_SESSIONS_PER_HOUR=200` and `MAX_TURNS=30`
   - do not set `ALLOW_TEXT_TURN`
3. A Space is its own git repo. Build a deploy branch that contains the clips and the Space front matter, and keep it off `main`:
   ```
   git checkout -b hf-deploy
   rm -rf audio/_live                  # per-session leftovers, not needed
   git add -f audio                    # audio/ is ignored on main, force-add it on this branch only
   ```
   Add this block as the very first lines of `README.md` on this branch (Spaces reads its settings from it):
   ```
   ---
   title: Scam Call Simulator
   sdk: docker
   app_port: 7860
   ---
   ```
   Then commit and push to the Space (use your Hugging Face username and the access token as the password):
   ```
   git commit -am "Space deploy"
   git remote add space https://huggingface.co/spaces/<user>/<space-name>
   git push space hf-deploy:main -f
   ```
   (`-f` is needed because a new Space already has its own starter commit.)
4. The Space builds the Dockerfile by itself; watch the Logs tab. When it says Running, open `https://<user>-<space-name>.hf.space` (the direct URL, not the embedded page on huggingface.co). It is HTTPS, so the microphone works on phones.
5. To redeploy: `git checkout hf-deploy && git rebase main && git push space hf-deploy:main -f` (the Space repo has its own history, so a forced push of this branch is normal here).

Known catches to check:
- **Writable folder.** Spaces run the container as a non-root user, but the app writes custom-name clips to `/app/audio/_live`. If that folder is not writable, the app silently falls back to the default name, so custom names will not work. The likely fix is in the `Dockerfile`, before `CMD`: `RUN useradd -m -u 1000 user && mkdir -p /app/audio/_live && chown -R user /app` then `USER user`.
- **Sleeping and restarts.** Free Spaces can sleep when idle, and a restart wipes in-memory sessions (a call in progress would fail). Open the app just before recording the demo and expect a slow first load.
- **One instance only.** Keep a single replica; sessions live in that process's memory.
- **Push size.** The clips are about 45 MB (largest about 1 MB each). If the push is rejected for file size, run `git lfs track "*.wav"` on the deploy branch and commit again.

Other container hosts (Render, Railway, Fly.io) work the same way: create a web service from the GitHub repo using the `Dockerfile`, add the same env vars, and get the clips into the build (same deploy-branch trick, or run `prerender.py` during the build with the key available).

### B. Vercel. Not recommended
Vercel runs the app as short-lived serverless functions. As the code stands, four things break:
1. **Sessions vanish.** Requests can land on different instances, so a turn often hits one that has never seen the call and returns 404 "session not found". You would need an external store (for example Upstash Redis) or call state carried in a signed token.
2. **No ffmpeg.** The `imageio-ffmpeg` fallback in `backend/config.py` might work, but the bundled binary is large against the function size limit (about 250 MB unzipped).
3. **Audio files.** The clips are git-ignored and must be committed and included in the deploy. The live custom-name clips are written to disk at runtime, and Vercel's disk is read-only apart from `/tmp` and not shared between instances, so that feature would need blob storage.
4. **Timeouts and rate limit.** Custom-name rendering takes about 6 seconds and speech-to-text takes time too, so check your plan's function time limit. The hourly session cap (`_session_starts`) is per instance, so it would not hold.

If you still want to try it:
1. Add a root `app.py` containing `from backend.app import app` so Vercel finds the FastAPI app.
2. Fix the four problems above.
3. At vercel.com/new, import the GitHub repo.
4. Under Settings > Environment Variables set `GNANI_API_KEY` and `INVITE_CODE` (never commit the key).
5. Deploy. HTTPS is automatic, so the microphone works on phones.
