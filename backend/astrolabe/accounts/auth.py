"""Authentication backend and the FastAPIUsers instance.

Sessions use a secure httpOnly cookie carrying a JWT (signed with ``AUTH_SECRET``). The cookie
is SameSite=lax and marked Secure in production. Login requires a verified email.
"""
from __future__ import annotations

import uuid

from fastapi_users import FastAPIUsers
from fastapi_users.authentication import (
    AuthenticationBackend,
    CookieTransport,
    JWTStrategy,
)

from ..config import get_settings
from .manager import get_user_manager
from .models import User


def _cookie_transport() -> CookieTransport:
    s = get_settings()
    return CookieTransport(
        cookie_name=s.auth_cookie_name,
        cookie_max_age=s.auth_token_lifetime_seconds,
        cookie_secure=s.auth_cookie_secure,
        cookie_httponly=True,
        cookie_samesite="lax",
    )


def _jwt_strategy() -> JWTStrategy:
    s = get_settings()
    return JWTStrategy(secret=s.auth_secret, lifetime_seconds=s.auth_token_lifetime_seconds)


auth_backend = AuthenticationBackend(
    name="cookie",
    transport=_cookie_transport(),
    get_strategy=_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

# Dependencies for route protection. ``verified=True`` means both active AND verified.
current_active_user = fastapi_users.current_user(active=True)
current_verified_user = fastapi_users.current_user(active=True, verified=True)
current_optional_user = fastapi_users.current_user(active=True, optional=True)
