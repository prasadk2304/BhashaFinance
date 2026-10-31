"""
Spoken number and currency amount converter for Indian fintech.
Converts amounts like 'Rs 80,000', '₹1.5 lakh', '4,500' into natural spoken words
in English, Hindi (hi-IN), and Marathi (mr-IN) before Text-to-Speech synthesis.
"""

import re
from typing import Optional

# English number maps
ONES_EN = {
    0: "", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
    6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
    11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen", 15: "fifteen",
    16: "sixteen", 17: "seventeen", 18: "eighteen", 19: "nineteen"
}
TENS_EN = {
    2: "twenty", 3: "thirty", 4: "forty", 5: "fifty",
    6: "sixty", 7: "seventy", 8: "eighty", 9: "ninety"
}

# Hindi number maps
ONES_HI = {
    0: "", 1: "एक", 2: "दो", 3: "तीन", 4: "चार", 5: "पाँच",
    6: "छह", 7: "सात", 8: "आठ", 9: "नौ", 10: "दस",
    11: "ग्यारह", 12: "बारह", 13: "तेरह", 14: "चौदह", 15: "पंद्रह",
    16: "सोलह", 17: "सत्रह", 18: "अठारह", 19: "उन्नीस", 20: "बीस",
    21: "इक्कीस", 22: "बाईस", 23: "तेईस", 24: "चौबीस", 25: "पच्चीस",
    26: "छब्बीस", 27: "सत्ताईस", 28: "अट्ठाईस", 29: "उनतीस", 30: "तीस",
    35: "पैंतीस", 40: "चालीस", 45: "पैंतालीस", 50: "पचास", 55: "पचपन",
    60: "साठ", 62: "बासठ", 65: "पैंसठ", 70: "सत्तर", 75: "पचहत्तर",
    80: "अस्सी", 85: "पचासी", 90: "नब्बे", 95: "पंचानवे"
}

# Marathi number maps
ONES_MR = {
    0: "", 1: "एक", 2: "दोन", 3: "तीन", 4: "चार", 5: "पाच",
    6: "सहा", 7: "सात", 8: "आठ", 9: "नऊ", 10: "दहा",
    11: "अकरा", 12: "बारा", 13: "तेरा", 14: "चौदा", 15: "पंधरा",
    16: "सोळा", 17: "सतरा", 18: "अठरा", 19: "एकोणीस", 20: "वीस",
    21: "एकवीस", 22: "बावीस", 23: "तेवीस", 24: "चोवीस", 25: "पंचवीस",
    26: "सव्वीस", 27: "सत्तावीस", 28: "अठ्ठावीस", 29: "एकोणतीस", 30: "तीस",
    35: "पस्तीस", 40: "चाळीस", 45: "पंचेचाळीस", 50: "पन्नास", 55: "पंचावन्न",
    60: "साठ", 62: "पासष्ट", 65: "पासष्ट", 70: "सत्तर", 75: "पंच्याहत्तर",
    80: "ऐंशी", 85: "पंच्याऐंशी", 90: "नव्वद", 95: "पंच्याण्णव"
}


def number_to_words_en(n: int) -> str:
    """Converts positive integer to Indian English words using Lakh/Crore system."""
    if n == 0:
        return "zero"
    if n < 0:
        return "minus " + number_to_words_en(-n)

    parts = []

    # Crores (10,000,000)
    crores = n // 10000000
    n %= 10000000
    if crores > 0:
        parts.append(f"{number_to_words_en(crores)} crore")

    # Lakhs (100,000)
    lakhs = n // 100000
    n %= 100000
    if lakhs > 0:
        parts.append(f"{number_to_words_en(lakhs)} lakh")

    # Thousands (1,000)
    thousands = n // 1000
    n %= 1000
    if thousands > 0:
        parts.append(f"{number_to_words_en(thousands)} thousand")

    # Hundreds (100)
    hundreds = n // 100
    n %= 100
    if hundreds > 0:
        parts.append(f"{ONES_EN[hundreds]} hundred")

    # Remainder < 100
    if n > 0:
        if n < 20:
            parts.append(ONES_EN[n])
        else:
            tens = n // 10
            rem = n % 10
            t_str = TENS_EN[tens]
            if rem > 0:
                parts.append(f"{t_str}-{ONES_EN[rem]}")
            else:
                parts.append(t_str)

    return " ".join(parts).strip()


