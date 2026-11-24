from pathlib import Path

from ha_cca.transcripts import Transcripts

OURS = "8f14e45f-ceea-467a-9575-1f0a2f8a1c11"
OTHER = "2f6af861-eb56-4f75-ba62-6e7cd820517c"
CLAUDES = "337ccddc-edb0-464d-9e76-5effee12e96e"


def touch(path: Path, text: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_the_project_folder_is_named_as_claude_code_names_it(tmp_path):
    transcripts = Transcripts(tmp_path / "claude")
    workdir = Path(f"/data/sessions/{OURS}/workdir")
    assert transcripts.project_dir(workdir) == tmp_path / "claude" / "projects" / f"-data-sessions-{OURS}-workdir"
    assert transcripts.path(workdir, CLAUDES).name == f"{CLAUDES}.jsonl"


def test_a_transcript_is_found_by_the_sessions_working_directory_and_claudes_id(tmp_path):
    transcripts = Transcripts(tmp_path / "claude")
    workdir = Path(f"/data/sessions/{OURS}/workdir")
    touch(transcripts.path(workdir, CLAUDES), '{"type": "user", "message": {"role": "user", "content": "hi"}}\n')
    assert transcripts.exists(workdir, CLAUDES)
    assert not transcripts.exists(workdir, OTHER)
    assert not transcripts.exists(Path(f"/data/sessions/{OTHER}/workdir"), CLAUDES)


def test_remove_project_removes_only_that_sessions_project_folder(tmp_path):
    claude = tmp_path / "claude"
    transcripts = Transcripts(claude)
    ours, other = Path(f"/data/sessions/{OURS}/workdir"), Path(f"/data/sessions/{OTHER}/workdir")
    touch(transcripts.path(ours, CLAUDES), "{}")
    touch(transcripts.project_dir(ours) / CLAUDES / "tool-results" / "webfetch-1.png", "png")
    touch(transcripts.path(other, CLAUDES), "{}")
    touch(claude / "sessions" / "246.json", f'{{"sessionId": "{CLAUDES}"}}')  # Claude Code's own state

    assert transcripts.remove_project(ours) == [transcripts.project_dir(ours)]

    assert not transcripts.project_dir(ours).exists()
    assert transcripts.exists(other, CLAUDES)
    assert (claude / "sessions" / "246.json").exists()


def test_the_history_shows_attached_files_instead_of_their_lines(tmp_path):
    transcripts = Transcripts(tmp_path / "claude")
    workdir = Path(f"/data/sessions/{OURS}/workdir")
    text = f"which plant is this — a fern?\\n\\n[Attached file: {workdir}/attachments/plant.jpg]\\n[Attached file: {workdir}/attachments/bill.pdf]"
    touch(transcripts.path(workdir, CLAUDES),
          '{"type": "user", "timestamp": "t", "message": {"role": "user", "content": "' + text + '"}}\n')
    (item,) = transcripts.messages(workdir, CLAUDES, home_assistant=False)
    assert item["text"] == "which plant is this — a fern?"
    assert item["attachments"] == [{"name": "plant.jpg", "image": True}, {"name": "bill.pdf", "image": False}]


def test_remove_project_of_a_session_claude_never_started(tmp_path):
    transcripts = Transcripts(tmp_path / "claude")
    assert transcripts.remove_project(Path(f"/data/sessions/{OURS}/workdir")) == []


def test_remove_project_does_not_follow_a_link(tmp_path):
    claude = tmp_path / "claude"
    transcripts = Transcripts(claude)
    workdir = Path(f"/data/sessions/{OURS}/workdir")
    outside = touch(tmp_path / "outside" / "keep.txt", "keep")
    transcripts.project_dir(workdir).parent.mkdir(parents=True)
    transcripts.project_dir(workdir).symlink_to(outside.parent)
    assert transcripts.remove_project(workdir) == []
    assert outside.read_text() == "keep"
