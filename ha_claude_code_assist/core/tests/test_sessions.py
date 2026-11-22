import asyncio
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import ClassVar

import pytest

from ha_cca import sessions as sessions_module
from ha_cca.claude_process import ProcessExitedError
from ha_cca.config import parse_options
from ha_cca.launch import build_launch_spec
from ha_cca.sessions import ClaudeSession, SessionManager, SessionSettings, SessionStore, TurnError


def usage_event(model="claude-test", input_tokens=10, cache_read=90, cache_creation=0):
    return {"type": "assistant", "message": {"model": model, "usage": {
        "input_tokens": input_tokens, "cache_read_input_tokens": cache_read,
        "cache_creation_input_tokens": cache_creation}}}


class FakeProcess:
    """Stands in for Claude Code. Like Claude Code it reports its session id in the init event of
    every turn (the one given with --session-id, or the resumed one) and its usage as the
    conversation's running total (`modelUsage`)."""

    instances: ClassVar[list["FakeProcess"]] = []  # every process started, reset by each test
    fail_next = False
    reject_token_next = False
    # When set, the next new conversation reports this id instead of the one it was given.
    report_other_id: str | None = None
    # When set, the next init event carries no session id.
    report_no_id = False
    # Replaces the next turn's events, to test unusual streams.
    script: list[dict] | None = None
    # When set, the next turn waits for it: lets a test act while a turn runs.
    hold: asyncio.Event | None = None

    def __init__(self, spec):
        self.spec = spec
        self.running = False
        self.closed = False
        self.messages = []
        self.claude_id = spec.session_id
        if not spec.resume and FakeProcess.report_other_id:
            self.claude_id, FakeProcess.report_other_id = FakeProcess.report_other_id, None
        FakeProcess.instances.append(self)

    @property
    def alive(self):
        return self.running

    async def start(self):
        self.running = True

    async def turn(self, text):
        if FakeProcess.hold is not None:
            hold, FakeProcess.hold = FakeProcess.hold, None
            await hold.wait()
        if FakeProcess.fail_next:
            FakeProcess.fail_next = False
            self.running = False
            raise ProcessExitedError("Claude Code stopped unexpectedly.", "exit code 1")
        self.messages.append(text)
        reported = None if FakeProcess.report_no_id else self.claude_id
        FakeProcess.report_no_id = False
        yield {"type": "system", "subtype": "init", "session_id": reported, "tools": ["Read"]}
        if FakeProcess.script is not None:
            events, FakeProcess.script = FakeProcess.script, None
            for event in events:
                yield event
            return
        if FakeProcess.reject_token_next:
            FakeProcess.reject_token_next = False
            # What Claude Code emits when the subscription token is rejected.
            yield {"type": "assistant", "error": "authentication_failed",
                   "message": {"model": "<synthetic>", "content": [{"type": "text", "text": "Failed to authenticate."}]}}
            yield {"type": "result", "subtype": "success", "is_error": True, "api_error_status": 401,
                   "result": "Failed to authenticate. API Error: 401 OAuth access token is invalid."}
            return
        turns = len(self.messages)
        yield usage_event()
        yield {"type": "result", "subtype": "success", "is_error": False, "result": f"echo: {text}",
               "modelUsage": {
                   "claude-test": {"inputTokens": 10 * turns, "outputTokens": 5 * turns,
                                   "cacheReadInputTokens": 90 * turns, "cacheCreationInputTokens": 20,
                                   "webSearchRequests": 1, "costUSD": 0.5 * turns, "contextWindow": 1000},
                   "claude-helper": {"inputTokens": 1, "outputTokens": 1, "cacheReadInputTokens": 0,
                                     "cacheCreationInputTokens": 0, "webSearchRequests": 0, "costUSD": 0.25,
                                     "contextWindow": 200},
               }}

    async def close(self):
        self.running = False
        self.closed = True


