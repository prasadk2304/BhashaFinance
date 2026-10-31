# Private review handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add language-correct voice, a least-data document-review stage, and a masked human-review handoff to the existing BhashaFinance demo journeys.

**Architecture:** A pure backend privacy boundary redacts recognised identifiers before message persistence and LLM calls. The existing planner gains a consented document-review stage, while SQLite holds only masked review packets and material-request statuses. The current mobile shell renders the masked preview, voice read-back, readiness factors, and human-review status.

**Tech Stack:** FastAPI, Pydantic, SQLite, Sarvam TTS/STT, Next.js/React, TypeScript, Vitest, pytest.

**Spec:** `docs/superpowers/specs/2026-10-31-private-review-handoff-design.md`

## Global Constraints

- All data remains synthetic/demo-only; do not add real document upload, storage, verification, payments, disbursal, or investment execution.
- Never send or persist raw PAN, Aadhaar, mobile, DOB, bank account, account/application IDs, or document text to an LLM, message history, state JSON, or review packet.
- Show only deterministic, explanatory `Ready for human review`, `Needs supporting material`, or `Affordability needs human review` outcomes—never a lending confidence percentage, sanction, or RBI eligibility claim.
- Consent must disclose its purpose, require explicit affirmative action, record method/time/redacted text, and allow decline.
- Keep the active BCP-47 language on session creation and every turn; TTS and browser fallback must use it.
- Reuse the current mobile design tokens and ensure fixed controls clear the bottom tab bar.

## Review Focus

- PAN/Aadhaar/mobile/DOB/bank/account identifier embedded within an ordinary voice transcript must be absent from LLM input and state JSON; covered by Task 1.
- A false affirmative such as “I will think about it” must not create consent/review case; covered by Task 2.
- Payment-help/credit-recovery must not unexpectedly request KYC material; covered by Task 2.
- A `hi-IN` or `mr-IN` session initial prompt and a later response must carry the same language into its audio request; covered by Task 3.
- A reviewer request for material not on the original checklist must show a customer-visible explicit request without exposing raw identifiers; covered by Task 4.

---

### Task 1: Server-side privacy boundary

**Files:**
- Create: `backend/privacy.py`
- Create: `backend/tests/test_privacy.py`
- Modify: `backend/llm/service.py`
- Modify: `backend/main.py`

**Interfaces:**
- Produces `RedactedInput(text: str, previews: dict[str, str], detected_types: set[str])` and `redact_sensitive_text(text: str) -> RedactedInput`.
- `LLMService.extract_with_fallback` consumes only an already-redacted transcript.
- `main.py` consumes `RedactedInput` before LLM extraction, `MessageEntry` creation, and `save_state`.

- [ ] **Step 1: Write failing privacy tests**

```python
def test_redacts_pan_aadhaar_mobile_dob_bank_and_account_identifiers():
    result = redact_sensitive_text("PAN ABCDE1234F, Aadhaar 1234 5678 9012, DOB 01/02/1990")
    assert "ABCDE1234F" not in result.text
    assert result.previews["pan"] == "ABCDE****F"

@pytest.mark.anyio
async def test_turn_persists_and_sends_redacted_voice_text_only(...):
    ...
```

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m pytest backend/tests/test_privacy.py -q`  
Expected: FAIL because `backend.privacy` does not exist.

- [ ] **Step 3: Implement deterministic redaction and input boundary**

Implement the module without any external service. In `main.py`, retain only redacted user/assistant content in state, pass redacted text to the LLM service, and do not log raw input. Do not add a reversible token map.

- [ ] **Step 4: Run Task 1 tests to verify GREEN**

Run: `python -m pytest backend/tests/test_privacy.py -q`  
Expected: PASS.

### Task 2: Document-review planner and masked review persistence

**Files:**
- Modify: `backend/state.py`
- Modify: `backend/planner.py`
- Modify: `backend/rules/product_specs.py`
- Modify: `backend/database.py`
- Modify: `backend/main.py`
- Create: `backend/tests/test_document_review.py`

**Interfaces:**
- Consumes `RedactedInput.previews` from Task 1 and existing `JourneyState`/`ConsentState`.
- Produces `DocumentChecklistItem`, `ReviewCase`, `ReviewStatus`, `build_readiness_result(state)`, `create_review_case`, and `request_review_material`.
- `TurnResponse` adds `review_case` only after the document-review stage.

- [ ] **Step 1: Write failing planner/database tests**

```python
def test_personal_loan_consent_moves_to_document_review_with_masked_checklist(): ...
def test_sip_has_kyc_and_mandate_checklist_but_payment_help_has_no_kyc_documents(): ...
def test_review_case_requires_explicit_document_handoff_consent_and_stores_masked_packet_only(): ...
def test_reviewer_material_request_becomes_customer_action(): ...
```

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m pytest backend/tests/test_document_review.py -q`  
Expected: FAIL because document-review models and review-case APIs do not exist.

