"""Wallet sidecar for ``trade_sample`` (research lab; descriptive wallet-behaviour data).

Derived from the SAME ``/trades`` response bodies the sampler already fetched (no extra requests)
and written beside, never into, ``trades.csv.gz`` / ``features.csv.gz`` / ``manifest.json``:
``wallets.csv.gz`` plus ``wallets_manifest.json``.

Privacy: the Data API ``proxyWallet`` is converted at parse time to an HMAC-SHA256 keyed hash
(key file ``~/.arepo/wallet_hash_key``, mode 600, created once if absent and never printed or
committed). Raw addresses are never stored, logged or returned by this module. The key file's
bytes are used verbatim as the HMAC key, so any process that created the file first (for
example a historical backfill) yields identical hashes. Addresses are lower-cased before hashing.

Nothing here labels any wallet or trade as insider or informed trading. A hash is only a stable
pseudonymous identifier for "the same address".

Fail-safe: any error disables the sidecar only. The main sample still completes and the sidecar
manifest records ``sidecar_status: "missing"``.
"""

from __future__ import annotations

import gzip
import hashlib
import hmac
import io
import json
import logging
import os
import secrets
from pathlib import Path

log = logging.getLogger(__name__)

WALLET_VERSION = "wallet-sidecar-v1"
KEY_ENV = "AREPO_WALLET_HASH_KEY_PATH"
DEFAULT_KEY_PATH = Path.home() / ".arepo" / "wallet_hash_key"
WALLET_COLS = ["market_id", "condition_id", "ts", "side", "outcome_index", "asset", "size",
               "price", "wallet_hash"]


def key_path() -> Path:
    env = os.environ.get(KEY_ENV)
    return Path(env) if env else DEFAULT_KEY_PATH


def load_or_create_key(path: Path | None = None) -> bytes:
    """Return the HMAC key, creating the file atomically with mode 600 if (and only if) absent.

    Create-if-absent: the candidate is written to a private temp file and hard-linked into place
    (``os.link`` fails if the target exists), so a concurrent creator never gets overwritten and a
    reader never sees a partial key.
    """
    path = Path(path) if path else key_path()
    if not path.exists():
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        tmp = path.with_name(f"{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(secrets.token_hex(32).encode())
                fh.flush()
                os.fsync(fh.fileno())
            try:
                os.link(tmp, path)
            except FileExistsError:
                pass  # someone else won the race; use theirs
        finally:
            tmp.unlink(missing_ok=True)
    key = path.read_bytes()  # verbatim: text or raw bytes, whoever created it
    if not key:
        raise ValueError("wallet hash key file is empty")
    return key


def hash_wallet(key: bytes, address: object) -> str | None:
    """Keyed hash of an address (lower-cased); None for missing/blank input."""
    if address is None:
        return None
    s = str(address).strip().lower()
    if not s:
        return None
    return hmac.new(key, s.encode(), hashlib.sha256).hexdigest()


class WalletSidecar:
    """Accumulates hashed wallet rows per market; any internal error disables it (never raises)."""

    def __init__(self, key_file: Path | None = None) -> None:
        self.rows: list[dict] = []
        self.error: str | None = None
        self.n_missing_wallet = 0
        self._key: bytes | None = None
        try:
            self._key = load_or_create_key(key_file)
        except Exception as exc:  # fail-safe: the main sample must still complete
            self.error = type(exc).__name__
            log.warning("wallet sidecar disabled (%s)", type(exc).__name__)

    def add_market(self, body: bytes, market_id: str, condition_id: str,
                   max_ts: float) -> None:
        """Parse a response body again for wallet fields; keeps trades with ts <= ``max_ts``
        (the same rule the main sample uses), in the same order as the main ``trades.csv.gz``."""
        if self.error or self._key is None:
            return
        try:
            data = json.loads(body)
            if not isinstance(data, list):
                raise ValueError("not a list")
            parsed = []
            for it in data:
                try:
                    ts = int(it["timestamp"])
                    side = str(it["side"]).upper()
                    price, size = float(it["price"]), float(it["size"])
                except (KeyError, TypeError, ValueError):
                    continue  # malformed: also skipped by the main parser
                oi = it.get("outcomeIndex")
                parsed.append({
                    "market_id": market_id, "condition_id": condition_id, "ts": ts,
                    "side": side, "outcome_index": None if oi is None else int(oi),
                    "asset": None if it.get("asset") is None else str(it["asset"]),
                    "size": size, "price": price,
                    "wallet_hash": hash_wallet(self._key, it.get("proxyWallet")),
                })
            parsed.sort(key=lambda t: -t["ts"])  # stable, as parse_trades
            kept = [t for t in parsed if t["ts"] <= max_ts]
            self.n_missing_wallet += sum(1 for t in kept if t["wallet_hash"] is None)
            self.rows.extend(kept)
        except Exception as exc:
            self.error = type(exc).__name__
            self.rows = []
            log.warning("wallet sidecar disabled (%s)", type(exc).__name__)

    def write(self, out: Path, main_state: str) -> dict:
        """Write wallets.csv.gz + wallets_manifest.json. Never raises."""
        import pandas as pd

        manifest: dict = {"wallet_version": WALLET_VERSION, "main_state": main_state,
                          "columns": WALLET_COLS, "hash": "HMAC-SHA256, key not recorded"}
        try:
            if self.error:
                raise RuntimeError(self.error)
            df = pd.DataFrame(self.rows, columns=WALLET_COLS)
            buf = io.BytesIO()
            with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
                gz.write(df.to_csv(index=False).encode())
            _atomic(out / "wallets.csv.gz", buf.getvalue())
            manifest.update(sidecar_status="complete" if main_state == "complete"
                            else "partial_capture", row_count=len(df),
                            rows_missing_wallet=self.n_missing_wallet)
        except Exception as exc:
            log.warning("wallet sidecar write failed (%s)", type(exc).__name__)
            (out / "wallets.csv.gz").unlink(missing_ok=True)
            manifest.update(sidecar_status="missing", error=type(exc).__name__)
        try:
            _atomic(out / "wallets_manifest.json",
                    (json.dumps(manifest, indent=1) + "\n").encode())
        except Exception:
            log.warning("wallet sidecar manifest write failed")
        return manifest


def _atomic(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
