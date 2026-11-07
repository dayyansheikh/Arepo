"""Public, allow-listed projection of the signal engine's section of the latest host Lab snapshot.

The research host already pushes the engine's dashboard and the champion's per-market feed to the
signed ``/lab`` snapshot (owner-only). This module builds the only view of it that may be public:

* the champion's ``dir_2h`` signal strength for the feed's top markets (no 6h/24h, no ``res_7d``);
* the champion's prospective ``dir_2h`` record;
* a ``dir_2h`` leaderboard of non-embargoed models; embargoed models keep only their id and a
  ``hidden_until`` date, with no numbers.

Every field is copied by an explicit allow-list, so anything new the host adds stays private. The
embargo is re-checked here against the request time and fails safe: an unparseable embargo date,
or a model missing from the snapshot's model list, hides the row. A champion under embargo drops
the whole feed. Wording is "signal strength": forecast quality only, never a profit claim.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

PUBLIC_SCHEMA = "arepo-public-signals-v1"
TARGET = "dir_2h"
FEED_STALE_AFTER = timedelta(hours=6)
MAX_ROWS = 20
DEFAULT_MIN_DAYS = 14  # promotion rule minimum (DESIGN_V1); the snapshot's value wins
NOTICE = (
    "Research only. Signal strength is forecast quality of the Polymarket mid's direction "
    "over the next 2 hours, scored prospectively. It is not a probability of profit, not an "
    "edge claim and not advice."
)

_MARKET_FIELDS = ("market_id", "title", "url", "category", "mid", "spread", "hours_to_end")
_BAND_FIELDS = ("days", "log_loss", "brier", "cal_slope", "cal_intercept")
_RECORD_FIELDS = ("days", "n", "auc", "brier", "log_loss", "cal_slope", "cal_intercept")


def _parse(value) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        if len(value) == 10:  # date-only embargo: hidden through the whole UTC day
            return datetime.fromisoformat(value).replace(tzinfo=UTC) + timedelta(days=1)
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _hidden_until(model: dict, now: datetime) -> str | None:
    """The embargo date to show while a model is embargoed, else None. Fails safe."""
    until = model.get("embargoed_until")
    if until in (None, ""):
        return None
    t = _parse(until)
    if t is None:
        return str(until)[:32] or "unknown"
    return str(until)[:32] if t > now else None


def band(s: float) -> str:
    """Confidence label on |signal strength|, cut-offs declared in signal-engine DESIGN_V1 §62."""
    a = abs(s)
    return "strong" if a >= 0.25 else "moderate" if a >= 0.10 else "weak"


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _record(row: dict) -> dict:
    return {k: _num(row.get(k)) for k in _RECORD_FIELDS}


def _market(row: dict) -> dict | None:
    s = _num(row.get("s_2h"))
    if s is None:
        return None
    out = {k: row.get(k) for k in _MARKET_FIELDS}
    for k in ("title", "url", "category"):
        out[k] = str(out[k])[:300] if isinstance(out[k], str) else None
    if not (isinstance(out["url"], str) and out["url"].startswith("https://polymarket.com/")):
        out["url"] = None
    for k in ("market_id", "mid", "spread", "hours_to_end"):
        out[k] = _num(out[k])
    out["signal_strength"] = s
    out["confidence"] = band(s)
    return out


def _bands(b) -> list:
    """The champion's confidence-band record (DESIGN_V1 §62): proper scores only, and only for
    bands meeting the declared minimum size (the host marks the rest ``unavailable``)."""
    if not isinstance(b, dict):
        return []
    out = []
    for r in b.get("rows") or []:
        if not (isinstance(r, dict) and r.get("band") in ("strong", "moderate", "weak")):
            continue
        row = {
            "band": r["band"],
            "n": _num(r.get("n")),
            "events": _num(r.get("events")),
            "status": "ok" if r.get("status") == "ok" else "unavailable",
        }
        if row["status"] == "ok":
            row.update({k: _num(r.get(k)) for k in _BAND_FIELDS})
        out.append(row)
    return out


def _leaderboard(se: dict, models: dict[str, dict], champion_id: str | None, now: datetime) -> list:
    rows = {}
    pros = se.get("prospective")
    for r in (pros.get("rows") if isinstance(pros, dict) else None) or []:
        if isinstance(r, dict) and r.get("target") == TARGET and isinstance(r.get("model_id"), str):
            rows[r["model_id"]] = r
    promo = se.get("promotion")
    min_days = _num(promo.get("min_days")) if isinstance(promo, dict) else None
    min_days = min_days or DEFAULT_MIN_DAYS
    board = []
    for mid, m in models.items():
        hidden = _hidden_until(m, now)
        entry = {
            "model_id": mid,
            "family": str(m.get("family") or "")[:60],
            "role": "champion" if mid == champion_id else "challenger",
        }
        if hidden is not None:
            board.append({**entry, "hidden_until": hidden})
        elif mid in rows:
            rec = _record(rows[mid])
            board.append({**entry, **rec, "provisional": (rec["days"] or 0) < min_days})
    scored = [b for b in board if "hidden_until" not in b]
    # Champion first, then models with the promotion rule's minimum days, each by log loss (a
    # proper score; lower is better). AUC alone would rank a 2-day-old model first.
    inf = float("inf")
    scored.sort(key=lambda b: (b["role"] != "champion", b["provisional"], b["log_loss"] or inf))
    return scored + sorted((b for b in board if "hidden_until" in b), key=lambda b: b["model_id"])


def project(payload: dict, received_at: datetime | None, now: datetime) -> dict:
    """Allow-listed public view of a host snapshot payload; ``status`` says what is missing."""
    out = {
        "schema": PUBLIC_SCHEMA,
        "notice": NOTICE,
        "target": TARGET,
        "server_time": now.isoformat(),
        "snapshot_received_at": received_at.isoformat() if received_at else None,
        "status": "unavailable",
        "champion": None,
        "feed": None,
        "leaderboard": [],
    }
    se = payload.get("signal_engine") if isinstance(payload, dict) else None
    if not isinstance(se, dict) or se.get("schema") != "se-dash-v1":
        return out
    models = {
        m["model_id"]: m
        for m in se.get("models") or []
        if isinstance(m, dict)
        and isinstance(m.get("model_id"), str)
        and m.get("status", "active") == "active"
    }
    champ = se.get("champion")
    champ = champ.get("model_id") if isinstance(champ, dict) else None
    champ_ok = champ in models and _hidden_until(models[champ], now) is None
    out["leaderboard"] = _leaderboard(se, models, champ, now)
    out["status"] = "ok"
    if not champ_ok:
        out["status"] = "champion_hidden"
        return out
    out["champion"] = {"model_id": champ, "family": str(models[champ].get("family") or "")[:60]}
    feed = se.get("feed")
    if not (
        isinstance(feed, dict)
        and feed.get("schema") == "se-feed-v1"
        and (feed.get("champion") or {}).get("model_id") == champ
    ):
        out["status"] = "no_feed"
        return out
    origin = _parse(feed.get("origin_utc"))
    stale = origin is None or now - origin > FEED_STALE_AFTER or bool(feed.get("stale"))
    record = [
        r
        for r in ((feed.get("track_record") or {}).get("rows") or [])
        if isinstance(r, dict) and r.get("target") == TARGET
    ]
    out["feed"] = {
        "origin_utc": origin.isoformat() if origin else None,
        "prediction_written_utc": str(feed.get("prediction_written_utc") or "")[:40] or None,
        "prediction_sha256": str(feed.get("prediction_sha256") or "")[:64] or None,
        "stale": stale,
        "top_up": [
            m
            for m in map(_market, [r for r in feed.get("top_up") or [] if isinstance(r, dict)])
            if m is not None and m["signal_strength"] > 0
        ][:MAX_ROWS],
        "top_down": [
            m
            for m in map(_market, [r for r in feed.get("top_down") or [] if isinstance(r, dict)])
            if m is not None and m["signal_strength"] < 0
        ][:MAX_ROWS],
        "track_record": _record(record[0]) if record else None,
        "days_scored": _num((feed.get("track_record") or {}).get("days_scored")),
        "bands": _bands(feed.get("bands")),
    }
    if stale:
        out["status"] = "stale"
    return out


def project_text(payload_text: str, received_at: datetime | None, now: datetime) -> dict:
    try:
        payload = json.loads(payload_text)
    except ValueError:
        payload = None
    return project(payload if isinstance(payload, dict) else {}, received_at, now)
