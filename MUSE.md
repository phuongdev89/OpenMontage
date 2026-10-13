# OpenMontage — Kênh "Toán Olympic Cùng Con"
_Người soạn: 1 Muse đáng yêu · Ngày: 2026-10-13 · Người nhận: Muse mới

Đọc file này từ đầu đến cuối trước khi làm bất kỳ việc gì. Mọi bài học trong mục 4 đều là xương máu thật, không được lặp lại.

## 1. Bối cảnh

- Kênh YouTube dạy toán tiểu học **"Toán Olympic Cùng Con"**.
- Sản xuất video giải toán bằng hệ thống **OpenMontage** tại `~/workspace/openmontage` (nhánh `feat/math-video`).
- Đối tượng: học sinh cấp tiểu học + phụ huynh. Giọng đọc: nam, ấm, không xưng thầy/cô, không dùng ngôi thứ nhất.
- Các video trước đã làm theo pipeline `animated-explainer` + playbook `math-manipulatives` —
  đây chỉ là lựa chọn đã dùng, **không phải quy định cố định** (xem mục 5).

## 2. Checkout và cài đặt project

```bash
# 1. Clone từ fork, đúng nhánh đang dùng
git clone https://github.com/phuongdev89/openmontage
cd openmontage
git checkout feat/math-video

# 2. Cài đặt chuẩn của repo (venv + requirements + remotion + piper + hyperframes)
make setup

# 3. Tạo venv riêng cho Manim + VieNeu TTS (venv chuẩn của repo thiếu 2 thứ này)
python3 -m venv .venv-manim
.venv-manim/bin/pip install manim==0.22.0 vieneu==3.8.3 pillow numpy scipy soundfile
# PIN bản này — bản 2.x crash khi parse proxy (lỗi httpx2 "Invalid port")
.venv-manim/bin/pip install "huggingface_hub==0.34.0"
```

- **FFmpeg** phải có sẵn (`ffmpeg -version`).
- **Font:** Noto Sans đầy đủ (Regular/Bold) tại `/usr/share/fonts/truetype/noto/` — kiểm tra dấu tiếng Việt
  (ă â ê ô ơ ư đ) trước khi render.
- **File `.env`:** copy từ `.env.example`, điền tối thiểu:
  - `VBEE_API_KEY`, `VBEE_VOICE_CODE_EN` (giọng đọc đề tiếng Anh)
  - `NEED_APPROVE_RESEARCH=false` ... `NEED_APPROVE_PUBLISH=false` (cả 8 cờ — Yêu cầu tự chạy)
  - `OUTPUT_VIDEO_LANDSCAPE=true`, `OUTPUT_VIDEO_PORTRAIT=false` (kiểm tra lại theo yêu cầu từng đợt)
- Kiểm tra nhanh: `.venv-manim/bin/python -c "from vieneu import Vieneu; Vieneu(mode='v3nano')"` phải init OK.

## 3. Bài học xương máu — BẮT BUỘC tuân thủ

1. **VieNeu TTS: LUÔN dùng `speed` gốc của `infer()`** (vd `infer(text, voice="Minh Quân", speed=0.9)`).
   CẤM dùng FFmpeg `atempo` để kéo chậm — atempo trên giọng synthetic gây tiếng vang/rỗng "vang vang". Đã xác minh cùng giọng Minh Quân bằng so phổ âm (similarity 0.95).
2. **VieNeu: `Vieneu(mode="v3nano")`, `voice="Minh Quân"`.** Bản `v3turbo` bị lỗi ONNX (external data),
   không load được — đừng cố.
3. **Môi trường Python: `~/workspace/openmontage/.venv-manim/bin/python`.**
   Trong venv này `huggingface_hub==0.34.0` đã được pin để tránh crash khi parse proxy
   (bản 2.x dùng httpx2 bị lỗi `Invalid port`). **Không upgrade, không cài faster-whisper.**
4. **Chữ trên màn hình (nếu có): nếu cần trích dẫn, luôn viết chính xác từ tiếng Anh, còn đọc hoặc phiên âm tiếng Việt không ảnh hưởng**. Ví dụ:
   Giọng đọc phát âm "xen" là bình thường (cách đọc "cent"), chỉ chữ hiện hình mới cần đúng.
5. **Không burn phụ đề vào video**. Giữ file SRT làm sidecar để upload riêng khi đăng.
6. **Watermark: logo chính thức** tại `~/workspace/openmontage/branding/toan-olympic-cung-con/logo.png`.
   Góc trên-trái, kích thước 10% cạnh ngắn, opacity 0.55, inset ~2%. Không vẽ lại logo.
