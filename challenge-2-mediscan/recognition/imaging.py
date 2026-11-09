from io import BytesIO
import warnings

from PIL import Image, ImageOps, ImageStat, UnidentifiedImageError

from .config import Settings
from .errors import RecognitionError


def prepare(data: bytes, settings: Settings) -> tuple[Image.Image, list[str]]:
    if len(data) > settings.max_bytes:
        raise RecognitionError(413, "image_size", "Image exceeds the byte limit.")
    if not (data.startswith(b"\xff\xd8\xff") or data.startswith(b"\x89PNG\r\n\x1a\n")):
        raise RecognitionError(415, "image_format", "Only decoded JPEG and PNG images are supported.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as probe:
                if probe.format not in {"JPEG", "PNG"}:
                    raise RecognitionError(415, "image_format", "Unsupported decoded format.")
                if probe.width * probe.height > settings.max_pixels:
                    raise RecognitionError(413, "pixel_limit", "Image exceeds the pixel limit.")
                if getattr(probe, "n_frames", 1) != 1:
                    raise RecognitionError(415, "animated_image", "Animated images are unsupported.")
                probe.verify()
            with Image.open(BytesIO(data)) as source:
                source.load()
                image = ImageOps.exif_transpose(source).convert("RGB")
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise RecognitionError(413, "pixel_limit", "Image exceeds the decoder safety limit.") from None
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        raise RecognitionError(400, "corrupt_image", "Image content is corrupted or truncated.") from None
    if min(image.size) < 32:
        raise RecognitionError(400, "image_dimensions", "Image must be at least 32 pixels on each side.")
    notes = []
    image.thumbnail((settings.max_edge, settings.max_edge), Image.Resampling.LANCZOS)
    gray = image.convert("L")
    if ImageStat.Stat(gray).stddev[0] < 25:
        notes.append("Low global contrast; provide a well-lit, sharp image if recognition fails.")
    if min(image.size) < 200:
        notes.append("Small image; fine print may be illegible.")
    if settings.contrast:
        image = ImageOps.autocontrast(image, cutoff=1)
        notes.append("Experimental contrast enhancement enabled.")
    return image, notes
