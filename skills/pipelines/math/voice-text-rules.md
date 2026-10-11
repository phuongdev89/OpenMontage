# Math Video — Voice & Text Rules

> **Scope:** Quy tắc này áp dụng cho mọi video giải toán trong OpenMontage.
> Nó bổ sung (không thay thế) `skills/meta/voice-performance-director.md`
> và `AGENT_GUIDE.md → Math Problem Videos`.
>
> **Nguồn gốc:** Port từ `Auto-Create-Video/docs/voice-text-rules.md`
> (2026-10-10, phuongdev89). Giữ nguyên ngữ nghĩa; chỉ bổ sung
> ngữ cảnh OpenMontage (tên tool, env var, schema path).

---

## 1. Giọng đọc và cách xưng hô (Persona — HARD RULES)

- **Giới tính:** Luôn dùng giọng **nam** của provider đang cấu hình.
  Không tự suy đoán giới tính từ voice ID không có mô tả.
  Không tự thay giọng người dùng đã cấu hình.
- **Không tự xưng/ngôi thứ nhất:** Trong lời thoại do agent viết, tuyệt đối
  không tự xưng **thầy**, **cô** hay vai trò nào khác; không dùng ngôi thứ
  nhất số ít hoặc số nhiều, gồm `tôi`, `mình`, `ta`, `chúng tôi`, `chúng ta`
  và `chúng mình`. Áp dụng cho kịch bản, `voiceText`, phụ đề và nội dung
  hiển thị do người dẫn thuật lại.
- Gọi người học trực tiếp là **các em**, **các con** hoặc **các bạn nhỏ**;
  có thể dùng câu trung tính hoặc mệnh lệnh như **"hãy cùng..."**.
- Không dùng **cô** để tự xưng. Không sửa nội dung nguồn phải đọc/trích
  nguyên văn; quy tắc này áp dụng cho lời dẫn do agent soạn.
- **Routing bắt buộc theo ngôn ngữ (agent phải làm đúng thứ tự này):**
  1. Lời tiếng Việt: **ưu tiên sử dụng skill `vieneu-tts`** để tạo audio
     bằng VieNeu-TTS local và preset giọng nam đã chọn.
  2. Nếu skill `vieneu-tts` không khả dụng (thiếu package, model hoặc lỗi
     runtime), **dùng API `vbee` làm fallback cho tiếng Việt** với
     `VBEE_VOICE_CODE_VI`.
  3. Lời tiếng Anh: **luôn sử dụng API `vbee`**, với
     `VBEE_VOICE_CODE_EN` (mặc định `am_echo`). Không dùng VieNeu để đọc
     tiếng Anh.
  Không tự đổi thứ tự ưu tiên hoặc provider; ghi provider thực tế và lý do
  fallback vào asset manifest. Cả hai giọng đều theo persona nam.

---

## 2. Viết lời đọc tiếng Việt (`voiceText`)

Lời đọc và text hiển thị là **hai phần riêng biệt**: text trên hình có thể
giữ chữ số, ký hiệu toán và LaTeX; lời đọc phải viết số và phép toán
bằng chữ để TTS đọc tự nhiên.

### 2a. Quy tắc chung

- Viết tất cả chữ số và ký hiệu toán thành chữ: cộng, trừ, nhân, chia,
  bằng, lớn hơn, nhỏ hơn, phần trăm.
- **Không** đưa công thức LaTeX vào `voiceText`.
- **Không** dùng emoji, Markdown hoặc URL trong lời đọc.
- Kết thúc mỗi câu bằng dấu chấm hoặc dấu chấm hỏi để TTS ngắt nghỉ tự nhiên.
- Dùng đúng thuật ngữ toán, đọc đầy đủ đơn vị và điều kiện;
  không đổi nội dung đề khi chuyển từ ký hiệu sang lời nói.

### 2b. Bảng quy đổi

| Hiển thị | `voiceText` |
|---|---|
| `2x + 5 = 17` | hai nhân x cộng năm bằng mười bảy |
| `3.5` hoặc `3,5` | ba phẩy năm |
| `1/2` | một phần hai |
| `x²` | x bình phương |
| `√9` | căn bậc hai của chín |
| `30%` | ba mươi phần trăm |
| `3:1` (tỉ lệ) | ba so với một |
| `1 000` (số nguyên) | một nghìn |
| `12 cm²` | mười hai xăng ti mét vuông |

