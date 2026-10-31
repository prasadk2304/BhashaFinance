import re
from typing import Dict, List, Optional, Tuple

WORD_NUMBERS: Dict[str, int] = {
    "zero": 0,
    "one": 1,
    "ek": 1,
    "two": 2,
    "do": 2,
    "three": 3,
    "teen": 3,
    "four": 4,
    "chaar": 4,
    "five": 5,
    "paanch": 5,
    "six": 6,
    "che": 6,
    "chhah": 6,
    "seven": 7,
    "saat": 7,
    "eight": 8,
    "aath": 8,
    "nine": 9,
    "nau": 9,
    "ten": 10,
    "das": 10,
    "eleven": 11,
    "twelve": 12,
    "barah": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "pandrah": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "bees": 20,
    "thirty": 30,
    "tees": 30,
    "forty": 40,
    "chaalis": 40,
    "fifty": 50,
    "pachaas": 50,
    "sixty": 60,
    "saath": 60,
    "seventy": 70,
    "sattar": 70,
    "eighty": 80,
    "assi": 80,
    "ninety": 90,
    "nabbe": 90,
}

MULTIPLIERS: Dict[str, float] = {
    "hundred": 100.0,
    "sau": 100.0,
    "k": 1000.0,
    "thousand": 1000.0,
    "thousands": 1000.0,
    "hazaar": 1000.0,
    "hazar": 1000.0,
    "lakh": 100000.0,
    "lakhs": 100000.0,
    "lac": 100000.0,
    "lacs": 100000.0,
    "lk": 100000.0,
    "crore": 10000000.0,
    "crores": 10000000.0,
    "cr": 10000000.0,
    "crs": 10000000.0,
    "million": 1000000.0,
    "millions": 1000000.0,
    "billion": 1000000000.0,
}

SPECIAL_COLLOQUIAL: Dict[str, float] = {
    "dedh lakh": 150000.0,
    "dhai lakh": 250000.0,
    "aadha lakh": 50000.0,
    "dedh hazaar": 1500.0,
    "dhai hazaar": 2500.0,
}


def words_to_number(phrase: str) -> Optional[float]:
    """
    Parses English/Hinglish word phrases like:
    'eighty thousand', 'one lakh fifty thousand', 'twenty eight thousand',
    'two crore fifty lakh'.
    """
    phrase = phrase.lower().strip()
    if not phrase:
        return None

    # Check colloquial shortcuts
    if phrase in SPECIAL_COLLOQUIAL:
        return SPECIAL_COLLOQUIAL[phrase]

    tokens = re.split(r"[\s\-]+", phrase)
    total = 0.0
    current = 0.0

    valid_token_found = False

    for token in tokens:
        if token in ("and", "rupees", "rs", "inr"):
            continue

        if token in WORD_NUMBERS:
            current += WORD_NUMBERS[token]
            valid_token_found = True
        elif token in ("hundred", "sau"):
            current = (current if current != 0 else 1.0) * 100.0
            valid_token_found = True
        elif token in ("thousand", "thousands", "hazaar", "hazar", "k"):
            current = (current if current != 0 else 1.0) * 1000.0
            total += current
            current = 0.0
            valid_token_found = True
        elif token in ("lakh", "lakhs", "lac", "lacs", "lk"):
            current = (current if current != 0 else 1.0) * 100000.0
            total += current
            current = 0.0
            valid_token_found = True
        elif token in ("crore", "crores", "cr", "crs"):
            current = (current if current != 0 else 1.0) * 10000000.0
            total += current
            current = 0.0
            valid_token_found = True
        elif token in ("million", "millions"):
            current = (current if current != 0 else 1.0) * 1000000.0
            total += current
            current = 0.0
            valid_token_found = True
        else:
            # Check if token is digits like '1.5' or '50' inside a words phrase
            try:
                num = float(token.replace(",", ""))
                current += num
                valid_token_found = True
            except ValueError:
                return None

    if not valid_token_found:
        return None

    return total + current


