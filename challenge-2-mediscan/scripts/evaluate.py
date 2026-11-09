"""Real-engine evaluation. Generated transcripts are not manually labelled photos."""
import argparse
import hashlib
import json
import platform
import resource
import statistics
import time
import unicodedata
from pathlib import Path

from recognition.config import ROOT, Settings
from recognition.ocr import TesseractOCR
from recognition.service import RecognitionService


def load_manifest(path):
    manifest = json.loads(Path(path).read_text())
    families = {}
    for row in manifest["images"]:
        family, split = row["family_id"], row["split"]
        if family in families and families[family] != split:
            raise ValueError(f"Split leakage for family {family}")
        families[family] = split
        if hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError(f"Image checksum mismatch: {row['path']}")
    return manifest


def edit_distance(a, b):
    previous = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        current = [i]
        for j, y in enumerate(b, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j-1] + (x != y)))
        previous = current
    return previous[-1]


def metric_text(text):
    return " ".join("".join(c for c in unicodedata.normalize("NFC", text)
                            if unicodedata.category(c) != "Cf").split())


def ratio(n, d):
    return round(n / d, 4) if d else None


def summarize(rows):
    positives = [r for r in rows if r["expected_product_id"] is not None]
    negatives = [r for r in rows if r["expected_product_id"] is None]
    accepted = [r for r in rows if r["status"] == "matched"]
    transcribed = [r for r in rows if r["expected_text"]]
    chars = sum(len(metric_text(r["expected_text"])) for r in transcribed)
    words = sum(len(metric_text(r["expected_text"]).split()) for r in transcribed)
    cer_errors = sum(edit_distance(metric_text(r["expected_text"]), metric_text(r.get("primary_ocr_text", r["raw_ocr_text"]))) for r in transcribed)
    wer_errors = sum(edit_distance(metric_text(r["expected_text"]).split(), metric_text(r.get("primary_ocr_text", r["raw_ocr_text"])).split()) for r in transcribed)
    latencies = sorted(r["processing_time_ms"] for r in rows)
    p95 = statistics.quantiles(latencies, n=100, method="inclusive")[94] if len(latencies) > 1 else (latencies[0] if latencies else None)
    return dict(sample_count=len(rows), known_count=len(positives), unknown_count=len(negatives),
                accepted_count=len(accepted),
                ocr_transcribed_count=len(transcribed), ocr_reference_characters=chars, ocr_reference_words=words,
                cer=ratio(cer_errors, chars), wer=ratio(wer_errors, words),
                field_accuracy={field: ratio(sum(r["fields"][field] == r["expected_fields"][field] for r in positives), len(positives))
                                for field in ("strength", "form", "pack_size")},
                name_alias_recall=ratio(sum(r["name_alias_present"] for r in positives), len(positives)),
                top1_candidate_accuracy=ratio(sum(r["candidate_ids"][:1] == [r["expected_product_id"]] for r in positives), len(positives)),
                end_to_end_top1_accuracy=ratio(sum(r["matched_id"] == r["expected_product_id"] for r in positives), len(positives)),
                top3_candidate_recall=ratio(sum(r["expected_product_id"] in r["candidate_ids"] for r in positives), len(positives)),
                precision_accepted=ratio(sum(r["matched_id"] == r["expected_product_id"] for r in accepted), len(accepted)),
                acceptance_rate=ratio(len(accepted), len(rows)), abstention_rate=ratio(len(rows)-len(accepted), len(rows)),
                false_matches_unknown_count=sum(r["status"] == "matched" for r in negatives),
                false_matches_unknown_rate=ratio(sum(r["status"] == "matched" for r in negatives), len(negatives)),
                latency_p50_ms=round(statistics.median(latencies), 2) if latencies else None,
                latency_p95_ms=round(p95, 2) if p95 is not None else None)


def run(manifest_path, split, settings=None):
    settings = settings or Settings()
    manifest = load_manifest(manifest_path)
    ocr = TesseractOCR(settings.tessdata)
    service = RecognitionService(settings, ocr)
    rows = []
    try:
        for source in manifest["images"]:
            if source["split"] != split:
                continue
            result = service.recognize((ROOT / source["path"]).read_bytes(), source["image_id"])
            p = next((p for p in service.products if p.product_id == source["product_id"]), None)
            from recognition.extraction import normalize
            names = result["extracted_fields"]["product_name"] or ""
            rows.append(dict(image_id=source["image_id"], family_id=source["family_id"], language=source["language"],
                             condition=source["condition"], kind=source["kind"],
                             expected_product_id=source["product_id"], expected_fields=source["fields"],
                             expected_text=source["transcription"], raw_ocr_text=result["raw_ocr_text"],
                             transcription_source=source.get("transcription_source"),
                             primary_ocr_text=result["primary_ocr_text"],
                             fields=result["extracted_fields"], status=result["status"],
                             matched_id=result["matched_product"]["product_id"] if result["matched_product"] else None,
                             candidate_ids=[c["product_id"] for c in result["candidates"]],
                             name_alias_present=bool(p and any(normalize(a) in names for a in [p.name, *p.aliases])),
                             processing_time_ms=result["processing_time_ms"], warnings=result["warnings"]))
    finally:
        ocr.close()
    return rows, service


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=str(ROOT / "data/demo/manifest.json"))
    parser.add_argument("--split", choices=["dev", "test"], default="test")
    parser.add_argument("--output", default=str(ROOT / "reports/evaluation-test.json"))
    parser.add_argument("--contrast", action="store_true")
    args = parser.parse_args()
    from dataclasses import replace
    start = time.perf_counter()
    rows, service = run(args.manifest, args.split, replace(Settings(), contrast=args.contrast))
    import tesserocr
    report = dict(split=args.split, synthetic_only=all(row["kind"].startswith("synthetic_") for row in rows),
                  photograph_count=sum(row["kind"] == "natural_photo" for row in rows),
                  user_supplied_packaging_image_count=sum(row["kind"] == "user_supplied_packaging_image" for row in rows),
                  metric_protocol="CER/WER score primary_ocr_text only (not concatenated/repeated fallback passes), micro-averaged, NFC + whitespace collapse + bidi-control removal; case, accents and digit scripts preserved. Reference provenance is recorded per row; null/empty transcripts are excluded. Identification uses all retained OCR evidence. Null means no denominator. End-to-end accuracy requires accepted correct ID. Name metric is exact visible alias recall, not inferred brand transcription accuracy.",
                  latency_protocol="Warm in-process service, decode+all OCR passes+matching; excludes HTTP/upload/startup. p95 inclusive quantile. Groups may be small and share photo families.",
                  engine=tesserocr.tesseract_version(), python=platform.python_version(), platform=platform.platform(),
                  cpu=next((line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')), platform.processor()),
                  peak_process_rss_mib=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2),
                  total_seconds=round(time.perf_counter()-start, 2), thresholds=service.thresholds,
                  contrast=service.settings.contrast, overall=summarize(rows),
                  by_language={v: summarize([r for r in rows if r["language"] == v]) for v in sorted({r["language"] for r in rows})},
                  by_condition={v: summarize([r for r in rows if r["condition"] == v]) for v in sorted({r["condition"] for r in rows})},
                  by_kind={v: summarize([r for r in rows if r["kind"] == v]) for v in sorted({r["kind"] for r in rows})}, rows=rows)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps(report["overall"], indent=2))
    print(f"Measured report: {args.output}")


if __name__ == "__main__":
    main()
