"""Filesystem notifications must survive a missing native watcher."""
import asyncio
import sys
from contextlib import suppress

from backlot import server


def test_realtime_without_watchfiles(tmp_path, monkeypatch):
    root = tmp_path / "projects"
    monkeypatch.setattr(server, "PROJECTS_DIR", root)
    monkeypatch.setattr(server, "RECONCILE_SECONDS", 0.05, raising=False)
    monkeypatch.setitem(sys.modules, "watchfiles", None)
    monkeypatch.setattr(server, "hub", server.ChangeHub())
    monkeypatch.setattr(server, "_summary_cache", {"Film": {"title": "old"}})

    async def run():
        q = server.hub.subscribe("Film")
        task = asyncio.create_task(server._watch_projects())
        try:
            await asyncio.sleep(0.1)
            project = root / "Film"
            project.mkdir(parents=True)
            content = project / "project.json"
            content.write_text('{"title":"first"}')
            assert await asyncio.wait_for(q.get(), 1) == "Film"
            assert "Film" not in server._summary_cache
            content.write_text('{"title":"second"}')
            assert await asyncio.wait_for(q.get(), 1) == "Film"
            content.unlink()
            assert await asyncio.wait_for(q.get(), 1) == "Film"
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    asyncio.run(run())


def test_project_change_preserves_case(tmp_path, monkeypatch):
    import os
    root = tmp_path / "projects"
    monkeypatch.setattr(server, "_PROJECTS_ROOT_STR", os.path.normcase(str(root)))
    assert server._project_of_change(str(root / "MyFilm" / "project.json")) == "MyFilm"
    assert server._project_of_change(str(tmp_path / "projects-other" / "Film")) is None


def test_native_resource_exhaustion_stops_retrying(tmp_path, monkeypatch, caplog):
    import types

    monkeypatch.setattr(server, "PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(server, "RECONCILE_SECONDS", 0.01)
    calls = []

    async def broken_watch(*args, **kwargs):
        calls.append(True)
        # watchfiles wraps OS errors in a Rust exception, not OSError.
        raise RuntimeError("Error creating recommended watcher: Too many open files (os error 24)")
        yield

    monkeypatch.setitem(sys.modules, "watchfiles", types.SimpleNamespace(awatch=broken_watch))

    async def run():
        task = asyncio.create_task(server._watch_native())
        try:
            await asyncio.sleep(0.06)
            assert task.done(), "Resource exhaustion must switch to reconciliation instead of retrying"
            await task
            assert len(calls) == 1
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    asyncio.run(run())
    assert "reconciliation" in caplog.text


def test_reconciliation_survives_native_failure(tmp_path, monkeypatch):
    root = tmp_path / "projects"
    project = root / "Film"
    project.mkdir(parents=True)
    content = project / "note.txt"
    content.write_text("before")
    monkeypatch.setattr(server, "PROJECTS_DIR", root)
    monkeypatch.setattr(server, "RECONCILE_SECONDS", 0.05)
    monkeypatch.setattr(server, "hub", server.ChangeHub())

    async def broken_watch(*args, **kwargs):
        raise OSError("simulated watch handle failure")
        yield  # async generator matching awatch

    import types
    monkeypatch.setitem(sys.modules, "watchfiles", types.SimpleNamespace(awatch=broken_watch))

    async def run():
        q = server.hub.subscribe("Film")
        task = asyncio.create_task(server._watch_projects())
        try:
            await asyncio.sleep(0.1)
            content.write_text("after")
            assert await asyncio.wait_for(q.get(), 1) == "Film"
            assert not task.done()
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
    asyncio.run(run())


def test_signatures_detect_replace_rename_and_ignore_noise(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "PROJECTS_DIR", tmp_path)
    project = tmp_path / "Film"
    project.mkdir()
    file = project / "note.txt"
    file.write_text("before")
    before = server._project_signatures()
    noise = project / "node_modules"
    noise.mkdir()
    (noise / "huge.js").write_text("noise")
    assert server._project_signatures() == before
    replacement = project / "replacement.txt"
    replacement.write_text("after")
    replacement.replace(file)
    after = server._project_signatures()
    assert after != before
    file.rename(project / "renamed.txt")
    assert server._project_signatures() != after


def test_reconciliation_recovers_from_initial_scan_failure(monkeypatch):
    import errno

    scans = []
    monkeypatch.setattr(server, "RECONCILE_SECONDS", 0.01)
    monkeypatch.setattr(server, "hub", server.ChangeHub())
    monkeypatch.setattr(server, "_summary_cache", {"Film": {"title": "stale"}})
    monkeypatch.setitem(sys.modules, "watchfiles", None)

    def scan():
        scans.append(True)
        if len(scans) == 1:
            raise OSError(errno.EMFILE, "Too many open files")
        return {"Film": ("updated",)}

    monkeypatch.setattr(server, "_project_signatures", scan)

    async def run():
        q = server.hub.subscribe("Film")
        task = asyncio.create_task(server._watch_projects())
        try:
            assert await asyncio.wait_for(q.get(), 0.5) == "Film"
            assert not task.done()
            assert "Film" not in server._summary_cache
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError, OSError):
                await task

    asyncio.run(run())
