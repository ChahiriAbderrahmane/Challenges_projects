"""Create explicitly synthetic regression fixtures, never pretend these are photos."""
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps, features

ROOT = Path(__file__).resolve().parent.parent
FR_FONT = "/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono.ttf"
AR_FONT = "/usr/share/fonts/google-noto-vf/NotoSansArabic[wght].ttf"
BRANDS = [("Zefrano", "زفرانو"), ("Lumavex", "لومافكس"), ("Noravel", "نورافيل"),
          ("Tazorin", "تازورين"), ("Belmora", "بيلمورا")]


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    if not features.check_feature("raqm"):
        raise RuntimeError("Pillow RAQM shaping required for valid Arabic fixtures")
    directory = ROOT / "data/demo/images"
    directory.mkdir(parents=True, exist_ok=True)
    products, manifest = [], []

    def save(image, identifier, family, split, language, condition, text, product_id, fields, kind="synthetic_render"):
        path = directory / f"{identifier}.png"
        image.save(path)
        manifest.append(dict(image_id=identifier, path=str(path.relative_to(ROOT)),
                             sha256=hashlib.sha256(path.read_bytes()).hexdigest(), family_id=family,
                             split=split, language=language, condition=condition, kind=kind,
                             transcription=text, transcription_source="Exact generator input; not a manual photograph transcription",
                             product_id=product_id, fields=fields,
                             provenance="Locally rendered fictional label; scripts/prepare_demo.py", rights="CC0-1.0 synthetic fixture; font rights remain with their owners"))

    for i, (brand, arabic) in enumerate(BRANDS):
        form = "capsule" if i % 2 else "tablet"
        fr_form, ar_form = ("gélules", "كبسولات") if i % 2 else ("comprimés", "أقراص")
        for strength in (100, 250, 500):
            pid = f"demo-{i+1:02}-{strength}"
            pack = 20 if i % 2 else 12
            expected = dict(strength=f"{strength} mg", form=form, pack_size=pack)
            products.append(dict(product_id=pid, name=brand, aliases=[arabic], **expected))
            for split in ("dev", "test"):
                for language in ("fr", "ar"):
                    identifier = f"{pid}-{language}-{split}"
                    family = identifier
                    if language == "fr":
                        lines = [brand, f"{strength} mg", f"{pack} {fr_form}"]
                        font = ImageFont.truetype(FR_FONT, 60 if split == "dev" else 54)
                    else:
                        digits = str(strength).translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))
                        count = str(pack).translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))
                        lines = [arabic, f"{digits} ملغ", f"{count} {ar_form}"]
                        font = ImageFont.truetype(AR_FONT, 65 if split == "dev" else 58)
                    image = Image.new("RGB", (1100, 600), "white")
                    draw = ImageDraw.Draw(image)
                    # Separate source layouts, not degraded copies across splits.
                    left, top = (110, 60) if split == "dev" else (180, 100)
                    for j, line in enumerate(lines):
                        if language == "ar":
                            draw.text((920, top+j*140), line, font=font, fill="black", anchor="ra", direction="rtl", language="ar")
                        else:
                            draw.text((left, top+j*140), line, font=font, fill="black")
                    text = "\n".join(lines)
                    save(image, identifier, family, split, language, "clear", text, pid, expected)
                    if split == "test" and strength == 250 and i < 2:
                        variants = {
                            "rotation90": image.rotate(90, expand=True),
                            "blur": image.filter(ImageFilter.GaussianBlur(2)),
                            "low_contrast": ImageEnhance.Contrast(image).enhance(0.25),
                            "uneven_lighting": ImageChops.multiply(image, ImageOps.colorize(
                                Image.linear_gradient("L").resize(image.size), "#777777", "#ffffff")),
                        }
                        for condition, changed in variants.items():
                            save(changed, identifier+"-"+condition, family, split, language, condition,
                                 text, pid, expected, "synthetic_degradation")
                        save(image.crop((0, 0, 1100, 230)), identifier+"-partial", family, split,
                             language, "partial", lines[0], pid,
                             dict(strength=None, form=None, pack_size=None), "synthetic_degradation")
    for split in ("dev", "test"):
        for label, text in (("unknown", "Xylophene\n750 mg\n20 comprimés"),
                            ("nonmed", "Bonjour\nSavon de toilette"),
                            ("conflict", "Zefrano\n900 mg\n12 comprimés"), ("blank", "")):
            image = Image.new("RGB", (1100, 600), "white")
            ImageDraw.Draw(image).multiline_text((100, 80 if split == "dev" else 120), text,
                                                 font=ImageFont.truetype(FR_FONT, 56), fill="black", spacing=35)
            save(image, f"negative-{label}-{split}", f"negative-{label}-{split}", split, "fr", label,
                 text, None, dict(strength=None, form=None, pack_size=None))
    dump(ROOT / "data/catalogue.json", dict(version="demo-1", synthetic=True,
         supplements=["catalogue-reference.json"],
         provenance="Fictional labels authored by scripts/prepare_demo.py; no claim of marketed products or Moroccan coverage",
         usage_rights="CC0-1.0 for fictional catalogue records", products=products))
    dump(ROOT / "data/demo/manifest.json", dict(version=1, synthetic_only=True, images=manifest,
         fonts={language: {"path": path, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}
                for language, path in (("fr", FR_FONT), ("ar", AR_FONT))},
         split_policy="Independent rendered layouts; all degradations remain with their original family. No photographs available."))
    print(f"Prepared {len(products)} fictional variants and {len(manifest)} synthetic images; zero real photos.")


if __name__ == "__main__":
    main()
