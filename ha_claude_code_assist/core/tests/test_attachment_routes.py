from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ha_cca.attachment_routes import attachment_router

OURS = "8f14e45f-ceea-467a-9575-1f0a2f8a1c11"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


class FakeSessions:
    def __init__(self, root: Path):
        self.root = root

    def get(self, session_id):
        if session_id != OURS:
            raise KeyError("This session no longer exists.")

    def workdir(self, session_id):
        return self.root / session_id / "workdir"


@pytest.fixture
def client(tmp_path):
    app = FastAPI()
    app.include_router(attachment_router(FakeSessions(tmp_path)))
    return TestClient(app), tmp_path / OURS / "workdir" / "attachments"


def test_upload_saves_the_bytes_as_sent(client):
    http, folder = client
    response = http.post(f"/api/sessions/{OURS}/attachments", params={"name": "photo.png"}, content=PNG)
    assert response.status_code == 200 and response.json() == {"name": "photo.png", "size": len(PNG)}
    assert (folder / "photo.png").read_bytes() == PNG


def test_upload_twice_keeps_both(client):
    http, folder = client
    for _ in range(2):
        http.post(f"/api/sessions/{OURS}/attachments", params={"name": "photo.png"}, content=PNG)
    assert sorted(p.name for p in folder.iterdir()) == ["photo (2).png", "photo.png"]


def test_upload_with_a_path_in_the_name_stays_in_the_attachments(client):
    http, folder = client
    response = http.post(f"/api/sessions/{OURS}/attachments", params={"name": "../../options.json"}, content=b"{}")
    assert response.json()["name"] == "options.json" and (folder / "options.json").is_file()


@pytest.mark.parametrize("session_id", ["2f6af861-eb56-4f75-ba62-6e7cd820517c", "not-a-session"])
def test_upload_to_a_session_that_does_not_exist(client, session_id):
    http, folder = client
    response = http.post(f"/api/sessions/{session_id}/attachments", params={"name": "a.png"}, content=PNG)
    assert response.status_code == 404 and response.json() == {"error": "This session no longer exists."}
    assert not folder.exists()


def test_a_picture_is_served_safely(client):
    http, _ = client
    http.post(f"/api/sessions/{OURS}/attachments", params={"name": "photo.png"}, content=PNG)
    response = http.get(f"/api/sessions/{OURS}/attachments/photo.png")
    assert response.status_code == 200 and response.content == PNG
    assert response.headers["content-type"] == "image/png"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "sandbox" in response.headers["content-security-policy"]


@pytest.mark.parametrize("name", ["page.html", "drawing.svg", "bill.pdf", "notes.txt"])
def test_only_pictures_are_served(client, name):
    http, _ = client
    http.post(f"/api/sessions/{OURS}/attachments", params={"name": name}, content=b"<script>alert(1)</script>")
    assert http.get(f"/api/sessions/{OURS}/attachments/{name}").status_code == 404


def test_a_missing_picture_or_another_sessions(client):
    http, _ = client
    assert http.get(f"/api/sessions/{OURS}/attachments/none.png").status_code == 404
    assert http.get("/api/sessions/2f6af861-eb56-4f75-ba62-6e7cd820517c/attachments/a.png").status_code == 404


@pytest.mark.parametrize("name", ["photo.png", "page.html", "drawing.svg", "Power bill November.pdf"])
def test_any_file_can_be_downloaded_and_is_never_opened_as_a_page(client, name):
    http, _ = client
    saved = http.post(f"/api/sessions/{OURS}/attachments", params={"name": name}, content=b"<svg onload=alert(1)>").json()["name"]
    response = http.get(f"/api/sessions/{OURS}/attachments/{saved}/download")
    assert response.status_code == 200 and response.content == b"<svg onload=alert(1)>"
    assert response.headers["content-type"] == "application/octet-stream"
    assert response.headers["content-disposition"].startswith("attachment;")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "sandbox" in response.headers["content-security-policy"]


def test_download_of_a_missing_file_or_another_sessions(client):
    http, _ = client
    assert http.get(f"/api/sessions/{OURS}/attachments/none.pdf/download").status_code == 404
    assert http.get("/api/sessions/2f6af861-eb56-4f75-ba62-6e7cd820517c/attachments/a.pdf/download").status_code == 404
