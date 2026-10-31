import pytest
from backend.planner import (
    initialize_journey,
    plan_next_step,
    submit_journey_application,
)
from backend.rules.product_specs import get_product_spec
from backend.state import FieldStatus, JourneyStatus


def test_planner_asks_only_next_missing_field():
    spec = get_product_spec("personal_loan")
    assert spec is not None

    state = initialize_journey(session_id="test_sess_01", journey_id="personal_loan")
    assert state.status == JourneyStatus.COLLECTING

    # Step 1: Initial call asks for first missing required field: 'monthly_income'
    step1 = plan_next_step(state=state, user_input=None, spec=spec)
    assert step1.next_action == "ask_field"
    assert step1.target_field == "monthly_income"
    assert "income" in step1.prompt_message.lower()

    # Step 2: User answers with "80k" -> confirmed, now asks for next missing: 'loan_amount'
    step2 = plan_next_step(state=state, user_input="80k", spec=spec)
    assert state.fields["monthly_income"].value == 80000.0
    assert state.fields["monthly_income"].status == FieldStatus.CONFIRMED
    assert step2.next_action == "ask_field"
    assert step2.target_field == "loan_amount"
    assert "loan amount" in step2.prompt_message.lower()

    # Step 3: User answers with "1.5 lakh" -> confirmed, now asks for next missing: 'tenure_months'
    step3 = plan_next_step(state=state, user_input="1.5 lakh", spec=spec)
    assert state.fields["loan_amount"].value == 150000.0
    assert state.fields["loan_amount"].status == FieldStatus.CONFIRMED
    assert step3.next_action == "ask_field"
    assert step3.target_field == "tenure_months"
    assert "tenure" in step3.prompt_message.lower()

    # Step 4: User answers with "2 years" -> parsed as 24 months, now asks for: 'existing_emis'
    step4 = plan_next_step(state=state, user_input="2 years", spec=spec)
    assert state.fields["tenure_months"].value == 24
    assert step4.next_action == "ask_field"
    assert step4.target_field == "existing_emis"

    # Step 5: User answers "0" or "zero" for existing emis
    step5 = plan_next_step(state=state, user_input="zero", spec=spec)
    assert state.fields["existing_emis"].value == 0.0

    # All required fields are now filled! Next action MUST be request_consent
    assert step5.next_action == "request_consent"
    assert state.status == JourneyStatus.AWAITING_CONSENT
    assert step5.calculation is not None
    assert step5.calculation.sample_label == "Sample"
    assert step5.calculation.is_synthetic is True
    assert "consent" in step5.prompt_message.lower()


def test_no_submission_without_explicit_consent():
    state = initialize_journey(session_id="test_sess_consent", journey_id="personal_loan")
    spec = get_product_spec("personal_loan")

    # Fast-fill all fields
    plan_next_step(state, "80k", spec)
    plan_next_step(state, "1.5 lakh", spec)
    plan_next_step(state, "12 months", spec)
    step = plan_next_step(state, "0", spec)

    assert state.status == JourneyStatus.AWAITING_CONSENT
    assert state.consent.granted is False

    # Principle: No submission without explicit consent!
    with pytest.raises(PermissionError, match="explicit user consent is required"):
        submit_journey_application(state)

    # User explicitly declines
    plan_next_step(state, "No, not ready yet", spec)
    assert state.consent.granted is False
    assert state.status == JourneyStatus.COLLECTING

    # Attempting to submit again must still fail
    with pytest.raises(PermissionError):
        submit_journey_application(state)

    # Return to awaiting consent
    step_calc = plan_next_step(state, None, spec)
    assert state.status == JourneyStatus.AWAITING_CONSENT

    # User provides explicit consent
    step_submit = plan_next_step(state, "Yes, I agree", spec)
    assert state.consent.granted is True
    assert state.status == JourneyStatus.SUBMITTED
    assert step_submit.next_action == "submitted"

    # Now submission succeeds cleanly
    submission = submit_journey_application(state)
    assert submission["status"] == "success"
    assert submission["is_sample"] is True
    assert "SAMPLE-PAYTM-" in submission["sample_reference_id"]


def test_sip_journey_planner():
    state = initialize_journey(session_id="test_sip_01", journey_id="sip")
    spec = get_product_spec("sip")

    # Step 1: ask monthly_investment
    s1 = plan_next_step(state, None, spec)
    assert s1.target_field == "monthly_investment"

    # Step 2: user enters 5000 -> ask duration_years
    s2 = plan_next_step(state, "5000", spec)
    assert s2.target_field == "duration_years"

    # Step 3: user enters 3 years -> expected_annual_return has default 12.0
    # but let's confirm or let default apply
    s3 = plan_next_step(state, "3 years", spec)
    # If expected_annual_return has default_value, it's already INFERRED
    # Check if calculation is triggered
    assert state.status == JourneyStatus.AWAITING_CONSENT
    assert state.calculation is not None
    assert state.calculation.metrics["monthly_investment"] == 5000.0
    assert state.calculation.metrics["duration_years"] == 3.0
    assert state.calculation.sample_label == "Sample"


def test_payment_help_journey_planner():
    state = initialize_journey(session_id="test_pay_help_01", journey_id="payment_help")
    spec = get_product_spec("payment_help")

    # Step 1: ask account_id
    s1 = plan_next_step(state, None, spec)
    assert s1.target_field == "account_id"

    # Step 2: enter loan ID -> ask issue_type
    s2 = plan_next_step(state, "LOAN-8891", spec)
    assert s2.target_field == "issue_type"

    # Step 3: enter issue -> ask amount_due
    s3 = plan_next_step(state, "auto debit bounce", spec)
    assert s3.target_field == "amount_due"

    # Step 4: enter amount 4,500
    s4 = plan_next_step(state, "4,500", spec)
    assert state.status == JourneyStatus.AWAITING_CONSENT
    assert state.calculation.metrics["late_fee_waiver"] == 350.0
    assert state.calculation.metrics["net_payable"] == 4500.0


def test_loan_rejection_journey_planner():
    state = initialize_journey(session_id="test_rej_01", journey_id="loan_rejection")
    spec = get_product_spec("loan_rejection")

    # Step 1: ask application_id
    s1 = plan_next_step(state, None, spec)
    assert s1.target_field == "application_id"

    # Step 2: enter APP-9921 -> ask rejection_reason_code
    s2 = plan_next_step(state, "APP-9921", spec)
    assert s2.target_field == "rejection_reason_code"

    # Step 3: enter HIGH_FOIR -> ask current_score_or_foir
    s3 = plan_next_step(state, "high foir debt", spec)
    assert s3.target_field == "current_score_or_foir"

    # Step 4: enter 62%
    s4 = plan_next_step(state, "62%", spec)
    assert state.status == JourneyStatus.AWAITING_CONSENT
    assert state.calculation.metrics["cooling_off_days"] == 90
    assert "Reduce FOIR below 45%" in state.calculation.metrics["target_metric"]
