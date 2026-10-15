"""Snapshot metadata sidecar (research lab, multi-signal design Task 1 / feature a12).

Derived from the SAME Gamma page bodies the collector already fetched (no extra requests) and
written beside, never into, ``rows.csv.gz``/``manifest.json``: ``rows_ext.csv.gz`` plus
``ext_manifest.json``. Absent fields are empty (missing), never 0. Raw ``feeType`` is kept next to
the derived ``fee_category`` (frozen D120 prefix map, imported). Rows join the main snapshot on
(capture_id, market_id) and carry the token and event ids. Failure never affects the snapshot: the
sidecar is then marked ``missing`` and no rows file is written.
"""

from __future__ import annotations

import csv
import gzip
import json
import logging
from pathlib import Path
from typing import Any

from astrolabe.research_panel.pairing import fee_category, row_facts

from .extract import _event_id, _flag, _json_list, _token0, parse_num

EXT_VERSION = "snapshot-ext-v3"
log = logging.getLogger(__name__)

KEYS = ["capture_id", "received_utc", "page_index", "market_id", "condition_id",
        "clob_token_id_0", "clob_token_id_1", "event_id"]
MARKET_NUM = {
    "taker_base_fee": "takerBaseFee", "order_price_min_tick_size": "orderPriceMinTickSize",
    "order_min_size": "orderMinSize", "competitive": "competitive",
    "rewards_min_size": "rewardsMinSize", "rewards_max_spread": "rewardsMaxSpread",
    "volume_num": "volumeNum", "open_interest": "openInterest",
}
MARKET_FLAG = {"fees_enabled": "feesEnabled", "accepting_orders": "acceptingOrders"}
MARKET_TEXT = {"created_at": "createdAt", "start_date": "startDate",
               "uma_resolution_statuses": "umaResolutionStatuses"}
EVENT_NUM = {"event_open_interest": "openInterest", "event_comment_count": "commentCount",
             "event_volume": "volume", "event_liquidity": "liquidity"}
EVENT_TEXT = {"event_created_at": "createdAt"}
COLUMNS = [*KEYS, "fee_type", "fee_category", *MARKET_FLAG, *MARKET_NUM, *MARKET_TEXT,
           "clob_rewards", *EVENT_NUM, *EVENT_TEXT, "event_neg_risk_augmented",
           "fee_schedule", "event_ids", "series_slugs", "neg_risk_market_id",
           "parent_event_ids"]


def _text(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, (list, dict)):
        return json.dumps(v, sort_keys=True, separators=(",", ":"))
    return str(v)


def _json_col(values: list) -> str | None:
    return json.dumps(values, separators=(",", ":")) if values else None


def _parent_ids(m: dict, event_ids: list) -> str | None:
    """JSON list aligned with ``event_ids`` (same sorted order): each event's ``parentEventId`` or
    null. Blank only when the market has no event ids; an all-null list means "no parent"."""
    if not event_ids:
        return None
    par: dict = {}
    for e in (m.get("events") if isinstance(m.get("events"), list) else []):
        pid = e.get("parentEventId") if isinstance(e, dict) else None
        if pid not in (None, "") and e.get("id") is not None:
            par.setdefault(str(e["id"]), str(pid))
    return json.dumps([par.get(i) for i in event_ids], separators=(",", ":"))


def ext_row(m: dict, capture_id: str, received: str, page_index: int) -> dict | None:
    """Sidecar row for one Gamma market dict (None without a market id, as in ``market_row``)."""
    if m.get("id") is None:
        return None
    ev0 = next(iter(m["events"]), None) if isinstance(m.get("events"), list) else None
    ev0 = ev0 if isinstance(ev0, dict) else {}
    ids = _json_list(m.get("clobTokenIds"))
    tok1 = str(ids[1]) if ids and len(ids) > 1 and ids[1] not in (None, "") else None
    fee_type = m.get("feeType")
    facts = row_facts(m)  # same extraction D120 uses for GROUPING_LINKS (ALL events, not ev0)
    r: dict = {
        "capture_id": capture_id, "received_utc": received, "page_index": page_index,
        "market_id": str(m["id"]), "condition_id": m.get("conditionId"),
        "clob_token_id_0": _token0(m), "clob_token_id_1": tok1, "event_id": _event_id(m),
        "fee_type": _text(fee_type),
        "fee_category": fee_category(fee_type),
        "clob_rewards": _text(m.get("clobRewards")),
        "fee_schedule": _text(m.get("feeSchedule")),  # raw string kept verbatim
        "event_ids": _json_col(facts["event_ids"]),  # JSON lists, sorted unique; blank = none
        "series_slugs": _json_col(facts["series_slugs"]),
        "parent_event_ids": _parent_ids(m, facts["event_ids"]),  # v3, aligned with event_ids
        "neg_risk_market_id": facts["neg_risk_market_id"],
        "event_neg_risk_augmented": _flag(ev0.get("negRiskAugmented")),
    }
    r.update({k: _flag(m.get(s)) for k, s in MARKET_FLAG.items()})
    r.update({k: parse_num(m.get(s)) for k, s in MARKET_NUM.items()})
    r.update({k: _text(m.get(s)) for k, s in MARKET_TEXT.items()})
    r.update({k: parse_num(ev0.get(s)) for k, s in EVENT_NUM.items()})
    r.update({k: _text(ev0.get(s)) for k, s in EVENT_TEXT.items()})
    return r


class SidecarBuilder:
    """Accumulates sidecar rows page by page; any internal error disables it (never raises)."""

    def __init__(self) -> None:
        self.rows: list[dict] = []
        self.error: str | None = None

    def add_page(self, markets: list, capture_id: str, received: str, page_index: int) -> None:
        if self.error:
            return
        try:
            new = [ext_row(m, capture_id, received, page_index)
                   for m in markets if isinstance(m, dict)]
            self.rows.extend(r for r in new if r is not None)
        except Exception as exc:  # fail-safe: the main snapshot must still complete
            self.error = f"{type(exc).__name__}: {exc}"
            self.rows = []
            log.exception("snapshot sidecar disabled")

    def write(self, tmp: Path, kept: list[dict], main_state: str, capture_id: str) -> None:
        """Write rows_ext.csv.gz + ext_manifest.json aligned 1:1 to the kept main rows."""
        manifest: dict = {"ext_version": EXT_VERSION, "capture_id": capture_id,
                          "main_state": main_state, "columns": COLUMNS}
        try:
            if self.error:
                raise RuntimeError(self.error)
            keep = {(r["market_id"], r["received_utc"], r["page_index"]) for r in kept}
            n = 0
            part = tmp / "rows_ext.csv.gz.part"
            with gzip.open(part, "wt", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=COLUMNS)
                w.writeheader()
                for r in self.rows:
                    if (r["market_id"], r["received_utc"], r["page_index"]) in keep:
                        w.writerow(r)
                        n += 1
            if n != len(kept):
                raise RuntimeError(f"alignment {n} != {len(kept)}")
            part.rename(tmp / "rows_ext.csv.gz")
            manifest.update(sidecar_status="complete" if main_state == "complete"
                            else "partial_capture", row_count=n)
        except Exception as exc:
            log.exception("snapshot sidecar write failed")
            (tmp / "rows_ext.csv.gz.part").unlink(missing_ok=True)
            (tmp / "rows_ext.csv.gz").unlink(missing_ok=True)
            manifest.update(sidecar_status="missing", error=f"{type(exc).__name__}: {exc}")
        try:
            (tmp / "ext_manifest.json").write_text(json.dumps(manifest, indent=1))
        except Exception:
            log.exception("ext_manifest write failed")
