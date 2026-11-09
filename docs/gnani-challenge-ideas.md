# Gnani AI Internship Challenge: Project Ideas

Draft as of Sun 8 Nov 2026. Shortlist of three ideas for our team of two, with build, data, and deployment notes. Final pick is still open.

## 1. Challenge facts that constrain us

- **Goal:** build a working application on Gnani AI's models or APIs that solves a practical need. There is no fixed problem statement.
- **Deadline:** final submissions close Tue 10 Nov 2026, 11:59 PM IST.
- **One entry per team.** We cannot ship all three ideas as separate entries.
- **Deliverables:** working app on at least one Gnani model/API, public demo video, written project explanation (problem, users, models/APIs used, each member's contribution), and a public demo post on LinkedIn and/or X tagged with #GreatIndianAIInternshipChallenge and #GnaniAI, tagging Gnani AI. The post must be live before we submit.
- **Two tracks:**
  - Ten award categories at Rs 50,000 each (Main Character, Mixed Vibes, Real Deal, Noise Canceller, Two-Person Army, Solo Ninja, Jugaad Genius, Small Town Big Build, Demo Day Drop, Crowd Favourite). No team wins more than one.
  - Internship selection (up to 100 six-month roles): verified engagement on the nominated post, then a check for genuine Gnani usage, then shortlisting, interviews, and written offers. Engagement is recorded by the cutoff, so post early.
- **Rules:** synthetic data only (no real phone numbers, Aadhaar, PAN, account numbers, or recorded calls). No purchased engagement, bots, engagement swaps, plagiarism, or misleading demos.
- **Scope:** only the API platform (app.gnani.ai/voice) is covered. Agent Builder is out of scope.
- **Credits:** 5,000 programme credits, held on the primary registrant's account.

## 2. What we have

- Gnani API access, 3 API keys, 5,000 credits. Observed burn: TTS about 0.6 credits per request (100 to 300 Hindi characters), STT about a tenth of that. At that rate, 5,000 credits is roughly 8,000 TTS calls. Pricing is not in the docs, so confirm on the dashboard, including whether STT cost scales with audio length and whether credits are per key or per account.
- Evon v3.3 (30B-A3B) open weights. Not on the API platform.
- Claude Pro. This is a chat subscription and does not provide API calls for the app at runtime. Use it for writing code, scripts, and test sets.

### Gnani API quick reference

- REST base: `https://api.vachana.ai`. WebSocket base: `wss://api.vachana.ai`.
- Auth: `X-API-Key-ID` header on REST, `x-api-key-id` on WebSocket upgrade headers.
- STT REST: `POST /stt/v3` (multipart: `audio_file`, `model` = `prisma-v3.0` or default `prisma-v2.5`, `language_code` e.g. `hi-IN` or `indic-auto` on v3.0). Formats: WAV, MP3, OGG, FLAC, AAC, M4A. Sample rate 8 to 44.1 kHz. Quick-start says 30 s max, the overview says 60 s: test with short clips.
- STT realtime: `wss://api.vachana.ai/stt/v3/stream`. Binary PCM 16-bit mono, 8 or 16 kHz, send `{"type":"commit"}` when done.
- TTS REST: `POST /api/v1/tts/inference` (JSON: `text`, `voice` e.g. `Nalini`, `model` = `timbre-v2.5`, `language`, `speed`, `audio_config`). Also SSE at `/api/v1/tts/sse` and WebSocket at `wss://api.vachana.ai/api/v1/tts`. Docs disagree on whether realtime TTS returns base64 JSON or binary PCM, so prefer REST or SSE.
- Not in the pages we read: supported-language list, TTS voice catalog, rate limits, error codes. Check these before committing to a regional language.

Smoke test (about 1 credit):

```bash
curl -X POST https://api.vachana.ai/api/v1/tts/inference \
  -H "X-API-Key-ID: $GNANI_KEY" -H "Content-Type: application/json" \
  -d '{"text":"नमस्ते, आपको क्या चाहिए?","voice":"Nalini","model":"timbre-v2.5","language":"hi-IN","speed":1.0,"audio_config":{"sample_rate":44100,"num_channels":1,"sample_width":2,"encoding":"linear_pcm","container":"wav"}}' \
  --output out.wav

curl -X POST https://api.vachana.ai/stt/v3 \
  -H "X-API-Key-ID: $GNANI_KEY" \
  -F audio_file=@out.wav -F model=prisma-v3.0 -F language_code=hi-IN
```

## 3. The three ideas

### Idea 1: Scam-call simulator (Real Deal, Jugaad Genius)

A safe rehearsal of a "digital arrest" or fake-bank-officer call, so people recognize the pressure tactics before a real call arrives.

- **Users:** people likely to get these calls (parents, elderly relatives, first-time smartphone users), and the younger relatives who share it with them.
- **Input:** spoken replies and a hang-up button. A synthetic OTP is shown on screen and the fake officer demands it.
- **Output:** a live call with escalating TTS pressure, then a spoken and on-screen debrief: which tactics were used (urgency, authority, secrecy, "don't tell your family"), which ones worked on the user, and what to do instead. Optional share card.
- **Interaction:** pick a scenario and language, press "answer call", talk, get the debrief.
- **Build:** scenario graph in JSON (node = pre-rendered scammer line plus branch rules). Each turn: STT, classify intent (comply / refuse / confused / hang up), next node. OTP leak detection by regex over the transcript, covering Latin digits, Devanagari digits, and spoken digit words. Evon is optional as a fallback classifier for unrecognised replies. Do not let any model write live scammer dialogue.
- **Training:** none. Write about 100 test utterances (around 20 per intent, Hindi and Hinglish) and tune the rules against them.
- **Data:** none at runtime. Base the tactics and debrief on official advisories (cybercrime reporting portal, RBI and government awareness material) and verify any factual claim before putting it in the app.
- **Pros:** most shareable, real impact, fully synthetic, most robust in a demo, works without an LLM.
- **Cons:** quality depends on the script, not engineering. Must clearly state the caller is a simulation.
- **Extensions:** more scenarios (courier parcel, KYC expiry, fake job offer), more languages, family mode with scores, a "calls survived" leaderboard.

### Idea 4: Mock placement interviewer (Real Deal, Crowd Favourite)

A voice interviewer that gives feedback on how you spoke, not just what you said.

- **Users:** final-year students preparing for placements. Also our likely LinkedIn audience.
- **Input:** spoken answers to 5 or 6 questions from a question bank (introduction, strengths, conflict, failure, why this company).
- **Output:** per-answer and overall reports: pace (words per minute), filler words, answer length, English/Hindi mix, a rough structure check (situation, action, result). A short TTS summary at the end.
- **Interaction:** choose role and language preference, listen to the question, record, answer, move on, review the report.
- **Build:** pace = word count divided by speaking time measured from the audio (trim silence). Fillers = lexicon matches (English: um, uh, like, basically, you know; Hindi: matlab, toh, yaani). Language mix = Devanagari vs Latin token ratio, if Prisma outputs code-mixed text that way (test this). Evon can score a rubric as JSON and generate a follow-up question. Answers over 30 s need realtime STT.
- **Training:** none. Calibrate thresholds on 15 to 20 recordings of ourselves, including deliberately filler-heavy ones. Present the bands as heuristics, not science.
- **Data:** own recordings and a self-written 30-question bank. Optional: an accented Indian English test set to sanity-check the STT.
- **Main risk:** ASR often drops "um" and "uh". Test in the first hour. If fillers vanish, fall back to pace and structure scoring and drop the filler claim. Do not score accent. Do not claim to measure "confidence".
- **Pros:** broad appeal, easy to chart, best genuine use of Evon.
- **Cons:** most technical risk of the three, and requires a working GPU path if Evon is used.
- **Extensions:** company-specific question banks, progress graph across attempts, re-answer-with-feedback loop.

### Idea 5: Voice-to-government-form (Main Character, Real Deal)

A spoken form-filling assistant for people who find typed forms hard.

- **Users:** low-literacy or low-typing users, and helpers at a village kiosk or CSC.
- **Input:** spoken answers to the fields of one fixed form (name, age, district, mobile, income bracket). Synthetic values only.
- **Output:** a filled form on screen, exported as JSON or PDF, with a spoken read-back of every field.
- **Interaction:** detect language from the first reply (`indic-auto` on Prisma v3.0), ask one field at a time, read back, wait for yes or no, re-ask on no.
- **Build:** YAML form schema (field, type, validator, prompts per language, pre-cached TTS). Yes/no by keyword lists per language. Phone numbers by digit-by-digit speech. Names need native-script to English transliteration, which is the hard part: Evon by prompt, or an open transliteration library.
- **Training:** none.
- **Data:** Faker with Indian locales for synthetic names and addresses, district lists from official public sources, own recorded test audio.
- **Pros:** clear real-world framing, shows STT and TTS together through the confirmation loop.
- **Cons:** weakest differentiation (likely to be a common pick), name transliteration and spoken numbers are error-prone, looks less general with a hard-coded form.
- **Extensions:** multiple forms, correction by voice ("change my village"), dialect handling, printable summary.

## 4. Shared stack (build once, reuse for any idea)

- **Frontend:** single page, push-to-talk button, audio playback.
- **Backend:** FastAPI holding the API keys in environment variables. Browsers cannot set custom headers on WebSockets, so all Gnani calls must be proxied through the backend.
- **Audio:** Chrome's MediaRecorder produces webm, which is not on the supported STT format list. Convert with ffmpeg on the server (include it in the Dockerfile).
- **Credit saver:** pre-render every fixed TTS line once and serve it as a static file. Only STT remains a per-turn cost.
- **Keys:** one for dev, one for the live demo, one for recording. Never in frontend code or a public repo.

## 5. Evon (reasoning model) notes

- 30B-parameter mixture-of-experts, about 3.5B active per token, 128K context, Apache 2.0, text only. Languages: English, Hindi, Bengali, Telugu, Tamil, Marathi, Gujarati, Kannada, Malayalam, Odia, Punjabi.
- Hardware per the model page: Linux with an NVIDIA H100 80GB, H200, or A100. Quantized builds are listed for llama.cpp, Ollama, and LM Studio.
- Serving: vLLM (OpenAI-compatible) with the `nano_v3` reasoning parser, and `trust_remote_code=True` for Transformers. Reasoning is on by default, so set `enable_thinking=False` for a voice loop. Lower `--max-model-len` (for example 8192) to save memory.
- Tool use is described as still under development: do not build on function calling.
- The model page's example IDs omit the `-30B-A3B` suffix that the URL has. Check the exact repo name.
- Decision rule: if a working GPU or quantized setup is not running by tonight, ship with rules and skip Evon. Do not spend day one on hosting.
- Any voice agent built on the model must disclose that it is AI.

## 6. Deployment

- Static frontend plus FastAPI backend on a host that supports WebSockets and Docker (Render, Railway, Fly.io, or a Hugging Face Space). Avoid serverless platforms for the WebSocket path. Microphone access needs HTTPS, which these hosts provide. Free tiers cold-start, so warm the app before recording.
- Evon: a rented GPU running vLLM, or a local quantized build.
- A live link is not a stated deliverable. The video, written explanation, and post are. If we do go live, add per-session call caps and an invite code so strangers cannot drain the credits.

## 7. Comparison

| | 1. Scam simulator | 4. Interviewer | 5. Voice form |
|---|---|---|---|
| Needs an LLM | No (optional fallback) | Helpful (rubric, follow-ups) | Helpful (names) |
| Needs Evon on GPU | No | Best fit | Optional |
| Demo robustness | High | Medium | Medium |
| Shareability | High | High (students) | Medium |
| Differentiation | High | Medium-high | Low |
| Biggest risk | Script quality | ASR drops fillers | Name transliteration |

Current lean: Idea 1 as the main build (scripted, robust, shareable), with Idea 4 as a stretch mode only if the shared core is done early and a GPU path exists.

## 8. Open decisions

1. Which single idea do we commit to?
2. Do we have an 80GB GPU (or acceptable quantized setup) available tonight? If not, Evon is out.
3. Which language(s)? Check Gnani's supported-language list and TTS voice catalog first.
4. Who takes which half (voice core and backend vs script, UI, demo video, and post)?

## 9. Rough timeline (IST)

- **Sun night:** run the smoke test, check the language list and voices, lock the idea, write the demo script first.
- **Mon:** finish the working loop, record the demo, post it early (engagement is counted until the cutoff), submit.
- **Tue:** buffer only. Final submissions close at 11:59 PM.

## Sources

- Challenge page: https://www.gnani.ai/internship
- Quick start: https://docs.gnani.ai/api/introduction/quick-start
- API overview: https://docs.gnani.ai/api/introduction/introduction
- Evon v3.3: https://huggingface.co/gnani/gnani-evon-v3.3-30B-A3B
