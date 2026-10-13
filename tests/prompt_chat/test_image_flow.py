import base64
import io
import json
import zipfile
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from prompt_chat import attachments, server


def test_gateway_fenced_json_supported():
    assert server.parse_ai_json('```json\n{"ok":true}\n```') == {"ok": True}


@pytest.mark.parametrize("field, question", [("source", "Nguồn"), ("grade", "lớp hoặc bậc"), ("solution_mode", "để ngỏ")])
def test_each_missing_preference_blocks_generation(harness, monkeypatch, field, question):
    client, conv = harness
    analysis = {"source": "A", "grade": "2", "solution_mode": "solve", "questions": "Q"}
    analysis[field] = None
    calls = mock_ai(monkeypatch, analysis)
    done = events(client.post(f"/api/conversations/{conv}/messages", json={"content": "Q"}))[-1]
    assert question in done["content"]
    assert done["metadata"]["kind"] == "clarification"
    assert len(calls) == 1


def test_invalid_crop_is_not_packaged(harness, monkeypatch):
    client, conv = harness
    calls = mock_ai(monkeypatch, {"source": "A", "grade": "2", "solution_mode": "open", "questions": "Q",
        "crops": [{"image_index": 0, "box": [-5, 0, 500, 500]}]})
    done = events(client.post(f"/api/conversations/{conv}/messages", json={"images": [image_input()]}))[-1]
    assert "error" in done
    assert len(calls) == 1


@pytest.fixture
def harness(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "DB_PATH", tmp_path / "chat.db")
    monkeypatch.setattr(server, "DATA_DIR", tmp_path / "files")
    monkeypatch.setattr(attachments, "DATA_DIR", tmp_path / "files")
    server.init_db()
    client = TestClient(server.app)
    conv = client.post("/api/conversations", json={}).json()["id"]
    return client, conv


def image_input():
    buffer = io.BytesIO()
    Image.new("RGB", (200, 100), "white").save(buffer, format="PNG")
    return {"name": "problem.png", "data_url": "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()}


def mock_ai(monkeypatch, analysis, review=None, prompt_review=None):
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        if kwargs["messages"][0]["content"] == server.PROMPT_REVIEW:
            data = prompt_review if prompt_review is not None else {"ok": True}
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(data)))])
        if kwargs.get("stream"):
            return [SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="```text\nĐề bài; hình nguồn: figure_01.png; chế độ để ngỏ.\n```"))])]
        data = review if len(calls) == 2 and review is not None else analysis
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(data)))])
    monkeypatch.setattr(server, "get_ai_client", lambda: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    return calls


def events(response):
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]


def test_missing_metadata_asks_before_prompt_or_zip(harness, monkeypatch):
    client, conv = harness
    calls = mock_ai(monkeypatch, {"source": None, "grade": None, "solution_mode": None, "questions": "2+3=?"})
    response = client.post(f"/api/conversations/{conv}/messages", json={"images": [image_input()]})
    done = events(response)[-1]
    assert done["metadata"]["kind"] == "clarification"
    assert all(word in done["content"] for word in ["Nguồn", "lớp", "để ngỏ"])
    assert "zip_url" not in done["metadata"]
    assert len(calls) == 1
    assert any(part["type"] == "image_url" for part in calls[0]["messages"][1]["content"])
    messages = client.get(f"/api/conversations/{conv}").json()["messages"]
    assert client.get(messages[0]["metadata"]["images"][0]["url"]).status_code == 200


def test_confirmed_metadata_crops_and_exports_zip(harness, monkeypatch):
    client, conv = harness
    analysis = {"source": "Sách A", "grade": "Lớp 2", "solution_mode": "open", "questions": "Đếm hình",
                "has_diagram": True, "crops": [{"image_index": 0, "box": [100, 200, 800, 900], "question": "1"}]}
    calls = mock_ai(monkeypatch, analysis, {"ok": True})
    done = events(client.post(f"/api/conversations/{conv}/messages", json={"images": [image_input()]}))[-1]
    metadata = done["metadata"]
    assert metadata["kind"] == "prompt"
    assert len(calls) == 4
    with zipfile.ZipFile(io.BytesIO(client.get(metadata["zip_url"]).content)) as archive:
        assert set(archive.namelist()) == {"prompt.txt", "figure_01.png", "manifest.json"}
        assert not archive.read("prompt.txt").startswith(b"```")
        with Image.open(io.BytesIO(archive.read("figure_01.png"))) as image:
            assert image.size == (140, 70)
    assert client.get(metadata["raw_url"]).status_code == 200
    stored = client.get(f"/api/conversations/{conv}").json()["messages"][-1]
    assert stored["metadata"]["zip_url"] == metadata["zip_url"]


def test_bad_crop_review_blocks_prompt(harness, monkeypatch):
    client, conv = harness
    calls = mock_ai(monkeypatch, {"source": "A", "grade": "2", "solution_mode": "solve", "questions": "Q",
        "crops": [{"image_index": 0, "box": [0, 0, 500, 500]}]}, {"ok": False, "clarification": "Nhãn bị cắt, gửi ảnh rõ hơn."})
    done = events(client.post(f"/api/conversations/{conv}/messages", json={"images": [image_input()]}))[-1]
    assert done["metadata"]["kind"] == "clarification"
    assert len(calls) == 2
    assert "zip_url" not in done["metadata"]


def test_invalid_image_and_download_path_rejected(harness):
    client, conv = harness
    assert client.post(f"/api/conversations/{conv}/messages", json={"images": [{"data_url": "data:image/png;base64,invalid"}]}).status_code == 400
    assert client.get("/api/packages/not-a-package/package.zip").status_code == 404


def test_later_answer_keeps_original_image_in_history(harness, monkeypatch):
    client, conv = harness
    mock_ai(monkeypatch, {"questions": "Q"})
    client.post(f"/api/conversations/{conv}/messages", json={"images": [image_input()]})
    calls = mock_ai(monkeypatch, {"source": "A", "grade": "2", "solution_mode": "open", "questions": "Q", "crops": []})
    done = events(client.post(f"/api/conversations/{conv}/messages", json={"content": "Sách A, lớp 2, để ngỏ"}))[-1]
    assert done["metadata"]["kind"] == "prompt"
    assert any(isinstance(message["content"], list) for message in calls[0]["messages"])


def test_reviewed_prompt_is_the_downloaded_raw_content(harness, monkeypatch):
    client, conv = harness
    mock_ai(monkeypatch, {"source": "A", "grade": "2", "solution_mode": "open", "questions": "Q"},
            prompt_review={"ok": False, "corrected_prompt": "```text\nĐể ngỏ, hãy bình luận đáp án.\n```", "issues": ["answer leaked"]})
    response = events(client.post(f"/api/conversations/{conv}/messages", json={"content": "Q"}))
    done = response[-1]
    assert all("chunk" not in event for event in response)
    assert client.get(done["metadata"]["raw_url"]).text == "Để ngỏ, hãy bình luận đáp án."


def test_failed_prompt_review_without_correction_blocks_package(harness, monkeypatch):
    client, conv = harness
    mock_ai(monkeypatch, {"source": "A", "grade": "2", "solution_mode": "open", "questions": "Q"},
            prompt_review={"ok": False})
    done = events(client.post(f"/api/conversations/{conv}/messages", json={"content": "Q"}))[-1]
    assert "error" in done
    assert "metadata" not in done
