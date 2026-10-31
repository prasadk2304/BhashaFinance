from backend.voice_router import classify_journey_intent


def test_routes_payment_failure_to_payment_help():
    result = classify_journey_intent("My auto debit EMI failed and I need help")
    assert result.journey_id == "payment_help"
    assert result.needs_clarification is False


def test_routes_sip_request_to_wealth_journey():
    result = classify_journey_intent("I want to invest ten thousand every month in a SIP")
    assert result.journey_id == "sip"


def test_routes_marathi_emi_failure_to_payment_help():
    result = classify_journey_intent("माझे ईएमआय ऑटो डेबिट फेल झाले आहे")
    assert result.journey_id == "payment_help"


def test_routes_marathi_sip_request_to_wealth_journey():
    result = classify_journey_intent("मला दर महिन्याला एसआयपी मध्ये गुंतवणूक करायची आहे")
    assert result.journey_id == "sip"


def test_asks_for_clarification_when_intent_is_ambiguous():
    result = classify_journey_intent("Can you help me with my money?")
    assert result.journey_id is None
    assert result.needs_clarification is True
