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
- **Tuân thủ thứ tự stage tuần tự:** `research` → `proposal`/`idea` → `script` → `scene_plan` → `assets` → `edit` → `compose` → `publish`. (Thứ tự và tên stage thật lấy từ manifest đã chọn — `pipeline_defs/*.yaml` là authority; `publish` là stage cuối và có gate ở `animation`/`animated-explainer`.)
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
- *Lưu ý phạm vi enforcement:* Gate và prerequisite chỉ có hiệu lực khi `pipeline_type` resolve được từ manifest thật. `write_checkpoint()` tự backfill `pipeline_type`/`style_playbook` từ marker `project.json`, nên project đã `init_project()` không thể bypass bằng cách bỏ tham số; nhưng nếu project chưa init và caller bỏ `pipeline_type`, gate lẫn prerequisite bị bỏ qua âm thầm (fail-open). Chỉ chạy production trên project đã `init_project()` với `pipeline_type` là tên manifest thật.

---

## 5. TTS Routing (Tiếng Việt & Tiếng Anh)

- **Lời thoại:** Không tự xưng thầy/cô hoặc vai trò người dẫn; loại bỏ toàn bộ ngôi thứ nhất số ít và số nhiều trong lời thoại do agent viết. Dùng cách nói trực tiếp với người xem hoặc câu trung tính/mệnh lệnh như "hãy cùng..."; giữ nguyên nội dung nguồn bắt buộc đọc/trích nguyên văn. Chi tiết áp dụng tại `AGENT_GUIDE.md` và skill lời thoại theo pipeline.
- **Với tiếng Việt:**
  - Bắt buộc kiểm tra và thử skill `vieneu-tts` (VieNeu-TTS local) trước.
  - Chỉ dùng API Vbee tiếng Việt khi VieNeu thật sự không khả dụng vì thiếu package, model hoặc runtime failure.
  - **Cấm gọi `VbeeTTS()` trực tiếp cho tiếng Việt nếu chưa kiểm tra VieNeu.**
  - Không tuyên bố VieNeu đã được thử nếu chưa có log/tool output thực tế chứng minh.
  - Khi phải fallback sang Vbee, bắt buộc ghi rõ vào artifact (`asset_manifest.json`, `render_report.json`):
    - Provider thực tế (`vbee`).
    - Lý do fallback (`fallback_reason`).
    - Lỗi cụ thể hoặc điều kiện khiến VieNeu không dùng được.

### VieNeu voice default

Khi sử dụng VieNeu-TTS cho tiếng Việt:

1. Giọng mặc định bắt buộc là `Minh Quân`.
2. Luôn truyền rõ tham số `voice="Minh Quân"`.
3. Không được dùng `Anh Khôi`, `Đoan Trang` hoặc giọng khác nếu người dùng chưa yêu cầu rõ.
4. Không được suy ra giọng từ tên project, artifact cũ, biến môi trường hoặc giá trị mặc định của package.
5. Trước khi tạo audio, phải ghi nhận:
   - `provider: vieneu`
   - `voice: Minh Quân`
   - `voice_source: AGENTS.md`
6. Sau khi tạo audio, phải kiểm tra metadata/audio manifest xác nhận đúng `Minh Quân`.
7. Nếu VieNeu không hỗ trợ hoặc không xác định được preset `Minh Quân`, phải dừng và báo lỗi; không tự đổi sang giọng khác.

- **Với tiếng Anh (đọc đề toán):**
  - Luôn dùng API Vbee (`VBEE_VOICE_CODE_EN`, mặc định `am_echo`) với tốc độ `0.85x`, áp gain `1.20` khi mix âm thanh theo math rules hiện hành.

---

## 6. Generation Timing & Media Creation Gate

- **Tuyệt đối không tạo audio, image, video hoặc render trước approval tương ứng.**
  - Stage `scene_plan` phải được duyệt trước khi gọi tool tạo media ở stage `assets`.
  - Stage `assets` (storyboard / filmstrip) phải được duyệt trước khi gọi render video ở stage `compose`. Không render video draft/full ở stage `assets` để thay thế storyboard.
- **Nếu lỡ gọi tool trước approval:** Phải dừng ngay lập tức, báo cáo vi phạm gate cho người dùng và không tiếp tục âm thầm.
- **Lưu ý:** Checkpoint không tự động ngăn chặn việc gọi tool phát sinh trước đó trong code Python; đây là ràng buộc quy trình nghiêm ngặt mà agent phải tự giác tuân thủ.

### Xuất hội thoại sau compose và publish

- Sau khi stage `compose` hoàn tất thành công và checkpoint đã ghi `completed`, bắt buộc dùng skill `export-conversation` xuất hội thoại hiện tại ở cả Markdown và JSON (`-f all`) vào session directory của skill.
- Ghi nhớ conversation ID và đúng output base path của hai tệp. Sau khi người dùng cho phép publish và stage `publish` hoàn tất thành công, chạy lại skill cho cùng conversation ID và cùng base path để ghi đè hai tệp cũ bằng hội thoại đã cập nhật. Truyền đường dẫn base file, không chỉ truyền thư mục, vì truyền thư mục sẽ tạo tên tệp timestamp mới.
- Tuân thủ source selection và output rules của skill; không tự chép hoặc dựng lại transcript.

