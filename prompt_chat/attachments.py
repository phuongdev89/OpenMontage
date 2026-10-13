"""Persist source images and build question-scoped prompt packages."""
import base64
import io
import json
import math
import re
import uuid
import zipfile
from pathlib import Path

from fastapi import HTTPException
from PIL import Image, ImageOps

DATA_DIR = Path(__file__).resolve().parent / "data" / "files"
MAX_IMAGES = 8
MAX_IMAGE_BYTES = 10 * 1024 * 1024


def store_images(images):
    if len(images) > MAX_IMAGES:
        raise HTTPException(400, "Tối đa 8 ảnh mỗi tin nhắn.")
    stored = []
    for image in images:
        try:
            prefix, encoded = image.data_url.split(",", 1)
            if prefix not in {"data:image/png;base64", "data:image/jpeg;base64", "data:image/webp;base64"}:
                raise ValueError("Chỉ nhận PNG, JPEG hoặc WebP")
            if len(encoded) > MAX_IMAGE_BYTES * 4 // 3 + 8:
                raise ValueError("Ảnh vượt 10 MB")
            raw = base64.b64decode(encoded, validate=True)
            if len(raw) > MAX_IMAGE_BYTES:
                raise ValueError("Ảnh vượt 10 MB")
            with Image.open(io.BytesIO(raw)) as source:
                if source.width * source.height > 25_000_000:
                    raise ValueError("Ảnh vượt 25 megapixel")
                oriented = ImageOps.exif_transpose(source)
                normalized = oriented.convert("RGBA" if "A" in oriented.getbands() or "transparency" in oriented.info else "RGB")
                DATA_DIR.mkdir(parents=True, exist_ok=True)
                name = uuid.uuid4().hex + ".png"
                normalized.save(DATA_DIR / name)
                stored.append({"file": name, "name": image.name, "width": normalized.width,
                               "height": normalized.height, "url": f"/api/files/{name}"})
        except (ValueError, OSError, Image.DecompressionBombError) as exc:
            raise HTTPException(400, f"Ảnh không hợp lệ: {exc}") from exc
    return stored


def image_part(image):
    encoded = base64.b64encode((DATA_DIR / image["file"]).read_bytes()).decode()
    return {"type": "image_url", "image_url": {"url": "data:image/png;base64," + encoded}}


def crop_images(crops, images, output):
    result = []
    for index, crop in enumerate(crops):
        source_index = crop.get("image_index")
        box = crop.get("box")
        if type(source_index) is not int or not 0 <= source_index < len(images):
            raise ValueError("Crop tham chiếu ảnh không hợp lệ")
        if not isinstance(box, list) or len(box) != 4 or any(
            type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1000 for v in box
        ) or box[0] >= box[2] or box[1] >= box[3]:
            raise ValueError("Tọa độ crop không hợp lệ")
        source = images[source_index]
        with Image.open(DATA_DIR / source["file"]) as image:
            # Outward rounding preserves edge labels. Coordinates include padding.
            pixels = (math.floor(box[0] * image.width / 1000), math.floor(box[1] * image.height / 1000),
                      math.ceil(box[2] * image.width / 1000), math.ceil(box[3] * image.height / 1000))
            name = f"figure_{index + 1:02d}.png"
            image.crop(pixels).save(output / name)
        result.append({"file": name, "source": source["file"], "box": pixels,
                       "question": crop.get("question", ""), "description": crop.get("description", "")})
    return result


def package_prompt(prompt, crops, directory, analysis):
    raw = "\n\n".join(re.findall(r"```[^\n]*\n(.*?)```", prompt, re.S)).strip() or prompt.strip()
    (directory / "prompt.txt").write_text(raw, encoding="utf-8")
    (directory / "manifest.json").write_text(json.dumps({"analysis": analysis, "crops": crops},
                                                       ensure_ascii=False, indent=2), encoding="utf-8")
    with zipfile.ZipFile(directory / "package.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(directory.iterdir()):
            if path.suffix in {".png", ".txt", ".json"}:
                archive.write(path, path.name)
    base = f"/api/packages/{directory.name}"
    return {"raw_url": base + "/prompt.txt", "zip_url": base + "/package.zip",
            "crops": [{**crop, "url": base + "/" + crop["file"]} for crop in crops]}
