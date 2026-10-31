import math
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EmiCalculationResult(BaseModel):
    principal: float
    annual_interest_rate: float
    tenure_months: int
    monthly_emi: float
    monthly_emi_rounded: int
    total_interest: float
    total_amount_payable: float
    sample_label: str = "Sample"
    is_synthetic: bool = True
    disclaimer: str = (
        "Sample offer for illustrative purposes only. Actual interest rates and "
        "repayment terms are determined by lending partners."
    )
    amortization_sample: Optional[List[Dict[str, Any]]] = None


def calculate_emi(
    principal: float,
    annual_interest_rate: float,
    tenure_months: int,
    generate_schedule: bool = False,
) -> EmiCalculationResult:
    """
    Deterministically computes Equated Monthly Installment (EMI) for a loan.
    Formula:
        EMI = [P x r x (1+r)^n] / [(1+r)^n - 1]
    where:
        P = Principal loan amount
        r = Monthly interest rate (annual_rate / 12 / 100)
        n = Tenure in months
    """
    if principal <= 0:
        raise ValueError("Principal loan amount must be greater than zero.")
    if tenure_months <= 0:
        raise ValueError("Tenure in months must be greater than zero.")
    if annual_interest_rate < 0:
        raise ValueError("Annual interest rate cannot be negative.")

    if annual_interest_rate == 0.0:
        monthly_emi = principal / tenure_months
        total_amount = principal
        total_interest = 0.0
    else:
        monthly_rate = annual_interest_rate / (12.0 * 100.0)
        numerator = principal * monthly_rate * math.pow(1.0 + monthly_rate, tenure_months)
        denominator = math.pow(1.0 + monthly_rate, tenure_months) - 1.0
        monthly_emi = numerator / denominator
        total_amount = monthly_emi * tenure_months
        total_interest = total_amount - principal

    monthly_emi_rounded = int(round(monthly_emi))
    total_interest_rounded = round(total_interest, 2)
    total_amount_rounded = round(total_amount, 2)

    schedule = None
    if generate_schedule:
        schedule = []
        balance = principal
        monthly_rate = (annual_interest_rate / (12.0 * 100.0)) if annual_interest_rate > 0 else 0.0
        for m in range(1, tenure_months + 1):
            interest_component = balance * monthly_rate
            principal_component = monthly_emi - interest_component
            if balance < principal_component or m == tenure_months:
                principal_component = balance
                balance = 0.0
            else:
                balance -= principal_component

            schedule.append({
                "month": m,
                "emi": round(monthly_emi, 2),
                "principal": round(principal_component, 2),
                "interest": round(interest_component, 2),
                "remaining_balance": round(max(0.0, balance), 2),
            })

    return EmiCalculationResult(
        principal=round(principal, 2),
        annual_interest_rate=round(annual_interest_rate, 2),
        tenure_months=tenure_months,
        monthly_emi=round(monthly_emi, 2),
        monthly_emi_rounded=monthly_emi_rounded,
        total_interest=total_interest_rounded,
        total_amount_payable=total_amount_rounded,
        amortization_sample=schedule,
    )

