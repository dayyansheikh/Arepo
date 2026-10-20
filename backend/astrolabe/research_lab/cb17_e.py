# ruff: noqa: E501
"""CB17-E window code (docs/research_lab/CREATIVE_BATCH_17.md section CB17-E; rules part ``E`` = ``cb17_rules_e``): first-day prints, a CENSUS ONLY (k = 0).

q0407 (branch T: E features only) builds one row per SCREEN_8 monitor transaction (CB13's pinned ``build_transactions``; the print reader keeps the whitelisted fields only, so ``side``,
``recv_ts`` and wallet fields never reach a dict) with CB13-T's touch-consistent status by pin (``cb16_q.make_fills`` on a touch-mode quote index: no mark accessor), the LABELLER class,
the static ``created_at`` (first capture carrying the market) and the pre-fill proxy inputs. q0408 counts both populations (O1's literal reading, part E) and writes the re-entry verdict;
the proxy SE is written alone (no point estimate).
"""

from __future__ import annotations

import json
import math
from collections import Counter
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from . import cb13_common as c13
from . import cb13_label as lab
from . import cb13_t as t13
from . import cb16_q as q16
from . import cb17_common as c17
from . import cb17_pre as pre
from . import cb17_rules_e as re_
from . import cb17_wcommon as w
from . import cb17_win as win

Refused = c17.Refused

ROWS_NAME = "e_rows.json.gz"
KEEP = ("condition_id", "market_id", "event_id", "label", "path_key", "tau", "status", "d", "mid0", "prev_mid", "created_epoch", "block", "cash", "P", "fee_type")
PRINT_KEEP = (*c17.PRINT_FIELDS, "tx16")
CHUNK = 5000


