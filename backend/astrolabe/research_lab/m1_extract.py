# ruff: noqa: E501
"""M1-J1 window-time extractor and M1-J2 window close (``MEASUREMENT_M1_CH263.md`` 9.2, 9.3). Research tooling; no network, no resolution read.

J1 reads only snapshot rows / sidecar of captures k - 1 and k and sweep 1 of k (column-selected), strictly in chronological slot order, and
writes write-once ``units/<capture_id>.jsonl.gz`` and ``status/<capture_id>.json`` per capture, with a small state file whose sha256 before
and after is chained through the status files. It never reads a capture after k for a unit, nor a resolution, label or outcome field.
"""

from __future__ import annotations

import base64
import gzip
import io
import json
import math
import os
import resource
import sys
import time
from collections import Counter
from pathlib import Path

from . import boundary_map_ch240 as c240
from . import census_map_ch269 as c269
from . import costs
from . import m1_j0 as j0
from . import m1_spec as sp
from . import population_map_ch251 as c251

CLASSES = j0.CLASSES
SWEEP_COLS = ("token_id", "market_id", "batch_receipt_utc", "best_ask", "ask_size_1", "depth_ask_1c")
EXT_COLS = j0.EXT_COLS
ROW_COLS = j0.ROW_COLS
STATE_REL = Path("state") / "m1_state.json"
OUTPUTS = ("units", "status", "state", "logs")


class M1Refusal(RuntimeError):
    """A declared refusal (overwrite, order, state chain, date gate, pin)."""


# --- helpers ----------------------------------------------------------------------------------------------------------------------------

def _clean(x):
    if isinstance(x, float) and not math.isfinite(x):
        return None
    if isinstance(x, dict):
        return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    return x


def dumps(o) -> str:
    return json.dumps(_clean(o), sort_keys=True, separators=(",", ":"))


def sha_bytes(b: bytes) -> str:
    import hashlib

    return hashlib.sha256(b).hexdigest()


def gz_bytes(text: str) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as g:
        g.write(text.encode())
    return buf.getvalue()


def peak_rss_mb() -> float:
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return round(r / (2**20 if sys.platform == "darwin" else 1024.0), 1)