class Clock:
    def __init__(self):
        self.value = datetime(2026, 11, 21, 8, 0, tzinfo=UTC)

    def __call__(self):
        return self.value

    def advance(self, **kwargs):
        self.value += timedelta(**kwargs)


@dataclass
class Env:
    tmp_path: Path
    clock: Clock = field(default_factory=Clock)
    # Claude Code's transcripts that exist, by Claude Code's session id.
    transcripts: set[str] = field(default_factory=set)
    removed: list[str] = field(default_factory=list)
    defaults: SessionSettings = field(default_factory=lambda: SessionSettings("haiku", "low", False, True, True))
    mcp_servers: dict = field(default_factory=lambda: {"ha-mcp": {"type": "http", "url": "http://x"}})
    retention: timedelta = timedelta(days=30)

    @property
    def root(self) -> Path:
        return self.tmp_path / "sessions"

    def manager(self) -> SessionManager:
        store = SessionStore(self.root)

        def launch(record, resume):
            settings = parse_options({"mcp_servers": json.dumps({"mcpServers": self.mcp_servers})})
            return build_launch_spec(record, resume, settings=settings, memory_text="(no entries)",
                                     internal_mcp_url="http://127.0.0.1:8099/mcp",
                                     workdir=store.workdir(record.session_id), config_dir=self.tmp_path / "claude")

        def remove_claude_files(record):
            self.removed.append(record.session_id)
            return []

        return SessionManager(
            store,
            timeout=lambda: timedelta(minutes=5),
            retention=lambda: self.retention,
            # A new object each time, as the app builds one from the current settings.
            defaults=lambda: SessionSettings(self.defaults.model, self.defaults.effort, self.defaults.web_search,
                                             self.defaults.memory_enabled, self.defaults.read_files),
            spec_builder=launch,
            transcript_exists=lambda record: record.claude.session_id in self.transcripts,
            remove_claude_files=remove_claude_files,
            process_factory=FakeProcess,
            now=self.clock,
        )

    def stored(self, session_id: str) -> dict:
        return json.loads((self.root / session_id / "session.json").read_text())

    def folders(self) -> list[str]:
        return sorted(p.name for p in self.root.iterdir()) if self.root.is_dir() else []


@pytest.fixture
def env(tmp_path):
    FakeProcess.instances = []
    FakeProcess.fail_next = False
    FakeProcess.reject_token_next = False
    FakeProcess.report_other_id = None
    FakeProcess.report_no_id = False
    FakeProcess.script = None
    FakeProcess.hold = None
    return Env(tmp_path)


# --- the record and its folder -------------------------------------------------


async def test_record_layout_keeps_ours_settings_and_claude_apart(env):
    manager = env.manager()
    result = await manager.send("panel", "user-1", "c1", "hello", source_name="Test")
    stored = env.stored(result.session_id)
    assert list(stored) == ["session_id", "title", "source", "conversation_ids", "created_at", "last_activity",
                            "closed_at", "settings", "claude"]
    assert stored["session_id"] == result.session_id
    assert stored["settings"] == {"model": "haiku", "effort": "low", "web_search": False, "memory_enabled": True,
                                  "read_files": True, "mcp_servers": ["ha-mcp"]}
    assert list(stored["claude"]) == ["session_id", "context_tokens", "context_window", "input_tokens",
                                      "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens",
                                      "web_search_requests", "cost_usd"]


async def test_one_folder_per_session_with_its_record_and_working_directory(env):
    manager = env.manager()
    a = await manager.send("panel", "user-1", "c1", "hi")
    b = await manager.send("panel", "user-2", "c2", "hi")
    assert env.folders() == sorted([a.session_id, b.session_id])
    for result in (a, b):
        folder = env.root / result.session_id
        assert sorted(p.name for p in folder.iterdir()) == ["session.json", "workdir"]
        assert manager.workdir(result.session_id) == folder / "workdir"
    assert not (env.tmp_path / "sessions.json").exists()


