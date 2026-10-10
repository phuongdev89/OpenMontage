# Math Video — Creator Review

> **Scope:** Phần duyệt riêng cho người tạo video — hiển thị lời giải đầy đủ
> và kết quả audit **trong chat**, trước khi chọn concept hay chạy TTS/render.
>
> Đây là nội dung **nội bộ cho người tạo**, không phải bài giảng trả cho học sinh.
> Video, lời đọc, phụ đề và nội dung hướng dẫn cho người học vẫn giữ
> đáp án cuối ngoài nội dung (với chế độ `guided`).
>
> **Nguồn gốc:** Port từ `Auto-Create-Video/docs/math-video-workflow.md`
> mục "Duyệt lời giải và audit" (2026-10-10, phuongdev89).

---

## 1. Thứ tự bắt buộc (mục #23)

```
nhận đề
  → xác định lớp + chọn solutionMode  (chờ input thật)
  → giải và tự kiểm chứng nội bộ
  → viết kịch bản nháp
  → validate schema
  → [audit độc lập — mục 20, sẽ bổ sung]
  → hiển thị Creator Review trong chat   ← file này
  → chọn concept video  (nếu tạo video)
  → TTS / render  (chỉ khi audit đạt)
```

**Không** đi thẳng từ lựa chọn cách giải sang concept hay sản xuất.
Yêu cầu chỉ giải toán bằng văn bản cũng phải giải, audit và hiển thị
Creator Review trước khi trả bài.

---

## 2. Nội dung phải hiển thị trong chat (mục #23)

Sau khi audit kết thúc, hiển thị **ngay trong chat** — không chỉ trả link
hoặc câu "đã pass":

### 2a. Lời giải đầy đủ

- Giả thiết và điều kiện xác định.
- Các bước có lý do.
- Đáp án.
- Phép kiểm tra (thay nghiệm, tính độc lập, đơn vị, xét trường hợp).
- Với trắc nghiệm: ghi cả giá trị và phương án — không chỉ đoán chữ cái.

> Với chế độ `guided`: phần Creator Review **có thể** chứa lời giải đầy đủ và đáp án
> vì đây là duyệt nội bộ cho người tạo. Video và phụ đề cho học sinh vẫn không lộ.

### 2b. Kết quả audit thực tế

- Trạng thái: `pass / fail / uncertain / unverified`.
- Model và thời điểm chạy audit.
- Chạy mới hay dùng cache khớp nội dung hiện tại.
- Bằng chứng đối chiếu: suy luận, điều kiện, đáp án.
- Với `guided`: bằng chứng không lộ đáp án trong kịch bản.
- Nêu lỗi / mâu thuẫn / điểm chưa kiểm chứng (nếu có).

---

## 3. Quy tắc trình bày Creator Review

- **Không** dùng kết quả validate/mock thay cho audit thật.
- Nếu audit lỗi hoặc chưa đạt: báo trạng thái và vấn đề thực tế,
  **dừng** TTS/render; không tự ghi nhãn pass.
- Khi sửa nội dung toán: audit lại và hiển thị kết quả cập nhật trước khi tiếp tục.
- Trình bày Creator Review không tự tạo thêm một bước hỏi xác nhận;
  vẫn giữ bước chọn concept rõ ràng như quy định.

---

## 4. Lưu trữ nội bộ

| File | Nội dung | Chia sẻ với học sinh? |
|------|----------|----------------------|
| `projects/<id>/artifacts/solution.md` | Lời giải đầy đủ, đáp án, kiểm tra | ❌ Không |
| `projects/<id>/artifacts/grade-selection.json` | Lớp đã chọn, lý do | ❌ Không |
| `projects/<id>/artifacts/script.json` | Kịch bản video | Script chứa voiceText đã được lọc |

Không phục vụ `solution.md` qua bất kỳ endpoint công khai nào.

---

## 5. Tham chiếu liên quan

- Audit độc lập: `workflow-director.md` *(sẽ bổ sung — mục #20)*
- Phase sequence: [`script-director.md`](script-director.md)
- Guided leak check: [`script-director.md`](script-director.md) mục 6
