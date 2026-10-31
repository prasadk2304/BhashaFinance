from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field as PydanticField


class FieldStatus(str, Enum):
    MISSING = "missing"
    INFERRED = "inferred"
    CONFIRMED = "confirmed"


class FieldSource(str, Enum):
    USER_INPUT = "user_input"
    REGEX_PARSER = "regex_parser"
    LLM_EXTRACTION = "llm_extraction"
    RULE_INFERENCE = "rule_inference"
    DEFAULT = "default"


class Field(BaseModel):
    name: str
    value: Optional[Any] = None
    status: FieldStatus = FieldStatus.MISSING
    source: FieldSource = FieldSource.DEFAULT
    label: Optional[str] = None
    unit: Optional[str] = None
    prompt_question: Optional[str] = None

    def mark_confirmed(self, val: Any, source: FieldSource = FieldSource.USER_INPUT):
        self.value = val
        self.status = FieldStatus.CONFIRMED
        self.source = source

    def mark_inferred(self, val: Any, source: FieldSource = FieldSource.RULE_INFERENCE):
        self.value = val
        self.status = FieldStatus.INFERRED
        self.source = source

    def mark_missing(self):
        self.value = None
        self.status = FieldStatus.MISSING
        self.source = FieldSource.DEFAULT


class ConsentState(BaseModel):
    requested: bool = False
    granted: bool = False
    consent_text: Optional[str] = None
    granted_at: Optional[str] = None
    method: Optional[str] = None  # e.g., "voice", "text_input", "explicit_button"

    def grant(self, text: str, method: str = "voice"):
        self.granted = True
        self.requested = True
        self.consent_text = text
        self.granted_at = datetime.now(timezone.utc).isoformat()
        self.method = method

    def revoke(self):
        self.granted = False
        self.granted_at = None


class JourneyStatus(str, Enum):
    COLLECTING = "collecting"
    CALCULATED = "calculated"
    AWAITING_CONSENT = "awaiting_consent"
    SUBMITTED = "submitted"
    REJECTED = "rejected"


class CalculationResult(BaseModel):
    journey_id: str
    sample_label: str = "Sample"
    is_synthetic: bool = True
    disclosures: List[str] = PydanticField(default_factory=list)
    metrics: Dict[str, Any] = PydanticField(default_factory=dict)
    schedule: Optional[List[Dict[str, Any]]] = None
    explanation: Optional[str] = None


class MessageEntry(BaseModel):
    sender: str  # "user" | "assistant" | "system"
    text: str
    timestamp: str = PydanticField(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    audio_url: Optional[str] = None


class JourneyState(BaseModel):
    session_id: str
    journey_id: str
    status: JourneyStatus = JourneyStatus.COLLECTING
    fields: Dict[str, Field] = PydanticField(default_factory=dict)
    calculation: Optional[CalculationResult] = None
    consent: ConsentState = PydanticField(default_factory=ConsentState)
    messages: List[MessageEntry] = PydanticField(default_factory=list)
    created_at: str = PydanticField(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = PydanticField(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def get_field(self, name: str) -> Optional[Field]:
        return self.fields.get(name)

    def set_field(
        self,
        name: str,
        value: Any,
        status: FieldStatus,
        source: FieldSource,
        label: Optional[str] = None,
        unit: Optional[str] = None,
        prompt_question: Optional[str] = None,
    ) -> Field:
        field = self.fields.get(name)
        if field is None:
            field = Field(
                name=name,
                value=value,
                status=status,
                source=source,
                label=label,
                unit=unit,
                prompt_question=prompt_question,
            )
            self.fields[name] = field
        else:
            field.value = value
            field.status = status
            field.source = source
            if label:
                field.label = label
            if unit:
                field.unit = unit
            if prompt_question:
                field.prompt_question = prompt_question
        self.update_timestamp()
        return field

    def get_missing_required_fields(self, required_field_names: List[str]) -> List[str]:
        missing = []
        for name in required_field_names:
            field = self.fields.get(name)
            if not field or field.status == FieldStatus.MISSING or field.value is None:
                missing.append(name)
        return missing

    def is_ready_for_calculation(self, required_field_names: List[str]) -> bool:
        return len(self.get_missing_required_fields(required_field_names)) == 0

    def can_submit(self) -> bool:
        """Rule: No submission without explicit consent."""
        return self.consent.granted and self.status == JourneyStatus.AWAITING_CONSENT

    def to_values_dict(self) -> Dict[str, Any]:
        """Extracts confirmed and inferred values as a simple dictionary for calculation."""
        return {
            k: v.value
            for k, v in self.fields.items()
            if v.value is not None and v.status in (FieldStatus.CONFIRMED, FieldStatus.INFERRED)
        }

