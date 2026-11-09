from dataclasses import dataclass
import os
import re

from PIL import Image

from .errors import RecognitionError
from .schemas import OCRWord


@dataclass
class OCRResult:
    text: str
    words: list[OCRWord]
    primary_text: str | None = None


class TesseractOCR:
    """One native API per serialized worker; never shared concurrently."""

    def __init__(self, tessdata: str):
        os.environ.setdefault("OMP_THREAD_LIMIT", "1")
        try:
            import tesserocr
            self.module = tesserocr
            self.api = tesserocr.PyTessBaseAPI(path=tessdata, lang="fra+ara", psm=tesserocr.PSM.AUTO)
            if not {"fra", "ara"}.issubset(self.api.GetLoadedLanguages()):
                raise RuntimeError("Required languages not loaded")
        except (ImportError, RuntimeError, OSError):
            raise RecognitionError(503, "ocr_dependency", "Arabic/French OCR is unavailable; check engine and language models.") from None

    def read(self, image: Image.Image, psm=None) -> OCRResult:
        self.api.SetPageSegMode(self.module.PSM.AUTO if psm is None else psm)
        self.api.SetImage(image)
        text = self.api.GetUTF8Text().strip()
        words = []
        iterator = self.api.GetIterator()
        if iterator:
            level = self.module.RIL.WORD
            while True:
                try:
                    word = iterator.GetUTF8Text(level)
                    box = iterator.BoundingBox(level)
                except RuntimeError:  # empty/non-text layout elements
                    word, box = None, None
                if word and box:
                    words.append(OCRWord(text=word.strip(), bbox=box, confidence=iterator.Confidence(level)))
                if not iterator.Next(level):
                    break
        self.api.Clear()
        return OCRResult(text, words)

    def read_packaging(self, image: Image.Image, baseline: OCRResult) -> OCRResult:
        """Bounded layout fallback for oversized brand/digits and small adjacent units.

        Keep every raw pass. Never infer a unit from the catalogue or treat a bare
        number as strength. Confirm a numeric crop independently, then read only
        its immediately adjacent region. Conflicting readings remain in the text.
        """
        block = self.read(image, self.module.PSM.SINGLE_BLOCK)
        sparse = self.read(image, self.module.PSM.SPARSE_TEXT)
        parts = [("baseline", baseline), ("single block", block), ("sparse text", sparse)]
        words = [word for _, result in parts for word in result.words]
        refinements = []
        attempted = 0
        seen = set()
        for word in block.words:
            numeric = word.text.strip(".,;:")
            if not re.fullmatch(r"\d{2,5}", numeric):
                continue
            x1, y1, x2, y2 = word.bbox
            height = y2 - y1
            if height < 12 or word.bbox in seen:
                continue
            seen.add(word.bbox)
            attempted += 1
            if attempted > 2:
                break
            pad = max(2, round(height * 0.1))
            number_box = (max(0, x1-pad), max(0, y1-pad), min(image.width, x2+pad), min(image.height, y2+pad))
            confirmation = self.read(image.crop(number_box), self.module.PSM.SINGLE_LINE)
            # Require agreement on all digits, including zeroes; never repair 100 to 1000.
            if confirmation.text.strip() != numeric:
                continue
            unit_box = (max(0, x2-pad), max(0, y1), min(image.width, x2+round(height*1.6)), min(image.height, y2+round(height*0.6)))
            if unit_box[2] <= unit_box[0]:
                continue
            unit_result = self.read(image.crop(unit_box), self.module.PSM.SINGLE_LINE)
            if unit_result.text.strip().lower() not in {"mg", "g", "mcg", "µg", "μg", "ملغ", "مجم"}:
                continue
            refinements.append(f"{numeric} {unit_result.text.strip()}")
            for result, box in ((confirmation, number_box), (unit_result, unit_box)):
                for detected in result.words:
                    a, b, c, d = detected.bbox
                    words.append(detected.model_copy(update={"bbox": (a+box[0], b+box[1], c+box[0], d+box[1])}))
        text = "\n\n".join(f"[{name}]\n{result.text}" for name, result in parts)
        if refinements:
            text += "\n\n[Confirmed adjacent number and unit crops]\n" + "\n".join(refinements)
        return OCRResult(text, words, primary_text=baseline.text)

    def close(self):
        self.api.End()
