"""HTTP routes for the files attached to a message: upload, and the pictures the panel shows.

Files go over HTTP, not the panel's WebSocket: a large upload must not hold up the answers
streaming on it. Home Assistant's Ingress lets through at most 16 MiB per request.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, Request, Response
from fastapi.responses import FileResponse, JSONResponse

from . import attachments
from .sessions import SessionManager

# A served file never runs as a page of Home Assistant's origin: only pictures are served, and
# the browser is told not to guess another type nor to run anything in them.
SAFE_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'none'; sandbox",
    "Cache-Control": "private, max-age=86400",
}


def attachment_router(sessions: SessionManager) -> APIRouter:
    router = APIRouter()

    def workdir(session_id: str) -> Path | None:
        try:
            sessions.get(session_id)
            return sessions.workdir(session_id)
        except (KeyError, ValueError):
            return None

    @router.post("/api/sessions/{session_id}/attachments")
    async def upload(session_id: str, name: str, request: Request) -> Response:
        folder = workdir(session_id)
        if folder is None:
            return JSONResponse({"error": "This session no longer exists."}, status_code=404)
        data = await request.body()
        saved = await asyncio.to_thread(attachments.save, folder, name, data)
        return JSONResponse({"name": saved, "size": len(data)})

    @router.get("/api/sessions/{session_id}/attachments/{name}")
    async def picture(session_id: str, name: str) -> Response:
        folder = workdir(session_id)
        file = attachments.path(folder, name) if folder is not None else None
        media_type = attachments.IMAGE_TYPES.get(Path(name).suffix.lower())
        if file is None or media_type is None:
            return JSONResponse({"error": "This picture is not available."}, status_code=404)
        return FileResponse(file, media_type=media_type, headers=SAFE_HEADERS)

    @router.get("/api/sessions/{session_id}/attachments/{name}/download")
    async def download(session_id: str, name: str) -> Response:
        """Any attached file, as a download: the browser saves it, never opens it as a page."""
        folder = workdir(session_id)
        file = attachments.path(folder, name) if folder is not None else None
        if file is None:
            return JSONResponse({"error": "This file is not available."}, status_code=404)
        return FileResponse(file, media_type="application/octet-stream", filename=name,
                            content_disposition_type="attachment", headers=SAFE_HEADERS)

    return router
