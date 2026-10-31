"""Local, irreversible redaction for data that must not leave the demo backend."""

from dataclasses import dataclass, field
import re
from typing import Callable


PAN_PATTERN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.IGNORECASE)
# Formatted Aadhaar values are recognised explicitly. An unlabelled, unspaced
# 12-digit value is treated as a bank-account-like identifier; either way it
# is redacted, but we avoid incorrectly presenting it as an Aadhaar preview.
AADHAAR_PATTERN = re.compile(r"(?<![\d+])(?:\d{4}[\s-]){2}\d{4}(?!\d)")
MOBILE_PATTERN = re.compile(r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)")
DOB_PATTERN = re.compile(r"(?<!\d)(?:0?[1-9]|[12]\d|3[01])[/-](?:0?[1-9]|1[0-2])[/-](?:19|20)\d{2}(?!\d)")
ACCOUNT_IDENTIFIER_PATTERN = re.compile(
    r"\b(?:PAYTM-(?:LN|WLT)-\d{3,}|APP(?:LICATION)?-[A-Z0-9-]*\d+)\b",
    re.IGNORECASE,
)
BANK_ACCOUNT_PATTERN = re.compile(r"(?<![\dA-Za-z])\d(?:[\s-]?\d){8,17}(?![\dA-Za-z])")


@dataclass(frozen=True)
class RedactedInput:
    """Text safe for persistence/LLM use plus customer-safe masked previews."""

    text: str
    previews: dict[str, str] = field(default_factory=dict)
    detected_types: set[str] = field(default_factory=set)


def _replace(
    text: str,
    pattern: re.Pattern[str],
    key: str,
    placeholder: str,
    mask: Callable[[str], str],
    previews: dict[str, str],
    detected_types: set[str],
) -> str:
    def replacement(match: re.Match[str]) -> str:
        detected_types.add(key)
        previews.setdefault(key, mask(match.group(0)))
        return placeholder

    return pattern.sub(replacement, text)


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def _mask_account_identifier(value: str) -> str:
    return re.sub(r"\d(?=\d{4})", "*", value)


def _mask_aadhaar(value: str) -> str:
    return f"XXXX XXXX {_digits(value)[-4:]}"


def _mask_mobile(value: str) -> str:
    return f"+91 ******{_digits(value)[-4:]}"


def _mask_dob(value: str) -> str:
    return "**/**/" + re.split(r"[/-]", value)[-1]


def _mask_bank_account(value: str) -> str:
    return f"••••{_digits(value)[-4:]}"


def redact_sensitive_text(text: str) -> RedactedInput:
    """Replace recognised identifiers before text reaches storage or an LLM.

    The result intentionally carries no original-value mapping. Masked previews
    are suitable for a customer read-back or a demo reviewer packet only.
    """
    previews: dict[str, str] = {}
    detected_types: set[str] = set()
    safe = text or ""

    safe = _replace(
        safe,
        ACCOUNT_IDENTIFIER_PATTERN,
        "account_identifier",
        "[ACCOUNT_REDACTED]",
        _mask_account_identifier,
        previews,
        detected_types,
    )
    safe = _replace(
        safe,
        PAN_PATTERN,
        "pan",
        "[PAN_REDACTED]",
        lambda value: f"{value[:5].upper()}****{value[-1:].upper()}",
        previews,
        detected_types,
    )
    safe = _replace(
        safe,
        AADHAAR_PATTERN,
        "aadhaar",
        "[AADHAAR_REDACTED]",
        _mask_aadhaar,
        previews,
        detected_types,
    )
    safe = _replace(
        safe,
        MOBILE_PATTERN,
        "mobile",
        "[MOBILE_REDACTED]",
        _mask_mobile,
        previews,
        detected_types,
    )
    safe = _replace(
        safe,
        DOB_PATTERN,
        "dob",
        "[DOB_REDACTED]",
        _mask_dob,
        previews,
        detected_types,
    )
    safe = _replace(
        safe,
        BANK_ACCOUNT_PATTERN,
        "bank_account",
        "[BANK_ACCOUNT_REDACTED]",
        _mask_bank_account,
        previews,
        detected_types,
    )

    return RedactedInput(text=safe, previews=previews, detected_types=detected_types)
