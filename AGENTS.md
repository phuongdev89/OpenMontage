# OpenMontage - Core Agent Governance & Instructions

> **MANDATORY CONTRACT**: These governance rules are directly injected into runtime prompt context. They are strictly binding on every agent interaction in OpenMontage.
> Detailed guide: [`AGENT_GUIDE.md`](AGENT_GUIDE.md) | Architecture: [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md)

---

## 1. Mandatory Startup Checklist

### First question before production work

Ngay khi nhận task sản xuất video MỚI, câu hỏi đầu tiên chỉ gồm:
1. **Duyệt thủ công toàn bộ (khuyến nghị)**
2. **Duyệt mỗi concept, còn đâu tự động hoàn toàn**
3. **Tự động hoàn toàn**

Chờ câu trả lời trực tiếp trước onboarding, hỏi lớp/solutionMode/concept/runtime,
research, preflight, init, tạo artifact hoặc gọi provider. Không coi option chọn
sẵn là câu trả lời. Sau lựa chọn mới thực hiện checklist dưới đây. Đọc
`skills/meta/approval-mode.md`; dùng `set_approval_mode()` sau init để lưu mode
và nguyên văn lựa chọn cho project. Resume dùng mode đã lưu, không hỏi lại hoặc
kế thừa quyền project khác. Sửa code/quy tắc không tự bật mode cho project đang có.

`manual_all` chờ duyệt mọi stage, kể cả manifest mặc định không gated.
`concept_only` chỉ chờ chọn/duyệt concept từ catalog đầy đủ; ghi bằng
`record_concept_approval()` rồi tự động mọi bước khác. Concept thay đổi phải duyệt
lại. `full_auto` tự chọn concept phù hợp và tự chạy cả publish. Các mode tự động
ưu tiên hơn quy tắc hỏi preference ban đầu/chờ duyệt stage; review, schema,
checkpoint, chất lượng và ràng buộc cụ thể của user vẫn bắt buộc.

Every production task MUST execute this sequence before calling any generation tools or creating media:

1. **Đọc AGENT_GUIDE.md**: Nắm rõ operating contract và decision protocols.
2. **Đọc pipeline manifest**: Đọc `pipeline_defs/<pipeline>.yaml` tương ứng.
3. **Xác định stage hiện tại**: Dùng `lib.checkpoint.get_next_stage()`.
4. **Đọc stage director skill**: Đọc `skills/pipelines/<pipeline>/<stage>-director.md`.
5. **Kiểm tra checkpoint predecessor**: Xác nhận stage trước đã `completed` và có human approval hoặc auto-authorization hợp lệ (nếu có gate).
6. **Kiểm tra stage có gated không**: Đọc `human_approval_default` từ pipeline manifest.
7. **Kiểm tra approval evidence từ tin nhắn người dùng**: Xác minh duyệt từng gate hoặc ủy quyền tự động duyệt tường minh cho project hiện tại.
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
- Lựa chọn mode ở câu hỏi đầu tiên là chỉ thị duyệt của project. Concept_only lưu bằng chứng chọn/duyệt concept riêng; không biến nó thành human approval của mọi stage. Xem `skills/meta/approval-mode.md`.
- Khi người dùng nói rõ **“cho phép tự động duyệt”** cho project hiện tại, gọi `lib.checkpoint.authorize_auto_approval()` sau `init_project()` và trước khi tiếp tục pipeline, lưu nguyên văn chỉ thị. Quyền này áp dụng cho mọi gate còn lại của đúng project đó, kể cả sau khi resume; không áp dụng cho project khác. Người dùng có thể thu hồi bằng `revoke_auto_approval()`.
- Auto-authorization cho phép tiếp tục qua gate mà không hỏi lại, nhưng **không phải human approval**: checkpoint gated vẫn ghi `human_approval_required: true`, `human_approved: false` và `approval_resolution.type: "auto_authorized"` cùng chỉ thị nguồn. Không tự đổi `human_approved` thành `true`.
- Ngoại lệ này ưu tiên hơn chỉ dẫn chờ duyệt trong stage director, sample review và checklist; review, schema validation, thứ tự stage, checkpoint và các ràng buộc cụ thể của người dùng vẫn bắt buộc. Bao gồm gate `publish` trong phạm vi task đã được yêu cầu. Nếu stage đang `awaiting_human`, review rồi ghi lại `completed` qua writer trước khi chạy downstream. Không bật chế độ cho project khi người dùng chỉ đang yêu cầu sửa quy tắc này.
- **Khi mode manual_all, hoặc stage cần duyệt theo manifest/project mà chưa có auto-authorization hợp lệ cho stage đó:**
  1. Ghi checkpoint `status="awaiting_human"` bằng `lib.checkpoint.write_checkpoint()`.
  2. Trình bày tóm tắt artifact và review summary cho người dùng.
  3. Hỏi rõ ràng người dùng có duyệt để chuyển sang stage tiếp theo hay không.
  4. **KẾT THÚC LƯỢT NGAY (END YOUR TURN).** Cấm gọi thêm bất kỳ tool downstream nào trong cùng response.
  5. **Chỉ tiếp tục sau câu trả lời trực tiếp của người dùng, trừ khi project có auto-authorization hợp lệ đã ghi nhận.**
