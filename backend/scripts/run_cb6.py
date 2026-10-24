# ruff: noqa: E501
"""CB6 runner, data side (docs/research_lab/CREATIVE_BATCH_6.md CB6-F and 10.3). Run from cwd=backend (queue worker).
EXPLORATORY: no edge, calibration or profitability claim.

    python scripts/run_cb6.py rules                 # write docs/research_lab/seals/cb6_tail_rules_v3.json (commit it before q0120b)
    python scripts/run_cb6.py exclusion-keys ...    # stop after the exclusion keys (Gamma lookup of the excluded ids)
    python scripts/run_cb6.py tail-smoke ...        # q0136 (smoke v2; q0135 v1 FAILED): 20-market fidelity-60 smoke test, counts only
    python scripts/run_cb6.py tail-fetch ...        # q0120 (alias fetch): one resumable chunk of the h8_tail fetch
                                                    # q0120b: --run-id h8_tail_b --topup-of h8_tail --windows-per-day 9 (amendment A-T1)
    python scripts/run_cb6.py tail-seal ...         # q0121 (alias seal): seal h8_tail (--topup-run h8_tail_b: union seal)
    python scripts/run_cb6.py verify-seal           # verify the seal against the committed copy

Exit codes: 0 ok / transient pause / terminal state (tail_fetch_complete, not_run_deadline, disjointness_unverified);
1 error; 2 refusal of a guard (rules hash, any exclusion file missing or mismatching its pin, smoke not PASS, run id,
declared arguments changed); 75 (EX_TEMPFAIL) headroom refusal or h7 runs not yet terminal: the queue retries later.
A fetch at or after T_seal 2026-10-22T00:00Z starts no chunk (status not_run_deadline for an incomplete run).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

REFUSED, TEMPFAIL, DISK_BUDGET = 2, 75, 4  # 4: output cap full, a declared end state (never retried)


def _emit(obj: dict) -> None:
    print(json.dumps(obj, default=str, sort_keys=True))


def _csv(v) -> list[str]:
    return [x.strip() for x in str(v or "").split(",") if x.strip()]


def _data_path(p: str, data_dumps: Path) -> Path:
    q = Path(p)
    if q.is_absolute() or q.exists():
        return q
    return data_dumps / q


def _declared_mismatches(a, t) -> list[str]:
    bad = []
    top = a.run_id == t.RUN_ID_B  # amendment A-T1: the top-up run declares 9 windows per day and its parent
    wpd = t.TOPUP_WINDOWS_PER_DAY if top else t.WINDOWS_PER_DAY
    if (getattr(a, "topup_of", "") or "") != (t.RUN_ID if top else ""):
        bad.append(f"topup_of={getattr(a, 'topup_of', '')!r} (declared {t.RUN_ID if top else ''!r})")
    checks = {
        "seed": (a.seed, t.SEED), "n_markets": (a.n_markets, t.N_MARKETS), "created_from": (a.created_from, t.CREATED_FROM),
        "created_to": (a.created_to, t.CREATED_TO), "end_before_fetch_days": (a.end_before_fetch_days, t.END_BEFORE_FETCH_DAYS),
        "windows_per_day": (a.windows_per_day, wpd), "max_origins": (a.max_origins, t.MAX_ORIGINS),
        "price_fidelity": (a.price_fidelity, t.PRICE_FIDELITY), "print_pages": (a.print_pages, t.PRINT_PAGES),
        "max_unverified_key_share": (a.max_unverified_key_share, t.MAX_UNVERIFIED_KEY_SHARE),
    }
    for k, (got, want) in checks.items():
        if got != want:
            bad.append(f"{k}={got!r} (declared {want!r})")
    if t.c4._ep(a.cap_at) != t.T_SEAL_EPOCH:
        bad.append(f"cap_at={a.cap_at!r}")
    if set(_csv(a.exclude_categories)) != {"weather"}:
        bad.append("exclude_categories")
    if set(_csv(a.exclude_runs)) != {"h1_first", "h2_main", "h3_power"}:
        bad.append("exclude_runs")
    if set(_csv(a.exclude_event_keys)) != set(t.KEY_TYPES):
        bad.append("exclude_event_keys")
    return bad


def _seal_paths(a, seals_dir: Path) -> dict[str, Path]:
    out = {}
    for p in _csv(a.exclude_seal_ids):
        out[Path(p).name] = Path(p)
    return out


def _limiter(t, rps: float, standalone: bool):
    from astrolabe.research_lab import history_backfill as hb

    return hb.Limiter(hb.httpx_transport(), rps=min(rps, 4.0), live_check=None if standalone else hb.live_pass_or_lock)


def cmd_rules(a) -> int:
    from astrolabe.research_lab import cb6_tail as t

    try:
        path = t.write_rules(Path(a.path) if a.path else t.RULES_FILE)
    except t.Refused as exc:
        _emit({"refused": str(exc)})
        return REFUSED
    doc = t.rules_file_doc()
    _emit({"written": str(path), "rules_sha256": doc["rules_sha256"], "funcs_sha256": doc["funcs_sha256"]})
    return 0


def cmd_fetch(a) -> int:
    from astrolabe.research_lab import cb6_tail as t
    from astrolabe.research_lab import history_backfill as hb

    root = Path(a.root) if a.root else t.HIST_ROOT
    data_dumps = Path(a.data_dumps) if a.data_dumps else t.c4.DATA_DUMPS
    standalone = bool(a.standalone)
    try:
        bad = _declared_mismatches(a, t)
        if bad:
            raise t.Refused(f"arguments differ from the declaration: {bad}")
        seals_dir = Path(a.seals_dir) if a.seals_dir else t.SEALS_DIR
        kw = dict(
            history_root=Path(a.history_root) if a.history_root else root, seals_dir=seals_dir,
            seal_paths=_seal_paths(a, seals_dir), rules_path=Path(a.rules) if a.rules else t.RULES_FILE,
            smoke_path=_data_path(a.require_smoke, data_dumps), cap_at=a.cap_at, rps=min(a.rps, 4.0),
            disk_cap=int(a.disk_cap_gb * 1024**3), budget_min=a.budget_min, data_dumps=data_dumps,
            data_dumps_cap_gb=a.data_dumps_cap_gb, stage=a.stage, topup_of=(a.topup_of or None),
            seed=a.seed, n_markets=a.n_markets, windows_per_day=a.windows_per_day,
            live_check=None if standalone else hb.live_pass_or_lock,
            snapshot_root=None if standalone else Path(a.snapshot_root or t.c4.SNAPSHOT_ROOT))
        m = t.tail_fetch(root, a.run_id, hb.httpx_transport(), **kw)
    except t.Refused as exc:
        _emit({"refused": str(exc)})
        return REFUSED
    except t.NotNow as exc:
        _emit({"tempfail": str(exc)})
        return TEMPFAIL
    except Exception as exc:
        _emit({"error": f"{type(exc).__name__}: {exc}"[:300]})
        return 1
    if m.get("status") == t.DISK_BUDGET_TOKEN:
        _emit({"status": t.DISK_BUDGET_TOKEN, "stopped": m.get("stopped"), "counts": m.get("counts")})
        return DISK_BUDGET
    _emit({"status": m.get("status") or ("in_progress" if m.get("stopped") else None), "stopped": m.get("stopped"),
           "complete": m.get("complete"), "counts": m.get("counts"), "transient": m.get("transient"),
           "requests": m.get("requests")})
    return 0


def cmd_smoke(a) -> int:
    from astrolabe.research_lab import cb6_tail as t

    root = Path(a.root) if a.root else t.HIST_ROOT
    data_dumps = Path(a.data_dumps) if a.data_dumps else t.c4.DATA_DUMPS
    out = _data_path(a.out, data_dumps) if a.out else t.SMOKE_DEFAULT
    if out.exists():  # write-once: a FAIL can never be replaced by a later PASS
        _emit({"refused": f"smoke result {out} already exists; it is write-once"})
        return REFUSED
    if out.name == t.SMOKE_V1_PATH.name:  # the v1 (q0135, FAIL) result name is never reused, on any machine
        _emit({"refused": f"{out.name} is the smoke v1 result name; smoke v2 writes a new path"})
        return REFUSED
    try:
        seals_dir = Path(a.seals_dir) if a.seals_dir else t.SEALS_DIR
        rules_sha = t.verify_rules(Path(a.rules) if a.rules else t.RULES_FILE, require_committed=not a.allow_uncommitted_rules)
        files = t.verify_exclusion_files(t.EXCLUSION_PINS, history_root=Path(a.history_root) if a.history_root else root,
                                         seals_dir=seals_dir, seal_paths=_seal_paths(a, seals_dir))
        res = t.run_smoke(_limiter(t, a.rps, a.standalone), files, t.EXCLUSION_PINS, rules_sha)
    except t.Refused as exc:
        _emit({"refused": str(exc)})
        return REFUSED
    except Exception as exc:
        _emit({"error": f"{type(exc).__name__}: {exc}"[:300]})
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        with out.open("x") as fh:  # exclusive create: also closes the race between the check above and the write
            fh.write(json.dumps(res, indent=1, sort_keys=True))
    except FileExistsError:
        _emit({"refused": f"smoke result {out} already exists; it is write-once"})
        return REFUSED
    _emit({"smoke": res["pass"], **{k: res[k] for k in ("n_requested", "n_pass", "n_failed_requests")}, "written": str(out)})
    return 0


def cmd_seal(a) -> int:
    from astrolabe.research_lab import cb6_tail as t
    from astrolabe.research_lab import history_backfill as hb

    root = Path(a.root) if a.root else t.HIST_ROOT
    try:
        t.refuse_path(root)
        res = t.seal_tail(root, a.run_id, transport=hb.httpx_transport(), seals_dir=Path(a.seals_dir) if a.seals_dir else None,
                          h7_seals_dir=Path(a.h7_seals) if a.h7_seals else None,
                          trials_path=Path(a.trials_path) if a.trials_path else None, rps=min(a.rps, 2.0),
                          recheck_keys=a.recheck_keys, live_check=None if a.standalone else hb.live_pass_or_lock,
                          topup_run_id=(a.topup_run if a.topup_run not in ("", "none") else None))
    except t.NotNow as exc:
        _emit({"tempfail": str(exc)})
        return TEMPFAIL
    except (t.Refused, t.SealError, FileNotFoundError) as exc:
        _emit({"refused": str(exc)})
        return REFUSED
    except Exception as exc:
        _emit({"error": f"{type(exc).__name__}: {exc}"[:300]})
        return 1
    _emit(res)
    return 0


def cmd_verify(a) -> int:
    from astrolabe.research_lab import cb6_tail as t

    try:
        seal = t.verify_tail(Path(a.root) if a.root else t.HIST_ROOT, a.run_id, Path(a.seals_dir) if a.seals_dir else None)
    except (t.SealError, FileNotFoundError, t.Refused) as exc:
        _emit({"run_id": a.run_id, "error": str(exc)})
        return 1
    _emit({"run_id": a.run_id, "verified": True, "listing_sha256": seal["listing_sha256"],
           "read_location": seal.get("read_location"), "split_counts": (seal.get("split") or {}).get("counts"),
           "topup": {k: v for k, v in (seal.get("topup") or {}).items() if k != "files"}})
    return 0


def build_parser() -> argparse.ArgumentParser:
    from astrolabe.research_lab import cb6_tail as t

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(q: argparse.ArgumentParser) -> None:
        q.add_argument("--run-id", default=t.RUN_ID)
        q.add_argument("--root", default=None, help="history root (default data-dumps/research_lab/history)")
        q.add_argument("--history-root", default=None, help="where h1_first/h2_main/h3_power sample.csv.gz live (default --root)")
        q.add_argument("--seals-dir", default=None)
        q.add_argument("--rules", default=None)
        q.add_argument("--exclude-seal-ids", default="")
        q.add_argument("--data-dumps", default=None)
        q.add_argument("--rps", type=float, default=4.0)
        q.add_argument("--standalone", action="store_true",
                       help="Mac fallback: own limiter, no collector yield or health check (use --rps 3)")

    p = sub.add_parser("rules", help="write seals/cb6_tail_rules.json")
    p.add_argument("--path", default=None)

    def fetch_args(q: argparse.ArgumentParser) -> None:
        common(q)
        q.add_argument("--seed", default=t.SEED)
        q.add_argument("--n-markets", type=int, default=t.N_MARKETS)
        q.add_argument("--created-from", default=t.CREATED_FROM)
        q.add_argument("--created-to", default=t.CREATED_TO)
        q.add_argument("--end-before-fetch-days", type=int, default=t.END_BEFORE_FETCH_DAYS)
        q.add_argument("--windows-per-day", type=int, default=t.WINDOWS_PER_DAY)
        q.add_argument("--max-origins", type=int, default=t.MAX_ORIGINS)
        q.add_argument("--price-fidelity", type=int, default=t.PRICE_FIDELITY)
        q.add_argument("--print-pages", type=int, default=t.PRINT_PAGES)
        q.add_argument("--exclude-runs", default="h1_first,h2_main,h3_power")
        q.add_argument("--exclude-event-keys", default=",".join(t.KEY_TYPES))
        q.add_argument("--max-unverified-key-share", type=float, default=t.MAX_UNVERIFIED_KEY_SHARE)
        q.add_argument("--exclude-categories", default="weather")
        q.add_argument("--require-smoke", default=str(t.SMOKE_DEFAULT))
        q.add_argument("--cap-at", default=t.T_SEAL)
        q.add_argument("--disk-cap-gb", type=float, default=t.OUTPUT_CAP_GB)
        q.add_argument("--budget-min", type=float, default=None)
        q.add_argument("--data-dumps-cap-gb", type=float, default=t.DATA_DUMPS_FETCH_CAP_GB)
        q.add_argument("--snapshot-root", default=None)
        q.add_argument("--topup-of", default="", help="amendment A-T1: parent run of the h8_tail_b top-up (h8_tail)")

    for name in ("tail-fetch", "fetch"):
        p = sub.add_parser(name, help="one resumable chunk of the h8_tail fetch (q0120)")
        fetch_args(p)
        p.add_argument("--stage", choices=["all", "keys"], default="all")
    p = sub.add_parser("exclusion-keys", help="stop after the exclusion keys")
    fetch_args(p)
    p.set_defaults(stage="keys")

    p = sub.add_parser("tail-smoke", help="20-market fidelity-60 smoke test (counts only)")
    common(p)
    p.add_argument("--out", default=None)
    p.add_argument("--allow-uncommitted-rules", action="store_true", help="smoke runs before the rules file is committed")
    for name in ("tail-seal", "seal"):
        p = sub.add_parser(name, help="seal h8_tail (q0121)")
        common(p)
        p.add_argument("--split-seed", default=t.SPLIT_SEED)
        p.add_argument("--h7-seals", default=None)
        p.add_argument("--recheck-keys", action="store_true")
        p.add_argument("--topup-run", default="", help="amendment A-T1: seal h8_tail together with this top-up run (h8_tail_b)")
        p.add_argument("--trials-path", default=None)
    p = sub.add_parser("verify-seal", help="verify the seal and its committed copy")
    common(p)
    return ap


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    if a.cmd == "rules":
        return cmd_rules(a)
    if a.cmd in ("tail-fetch", "fetch", "exclusion-keys"):
        if a.cmd == "exclusion-keys":
            a.stage = "keys"
        return cmd_fetch(a)
    if a.cmd == "tail-smoke":
        return cmd_smoke(a)
    if a.cmd in ("tail-seal", "seal"):
        from astrolabe.research_lab import cb6_tail as t

        if a.split_seed != t.SPLIT_SEED:
            _emit({"refused": f"split seed must be {t.SPLIT_SEED!r}"})
            return REFUSED
        return cmd_seal(a)
    if a.cmd == "verify-seal":
        return cmd_verify(a)
    return REFUSED


if __name__ == "__main__":
    raise SystemExit(main())
