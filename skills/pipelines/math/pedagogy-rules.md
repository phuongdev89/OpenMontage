# Math Video — Pedagogy Rules

> **Scope:** Quy tắc sư phạm cho mọi video giải toán trong OpenMontage.
> Đọc file này **trước** khi viết lời giảng (`voiceText`), chọn mức giải thích,
> hay khai báo `teachingAid`.
>
> **Phụ thuộc:** Đọc sau khi đã xác định lớp và `solutionMode`
> (xem [`script-director.md`](script-director.md) mục 2–3).
>
> **Nguồn gốc:** Port từ `Auto-Create-Video/docs/math-pedagogy-rules.md`
> (2026-10-10, phuongdev89). Bỏ các ref nội bộ ACV (references/ PDF);
> giữ nguyên 7 nguyên tắc, ví dụ đạt/chưa đạt, và quy tắc teachingAid.

---

## 1. Mục tiêu

Người học hiểu **vì sao** cách giải đúng, biết **khi nào** dùng và có thể
**tự thực hiện** phần phù hợp với trình độ.

- Không bắt bài đơn giản phải có đủ mọi hoạt động dưới đây.
- Giải và kiểm chứng nội bộ trước; các quy tắc này không thay thế kiểm tra tính đúng của toán học.

---

## 2. Chuẩn bị bài giảng

Xác định từ đề và yêu cầu:
- Trình độ dự kiến (lớp đã được người dùng xác nhận).
- Kiến thức nền cần dùng.
- Mục tiêu học tập.
- Một chỗ người học **có thể gặp khó khăn**.

Điều chỉnh phương pháp theo lớp đã xác nhận. Không khẳng định bài thuộc chương trình lớp cụ thể chỉ từ suy đoán.

---

## 3. Bảy nguyên tắc trình bày (mục #17)

### Nguyên tắc 1 — Giải thích lý do

Nêu ý nghĩa và điều kiện của phép biến đổi quan trọng, không chỉ đọc lại công thức.
Mô tả cách chọn phương pháp; chỉ so sánh thêm cách khác khi giúp hiểu cấu trúc bài,
không liệt kê cho đủ.

### Nguyên tắc 2 — Làm rõ ký hiệu và biểu diễn

Giải thích biến, đơn vị và quan hệ giữa sơ đồ với công thức.
Chỉ dùng hình khi giúp hiểu; không suy ra tính chất chỉ từ hình trông có vẻ đúng.
Dạy người học cách tự kiểm tra và xem lại hướng giải.

### Nguyên tắc 3 — Phù hợp kiến thức nền

Dùng thuật ngữ và phương pháp người học có thể theo được;
nhắc hoặc giải thích kiến thức mới trước khi dùng.
**Không** dùng mẹo vượt cấp làm lời giải chính nếu chưa giải thích cơ sở.

### Nguyên tắc 4 — Gợi ý vừa đủ

Đi từ nhận diện dữ kiện → chọn hướng → gợi ý bước cụ thể.
Trong video không tương tác, chọn mức gợi ý theo trình độ dự kiến,
không giả định học sinh đã hiểu hoặc làm đúng.

### Nguyên tắc 5 — Xử lý hiểu lầm có mục đích

Nếu có lỗi dễ gặp liên quan, chỉ rõ vì sao sai và cách sửa.
Không gán lỗi cho người học khi chưa thấy bài làm;
không dùng lời chê như *"bài dễ thế mà cũng sai"*.

### Nguyên tắc 6 — Chừa cơ hội suy nghĩ

Đặt câu hỏi cụ thể, ví dụ *"Vì sao cần trừ ở cả hai vế?"*
thay vì chỉ *"Các em hiểu chưa?"*.
Trong video, mời người học tạm dừng để làm;
không nói rằng hệ thống đang chờ hoặc chấm bài khi chưa có chức năng đó.

### Nguyên tắc 7 — Giữ mạch bài rõ

Mỗi đoạn tập trung một ý chính, nối dữ kiện với bước suy luận.
Kết hợp lời giải thích với công thức đang hiển thị;
chia đoạn khi có nhiều thao tác mới.
Không thêm cảnh, hiệu ứng hoặc thuật ngữ không giúp hiểu.

---

## 4. Hai chế độ giải — cách dạy

| Chế độ | Cách dạy | Phần tự làm |
|--------|----------|-------------|
| `answer` | Trình bày đủ bước và lý do, kiểm tra, kết luận đúng yêu cầu | Có thể hỏi dự đoán trước khi giải thích, nhưng cuối bài phải công bố đáp án |
| `guided` | Chọn gợi ý đủ để người học tiếp tục; giải thích phương pháp, hướng dẫn cách tự kiểm tra | Chừa một bước suy luận hoặc tính toán có ý nghĩa, phù hợp trình độ; chưa công bố kết quả cuối |

**Chế độ `guided` không phải giải hết rồi che con số cuối.** Xác định phần người học sẽ tự làm **trước** khi viết kịch bản. Không hoàn tất chứng minh rồi chỉ bỏ câu "điều phải chứng minh"; không loại hết phương án trắc nghiệm sai để còn đúng một phương án.

---

## 5. Ví dụ "chưa đạt / đạt" (mục #17)

