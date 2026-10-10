# Math Video — Visual Concepts

> **Scope:** Hướng dẫn agent chọn và áp dụng 6 visual concept cho video toán.
> Đọc file này sau khi đã có `solutionMode` và `selectedGrade`,
> trước khi gọi `video_compose`.
>
> **Nguồn gốc:** Port ý tưởng từ `Auto-Create-Video/docs/video-concepts.md`
> (2026-10-10, phuongdev89). Renderer là Remotion/HyperFrames của OpenMontage,
> không phải pipeline ACV. Visual trông tương tự, không y hệt.

---

## 1. Sáu concept và khi nào dùng

| `visualConcept` | Tên hiển thị | Playbook | Dùng tốt cho |
|-----------------|-------------|----------|--------------|
| `news` | Giấy Note | `styles/math-news.yaml` | Mọi cấp, bài đại số, đề thi — cần layout rõ ràng |
| `detective` | Thám Tử | `styles/math-detective.yaml` | Bài logic, chứng minh, tìm ẩn, nhiều bước suy luận |
| `neon` | Neon Lab | `styles/math-neon.yaml` | THPT, Olympic, nhiều công thức, hình học không gian |
| `chalkboard` | Bảng Phấn | `styles/math-chalkboard.yaml` | Mọi cấp, thân thiện, hình học, đại số cơ bản |
| `notebook` | Vở Ô Ly | `styles/math-notebook.yaml` | Tiểu học, THCS, bài đời sống, phân số, số học |
| `manipulatives` | Đồ Vật Trực Quan | `styles/math-manipulatives.yaml` | Tiểu học; bài đếm, chia nhóm, tỉ lệ, đồ vật cụ thể |

Kịch bản cũ không khai báo `visualConcept` dùng style mặc định `clean-professional`.
Không tự thay concept của video đã tạo.

---

## 2. Khi nào hỏi người dùng

Hỏi **sau** khi đã:
1. Xác định lớp (`selectedGrade`)
2. Chọn `solutionMode`
3. Giải và audit xong
4. Hiển thị Creator Review

Hỏi **trước** khi viết kịch bản hoặc gọi TTS/render.

Dùng `AskUserQuestion` (Claude Code) hoặc `request_user_input_async` (Codex):

> **Bạn muốn video trông theo phong cách nào?**
>
> - 📄 **Giấy Note** — sạch, rõ ràng, dễ theo dõi
> - 🔍 **Thám Tử** — hồ sơ bí ẩn, đường nối manh mối
> - 💡 **Neon Lab** — futuristic, nhiều công thức
> - 🖊️ **Bảng Phấn** — bảng đen phấn trắng, cổ điển
> - 📓 **Vở Ô Ly** — giấy học trò, thân quen
> - 🧩 **Đồ Vật Trực Quan** — đồ vật màu sắc, phù hợp bài đếm

Nếu môi trường không hỗ trợ lựa chọn bấm, liệt kê bằng văn bản và chờ.
Không tự mặc định concept khi chưa có câu trả lời.

---

## 3. Sau khi người dùng chọn

### 3a. Ghi vào script

```json
{
  "metadata": {
    "visualConcept": "chalkboard"
  }
}
```

### 3b. Load playbook tương ứng

```python
from lib.pipeline_loader import load_playbook
playbook = load_playbook(f"styles/math-{visual_concept}.yaml")
```

Dùng `playbook.visual_language.color_palette` và `playbook.math_scene_defaults`
khi khai báo màu sắc, background, motion cho từng scene.

### 3c. Áp dụng vào scene types

Các field Remotion nhận từ playbook:

| Playbook field | Remotion field |
|---|---|
| `math_scene_defaults.math_step.background` | `cut.backgroundOverlay` hoặc `cut.color` |
| `visual_language.color_palette.equation_highlight` | màu highlight KaTeX |
| `motion.entrance` | animation style của scene |
| `motion.pacing_rules` | `in_seconds` / `out_seconds` |
| `typography.equation.size_multiplier` | font size scale |

Với HyperFrames: map palette sang CSS variables; dùng `motion.animation_style`
để chọn GSAP easing.

---

## 4. Ràng buộc đặc biệt theo concept

### `manipulatives` — bắt buộc đọc thêm

Concept này yêu cầu `teachingAid` tùy chỉnh theo từng bài.
Đọc [`pedagogy-rules.md`](pedagogy-rules.md) mục 6 trước khi khai báo `templateData.teachingAid`.
Không tự suy số lượng vật từ LaTeX.

### `detective` + `neon` — đề tiếng Anh

Hai concept tối (nền `#1C1C1E`, `#0A0A0F`) cần kiểm tra contrast
đặc biệt khi hiển thị đề tiếng Anh (chữ trắng trên nền tối). Đảm bảo
`read-english` scene dùng `equation_box` với nền sáng để đề dễ đọc.

### `chalkboard` + `notebook` — animation write

Hai concept này có `write_animation: true` và `slide_up: true`.
Tốc độ animation phải khớp lời đọc thực tế — không cố định giây.
Kiểm tra bằng audio thật trước render cuối.

---

## 5. Chỉ đổi concept không cần audit lại

`visualConcept` chỉ ảnh hưởng màu sắc và animation — không thay đổi
`voiceText`, công thức hay lời giải. Nếu chỉ đổi concept (không sửa nội dung):
- Audio cũ vẫn dùng được.
- Audit cũ vẫn còn hiệu lực.
- Chỉ cần re-render composition.

Nếu sửa `templateData.objects` hoặc `teachingAid` → phải audit lại.

---

## 6. Tham chiếu liên quan

- Playbook files: `styles/math-*.yaml`
- TeachingAid design: [`pedagogy-rules.md`](pedagogy-rules.md) mục 6
- Phase sequence: [`script-director.md`](script-director.md)
- Render hai video: [`compose-director.md`](compose-director.md)