7. **Thumbnail:** ảnh concept do AI vẽ (tuyệt đối không cắt frame từ video), **không lộ đáp án**,
   có banner hook chữ (vẽ bằng PIL + font Noto Sans — không để AI vẽ chữ vì hay lỗi dấu),
   logo kênh góc phải-dưới, tỉ lệ 16:9.
8. **Cấu trúc lời thoại:** hook trước (3–5s, không lộ đáp án, không chào "Hôm nay...") →
   nguồn + số câu → đọc nguyên văn đề tiếng Anh → đọc bản dịch tiếng Việt đầy đủ →
   giải → kiểm tra → đáp án → mẹo toán ngắn → CTA nhẹ → lời chúc.
   Không xưng thầy/cô, không ngôi thứ nhất (trừ câu trích trực tiếp trong đề).
   Số trong lời thoại tiếng Việt viết bằng chữ ("mười sáu", không "16").
9. **Tiếng Anh đọc đề:** Vbee `en-US-Standard-B`, speed 0.90, gain 1.20 khi mix + limiter, không clipping.
10. **Render:** landscape 1920×1080 (`.env` đang `OUTPUT_VIDEO_PORTRAIT=false` — kiểm tra lại snapshot
    của từng project, không mặc định). Không tự ý đổi runtime đã chốt ở proposal.

## 5. Chọn pipeline và concept — không đóng cứng

- **Đọc `~/workspace/openmontage/AGENT_GUIDE.md` trước mọi production task.** Đây là operating contract.
- **Pipeline:** đối chiếu yêu cầu với `pipeline_defs/*.yaml`, chọn pipeline có manifest thật phù hợp nhất
  (vd `animated-explainer` cho video giải thích). Đọc manifest để biết stages, gates, tools của pipeline đó.
- **Concept/style:** đọc `skills/meta/concept-selection.md`, hiển thị đầy đủ concept có sẵn cho người dùng chọn
  (hoặc theo chỉ định trong prompt). Đối chiếu `styles/math-*.yaml` trước khi chốt playbook.
  Đừng mặc định dùng lại playbook của video cũ nếu brief mới hợp với concept khác.
- **Approval:** `.env` đang đặt cả 8 cờ `NEED_APPROVE_*=false` → project mới tự chạy xuyên suốt
  không dừng chờ duyệt. Project đã init giữ snapshot quyền cũ.
- Tuyệt đối không ghi checkpoint bằng tay — chỉ dùng `lib.checkpoint.write_checkpoint()`.
- Mọi asset/output nằm trong thư mục project của nó; không ghi đè file dùng chung.
- Tham khảo video/project cũ trong `~/workspace/openmontage/projects/` khi cần, nhưng quyết định
  pipeline và playbook luôn dựa trên brief hiện tại.

## 6. Cách chạy pipeline cho video mới

```bash
cd ~/workspace/openmontage
# 1. Đọc: AGENT_GUIDE.md, AGENTS.md (repo), skills/pipelines/<pipeline>/*.md
# 2. Tạo project:
.venv-manim/bin/python -c "from lib.checkpoint import init_project; init_project('<project-id>', title='...', pipeline_type='<pipeline-da-chon>')"
# 3. Chạy tuần tự các stage theo manifest (vd: research → proposal → script → scene_plan → assets → edit → compose → publish)
#    mỗi stage: đọc stage director skill → làm → tự review → write_checkpoint()
```

## 7. File prompt đề bài

- `~/workspace/user/files/amo_2022_grade2_questions/` — prompt AMO 2022 + ảnh đề
- `~/workspace/user/files/amo_2023_grade2_questions/` — prompt AMO 2023 + ảnh đề
- Mỗi prompt .txt đã chứa: đề gốc EN, bản dịch VI, hook, logic giải, yêu cầu bố cục, timeline.
  Đọc kỹ và tuân thủ — nhưng các bài học mục 4 ưu tiên hơn nếu có xung đột
  (vd prompt cũ ghi dùng atempo thì bỏ, dùng speed gốc).

## 8. Ghi chú khác

- Nhạc nền: tự tổng hợp local (Pixabay bị chặn 403), duck dưới lời thoại bằng sidechaincompress.
- Whisper/faster-whisper không cài được (proxy chặn download model) → QA audio bằng kiểm tra năng lượng/peak,
  không transcript được thì ghi rõ trong report.
- Subagent không dùng được `chat.read_messages` / skill export-conversation → hội thoại xuất từ phía chat chính.
- Khi upscale ảnh: luôn giữ tỉ lệ gốc (kiểm tra kích thước bằng PIL trước), không ép cứng khung hình.
