import asyncio
import json
from pathlib import Path

import pytest

from ha_cca import attachments
from ha_cca.config import parse_options
from ha_cca.panel import Panel
from ha_cca.prompt import DEFAULTS, SECTIONS
from ha_cca.sessions import ClaudeSession, SessionRecord, SessionSettings
from ha_cca.transcripts import Transcripts

OURS = "8f14e45f-ceea-467a-9575-1f0a2f8a1c11"
CLAUDES = "337ccddc-edb0-464d-9e76-5effee12e96e"


class FakeSettings:
    def __init__(self):
        self.raw = {"model": "haiku", "claude_code_oauth_token": "token"}
        self.settings = parse_options(self.raw)

    async def update(self, changes):
        self.raw = {**self.raw, **changes}
        self.settings = parse_options(self.raw)
        return self.settings

    def token_status(self):
        return {"configured": False}


class FakeSessions:
    token_rejected_at = None

    def __init__(self, claude_id=None, root=Path("/data/sessions"), read_files=True, title="", channel="panel"):
        self.root = root
        self.runs = []
        self.record = SessionRecord(
            session_id=OURS, title=title, source={"channel": channel, "key": "u"}, conversation_ids=["c"],
            created_at="2026-01-01T00:00:00+00:00", last_activity="2026-01-01T00:00:00+00:00", closed_at=None,
            settings=SessionSettings("haiku", "low", False, True, read_files), claude=ClaudeSession(session_id=claude_id))

    async def resolve(self, channel, key, conversation_id, name=None):
        return self.record

    async def run(self, record, text, title=None, move_if_closed=True):
        self.runs.append({"text": text, "title": title, "move_if_closed": move_if_closed})

    def subscribe(self, listener):
        return lambda: None

    def get(self, session_id):
        if session_id != OURS:
            raise KeyError("This session no longer exists.")
        return self.record

    def workdir(self, session_id):
        return self.root / session_id / "workdir"

    def home_assistant_inputs(self, session_id):
        self.get(session_id)
        return [{"received_at": "2026-01-01T00:00:00+00:00", "input": {"text": "hi", "language": "it"}}]

    async def delete(self, session_id):
        self.get(session_id)


class FakeMemory:
    def subscribe(self, listener):
        return lambda: None


def make_panel(applied, sessions=None, transcripts=None):
    def on_settings_changed(changes):
        applied.append(changes)
    return Panel(sessions or FakeSessions(), FakeMemory(), FakeSettings(), transcripts=transcripts,
                 on_settings_changed=on_settings_changed, status=dict)


async def ask(panel, request):
    outbox = asyncio.Queue()
    await panel._handle({"id": 1, **request}, ("u", None), outbox)
    return outbox.get_nowait()


def drain(outbox: asyncio.Queue) -> list[dict]:
    items = []
    while not outbox.empty():
        items.append(outbox.get_nowait())
    return items


async def test_every_open_panel_hears_of_a_settings_change_once_it_is_applied():
    applied = []
    panel = make_panel(applied)
    saving, other = asyncio.Queue(), asyncio.Queue()
    panel._outboxes.update({saving, other})  # two open panels, as serve() registers them

    await panel._handle({"id": 1, "type": "settings/update", "changes": {"model": "opus"}}, ("u", None), saving)

    assert applied == [{"model": "opus"}]
    event = {"type": "event", "event": {"type": "settings_changed"}}
    assert drain(other) == [event]
    sent = drain(saving)
    assert sent[0] == event  # before the answer, so the panel that saved refreshes too
    assert sent[1]["success"] is True and sent[1]["result"]["values"]["model"] == "opus"


async def test_an_event_reaches_every_open_panel():
    panel = make_panel([])
    first, second = asyncio.Queue(), asyncio.Queue()
    panel._outboxes.update({first, second})
    panel.notify({"type": "status_changed"})
    assert drain(first) == drain(second) == [{"type": "event", "event": {"type": "status_changed"}}]