def iter_prints(trades_dir: Path, lo: float, hi: float, stats: Counter) -> Iterator[dict]:
    """Whitelisted prints with venue time in ``[lo, hi)``: the JSON decoder keeps ``PRINT_FIELDS`` + ``tx16`` only (``side``, ``recv_ts``, wallet and key never reach a dict), then CB13's
    pinned ``whitelist_print`` types them. Day files by receipt (the day after ``hi`` included)."""
    w.guard_window_row(lo, "print window start")
    hook = lambda kv: {k: v for k, v in kv if k in PRINT_KEEP}  # noqa: E731
    d0 = datetime.fromtimestamp(lo, UTC).date().toordinal()
    d1 = datetime.fromtimestamp(hi - 1, UTC).date().toordinal() + 1
    for o in range(d0, d1 + 1):
        p = Path(trades_dir) / f"trades-{datetime.fromordinal(o):%Y%m%d}.jsonl"
        win.refuse_window_path(p, ("live_trades",))
        if not p.exists():
            stats["monitor_days_missing"] += 1
            continue
        with p.open("r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    rec = json.loads(line, object_pairs_hook=hook)
                except ValueError:
                    stats["monitor_bad_lines"] += 1
                    continue
                x = c13.whitelist_print(rec) if isinstance(rec, dict) else None
                if x is not None and lo <= x["ts"] < hi:
                    yield x


def build_frame(trades_dir: Path, snap_root: Path, *, units: tuple[float, float], cap_lo: float, drops: dict[str, str] | None = None) -> dict:
    """Transactions with ``tau`` in the window, their CB13-T status (touch-consistent rule by pin), class, creation time and pre-fill proxy inputs. Features only."""
    stats: Counter = Counter()
    prints = list(iter_prints(trades_dir, units[0], units[1], stats))
    txs, info = t13.build_transactions(prints)
    prints = None
    caps = q16.list_captures(snap_root, cap_lo, units[1])
    qi = q16.load_quote_index(caps, {t["condition_id"] for t in txs}, "touch")
    rows: list[dict] = []
    counts: Counter = Counter()
    for i in range(0, len(txs), CHUNK):
        chunk, cnt = q16.make_fills(txs[i:i + CHUNK], qi, drops or {})
        counts.update(cnt)
        for r in chunk:
            rows.append({k: r.get(k) for k in KEEP})
    return {"rows": rows, "status_counts": dict(counts), "transactions": len(txs), "n_captures": len(caps), "stats": dict(stats), "info": info}


def write_frame(out_dir: Path, fr: dict) -> list[Path]:
    return [win.write_json_gz(Path(out_dir) / ROWS_NAME, {k: fr[k] for k in ("rows", "status_counts", "transactions", "n_captures", "stats", "info")})]


def load_frame(rdir: Path) -> dict:
    return win.read_json_gz(Path(rdir) / ROWS_NAME)


def census(fr: dict) -> dict:
    """The E census (counts; the proxy SE alone) and the declared re-entry verdict (O1 literal reading: counts on all non-sports transactions, the MDE on the signable fills)."""
    rows = fr["rows"]
    by: dict[str, Counter] = {"all": Counter(), "signable": Counter()}
    mk_groups: dict[str, dict[str, set]] = {"all": {}, "signable": {}}
    ev_groups: dict[str, dict[str, set]] = {"all": {}, "signable": {}}
    unsignable: Counter = Counter()
    n_first = {"all": 0, "signable": 0}
    proxy_rows = []
    for r in rows:
        sports = r["label"] == lab.SPORTS
        tau = float(r["tau"])
        age = re_.market_age_h(tau, float(r["created_epoch"]) if r.get("created_epoch") is not None else math.nan)
        g = re_.age_group(age)
        hour = int((tau % 86400) // 3600)
        signable = r["status"] == t13.SCREEN_STATUS_FILL
        for pop in ("all", "signable") if signable else ("all",):
            if g == "first":
                by[pop][f"first|class={r['label']}"] += 1
                by[pop][f"first|sports={int(sports)}"] += 1
                by[pop][f"first|hour={hour:02d}"] += 1
            if sports:
                continue
            if g == "first":
                n_first[pop] += 1
            if g is not None:
                mk_groups[pop].setdefault(r["condition_id"], set()).add(g)
                ev_groups[pop].setdefault(r["event_id"] or r["condition_id"], set()).add(g)
        if g == "first" and not sports and not signable:
            unsignable[r["status"] if not str(r["status"]).startswith(t13.S_KEY) else t13.S_KEY] += 1
        if signable and not sports and g is not None and r.get("prev_mid") is not None and math.isfinite(float(r["prev_mid"])):
            proxy_rows.append((100.0 * float(r["d"]) * (float(r["mid0"]) - float(r["prev_mid"])), 1.0 if g == "first" else 0.0, r["condition_id"], r["event_id"] or r["condition_id"],
                               r["path_key"] or f"event:{r['event_id']}", tau))
    both = {pop: sorted(m for m, s in mk_groups[pop].items() if s == {"first", "later"}) for pop in mk_groups}
    both_ev = {pop: len([e for e, s in ev_groups[pop].items() if s == {"first", "later"}]) for pop in ev_groups}
    ways = {"event": [x[3] for x in proxy_rows], "path_x_block": [(x[4], c17.block6(x[5])) for x in proxy_rows], "block6": [c17.block6(x[5]) for x in proxy_rows]}
    se = pre.fe_cluster_se([x[0] for x in proxy_rows], [x[1] for x in proxy_rows], [x[2] for x in proxy_rows], ways) if proxy_rows else {"n": 0, "se": None, "mde": None}
    verdict = re_.reentry_verdict(n_first["all"], len(both["all"]), se.get("mde"))
    first_total = n_first["all"]
    return {"populations": {"counts": re_.POPULATION_COUNTS, "mde": re_.POPULATION_MDE, "rule": re_.POPULATION_RULE},
            "first_day_transactions_non_sports": n_first, "markets_first_and_later": {k: len(v) for k, v in both.items()}, "events_first_and_later": both_ev,
            "first_day_tables": {k: dict(sorted(v.items())) for k, v in by.items()}, "first_day_unsignable_by_status": dict(sorted(unsignable.items())),
            "first_day_unsignable_share": (sum(unsignable.values()) / first_total) if first_total else None, "proxy_se": se, "reentry": verdict, "k": 0,
            "status_counts": fr.get("status_counts"), "transactions": fr.get("transactions")}


def declared() -> dict:
    return {"rows": ROWS_NAME, "keep": list(KEEP), "print_keep": list(PRINT_KEEP), "chunk": CHUNK}
