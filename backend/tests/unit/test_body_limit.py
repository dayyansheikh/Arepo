"""R2-04: outermost body-limit middleware and header pre-checks before body read."""
import asyncio

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from astrolabe.api.body_limit import BodyLimitMiddleware
from astrolabe.lab import signing


def _app():
    app = FastAPI()

    @app.post("/x")
    async def x(request: Request):
        return {"n": len(await request.body())}

    @app.post("/big")
    async def big(request: Request):
        return {"n": len(await request.body())}

    app.add_middleware(BodyLimitMiddleware, default_limit=100, path_limits={"/big": 1000})
    return app


def test_small_ok_and_per_path_limit():
    c = TestClient(_app())
    assert c.post("/x", content=b"a" * 100).json() == {"n": 100}
    assert c.post("/x", content=b"a" * 101).status_code == 413
    assert c.post("/big", content=b"a" * 1000).status_code == 200
    assert c.post("/big", content=b"a" * 1001).status_code == 413


def test_streamed_body_over_limit_is_413():
    c = TestClient(_app())

    def gen():
        for _ in range(5):
            yield b"a" * 50

    assert c.post("/x", content=gen()).status_code == 413


def test_asgi_lying_content_length_is_still_capped():
    app = _app()
    sent = []

    async def run():
        msgs = [{"type": "http.request", "body": b"a" * 60, "more_body": True},
                {"type": "http.request", "body": b"a" * 60, "more_body": False}]

        async def receive():
            return msgs.pop(0)

        async def send(m):
            sent.append(m)

        scope = {"type": "http", "method": "POST", "path": "/x", "raw_path": b"/x",
                 "query_string": b"", "headers": [(b"content-length", b"10")],
                 "server": ("t", 80), "client": ("c", 1), "scheme": "http",
                 "http_version": "1.1", "root_path": ""}
        await app(scope, receive, send)

    asyncio.run(run())
    assert sent[0]["status"] == 413


def test_signature_precheck_rejects_before_body():
    with pytest.raises(signing.SignatureError):
        signing.precheck_headers(source="nobody", timestamp="1", signature="x")
    with pytest.raises(signing.SignatureError):
        signing.precheck_headers(source="host", timestamp=None, signature="x")
    with pytest.raises(signing.SignatureError):
        signing.precheck_headers(source="host", timestamp="1", signature="x")
