# Private review handoff design

## Intent

BhashaFinance will keep its Marathi/Hindi/English voice replies in the user-selected language, then extend an existing journey with a privacy-first document-readiness and human-review handoff. The goal is a clear demo of what a customer may need next, what they consent to share, and when a human reviewer must decide—not automated lending or investment approval.

## Goals

- Synthesize every assistant reply in the active `mr-IN`, `hi-IN`, or `en-IN` session language.
- After a customer explicitly accepts an illustrative journey outcome, show a product-specific materials checklist and purpose for every item.
- Accept typed or spoken confirmation that the displayed, **masked** preview is correct and that the customer consents to a human-review handoff.
- Prevent raw PAN, Aadhaar, mobile number, bank-account number, DOB, account identifiers, and raw document text from being sent to Sarvam/Ollama or written to message/state/audit logs.
- Create a demo review case that exposes only a masked, purpose-limited packet to the in-app human-review queue.
- Allow a demo reviewer to request a named missing item; surface that request in the customer journey.
- Show a transparent, deterministic **illustrative readiness** result for personal/car/home/gold loan categories. It is not a credit score, confidence percentage, sanction decision, or a statement of RBI eligibility.

## Non-goals

- No real underwriting, loan sanction, investment advice, KYC, Aadhaar/PAN verification, bureau pull, bank-statement upload, mandate execution, payment, or disbursal.
- No storage, display, or transmission of unmasked identifiers in this demo.
- No claim that RBI determines a single document checklist or approves a specific customer. Lending policy and final decisions remain with the regulated entity and authorised human reviewers.
- No general-purpose document OCR or passing documents to an LLM.

## Compliance boundary

The flow will request only need-based information, disclose a specific purpose before consent, record the consent method/time, let the customer decline, and create an auditable handoff record. This mirrors relevant safeguards in RBI’s Digital Lending Guidelines but is a demo implementation, not a compliance certification. The app will continue to label all calculations and outputs as Sample / illustrative.

## Approaches considered

1. Synthetic document-only demo: easy and safe, but does not prove the redaction boundary for typed/spoken identifiers.
2. Secure real-document vault: requires identity/KYC vendors, encryption/key management, Indian data-residency controls, retention/deletion procedures, authentication/authorisation, and a regulated-entity operating model. It is out of scope for this repository.
3. **Strict least-data review workflow (chosen):** a backend redaction gate recognises sensitive values locally; LLM calls receive only opaque placeholders and derived, non-sensitive facts. Persisted state and human-review packets contain only masked previews and document-completeness statuses. This proves the privacy boundary without pretending to collect real documents.

## Journey behaviour

### Language-correct voice

`CreateSessionRequest` and each turn will carry the validated language. The backend will retain it per session and pass it to TTS for the initial prompt, subsequent replies, read-backs, consent confirmation, and human-review status. Browser speech fallback will use the same language code.

### Sensitive-data gate

A pure backend redaction module will:

- recognise PAN, Aadhaar (including spaced/hyphenated forms), Indian mobile numbers, bank-account-like digit sequences, DOB/date patterns, and supported account/application IDs;
- substitute stable placeholders such as `[PAN_REDACTED]` and create an associated masked preview (`ABCDE****F`, `XXXX XXXX 1234`, `••••4521`, `••-••-1990`);
- send only the redacted string to LLM extraction/explanation;
- ensure user messages and persisted `JourneyState` retain the redacted form; and
- reject raw document payloads in the demo rather than attempting to store them.

Deterministic parsers may use a value momentarily in memory only to create a masked preview or boolean/document status. No reversible mapping is persisted or sent to an LLM.

### Product checklists

After the existing deterministic calculation and its first explicit illustrative-offer consent, the planner moves to `document_review` rather than direct submission.

- Personal/car/home/gold loan: identity/KYC status, PAN preview, DOB preview, six-month bank-statement availability, and product-appropriate collateral/income evidence status.
- SIP: KYC/PAN availability, bank-mandate readiness, and risk-disclosure acknowledgement. It remains an illustrative projection, not a recommendation or execution instruction.
- Payment help and credit-recovery: do not request identity documents; collect only issue-specific evidence/statuses where necessary.

The screen will say why each item is requested and whether it is missing, ready, or awaiting reviewer clarification. It will not assert that the checklist is an RBI-prescribed list.

### Preview, read-back, and consent

The customer sees only masked values plus document readiness. “Read details” sends the masked preview through TTS in the active language. The customer can edit a status, decline, or explicitly confirm using voice/text/button. The consent record includes a purpose string, method, timestamp, and redacted confirmation text.

### Illustrative readiness and human review

The deterministic rules engine produces one of:

- `Ready for human review`
- `Needs supporting material`
- `Affordability needs human review`

It lists the factors used (for example, declared income/obligations and materials completeness), so no opaque confidence percentage is presented. The submission creates a `ReviewCase` in SQLite with masked packet, consent audit reference, checklist, readiness factors, and `pending` status. The existing handoff modal becomes a customer-safe status screen; a small demo reviewer control can request a named material. That request is persisted and appears on the customer’s journey as an action needed.

## Architecture and files

- `backend/privacy.py`: deterministic detection, masking, redaction, and request-safe DTO helpers; no network calls.
- `backend/state.py`: language, document checklist, review state, and consent-purpose models.
- `backend/planner.py` and `backend/rules/product_specs.py`: add staged document review after illustrative consent and product-specific document metadata.
- `backend/database.py`: `review_cases` and `review_requests` tables; save/query masked packets only.
- `backend/main.py`: carry language on session creation; redact all inputs before LLM/message persistence; create/retrieve review cases; accept demo reviewer material requests.
- `backend/llm/*`: accept already-redacted content only; retain no raw prompt logging.
- `frontend/src/lib/api.ts`, `frontend/src/types/index.ts`: typed language/review APIs.
- `frontend/src/app/page.tsx` plus focused components: masked preview/read-back, consent, illustrative readiness, customer review status, and a clearly labelled demo reviewer request surface.
- `frontend/src/components/ConversationPanel.tsx`: language-correct browser fallback speech and replay.

## Tests and acceptance criteria

- A Marathi and Hindi session receives an initial and follow-up audio response synthesized with its own session language.
- PAN, Aadhaar, mobile, DOB, bank-account and account-ID samples are redacted before `SarvamProvider.extract`; raw values are absent from stored session JSON and the review packet.
- A personal-loan acceptance transitions to document review; SIP asks only its checklist; payment help does not ask for KYC documents.
- A masked preview can be read aloud and only an explicit confirmation creates a review case.
- The review case shows deterministic illustrative readiness factors, never a credit approval/confidence claim.
- A reviewer material request reaches the customer as an actionable missing item.
- Existing lending, SIP, payment-help, voice-router, consent, frontend build and lint checks remain green.

## Remaining production work outside this demo

Before any real user data is accepted: regulated-entity ownership and policy approval; verified KYC/bureau/bank data integrations; encryption and key management; India-resident storage and retention/deletion controls; authenticated role-based reviewer console; consent/privacy notices; security and legal review; KFS/APR/cooling-off and grievance workflows as applicable.
