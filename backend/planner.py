import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.rules.parser import (
    extract_all_amounts,
    parse_amount,
    parse_percentage,
    parse_tenure_months,
)
from backend.rules.product_specs import ProductSpec, get_product_spec
from backend.state import (
    CalculationResult,
    ConsentState,
    Field as StateField,
    FieldSource,
    FieldStatus,
    JourneyState,
    JourneyStatus,
    MessageEntry,
)

CONSENT_AFFIRMATIVE_TERMS = {
    "yes", "y", "agree", "i agree", "consent", "i consent", "submit",
    "proceed", "confirm", "confirmed", "haan", "ha", "theek hai",
    "sahi hai", "accept", "approved", "ok", "okay", "sure", "done",
    "continue", "go ahead"
}

CONSENT_NEGATIVE_TERMS = {
    "no", "n", "disagree", "reject", "cancel", "nahi", "na", "stop",
    "abort", "change", "edit", "not now"
}


class PlannerStepResult(BaseModel):
    state: JourneyState
    next_action: str  # "ask_field" | "request_consent" | "submitted" | "completed" | "clarify"
    target_field: Optional[str] = None
    prompt_message: str
    calculation: Optional[CalculationResult] = None
    is_sample: bool = True


def initialize_journey(session_id: str, journey_id: str) -> JourneyState:
    """
    Initializes a new journey state based on the ProductSpec.
    All required fields start with status=MISSING.
    """
    spec = get_product_spec(journey_id)
    if not spec:
        raise ValueError(f"Unknown journey_id: {journey_id}")

    fields: Dict[str, StateField] = {}
    for name, f_def in spec.field_definitions.items():
        if f_def.default_value is not None:
            # Default values are marked INFERRED, not missing
            fields[name] = StateField(
                name=name,
                value=f_def.default_value,
                status=FieldStatus.INFERRED,
                source=FieldSource.DEFAULT,
                label=f_def.label,
                unit=f_def.unit,
                prompt_question=f_def.prompt_question,
            )
        else:
            fields[name] = StateField(
                name=name,
                value=None,
                status=FieldStatus.MISSING,
                source=FieldSource.DEFAULT,
                label=f_def.label,
                unit=f_def.unit,
                prompt_question=f_def.prompt_question,
            )

    state = JourneyState(
        session_id=session_id,
        journey_id=journey_id,
        status=JourneyStatus.COLLECTING,
        fields=fields,
    )
    return state


def detect_consent_intent(text: str) -> Optional[bool]:
    """
    Deterministically detects whether text expresses affirmative or negative consent.
    """
    cleaned = re.sub(r"[^\w\s]", "", text.lower()).strip()
    words = cleaned.split()

    # Exact or phrase check
    if cleaned in CONSENT_AFFIRMATIVE_TERMS:
        return True
    if cleaned in CONSENT_NEGATIVE_TERMS:
        return False

    # Check any matching affirmative word
    for word in words:
        if word in CONSENT_AFFIRMATIVE_TERMS:
            return True
        if word in CONSENT_NEGATIVE_TERMS:
            return False

    return None


def extract_field_with_regex(field_name: str, text: str, spec: ProductSpec) -> Optional[Any]:
    """
    Deterministic regex parser tailored to the targeted field before invoking LLM.
    """
    f_def = spec.field_definitions.get(field_name)
    if not f_def:
        return None

    # Tenure fields
    if "tenure" in field_name or f_def.unit in ("months", "years"):
        months = parse_tenure_months(text)
        if months is not None:
            if f_def.unit == "years":
                return round(months / 12.0, 1)
            return months

    # Percentage fields
    if "return" in field_name or "rate" in field_name or f_def.unit == "%":
        pct = parse_percentage(text)
        if pct is not None:
            return pct

    # Amount fields (income, loan_amount, investment, emis, amount_due)
    if f_def.unit == "₹" or "amount" in field_name or "income" in field_name or "emi" in field_name:
        amt = parse_amount(text)
        if amt is not None:
            return amt

    # Issue type or code strings
    if field_name == "issue_type":
        lower = text.lower()
        if "bounce" in lower or "debit" in lower:
            return "auto_debit_bounce"
        if "restructure" in lower or "hardship" in lower:
            return "hardship_restructure"
        if "fail" in lower or "error" in lower or "declined" in lower:
            return "payment_failed"
        return text.strip()

    if field_name == "rejection_reason_code":
        lower = text.lower()
        if "foir" in lower or "obligation" in lower or "debt" in lower:
            return "HIGH_FOIR"
        if "score" in lower or "cibil" in lower or "credit" in lower:
            return "LOW_CREDIT_SCORE"
        return text.strip().upper()

    # Generic string or numeric fallback
    if f_def.data_type == "str":
        return text.strip()
    elif f_def.data_type in ("float", "int"):
        parsed = parse_amount(text)
        if parsed is not None:
            return int(parsed) if f_def.data_type == "int" else parsed

    return None


