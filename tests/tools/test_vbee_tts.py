"""Focused tests for Vbee AIVoice text-to-speech tool.

No live network calls: all HTTP requests are monkeypatched.
Covers tool contract, registry discovery, status behavior, voice resolution,
polling and direct audio handling, error scenarios, and TTSSelector integration.
"""

import json
import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.base_tool import BaseTool, ToolRuntime, ToolStatus, ToolTier
from tools.tool_registry import ToolRegistry
from tools.audio.vbee_tts import VbeeTTS


FAKE_MP3 = b"\xff\xfb\x90\x00" + b"\x00" * 64
FAKE_WAV = b"RIFF" + b"\x00" * 40


class _FakeResponse:
    def __init__(
        self,
        json_data: dict[str, Any] | None = None,
        content: bytes = b"",
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ):
        self._json_data = json_data
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}

    def json(self) -> dict[str, Any]:
        if self._json_data is not None:
            return self._json_data
        raise ValueError("No JSON in response")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


@pytest.fixture
def vbee_env(monkeypatch):
    monkeypatch.setenv("VBEE_ACCESS_TOKEN", "fake-token-12345")
    monkeypatch.setenv("VBEE_APP_ID", "fake-app-67890")
    monkeypatch.delenv("VBEE_API_KEY", raising=False)
    monkeypatch.delenv("VBEE_VOICE_CODE", raising=False)
    monkeypatch.delenv("VBEE_API_URL", raising=False)


# ---- Contract ----

class TestContract:
    def test_inherits_base_tool(self):
        assert issubclass(VbeeTTS, BaseTool)

    def test_identity(self):
        tool = VbeeTTS()
        assert tool.name == "vbee_tts"
        assert tool.capability == "tts"
        assert tool.provider == "vbee"
        assert tool.runtime == ToolRuntime.API
        assert tool.tier == ToolTier.VOICE
        assert tool.fallback == "google_tts"
        assert "vbee-tts" in tool.agent_skills
        assert "text-to-speech" in tool.agent_skills
        assert tool.supports.get("vietnamese_specialized") is True

    def test_get_info_valid(self):
        info = VbeeTTS().get_info()
        assert info["name"] == "vbee_tts"
        assert info["capability"] == "tts"
        assert "text" in info["input_schema"]["properties"]
        assert "voice_code" in info["input_schema"]["properties"]

    def test_estimate_cost(self):
        tool = VbeeTTS()
        assert tool.estimate_cost({"text": "Xin chào OpenMontage"}) == pytest.approx(
            len("Xin chào OpenMontage") * 0.000008, rel=1e-3
        )
        assert tool.estimate_cost({}) == 0.0


# ---- Registry discovery ----

class TestDiscovery:
    def test_discoverable(self):
        reg = ToolRegistry()
        reg.discover("tools")
        assert reg.get("vbee_tts") is not None

    def test_capability_routing(self):
        reg = ToolRegistry()
        reg.discover("tools")
        names = [t.name for t in reg.get_by_capability("tts")]
        assert "vbee_tts" in names


# ---- Status behavior ----

