# Math Video — Script Director

> **Scope:** Quy tắc viết kịch bản cho mọi video giải toán trong OpenMontage.
> Đọc file này **trước** khi viết bất kỳ `voiceText`, khai báo phase, hay gọi TTS.
>
> **Phụ thuộc (đọc theo thứ tự):**
> 1. [`skills/pipelines/math/voice-text-rules.md`](voice-text-rules.md) — persona, encoding, hook, EN-TTS
> 2. [`AGENT_GUIDE.md → Math Problem Videos`](../../../AGENT_GUIDE.md) — thứ tự đọc đề EN
> 3. [`skills/meta/voice-performance-director.md`](../../meta/voice-performance-director.md) — delivery cues
>
> **Nguồn gốc:** Port từ `Auto-Create-Video/docs/math-video-workflow.md`
> (2026-10-10, phuongdev89). Bỏ các mục về toolchain nội bộ ACV (npm pipeline,
> progress server); giữ nguyên quy tắc kịch bản và phase sequence.

---

## 1. Thứ tự bắt buộc trước khi viết kịch bản

```
nhận đề
  → xác định lớp  (mục 2)
  → hỏi/chờ chọn lớp
  → hỏi/chờ chọn solutionMode  (mục 3)
  → giải và tự kiểm chứng nội bộ
  → viết kịch bản
  → validate schema
```

**Không** đi thẳng từ lựa chọn cách giải sang kịch bản hay sản xuất.

---

## 2. Xác định lớp trước khi giải (mục #12)

### 2a. Khi lớp đã rõ

Nếu đầu vào hoặc người dùng đã nêu lớp/trình độ rõ ràng, dùng thông tin đó; không hỏi lại khi tiếp tục cùng bài.

### 2b. Khi chưa biết lớp

Agent phải tự phân tích trước khi hỏi: chủ đề, kiến thức tiên quyết, loại phép toán, ký hiệu, yêu cầu chứng minh, cách giải phù hợp. Không suy lớp chỉ từ độ lớn con số, tên file hay một từ khóa.

Sau phân tích, hỏi người dùng:

> **Bạn muốn thầy giảng bài này cho lớp mấy?**
>
> Nêu khoảng lớp phù hợp và một lý do ngắn; mỗi lớp trong khoảng là một lựa chọn riêng, đánh dấu **Lớp N (Khuyến nghị)**. Ví dụ: *"Kiến thức cần dùng là phương trình một ẩn; đề có thể phù hợp lớp 6–8. Thầy đề xuất lớp 7."*

- Dùng `AskUserQuestion` (Claude Code) hoặc `request_user_input_async` (Codex) với `options` là các nhãn lớp.
- Có thể gộp câu hỏi lớp và câu hỏi `solutionMode` trong một lần hỏi, mỗi câu giữ lựa chọn riêng.
- **Chờ câu trả lời thật** cho cả hai trước khi giải, viết kịch bản hoặc gọi TTS/render.
- Nếu kiến thức không thuộc phổ thông, đưa lựa chọn trình độ tương ứng, không ép thành lớp 1–12.
- Nếu môi trường không hỗ trợ lựa chọn bấm, hiển thị bằng văn bản đánh số và chờ.

### 2c. Lưu kết quả

Lưu vào `projects/YYYY-MM-DD_<project-id>/artifacts/grade-selection.json`:

```json
{
  "source": "inferred | provided",
  "suggestedGrades": ["Lớp 7", "Lớp 8"],
  "recommendedGrade": "Lớp 7",
  "reason": "Kiến thức cần dùng là phương trình một ẩn",
  "confidence": "high | medium | low",
  "selectedGrade": "Lớp 7"
}
```

`selectedGrade` chỉ ghi sau câu trả lời thật. Ghi lớp đã chọn vào `problem.level` của script. Nếu người dùng đổi lớp sau khi audit, rà soát lại kịch bản.

---

## 3. Chọn chế độ giải — `solutionMode` (mục #13)

Trước khi giải hoặc viết kịch bản, hỏi:

