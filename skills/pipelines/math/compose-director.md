# Math Video — Compose Director

> **Scope:** Quy tắc render và xuất file cho video giải toán trong OpenMontage.
> Đọc file này trước khi gọi `video_compose` hoặc bất kỳ render tool nào.
>
> **Phụ thuộc:** Kịch bản đã được audit pass trước khi render
> (xem `workflow-director.md` khi có).
>
> **Nguồn gốc:** Port từ `Auto-Create-Video/docs/math-video-workflow.md`
> mục "HTML responsive và hai video bắt buộc" (2026-10-10, phuongdev89).

---

## 1. Hai video bắt buộc (mục #22)

Mọi video giải toán phải xuất **cả hai bản**:

| Bản | Kích thước | File |
|-----|-----------|------|
| Dọc (Portrait) | 1080 × 1920 | `video-portrait.mp4` |
| Ngang (Landscape) | 1920 × 1080 | `video-landscape.mp4` |

`video.mp4` vẫn là bản dọc để tương thích ngược.

**Quy tắc bắt buộc:**

- Chỉ báo hoàn tất sau khi **cả hai** render thành công.
- Nếu một bản lỗi: báo thiếu bản đó, chưa giao đủ đầu ra — không báo xong.
- `--no-render` chỉ xuất composition/audio để preview; **không** được gọi là đã giao hai video.

---

## 2. Layout bản ngang

Bản ngang **không** kéo giãn hình dọc. Dùng layout hai cột:

- **Rail trái:** tiêu đề, đề bài.
- **Vùng phải:** nội dung làm bài (equations, diagram, steps).

Bố cục này cần duyệt riêng nếu nâng thiết kế từ script legacy.

---

## 3. HTML composition — responsive

Mọi HTML composition phải:

- Fit toàn bộ canvas theo viewport, cập nhật khi resize.
- Không crop công thức hay hình.
- Preview mobile/desktop không đổi timeline hoặc nội dung đã audit.
- Kích thước xuất cố định theo metadata của từng composition.

---

## 4. Audio — dùng chung

Hai bản **dùng chung** audio, lời đọc, audit và scene timing.
Không gọi TTS thêm chỉ vì đổi tỷ lệ.

---

## 5. Kiểm tra sau render

Trước khi báo hoàn tất:

- Mở cả hai HTML trên browser, seek timeline, kiểm tra layout.
- `ffprobe` cả hai MP4 để xác nhận kích thước và duration.
- Kiểm tra đáp án, chữ, độ đọc được và audio trên MP4 cuối.
- Báo riêng bằng chứng: schema/test, Vbee English TTS, provider TTS, render.
- Mock không chứng minh TTS thật.

---

## 6. `formats.json`

Ghi đường dẫn và kích thước cả hai bản vào
`projects/YYYY-MM-DD_HH-MM-SS_<project-id>/artifacts/formats.json`:

```json
{
  "portrait": {
    "path": "projects/YYYY-MM-DD_HH-MM-SS_<project-id>/renders/video-portrait.mp4",
    "width": 1080,
    "height": 1920
  },
  "landscape": {
    "path": "projects/YYYY-MM-DD_HH-MM-SS_<project-id>/renders/video-landscape.mp4",
    "width": 1920,
    "height": 1080
  }
}
```

---

## 7. Tham chiếu liên quan

- Audit trước render: `workflow-director.md` *(sẽ bổ sung)*
- Phase sequence và templates: [`script-director.md`](script-director.md)
- Pedagogy + teachingAid: [`pedagogy-rules.md`](pedagogy-rules.md)
