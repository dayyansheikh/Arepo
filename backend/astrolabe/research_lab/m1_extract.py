# ruff: noqa: E501
"""M1-J1 window-time extractor and M1-J2 window close (``MEASUREMENT_M1_CH263.md`` 9.2, 9.3). Research tooling; no network, no resolution read.

J1 reads only snapshot rows / sidecar of captures k - 1 and k and sweep 1 of k (column-selected), strictly in chronological slot order, and
writes write-once ``units/<capture_id>.jsonl.gz`` and ``status/<capture_id>.json`` per capture, with a small state file whose sha256 before
and after is chained through the status files. It never reads a capture after k for a unit, nor a resolution, label or outcome field.
"""

from __future__ import annotations

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
        out.append({"id": p.parent.name, "capture_id": str(m.get("capture_id") or p.parent.name), "start": t, "dir": p.parent})
    return sorted(out, key=lambda c: (c["start"], c["id"]))


def window_captures(root: Path, spec: dict) -> tuple[dict, list[dict]]:
    """({slot: capture} the first complete capture of each window slot by start, [later duplicates of a slot])."""
    a, b = sp.ts(spec, "registered_utc"), sp.ts(spec, "end_utc")
    wslots = set(sp.window_slots(spec))
    by: dict = {}
    extra: list = []
    for c in list_complete(root):
        if not (a <= c["start"] < b):
            continue
        s, on = sp.slot_of(spec, c["start"])
        if not on or s not in wslots:
            continue
        c = c | {"slot": s}
        if s in by:
            extra.append(c)
        else:
            by[s] = c
    return by, extra


def sweep_dirs(root: Path | None) -> dict:
    return j0.discover_sweeps(root) if root is not None else {}


# --- readers ----------------------------------------------------------------------------------------------------------------------------

def read_sidecar(path: Path, notes: Counter) -> dict:
    """{codes: {mid: code}, raw: {mid: raw status string}, cand: {mid: fields}, has_fe: bool}; column-selected."""
    out = {"codes": {}, "raw": {}, "cand": {}, "has_fe": False}
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
    for mid_s, rec, tok1, uma, acc, ft, fc, ss, fe, fsch, tick in it:
        try:
            mid = int(mid_s)
        except ValueError:
            continue
        code, _both = j0.status_code(uma)
        codes[mid] = code
        raw[mid] = sys.intern(str(uma))  # raw status strings at k and k - 1 go into the unit record; interned (most are the same few strings)
        if code in (1, 2) and "propos" in str(uma).lower():
            cand[mid] = {"ext_rec": c240.parse_utc(rec), "tok1": tok1, "code": code, "acc": acc, "ft": ft, "fc": fc, "ss": ss, "fe": fe, "fsch": fsch, "tick": tick}
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
        if cls is None and (r is None or not c240._truthy(r["binary"]) or c240._truthy(r["closed"]) or not c240._truthy(r["active"]) or j0.false_flag(f["acc"])):
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
    key = costs.category_key(f["fc"])
    rate, _rebate = c251.fee_parse(f["fsch"])
    sched = rate if math.isfinite(rate) else None
    exponent = fee_exponent(f["fsch"])
    fe_tri = None if (not k["has_fe"] or str(f["fe"]).strip() == "") else bool(c240._truthy(f["fe"]))
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
        "t_d": t_d, "t_d_utc": sp.iso(t_d), "row_received_utc": r["rec"], "sidecar_received_utc": f["ext_rec"],
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
    k = read_sidecar(cap["dir"] / "rows_ext.csv.gz", notes)
    has_prev = prev_cap is not None
    prev = read_sidecar(prev_cap["dir"] / "rows_ext.csv.gz", notes) if has_prev else {"codes": {}, "raw": {}, "cand": {}, "has_fe": False}
    prev_rows = read_rows(prev_cap["dir"] / "rows.csv.gz", set(), notes, want_rows=False)[0] if has_prev else set()
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
    lines = [dumps(build_unit(u, cap, prev_cap, k, prev, sweep, spec, sha)) for u in units]
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


