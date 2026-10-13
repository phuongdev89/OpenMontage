"""Create disposable project downloads without touching production files."""
import os
import tempfile
import zipfile
from pathlib import Path


EXCLUDED_DIRS = {"node_modules", ".git", "__pycache__", ".cache", ".venv", "venv"}


def build_archive(project: Path) -> Path:
    project = project.resolve()
    fd, name = tempfile.mkstemp(prefix="backlot-project-", suffix=".zip")
    os.close(fd)
    archive = Path(name)
    try:
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as output:
            for directory, dirs, files in os.walk(project, followlinks=False):
                base = Path(directory)
                dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not (base / d).is_symlink()
                           and (base / d).resolve().is_relative_to(project)]
                for name in sorted(files):
                    source = base / name
                    if name == ".env" or name.startswith(".env.") and name != ".env.example":
                        continue
                    if source.is_symlink() or not source.resolve().is_relative_to(project):
                        continue
                    output.write(source, (Path(project.name) / source.relative_to(project)).as_posix())
        return archive
    except BaseException:
        archive.unlink(missing_ok=True)
        raise
