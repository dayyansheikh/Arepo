"""Reference signer for Lab clients (mirrors signing.verify_signature)."""
from __future__ import annotations

import base64

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .signing import signing_string


def sign(
    private_key: Ed25519PrivateKey,
    method: str,
    path: str,
    body: bytes,
    ts: int,
    *,
    source: str,
) -> dict[str, str]:
    """Return the X-Lab-* headers. ``path`` has no query string; ``body`` is b"" for GET."""
    sig = private_key.sign(signing_string(method, path, str(ts), body))
    return {
        "X-Lab-Source": source,
        "X-Lab-Timestamp": str(ts),
        "X-Lab-Signature": base64.b64encode(sig).decode(),
    }
