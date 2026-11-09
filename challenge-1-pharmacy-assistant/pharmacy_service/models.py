from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

Intent = Literal['medication_request', 'availability', 'pharmacy_phone', 'pharmacy_location', 'greeting', 'out_of_scope', 'unknown']
Language = Literal['arabic', 'darija', 'french', 'mixed', 'undetermined']

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

class Medication(StrictModel):
    expressed_name: str = Field(min_length=1, max_length=100)
    quantity: float | None = Field(default=None, gt=0, le=10000)
    unit: str | None = Field(default=None, max_length=40)
    dosage: str | None = Field(default=None, max_length=40)
    form: str | None = Field(default=None, max_length=40)
    normalized_name: str | None = Field(default=None, max_length=100)
    catalog_id: str | None = Field(default=None, max_length=40)
    match_status: Literal['found', 'ambiguous', 'unknown'] = 'unknown'

class Pharmacy(StrictModel):
    name: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=100)

class Context(StrictModel):
    intents: list[Intent] = Field(default_factory=list, max_length=7)
    medications: list[Medication] = Field(default_factory=list, max_length=10)
    pharmacy: Pharmacy = Field(default_factory=Pharmacy)

class AnalyzeRequest(StrictModel):
    model_config = ConfigDict(extra='forbid')
    text: str = Field(min_length=1, max_length=4000, examples=['Avez-vous du Doliprane 500 mg ?'])
    context: Context | None = None

    @field_validator('text')
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError('text must not be blank')
        return value

class Extraction(StrictModel):
    language: Language
    intents: list[Intent] = Field(min_length=1, max_length=7)
    medications: list[Medication] = Field(default_factory=list, max_length=10)
    pharmacy: Pharmacy = Field(default_factory=Pharmacy)
    reply: str = Field(default='', max_length=500)

class AnalyzeResponse(StrictModel):
    request_id: str
    original_text: str
    language: Language
    intents: list[Intent]
    medications: list[Medication]
    pharmacy: Pharmacy
    needs_clarification: bool
    missing_fields: list[str]
    clarification_question: str | None
    reply: str
    warnings: list[str]
