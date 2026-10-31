# BhashaFinance Mobile Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the existing desktop-oriented BhashaFinance layout with the approved mobile-first five-tab shell while preserving all existing backend integration and journey behavior.

**Architecture:** Keep `page.tsx` as the state/API coordinator and move screen layout into focused `mobile` components. Existing conversation, state, studio, transaction, and handoff components remain the behavior layer, rendered within the mobile routes/sheet. A small client-only profile module holds only masked synthetic user data and session-scoped consent preferences.

**Tech Stack:** Next.js 14, React 18, TypeScript, Tailwind CSS, Lucide React; existing FastAPI API client.

**Spec:** `docs/superpowers/specs/2026-10-31-bhashafinance-mobile-shell-design.md`

## Global Constraints

- Preserve all existing API calls, application state, journeys, calculations, and existing control paths.
- Use a maximum 420px centered frame, `100dvh`, safe-area insets, scrollable content, and a fixed tab bar that never overlays actions.
- Implement exactly Home, Journeys, Voice, Activity, and Profile; do not add product features.
- Never display or transmit unmasked synthetic identifiers; the profile module holds only masked values.
- Use the specified colors, Inter, 8px spacing, 16px-radius cards, 48px actions, Lucide-only icons, accessible focus/ARIA states, and reduced motion.
- `npm run build` and `npm run lint` must pass.

## Review Focus

- A session is absent: Home uses a clear new-user state rather than attempting to resume undefined state.
- Transaction consent is off: Activity and insight UI show sharing guidance and never expose ledger-derived values.
- A failed/pending transaction is selected: Payment help starts with the known account/amount rather than a raw identifier leaking to voice/LLM paths.
- A voice turn returns a 503: the sheet keeps the typed fallback visible and announces a calm status.
- At 375px and 420px: fixed navigation and sticky journey actions leave all controls fully tappable above safe-area padding.

---

### Task 1: Mobile design primitives and masked demo-user state

**Files:**
- Create: `frontend/src/lib/demoUser.ts`
- Create: `frontend/src/components/mobile/MobileShell.tsx`
- Modify: `frontend/src/app/globals.css`
- Test: `frontend/src/lib/demoUser.test.ts` (using the selected frontend test runner)

**Interfaces:**
- Produces `DEMO_USER`, `DemoConsentPreferences`, and session-safe preference read/write helpers.
- Produces `MobileShell({ activeTab, onTabChange, children, onVoiceOpen })` for every later mobile screen.

- [ ] Write failing tests proving demo values are masked and default consent enables transaction history/bank data.
- [ ] Run the tests and verify they fail because the module is absent.
- [ ] Implement the masked demo user and safe session-storage helpers; implement the shell with nav-safe content padding, five tabs, button labels, and reduced-motion/safe-area styles.
- [ ] Run unit tests and `npm run build` to verify green compilation.
- [ ] Commit `feat: add mobile shell foundations`.

### Task 2: Home and Journeys screens

**Files:**
- Create: `frontend/src/components/mobile/HomeScreen.tsx`
- Create: `frontend/src/components/mobile/JourneysScreen.tsx`
- Modify: `frontend/src/app/page.tsx`
- Modify: `frontend/src/components/StartScreen.tsx` only if product-card presentation reuse is practical

**Interfaces:**
- Consumes `Product[]`, `TurnResponse | null`, mock `Transaction[]`, and `DemoConsentPreferences`.
- Produces callbacks `onStartJourney(journeyId)`, `onContinue()`, `onLoadScenario(journeyId)`, and `onReset()` consumed by `page.tsx`.

- [ ] Write failing component tests for resume visibility and consent-gated spare-money copy.
- [ ] Run the tests and verify the missing components fail as expected.
- [ ] Implement the Home greeting/resume/quick-action/insight/activity states and Journeys full-width product cards with required fields and Start actions; preserve scenario/reset utilities contextually.
- [ ] Run component tests and `npm run build`.
- [ ] Commit `feat: add home and journeys mobile screens`.

### Task 3: Mobile journey detail and voice sheet

**Files:**
- Create: `frontend/src/components/mobile/JourneyDetailScreen.tsx`
- Create: `frontend/src/components/mobile/VoiceSheet.tsx`
- Modify: `frontend/src/app/page.tsx`
- Modify: `frontend/src/components/ConversationPanel.tsx` only for reusable presentational hooks/props

**Interfaces:**
- Consumes the existing `TurnResponse`, sending/consent/ticket/handoff callbacks, and `VoiceSheet` receives existing audio/text handlers and calm notice state.
- Produces back-navigation to Journeys and a controlled `isVoiceSheetOpen` state.

- [ ] Write failing tests for sheet aria-live status, type fallback, and inferred amount confirmation display.
- [ ] Run the tests and verify expected failures before implementation.
- [ ] Wrap existing conversation/state/studio behavior in full-screen mobile journey detail; add a sheet that renders the existing mic/text/transcript/replay/citation/read-back behavior without duplicating API logic.
- [ ] Run relevant tests and `npm run build`; manually check at 375px and 420px.
- [ ] Commit `feat: add mobile journey detail and voice sheet`.

### Task 4: Activity and Profile screens

**Files:**
- Create: `frontend/src/components/mobile/ActivityScreen.tsx`
- Create: `frontend/src/components/mobile/ProfileScreen.tsx`
- Modify: `frontend/src/app/page.tsx`
- Modify: `frontend/src/types/index.ts` only for local presentation types if required

**Interfaces:**
- Consumes existing transactions/customer id and `DemoConsentPreferences`.
- Produces `onGetHelp(transaction)` and preference/delete handlers in `page.tsx`.

- [ ] Write failing tests proving transaction grouping/status rendering and consent-off empty guidance; add tests for masked profile data and preference changes.
- [ ] Run the tests to verify they fail before implementation.
- [ ] Implement grouped activity/details/get-help prefill and profile identity/KYC/sample score/consent/language/delete dialog/version states.
- [ ] Run tests and `npm run build`.
- [ ] Commit `feat: add activity and profile mobile screens`.

### Task 5: Responsive/accessibility polish and verification

**Files:**
- Modify: `frontend/src/app/globals.css`
- Modify: all Task 1–4 mobile components only as verification requires

**Interfaces:**
- Consumes the completed shell and screen components; preserves every existing callback.

- [ ] Write failing focused tests for tab labels, keyboard-visible focus, and tab-bar/sticky-action spacing class contracts.
- [ ] Run them to verify failure.
- [ ] Implement final loading/empty/error states, focus-visible and reduced-motion support, exact color/spacing compliance, and mobile safe-area spacing.
- [ ] Run the full frontend test command, `npm run lint`, and `npm run build`; inspect the running app at 375px, 420px, and desktop frame widths.
- [ ] Commit `feat: finalize mobile-first BhashaFinance UI`.