async def test_a_refused_change_tells_nobody():
    applied = []
    panel = make_panel(applied)
    saving, other = asyncio.Queue(), asyncio.Queue()
    panel._outboxes.update({saving, other})

    await panel._handle({"id": 1, "type": "settings/update", "changes": {"model": "gpt"}}, ("u", None), saving)

    assert applied == [] and drain(other) == []
    (answer,) = drain(saving)
    assert answer["success"] is False and answer["error"] == "The model must be haiku, sonnet or opus."


async def test_history_of_a_session_claude_never_answered_is_empty(tmp_path):
    panel = make_panel([], FakeSessions(claude_id=None), Transcripts(tmp_path))
    answer = await ask(panel, {"type": "sessions/history", "session_id": OURS})
    assert answer == {"id": 1, "type": "result", "success": True, "result": []}


async def test_history_whose_transcript_claude_code_removed_is_empty(tmp_path):
    panel = make_panel([], FakeSessions(claude_id=CLAUDES), Transcripts(tmp_path))
    answer = await ask(panel, {"type": "sessions/history", "session_id": OURS})
    assert answer["success"] is True and answer["result"] == []


async def test_history_reads_claudes_transcript_from_the_sessions_project_folder(tmp_path):
    transcripts = Transcripts(tmp_path)
    path = transcripts.path(Path(f"/data/sessions/{OURS}/workdir"), CLAUDES)
    path.parent.mkdir(parents=True)
    path.write_text('{"type": "user", "timestamp": "2026-01-01T00:00:00Z", "message": {"role": "user", "content": "hello"}}\n')
    panel = make_panel([], FakeSessions(claude_id=CLAUDES), transcripts)
    answer = await ask(panel, {"type": "sessions/history", "session_id": OURS})
    assert [item["text"] for item in answer["result"]] == ["hello"]


@pytest.mark.parametrize("channel, text, context", [
    ("home_assistant", "yes", "Asked about the garage."),
    ("panel", "<home_assistant_context>\nAsked about the garage.\n</home_assistant_context>\n\nyes", None),
])
async def test_only_a_home_assistant_session_shows_the_context_apart(tmp_path, channel, text, context):
    transcripts = Transcripts(tmp_path)
    path = transcripts.path(Path(f"/data/sessions/{OURS}/workdir"), CLAUDES)
    path.parent.mkdir(parents=True)
    message = "<home_assistant_context>\nAsked about the garage.\n</home_assistant_context>\n\nyes"
    path.write_text(json.dumps({"type": "user", "timestamp": "t", "message": {"role": "user", "content": message}}) + "\n")
    panel = make_panel([], FakeSessions(claude_id=CLAUDES, channel=channel), transcripts)
    (item,) = (await ask(panel, {"type": "sessions/history", "session_id": OURS}))["result"]
    assert item["text"] == text and item.get("context") == context


async def test_what_home_assistant_sent_with_each_message(tmp_path):
    panel = make_panel([], FakeSessions(channel="home_assistant"), Transcripts(tmp_path))
    answer = await ask(panel, {"type": "sessions/home_assistant", "session_id": OURS})
    assert answer["result"] == [{"received_at": "2026-01-01T00:00:00+00:00", "input": {"text": "hi", "language": "it"}}]


async def test_the_settings_show_every_section_of_every_prompt():
    panel = make_panel([])
    await ask(panel, {"type": "settings/update", "changes": {"prompt_home_assistant_identity": "You are Jarvis."}})
    view = (await ask(panel, {"type": "settings/get"}))["result"]
    assert list(view["prompts"]) == ["panel", "home_assistant"]
    assert list(view["prompts"]["panel"]) == list(SECTIONS)
    assert view["prompts"]["home_assistant"]["identity"] == {
        "option": "prompt_home_assistant_identity", "text": "You are Jarvis.", "default": DEFAULTS["home_assistant"]["identity"]}
    assert view["prompts"]["panel"]["identity"]["text"] == DEFAULTS["panel"]["identity"]
    assert not any(key.startswith("prompt_") for key in view["values"])


