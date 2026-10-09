"""Vbee AIVoice text-to-speech provider tool.

Vbee (vbee.vn) provides natural, expressive Vietnamese neural speech synthesis
with regional accents (North/Hanoi, South/Saigon, Central/Hue).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    RetryPolicy,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolStatus,
    ToolTier,
)


class VbeeTTS(BaseTool):
    name = "vbee_tts"
    version = "0.1.0"
    tier = ToolTier.VOICE
    capability = "tts"
    provider = "vbee"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.ASYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.API

    dependencies = ["env:VBEE_ACCESS_TOKEN", "env:VBEE_APP_ID"]
    install_instructions = (
        "Set VBEE_ACCESS_TOKEN (or VBEE_API_KEY) to your Vbee access token.\n"
        "Set VBEE_APP_ID to your Vbee application ID from https://studio.vbee.vn/apps.\n"
        "Optional: set VBEE_VOICE_CODE to override the default voice.\n"
        "Optional: set VBEE_API_URL to override the endpoint (defaults to https://vbee.vn/api/v1/tts)."
    )
    fallback = "google_tts"
    fallback_tools = ["google_tts", "elevenlabs_tts", "openai_tts", "piper_tts"]
    agent_skills = ["vbee-tts", "text-to-speech"]

    capabilities = [
        "text_to_speech",
        "voice_selection",
        "multilingual",
    ]
    supports = {
        "voice_cloning": False,
        "multilingual": True,
        "offline": False,
        "native_audio": True,
        "vietnamese_specialized": True,
    }
    best_for = [
        "natural Vietnamese narration across regional accents",
        "Vietnamese explainer and educational videos",
        "Vietnamese corporate and news voiceovers",
    ]
    not_good_for = [
        "fully offline production",
        "zero-credential environments",
        "real-time interactive streaming audio",
    ]

    DEFAULT_API_URL = "https://vbee.vn/api/v1/tts"
    DEFAULT_VOICE = "hn_female_ngochuyen_full_48k-fhg"

    VOICE_ALIASES: dict[str, str] = {
        # Northern (Hà Nội)
        "ngochuyen": "hn_female_ngochuyen_full_48k-fhg",
        "hn_female": "hn_female_ngochuyen_full_48k-fhg",
        "hanoi_female": "hn_female_ngochuyen_full_48k-fhg",
        "manhdung": "hn_male_manhdung_news_48k-fhg",
        "hn_male": "hn_male_manhdung_news_48k-fhg",
        "hanoi_male": "hn_male_manhdung_news_48k-fhg",
        "maiphuong": "hn_female_maiphuong_48k-fhg",
        "thutrang": "hn_female_thutrang_48k-fhg",
        "ducanh": "hn_male_ducanh_48k-fhg",

        # Southern (Sài Gòn)
        "thaotrinh": "sg_female_thaotrinh_48k-fhg",
        "sg_female": "sg_female_thaotrinh_48k-fhg",
        "saigon_female": "sg_female_thaotrinh_48k-fhg",
        "minhhoang": "sg_male_minhhoang_48k-fhg",
        "sg_male": "sg_male_minhhoang_48k-fhg",
        "saigon_male": "sg_male_minhhoang_48k-fhg",
        "lanhuong": "sg_female_lanhuong_48k-fhg",

        # Central (Huế)
        "huonggiang": "hue_female_huonggiang_48k-fhg",
        "hue_female": "hue_female_huonggiang_48k-fhg",
        "duyphuong": "hue_male_duyphuong_48k-fhg",
        "hue_male": "hue_male_duyphuong_48k-fhg",
    }

    input_schema = {
        "type": "object",
        "required": ["text"],
        "properties": {
            "text": {"type": "string", "description": "Text to convert to speech in Vietnamese"},
            "voice_code": {
                "type": "string",
                "description": (
                    "Vbee speaker voice code or alias (e.g. ngochuyen, manhdung, thaotrinh, "
                    "or full code hn_female_ngochuyen_full_48k-fhg). Defaults to VBEE_VOICE_CODE."
                ),
            },
            "voice_id": {
                "type": "string",
                "description": "Alias for voice_code.",
            },
            "voice": {
                "type": "string",
                "description": "Alias for voice_code.",
            },
            "audio_type": {
                "type": "string",
                "default": "mp3",
                "enum": ["mp3", "wav"],
                "description": "Output audio format (mp3 or wav).",
            },
            "format": {
                "type": "string",
                "enum": ["mp3", "wav"],
                "description": "Alias for audio_type.",
            },
            "speed_rate": {
                "type": "number",
                "default": 1.0,
                "minimum": 0.1,
                "maximum": 1.9,
                "description": "Speech speed rate (0.1 - 1.9, default 1.0).",
            },
            "speed": {
                "type": "number",
                "description": "Alias for speed_rate.",
            },
            "speaking_rate": {
                "type": "number",
                "description": "Alias for speed_rate.",
            },
            "callback_url": {
                "type": "string",
                "description": "Optional callback URL for completion notifications.",
            },
            "output_path": {"type": "string"},
            "metadata_path": {
                "type": "string",
                "description": "Where to save the query metadata JSON. Defaults next to output_path.",
            },
            "poll_interval_seconds": {
                "type": "number",
                "default": 2.0,
                "minimum": 0.5,
            },
            "timeout_seconds": {
                "type": "integer",
                "default": 300,
                "minimum": 10,
            },
        },
    }

    output_schema = {
        "type": "object",
        "properties": {
            "output": {"type": "string"},
            "metadata_path": {"type": "string"},
            "task_id": {"type": "string"},
            "audio_duration_seconds": {"type": ["number", "null"]},
            "voice_code": {"type": "string"},
            "audio_type": {"type": "string"},
            "audio_link": {"type": "string"},
        },
    }

    artifact_schema = {
        "type": "array",
        "items": {"type": "string"},
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=256, vram_mb=0, disk_mb=50, network_required=True
    )
    retry_policy = RetryPolicy(
        max_retries=2,
        backoff_seconds=2.0,
        retryable_errors=["timeout", "rate_limit", "connection", "server_error"],
    )
    idempotency_key_fields = ["text", "voice_code", "speed_rate", "audio_type"]
    side_effects = [
        "writes audio file to output_path",
        "writes Vbee query metadata JSON next to output_path",
        "calls Vbee AIVoice API",
    ]
    user_visible_verification = [
        "Listen to generated audio for Vietnamese regional naturalness and pacing",
        "Check audio duration against planned scene timing",
    ]
    quality_score = 0.86
    latency_p50_seconds = 5.0

    @classmethod
    def _resolve_credentials(cls) -> tuple[str | None, str | None]:
        token = os.environ.get("VBEE_ACCESS_TOKEN") or os.environ.get("VBEE_API_KEY")
        app_id = os.environ.get("VBEE_APP_ID")
        return token, app_id

    def get_status(self) -> ToolStatus:
        token, app_id = self._resolve_credentials()
        if token and app_id:
            return ToolStatus.AVAILABLE
        return ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        text = inputs.get("text", "")
        # Vbee standard pricing is approx ~0.000008 USD per character (~200 VND / 1000 chars)
        return round(len(text) * 0.000008, 6)

    def _resolve_voice(self, inputs: dict[str, Any]) -> str:
        raw_voice = (
            inputs.get("voice_code")
            or inputs.get("voice_id")
            or inputs.get("voice")
            or os.environ.get("VBEE_VOICE_CODE")
            or self.DEFAULT_VOICE
        )
        normalized = str(raw_voice).strip().lower()
        return self.VOICE_ALIASES.get(normalized, str(raw_voice).strip())

    @staticmethod
    def _resolve_speed(inputs: dict[str, Any]) -> float:
        speed = inputs.get("speed_rate")
        if speed is None:
            speed = inputs.get("speed")
        if speed is None:
            speed = inputs.get("speaking_rate")
        if speed is None:
            return 1.0
        try:
            val = float(speed)
            return round(max(0.1, min(1.9, val)), 2)
        except (ValueError, TypeError):
            return 1.0

    @staticmethod
    def _resolve_audio_type(inputs: dict[str, Any]) -> str:
        fmt = str(inputs.get("audio_type") or inputs.get("format") or "mp3").lower()
        return "wav" if fmt in ("wav", "wave") else "mp3"

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        token, app_id = self._resolve_credentials()
        if not token or not app_id:
            missing = []
            if not token:
                missing.append("VBEE_ACCESS_TOKEN (or VBEE_API_KEY)")
            if not app_id:
                missing.append("VBEE_APP_ID")
            return ToolResult(
                success=False,
                error=f"Vbee credentials not configured: missing {', '.join(missing)}. {self.install_instructions}",
            )

        text = inputs.get("text", "").strip()
        if not text:
            return ToolResult(success=False, error="Input 'text' is required and cannot be empty.")

        voice_code = self._resolve_voice(inputs)
        speed_rate = self._resolve_speed(inputs)
        audio_type = self._resolve_audio_type(inputs)
        api_url = os.environ.get("VBEE_API_URL") or self.DEFAULT_API_URL

        output_path = Path(inputs.get("output_path", f"vbee_tts.{audio_type}"))
        metadata_path = Path(
            inputs.get("metadata_path") or output_path.with_suffix(output_path.suffix + ".json")
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)

        start = time.time()
        try:
            result = self._generate(
                inputs,
                token=token,
                app_id=app_id,
                api_url=api_url,
                voice_code=voice_code,
                speed_rate=speed_rate,
                audio_type=audio_type,
                output_path=output_path,
                metadata_path=metadata_path,
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                error=f"Vbee TTS failed: {self._safe_error(exc, token=token, app_id=app_id)}",
            )

        result.duration_seconds = round(time.time() - start, 2)
        if not result.cost_usd:
            result.cost_usd = self.estimate_cost(inputs)
        return result

    def _generate(
        self,
        inputs: dict[str, Any],
        *,
        token: str,
        app_id: str,
        api_url: str,
        voice_code: str,
        speed_rate: float,
        audio_type: str,
        output_path: Path,
        metadata_path: Path,
    ) -> ToolResult:
        import requests

        text = inputs["text"].strip()
        callback_url = inputs.get("callback_url", "https://openmontage.internal/callback")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        body = {
            "app_id": app_id,
            "input_text": text,
            "voice_code": voice_code,
            "audio_type": audio_type,
            "speed_rate": speed_rate,
            "callback_url": callback_url,
        }

        submit_response = requests.post(api_url, headers=headers, json=body, timeout=(10, 60))

        # Check if direct audio stream returned
        content_type = submit_response.headers.get("Content-Type", "")
        if submit_response.status_code == 200 and content_type.startswith("audio/"):
            output_path.write_bytes(submit_response.content)
            audio_duration = self._audio_duration(output_path)
            meta = {
                "status": "SUCCESS",
                "direct_stream": True,
                "voice_code": voice_code,
                "speed_rate": speed_rate,
                "audio_type": audio_type,
            }
            metadata_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return ToolResult(
                success=True,
                data={
                    "provider": self.provider,
                    "voice_code": voice_code,
                    "audio_type": audio_type,
                    "speed_rate": speed_rate,
                    "text_length": len(text),
                    "output": str(output_path),
                    "metadata_path": str(metadata_path),
                    "audio_duration_seconds": round(audio_duration, 2) if audio_duration else None,
                },
                artifacts=[str(output_path), str(metadata_path)],
                cost_usd=self.estimate_cost(inputs),
                model=f"vbee:{voice_code}",
            )

        submit_data = self._json_or_raise(submit_response)
        self._raise_for_vbee_error(submit_response.status_code, submit_data)

        # Extract request_id or direct audio_link if completed immediately
        task_id = self._extract_request_id(submit_data)
        audio_link = self._extract_audio_link(submit_data)

        query_data = submit_data
        if not audio_link:
            if not task_id:
                raise RuntimeError(
                    f"Vbee submit succeeded but returned neither request_id nor audio_link: {submit_data}"
                )
            query_data = self._poll_query(
                requests_module=requests,
                api_url=api_url,
                token=token,
                task_id=task_id,
                poll_interval=float(inputs.get("poll_interval_seconds", 2.0)),
                timeout_seconds=int(inputs.get("timeout_seconds", 300)),
            )
            audio_link = self._extract_audio_link(query_data)

        if not audio_link:
            raise RuntimeError(f"Vbee task completed but did not return audio_link: {query_data}")

        audio_response = requests.get(audio_link, timeout=(10, 120))
        audio_response.raise_for_status()
        output_path.write_bytes(audio_response.content)

        metadata_path.write_text(json.dumps(query_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        audio_duration = self._audio_duration(output_path)
        cost = self.estimate_cost(inputs)

        return ToolResult(
            success=True,
            data={
                "provider": self.provider,
                "model": f"vbee:{voice_code}",
                "voice_code": voice_code,
                "audio_type": audio_type,
                "speed_rate": speed_rate,
                "text_length": len(text),
                "task_id": task_id,
                "audio_link": audio_link,
                "audio_duration_seconds": round(audio_duration, 2) if audio_duration else None,
                "output": str(output_path),
                "metadata_path": str(metadata_path),
            },
            artifacts=[str(output_path), str(metadata_path)],
            cost_usd=cost,
            model=f"vbee:{voice_code}",
        )

    def _poll_query(
        self,
        *,
        requests_module: Any,
        api_url: str,
        token: str,
        task_id: str,
        poll_interval: float,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        deadline = time.time() + timeout_seconds
        headers = {"Authorization": f"Bearer {token}"}
        status_url = f"{api_url.rstrip('/')}/{task_id}"

        while time.time() < deadline:
            time.sleep(poll_interval)
            response = requests_module.get(status_url, headers=headers, timeout=(10, 60))
            data = self._json_or_raise(response)
            self._raise_for_vbee_error(response.status_code, data)

            status = self._extract_status(data)
            if status in ("SUCCESS", "COMPLETED", "DONE", 1, 200):
                return data
            if status in ("FAILED", "ERROR", "FAILURE"):
                msg = data.get("message") or (data.get("result") or {}).get("message") or "Task processing failed"
                raise RuntimeError(f"Vbee task {task_id} failed: {msg}")

        raise TimeoutError(f"Vbee task {task_id} did not finish within {timeout_seconds} seconds")

    @staticmethod
    def _extract_request_id(data: dict[str, Any]) -> str | None:
        result = data.get("result")
        if isinstance(result, dict) and result.get("request_id"):
            return str(result["request_id"])
        data_field = data.get("data")
        if isinstance(data_field, dict) and data_field.get("request_id"):
            return str(data_field["request_id"])
        if data.get("request_id"):
            return str(data["request_id"])
        if data.get("id"):
            return str(data["id"])
        return None

    @staticmethod
    def _extract_audio_link(data: dict[str, Any]) -> str | None:
        result = data.get("result")
        if isinstance(result, dict):
            if result.get("audio_link"):
                return str(result["audio_link"])
            if result.get("audio_url"):
                return str(result["audio_url"])
        data_field = data.get("data")
        if isinstance(data_field, dict):
            if data_field.get("audio_link"):
                return str(data_field["audio_link"])
            if data_field.get("audio_url"):
                return str(data_field["audio_url"])
        if data.get("audio_link"):
            return str(data["audio_link"])
        if data.get("audio_url"):
            return str(data["audio_url"])
        return None

    @staticmethod
    def _extract_status(data: dict[str, Any]) -> str | int:
        result = data.get("result")
        if isinstance(result, dict) and "status" in result:
            return result["status"]
        data_field = data.get("data")
        if isinstance(data_field, dict) and "status" in data_field:
            return data_field["status"]
        if "status" in data:
            return data["status"]
        return "UNKNOWN"

    @staticmethod
    def _json_or_raise(response: Any) -> dict[str, Any]:
        try:
            return response.json()
        except ValueError as exc:
            raise RuntimeError(f"Non-JSON response from Vbee API: HTTP {response.status_code}") from exc

    def _raise_for_vbee_error(self, http_status: int, payload: dict[str, Any]) -> None:
        if http_status >= 400:
            msg = payload.get("message") or payload.get("error") or "HTTP error"
            code = payload.get("code") or payload.get("status")
            hint = self._diagnostic_hint(str(msg))
            raise RuntimeError(f"Vbee HTTP {http_status}, code {code}: {msg}{hint}")

        status = self._extract_status(payload)
        if status in ("FAILED", "ERROR"):
            msg = payload.get("message") or (payload.get("result") or {}).get("message") or "API error"
            hint = self._diagnostic_hint(str(msg))
            raise RuntimeError(f"Vbee error: {msg}{hint}")

    @staticmethod
    def _diagnostic_hint(message: str) -> str:
        lowered = message.lower()
        if "unauthorized" in lowered or "invalid token" in lowered or "token" in lowered:
            return " (check VBEE_ACCESS_TOKEN / VBEE_API_KEY)"
        if "app_id" in lowered or "app not found" in lowered:
            return " (check VBEE_APP_ID)"
        if "voice" in lowered or "not found" in lowered:
            return " (check voice_code and available voices in Vbee voice library)"
        if "balance" in lowered or "quota" in lowered or "credit" in lowered:
            return " (check account balance or credits on vbee.vn)"
        return ""

    @staticmethod
    def _safe_error(exc: Exception, *, token: str | None = None, app_id: str | None = None) -> str:
        err = str(exc)
        if token:
            err = err.replace(token, "[redacted]")
        if app_id:
            err = err.replace(app_id, "[redacted]")
        return err

    @staticmethod
    def _audio_duration(path: Path) -> float | None:
        try:
            from tools.analysis.audio_probe import probe_duration

            return probe_duration(path)
        except Exception:
            return None