- **TUYỆT ĐỐI KHÔNG tự đặt `human_approved=True`.** Chỉ được truyền `human_approved=True` vào `write_checkpoint()` sau khi người dùng đã phản hồi đồng ý rõ ràng ở lượt trước.
- **Không được suy ra approval** từ việc người dùng đã chọn option hoặc đã yêu cầu tạo video ở các lượt trước. Approval có tính chất per-gate (từng cổng riêng biệt).
- **Không gọi downstream tool trong cùng lượt sau khi ghi `awaiting_human`.**
- **Nếu không chắc chắn approval có thật hay không, bắt buộc giữ trạng thái `awaiting_human` hoặc `pending`.**

---

## 4. Checkpoint Integrity & Error Handling

- **Luôn dùng `lib.checkpoint.write_checkpoint()`** để ghi nhận trạng thái.
- **TUYỆT ĐỐI KHÔNG dùng `json.dump`, `Write`, `Set-Content` hoặc bất kỳ file tool nào** để tự tạo hoặc sửa đổi file `checkpoint_*.json`.
- **Không được đánh dấu stage là `completed` nếu predecessor còn thiếu hoặc chưa được duyệt/ủy quyền tự động hợp lệ.**
- **Khi gặp `GATE VIOLATION`, `PREREQUISITE VIOLATION` hoặc schema error:**
  - DỪNG NGAY LẬP TỨC.
  - Báo rõ nguyên nhân lỗi cho người dùng.
  - KHÔNG tự tiện thêm `human_approved=True` để lách luật.
  - KHÔNG tiếp tục render hoặc tạo media.
- *Lưu ý cơ chế kiểm soát:* Python code xác minh human approval boolean và auto-authorization được ghi trong project marker; agent không tự đặt `human_approved=True` khi chạy theo auto-authorization.
- *Lưu ý phạm vi enforcement:* Gate và prerequisite chỉ có hiệu lực khi `pipeline_type` resolve được từ manifest thật. `write_checkpoint()` tự backfill `pipeline_type`/`style_playbook` từ marker `project.json`, nên project đã `init_project()` không thể bypass bằng cách bỏ tham số; nhưng nếu project chưa init và caller bỏ `pipeline_type`, gate lẫn prerequisite bị bỏ qua âm thầm (fail-open). Chỉ chạy production trên project đã `init_project()` với `pipeline_type` là tên manifest thật.

---

## 5. TTS Routing (Tiếng Việt & Tiếng Anh)

