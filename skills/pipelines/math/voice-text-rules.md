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
- **Xưng hô:** Khi giảng hoặc nói với người xem, luôn xưng **thầy**.
  Gọi người học là **các em**, **các con** hoặc **các bạn nhỏ**.
- **Từ cấm:** Không dùng **cô** trong kịch bản, `voiceText`, phụ đề
  hoặc bất kỳ nội dung hiển thị nào.
- **Vbee:** Lời Việt dùng `VBEE_VOICE_CODE_VI`; đề gốc tiếng Anh dùng
  `VBEE_VOICE_CODE_EN` (mặc định `am_echo`). Cả hai giọng đều theo
  persona nam; xem mục 3 về blocker khi thiếu config EN.

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
  "voiceText": "Thầy trừ năm ở cả hai vế để giữ phương trình tương đương.",
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

Video phải mở bằng lời chào ngắn, nói nhiệm vụ hôm nay **dưới dạng thử thách
của chính bài toán**, nhắc điều kiện quan trọng và hỏi một câu khiến người học
muốn thử ngay.

**Cấm:**
- Dùng lời giới thiệu chung chung như *"bài toán rất thú vị"*.
- Đọc đối tượng/lớp học thay cho hook.
- Tiết lộ đáp án hay bước giải trong hook.
- Ở chế độ `guided`: minh họa thao tác làm lộ bước quyết định hoặc đáp án.

**Khai báo:**
- Đặt câu hook vào `math-intro.hookQuestion` (viết số bằng chữ, kết thúc `?`).
- Đọc nguyên câu hook trong `voiceText` của scene mở đầu.
- Dùng `math-intro.teachingAid` cho icon/hình phù hợp đề ngay đầu video.
- Script schema kiểm tra `hookQuestion` có trong `voiceText`; kịch bản cũ thiếu
  trường này vẫn tương thích (không bị chặn).

### 3b. Trình tự bắt buộc — đề tiếng Việt

```
lời chào → nói hôm nay học/làm gì → nội dung → lời chúc
```

Ví dụ lời chào: *"Thầy chào các em. Hôm nay thầy cùng các em tìm hiểu cách
giải phương trình."*

### 3c. Trình tự bắt buộc — đề tiếng Anh

```
1. Chào bằng tiếng Việt
2. Nói hôm nay học/giải bài gì
3. Thông báo sẽ đọc nguyên văn tiếng Anh
4. Đọc toàn bộ đề = Vbee VBEE_VOICE_CODE_EN (am_echo), tốc độ 0.9×
5. Đọc bản dịch Việt đầy đủ, chính xác = giọng nam Việt
6. Bắt đầu lời giải / hướng dẫn (SAU KHI đọc cả đề gốc và bản dịch)
```

**Quy tắc kỹ thuật cho đề tiếng Anh:**

- Đề gốc tiếng Anh dùng trường `englishText`; `voiceText` để **rỗng** cho scene đó.
  Giữ nguyên nội dung, thứ tự câu, số và ký hiệu; không dịch, tóm tắt hay phiên âm.
  Quy tắc viết số bằng chữ tiếng Việt **không áp dụng** cho đoạn nguyên văn Anh.
- Tạo audio tiếng Anh riêng bằng `vbee_tts` với `language="en"`, ghép đúng timeline.
  **Không** đưa nguyên văn tiếng Anh qua giọng Việt.
- **Blocker:** Thiếu `VBEE_VOICE_CODE_EN` / `VBEE_APP_ID` / `VBEE_ACCESS_TOKEN`
  phải dừng và báo lỗi **trước** khi chạy TTS Việt. Không tự đổi provider.
  Không tự đặt `language="vi"` cho đoạn đề Anh.
- Hiển thị đề gốc khi đọc tiếng Anh; hiển thị bản dịch khi đọc Việt.
  Căn thời lượng scene theo audio thực tế; không ép thời lượng cố định.

### 3d. Kết thúc video

- CTA (nếu có) đặt **trước** lời chúc.
- Câu cuối cùng **bắt buộc** là lời chúc phù hợp với lứa tuổi học sinh.
  Ví dụ: *"Thầy chúc các em học tốt và luôn tự tin khi giải toán."*

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
