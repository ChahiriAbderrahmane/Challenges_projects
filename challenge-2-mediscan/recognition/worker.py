"""Persistent native worker with a real killable CPU deadline, no work queue."""
import multiprocessing as mp

from .config import Settings
from .errors import RecognitionError


def _serve(connection, settings):
    ocr = None
    try:
        from .ocr import TesseractOCR
        from .service import RecognitionService
        ocr = TesseractOCR(settings.tessdata)
        service = RecognitionService(settings, ocr)
        connection.send(("ready", None))
        while True:
            command = connection.recv()
            if command is None:
                return
            data, request_id = command
            try:
                connection.send(("result", service.recognize(data, request_id)))
            except RecognitionError as error:
                connection.send(("error", (error.status, error.category, error.message)))
            except Exception:
                connection.send(("error", (500, "processing_failure", "Recognition failed internally.")))
    except RecognitionError as error:
        connection.send(("error", (error.status, error.category, error.message)))
    except Exception:
        connection.send(("error", (503, "worker_initialization", "Recognition worker could not initialize.")))
    finally:
        if ocr:
            ocr.close()
        connection.close()


class ProcessRunner:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.process = None
        self.connection = None
        self.ready = False

    def start(self):
        self.close()
        parent, child = mp.get_context("spawn").Pipe()
        self.connection = parent
        self.process = mp.get_context("spawn").Process(target=_serve, args=(child, self.settings), daemon=True)
        self.process.start()
        child.close()
        kind, value = self._receive(self.settings.cpu_timeout)
        if kind != "ready":
            self.close()
            raise RecognitionError(*value)
        self.ready = True

    def _receive(self, timeout):
        try:
            if not self.connection.poll(timeout):
                self.close()
                raise RecognitionError(504, "cpu_timeout", "Recognition deadline exceeded; CPU worker terminated.")
            return self.connection.recv()
        except (EOFError, BrokenPipeError, OSError):
            self.close()
            raise RecognitionError(503, "worker_unavailable", "Recognition worker is unavailable.") from None

    def recognize(self, data, request_id):
        if not self.ready or not self.process.is_alive():
            self.start()
        try:
            self.connection.send((data, request_id))
        except (OSError, EOFError):
            self.close()
            raise RecognitionError(503, "worker_unavailable", "Recognition worker is unavailable.") from None
        kind, value = self._receive(self.settings.cpu_timeout)
        if kind == "error":
            raise RecognitionError(*value)
        return value

    def close(self):
        self.ready = False
        if self.process:
            if self.process.is_alive():
                self.process.terminate()
            self.process.join(timeout=2)
            if self.process.is_alive():
                self.process.kill()
                self.process.join()
            self.process.close()
        if self.connection:
            self.connection.close()
        self.process = self.connection = None
