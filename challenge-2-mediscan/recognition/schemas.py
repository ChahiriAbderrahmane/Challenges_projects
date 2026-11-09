from typing import Literal

from pydantic import BaseModel, Field


class Product(BaseModel):
    product_id: str
    name: str
    strength: str
    form: str
    pack_size: int
    aliases: list[str] = Field(default_factory=list, exclude=True)


class Fields(BaseModel):
    product_name: str | None = None
    strength: str | None = None
    form: str | None = None
    pack_size: int | None = None
    observed_strengths: list[str] = Field(default_factory=list)


class Candidate(BaseModel):
    product_id: str
    name: str
    strength: str
    form: str
    pack_size: int
    score: float = Field(description="0–100 ranking utility, NOT a probability or OCR confidence")
    evidence: list[str]


class OCRWord(BaseModel):
    text: str
    bbox: tuple[int, int, int, int]
    confidence: float = Field(description="Tesseract word confidence 0–100; not product confidence")


class RecognitionResult(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{
        "request_id": "7f1e2d3c4b5a", "status": "ambiguous", "raw_ocr_text": "Zefrano",
        "extracted_fields": {"product_name": "zefrano", "strength": None, "form": None, "pack_size": None, "observed_strengths": []},
        "matched_product": None, "candidates": [],
        "matching_evidence": ["Strength is missing. Provide a clearer front-label image."],
        "warnings": ["Fictional demonstration catalogue."], "processing_time_ms": 230.5, "ocr_words": []
    }]}}
    request_id: str
    status: Literal["matched", "ambiguous", "unknown", "unreadable"]
    raw_ocr_text: str
    primary_ocr_text: str | None = Field(default=None, description="Primary engine pass, without repeated auxiliary passes; used for comparable baseline CER/WER")
    extracted_fields: Fields
    matched_product: Candidate | None = None
    candidates: list[Candidate] = Field(default_factory=list)
    matching_evidence: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    processing_time_ms: float
    ocr_words: list[OCRWord] = Field(default_factory=list)


class ErrorDetail(BaseModel):
    request_id: str
    category: str
    message: str


class ErrorResponse(BaseModel):
    detail: ErrorDetail
