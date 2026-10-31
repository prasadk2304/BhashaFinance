import pytest
from backend.rules.emi import calculate_emi, EmiCalculationResult


def test_standard_emi_calculation():
    # ₹1,00,000 loan at 12% annual interest for 12 months
    # Formula: r = 0.01, (1.01)^12 = 1.12682503
    # EMI = 100000 * 0.01 * 1.12682503 / 0.12682503 = 8884.878...
    result = calculate_emi(principal=100000, annual_interest_rate=12.0, tenure_months=12)

    assert isinstance(result, EmiCalculationResult)
    assert result.principal == 100000.0
    assert result.annual_interest_rate == 12.0
    assert result.tenure_months == 12
    assert result.monthly_emi_rounded == 8885
    assert pytest.approx(result.monthly_emi, 0.01) == 8884.88
    assert pytest.approx(result.total_amount_payable, 0.1) == 106618.55
    assert pytest.approx(result.total_interest, 0.1) == 6618.55
    assert result.sample_label == "Sample"
    assert result.is_synthetic is True


def test_zero_interest_rate_emi():
    # ₹60,000 at 0% for 6 months -> EMI = 10,000
    result = calculate_emi(principal=60000, annual_interest_rate=0.0, tenure_months=6)

    assert result.monthly_emi == 10000.0
    assert result.monthly_emi_rounded == 10000
    assert result.total_interest == 0.0
    assert result.total_amount_payable == 60000.0


def test_tenure_variations():
    # ₹5,00,000 loan at 10.5% for 36 months (3 years)
    result_36m = calculate_emi(principal=500000, annual_interest_rate=10.5, tenure_months=36)
    assert result_36m.monthly_emi_rounded == 16251

    # ₹5,00,000 loan at 10.5% for 60 months (5 years)
    result_60m = calculate_emi(principal=500000, annual_interest_rate=10.5, tenure_months=60)
    assert result_60m.monthly_emi_rounded == 10747
    assert result_60m.monthly_emi < result_36m.monthly_emi
    assert result_60m.total_interest > result_36m.total_interest


def test_amortization_schedule_consistency():
    principal = 50000
    rate = 14.0
    tenure = 6
    result = calculate_emi(principal=principal, annual_interest_rate=rate, tenure_months=tenure, generate_schedule=True)

    assert result.amortization_sample is not None
    assert len(result.amortization_sample) == tenure

    total_principal_paid = sum(item["principal"] for item in result.amortization_sample)
    assert pytest.approx(total_principal_paid, 0.5) == principal

    # Final month balance must be zero
    assert result.amortization_sample[-1]["remaining_balance"] == 0.0


def test_emi_validation_errors():
    with pytest.raises(ValueError, match="Principal loan amount must be greater than zero"):
        calculate_emi(principal=0, annual_interest_rate=12.0, tenure_months=12)

    with pytest.raises(ValueError, match="Tenure in months must be greater than zero"):
        calculate_emi(principal=10000, annual_interest_rate=12.0, tenure_months=0)

    with pytest.raises(ValueError, match="Annual interest rate cannot be negative"):
        calculate_emi(principal=10000, annual_interest_rate=-5.0, tenure_months=12)
