"""Backlot CLI.

    python -m backlot open [project-id]   # start server if needed, open browser
    python -m backlot serve [--port N]    # run the server in the foreground

``open`` is idempotent and non-fatal by design: agents call it at pipeline
initialization and must continue the production even if it fails.

On Windows ``serve`` also shows a tray icon (left-click opens the board,
right-click offers restart/quit) — see ``backlot.tray``.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import urllib.request
import webbrowser

from backlot import DEFAULT_PORT


def _port() -> int:
    try:
        return int(os.environ.get("BACKLOT_PORT", DEFAULT_PORT))
    except ValueError:
        return DEFAULT_PORT


def _server_alive(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False


def _spawn_server(port: int) -> None:
    """Start the server as a detached background process."""
    cmd = [sys.executable, "-m", "backlot", "serve", "--port", str(port)]
    kwargs: dict = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "stdin": subprocess.DEVNULL,
    }
    if os.name == "nt":
        kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
        )
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(cmd, **kwargs)


def _wait_for_port_free(port: int, timeout: float = 12.0, poll: float = 0.25) -> None:
    """Block while the port still answers, for a restart replacing this server.

    A replacement ``serve`` process races the predecessor's shutdown for the
    port; waiting here (instead of failing to bind) makes tray Restart seamless.
    Two consecutive failed health checks are required so a single slow response
    is not mistaken for the predecessor being gone.
    """
    if not _server_alive(port):
        return
    deadline = time.time() + timeout
    misses = 0
    while time.time() < deadline:
        if _server_alive(port):
            misses = 0
        else:
            misses += 1
            if misses >= 2:
                time.sleep(0.2)  # let the listener finish closing
                return
        time.sleep(poll)


def restart_server(port: int, shutdown) -> None:
    """Spawn a replacement server, then signal this one to stop.

    The replacement must be spawned before shutting down: after this process
    exits there is nobody left to restart it.
    """
    _spawn_server(port)
    shutdown()


def cmd_open(project_id: str | None) -> int:
    port = _port()
    if not _server_alive(port):
        try:
            _spawn_server(port)
        except Exception as exc:
            print(f"backlot: could not start server ({exc}) — continuing without the board")
            return 1
        deadline = time.time() + 15
        while time.time() < deadline:
            if _server_alive(port):
                break
            time.sleep(0.4)
        else:
            print("backlot: server did not come up in time — continuing without the board")
            return 1
    url = f"http://127.0.0.1:{port}/"
    if project_id:
        url = f"http://127.0.0.1:{port}/p/{project_id}"
    try:
        webbrowser.open(url)
    except Exception:
        pass
    print(f"backlot: {url}")
    return 0


def cmd_serve(port: int) -> int:
    import threading

    import uvicorn

    from backlot import tray

    _wait_for_port_free(port)
    config = uvicorn.Config(
        "backlot.server:app",
        host="127.0.0.1",
        port=port,
        log_level="warning",
        # A browser holding an SSE stream would otherwise stall shutdown forever.
        timeout_graceful_shutdown=3,
    )
    server = uvicorn.Server(config)
    watchdog: threading.Timer | None = None

    def _shutdown() -> None:
        nonlocal watchdog
        # Last resort: if graceful shutdown wedges, exit hard so a tray
        # Restart/Quit always lands instead of leaving a zombie holder.
        watchdog = threading.Timer(10.0, os._exit, args=(0,))
        watchdog.daemon = True
        watchdog.start()
        server.should_exit = True

    tray_icon = tray.start_tray(
        port=port,
        on_restart=lambda: restart_server(port, _shutdown),
        on_quit=_shutdown,
    )
    try:
        server.run()
    finally:
        if watchdog is not None:
            watchdog.cancel()
        if tray_icon is not None:
            tray_icon.stop()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="backlot", description=__doc__)
    sub = parser.add_subparsers(dest="command")

    p_open = sub.add_parser("open", help="open the board in the browser (starts server if needed)")
    p_open.add_argument("project_id", nargs="?", default=None)

    p_serve = sub.add_parser("serve", help="run the Backlot server in the foreground")
    p_serve.add_argument("--port", type=int, default=_port())

    args = parser.parse_args(argv)
    if args.command == "open":
        return cmd_open(args.project_id)
    if args.command == "serve":
        return cmd_serve(args.port)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
