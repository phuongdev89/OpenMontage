# Audit Báo Cáo: Khả Năng Tạo Video Ngoài Toán Học Trong OpenMontage

**Thời điểm audit**: 2026-10-18  
**Branch**: `phuong`  
**Trạng thái git**: Sạch (chỉ có file audit untracked)  
**Mục tiêu**: Xác minh khả năng sản xuất video phi toán học, rà soát caller branding, đối chiếu quy tắc giọng mặc định, phân định hỗ trợ cấu hình vs E2E test, kiểm tra trạng thái API tools mà không lộ secret.

---

## 1. Phân Loại 12 Pipeline Ngoài Toán (Configured vs E2E Test)

Hệ thống định nghĩa 13 pipeline manifests trong `pipeline_defs/` (12 pipeline sản xuất ngoài toán + 1 smoke test). 100% pipeline đều có file manifest YAML hợp lệ (`test_pipeline_catalog.py` pass 40/40) và đầy đủ 100% stage director markdown skills.

Mức độ kiểm thử thực tế được phân định rõ như sau:

| STT | Pipeline Manifest | Trạng Thái Kiểm Thử (Verification Level) | Bằng Chứng / Test Files |
|---|---|---|---|
| 1 | `animated-explainer.yaml` | **Đã chạy E2E hoàn chỉnh (PASS 38/38)** | `tests/qa/test_08_end_to_end.py`, `tests/contracts/test_phase0_contracts.py` |
| 2 | `cinematic.yaml` | **Tích hợp Remotion Adapter & Gate Scenarios** | `tests/tools/test_cinematic_remotion_adapter.py`, `tests/backlot/test_gate_scenarios.py` |
| 3 | `talking-head.yaml` | **Kịch bản mẫu Golden Scenario & Contracts** | `tests/eval/golden_scenarios/talking_head_basic.json`, `tests/contracts/test_phase0_contracts.py` |
| 4 | `character-animation.yaml` | **Contract Pipeline & Non-canonical Checkpoints** | `tests/contracts/test_character_animation_pipeline.py`, `tests/lib/test_checkpoint_noncanonical_stage.py` |
| 5 | `documentary-montage.yaml` | **Governance & Corpus Retrieval Contracts** | `tests/tools/test_documentary_governance.py`, `tests/contracts/test_pipeline_catalog.py` |
| 6 | `animation.yaml` | **Kiểm thử Compose & Formats Contract** | `tests/qa/test_09_hyperframes_compose.py`, `tests/tools/test_hyperframes_compose.py`, `tests/test_output_formats.py` |
| 7 | `screen-demo.yaml` | **Contract Catalog & Skill Pointers** | `tests/contracts/test_pipeline_catalog.py`, `tests/contracts/test_agent_skill_pointers.py` |
| 8 | `avatar-spokesperson.yaml` | **Hỗ trợ theo cấu hình (Configuration-ready)** | Manifest + 7 stage director skills; chưa có file test E2E riêng |
| 9 | `clip-factory.yaml` | **Hỗ trợ theo cấu hình (Configuration-ready)** | Manifest + 7 stage director skills; chưa có file test E2E riêng |
| 10 | `hybrid.yaml` | **Hỗ trợ theo cấu hình (Configuration-ready)** | Manifest + 7 stage director skills; `tests/backlot/test_ui_bug_bash.py` |
| 11 | `localization-dub.yaml` | **Hỗ trợ theo cấu hình (Configuration-ready)** | Manifest + 7 stage director skills; chưa có file test E2E riêng |
| 12 | `podcast-repurpose.yaml` | **Hỗ trợ theo cấu hình (Configuration-ready)** | Manifest + 7 stage director skills; chưa có file test E2E riêng |

---

## 2. Bằng Chứng Kiểm Thử E2E (`test_08_end_to_end.py`)

### Lệnh thực thi & Exit Code
- **Command**: `.\.venv\Scripts\python.exe tests/qa/test_08_end_to_end.py`
- **Exit Code**: `0`
- **Kết quả tổng kết**: `END-TO-END TEST COMPLETE: 38 passed, 0 failed`

### Trích xuất Log Thực Tế
```text
--- Stage 0: research ---
  [PASS] Research brief validates against schema
  [PASS] Research checkpoint written
--- Stage 1: proposal ---
  [PASS] Proposal packet validates against schema
  [PASS] Proposal checkpoint written
--- Stage 2: script ---
  [PASS] Script validates against schema
--- Stage 3: scene_plan ---
  [PASS] Scene plan validates against schema
--- Stage 4: assets ---
  [PASS] Asset manifest validates against schema
  [PASS] All asset files exist on disk
--- Stage 5: edit ---
  [PASS] Edit decisions validates against schema
--- Stage 6: compose (real tools) ---
  Mixing audio...
  [PASS] Audio mix succeeded
  Composing video...
  [PASS] Video compose succeeded
  [PASS] Output video exists
  Output: 1920x1080 h264 | 60.0s | Audio: aac | Size: 720532 bytes
  [PASS] Video has audio track
  [PASS] Video has video track
  [PASS] Duration > 30s -- 60.0s
  [PASS] Render report validates against schema
--- Stage 7: publish ---
  [PASS] Publish log validates against schema
Final video: D:\AI\OpenMontage\tests\qa\output\e2e_final_output.mp4
```

