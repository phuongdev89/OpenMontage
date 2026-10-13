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
import subprocess
import sys
import time
import urllib.request

url = "http://127.0.0.1:4751"

def healthy():
    try:
        with urllib.request.urlopen(url + "/api/health", timeout=1) as response:
            return response.status == 200
    except Exception:
        return False

if healthy():
    print(f"Backlot already running: {url}")
    sys.exit(0)

cache = Path(".cache")
cache.mkdir(exist_ok=True)
log_path = cache / "backlot.log"
with log_path.open("ab", buffering=0) as log:
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backlot.server:app",
         "--host", "0.0.0.0", "--port", "4751"],
        stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True,
    )
for _ in range(40):
    if process.poll() is not None:
        sys.exit(f"Backlot failed to start. See {log_path.resolve()}")
    if healthy():
        print(f"Backlot running in background (PID {process.pid}): {url}")
        print(f"Log: {log_path.resolve()}")
        break
    time.sleep(0.25)
else:
    sys.exit(f"Backlot startup not confirmed (PID {process.pid}). See {log_path.resolve()}")
PY
