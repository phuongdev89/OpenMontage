@echo off
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (
    set "PY_BIN=.venv\Scripts\python.exe"
) else (
    set "PY_BIN=python"
)
set PORT=4760
if defined PROMPT_CHAT_PORT set PORT=%PROMPT_CHAT_PORT%

echo ==========================================================
echo Video Prompt Chat dang chay (ho tro SSE):
echo  - Cuc bo:       http://localhost:%PORT%
echo  - Mang noi bo:  Kiem tra ipconfig de lay IPv4
echo ==========================================================

start http://localhost:%PORT%
%PY_BIN% -m uvicorn prompt_chat.server:app --host 0.0.0.0 --port %PORT%
