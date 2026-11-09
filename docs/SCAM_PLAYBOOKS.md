# Scam playbooks: research for the next scenarios

Research only. Nothing here is built. Written 9 Nov 2026 for scenarios 1, 2, 5, 7, 8 from the shortlist.

**Verification status, read this first.** Most points come from search-result summaries of news and police pages, not from the official pages themselves.
- `READ` = the page was opened and read in full.
- `SNIPPET` = seen only as a search summary. Open it before any claim goes into the app.
- The RBI BE(A)WARE booklet could not be read by the fetch tool (both of its URLs redirected to the RBI home page). It is the best single source for scenarios 1, 2 and 5, so please open it in a browser and check the "KYC updation", "card" and "lottery / loan offers" sections. Search for "BE(A)WARE RBI booklet" on rbi.org.in.

## Tricks that repeat across all scams (the tactic list)

| Trick | Seen in | Status in our debrief |
|---|---|---|
| Fake authority (bank, police, government, company) | all | `authority` exists |
| Fear (account blocked, arrest, loss) | 1, 2, 7 | `fear` exists |
| Urgency / deadline | all | `urgency` exists |
| Secrecy / "do not tell anyone" | digital arrest, 7 | `secrecy` exists |
| False helper ("I am here to help you") | 1, 2, 5 | `false_help` exists |
| Asking for a credential (OTP, PIN, CVV) | 1, 2, 5 | `credential_request` exists |
| **Greed / too-good offer** (prize, points, refund) | 5, 8 | new: `greed` |
| **Small win, then bigger payments** | 8 (task scam, KBC) | new: `escalating_payments` |
| **"Click this link / install this app"** | 1, 5 | new: `install_app` |
| **Already knows your details** (builds trust) | 1, 2, 5 | covered by `ask_info` answer |
| **Emotional pressure on a loved one** | 7 | new: `emotional` |
| **Impersonating someone you know** | 7 | new: `impersonation` |

## 1. Bank KYC expiry or "account will be blocked"

**Story.** Caller says they are from the bank (or a "KYC department"). Your KYC has expired or the account has a problem, and it will be blocked today. They offer to fix it over the phone.
**Typical steps.** Name or a few real details to build trust, then the block threat, then "I will help you update it", then a request for an OTP or a link or app, then escalation if you hesitate.
**What they ask for.** OTP, card details, or to install an app.
**Evidence.**
- RBI says callers pose as officials from RBI, banks, government or couriers, threaten legal action or account freezing, and press people to share an OTP or install unverified apps. (RBI Kehta Hai and RBI press release; `SNIPPET`.)
- The RBI BE(A)WARE booklet is described as listing vishing calls that use KYC updating and unblocking an account or SIM as the pretext, and says the caller first shares a few customer details (name, date of birth) to build trust. (Secondary summaries; `SNIPPET`.)
- Key advice: banks and genuine entities never ask for a password, card details, CVV or OTP. (`SNIPPET`.)
**Fits our engine:** almost exactly. The soft-then-pressure flow is the same. New content: a block-the-account fear line instead of a parcel and a warrant.

## 2. "Suspicious transaction on your account"

**Story.** Caller (or a robo-call) says a debit of some amount has just been made. "If this was not you, I will cancel it, but I need the OTP that just came to your phone."
**Why it works.** The OTP the victim reads out is what approves a payment the fraudster has already started. It is the reverse of what the caller claims.
**Variants found.**
- Call merging: the caller asks you to merge another call, which is the bank's OTP call being joined to yours. NPCI warned about it. (Outlook Money / Business Standard coverage; `SNIPPET`.)
- Fabricated emergencies such as an unauthorised transaction or a suspended account. (Hyderabad cybercrime alert coverage; `SNIPPET`.)
- Telecom OTP-warning features are being introduced (Airtel). (News; `SNIPPET`.)
**Caution.** I found no RBI or NPCI document that describes this exact "share OTP to cancel" script, only general OTP guidance and the call-merging alert. Treat the script as realistic but not officially documented.
**Do not put in the app:** any rule about when a customer is not liable for a loss. Sources conflict on the time limits (24 hours, 3 working days).
**Fits our engine:** the simplest of all. Almost the same graph as digital arrest, with an amount and a merchant name in the lines.

## 5. Credit card reward points or limit increase

**Story.** "Your reward points will expire today. I can help you redeem them." Or "we can raise your credit limit."
**Typical steps.** Link or app (often on WhatsApp) to "claim" the points, the victim enters card details, then the OTPs arrive and the caller asks for them, sometimes several times.
**Cases reported.**
- A man gave OTPs five times before losing about 1.31 lakh (Free Press Journal; `SNIPPET`).
- A Hyderabad case where the caller sent a link, had the victim install an app and enter card details (cybercrime police warning coverage; `SNIPPET`).
- A High Court judge lost about 6 lakh in a similar scheme (news; `SNIPPET`).
- Police advisories also flag fake credit-limit-increase offers (Hyderabad, Telangana; `SNIPPET`).
**Advice repeated by banks and police:** verify by calling the bank's official number, never share CVV, PIN or OTP, install apps only from the official stores. (`SNIPPET`; an AU bank page was among the results.)
**What the engine needs:** the ending is not only "said the OTP". It can also be "said the card number or CVV" or "agreed to install the app". We would need a detector for a 16-digit card number and a 3-digit CVV (synthetic values shown on screen, like the practice OTP).