> **Bạn muốn giải bài toán theo cách nào?**
>
> - **Giải ra đáp án** → `solutionMode: "answer"`
> - **Hướng dẫn giải và để ngỏ đáp án** → `solutionMode: "guided"`

**Quy tắc bắt buộc:**

- Không xem lựa chọn được đánh dấu sẵn hoặc hết thời gian chờ là câu trả lời.
- Không tự mặc định và không giải/TTS/render khi câu hỏi chưa được trả lời.
- Có thể đọc đề và kiểm tra dữ kiện trong khi chờ.
- Khi tiếp tục cùng bài đã chọn, dùng lại lựa chọn cũ.
- Khi nhận bài mới, phải hiển thị lại lựa chọn.

Trong **cả hai chế độ**, agent vẫn giải và kiểm chứng **nội bộ** đầy đủ.

---

## 4. Phase sequence kịch bản (mục #7, #8, #9)

### 4a. Đề tiếng Việt — chế độ `answer`

```
introduction → problem → [strategy] → solution (N cảnh) → check → answer → closing
```

- `strategy` tùy chọn nhưng khuyến nghị cho bài phức tạp.

### 4b. Đề tiếng Việt — chế độ `guided`

```
introduction → problem → strategy → solution (hướng dẫn, KHÔNG hoàn tất đáp án) → check → practice → closing
```

- `strategy` **bắt buộc**.
- Đúng **một** cảnh `practice` dùng template `math-step`.
- **Không** có phase `answer` hoặc template `math-answer`.

### 4c. Đề tiếng Anh — chế độ `answer`

```
introduction → read-english → read-translation → [strategy] → solution → check → answer → closing
```

- `introduction`: mở ngay bằng hook thử thách cụ thể theo concept; lời chào chỉ được đặt sau dữ kiện gợi tò mò, rồi **thông báo** sẽ đọc nguyên văn tiếng Anh.
- `read-english`: dùng `englishText`, `voiceText` để **rỗng**; TTS = `vbee_tts` với `language="en"` ở `0.90×` (tốc độ cố định; không giảm thêm khi mix).
- `read-translation`: đọc bản dịch Việt đầy đủ, chính xác bằng giọng nam Việt.
- Có thể chia đề/bản dịch thành nhiều cảnh liên tiếp, giữ đầy đủ nguyên văn khi ghép.

### 4d. Đề tiếng Anh — chế độ `guided`

```
introduction → read-english → read-translation → strategy → solution → check → practice → closing
```

- Giữ nguyên thứ tự đọc EN/bản dịch như `answer`; `strategy` bắt buộc; thay `answer` bằng `practice`.

---

## 5. Quy tắc từng phase

### `introduction`

- Lời chào theo [`voice-text-rules.md`](voice-text-rules.md) mục 3b.
- Hook phải nêu mâu thuẫn/dữ kiện lạ của bài toán bằng ngôn ngữ của `visualConcept`, tạo tò mò rồi đặt câu hỏi cụ thể; không dùng lời chào hoặc tên kỳ thi làm hook thay thế (mục 3a trong voice-text-rules và mẫu tại `visual-concepts.md`).
- Khai báo câu hỏi thử thách cuối hook trong `math-intro.hookQuestion`; đọc nguyên câu trong `voiceText`. Chỉ dẫn SFX/visual không được đưa vào lời đọc nếu không chủ ý cho TTS đọc.

### `read-english` (chỉ đề Anh)

- `templateData.template`: `math-problem`, `templateData.text` = `englishText`.
- `voiceText`: **rỗng** (pipeline đọc từ `englishText` qua Vbee EN).
- Giữ nguyên nội dung, thứ tự câu, số, ký hiệu; không dịch hay tóm tắt.
- Hiển thị đề gốc trên màn hình khi cảnh này phát.
- **Blocker:** thiếu `VBEE_VOICE_CODE_EN` / `VBEE_APP_ID` / `VBEE_ACCESS_TOKEN` → dừng, không chạy TTS Việt tiếp.

### `read-translation` (chỉ đề Anh)

