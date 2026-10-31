import math
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SipCalculationResult(BaseModel):
    monthly_investment: float
    expected_annual_return: float
    duration_years: float
    total_months: int
    total_invested: float
    estimated_returns: float  # wealth gain
    future_value: float
    future_value_rounded: int
    sample_label: str = "Sample"
    is_synthetic: bool = True
    disclaimer: str = (
        "Sample projection for illustrative purposes only. Mutual fund investments "
        "are subject to market risks; read all scheme related documents carefully."
    )
    yearly_growth_sample: Optional[List[Dict[str, Any]]] = None


def calculate_sip(
    monthly_investment: float,
    expected_annual_return: float,
    duration_years: float,
    generate_yearly_breakdown: bool = False,
) -> SipCalculationResult:
    """
    Deterministically computes Future Value (FV) of a monthly Systematic Investment Plan (SIP).
    Formula:
        FV = P * [((1 + i)^n - 1) / i] * (1 + i)
    where:
        P = Monthly investment amount
        i = Monthly rate of return (annual_return / 12 / 100)
        n = Total number of monthly installments (duration_years * 12)
    """
    if monthly_investment <= 0:
        raise ValueError("Monthly investment amount must be greater than zero.")
    if duration_years <= 0:
        raise ValueError("Investment duration in years must be greater than zero.")
    if expected_annual_return < 0:
        raise ValueError("Expected annual return rate cannot be negative.")

    total_months = int(round(duration_years * 12))
    if total_months <= 0:
        raise ValueError("Total duration must translate to at least 1 month.")

    total_invested = monthly_investment * total_months

    if expected_annual_return == 0.0:
        future_value = total_invested
        estimated_returns = 0.0
    else:
        monthly_rate = expected_annual_return / (12.0 * 100.0)
        compound_factor = math.pow(1.0 + monthly_rate, total_months)
        future_value = monthly_investment * ((compound_factor - 1.0) / monthly_rate) * (1.0 + monthly_rate)
        estimated_returns = future_value - total_invested

    yearly_growth = None
    if generate_yearly_breakdown:
        yearly_growth = []
        max_years = int(math.ceil(duration_years))
        monthly_rate = (expected_annual_return / (12.0 * 100.0)) if expected_annual_return > 0 else 0.0
        for y in range(1, max_years + 1):
            m_count = min(y * 12, total_months)
            invested_so_far = monthly_investment * m_count
            if expected_annual_return == 0.0:
                fv_so_far = invested_so_far
            else:
                cf = math.pow(1.0 + monthly_rate, m_count)
                fv_so_far = monthly_investment * ((cf - 1.0) / monthly_rate) * (1.0 + monthly_rate)
            yearly_growth.append({
                "year": y,
                "months": m_count,
                "invested_amount": round(invested_so_far, 2),
                "wealth_gain": round(fv_so_far - invested_so_far, 2),
                "projected_corpus": round(fv_so_far, 2),
            })

    return SipCalculationResult(
        monthly_investment=round(monthly_investment, 2),
        expected_annual_return=round(expected_annual_return, 2),
        duration_years=round(duration_years, 2),
        total_months=total_months,
        total_invested=round(total_invested, 2),
        estimated_returns=round(estimated_returns, 2),
        future_value=round(future_value, 2),
        future_value_rounded=int(round(future_value)),
        yearly_growth_sample=yearly_growth,
    )
