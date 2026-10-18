# ruff: noqa: E501
"""CB11-P / CB11-A shared parts (docs/research_lab/CREATIVE_BATCH_11.md sections 1.3, 1.4, 2.3, 2.6, 2.7, CB11-F; round-1 revision).

Strict Gamma parser for the P and A frames (stored whitelist; the outcome-adjacent fields are routed to separate in-memory accessors and the P guarded file only),
the transaction files (market, time, YES-terms price, size: no side, wallet or hash), the freeze-part declaration hash (W and P/A are hashed separately so W can
freeze first), the P/A rules file ``seals/cb11_pa_rules.json`` (function SOURCE hashed over the P/A modules and the shared functions they call; it is separate from
``cb11_rules.json`` so adding P/A leaves the W rules hash untouched) and small numeric helpers. No outcome analysis lives here.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import inspect
import json
import math
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from . import cb8_common as cm
from . import cb9_common as c9
from . import cb10_common as c10
from . import cb11_common as c11

Refused = cm.Refused
NotNow = cm.NotNow

DAY = 86400.0
HOUR = 3600.0
PA_RULES_VERSION = "cb11-pa-rules-v1"
PA_RULES_FILE = c11.SEALS_DIR / "cb11_pa_rules.json"
FREEZE_PART = "PA"
MDE_Z = 2.326 + 0.842  # z_0.99 + z_0.80
TX_COLUMNS = ["ts", "price", "size"]

# Stored Gamma columns (design 1.4): no outcome, status, price, volume or liquidity field is ever stored in the frames.
PA_COLUMNS = ["market_id", "condition_id", "token0", "token1", "start_epoch", "end_epoch", "neg_risk", "neg_risk_market_id", "event_id", "event_ids", "series_ids", "tag_ids",
              "fee_rate"]
GAMMA_FORBIDDEN = tuple(c10.GAMMA_FORBIDDEN) + ("closedTime", "outcomePrices", "umaResolutionStatus", "umaResolutionStatuses", "lastTradePrice", "bestBid", "bestAsk", "volumeNum")


def ep(d: str) -> float:
    return cm.ep(d + "T00:00:00Z")


def day_of(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, UTC).strftime("%Y-%m-%d")


def iso_week_of(epoch: float) -> str:
    y, w, _ = datetime.fromtimestamp(epoch, UTC).isocalendar()
    return f"{y}-W{w:02d}"


def month_of(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, UTC).strftime("%Y-%m")


def utc_midnight(epoch: float) -> float:
    return float(np.floor(epoch / DAY) * DAY)


def fnum(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return math.nan


def isnan(x) -> bool:
    return isinstance(x, float) and math.isnan(x)


def blank(x):
    return "" if isnan(x) else x


# =====================================================================================================================================
# Gamma parser (stored whitelist) and the separate in-memory / guarded accessors
# =====================================================================================================================================


def _tag_ids(m: dict) -> str:
    ids: list[str] = []
    for src in [m.get("tags"), *(e.get("tags") for e in (m.get("events") if isinstance(m.get("events"), list) else []) if isinstance(e, dict))]:
        for t in (src if isinstance(src, list) else []):
            if isinstance(t, dict) and t.get("id") is not None and str(t["id"]) not in ids:
                ids.append(str(t["id"]))
    return ";".join(ids)


def pa_row(m: dict) -> dict | None:
    """The ONLY stored parser of the P and A frames: ``id, conditionId, clobTokenIds, startDate (createdAt if missing), endDate, negRisk, negRiskMarketID,
    event ids, series ids, tag ids, feeSchedule rate``. ``None`` unless the market has an id, a condition id, two outcome labels and two token ids. Every
    other field (``closedTime``, ``outcomePrices``, ``umaResolutionStatus(es)``, prices, volume, liquidity, the text) is dropped here; the text and the
    outcome-adjacent fields are reachable only through :func:`pa_aux` / :func:`pa_guarded`."""
    if not isinstance(m, dict) or m.get("id") is None or not m.get("conditionId"):
        return None
    labels = c10._listish(m.get("outcomes"))
    toks = [str(x) for x in c10._listish(m.get("clobTokenIds"))]
    if len(labels) != 2 or len(toks) != 2:
        return None
    evs = [e for e in (m.get("events") if isinstance(m.get("events"), list) else []) if isinstance(e, dict)]
    eids, sids = [], []
    for e in evs:
        if e.get("id") is not None and str(e["id"]) not in eids:
            eids.append(str(e["id"]))
        for s in (e.get("series") if isinstance(e.get("series"), list) else []):
            if isinstance(s, dict) and s.get("id") is not None and str(s["id"]) not in sids:
                sids.append(str(s["id"]))
    fs = m.get("feeSchedule") if isinstance(m.get("feeSchedule"), dict) else {}
    start = c10._epoch(m.get("startDate"))
    if not math.isfinite(start):
        start = c10._epoch(m.get("createdAt"))
    return {"market_id": str(m["id"]), "condition_id": str(m["conditionId"]), "token0": toks[0], "token1": toks[1], "start_epoch": start, "end_epoch": c10._epoch(m.get("endDate")),
            "neg_risk": int(bool(m.get("negRisk"))), "neg_risk_market_id": str(m.get("negRiskMarketID") or ""), "event_id": eids[0] if eids else "", "event_ids": ";".join(eids),
            "series_ids": ";".join(sids), "tag_ids": _tag_ids(m), "fee_rate": c10._num(fs.get("rate"))}


def assert_pa_whitelisted(row: dict, extra: tuple[str, ...] = ()) -> None:
    bad = [k for k in row if k not in PA_COLUMNS and k not in extra]
    if bad:
        raise Refused(f"non-whitelisted fields {bad} in a CB11 P/A frame row")


def pa_aux(m: dict) -> dict:
    """In-memory only (never stored): the question, the first event title and end date, the fee-type string, the number ``volumeNum`` (A stores only the boolean
    ``vol_ok``) and the slug. Used for the frozen text flags, the entity rule and the topic labels."""
    evs = [e for e in (m.get("events") if isinstance(m.get("events"), list) else []) if isinstance(e, dict)]
    return {"question": str(m.get("question") or "")[:300], "slug": str(m.get("slug") or "")[:200], "event_title": str(evs[0].get("title") or "")[:300] if evs else "",
            "event_end": c10._epoch(evs[0].get("endDate")) if evs else math.nan, "fee_type": m.get("feeType"), "volume": c10._num(m.get("volumeNum")),
            "created": c10._epoch(m.get("createdAt")), "end": c10._epoch(m.get("endDate"))}


def pa_guarded(m: dict) -> dict:
    """The separate accessor that routes the outcome-adjacent fields (outcome vector, UMA status, close time) to the P guarded file ONLY."""
    return {"market_id": str(m.get("id")), "outcome_prices": json.dumps([str(x) for x in c10._listish(m.get("outcomePrices"))]),
            "uma_status": str(m.get("umaResolutionStatus") or ""), "closed_epoch": c10._epoch(m.get("closedTime"))}


def topic_label(row: dict, aux: dict) -> str:
    """One category label from listing fields (fee type, question, event title, slug): ``sports`` / ``crypto`` / ``weather`` / ... for the exclusions."""
    from astrolabe.research_panel.pairing import fee_category  # noqa: PLC0415

    from . import cb7_common as c7  # noqa: PLC0415
    from . import history_topics  # noqa: PLC0415

    fc = fee_category(aux.get("fee_type")) or ""
    if c7.is_weather(fc, aux["question"], aux["event_title"]):
        return "weather"
    return history_topics.topic_of(aux["question"], aux["event_title"], aux["slug"], fc)


def event_key(r: dict) -> str:
    return (str(r.get("event_ids") or "").split(";")[0] or str(r.get("event_id") or "")) or f"m{r['market_id']}"


# =====================================================================================================================================
# Transactions (aggregated at fetch; market, ts, YES-terms price, size)
# =====================================================================================================================================


def write_tx_file(fr, path: Path, tx: list[tuple[float, float, float]]) -> None:
    fr.budget.write_gz_csv(path, TX_COLUMNS, ([a, b, c] for a, b, c in tx))
    fr.record_file(path)


def read_tx_file(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    ts, pr, sz = [], [], []
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            ts.append(float(r["ts"]))
            pr.append(float(r["price"]))
            sz.append(float(r["size"]))
    o = np.argsort(np.array(ts), kind="stable")
    return np.array(ts)[o], np.array(pr)[o], np.array(sz)[o]


def vwap_before(tx: tuple[np.ndarray, np.ndarray, np.ndarray] | None, s: float, win_s: float = HOUR, back_s: float = 6 * HOUR) -> float:
    """Price at ``s`` from transactions strictly before ``s``: the size-weighted VWAP of those in ``[s - win_s, s)``, else the last in ``[s - back_s, s)``, else NaN."""
    if tx is None or len(tx[0]) == 0:
        return math.nan
    ts, pr, sz = tx
    hi = int(np.searchsorted(ts, s, side="left"))
    if hi == 0:
        return math.nan
    lo = int(np.searchsorted(ts, s - win_s, side="left"))
    if hi > lo and sz[lo:hi].sum() > 0:
        return float((pr[lo:hi] * sz[lo:hi]).sum() / sz[lo:hi].sum())
    if ts[hi - 1] >= s - back_s:
        return float(pr[hi - 1])
    return math.nan


# =====================================================================================================================================
# Statistics helpers
# =====================================================================================================================================


def boot_se(v: np.ndarray, cl: np.ndarray, rng: np.random.Generator, n_inner: int) -> float:
    """Cluster-bootstrap standard error of mean(v)."""
    import pandas as pd  # noqa: PLC0415

    codes, uniq = pd.factorize(np.asarray(cl).astype(str))
    g = len(uniq)
    if g < 2:
        return math.nan
    s = np.bincount(codes, weights=np.asarray(v, float), minlength=g)
    c = np.bincount(codes, minlength=g).astype(float)
    idx = rng.integers(0, g, (n_inner, g))
    means = s[idx].sum(1) / np.maximum(c[idx].sum(1), 1e-12)
    return float(means.std(ddof=1))


def logistic_slope(y: np.ndarray, x: np.ndarray, iters: int = 50) -> float:
    """Slope of the logistic regression of ``y`` (0/1) on ``x`` = logit(p) with an intercept (IRLS); > 1 is underconfidence (reported, uncounted)."""
    y, x = np.asarray(y, float), np.asarray(x, float)
    if len(y) < 10 or y.min() == y.max():
        return math.nan
    X = np.column_stack([np.ones_like(x), x])
    b = np.zeros(2)
    for _ in range(iters):
        eta = np.clip(X @ b, -30, 30)
        mu = 1.0 / (1.0 + np.exp(-eta))
        w = np.maximum(mu * (1 - mu), 1e-9)
        z = eta + (y - mu) / w
        xtw = X.T * w
        try:
            nb = np.linalg.solve(xtw @ X, xtw @ z)
        except np.linalg.LinAlgError:
            return math.nan
        if np.max(np.abs(nb - b)) < 1e-8:
            b = nb
            break
        b = nb
    return float(b[1])


def tercile_labels(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, float)
    if len(x) == 0:
        return np.array([], dtype=object)
    q1, q2 = np.quantile(x, [1 / 3, 2 / 3])
    return np.where(x <= q1, "low", np.where(x <= q2, "mid", "high")).astype(object)


def months_ok(months: np.ndarray, values_by_month_fn, min_units: int = 100, share: float = 2 / 3) -> dict:
    """Month rule: the sign (value > 0) holds in at least ``share`` of the months with at least ``min_units`` units. ``values_by_month_fn(month) -> (n, value)``."""
    per, ok_n, n_m = {}, 0, 0
    for mo in sorted(set(np.asarray(months).astype(str).tolist())):
        n, val = values_by_month_fn(mo)
        per[mo] = {"n": int(n), "value": None if val is None or not math.isfinite(val) else float(val)}
        if n >= min_units:
            n_m += 1
            ok_n += int(val is not None and math.isfinite(val) and val > 0)
    return {"by_month": per, "months_counted": n_m, "months_positive": ok_n, "ok": bool(n_m > 0 and ok_n / n_m >= share)}


# =====================================================================================================================================
# Resumable-fetch helpers
# =====================================================================================================================================


def in_progress(fr, why: str) -> dict:
    m = fr.manifest(why, {"transient": True})
    m["status"] = "in_progress"
    return m


def read_jsonl_by(path: Path, key: str) -> dict[str, dict]:
    have: dict[str, dict] = {}
    if Path(path).exists():
        for line in Path(path).read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                have[str(rec[key])] = rec
    return have


def append_jsonl(path: Path, rec: dict) -> None:
    with Path(path).open("a") as fh:
        fh.write(json.dumps(rec, default=float, sort_keys=True) + "\n")


def state_flag(rdir: Path, name: str) -> bool:
    mp = Path(rdir) / "manifest.json"
    if not mp.exists():
        return False
    return bool((json.loads(mp.read_text()).get("state") or {}).get(name))


# =====================================================================================================================================
# Rules file and freeze part (P and A; separate from cb11_rules.json)
# =====================================================================================================================================


def _shared_funcs() -> tuple:
    return (c11.cluster_p, c11.cluster_p_week, c11.placebo_advance_rate, c11.one_sided_boot_p, c11.open_guarded, c11.batch_holm_label, c11.seal_holdout,
            c11.verify_holdout_seal, c11.require_disk, c11.drop_by_keys_w, c10.cluster_p_d, c10.contrast_pseudo, c10.drop_by_keys, c10.placebo_advance_rate, c10.leave_one_out_sign,
            c9.holm, c9.top_k_drop_mask, c9.cluster_bootstrap_means)


def _pa_mods():
    from . import cb11_a, cb11_p  # noqa: PLC0415

    return [cb11_p, cb11_a]


def freeze_part_pa() -> dict:
    """The declaration the P/A part of ``model_specs/cb11_v1.json`` must carry: the P and A ``declared()`` blocks, the P/A function-source hashes and their own
    sha256 (``declaration_sha256``). The W part is hashed separately, so W can freeze first and no P/A read changes it."""
    mods = _pa_mods()
    funcs = [f for m in mods for f in m.rule_funcs()] + list(rule_funcs())
    body = {"declared": {m.__name__.rsplit(".", 1)[-1]: m.declared() for m in mods}, "version": PA_RULES_VERSION,
            "funcs_sha256": hashlib.sha256("\n".join(inspect.getsource(f) for f in funcs).encode()).hexdigest()}
    body = json.loads(json.dumps(body, sort_keys=True, default=str))
    return {**body, "declaration_sha256": hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()}


def require_freeze_pa(spec_path: Path | None = None, *, require_committed: bool = True) -> str:
    """Screens and reps of P and A refuse before the P/A part of the CB11 freeze is committed AND equals this code's declaration (stricter than the W part, which
    only checks that its part exists)."""
    c11.require_freeze(FREEZE_PART, spec_path, require_committed=require_committed)
    doc = json.loads(Path(spec_path or c11.FREEZE_SPEC).read_text())[FREEZE_PART]
    want = freeze_part_pa()["declaration_sha256"]
    if not isinstance(doc, dict) or doc.get("declaration_sha256") != want:
        raise Refused(f"the P/A part of the CB11 freeze spec does not carry this code's declaration_sha256 {want}; refusing")
    return want


def pa_rules_doc() -> dict:
    mods = _pa_mods()
    funcs = [f for m in mods for f in m.rule_funcs()] + list(rule_funcs()) + list(_shared_funcs())
    seen: set[int] = set()
    funcs = [f for f in funcs if not (id(f) in seen or seen.add(id(f)))]
    return {"rules_version": PA_RULES_VERSION, "declared": {m.__name__.rsplit(".", 1)[-1]: m.declared() for m in mods},
            "common": {k: c11.common_declared()[k] for k in ("t11_hist_end", "stage1", "stage2", "uncertainty", "placebos", "counting", "disk", "stall", "wallet_and_side")},
            "freeze_part": {"name": FREEZE_PART, "rule": "the P/A part of model_specs/cb11_v1.json carries freeze_part_pa()['declaration_sha256']; the W part is hashed separately"},
            "func_sources_sha256": {f"{f.__module__.rsplit('.', 1)[-1]}.{f.__qualname__}": hashlib.sha256(inspect.getsource(f).encode()).hexdigest() for f in funcs},
            "funcs_sha256": hashlib.sha256("\n".join(inspect.getsource(f) for f in funcs).encode()).hexdigest()}


def pa_rules_file_doc() -> dict:
    d = json.loads(json.dumps(pa_rules_doc(), sort_keys=True, default=str))
    return {**d, "rules_sha256": cm.sha_obj(d)}


def write_pa_rules(path: Path | None = None) -> Path:
    path = Path(path or PA_RULES_FILE)
    want = pa_rules_file_doc()
    if path.exists() and json.loads(path.read_text()) != want:
        raise Refused(f"{path} exists with different content; a rules file is never rewritten")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(want, indent=1, sort_keys=True) + "\n")
    return path


def verify_pa_rules(path: Path | None = None, *, require_committed: bool = True) -> str:
    """Refuse (exit 2) unless the P/A rules file equals the code's. Returns its ``rules_sha256``."""
    path = Path(path or PA_RULES_FILE)
    if not path.exists():
        raise Refused(f"P/A rules file {path} not found")
    if require_committed:
        from . import cb1_history  # noqa: PLC0415

        if not cb1_history.spec_committed(path):
            raise Refused(f"P/A rules file {path} is not committed (or differs from HEAD)")
    try:
        doc = json.loads(path.read_text())
    except ValueError as exc:
        raise Refused(f"P/A rules file {path} unreadable") from exc
    want = pa_rules_file_doc()
    if doc != want:
        raise Refused(f"P/A rules hash mismatch: file {doc.get('rules_sha256')} != code {want['rules_sha256']}")
    return want["rules_sha256"]


