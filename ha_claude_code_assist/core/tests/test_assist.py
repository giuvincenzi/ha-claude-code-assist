import json
from dataclasses import dataclass, field

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ha_cca import access
from ha_cca.assist import AssistToken, assist_router, stream_turn, text_delta
from ha_cca.sessions import TurnError, TurnResult

OURS = "8f14e45f-ceea-467a-9575-1f0a2f8a1c11"


def stream_event(inner):
    return {"type": "turn_event", "session_id": OURS, "event": {"type": "stream_event", "event": inner}}


def text_block():
    return stream_event({"type": "content_block_start", "content_block": {"type": "text"}})


def text(chunk):
    return stream_event({"type": "content_block_delta", "delta": {"type": "text_delta", "text": chunk}})


@dataclass
class Record:
    session_id: str = OURS


@dataclass
class FakeSessions:
    """Publishes the events of a turn as the session manager does, then returns its result."""

    events: list[dict] = field(default_factory=list)
    result: TurnResult | None = None
    error: TurnError | None = None
    resolved: list[tuple] = field(default_factory=list)
    listeners: list = field(default_factory=list)

    async def resolve(self, channel, key, conversation_id, name=None):
        self.resolved.append((channel, key, conversation_id, name))
        return Record()

    def subscribe(self, listener):
        self.listeners.append(listener)
        return lambda: self.listeners.remove(listener)

    async def run(self, record, message):
        for event in self.events:
            for listener in list(self.listeners):
                listener(event)
        if self.error:
            raise self.error
        return self.result


async def collect(sessions, text_="hello", conversation_id="ha-1", key="satellite.kitchen", name="Kitchen"):
    return [item async for item in stream_turn(sessions, text_, conversation_id, key, name)]


# --- who reaches what -----------------------------------------------------------


@pytest.mark.parametrize("path, host, allowed", [
    ("/", access.INGRESS_PROXY, True),
    ("/ws", access.INGRESS_PROXY, True),
    ("/api/sessions/x/attachments", access.INGRESS_PROXY, True),
    ("/", access.HOME_ASSISTANT_CORE, False),  # Home Assistant Core never reaches the panel
    ("/ws", access.HOME_ASSISTANT_CORE, False),
    ("/api/assist", access.HOME_ASSISTANT_CORE, True),
    ("/api/assist/check", access.HOME_ASSISTANT_CORE, True),
    ("/api/assist", access.INGRESS_PROXY, False),  # nor the panel's users Assist
    ("/api/assistant", access.HOME_ASSISTANT_CORE, False),  # a path that only starts the same
    ("/api/assist", "172.30.33.5", False),  # another app
    ("/mcp", "127.0.0.1", True),
    ("/mcp", access.HOME_ASSISTANT_CORE, False),
    ("/", "127.0.0.1", False),
])
def test_each_part_answers_only_its_client(path, host, allowed):
    assert access.allowed(path, host) is allowed


# --- the token -------------------------------------------------------------------


def test_the_token_is_made_once_and_kept(tmp_path):
    first = AssistToken(tmp_path / "assist_token")
    assert len(first.value) >= 40
    assert (tmp_path / "assist_token").stat().st_mode & 0o777 == 0o600
    assert AssistToken(tmp_path / "assist_token").value == first.value


@pytest.mark.parametrize("header, matches", [
    (lambda t: f"Bearer {t}", True),
    (lambda t: t, True),
    (lambda t: f"Bearer {t}x", False),
    (lambda t: "Bearer ", False),
    (lambda t: "", False),
    (lambda t: None, False),
])
def test_the_token_must_match_exactly(tmp_path, header, matches):
    token = AssistToken(tmp_path / "assist_token")
    assert token.matches(header(token.value)) is matches


# --- the answer, streamed ---------------------------------------------------------


async def test_the_answer_streams_and_ends():
    sessions = FakeSessions(events=[
        text_block(), text("The kitchen "), text("light is on."),
        {"type": "turn_finished", "session_id": OURS, "is_error": False, "error": None, "text": "The kitchen light is on."},
    ], result=TurnResult(OURS, "The kitchen light is on.", False))
    items = await collect(sessions)
    assert items == [{"delta": "The kitchen "}, {"delta": "light is on."}, {"done": True, "error": None, "text": ""}]
    assert sessions.resolved == [("voice", "satellite.kitchen", "ha-1", "Kitchen")]
    assert sessions.listeners == []  # stops listening


