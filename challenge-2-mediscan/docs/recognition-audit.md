# Phase 0: implementation audit (2026-10-27)

The requested working directory `/home/Chahiri/Documents/projects/ph2` contained
only an empty Python 3.12.15 `.venv`, and is not a Git repository. No application
was present to modify. The adjacent `../ph` is a Git checkout whose origin is
`https://github.com/abelmou/Healthcare-Assistant.git`. It has modified README and
`app_chainlit.py` plus untracked pharmacy service, tests and documentation.
Those files are user work and were inspected read-only. Other adjacent checkouts
also contain upstream `ocr.py`. This delivery is an independent application here.

| Requirement | Actual existing implementation (`../ph`) | Missing work | Action |
|---|---|---|---|
| Upload validation | Streamlit extension selector, Pillow decode; accepts PDF | byte/pixel limits, decoded type checks, overload control | New bounded JPEG/PNG API |
| Preprocessing | `ocr.py:22–36`: OpenCV grayscale, fixed threshold 130 | EXIF, quality inspection, baseline comparison | Pillow baseline, conservative optional contrast |
| Arabic/French OCR | `pytesseract.image_to_string(lang="ara+eng+fra")` | verified engine/models, boxes, timeouts | Tesseract in-process adapter |
| Identifier extraction | LLaMa prescription formatting prompt requiring an answer regardless of input quality | deterministic box field extraction | Explicit evidence, unknown fields |
| Recognition | No product matcher in `ocr.py` | catalogue, ranking, conflicts, abstention | Local labelled demonstration catalogue |
| Adjacent pharmacy catalogue | `pharmacy_service/catalog.json`: three demo name/alias entries, no strengths/forms/packs/provenance; `/api/analyze` processes LLM-extracted patient text | variant-level reference evidence and image pipeline | Preserve this service; do not treat its name list as a validated medicine database |
| Persistence | temp files, Azure upload; malformed `_init_` constructor | local-only default | No external uploads, no retained input |
| API/evaluation | Streamlit prescription UI | schemas, tests, labelled image data, metrics | Separate FastAPI application |
| Challenge #1 | `app_chainlit.py`: three translation models, Ollama, generation lock, bounded history, async thread offload | no Challenge #2 reuse needed | Leave whole checkout and environment untouched |
| Dependencies | `requirement.txt` mostly unpinned chatbot packages; OCR imports not all declared | isolated reproducible installation | Dedicated Python 3.12 requirements lock |

Environment: Fedora 43, Intel i5-1335U (12 logical CPUs), CPU-only execution.
System has Tesseract libraries 5.5.2 and English traineddata, but no `tesseract`
executable, French or Arabic data. No `.venv312` in the inspected locations.
No medication-box images or labelled image catalogue were found in `../ph/data`.
No chatbot runtime smoke test was attempted: importing it downloads translation
models and requires its own Ollama setup. Preservation is filesystem isolation,
not a claim that its external services were tested.

Reusable idea: Tesseract language selection. Do not reuse prescription prompting,
fixed thresholding, PDF processing, storage integration or application imports.
