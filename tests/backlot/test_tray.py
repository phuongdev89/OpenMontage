"""Unit tests for the Backlot tray icon (backlot/tray.py) and the serve-side
restart helpers it relies on (backlot/__main__.py)."""

import io
import sys

import pytest
from PIL import Image

from backlot import __main__ as main_mod
from backlot import tray as tray_mod


def test_icon_bytes_valid_ico():
    data = tray_mod._icon_bytes()
    assert data[:4] == b"\x00\x00\x01\x00"  # ICO magic: reserved + type=icon
    img = Image.open(io.BytesIO(data))
    assert img.size[0] >= 16


def test_enabled_default_on_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delenv("BACKLOT_TRAY", raising=False)
    assert tray_mod._enabled() is True


@pytest.mark.parametrize("flag", ["0", "false", "off", "no"])
def test_enabled_env_kill_switch(monkeypatch, flag):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("BACKLOT_TRAY", flag)
    assert tray_mod._enabled() is False


def test_enabled_unsupported_platform(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("BACKLOT_TRAY", raising=False)
    assert tray_mod._enabled() is False


def test_start_tray_disabled_returns_none(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("BACKLOT_TRAY", "0")
    handle = tray_mod.start_tray(port=1, on_restart=lambda: None, on_quit=lambda: None)
    assert handle is None


def test_start_tray_non_windows_returns_none(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("BACKLOT_TRAY", raising=False)
    handle = tray_mod.start_tray(port=1, on_restart=lambda: None, on_quit=lambda: None)
    assert handle is None


def test_wait_for_port_free_returns_immediately_when_free(monkeypatch):
    monkeypatch.setattr(main_mod, "_server_alive", lambda port: False)
    main_mod._wait_for_port_free(9999, timeout=1.0, poll=0.01)  # must not sleep/wait


def test_wait_for_port_free_returns_after_two_consecutive_misses(monkeypatch):
    calls = {"n": 0}

    def flaky_alive(port):
        calls["n"] += 1
        # busy at first, one transient miss, busy again, then gone for good
        results = [True, False, True, False, False]
        return results[min(calls["n"] - 1, 4)]

    monkeypatch.setattr(main_mod, "_server_alive", flaky_alive)
    main_mod._wait_for_port_free(9999, timeout=5.0, poll=0.01)
    assert calls["n"] >= 5  # the lone miss must not end the wait


def test_wait_for_port_free_times_out(monkeypatch):
    monkeypatch.setattr(main_mod, "_server_alive", lambda port: True)
    main_mod._wait_for_port_free(9999, timeout=0.05, poll=0.02)  # returns, no raise


def test_restart_server_spawns_before_shutdown(monkeypatch):
    order = []
    monkeypatch.setattr(main_mod, "_spawn_server", lambda port: order.append("spawn"))
    shutdown = lambda: order.append("shutdown")  # noqa: E731 - local alias keeps the list readable
    main_mod.restart_server(4750, shutdown)
    assert order == ["spawn", "shutdown"]
