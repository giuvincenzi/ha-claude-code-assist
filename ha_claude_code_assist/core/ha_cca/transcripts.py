"""Claude Code's own files of a session: its transcript, read for display, and their removal.

The transcript format is internal to Claude Code (the CLI version is pinned in
the image); parsing is tolerant and skips anything it does not recognise.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from .attachments import IMAGE_TYPES, split_attachments

PREVIEW_LENGTH = 2000


class Transcripts:
    """Claude Code keeps a session's files in its project folder, named after the working
    directory it started in (non-alphanumerics replaced by "-"): the transcript
    `<claude session id>.jsonl` and `<claude session id>/` (WebFetch's downloads). Every session
    starts in its own working directory, so its project folder holds only its own files."""

    def __init__(self, config_dir: Path) -> None:
        self._projects = config_dir / "projects"

    def project_dir(self, workdir: Path) -> Path:
        return self._projects / re.sub(r"[^A-Za-z0-9]", "-", str(workdir))

    def path(self, workdir: Path, claude_session_id: str) -> Path:
        return self.project_dir(workdir) / f"{claude_session_id}.jsonl"

    def exists(self, workdir: Path, claude_session_id: str) -> bool:
        return self.path(workdir, claude_session_id).is_file()

    def remove_project(self, workdir: Path) -> list[Path]:
        """Removes the project folder of a session's working directory, with everything Claude
        Code keeps there for the session. Returns what was removed."""
        folder = self.project_dir(workdir)
        if folder.is_symlink() or not folder.is_dir():
            return []
        shutil.rmtree(folder)
        return [folder]

    def messages(self, workdir: Path, claude_session_id: str) -> list[dict[str, Any]]:
        """Conversation items: user text, assistant text, and tool calls with their results."""
        try:
            lines = self.path(workdir, claude_session_id).read_text().splitlines()
        except FileNotFoundError:
            return []
        items: list[dict[str, Any]] = []
        tools: dict[str, dict[str, Any]] = {}
        for line in lines:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            message = entry.get("message") or {}
            content = message.get("content")
            if entry.get("type") == "user":
                if isinstance(content, str):
                    text, names = split_attachments(content, workdir)
                    item: dict[str, Any] = {"kind": "user", "text": text, "timestamp": entry.get("timestamp")}
                    if names:
                        item["attachments"] = [attachment(name) for name in names]
                    items.append(item)
                    continue
                for block in content if isinstance(content, list) else []:
                    if block.get("type") == "tool_result" and block.get("tool_use_id") in tools:
                        tools[block["tool_use_id"]].update(
                            result=_preview(block.get("content")), is_error=bool(block.get("is_error")))
            elif entry.get("type") == "assistant":
                for block in content if isinstance(content, list) else []:
                    if block.get("type") == "text" and block.get("text", "").strip():
                        items.append({"kind": "assistant", "text": block["text"], "timestamp": entry.get("timestamp")})
                    elif block.get("type") == "tool_use":
                        item = {"kind": "tool", "name": block.get("name"), "input": block.get("input"),
                                "result": None, "is_error": False, "timestamp": entry.get("timestamp")}
                        tools[block.get("id")] = item
                        items.append(item)
        return items


def attachment(name: str) -> dict[str, Any]:
    """An attached file as the panel shows it: its name, and whether it is a picture."""
    return {"name": name, "image": Path(name).suffix.lower() in IMAGE_TYPES}


def _preview(content: Any) -> str:
    if isinstance(content, list):
        content = "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
    text = content if isinstance(content, str) else json.dumps(content)
    return text if len(text) <= PREVIEW_LENGTH else text[:PREVIEW_LENGTH] + "…"
