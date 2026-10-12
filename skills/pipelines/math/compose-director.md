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

## 1. Tỷ lệ xuất theo cấu hình

Video kênh Toán Olympic Cùng Con: đọc `skills/pipelines/shared/channel-branding.md`.
Thêm watermark logo gốc cố định ở góc trên trái, cách mỗi cạnh kề tối đa 5%;
QA bản đã có watermark trước khi ghi checkpoint compose completed.

Đọc `skills/pipelines/shared/output-formats.md`. Chỉ dựng và xuất các bản trong
`project.json.output_video_formats`, được chụp từ `.env` khi init project:

| Bản | Kích thước | File |
|-----|-----------|------|
| Dọc (Portrait) | 1080 × 1920 | `video-portrait.mp4` |
| Ngang (Landscape) | 1920 × 1080 | `video-landscape.mp4` |

`video.mp4`, nếu dùng, là alias của bản dọc khi được bật, nếu không là bản ngang.

**Quy tắc bắt buộc:**

- Chỉ báo hoàn tất sau khi **mọi bản được bật** render thành công.
- Nếu một bản được bật lỗi: báo thiếu bản đó, chưa giao đủ đầu ra — không báo xong.
- `--no-render` chỉ xuất composition/audio để preview; **không** được gọi là đã giao đủ các bản được bật.

---

## 2. Layout bản ngang

Đọc `device-layout-rules.md` trước khi dựng hoặc sửa composition: bản ngang 16:9 dành cho PC/TV/tablet, bản dọc 9:16 dành cho Facebook/TikTok trên điện thoại. Mỗi bản có layout và bằng chứng độ đọc riêng; bản dọc cần safe area, preview 360 px và kiểm tra nhãn toán theo trạng thái cảnh.

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

- Mở HTML của mọi bản được bật trên browser, seek timeline, kiểm tra layout.
- `ffprobe` mọi MP4 được bật để xác nhận kích thước và duration.
- Kiểm tra đáp án, chữ, độ đọc được và audio trên MP4 cuối.
- Báo riêng bằng chứng: schema/test, Vbee English TTS, provider TTS, render.
- Mock không chứng minh TTS thật.

---

## 6. `formats.json`

Ghi đường dẫn và kích thước CHỈ các bản được bật vào
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

The JSON above illustrates both formats enabled. Omit disabled entries. The
publish director must include every enabled render in `exports/video/`; a single
generic `output.mp4` does not replace the enabled named outputs.
See [`skills/pipelines/explainer/publish-director.md`](../explainer/publish-director.md).

---

## 7. Tham chiếu liên quan

- Audit trước render: `workflow-director.md` *(sẽ bổ sung)*
- Phase sequence và templates: [`script-director.md`](script-director.md)
- Pedagogy + teachingAid: [`pedagogy-rules.md`](pedagogy-rules.md)

## Vietnamese typography and text containment gate

- SVG tải bằng `<img>` là tài liệu độc lập: font CSS của trang cha không tự truyền vào SVG. Phải đóng gói font đã xác minh ngay trong SVG hoặc chuyển chữ thành vector paths; kiểm tra từng SVG khi render độc lập. Chờ `document.fonts.ready` của trang cha không chứng minh font bên trong ảnh SVG đã tải.
- Kiểm tra bounding box của mọi `<text>` so với rect/badge chứa nó, không chỉ so với viewBox hay card HTML ngoài cùng. Cả nhãn ngắn và tiêu đề diagram đều phải vừa khung, có padding; lưu ảnh thực tế làm bằng chứng.
- Final review không được ghi `unreadable_text: false` hay `issues: []` khi ảnh review vẫn có chữ tràn hoặc glyph sai. Bất kỳ lỗi đó phải được ghi critical và sửa trước khi kết luận PASS.

- Dùng font hỗ trợ đầy đủ dấu tiếng Việt ở đúng weight/style; kiểm tra chuỗi có ă â ê ô ơ ư đ và dấu kép. Nạp font local hoặc font đã xác minh, không dựa vào fallback trên máy preview.
- Trước capture/render phải chờ font tải xong (`document.fonts.ready` với HTML/browser). Xác minh font thực tế và ảnh raster tiếng Việt; chỉ khai báo font-family không đủ bằng chứng.
- Kiểm tra mọi text container ở mọi tỷ lệ được bật (portrait/landscape), gồm tiêu đề, đề bài, labels, phụ đề và CTA. Với HTML kiểm tra scrollWidth/clientWidth và scrollHeight/clientHeight, sau đó kiểm tra ảnh thật để bắt dấu bị cắt hoặc glyph lỗi; runtime khác dùng kiểm tra bounding box tương đương.
- Chữ và dấu phải nằm trong border với padding an toàn. Sửa bằng wrap, chia trang, tăng vùng chữ hoặc giảm cỡ chữ trong giới hạn dễ đọc của playbook. Cấm dùng overflow:hidden/ellipsis để che mất nội dung hay bóp chữ méo.
- Ghi bằng chứng font, frame/ảnh review, tỷ lệ khung hình và kết quả containment vào review/render_report. Font lỗi hoặc chữ tràn = critical: sửa source trước render; auto-approval không bỏ qua kiểm tra này.


## Concurrent project isolation (binding)

Before media work, read `skills/pipelines/shared/project-isolation.md`. Bind all source, narration, public assets, temporary props and outputs to the exact current project. Verify audio ownership in every enabled final aspect ratio.