async def test_the_parts_of_an_answer_are_separated():
    sessions = FakeSessions(events=[
        text_block(), text("Let me check."),
        stream_event({"type": "content_block_start", "content_block": {"type": "tool_use"}}),
        text_block(), text("It is 21 degrees."),
        {"type": "turn_finished", "session_id": OURS, "is_error": False, "error": None, "text": "It is 21 degrees."},
    ])
    deltas = [i["delta"] for i in await collect(sessions) if "delta" in i]
    assert "".join(deltas) == "Let me check.\n\nIt is 21 degrees."


async def test_an_answer_that_did_not_stream_comes_whole():
    sessions = FakeSessions(events=[
        {"type": "turn_finished", "session_id": OURS, "is_error": False, "error": None, "text": "Done."},
    ])
    assert await collect(sessions) == [{"done": True, "error": None, "text": "Done."}]


async def test_an_error_says_what_happened():
    message = "Claude Code could not sign in because the setup token was rejected."
    sessions = FakeSessions(events=[
        {"type": "turn_finished", "session_id": OURS, "is_error": True, "error": "authentication_failed", "text": message},
    ])
    assert await collect(sessions) == [{"done": True, "error": "authentication_failed", "text": message}]


async def test_a_turn_that_fails_before_running():
    sessions = FakeSessions(error=TurnError("Claude Code stopped unexpectedly."))
    assert await collect(sessions) == [{"done": True, "error": "failed", "text": "Claude Code stopped unexpectedly."}]


async def test_events_of_other_sessions_are_not_part_of_the_answer():
    other = {"type": "turn_event", "session_id": "2f6af861-eb56-4f75-ba62-6e7cd820517c",
             "event": text("not ours")["event"]}
    sessions = FakeSessions(events=[
        other, {"type": "session_updated", "session": {}}, text("ours"),
        {"type": "turn_finished", "session_id": OURS, "is_error": False, "error": None, "text": "ours"},
    ])
    assert [i for i in await collect(sessions) if "delta" in i] == [{"delta": "ours"}]


async def test_a_message_moved_to_a_new_session_still_gets_its_answer():
    # This session closed while the message waited: the answer came from a new session.
    sessions = FakeSessions(events=[], result=TurnResult("2f6af861-eb56-4f75-ba62-6e7cd820517c", "Hello!", False))
    assert await collect(sessions) == [{"done": True, "error": None, "text": "Hello!"}]


def test_text_delta_reads_only_the_assistants_text():
    assert text_delta(text("hi")) == ("hi", False)
    assert text_delta(text_block()) == (None, True)
    assert text_delta(stream_event({"type": "content_block_delta", "delta": {"type": "input_json_delta"}})) == (None, False)
    assert text_delta({"type": "turn_started", "session_id": OURS}) == (None, False)


# --- the routes ---------------------------------------------------------------------


@pytest.fixture
def client(tmp_path):
    token = AssistToken(tmp_path / "assist_token")
    sessions = FakeSessions(events=[
        text("Hi"), {"type": "turn_finished", "session_id": OURS, "is_error": False, "error": None, "text": "Hi"},
    ])
    app = FastAPI()
    app.include_router(assist_router(sessions, token))
    return TestClient(app), token, sessions


def test_check_with_the_token(client):
    http, token, _ = client
    assert http.get("/api/assist/check", headers={"Authorization": f"Bearer {token.value}"}).json() == {"ok": True}


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer wrong"}])
def test_nothing_without_the_token(client, headers):
    http, _, sessions = client
    assert http.get("/api/assist/check", headers=headers).status_code == 401
    response = http.post("/api/assist", headers=headers, json={"text": "hi", "source": {"key": "k"}})
    assert response.status_code == 401
    assert response.json() == {"error": "The token of HA Claude Code Assist is not valid."}
    assert sessions.resolved == []


def test_a_message_streams_as_lines_of_json(client):
    http, token, sessions = client
    response = http.post("/api/assist", headers={"Authorization": f"Bearer {token.value}"},
                         json={"text": "hello", "conversation_id": "ha-1", "source": {"key": "satellite.kitchen", "name": "Kitchen"}})
    assert response.headers["content-type"] == "application/x-ndjson"
    assert [json.loads(line) for line in response.text.splitlines()] == [
        {"delta": "Hi"}, {"done": True, "error": None, "text": ""}]
    assert sessions.resolved == [("voice", "satellite.kitchen", "ha-1", "Kitchen")]


@pytest.mark.parametrize("body", [{"text": "", "source": {"key": "k"}}, {"text": "hi"}, {"text": "hi", "source": {}}])
def test_a_message_needs_its_text_and_source(client, body):
    http, token, _ = client
    response = http.post("/api/assist", headers={"Authorization": f"Bearer {token.value}"}, json=body)
    assert response.status_code == 400