- **Lời thoại:** Không tự xưng thầy/cô hoặc vai trò người dẫn; loại bỏ toàn bộ ngôi thứ nhất số ít và số nhiều trong lời thoại do agent viết. Dùng cách nói trực tiếp với người xem hoặc câu trung tính/mệnh lệnh như "hãy cùng..."; giữ nguyên nội dung nguồn bắt buộc đọc/trích nguyên văn. Chi tiết áp dụng tại `AGENT_GUIDE.md` và skill lời thoại theo pipeline.
- **Tốc độ lời đọc VI và EN:** Cố định tốc độ hiệu dụng ở `0.90×` so với tốc độ native `1.0×` của provider cho cả tiếng Việt và tiếng Anh. Không nhân với tốc độ cũ và không áp thêm mức giảm 10%. Với Vbee truyền rõ `speed_rate=0.90`; nếu adapter dùng `speed` thì truyền `speed=0.90`. Với VieNeu không hỗ trợ speed, tạo audio native rồi áp time-stretch giữ cao độ `atempo=0.90` đúng một lần. Audio đã ở `0.90×` phải giữ nguyên tốc độ khi compose/mix; không time-stretch lần nữa. Ghi `baseline_speed=1.0`, `target_speed=0.90`, `effective_speed=0.90` và filter thực tế trong `voice_performance.provider_settings`; nếu tái sử dụng audio phải kiểm tra metadata, không mặc định coi là native. Điều chỉnh thời lượng cảnh theo audio.
- **Publish video toán:** Đọc `skills/pipelines/shared/output-formats.md`; `.env` chọn tỷ lệ cho project mới, `project.json.output_video_formats` giữ lựa chọn khi resume. `exports/video/` chỉ bắt buộc mọi bản được bật: ngang 1920×1080, dọc 1080×1920; rà thumbnail cuối để đảm bảo không có đáp án hoặc phép giải đã hoàn tất. Theo `skills/pipelines/explainer/publish-director.md`.
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
  - Luôn dùng API Vbee (`VBEE_VOICE_CODE_EN`, mặc định `am_echo`) với tốc độ `0.90x`, áp gain `1.20` khi mix âm thanh theo math rules hiện hành.

---

## 6. Generation Timing & Media Creation Gate

- **Tuyệt đối không tạo audio, image, video hoặc render trước approval tương ứng hoặc auto-authorization hợp lệ của project.**
  - Stage `scene_plan` phải được duyệt trước khi gọi tool tạo media ở stage `assets`.
  - Stage `assets` (storyboard / filmstrip) phải được duyệt trước khi gọi render video ở stage `compose`. Không render video draft/full ở stage `assets` để thay thế storyboard.
- **Nếu lỡ gọi tool trước approval/auto-authorization:** Phải dừng ngay lập tức, báo cáo vi phạm gate cho người dùng và không tiếp tục âm thầm.
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
7. **Stage gated** (`human_approval_default: true`): nếu project có auto-authorization hợp lệ, tiếp tục và ghi `approval_resolution`; nếu không, ghi `awaiting_human`, hỏi user, KẾT THÚC LƯỢT.
8. **Không tự đặt `human_approved=True`** — chỉ truyền `True` sau câu trả lời duyệt tường minh của user cho gate đó ở lượt trước. Auto-authorization phải giữ `human_approved=False`.
9. **TaskCreate/TaskUpdate/todo list của ZCode không phải checkpoint** — xem section 2.
10. **Không ghi `checkpoint_*.json` bằng Write/json.dump hay file tool nào** — chỉ qua `lib.checkpoint.write_checkpoint()`.
11. **Tiếng Việt: thử VieNeu trước Vbee** theo đúng quy trình trong skill `vieneu-tts` (`import vieneu` → cài nếu thiếu → chạy `generate_voice.py`), giữ log/output làm bằng chứng; không tuyên bố đã thử nếu không có log.
12. **Fallback Vbee phải ghi `provider` thực tế + `fallback_reason`** vào `asset_manifest` và `render_report` (lưu ý: schema không bắt buộc các trường này — nghĩa kỷ luật, xem section 5).
13. **Điều kiện chưa xác minh → không gọi generation tool.** Ví dụ: package `vieneu` đã cài nhưng chưa từng infer thành công ⇒ coi là UNVERIFIED khi cân nhắc fallback.
14. **Phát hiện artifact/media do agent khác tạo trước checkpoint hợp lệ:** báo trạng thái lệch governance cho user, không tự sửa hay xóa dữ liệu cũ.

