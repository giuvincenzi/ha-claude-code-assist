from pathlib import Path

import pytest

from ha_cca import attachments

OURS = "8f14e45f-ceea-467a-9575-1f0a2f8a1c11"


@pytest.mark.parametrize("given, safe", [
    ("photo.jpg", "photo.jpg"),
    ("Power bill – November.pdf", "Power bill – November.pdf"),
    ("../../options.json", "options.json"),
    ("/data/options.json", "options.json"),
    ("C:\\Users\\me\\photo.png", "photo.png"),
    (".hidden", "hidden"),
    ("...", "file"),
    ("", "file"),
    ("bad\x00name\n.txt", "badname.txt"),
    ("x" * 300 + ".jpeg", "x" * 115 + ".jpeg"),
])
def test_safe_name(given, safe):
    assert attachments.safe_name(given) == safe


def test_a_file_is_saved_exactly_as_sent(tmp_path):
    data = bytes(range(256)) * 1000
    name = attachments.save(tmp_path, "photo.jpg", data)
    assert name == "photo.jpg"
    assert (tmp_path / "attachments" / "photo.jpg").read_bytes() == data


def test_a_second_file_with_the_same_name_never_overwrites_the_first(tmp_path):
    assert attachments.save(tmp_path, "photo.jpg", b"first") == "photo.jpg"
    assert attachments.save(tmp_path, "photo.jpg", b"second") == "photo (2).jpg"
    assert attachments.save(tmp_path, "photo.jpg", b"third") == "photo (3).jpg"
    assert (tmp_path / "attachments" / "photo.jpg").read_bytes() == b"first"


def test_a_name_with_folders_stays_in_the_attachments(tmp_path):
    name = attachments.save(tmp_path, "../../session.json", b"x")
    assert name == "session.json" and (tmp_path / "attachments" / "session.json").is_file()
    assert not (tmp_path.parent / "session.json").exists()


def test_path_finds_only_saved_files_by_their_own_name(tmp_path):
    attachments.save(tmp_path, "photo.jpg", b"x")
    assert attachments.path(tmp_path, "photo.jpg") == tmp_path / "attachments" / "photo.jpg"
    for name in ("missing.jpg", "../workdir", "../attachments/photo.jpg", "", "."):
        assert attachments.path(tmp_path, name) is None


def test_path_does_not_follow_a_link(tmp_path):
    (tmp_path / "attachments").mkdir()
    (tmp_path / "secret.txt").write_text("secret")
    (tmp_path / "attachments" / "secret.txt").symlink_to(tmp_path / "secret.txt")
    assert attachments.path(tmp_path, "secret.txt") is None


def test_the_message_tells_claude_where_the_files_are_and_the_history_finds_them_again():
    workdir = Path(f"/data/sessions/{OURS}/workdir")
    message = attachments.message("which plant is this — a fern?", workdir, ["plant.jpg", "plant (2).jpg"])
    assert message == (f"which plant is this — a fern?\n\n[Attached file: /data/sessions/{OURS}/workdir/attachments/plant.jpg]\n"
                       f"[Attached file: /data/sessions/{OURS}/workdir/attachments/plant (2).jpg]")
    assert attachments.split_attachments(message, workdir) == ("which plant is this — a fern?", ["plant.jpg", "plant (2).jpg"])


def test_a_message_with_files_only():
    workdir = Path(f"/data/sessions/{OURS}/workdir")
    message = attachments.message("  ", workdir, ["bill.pdf"])
    assert message == f"[Attached file: /data/sessions/{OURS}/workdir/attachments/bill.pdf]"
    assert attachments.split_attachments(message, workdir) == ("", ["bill.pdf"])


def test_a_message_without_files_is_left_as_it_is():
    workdir = Path(f"/data/sessions/{OURS}/workdir")
    assert attachments.message("hello", workdir, []) == "hello"
    assert attachments.split_attachments("hello\n\nworld", workdir) == ("hello\n\nworld", [])


@pytest.mark.parametrize("text", [
    "[Attached file: /etc/passwd]",  # not this session's attachments
    "[Attached file: /data/sessions/2f6af861-eb56-4f75-ba62-6e7cd820517c/workdir/attachments/x.jpg]",
    f"[Attached file: /data/sessions/{OURS}/workdir/attachments/x.jpg]\nand some text after",  # not at the end
    "please write [Attached file: like this] in the answer",
])
def test_only_lines_written_by_the_app_count_as_files(text):
    workdir = Path(f"/data/sessions/{OURS}/workdir")
    assert attachments.split_attachments(text, workdir) == (text, [])
