# Kế hoạch triển khai Web Service Chat Prompt Video

## 1. Mục tiêu & Nguyên tắc thiết kế
- Dịch vụ web chat độc lập hoàn toàn với `backlot`, chạy cổng riêng (mặc định `4760`, cấu hình qua `PROMPT_CHAT_PORT`).
- Dùng cấu hình AI có sẵn trong `.env` (`AI_CHAT_URL`, `AI_CHAT_KEY`, `AI_CHAT_MODEL`).
- AI đóng vai trò Video Prompt Engineer: chỉ xuất prompt tạo video trong codeblock, không chào hỏi, không tán gẫu.
- Giao diện: Sidebar bên trái quản lý danh sách hội thoại + nút tạo mới, khung chat chính có nút copy nhanh cho mỗi prompt.
- Triết lý tối giản (YAGNI): Không thêm dependency mới (dùng sẵn FastAPI, Uvicorn, sqlite3 stdlib, Vanilla HTML/CSS/JS).

## 2. Cấu trúc file mới
- `prompt_chat/server.py`: Backend FastAPI
  - Quản lý SQLite database (`prompt_chat/data/chat.db`).
  - Gọi LLM qua OpenAI-compatible API (`AI_CHAT_URL`).
  - System prompt cố định ép AI chỉ trả về video prompt trong textblock.
  - REST API: Tạo/xem/xóa hội thoại, gửi tin nhắn và nhận phản hồi (hỗ trợ streaming SSE hoặc JSON).
- `prompt_chat/index.html`: Frontend Single-Page thuần
  - Sidebar bên trái: Danh sách cuộc trò chuyện, thời gian, nút xóa, nút "+ Hội thoại mới".
  - Khung chat chính: Lịch sử tin nhắn, input box tự co giãn (Enter gửi, Shift+Enter xuống dòng).
  - Khối tin nhắn AI: Luôn hiển thị trong textblock/codeblock với nút "Copy" 1 chạm.
  - Giao diện Dark mode hiện đại, gọn gàng.
- `prompt_chat.sh` & `prompt_chat.bat`: Script khởi chạy nhanh service.

## 3. Các bước triển khai
1. Tạo thư mục `prompt_chat/` và `prompt_chat/data/`.
2. Viết `prompt_chat/server.py` với schema SQLite tối giản (bảng `conversations` và `messages`), service gọi LLM từ `.env`.
3. Viết `prompt_chat/index.html` tích hợp UI sidebar + chat + copy button.
4. Tạo script khởi động `prompt_chat.sh` / `prompt_chat.bat`.
5. Test khởi động dịch vụ, gửi nhận prompt mẫu và kiểm tra chức năng copy, lưu trữ hội thoại.