---

## 8. Visual Style Contract

### Toán Olympic Cùng Con channel branding

- Đọc `skills/pipelines/shared/channel-branding.md` trước assets/compose cho video kênh này. Logo gốc tại `branding/toan-olympic-cung-con/logo.png`; không thay bằng chữ hoặc vẽ lại.
- Watermark cố định ở góc trên trái suốt video, không đổi góc. Khoảng cách từ bounding box logo tới mỗi cạnh kề không vượt 5% của chiều khung tương ứng (mặc định 2%). Chỉ logo watermark thỉnh thoảng xoay quanh trục dọc; logo credit không xoay. Lưu lịch xoay theo đúng project để render lại nhất quán.

### Full concept selection

- Trước khi hỏi concept/style, đọc `skills/meta/concept-selection.md` và kiểm tra catalog hiện có. Hiển thị TOÀN BỘ concept có sẵn với tên dễ hiểu và mô tả ngắn trong danh sách chọn.
- Không rút còn 2–3 concept được đề xuất rồi buộc người dùng tự nhập các concept còn lại. Có thể đánh dấu mục khuyên dùng nhưng phải giữ đủ tất cả lựa chọn. Concept tùy chỉnh chỉ là bổ sung.
- Video toán hiện có Bản tin Thời sự, Thám Tử, Neon Lab, Bảng Phấn, Vở Ô Ly, Đồ Vật Trực Quan. Đối chiếu reference và `styles/math-*.yaml` để bổ sung concept mới; không đóng cứng số lượng.
- Codex dùng `request_user_input_async` với đầy đủ options. Nếu host giới hạn option, hiện toàn bộ danh sách theo nhóm/đánh số; người dùng chỉ cần chọn mục đã hiển thị, không cần đọc code hoặc tự đoán tên. Không suy ra câu trả lời từ option được chọn sẵn.

### Concurrent project isolation

- Bind each run to the exact absolute directory returned by `init_project()` and its `project.json`; do not select the newest project, first glob match, process cwd or another chat's project variable.
- Every project's source, props, public media, concat list, narration and output must live under that project. Never overwrite shared `remotion-composer/src/Root.tsx`, generic components, `public/master_narration.mp3`, `.scratch/generate_audio.py` or a common props JSON during production. Reusable engine code is read-only for production.
- Remotion atelier requires explicit `bespoke.public_dir` under the current project and `--public-dir` on every render. Use project-local source and a render-specific snapshot/props path. Never silently fall back to the shared composer public directory when a directory is missing.
- Before compose, resolve every narration path against the current project, verify file hash, script/scene identity, duration and speed metadata. Record project directory, source path and SHA-256 in the asset manifest/render report. Compare the rendered audio with that project's approved narration, including EN/VI readings; stream presence and volume alone are not sufficient.
- Keep conversation ID/source bound to the current chat; do not borrow an ID from another checkpoint or pick the newest global conversation when runs overlap. Validate the exported transcript actually contains the current project/source problem before copying it to exports.
- Read `skills/pipelines/shared/project-isolation.md` before assets and compose, and `skills/pipelines/shared/posting-package.md` before publish. Complete the posting package (title, YouTube description, distinct Facebook/TikTok caption, concept-led generated thumbnail and every enabled video variant) before publish completion. Dedicated thumbnail creation uses the installed `image-generate` skill: built-in first, configured API fallback with evidence; never extract a frame from the video.

