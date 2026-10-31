import logging
from typing import Any, Dict, List, Optional

from backend.config import settings
from backend.llm.base import ExtractionFieldResult, ExtractionResult, LLMProvider
from backend.llm.ollama import OllamaProvider
from backend.llm.sarvam import SarvamProvider
from backend.rules.parser import (
    extract_all_amounts,
    parse_amount,
    parse_percentage,
    parse_tenure_months,
)

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(
        self,
        provider_name: Optional[str] = None,
        sarvam_provider: Optional[SarvamProvider] = None,
        ollama_provider: Optional[OllamaProvider] = None,
    ):
        self.provider_name = (provider_name or settings.llm_provider).lower()
        self.sarvam = sarvam_provider or SarvamProvider()
        self.ollama = ollama_provider or OllamaProvider()

    def _get_active_provider(self) -> LLMProvider:
        if self.provider_name == "ollama":
            return self.ollama
        return self.sarvam

    async def extract_with_fallback(
        self,
        transcript: str,
        schema: Dict[str, Any],
        language: str = "en",
    ) -> ExtractionResult:
        """
        Executes extraction with automatic fallback chain:
        Sarvam (8s timeout, 1 retry) -> Ollama (1 retry) -> Regex Parser alone.

        Security: Never logs transcripts or keys.
        """
        raw_extracted: Dict[str, Any] = {}
        successful_source: str = "regex_parser"

        # 1. Primary Provider attempt
        if self.provider_name == "sarvam":
            try:
                raw_extracted = await self.sarvam.extract(transcript, schema, language)
                successful_source = "sarvam"
            except Exception as e:
                # Security: log only error type without transcripts or keys
                logger.warning("Sarvam extraction failed (%s), falling back to Ollama.", type(e).__name__)
                try:
                    raw_extracted = await self.ollama.extract(transcript, schema, language)
                    successful_source = "ollama"
                except Exception as o_err:
                    logger.warning("Ollama fallback extraction failed (%s), using regex parser alone.", type(o_err).__name__)
                    raw_extracted = {}
                    successful_source = "regex_parser"
        elif self.provider_name == "ollama":
            try:
                raw_extracted = await self.ollama.extract(transcript, schema, language)
                successful_source = "ollama"
            except Exception as e:
                logger.warning("Ollama extraction failed (%s), using regex parser alone.", type(e).__name__)
                raw_extracted = {}
                successful_source = "regex_parser"
        else:
            successful_source = "regex_parser"

        # 2. Deterministic Regex Parser Verification
        # Every extracted number must match the regex parser output; on mismatch mark status="inferred" and ask for read-back.
        final_fields: Dict[str, Any] = {}
        field_meta: Dict[str, ExtractionFieldResult] = {}

        # Extract all amounts deterministically from the utterance
        regex_amounts = [amt for _, amt in extract_all_amounts(transcript)]
        regex_single_amount = parse_amount(transcript)
        regex_tenure = parse_tenure_months(transcript)
        regex_pct = parse_percentage(transcript)

        for field_name, expected_type in schema.items():
            llm_val = raw_extracted.get(field_name)

            # Check if field represents tenure
            if "tenure" in field_name or "duration" in field_name:
                matched_val = regex_tenure
                if llm_val is not None:
                    try:
                        llm_num = int(llm_val)
                    except (ValueError, TypeError):
                        llm_num = None

                    if matched_val is not None and llm_num is not None and llm_num == matched_val:
                        final_fields[field_name] = matched_val
                        field_meta[field_name] = ExtractionFieldResult(
                            value=matched_val,
                            status="confirmed",
                            source=successful_source,
                            readback_required=False,
                        )
                    elif llm_num is not None:
                        # Mismatch between LLM and regex
                        final_fields[field_name] = llm_num
                        field_meta[field_name] = ExtractionFieldResult(
                            value=llm_num,
                            status="inferred",
                            source=successful_source,
                            readback_required=True,
                            readback_message=f"I noted {llm_num} months. Could you please confirm if this tenure is correct?",
                        )
                elif matched_val is not None:
                    # Regex parser alone found the tenure
                    final_fields[field_name] = matched_val
                    field_meta[field_name] = ExtractionFieldResult(
                        value=matched_val,
                        status="confirmed",
                        source="regex_parser",
                        readback_required=False,
                    )
                else:
                    final_fields[field_name] = None
                    field_meta[field_name] = ExtractionFieldResult(
                        value=None,
                        status="missing",
                        source="default",
                    )
                continue

            # Check if field represents an amount / monetary value
            if "amount" in field_name or "income" in field_name or "investment" in field_name or "emi" in field_name or "due" in field_name:
                if llm_val is not None:
                    try:
                        llm_num = float(llm_val)
                    except (ValueError, TypeError):
                        llm_num = None

                    # Check match against regex parser output
                    is_match = False
                    if llm_num is not None:
                        if regex_single_amount is not None and abs(llm_num - regex_single_amount) < 0.01:
                            is_match = True
                        elif any(abs(llm_num - r_amt) < 0.01 for r_amt in regex_amounts):
                            is_match = True

                    if is_match and llm_num is not None:
                        final_fields[field_name] = llm_num
                        field_meta[field_name] = ExtractionFieldResult(
                            value=llm_num,
                            status="confirmed",
                            source=successful_source,
                            readback_required=False,
                        )
                    elif llm_num is not None:
                        # Number Mismatch detected: mark status="inferred" and ask for read-back
                        final_fields[field_name] = llm_num
                        candidate_hint = regex_single_amount if regex_single_amount is not None else "different value"
                        field_meta[field_name] = ExtractionFieldResult(
                            value=llm_num,
                            status="inferred",
                            source=successful_source,
                            readback_required=True,
                            readback_message=f"I noted ₹{llm_num:,.0f}, but detected {candidate_hint}. Could you please confirm the exact amount?",
                        )
                    else:
                        final_fields[field_name] = None
                        field_meta[field_name] = ExtractionFieldResult(
                            value=None,
                            status="missing",
                            source="default",
                        )
                elif regex_single_amount is not None:
                    # Fallback to regex parser alone!
                    final_fields[field_name] = regex_single_amount
                    field_meta[field_name] = ExtractionFieldResult(
                        value=regex_single_amount,
                        status="confirmed",
                        source="regex_parser",
                        readback_required=False,
                    )
                else:
                    final_fields[field_name] = None
                    field_meta[field_name] = ExtractionFieldResult(
                        value=None,
                        status="missing",
                        source="default",
                    )
                continue

            # Generic string / non-numeric fields
            if llm_val is not None:
                str_val = str(llm_val).strip()
                # If field looks like an identifier, check if full token exists in transcript
                if "id" in field_name or "code" in field_name or "account" in field_name:
                    id_matches = re.findall(r"[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)+", transcript)
                    for m in id_matches:
                        if str_val in m:
                            str_val = m
                            break
                final_fields[field_name] = str_val
                field_meta[field_name] = ExtractionFieldResult(
                    value=str_val,
                    status="confirmed",
                    source=successful_source,
                    readback_required=False,
                )
            elif successful_source == "regex_parser" or not llm_val:
                # Deterministic regex / pattern extraction for strings in fallback mode
                parsed_str = None
                if "id" in field_name or "code" in field_name or "account" in field_name:
                    id_matches = re.findall(r"[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)+", transcript)
                    if id_matches:
                        parsed_str = id_matches[0]
                    elif transcript.strip():
                        parsed_str = transcript.strip()
                elif field_name == "issue_type":
                    lower = transcript.lower()
                    if "bounce" in lower or "debit" in lower:
                        parsed_str = "auto_debit_bounce"
                    elif "restructure" in lower or "hardship" in lower:
                        parsed_str = "hardship_restructure"
                    elif "fail" in lower or "error" in lower or "declined" in lower:
                        parsed_str = "payment_failed"
                    else:
                        parsed_str = transcript.strip()
                elif field_name == "rejection_reason_code":
                    lower = transcript.lower()
                    if "foir" in lower or "obligation" in lower or "debt" in lower:
                        parsed_str = "HIGH_FOIR"
                    elif "score" in lower or "cibil" in lower or "credit" in lower:
                        parsed_str = "LOW_CREDIT_SCORE"
                    else:
                        parsed_str = transcript.strip().upper()
                elif expected_type == "str" and transcript.strip():
                    parsed_str = transcript.strip()

                if parsed_str is not None:
                    final_fields[field_name] = parsed_str
                    field_meta[field_name] = ExtractionFieldResult(
                        value=parsed_str,
                        status="confirmed",
                        source="regex_parser",
                        readback_required=False,
                    )
                else:
                    final_fields[field_name] = None
                    field_meta[field_name] = ExtractionFieldResult(
                        value=None,
                        status="missing",
                        source="default",
                    )

        return ExtractionResult(
            extracted_fields=final_fields,
            field_metadata=field_meta,
            source_provider=successful_source,
            confidence=1.0 if successful_source != "regex_parser" else 0.8,
            detected_language=language,
        )

    async def explain(
        self,
        facts: Dict[str, Any],
        language: str = "en",
        tone: str = "professional",
    ) -> str:
        """
        Explains backend-computed facts using active provider with fallback to Ollama,
        then fallback to deterministic template.
        Rule: Prompt receives ONLY backend-computed facts and must not add numbers, approval claims or advice.
        """
        # 1. Try active provider
        provider = self._get_active_provider()
        try:
            return await provider.explain(facts, language, tone)
        except Exception as e:
            logger.warning("Primary provider explain failed (%s), attempting Ollama fallback.", type(e).__name__)

        # 2. Try Ollama fallback if primary wasn't Ollama
        if provider != self.ollama:
            try:
                return await self.ollama.explain(facts, language, tone)
            except Exception as o_err:
                logger.warning("Ollama fallback explain failed (%s).", type(o_err).__name__)

        # 3. Deterministic template fallback
        journey = facts.get("journey_id", "financial")
        return (
            f"Here is your {journey.replace('_', ' ')} summary based on verified inputs. "
            "All figures are Sample non-binding calculations for demonstration purposes only."
        )


llm_service = LLMService()