def init_state(store: Path, snap_root: Path, spec: dict, sha: dict, pin_rec: dict) -> State:
    """Look-back (E3): every retained complete capture starting before ``registered_utc``, raw sidecars only (``pre_window_source``)."""
    reg = sp.ts(spec, "registered_utc")
    caps = [c for c in list_complete(snap_root) if c["start"] < reg]
    notes: Counter = Counter()
    st = State()
    for c in caps:
        side = read_sidecar(c["dir"] / "rows_ext.csv.gz", notes)
        st.state_markets |= {m for m, code in side["codes"].items() if code in (1, 2)}
    st.last_slot = sp.window_slots(spec)[0] - 1
    st.last_kind = "init"
    n = len(caps)
    st.lookback = {"pre_window_source": n, "below_minimum": n < spec["lookback_min_captures"], "minimum": spec["lookback_min_captures"],
                   "first_capture_utc": sp.iso(caps[0]["start"]) if caps else None, "last_capture_utc": sp.iso(caps[-1]["start"]) if caps else None}
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
             paths: dict | None = None, design: Path | None = None) -> dict:
    """Process every decidable window slot in increasing order; returns counts. Refuses on pin mismatch or a broken state chain."""
    pin_rec = sp.check_pins(spec, paths, design)
    now = time.time() if now is None else now
    store = Path(store)
    sha = {"spec": sp.spec_sha(spec), "code": sp.code_sha()}
    for d in OUTPUTS:
        (store / d).mkdir(parents=True, exist_ok=True)
    loaded = load_state(store)
    st = loaded[0] if loaded else init_state(store, snap_root, spec, sha, pin_rec)
    caps, extra = window_captures(snap_root, spec)
    sweeps = sweep_dirs(sweep_root)
    slots = sp.window_slots(spec)
    res: Counter = Counter()
    for s in slots:
        miss_path = status_path(store, spec, s, None)
        recorded_missing = miss_path.exists()
        cap = None if recorded_missing else caps.get(s)
        done_path = miss_path if recorded_missing else status_path(store, spec, s, cap)
        if done_path.exists() and st.last_slot >= s:
            continue
        if st.last_slot > s - 1 or st.last_slot < s - 1:
            raise M1Refusal(f"state chain broken before slot {s}: the state file's last folded slot is {st.last_slot}, expected {s - 1} "
                            f"(a state holding a capture at or after k, or a gap, makes the run refuse)")
        g = sp.slot_time(spec, s)
        if cap is None:
            if not recorded_missing and now < g + spec["missing_after_grid_s"]:
                res["waiting_for_slot"] += 1
                break
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
    for s in slots:  # late captures of slots already recorded missing stay unprocessed (counted)
        cap = caps.get(s)
        if cap is not None and status_path(store, spec, s, None).exists():
            p = store / "status" / f"late_{cap['capture_id']}.json"
            _write_once(p, dumps({"kind": "late_capture_ignored", "capture_id": cap["capture_id"], "slot": s, "capture_start_utc": sp.iso(cap["start"])}).encode(), _same_json)
            res["late_capture_ignored"] += 1
    res["duplicate_slot_capture_ignored"] += len(extra)
    rec = {"now_utc": sp.iso(now), "peak_rss_mb": peak_rss_mb(), "spec_sha": sha["spec"], "code_sha": sha["code"]} | dict(res)
    (store / "logs").mkdir(parents=True, exist_ok=True)
    with open(store / "logs" / "j1_runs.jsonl", "a") as fh:
        fh.write(dumps(rec) + "\n")
    return rec


# --- audit and close ----------------------------------------------------------------------------------------------------------------------

def load_statuses(store: Path) -> tuple[dict | None, list[dict], list[dict]]:
    init = None
    chain: list = []
    late: list = []
    for p in sorted((Path(store) / "status").glob("*.json")):
        d = json.loads(p.read_text())
        if d.get("kind") == "init":
            init = d
        elif d.get("kind") == "late_capture_ignored":
            late.append(d)
        else:
            chain.append(d)
    return init, sorted(chain, key=lambda d: d["slot"]), late


def audit_chain(store: Path, spec: dict) -> dict:
    """Void case 11.2(a): every slot in order, each status's state sha before equal to the previous one's after (starting at the init status)."""
    init, chain, late = load_statuses(store)
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
           "missing_slots": audit["missing_slots"], "late_capture_ignored": audit["late_capture_ignored"], "units": n_units, "chain": audit, "files": files}
    p = store / "manifest.json"
    _write_once(p, dumps(man).encode(), _same_json)
    return man | {"manifest_sha256": sp.sha256_file(p)}