async def test_store_round_trip(env):
    manager = env.manager()
    result = await manager.send("panel", "user-1", "c1", "hello")
    loaded = {r.session_id: r for r in SessionStore(env.root).load()}
    assert loaded[result.session_id] == manager.get(result.session_id)


def test_store_ignores_a_folder_without_a_record(env):
    (env.root / "8f14e45f-ceea-467a-9575-1f0a2f8a1c11" / "workdir").mkdir(parents=True)
    assert SessionStore(env.root).load() == []


async def test_store_skips_records_it_cannot_read_and_loads_the_others(env):
    manager = env.manager()
    good = await manager.send("panel", "user-1", "c1", "hi")
    broken = env.root / "11111111-2222-4333-8444-555555555555"
    broken.mkdir()
    (broken / "session.json").write_text("{not json")
    old = env.root / "22222222-3333-4444-8555-666666666666"
    old.mkdir()
    (old / "session.json").write_text('{"session_id": "22222222-3333-4444-8555-666666666666"}')  # fields missing
    assert [r.session_id for r in SessionStore(env.root).load()] == [good.session_id]
    assert broken.exists() and old.exists()  # left as they are


def test_store_remove_of_a_missing_folder(env):
    SessionStore(env.root).remove("8f14e45f-ceea-467a-9575-1f0a2f8a1c11")


def test_store_accepts_only_session_ids(env):
    store = SessionStore(env.root)
    for bad in ("", "..", "../x", "8F14E45F-CEEA-467A-9575-1F0A2F8A1C11", "a/b"):
        with pytest.raises(ValueError, match="not a session id"):
            store.folder(bad)


async def test_new_session_starts_without_claudes_id_and_gets_its_title_from_the_first_message(env):
    manager = env.manager()
    record = await manager.resolve("panel", "user-1", "c1")
    assert record.title == "" and record.claude == ClaudeSession()
    assert env.stored(record.session_id)["claude"]["session_id"] is None
    await manager.run(record, "  turn on\n the   kitchen light " + "x" * 100)
    assert record.title == ("turn on the kitchen light " + "x" * 100)[:80]
    await manager.run(record, "second message")
    assert record.title.startswith("turn on the kitchen light")


# --- our session id and Claude Code's ------------------------------------------


async def test_a_new_conversation_gets_our_id_and_claudes_is_what_it_reports(env):
    manager = env.manager()
    result = await manager.send("panel", "user-1", "c1", "hi")
    (process,) = FakeProcess.instances
    assert (process.spec.resume, process.spec.session_id) == (False, result.session_id)
    assert process.spec.workdir == env.root / result.session_id / "workdir"
    record = manager.get(result.session_id)
    assert record.claude.session_id == result.session_id  # what Claude Code reported
    assert env.stored(result.session_id)["claude"]["session_id"] == result.session_id


async def test_resume_uses_claudes_id_from_the_same_working_directory(env):
    manager = env.manager()
    first = await manager.send("panel", "user-1", "c1", "hi")
    env.transcripts.add(manager.get(first.session_id).claude.session_id)
    await manager.shutdown()  # app restart: processes stop, sessions stay open

    restarted = env.manager()
    env.clock.advance(minutes=1)
    second = await restarted.send("panel", "user-1", "c1", "still there?")
    assert second.session_id == first.session_id
    resumed = FakeProcess.instances[-1].spec
    assert (resumed.resume, resumed.session_id) == (True, restarted.get(first.session_id).claude.session_id)
    assert resumed.workdir == FakeProcess.instances[0].spec.workdir


