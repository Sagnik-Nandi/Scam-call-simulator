# Scam Call Simulator: Submission Pack

Working draft for the team. Replace every bracketed placeholder before submitting. Both scenarios, the scenario picker and the pre-rendered audio are done. Deployment is the remaining build step.

## 1. Project explanation

**Problem.** Scam calls such as "digital arrest" and fake bank-fraud calls work through pressure. The caller claims to be police or a bank officer, says the person is in serious trouble, tells them not to tell anyone, and asks them to read out a one-time password (OTP). Most people have never rehearsed this, so the first real call is the first time they face it.

**Who it is for.** People most likely to receive these calls: parents, elderly relatives and first-time smartphone users, and the younger relatives who share the app with them.

**What the app does.** The user chooses English, Hindi or Bengali, and answers a simulated call. They talk back by voice. A fixed-script caller escalates, and at the OTP step the app shows a synthetic six-digit code on screen and the caller demands it. The user can refuse, hang up, ask questions, or read the code out. The debrief then lists the tactics used, marks which ones worked on the user, says what to do instead, and gives the 1930 helpline and cybercrime.gov.in.

**Scenarios.** "Digital arrest call": a parcel allegedly containing drugs, and the caller says the user is under digital arrest. "Suspicious transaction call": a debit has just been made, and the caller asks for the OTP to "cancel" it, when reading it out would actually approve the payment.

**Gnani models and APIs.** Prisma speech-to-text (model `prisma-v3.0`, `POST /stt/v3`) transcribes every user reply, with an explicit language code on each turn. Timbre text-to-speech (model `timbre-v2.5`, `POST /api/v1/tts/inference`) renders every caller and debrief line once, ahead of time. The few lines that use a practice name typed by the user are rendered live.

**How it works.** Microphone audio is converted to 16 kHz WAV with ffmpeg. A loudness check skips the speech-to-text call when the reply is silent. The transcript then goes through an OTP-leak check and a keyword intent classifier. The classifier sorts each reply into one of twelve kinds, such as going along, refusing, hanging up, asking who the caller is, asking for proof, asking what the call is about, stalling, or saying they are scared. It has per-language phrase lists, including mixed-script replies such as "verify कैसे करेंगे". A rule-based call graph picks the next fixed line and returns its pre-rendered clip. Questions get an in-character answer, and a caller who is pushed back on escalates with warnings, as real callers do.

**Design choices.** No live language model writes any caller dialogue, so every line can be reviewed before it is heard. The OTP-leak detector recognises Latin digits, Devanagari and Bengali digits, and spoken digit words. Every call screen says it is a simulation. All data is synthetic, and the OTP is random for each call. Abuse protection uses an invite code and configurable caps on turns and sessions.

**Limitations.** The Hindi and Bengali lines were machine-drafted from the English and still need native review. Some debrief facts, including the helpline details, are still being checked against official sources. Replies are understood by phrase rules, so an unusual phrasing can get the next scripted line instead of a direct answer. Sessions are held in memory, so it must run as a single instance.

**Next step.** Replace the phrase rules with Gnani's Evon v3.3 reasoning model, used only to classify what the user said, never to write the caller's lines. We looked into it: Evon is not on the API platform yet, and the 30B open weights need a GPU we did not have for this build.

## 2. Team and contributions

- [Member 1 name] — built the scenario engine and call graph, the intent classifier, the OTP-leak detector, the "Digital arrest call" scenario in English, Hindi and Bengali, the web frontend, and the automated test suite.
- [Member 2 name] — built the "Suspicious transaction call" scenario in English, Hindi and Bengali, the scenario picker, `.env` configuration, the reply-understanding improvements found in live testing (questions about the call, bank callbacks, mixed-script Hindi and Bengali), the audio pre-rendering for both scenarios, the public deployment, and this submission pack.

## 3. Demo video script (about 95 seconds)

Record from the deployed app over HTTPS, so the microphone works. Use English for the recording unless the Hindi lines have had native review. Keep the SIMULATION banner visible on every call screen.

