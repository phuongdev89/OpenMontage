"""Persist source images and build question-scoped prompt packages."""
import base64
import io
import json
import math
import re
import uuid
import unicodedata
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


def question_items(analysis):
    questions = analysis.get("questions") or []
    if not isinstance(questions, list):
        questions = [questions]
    result, used = [], set()
    for index, question in enumerate(questions):
        if isinstance(question, dict):
            text = question.get("text") or question.get("question") or question.get("title") or ""
            number = question.get("number", question.get("id", index + 1))
        else:
            text, number = str(question), index + 1
        ascii_text = unicodedata.normalize("NFKD", str(text).lower().replace("đ", "d")).encode("ascii", "ignore").decode()
        slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")[:100].rstrip("-") or f"cau-hoi-{index + 1}"
        if slug in {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}:
            slug = "cau-hoi-" + slug
        base, suffix = slug, 2
        while slug in used:
            slug = f"{base}-{suffix}"
            suffix += 1
        used.add(slug)
        result.append({"number": str(number), "text": str(text), "slug": slug})
    return result


def crop_images(crops, images, output, questions):
    result = []
    counts = {}
    for index, crop in enumerate(crops):
        source_index = crop.get("image_index")
        box = crop.get("box")
        if type(source_index) is not int or not 0 <= source_index < len(images):
            raise ValueError("Crop tham chiếu ảnh không hợp lệ")
        if not isinstance(box, list) or len(box) != 4 or any(
            type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1000 for v in box
        ) or box[0] >= box[2] or box[1] >= box[3]:
            raise ValueError("Tọa độ crop không hợp lệ")
        question_ref = str(crop.get("question", ""))
        matches = [question for question in questions if question_ref in {question["number"], question["text"]}]
        if len(matches) == 1:
            question = matches[0]
        elif len(questions) == 1:
            question = questions[0]
        else:
            raise ValueError("Không xác định được câu hỏi tương ứng với ảnh crop")
        slug = question["slug"]
        counts[slug] = counts.get(slug, 0) + 1
        name = slug + (f"-anh-{counts[slug]}" if counts[slug] > 1 else "") + ".png"
        # A slug from a different question can collide with a numbered image.
        while (output / name).exists():
            counts[slug] += 1
            name = f"{slug}-anh-{counts[slug]}.png"
        source = images[source_index]
        with Image.open(DATA_DIR / source["file"]) as image:
            # Outward rounding preserves edge labels. Coordinates include padding.
            pixels = (math.floor(box[0] * image.width / 1000), math.floor(box[1] * image.height / 1000),
                      math.ceil(box[2] * image.width / 1000), math.ceil(box[3] * image.height / 1000))
            image.crop(pixels).save(output / name)
        result.append({"file": name, "source": source["file"], "box": pixels,
                       "question": question["number"], "slug": slug, "description": crop.get("description", "")})
    return result


def package_prompt(prompt, crops, directory, analysis):
    blocks = [block.strip() for block in re.findall(r"```[^\n]*\n(.*?)```", prompt, re.S)] or [prompt.strip()]
    questions = question_items(analysis)
    if len(blocks) != len(questions):
        raise ValueError("Số prompt không khớp số câu hỏi; cần một block đầy đủ cho mỗi câu")
    base = f"/api/packages/{directory.name}"
    prompts = []
    for question, raw in zip(questions, blocks):
        name = question["slug"] + ".txt"
        (directory / name).write_text(raw, encoding="utf-8")
        prompts.append({"file": name, "url": base + "/" + name, "question": question["number"]})
    (directory / "manifest.json").write_text(json.dumps({"analysis": analysis, "crops": crops},
                                                       ensure_ascii=False, indent=2), encoding="utf-8")
    return {"raw_url": prompts[0]["url"], "prompts": prompts,
            "crops": [{**crop, "url": base + "/" + crop["file"]} for crop in crops]}
