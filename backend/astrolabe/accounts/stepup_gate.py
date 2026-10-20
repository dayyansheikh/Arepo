"""Site-wide security-key gate for accounts that have registered a hardware key / passkey.

Once a user has a registered WebAuthn credential (see ``astrolabe.lab.security_keys``), every
endpoint that acts as that user needs a live step-up in addition to the password session. This is
enforced at the single place every cookie session is resolved, so no route can forget it:

* :class:`StepUpJWTStrategy` resolves the session cookie as usual and, for a locked user, returns
  *no user* (so optional-user endpoints behave as signed out and nothing personal leaks) and flags
  the request as locked;
* :class:`StepUpMiddleware` puts the request's step-up cookie and path in a context variable for
  the strategy, and turns the resulting 401 of a locked request into
  ``403 {"detail": {"code": "hardware_key_required", ...}}`` so the UI can show the unlock screen.

Exempt: sign-out and the ``/api/lab/webauthn/*`` ceremony endpoints (which apply their own
checks). Machine-signed ``/api/lab/agent/*`` endpoints never read the session cookie at all.
"""
from __future__ import annotations

import json
from contextvars import ContextVar
from typing import Any

from fastapi_users.authentication import JWTStrategy
from starlette.requests import cookie_parser

from ..domain.models import utcnow

EXEMPT_PREFIXES = ("/api/auth/logout", "/api/lab/webauthn/")
LOCKED_CODE = "hardware_key_required"

_request_ctx: ContextVar[dict[str, Any] | None] = ContextVar("arepo_stepup_ctx", default=None)


def is_exempt(path: str) -> bool:
    return any(path == p or path.startswith(p) for p in EXEMPT_PREFIXES)


def locked_body(keys: int) -> dict:
    return {"detail": {
        "code": LOCKED_CODE,
        "message": "Tap your security key to continue." if keys
        else "Register a security key to continue.",
        "keys": keys,
    }}


class StepUpJWTStrategy(JWTStrategy):
    async def read_token(self, token, user_manager):  # type: ignore[override]
        user = await super().read_token(token, user_manager)
        if user is None:
            return None
        from ..lab import security_keys  # local import: lab models import accounts models

        ctx = _request_ctx.get()
        path = ctx["path"] if ctx else ""
        if ctx is not None and is_exempt(path):
            return user
        stepup_token = ctx["stepup"] if ctx else None
        session = user_manager.user_db.session
        keys = await security_keys.user_locked(session, user, stepup_token, utcnow())
        if keys is None:
            return user
        if ctx is not None:
            ctx["locked"] = keys
        return None


class StepUpMiddleware:
    """Pure ASGI (shares the request task's context with the dependencies)."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        from ..lab.security_keys import STEPUP_COOKIE

        cookie_header = ""
        for k, v in scope.get("headers") or []:
            if k == b"cookie":
                cookie_header = v.decode("latin-1")
                break
        ctx: dict[str, Any] = {
            "path": scope.get("path", ""),
            "stepup": cookie_parser(cookie_header).get(STEPUP_COOKIE) if cookie_header else None,
            "locked": None,
        }
        reset = _request_ctx.set(ctx)
        replaced = False

        async def _send(message) -> None:
            nonlocal replaced
            if (message["type"] == "http.response.start" and message["status"] == 401
                    and ctx["locked"] is not None):
                replaced = True
                body = json.dumps(locked_body(ctx["locked"])).encode()
                await send({"type": "http.response.start", "status": 403, "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"cache-control", b"no-store"),
                ]})
                await send({"type": "http.response.body", "body": body})
                return
            if replaced:
                return  # swallow the original 401 body
            await send(message)

        try:
            await self.app(scope, receive, _send)
        finally:
            _request_ctx.reset(reset)