def number_to_words_hi(n: int) -> str:
    """Converts positive integer to Hindi words using Lakh/Crore system."""
    if n == 0:
        return "शून्य"
    if n < 0:
        return "ऋण " + number_to_words_hi(-n)

    parts = []

    crores = n // 10000000
    n %= 10000000
    if crores > 0:
        parts.append(f"{number_to_words_hi(crores)} करोड़")

    lakhs = n // 100000
    n %= 100000
    if lakhs > 0:
        parts.append(f"{number_to_words_hi(lakhs)} लाख")

    thousands = n // 1000
    n %= 1000
    if thousands > 0:
        parts.append(f"{number_to_words_hi(thousands)} हज़ार")

    hundreds = n // 100
    n %= 100
    if hundreds > 0:
        parts.append(f"{ONES_HI.get(hundreds, str(hundreds))} सौ")

    if n > 0:
        if n in ONES_HI:
            parts.append(ONES_HI[n])
        else:
            tens = (n // 10) * 10
            rem = n % 10
            tens_word = ONES_HI.get(tens, str(tens))
            rem_word = ONES_HI.get(rem, str(rem))
            parts.append(f"{tens_word} {rem_word}".strip())

    return " ".join(parts).strip()


def number_to_words_mr(n: int) -> str:
    """Converts positive integer to Marathi words using Lakh/Crore system."""
    if n == 0:
        return "शून्य"
    if n < 0:
        return "उणे " + number_to_words_mr(-n)

    parts = []

    crores = n // 10000000
    n %= 10000000
    if crores > 0:
        parts.append(f"{number_to_words_mr(crores)} कोटी")

    lakhs = n // 100000
    n %= 100000
    if lakhs > 0:
        parts.append(f"{number_to_words_mr(lakhs)} लाख")

    thousands = n // 1000
    n %= 1000
    if thousands > 0:
        parts.append(f"{number_to_words_mr(thousands)} हजार")

    hundreds = n // 100
    n %= 100
    if hundreds > 0:
        if hundreds == 1:
            parts.append("शंभर")
        elif hundreds == 2:
            parts.append("दोनशे")
        elif hundreds == 3:
            parts.append("तीनशे")
        elif hundreds == 4:
            parts.append("चारशे")
        elif hundreds == 5:
            parts.append("पाचशे")
        else:
            parts.append(f"{ONES_MR.get(hundreds, str(hundreds))}शे")

    if n > 0:
        if n in ONES_MR:
            parts.append(ONES_MR[n])
        else:
            tens = (n // 10) * 10
            rem = n % 10
            tens_word = ONES_MR.get(tens, str(tens))
            rem_word = ONES_MR.get(rem, str(rem))
            parts.append(f"{tens_word} {rem_word}".strip())

    return " ".join(parts).strip()


def format_amount_to_words(amount: float, language_code: str = "en-IN") -> str:
    """
    Formats a numeric amount into spoken words with currency in the target language.
    """
    int_amt = int(round(amount))
    lang = language_code.lower()

    if "mr" in lang:
        words = number_to_words_mr(int_amt)
        return f"{words} रुपये"
    elif "hi" in lang:
        words = number_to_words_hi(int_amt)
        return f"{words} रुपये"
    else:
        words = number_to_words_en(int_amt)
        return f"{words} rupees"


def convert_amounts_in_text(text: str, language_code: str = "en-IN") -> str:
    """
    Replaces all monetary figures in text with spoken words before TTS.
    Examples:
    - "₹80,000" -> "eighty thousand rupees" / "अस्सी हज़ार रुपये" / "ऐंशी हजार रुपये"
    - "Rs. 1,50,000" -> "one lakh fifty thousand rupees"
    - "Rs 4,500.00" -> "four thousand five hundred rupees"
    """
    if not text:
        return text

    # Pattern matches ₹80,000 or Rs. 80,000 or Rs 80,000 or ₹1.5 lakh
    currency_pattern = re.compile(
        r"(?:₹|rs\.?|inr)\s*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)(?:\s*(lakh|crore|k)\b)?",
        re.IGNORECASE
    )

    def replace_match(match: re.Match) -> str:
        raw_num = match.group(1).replace(",", "")
        multiplier = (match.group(2) or "").lower()
        try:
            val = float(raw_num)
            if multiplier == "crore":
                val *= 10000000
            elif multiplier == "lakh":
                val *= 100000
            elif multiplier == "k":
                val *= 1000
            return format_amount_to_words(val, language_code)
        except (ValueError, TypeError):
            return match.group(0)

    converted = currency_pattern.sub(replace_match, text)

    # Clean up isolated symbols if any remain
    converted = re.sub(r"₹\s*", "rupees ", converted)
    return converted
