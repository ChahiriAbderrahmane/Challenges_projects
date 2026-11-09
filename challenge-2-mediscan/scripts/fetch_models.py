"""Download only two small official fast models; verify against checked hashes."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent


def main():
    manifest = json.loads((ROOT / "models/sources.json").read_text())
    for model in manifest["models"]:
        destination = ROOT / "models" / model["file"]
        if destination.exists() and hashlib.sha256(destination.read_bytes()).hexdigest() == model["sha256"]:
            continue
        with urlopen(model["url"], timeout=30) as response:
            data = response.read(10 * 1024 * 1024)
        digest = hashlib.sha256(data).hexdigest()
        if digest != model["sha256"]:
            raise ValueError(f"Model checksum mismatch: {model['file']}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        print(f"Verified {model['file']}: {len(data)} bytes")


if __name__ == "__main__":
    main()