| Time | Screen | Action and what to say |
|---|---|---|
| 0:00 to 0:08 | Landing page | Show the title and the SIMULATION banner. Say: "This is a simulation. The caller is scripted and all data is synthetic." |
| 0:08 to 0:18 | Language and scenario choice | Pick English, then "Digital arrest call" in the scenario picker. Say: "The app runs in English, Hindi and Bengali." |
| 0:18 to 0:28 | Answer call | Press "Answer call". Let the caller's first line play. Say: "The caller claims to be an officer and sounds urgent." |
| 0:28 to 0:38 | One question | Tap to speak and ask "Who are you?". Let the in-character reply play. Say: "Every caller line is a fixed, reviewed clip, not model output." |
| 0:38 to 0:48 | Refuse and hang up | Say: "I will not share any code. I am hanging up." Press hang up. |
| 0:48 to 0:56 | Second run | Press "Try again", pick "Suspicious transaction call", and press "Answer call". Let the caller escalate until the on-screen OTP is demanded. Point at the SIMULATION banner and the code. Say: "This code is random and synthetic." |
| 0:56 to 1:06 | Lose path | Read the on-screen code aloud to the microphone. The caller reacts and the call ends as a loss. Say: "This is what happens when the code is read out." |
| 1:06 to 1:24 | Debrief | Scroll through the tactics list. Point out the tactics marked as having worked, the "what to do instead" text, and the 1930 helpline and cybercrime.gov.in. Say: "Urgency, authority and secrecy are the signs. Hang up and call the bank or 1930 yourself." |
| 1:24 to 1:34 | Closing card (10 seconds) | Show the architecture card with the flow: mic, Prisma STT, intent rules, call graph, Timbre pre-rendered clips, debrief. Say: "Built on Gnani Prisma for speech-to-text and Timbre for text-to-speech. The caller's words are fixed and reviewed, and no live model writes them." |

## 4. Launch posts

### LinkedIn draft

Scam calls like "digital arrest" work through pressure. The caller says you are in serious trouble, tells you not to tell your family, and asks you to read out a one-time password. Most people have never rehearsed this, so the first real call is the first time they face it.

For the #GreatIndianAIInternshipChallenge, our team built a Scam Call Simulator with @Gnani AI. You answer a simulated call in English, Hindi or Bengali and talk back by voice. A scripted caller escalates and asks for an on-screen OTP. Refuse, or read it out and see what happens. A debrief shows which tactics were used, which ones worked on you, and what to do instead, with the 1930 helpline and cybercrime.gov.in.

Under the hood, Gnani Prisma transcribes each reply and Gnani Timbre renders the caller's lines ahead of time. A rule-based call graph chooses the next fixed line. No live model writes the scammer's words.

This is a simulation. The caller is scripted, the OTP is random, and all data is synthetic. Hindi and Bengali lines are still awaiting native review.

Try it: https://scam-call-simulator.onrender.com/
Code: https://github.com/rajatdas-cs/Scam-call-simulator

#GreatIndianAIInternshipChallenge #GnaniAI

### X / Twitter draft

Built a scam-call simulator for the #GreatIndianAIInternshipChallenge #GnaniAI with @Gnani AI. Talk back to a scripted "digital arrest" call, or read the fake OTP and see the debrief. Simulation, synthetic data. https://scam-call-simulator.onrender.com/ https://github.com/rajatdas-cs/Scam-call-simulator

## 5. Final checklist (in order)

- [ ] Native-speaker review of the Hindi and Bengali lines in `scenarios/*/lines/hi.json` and `scenarios/*/lines/bn.json`.
- [ ] Verify every UNVERIFIED row in `docs/SOURCES.md`: open the official page, record the date and what it says, and soften any claim the source does not support.
- [x] Pre-render audio for both scenarios and all languages (done 10 Nov: 270 clips).
- [ ] Deploy to Hugging Face Spaces (TEAMMATE.md section 8) with secrets `GNANI_API_KEY` and `INVITE_CODE`, and the `MAX_TURNS` and `MAX_SESSIONS_PER_HOUR` variables set.
- [ ] Test on a phone over HTTPS: microphone permission, both scenarios, win path, lose path, silence, and a question to the caller.
- [ ] Record the demo video from the deployed app, following section 3.
- [ ] Publish the LinkedIn and X posts with the real demo and repo links. Confirm they are public and live before submitting.
- [ ] Submit the form with the written explanation, team names, demo video link and post links.