- `styles/<style_playbook>.yaml` là authority cho ngôn ngữ hình ảnh tổng thể: nền, palette, typography, hình khối, texture, shadow và motion. Storyboard đã duyệt triển khai các nguyên tắc đó theo từng cảnh; storyboard không tự động cho phép đổi playbook.
- Trước render, đối chiếu composition source với cả playbook và storyboard đã duyệt. Kiểm tra mọi CSS rule, inline style, SVG fill/stroke, component theme và preset; không chỉ kiểm tra màu nền hoặc một frame.
- Không tự thêm theme, font, màu nhấn hay hiệu ứng trái playbook dựa trên tên project, gu cá nhân, template/runtime mặc định hoặc artifact cũ. Chỉ dùng biến thể khi storyboard đã duyệt mô tả rõ và biến thể vẫn nằm trong giới hạn của playbook.
- Xác minh tương phản chữ/nền và giới hạn số màu theo `quality_rules` của playbook; bảo đảm các tỷ lệ được bật dùng cùng visual language.
- Nếu phát hiện lệch, sửa composition source trước khi render. Nếu cần thay đổi vượt quá playbook hoặc storyboard đã duyệt, dừng ở source draft và xin duyệt lại storyboard; không tự render để thử.
- Sau render, kiểm tra frame đại diện ở các cảnh và mọi tỷ lệ khung hình được bật để xác nhận output thực sự giữ đúng style. Source-only edits không cập nhật MP4 đã publish; chỉ render lại khi người dùng yêu cầu hoặc pipeline đang ở compose với approval còn hiệu lực.

### Portrait-first layout rules

- Portrait và landscape phải có composition riêng theo từng tỷ lệ; không thu nhỏ một layout ngang để nhét vào khung dọc.
- Landscape 16:9 (1920×1080) phục vụ xem trên PC, TV và tablet; portrait 9:16 (1080×1920) phục vụ Facebook/TikTok trên điện thoại. Đánh giá độ đọc theo thiết bị đích, không chỉ theo độ phân giải file.
- Với portrait 1080×1920, thiết kế nội dung quan trọng trong safe area tối thiểu 72 px bên trái, 144 px bên phải, 120 px phía trên và 280 px phía dưới để tránh nút tương tác/caption của ứng dụng. Đây là baseline nội bộ bảo thủ, không phải cam kết UI cố định của nền tảng; preview với overlay ứng dụng đích trước bàn giao. Không dành vùng cố định cho footer minh họa nếu nó làm giảm kích thước sơ đồ hoặc chữ.
- Dùng vùng trung tâm cho một ý toán học mỗi cảnh: vật mẫu/sơ đồ là trọng tâm; tiêu đề và chú thích hỗ trợ. Chỉ giữ các dữ kiện cần thiết cho lời đọc hiện tại, không lặp lại cùng nội dung trong nhiều bảng.
- Kiểm tra ở viewport tương đương 360×640: chữ thân bài raster không nhỏ hơn 16 px, phép tính và nhãn sơ đồ không nhỏ hơn 18 px; câu dài phải chia cảnh hoặc phân cấp rõ, không thu nhỏ để vừa.
- Các phép biến đổi phải được thể hiện theo trạng thái: nêu rõ trạng thái ban đầu, thao tác đang diễn ra và kết quả đã hoàn tất. Không đưa đáp án lên hook, footer hoặc hình nền trước cảnh đáp án được duyệt.
- Với bài toán nhiều bước, tiết lộ từng thao tác theo timeline lời đọc; giữ tổng kết kiểm tra khớp với dữ kiện ban đầu và phân biệt rõ tổng trung gian đã biến đổi với tổng ban đầu.

### Hook-first acceptance gate

- Câu được đọc đầu tiên phải nêu manh mối/mâu thuẫn hoặc thử thách cụ thể theo concept; cấm mở bằng "Chào", "Xin chào", lời giới thiệu lớp/kỳ thi hoặc "Hôm nay...". SFX mở đầu không thay thế hook trong lời đọc.
- Trong 3–5 giây đầu, hình và lời đọc phải cùng tạo tò mò từ dữ kiện đúng của bài toán. Lời chào, nếu có, xuất hiện sau dữ kiện hook; không bắt buộc có lời chào.
- Hook phải có câu hỏi/thách thức cụ thể, không lộ đáp án; tạo kịch tính bằng concept, không bịa dữ kiện hay phóng đại sai toán học.
- Review script phải trích nguyên câu đầu và ghi PASS/FAIL cho hook-first. FAIL thì sửa trước TTS, kể cả chế độ tự động duyệt.

