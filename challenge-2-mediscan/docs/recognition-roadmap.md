# Ordered roadmap and acceptance gates

1. **Audit/design:** inspect source and user changes, verify language support,
   document decisions. Gate: audit matrix and architecture exist before code.
2. **Vertical slice:** Pillow → reusable Tesseract → fields → JSON catalogue →
   FastAPI. Gate: real-engine rendered French and Arabic requests produce complete
   schemas, and clear supported evidence can match.
3. **Robustness:** byte/pixel/decode limits, EXIF, bounded rotation, native-process
   timeouts, overload/dependency errors, strength conflict veto and abstention.
   Gate: meaningful unit/API tests plus real-engine integration tests pass.
4. **Dataset/evaluation:** provenance manifest, original-family split isolation,
   development threshold selection, held-out metrics and condition/language
   breakdowns. Gate: actual measured report with counts, failures, hardware and
   explicit synthetic-vs-real distinctions. Collection target: ≥15 real variants,
   ≥60 licensed photos including unknowns. Synthetic renders do not satisfy it.
5. **Delivery:** pinned dependencies, Fedora commands, curl/Swagger, demonstration,
   limitations and collection plan. Gate: installation checks, all tests, real
   OCR evaluation and original checkout preservation reviewed.

Future work is evidence-led: collect real packages first, then compare engines
and contrast/deskew if measured failure patterns justify them. No training or
infrastructure expansion without such evidence.

## Delivered status

* Phases 0–1: audit and design delivered; no adjacent project files edited.
* Phase 2: real-engine French vertical slice and live HTTP smoke verified.
* Phase 3: 41 tests pass locally after the Doliprane/UI follow-ups, including worker
  timeout/restart, API failure paths and the user-provided real packaging image.
  The private-image test skips when that asset is unavailable; see `docs/doliprane-fix.md`.
  Synthetic uneven lighting and Arabic-digit failures remain documented.
* Phase 4: 88 synthetic fixtures, development tuning and held-out measured reports
  delivered. **Real-photo dataset target and real-photo transcription/evaluation
  gates are unmet**; collection plan is in `docs/dataset.md`.
* Phase 5: pinned environment, Fedora setup, model hashes, Swagger/curl, related
  work and demonstration delivered. Chatbot runtime is not revalidated because
  it uses separate downloaded models and external Ollama services.
* UI follow-up: same-origin French web interface at `/`, with preview, drag/drop,
  recognition, abstention/error states, OCR/JSON details and responsive layout.
  A real Chrome integration check passed against Doliprane, plus state rendering,
  overload/reset, text-only untrusted output and a 390 px mobile viewport.
