# ruff: noqa: E501
"""Synthetic WINDOW worlds for the CB17 window-code tests (offline; no real data of any window is ever read). Times are placed at or after the lookback floor 2026-10-26T00:00Z.

``world(root, s, ...)`` writes, under ``root``: complete captures every ``cadence`` seconds (event / sidecar / open-interest fields), book sweeps (two per pass, outcome-0 token ``T<m>``),
and monitor day files with touch-consistent prints. Fields CB17 must never read (side, wallet, key, recv_ts, chg_*, outcome_prices ...) are present in every file.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from astrolabe.research_lab import cb17_wcommon as w
from tests.cb17_synth import ep, print_, stamp, write_capture, write_day, write_sweep

FLOOR = ep("2026-10-26T00:00:00Z")
H = 3600.0


def events_by_arm(n_per_arm: int) -> dict[int, list[str]]:
    out: dict[int, list[str]] = {0: [], 1: []}
    i = 0
    while min(len(out[0]), len(out[1])) < n_per_arm:
        e = f"EV{i}"
        out[w.arm(e)].append(e)
        i += 1
    return out


def world(root: Path, s: float, *, n_events: int = 12, members: int = 2, n_passes: int = 14, cadence: float = 7200.0, seed: int = 5, arm: int | None = None, with_prints: bool = True,
          oi_step: float = 50.0) -> dict:
    """Markets ``m`` = 1..n_events*members in events EV*; captures at ``s + k * cadence``; passes (two sweeps, 120 s apart) at ``s + k * cadence + 20 s``. Returns paths and the market map."""
    rng = np.random.default_rng(seed)
    root = Path(root)
    snap, sw, tr = root / "snapshots", root / "book_sweeps", root / "live_trades"
    pool = events_by_arm(n_events)
    evs = (pool[arm] if arm is not None else [e for pair in zip(pool[0], pool[1], strict=False) for e in pair])[:n_events]
    markets = []
    for ei, e in enumerate(evs):
        for j in range(members):
            markets.append({"m": ei * members + j + 1, "ev": e, "j": j})
    mids = {m["m"]: 0.5 for m in markets}
    oi = {e: 1000.0 for e in evs}
    vol = {e: 5000.0 for e in evs}
    prints_by_day: dict[str, list[dict]] = {}
    for k in range(n_passes):
        t = s + k * cadence
        quotes = []
        for e in evs:
            traded = rng.random() < 0.8
            if traded:
                vol[e] += 400.0 + 100.0 * rng.random()
                oi[e] += oi_step * (1 if rng.random() < 0.6 else -1) * rng.random()
        for m in markets:
            mids[m["m"]] = float(np.clip(mids[m["m"]] + rng.normal(0, 0.012), 0.2, 0.8))
            mid = mids[m["m"]]
            q = {"mid": str(m["m"]), "cid": f"c{m['m']}", "eid": m["ev"], "bid": f"{mid - 0.01:.3f}", "ask": f"{mid + 0.01:.3f}", "liq": "40000", "oi": f"{oi[m['ev']]:.1f}", "vol": f"{vol[m['ev']]:.1f}",
                 "series": '["btc-weekly"]' if m["m"] % 2 else "[]", "created": "2026-09-01T00:00:00Z", "end": "2027-01-01T00:00:00Z"}
            quotes.append(q)
        write_capture(snap, t + 60.0, quotes, name=stamp(t + 60.0, f"{k:08x}"))
        books = []
        for m in markets:
            mid = mids[m["m"]]
            age = [30.0, 300.0, 1200.0, 4000.0][(m["m"] + k) % 4]
            books.append((m, mid, age))
        for jx, off in enumerate((20.0, 140.0)):
            recv = t + off
            rows = []
            for m, mid, age in books:
                # the touch is unchanged inside a pass; the depth beneath the touch shifts on some tokens (the "breathing book")
                shift = (m["m"] + k) % 3 == 0
                rows.append({"tok": f"T{m['m']}", "mid": str(m["m"]), "bid": f"{mid - 0.01:.3f}", "ask": f"{mid + 0.01:.3f}", "ts": int((t + 20.0 - age + (60.0 if (shift and jx == 1) else 0.0)) * 1000),
                             "hash": f"h{m['m']}-{k}-{jx if shift else 0}", "d5b": 2000 + (400 * jx if shift else 0), "d5a": 2000 - (400 * jx if shift else 0), "recv": recv})
            write_sweep(sw, recv, rows, name=stamp(recv, f"{k:04x}{jx:04x}"))
        if with_prints:
            for m in markets[: len(markets) // 2]:
                ts = t + 3000.0 + 7.0 * m["m"]
                day = datetime.fromtimestamp(ts, UTC).strftime("%Y%m%d")
                prints_by_day.setdefault(day, []).append(print_(ts, f"c{m['m']}", 0.5 + 0.01 * (-1) ** m["m"], oi=0, side="BUY" if m["m"] % 2 else "SELL", size=300.0,
                                                                    tx=f"tx{k}-{m['m']}", title="Will it happen?", mkt=str(m["m"]), ev=m["ev"]))
    if with_prints:
        for day, lines in prints_by_day.items():
            write_day(tr, day, lines)
    return {"snap": snap, "sw": sw, "tr": tr, "markets": markets, "events": evs, "end": s + n_passes * cadence}


def write_records(tmp: Path, *, rules: Path, code_sha: str, shas: dict, t17_utc: str = "2026-10-24T12:00:00Z", frozen_utc: str = "2026-10-25T00:00:00Z", attestation: str = "attested (test)") -> dict:
    """The committed-record stand-ins of a test (read with ``--allow-uncommitted-rules``): code freeze, T17_rules."""
    cf = Path(tmp) / "cb17_code_freeze.json"
    cf.write_text(json.dumps({"code_sha256": code_sha, "rules_sha256": shas, "frozen_utc": frozen_utc, "attestation_code_freeze": attestation}))
    t17 = Path(tmp) / "cb17_t17_rules.json"
    t17.write_text(json.dumps({"t17_rules_utc": t17_utc, "parts": {k: v for k, v in shas.items() if k in ("common", "B", "C", "E")}}))
    return {"freeze": cf, "t17": t17}


def sha_of(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class JobEnv:
    """Everything a runner invocation of a window job needs, in a tmp dir: rules file (parts pre, common, B, C, E), code-freeze and T17_rules stand-ins, a passing ``smoke.json``, the
    synthetic world (arm 0 for SCREEN_8, arm 1 for REP_8), E011 / CB3 hold stand-ins and the seals directory. Used with ``--allow-uncommitted-rules`` (the test hook)."""

    def __init__(self, tmp: Path, *, screen_events: int = 12, rep_events: int = 12, passes: int = 30, with_smoke: bool = True):
        from astrolabe.research_lab import cb17_common as c17
        from astrolabe.research_lab import cb17_win as win

        self.tmp = Path(tmp)
        self.rules = self.tmp / "cb17_rules.json"
        c17.write_rules(self.rules)
        self.shas = win.verify_parts(self.rules, require_committed=False)
        self.s8 = FLOOR
        self.dd = self.tmp / "dd"
        self.dd.mkdir()
        self.root = self.tmp / "creative_batch17"
        self.seals = self.tmp / "seals"
        self.seals.mkdir()
        self.trials = self.tmp / "trials.jsonl"
        rec = write_records(self.tmp, rules=self.rules, code_sha=win.code_sha256(), shas=self.shas)
        self.freeze, self.t17 = rec["freeze"], rec["t17"]
        # one host tree: SCREEN_8 holds arm-0 events from S_8, REP_8 arm-1 events from S_8 + 14 d
        rep0 = self.s8 + 14 * 86400.0
        sc = world(self.tmp / "host", self.s8, n_events=screen_events, n_passes=passes, arm=0, seed=5)
        rp = world(self.tmp / "host", rep0 + 0.0, n_events=rep_events, n_passes=passes, arm=1, seed=6)
        self.host = self.tmp / "host"
        self.screen, self.rep = sc, rp
        self.e011 = self.tmp / "e011_analysis_commit.json"
        self.e011.write_text(json.dumps({"e011_analysis_commit": "abc123"}))
        self.cb3 = self.tmp / "cb3_specs"
        self.cb3.mkdir()
        (self.cb3 / "cb3_v1.json").write_text("{}")
        self.late = ep("2026-11-24T00:00:00Z")
        if with_smoke:
            self.write_smoke()

    def write_smoke(self, **override) -> Path:
        from astrolabe.research_lab import cb17_wcommon as w

        crit = {k: True for k in w.SMOKE_CRITERIA}
        crit.update(override)
        self.root.mkdir(parents=True, exist_ok=True)
        p = self.root / "smoke.json"
        pf = {f: all(crit.get(k) is True for k in need) for f, need in w.SMOKE_NEEDS.items()}
        p.write_text(json.dumps({"criteria": crit, "pass": all(crit.values()), "pass_by_family": pf}))
        return p

    def argv(self, *cmd: str, now: float | None = None, extra: tuple = ()) -> list[str]:
        a = [*cmd, "--root", str(self.root), "--rules", str(self.rules), "--allow-uncommitted-rules", "--standalone", "--trials-path", str(self.trials), "--data-dumps", str(self.dd),
             "--snapshot-dir", str(self.host / "snapshots"), "--sweep-dir", str(self.host / "book_sweeps"), "--trades-dir", str(self.host / "live_trades"), "--seals-dir", str(self.seals),
             "--code-freeze", str(self.freeze), "--t17-record", str(self.t17)]
        if now is not None:
            a += ["--now", str(now)]
        return [*a, *extra]
