---
name: vbee-tts
description: Generate natural Vietnamese narration with Vbee AIVoice (vbee.vn). Use when creating Vietnamese voiceovers, when the user requests Vbee TTS, or when narration needs regional Vietnamese accents (North, South, Central).
---

# Vbee AIVoice TTS

Vbee (vbee.vn) provides specialized Vietnamese neural text-to-speech with natural intonation and distinct regional accents (North/Hanoi, South/Saigon, Central/Hue).

Requires `VBEE_ACCESS_TOKEN` (or `VBEE_API_KEY`) and `VBEE_APP_ID` in `.env`.

Optional:
- `VBEE_VOICE_CODE_VI`: Default Vietnamese speaker voice code (defaults to `hn_female_ngochuyen_full_48k-fhg`).
- `VBEE_VOICE_CODE_EN`: Voice code for English-language text (defaults to `am_echo`). Set `language="en"` in the tool call to activate.
- `VBEE_API_URL`: Custom endpoint override (defaults to `https://vbee.vn/api/v1/tts`).

## Popular Voices and Aliases

OpenMontage provides friendly aliases for commonly used Vbee voices:

| Region | Alias / Voice | Vbee Voice Code | Description |
|---|---|---|---|
| **Northern (Bắc)** | `ngochuyen`, `hn_female` | `hn_female_ngochuyen_full_48k-fhg` | Ngọc Huyền (Hà Nội, nữ, giọng chuẩn tin tức / thuyết minh) |
| | `manhdung`, `hn_male` | `hn_male_manhdung_news_48k-fhg` | Mạnh Dũng (Hà Nội, nam, giọng đọc báo / chuyên nghiệp) |
| | `maiphuong` | `hn_female_maiphuong_48k-fhg` | Mai Phương (Hà Nội, nữ) |
| | `thutrang` | `hn_female_thutrang_48k-fhg` | Thu Trang (Hà Nội, nữ) |
| | `ducanh` | `hn_male_ducanh_48k-fhg` | Đức Anh (Hà Nội, nam) |
| **Southern (Nam)** | `thaotrinh`, `sg_female` | `sg_female_thaotrinh_48k-fhg` | Thảo Trinh (Sài Gòn, nữ, truyền cảm) |
| | `minhhoang`, `sg_male` | `sg_male_minhhoang_48k-fhg` | Minh Hoàng (Sài Gòn, nam, ấm áp) |
| | `lanhuong` | `sg_female_lanhuong_48k-fhg` | Lan Hương (Sài Gòn, nữ) |
| **Central (Trung)** | `huonggiang`, `hue_female` | `hue_female_huonggiang_48k-fhg` | Hương Giang (Huế, nữ, dịu dàng) |
| | `duyphuong`, `hue_male` | `hue_male_duyphuong_48k-fhg` | Duy Phương (Huế, nam) |

Any full `voice_code` from the Vbee voice library (https://vbee.vn) can also be passed directly.

## Usage via TTS Selector

```python
from tools.audio.tts_selector import TTSSelector

result = TTSSelector().execute({
    "preferred_provider": "vbee",
    "text": "Chào mừng bạn đến với OpenMontage, hệ thống sản xuất video tự động bằng AI.",
    "voice_id": "ngochuyen",
    "speed": 1.0,
    "output_format": "mp3",
    "output_path": "projects/my-project/assets/audio/narration.mp3",
})
```

## Direct Tool Usage

```python
from tools.audio.vbee_tts import VbeeTTS

result = VbeeTTS().execute({
    "text": "Trí tuệ nhân tạo đang thay đổi cách chúng ta sáng tạo nội dung số.",
    "voice_code": "hn_male_manhdung_news_48k-fhg",
    "speed_rate": 1.0,
    "audio_type": "mp3",
    "output_path": "projects/my-project/assets/audio/voiceover.mp3",
})
```

## Parameter Guide

- `text` (required): Vietnamese narration text. Use clear punctuation (commas, periods) to ensure natural pauses.
- `voice_code` / `voice_id`: Voice alias or exact Vbee voice code.
- `speed_rate` / `speed`: Float between `0.1` and `1.9` (default `1.0`).
- `audio_type` / `format`: `"mp3"` (default) or `"wav"`.
- `output_path`: Target file destination (always under `projects/<project-id>/`).
- `metadata_path`: Optional JSON metadata file path (defaults next to `output_path`).
