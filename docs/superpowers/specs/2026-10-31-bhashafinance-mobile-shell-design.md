# BhashaFinance Mobile Shell Design

## Intent

Redesign BhashaFinance AI as a mobile-first experience for the synthetic demo user, while preserving every existing backend call, state transition, journey component, and current UI action. The app must make the four financial journeys and voice assistance easier to use at 375px and 420px without reducing the existing demo capabilities.

## Goals

- Render the application inside a 420px maximum-width, 100dvh mobile frame that centers on desktop and is full-width on phones.
- Use five primary destinations: Home, Journeys, Voice, Activity, and Profile.
- Preserve the current product catalog, seeded demo scenarios, language selection, demo reset, ledger, agent handoff, transcript review, inferred-value confirmation, consent flow, ticket creation, interactive journey studios, TTS playback, and API integration.
- Create a synthetic, masking-safe demo-user data source and local session consent preferences.
- Meet the prescribed visual system, accessibility requirements, and safe-area/tab-bar spacing.

## Non-goals

- Do not change API contracts, FastAPI business logic, calculation rules, mock customer records, LLM prompts, or RAG behavior.
- Do not add journeys, new financial decisions, authentication, persistence beyond browser session state, or real customer data.
- Do not surface unmasked personal identifiers or send profile identifiers to an LLM.

## Chosen Approach

Use a five-tab shell for top-level navigation. Existing controls remain available where their outcome is relevant instead of being moved into a global overflow menu:

- Home retains demo scenario access and Demo Reset through a compact utility row or contextual entry while surfacing quick starts and resume.
- Journeys owns product selection and opens the existing state panel/studio as a full-screen detail with a back action and sticky action area above the tab bar.
- Voice owns recording, TTS response playback, editable transcription, inferred-amount read-back, citations, and type fallback in a modal bottom sheet.
- Activity owns the current customer ledger; failed and pending transactions can begin a prefilled payment-help journey.
- Profile owns masked demo identity, consent preferences, language preference, version, and demo-data deletion confirmation.
- Agent handoff remains reachable during an active journey and payment-help context. Consent, ticket creation, and interactive studio actions remain within the active journey.

### Alternatives Considered

1. **Chosen: contextual action placement in the five-tab shell.** Keeps primary paths visible and makes mobile navigation predictable without losing existing controls.
2. **Rejected: persistent global overflow menu.** Fits more controls at the top level but hides important actions and weakens the intended screen hierarchy.

## Information Architecture

### Shared shell

- Neutral `#F5F7FA` desktop surround; white app UI inside a maximum 420px frame.
- `min-height: 100dvh`, safe-area padding on relevant edges, scrollable content, and a fixed white tab bar with no content overlap.
- A simple per-screen header uses a title and language chip, defaulting to `mr-IN`.
- Active tab uses navy icon/label and blue indicator dot. The Voice control is a raised 56px navy circular button, white mic icon, and 4px page-color ring.

### Home

- Greets the first name from `demoUser`.
- Shows Resume only when `activeSession` exists, including field-derived progress, next target field/action, and Continue.
- Shows all four journey starts in a 2×2 quick-action grid.
- Calculates a synthetic monthly spare-money insight from the existing mock ledger only when transaction-history consent is enabled; otherwise uses the requested sharing prompt.
- Shows three recent activity rows based on the loaded ledger/current session.
- Retains seeded demo scenario selection and reset access without introducing a separate feature.

### Journeys and journey detail

- Lists all four products as full-width cards with their existing title, description, required information, and Start action.
- Journey detail reuses `ConversationPanel`, `JourneyStatePanel`, all four existing studio components, consent controls, ticket flow, transaction selection, and handoff modal.
- A back arrow returns to Journeys. Any primary journey action stays sticky above the tab bar and safe area.

### Voice

- Opens as a full-height bottom sheet above the tab bar.
- Reuses the existing audio handling and conversation state. It displays language, mic state, live transcript field, state chips, assistant message, replay control, citations, type fallback, and close handle.
- Listening has a 1-second blue-ring pulse, disabled under reduced motion. `aria-live` announces voice state.
- Inferred values use the existing Yes/Edit/Resubmit flow in a compact confirmation card.

### Activity

- Uses `fetchCustomerTransactions` data, grouped by date with merchant/description, tabular amount, and status badge.
- Failed and pending rows show a detail state with Get help; this starts the existing payment-help journey and pre-populates it from the selected transaction.
- Ledger-derived content is consent-gated with an empty/share-data state.

### Profile

- Uses only one static synthetic `demoUser` record with pre-masked values: masked mobile, PAN `ABCDE****F`, Aadhaar `XXXX XXXX 1234`, and linked bank ending `4521`.
- Displays Demo profile, verified-demo rows, KYC, sample credit score band/note, consent toggles, language preference, delete-demo-data dialog, and app version.
- Consent preferences are React session state persisted through `sessionStorage`; clearing demo data removes that local session state and returns the app to the clean home state.

## Visual and Accessibility System

- Use Inter, 16px base, 12–13px caption styles, 8px layout spacing, 16px-radius border cards, 48px controls, 12px-radius buttons, no gradients, decorative illustrations, glass, or shadows on cards.
- Use only: navy `#002E6E`, blue `#00BAF2`, text `#1B2A41`, muted `#475569`, page `#F5F7FA`, card `#FFFFFF`, border `#E1E8F0`, blue tint `#E6F7FD`, navy tint `#E8EEF6`, success `#1E8E5A`, warning `#B7791F`, danger `#C0392B`.
- Icon-only controls have aria labels; all interactive states have visible focus outlines; status is expressed with text and color; money uses tabular figures.
- Each screen/list has loading, empty, and error states. Transitions last 150–200ms; the sheet slides upward without bounce.

## Files and Boundaries

- `frontend/src/app/page.tsx`: shell navigation and composition only; retains API/state orchestration.
- `frontend/src/lib/demoUser.ts`: masked synthetic identity and session preference helpers.
- `frontend/src/components/mobile/*`: shared shell, tab bar, header, home, journeys, activity, profile, and voice-sheet presentation components.
- Existing `ConversationPanel`, `JourneyStatePanel`, studio components, transaction and handoff modals remain functional and are styled/wrapped rather than replaced at the business-logic layer.
- `frontend/src/app/globals.css`: tokens, safe-area, mobile-frame, focus, loading, and reduced-motion rules.

## Validation

- Build with `npm run build` without lint errors.
- Verify keyboard navigation and tab-bar/sticky-action spacing at 375px, 420px, and desktop centered-frame widths.
- Verify all existing journey calls, consent, ticket, handoff, scenario, reset, language, ledger, voice fallback, and inferred-value actions remain reachable.
- Verify profile data stays masked and transaction-dependent UI responds to disabled consent.
