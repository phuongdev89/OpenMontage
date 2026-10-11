# OpenMontage - Core Agent Governance & Instructions

> **MANDATORY CONTRACT**: These governance rules are directly injected into runtime prompt context. They are strictly binding on every agent interaction in OpenMontage.
> Detailed guide: [`AGENT_GUIDE.md`](AGENT_GUIDE.md) | Architecture: [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md)

---

## 1. Mandatory Startup Checklist

Every production task MUST execute this sequence before calling any generation tools or creating media:

1. **Đọc AGENT_GUIDE.md**: Nắm rõ operating contract và decision protocols.
2. **Đọc pipeline manifest**: Đọc `pipeline_defs/<pipeline>.yaml` tương ứng.
3. **Xác định stage hiện tại**: Dùng `lib.checkpoint.get_next_stage()`.
4. **Đọc stage director skill**: Đọc `skills/pipelines/<pipeline>/<stage>-director.md`.
5. **Kiểm tra checkpoint predecessor**: Xác nhận stage trước đã `completed` và `human_approved` (nếu có gate).
6. **Kiểm tra stage có gated không**: Đọc `human_approval_default` từ pipeline manifest.
7. **Kiểm tra approval evidence từ tin nhắn người dùng**: Xác minh approval thực tế từ người dùng.
8. **Kiểm tra provider routing**: Xác định provider theo thứ tự ưu tiên (TTS, image, video).
9. **Nếu bất kỳ mục nào chưa xác minh, KHÔNG gọi generation tool.**

---

## 2. Pipeline State Machine & Execution Order

- **Mọi video production bắt buộc phải đi qua pipeline manifest** (`pipeline_defs/*.yaml`). Không chạy ad-hoc scripts.
- **Xác định pipeline và đọc manifest** trước khi tạo bất kỳ artifact nào hoặc gọi generation tool.
- **Tuân thủ thứ tự stage tuần tự:** `research` → `proposal`/`idea` → `script` → `scene_plan` → `assets` → `edit` → `compose`.
- **Cấm coi TaskCreate, TaskUpdate hoặc trạng thái nội bộ của agent là checkpoint.** Checkpoint hợp lệ duy nhất là file JSON được ghi vào disk bởi `lib.checkpoint.write_checkpoint()`.
- **Cấm coi artifact đã tạo đồng nghĩa với việc user đã duyệt stage.** Artifact chỉ là bản nháp đầu ra kỹ thuật của stage, chưa có giá trị phê duyệt cho tới khi user xác nhận.

---

## 3. Human Approval & Gate Protocol

- **Lựa chọn tùy chọn ban đầu** (chọn lớp toán, `solutionMode`, visual concept, hay render runtime) **chỉ là user preference, KHÔNG PHẢI stage approval.**
- **Với mọi stage có `human_approval_default: true` trong pipeline manifest:**
  1. Ghi checkpoint `status="awaiting_human"` bằng `lib.checkpoint.write_checkpoint()`.
  2. Trình bày tóm tắt artifact và review summary cho người dùng.
  3. Hỏi rõ ràng người dùng có duyệt để chuyển sang stage tiếp theo hay không.
  4. **KẾT THÚC LƯỢT NGAY (END YOUR TURN).** Cấm gọi thêm bất kỳ tool downstream nào trong cùng response.
  5. **Chỉ tiếp tục sau câu trả lời trực tiếp của người dùng.**
- **TUYỆT ĐỐI KHÔNG tự đặt `human_approved=True`.** Chỉ được truyền `human_approved=True` vào `write_checkpoint()` sau khi người dùng đã phản hồi đồng ý rõ ràng ở lượt trước.
- **Không được suy ra approval** từ việc người dùng đã chọn option hoặc đã yêu cầu tạo video ở các lượt trước. Approval có tính chất per-gate (từng cổng riêng biệt).
- **Không gọi downstream tool trong cùng lượt sau khi ghi `awaiting_human`.**
- **Nếu không chắc chắn approval có thật hay không, bắt buộc giữ trạng thái `awaiting_human` hoặc `pending`.**

---

## 4. Checkpoint Integrity & Error Handling

- **Luôn dùng `lib.checkpoint.write_checkpoint()`** để ghi nhận trạng thái.
- **TUYỆT ĐỐI KHÔNG dùng `json.dump`, `Write`, `Set-Content` hoặc bất kỳ file tool nào** để tự tạo hoặc sửa đổi file `checkpoint_*.json`.
- **Không được đánh dấu stage là `completed` nếu predecessor còn thiếu hoặc chưa được duyệt.**
- **Khi gặp `GATE VIOLATION`, `PREREQUISITE VIOLATION` hoặc schema error:**
  - DỪNG NGAY LẬP TỨC.
  - Báo rõ nguyên nhân lỗi cho người dùng.
  - KHÔNG tự tiện thêm `human_approved=True` để lách luật.
  - KHÔNG tiếp tục render hoặc tạo media.
- *Lưu ý cơ chế kiểm soát:* Python code chỉ kiểm tra giá trị boolean của tham số `human_approved`, không tự xác minh được nguồn gốc (provenance) của approval. Do đó, việc không tự đặt `human_approved=True` là cam kết kỷ luật bắt buộc của agent.

---

## 5. TTS Routing (Tiếng Việt & Tiếng Anh)

- **Với tiếng Việt:**
  - Bắt buộc kiểm tra và thử skill `vieneu-tts` (VieNeu-TTS local) trước.
  - Chỉ dùng API Vbee tiếng Việt khi VieNeu thật sự không khả dụng vì thiếu package, model hoặc runtime failure.
  - **Cấm gọi `VbeeTTS()` trực tiếp cho tiếng Việt nếu chưa kiểm tra VieNeu.**
  - Không tuyên bố VieNeu đã được thử nếu chưa có log/tool output thực tế chứng minh.
  - Khi phải fallback sang Vbee, bắt buộc ghi rõ vào artifact (`asset_manifest.json`, `render_report.json`):
    - Provider thực tế (`vbee`).
    - Lý do fallback (`fallback_reason`).
    - Lỗi cụ thể hoặc điều kiện khiến VieNeu không dùng được.
- **Với tiếng Anh (đọc đề toán):**
  - Luôn dùng API Vbee (`VBEE_VOICE_CODE_EN`, mặc định `am_echo`) với tốc độ `0.85x`, áp gain `1.20` khi mix âm thanh theo math rules hiện hành.

---

## 6. Generation Timing & Media Creation Gate

- **Tuyệt đối không tạo audio, image, video hoặc render trước approval tương ứng.**
  - Stage `scene_plan` phải được duyệt trước khi gọi tool tạo media ở stage `assets`.
  - Stage `assets` (storyboard / filmstrip) phải được duyệt trước khi gọi render video ở stage `compose`. Không render video draft/full ở stage `assets` để thay thế storyboard.
- **Nếu lỡ gọi tool trước approval:** Phải dừng ngay lập tức, báo cáo vi phạm gate cho người dùng và không tiếp tục âm thầm.
- **Lưu ý:** Checkpoint không tự động ngăn chặn việc gọi tool phát sinh trước đó trong code Python; đây là ràng buộc quy trình nghiêm ngặt mà agent phải tự giác tuân thủ.