## 7. Family emergency ("Mom, I am in trouble")

**Story.** A voice that sounds like a relative, or a caller claiming that a relative has had an accident, been arrested or is in hospital, asks for money immediately, usually by UPI. "Do not tell Dad."
**Evidence.**
- The Tamil Nadu Cyber Crime Wing issued an advisory (April 2024) that fraudsters use AI voice cloning to imitate family members or friends, getting samples from social media or from a "wrong number" call, and urged people to verify identity before sending money. (Coverage by Inc42 and others; `SNIPPET`.)
- Scripts reported: accident, hospital, arrest, "pay now by UPI". (Blogs and news; `SNIPPET`, the blogs are weaker.)
- Common defences: a family safe word, hang up and call the relative back on a saved number, do not pay under pressure. (`SNIPPET`.)
**Important for us.**
- Not an OTP scam. The ending condition is "agrees to send money" or "shares UPI details". We need a new intent ("will pay") and amount detection.
- We must not clone a real person's voice. Use a generic voice for the "relative", and say clearly that the call is a simulation.
- Emotional content (a child in danger) needs care in tone. Keep it short and not graphic.

## 8. Lottery or prize, fake job, tax refund (three separate scripts)

**KBC lottery.** `READ` (Delhi Police page).
- Contact by WhatsApp from unknown numbers, many starting with +92.
- "You won 25 lakh in a KBC and Reliance Jio lottery." Contact the number in the message.
- First pay a "refundable" amount for "processing" and "GST, etc."
- After each payment they ask for more "on one pretext or another", and the prize amount is later raised (45 lakh, then 75 lakh).
- When the victim refuses, they stop calling and discontinue the numbers.
- Delhi Police advice: such a message is "in all likelihood a fraud". It exploits greed. A genuine lottery deducts tax from the prize, so paying in advance is a sign of fraud. A caller who insists on secrecy is a warning sign. Discuss with family and verify by other means.
- The page names no helpline, only the nearest police station.

**Part-time task or fake job scam.** (Kotak guide, search summary; `SNIPPET`.)
- Contact by SMS or WhatsApp about a part-time job, small early payouts, escalating tasks that need bigger deposits, then a demand for GST or tax before withdrawal. Victims are often moved to a Telegram group.

**Income-tax refund.** (A 2019 report; `SNIPPET`, old.)
- A link to a lookalike tax site that asks for login details.

**Fits our engine:** the ending is again "pays money" or "shares login details", so scenario 7 and scenario 8 can share the new "will pay" detection.

## What the engine would need (not built)

| Need | Used by | Effort |
|---|---|---|
| New tactic names with debrief text in 3 languages (`greed`, `escalating_payments`, `install_app`, `emotional`, `impersonation`) | 5, 7, 8 | small |
| Card number and CVV detector, synthetic card shown on screen | 5 | medium |
| "Agrees to pay or install" intent (keywords per language, amounts) | 5, 7, 8 | medium |
| A different ending rule: "paid" or "installed" instead of "said the OTP" | 5, 7, 8 | small |
| Scenario lines: about 25 per scenario per language, plus debrief text | all | the main work |
| Fact-checking each claim against an official page | all | ongoing |

## Suggested order
1. **Scenario 2 (suspicious transaction)** first: almost no new engine work, the most recognisable.
2. **Scenario 1 (KYC)** next: same engine, a different story. It could share most lines with scenario 2.
3. **Scenario 5 (card reward points)** after that: needs the card and install detection.
4. **Scenarios 7 and 8** last, because they need the payment ending and careful tone.

## Sources
- RBI Kehta Hai, fraud emails, calls and SMSs: https://website.rbi.org.in/web/rbi/rbi-kehta-hai/fraud-emails-calls-and-smses (`SNIPPET`)
- RBI press release, cautions against fraudulent activities in its name: https://website.rbi.org.in/web/rbi/-/press-releases/rbi-cautions-against-fraudulent-activities-in-its-name (`SNIPPET`)
- RBI BE(A)WARE booklet (7 March 2022): press release https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=53372 (could not be fetched; `UNREAD`)
- NPCI call-merging warning, covered by Outlook Money and Business Standard (`SNIPPET`)
- Delhi Police, KBC lottery frauds: https://cyber.delhipolice.gov.in/KBClottery.html (`READ`)
- Tamil Nadu Cyber Crime Wing voice-cloning advisory, covered by Inc42 (https://inc42.com/?p=454767) (`SNIPPET`)
- Credit card reward-point fraud coverage: Free Press Journal, Udayavani, Deccan Herald, AU Bank blog (`SNIPPET`)
- Kotak "fake jobs" safe-banking guide (`SNIPPET`)
