import pytest
from backend.rules.foir import calculate_foir, FoirCalculationResult


def test_eligible_foir():
    # Income: ₹80,000, Existing: ₹10,000, Proposed EMI: ₹15,000
    # Total obligation = ₹25,000 -> FOIR = 31.25% (<= 50%)
    result = calculate_foir(
        monthly_income=80000,
        existing_obligations=10000,
        proposed_emi=15000,
        max_foir_threshold_pct=50.0,
    )

    assert isinstance(result, FoirCalculationResult)
    assert result.foir_percentage == 31.25
    assert result.is_eligible is True
    assert result.status_label == "Eligible"
    assert result.max_allowable_total_obligation == 40000.0
    assert result.max_allowable_emi == 30000.0
    assert result.excess_obligation == 0.0
    assert result.sample_label == "Sample"
    assert result.is_synthetic is True


def test_foir_exceeded():
    # Income: ₹50,000, Existing: ₹15,000, Proposed EMI: ₹15,000
    # Total obligation = ₹30,000 -> FOIR = 60.0% (> 50%)
    result = calculate_foir(
        monthly_income=50000,
        existing_obligations=15000,
        proposed_emi=15000,
        max_foir_threshold_pct=50.0,
    )

    assert result.foir_percentage == 60.0
    assert result.is_eligible is False
    assert result.status_label == "FOIR Exceeded"
    assert result.max_allowable_total_obligation == 25000.0
    assert result.max_allowable_emi == 10000.0
    assert result.excess_obligation == 5000.0


def test_overleveraged_borrower():
    # Income: ₹40,000, Existing: ₹25,000 (already > 50% threshold of 20,000)
    result = calculate_foir(
        monthly_income=40000,
        existing_obligations=25000,
        proposed_emi=5000,
        max_foir_threshold_pct=50.0,
    )

    assert result.is_eligible is False
    assert result.status_label == "Overleveraged"
    assert result.max_allowable_emi == 0.0
    assert result.excess_obligation == 10000.0


def test_max_eligible_loan_derivation():
    # Monthly income 60,000, existing obligations 10,000
    # Max allowable total obligation = 30,000 (at 50%)
    # Max allowable EMI = 20,000
    # At 12% p.a. for 24 months, compute max eligible loan
    result = calculate_foir(
        monthly_income=60000,
        existing_obligations=10000,
        proposed_emi=12000,
        annual_interest_rate=12.0,
        tenure_months=24,
    )

    assert result.is_eligible is True
    assert result.max_allowable_emi == 20000.0
    assert result.max_eligible_loan_amount is not None
    assert result.max_eligible_loan_amount > 400000.0
    assert pytest.approx(result.max_eligible_loan_amount, 100.0) == 424867.7


def test_foir_input_validation():
    with pytest.raises(ValueError, match="Monthly income must be greater than zero"):
        calculate_foir(monthly_income=0, existing_obligations=5000, proposed_emi=5000)

    with pytest.raises(ValueError, match="Existing obligations cannot be negative"):
        calculate_foir(monthly_income=50000, existing_obligations=-1000)

    with pytest.raises(ValueError, match="FOIR threshold percentage must be between 0 and 100"):
        calculate_foir(monthly_income=50000, max_foir_threshold_pct=110)

