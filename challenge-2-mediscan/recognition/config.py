import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    tessdata: str = os.getenv("RECOGNITION_TESSDATA", str(ROOT / "models"))
    catalogue: str = os.getenv("RECOGNITION_CATALOGUE", str(ROOT / "data/catalogue.json"))
    thresholds: str = os.getenv("RECOGNITION_THRESHOLDS", str(ROOT / "data/thresholds.json"))
    max_bytes: int = 8 * 1024 * 1024
    max_pixels: int = 16_000_000
    max_edge: int = 2000
    cpu_timeout: float = float(os.getenv("RECOGNITION_CPU_TIMEOUT", "20"))
    upload_timeout: float = float(os.getenv("RECOGNITION_UPLOAD_TIMEOUT", "10"))
    contrast: bool = os.getenv("RECOGNITION_CONTRAST", "0") == "1"
