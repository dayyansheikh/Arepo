# ruff: noqa: E501
"""Ed25519 request signing and a tiny HTTP helper for the Arepo Lab machine clients.

Contract: docs/lab/LAB_DASHBOARD_SPEC.md ("Request signing"). Headers sent on every machine request:
  X-Lab-Source: host|mac
  X-Lab-Timestamp: <unix seconds>
  X-Lab-Signature: base64(Ed25519 signature over "{METHOD}\\n{PATH}\\n{TIMESTAMP}\\n{sha256_hex(body)}")
PATH has no query string; GET bodies are empty (sha256 of b"").

The private key (PKCS8 PEM, ~/.arepo/lab/lab_ed25519.pem) never leaves the machine and is never printed.
Standard library plus `cryptography` only (host venv ~/arepo/.venv, Mac backend/.venv).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_API = "https://arepo-api.onrender.com"
DEFAULT_KEY = Path.home() / ".arepo" / "lab" / "lab_ed25519.pem"
TIMEOUT_S = 60  # Render free tier cold start
RETRIES = 1
SCHEMA = "arepo-lab-v1"


def api_base() -> str:
    return os.environ.get("AREPO_LAB_API", DEFAULT_API).rstrip("/")


def load_private_key(path: Path | str | None = None):
    from cryptography.hazmat.primitives import serialization

    p = Path(path) if path else Path(os.environ.get("AREPO_LAB_KEY", DEFAULT_KEY))
    return serialization.load_pem_private_key(p.read_bytes(), password=None)


def signing_string(method: str, path: str, timestamp: int | str, body: bytes) -> bytes:
    path = path.split("?", 1)[0]
    return f"{method.upper()}\n{path}\n{timestamp}\n{hashlib.sha256(body).hexdigest()}".encode()


def sign(key, method: str, path: str, timestamp: int | str, body: bytes = b"") -> str:
    return base64.b64encode(key.sign(signing_string(method, path, timestamp, body))).decode("ascii")


def signed_headers(key, source: str, method: str, path: str, body: bytes = b"", timestamp: int | None = None) -> dict:
    ts = int(time.time()) if timestamp is None else int(timestamp)
    return {
        "X-Lab-Source": source,
        "X-Lab-Timestamp": str(ts),
        "X-Lab-Signature": sign(key, method, path, ts, body),
    }


def request(method: str, path: str, source: str, key, body: bytes | dict | None = None,
            base: str | None = None, timeout: int = TIMEOUT_S, retries: int = RETRIES):
    """Signed request. Returns (status, parsed JSON | text | None). Never raises on HTTP/network errors:
    returns (0, "<error text>") when the server could not be reached. Re-signs (fresh timestamp) on each retry."""
    if isinstance(body, dict):
        body = json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
    body = body or b""
    url = (base or api_base()) + path
    last: tuple[int, object] = (0, "no attempt")
    for _attempt in range(retries + 1):
        headers = signed_headers(key, source, method, path, body)
        if body:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=body if method.upper() != "GET" else None, method=method.upper(),
                                     headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - https base, fixed host
                status, raw = resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            status, raw = exc.code, exc.read()
        except Exception as exc:  # noqa: BLE001 - URLError, timeout, ssl: report, retry once
            last = (0, f"{type(exc).__name__}: {exc}"[:300])
            continue
        last = (status, _parse(raw))
        if status < 500:
            return last
    return last


def _parse(raw: bytes):
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except ValueError:
        return raw.decode("utf-8", "replace")[:500]