---

## 7. ZCode Runtime Contract

> **Phạm vi áp dụng:** Section này chỉ ràng buộc agent ZCode (runtime: ZCode CLI/desktop). Không thay đổi nghĩa vụ của Antigravity (section 1–6, `GEMINI.md`) hay Claude Code (`CLAUDE.md`). Nguồn xác minh: audit ngày 2026-10-11 — context injection thực tế của ZCode host, `lib/checkpoint.py`, `pipeline_defs/animation.yaml`, `pipeline_defs/animated-explainer.yaml`.

1. **Auto-inject:** ZCode host tự nạp `AGENTS.md` vào context (đã xác minh bằng injection thực tế). Mọi file khác — kể cả `AGENT_GUIDE.md` — KHÔNG được nạp tự động; markdown pointer không tạo ra auto-load.
2. **Đọc `AGENT_GUIDE.md` trọn vẹn trước mọi production task** bằng công cụ đọc file, không dựa vào ký ức phiên trước.
3. **Đọc pipeline manifest thật** (`pipeline_defs/<pipeline>.yaml`) trước khi chạy stage nào. `pipeline_defs/math.yaml` KHÔNG tồn tại — không tham chiếu nó.
4. **Video toán chạy trên pipeline thật có manifest** — ví dụ `animation` hoặc `animated-explainer` (cả hai khai báo `math_animate` ở stage `assets`); `pipeline_type` truyền vào checkpoint phải là tên manifest thật, nếu không `_stage_requires_approval` raise.
5. **Đọc stage director skill** (`skills/pipelines/<pipeline>/<stage>-director.md`) trước từng stage.
6. **Preference không phải stage approval** — xem section 3.
7. **Stage gated** (`human_approval_default: true`): ghi `awaiting_human` qua `write_checkpoint()`, hỏi user, KẾT THÚC LƯỢT.
8. **Không tự đặt `human_approved=True`** — chỉ truyền `True` sau câu trả lời duyệt tường minh của user cho gate đó ở lượt trước.
9. **TaskCreate/TaskUpdate/todo list của ZCode không phải checkpoint** — xem section 2.
10. **Không ghi `checkpoint_*.json` bằng Write/json.dump hay file tool nào** — chỉ qua `lib.checkpoint.write_checkpoint()`.
11. **Tiếng Việt: thử VieNeu trước Vbee** theo đúng quy trình trong skill `vieneu-tts` (`import vieneu` → cài nếu thiếu → chạy `generate_voice.py`), giữ log/output làm bằng chứng; không tuyên bố đã thử nếu không có log.
12. **Fallback Vbee phải ghi `provider` thực tế + `fallback_reason`** vào `asset_manifest` và `render_report` (lưu ý: schema không bắt buộc các trường này — nghĩa kỷ luật, xem section 5).
13. **Điều kiện chưa xác minh → không gọi generation tool.** Ví dụ: package `vieneu` đã cài nhưng chưa từng infer thành công ⇒ coi là UNVERIFIED khi cân nhắc fallback.
14. **Phát hiện artifact/media do agent khác tạo trước checkpoint hợp lệ:** báo trạng thái lệch governance cho user, không tự sửa hay xóa dữ liệu cũ.

---

## 8. Visual Style Contract

- `styles/<style_playbook>.yaml` là authority cho ngôn ngữ hình ảnh tổng thể: nền, palette, typography, hình khối, texture, shadow và motion. Storyboard đã duyệt triển khai các nguyên tắc đó theo từng cảnh; storyboard không tự động cho phép đổi playbook.
- Trước render, đối chiếu composition source với cả playbook và storyboard đã duyệt. Kiểm tra mọi CSS rule, inline style, SVG fill/stroke, component theme và preset; không chỉ kiểm tra màu nền hoặc một frame.
- Không tự thêm theme, font, màu nhấn hay hiệu ứng trái playbook dựa trên tên project, gu cá nhân, template/runtime mặc định hoặc artifact cũ. Chỉ dùng biến thể khi storyboard đã duyệt mô tả rõ và biến thể vẫn nằm trong giới hạn của playbook.
- Xác minh tương phản chữ/nền và giới hạn số màu theo `quality_rules` của playbook; bảo đảm hai tỷ lệ khung hình dùng cùng visual language.
- Nếu phát hiện lệch, sửa composition source trước khi render. Nếu cần thay đổi vượt quá playbook hoặc storyboard đã duyệt, dừng ở source draft và xin duyệt lại storyboard; không tự render để thử.
- Sau render, kiểm tra frame đại diện ở các cảnh và cả hai tỷ lệ khung hình để xác nhận output thực sự giữ đúng style. Source-only edits không cập nhật MP4 đã publish; chỉ render lại khi người dùng yêu cầu hoặc pipeline đang ở compose với approval còn hiệu lực.