class TestStatus:
    def test_unavailable_when_missing_credentials(self, monkeypatch):
        monkeypatch.delenv("VBEE_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("VBEE_API_KEY", raising=False)
        monkeypatch.delenv("VBEE_APP_ID", raising=False)
        assert VbeeTTS().get_status() == ToolStatus.UNAVAILABLE

    def test_unavailable_when_missing_app_id(self, monkeypatch):
        monkeypatch.setenv("VBEE_ACCESS_TOKEN", "token-only")
        monkeypatch.delenv("VBEE_APP_ID", raising=False)
        assert VbeeTTS().get_status() == ToolStatus.UNAVAILABLE

    def test_unavailable_when_missing_token(self, monkeypatch):
        monkeypatch.delenv("VBEE_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("VBEE_API_KEY", raising=False)
        monkeypatch.setenv("VBEE_APP_ID", "app-only")
        assert VbeeTTS().get_status() == ToolStatus.UNAVAILABLE

    def test_available_with_access_token_and_app_id(self, vbee_env):
        assert VbeeTTS().get_status() == ToolStatus.AVAILABLE

    def test_available_with_api_key_alias_and_app_id(self, monkeypatch):
        monkeypatch.delenv("VBEE_ACCESS_TOKEN", raising=False)
        monkeypatch.setenv("VBEE_API_KEY", "api-key-alias")
        monkeypatch.setenv("VBEE_APP_ID", "app-id")
        assert VbeeTTS().get_status() == ToolStatus.AVAILABLE


# ---- Voice & Parameter Resolution ----

class TestParameterResolution:
    def test_voice_alias_resolution(self):
        tool = VbeeTTS()
        assert tool._resolve_voice({"voice_code": "ngochuyen"}) == "hn_female_ngochuyen_full_48k-fhg"
        assert tool._resolve_voice({"voice_id": "HN_FEMALE"}) == "hn_female_ngochuyen_full_48k-fhg"
        assert tool._resolve_voice({"voice": "manhdung"}) == "hn_male_manhdung_news_48k-fhg"
        assert tool._resolve_voice({"voice": "thaotrinh"}) == "sg_female_thaotrinh_48k-fhg"
        assert tool._resolve_voice({"voice": "sg_male"}) == "sg_male_minhhoang_48k-fhg"
        assert tool._resolve_voice({"voice": "huonggiang"}) == "hue_female_huonggiang_48k-fhg"
        # Full or custom codes pass through untouched
        assert tool._resolve_voice({"voice": "custom_voice_48k"}) == "custom_voice_48k"
        # Default voice when empty
        assert tool._resolve_voice({}) == VbeeTTS.DEFAULT_VOICE

    def test_speed_resolution_and_clamping(self):
        tool = VbeeTTS()
        assert tool._resolve_speed({"speed_rate": 1.25}) == 1.25
        assert tool._resolve_speed({"speed": 0.8}) == 0.8
        assert tool._resolve_speed({"speaking_rate": 1.1}) == 1.1
        # Clamping
        assert tool._resolve_speed({"speed_rate": 0.05}) == 0.1
        assert tool._resolve_speed({"speed_rate": 3.0}) == 1.9
        assert tool._resolve_speed({}) == 1.0

    def test_audio_type_resolution(self):
        tool = VbeeTTS()
        assert tool._resolve_audio_type({"audio_type": "mp3"}) == "mp3"
        assert tool._resolve_audio_type({"format": "wav"}) == "wav"
        assert tool._resolve_audio_type({"format": "WAVE"}) == "wav"
        assert tool._resolve_audio_type({}) == "mp3"


# ---- Execution with Mocks ----

class TestExecute:
    def test_missing_credentials_fails(self, monkeypatch):
        monkeypatch.delenv("VBEE_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("VBEE_API_KEY", raising=False)
        monkeypatch.delenv("VBEE_APP_ID", raising=False)
        res = VbeeTTS().execute({"text": "Xin chào"})
        assert not res.success
        assert "not configured" in res.error.lower()

    def test_empty_text_fails(self, vbee_env):
        res = VbeeTTS().execute({"text": "   "})
        assert not res.success
        assert "empty" in res.error.lower()

    def test_submit_and_poll_success(self, vbee_env, tmp_path, monkeypatch):
        import requests

        post_calls = []
        get_calls = []

        def fake_post(url, headers=None, json=None, timeout=None):
            post_calls.append({"url": url, "headers": headers, "body": json})
            return _FakeResponse(
                json_data={
                    "status": 200,
                    "result": {"request_id": "req-999", "status": "IN_PROGRESS"},
                },
                status_code=200,
            )

        def fake_get(url, headers=None, timeout=None):
            get_calls.append({"url": url, "headers": headers})
            if "req-999" in url:
                return _FakeResponse(
                    json_data={
                        "status": 200,
                        "result": {
                            "status": "SUCCESS",
                            "audio_link": "https://cdn.vbee.vn/audio/output-999.mp3",
                        },
                    },
                    status_code=200,
                )
            if "output-999.mp3" in url:
                return _FakeResponse(content=FAKE_MP3, status_code=200)
            return _FakeResponse(status_code=404)

        monkeypatch.setattr(requests, "post", fake_post)
        monkeypatch.setattr(requests, "get", fake_get)
        monkeypatch.setattr(VbeeTTS, "_audio_duration", staticmethod(lambda p: 3.5))

        out_file = tmp_path / "test_vbee.mp3"
        res = VbeeTTS().execute(
            {
                "text": "Chào bạn đến với Vbee",
                "voice_code": "ngochuyen",
                "speed_rate": 1.1,
                "output_path": str(out_file),
                "poll_interval_seconds": 0.01,
            }
        )

        assert res.success
        assert res.data["provider"] == "vbee"
        assert res.data["voice_code"] == "hn_female_ngochuyen_full_48k-fhg"
        assert res.data["task_id"] == "req-999"
        assert res.data["audio_duration_seconds"] == 3.5
        assert out_file.exists()
        assert out_file.read_bytes() == FAKE_MP3

        # Verify POST payload sent
        assert len(post_calls) == 1
        assert post_calls[0]["body"]["app_id"] == "fake-app-67890"
        assert post_calls[0]["body"]["input_text"] == "Chào bạn đến với Vbee"
        assert post_calls[0]["body"]["voice_code"] == "hn_female_ngochuyen_full_48k-fhg"
        assert post_calls[0]["headers"]["Authorization"] == "Bearer fake-token-12345"

        # Verify metadata file written
        meta_file = out_file.with_suffix(".mp3.json")
        assert meta_file.exists()
        meta_content = json.loads(meta_file.read_text(encoding="utf-8"))
        assert meta_content["result"]["status"] == "SUCCESS"

    def test_direct_audio_stream(self, vbee_env, tmp_path, monkeypatch):
        import requests

        def fake_post(url, headers=None, json=None, timeout=None):
            return _FakeResponse(
                content=FAKE_MP3,
                status_code=200,
                headers={"Content-Type": "audio/mpeg"},
            )

        monkeypatch.setattr(requests, "post", fake_post)
        monkeypatch.setattr(VbeeTTS, "_audio_duration", staticmethod(lambda p: 2.1))

        out_file = tmp_path / "stream_vbee.mp3"
        res = VbeeTTS().execute(
            {
                "text": "Phát trực tiếp",
                "output_path": str(out_file),
            }
        )

        assert res.success
        assert res.data["audio_duration_seconds"] == 2.1
        assert out_file.read_bytes() == FAKE_MP3

    def test_task_failed_in_polling(self, vbee_env, tmp_path, monkeypatch):
        import requests

        def fake_post(url, headers=None, json=None, timeout=None):
            return _FakeResponse(
                json_data={"result": {"request_id": "fail-1", "status": "IN_PROGRESS"}},
                status_code=200,
            )

        def fake_get(url, headers=None, timeout=None):
            return _FakeResponse(
                json_data={
                    "status": 200,
                    "result": {"status": "FAILED", "message": "Text contains invalid characters"},
                },
                status_code=200,
            )

        monkeypatch.setattr(requests, "post", fake_post)
        monkeypatch.setattr(requests, "get", fake_get)

        res = VbeeTTS().execute(
            {
                "text": "Kiểm tra lỗi",
                "output_path": str(tmp_path / "fail.mp3"),
                "poll_interval_seconds": 0.01,
            }
        )

        assert not res.success
        assert "failed" in res.error.lower()
        assert "invalid characters" in res.error

    def test_http_401_surfaces_diagnostic(self, vbee_env, tmp_path, monkeypatch):
        import requests

        def fake_post(url, headers=None, json=None, timeout=None):
            return _FakeResponse(
                json_data={"message": "Unauthorized access token", "code": 401},
                status_code=401,
            )

        monkeypatch.setattr(requests, "post", fake_post)

        res = VbeeTTS().execute(
            {
                "text": "Kiểm tra 401",
                "output_path": str(tmp_path / "auth.mp3"),
            }
        )

        assert not res.success
        assert "401" in res.error
        assert "vbee_access_token" in res.error.lower()


# ---- TTSSelector Integration ----

class TestTTSSelectorIntegration:
    def test_selector_adapts_inputs_for_vbee(self, vbee_env, tmp_path, monkeypatch):
        import requests
        from tools.audio.tts_selector import TTSSelector

        captured_post = {}

        def fake_post(url, headers=None, json=None, timeout=None):
            captured_post.update(json or {})
            return _FakeResponse(
                json_data={
                    "result": {
                        "status": "SUCCESS",
                        "audio_link": "https://cdn.vbee.vn/audio/fast.mp3",
                    }
                },
                status_code=200,
            )

        def fake_get(url, headers=None, timeout=None):
            return _FakeResponse(content=FAKE_MP3, status_code=200)

        monkeypatch.setattr(requests, "post", fake_post)
        monkeypatch.setattr(requests, "get", fake_get)
        monkeypatch.setattr(TTSSelector, "_providers", lambda self: [VbeeTTS()])

        out_file = tmp_path / "selector_vbee.mp3"
        result = TTSSelector().execute(
            {
                "text": "Thử nghiệm bộ chọn TTS",
                "preferred_provider": "vbee",
                "voice_id": "manhdung",
                "speaking_rate": 1.2,
                "output_format": "mp3",
                "output_path": str(out_file),
            }
        )

        assert result.success
        assert result.data["selected_tool"] == "vbee_tts"
        assert result.data["selected_provider"] == "vbee"
        assert captured_post["voice_code"] == "hn_male_manhdung_news_48k-fhg"
        assert captured_post["speed_rate"] == 1.2
        assert captured_post["audio_type"] == "mp3"