def parse_amount(text: str) -> Optional[float]:
    """
    Extracts and normalizes an amount from natural text.
    Handles:
      - 80k, 80 K, 2.5k
      - 1.5 lakh, 1.5lakh, 2 lacs, 5 lakhs, 10 L
      - 2 crore, 1.5 cr
      - 28,000, 1,50,000, 50000
      - eighty thousand, one lakh fifty thousand
      - 1 lakh 20 thousand
      - ₹80,000, Rs. 1.5 lakh
    """
    if not text:
        return None

    cleaned = text.strip()

    # Normalize currency prefixes
    cleaned = re.sub(r"(?i)^(₹|rs\.?|inr)\s*", "", cleaned)
    cleaned = re.sub(r"(?i)\s*(rupees|rs\.?|inr|per\s+month|p\.?m\.?|monthly)$", "", cleaned).strip()

    # Check exact word match first if whole string is words
    word_val = words_to_number(cleaned)
    if word_val is not None:
        return word_val

    # Regex pattern for shorthand like:
    # 80k, 1.5 lakh, 1.5lakh, 2 crore, 28,000
    # Also compound like '1 lakh 20 thousand' or '2.5 cr'
    pattern = re.compile(
        r"""
        (?P<num>\d+(?:,\d+)*(?:\.\d+)?)              # Number part, e.g. 80, 1.5, 28,000
        \s*
        (?P<unit>k|thousand|thousands|hazaar|hazar|lakh|lakhs|lac|lacs|lk|crore|crores|cr|crs|hundred|sau)? # Optional unit
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    matches = list(pattern.finditer(cleaned))
    if not matches:
        return None

    # Check if there are multiple parts like "1 lakh 20 thousand"
    valid_components = []
    for m in matches:
        num_str = m.group("num")
        unit_str = m.group("unit")

        if not num_str:
            continue

        try:
            val = float(num_str.replace(",", ""))
        except ValueError:
            continue

        if unit_str:
            unit_key = unit_str.lower()
            if unit_key in MULTIPLIERS:
                val = val * MULTIPLIERS[unit_key]
        valid_components.append((m, val))

    if not valid_components:
        return None

    # Check if the first and subsequent components are contiguous parts of a compound number
    # (e.g. "1 lakh 20 thousand" or "1 lakh and 20 thousand")
    # If separated by other words like "with", "salary", etc., they are distinct values.
    compound_sum = valid_components[0][1]
    prev_match = valid_components[0][0]
    prev_val = valid_components[0][1]

    for curr_match, curr_val in valid_components[1:]:
        intervening = cleaned[prev_match.end():curr_match.start()].strip().lower()
        # Only allow whitespace or "and" between compound components
        if intervening in ("", "and") and prev_val > curr_val:
            compound_sum += curr_val
            prev_match = curr_match
            prev_val = curr_val
        else:
            # Not part of the compound number
            break

    return compound_sum


def extract_all_amounts(text: str) -> List[Tuple[str, float]]:
    """
    Extracts all numerical and monetary expressions from a text message.
    Returns list of tuples: (matched_text, numeric_value).
    """
    if not text:
        return []

    results = []

    # 1. Check for word-based expressions: "eighty thousand", "one lakh fifty thousand"
    # Find word spans
    word_pattern = re.compile(
        r"\b(?:(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|"
        r"fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|"
        r"sixty|seventy|eighty|ninety|dedh|dhai|ek|do|teen|chaar|paanch)\s*)+"
        r"(?:(?:crore|crores|lakh|lakhs|lac|lacs|thousand|thousands|hazaar|hazar|hundred|sau)\s*)*\b",
        re.IGNORECASE,
    )
    for match in word_pattern.finditer(text):
        m_str = match.group(0).strip()
        val = words_to_number(m_str)
        if val is not None and val > 0:
            results.append((m_str, val))

    # 2. Check for numeric and shorthand patterns: "80k", "1.5 lakh", "28,000", "₹50,000"
    num_pattern = re.compile(
        r"(?:(?:₹|rs\.?|inr)\s*)?"
        r"(\d+(?:,\d+)*(?:\.\d+)?)"
        r"\s*"
        r"(k|thousand|thousands|hazaar|hazar|lakh|lakhs|lac|lacs|lk|crore|crores|cr|crs|hundred|sau)?\b",
        re.IGNORECASE,
    )
    for match in num_pattern.finditer(text):
        full_match = match.group(0).strip()
        val = parse_amount(full_match)
        if val is not None and val > 0:
            # Avoid duplicate if already covered by word parser
            if not any(full_match in r[0] or r[0] in full_match for r in results):
                results.append((full_match, val))

    return results


def parse_tenure_months(text: str) -> Optional[int]:
    """
    Parses tenure from natural language expressions into months.
    Examples:
      - '2 years' -> 24
      - '1.5 years' -> 18
      - '18 months' -> 18
      - '3 saal' -> 36
      - '6 mahine' -> 6
      - '24' -> 24
    """
    if not text:
        return None

    cleaned = text.lower().strip()

    # Pattern for years
    m_year = re.search(r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?|saal|baras)", cleaned)
    if m_year:
        years = float(m_year.group(1))
        return int(round(years * 12))

    # Pattern for months
    m_month = re.search(r"(\d+)\s*(?:months?|mths?|mahine|maheene)", cleaned)
    if m_month:
        return int(m_month.group(1))

    # Raw digits (if purely a tenure number in context, e.g. "12", "24", "36")
    m_pure = re.match(r"^(\d+)$", cleaned)
    if m_pure:
        return int(m_pure.group(1))

    return None


def parse_percentage(text: str) -> Optional[float]:
    """
    Parses interest rates or returns percentage.
    Examples:
      - '12%' -> 12.0
      - '12.5 percent' -> 12.5
      - '14.2% p.a.' -> 14.2
      - '10 per cent per annum' -> 10.0
    """
    if not text:
        return None

    cleaned = text.lower().strip()
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:%|percent|per\s*cent)?", cleaned)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None
