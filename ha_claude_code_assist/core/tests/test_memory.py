import json
import subprocess

import pytest

from ha_cca.memory import MemoryLimitError, MemoryStore


def commits(directory):
    out = subprocess.run(["git", "-C", str(directory), "log", "--format=%s"],
                         capture_output=True, text=True, check=True).stdout
    return out.splitlines()


@pytest.fixture
def store(tmp_path):
    return MemoryStore(tmp_path / "memory", max_entries=3, max_entry_length=40)


async def test_add_persists_and_commits(store):
    first = await store.add("The study is the room called Office", "claude", "conv-1")
    second = await store.add("  Evening   light at 40%  ", "user")
    assert (first.id, second.id) == (1, 2)
    assert second.text == "Evening light at 40%"  # whitespace normalised
    data = json.loads((store.directory / "memory.json").read_text())
    assert [e["id"] for e in data["entries"]] == [1, 2]
    assert data["entries"][0]["conversation_id"] == "conv-1"
    assert commits(store.directory) == ["Add memory 2 (user)", "Add memory 1 (claude)"]


async def test_reload_from_disk(store, tmp_path):
    await store.add("A fact", "user")
    reloaded = MemoryStore(tmp_path / "memory", max_entries=3, max_entry_length=40)
    assert [e.text for e in reloaded.entries()] == ["A fact"]


async def test_render_is_deterministic(store):
    assert store.render() == "(no entries)"
    await store.add("First", "user")
    await store.add("Second", "claude")
    assert store.render() == "- [1] First\n- [2] Second"


async def test_limits(store):
    with pytest.raises(MemoryLimitError, match="limit is 40"):
        await store.add("x" * 41, "user")
    with pytest.raises(MemoryLimitError, match="empty"):
        await store.add("   ", "user")
    for i in range(3):
        await store.add(f"fact {i}", "user")
    with pytest.raises(MemoryLimitError, match="full"):
        await store.add("one more", "user")


async def test_update_and_remove(store):
    entry = await store.add("Old text", "claude")
    updated = await store.update(entry.id, "New text")
    assert updated.text == "New text" and updated.created_by == "claude"
    await store.remove(entry.id, removed_by="user")
    assert store.entries() == []
    with pytest.raises(KeyError):
        await store.remove(entry.id, removed_by="user")


async def test_ids_are_never_reused(store, tmp_path):
    first = await store.add("First", "user")
    await store.remove(first.id, removed_by="user")
    assert (await store.add("Second", "user")).id == 2
    reloaded = MemoryStore(tmp_path / "memory", max_entries=3, max_entry_length=40)
    assert (await reloaded.add("Third", "user")).id == 3


async def test_listeners(store):
    calls = []
    unsubscribe = store.subscribe(lambda: calls.append(1))
    await store.add("A", "user")
    unsubscribe()
    await store.add("B", "user")
    assert calls == [1]
