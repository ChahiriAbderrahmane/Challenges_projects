import json
import re
from difflib import SequenceMatcher
from pathlib import Path

from .extraction import normalize
from .schemas import Candidate, Fields, Product


def load_catalogue(path: str) -> tuple[list[Product], dict]:
    catalogue = json.loads(Path(path).read_text())
    # Keep authored reference data separate from regenerable synthetic fixtures.
    sources = [catalogue]
    for supplement in catalogue.get("supplements", []):
        sources.append(json.loads((Path(path).parent / supplement).read_text()))
    products = [Product.model_validate(p) for source in sources for p in source["products"]]
    if len({p.product_id for p in products}) != len(products) or not products:
        raise ValueError("Catalogue IDs must be unique and catalogue nonempty")
    metadata = dict(catalogue)
    metadata["synthetic"] = all(source.get("synthetic", False) for source in sources)
    metadata["contains_synthetic"] = any(source.get("synthetic", False) for source in sources)
    metadata["synthetic_product_ids"] = [p["product_id"] for source in sources if source.get("synthetic") for p in source["products"]]
    return products, metadata


def name_similarity(observed: str, alias: str) -> float:
    tokens = re.findall(r"[^\W_]+(?:[-'][^\W_]+)*", normalize(observed))
    expected = re.findall(r"[^\W_]+(?:[-'][^\W_]+)*", normalize(alias))
    n = len(expected)
    if not n or not tokens:
        return 0
    reference = " ".join(expected)
    windows = [" ".join(tokens[i:i+n]) for i in range(len(tokens))]
    # Numeric brand designators (B12 vs B6, Formula 1 vs Formula 2) are meaningful,
    # not OCR punctuation or strength, and must never be fuzzily interchanged.
    return max((SequenceMatcher(None, window, reference).ratio() for window in windows
                if re.findall(r"\d+", window) == re.findall(r"\d+", reference)), default=0)


def match(fields: Fields, products: list[Product], thresholds: dict, unresolved: bool = False):
    ranked = []
    for p in products:
        similarity = max(name_similarity(fields.product_name or "", a) for a in [p.name, *p.aliases])
        if similarity < thresholds["candidate_name"]:
            continue
        score = 70 * similarity
        evidence = [f"name_similarity={similarity:.3f}"]
        conflicts = []
        for field, weight in (("strength", 15), ("form", 8), ("pack_size", 7)):
            observed = getattr(fields, field)
            if observed is None:
                evidence.append(f"{field}: missing")
            elif observed == getattr(p, field):
                score += weight
                evidence.append(f"{field}: agrees")
            else:
                conflicts.append(field)
                evidence.append(f"{field}: CONFLICT")
                score -= 60
        candidate = Candidate(**p.model_dump(), score=round(max(0, score), 2), evidence=evidence)
        ranked.append((candidate, similarity, conflicts))
    ranked.sort(key=lambda r: (-r[0].score, r[0].product_id))
    candidates = [r[0] for r in ranked[:3]]
    if not ranked:
        return "unknown", None, [], ["No catalogue name has sufficient visible support. Provide a clearer box image or check catalogue coverage."]
    top, similarity, conflicts = ranked[0]
    strongest_name = max(r[1] for r in ranked)
    name_strength_conflict = (similarity < strongest_name and strongest_name >= thresholds["accept_name"]
                              and any(r[1] == strongest_name and "strength" in r[2] for r in ranked))
    margin = top.score - ranked[1][0].score if len(ranked) > 1 else 100
    evidence = [f"ranking_margin={margin:.2f}; scores are utilities, not probabilities"]
    if (similarity >= thresholds["accept_name"] and fields.strength is not None
            and not conflicts and not unresolved and not name_strength_conflict and top.score >= thresholds["accept_score"]
            and margin >= thresholds["margin"]):
        return "matched", top, candidates, evidence + ["Visible name and strength supported; no conflicting fields."]
    reason = "Conflicting evidence prevents acceptance." if conflicts or unresolved or name_strength_conflict else "Insufficient identifying evidence or insufficient separation between variants."
    if name_strength_conflict:
        evidence.append("The strongest visible name conflicts with the observed strength; a similar spelling cannot override it.")
    status = "unknown" if conflicts and all(r[2] for r in ranked) else "ambiguous"
    return status, None, candidates, evidence + [reason, "Provide a clearer image showing name, strength, form and pack quantity."]
