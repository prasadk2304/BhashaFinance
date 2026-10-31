"""
Plain-language inline definition injector for fintech terms.
Adds beginner-friendly explanations on first mention for:
- EMI: Equated Monthly Installment (your fixed monthly payment)
- FOIR: Fixed Obligation to Income Ratio (percentage of monthly income spent on loan payments)
- tenure: total loan duration in months
- APR: Annual Percentage Rate (yearly interest rate including standard fees)
"""

import re

# Term patterns and their expanded inline definition on first mention
TERM_DEFINITIONS = [
    (
        r"\bEMI\b(?!\s*\()",
        "EMI (Equated Monthly Installment: your fixed monthly payment)"
    ),
    (
        r"\bFOIR\b(?!\s*\()",
        "FOIR (Fixed Obligation to Income Ratio: percentage of monthly income spent on loan payments)"
    ),
    (
        r"\btenure\b(?!\s*\()",
        "tenure (the total loan duration in months)"
    ),
    (
        r"\bAPR\b(?!\s*\()",
        "APR (Annual Percentage Rate: yearly interest rate including standard fees)"
    ),
]


def add_inline_definitions(text: str) -> str:
    """
    Adds plain-language inline definitions for EMI, FOIR, tenure, APR
    strictly on their first mention, without duplicating if already explained.
    """
    if not text:
        return text

    result = text
    for pattern, replacement in TERM_DEFINITIONS:
        # Check if definition is already in text to prevent double expansion
        if "(" in replacement:
            inner_def = replacement.split("(")[1].split("—")[0].strip()
            if inner_def.lower() in result.lower():
                continue

        # Replace ONLY the first occurrence (count=1)
        result = re.sub(pattern, replacement, result, count=1)

    return result
