# Dataset, provenance and collection gap

Update: a user-provided Doliprane packshot is now referenced separately in
`data/local-regressions/manifest.json`, with unknown artwork redistribution
rights and no exhaustive transcription. Its source-verified French catalogue
record is in `data/catalogue-reference.json`. It is a private development
regression; it does not change the 88-image synthetic benchmark or satisfy the
licensed-photograph collection target.

## What is actually available
`data/demo/manifest.json` and `data/demo/images/` are **synthetic regression
fixtures**, created by `python -m scripts.prepare_demo`. The catalogue has 15
fictional product variants (five invented names, three strengths each). These are
not verified marketed medicines, and no active ingredients are asserted.

The fixture set has 88 images: 60 independently rendered clear labels (15 variants
× French/Arabic × dev/test), 20 synthetic degradations and eight negatives.
There are **zero real packaging photographs**. This does **not** satisfy the
collection target of 15 real variants and 60 real images.

Development: 34 images. Held-out test: 54 images. Each original rendered layout
has a family ID; its rotations, blur, partial crops, gradients and contrast changes
remain exclusively in its split. Independent layouts share the catalogue and
font; this is a deliberately easy regression benchmark, not independent real-world
photographic diversity. There are four test degradations per condition: rotation
90°, Gaussian blur radius 2, contrast factor .25, illumination gradient, and
partial name-only visibility. No claim of naturally difficult images is made.
Negatives per split: absent fictional product, non-medication text, a known brand
with unsupported strength and blank image. None is a real non-medication photo.

Each manifest row records image ID, path, SHA-256, original family, split,
language, condition, synthetic kind, product ID (null for unknown), expected
visible fields, transcript, origin and usage rights. Text references are generator
input, **not manually transcribed real samples**. Arabic shaping requires RAQM;
font file hashes are recorded. Fonts are installed system assets, not redistributed:
[DejaVu](https://dejavu-fonts.github.io/) and
[Noto Arabic](https://github.com/notofonts/arabic). Fixture content and fictional
catalogue records are offered under CC0-1.0; font licenses remain applicable.

## Real-photo collection plan
1. Obtain permission to photograph and redistribute box fronts (avoid personal
   labels). Record photographer consent/license, date, source and source URL if
   applicable. Do not copy retailer images without verified rights.
2. Collect at least **15 marketed variants × four separate captures = 60 photos**,
   plus at least 15 unknown/non-medication negatives. Include multiple strengths
   and pack sizes of the same brand, similar brand spellings, Arabic-only,
   French-only and bilingual labels. Include Arabic-Indic and Latin digits.
3. Capture clear fronts, natural illumination changes, rotations, blur and partial
   visibility. Each capture is a photo, not an augmented duplicate. Ensure clean
   references remain possible. Avoid falsifying genuine labels to manufacture data.
4. Verify catalogue ID, official name, strength, form, pack and optional ingredient
   against a manufacturer/regulator source; record URL, access date and rights per
   record. An inaccessible/uncertain source means the field stays unknown. Import
   only after rights and the exact marketed variant have been checked.
5. Manually transcribe visible text in logical Unicode order; a second reviewer
   adjudicates uncertain regions and fields. Mark illegible fields null. Record
   ground-truth catalogue absence separately from failed OCR.
6. Assign original/photo-session families to dev or held-out test **before** making
   degradations; group near-duplicate captures together. Aim for approximately
   2/3 development, 1/3 test, with both languages and unknowns in each. Freeze test
   before threshold tuning; preserve a versioned manifest and checksum history.
7. Report natural photographs independently from synthetic degradations. Report
   sample counts and language/condition intersections, noting insufficient groups.
   Use development failures to justify a second OCR engine or perspective work.

The existing manifest schema can store licensed photos without changing the API.
The evaluator currently reads UTF-8 JSON manifests, validates hashes and family
isolation, and checks product IDs through expected labels. Review and version a
real catalogue before running it; never mix fictional IDs with marketed products.
