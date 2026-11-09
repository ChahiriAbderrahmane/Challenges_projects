# Measured evaluation — 2026-10-27

> Historical baseline, before the Doliprane layout fallback. Current follow-up
> reports are `reports/evaluation-{dev,test}-layout-fallback.json`; see
> [the correction report](doliprane-fix.md) for current metrics and 40-test status.
> The new user-supplied packshot is a separate private development regression,
> not part of the 88-image synthetic benchmark.

## Scope and reproducibility
This is an **88-image synthetic regression set**, with 15 fictional variants.
There are **zero real packaging photos** and zero manually transcribed real-photo
samples. Generator references enable reproducible OCR tests but do not establish
real-world medication recognition. No other OCR engine was installed or benchmarked.

Development: 34 images, 30 known variants plus four negatives. Held-out test:
54 images, 50 known-positive images plus four negatives. Twenty test images are
synthetic degradations of four original families, so these are not 54 independent
product/photo observations. See `data/demo/manifest.json` for every label and hash.

Measured on Fedora 43 x86_64, Python 3.12.15, Intel Core i5-1335U, 12 logical CPUs,
CPU only, `OMP_THREAD_LIMIT=1`. The installed `tesserocr==2.9.1` binary wheel reports
**Tesseract 5.5.1 / Leptonica 1.85.0**, independent of Fedora's system library 5.5.2.
Official `tessdata_fast` Arabic/French hashes are pinned in `models/sources.json`.

Commands are in the README. JSON reports contain actual per-image OCR strings,
fields, selected IDs, candidate IDs, status, latency and warnings:

* `reports/calibration.json`: all 27 development threshold trials.
* `reports/evaluation-dev.json`: baseline development run.
* `reports/evaluation-dev-contrast.json`: development contrast experiment.
* `reports/evaluation-test.json`: final held-out run.

No threshold was chosen using held-out results. Grid search maximized correct
development accepts with zero observed false accepts, then used a conservative
tie break: name ≥.95, ranking utility ≥95, margin ≥12; candidate name ≥.65.
Development accepted 15/34, all correct. Several settings tied: this dataset
does **not** precisely identify an operating point. These thresholds are
synthetically tuned abstention rules, never calibrated probabilities.

## Held-out results

| Metric | Observed result | Denominator / interpretation |
|---|---:|---|
| OCR CER | 33.67% | 1,274 reference characters, 53 nonblank images |
| OCR WER | 40.73% | 248 reference words, same images |
| Strength exact extraction | 50% | 50 known-positive images, including correctly missing fields |
| Form exact extraction | 62% | same 50 images |
| Pack-size exact extraction | 54% | same 50 images |
| Exact visible name/alias recall | 74% | 50 known-positive images; not a brand-string accuracy estimate |
| Top-1 ranked-candidate accuracy | 50% | 25/50, before acceptance |
| End-to-end accepted top-1 accuracy | **42%** | **21/50** known-positive images |
| Top-3 candidate recall | 74% | 37/50 known-positive images |
| Precision among accepted matches | 100% observed | **21/21** accepted images; small synthetic sample |
| Acceptance / abstention | 38.89% / 61.11% | 21/54 and 33/54 |
| False accepts on unknown negatives | 0 observed | **0/4**; insufficient to estimate a reliable false-match rate |
| Warm latency p50 / p95 | 441.06 / 709.37 ms | 54 requests, includes decode, all OCR passes, matching |
| Peak evaluation-process RSS | 77.93 MiB | Includes Python, model, Pillow and service; not total API deployment RSS |

Latency excludes HTTP, upload, cold worker startup and model downloads. p95 uses
an inclusive interpolated quantile. Native worker startup has its own deadline;
additional API workers multiply process memory and CPU contention.
CER/WER are micro-averaged edit distances after NFC normalization, whitespace
collapse and bidi-control removal. Case, accents and digit scripts remain
meaningful; insertions can make error rates exceed 100%. A null report metric
means there is no denominator. All current references are exact generator text.

## Language breakdown

| Language | Images (known / negative) | CER | WER | Accepted correct / known | Top-3 recall |
|---|---:|---:|---:|---:|---:|
| French | 29 (25 / 4) | 4.45% | 5.34% | 21/25 (84%) | 92% |
| Arabic | 25 (25 / 0) | 68.86% | 80.34% | **0/25** | 56% |

The Arabic result is an important failure, not evidence of supported robust
identification. Tesseract can recover some Arabic aliases, but frequently omits
the strength line and confuses Arabic-Indic digits. Missing fields remain unknown
and prevent acceptance. No Arabic negative-image false-match rate can be reported
because the present negatives are French. Unit tests verify Arabic extraction
given correct text, which does not imply Arabic OCR is accurate.

A targeted development inspection of one Arabic fixture using PSM 6 and 11 and
`ara`, `ara+fra`, `fra+ara` still failed to recover the strength reliably. Merely
changing language order/segmentation did not resolve this observed case. These
spot checks are diagnostic only, not a comparative benchmark.

## Condition and synthetic-kind breakdowns

| Test condition | Images | Correct accepted / known |
|---|---:|---:|
| Clear | 30 | 15/30 |
| Blur (synthetic) | 4 | 2/4 |
| Low contrast (synthetic) | 4 | 2/4 |
| 90° rotation (synthetic) | 4 | 2/4 |
| Uneven-light gradient (synthetic) | 4 | 0/4 |
| Name-only partial crop (synthetic) | 4 | 0/4, expected abstention |

Clear known renders: 15/30 accepted correctly (all 15 clear French images;
zero clear Arabic images). Degradations: 6/20 accepted, all correct. Gradients
exposed a limitation even for French; partial crops correctly lack identifying
strength and abstain. Non-medication, unsupported-strength and absent-product
negatives each abstained; the blank image was unreadable. Per-language and
per-condition metrics and sample counts are in JSON. These groups are too small
to claim robustness; there are no naturally difficult photograph results.

## Preprocessing decision
Development baseline and opt-in autocontrast each accepted 15/34 with no false
accepts. CER stayed 30.49%; WER changed from 40.24% to 38.41%, without any
identification gain. Median latency was 361.07 versus 387.25 ms in separate runs;
single-run timing differences are not statistically established. Contrast remains
**disabled by default**. Arbitrary deskew/perspective transforms were not added
without photographs or measured evidence that they solve the observed errors.

## Tests and delivery gates
`python -m pytest -q`: **35 passed**, including real Arabic/French OCR API
integration, unknown/blank cases, upload validation, EXIF orientation, alias and
unit normalization, strength/form conflicts, close spellings, missing-pack
ambiguity, meaningful numeric brand designators (B12 versus B6), overload,
dependency failure and actual process timeout/restart.
`python -m pip check`: no broken requirements.
An actual Uvicorn process on localhost passed health and a multipart `curl`
request: `matched`, `demo-01-100`, measured HTTP processing time 168.88 ms for
that single smoke request. Request-ID/category/timing log output was verified.
This is a functional check, not a latency benchmark.
One dependency deprecation warning is emitted by Starlette's TestClient using
AnyIO's old BlockingPortal alias; it did not affect execution.

Working vertical-slice and failure-handling gates pass. Real-photo collection,
manual photograph transcription, real-world Arabic identification and meaningful
unknown false-match calibration remain **unmet**. The next justified engineering
step is licensed Arabic/French photo collection, followed by a controlled CPU
comparison with a scene-text engine. Any additional large runtime/model download
requires approval. No training is justified by the current evidence.
