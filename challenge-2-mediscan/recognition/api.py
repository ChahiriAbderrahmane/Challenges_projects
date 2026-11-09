import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import UploadFile
from starlette.requests import Request as FormRequest

from .config import Settings
from .errors import RecognitionError
from .schemas import ErrorResponse, RecognitionResult
from .worker import ProcessRunner

logger = logging.getLogger("recognition")
logger.setLevel(logging.INFO)


def create_app(settings: Settings | None = None, runner=None):
    settings = settings or Settings()
    runner = runner or ProcessRunner(settings)

    @asynccontextmanager
    async def lifespan(app):
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
        try:
            await asyncio.to_thread(runner.start)
        except RecognitionError as error:
            logger.error("startup category=%s", error.category)
        yield
        await asyncio.to_thread(runner.close)

    app = FastAPI(title="Medication Box Recognition — Challenge #2", version="1.0.0", lifespan=lifespan,
                  description="Arabic/French printed box identification against a local catalogue. Scores are ranking utilities, not probabilities. Catalogue includes limited sourced French references and fictional demonstration records.")
    app.state.runner = runner
    app.state.busy = False
    static_directory = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=static_directory), name="static")

    @app.get("/", include_in_schema=False)
    async def interface():
        return FileResponse(static_directory / "index.html", headers={
            "Cache-Control": "no-cache",
            "Content-Security-Policy": "default-src 'self'; img-src 'self' blob:; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        })

    @app.middleware("http")
    async def request_context(request, call_next):
        request.state.request_id = uuid.uuid4().hex
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(RecognitionError)
    async def recognition_error(request, error):
        logger.warning("request_id=%s category=%s processing_time_ms=%.2f", request.state.request_id, error.category,
                       (time.perf_counter() - getattr(request.state, "started", time.perf_counter())) * 1000)
        return JSONResponse(status_code=error.status,
                            content={"detail": {"request_id": request.state.request_id, "category": error.category, "message": error.message}},
                            headers={"Retry-After": "1"} if error.status == 429 else None)

    @app.exception_handler(Exception)
    async def internal_error(request, error):
        request_id = getattr(request.state, "request_id", uuid.uuid4().hex)
        logger.error("request_id=%s category=internal_failure", request_id)
        return JSONResponse(status_code=500, headers={"X-Request-ID": request_id}, content={"detail": {
            "request_id": request_id, "category": "internal_failure", "message": "Recognition failed internally."}})

    @app.get("/health", responses={503: {"description": "OCR worker unavailable"}})
    async def health():
        try:
            alive = runner.ready and (not hasattr(runner, "process") or (runner.process is not None and runner.process.is_alive()))
        except (ValueError, AttributeError):  # process may be closing in the worker supervisor thread
            alive = False
        return JSONResponse(status_code=200 if alive else 503, content={"status": "ok" if alive else "degraded", "ocr_ready": alive, "languages": ["fra", "ara"], "catalogue": "local"})

    @app.post("/api/recognize", response_model=RecognitionResult,
              responses={code: {"model": ErrorResponse} for code in (400, 413, 415, 422, 429, 500, 503, 504)},
              openapi_extra={"requestBody": {"required": True, "content": {"multipart/form-data": {"schema": {"type": "object", "required": ["image"], "properties": {"image": {"type": "string", "format": "binary", "description": "JPEG/PNG, up to 8 MiB and 16 MP"}}}}}}})
    async def recognize(request: Request):
        """Upload a box front. Unknown/unreadable images return 200; see matching_evidence for explanations."""
        if app.state.busy:
            raise RecognitionError(429, "overload", "Recognition capacity is busy. Retry later.")
        app.state.busy = True  # no await between check and set: atomic on event loop
        start = time.perf_counter()
        request.state.started = start
        try:
            content_type = request.headers.get("content-type", "")
            if not content_type.lower().startswith("multipart/form-data"):
                raise RecognitionError(415, "multipart_required", "Use multipart/form-data with an image field.")
            limit = settings.max_bytes + 64 * 1024
            body = bytearray()
            async with asyncio.timeout(settings.upload_timeout):
                async for chunk in request.stream():
                    if len(body) + len(chunk) > limit:
                        raise RecognitionError(413, "body_size", "Multipart request exceeds the size limit.")
                    body.extend(chunk)

            async def receive():
                return {"type": "http.request", "body": bytes(body), "more_body": False}

            form_request = FormRequest(request.scope, receive)
            try:
                async with form_request.form(max_files=1, max_fields=0, max_part_size=limit) as form:
                    if len(form.multi_items()) != 1 or not isinstance(form.get("image"), UploadFile):
                        raise RecognitionError(422, "image_required", "Supply exactly one file in the image field.")
                    image = form["image"]
                    data = await image.read(settings.max_bytes + 1)
                    if len(data) > settings.max_bytes:
                        raise RecognitionError(413, "image_size", "Image exceeds the byte limit.")
            except RecognitionError:
                raise
            except Exception:
                raise RecognitionError(400, "invalid_multipart", "Malformed multipart upload.") from None
            work = asyncio.create_task(asyncio.to_thread(runner.recognize, data, request.state.request_id))
            try:
                result = await asyncio.shield(work)
            except asyncio.CancelledError:
                # Client cancellation must not release admission while native work remains.
                # The process runner still enforces its CPU deadline and kills on expiry.
                try:
                    await asyncio.shield(work)
                except Exception:
                    pass
                raise
            result["processing_time_ms"] = round((time.perf_counter() - start) * 1000, 2)
            logger.info("request_id=%s category=%s processing_time_ms=%s", request.state.request_id, result["status"], result["processing_time_ms"])
            return result
        except TimeoutError:
            raise RecognitionError(504, "upload_timeout", "Upload read deadline exceeded.") from None
        except RecognitionError:
            raise
        except Exception:
            raise RecognitionError(500, "internal_failure", "Recognition failed internally.") from None
        finally:
            app.state.busy = False

    return app


app = create_app()
