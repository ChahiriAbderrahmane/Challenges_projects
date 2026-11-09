"""Required real OCR tests: fail with explicit setup error if models are absent."""
from pathlib import Path

from fastapi.testclient import TestClient

from recognition.api import create_app
from recognition.config import ROOT


def test_real_engine_api_french_and_arabic_and_unknown():
    with TestClient(create_app()) as client:
        assert client.get("/health").status_code == 200, "Run python -m scripts.fetch_models first"
        for name, expected in (("demo-01-100-fr-dev", "matched"),
                               ("demo-01-100-ar-dev", None), ("negative-unknown-test", "unknown"),
                               ("negative-blank-test", "unreadable")):
            response = client.post("/api/recognize", files={"image": (name+".png", (ROOT / f"data/demo/images/{name}.png").read_bytes(), "image/png")})
            assert response.status_code == 200, response.text
            result = response.json()
            if expected:
                assert result["status"] == expected
            else:
                # Actual Arabic engine behavior is measured, not mocked into success.
                assert any("\u0600" <= c <= "\u06ff" for c in result["raw_ocr_text"])
                assert result["status"] in {"matched", "ambiguous", "unknown"}
                if result["status"] == "matched":
                    assert result["matched_product"]["product_id"] == "demo-01-100"


def test_cpu_deadline_terminates_worker():
    from dataclasses import replace
    import pytest
    from recognition.config import Settings
    from recognition.errors import RecognitionError
    from recognition.worker import ProcessRunner
    runner = ProcessRunner(Settings())
    try:
        runner.start()
        process = runner.process
        runner.settings = replace(runner.settings, cpu_timeout=0.000001)
        with pytest.raises(RecognitionError) as error:
            runner.recognize((ROOT / "data/demo/images/demo-01-100-fr-dev.png").read_bytes(), "deadline-test")
        assert error.value.status == 504
        assert runner.process is None and not runner.ready
        assert process._closed
        runner.settings = Settings()
        assert runner.recognize((ROOT / "data/demo/images/demo-01-100-fr-dev.png").read_bytes(), "restart")["status"] == "matched"
    finally:
        runner.close()


def test_user_doliprane_image_with_real_ocr():
    import pytest
    # Private user-supplied asset, not copied into the public synthetic dataset.
    image = ROOT / "doliprane-1000-mg-8-sachets-9261.dsGPD15_Z9IFisZmfHVEVVw5uGg.png"
    if not image.exists():
        pytest.skip("User-provided regression photo unavailable; redistribution rights not established")
    with TestClient(create_app()) as client:
        response = client.post("/api/recognize", files={"image": ("box.png", image.read_bytes(), "image/png")})
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["status"] == "matched", result
        assert result["matched_product"]["product_id"] == "fr-cip-3400936246980"
        assert result["extracted_fields"]["strength"] == "1000 mg"
        assert result["extracted_fields"]["product_name"] == "doliprane"
        assert result["extracted_fields"]["pack_size"] == 8
        assert result["extracted_fields"]["form"] == "powder_oral_solution"
        assert "1000 mg" in result["raw_ocr_text"]
