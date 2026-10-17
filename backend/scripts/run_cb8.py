# ruff: noqa: E501
"""CB8 runner, collection and fetch side (docs/research_lab/CREATIVE_BATCH_8.md CB8-H "Collection", CB8-W "Data", CB8-F). Run from
cwd=backend (queue worker). EXPLORATORY / PROSPECTIVE DATA ONLY: no edge, calibration or profitability claim; no analysis code here.

    python scripts/run_cb8.py rules --which holders|flow    # write docs/research_lab/seals/cb8_holders_rules_v3.json | cb8_flow_rules.json (commit first)
    python scripts/run_cb8.py key-fingerprint               # print the strict-loaded key's fingerprint (never the key)
    python scripts/run_cb8.py holders-smoke ...             # q0160b (smoke v2): /oi frame of every base market + 20 live markets, counts and ratios only, WRITE-ONCE
    python scripts/run_cb8.py holders-snap ...              # q0162: daily /holders snapshot (prospective; rolling)
    python scripts/run_cb8.py holders-prints ...            # q0163: windowed prints and capture marks (rolling)
    python scripts/run_cb8.py holders-pin-h2 --start-utc T  # write-once pin of window 2 (after the CB8 freeze commit + 2 h)
    python scripts/run_cb8.py flow-fetch ...                # q0167: one resumable chunk of the h9_flow fetch
    python scripts/run_cb8.py flow-seal                     # q0168: seal h9_flow (seal-time drops, committed copy)
    python scripts/run_cb8.py rules --which updown          # write docs/research_lab/seals/cb8_rules_v2.json (B data rules; v1 cb8_rules.json is superseded; commit first)
    python scripts/run_cb8.py derive-exclusion-ids --kind c1_legs|cb5_listings --src PATH --out CSV   # ids CSV + .meta.json sidecar for the REQUIRED q0164 --extra-pin
    python scripts/run_cb8.py smoke ...                     # q0161: Data API paging, Binance checksums, pmxt HEADs; counts only, WRITE-ONCE
    python scripts/run_cb8.py exclusion-keys ...            # q0164: ids and event / neg-risk / series keys of every prior sample and seal copy
    python scripts/run_cb8.py updown-frame ...              # q0165: Gamma frame, rule-text checks, week split, Binance 1m archive (outcome guard)
    python scripts/run_cb8.py updown-books ...              # q0166: pmxt coverage audit, book states at the checkpoints, last-15-minute prints, HOLDOUT seal

Exit codes: 0 ok / transient pause / idle heartbeat / terminal state (holders_collection_complete, holders_prints_complete,
flow_fetch_complete, disjointness_unverified); 1 error; 2 refusal of a guard (rules hash, key missing / mode-unsafe / fingerprint
mismatch, smoke not met or result exists, run id, refused root, declared arguments changed); 4 disk budget exhausted (a declared end
state, never retried); 75 (EX_TEMPFAIL) data-dumps headroom refusal, before the declared start, nothing to do yet, or a network failure
in the smoke (nothing written): the queue retries in 30 minutes. A rolling job that is idle returns exit 0 (status idle_heartbeat) at
least every 10 hours so the queue's 48-consecutive-tempfail limit never fires while it waits.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

REFUSED, TEMPFAIL, DISK_BUDGET = 2, 75, 4


def _emit(obj: dict) -> None:
    print(json.dumps(obj, default=str, sort_keys=True))


def _bad(checks: dict) -> list[str]:
    return [f"{k}={got!r} (declared {want!r})" for k, (got, want) in checks.items() if got != want]


def _data_path(p: str | None, default: Path, data_dumps: Path | None) -> Path:
    if not p:
        return default
    q = Path(p)
    return q if q.is_absolute() or q.exists() or data_dumps is None else data_dumps / q


def _guarded(fn):
    """Run ``fn`` and map the CB8 exceptions to exit codes; ``fn`` returns (exit code, payload dict)."""

    def wrapper(a) -> int:
        from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

        try:
            code, payload = fn(a, cm)
        except cm.Refused as exc:
            _emit({"refused": str(exc)})
            return REFUSED
        except cm.NotNow as exc:
            _emit({"tempfail": str(exc)})
            return TEMPFAIL
        except (cm.SealError, FileNotFoundError) as exc:
            _emit({"refused": str(exc)})
            return REFUSED
        except Exception as exc:
            _emit({"error": f"{type(exc).__name__}: {exc}"[:300]})
            return 1
        _emit(payload)
        return code

    return wrapper


def _result(m: dict, cm, extra_keys=("day", "idle", "idle_kind")) -> tuple[int, dict]:
    if m.get("status") == cm.DISK_BUDGET_TOKEN:
        return DISK_BUDGET, {"status": cm.DISK_BUDGET_TOKEN, "stopped": m.get("stopped"), "counts": m.get("counts")}
    return 0, {"status": m.get("status") or ("in_progress" if m.get("stopped") else None), "stopped": m.get("stopped"), "complete": m.get("complete"),
               "counts": m.get("counts"), "transient": m.get("transient"), "requests": m.get("requests"), **{k: m.get(k) for k in extra_keys if m.get(k) is not None}}


def _setup(a, cm, kind: str):
    """(rules_sha, fingerprint, key): rules hash check first, then the strict key with the pinned fingerprint."""
    path = Path(a.rules) if a.rules else (cm.HOLDERS_RULES_FILE if kind == "holders" else cm.FLOW_RULES_FILE)
    sha, fp = cm.verify_rules(kind, path, require_committed=not a.allow_uncommitted_rules)
    key = cm.load_wallet_key_strict(Path(a.wallet_key_path) if a.wallet_key_path else None, fp)
    return sha, fp, key


def _hist_common(a, cm):
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    standalone = bool(a.standalone)
    data_dumps = Path(a.data_dumps) if a.data_dumps else cm.DATA_DUMPS
    return dict(rps=min(a.rps, 4.0), disk_cap=int(a.disk_cap_gb * 1024**3), budget_min=a.budget_min, data_dumps=data_dumps,
                data_dumps_cap_gb=a.data_dumps_cap_gb, live_check=None if standalone else hb.live_pass_or_lock,
                health_snapshot_root=None if standalone else Path(a.snapshot_root or cm.c4.SNAPSHOT_ROOT)), data_dumps


def cmd_rules(a) -> int:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    try:
        kind = a.which
        if kind == "updown":  # B rules: no wallet is hashed, so no key is read and no fingerprint is pinned
            from astrolabe.research_lab import cb8_updown as u  # noqa: PLC0415

            out = u.write_rules(Path(a.path) if a.path else u.RULES_FILE)
            doc = u.rules_file_doc()
            _emit({"written": str(out), "rules_sha256": doc["rules_sha256"], "funcs_sha256": doc["funcs_sha256"]})
            return 0
        path = Path(a.path) if a.path else (cm.HOLDERS_RULES_FILE if kind == "holders" else cm.FLOW_RULES_FILE)
        fp = a.key_fingerprint or cm.key_fingerprint(cm.load_wallet_key_strict(Path(a.wallet_key_path) if a.wallet_key_path else None))
        out = cm.write_rules(kind, path, fp)
    except cm.Refused as exc:
        _emit({"refused": str(exc)})
        return REFUSED
    doc = cm.rules_file_doc(kind, fp)
    _emit({"written": str(out), "rules_sha256": doc["rules_sha256"], "funcs_sha256": doc["funcs_sha256"], "wallet_key_fingerprint": fp})
    return 0


def cmd_key_fp(a) -> int:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    try:
        _emit({"wallet_key_fingerprint": cm.key_fingerprint(cm.load_wallet_key_strict(Path(a.wallet_key_path) if a.wallet_key_path else None))})
    except cm.Refused as exc:
        _emit({"refused": str(exc)})
        return REFUSED
    return 0


@_guarded
def cmd_holders_smoke(a, cm):
    from astrolabe.research_lab import cb8_holders as h  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    out = _data_path(a.out, h.SMOKE_DEFAULT, None)
    if out.exists():  # write-once: a FAIL can never be replaced by a later PASS
        raise cm.Refused(f"smoke result {out} already exists; it is write-once")
    declared = _bad({"n": (a.n, h.N_SMOKE), "seed": (a.seed, h.SEED_SMOKE)})
    if declared:
        raise cm.Refused(f"arguments differ from the declaration: {declared}")
    sha, fp, key = _setup(a, cm, "holders")
    caps = h.list_captures(Path(a.snapshot_root or cm.c4.SNAPSHOT_ROOT))
    if not caps:
        raise cm.NotNow("no complete capture on this host")
    cap = caps[-1]
    base, _ = h.holders_frame(h.read_capture(cap["dir"]))
    lim = hb.Limiter(hb.httpx_transport(), rps=min(a.rps, 2.0), live_check=None if a.standalone else hb.live_pass_or_lock)
    res = h.holders_smoke(lim, key, base, sha, fp, cap["capture_id"], oi_rps=a.oi_rps)
    cm.write_once_json(out, res)
    return 0, {"smoke": res["pass"], "a": res["criterion_a_http_ok"], "b": res["criterion_b_shape"], "c": res["criterion_c_rows_per_token_le_20"],
               "e": res["criterion_e_oi_units_label"], "f": res["criterion_f_key_fingerprint"], "g": res["criterion_g_paging"],
               "h": res["criterion_h_oi_source"], "n_http_ok": res["n_http_ok"], "frame_size": res["frame_size"], "written": str(out)}


def _holders_run(a, cm, which: str):
    from astrolabe.research_lab import cb8_holders as h  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    kw, _ = _hist_common(a, cm)
    root = Path(a.root) if a.root else h.HOLDERS_DIR
    cm.refuse_path(root)
    smoke = _data_path(a.smoke, h.SMOKE_DEFAULT, None)
    sha, fp, key = _setup(a, cm, "holders")
    common = dict(key=key, fp=fp, rules_sha=sha, smoke_path=smoke, snapshot_root=Path(a.snapshot_root) if a.snapshot_root else None, **kw)
    if which == "snap":
        common["oi_rps"] = min(a.oi_rps, h.OI_RPS)
    declared_cap = h.SNAP_OUTPUT_CAP_GB if which == "snap" else h.PRINTS_OUTPUT_CAP_GB
    if abs(a.disk_cap_gb - declared_cap) > 1e-9:
        raise cm.Refused(f"arguments differ from the declaration: ['disk_cap_gb={a.disk_cap_gb!r} (declared {declared_cap!r})']")
    if which == "snap":
        bad = _bad({"n_main": (a.n_main, h.N_MAIN), "n_sports": (a.n_sports, h.N_SPORTS)})
        if bad:
            raise cm.Refused(f"arguments differ from the declaration: {bad}")
        m = h.holders_snap(root, hb.httpx_transport(), n_main=a.n_main, n_sports=a.n_sports, **common)
    else:
        bad = _bad({"lag_h": (a.lag_h, h.LAG_H), "day_pages": (a.day_pages, h.PRINT_PAGES)})
        if bad:
            raise cm.Refused(f"arguments differ from the declaration: {bad}")
        m = h.holders_prints(root, hb.httpx_transport(), lag_h=a.lag_h, day_pages=a.day_pages, **common)
    return _result(m, cm)


@_guarded
def cmd_holders_snap(a, cm):
    return _holders_run(a, cm, "snap")


@_guarded
def cmd_holders_prints(a, cm):
    return _holders_run(a, cm, "prints")


@_guarded
def cmd_pin_h2(a, cm):
    from astrolabe.research_lab import cb8_holders as h  # noqa: PLC0415

    t = datetime.strptime(a.start_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC).timestamp()
    return 0, h.pin_h2(Path(a.root) if a.root else h.HOLDERS_DIR, t, now=time.time())


@_guarded
def cmd_flow_fetch(a, cm):
    from astrolabe.research_lab import cb8_flow as f  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    kw, data_dumps = _hist_common(a, cm)
    bad = _bad({"n_main": (a.n_main, f.N_MAIN), "n_sports": (a.n_sports, f.N_SPORTS), "window_h": (a.window_h, f.WINDOW_H), "day_pages": (a.day_pages, f.DAY_PAGES),
                "disk_cap_gb": (a.disk_cap_gb, f.OUTPUT_CAP_GB)})
    if cm.c4._ep(a.cap_at) != cm.ep(f.HIST_END):
        bad.append(f"cap_at={a.cap_at!r}")
    if bad:
        raise cm.Refused(f"arguments differ from the declaration: {bad}")
    root = Path(a.root) if a.root else cm.HIST_ROOT
    sha, fp, key = _setup(a, cm, "flow")
    kw.pop("health_snapshot_root")
    m = f.flow_fetch(root, a.run_id, hb.httpx_transport(), key=key, fp=fp, rules_sha=sha,
                     exclusion_keys_path=_data_path(a.exclusion_keys, f.EXCLUSION_KEYS_DEFAULT, data_dumps),
                     smoke_path=_data_path(a.require_smoke, f.SMOKE_DEFAULT, data_dumps), n_main=a.n_main, n_sports=a.n_sports, day_pages=a.day_pages,
                     snapshot_root=None if a.standalone else Path(a.snapshot_root or cm.c4.SNAPSHOT_ROOT), cap_at=a.cap_at, **kw)
    return _result(m, cm)


@_guarded
def cmd_flow_seal(a, cm):
    from astrolabe.research_lab import cb8_flow as f  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    _sha, fp, _key = _setup(a, cm, "flow")
    res = f.flow_seal(Path(a.root) if a.root else cm.HIST_ROOT, a.run_id, fp=fp, transport=hb.httpx_transport(),
                      seals_dir=Path(a.seals_dir) if a.seals_dir else None, trials_path=Path(a.trials_path) if a.trials_path else None,
                      rps=min(a.rps, 2.0), live_check=None if a.standalone else hb.live_pass_or_lock)
    return 0, res


def _b_rules(a) -> str:
    from astrolabe.research_lab import cb8_updown as u  # noqa: PLC0415

    return u.verify_rules(Path(a.rules) if a.rules else u.RULES_FILE, require_committed=not a.allow_uncommitted_rules)


def _b_net(a, cm) -> dict:
    """Common keyword arguments of the B network jobs (no wallets): data-dumps guard, collector yield and health check."""
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    standalone = bool(a.standalone)
    return dict(rps=min(a.rps, 4.0), data_dumps=Path(a.data_dumps) if a.data_dumps else cm.DATA_DUMPS, data_dumps_cap_gb=a.data_dumps_cap_gb,
                live_check=None if standalone else hb.live_pass_or_lock, snapshot_root=None if standalone else Path(a.snapshot_root or cm.c4.SNAPSHOT_ROOT))


def _b_root(a, cm) -> Path:
    root = Path(a.root) if a.root else cm.CB8_DIR
    cm.refuse_path(root)
    return root


def _extra_pins(values: list[str] | None) -> list[dict]:
    out = []
    for v in values or []:
        parts = str(v).split(":")
        if len(parts) != 3 or len(parts[2]) != 64:
            raise ValueError(f"--extra-pin must be NAME:PATH:SHA256, got {v!r}")
        out.append({"name": parts[0], "kind": "ids", "path": parts[1], "sha256": parts[2]})
    return out


@_guarded
def cmd_smoke(a, cm):
    from astrolabe.research_lab import cb7_common as c7  # noqa: PLC0415
    from astrolabe.research_lab import cb8_updown as u  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415
    from astrolabe.research_lab import history_sources as hs  # noqa: PLC0415

    out = _data_path(a.out, u.SMOKE_DEFAULT, None)
    if out.exists():  # write-once: a FAIL can never be replaced by a later PASS
        raise cm.Refused(f"smoke result {out} already exists; it is write-once")
    declared = _bad({"n": (a.n, u.SMOKE_N), "seed": (a.seed, u.SMOKE_SEED_POOL), "candidates": (a.candidates, u.SMOKE_CANDIDATES)})
    if declared:
        raise cm.Refused(f"arguments differ from the declaration: {declared}")
    sha = _b_rules(a)
    files = cm.c6.verify_exclusion_files(c7.EXCLUSION_PINS, history_root=Path(a.history_root) if a.history_root else cm.HIST_ROOT,
                                         seals_dir=Path(a.seals_dir) if a.seals_dir else cm.SEALS_DIR)
    lim = hb.Limiter(hb.httpx_transport(), rps=min(a.rps, 4.0), live_check=None if a.standalone else hb.live_pass_or_lock)
    res = u.run_smoke(lim, files, c7.EXCLUSION_PINS, sha, blob_get=u.httpx_blob_get(), size_fn=hs.httpx_size)
    cm.write_once_json(out, res)
    return 0, {"smoke": res["pass"], "a": res["criterion_a_data_api_paging"], "b": res["criterion_b_binance_checksum"], "c": res["criterion_c_pmxt_heads"],
               "n_requested": res["n_requested"], "n_nonempty": res["n_nonempty"], "written": str(out)}


@_guarded
def cmd_exclusion_keys(a, cm):
    from astrolabe.research_lab import cb8_updown as u  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    if abs(a.disk_cap_gb - u.KEYS_OUTPUT_CAP_GB) > 1e-9:
        raise cm.Refused(f"arguments differ from the declaration: ['disk_cap_gb={a.disk_cap_gb!r} (declared {u.KEYS_OUTPUT_CAP_GB!r})']")
    sha = _b_rules(a)
    root = _b_root(a, cm)
    kw = _b_net(a, cm)
    u.smoke_ok(_data_path(a.require_smoke, u.SMOKE_DEFAULT, None), sha, ())  # the smoke must exist under this rules hash (queue order); criteria are checked by the consumers
    try:
        extra = _extra_pins(a.extra_pin)
    except ValueError as exc:
        raise cm.Refused(str(exc)) from None
    res = u.exclusion_keys(root, hb.httpx_transport(), rules_sha=sha, history_root=Path(a.history_root) if a.history_root else cm.HIST_ROOT,
                           seals_dir=Path(a.seals_dir) if a.seals_dir else None, extra_pins=extra, disk_cap=int(a.disk_cap_gb * 1024**3), dest_dir=root, **kw)
    if res.get("status") == cm.DISK_BUDGET_TOKEN:
        return DISK_BUDGET, {"status": cm.DISK_BUDGET_TOKEN, "stopped": res.get("stopped")}
    rep = res.get("exclusion_report") or {}
    return 0, {"status": res.get("status"), "stopped": res.get("stopped"), "complete": res.get("complete"), "n_ids": rep.get("n_ids"), "n_missing": rep.get("n_missing"),
               "missing_share": rep.get("missing_share"), "keys": rep.get("keys"), "transient": res.get("transient")}


@_guarded
def cmd_derive_exclusion_ids(a, cm):
    """Ids only: derive the ids CSV (+ ``.meta.json`` with the source sha256) of a REQUIRED q0164 extra pin. Offline, no network, write-once."""
    from astrolabe.research_lab import cb8_updown as u  # noqa: PLC0415

    out = Path(a.out)
    cm.refuse_path(out)
    meta = u.derive_exclusion_ids(a.kind, Path(a.src), out)
    return 0, {"written": str(out), "ids_sha256": meta["ids_sha256"], "source_sha256": meta["source_sha256"], "n_ids": meta["n_ids"], "pin_argument": f"--extra-pin {a.kind}:{out}:{meta['ids_sha256']}"}


@_guarded
def cmd_updown_frame(a, cm):
    from astrolabe.research_lab import cb8_updown as u  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    bad = _bad({"days": (a.days, f"{u.B_FIRST}:{u.B_END}"), "disk_cap_gb": (a.disk_cap_gb, u.FRAME_OUTPUT_CAP_GB)})
    if bad:
        raise cm.Refused(f"arguments differ from the declaration: {bad}")
    sha = _b_rules(a)
    root = _b_root(a, cm)
    kw = _b_net(a, cm)
    m = u.updown_frame(root, hb.httpx_transport(), rules_sha=sha, blob_get=u.httpx_blob_get(), smoke_path=_data_path(a.require_smoke, u.SMOKE_DEFAULT, None),
                       exclusion_keys_path=_data_path(a.exclusion_keys, u.EXCLUSION_KEYS_DEFAULT, None), disk_cap=int(a.disk_cap_gb * 1024**3),
                       budget_min=a.budget_min, **kw)
    return _result(m, cm)


@_guarded
def cmd_updown_books(a, cm):
    from astrolabe.research_lab import cb1_history  # noqa: PLC0415
    from astrolabe.research_lab import cb8_books as bk  # noqa: PLC0415
    from astrolabe.research_lab import cb8_updown as u  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415
    from astrolabe.research_lab import history_sources as hs  # noqa: PLC0415

    bad = _bad({"ingress_cap_gb": (a.ingress_cap_gb, bk.INGRESS_CAP_GB), "audit_hour": (a.audit_hour, bk.AUDIT_HOUR), "audit_days": (a.audit_days, bk.AUDIT_DAYS),
                "disk_cap_gb": (a.disk_cap_gb, bk.OUTPUT_CAP_GB)})
    if bad:
        raise cm.Refused(f"arguments differ from the declaration: {bad}")
    sha = _b_rules(a)
    root = _b_root(a, cm)
    kw = _b_net(a, cm)
    m = bk.books_fetch(root, hb.httpx_transport(), rules_sha=sha, fetch=hs.httpx_range_fetch(), size_fn=hs.httpx_size, smoke_path=_data_path(a.require_smoke, u.SMOKE_DEFAULT, None),
                       ingress_cap_gb=a.ingress_cap_gb, audit_hour=a.audit_hour, audit_days=a.audit_days, disk_cap=int(a.disk_cap_gb * 1024**3), budget_min=a.budget_min,
                       seals_dir=Path(a.seals_dir) if a.seals_dir else None,
                       is_committed=None if a.allow_uncommitted_rules else cb1_history.spec_committed, **kw)
    return _result(m, cm)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(q: argparse.ArgumentParser, *, root_help: str = "output root") -> None:
        q.add_argument("--root", default=None, help=root_help)
        q.add_argument("--rules", default=None)
        q.add_argument("--wallet-key-path", default=None, help="default ~/.arepo/wallet_hash_key (or AREPO_WALLET_HASH_KEY_PATH); never created")
        q.add_argument("--data-dumps", default=None)
        q.add_argument("--rps", type=float, default=2.0)
        q.add_argument("--standalone", action="store_true", help="no collector yield / health check (tests, off-host)")
        q.add_argument("--snapshot-root", default=None)
        q.add_argument("--allow-uncommitted-rules", action="store_true")

    def collect(q: argparse.ArgumentParser) -> None:
        common(q)
        q.add_argument("--smoke", default=None, help="holders smoke v2 result (default research_lab/creative_batch8/holders_smoke_v2.json)")
        q.add_argument("--oi-rps", type=float, default=4.0, help="pacing of the /oi frame build only (<= 4); /holders and /trades stay <= 2 rps")
        q.add_argument("--disk-cap-gb", type=float, required=True)
        q.add_argument("--data-dumps-cap-gb", type=float, default=12.5)
        q.add_argument("--budget-min", type=float, default=None)

    q = sub.add_parser("rules")
    q.add_argument("--which", choices=("holders", "flow", "updown"), default="holders")
    q.add_argument("--path", default=None)
    q.add_argument("--key-fingerprint", default=None, help="16 hex characters; default: computed from the strict-loaded key")
    q.add_argument("--wallet-key-path", default=None)
    q.set_defaults(fn=cmd_rules)

    q = sub.add_parser("key-fingerprint")
    q.add_argument("--wallet-key-path", default=None)
    q.set_defaults(fn=cmd_key_fp)

    q = sub.add_parser("holders-smoke")
    common(q)
    q.add_argument("--n", type=int, default=20)
    q.add_argument("--seed", default="arepo-cb8-hsmoke-v2")
    q.add_argument("--oi-rps", type=float, default=4.0, help="pacing of the /oi frame build only (<= 4)")
    q.add_argument("--out", default=None)
    q.set_defaults(fn=cmd_holders_smoke)

    q = sub.add_parser("holders-snap")
    collect(q)
    q.add_argument("--n-main", type=int, default=1500)
    q.add_argument("--n-sports", type=int, default=300)
    q.set_defaults(fn=cmd_holders_snap)

    q = sub.add_parser("holders-prints")
    collect(q)
    q.add_argument("--lag-h", type=float, default=30.0)
    q.add_argument("--day-pages", type=int, default=5)
    q.set_defaults(fn=cmd_holders_prints)

    q = sub.add_parser("holders-pin-h2")
    q.add_argument("--root", default=None)
    q.add_argument("--start-utc", required=True, help="T8_H2_start, YYYY-MM-DDTHH:MM:SSZ (>= T8_H1_end, after the CB8 freeze commit + 2 h)")
    q.set_defaults(fn=cmd_pin_h2)

    q = sub.add_parser("flow-fetch")
    common(q, root_help="history root (default data-dumps/research_lab/history)")
    q.add_argument("--run-id", default="h9_flow")
    q.add_argument("--n-main", type=int, default=1500)
    q.add_argument("--n-sports", type=int, default=300)
    q.add_argument("--window-h", type=int, default=72)
    q.add_argument("--day-pages", type=int, default=10)
    q.add_argument("--cap-at", default="2026-10-01T00:00Z")
    q.add_argument("--exclusion-keys", default="research_lab/creative_batch8/exclusion_keys.csv.gz")
    q.add_argument("--require-smoke", default="research_lab/creative_batch8/smoke.json")
    q.add_argument("--disk-cap-gb", type=float, required=True)
    q.add_argument("--data-dumps-cap-gb", type=float, default=12.5)
    q.add_argument("--budget-min", type=float, default=None)
    q.set_defaults(fn=cmd_flow_fetch, rps=4.0)

    q = sub.add_parser("flow-seal")
    common(q, root_help="history root")
    q.add_argument("--run-id", default="h9_flow")
    q.add_argument("--seals-dir", default=None)
    q.add_argument("--trials-path", default=None)
    q.set_defaults(fn=cmd_flow_seal)

    def bcommon(q: argparse.ArgumentParser) -> None:
        q.add_argument("--root", default=None, help="creative_batch8 root (default data-dumps/research_lab/creative_batch8)")
        q.add_argument("--rules", default=None, help="default docs/research_lab/seals/cb8_rules_v2.json")
        q.add_argument("--data-dumps", default=None)
        q.add_argument("--rps", type=float, default=2.0)
        q.add_argument("--standalone", action="store_true", help="no collector yield / health check (tests, off-host)")
        q.add_argument("--snapshot-root", default=None)
        q.add_argument("--allow-uncommitted-rules", action="store_true")
        q.add_argument("--history-root", default=None)
        q.add_argument("--seals-dir", default=None)
        q.add_argument("--require-smoke", default=None, help="default creative_batch8/smoke.json")
        q.add_argument("--data-dumps-cap-gb", type=float, default=12.5)
        q.add_argument("--budget-min", type=float, default=None)

    q = sub.add_parser("smoke")
    bcommon(q)
    q.add_argument("--n", type=int, default=20)
    q.add_argument("--candidates", type=int, default=200)
    q.add_argument("--seed", default="arepo-cb8-smoke-pool")
    q.add_argument("--out", default=None)
    q.set_defaults(fn=cmd_smoke)

    q = sub.add_parser("exclusion-keys")
    bcommon(q)
    q.add_argument("--disk-cap-gb", type=float, default=0.01)
    q.add_argument("--extra-pin", action="append", default=None, help="NAME:PATH:SHA256 of an ids CSV (market_id column) with its .meta.json sidecar; REQUIRED: c1_legs and cb5_listings (see derive-exclusion-ids); repeatable")
    q.set_defaults(fn=cmd_exclusion_keys)

    q = sub.add_parser("derive-exclusion-ids")
    q.add_argument("--kind", required=True, choices=["c1_legs", "cb5_listings"])
    q.add_argument("--src", required=True, help="c1_legs: cross_venue/matches.json; cb5_listings: the cb5_extract/listings directory")
    q.add_argument("--out", required=True, help="e.g. data-dumps/research_lab/creative_batch8/pins/<kind>_ids.csv (a .meta.json sidecar is written beside it)")
    q.set_defaults(fn=cmd_derive_exclusion_ids)

    q = sub.add_parser("updown-frame")
    bcommon(q)
    q.add_argument("--days", default="2026-04-13:2026-08-10")
    q.add_argument("--exclusion-keys", default=None, help="default creative_batch8/exclusion_keys.csv.gz")
    q.add_argument("--disk-cap-gb", type=float, required=True)
    q.set_defaults(fn=cmd_updown_frame)

    q = sub.add_parser("updown-books")
    bcommon(q)
    q.add_argument("--ingress-cap-gb", type=float, default=90.0)
    q.add_argument("--audit-hour", type=int, default=13)
    q.add_argument("--audit-days", type=int, default=20)
    q.add_argument("--disk-cap-gb", type=float, required=True)
    q.set_defaults(fn=cmd_updown_books)
    return ap


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    if getattr(a, "cmd", "") in ("flow-fetch", "flow-seal"):
        a.which = "flow"
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
