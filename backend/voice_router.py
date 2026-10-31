"""Deterministic, privacy-safe routing for the home voice agent."""

from typing import Optional
from pydantic import BaseModel


class JourneyRoute(BaseModel):
    journey_id: Optional[str] = None
    needs_clarification: bool = False
    prompt: str = ""


ROUTE_KEYWORDS = {
    "payment_help": (
        "payment failed", "auto debit", "auto-debit", "emi failed", "bounce", "nach", "overdue", "restructure", "repayment",
        "ईएमआय", "ऑटो डेबिट", "फेल", "पेमेंट", "हप्ता", "भुगतान", "ऑटो डेबिट फेल", "किस्त",
    ),
    "sip": (
        "sip", "invest", "investment", "mutual fund", "wealth", "save monthly",
        "एसआयपी", "गुंतवणूक", "म्युच्युअल फंड", "निवेश", "म्यूचुअल फंड",
    ),
    "loan_rejection": (
        "rejected", "rejection", "declined", "cibil", "credit score", "reapply",
        "नाकार", "रिजेक्ट", "क्रेडिट स्कोअर", "सिबिल", "अस्वीकृत",
    ),
    "personal_loan": (
        "personal loan", "loan amount", "need a loan", "borrow", "emi for loan",
        "पर्सनल लोन", "कर्ज", "लोन", "कर्ज पाहिजे", "ऋण",
    ),
}


def classify_journey_intent(transcript: str) -> JourneyRoute:
    text = transcript.lower().strip()
    scores = {journey: sum(1 for keyword in keywords if keyword in text) for journey, keywords in ROUTE_KEYWORDS.items()}
    best_score = max(scores.values(), default=0)
    winners = [journey for journey, score in scores.items() if score == best_score and score > 0]

    if len(winners) != 1:
        return JourneyRoute(
            needs_clarification=True,
            prompt="I can help with a personal loan, SIP investment, EMI or payment help, or a loan rejection. Which one would you like to discuss?",
        )

    return JourneyRoute(journey_id=winners[0])