### 2c. Phiên âm tên kỳ thi

Nếu TTS đọc sai tên kỳ thi, ghi theo cách đọc vào `voiceText`:

| Tên gốc | Viết trong `voiceText` |
|---------|------------------------|
| AMO | a mờ ô |
| TIMO | ti mô |
| FMO | ép mờ ô |
| ASMO | a ét mờ ô |
| SEAMO | si mờ ô |
| HKIMO | hát ca i mờ ô |
| KANGAROO | căng ga ru |
| IKMC | i ca mờ cê |

### 2d. Ví dụ tách lời đọc và công thức hiển thị

```json
{
  "voiceText": "Trừ năm ở cả hai vế để giữ phương trình tương đương.",
  "templateData": {
    "template": "math-step",
    "title": "Trừ 5 ở hai vế",
    "equations": ["2x + 5 - 5 = 17 - 5"]
  }
}
```

---

## 3. Trình tự mở đầu, đọc đề và kết thúc (BẮTBUỘC)

### 3a. Hook bằng thử thách cụ thể

Video phải mở bằng một hook giữ chân người xem, không chỉ là lời chào rồi
đọc lại đề. Hook phải nêu mâu thuẫn hoặc dữ kiện lạ nhất của chính bài toán,
diễn đạt theo `visualConcept` đã chọn, rồi đặt câu hỏi cụ thể khiến người xem
muốn tìm đáp án. Có thể mở bằng một âm thanh/hình ảnh đặc trưng của concept,
nhưng hiệu ứng sân khấu phải nằm ngoài `voiceText` nếu không được đọc thành lời.

**Cấm:**
- Mở đầu chỉ bằng lời chào, tên lớp/kỳ thi, hoặc câu dẫn chung chung như
  *"Hôm nay chúng ta sẽ học một bài toán rất thú vị"*.
- Chỉ đọc lại nguyên văn đề mà chưa tạo mâu thuẫn, hình ảnh hoặc câu hỏi gợi tò mò.
- Dùng concept không liên quan tới ngôn ngữ hình ảnh của video.
- Tiết lộ đáp án hay bước giải trong hook.
- Ở chế độ `guided`: minh họa thao tác làm lộ bước quyết định hoặc đáp án.
- Tự xưng hoặc dùng ngôi thứ nhất trong hook; xem mục 1.