async def test_each_id_is_used_for_what_it_is_when_claude_reports_another(env):
    FakeProcess.report_other_id = "11111111-2222-4333-8444-555555555555"
    manager = env.manager()
    first = await manager.send("panel", "user-1", "c1", "hi")
    record = manager.get(first.session_id)
    assert record.session_id == first.session_id != record.claude.session_id
    assert record.claude.session_id == "11111111-2222-4333-8444-555555555555"
    assert env.folders() == [first.session_id]  # our folder, by our id

    env.transcripts.add(record.claude.session_id)
    await manager.shutdown()
    restarted = env.manager()
    await restarted.send("panel", "user-1", "c1", "again")
    resumed = FakeProcess.instances[-1].spec
    assert (resumed.resume, resumed.session_id) == (True, "11111111-2222-4333-8444-555555555555")
    assert resumed.workdir == env.root / first.session_id / "workdir"


async def test_a_session_claude_never_answered_starts_again_with_our_id(env):
    manager = env.manager()
    record = await manager.resolve("panel", "user-1", "c1")
    FakeProcess.fail_next = True  # Claude Code stops before reporting anything
    with pytest.raises(TurnError):
        await manager.run(record, "hi")
    assert record.claude.session_id is None


async def test_an_init_event_without_an_id_keeps_what_was_known(env):
    manager = env.manager()
    first = await manager.send("panel", "user-1", "c1", "hi")
    known = manager.get(first.session_id).claude.session_id
    FakeProcess.report_no_id = True
    await manager.send("panel", "user-1", "c1", "again")
    assert manager.get(first.session_id).claude.session_id == known


async def test_the_working_directory_is_made_again_when_missing(env):
    manager = env.manager()
    first = await manager.send("panel", "user-1", "c1", "hi")
    workdir = manager.workdir(first.session_id)
    workdir.rmdir()
    await manager.shutdown()
    restarted = env.manager()
    await restarted.send("panel", "user-1", "c1", "again")
    assert workdir.is_dir()


async def test_no_resume_without_claudes_transcript(env):
    manager = env.manager()
    first = await manager.send("panel", "user-1", "c1", "hi")
    await manager.shutdown()  # the transcript was never written (env.transcripts is empty)
    restarted = env.manager()
    await restarted.send("panel", "user-1", "c1", "again")
    spec = FakeProcess.instances[-1].spec
    assert (spec.resume, spec.session_id) == (False, first.session_id)


# --- settings ------------------------------------------------------------------


async def test_a_given_title_names_the_session(env):
    manager = env.manager()
    record = await manager.resolve("panel", "user-1", "c1")
    await manager.run(record, "what is it?\n\n[Attached file: /x/attachments/a.jpg]", title="what is it?")
    assert record.title == "what is it?"


async def test_a_message_with_files_is_not_moved_to_a_new_session(env):
    manager = env.manager()
    record = await manager.resolve("panel", "user-1", "c1")
    await manager.close(record.session_id)  # ended between the upload and the message
    with pytest.raises(TurnError, match="Attach the files again"):
        await manager.run(record, "with files", move_if_closed=False)
    assert len(manager.sessions()) == 1  # no new session for it


async def test_settings_are_fixed_when_the_conversation_starts(env):
    manager = env.manager()
    first = await manager.send("panel", "user-1", "c1", "hi")
    env.defaults = SessionSettings("opus", "high", True, False, False)
    again = await manager.send("panel", "user-1", "c1", "hi")
    assert again.session_id == first.session_id
    kept = manager.get(first.session_id).settings
    assert (kept.model, kept.effort, kept.web_search, kept.memory_enabled, kept.read_files) == ("haiku", "low", False, True, True)
    other = manager.get((await manager.send("panel", "user-2", "c2", "hi")).session_id).settings
    assert (other.model, other.effort, other.web_search, other.memory_enabled, other.read_files) == ("opus", "high", True, False, False)
    assert "Read" not in FakeProcess.instances[-1].spec.builtin_tools


