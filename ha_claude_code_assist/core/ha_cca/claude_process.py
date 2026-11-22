"""One Claude Code process in headless stream-json mode, holding one session."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)

STREAM_LIMIT = 16 * 1024 * 1024


class ProcessExitedError(RuntimeError):
    """Claude Code stopped. The message is for the user; `detail` (exit code, last lines of its
    error output) is for the log."""

    def __init__(self, message: str, detail: str = "") -> None:
        super().__init__(message)
        self.detail = detail


@dataclass(frozen=True)
class LaunchSpec:
    # --resume with Claude Code's session id when its transcript exists; otherwise --session-id
    # with the id Claude Code should give the new conversation (ours).
    session_id: str
    resume: bool
    model: str
    effort: str
    system_prompt: str
    mcp_config: dict[str, Any]
    builtin_tools: list[str]  # Claude Code's own tools, e.g. WebSearch; empty = none
    allowed_tools: list[str]
    disallowed_tools: list[str]  # removed from Claude's context
    oauth_token: str
    workdir: Path
    config_dir: Path
    claude_settings: dict[str, Any]  # Claude Code settings for this process (--settings)

    def command(self) -> list[str]:
        cmd = [
            "claude", "-p",
            "--input-format", "stream-json",
            "--output-format", "stream-json",
            "--verbose",
            "--include-partial-messages",
            "--model", self.model,
            "--effort", self.effort,
            "--tools", ",".join(self.builtin_tools),
            "--strict-mcp-config",
            "--mcp-config", json.dumps(self.mcp_config),
            "--permission-mode", "dontAsk",
            "--settings", json.dumps(self.claude_settings),
            "--allowedTools", ",".join(self.allowed_tools),
            "--system-prompt", self.system_prompt,
        ]
        if self.disallowed_tools:
            cmd += ["--disallowedTools", ",".join(self.disallowed_tools)]
        cmd += ["--resume", self.session_id] if self.resume else ["--session-id", self.session_id]
        return cmd

    def environment(self) -> dict[str, str]:
        env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "SUPERVISOR_TOKEN")}
        env.update({
            "CLAUDE_CODE_OAUTH_TOKEN": self.oauth_token,
            "CLAUDE_CONFIG_DIR": str(self.config_dir),
            "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
            "DISABLE_UPDATES": "1",
        })
        return env


class ClaudeProcess:
    def __init__(self, spec: LaunchSpec) -> None:
        self.spec = spec
        self._proc: asyncio.subprocess.Process | None = None
        self._stderr_task: asyncio.Task[None] | None = None
        self._stderr_tail: list[str] = []

    @property
    def alive(self) -> bool:
        return self._proc is not None and self._proc.returncode is None

    async def start(self) -> None:
        self.spec.workdir.mkdir(parents=True, exist_ok=True)
        self._proc = await asyncio.create_subprocess_exec(
            *self.spec.command(),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self.spec.environment(),
            cwd=self.spec.workdir,
            limit=STREAM_LIMIT,
        )
        self._stderr_task = asyncio.create_task(self._drain_stderr())
        LOGGER.info("Claude Code started for session %s (pid %s, %s)",
                    self.spec.session_id, self._proc.pid, "resume" if self.spec.resume else "new")

    async def turn(self, text: str) -> AsyncIterator[dict[str, Any]]:
        """Sends one user message and yields its events, the final `result` included."""
        assert self._proc is not None and self._proc.stdin is not None and self._proc.stdout is not None
        message = {"type": "user", "message": {"role": "user", "content": text}, "parent_tool_use_id": None}
        try:
            self._proc.stdin.write((json.dumps(message) + "\n").encode())
            await self._proc.stdin.drain()
        except (BrokenPipeError, ConnectionResetError) as err:
            raise self._exited() from err
        while True:
            line = await self._proc.stdout.readline()
            if not line:
                await self._proc.wait()
                raise self._exited()
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                LOGGER.warning("Unparsable line from Claude Code: %r", line[:200])
                continue
            yield event
            if event.get("type") == "result":
                return

    async def close(self, timeout: float = 10) -> None:
        """Ends the process cleanly (EOF on stdin), killing it after a timeout."""
        if self._proc is None:
            return
        if self._proc.stdin is not None and not self._proc.stdin.is_closing():
            self._proc.stdin.close()
        try:
            await asyncio.wait_for(self._proc.wait(), timeout)
        except TimeoutError:
            self._proc.kill()
            await self._proc.wait()
        if self._stderr_task is not None:
            with contextlib.suppress(asyncio.CancelledError):
                await self._stderr_task

    async def _drain_stderr(self) -> None:
        assert self._proc is not None and self._proc.stderr is not None
        async for raw in self._proc.stderr:
            line = raw.decode(errors="replace").rstrip()
            if line:
                self._stderr_tail = [*self._stderr_tail[-19:], line]
                LOGGER.warning("Claude Code [%s]: %s", self.spec.session_id, line)

    def _exited(self) -> ProcessExitedError:
        code = self._proc.returncode if self._proc else None
        tail = " | ".join(self._stderr_tail[-3:])
        return ProcessExitedError(
            "Claude Code stopped unexpectedly, so this session was closed. Send your message again to start a new one.",
            f"exit code {code}" + (f", {tail}" if tail else ""))
