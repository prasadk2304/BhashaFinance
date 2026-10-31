import json
import logging
from typing import Any, Dict, Optional, Type, TypeVar
import httpx
from pydantic import BaseModel, ValidationError

from backend.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class FieldExtractionResult(BaseModel):
    extracted_fields: Dict[str, Any] = {}
    confidence: float = 1.0
    detected_language: str = "en"
    raw_intent: Optional[str] = None


class ExplanationResult(BaseModel):
    explanation: str
    tone: str = "professional"
    sample_disclaimer_included: bool = True


class OllamaClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.llm_model
        self.timeout = timeout_seconds

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        """
        Calls Ollama at localhost:11434 with temperature 0, structured JSON output,
        validates with Pydantic, and retries once on failure.
        """
        schema = response_model.model_json_schema()
        system = (
            system_prompt
            or "You are BhashaFinance AI, a multilingual Paytm lending journey assistant. "
            "You only extract fields and write customer explanations. You never perform arithmetic "
            "or calculate numbers; all numbers are determined by Python rules. "
            "Return valid JSON matching the requested schema."
        )

        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.0,
            },
        }

        # Attempt 1 + 1 retry on failure
        last_error = None
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(f"{self.base_url}/api/generate", json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    response_text = data.get("response", "").strip()

                    # Parse JSON
                    parsed_json = json.loads(response_text)
                    validated = response_model.model_validate(parsed_json)
                    return validated
            except (httpx.HTTPError, json.JSONDecodeError, ValidationError) as err:
                last_error = err
                logger.warning("Ollama call attempt %d failed: %s", attempt + 1, str(err))
                if attempt == 0:
                    continue  # Retry once

        # If both attempts failed, re-raise or provide fallback
        raise RuntimeError(f"Ollama structured generation failed after 1 retry: {last_error}")

    async def extract_fields(
        self,
        user_utterance: str,
        target_fields: list[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> FieldExtractionResult:
        """
        Extracts values for target fields using Ollama, constrained by schema.
        Note: The LLM only extracts fields; numbers are parsed & verified deterministically.
        """
        prompt = (
            f"User Utterance: \"{user_utterance}\"\n"
            f"Target Fields to extract: {target_fields}\n"
            f"Context: {context or {}}\n\n"
            "Extract values for the target fields from the user utterance. "
            "Return JSON with 'extracted_fields' (dictionary of field: value), "
            "'confidence' (float 0-1), 'detected_language' (e.g. en, hi, hinglish), and 'raw_intent'."
        )
        try:
            return await self.generate_structured(prompt, FieldExtractionResult)
        except Exception as e:
            logger.info("Ollama offline or failed, returning empty extraction fallback: %s", e)
            return FieldExtractionResult(
                extracted_fields={},
                confidence=0.0,
                detected_language="en",
                raw_intent="fallback",
            )

    async def generate_explanation(
        self,
        journey_title: str,
        metrics: Dict[str, Any],
        language: str = "en",
    ) -> str:
        """
        Generates an easy-to-understand customer explanation for the calculated offer.
        LLM only writes the explanation; all metrics passed in are pre-calculated by Python rules.
        """
        prompt = (
            f"Product: {journey_title}\n"
            f"Pre-calculated Deterministic Metrics: {metrics}\n"
            f"Target Language: {language}\n\n"
            "Write a concise, friendly explanation of this Sample offer for the user. "
            "Always clearly mention that this is a 'Sample' offer and figures are illustrative. "
            "Do NOT alter any numbers."
        )
        try:
            res = await self.generate_structured(prompt, ExplanationResult)
            return res.explanation
        except Exception:
            # Fallback explanation template
            return (
                f"Here is your {journey_title} summary. All presented numbers are Sample figures "
                "calculated deterministically based on standard financial rules."
            )

