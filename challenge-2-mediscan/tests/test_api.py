import threading
from dataclasses import replace
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from recognition.api import create_app
from recognition.config import Settings
from recognition.errors import RecognitionError
from recognition.imaging import prepare
from recognition.ocr import OCRResult
from recognition.service import RecognitionService


class FixedOCR:
    def read(self, image):
        return OCRResult("Zefrano\n100 mg\n12 comprimés", [])


class LocalRunner:
    ready = False
    def __init__(self, settings):
        self.service = RecognitionService(settings, FixedOCR())
    def start(self):
        self.ready = True
    def close(self):
        self.ready = False
    def recognize(self, data, request_id):
        return self.service.recognize(data, request_id)


def image_bytes(fmt="PNG", size=(400, 400)):
    stream = BytesIO()
    Image.new("RGB", size, "white").save(stream, format=fmt)
    return stream.getvalue()


@pytest.fixture
def client():
    settings = replace(Settings(), max_bytes=10_000, max_pixels=1_000_000)
    with TestClient(create_app(settings, LocalRunner(settings))) as client:
        yield client


def test_valid_content_despite_wrong_mime_and_extension(client):
    response = client.post("/api/recognize", files={"image": ("wrong.bin", image_bytes(), "application/octet-stream")})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "matched"
    assert response.headers["X-Request-ID"] == data["request_id"]
    assert data["matched_product"]["product_id"] == "demo-01-100"


@pytest.mark.parametrize("data,code", [(b"not an image", 415), (b"\x89PNG\r\n\x1a\ntruncated", 400), (b"x"*10001, 413)])
def test_invalid_uploads(client, data, code):
    response = client.post("/api/recognize", files={"image": ("box.png", data, "image/png")})
    assert response.status_code == code
    assert "request_id" in response.json()["detail"]
    assert "Traceback" not in response.text


def test_pixel_limit(client):
    assert client.post("/api/recognize", files={"image": ("box.png", image_bytes(size=(1100, 1100)))}).status_code == 413


def test_missing_or_extra_parts(client):
    assert client.post("/api/recognize", files={"other": ("x", image_bytes())}).status_code == 422
    assert client.post("/api/recognize", json={}).status_code == 415
    assert client.post("/api/recognize", files=[("image", ("a", image_bytes())), ("image", ("b", image_bytes()))]).status_code == 400


def test_unsupported_decoded_format():
    with pytest.raises(RecognitionError) as error:
        prepare(image_bytes("GIF"), Settings())
    assert error.value.status == 415


def test_exif_orientation():
    stream = BytesIO()
    image = Image.new("RGB", (320, 640))
    exif = Image.Exif()
    exif[274] = 6
    image.save(stream, format="JPEG", exif=exif)
    result, _ = prepare(stream.getvalue(), Settings())
    assert result.size == (640, 320)


def test_dependency_failure_sanitized():
    class Broken(LocalRunner):
        def start(self):
            raise RecognitionError(503, "ocr_dependency", "Required OCR unavailable.")
        def recognize(self, data, request_id):
            self.start()
    settings = Settings()
    with TestClient(create_app(settings, Broken(settings))) as client:
        assert client.get("/health").status_code == 503
        assert client.post("/api/recognize", files={"image": ("a", image_bytes())}).status_code == 503


def test_overload_rejected_and_health_responsive():
    started, release = threading.Event(), threading.Event()
    class Slow(LocalRunner):
        def recognize(self, data, request_id):
            started.set()
            assert release.wait(5)
            return super().recognize(data, request_id)
    settings = Settings()
    with TestClient(create_app(settings, Slow(settings))) as client:
        results = []
        thread = threading.Thread(target=lambda: results.append(client.post("/api/recognize", files={"image": ("a", image_bytes())})))
        thread.start()
        assert started.wait(5)
        try:
            assert client.get("/health").status_code == 200
            assert client.post("/api/recognize", files={"image": ("b", image_bytes())}).status_code == 429
        finally:
            release.set()
            thread.join(5)
        assert results[0].status_code == 200


def test_openapi_documents_binary_upload(client):
    schema = client.get("/openapi.json").json()
    assert "multipart/form-data" in schema["paths"]["/api/recognize"]["post"]["requestBody"]["content"]


def test_web_interface_and_local_assets_are_available(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert 'lang="fr"' in response.text
    for path in ("/static/app.js", "/static/app.css", "/static/icon.svg"):
        assert client.get(path).status_code == 200


@pytest.mark.parametrize("error,code,category", [
    (RecognitionError(504, "cpu_timeout", "CPU worker terminated."), 504, "cpu_timeout"),
    (RuntimeError("private internal details"), 500, "internal_failure"),
])
def test_runner_failure_http_contract(error, code, category):
    class Failing(LocalRunner):
        def recognize(self, data, request_id):
            raise error
    settings = Settings()
    with TestClient(create_app(settings, Failing(settings))) as client:
        response = client.post("/api/recognize", files={"image": ("a", image_bytes())})
        assert response.status_code == code
        assert response.json()["detail"]["category"] == category
        assert "private internal details" not in response.text
        assert response.headers["X-Request-ID"] == response.json()["detail"]["request_id"]
