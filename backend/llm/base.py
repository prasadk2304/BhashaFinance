from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ExtractionFieldResult(BaseModel):
    value: Optional[Any] = None
    status: str = "confirmed"  # "confirmed" | "inferred" | "missing"
    source: str = "llm_extraction"  # "llm_extraction" | "regex_parser" | "default"
    readback_required: bool = False
    readback_message: Optional[str] = None


class ExtractionResult(BaseModel):
    extracted_fields: Dict[str, Any] = Field(default_factory=dict)
    field_metadata: Dict[str, ExtractionFieldResult] = Field(default_factory=dict)
    source_provider: str = "unknown"
    confidence: float = 1.0
    detected_language: str = "en"


class LLMProvider(ABC):
    @abstractmethod
    async def extract(
        self,
        transcript: str,
        schema: Dict[str, Any],
        language: str = "en",
    ) -> Dict[str, Any]:
        """
        Extracts structured values from transcript matching schema.
        Rules:
        - Return valid JSON only
        - Return null for anything not explicitly stated (no guessing)
        - Never log transcripts or API keys
        """
        pass

    @abstractmethod
    async def explain(
        self,
        facts: Dict[str, Any],
        language: str = "en",
        tone: str = "professional",
    ) -> str:
        """
        Generates customer explanation grounded strictly in backend-computed facts.
        Rules:
        - Prompt receives only backend-computed facts
        - Must not add numbers, approval claims, or advice
        - Never log transcripts or API keys
        """
        pass