async def test_mcp_servers_are_those_of_the_last_process_start(env):
    manager = env.manager()
    first = await manager.send("panel", "user-1", "c1", "hi")
    assert manager.get(first.session_id).settings.mcp_servers == ["ha-mcp"]
    # Changing the settings does not touch a running process...
    env.mcp_servers = {"other": {"type": "http", "url": "http://y"}}
    await manager.send("panel", "user-1", "c1", "hi")
    assert manager.get(first.session_id).settings.mcp_servers == ["ha-mcp"]
    # ...a resumed one gets the configured servers.
    env.transcripts.add(manager.get(first.session_id).claude.session_id)
    await manager.shutdown()
    restarted = env.manager()
    await restarted.send("panel", "user-1", "c1", "hi")
    assert restarted.get(first.session_id).settings.mcp_servers == ["other"]


async def test_no_mcp_servers(env):
    env.mcp_servers = {}
    manager = env.manager()
    result = await manager.send("panel", "user-1", "c1", "hi")
    assert manager.get(result.session_id).settings.mcp_servers == []


# --- what Claude Code reports ------------------------------------------------


async def test_usage_is_the_latest_running_total_and_the_window_of_the_answering_model(env):
    manager = env.manager()
    first = await manager.send("panel", "user-1", "c1", "hello")
    await manager.send("panel", "user-1", "c1", "again")
    claude = manager.get(first.session_id).claude
    # The second result's totals (both models), not the sum of both results.
    assert (claude.input_tokens, claude.output_tokens, claude.cache_read_input_tokens,
            claude.cache_creation_input_tokens, claude.web_search_requests, claude.cost_usd) == (21, 11, 180, 20, 1, 1.25)
    assert claude.context_window == 1000  # claude-test answered, not claude-helper (200)
    assert claude.context_tokens == 100


async def test_context_is_the_last_model_call_of_the_turn(env):
    manager = env.manager()
    FakeProcess.script = [
        usage_event(input_tokens=5, cache_read=100),  # asks for a tool
        usage_event(input_tokens=7, cache_read=300, cache_creation=20),  # answers
        {"type": "result", "subtype": "success", "is_error": False, "result": "done",
         "modelUsage": {"claude-test": {"inputTokens": 12, "contextWindow": 1000}}},
    ]
    result = await manager.send("panel", "user-1", "c1", "hi")
    assert manager.get(result.session_id).claude.context_tokens == 327


async def test_window_falls_back_to_the_largest_when_the_model_is_unknown(env):
    manager = env.manager()
    FakeProcess.script = [
        {"type": "assistant", "message": {"usage": {"input_tokens": 1}}},
        {"type": "result", "subtype": "success", "is_error": False, "result": "done",
         "modelUsage": {"a": {"contextWindow": 200}, "b": {"contextWindow": 1000}}},
    ]
    result = await manager.send("panel", "user-1", "c1", "hi")
    assert manager.get(result.session_id).claude.context_window == 1000


async def test_a_result_without_usage_keeps_the_previous_totals(env):
    manager = env.manager()
    first = await manager.send("panel", "user-1", "c1", "hello")
    before = manager.get(first.session_id).claude.input_tokens
    FakeProcess.script = [{"type": "result", "subtype": "error_during_execution", "is_error": True, "result": ""}]
    await manager.send("panel", "user-1", "c1", "again")
    claude = manager.get(first.session_id).claude
    assert claude.input_tokens == before and claude.context_tokens == 100


async def test_usage_is_saved(env):
    manager = env.manager()
    result = await manager.send("panel", "user-1", "c1", "hello")
    claude = env.stored(result.session_id)["claude"]
    assert claude["context_tokens"] == 100 and claude["cost_usd"] == 0.75


# --- routing and lifecycle -----------------------------------------------------


async def test_same_source_continues_the_session(env):
    manager = env.manager()
    first = await manager.send("panel", "user-1", "conv-a", "hello")
    env.clock.advance(minutes=4)
    second = await manager.send("panel", "user-1", "conv-a", "again")
    assert first.session_id == second.session_id
    assert second.text == "echo: again"
    assert len(FakeProcess.instances) == 1


