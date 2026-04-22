from __future__ import annotations

import base64
import io
import mimetypes
from pathlib import Path

from PIL import Image


def make_data_url(path: str | Path, size: tuple[int, int] = (320, 320)) -> str | None:
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        return None

    try:
        with Image.open(file_path) as image:
            image = image.convert("RGB")
            image.thumbnail(size)
            buf = io.BytesIO()
            image.save(buf, format="JPEG", quality=85, optimize=True)
            encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
            return f"data:image/jpeg;base64,{encoded}"
    except Exception:
        mime, _ = mimetypes.guess_type(str(file_path))
        if not mime or not mime.startswith("image/"):
            return None
        try:
            data = file_path.read_bytes()
            encoded = base64.b64encode(data).decode("utf-8")
            return f"data:{mime};base64,{encoded}"
        except Exception:
            return None
