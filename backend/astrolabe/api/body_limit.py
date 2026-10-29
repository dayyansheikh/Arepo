"""Outermost pure-ASGI request-body size limit (audit R2-04).

Rejects with 413 when ``Content-Length`` exceeds the limit, and also when the streamed bytes exceed
it (chunked / lying clients), before any route or dependency buffers the body. Default 64 KiB;
per-path overrides for the signed Lab snapshot upload.
"""
from __future__ import annotations

import json

DEFAULT_LIMIT = 64 * 1024
PATH_LIMITS: dict[str, int] = {"/api/lab/agent/snapshot": 2 * 1024 * 1024}

_BODY = json.dumps({"error": "payload_too_large", "detail": "Request body too large."}).encode()


class _TooLarge(Exception):
    pass


class BodyLimitMiddleware:
    def __init__(self, app, default_limit: int = DEFAULT_LIMIT,
                 path_limits: dict[str, int] | None = None) -> None:
        self.app = app
        self.default_limit = default_limit
        self.path_limits = PATH_LIMITS if path_limits is None else path_limits

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        limit = self.path_limits.get(scope.get("path", ""), self.default_limit)
        declared = None
        for k, v in scope.get("headers") or []:
            if k == b"content-length":
                try:
                    declared = int(v)
                except ValueError:
                    declared = None
                break
        started = False

        async def reject() -> None:
            await send({"type": "http.response.start", "status": 413, "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(_BODY)).encode()),
                (b"connection", b"close"),
            ]})
            await send({"type": "http.response.body", "body": _BODY})

        if declared is not None and declared > limit:
            await reject()
            return

        seen = 0

        async def limited_receive():
            nonlocal seen
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > limit:
                    raise _TooLarge()
            return message

        async def tracking_send(message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except _TooLarge:
            if not started:
                await reject()