**Khung hook:** tín hiệu đặc trưng của concept → dữ kiện/mâu thuẫn chính xác
của bài toán → gọi người xem theo concept → câu hỏi mở hoặc lời mời bắt đầu.
Không bắt buộc đủ bốn nhịp nếu làm hook dài dòng; ưu tiên vào thử thách sớm.
Các ví dụ theo từng concept nằm trong
[`visual-concepts.md`](visual-concepts.md#3d-hook-theo-visual-concept).

**Khai báo:**
- Đặt câu hỏi thử thách cuối hook vào `math-intro.hookQuestion` (viết số bằng chữ, kết thúc `?`).
- Đọc nguyên câu hook trong `voiceText` của scene mở đầu.
- Dùng `math-intro.teachingAid` cho icon/hình phù hợp đề ngay đầu video.
- Script schema kiểm tra `hookQuestion` có trong `voiceText`; kịch bản cũ thiếu
  trường này vẫn tương thích (không bị chặn).

### 3b. Trình tự bắt buộc — đề tiếng Việt

```
cue theo concept (nếu có) → hook nêu thử thách → đề bài đầy đủ → lời giải → lời chúc
```

Hook được mở bằng mâu thuẫn hoặc dữ kiện gợi tò mò của bài toán; lời chào và
cách gọi người xem được lồng tự nhiên vào hook, không đặt một đoạn chào chung
chung lên trước để trì hoãn thử thách. Không đọc lặp lại cùng một dữ kiện dài
dòng ở cả hook và phần đề bài đầy đủ.

### 3c. Trình tự bắt buộc — đề tiếng Anh

```
1. Chào bằng tiếng Việt
2. Nói hôm nay học/giải bài gì
3. Thông báo sẽ đọc nguyên văn tiếng Anh
4. Đọc toàn bộ đề = Vbee API với `VBEE_VOICE_CODE_EN` (mặc định `am_echo`), tốc độ 0.85×; khi mix, tăng gain riêng đoạn tiếng Anh lên 1.20 và kiểm tra không clipping. Thiếu cấu hình Vbee tiếng Anh = blocker; chỉ thay provider khi người dùng duyệt.
5. Đọc bản dịch Việt đầy đủ, chính xác = ưu tiên skill `vieneu-tts`; nếu
   skill không khả dụng thì dùng API `vbee` với `VBEE_VOICE_CODE_VI`.
6. Bắt đầu lời giải / hướng dẫn (SAU KHI đọc cả đề gốc và bản dịch)
```

**Quy tắc kỹ thuật cho đề tiếng Anh:**

- Đề gốc tiếng Anh dùng trường `englishText`; `voiceText` để **rỗng** cho scene đó.
  Giữ nguyên nội dung, thứ tự câu, số và ký hiệu; không dịch, tóm tắt hay phiên âm.
  Quy tắc viết số bằng chữ tiếng Việt **không áp dụng** cho đoạn nguyên văn Anh.
- Tạo audio tiếng Anh riêng bằng `vbee_tts` với `language="en"`, ghép đúng timeline.
  **Không** đưa nguyên văn tiếng Anh qua giọng Việt.
- Tạo các đoạn tiếng Việt bằng skill `vieneu-tts` trước; chỉ khi skill không
  khả dụng mới gọi API `vbee` tiếng Việt. Ghi rõ provider thực tế, lý do
  fallback, preset/voice, tốc độ và đường dẫn audio vào asset manifest.
- **Blocker:** Thiếu `VBEE_VOICE_CODE_EN` / `VBEE_APP_ID` / `VBEE_ACCESS_TOKEN`
  phải dừng và báo lỗi **trước** khi chạy TTS Việt. Không tự đổi provider.
  Không tự đặt `language="vi"` cho đoạn đề Anh.
- Hiển thị đề gốc khi đọc tiếng Anh; hiển thị bản dịch khi đọc Việt.
  Căn thời lượng scene theo audio thực tế; không ép thời lượng cố định.

### 3d. Kết thúc video

- CTA (nếu có) đặt **trước** lời chúc.
- Câu cuối cùng **bắt buộc** là lời chúc phù hợp với lứa tuổi học sinh.
  Ví dụ: *"Chúc các con học tốt và luôn tự tin khi giải toán."*

---

## 4. Hai chế độ giải (`solutionMode`)

Trước khi giải, hỏi người dùng chọn một trong hai chế độ:

| Lựa chọn hiển thị | `solutionMode` |
|---|---|
| Giải ra đáp án | `answer` |
| Hướng dẫn giải và để ngỏ đáp án | `guided` |

### Chế độ `answer`

Trình bày đầy đủ lời giải, kiểm tra và đáp án trước lời chúc.

### Chế độ `guided`

- Hướng dẫn phương pháp và các bước; để người học tự hoàn thành bước quyết định.
- Chỉ hướng dẫn cách tự kiểm tra, **không** đọc nghiệm để thay lại.
- Kết thúc nội dung bằng câu hỏi hoặc nhiệm vụ tự làm (`practice`), rồi lời chúc.
- Rà soát **toàn bộ** lời đọc, công thức, tiêu đề, sơ đồ và phụ đề để không lộ
  đáp án cuối hoặc phương án trắc nghiệm đúng.
- Không hoàn tất lời giải rồi chỉ bỏ scene kết luận.
- Lời giải đầy đủ lưu riêng trong `solution.md` (nội bộ) — không chia sẻ với người xem.

---

## 5. Tham chiếu liên quan

- Quy tắc sư phạm toán: [`skills/pipelines/math/pedagogy-rules.md`](pedagogy-rules.md) *(sẽ bổ sung)*
- Workflow đầy đủ: [`AGENT_GUIDE.md → Math Problem Videos`](../../../AGENT_GUIDE.md)
- Voice performance chung: [`skills/meta/voice-performance-director.md`](../../meta/voice-performance-director.md)
- Tool TTS: `tools/audio/vbee_tts.py` — param `language="en"` cho đề Anh
