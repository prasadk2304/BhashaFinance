import math
from typing import Optional
from pydantic import BaseModel, Field


class FoirCalculationResult(BaseModel):
    monthly_income: float
    existing_obligations: float
    proposed_emi: float
    max_foir_threshold_pct: float
    foir_percentage: float
    max_allowable_total_obligation: float
    max_allowable_emi: float
    is_eligible: bool
    status_label: str  # "Eligible" | "FOIR Exceeded" | "Overleveraged"
    excess_obligation: float
    max_eligible_loan_amount: Optional[float] = None
    sample_label: str = "Sample"
    is_synthetic: bool = True
    disclaimer: str = (
        "Sample assessment for illustrative purposes only. Final credit underwriting "
        "rules and debt-to-income limits vary across lending partners."
    )


def calculate_foir(
    monthly_income: float,
    existing_obligations: float = 0.0,
    proposed_emi: float = 0.0,
    max_foir_threshold_pct: float = 50.0,
    annual_interest_rate: Optional[float] = None,
    tenure_months: Optional[int] = None,
) -> FoirCalculationResult:
    """
    Deterministically computes Fixed Obligation to Income Ratio (FOIR).
    Formula:
        FOIR (%) = [(Existing Obligations + Proposed EMI) / Monthly Net Income] * 100
    """
    if monthly_income <= 0:
        raise ValueError("Monthly income must be greater than zero.")
    if existing_obligations < 0:
        raise ValueError("Existing obligations cannot be negative.")
    if proposed_emi < 0:
        raise ValueError("Proposed EMI cannot be negative.")
    if max_foir_threshold_pct <= 0 or max_foir_threshold_pct > 100:
        raise ValueError("FOIR threshold percentage must be between 0 and 100.")

    total_obligation = existing_obligations + proposed_emi
    foir_percentage = (total_obligation / monthly_income) * 100.0

    max_allowable_total_obligation = monthly_income * (max_foir_threshold_pct / 100.0)
    max_allowable_emi = max(0.0, max_allowable_total_obligation - existing_obligations)
    is_eligible = foir_percentage <= max_foir_threshold_pct

    excess_obligation = max(0.0, total_obligation - max_allowable_total_obligation)

    if is_eligible:
        status_label = "Eligible"
    elif existing_obligations >= max_allowable_total_obligation:
        status_label = "Overleveraged"
    else:
        status_label = "FOIR Exceeded"

    max_eligible_loan: Optional[float] = None
    if annual_interest_rate is not None and tenure_months is not None and tenure_months > 0:
        if max_allowable_emi <= 0:
            max_eligible_loan = 0.0
        elif annual_interest_rate == 0:
            max_eligible_loan = round(max_allowable_emi * tenure_months, 2)
        else:
            r = annual_interest_rate / (12.0 * 100.0)
            comp = math.pow(1.0 + r, tenure_months)
            p_max = (max_allowable_emi * (comp - 1.0)) / (r * comp)
            max_eligible_loan = round(max(0.0, p_max), 2)

    return FoirCalculationResult(
        monthly_income=round(monthly_income, 2),
        existing_obligations=round(existing_obligations, 2),
        proposed_emi=round(proposed_emi, 2),
        max_foir_threshold_pct=round(max_foir_threshold_pct, 2),
        foir_percentage=round(foir_percentage, 2),
        max_allowable_total_obligation=round(max_allowable_total_obligation, 2),
        max_allowable_emi=round(max_allowable_emi, 2),
        is_eligible=is_eligible,
        status_label=status_label,
        excess_obligation=round(excess_obligation, 2),
        max_eligible_loan_amount=max_eligible_loan,
    )
