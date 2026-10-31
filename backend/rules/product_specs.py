from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.rules.emi import calculate_emi
from backend.rules.foir import calculate_foir
from backend.rules.sip import calculate_sip
from backend.state import CalculationResult


class FieldDefinition(BaseModel):
    name: str
    label: str
    unit: Optional[str] = None
    data_type: str = "float"  # float, int, str
    prompt_question: str
    hint: Optional[str] = None
    default_value: Optional[Any] = None
    why_we_ask: Optional[str] = None


class ProductSpec(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    journey_id: str
    title: str
    description: str
    category: str
    required_fields: List[str]
    optional_fields: List[str] = Field(default_factory=list)
    field_definitions: Dict[str, FieldDefinition]
    calculate_fn: Optional[Callable[[Dict[str, Any]], CalculationResult]] = None
    disclosures: List[str]
    consent_prompt_template: str
    sample_label: str = "Sample"


# ==============================================================================
# 1. PERSONAL LOAN JOURNEY
# ==============================================================================

def calculate_personal_loan_journey(data: Dict[str, Any]) -> CalculationResult:
    """
    Deterministic calculation for personal loan journey.
    """
    income = float(data.get("monthly_income", 0.0))
    amount = float(data.get("loan_amount", 0.0))
    tenure = int(data.get("tenure_months", 12))
    existing_emis = float(data.get("existing_emis", 0.0))

    # Deterministic synthetic interest rate rule based on income tier
    if income >= 75000:
        annual_rate = 11.5
    elif income >= 40000:
        annual_rate = 12.5
    else:
        annual_rate = 14.0

    # Deterministic EMI
    emi_res = calculate_emi(
        principal=amount,
        annual_interest_rate=annual_rate,
        tenure_months=tenure,
        generate_schedule=True,
    )

    # Deterministic FOIR
    foir_res = calculate_foir(
        monthly_income=income,
        existing_obligations=existing_emis,
        proposed_emi=emi_res.monthly_emi,
        max_foir_threshold_pct=50.0,
        annual_interest_rate=annual_rate,
        tenure_months=tenure,
    )

    metrics = {
        "monthly_income": income,
        "loan_amount": amount,
        "tenure_months": tenure,
        "annual_interest_rate": annual_rate,
        "monthly_emi": emi_res.monthly_emi,
        "monthly_emi_rounded": emi_res.monthly_emi_rounded,
        "total_interest": emi_res.total_interest,
        "total_amount_payable": emi_res.total_amount_payable,
        "existing_emis": existing_emis,
        "foir_percentage": foir_res.foir_percentage,
        "is_eligible": foir_res.is_eligible,
        "eligibility_status": foir_res.status_label,
        "max_allowable_emi": foir_res.max_allowable_emi,
        "max_eligible_loan_amount": foir_res.max_eligible_loan_amount,
        "excess_obligation": foir_res.excess_obligation,
    }

    disclosures = [
        "Sample offer for demonstration purposes only. All calculations and figures are synthetic.",
        "Final approval is subject to credit assessment and KYC verification by partnered lending institutions.",
        "Illustrative processing fee of up to 2% + GST may apply.",
    ]

    return CalculationResult(
        journey_id="personal_loan",
        sample_label="Sample",
        is_synthetic=True,
        disclosures=disclosures,
        metrics=metrics,
        schedule=emi_res.amortization_sample,
    )


PERSONAL_LOAN_SPEC = ProductSpec(
    journey_id="personal_loan",
    title="Paytm Personal Loan (Sample)",
    description="Instant personal loan eligibility and EMI calculation with FOIR risk assessment.",
    category="Lending",
    required_fields=["monthly_income", "loan_amount", "tenure_months", "existing_emis"],
    field_definitions={
        "monthly_income": FieldDefinition(
            name="monthly_income",
            label="Monthly Net Income",
            unit="₹",
            data_type="float",
            prompt_question="What is your net monthly take-home salary or income?",
            hint="e.g. 50,000 or 80k",
            why_we_ask="We use your income to verify loan eligibility and ensure your total debt stays safely within the 50% FOIR limit.",
        ),
        "loan_amount": FieldDefinition(
            name="loan_amount",
            label="Desired Loan Amount",
            unit="₹",
            data_type="float",
            prompt_question="How much loan amount do you need?",
            hint="e.g. 1.5 lakh, 80k, 28,000",
            why_we_ask="We need your requested loan amount to compute the exact monthly EMI and interest schedule for your offers.",
        ),
        "tenure_months": FieldDefinition(
            name="tenure_months",
            label="Loan Tenure",
            unit="months",
            data_type="int",
            prompt_question="What repayment tenure would you prefer in months or years?",
            hint="e.g. 12 months, 2 years, 24",
            why_we_ask="Tenure determines your monthly installment size and total interest payable over the loan duration.",
        ),
        "existing_emis": FieldDefinition(
            name="existing_emis",
            label="Existing Monthly EMIs",
            unit="₹",
            data_type="float",
            prompt_question="Do you currently pay any monthly EMIs or loan obligations? If none, please say zero.",
            hint="e.g. 5,000 or zero",
            default_value=None,
            why_we_ask="Existing debt obligations are required to calculate your Fixed Obligation to Income Ratio (FOIR) to prevent over-borrowing.",
        ),
    },
    calculate_fn=calculate_personal_loan_journey,
    disclosures=[
        "Sample offer for demonstration purposes only. All calculations and figures are synthetic.",
        "Final approval is subject to credit assessment and KYC verification by partnered lending institutions.",
        "Illustrative processing fee of up to 2% + GST may apply.",
    ],
    consent_prompt_template=(
        "Based on your inputs, your Sample loan offer is ₹{loan_amount:,.0f} for {tenure_months} months "
        "at {annual_interest_rate}% p.a., with an EMI of ₹{monthly_emi_rounded:,}/month. "
        "Do you provide explicit consent to submit this Sample application?"
    ),
)


# ==============================================================================
# 2. SIP (SYSTEMATIC INVESTMENT PLAN) JOURNEY
# ==============================================================================

def calculate_sip_journey(data: Dict[str, Any]) -> CalculationResult:
    """
    Deterministic calculation for SIP journey.
    """
    monthly_inv = float(data.get("monthly_investment", 0.0))
    duration_yrs = float(data.get("duration_years", 3.0))
    annual_return = float(data.get("expected_annual_return", 12.0))

    sip_res = calculate_sip(
        monthly_investment=monthly_inv,
        expected_annual_return=annual_return,
        duration_years=duration_yrs,
        generate_yearly_breakdown=True,
    )

    metrics = {
        "monthly_investment": monthly_inv,
        "expected_annual_return": annual_return,
        "duration_years": duration_yrs,
        "total_months": sip_res.total_months,
        "total_invested": sip_res.total_invested,
        "estimated_returns": sip_res.estimated_returns,
        "future_value": sip_res.future_value,
        "future_value_rounded": sip_res.future_value_rounded,
    }

    disclosures = [
        "Sample projection for illustrative purposes only. All calculations and figures are synthetic.",
        "Mutual fund investments are subject to market risks; read all scheme related documents carefully.",
        "Past performance is not indicative of future market returns.",
    ]

    return CalculationResult(
        journey_id="sip",
        sample_label="Sample",
        is_synthetic=True,
        disclosures=disclosures,
        metrics=metrics,
        schedule=sip_res.yearly_growth_sample,
    )


SIP_SPEC = ProductSpec(
    journey_id="sip",
    title="Paytm Wealth SIP (Sample)",
    description="Systematic Investment Plan growth projections and wealth compounding simulation.",
    category="Wealth",
    required_fields=["monthly_investment", "duration_years", "expected_annual_return"],
    field_definitions={
        "monthly_investment": FieldDefinition(
            name="monthly_investment",
            label="Monthly SIP Amount",
            unit="₹",
            data_type="float",
            prompt_question="How much would you like to invest monthly in this SIP?",
            hint="e.g. 5,000 or 10k",
            why_we_ask="Your monthly contribution defines how much principal will compound over time in the SIP.",
        ),
        "duration_years": FieldDefinition(
            name="duration_years",
            label="Investment Horizon",
            unit="years",
            data_type="float",
            prompt_question="For how many years do you plan to continue this investment?",
            hint="e.g. 3 years, 5 years, 10",
            why_we_ask="Investment horizon determines how compound interest multiplies wealth over your chosen time period.",
        ),
        "expected_annual_return": FieldDefinition(
            name="expected_annual_return",
            label="Expected Annual Return",
            unit="%",
            data_type="float",
            prompt_question="What expected annual return percentage would you like to benchmark? (Standard is 12%)",
            hint="e.g. 12%, 14 percent",
            default_value=12.0,
            why_we_ask="Expected benchmark return rate provides an illustrative simulation of mutual fund growth.",
        ),
    },
    calculate_fn=calculate_sip_journey,
    disclosures=[
        "Sample projection for illustrative purposes only. All calculations and figures are synthetic.",
        "Mutual fund investments are subject to market risks; read all scheme related documents carefully.",
        "Past performance is not indicative of future market returns.",
    ],
    consent_prompt_template=(
        "With a monthly SIP of ₹{monthly_investment:,.0f} over {duration_years} years at {expected_annual_return}% p.a., "
        "your projected Sample corpus is ₹{future_value_rounded:,} (Invested: ₹{total_invested:,.0f}, Gain: ₹{estimated_returns:,.0f}). "
        "Do you consent to schedule this Sample SIP investment mandate?"
    ),
)


# ==============================================================================
# 3. PAYMENT HELP JOURNEY
# ==============================================================================

def calculate_payment_help_journey(data: Dict[str, Any]) -> CalculationResult:
    """
    Deterministic resolution for payment help journey.
    """
    account_id = str(data.get("account_id", "PAYTM-LOAN-SAMPLE"))
    issue_type = str(data.get("issue_type", "payment_failed")).lower()
    amount_due = float(data.get("amount_due", 0.0))

    late_fee_waiver = 0.0
    grace_period_hours = 48
    restructured_emi = None

    if "bounce" in issue_type or "auto_debit" in issue_type:
        late_fee_waiver = 350.0  # Synthetic bounce charge waiver
        net_payable = max(0.0, amount_due)
        resolution_strategy = "Waive ₹350 auto-debit bounce charge with 48-hour re-payment window"
    elif "restructure" in issue_type or "hardship" in issue_type:
        # Extend tenure by 6 months, reducing EMI by 25%
        restructured_emi = round(amount_due * 0.75, 2)
        net_payable = restructured_emi
        resolution_strategy = "Hardship tenure extension: reduced monthly obligation by 25%"
    else:
        net_payable = amount_due
        resolution_strategy = "Instant payment reconciliation with instant clearance token"

    metrics = {
        "account_id": account_id,
        "issue_type": issue_type,
        "original_amount_due": amount_due,
        "late_fee_waiver": late_fee_waiver,
        "net_payable": net_payable,
        "grace_period_hours": grace_period_hours,
        "restructured_emi": restructured_emi,
        "resolution_strategy": resolution_strategy,
        "payment_token": f"SAMPLE-PAY-{abs(hash(account_id)) % 100000:05d}",
        "instant_pay_link": f"https://paytm.com/sample-pay/{account_id}",
    }

    disclosures = [
        "Sample resolution assistance for demonstration purposes only.",
        "Payment reconciliation is subject to inter-bank clearing cycles (NPCI/NACH).",
        "Waiver offers are synthetic and subject to partner NBFC policy.",
    ]

    return CalculationResult(
        journey_id="payment_help",
        sample_label="Sample",
        is_synthetic=True,
        disclosures=disclosures,
        metrics=metrics,
    )


PAYMENT_HELP_SPEC = ProductSpec(
    journey_id="payment_help",
    title="Paytm Payment & EMI Assistance (Sample)",
    description="Troubleshooting auto-debit failures, bounce charges, and loan repayment hardship.",
    category="Support",
    required_fields=["account_id", "issue_type", "amount_due"],
    field_definitions={
        "account_id": FieldDefinition(
            name="account_id",
            label="Loan / Account ID",
            data_type="str",
            prompt_question="Could you share your loan account number or registered mobile number?",
            hint="e.g. LOAN-1029 or 9876543210",
            why_we_ask="Your loan account number allows us to locate your specific transaction records and auto-debit status.",
        ),
        "issue_type": FieldDefinition(
            name="issue_type",
            label="Issue Category",
            data_type="str",
            prompt_question="What issue are you facing: payment failed, auto-debit bounce, or requesting EMI restructure?",
            hint="e.g. auto debit bounce, payment failed, restructure",
            why_we_ask="Knowing your exact issue lets us apply targeted resolutions like 48-hour auto-debit bounce charge waivers.",
        ),
        "amount_due": FieldDefinition(
            name="amount_due",
            label="Amount Due / Pending",
            unit="₹",
            data_type="float",
            prompt_question="What is the pending or overdue EMI amount?",
            hint="e.g. 4,500 or 5k",
            why_we_ask="Your pending amount ensures we calculate the exact net payable balance after fee waivers.",
        ),
    },
    calculate_fn=calculate_payment_help_journey,
    disclosures=[
        "Sample resolution assistance for demonstration purposes only.",
        "Payment reconciliation is subject to inter-bank clearing cycles (NPCI/NACH).",
        "Waiver offers are synthetic and subject to partner NBFC policy.",
    ],
    consent_prompt_template=(
        "We have generated a Sample resolution for Account {account_id}: {resolution_strategy}. "
        "Net payable is ₹{net_payable:,.2f} with {grace_period_hours}h grace period. "
        "Do you give consent to apply this Sample resolution and generate your payment token?"
    ),
)


# ==============================================================================
# 4. LOAN REJECTION JOURNEY
# ==============================================================================

def calculate_loan_rejection_journey(data: Dict[str, Any]) -> CalculationResult:
    """
    Deterministic recovery plan calculation for loan rejection.
    """
    app_id = str(data.get("application_id", "APP-SAMPLE"))
    reason = str(data.get("rejection_reason_code", "HIGH_FOIR")).upper()
    current_val = float(data.get("current_score_or_foir", 65.0))

    cooling_off_days = 90
    reapply_date = (datetime.now(timezone.utc) + timedelta(days=cooling_off_days)).strftime("%d-%b-%Y")

    action_steps = []
    target_metric = ""

    if "FOIR" in reason or current_val <= 100:  # FOIR percentage context
        target_metric = "Reduce FOIR below 45% (Current: {:.1f}%)".format(current_val)
        excess_pct = max(0.0, current_val - 45.0)
        action_steps = [
            f"Pre-close or foreclose high-cost active credit lines to shave {excess_pct:.1f}% off your debt ratio.",
            "Avoid applying for new personal loans or credit cards during the 90-day cooling period.",
            "Add a co-applicant or guarantor with stable monthly income when re-applying.",
        ]
    else:  # Credit Score context (e.g. 640)
        target_metric = "Improve CIBIL score to 720+ (Current: {:.0f})".format(current_val)
        action_steps = [
            "Ensure 100% on-time repayment of existing credit card dues and EMIs for 3 consecutive billing cycles.",
            "Keep overall credit card utilization below 30% of total limit.",
            "Dispute any incorrect overdue remarks or reporting inaccuracies on your CIBIL report.",
        ]

    metrics = {
        "application_id": app_id,
        "rejection_reason_code": reason,
        "current_score_or_foir": current_val,
        "cooling_off_days": cooling_off_days,
        "reapply_eligible_date": reapply_date,
        "target_metric": target_metric,
        "action_steps": action_steps,
    }

    disclosures = [
        "Sample advisory for illustrative credit improvement. Non-binding synthetic analysis.",
        "Credit scores are independently maintained by credit information companies (CIBIL/Experian).",
        "Re-application does not guarantee automated approval.",
    ]

    return CalculationResult(
        journey_id="loan_rejection",
        sample_label="Sample",
        is_synthetic=True,
        disclosures=disclosures,
        metrics=metrics,
    )


LOAN_REJECTION_SPEC = ProductSpec(
    journey_id="loan_rejection",
    title="Paytm Credit Recovery & Re-application (Sample)",
    description="Transparent root-cause explanation and 90-day cooling-off recovery roadmap.",
    category="Underwriting",
    required_fields=["application_id", "rejection_reason_code", "current_score_or_foir"],
    field_definitions={
        "application_id": FieldDefinition(
            name="application_id",
            label="Previous Application ID",
            data_type="str",
            prompt_question="Please enter or speak your previous loan application number.",
            hint="e.g. APP-8271",
            why_we_ask="Your previous application ID links directly to the underwriting evaluation record to determine root causes.",
        ),
        "rejection_reason_code": FieldDefinition(
            name="rejection_reason_code",
            label="Decline Reason",
            data_type="str",
            prompt_question="What reason was indicated: high obligations (HIGH_FOIR) or low credit score (LOW_CREDIT_SCORE)?",
            hint="e.g. HIGH_FOIR or LOW_CREDIT_SCORE",
            why_we_ask="Knowing why the application was declined lets us generate a targeted 90-day recovery roadmap.",
        ),
        "current_score_or_foir": FieldDefinition(
            name="current_score_or_foir",
            label="Current FOIR (%) or Credit Score",
            unit="",
            data_type="float",
            prompt_question="What is your current FOIR percentage (e.g. 62%) or CIBIL score (e.g. 640)?",
            hint="e.g. 62 or 640",
            why_we_ask="Your current score or debt ratio helps us simulate what-if scenarios to reach approval criteria.",
        ),
    },
    calculate_fn=calculate_loan_rejection_journey,
    disclosures=[
        "Sample advisory for illustrative credit improvement. Non-binding synthetic analysis.",
        "Credit scores are independently maintained by credit information companies (CIBIL/Experian).",
        "Re-application does not guarantee automated approval.",
    ],
    consent_prompt_template=(
        "We have charted your Sample recovery roadmap to re-apply on {reapply_eligible_date}: {target_metric}. "
        "Do you consent to enroll in this Sample 90-day credit improvement milestone plan?"
    ),
)


# Registry of all journeys
PRODUCT_SPECS: Dict[str, ProductSpec] = {
    "personal_loan": PERSONAL_LOAN_SPEC,
    "sip": SIP_SPEC,
    "payment_help": PAYMENT_HELP_SPEC,
    "loan_rejection": LOAN_REJECTION_SPEC,
}


def get_product_spec(journey_id: str) -> Optional[ProductSpec]:
    return PRODUCT_SPECS.get(journey_id)
