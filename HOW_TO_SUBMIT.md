# How to run the demo and submit

Team-only guide for the Gnani AI Internship Challenge. The deadline is **Tue 10 Nov 2026, 11:59 PM IST**. Either of us can follow it from the zip.

The text for the form (project explanation, team contributions, video script, LinkedIn and X posts) is in `SUBMISSION.md`.

## 0. What is in the zip

- The full project, with **all 270 pre-rendered caller clips** in `audio/digital_arrest/` and `audio/suspicious_transaction/`. You do not need to spend credits rendering them again.
- It does **not** include `.env` (the API key), `.venv`, caches, or `audio/_live/` (clips rendered during our own test calls). You create `.env` yourself in step 1.

## 1. Run the demo locally (about 5 minutes)

You need Python 3.11 or newer. ffmpeg is optional: if it is not installed, the `imageio-ffmpeg` package supplies a copy. On a Mac you can also run `brew install ffmpeg`.

```bash
cd hackathon-gnani-scam-call-simulator
```
```bash
python3 -m venv .venv && source .venv/bin/activate
```
```bash
pip install -r requirements.txt
```

Create a file named `.env` in the project folder with one line. One Gnani key covers both Prisma STT and Timbre TTS. Never commit this file. `.gitignore` already excludes it.

```
GNANI_API_KEY=paste-your-key-here
```

Start the app:

```bash
uvicorn backend.app:app --port 8000
```

Open http://127.0.0.1:8000 in Chrome. The browser allows the microphone on `localhost` without HTTPS. Pick a language and a scenario, then press **Answer call** and tap to speak.

- **Check:** http://127.0.0.1:8000/api/health should show `"key_configured": true`.
- **No microphone, or want to save credits?** Start it with `ALLOW_TEXT_TURN=1 uvicorn backend.app:app --port 8000`. A text box then appears, so you can type replies. Typed replies do not call speech-to-text. Do not turn this on in the public deployment.
- **Tests:** `python -m pytest -q` runs without network or credits. Expected result: 254 passed.

### Things to try in a demo call

| Scenario | Say | What happens |
|---|---|---|
| Either | "What is this about?" | The caller tells the story |
| Either | "Who are you? Which bank?" | An in-character answer, then the caller pushes on |
| Either | "I will call my bank myself" | The caller escalates with a warning |
| Either | Read out the six-digit code shown on screen | You lose. The debrief shows which tactics worked |
| Either | "I will not share any code. I am hanging up." or press hang up | You win. Debrief |

## 2. Push the code to GitHub (teammate with GitHub access)

`audio/` is in `.gitignore`, so the clips are not pushed to GitHub. That is fine: the public demo runs on Hugging Face (step 3), and anyone cloning the repo can render the clips again with `python scripts/prerender.py --scenario all` (roughly 40 to 70 credits).

**If the team repo already exists**, copy the new files over your clone and push:

```bash
git clone https://github.com/<owner>/<repo>.git && cd <repo>
```
```bash
rsync -a --exclude .git --exclude .env --exclude .venv --exclude audio/ ../hackathon-gnani-scam-call-simulator/ ./
```
```bash
git status
```

Check that `git status` does not list `.env` or `api-key.txt`, then:

```bash
git add -A && git commit -m "Add suspicious transaction scenario, scenario picker, reply-understanding fixes, submission pack"
```
```bash
git push
```

**If there is no repo yet** (needs the `gh` CLI, logged in with `gh auth login`):

```bash
cd hackathon-gnani-scam-call-simulator && git init -b main && git add -A && git status
```
```bash
git commit -m "Scam Call Simulator for the Gnani AI Internship Challenge"
```
```bash
gh repo create <repo-name> --public --source . --push
```

The submission needs a public repo link, so the repo must be public.

## 3. Deploy the public demo on Hugging Face Spaces (free)

The mic only works over HTTPS, and a Space gives you that.

1. Go to https://huggingface.co/new-space. Choose **SDK: Docker**, the **Blank** template, and **CPU basic (free)**. Make the Space **public**.
2. In the Space, open **Settings → Variables and secrets** and add:
   - Secret `GNANI_API_KEY`: the key.
   - Variable `MAX_TURNS` = `30` and variable `MAX_SESSIONS_PER_HOUR` = `200`. These cap credit spend.
   - Optional: secret `INVITE_CODE`. If you set it, visitors must type the code, so put it in the submission. Leaving it out is simpler for judges.
   - Do **not** set `ALLOW_TEXT_TURN`.
3. Push the code and audio. The clips go through Git LFS:

```bash
brew install git-lfs && git lfs install
```
```bash
git clone https://huggingface.co/spaces/<hf-user>/<space-name> space && cd space
```
```bash
rsync -a --exclude .git --exclude .env --exclude .venv --exclude audio/_live --exclude .gitignore ../hackathon-gnani-scam-call-simulator/ ./
```
```bash
git lfs track "*.wav" "*.png" && git add .gitattributes
```

   Replace the top of the Space's `README.md` with this header. The Space reads its settings from it:

```
---
title: Scam Call Simulator
emoji: 📞
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---
```

   Then commit and push. Git asks for your Hugging Face username, and for a **write** access token as the password. Create the token at https://huggingface.co/settings/tokens.

```bash
git add -A && git status
```
```bash
git commit -m "Deploy Scam Call Simulator" && git push
```

4. Watch the **Logs** tab. The build takes a few minutes. When it says Running, open `https://<hf-user>-<space-name>.hf.space`.
5. Check `https://<hf-user>-<space-name>.hf.space/api/health`. It should show `"key_configured": true`.

Rajat's machine has a ready-made copy of this repo at `~/Downloads/scam-call-simulator-space`, with LFS and the header already set. From there it is only `git remote add space https://huggingface.co/spaces/<hf-user>/<space-name>`, then `git push --force space main`.

## 4. Submit (in this order)

- [ ] Open the Space on a phone over HTTPS. Allow the mic, then do one call per scenario: a win, a loss, and one question to the caller.
- [ ] Record the demo video from the deployed app, following `SUBMISSION.md` section 3 (about 95 seconds).
- [ ] In `SUBMISSION.md`, replace `[Member 1 name]`, `[Member 2 name]`, `[demo link]` and `[repo link]`.
- [ ] Publish the LinkedIn and X posts from `SUBMISSION.md` section 4. Check that they are **public and live** before submitting.
- [ ] Fill in the submission form with the written explanation (section 1), team names, the demo video link, the repo link, the Space link, and the post links.

## If something goes wrong

| Symptom | Fix |
|---|---|
| `key_configured: false` | `.env` is missing or not in the folder you started from, or the Space secret is not named exactly `GNANI_API_KEY`. Restart after fixing it. |
| The caller is silent or a clip is missing (404) | The `audio/` folder did not come along. Copy it from the zip, or run `python scripts/prerender.py --scenario all`. |
| No mic prompt on the phone | The page must be HTTPS, which the Space URL is. Allow the mic in the browser's site settings. |
| The Docker build fails at `COPY audio` | `audio/` was not pushed. Run `git lfs ls-files \| wc -l` in the Space clone; it should be about 270. |
| Every reply "doesn't register" | Check the Space logs for STT errors. Gnani allows one active request at a time, so do not run two calls at once. |
