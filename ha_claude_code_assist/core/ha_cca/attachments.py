"""Files the user attaches to a message, kept in the session's working directory.

A file is saved as it was sent (no conversion, no size limit of ours: Home Assistant's Ingress
lets through at most 16 MiB). The message tells Claude where it is with one line per file,
`[Attached file: <path>]`, and Claude Code opens it with Read. That line is our own convention:
`split_attachments` finds it again in the transcript, so the panel shows the file instead.
"""

from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path

FOLDER = "attachments"
MAX_NAME_LENGTH = 120
# The images the panel shows as pictures; other files are listed by name.
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
               ".webp": "image/webp"}
_LINE = re.compile(r"^\[Attached file: (?P<path>/[^\]\n]+)\]$")


def folder(workdir: Path) -> Path:
    return workdir / FOLDER


def safe_name(name: str) -> str:
    """The file's own name, made safe to write: no folders, no control characters, no leading
    dots (hidden files), at most MAX_NAME_LENGTH characters with the extension kept."""
    name = re.split(r"[/\\]", name)[-1]
    name = "".join(c for c in name if unicodedata.category(c)[0] != "C").strip().lstrip(".").strip()
    if not name:
        return "file"
    stem, suffix = os.path.splitext(name)
    if len(name) > MAX_NAME_LENGTH:
        suffix = suffix[:16]
        name = stem[: MAX_NAME_LENGTH - len(suffix)] + suffix
    return name


def save(workdir: Path, name: str, data: bytes) -> str:
    """Saves the bytes under a free name and returns that name: a second "photo.jpg" becomes
    "photo (2).jpg", so a file is never overwritten."""
    target_dir = folder(workdir)
    target_dir.mkdir(parents=True, exist_ok=True)
    name = safe_name(name)
    stem, suffix = os.path.splitext(name)
    candidate, n = name, 1
    while True:
        try:
            # Exclusive creation: two uploads with the same name never write the same file.
            with open(target_dir / candidate, "xb") as file:
                file.write(data)
            return candidate
        except FileExistsError:
            n += 1
            candidate = f"{stem} ({n}){suffix}"


def path(workdir: Path, name: str) -> Path | None:
    """The saved file with this name, or None when there is none (or the name is not one)."""
    if name != safe_name(name):
        return None
    candidate = folder(workdir) / name
    return candidate if candidate.is_file() and not candidate.is_symlink() else None


def message(text: str, workdir: Path, names: list[str]) -> str:
    """The message Claude gets: the user's text, then one line per attached file."""
    lines = [f"[Attached file: {folder(workdir) / name}]" for name in names]
    return "\n\n".join(part for part in (text.strip(), "\n".join(lines)) if part)


def split_attachments(text: str, workdir: Path) -> tuple[str, list[str]]:
    """The user's text and the names of the files attached to it, from a message written by
    `message`. Only lines at the end, pointing into this session's attachments, count."""
    lines = text.rstrip().split("\n")
    names: list[str] = []
    attachments = folder(workdir)
    while lines:
        match = _LINE.match(lines[-1].strip())
        if not match or Path(match["path"]).parent != attachments:
            break
        names.insert(0, Path(match["path"]).name)
        lines.pop()
    return "\n".join(lines).strip(), names
