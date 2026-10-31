import json
import logging
from typing import Any, Dict, Optional
import httpx

from backend.config import settings
from backend.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class SarvamProvider(LLMProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 8.0,
    ):
        self.api_key = api_key or settings.sarvam_api_key
        self.base_url = (base_url or settings.sarvam_api_base_url).rstrip("/")
        self.model = model or settings.sarvam_chat_model
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    async def _post_chat_completion(
        self,
        messages: list[dict],
        max_tokens: int = 300,
        temperature: float = 0.0,
        response_format: Optional[dict] = None,
    ) -> str:
        if not self.is_configured:
            raise ValueError("Sarvam API key is not configured.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            # A short extraction or conversational reply can otherwise spend
            # its whole token allowance on hidden reasoning and return an
            # empty message. Sarvam documents `null` as the opt-out value.
            "reasoning_effort": None,
        }
        if response_format:
            payload["response_format"] = response_format

        url = f"{self.base_url}/chat/completions"

        last_err = None
        # Max 2 attempts (1 initial + 1 retry on timeout, error or invalid response)
        for attempt in range(2):
            try:
                # The desktop environment can expose unusable proxy variables.
                # Sarvam is reached directly; do not inherit those proxy settings.
                async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices and "message" in choices[0]:
                        content = choices[0]["message"].get("content")
                        if isinstance(content, str) and content.strip():
                            return content.strip()
                    raise ValueError("Empty completion response from Sarvam API.")
            except (httpx.TimeoutException, httpx.HTTPError, ValueError, Exception) as err:
                last_err = err
                # Security: NEVER log transcripts or API keys!
                logger.warning("SarvamProvider request attempt %d failed: %s", attempt + 1, type(err).__name__)
                if attempt == 0:
                    continue

        raise RuntimeError(f"SarvamProvider request failed after 1 retry: {type(last_err).__name__}")

    async def extract(
        self,
        transcript: str,
        schema: Dict[str, Any],
        language: str = "en",
    ) -> Dict[str, Any]:
        """
        Extracts structured fields matching schema from transcript using Sarvam.
        Rules:
        - Return valid JSON only
        - Return null for anything not explicitly stated (no guessing)
        - Never log transcripts or API keys
        """
        system_prompt = (
            "You are an accurate information extractor for financial applications. "
            "Extract values explicitly stated in the user utterance matching this schema:\n"
            f"{json.dumps(schema, indent=2)}\n\n"
            "STRICT EXTRACTION RULES:\n"
            "1. Output valid JSON ONLY matching the schema keys.\n"
            "2. Output null for any field not explicitly stated by the user. NEVER guess or assume.\n"
            "3. For identifier fields, codes, account numbers, or reference strings (such as account_id, application_id), "
            "preserve the EXACT full alphanumeric string including any prefixes, letters, and hyphens (e.g., 'PAYTM-LN-8812'). "
            "Never strip letters or truncate to only digits.\n"
            "4. Do not include markdown formatting or commentary."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User utterance in {language}: {transcript}"},
        ]

        # Call with small max_tokens
        raw_text = await self._post_chat_completion(
            messages=messages,
            max_tokens=250,
            temperature=0.0,
            response_format={"type": "json_object"},
        )

        try:
            parsed = json.loads(raw_text)
            if isinstance(parsed, dict):
                return parsed
            raise ValueError("Parsed output is not a JSON object")
        except json.JSONDecodeError as err:
            logger.warning("SarvamProvider output failed JSON parsing: %s", type(err).__name__)
            raise ValueError(f"Invalid JSON returned by Sarvam: {type(err).__name__}")

    async def explain(
        self,
        facts: Dict[str, Any],
        language: str = "en",
        tone: str = "professional",
    ) -> str:
        """
        Generates customer explanation grounded strictly in backend-computed facts.
        Prompt receives only backend-computed facts and must not add numbers, approval claims or advice.
        """
        if tone == "calm":
            tone_directive = (
                "CALM URGENCY/DISTRESS STYLE:\n"
                "- Acknowledge the user's situation in ONE short sentence.\n"
                "- Give the concrete next step FIRST before anything else.\n"
                "- Keep the explanation strictly UNDER 40 WORDS.\n"
                "- Use a calm, reassuring, empathetic tone."
            )
        else:
            tone_directive = f"Write in a {tone} tone."

        system_prompt = (
            f"You are a customer service explainer for Paytm lending.\n"
            f"{tone_directive}\n"
            f"Language: {language}\n\n"
            "STRICT RULES:\n"
            "1. Base your explanation ONLY on the provided backend facts.\n"
            "2. NEVER invent or alter numbers, interest rates, or calculations.\n"
            "3. NEVER make approval claims or promises. (Sanctions are strictly non-binding).\n"
            "4. NEVER give financial or investment advice.\n"
            "5. Always clearly state this is a Sample illustrative offer."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Backend-computed facts: {json.dumps(facts, indent=2)}"},
        ]

        return await self._post_chat_completion(
            messages=messages,
            max_tokens=300,
            temperature=0.0,
        )