def _write_once(path: Path, data: bytes, same) -> str:
    """Create ``path`` exclusively. If it exists, accept only identical content (idempotent re-run); else refuse to overwrite."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if same(path.read_bytes(), data):
            return "present_identical"
        raise M1Refusal(f"refuses to overwrite {path}")
    with open(path, "xb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    return "written"


def _same_gz(a: bytes, b: bytes) -> bool:
    try:
        return gzip.decompress(a) == gzip.decompress(b)
    except OSError:
        return False


def _same_json(a: bytes, b: bytes) -> bool:
    try:
        return json.loads(a) == json.loads(b)
    except ValueError:
        return False


def fee_exponent(fee_schedule) -> float:
    try:
        d = json.loads(fee_schedule) if isinstance(fee_schedule, str) and fee_schedule else {}
        e = float(d.get("exponent")) if isinstance(d, dict) and d.get("exponent") is not None else 1.0
        return e if math.isfinite(e) else 1.0
    except (ValueError, TypeError):
        return 1.0


def encode_ids(ids) -> dict:
    """A set of integer ids as sorted deltas, newline-separated, gzip (mtime 0), base64: small, deterministic, round-trips exactly."""
    prev, parts = 0, []
    for i in sorted(ids):
        parts.append(str(i - prev))
        prev = i
    return {"n": len(parts), "encoding": "sorted ids as deltas from 0, decimal, newline-separated, gzip mtime 0, base64", "gz_b64": base64.b64encode(gz_bytes("\n".join(parts))).decode()}


def decode_ids(d: dict) -> set:
    txt = gzip.decompress(base64.b64decode(d["gz_b64"])).decode()
    out, acc = set(), 0
    for line in txt.split("\n"):
        if line:
            acc += int(line)
            out.add(acc)
    return out


def fees_enabled_tri(has_fe: bool, raw) -> bool | None:
    """L1 flag (ambiguity 7): ``False`` only for a literal false, ``True`` for a truthy value, otherwise ``None`` (the conservative fee)."""
    if not has_fe or str(raw).strip() == "":
        return None
    if j0.false_flag(raw):
        return False
    return True if c240._truthy(raw) else None


# --- state ------------------------------------------------------------------------------------------------------------------------------

class State:
    """Markets with any proposal or dispute state seen in captures before k, the earlier M1 unit markets, and the last decided slot."""

    def __init__(self, d: dict | None = None) -> None:
        d = d or {}
        self.last_slot: int = d.get("last_slot", -1)
        self.last_capture_id: str | None = d.get("last_capture_id")
        self.last_kind: str = d.get("last_kind", "init")
        self.state_markets: set = set(d.get("state_markets", []))
        self.unit_markets: set = set(d.get("unit_markets", []))
        self.lookback: dict = d.get("lookback", {})

    def to_bytes(self) -> bytes:
        return dumps({"last_slot": self.last_slot, "last_capture_id": self.last_capture_id, "last_kind": self.last_kind,
                      "state_markets": sorted(self.state_markets), "unit_markets": sorted(self.unit_markets), "lookback": self.lookback}).encode()

    def sha(self) -> str:
        return sha_bytes(self.to_bytes())

    def copy(self) -> State:
        return State(json.loads(self.to_bytes()))


def load_state(store: Path) -> tuple[State, str] | None:
    p = store / STATE_REL
    if not p.exists():
        return None
    b = p.read_bytes()
    st = State(json.loads(b))
    return st, sha_bytes(b)


def save_state(store: Path, st: State) -> None:
    p = store / STATE_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f".{p.name}.{os.getpid()}.tmp")
    tmp.write_bytes(st.to_bytes())
    os.replace(tmp, p)


# --- discovery ---------------------------------------------------------------------------------------------------------------------------

def list_complete(root: Path) -> list[dict]:
    """Every complete capture (manifest ``state`` complete, rows present) with its start; ordered by (start, id)."""
    out = []
    for p in sorted(Path(root).glob("*/manifest.json")):
        try:
            m = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        t = c240.parse_utc(m.get("started_utc"))
        if m.get("state") != "complete" or not math.isfinite(t) or not (p.parent / "rows.csv.gz").exists():
            continue
        out.append({"id": p.parent.name, "capture_id": str(m.get("capture_id") or p.parent.name), "start": t, "dir": p.parent,
                    "fin": c240.parse_utc(m.get("finished_utc"))})  # the manifest's finish time (collector.py), judged by 9.2's missing rule
    return sorted(out, key=lambda c: (c["start"], c["id"]))


def count_noncomplete(root: Path, before: float) -> dict:
    """Manifests that exist and start before ``before`` but are not complete (state not complete or rows missing); counted, never used."""
    n = 0
    unparseable = 0
    for p in sorted(Path(root).glob("*/manifest.json")):
        try:
            m = json.loads(p.read_text())
        except (OSError, ValueError):
            unparseable += 1  # time unknown, so not assigned to "before the window" (S1)
            continue
        t = c240.parse_utc(m.get("started_utc"))
        if math.isfinite(t) and t < before and (m.get("state") != "complete" or not (p.parent / "rows.csv.gz").exists()):
            n += 1
    return {"noncomplete_manifests_before_window": n, "unparseable_manifests": unparseable}


def window_captures(root: Path, spec: dict) -> tuple[dict, list[dict], list[dict], list[dict]]:
    """({slot: capture} the first on-time complete capture of each window slot by start, [later on-time duplicates], [late captures], [off-grid captures]).
    On time (9.2): the manifest's ``finished_utc`` is at most grid time + 6 h; the rule is a fact about the capture, not about when J1 runs. A manifest
    without a parseable ``finished_utc`` is not on time (re-check R3): it goes to the late list, flagged ``fin_missing``."""
    a, b = sp.ts(spec, "registered_utc"), sp.ts(spec, "end_utc")
    wslots = set(sp.window_slots(spec))
    by: dict = {}
    extra: list = []
    late: list = []
    off: list = []
    for c in list_complete(root):
        if not (a <= c["start"] < b):
            continue
        s, on = sp.slot_of(spec, c["start"])
        if not on or s not in wslots:
            off.append(c | {"slot": s})
            continue
        fin_missing = not math.isfinite(c["fin"])
        c = c | {"slot": s, "fin_missing": fin_missing}
        if fin_missing or c["fin"] > sp.slot_time(spec, s) + spec["missing_after_grid_s"]:  # absent or unparseable finished_utc is not on time (R3)
            late.append(c)
        elif s in by:
            extra.append(c)
        else:
            by[s] = c
    return by, extra, late, off


def sweep_dirs(root: Path | None) -> dict:
    return j0.discover_sweeps(root) if root is not None else {}


# --- readers ----------------------------------------------------------------------------------------------------------------------------

def read_sidecar(path: Path, notes: Counter, scope: str | None = None) -> dict:
    """{codes: {mid: code}, raw: {mid: raw status string}, cand: {mid: fields}, has_fe: bool, in_scope: set | None}; column-selected.
    With ``scope`` the ids of every row whose E5 category (capture k's own sidecar row) equals it are collected; ``None`` when unreadable."""
    out = {"codes": {}, "raw": {}, "cand": {}, "has_fe": False, "in_scope": None}
    if not Path(path).exists():
        notes["captures_without_sidecar"] += 1
        return out
    it = j0.iter_csv(path, EXT_COLS)
    pres = next(it, None)
    if pres is None:
        return out
    for c, ok in zip(EXT_COLS, pres, strict=True):
        if not ok:
            notes[f"sidecar_column_missing:{c}"] += 1
    out["has_fe"] = pres[EXT_COLS.index("fees_enabled")]
    codes, raw, cand = out["codes"], out["raw"], out["cand"]
    in_scope: set | None = set() if scope is not None else None
    cat_cache: dict = {}
    for mid_s, rec, tok1, uma, acc, ft, fc, ss, fe, fsch, tick in it:
        try:
            mid = int(mid_s)
        except ValueError:
            notes["unparseable_market_id:sidecar"] += 1
            continue
        if in_scope is not None:
            key = (ft, fc, ss)
            cat = cat_cache.get(key)
            if cat is None:
                cat = cat_cache[key] = c240.category_of(ft, fc, ss, True)
            if cat == scope:
                in_scope.add(mid)
        code, _both = j0.status_code(uma)
        codes[mid] = code
        raw[mid] = sys.intern(str(uma))  # raw status strings at k and k - 1 go into the unit record; interned (most are the same few strings)
        if code in (1, 2) and "propos" in str(uma).lower():
            cand[mid] = {"ext_rec": c240.parse_utc(rec), "tok1": tok1, "code": code, "acc": acc, "ft": ft, "fc": fc, "ss": ss, "fe": fe, "fsch": fsch, "tick": tick}
    out["in_scope"] = in_scope
    return out


def read_rows(path: Path, cand_ids, notes: Counter, want_rows: bool = True) -> tuple[set, Counter, dict]:
    row_ids: set = set()
    evc: Counter = Counter()
    rows: dict = {}
    it = j0.iter_csv(path, ROW_COLS)
    pres = next(it, None)
    if pres is None:
        return row_ids, evc, rows
    for c, ok in zip(ROW_COLS, pres, strict=True):
        if not ok:
            notes[f"rows_column_missing:{c}"] += 1
    for mid_s, ev, rec, closed, active, binary, bid, ask, liq, end, tok0 in it:
        try:
            mid = int(mid_s)
        except ValueError:
            notes["unparseable_market_id:rows"] += 1
            continue
        row_ids.add(mid)
        if not want_rows:
            continue
        is_open = c240._truthy(binary) and not c240._truthy(closed) and c240._truthy(active)
        raw_ev = str(ev).strip()
        evk = raw_ev if raw_ev else f"market:{mid}"  # an empty event_id is its own one-market event and cluster (3.4)
        if is_open:
            evc[evk] += 1
        if mid in cand_ids:
            rows[mid] = {"ev": evk, "ev_raw": raw_ev, "rec": c240.parse_utc(rec), "closed": closed, "active": active, "binary": binary,
                         "bid": j0.r6(c240._f(bid)), "ask": j0.r6(c240._f(ask)), "liq": c240._f(liq), "end": c240.parse_utc(end), "end_raw": str(end), "tok0": tok0}
    return row_ids, evc, rows


def read_sweep(sweep_dir: Path | None, want: dict) -> tuple[dict, bool]:
    """{token: {rec, best_ask, ask_size_1, depth_ask_1c}} for the wanted tokens, first row per token; and whether sweep 1 is present."""
    got: dict = {}
    if sweep_dir is None or not (Path(sweep_dir) / "rows.csv.gz").exists():
        return got, False
    it = j0.iter_csv(Path(sweep_dir) / "rows.csv.gz", SWEEP_COLS)
    pres = next(it, None)
    if pres is None:
        return got, True
    for tok, _mid, rec, ba, asz, d1 in it:
        if tok in want and tok not in got:
            got[tok] = {"rec": c240.parse_utc(rec), "best_ask": j0.r6(c240._f(ba)), "ask_size_1": c240._f(asz), "depth_ask_1c": c240._f(d1)}
    return got, True


def hash_inputs(paths: list[Path]) -> list[dict]:
    return [{"path": str(p), "bytes": p.stat().st_size, "sha256": sp.sha256_file(p)} for p in paths if p.exists()]


# --- classification and unit records --------------------------------------------------------------------------------------------------

def classify(cap: dict, has_prev: bool, k: dict, prev: dict | None, prev_row_ids: set, rows: dict, evc: Counter, st: State, spec: dict) -> tuple[Counter, Counter, list[dict], list]:
    """E1-E7 (3.2) in order; the first failing rule names the class. Returns (funnel, funnel_by_category, new unit dicts)."""
    funnel: Counter = Counter()
    by_cat: Counter = Counter()
    units: list = []
    contested: list = []  # c on the side nearer 1 of each contested unit (8.2: mean c and count only)
    fav = spec["fav"]
    for mid in sorted(k["cand"]):
        f = k["cand"][mid]
        cat = c240.category_of(f["ft"], f["fc"], f["ss"], True)
        cls = None
        if not has_prev:
            cls = "no_previous_capture"
        elif f["code"] == 2:
            cls = "disputed_at_k"
        elif mid not in prev_row_ids or mid not in prev["codes"]:
            cls = "no_k_minus_1_row"
        elif prev["codes"][mid] in (1, 2, 3):
            cls = "already_proposed"
        elif mid in st.unit_markets or mid in st.state_markets:
            cls = "prior_proposal_state"
        r = rows.get(mid)
        if cls is None and r is None:
            cls = "not_open_at_k:no_row_at_k"  # a sidecar candidate with no row at k (counted apart from a closed or inactive row)
        if cls is None and (not c240._truthy(r["binary"]) or c240._truthy(r["closed"]) or not c240._truthy(r["active"]) or j0.false_flag(f["acc"])):
            cls = "not_open_at_k"
        if cls is None and cat != spec["scope"]:
            cls = f"out_of_scope_{cat}"
        side = None
        if cls is None:
            bid, ask = r["bid"], r["ask"]
            if not (bid > 0 and bid < ask and ask <= 1):
                cls = "not_two_sided"
            else:
                mid_k = j0.r6((bid + ask) / 2.0)
                if mid_k >= fav:
                    side, ask_f, bid_f = "YES", ask, bid
                elif mid_k <= j0.r6(1 - fav):
                    side, ask_f, bid_f = "NO", j0.r6(1.0 - bid), j0.r6(1.0 - ask)
                else:
                    cls = "contested"
                    contested.append(j0.r6(1.0 - (ask if mid_k >= 0.5 else j0.r6(1.0 - bid))))
        funnel[cls or "unit"] += 1
        by_cat[f"{cls or 'unit'}|{cat}"] += 1
        if cls is not None:
            continue
        units.append({"mid": mid, "f": f, "r": r, "cat": cat, "side": side, "ask_f": ask_f, "bid_f": bid_f, "mid_k": mid_k, "n_members": evc[r["ev"]]})
    return funnel, by_cat, units, contested


def build_unit(u: dict, cap: dict, prev_cap: dict, k: dict, prev: dict, sweep: dict, spec: dict, sha: dict) -> dict:
    f, r = u["f"], u["r"]
    ask_f, bid_f = u["ask_f"], u["bid_f"]
    c = j0.r6(1.0 - ask_f)
    side = u["side"]
    tok = r["tok0"] if side == "YES" else f["tok1"]
    sw = sweep.get(tok)
    times = [x for x in (r["rec"], f["ext_rec"], sw["rec"] if sw else math.nan) if math.isfinite(x)]
    t_d = max(times) if times else cap["start"]
    t_d_fallback = not times  # no parseable row, sidecar or sweep time: the capture start stands in (counted)
    key = costs.category_key(f["fc"])
    rate, _rebate = c251.fee_parse(f["fsch"])
    sched = rate if math.isfinite(rate) else None
    exponent = fee_exponent(f["fsch"])
    fe_tri = fees_enabled_tri(bool(k["has_fe"]), f["fe"])
    rate1 = costs.taker_rate(key, sched, fe_tri, policy=spec["fee_policy"])  # L1 (headline): honours fees_enabled
    rate2 = costs.taker_rate(key, sched, None, policy=spec["fee_policy"])  # L2: ignores the served fees_enabled
    tick = j0.r6(c240._f(f["tick"]))
    n_members = u["n_members"]
    tier = c269.tier_of(r["liq"])
    covered = bool(sw and math.isfinite(sw["ask_size_1"]))
    reg = sp.ts(spec, "registered_utc")
    day_idx = int((cap["start"] - reg) // 86400) + 1
    rec = {
        "market_id": u["mid"], "event_id": r["ev_raw"], "cluster": r["ev"], "side": side,
        "bid": r["bid"], "ask": r["ask"], "mid_k": u["mid_k"], "ask_f": ask_f, "bid_f": bid_f, "c": c, "mid_f": j0.r6((ask_f + bid_f) / 2.0),
        "h": j0.r6((r["ask"] - r["bid"]) / 2.0), "tick": tick, "ask_f_at_1": bool(ask_f == 1.0),
        "event_open_binary_members": n_members, "end_date": r["end_raw"], "end_rel": j0.end_rel_of(r["end"], t_d),
        "liquidity": r["liq"], "tier": j0.TIER_NAMES[tier], "category": u["cat"], "cat_k": key, "s2": j0.s2_cell(key),
        "fee_type": f["ft"], "fee_category": f["fc"], "fees_enabled": f["fe"], "fee_schedule": f["fsch"], "fee_exponent": exponent,
        "fee_schedule_rate": sched, "fee_class": c251.fee_class(f["fe"], bool(k["has_fe"]), f["fsch"])[0],
        "rate_L1": rate1, "rate_L2": rate2, "fee_L1": costs.taker_fee_ps(ask_f, rate1, exponent), "fee_L2": costs.taker_fee_ps(ask_f, rate2, exponent),
        "ladder": "standalone" if n_members <= 1 else ("member_winner" if side == "YES" else "member_loser"), "members": j0.members_of(n_members),
        "t_d": t_d, "t_d_utc": sp.iso(t_d), "t_d_fallback": t_d_fallback, "row_received_utc": r["rec"], "sidecar_received_utc": f["ext_rec"],
        "gap_ext_row_s": f["ext_rec"] - r["rec"], "gap_sweep_row_s": (sw["rec"] - r["rec"]) if sw else None,
        "sweep_covered": covered, "sweep_ask_size_1": sw["ask_size_1"] if sw else None, "sweep_best_ask": sw["best_ask"] if sw else None,
        "sweep_depth_ask_1c": sw["depth_ask_1c"] if sw else None, "sweep_batch_receipt_utc": sw["rec"] if sw else None,
        "status_k": k["raw"].get(u["mid"]), "status_k_minus_1": prev["raw"].get(u["mid"]),
        "capture_id": cap["capture_id"], "capture_k_minus_1_id": prev_cap["capture_id"], "k_start_utc": sp.iso(cap["start"]), "k_start_ts": cap["start"],
        "window_day": day_idx, "s10": f"days {7 * ((day_idx - 1) // 7) + 1}-{7 * ((day_idx - 1) // 7) + 7}",
        "spec_sha": sha["spec"], "code_sha": sha["code"], "role": sp.ROLE,
    }
    return rec


# --- one capture --------------------------------------------------------------------------------------------------------------------------

def process_capture(store: Path, cap: dict, prev_cap: dict | None, sweeps: dict, st: State, spec: dict, sha: dict, pin_rec: dict) -> tuple[State, dict, int]:
    """Classify capture k and return (state after, status dict, n units). Writes the unit and status files (write-once)."""
    notes: Counter = Counter()
    before = st.sha()
    k = read_sidecar(cap["dir"] / "rows_ext.csv.gz", notes, scope=spec["scope"])
    has_prev = prev_cap is not None
    # capture k - 1 was already counted when it was k: its read notes go to a throwaway counter so no capture's gaps are counted twice
    prev = read_sidecar(prev_cap["dir"] / "rows_ext.csv.gz", Counter()) if has_prev else {"codes": {}, "raw": {}, "cand": {}, "has_fe": False}
    prev_rows = read_rows(prev_cap["dir"] / "rows.csv.gz", set(), Counter(), want_rows=False)[0] if has_prev else set()
    _ids, evc, rows = read_rows(cap["dir"] / "rows.csv.gz", set(k["cand"]), notes)
    funnel, by_cat, units, contested = classify(cap, has_prev, k, prev, prev_rows, rows, evc, st, spec)
    sd = sweeps.get(cap["capture_id"]) or sweeps.get(cap["id"])
    want = {(u["r"]["tok0"] if u["side"] == "YES" else u["f"]["tok1"]): 1 for u in units} if units else {}
    if units:
        sweep, sweep_present = read_sweep(sd, want)
    else:
        sweep, sweep_present = {}, bool(sd is not None and (Path(sd) / "rows.csv.gz").exists())
    if sd is None:
        notes["captures_without_sweep_1"] += 1
    recs = [build_unit(u, cap, prev_cap, k, prev, sweep, spec, sha) for u in units]
    lines = [dumps(x) for x in recs]
    if cap.get("fin_missing"):
        notes["finished_utc_absent"] += 1
    sub: Counter = Counter()
    if not has_prev and cap["slot"] == sp.window_slots(spec)[0]:
        sub["no_previous_capture:first_window_slot"] = funnel.get("no_previous_capture", 0)  # the first window slot has no k - 1 by construction
    body = ("\n".join(lines) + "\n") if lines else ""
    ub = gz_bytes(body)
    after_state = st.copy()
    after_state.state_markets |= {m for m, c in k["codes"].items() if c in (1, 2)}
    after_state.unit_markets |= {u["mid"] for u in units}
    after_state.last_slot = cap["slot"]
    after_state.last_capture_id = cap["capture_id"]
    after_state.last_kind = "processed"
    ins = hash_inputs([cap["dir"] / "manifest.json", cap["dir"] / "rows.csv.gz", cap["dir"] / "rows_ext.csv.gz"])
    if has_prev:
        ins += hash_inputs([prev_cap["dir"] / "manifest.json", prev_cap["dir"] / "rows.csv.gz", prev_cap["dir"] / "rows_ext.csv.gz"])
    if sd is not None:
        ins += hash_inputs([Path(sd) / "manifest.json", Path(sd) / "rows.csv.gz"])  # sweep 1 files are hashed (9.2)
    status = {
        "kind": "processed", "capture_id": cap["capture_id"], "slot": cap["slot"], "grid_utc": sp.iso(sp.slot_time(spec, cap["slot"])), "capture_start_utc": sp.iso(cap["start"]),
        "complete": True, "prev_capture_id": prev_cap["capture_id"] if has_prev else None, "has_previous_capture": has_prev, "sweep_1_present": sweep_present,
        "units": len(lines), "unit_file_sha256": sha_bytes(ub), "funnel": {c: funnel.get(c, 0) for c in CLASSES} | {k2: v for k2, v in funnel.items() if k2 not in CLASSES},
        "funnel_sub": dict(sub), "t_d_fallbacks": sum(1 for x in recs if x["t_d_fallback"]),
        "in_scope_market_ids": encode_ids(k["in_scope"]) if k["in_scope"] is not None else None,  # amendment 18(b): E5's reader at k, for the survivorship line
        "funnel_by_category": dict(sorted(by_cat.items())), "contested_n": len(contested), "contested_c_sum": sum(contested), "notes": dict(sorted(notes.items())), "inputs": ins,
        "state_last_capture_before": st.last_capture_id, "state_last_slot_before": st.last_slot, "state_sha256_before": before, "state_sha256_after": after_state.sha(),
        "spec_sha": sha["spec"], "code_sha": sha["code"], "role": sp.ROLE, "pin_check": pin_rec,
    }
    cid = cap["capture_id"]
    _write_once(store / "units" / f"{cid}.jsonl.gz", ub, _same_gz)
    _write_once(store / "status" / f"{cid}.json", dumps(status).encode(), _same_json)
    return after_state, status, len(lines)


def missing_status(store: Path, slot: int, st: State, spec: dict, sha: dict, pin_rec: dict) -> tuple[State, dict]:
    after = st.copy()
    after.last_slot = slot
    after.last_kind = "missing"
    g = sp.slot_time(spec, slot)
    status = {"kind": "missing_capture", "slot": slot, "grid_utc": sp.iso(g), "state_last_capture_before": st.last_capture_id, "state_last_slot_before": st.last_slot,
              "state_sha256_before": st.sha(), "state_sha256_after": after.sha(), "spec_sha": sha["spec"], "code_sha": sha["code"], "role": sp.ROLE, "pin_check": pin_rec}
    _write_once(store / "status" / f"missing_{sp.iso(g).replace('-', '').replace(':', '')}.json", dumps(status).encode(), _same_json)
    return after, status


def status_path(store: Path, spec: dict, slot: int, cap: dict | None) -> Path:
    if cap is not None:
        return store / "status" / f"{cap['capture_id']}.json"
    return store / "status" / f"missing_{sp.iso(sp.slot_time(spec, slot)).replace('-', '').replace(':', '')}.json"


def init_state(store: Path, snap_root: Path, spec: dict, sha: dict, pin_rec: dict, now: float) -> State:
    """Look-back (E3): every retained complete capture starting before ``registered_utc``, raw sidecars only (``pre_window_source``).
    Refuses before ``registered_utc``: a run in the days before would build the look-back at once and every capture between that run and the
    window would be missing from E3's history."""
    reg = sp.ts(spec, "registered_utc")
    if now < reg:
        raise M1Refusal(f"J1 refuses before REGISTERED_UTC ({spec['registered_utc']}): the look-back state is built by the first run and must see every pre-window capture")
    caps = [c for c in list_complete(snap_root) if c["start"] < reg]
    notes: Counter = Counter()
    st = State()
    for c in caps:
        side = read_sidecar(c["dir"] / "rows_ext.csv.gz", notes)
        st.state_markets |= {m for m, code in side["codes"].items() if code in (1, 2)}
    st.last_slot = sp.window_slots(spec)[0] - 1
    st.last_kind = "init"
    n = len(caps)
    slots_on = {sp.slot_of(spec, c["start"])[0] for c in caps if sp.slot_of(spec, c["start"])[1]}
    gaps = (max(slots_on) - min(slots_on) + 1 - len(slots_on)) if slots_on else 0  # grid slots inside the look-back span with no on-grid capture (counted, never filled)
    st.lookback = {"pre_window_source": n, "below_minimum": n < spec["lookback_min_captures"], "minimum": spec["lookback_min_captures"],
                   "first_capture_utc": sp.iso(caps[0]["start"]) if caps else None, "last_capture_utc": sp.iso(caps[-1]["start"]) if caps else None,
                   "slot_gaps": gaps, "off_grid_captures": sum(1 for c in caps if not sp.slot_of(spec, c["start"])[1]),
                   **count_noncomplete(snap_root, reg)}
    status = {"kind": "init", "lookback": st.lookback, "notes": dict(sorted(notes.items())),
              "inputs": hash_inputs([p for c in caps for p in (c["dir"] / "manifest.json", c["dir"] / "rows_ext.csv.gz")]),
              "state_sha256_before": None, "state_sha256_after": st.sha(), "spec_sha": sha["spec"], "code_sha": sha["code"], "role": sp.ROLE, "pin_check": pin_rec}
    _write_once(store / "status" / "_init.json", dumps(status).encode(), _same_json)
    save_state(store, st)
    if n < spec["lookback_min_captures"]:
        print(f"M1-J1: look-back has {n} retained pre-window captures (< {spec['lookback_min_captures']}); printed, never filled", file=sys.stderr)
    return st


# --- the pass -------------------------------------------------------------------------------------------------------------------------

def run_pass(store: Path, snap_root: Path, sweep_root: Path | None, spec: dict = sp.SPEC, now: float | None = None,
             paths: dict | None = None, design: Path | None = None, pins: dict | None = None) -> dict:
    """Process every decidable window slot in increasing order; returns counts. Refuses on pin mismatch, a broken state chain, a closed window
    (``manifest.json`` exists), a start before ``registered_utc`` and, when ``pins`` is given, a ``spec_sha`` / ``code_sha`` different from the registered pins."""
    pin_rec = sp.check_pins(spec, paths, design)
    now = time.time() if now is None else now
    store = Path(store)
    sha = {"spec": sp.spec_sha(spec), "code": sp.code_sha()}
    if pins is not None and (pins.get("spec_sha") != sha["spec"] or pins.get("code_sha") != sha["code"]):
        raise sp.PinMismatch({"spec_sha": {"pin": pins.get("spec_sha"), "actual": sha["spec"]}, "code_sha": {"pin": pins.get("code_sha"), "actual": sha["code"]}})
    if (store / "manifest.json").exists():
        raise M1Refusal("J1 refuses: the window is closed (manifest.json exists)")
    for d in OUTPUTS:
        (store / d).mkdir(parents=True, exist_ok=True)
    loaded = load_state(store)
    st = loaded[0] if loaded else init_state(store, snap_root, spec, sha, pin_rec, now)
    caps, extra, late, off = window_captures(snap_root, spec)
    sweeps = sweep_dirs(sweep_root)
    slots = sp.window_slots(spec)
    res: Counter = Counter()
    chain_slots = {d["slot"] for d in load_all_statuses(store)[1]}  # a slot with any chain status is decided, whatever its capture id (R1)
    for s in slots:
        miss_path = status_path(store, spec, s, None)
        recorded_missing = miss_path.exists()
        cap = None if recorded_missing else caps.get(s)
        done_path = miss_path if recorded_missing else status_path(store, spec, s, cap)
        if (done_path.exists() or s in chain_slots) and st.last_slot >= s:
            continue
        if st.last_slot > s - 1 or st.last_slot < s - 1:
            raise M1Refusal(f"state chain broken before slot {s}: the state file's last folded slot is {st.last_slot}, expected {s - 1} "
                            f"(a state holding a capture at or after k, or a gap, makes the run refuse)")
        g = sp.slot_time(spec, s)
        if not recorded_missing and now < g + spec["missing_after_grid_s"]:  # R1: the on-time set of a slot is final only after grid + 6 h
            res["waiting_for_slot"] += 1
            break
        if cap is None:
            st, _ = missing_status(store, s, st, spec, sha, pin_rec)
            save_state(store, st)
            res["missing_capture"] += 1
            continue
        prev_cap = caps.get(s - 1) if (st.last_kind == "processed" and (s - 1) in caps) else None
        if prev_cap is not None and prev_cap["capture_id"] != st.last_capture_id:
            raise M1Refusal(f"state's last folded capture {st.last_capture_id} is not capture k - 1 {prev_cap['capture_id']}")
        st, _status, nu = process_capture(store, cap, prev_cap, sweeps, st, spec, sha, pin_rec)
        save_state(store, st)
        res["processed"] += 1
        res["units"] += nu
    # Captures that never enter the chain are counted in write-once status files, so J2's manifest carries them (not only the append log).
    # A late capture is one whose manifest finished after grid + 6 h; a slot recorded missing also keeps an on-time capture that was delivered later.
    decided = {s for s in slots if status_path(store, spec, s, None).exists() or status_path(store, spec, s, caps.get(s)).exists()}
    late_all = [(c, "finished_utc_absent" if c["fin_missing"] else "finished_after_grid_plus_6h") for c in late if c["slot"] in decided]
    late_all += [(caps[s], "delivered_after_missing_recorded") for s in slots if s in caps and status_path(store, spec, s, None).exists()]
    for c, why in late_all:
        _write_once(store / "status" / f"late_{c['capture_id']}.json", dumps({"kind": "late_capture_ignored", "capture_id": c["capture_id"], "slot": c["slot"], "reason": why,
                    "capture_start_utc": sp.iso(c["start"]), "finished_utc": None if c["fin_missing"] else sp.iso(c["fin"])}).encode(), _same_json)
        res["late_capture_ignored"] += 1
    for c in extra:
        _write_once(store / "status" / f"dup_{c['capture_id']}.json", dumps({"kind": "duplicate_slot_capture_ignored", "capture_id": c["capture_id"], "slot": c["slot"],
                    "kept_capture_id": caps[c["slot"]]["capture_id"], "capture_start_utc": sp.iso(c["start"])}).encode(), _same_json)
        res["duplicate_slot_capture_ignored"] += 1
    for c in off:
        _write_once(store / "status" / f"offgrid_{c['capture_id']}.json", dumps({"kind": "off_grid_capture_ignored", "capture_id": c["capture_id"], "nearest_slot": c["slot"],
                    "capture_start_utc": sp.iso(c["start"])}).encode(), _same_json)
        res["off_grid_capture_ignored"] += 1
    rec = {"now_utc": sp.iso(now), "peak_rss_mb": peak_rss_mb(), "spec_sha": sha["spec"], "code_sha": sha["code"]} | dict(res)
    (store / "logs").mkdir(parents=True, exist_ok=True)
    with open(store / "logs" / "j1_runs.jsonl", "a") as fh:
        fh.write(dumps(rec) + "\n")
    return rec


# --- audit and close ----------------------------------------------------------------------------------------------------------------------

SIDE_KINDS = ("late_capture_ignored", "duplicate_slot_capture_ignored", "off_grid_capture_ignored")


def load_all_statuses(store: Path) -> tuple[dict | None, list[dict], dict]:
    """(init status, chain statuses by slot, {side kind: [records]}) for late, duplicate and off-grid captures."""
    init = None
    chain: list = []
    side: dict = {k: [] for k in SIDE_KINDS}
    for p in sorted((Path(store) / "status").glob("*.json")):
        d = json.loads(p.read_text())
        if d.get("kind") == "init":
            init = d
        elif d.get("kind") in side:
            side[d["kind"]].append(d)
        else:
            chain.append(d)
    return init, sorted(chain, key=lambda d: d["slot"]), side


def load_statuses(store: Path) -> tuple[dict | None, list[dict], list[dict]]:
    init, chain, side = load_all_statuses(store)
    return init, chain, side["late_capture_ignored"]


def audit_chain(store: Path, spec: dict) -> dict:
    """Void case 11.2(a): every slot in order, each status's state sha before equal to the previous one's after (starting at the init status)."""
    init, chain, side = load_all_statuses(store)
    late = side["late_capture_ignored"]
    breaks: list = []
    if init is None:
        breaks.append("no_init_status")
    prev_after = init["state_sha256_after"] if init else None
    prev_slot = sp.window_slots(spec)[0] - 1
    for d in chain:
        if d["slot"] != prev_slot + 1:
            breaks.append(f"slot_gap_before_{d['slot']}")
        if d["state_sha256_before"] != prev_after:
            breaks.append(f"sha_break_at_{d['slot']}")
        if d["state_last_slot_before"] != prev_slot:
            breaks.append(f"last_slot_before_mismatch_at_{d['slot']}")
        prev_after, prev_slot = d["state_sha256_after"], d["slot"]
    return {"ok": not breaks, "breaks": breaks, "decided_slots": len(chain), "last_slot": prev_slot, "late_capture_ignored": len(late),
            "duplicate_slot_capture_ignored": len(side["duplicate_slot_capture_ignored"]), "off_grid_capture_ignored": len(side["off_grid_capture_ignored"]),
            "missing_slots": [d["slot"] for d in chain if d["kind"] == "missing_capture"]}


def close_window(store: Path, spec: dict = sp.SPEC, now: float | None = None, paths: dict | None = None, design: Path | None = None) -> dict:
    """J2: at ``end_utc`` + 6 h writes ``manifest.json`` (sha256 of every unit and status file, slot coverage, missing list); write-once."""
    sp.check_pins(spec, paths, design)
    now = time.time() if now is None else now
    if now < sp.ts(spec, "end_utc") + spec["close_after_end_s"]:
        raise M1Refusal("window close refuses before END_UTC + 6 h")
    store = Path(store)
    audit = audit_chain(store, spec)
    slots = sp.window_slots(spec)
    if audit["decided_slots"] != len(slots) or not audit["ok"]:
        raise M1Refusal(f"window close refuses: decided {audit['decided_slots']} of {len(slots)} slots, chain ok {audit['ok']} {audit['breaks'][:3]}")
    files = {str(p.relative_to(store)): sp.sha256_file(p) for sub in ("units", "status") for p in sorted((store / sub).glob("*")) if p.is_file()}
    n_units = 0
    for p in sorted((store / "units").glob("*.jsonl.gz")):
        n_units += sum(1 for _ in gzip.open(p, "rt"))
    man = {"kind": "M1-J2 window manifest", "spec_sha": sp.spec_sha(spec), "code_sha": sp.code_sha(), "role": sp.ROLE, "window_slots": len(slots),
           "processed_slots": len(slots) - len(audit["missing_slots"]), "slot_coverage": (len(slots) - len(audit["missing_slots"])) / len(slots),
           "missing_slots": audit["missing_slots"], "late_capture_ignored": audit["late_capture_ignored"],
           "duplicate_slot_capture_ignored": audit["duplicate_slot_capture_ignored"], "off_grid_capture_ignored": audit["off_grid_capture_ignored"], "units": n_units, "chain": audit, "files": files}
    p = store / "manifest.json"
    _write_once(p, dumps(man).encode(), _same_json)
    return man | {"manifest_sha256": sp.sha256_file(p)}