### Xác định Bản Chất Test (Mock vs Real Provider)
- **Bản chất**: **Hybrid Simulation**.
  - **Synthetic / Mock (Stage 0 đến 5)**: Các artifact (`research_brief`, `proposal_packet`, `script`, `scene_plan`, `asset_manifest`, `edit_decisions`) dùng dữ liệu JSON giả lập để kiểm tra schema, gate logic và lifecycle checkpoint. Assets media đầu vào dùng tín hiệu tổng hợp FFmpeg lavfi (`sine`, `color`).
  - **Real Local Provider (Stage 6 - Compose)**: Gọi trực tiếp các tool thực thi nội bộ `audio_mixer` và `video_compose` điều khiển FFmpeg cục bộ để hòa âm (loudnorm, ducking) và ghép video hoàn chỉnh thành tệp MP4 thực tế `e2e_final_output.mp4` (60s, 1920x1080, h264, aac).
  - **Không dùng Cloud API**: Không gọi các provider cloud trả phí (OpenAI, Runway, ElevenLabs).

---

## 3. Trạng Thái Cấu Hình Tools & Providers (Bảo Mật Tuyệt Đối Secrets)

Hệ thống phát hiện chính xác **138 tools** trong `tools.tool_registry`. Phân định trạng thái theo enum `ToolStatus` (`tools/base_tool.py:ToolStatus`):

| Trạng Thái Tool | Số Lượng | Tỷ Lệ | Diễn Giải Chi Tiết |
|---|---|---|---|
| `available` (Khả dụng ngay) | **41** | 29.7% | Sẵn sàng hoạt động (Local FFmpeg, Remotion, VieNeu v3.8.3, Vbee API, Mermaid, Pygments...) |
| `unavailable` (Chưa cấu hình) | **96** | 69.6% | Thiếu API key trong `.env` (Runway, Sora, Veo, Kling, ElevenLabs, HeyGen...) |
| `degraded` (Hoạt động một phần) | **1** | 0.7% | **`corpus_builder`**: 7/16 nguồn mở không cần key (Archive.org, Wikimedia, NASA...) sẵn sàng, nhưng thiếu package `cv2` và API key của các kho thương mại (Pexels, Unsplash) |
| **Tổng cộng** | **138** | 100% | **41 (available) + 96 (unavailable) + 1 (degraded) = 138** |

- **Tools khả dụng ngay (Configured / Local Ready): 41 tools**
  - **FFmpeg & FFprobe**: 100% sẵn sàng cho cắt ghép, hòa âm, probe, trích frame, watermark.
  - **Remotion**: Sẵn sàng qua Node.js (`remotion-composer/src/Root.tsx`).
  - **Local TTS / STT**: `vieneu-tts` (đã cài đặt `vieneu` 3.8.3 trong `.venv`), `whisperx`.
  - **Cloud TTS có sẵn cấu hình**: `vbee_tts` (đã có thông tin cấu hình trong môi trường).
  - **Local Utilities**: `diagram_gen` (Mermaid), `code_snippet` (Pygments), `threejs_world`, `export_bundle`, `composition_validator`.
- **Tools chưa khả dụng (Missing Keys / Packages): 96 tools**
  - **Generative Video Cloud**: `runway`, `veo`, `sora`, `kling`, `minimax`, `wan`, `ltx`, `seedance` (chưa có API key).
  - **Generative Image Cloud**: `ideogram`, `recraft`, `flux`, `fal`, `google_imagen` (chưa có API key).
  - **Cloud TTS/Music phụ**: `elevenlabs`, `cartesia`, `azure`, `dashscope`, `suno` (chưa có API key).
  - **Avatar Cloud**: `heygen`, `sadtalker` (chưa có API key).
- **Tool Degraded: 1 tool (`corpus_builder`)**
  - Vẫn chạy được retrieval trên các kho tư liệu mở công cộng (Archive.org, NASA, Wikimedia), nhưng giảm hiệu năng do thiếu opencv-python và thiếu kho ảnh/video Pexels/Unsplash.
  - **Bảo mật**: Không có bất kỳ giá trị secret hay API key nào được hiển thị trong báo cáo.

---

## 4. Rà Soát Caller Của `channel-branding.md` (Xác Minh Phạm Vi Áp Dụng)