async def test_unknown_session_is_reported_plainly(tmp_path):
    panel = make_panel([], FakeSessions(), Transcripts(tmp_path))
    for command in ("sessions/history", "sessions/home_assistant", "sessions/delete"):
        answer = await ask(panel, {"type": command, "session_id": "2f6af861-eb56-4f75-ba62-6e7cd820517c"})
        assert answer["success"] is False and answer["error"] == "This session no longer exists."



# --- attachments ---------------------------------------------------------------


async def test_prepare_gives_the_session_to_upload_into(tmp_path):
    panel = make_panel([], FakeSessions(root=tmp_path))
    answer = await ask(panel, {"type": "chat/prepare", "conversation_id": "c"})
    assert answer["result"] == {"session_id": OURS, "empty": True}
    panel = make_panel([], FakeSessions(root=tmp_path, title="hello"))
    assert (await ask(panel, {"type": "chat/prepare", "conversation_id": "c"}))["result"]["empty"] is False


async def test_prepare_is_refused_when_the_session_cannot_open_files(tmp_path):
    panel = make_panel([], FakeSessions(root=tmp_path, read_files=False))
    answer = await ask(panel, {"type": "chat/prepare", "conversation_id": "c"})
    assert answer["success"] is False and "Read files" in answer["error"]


async def test_send_with_attachments_tells_claude_where_they_are(tmp_path):
    sessions = FakeSessions(root=tmp_path)
    workdir = sessions.workdir(OURS)
    attachments.save(workdir, "photo.jpg", b"jpeg")
    panel = make_panel([], sessions)
    answer = await ask(panel, {"type": "chat/send", "conversation_id": "c", "text": "what is it?",
                               "attachments": ["photo.jpg"]})
    await asyncio.sleep(0)
    assert answer["result"] == {"session_id": OURS}
    (run,) = sessions.runs
    assert run == {"text": f"what is it?\n\n[Attached file: {workdir}/attachments/photo.jpg]",
                   "title": "what is it?", "move_if_closed": False}


async def test_send_with_files_only_takes_their_names_as_title(tmp_path):
    sessions = FakeSessions(root=tmp_path)
    attachments.save(sessions.workdir(OURS), "bill.pdf", b"%PDF")
    panel = make_panel([], sessions)
    await ask(panel, {"type": "chat/send", "conversation_id": "c", "text": "", "attachments": ["bill.pdf"]})
    await asyncio.sleep(0)
    assert sessions.runs[0]["title"] == "bill.pdf"


async def test_send_without_attachments_is_unchanged(tmp_path):
    sessions = FakeSessions(root=tmp_path)
    panel = make_panel([], sessions)
    await ask(panel, {"type": "chat/send", "conversation_id": "c", "text": "hello"})
    await asyncio.sleep(0)
    assert sessions.runs == [{"text": "hello", "title": "hello", "move_if_closed": True}]


@pytest.mark.parametrize("name", ["missing.jpg", "../session.json", "../../options.json"])
async def test_send_with_a_file_that_is_not_there(tmp_path, name):
    sessions = FakeSessions(root=tmp_path)
    panel = make_panel([], sessions)
    answer = await ask(panel, {"type": "chat/send", "conversation_id": "c", "text": "x", "attachments": [name]})
    assert answer["success"] is False and "did not reach the assistant" in answer["error"]
    assert sessions.runs == []


async def test_send_nothing(tmp_path):
    panel = make_panel([], FakeSessions(root=tmp_path))
    answer = await ask(panel, {"type": "chat/send", "conversation_id": "c", "text": "  ", "attachments": []})
    assert answer["success"] is False and answer["error"] == "Write a message first."
