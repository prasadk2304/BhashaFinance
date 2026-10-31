import pytest
from backend.rules.sip import calculate_sip, SipCalculationResult


def test_standard_sip_calculation():
    # ₹5,000 monthly, 12% annual return, 3 years (36 months)
    result = calculate_sip(monthly_investment=5000, expected_annual_return=12.0, duration_years=3)

    assert isinstance(result, SipCalculationResult)
    assert result.monthly_investment == 5000.0
    assert result.expected_annual_return == 12.0
    assert result.duration_years == 3.0
    assert result.total_months == 36
    assert result.total_invested == 180000.0
    assert pytest.approx(result.future_value, 1.0) == 217538.24
    assert result.future_value_rounded == 217538
    assert pytest.approx(result.estimated_returns, 1.0) == 37538.7
    assert result.sample_label == "Sample"
    assert result.is_synthetic is True


def test_zero_return_sip():
    # ₹10,000 monthly at 0% return for 2 years -> FV == Invested (240,000)
    result = calculate_sip(monthly_investment=10000, expected_annual_return=0.0, duration_years=2)

    assert result.total_months == 24
    assert result.total_invested == 240000.0
    assert result.future_value == 240000.0
    assert result.estimated_returns == 0.0


def test_sip_yearly_growth_schedule():
    result = calculate_sip(
        monthly_investment=2500,
        expected_annual_return=15.0,
        duration_years=5,
        generate_yearly_breakdown=True,
    )

    assert result.yearly_growth_sample is not None
    assert len(result.yearly_growth_sample) == 5

    # Year 1 invested should be 2500 * 12 = 30000
    assert result.yearly_growth_sample[0]["invested_amount"] == 30000.0
    # Year 5 invested should be 2500 * 60 = 150000
    assert result.yearly_growth_sample[4]["invested_amount"] == 150000.0

    # Compounding check: wealth gain should grow non-linearly
    assert result.yearly_growth_sample[4]["wealth_gain"] > (result.yearly_growth_sample[0]["wealth_gain"] * 5)


def test_sip_validation_errors():
    with pytest.raises(ValueError, match="Monthly investment amount must be greater than zero"):
        calculate_sip(monthly_investment=0, expected_annual_return=12.0, duration_years=3)

    with pytest.raises(ValueError, match="Investment duration in years must be greater than zero"):
        calculate_sip(monthly_investment=5000, expected_annual_return=12.0, duration_years=0)

    with pytest.raises(ValueError, match="Expected annual return rate cannot be negative"):
        calculate_sip(monthly_investment=5000, expected_annual_return=-2.0, duration_years=3)
