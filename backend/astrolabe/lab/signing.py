"""Ed25519 request-signature verification for the Lab machine endpoints.

Signed string: METHOD, PATH (no query string), TIMESTAMP and sha256_hex(body), joined by newlines.
Only public keys live here (not secret); private keys never leave the machines.
"""
from __future__ import annotations

import base64
import hashlib
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

PUBLIC_KEYS_B64: dict[str, str] = {
    "host": "ft3ahXh+cf8gqGCnTFUVpBb8ABGa3SSInrDWIYEqtLg=",
    "mac": "/2RTwa1W3d/5vI8GYrCkUu2eTEE/ZEh+hxufFLnfliA=",
}
MAX_SKEW_SECONDS = 300
MAX_BODY_BYTES = 2 * 1024 * 1024

_override: dict[str, str] | None = None


def set_public_keys_override(keys: dict[str, str] | None) -> None:
    """Test hook: replace the committed public keys (base64 raw Ed25519) or restore with None."""
    global _override
    _override = keys


def public_keys() -> dict[str, str]:
    return _override if _override is not None else PUBLIC_KEYS_B64


class SignatureError(Exception):
    pass


def signing_string(method: str, path: str, timestamp: str, body: bytes) -> bytes:
    digest = hashlib.sha256(body).hexdigest()
    return f"{method.upper()}\n{path}\n{timestamp}\n{digest}".encode()


def verify_signature(
    *,
    source: str | None,
    timestamp: str | None,
    signature: str | None,
    method: str,
    path: str,
    body: bytes,
    now: float | None = None,
) -> str:
    """Return the verified source name or raise SignatureError."""
    keys = public_keys()
    if not source or source not in keys:
        raise SignatureError("unknown source")
    if not timestamp or not signature:
        raise SignatureError("missing signature headers")
    try:
        ts = int(timestamp)
    except ValueError as exc:
        raise SignatureError("bad timestamp") from exc
    if abs((time.time() if now is None else now) - ts) > MAX_SKEW_SECONDS:
        raise SignatureError("stale timestamp")
    try:
        key = Ed25519PublicKey.from_public_bytes(base64.b64decode(keys[source]))
        key.verify(base64.b64decode(signature, validate=True),
                   signing_string(method, path, timestamp, body))
    except (InvalidSignature, ValueError) as exc:
        raise SignatureError("bad signature") from exc
    return source