def pa_rule_funcs() -> list:
    """Every function whose SOURCE the P/A rules part hashes (P and A modules, this module, and the shared functions they call)."""
    mods = _pa_mods()
    funcs = [f for m in mods for f in m.rule_funcs()] + list(rule_funcs()) + list(_shared_funcs())
    seen: set[int] = set()
    return [f for f in funcs if not (id(f) in seen or seen.add(id(f)))]


def pa_declared() -> dict:
    """The declared P/A constants (what a v2 rules file's PA part carries)."""
    return {m.__name__.rsplit(".", 1)[-1]: m.declared() for m in _pa_mods()}


def stage2_k_pa(results_dir: Path, explicit: int | None, fam: str) -> int:
    """Stage-2 Holm k for the P / A replication of family ``fam`` WITHOUT relying on the W results coupling. If all three Stage-1 results files exist ``explicit``
    (``--stage2-k``) must equal the derived k. Otherwise (d1) ``explicit`` is required and must be >= the conservative own-family count of ``stage2_k(own=fam)``
    (every test of a not-yet-final family counted as advancing, N7: k can only be too large, alpha / k at least as strict as the final one); a smaller k is refused."""
    try:
        derived = c11.stage2_k(results_dir)["k"]
    except NotNow:
        derived = None
    if explicit is None and derived is None:
        raise NotNow("Stage-2 k is not fixed until the last Stage-1 result is final; pass --stage2-k once it is")
    if explicit is not None and derived is not None and int(explicit) != derived:
        raise Refused(f"--stage2-k {explicit} differs from the derived k {derived}")
    k = int(explicit if explicit is not None else derived)
    if k < 1:
        raise Refused("Stage-2 k must be >= 1")
    if derived is None:
        floor_k = c11.stage2_k(results_dir, own=fam)["k"]  # NotNow while the family's own Stage-1 result is missing
        if k < floor_k:
            raise Refused(f"--stage2-k {k} is below the conservative count {floor_k} (every unfinished Stage-1 test counted as advancing); refusing a looser alpha / k")
    return k


PA_RULE_FUNCS = pa_rule_funcs  # callable list for the PA rules part: PA_RULE_FUNCS()


def declared() -> dict:
    return {"version": PA_RULES_VERSION, "stored_columns": list(PA_COLUMNS), "forbidden_gamma_fields": list(GAMMA_FORBIDDEN), "tx_columns": list(TX_COLUMNS), "mde_z": MDE_Z,
            "cb11_rules_pins": {"h8_tail_b": c11.H8_TAIL_B_KEYS_SHA256}}


def rule_funcs() -> tuple:
    return (pa_row, assert_pa_whitelisted, pa_aux, pa_guarded, topic_label, event_key, write_tx_file, read_tx_file, vwap_before, boot_se, logistic_slope, tercile_labels,
            months_ok, in_progress, read_jsonl_by, append_jsonl, state_flag, freeze_part_pa, require_freeze_pa, declared)
