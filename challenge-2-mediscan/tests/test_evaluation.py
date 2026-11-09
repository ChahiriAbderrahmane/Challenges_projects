import json

import pytest

from recognition.config import ROOT
from scripts.evaluate import edit_distance, load_manifest, summarize


def test_manifest_families_do_not_leak():
    manifest = load_manifest(ROOT / "data/demo/manifest.json")
    assert len(manifest["images"]) >= 60
    assert len({r["product_id"] for r in manifest["images"] if r["product_id"]}) == 15


def test_metrics_count_false_accepts():
    row = dict(expected_product_id=None, matched_id="wrong", status="matched", expected_text="",
               raw_ocr_text="", candidate_ids=["wrong"], fields={}, expected_fields={}, processing_time_ms=10)
    result = summarize([row])
    assert result["precision_accepted"] == 0
    assert result["false_matches_unknown_rate"] == 1
    assert result["cer"] is None
    assert edit_distance("kitten", "sitting") == 3


def test_ocr_metrics_do_not_score_repeated_auxiliary_passes_as_insertions():
    row = dict(expected_product_id=None, matched_id=None, status="unknown", expected_text="visible label",
               primary_ocr_text="visible label", raw_ocr_text="[pass one]\nvisible label\n[pass two]\nvisible label",
               candidate_ids=[], fields={}, expected_fields={}, processing_time_ms=10)
    result = summarize([row])
    assert result["cer"] == 0 and result["wer"] == 0