def plan_next_step(
    state: JourneyState,
    user_input: Optional[str] = None,
    spec: Optional[ProductSpec] = None,
) -> PlannerStepResult:
    """
    Generic Planner logic:
    1. If currently AWAITING_CONSENT: check for explicit consent.
    2. If user_input provided in COLLECTING: parse input for the active missing field.
    3. Ask ONLY for the next missing required field.
    4. Once all required fields are satisfied: run deterministic calculation and transition to AWAITING_CONSENT.
    5. Enforce: No submission without explicit consent.
    """
    if spec is None:
        spec = get_product_spec(state.journey_id)
        if not spec:
            raise ValueError(f"No ProductSpec found for {state.journey_id}")

    if user_input:
        state.messages.append(MessageEntry(sender="user", text=user_input))

    # -------------------------------------------------------------------------
    # Case 1: Currently Awaiting Consent
    # -------------------------------------------------------------------------
    if state.status == JourneyStatus.AWAITING_CONSENT:
        if user_input:
            consent_decision = detect_consent_intent(user_input)
            if consent_decision is True:
                state.consent.grant(text=user_input, method="user_input")
                state.status = JourneyStatus.SUBMITTED
                msg = (
                    f"Sample {spec.title} submitted successfully! Your synthetic reference "
                    f"tracking ID is SAMPLE-PAYTM-{abs(hash(state.session_id)) % 1000000:06d}. "
                    "Thank you for reviewing this Sample offer."
                )
                state.messages.append(MessageEntry(sender="assistant", text=msg))
                return PlannerStepResult(
                    state=state,
                    next_action="submitted",
                    prompt_message=msg,
                    calculation=state.calculation,
                )
            elif consent_decision is False:
                state.consent.revoke()
                state.status = JourneyStatus.COLLECTING
                msg = (
                    "You did not provide consent for this Sample application. "
                    "Which field would you like to update (e.g. amount, tenure)?"
                )
                state.messages.append(MessageEntry(sender="assistant", text=msg))
                return PlannerStepResult(
                    state=state,
                    next_action="clarify",
                    prompt_message=msg,
                    calculation=state.calculation,
                )
            else:
                # Ambiguous answer; reiterate consent requirement
                msg = (
                    "To proceed, explicit consent is required. Please say or type 'I agree' "
                    "to submit this Sample offer, or 'No' to cancel or modify."
                )
                state.messages.append(MessageEntry(sender="assistant", text=msg))
                return PlannerStepResult(
                    state=state,
                    next_action="request_consent",
                    prompt_message=msg,
                    calculation=state.calculation,
                )
        else:
            # Re-prompt consent template
            msg = spec.consent_prompt_template.format(**(state.calculation.metrics if state.calculation else {}))
            return PlannerStepResult(
                state=state,
                next_action="request_consent",
                prompt_message=msg,
                calculation=state.calculation,
            )

    # -------------------------------------------------------------------------
    # Case 2: In COLLECTING state - Parse input if provided
    # -------------------------------------------------------------------------
    missing_fields = state.get_missing_required_fields(spec.required_fields)

    if user_input and missing_fields:
        target_name = missing_fields[0]
        extracted_value = extract_field_with_regex(target_name, user_input, spec)

        if extracted_value is not None:
            f_def = spec.field_definitions.get(target_name)
            state.set_field(
                name=target_name,
                value=extracted_value,
                status=FieldStatus.CONFIRMED,
                source=FieldSource.REGEX_PARSER,
                label=f_def.label if f_def else None,
                unit=f_def.unit if f_def else None,
                prompt_question=f_def.prompt_question if f_def else None,
            )
            # Re-evaluate missing fields after setting
            missing_fields = state.get_missing_required_fields(spec.required_fields)

    # -------------------------------------------------------------------------
    # Case 3: Still missing required fields -> Ask ONLY for the next missing field
    # -------------------------------------------------------------------------
    if missing_fields:
        next_missing = missing_fields[0]
        f_def = spec.field_definitions[next_missing]
        prompt = f_def.prompt_question
        if f_def.hint:
            prompt += f" ({f_def.hint})"

        state.messages.append(MessageEntry(sender="assistant", text=prompt))
        return PlannerStepResult(
            state=state,
            next_action="ask_field",
            target_field=next_missing,
            prompt_message=prompt,
        )

    # -------------------------------------------------------------------------
    # Case 4: All required fields present -> Run deterministic calculate_fn
    # -------------------------------------------------------------------------
    if spec.calculate_fn:
        calc_result = spec.calculate_fn(state.to_values_dict())
        state.calculation = calc_result
    else:
        calc_result = CalculationResult(
            journey_id=spec.journey_id,
            sample_label="Sample",
            is_synthetic=True,
            disclosures=spec.disclosures,
            metrics=state.to_values_dict(),
        )
        state.calculation = calc_result

    state.status = JourneyStatus.AWAITING_CONSENT

    # Format consent prompt template with metrics
    try:
        consent_prompt = spec.consent_prompt_template.format(**calc_result.metrics)
    except KeyError:
        consent_prompt = f"Please confirm your Sample {spec.title} submission. Do you agree?"

    # Append disclosure note
    consent_prompt += f"\n\n[Sample Disclosure]: {spec.disclosures[0]}"

    state.messages.append(MessageEntry(sender="assistant", text=consent_prompt))

    return PlannerStepResult(
        state=state,
        next_action="request_consent",
        prompt_message=consent_prompt,
        calculation=calc_result,
    )


def submit_journey_application(state: JourneyState) -> Dict[str, Any]:
    """
    Submits a journey application.
    Rule: No submission without explicit consent!
    """
    if not state.can_submit() and state.status != JourneyStatus.SUBMITTED:
        raise PermissionError("Submission rejected: explicit user consent is required before submission.")

    return {
        "status": "success",
        "sample_reference_id": f"SAMPLE-PAYTM-{abs(hash(state.session_id)) % 1000000:06d}",
        "journey_id": state.journey_id,
        "is_sample": True,
        "is_synthetic": True,
        "consent": state.consent.model_dump(),
        "metrics": state.calculation.metrics if state.calculation else {},
        "disclosures": state.calculation.disclosures if state.calculation else [],
    }
