import json

import pytest

from recognition.config import Settings
from recognition.extraction import extract, normalize
from recognition.matching import load_catalogue, match


def identify(text):
    settings = Settings()
    products, _ = load_catalogue(settings.catalogue)
    fields, notes = extract(text)
    return match(fields, products, json.loads(open(settings.thresholds).read()), bool(notes))


def test_normalization_preserves_meaning():
    assert normalize("GÉLULES ٥٠٠ ۱۲") == "gelules 500 12"
    assert normalize("أقراص") != normalize("اقراص")
    assert normalize("زَفـرانو") == "زفرانو"


@pytest.mark.parametrize("text,strength,pack", [
    ("Zefrano\n0,5 g\n12 comprimés", "500 mg", 12),
    ("زفرانو\n٥٠٠ ملغ\n١٢ أقراص", "500 mg", 12),
    ("A\n250 mg / 5 ml\n100 ml", "50 mg/ml", None),
    ("A\n500 µg", "0.5 mg", None),
    ("Zefrano\nPrendre 2 comprimés de 500 mg par jour", None, None),
])
def test_fields(text, strength, pack):
    fields, _ = extract(text)
    assert fields.strength == strength
    assert fields.pack_size == pack


def test_clear_arabic_alias_matches_without_transliteration():
    status, product, _, _ = identify("زفرانو\n٥٠٠ ملغ\n١٢ أقراص")
    assert status == "matched" and product.product_id == "demo-01-500"


def test_strength_conflict_dominates_similar_name():
    status, product, _, _ = identify("Zefrano\n900 mg\n12 comprimés")
    assert status == "unknown" and product is None


@pytest.mark.parametrize("text", ["Zefrano", "Zefrano 100 mg 500 mg", "Zefrano 500 mg + 125 mg", "Zefrano 5%", "Zefrano 500 mg 12 gélules"])
def test_insufficient_or_conflicting_fields_never_accept(text):
    status, product, _, _ = identify(text)
    assert status != "matched" and product is None


def test_unknown_not_nearest_neighbor():
    status, product, candidates, _ = identify("Xylophene\n750 mg\n20 comprimés")
    assert status == "unknown" and product is None and candidates == []


def test_missing_pack_does_not_choose_between_pack_variants():
    settings = Settings()
    products, _ = load_catalogue(settings.catalogue)
    p = products[0]
    products.append(p.model_copy(update={"product_id": "other-pack", "pack_size": 24}))
    fields, _ = extract(f"{p.name}\n{p.strength}")
    status, product, _, _ = match(fields, products, json.loads(open(settings.thresholds).read()))
    assert status == "ambiguous" and product is None


def test_similar_spelling_cannot_override_exact_brand_strength_conflict():
    from recognition.schemas import Product
    products = [Product(product_id="exact", name="Demonstrationbrand", strength="100 mg", form="tablet", pack_size=12),
                Product(product_id="near", name="Demonstrationbrant", strength="500 mg", form="tablet", pack_size=12)]
    fields, _ = extract("Demonstrationbrand\n500 mg\n12 comprimés")
    thresholds = json.loads(open(Settings().thresholds).read())
    status, product, _, evidence = match(fields, products, thresholds)
    assert status != "matched" and product is None
    assert any("similar spelling" in e for e in evidence)


@pytest.mark.parametrize("visible,other", [("Complex B12", "Complex B6"), ("Formula 1", "Formula 2")])
def test_numeric_product_designators_are_not_discarded(visible, other):
    from recognition.matching import name_similarity
    fields, _ = extract(visible+"\n100 mg\n12 comprimés")
    assert name_similarity(fields.product_name, visible) == 1
    assert name_similarity(fields.product_name, other) == 0


def test_sachets_are_pack_quantity_not_strength_or_treatment_dosage():
    fields, notes = extract("Doliprane\n8 sachets-dose\npoudre pour solution buvable\n1000 mg")
    assert fields.strength == "1000 mg"
    assert fields.form == "powder_oral_solution"
    assert fields.pack_size == 8
    assert not notes


def test_sourced_doliprane_variant_and_strength_conflict():
    status, product, _, _ = identify("Doliprane\n1000 mg\n8 sachets-dose\npoudre pour solution buvable")
    assert status == "matched" and product.product_id == "fr-cip-3400936246980"
    status, product, _, _ = identify("Doliprane\n500 mg\n8 sachets-dose\npoudre pour solution buvable")
    assert status == "unknown" and product is None


def test_bare_number_or_conflicting_ocr_passes_cannot_identify_strength():
    text = "Doliprane\n1000\n8 sachets-dose\npoudre pour solution buvable"
    status, product, _, _ = identify(text)
    assert status == "ambiguous" and product is None
    text += "\n[Confirmed adjacent number and unit crops]\n1000 mg\n[other pass]\n100 mg"
    status, product, _, _ = identify(text)
    assert status != "matched" and product is None