## Vietnamese typography and text containment gate

- Dùng font hỗ trợ đầy đủ dấu tiếng Việt ở đúng weight/style; kiểm tra chuỗi có ă â ê ô ơ ư đ và dấu kép. Nạp font local hoặc font đã xác minh, không dựa vào fallback trên máy preview.
- Trước capture/render phải chờ font tải xong (`document.fonts.ready` với HTML/browser). Xác minh font thực tế và ảnh raster tiếng Việt; chỉ khai báo font-family không đủ bằng chứng.
- Kiểm tra mọi text container ở mọi tỷ lệ được bật (portrait/landscape), gồm tiêu đề, đề bài, labels, phụ đề và CTA. Với HTML kiểm tra scrollWidth/clientWidth và scrollHeight/clientHeight, sau đó kiểm tra ảnh thật để bắt dấu bị cắt hoặc glyph lỗi; runtime khác dùng kiểm tra bounding box tương đương.
- Chữ và dấu phải nằm trong border với padding an toàn. Sửa bằng wrap, chia trang, tăng vùng chữ hoặc giảm cỡ chữ trong giới hạn dễ đọc của playbook. Cấm dùng overflow:hidden/ellipsis để che mất nội dung hay bóp chữ méo.
- Ghi bằng chứng font, frame/ảnh review, tỷ lệ khung hình và kết quả containment vào review/render_report. Font lỗi hoặc chữ tràn = critical: sửa source trước render; auto-approval không bỏ qua kiểm tra này.

### Conversation export completion evidence

- Sau mỗi lần export thành công (sau compose và sau publish), bắt buộc copy cả Markdown và JSON từ session directory của skill vào `<project_dir>/exports/conversation/`. Giữ nguyên tên hai tệp và ghi đè đúng hai bản đã copy khi export lại sau publish; không tạo thêm bản timestamp mới. Chỉ báo hoàn tất export sau khi xác minh hai bản trong project tồn tại, không rỗng và khớp nội dung với nguồn (hash hoặc so sánh bytes). Ghi đường dẫn bản trong project cùng đường dẫn nguồn vào metadata checkpoint tương ứng và dẫn link bản trong project khi bàn giao. Copy thất bại phải báo rõ; không coi chỉ có bản trong `.scratch` là hoàn tất bước bàn giao.

- Sau checkpoint compose completed, bắt buộc thực thi skill `export-conversation` trước khi kết thúc lượt hoặc tiến tới publish, kể cả chế độ tự động duyệt. Đây là nghĩa vụ agent, không phải một bước cần hỏi người dùng.
- Không coi lệnh export được dự định hoặc đoạn transcript viết tay là đã xuất. Xác nhận exit code thành công, hai tệp Markdown/JSON tồn tại, đúng conversation ID/source và có nội dung transcript thật.
- Ghi conversation ID, source agent, output base path tuyệt đối, đường dẫn hai tệp và thời điểm export vào metadata checkpoint compose qua `write_checkpoint()`; giữ nguyên artifact và trạng thái approval khi bổ sung metadata. Dẫn link hai tệp khi báo hoàn tất.
- Sau publish completed, chạy lại export cùng ID/base path để ghi đè, xác minh lại và ghi bằng chứng vào metadata checkpoint publish. Auto-approval cũng phải thực hiện bước này.
- Nếu export thất bại hoặc không xác định được nguồn transcript: báo lỗi cụ thể, ghi pending/failed export trong metadata và không tuyên bố đã bàn giao đầy đủ; không tự tạo transcript thay thế.