- [ ] **Step 3: Implement the least-data review state machine**

Add declarative document requirements to product specs. After the existing illustrative-result consent, prompt for document readiness and a purpose-labeled human-review handoff consent. Store only masked previews/booleans, calculate transparent readiness from existing deterministic metrics and checklist completion, and preserve the existing payment-help/recovery flow.

- [ ] **Step 4: Run Task 2 tests to verify GREEN**

Run: `python -m pytest backend/tests/test_document_review.py -q`  
Expected: PASS.

### Task 3: Session language propagation and language-correct speech

**Files:**
- Modify: `backend/state.py`
- Modify: `backend/main.py`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/app/page.tsx`
- Modify: `frontend/src/components/ConversationPanel.tsx`
- Create: `backend/tests/test_session_language.py`

**Interfaces:**
- `CreateSessionRequest.language_code: Optional[str]` is validated and saved as `JourneyState.language_code`.
- `createSession(journeyId, customerId, languageCode)` sends it to `/sessions`.
- Every backend TTS call uses the state language; browser `SpeechSynthesisUtterance.lang` receives the same code.

- [ ] **Step 1: Write failing language tests**

```python
@pytest.mark.anyio
async def test_hindi_session_tts_uses_hindi_for_initial_and_followup_reply(...): ...

@pytest.mark.anyio
async def test_marathi_session_tts_uses_marathi_for_initial_and_followup_reply(...): ...
```

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m pytest backend/tests/test_session_language.py -q`  
Expected: FAIL because session creation ignores `language_code`.

- [ ] **Step 3: Implement session-language propagation**

Validate language once at session creation, persist it, use it for initial/reply/read-back/review-status TTS, and pass frontend selected language to `createSession`. Keep explicit per-turn language validation for compatibility.

- [ ] **Step 4: Run Task 3 tests to verify GREEN**

Run: `python -m pytest backend/tests/test_session_language.py -q`  
Expected: PASS.

### Task 4: Mobile masked-preview and review status UI

**Files:**
- Create: `frontend/src/components/ReviewReadinessCard.tsx`
- Modify: `frontend/src/app/page.tsx`
- Modify: `frontend/src/app/globals.css`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/types/index.ts`
- Create: `frontend/src/components/ReviewReadinessCard.test.tsx`

**Interfaces:**
- Consumes `ReviewCase` returned by Task 2 and `languageCode` from Task 3.
- Produces `ReviewReadinessCard` with masked fields, “Read details”, consent/submit controls, review status, and requested material.
- Customer actions call existing/new typed review endpoints; no raw identifier input or document upload UI is added.

- [ ] **Step 1: Write failing component tests**

```tsx
it("renders masked preview and never renders raw identifiers", () => { ... })
it("reads only the masked preview using the selected language", () => { ... })
it("shows a human material request as an actionable item", () => { ... })
```

- [ ] **Step 2: Run tests to verify RED**

Run: `npm test -- ReviewReadinessCard.test.tsx`  
Expected: FAIL because `ReviewReadinessCard` does not exist.

- [ ] **Step 3: Implement the mobile review surface**

Use existing card/button styles; show purpose and demo status; call TTS only with constructed masked text. Integrate it inside the journey screen above the existing handoff control. Keep one primary action and tab-bar clearance.

- [ ] **Step 4: Run Task 4 tests to verify GREEN**

Run: `npm test -- ReviewReadinessCard.test.tsx`  
Expected: PASS.

### Task 5: Regression verification

**Files:**
- Modify: relevant tests only if an integration contract uncovered by Tasks 1–4 needs coverage.

**Interfaces:**
- Consumes all prior task APIs.
- Produces evidence that the existing journeys, safety boundary, language voice path, frontend build, and lint remain compatible.

- [ ] **Step 1: Add a failing end-to-end test only if no prior test covers a contract boundary**

Use a FastAPI ASGI test to create a Marathi personal-loan session, complete its illustrative inputs, verify redacted state, create a review case, and retrieve a customer material request.

- [ ] **Step 2: Run it to verify RED/GREEN as applicable**

Run: `python -m pytest backend/tests/test_endpoints_and_rag.py backend/tests/test_document_review.py backend/tests/test_session_language.py -q`.

- [ ] **Step 3: Run complete verification**

Run:

```powershell
python -m pytest backend/tests -q
npm test -- --run
npm run lint
npm run build
```

Expected: all selected suites/build/lint exit 0. Record unrelated pre-existing failures separately rather than hiding them.

## Self-review

- Spec coverage: Tasks 1–4 cover the privacy boundary, product-specific review path, human request loop, language TTS, and mobile preview. Task 5 ties them together.
- Type consistency: backend `ReviewCase` is the sole review payload returned through `TurnResponse`; frontend uses that typed shape. `JourneyState.language_code` is the server source of truth.
- Review focus: each of the five listed risks has a named test task.
- Proportion: the plan names interfaces and test contracts without dictating implementation internals.
