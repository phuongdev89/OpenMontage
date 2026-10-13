#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
PORT="${PROMPT_CHAT_PORT:-4760}"
HOST="${PROMPT_CHAT_HOST:-0.0.0.0}"

PY_BIN="python3"
if [[ -x .venv/bin/python ]]; then
    PY_BIN=".venv/bin/python"
fi

LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")

echo "=========================================================="
echo "🎬 Video Prompt Chat đang chạy (hỗ trợ SSE):"
echo " - Cục bộ:       http://localhost:${PORT}"
echo " - Mạng nội bộ:  http://${LAN_IP}:${PORT}"
echo "=========================================================="

# Persist a detached server so later invocations can restart it by PID.
"$PY_BIN" - "$PORT" "$HOST" "$@" <<'PY'
from pathlib import Path
import fcntl
import os
import signal
import subprocess
import sys
import time
import urllib.request

port, host = sys.argv[1:3]
if not port.isdigit() or not 1 <= int(port) <= 65535:
    sys.exit("Prompt Chat: invalid PROMPT_CHAT_PORT")
cache = Path(".cache")
cache.mkdir(exist_ok=True)
suffix = "" if port == "4760" else f"-{port}"
pid_path = cache / f"prompt_chat{suffix}.pid"
log_path = cache / f"prompt_chat{suffix}.log"
lock = (cache / f"prompt_chat{suffix}.lock").open("a")
try:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    sys.exit("Prompt Chat: another launcher is already starting/restarting this port")

def owned_process(pid):
    try:
        proc = Path(f"/proc/{pid}")
        args = (proc / "cmdline").read_bytes().split(b"\0")
        return (pid > 1 and b"prompt_chat.server:app" in args and b"--port" in args
                and args[args.index(b"--port") + 1] == port.encode()
                and Path(os.readlink(proc / "cwd")).resolve() == Path.cwd().resolve())
    except (ValueError, OSError, IndexError):
        return False

def alive(pid):
    try:
        # A dead child may remain as a zombie until its parent reaps it.
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0] != "Z"
    except OSError:
        return False

try:
    saved_pid = int(pid_path.read_text().strip())
except (ValueError, OSError):
    saved_pid = None
targets = {saved_pid} if saved_pid is not None and owned_process(saved_pid) else set()
# Recover a server launched before PID tracking was introduced.
sockets = set()
for table in ("/proc/net/tcp", "/proc/net/tcp6"):
    for line in Path(table).read_text().splitlines()[1:]:
        fields = line.split()
        if int(fields[1].split(":")[1], 16) == int(port) and fields[3] == "0A":
            sockets.add(f"socket:[{fields[9]}]")
listeners = set()
if sockets:
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if any(os.readlink(fd) in sockets for fd in (proc / "fd").iterdir()):
                listeners.add(int(proc.name))
        except OSError:
            continue
    if not listeners or any(not owned_process(pid) for pid in listeners):
        sys.exit(f"Prompt Chat: port {port} belongs to an unverified process; restart aborted")
    targets.update(listeners)
if targets:
    print("Prompt Chat already running. Restarting...", flush=True)
    for pid in targets:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except PermissionError:
            sys.exit(f"Prompt Chat: cannot stop PID {pid}: permission denied")
    for _ in range(80):
        if not any(alive(pid) for pid in targets):
            break
        time.sleep(0.25)
    else:
        sys.exit("Prompt Chat: server did not stop within 20 seconds; restart aborted")
pid_path.unlink(missing_ok=True)
with log_path.open("ab", buffering=0) as log:
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "prompt_chat.server:app", "--host", host,
         "--port", port, *sys.argv[3:]], stdin=subprocess.DEVNULL, stdout=log,
        stderr=log, start_new_session=True,
    )
pid_path.write_text(str(process.pid) + "\n")
probe_host = "127.0.0.1" if host in {"0.0.0.0", "localhost"} else host
if ":" in probe_host:
    probe_host = "[::1]" if probe_host == "::" else f"[{probe_host}]"
url = f"http://{probe_host}:{port}"
for _ in range(120):
    if process.poll() is not None:
        pid_path.unlink(missing_ok=True)
        sys.exit(f"Prompt Chat failed to start. See {log_path.resolve()}")
    try:
        with urllib.request.urlopen(url + "/api/conversations", timeout=1) as response:
            if response.status == 200:
                print(f"Prompt Chat running in background (PID {process.pid}): {url}")
                print(f"PID: {pid_path.resolve()}\nLog: {log_path.resolve()}")
                break
    except Exception:
        pass
    time.sleep(0.25)
else:
    sys.exit(f"Prompt Chat startup not confirmed (PID {process.pid}). See {log_path.resolve()}")
PY