- Đọc **toàn bộ** bản dịch Việt, chính xác, không bỏ điều kiện hay đơn vị.
- Hiển thị bản dịch trên màn hình khi cảnh này phát.
- Căn thời lượng cảnh theo audio thực tế; không ép thời lượng cố định. (mục #11)

### `solution`

- Nhiều cảnh nếu cần (6–100 cảnh toàn bộ kịch bản).
- Chia đoạn dài thành cảnh nhỏ nhưng giữ toàn bộ nội dung.
- Mỗi cảnh dùng template `math-step`; tham chiếu pedagogy-rules để chọn mức giải thích phù hợp lớp đã chọn.

### `check`

- Chế độ `answer`: hướng dẫn kiểm tra thay nghiệm, điều kiện xác định, đơn vị.
- Chế độ `guided`: hướng dẫn cách tự kiểm tra **khi người học đã có kết quả**; không đọc nghiệm.

### `answer` (chỉ chế độ `answer`)

- Template `math-answer`; `answer` field = LaTeX của đáp án đúng.
- Phải bỏ hẳn trường `answer` trong script khi `solutionMode = "guided"`.

### `practice` (chỉ chế độ `guided`)

- Đúng một cảnh; template `math-step`.
- Giao bước còn lại hoặc câu hỏi để người học tự hoàn thành.
- Không gợi ý dẫn đến đáp án.

### `closing`

- Template `math-closing`; field `message` có lời chúc.
- CTA (nếu có) trong `voiceText` đặt **trước** câu lời chúc.
- Câu cuối cùng **bắt buộc** là lời chúc phù hợp lứa tuổi.

---

## 6. Guided — rà soát không lộ đáp án (mục #14)

Trước khi chạy TTS, rà soát **toàn bộ**:

| Đối tượng | Kiểm tra |
|-----------|----------|
| `voiceText` mọi cảnh | Không đọc nghiệm, không đọc kết quả bước quyết định |
| Tiêu đề (`title`) | Không chứa đáp án |
| Công thức (`equations`) | Không hoàn tất phép tính đến đáp án |
| `note` trong math-step | Không gợi ý trực tiếp kết quả |
| Phụ đề (subtitles) | Được sinh từ `voiceText` — nếu voiceText sạch, phụ đề sạch |
| Sơ đồ (`math-diagram`) | Không annotate kết quả |
| Phase `check` | Không thay nghiệm vào phương trình để "kiểm tra" rồi đọc vế bằng nhau |

**Không** chỉ bỏ cảnh `answer` sau khi đã đọc nghiệm ở bước `solution` trước đó.

Lời giải đầy đủ lưu trong `projects/YYYY-MM-DD_<project-id>/artifacts/solution.md` — **nội bộ**, không đưa vào video, phụ đề hay bất kỳ nội dung trả cho người xem.

---

## 7. Templates toán

| Template | Fields bắt buộc | Fields tùy chọn |
|----------|----------------|-----------------|
| `math-intro` | `title` | `subtitle`, `hookQuestion`, `teachingAid` |
| `math-problem` | `title`, `text` | `latex` |
| `math-step` | `title` | `explanation`, `equations` (0–4 LaTeX), `note` — phải có ít nhất `explanation` hoặc `equations` |
| `math-diagram` | `title`, `shapes` | `explanation`, `latex` |
| `math-answer` | `title`, `answer` (LaTeX) | `explanation`, `takeaway` |
| `math-closing` | `title`, `message` | — |

**Giới hạn số cảnh:** 6–100. Bài rất dài có thể chia video khi người dùng đồng ý.

---

## 8. Tham chiếu liên quan

- Persona + voiceText encoding: [`voice-text-rules.md`](voice-text-rules.md)
- Sư phạm toán + teachingAid: [`pedagogy-rules.md`](pedagogy-rules.md) *(sẽ bổ sung)*
- Audit độc lập: xem mục "Duyệt lời giải và audit" *(sẽ bổ sung trong workflow-director.md)*
- Render các tỷ lệ được bật: xem [`compose-director.md`](compose-director.md) và `skills/pipelines/shared/output-formats.md`.
