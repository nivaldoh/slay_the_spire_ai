"""Presentation image conversion, after gameplay. Pillow is an optional report extra."""

import base64
import io
from pathlib import Path


def webp(path: Path, *, max_size: tuple[int, int] = (1600, 1000)) -> dict:
    from PIL import Image

    with Image.open(path) as source:
        original_size = source.size
        image = source.convert("RGB")
        image.thumbnail(max_size)
        buffer = io.BytesIO()
        image.save(buffer, format="WEBP", quality=78, method=6)
    return {"image": "data:image/webp;base64," + base64.b64encode(buffer.getvalue()).decode(),
            "original_size": list(original_size), "size": list(image.size),
            "bytes": len(buffer.getvalue())}


def stills(episode: Path, entries: list[dict], *, embed: bool) -> list[dict]:
    """Retain failed captures and metadata, even when only featured images are embedded."""
    output = []
    for entry in entries:
        item = {**entry, "policy_input": False}
        filename = entry.get("file")
        if filename and embed:
            # Capture manifests name local files, never arbitrary report-host paths.
            if Path(filename).name != filename:
                item.update(status="error", error="Invalid still filename")
            else:
                try:
                    item.update(webp(episode / filename), status="embedded")
                except (OSError, ValueError, ImportError) as exc:
                    item.update(status="error", error=f"{type(exc).__name__}: cannot convert "
                                f"{filename}; Pillow is available in the report extra")
        elif filename:
            item["status"] = "metadata_only_nonfeatured_trial"
        output.append(item)
    return output
