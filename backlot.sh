#!/usr/bin/env bash
set -euo pipefail

# Resolve the checkout even when launched from another working directory.
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ! -x .venv/bin/python ]]; then
    echo "Backlot: missing .venv/bin/python. Create the Ubuntu virtual environment first." >&2
    exit 1
fi

# A new session and redirected standard streams survive terminal closure.
.venv/bin/python - <<'PY'
from pathlib import Path
import os
import signal
import subprocess
import sys
import time
import urllib.request

url = "http://127.0.0.1:4751"
pid_path = Path(".backlot/backlot.pid")
pid_path.parent.mkdir(exist_ok=True)

def saved_backlot_pid():
    try:
        pid = int(pid_path.read_text().strip())
        proc = Path(f"/proc/{pid}")
        args = (proc / "cmdline").read_bytes().split(b"\0")
        if (pid > 1 and b"backlot.server:app" in args and b"--port" in args
                and args[args.index(b"--port") + 1] == b"4751"
                and Path(os.readlink(proc / "cwd")).resolve() == Path.cwd().resolve()):
            return pid
    except (ValueError, OSError, IndexError):
        pass
    return None

def healthy():
    try:
        with urllib.request.urlopen(url + "/api/health", timeout=1) as response:
            return response.status == 200
    except Exception:
        return False

saved_pid = saved_backlot_pid()
if saved_pid is not None or healthy():
    # Identify the listener rather than killing every uvicorn/Backlot process.
    sockets = set()
    for table in ("/proc/net/tcp", "/proc/net/tcp6"):
        for line in Path(table).read_text().splitlines()[1:]:
            fields = line.split()
            if int(fields[1].split(":")[1], 16) == 4751 and fields[3] == "0A":
                sockets.add(f"socket:[{fields[9]}]")
    listeners = {saved_pid} if saved_pid is not None else set()
    for proc in ([] if saved_pid is not None else Path("/proc").iterdir()):
        if not proc.name.isdigit():
            continue
        try:
            if any(os.readlink(fd) in sockets for fd in (proc / "fd").iterdir()):
                listeners.add(int(proc.name))
        except (OSError, PermissionError):
            continue
    if not listeners:
        sys.exit("Backlot is running, but its listener PID could not be identified. Restart aborted.")
    for pid in listeners:
        try:
            args = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
        except OSError:
            sys.exit(f"Cannot verify listener PID {pid}. Restart aborted.")
        if (b"backlot.server:app" not in args
                or Path(os.readlink(Path(f"/proc/{pid}/cwd"))).resolve() != Path.cwd().resolve()):
            sys.exit(f"Port 4751 belongs to an unrecognized process (PID {pid}). Restart aborted.")
    print(f"Backlot already running: {url}. Restarting...", flush=True)
    for pid in listeners:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except PermissionError:
            sys.exit(f"Cannot stop Backlot PID {pid}: permission denied.")
    for _ in range(80):
        if all(not Path(f"/proc/{pid}").exists() for pid in listeners):
            break
        time.sleep(0.25)
    else:
        sys.exit("Backlot did not stop within 20 seconds. Restart aborted.")
    pid_path.unlink(missing_ok=True)

cache = Path(".cache")
cache.mkdir(exist_ok=True)
log_path = cache / "backlot.log"
with log_path.open("ab", buffering=0) as log:
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backlot.server:app",
         "--host", "0.0.0.0", "--port", "4751"],
        stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True,
    )
pid_path.write_text(str(process.pid) + "\n")
for _ in range(40):
    if process.poll() is not None:
        pid_path.unlink(missing_ok=True)
        sys.exit(f"Backlot failed to start. See {log_path.resolve()}")
    if healthy():
        print(f"Backlot running in background (PID {process.pid}): {url}")
        print(f"Log: {log_path.resolve()}")
        break
    time.sleep(0.25)
else:
    sys.exit(f"Backlot startup not confirmed (PID {process.pid}). See {log_path.resolve()}")
PY
