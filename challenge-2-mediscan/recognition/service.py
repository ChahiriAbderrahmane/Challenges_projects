import json
import re
import time
from pathlib import Path

from .config import Settings
from .extraction import extract, normalize
from .imaging import prepare
from .matching import load_catalogue, match
from .schemas import RecognitionResult


class RecognitionService:
    def __init__(self, settings: Settings, ocr):
        self.settings = settings
        self.ocr = ocr
        self.products, self.catalogue = load_catalogue(settings.catalogue)
        self.thresholds = json.loads(Path(settings.thresholds).read_text())

    def recognize(self, data: bytes, request_id: str) -> dict:
        start = time.perf_counter()
        image, notes = prepare(data, self.settings)
        best = None
        # Bounded fallback, preserve baseline; never concatenate contradictory passes.
        for angle in (0, 90, 270, 180):
            result = self.ocr.read(image if angle == 0 else image.rotate(angle, expand=True))
            fields, extraction_notes = extract(result.text)
            if angle == 0 and fields.product_name and not fields.strength and hasattr(self.ocr, "read_packaging"):
                result = self.ocr.read_packaging(image, result)
                fields, extraction_notes = extract(result.text)
                notes.append("Used bounded packaging-layout OCR fallback; raw passes and confirmed adjacent number/unit crops are preserved.")
            unresolved = bool(extraction_notes)
            status, product, candidates, evidence = match(fields, self.products, self.thresholds, unresolved)
            if not any(c.isalpha() for c in result.text):
                status, product, candidates = "unreadable", None, []
                evidence = ["No legible text. Provide a sharper, well-lit image of the front label."]
            # Prefer coherent name+strength, then ranking utility; not mean OCR confidence.
            quality = (status == "matched", max((c.score for c in candidates), default=0),
                       sum(value is not None for value in (fields.strength, fields.form, fields.pack_size)), len(result.words))
            if best is None or quality > best[0]:
                best = (quality, result, fields, status, product, candidates, evidence, extraction_notes, angle)
            if status == "matched" or (angle == 0 and candidates and fields.strength):
                break
        _, result, fields, status, product, candidates, evidence, extraction_notes, angle = best
        if product and fields.product_name:
            reference = next(p for p in self.products if p.product_id == product.product_id)
            # Return an actually observed exact alias, not the catalogue name for
            # a fuzzy match and not all the unrelated packaging text.
            for alias in sorted([reference.name, *reference.aliases], key=len, reverse=True):
                visible = re.search(r"(?<!\w)" + re.escape(normalize(alias)) + r"(?!\w)", fields.product_name)
                if visible:
                    fields.product_name = visible.group()
                    break
        if angle:
            notes.append(f"Selected orthogonal rotation {angle} degrees; word boxes reference that OCR image.")
        if product and product.product_id in self.catalogue.get("synthetic_product_ids", []):
            notes.append("Demonstration catalogue: fictional products; real-world coverage is not established.")
        elif self.catalogue.get("contains_synthetic"):
            notes.append("Limited catalogue includes fictional demonstration records and sourced French references; country and artwork version are not verified.")
        return RecognitionResult(request_id=request_id, status=status, raw_ocr_text=result.text,
                                 primary_ocr_text=result.primary_text or result.text,
                                 extracted_fields=fields, matched_product=product, candidates=candidates,
                                 matching_evidence=evidence, warnings=notes + extraction_notes,
                                 ocr_words=result.words,
                                 processing_time_ms=round((time.perf_counter() - start) * 1000, 2)).model_dump()
