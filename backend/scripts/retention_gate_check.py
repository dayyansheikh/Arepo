#!/usr/bin/env python3
"""Read-only check of the snapshot/sweep retention gate.

See docs/research_lab/data_catalogue/RETENTION.md ("Gate release"). The gate opens on MANIFEST
COMPLETENESS, not job status: for each creative-batch backfill, every complete capture in its
window (host complete manifests plus release-only captures from the data catalogue) must be in
the backfill's manifest as extracted or missing-with-reason. Prints one JSON line per backfill
and a final gate line; exit 0 = PASS, 1 = FAIL.

    cd ~/arepo/backend && ../.venv/bin/python scripts/retention_gate_check.py [--grace-h 4]

Classification of an unaccounted capture:
  - ``pending_recent``: a host capture younger than ``--grace-h`` (the next pass step may not
    have reached it yet);
  - ``at_risk``: an older host capture; its raw rows lie under the deletion root: gate FAILS;
  - ``release_only``: no manifest under the host snapshot root (raw rows are not under the
    deletion root, e.g. the /home/opc/arepo_val validation capture); deletion cannot remove
    them, so they do not fail the gate but are listed.
``strict_complete`` is the literal rule (no unaccounted capture at all). Reads manifests only;
writes nothing.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

DUMPS = ROOT / "data-dumps" / "research_lab"
CATALOGUE = ROOT / "docs" / "research_lab" / "data_catalogue"


def _ts(s: str) -> datetime:
    t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return (t if t.tzinfo else t.replace(tzinfo=UTC)).astimezone(UTC)


def _status_top(ent: dict) -> tuple[str | None, str | None]:
    return ent.get("status"), ent.get("reason")


def _status_cb2(ent: dict) -> tuple[str | None, str | None]:
    lc = ent.get("ladder_candidates") or {}
    if lc.get("status") == "written":
        return "extracted", None
    if ent.get("status") == "missing" or lc.get("status") == "missing":
        return "missing", ent.get("reason") or lc.get("reason")
    return None, None


# name, manifest (under research_lab), window [since, before), entry -> (status, reason), gating.
# Non-gating rows are deadlines: extract before the snapshot rule reaches those captures.
BACKFILLS = [
    (
        "CB1 q0030 (cb1_extract)",
        "cb1_extract/manifest.json",
        "2026-10-11T12:00:00Z",
        None,
        _status_top,
        True,
    ),
    (
        "CB2 q0041 (cb2_extract/ladder_candidates)",
        "cb2_extract/manifest.json",
        "2026-10-11T12:00:00Z",
        None,
        _status_cb2,
        True,
    ),
    (
        "CB3 q0060 (cb3_extract/quote_state)",
        "cb3_extract/manifest.json",
        None,
        "2026-10-15T21:00:00Z",
        _status_top,
        True,
    ),
    (
        "CB4 q0080 (cb4_extract/closewin)",
        "cb4_extract/manifest.json",
        "2026-10-11T12:00:00Z",
        None,
        _status_top,
        True,
    ),
    (
        "CB3 live (quote_state pass step, not wired; deadline only)",
        "cb3_extract/manifest.json",
        "2026-10-15T21:00:00Z",
        None,
        _status_top,
        False,
    ),
]
SNAPSHOT_RULE_DAYS = 8  # scripts/oracle/archive_retention.json (deferred/active snapshots rule)


def first_deletion(start: datetime, days: float = SNAPSHOT_RULE_DAYS) -> str:
    """First nightly 03:30Z rotation at which a capture started at ``start`` is past the rule."""
    t = start + timedelta(days=days)
    run = t.replace(hour=3, minute=30, second=0, microsecond=0)
    if run <= t:
        run += timedelta(days=1)
    return run.strftime("%Y-%m-%dT%H:%MZ")


# CB1/CB2 write a bare ``missing`` entry when the raw file raised ArchivedDataError (no reason).
IMPLICIT_REASON = "archived_data_error (implicit)"


def universe(snapshot_root: Path, catalogue_dir: Path) -> list[dict]:
    from astrolabe.research_lab import cb3_quote_state

    return cb3_quote_state.universe(
        snapshot_root, cb3_quote_state.catalogue_snapshot_captures(catalogue_dir)
    )


def check(
    name: str,
    manifest: Path,
    since: str | None,
    before: str | None,
    status_fn,
    caps: list[dict],
    now: datetime,
    grace_h: float,
    gating: bool = True,
) -> dict:
    lo = _ts(since) if since else None
    hi = _ts(before) if before else None
    man = json.loads(manifest.read_text()) if manifest.exists() else {"captures": {}}
    ents = man.get("captures", {})
    out = {
        "backfill": name,
        "gating": gating,
        "window": [since, before],
        "manifest": str(manifest),
        "n_universe": 0,
        "n_extracted": 0,
        "n_missing": 0,
        "missing_by_reason": {},
        "pending_recent": [],
        "at_risk": [],
        "release_only": [],
    }
    for c in caps:
        st = c["_start"]
        if (lo and st < lo) or (hi and st >= hi):
            continue
        out["n_universe"] += 1
        s, reason = status_fn(ents.get(c["capture_id"], {}))
        if s == "extracted":
            out["n_extracted"] += 1
        elif s == "missing":
            out["n_missing"] += 1
            r = reason or IMPLICIT_REASON
            out["missing_by_reason"][r] = out["missing_by_reason"].get(r, 0) + 1
        elif c.get("release_only"):
            out["release_only"].append(c["capture_id"])
        elif now - st < timedelta(hours=grace_h):
            out["pending_recent"].append(c["capture_id"])
        else:
            out["at_risk"].append(c["capture_id"])
    out["n_unaccounted"] = (
        len(out["pending_recent"]) + len(out["at_risk"]) + len(out["release_only"])
    )
    out["strict_complete"] = out["n_unaccounted"] == 0
    oldest = out["at_risk"][0] if out["at_risk"] else None
    out["oldest_at_risk"] = oldest
    start = {c["capture_id"]: c["_start"] for c in caps}
    out["oldest_at_risk_first_deletion_8d"] = first_deletion(start[oldest]) if oldest else None
    out["n_at_risk"] = len(out["at_risk"])
    out["at_risk"] = out["at_risk"][:5] + (["..."] if len(out["at_risk"]) > 5 else [])
    out["gate_pass"] = out["n_at_risk"] == 0 or not gating
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--dumps", type=Path, default=DUMPS, help="research_lab root (default: this repo's)"
    )
    ap.add_argument("--catalogue-dir", type=Path, default=CATALOGUE)
    ap.add_argument(
        "--grace-h", type=float, default=4.0, help="host captures younger than this may be pending"
    )
    ap.add_argument("--now", default=None, help="evaluation time (default: current UTC)")
    a = ap.parse_args(argv)
    now = _ts(a.now) if a.now else datetime.now(UTC)
    caps = universe(a.dumps / "snapshots", a.catalogue_dir)
    results = [
        check(n, a.dumps / m, s, b, f, caps, now, a.grace_h, g) for n, m, s, b, f, g in BACKFILLS
    ]
    for r in results:
        print(json.dumps(r, sort_keys=True))
    print(
        json.dumps(
            {
                "retention_gate": "PASS" if all(r["gate_pass"] for r in results) else "FAIL",
                "now": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "grace_h": a.grace_h,
                "n_complete_captures": len(caps),
                "n_release_only": sum(1 for c in caps if c.get("release_only")),
                "failing": [r["backfill"] for r in results if not r["gate_pass"]],
                "strict_incomplete": [r["backfill"] for r in results if not r["strict_complete"]],
                "deadlines": {
                    r["backfill"]: r["oldest_at_risk_first_deletion_8d"]
                    for r in results
                    if not r["gating"] and r["n_at_risk"]
                },
            }
        )
    )
    return 0 if all(r["gate_pass"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