async def test_new_conversation_id_from_same_source_is_attached(env):
    manager = env.manager()
    first = await manager.send("assist", "satellite-kitchen", "ha-1", "turn on the light")
    second = await manager.send("assist", "satellite-kitchen", "ha-2", "dim it")
    assert first.session_id == second.session_id
    assert manager.get(first.session_id).conversation_ids == ["ha-1", "ha-2"]
    assert env.stored(first.session_id)["conversation_ids"] == ["ha-1", "ha-2"]


async def test_known_conversation_id_wins(env):
    manager = env.manager()
    first = await manager.send("assist", "satellite-kitchen", "ha-1", "hi")
    other = await manager.send("assist", "satellite-office", "ha-1", "hi again")
    assert other.session_id == first.session_id


async def test_different_sources_get_different_sessions(env):
    manager = env.manager()
    a = await manager.send("panel", "user-1", "c1", "hi")
    b = await manager.send("panel", "user-2", "c2", "hi")
    assert a.session_id != b.session_id


async def test_timeout_closes_and_starts_a_new_session(env):
    manager = env.manager()
    first = await manager.send("panel", "user-1", "c1", "hi")
    env.clock.advance(minutes=5, seconds=1)
    second = await manager.send("panel", "user-1", "c1", "hi")
    assert second.session_id != first.session_id
    assert manager.get(first.session_id).closed_at is not None
    assert env.stored(first.session_id)["closed_at"] is not None
    assert FakeProcess.instances[0].closed


async def test_process_exit_closes_the_session(env):
    manager = env.manager()
    first = await manager.send("panel", "user-1", "c1", "hi")
    FakeProcess.fail_next = True
    with pytest.raises(TurnError, match="stopped unexpectedly"):
        await manager.send("panel", "user-1", "c1", "boom")
    assert manager.get(first.session_id).closed_at is not None
    third = await manager.send("panel", "user-1", "c1", "hi")
    assert third.session_id != first.session_id


async def test_close_is_refused_while_the_assistant_answers(env):
    manager = env.manager()
    first = await manager.send("panel", "user-1", "c1", "hi")
    hold = FakeProcess.hold = asyncio.Event()
    turn = asyncio.create_task(manager.run(manager.get(first.session_id), "slow"))
    await asyncio.sleep(0)
    with pytest.raises(TurnError, match=r"^The assistant is still answering\. Wait for the answer, then end the session\.$"):
        await manager.close(first.session_id)
    hold.set()
    await turn
    await manager.close(first.session_id)
    assert manager.get(first.session_id).closed_at is not None


async def test_unknown_session_message(env):
    manager = env.manager()
    with pytest.raises(KeyError) as err:
        manager.get("8f14e45f-ceea-467a-9575-1f0a2f8a1c11")
    assert err.value.args[0] == "This session no longer exists."


async def test_manual_close(env):
    manager = env.manager()
    first = await manager.send("panel", "user-1", "c1", "hi")
    await manager.close(first.session_id)
    assert manager.get(first.session_id).closed_at is not None
    assert not manager.sessions()[0]["active"]


async def test_events_are_published(env):
    manager = env.manager()
    events = []
    manager.subscribe(events.append)
    await manager.send("panel", "user-1", "c1", "hi")
    types = [e["type"] for e in events]
    assert types[0] == "session_updated"
    assert "turn_started" in types and types.count("turn_event") == 3
    finished = next(e for e in events if e["type"] == "turn_finished")
    assert finished["is_error"] is False and finished["text"] == "echo: hi"


async def test_source_name_is_recorded(env):
    manager = env.manager()
    result = await manager.send("panel", "user-1", "c1", "hi", source_name="Alex")
    assert manager.get(result.session_id).source == {"channel": "panel", "key": "user-1", "name": "Alex"}
    # same source without a name still continues the session
    again = await manager.send("panel", "user-1", "c1", "hi")
    assert again.session_id == result.session_id


