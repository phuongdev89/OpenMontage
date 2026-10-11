# Export-Conversation Skill

Hỗ trợ Antigravity và Codex. CLI tự nhận agent hiện tại; chọn rõ bằng `--agent antigravity|codex`. Với Codex, dùng `-c THREAD_ID` hoặc `--source <rollout.jsonl>` khi cần phiên khác. Nội dung reasoning nội bộ không được xuất nếu transcript không chứa văn bản đó. Claude Desktop chưa được hỗ trợ.

Kỹ năng xuất và sao lưu toàn diện lịch sử hội thoại AI Coding Agent thành tệp **Markdown (`.md`)** hoặc **JSON (`.json`)**. 

Được thiết kế để lưu vết chính xác quá trình làm việc, bao gồm cả các tầng dữ liệu mà giao diện chat thông thường không hiển thị: **lời thoại 2 chiều, suy nghĩ (thinking/chain-of-thought), lịch sử thực thi lệnh terminal (`run_command`), tác vụ nền (`manage_task`, `schedule`), và toàn bộ hoạt động nội bộ của các Subagents**.

---

## 1. Cấu trúc Thư mục Skill

```
export-conversation/
├── README.md                      # Tài liệu hướng dẫn chi tiết
├── SKILL.md                       # Đặc tả kỹ năng và quy trình chuẩn cho AI Agent
└── scripts/
    └── export_conversation.py     # Script trích xuất CLI thuần Python (Standard Library Only)
```

---

## 2. Điểm nổi bật & Tính năng

- 🚀 **Zero Dependencies**: Sử dụng 100% Python Standard Library (`json`, `pathlib`, `argparse`, `re`...). Không cần `pip install` bất kỳ gói nào.
- 🔍 **Tự động nhận diện (Auto-Discovery)**: Tự tìm thư mục `brain/` trên Windows, macOS và Linux. Tự phát hiện phiên hội thoại đang hoạt động hoặc phiên mới nhất nếu không truyền ID.
- 🤖 **Bóc tách Subagent đệ quy**: Tự động phát hiện các subagent được gọi trong phiên (`invoke_subagent`), tìm file transcript tương ứng trong hệ thống và bóc tách toàn bộ lịch sử trao đổi, lệnh chạy nội bộ của subagent.
- 💻 **Lịch sử Lệnh Terminal Đầy Đủ**: Tổng hợp bảng lệnh, working directory, exit code, stdout, stderr và log tác vụ nền (`task-*.log`).
- 📝 **Markdown chuẩn GitHub**: Trình bày rõ ràng, hỗ trợ thẻ `<details>` có thể thu gọn cho Thinking và Tool Arguments, kèm bảng thống kê và timeline.
- 📊 **JSON chuẩn hóa**: Xuất dữ liệu có cấu trúc phục vụ phân tích tự động, benchmark, evaluation hoặc ingest vào vector DB / RAG.

---

## 3. Hướng dẫn Sử dụng CLI

### Cú pháp Cơ bản:
```bash
python skills/export-conversation/scripts/export_conversation.py [OPTIONS]
```

### Các ví dụ thông dụng:

#### 1. Xuất phiên hội thoại mới nhất ra thư mục `./.scratch/` (cả `.md` và `.json`):
```bash
python skills/export-conversation/scripts/export_conversation.py
```

#### 2. Xuất một Conversation ID cụ thể:
```bash
python skills/export-conversation/scripts/export_conversation.py -c 42d0427a-b6aa-49e7-9da3-d1aa0bfed8bd
```

#### 3. Chỉ xuất định dạng Markdown ra file chỉ định:
```bash
python skills/export-conversation/scripts/export_conversation.py -f md -o ./my-report.md
```

#### 4. Chỉ xuất định dạng JSON:
```bash
python skills/export-conversation/scripts/export_conversation.py -f json -o ./backup-session.json
```

#### 5. Xuất tài liệu Markdown gọn nhẹ (không kèm thinking):
```bash
python skills/export-conversation/scripts/export_conversation.py -f md --no-thinking
```

#### 6. Bỏ qua việc bóc tách subagents (chỉ lấy main agent):
```bash
python skills/export-conversation/scripts/export_conversation.py --no-subagents
```

---

## 4. Bảng Tham số CLI

| Cờ / Tham số | Mô tả |
| :--- | :--- |
| `-c`, `--conversation-id` | ID của phiên hội thoại (mặc định lấy phiên mới nhất trong `brain/`). |
| `-b`, `--brain-dir` | Đường dẫn tùy biến tới thư mục `brain/` nếu đặt ở nơi không tiêu chuẩn. |
| `-f`, `--format` | Lựa chọn định dạng: `md`, `json`, hoặc `all` (mặc định: `all`). |
| `-o`, `--output` | Đường dẫn tệp hoặc thư mục lưu file kết quả. |
| `--no-thinking` | Không đưa phần suy nghĩ của model vào file Markdown. |
| `--no-subagents` | Không quét đệ quy vào transcript của subagents. |
| `-h`, `--help` | Hiển thị bảng trợ giúp. |

---

## 5. Cấu trúc Dữ liệu JSON Đầu ra

File JSON xuất ra tuân theo schema rõ ràng:
- `conversation_id`: ID phiên làm việc.
- `metadata`: Thống kê tổng số bước, số lượt thoại, số lệnh, số task, số subagent, thời gian bắt đầu/kết thúc.
- `dialogue`: Mảng các lượt thoại (speaker: `user` hoặc `assistant`, timestamp, thinking, response, tool_calls).
- `command_history`: Mảng toàn bộ lệnh terminal đã chạy (step_index, cwd, command, exit_code, output).
- `task_history`: Mảng các background task và schedule timer/cron kèm log nội bộ.
- `subagents`: Mảng các subagent kèm metadata, prompt được giao, và toàn bộ dữ liệu thực thi bên trong subagent đó.
- `timeline`: Danh sách tuần tự theo thời gian của tất cả các sự kiện đã diễn ra.

---

## 6. Bảo mật & An toàn Dữ liệu

> [!CAUTION]
> File export có thể chứa các giá trị biến môi trường, API keys hoặc thông tin nhạy cảm đã xuất hiện trong log terminal stdout/stderr hoặc câu lệnh.  
> Hãy kiểm tra nội dung file export trước khi chia sẻ ra môi trường công cộng hoặc commit lên GitHub.
