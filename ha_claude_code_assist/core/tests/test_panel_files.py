from fastapi import FastAPI
from fastapi.testclient import TestClient

from ha_cca.panel_files import add_panel_files


def client(tmp_path) -> TestClient:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text('<script src="./assets/index-abc123.js"></script>')
    (tmp_path / "assets" / "index-abc123.js").write_text("console.log('panel')")
    app = FastAPI()
    add_panel_files(app, tmp_path)
    return TestClient(app)


def test_the_page_is_asked_again_every_time(tmp_path):
    # An updated app must reach the browser: an old page would keep loading the old assets.
    response = client(tmp_path).get("/")
    assert response.status_code == 200 and "index-abc123.js" in response.text
    assert response.headers["cache-control"] == "no-cache"


def test_an_asset_is_kept_for_good(tmp_path):
    # Its name changes with its content, so a kept copy is never out of date.
    http = client(tmp_path)
    response = http.get("/assets/index-abc123.js")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"
    again = http.get("/assets/index-abc123.js", headers={"if-none-match": response.headers["etag"]})
    assert again.status_code == 304 and again.headers["cache-control"] == "public, max-age=31536000, immutable"


def test_a_missing_asset(tmp_path):
    assert client(tmp_path).get("/assets/index-old.js").status_code == 404
