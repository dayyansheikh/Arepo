# ruff: noqa: E501
"""CB7 runner, fetch side (docs/research_lab/CREATIVE_BATCH_7.md CB7-F and 5.2). Run from cwd=backend (queue worker).
EXPLORATORY: no edge, calibration or profitability claim. Fetch side only: no analysis or screen code.

    python scripts/run_cb7.py rules                  # write docs/research_lab/seals/cb7_text_geo_rules_v2.json (commit it before q0140b-q0143)
    python scripts/run_cb7.py smoke ...              # q0140b (smoke v2; v1 q0140 FAILed): slug -> pinned tag id; Data API print bounds/order/coverage; counts only, WRITE-ONCE
    python scripts/run_cb7.py exclusion-keys ...     # q0141: event / neg-risk / series keys of the h1/h2/h3/h5/h5_ladders ids
    python scripts/run_cb7.py text-fetch ...         # q0142: one resumable chunk of the h8_text fetch (T_seal-bound)
    python scripts/run_cb7.py geo-fetch ...          # q0143: one resumable chunk of the h8_geo fetch (T_seal-bound)
    python scripts/run_cb7.py text-seal | geo-seal   # q0144 / q0145: re-hash fetched files, record drops, seal
    python scripts/run_cb7.py verify-seal --run-id h8_text|h8_geo

Exit codes: 0 ok / transient pause / terminal state (text_fetch_complete, geo_fetch_complete, not_run_deadline,
disjointness_unverified, source_unverified, exclusion_keys_complete); 1 error; 2 refusal of a guard (rules hash, any exclusion
file missing or mismatching its pin, smoke not met, run id, refused root, declared arguments changed, smoke result exists);
4 disk budget exhausted (a declared end state, never retried); 75 (EX_TEMPFAIL) data-dumps headroom refusal or seal sources not
yet terminal: the queue retries later. A fetch at or after T_seal 2026-10-22T00:00Z starts no chunk (status not_run_deadline).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

REFUSED, TEMPFAIL, DISK_BUDGET = 2, 75, 4


def _emit(obj: dict) -> None:
    print(json.dumps(obj, default=str, sort_keys=True))


def _csv(v) -> list[str]:
    return [x.strip() for x in str(v or "").split(",") if x.strip()]


def _data_path(p: str, data_dumps: Path) -> Path:
    q = Path(p)
    if q.is_absolute() or q.exists():
        return q
    return data_dumps / q


def _seal_paths(a) -> dict[str, Path]:
    return {Path(p).name: Path(p) for p in _csv(getattr(a, "exclude_seal_ids", ""))}


def _bad(checks: dict) -> list[str]:
    return [f"{k}={got!r} (declared {want!r})" for k, (got, want) in checks.items() if got != want]


def _declared_common(a, cm) -> list[str]:
    bad = _bad({"end_before_fetch_days": (a.end_before_fetch_days, cm.END_BEFORE_FETCH_DAYS),
                "print_limit": (a.print_limit, cm.PRINT_LIMIT)})
    if cm.c4._ep(a.cap_at) != cm.T_SEAL_EPOCH:
        bad.append(f"cap_at={a.cap_at!r}")
    return bad


def _declared_text(a, cm) -> list[str]:
    bad = _declared_common(a, cm) + _bad({
        "seed": (a.seed, cm.TEXT_SEED), "n_markets": (a.n_markets, cm.N_TEXT_MARKETS), "end_from": (a.end_from, cm.TEXT_END_FROM),
        "windows_per_day": (a.windows_per_day, cm.WINDOWS_PER_DAY), "window_minutes": (a.window_minutes, cm.WINDOW_MINUTES),
        "min_life_days": (a.min_life_days, cm.TEXT_MIN_LIFE_DAYS), "sports_weight": (a.sports_weight, cm.SPORTS_WEIGHT),
        "origin_days_before_end": (a.origin_days_before_end, cm.TEXT_ORIGIN_DAYS)})
    if set(_csv(a.exclude_categories)) != {"weather", "geopolitics", "crypto_updown"}:
        bad.append("exclude_categories")
    return bad


def _declared_geo(a, cm) -> list[str]:
    bad = _declared_common(a, cm) + _bad({
        "seed": (a.seed, cm.GEO_SEED), "tag_slug": (a.tag_slug, cm.GEO_TAG_SLUG), "tag_id": (a.tag_id, cm.GEO_TAG_ID),
        "end_from": (a.end_from, cm.GEO_END_FROM), "min_life_days": (a.min_life_days, cm.GEO_MIN_LIFE_DAYS),
        "max_per_event": (a.max_per_event, cm.MAX_PER_EVENT), "cap_after_filters": (a.cap_after_filters, True),
        "origins_days_before_end": (a.origins_days_before_end, ",".join(str(x) for x in cm.GEO_ORIGIN_DAYS)),
        "band": (a.band, f"{cm.GEO_BAND[0]:.2f},{cm.GEO_BAND[1]:.2f}"),
        "max_failed_origin_share": (a.max_failed_origin_share, cm.MAX_FAILED_ORIGIN_SHARE)})
    return bad


def _paths(a, cm):
    data_dumps = Path(a.data_dumps) if a.data_dumps else cm.c4.DATA_DUMPS
    root = Path(a.root) if a.root else cm.HIST_ROOT
    return data_dumps, root


def cmd_rules(a) -> int:
    from astrolabe.research_lab import cb7_common as cm

    try:
        path = cm.write_rules(Path(a.path) if a.path else cm.RULES_FILE)
    except cm.Refused as exc:
        _emit({"refused": str(exc)})
        return REFUSED
    doc = cm.rules_file_doc()
    _emit({"written": str(path), "rules_sha256": doc["rules_sha256"], "funcs_sha256": doc["funcs_sha256"]})
    return 0


def cmd_smoke(a) -> int:
    from astrolabe.research_lab import cb7_common as cm
    from astrolabe.research_lab import history_backfill as hb

    data_dumps, root = _paths(a, cm)
    out = _data_path(a.out, data_dumps) if a.out else cm.SMOKE_DEFAULT
    if out.resolve() == cm.SMOKE_V1_PATH.resolve():  # the v1 FAIL is never overwritten
        _emit({"refused": "smoke v2 never writes the v1 result file (smoke.json)"})
        return REFUSED
    if out.exists():  # write-once: a FAIL can never be replaced by a later PASS
        _emit({"refused": f"smoke result {out} already exists; it is write-once"})
        return REFUSED
    declared = _bad({"seed": (a.seed, cm.SMOKE_SEED_V2), "n": (a.n, cm.SMOKE_N),
                     "min_volume": (a.min_volume, cm.SMOKE_MIN_VOLUME), "min_nonempty": (a.min_nonempty, cm.SMOKE_MIN_NONEMPTY),
                     "min_coverage": (a.min_coverage, cm.SMOKE_MIN_COVERAGE)})
    if declared:
        _emit({"refused": f"arguments differ from the declaration: {declared}"})
        return REFUSED
    try:
        seals_dir = Path(a.seals_dir) if a.seals_dir else cm.SEALS_DIR
        rules_sha = cm.verify_rules(Path(a.rules) if a.rules else cm.RULES_FILE, require_committed=not a.allow_uncommitted_rules)
        files = cm.c6.verify_exclusion_files(cm.EXCLUSION_PINS, history_root=Path(a.history_root) if a.history_root else root,
                                             seals_dir=seals_dir, seal_paths=_seal_paths(a))
        lim = hb.Limiter(hb.httpx_transport(), rps=min(a.rps, 4.0), live_check=None if a.standalone else hb.live_pass_or_lock)
        res = cm.run_smoke(lim, files, cm.EXCLUSION_PINS, rules_sha)
    except cm.Refused as exc:
        _emit({"refused": str(exc)})
        return REFUSED
    except cm.NotNow as exc:  # a network failure is never a permanent FAIL: nothing is written
        _emit({"tempfail": str(exc)})
        return TEMPFAIL
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
    _emit({"smoke": res["pass"], "a": res["criterion_a_slug_resolves_to_pinned_id"], "b": res["criterion_b_bounds_and_order"],
           "c": res["criterion_c_coverage"], **{k: res[k] for k in ("n_requested", "n_nonempty", "n_covered", "n_failed_requests")},
           "written": str(out)})
    return 0


def cmd_keys(a) -> int:
    from astrolabe.research_lab import cb7_common as cm
    from astrolabe.research_lab import history_backfill as hb

    data_dumps, root = _paths(a, cm)
    declared = _bad({"max_unverified_key_share": (a.max_unverified_key_share, cm.MAX_UNVERIFIED_KEY_SHARE)})
    if set(_csv(a.exclude_runs)) != {"h1_first", "h2_main", "h3_power"}:
        declared.append("exclude_runs")
    if set(_csv(a.key_types)) != set(cm.KEY_TYPES):
        declared.append("key_types")
    if declared:
        _emit({"refused": f"arguments differ from the declaration: {declared}"})
        return REFUSED
    standalone = bool(a.standalone)
    try:
        res = cm.exclusion_keys(
            data_dumps / "research_lab", hb.httpx_transport(), history_root=Path(a.history_root) if a.history_root else root,
            seals_dir=Path(a.seals_dir) if a.seals_dir else None, seal_paths=_seal_paths(a),
            rules_path=Path(a.rules) if a.rules else cm.RULES_FILE, require_committed=not a.allow_uncommitted_rules,
            rps=min(a.rps, 4.0), disk_cap=int(a.disk_cap_gb * 1024**3), data_dumps=data_dumps,
            data_dumps_cap_gb=a.data_dumps_cap_gb, live_check=None if standalone else hb.live_pass_or_lock,
            snapshot_root=None if standalone else Path(a.snapshot_root or cm.c4.SNAPSHOT_ROOT))
    except cm.Refused as exc:
        _emit({"refused": str(exc)})
        return REFUSED
    except cm.NotNow as exc:
        _emit({"tempfail": str(exc)})
        return TEMPFAIL
    except Exception as exc:
        _emit({"error": f"{type(exc).__name__}: {exc}"[:300]})
        return 1
    if res.get("status") == cm.DISK_BUDGET_TOKEN:
        _emit({"status": cm.DISK_BUDGET_TOKEN, "stopped": res.get("stopped")})
        return DISK_BUDGET
    rep = res.get("exclusion_report") or {}
    _emit({"status": res.get("status"), "stopped": res.get("stopped"), "complete": res.get("complete"),
           "n_ids": rep.get("n_ids"), "n_missing": rep.get("n_missing"), "missing_share": rep.get("missing_share"),
           "keys": rep.get("keys"), "transient": res.get("transient")})
    return 0


def _fetch(a, which: str) -> int:
    from astrolabe.research_lab import cb7_common as cm
    from astrolabe.research_lab import cb7_geo, cb7_text
    from astrolabe.research_lab import history_backfill as hb

    data_dumps, root = _paths(a, cm)
    standalone = bool(a.standalone)
    try:
        bad = _declared_text(a, cm) if which == "text" else _declared_geo(a, cm)
        if bad:
            raise cm.Refused(f"arguments differ from the declaration: {bad}")
        kw = dict(
            history_root=Path(a.history_root) if a.history_root else root, seals_dir=Path(a.seals_dir) if a.seals_dir else None,
            seal_paths=_seal_paths(a), rules_path=Path(a.rules) if a.rules else cm.RULES_FILE,
            smoke_path=_data_path(a.require_smoke, data_dumps), exclusion_keys_path=_data_path(a.exclusion_keys, data_dumps),
            cap_at=a.cap_at, rps=min(a.rps, 4.0), disk_cap=int(a.disk_cap_gb * 1024**3), budget_min=a.budget_min,
            data_dumps=data_dumps, data_dumps_cap_gb=a.data_dumps_cap_gb, require_committed=not a.allow_uncommitted_rules,
            live_check=None if standalone else hb.live_pass_or_lock,
            snapshot_root=None if standalone else Path(a.snapshot_root or cm.c4.SNAPSHOT_ROOT))
        if which == "text":
            m = cb7_text.text_fetch(root, a.run_id, hb.httpx_transport(), seed=a.seed, n_markets=a.n_markets, end_from=a.end_from,
                                    end_before_fetch_days=a.end_before_fetch_days, windows_per_day=a.windows_per_day,
                                    window_minutes=a.window_minutes, **kw)
        else:
            m = cb7_geo.geo_fetch(root, a.run_id, hb.httpx_transport(), seed=a.seed, tag_id=a.tag_id, end_from=a.end_from,
                                  end_before_fetch_days=a.end_before_fetch_days,
                                  max_failed_origin_share=a.max_failed_origin_share, **kw)
    except cm.Refused as exc:
        _emit({"refused": str(exc)})
        return REFUSED
    except cm.NotNow as exc:
        _emit({"tempfail": str(exc)})
        return TEMPFAIL
    except Exception as exc:
        _emit({"error": f"{type(exc).__name__}: {exc}"[:300]})
        return 1
    if m.get("status") == cm.DISK_BUDGET_TOKEN:
        _emit({"status": cm.DISK_BUDGET_TOKEN, "stopped": m.get("stopped"), "counts": m.get("counts")})
        return DISK_BUDGET
    _emit({"status": m.get("status") or ("in_progress" if m.get("stopped") else None), "stopped": m.get("stopped"),
           "complete": m.get("complete"), "counts": m.get("counts"), "transient": m.get("transient"),
           "requests": m.get("requests")})
    return 0


def cmd_text_fetch(a) -> int:
    return _fetch(a, "text")


def cmd_geo_fetch(a) -> int:
    return _fetch(a, "geo")


def cmd_seal(a, run_id: str) -> int:
    from astrolabe.research_lab import cb7_common as cm
    from astrolabe.research_lab import cb7_seal
    from astrolabe.research_lab import history_backfill as hb

    root = Path(a.root) if a.root else cm.HIST_ROOT
    try:
        res = cb7_seal.seal_cb7(root, run_id, transport=hb.httpx_transport(),
                                seals_dir=Path(a.drop_seals or a.seals_dir) if (a.drop_seals or a.seals_dir) else None,
                                trials_path=Path(a.trials_path) if a.trials_path else None, rps=min(a.rps, 2.0),
                                live_check=None if a.standalone else hb.live_pass_or_lock)
    except cm.NotNow as exc:
        _emit({"tempfail": str(exc)})
        return TEMPFAIL
    except (cm.Refused, cm.SealError, FileNotFoundError) as exc:
        _emit({"refused": str(exc)})
        return REFUSED
    except Exception as exc:
        _emit({"error": f"{type(exc).__name__}: {exc}"[:300]})
        return 1
    _emit(res)
    return 0


def cmd_verify(a) -> int:
    from astrolabe.research_lab import cb7_common as cm
    from astrolabe.research_lab import cb7_seal

    try:
        seal = cb7_seal.verify_cb7(Path(a.root) if a.root else cm.HIST_ROOT, a.run_id, Path(a.seals_dir) if a.seals_dir else None)
    except (cm.SealError, FileNotFoundError, cm.Refused) as exc:
        _emit({"run_id": a.run_id, "error": str(exc)})
        return 1
    _emit({"run_id": a.run_id, "verified": True, "listing_sha256": seal["listing_sha256"], "read_location": seal.get("read_location"),
           "drop_counts": ((seal.get("drops") or {}).get("counts"))})
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(q: argparse.ArgumentParser, run_id: str | None) -> None:
        if run_id:
            q.add_argument("--run-id", default=run_id)
        q.add_argument("--root", default=None, help="history root (default data-dumps/research_lab/history)")
        q.add_argument("--history-root", default=None, help="where h1_first/h2_main/h3_power sample.csv.gz live (default --root)")
        q.add_argument("--seals-dir", default=None)
        q.add_argument("--rules", default=None)
        q.add_argument("--exclude-seal-ids", default="")
        q.add_argument("--data-dumps", default=None)
        q.add_argument("--rps", type=float, default=4.0)
        q.add_argument("--standalone", action="store_true", help="no collector yield / health check (tests, off-host)")
        q.add_argument("--snapshot-root", default=None)
        q.add_argument("--allow-uncommitted-rules", action="store_true")

    def fetch_args(q: argparse.ArgumentParser, run_id: str) -> None:
        common(q, run_id)
        q.add_argument("--seed", default=None)
        q.add_argument("--end-from", default=None)
        q.add_argument("--end-before-fetch-days", type=int, default=7)
        q.add_argument("--min-life-days", type=int, default=9)
        q.add_argument("--print-limit", type=int, default=50)
        q.add_argument("--exclusion-keys", default="research_lab/creative_batch7/exclusion_keys.csv.gz")
        q.add_argument("--require-smoke", default="research_lab/creative_batch7/smoke_v2.json")
        q.add_argument("--cap-at", default="2026-10-22T00:00Z")
        q.add_argument("--disk-cap-gb", type=float, required=True)
        q.add_argument("--data-dumps-cap-gb", type=float, default=12.5)
        q.add_argument("--budget-min", type=float, default=None)

    q = sub.add_parser("rules")
    q.add_argument("--path", default=None)
    q.set_defaults(fn=cmd_rules)

    q = sub.add_parser("smoke")
    common(q, None)
    q.add_argument("--seed", default="arepo-cb7-smoke-v2")
    q.add_argument("--n", type=int, default=20)
    q.add_argument("--min-volume", type=float, default=10000.0)
    q.add_argument("--min-nonempty", type=int, default=10)
    q.add_argument("--min-coverage", type=int, default=14)
    q.add_argument("--out", default=None)
    q.set_defaults(fn=cmd_smoke)

    q = sub.add_parser("exclusion-keys")
    common(q, None)
    q.add_argument("--exclude-runs", default="h1_first,h2_main,h3_power")
    q.add_argument("--key-types", default="event,neg_risk_market,series")
    q.add_argument("--max-unverified-key-share", type=float, default=0.02)
    q.add_argument("--disk-cap-gb", type=float, default=0.01)
    q.add_argument("--data-dumps-cap-gb", type=float, default=12.5)
    q.set_defaults(fn=cmd_keys)

    q = sub.add_parser("text-fetch")
    fetch_args(q, "h8_text")
    q.add_argument("--n-markets", type=int, default=18000)
    q.add_argument("--windows-per-day", type=int, default=5)
    q.add_argument("--window-minutes", type=int, default=15)
    q.add_argument("--sports-weight", type=float, default=0.25)
    q.add_argument("--origin-days-before-end", type=int, default=7)
    q.add_argument("--exclude-categories", default="weather,geopolitics,crypto_updown")
    q.set_defaults(fn=cmd_text_fetch, seed="arepo-h8-text", end_from="2025-04-01")

    q = sub.add_parser("geo-fetch")
    fetch_args(q, "h8_geo")
    q.add_argument("--tag-slug", default="geopolitics")
    q.add_argument("--tag-id", default="100265")
    q.add_argument("--max-per-event", type=int, default=8)
    q.add_argument("--cap-after-filters", action="store_true")
    q.add_argument("--origins-days-before-end", default="30,14,7")
    q.add_argument("--band", default="0.02,0.10")
    q.add_argument("--max-failed-origin-share", type=float, default=0.02)
    q.set_defaults(fn=cmd_geo_fetch, seed="arepo-h8-geo", end_from="2025-06-01")

    for name, rid in (("text-seal", "h8_text"), ("geo-seal", "h8_geo")):
        q = sub.add_parser(name)
        common(q, rid)
        q.add_argument("--drop-seals", default=None, help="directory with the committed h8_tail / h7 seal copies")
        q.add_argument("--drop-runs", default="h8_tail,h7_cb4_era,h7_cb4_series")
        q.add_argument("--drop-frame", default="h8_geo" if name == "text-seal" else None)
        q.add_argument("--trials-path", default=None)
        q.set_defaults(fn=(lambda a, r=rid: cmd_seal(a, r)))

    q = sub.add_parser("verify-seal")
    common(q, "h8_text")
    q.set_defaults(fn=cmd_verify)
    return ap


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
