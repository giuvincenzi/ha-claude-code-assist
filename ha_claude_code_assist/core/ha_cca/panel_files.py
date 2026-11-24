"""The panel's own files: its page and the assets Vite builds, each named with a hash of its content.

- The page is served with `Cache-Control: no-cache`, so the browser asks every time whether it
  changed. Without it a browser may keep the page of an older version after the app is updated,
  and keep loading the assets that page names.
- An asset never changes under the same name, so the browser keeps it for as long as it likes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

PAGE_CACHE = "no-cache"
ASSET_CACHE = "public, max-age=31536000, immutable"


class _Assets(StaticFiles):
    def file_response(self, *args: Any, **kwargs: Any) -> Response:
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = ASSET_CACHE
        return response


def add_panel_files(app: FastAPI, web_dir: Path) -> None:
    """Serves the page at / and the assets under /assets."""

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(web_dir / "index.html", headers={"Cache-Control": PAGE_CACHE})

    if (web_dir / "assets").is_dir():
        app.mount("/assets", _Assets(directory=web_dir / "assets"), name="assets")
