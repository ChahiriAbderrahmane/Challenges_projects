import re
import unicodedata
from decimal import Decimal

from .schemas import Fields

FORMS = {
    "tablet": r"\bcomprimes?\b|\btablets?\b|أقراص|اقراص",
    "capsule": r"\bgelules?\b|\bcapsules?\b|كبسولات",
    "syrup": r"\bsirop\b|شراب",
    "cream": r"\bcreme\b|كريم",
    "powder_oral_solution": r"\bpoudre\s+pour\s+solution\s+buvable\b",
}
UNIT = r"mg|mcg|ug|μg|g|ml|مجم|ملغ|ميكروغرام|غ|مل"
STRENGTH = re.compile(rf"(?<![\w.])(\d+(?:[.,٫]\d+)?)\s*({UNIT})(?![a-z\u0600-\u06ff])(?:\s*/\s*(\d+(?:[.,٫]\d+)?)?\s*(ml|مل))?", re.I)
DOSE = re.compile(r"par jour|fois par|/jour|posologie|prendre|يوم|مرات|جرعة")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    text = "".join(str(unicodedata.digit(c)) if c.isdigit() else c for c in text)
    text = "".join("".join(c for c in unicodedata.normalize("NFD", char) if not unicodedata.combining(c))
                   if "LATIN" in unicodedata.name(char, "") else char for char in text)
    text = "".join(c for c in text if not "\u064b" <= c <= "\u0652")
    # Preserve Arabic letters including hamza distinctions; only remove tatweel.
    return "".join(c for c in unicodedata.normalize("NFC", text) if unicodedata.category(c) != "Cf").replace("ـ", "").replace("٫", ".")


def number(value: str) -> str:
    return format(Decimal(value.replace(",", ".")).normalize(), "f")


def canonical_strength(match: re.Match) -> str | None:
    value, unit, denominator, denominator_unit = match.groups()
    unit = {"مجم": "mg", "ملغ": "mg", "ميكروغرام": "mcg", "ug": "mcg", "μg": "mcg", "غ": "g", "مل": "ml"}.get(unit.lower(), unit.lower())
    if unit == "ml":  # bottle volume is not product strength
        return None
    quantity = Decimal(value.replace(",", "."))
    if unit == "g":
        quantity, unit = quantity * 1000, "mg"
    if unit == "mcg":
        quantity, unit = quantity / 1000, "mg"
    if denominator_unit:
        divisor = Decimal((denominator or "1").replace(",", "."))
        if divisor == 0:
            return None
        return f"{number(str(quantity / divisor))} {unit}/ml"
    return f"{number(str(quantity))} {unit}"


def extract(text: str) -> tuple[Fields, list[str]]:
    normalized = normalize(text)
    lines = [line.strip() for line in normalized.splitlines()
             if line.strip() and not DOSE.search(line) and not (line.strip().startswith("[") and line.strip().endswith("]"))]
    visible = "\n".join(lines)
    strengths = sorted({s for m in STRENGTH.finditer(visible) if (s := canonical_strength(m))})
    forms = [form for form, pattern in FORMS.items() if re.search(pattern, visible)]
    pack_pattern = r"(?:boite\s*(?:de)?|pack\s*(?:of)?|علبة\s*(?:من)?)\s*(\d+)\b|\b(\d+)\s*(?:comprimes?|gelules?|tablets?|capsules?|sachets?(?:[\s‐‑–-]*doses?)?|أقراص|اقراص|كبسولات|أكياس|اكياس)\b"
    packs = {int(a or b) for a, b in re.findall(pack_pattern, visible)}
    names = []
    for line in lines:
        cleaned = STRENGTH.sub(" ", line)
        cleaned = re.sub(pack_pattern, " ", cleaned)
        for pattern in FORMS.values():
            cleaned = re.sub(pattern, " ", cleaned)
        cleaned = re.sub(r"[^\w\s-]", " ", cleaned)
        cleaned = " ".join(cleaned.split())
        if cleaned:
            names.append(cleaned)
    notes = []
    if len(strengths) > 1:
        notes.append("Multiple strengths are visible; product strength is unresolved.")
    if len(forms) > 1 or len(packs) > 1:
        notes.append("Conflicting form or pack-size evidence is unresolved.")
    if re.search(r"\d\s*%|\d\s*[/+]\s*\d+\s*(?:mg|g|ملغ)", visible):
        notes.append("Unsupported compound or percentage strength; verify the label.")
        strength = None
    else:
        strength = strengths[0] if len(strengths) == 1 else None
    return Fields(product_name="\n".join(names) or None, strength=strength,
                  observed_strengths=strengths, form=forms[0] if len(forms) == 1 else None,
                  pack_size=next(iter(packs)) if len(packs) == 1 else None), notes
