# Math Video — Visual Concepts

> **Scope:** Chọn và áp dụng toàn bộ visual concept hiện có cho video toán (hiện có 6).
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
| `news` | Bản tin Thời sự | `styles/math-news.yaml` | Mọi cấp, bài đại số, đề thi — cần layout rõ ràng |
| `detective` | Thám Tử | `styles/math-detective.yaml` | Bài logic, chứng minh, tìm ẩn, nhiều bước suy luận |
| `neon` | Neon Lab | `styles/math-neon.yaml` | THPT, Olympic, nhiều công thức, hình học không gian |
| `chalkboard` | Bảng Phấn | `styles/math-chalkboard.yaml` | Mọi cấp, thân thiện, hình học, đại số cơ bản |
| `notebook` | Vở Ô Ly | `styles/math-notebook.yaml` | Tiểu học, THCS, bài đời sống, phân số, số học |
| `manipulatives` | Đồ Vật Trực Quan | `styles/math-manipulatives.yaml` | Tiểu học; bài đếm, chia nhóm, tỉ lệ, đồ vật cụ thể |

Kịch bản cũ không khai báo `visualConcept` dùng style mặc định `clean-professional`.
Không tự thay concept của video đã tạo.

---

## 2. Khi nào hỏi người dùng

Áp dụng mode đã lưu theo `skills/meta/approval-mode.md` trước: full_auto tự chọn
concept từ catalog đầy đủ, ghi lý do và không dừng hỏi; concept_only hỏi chọn/duyệt
concept rồi tự động những bước khác; manual_all theo quy trình dưới đây và vẫn
chờ duyệt từng stage. Mode ưu tiên hơn các câu chờ mặc định bên dưới.

Hỏi **sau** khi đã:
1. Xác định lớp (`selectedGrade`)
2. Chọn `solutionMode`
3. Giải và audit xong
4. Hiển thị Creator Review

Hỏi **trước** khi viết kịch bản hoặc gọi TTS/render.

Dùng `AskUserQuestion` (Claude Code) hoặc `request_user_input_async` (Codex):

Đọc `skills/meta/concept-selection.md` trước khi hỏi. Đối chiếu reference này và
`styles/math-*.yaml`; hiện **toàn bộ** concept có sẵn, kể cả mục không được
khuyên dùng cho bài/lớp hiện tại. Không rút còn 2–3 rồi buộc người dùng tự nhập
các mục còn lại. Bổ sung concept hỗ trợ mới vào danh sách khi catalog thay đổi.

Ở Codex, truyền toàn bộ danh sách vào `options` của **một** câu hỏi:

```json
{"questions": [{
  "title": "Bạn muốn video trông theo phong cách nào?",
  "options": [
    "Bản tin Thời sự — headline, bản tin và tường thuật",
    "Thám Tử — hồ sơ bí ẩn, đường nối manh mối",
    "Neon Lab — ánh sáng neon, phòng thí nghiệm tương lai",
    "Bảng Phấn — bảng xanh đen, chữ phấn cổ điển",
    "Vở Ô Ly — giấy học trò, nét viết thân quen",
    "Đồ Vật Trực Quan — đồ vật màu sắc, đếm và chia nhóm"
  ]
}]}
```

Có thể đánh dấu mục khuyên dùng nhưng không xóa các mục khác. Ô concept riêng
chỉ là bổ sung tùy chọn; nếu host giới hạn options, hiện đầy đủ danh sách theo
nhóm/đánh số và để người dùng chọn mục đã hiển thị.

> **Bạn muốn video trông theo phong cách nào?**
>
> - 📰 **Bản tin Thời sự** — headline, bản tin và tường thuật vụ việc
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

### 3d. Hook theo visual concept

Sau khi concept được chọn, hook phải mang đúng chất liệu và cách gọi khán giả
của concept đó. Giữ nguyên quan hệ toán học và đơn vị của đề; không tự thêm
đơn vị, kết quả, giới hạn thời gian hoặc sự kiện không có trong brief. Lời
thoại do agent viết không được tự xưng hay dùng ngôi thứ nhất theo
[`voice-text-rules.md`](voice-text-rules.md). Chỉ dẫn âm thanh trong ngoặc là
chỉ dẫn sản xuất, không đưa vào `voiceText` trừ khi cần đọc thành lời.

Các ví dụ dưới đây cùng dựa trên AMO lớp 2 năm 2022: một số sau khi nhân với
10 lớn hơn số ban đầu 63 đơn vị. Đây là mẫu để hiểu cách đổi sắc thái theo
concept, không phải câu chữ cố định cho bài khác.

#### `detective` — Thám tử / Phá án

*(Tiếng máy đánh chữ lách cách; con dấu "TOP SECRET" đóng xuống.)*

> Hồ sơ mật kỳ thi Olympic AMO vừa ghi nhận một manh mối kỳ lạ: một con số bí
> ẩn sau khi nhân với mười bỗng lớn hơn chính nó đúng sáu mươi ba đơn vị.
> Chào các thám tử nhí! Liệu các bạn có bẻ khóa được con số này trước khi hồ
> sơ khép lại? Cùng giải mã ngay!

#### `chalkboard` — Bảng đen phấn trắng

*(Tiếng gõ phấn cộc cộc trên bảng.)*

> Một câu đố thoạt nhìn tưởng hóc búa trong đề thi AMO: nhân một số với mười,
> kết quả vọt lên hơn số ban đầu sáu mươi ba đơn vị. Chào các bạn học sinh
> đến với lớp học giải đố! Nhìn lên bảng xem, phương pháp sơ đồ đoạn thẳng sẽ
> giúp giải bài này nhanh đến mức nào!

#### `manipulatives` — Đồ chơi tư duy / Khối xếp hình

*(Tiếng khối gỗ hoặc LEGO va vào nhau lách cách.)*

> Trên sơ đồ khối, thanh dài gấp mười lần thanh ban đầu nhưng chỉ hơn đúng
> sáu mươi ba đơn vị! Chào các bạn nhỏ yêu toán tư duy! Hãy quan sát các mảnh
> ghép xem con số bí ẩn là bao nhiêu nhé?

#### `neon` — Neon / Cyber Glow

*(Âm thanh radar quét; hiệu ứng laser kích hoạt.)*

> Cảnh báo thử thách cấp độ Olympic: hệ thống nhân mười vừa tạo ra một con số
> vượt giá trị ban đầu đúng sáu mươi ba đơn vị. Chào các chiến binh toán
> học! Sẵn sàng bẻ khóa mật mã này chưa? Đếm ngược bắt đầu!

#### `notebook` — Sổ tay vẽ chì

*(Tiếng ngòi chì sột soạt vẽ trên mặt giấy.)*

> Trang sổ tay hôm nay có một câu đố Olympic cực kỳ tinh quái: một số nhân
> với mười thì nhảy vọt thêm sáu mươi ba đơn vị. Chào các bạn nhỏ! Chuẩn bị
> bút chì và thước kẻ, cùng vẽ nhanh một sơ đồ để tìm ra con số bí ẩn này nhé!

#### `news` — Bản tin Thời sự

*(Nhạc hiệu thời sự dồn dập; headline đỏ chạy ngang.)*

> Bản tin nóng kỳ thi Olympic AMO: một con số sau khi nhân với mười vừa được
> phát hiện vượt giá trị ban đầu đúng sáu mươi ba đơn vị! Chào các bạn nhỏ
> đến với bản tin hôm nay. Manh mối vụ việc sẽ được làm sáng tỏ ngay sau đây!

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
