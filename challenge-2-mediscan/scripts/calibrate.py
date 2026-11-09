"""Development-only threshold selection; no held-out inputs are read by OCR."""
import itertools
import json

from recognition.config import ROOT
from recognition.matching import match
from recognition.schemas import Fields
from .evaluate import run


def main():
    rows, service = run(ROOT / "data/demo/manifest.json", "dev")
    trials = []
    for name, score, margin in itertools.product((0.85, 0.9, 0.95), (85, 90, 95), (5, 8, 12)):
        config = dict(candidate_name=0.65, accept_name=name, accept_score=score, margin=margin)
        correct = false = 0
        for row in rows:
            unresolved = any("unresolved" in w or "Unsupported compound" in w for w in row["warnings"])
            _, p, _, _ = match(Fields.model_validate(row["fields"]), service.products, config, unresolved)
            if p:
                if p.product_id == row["expected_product_id"]:
                    correct += 1
                else:
                    false += 1
        trials.append(dict(config=config, correct_accepted=correct, false_accepted=false))
    eligible = [t for t in trials if t["false_accepted"] == 0]
    if not eligible:
        raise RuntimeError("No configuration without development false accepts; revise matcher before publishing thresholds")
    selected = max(eligible, key=lambda t: (t["correct_accepted"], t["config"]["accept_name"], t["config"]["accept_score"], t["config"]["margin"]))
    config = dict(**selected["config"], calibration="Synthetic development-only grid selection: maximize correct accepts subject to zero observed false accepts; conservative tie break. No population probability calibration.")
    (ROOT / "data/thresholds.json").write_text(json.dumps(config, indent=2)+"\n")
    report = dict(sample_count=len(rows), photograph_count=0, split="dev", selected=selected, trials=trials,
                  limitation="Small synthetic development set; no real-world operating-point guarantee.")
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports/calibration.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(selected, indent=2))


if __name__ == "__main__":
    main()
