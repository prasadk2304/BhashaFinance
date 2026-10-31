import json
import logging
from typing import Any, Dict, Optional
import httpx

from backend.config import settings
from backend.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 15.0,
    ):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.llm_model
        self.timeout = timeout

    async def extract(
        self,
        transcript: str,
        schema: Dict[str, Any],
        language: str = "en",
    ) -> Dict[str, Any]:
        """
        Extracts structured fields matching schema from transcript using Ollama.
        Rules:
        - Return valid JSON only
        - Return null for anything not explicitly stated (no guessing)
        - Never log transcripts or keys
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

        payload = {
            "model": self.model,
            "prompt": f"User utterance in {language}: {transcript}",
            "system": system_prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.0,
                "num_predict": 250,
            },
        }

        last_err = None
        # Max 2 attempts (1 initial + 1 retry)
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(f"{self.base_url}/api/generate", json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    response_text = data.get("response", "").strip()
                    parsed = json.loads(response_text)
                    if isinstance(parsed, dict):
                        return parsed
                    raise ValueError("Parsed output is not a JSON object")
            except Exception as err:
                last_err = err
                # Security: NEVER log transcripts or API keys!
                logger.warning("OllamaProvider request attempt %d failed: %s", attempt + 1, type(err).__name__)
                if attempt == 0:
                    continue

        raise RuntimeError(f"OllamaProvider request failed after 1 retry: {type(last_err).__name__}")

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

        payload = {
            "model": self.model,
            "prompt": f"Backend-computed facts: {json.dumps(facts, indent=2)}",
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.0,
                "num_predict": 300,
            },
        }

        last_err = None
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(f"{self.base_url}/api/generate", json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    return data.get("response", "").strip()
            except Exception as err:
                last_err = err
                logger.warning("OllamaProvider explain attempt %d failed: %s", attempt + 1, type(err).__name__)
                if attempt == 0:
                    continue

        raise RuntimeError(f"OllamaProvider explain failed after 1 retry: {type(last_err).__name__}")
