"""Long-term memory: memory.json in a git repository, written only through this store."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


class MemoryLimitError(ValueError):
    """A write would exceed the configured memory limits."""


@dataclass(frozen=True)
class MemoryEntry:
    id: int
    text: str
    created_at: str
    created_by: str  # "claude" | "user"
    conversation_id: str | None


class MemoryStore:
    def __init__(self, directory: Path, max_entries: int, max_entry_length: int) -> None:
        self.directory = directory
        self.max_entries = max_entries
        self.max_entry_length = max_entry_length
        self._file = directory / "memory.json"
        self._lock = asyncio.Lock()
        self._listeners: set[Callable[[], None]] = set()
        directory.mkdir(parents=True, exist_ok=True)
        if not (directory / ".git").exists():
            self._git("init", "--quiet")
        self._entries, self._next_id = self._load()

    def entries(self) -> list[MemoryEntry]:
        return list(self._entries)

    def subscribe(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Calls `listener` after every change."""
        self._listeners.add(listener)
        return lambda: self._listeners.discard(listener)

    def render(self) -> str:
        """Deterministic text for the system prompt: same memory, same bytes."""
        if not self._entries:
            return "(no entries)"
        return "\n".join(f"- [{e.id}] {e.text}" for e in sorted(self._entries, key=lambda e: e.id))

    async def add(self, text: str, created_by: str, conversation_id: str | None = None) -> MemoryEntry:
        text = self._validate(text)
        async with self._lock:
            if len(self._entries) >= self.max_entries:
                entries = f"{self.max_entries} entr{'y' if self.max_entries == 1 else 'ies'}"
                raise MemoryLimitError(
                    f"The memory is full with {entries}. Remove an entry first, in the Memory tab of "
                    "the HA Claude Code Assist panel or by asking the assistant to forget one")
            # Ids are never reused: an id quoted in an old conversation keeps
            # pointing to the entry it meant, or to nothing.
            entry = MemoryEntry(
                id=self._next_id,
                text=text,
                created_at=datetime.now(UTC).isoformat(timespec="seconds"),
                created_by=created_by,
                conversation_id=conversation_id,
            )
            await self._save([*self._entries, entry], f"Add memory {entry.id} ({created_by})",
                             next_id=entry.id + 1)
            return entry

    async def update(self, entry_id: int, text: str) -> MemoryEntry:
        text = self._validate(text)
        async with self._lock:
            current = self._find(entry_id)
            updated = MemoryEntry(**{**asdict(current), "text": text})
            await self._save([updated if e.id == entry_id else e for e in self._entries],
                             f"Update memory {entry_id} (user)")
            return updated

    async def remove(self, entry_id: int, removed_by: str) -> None:
        async with self._lock:
            self._find(entry_id)
            await self._save([e for e in self._entries if e.id != entry_id],
                             f"Remove memory {entry_id} ({removed_by})")

    def _validate(self, text: str) -> str:
        text = " ".join(text.split())
        if not text:
            raise MemoryLimitError("The entry is empty. Write the fact to remember")
        if len(text) > self.max_entry_length:
            raise MemoryLimitError(
                f"The entry is {len(text)} characters long, but the limit is {self.max_entry_length}. Make it shorter")
        return text

    def _find(self, entry_id: int) -> MemoryEntry:
        for entry in self._entries:
            if entry.id == entry_id:
                return entry
        raise KeyError(f"There is no memory entry with id {entry_id}.")

    def _load(self) -> tuple[list[MemoryEntry], int]:
        try:
            data = json.loads(self._file.read_text())
        except FileNotFoundError:
            return [], 1
        return [MemoryEntry(**item) for item in data["entries"]], data["next_id"]

    async def _save(self, entries: list[MemoryEntry], message: str, next_id: int | None = None) -> None:
        next_id = next_id or self._next_id
        payload = json.dumps({"next_id": next_id, "entries": [asdict(e) for e in entries]},
                             indent=2, ensure_ascii=False) + "\n"
        tmp = self._file.with_suffix(".json.tmp")
        tmp.write_text(payload)
        os.replace(tmp, self._file)
        self._entries = entries
        self._next_id = next_id
        await asyncio.to_thread(self._commit, message)
        for listener in list(self._listeners):
            listener()

    def _commit(self, message: str) -> None:
        self._git("add", "memory.json")
        self._git("commit", "--quiet", "-m", message)

    def _git(self, *args: str) -> None:
        subprocess.run(
            ["git", "-C", str(self.directory),
             "-c", "user.name=ha-claude-code-assist", "-c", "user.email=ha-claude-code-assist@localhost",
             *args],
            check=True, capture_output=True,
        )
