import pytest
from backend.rules.parser import (
    extract_all_amounts,
    parse_amount,
    parse_percentage,
    parse_tenure_months,
    words_to_number,
)


def test_user_specified_core_examples():
    """
    Direct verification of prompt-required examples:
    80k, 1.5 lakh, 28,000, eighty thousand
    """
    assert parse_amount("80k") == 80000.0
    assert parse_amount("1.5 lakh") == 150000.0
    assert parse_amount("28,000") == 28000.0
    assert parse_amount("eighty thousand") == 80000.0


def test_shorthand_multipliers():
    assert parse_amount("80K") == 80000.0
    assert parse_amount("50k") == 50000.0
    assert parse_amount("2.5k") == 2500.0
    assert parse_amount("100k") == 100000.0


def test_indian_lakh_and_crore_variations():
    assert parse_amount("1.5lakh") == 150000.0
    assert parse_amount("2 lakh") == 200000.0
    assert parse_amount("5 lakhs") == 500000.0
    assert parse_amount("2 lacs") == 200000.0
    assert parse_amount("50 lacs") == 5000000.0
    assert parse_amount("2 crore") == 20000000.0
    assert parse_amount("1.5 cr") == 15000000.0
    assert parse_amount("2.5 crores") == 25000000.0


def test_english_words_parser():
    assert parse_amount("one lakh fifty thousand") == 150000.0
    assert parse_amount("twenty eight thousand") == 28000.0
    assert parse_amount("fifty thousand") == 50000.0
    assert parse_amount("two lakh") == 200000.0
    assert parse_amount("two crore") == 20000000.0
    assert parse_amount("ten thousand") == 10000.0
    assert parse_amount("five thousand five hundred") == 5500.0


def test_colloquial_and_hinglish():
    assert parse_amount("dedh lakh") == 150000.0
    assert parse_amount("dhai lakh") == 250000.0
    assert parse_amount("aadha lakh") == 50000.0
    assert parse_amount("50 hazaar") == 50000.0
    assert parse_amount("50 hazar") == 50000.0


def test_compound_and_punctuated_numbers():
    assert parse_amount("1 lakh 20 thousand") == 120000.0
    assert parse_amount("2 lakh 50 thousand") == 250000.0
    assert parse_amount("1,50,000") == 150000.0
    assert parse_amount("10,00,000") == 1000000.0
    assert parse_amount("₹80,000") == 80000.0
    assert parse_amount("Rs. 1.5 lakh") == 150000.0
    assert parse_amount("50,000 per month") == 50000.0


def test_extract_all_amounts():
    text = "My monthly salary is 80k and I want a loan of 1.5 lakh for existing EMIs of 10,000."
    extracted = extract_all_amounts(text)

    values = [val for _, val in extracted]
    assert 80000.0 in values
    assert 150000.0 in values
    assert 10000.0 in values


def test_tenure_parsing():
    assert parse_tenure_months("2 years") == 24
    assert parse_tenure_months("1.5 years") == 18
    assert parse_tenure_months("18 months") == 18
    assert parse_tenure_months("3 saal") == 36
    assert parse_tenure_months("6 mahine") == 6
    assert parse_tenure_months("24") == 24


def test_percentage_parsing():
    assert parse_percentage("12%") == 12.0
    assert parse_percentage("12.5 percent") == 12.5
    assert parse_percentage("14.2% p.a.") == 14.2
    assert parse_percentage("10 per cent per annum") == 10.0