Kiểm tra toàn bộ codebase cho thấy `skills/pipelines/shared/channel-branding.md`:
1. **Duy nhất các caller liên quan đến kênh Toán Olympic Cùng Con**:
   - `skills/pipelines/math/compose-director.md:1`
   - `AGENTS.md:153-155`: *"Đọc skills/pipelines/shared/channel-branding.md trước assets/compose cho video kênh này."*
   - `AGENT_GUIDE.md:716-717`: *"For Toán Olympic Cùng Con channel videos, read channel-branding before assets and compose."*
2. **Không có bất kỳ non-math pipeline nào gọi file này**:
   - Các file director của `animated-explainer`, `cinematic`, `talking-head`, `avatar-spokesperson`, `character-animation`... hoàn toàn không chứa tham chiếu đến `channel-branding.md`.
3. **Quy định nội tại của file (`channel-branding.md:7-8`)**:
   - *"Apply this identity to this channel's videos, not unrelated client channels."*
4. **Kết luận**:
   - Việc file đặt tại thư mục `shared/` là cách sắp xếp cấu trúc tài liệu. Caller rà soát chứng minh file này **không hề bị áp nhầm vào luồng video ngoài toán**.

---

## 5. Đối Chiếu Quy Tắc Giọng Nam Với Mặc Định `Minh Quân`

Đối chiếu giữa các văn bản governance:
- **`AGENTS.md:98-100` (Binding Rule)**:
  - *"1. Giọng mặc định bắt buộc là Minh Quân."*
  - *"2. Luôn truyền rõ tham số voice='Minh Quân'."*
  - *"3. Không được dùng Anh Khôi, Đoan Trang hoặc giọng khác nếu người dùng chưa yêu cầu rõ."*
- **`CLAUDE.md:144-146`**:
  - *"First: try vieneu-tts skill to generate audio locally with VieNeu-TTS and the selected male preset voice."*
- **`prompt_chat/prompt_rules.md:50`**:
  - *"VI: thử VieNeu thực tế trước, truyền voice='Minh Quân'..."*

### Đánh giá & Điều chỉnh đề xuất:
- Cụm từ *"selected male preset voice"* trong `CLAUDE.md:145` là sự cụ thể hóa của quy định bắt buộc dùng giọng **Minh Quân** tại `AGENTS.md:98`.
- Do đó, việc dùng giọng nam Minh Quân **không phải lỗi rò rỉ riêng của toán**, mà là **chính sách voice mặc định của toàn dự án OpenMontage**.
- **Đề xuất chuẩn xác**: Giữ nguyên `Minh Quân` làm giọng mặc định theo đúng `AGENTS.md:98`. Chỉ chuyển sang giọng nữ (như `Đoan Trang`) hoặc giọng khác khi người dùng có yêu cầu rõ ràng cho video cụ thể đó.

---

## 6. Điểm Cần Chú Ý Ở Tầng Governance

1. **Cảnh báo Vbee English (`CLAUDE.md:167-170`)**:
   - Nằm dưới mục `### English problem reading (math videos)`. Cần chú thích rõ ràng rằng điều kiện blocker này chỉ kích hoạt đối với các video toán có phần đọc đề tiếng Anh, không chặn luồng TTS tiếng Việt của các video phi toán.
2. **Pipeline `documentary-montage.yaml`**:
   - Chỉ có 5 stage (`idea` → `scene_plan` → `assets` → `edit` → `compose`), không có `script` và `publish`. Khi điều phối pipeline này cần xử lý điểm dừng hợp lệ tại `compose`.

---

## 7. Kết Luận Audit Cuối Cùng

1. **Phạm vi pipeline**: Hệ thống có **12 pipeline được cấu hình sẵn** (manifest YAML + 100% stage skills). Trong đó:
   - 7 pipeline có kiểm thử ở các cấp độ khác nhau (E2E hybrid simulation, adapter, golden scenario, contract).
   - 5 pipeline ở mức hỗ trợ theo cấu hình (chưa có test E2E riêng).
2. **Năng lực E2E thực tế**:
   - Bài test `test_08_end_to_end.py` (PASS 38/38) là bài **mô phỏng hybrid** (dùng mock JSON artifact cho planning/assets và gọi FFmpeg cục bộ thật để compose video). Bài này **chưa chứng minh E2E production với các cloud AI provider thật**.
3. **Phân bổ trạng thái tools**:
   - Tổng 138 tools: **41 available + 96 unavailable + 1 degraded (`corpus_builder`) = 138**.
   - Sẵn sàng ngay các luồng render local (FFmpeg, Remotion, VieNeu TTS). Thiếu API keys cho các dịch vụ sinh video/ảnh AI cloud.
4. **Branding & Voice Governance**:
   - `channel-branding.md`: Được bảo vệ chặt chẽ bởi caller, không rò rỉ sang video ngoài toán.
   - Giọng đọc: Khớp contract `AGENTS.md:98`, giữ mặc định `Minh Quân` cho toàn dự án, chỉ đổi giọng khi có yêu cầu cụ thể từ người dùng.