async def test_rejected_token_is_reported_clearly(env):
    manager = env.manager()
    events = []
    manager.subscribe(events.append)
    FakeProcess.reject_token_next = True
    result = await manager.send("panel", "user-1", "c1", "hi")
    finished = next(e for e in events if e["type"] == "turn_finished")
    assert result.is_error and finished["error"] == "authentication_failed"
    assert "token was rejected" in finished["text"] and "Settings" in finished["text"]
    assert manager.token_rejected_at is not None
    await manager.send("panel", "user-1", "c1", "hi again")
    assert manager.token_rejected_at is None


# --- deleting ------------------------------------------------------------------


async def test_delete_removes_the_sessions_folder_and_claudes_files(env):
    manager = env.manager()
    events = []
    manager.subscribe(events.append)
    first = await manager.send("panel", "user-1", "c1", "hi")
    process = FakeProcess.instances[0]
    events.clear()

    await manager.delete(first.session_id)

    assert process.closed
    assert env.folders() == []  # record and working directory
    assert env.removed == [first.session_id]  # Claude Code's files, found from our session
    with pytest.raises(KeyError):
        manager.get(first.session_id)
    assert manager.sessions() == []
    assert [e["type"] for e in events] == ["session_updated", "session_deleted"]
    assert events[-1]["session_id"] == first.session_id
    assert env.manager().sessions() == []  # gone after a restart too


async def test_delete_leaves_other_sessions_alone(env):
    manager = env.manager()
    kept = await manager.send("panel", "user-1", "c1", "hi")
    gone = await manager.send("panel", "user-2", "c2", "hi")
    await manager.delete(gone.session_id)
    assert [s["session_id"] for s in manager.sessions()] == [kept.session_id]
    assert env.folders() == [kept.session_id] and env.removed == [gone.session_id]
    assert not FakeProcess.instances[0].closed
    assert manager.get(kept.session_id).closed_at is None


async def test_delete_when_the_working_directory_is_already_gone(env):
    manager = env.manager()
    first = await manager.send("panel", "user-1", "c1", "hi")
    manager.workdir(first.session_id).rmdir()
    await manager.delete(first.session_id)
    assert env.folders() == [] and env.removed == [first.session_id]


async def test_delete_a_session_claude_never_answered(env):
    manager = env.manager()
    record = await manager.resolve("panel", "user-1", "c1")
    await manager.delete(record.session_id)
    assert env.folders() == [] and env.removed == [record.session_id]


async def test_delete_an_ended_session(env):
    manager = env.manager()
    first = await manager.send("panel", "user-1", "c1", "hi")
    await manager.close(first.session_id)
    await manager.delete(first.session_id)
    assert manager.sessions() == [] and env.folders() == [] and env.removed == [first.session_id]


async def test_delete_unknown_session(env):
    manager = env.manager()
    with pytest.raises(KeyError):
        await manager.delete("8f14e45f-ceea-467a-9575-1f0a2f8a1c11")
    assert env.removed == []


async def test_delete_is_refused_while_the_assistant_answers(env):
    manager = env.manager()
    first = await manager.send("panel", "user-1", "c1", "hi")
    record = manager.get(first.session_id)
    hold = FakeProcess.hold = asyncio.Event()
    turn = asyncio.create_task(manager.run(record, "slow"))
    await asyncio.sleep(0)  # the turn starts and waits
    with pytest.raises(TurnError, match="answering"):
        await manager.delete(first.session_id)
    assert manager.get(first.session_id) is record and env.folders() == [first.session_id]
    hold.set()
    assert (await turn).text == "echo: slow"
    await manager.delete(first.session_id)  # allowed once the answer is in
    assert env.folders() == []