Đề: tìm x biết `2x + 5 = 17`.

### Chế độ `answer`

**❌ Chưa đạt:**
> "Chuyển vế đổi dấu. Đáp án là x bằng sáu."

**✅ Đạt:**
> "Thầy trừ năm ở cả hai vế để giữ phương trình tương đương và đưa phần chứa x đứng riêng. Khi đó, hai nhân x bằng mười hai. Chia cả hai vế cho hai, ta được x bằng sáu. Thay sáu vào đề, hai nhân sáu cộng năm bằng mười bảy, nên kết quả thỏa mãn đề bài."

Lỗi có thể nhắc: chỉ trừ năm ở một vế làm thay đổi phương trình; "chuyển vế đổi dấu" cần được giải thích bằng phép toán thực hiện trên hai vế.

### Chế độ `guided`

**❌ Chưa đạt:**
> "Thầy tính được hai nhân x bằng mười hai, rồi x bằng sáu. Các em tự viết đáp án nhé."
> *(Kết quả đã bị tiết lộ.)*

**✅ Đạt:**
> "Mục tiêu là đưa x đứng riêng. Để bỏ phần cộng năm, ta cần thực hiện phép tính nào ở cả hai vế? Sau khi tự rút gọn, các em hãy tìm cách xử lý hệ số hai của x. Hãy viết giá trị tìm được và thay lại vào đề để kiểm tra hai vế."

Nhiệm vụ tự làm: chọn và thực hiện phép biến đổi, tìm x, rồi kiểm tra.

---

## 6. Minh họa đồ vật và `teachingAid` (mục #18, #19)

### 6a. Khai báo `requiresIllustration`

- Với bài cần minh họa trực quan, khai báo `problem.requiresIllustration: true`.
- Đánh dấu `needsIllustration: true` cho từng cảnh giải thích:
  - quan hệ không gian,
  - đếm đồ vật,
  - thao tác (cắt, tách, di chuyển).

### 6b. Thời điểm xuất hiện minh họa

Minh họa xuất hiện **ngay khi lời giảng bắt đầu dùng đến hình/đồ vật**,
từ cảnh `strategy` hoặc bước giải đầu tiên;
**không đợi** phần xét trường hợp hay kết luận.
Mốc thời gian phụ thuộc audio từng bài, không cố định.

### 6c. Thiết kế `teachingAid`

Dùng `templateData.teachingAid` trong `math-step` hoặc `math-diagram`.
Tự thiết kế giáo cụ riêng từ đề và lời giải — **không dùng bộ cân/giỏ cố định**;
**không chỉ dùng thẻ phép tính**.

Khai báo:
- Ý nghĩa và hình học của giáo cụ.
- Số lượng và nhãn.
- Animation cue theo từng ý: hiện vật → tô cạnh/nhóm đang được nói tới → cắt/tách → giữ trạng thái kết quả.

```json
{
  "templateData": {
    "template": "math-step",
    "title": "Chia 12 táo cho 4 bạn",
    "explanation": "Thầy chia đều mười hai quả táo thành bốn nhóm bằng nhau.",
    "teachingAid": {
      "type": "manipulative",
      "items": [
        { "icon": "apple", "count": 12, "label": "táo" }
      ],
      "cues": [
        { "action": "group", "groupSize": 3, "at": 0.3, "duration": 0.4 }
      ]
    }
  }
}
```

### 6d. Quy tắc animation

- Khi lời giảng nói cắt/tách/lấy ra: minh họa đường cắt rồi di chuyển phần được lấy.
- Phần phải dính liền: di chuyển đồng thời cùng khoảng dịch chuyển, không tách từng icon.
- Dùng lại icon và vị trí nhận diện giữa các cảnh.
- Không dùng nhãn chữ hoặc công thức **thay cho** minh họa cần thiết.
- Timing là tỷ lệ thời lượng cảnh, phải khớp lời đọc thực tế.
- Không suy diễn đường cắt hay đáp án từ tên đồ vật.

---

## 7. Rà soát trước khi gọi TTS

Trả lời các câu hỏi sau trước khi chạy TTS:

- Người học có đủ kiến thức nền để theo cách giải đã chọn không?
- Các bước quan trọng có lý do và điều kiện đúng, thuật ngữ/ký hiệu nhất quán không?
- Hình, lời đọc và công thức có cùng diễn đạt một quan hệ toán học không?
- Câu hỏi hoặc lỗi thường gặp được chọn có giúp hiểu bài này không?
- **Với `answer`:** lời giải đầy đủ, kết quả đã kiểm chứng và đáp án đúng yêu cầu chưa?
- **Với `guided`:** phần tự làm có ý nghĩa, vừa sức, cách tự kiểm tra rõ và không lộ kết quả cuối chưa?

---

## 8. Tham chiếu liên quan

- Phase sequence và solutionMode: [`script-director.md`](script-director.md)
- Persona + voiceText: [`voice-text-rules.md`](voice-text-rules.md)
- Tài liệu nguồn sư phạm: [`references/math-pedagogy/SOURCES.md`](references/math-pedagogy/SOURCES.md)
- Audit toán học: *(sẽ bổ sung trong `workflow-director.md`)*
