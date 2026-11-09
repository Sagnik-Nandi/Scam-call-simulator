# Factual claims in the app and where they come from

**Status key:** `UNVERIFIED` = taken from a search snippet or news coverage, the official page has NOT been opened and read yet.
Every claim shown to users (the `debrief.facts`, `debrief.help` and tactic text in `scenarios/*/lines/*.json`) must reach `VERIFIED` before release.
When verifying, record the date and what the page actually says.

| # | Claim in the app | Source to open and read | Status |
|---|---|---|---|
| 1 | Police, CBI, customs, ED and courts do not arrest people over a phone or video call | I4C/MHA advisory (covered by [Udayavani](https://udayavani.com/english-news/amid-rise-in-digital-arrest-cases-indian-cyber-crime-coordination-centre-issues-advisory-for-citizens), [India.com](https://www.india.com/technology/what-is-digital-arrest-mha-issues-advisory-dot-urges-citizens-to-ignore-fake-calls-6928496/)); find the primary MHA/I4C/PIB release | UNVERIFIED |
| 2 | "There is no such thing as a digital arrest" (wording in `facts[0]`) | Same as 1. If the official text does not say this, soften the sentence | UNVERIFIED |
| 3 | The typical hook is a parcel in your name containing drugs or fake passports | [MHA advisory coverage](https://www.newsx.com/national/mha-issues-warning-against-cyber-criminals-impersonating-government-agencies/) | UNVERIFIED |
| 4 | Scammers isolate victims ("do not tell anyone") and keep them on a long call | I4C advisory / MHA release | UNVERIFIED |
| 5 | The bank and the RBI never ask for OTP, PIN, CVV or password | [RBI Kehta Hai: fraud emails, calls and SMSs](https://website.rbi.org.in/web/rbi/rbi-kehta-hai/fraud-emails-calls-and-smses) | UNVERIFIED |
| 6 | Callers threaten to freeze or block accounts to pressure people into sharing OTPs | [RBI press release](https://website.rbi.org.in/web/rbi/-/press-releases/rbi-cautions-against-fraudulent-activities-in-its-name) | UNVERIFIED |
| 7 | Report with the 1930 helpline and cybercrime.gov.in | I4C / cybercrime.gov.in home page | UNVERIFIED |
| 8 | Government agencies do not use WhatsApp or Skype for official action | CERT-In / I4C statement (reported in coverage; find primary) | UNVERIFIED |
| 9 | Scammers often already know victims' names and details from leaked data, so knowing them proves nothing | Find an I4C/MHA/RBI awareness item that says this; otherwise soften or remove | UNVERIFIED |

## Do not use without a primary source
- Loss or case-count statistics seen in news coverage (for example "123,672 cases / Rs 1,935 crore in 2024"). Not verified. Not in the app.

## Language note
Hindi and Bengali lines are machine-drafted from the English base. They need a native reader to confirm tone and naturalness before release.