async def test_after_delete_the_same_chat_starts_a_new_session(env):
    manager = env.manager()
    first = await manager.send("panel", "user-1", "c1", "hi")
    await manager.delete(first.session_id)
    again = await manager.send("panel", "user-1", "c1", "hello again")
    assert again.session_id != first.session_id
    assert manager.get(again.session_id).title == "hello again"
    assert env.folders() == [again.session_id]


# --- expiry ----------------------------------------------------------------------


async def test_a_session_with_no_messages_for_longer_than_the_retention_is_deleted(env):
    manager = env.manager()
    old = await manager.send("panel", "user-1", "c1", "hi")
    env.clock.advance(days=20)
    recent = await manager.send("panel", "user-2", "c2", "hi")
    env.clock.advance(days=11)  # old: 31 days without messages, recent: 11

    assert await manager.remove_expired() == [old.session_id]

    assert [s["session_id"] for s in manager.sessions()] == [recent.session_id]
    assert env.folders() == [recent.session_id] and env.removed == [old.session_id]


async def test_exactly_the_retention_period_is_kept(env):
    manager = env.manager()
    await manager.send("panel", "user-1", "c1", "hi")
    env.clock.advance(days=30)
    assert await manager.remove_expired() == []


async def test_a_shorter_retention_deletes_the_older_sessions_right_away(env):
    manager = env.manager()
    ten_days = await manager.send("panel", "user-1", "c1", "hi")
    env.clock.advance(days=7)
    three_days = await manager.send("panel", "user-2", "c2", "hi")
    env.clock.advance(days=3)
    assert await manager.remove_expired() == []

    env.retention = timedelta(days=5)
    manager.schedule_expiry()
    await manager._expiry

    assert [s["session_id"] for s in manager.sessions()] == [three_days.session_id]
    assert env.removed == [ten_days.session_id]


async def test_a_session_answering_is_never_expired(env):
    env.retention = timedelta(days=1)
    manager = env.manager()
    first = await manager.send("panel", "user-1", "c1", "hi")
    hold = FakeProcess.hold = asyncio.Event()
    turn = asyncio.create_task(manager.run(manager.get(first.session_id), "slow"))
    await asyncio.sleep(0)
    env.clock.advance(days=3)  # its last answered message is now 3 days old

    assert await manager.remove_expired() == []
    hold.set()
    await turn
    assert manager.get(first.session_id)


async def test_expired_sessions_are_removed_when_the_app_starts_and_every_hour(env, monkeypatch):
    monkeypatch.setattr(sessions_module, "REAPER_INTERVAL", 0)
    manager = env.manager()
    first = await manager.send("panel", "user-1", "c1", "hi")
    env.clock.advance(days=31)
    restarted = env.manager()
    restarted.start()
    await until(lambda: env.removed == [first.session_id])  # at start
    assert restarted.sessions() == []

    second = await restarted.send("panel", "user-2", "c2", "hi")
    env.clock.advance(days=31)  # and more than an hour since the last removal
    await until(lambda: env.removed == [first.session_id, second.session_id])
    await restarted.shutdown()
    assert restarted.sessions() == [] and env.folders() == []


async def test_an_interrupted_deletion_leaves_the_session_listed_and_is_finished_later(env):
    manager = env.manager()
    first = await manager.send("panel", "user-1", "c1", "hi")

    def stopped(record):
        raise RuntimeError("app stopped")  # while Claude Code's files are being removed

    manager._remove_claude_files = stopped
    with pytest.raises(RuntimeError, match="app stopped"):
        await manager.delete(first.session_id)
    assert [s["session_id"] for s in manager.sessions()] == [first.session_id]
    assert env.folders() == [first.session_id]

    manager._remove_claude_files = lambda record: []
    await manager.delete(first.session_id)
    assert manager.sessions() == [] and env.folders() == []


async def until(condition, timeout=2.0):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while not condition():
        assert loop.time() < deadline, "timed out"
        await asyncio.sleep(0.01)
