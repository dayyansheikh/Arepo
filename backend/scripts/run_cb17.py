# ruff: noqa: E501
"""CB17 runner (docs/research_lab/CREATIVE_BATCH_17.md sections 4, 10.4). Run from cwd=backend (queue worker / cron). EXPLORATORY / METHODS DATA ONLY: no edge, calibration or profitability claim.
At this commit only part ``pre`` exists: the four counts-only pre-censuses on the WORN window [2026-10-12, 2026-10-16). Every one is a cpu-lane job with NO network. No outcome, mark, point
estimate, slope or net is computed or written (standard errors of declared pre-outcome proxies only; the result writer refuses a key that names one).

    python scripts/run_cb17.py rules                        # write docs/research_lab/seals/cb17_rules.json (part pre declared; common, A, B, C, E undeclared); commit before q0400
    python scripts/run_cb17.py pre-census --family A        # q0400: side-agreement branch (S or T), A's strata level, first-day counts, planning SEs
    python scripts/run_cb17.py pre-census --family B        # q0401: stamp semantics, age bins, shifted-beneath share, frozen cut points, B1 / B2 strata levels
    python scripts/run_cb17.py pre-census --family C        # q0402: traded event-intervals, trailing terciles, C's strata level
    python scripts/run_cb17.py cost-lag-map                 # q0403: executable round-trip cost at $1,000 / $5,000 and the monitor receipt lag

Exit codes: 0 ok; 1 error; 2 refusal (rules hash of part pre, refused root / holdout / out-of-window path, declared argument changed, result exists); 4 disk budget; 75 (EX_TEMPFAIL) a
collector pass is running, data-dumps / free-disk headroom: "pending", no trials line.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

REFUSED, TEMPFAIL, DISK_BUDGET = 2, 75, 4
DECLARED_DISK_CAP_GB = 0.01
FAMILIES = ("A", "B", "C")
RESULT_KEY = {"A": "A", "B": "B", "C": "C", "cost": "cost"}


def _emit(obj: dict) -> None:
    print(json.dumps(obj, default=str, sort_keys=True))


def _guarded(fn):
    def wrapper(a) -> int:
        from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

        try:
            code, payload = fn(a)
        except cm.Refused as exc:
            _emit({"refused": str(exc)})
            return REFUSED
        except cm.NotNow as exc:
            _emit({"tempfail": str(exc), "science": "pending (no trials line)"})
            return TEMPFAIL
        except (cm.SealError, FileNotFoundError) as exc:
            _emit({"refused": str(exc)})
            return REFUSED
        except Exception as exc:
            _emit({"error": f"{type(exc).__name__}: {exc}"[:300]})
            return 1
        _emit(payload)
        return code

    wrapper.__name__ = fn.__name__
    return wrapper


def _c17():
    from astrolabe.research_lab import cb17_common as c17  # noqa: PLC0415

    return c17


def _census():
    from astrolabe.research_lab import cb17_census as cen  # noqa: PLC0415

    return cen


# ---- paths and arguments ----------------------------------------------------------------------------------------------------------------------


def _root(a) -> Path:
    c17 = _c17()
    return c17.require_output_root(Path(a.root) if getattr(a, "root", None) else c17.CB17_DIR)


def _dir(a, attr: str, default: Path, allow: tuple[str, ...]) -> Path:
    c17 = _c17()
    p = Path(getattr(a, attr)) if getattr(a, attr, None) else default
    return c17.refuse_path(p, allow=allow)


def _declared(a) -> None:
    c17 = _c17()
    if abs(float(a.disk_cap_gb) - DECLARED_DISK_CAP_GB) > 1e-9:
        raise c17.Refused(f"arguments differ from the declaration: disk_cap_gb={a.disk_cap_gb!r} (declared {DECLARED_DISK_CAP_GB!r})")
    if float(a.data_dumps_cap_gb) > c17.DATA_DUMPS_CAP_GB + 1e-9:
        raise c17.Refused(f"arguments differ from the declaration: data_dumps_cap_gb={a.data_dumps_cap_gb!r} > {c17.DATA_DUMPS_CAP_GB!r}")


def _data_dumps(a) -> Path:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    return Path(a.data_dumps) if getattr(a, "data_dumps", None) else cm.DATA_DUMPS


def _committed(a) -> bool:
    return not getattr(a, "allow_uncommitted_rules", False)


def _rules(a) -> str:
    """Verify part ``pre`` (the only declared part). Returns its sha256."""
    c17 = _c17()
    if a.part != "pre":
        raise c17.Refused(f"part {a.part!r}: the CB17 pre-censuses bind on part 'pre' alone")
    return c17.verify_rules(Path(a.rules) if getattr(a, "rules", None) else None, require_committed=_committed(a), part="pre")


def _tp(a) -> Path | None:
    return Path(a.trials_path) if getattr(a, "trials_path", None) else None


def _gap(a) -> None:
    """Census jobs start outside :31-:55 of even hours and yield to the collector pass lock (``--standalone`` skips this: tests, off-host)."""
    if getattr(a, "standalone", False):
        return
    from astrolabe.research_lab import cb16_common as c16  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c16.collector_gap_ok(time.time(), hb.live_pass_or_lock)


def _out(a, default_name: str) -> Path:
    c17 = _c17()
    out = Path(a.out) if getattr(a, "out", None) else _root(a) / default_name
    c17.require_output_root(out)
    if out.exists():
        raise c17.Refused(f"{out} exists; a census is written once")
    return out


def _prepare(a, default_name: str) -> tuple[str, Path]:
    """Common start of every census: declared arguments, rules part pre, collector gap, output path, disk guard."""
    c17 = _c17()
    _declared(a)
    sha = _rules(a)
    _gap(a)
    out = _out(a, default_name)
    c17.require_disk(_data_dumps(a), a.data_dumps_cap_gb, int(a.disk_cap_gb * 1024**3))
    return sha, out


# ---- rules -------------------------------------------------------------------------------------------------------------------------------------


def cmd_rules(a) -> int:
    c17 = _c17()
    try:
        out = c17.write_rules(Path(a.path) if a.path else None)
        doc = c17.rules_file_doc()
    except c17.Refused as exc:
        _emit({"refused": str(exc)})
        return REFUSED
    _emit({"written": str(out), "rules_version": doc["rules_version"],
           "parts": {k: {"declared": v.get("part_declared") is not False, "rules_sha256": v.get("rules_sha256"), "reason": v.get("reason")} for k, v in doc["parts"].items()}})
    return 0


# ---- q0400-q0402 -------------------------------------------------------------------------------------------------------------------------------


def _summary(family: str, res: dict) -> dict:
    """The small, clean payload of the trials line (counts and decisions only)."""
    if family == "A":
        return {"p1_matches": res["p1_reproduction"]["matches"], "branch_recorded": res["branch_recorded"], "branch": res["branch"], "a_withdrawn_uncounted": res["a_withdrawn_uncounted"],
                "selected_level": res["strata"]["selected_level"], "selected_population": res["strata"]["selected_population"],
                "agreement_n": res["side_agreement"]["overall"].get("n"), "both_label_cells": res["both_label_cells"]["with_both"]}
    if family == "B":
        return {"selected_level_B1": (res["strata"]["B1"] or {}).get("selected_level"), "selected_level_B2": (res["strata"]["B2"] or {}).get("selected_level"),
                "units": res["cut_points"]["units"], "tokens_with_both_fresh_and_old": res["tokens_with_both_fresh_and_old"]}
    if family == "C":
        return {"selected_level": (res["strata"] or {}).get("selected_level"), "events_with_units_having_6_prior": res["events_with_units_having_6_prior"]}
    return {"sweeps_used": res["sweeps"]["used_first_of_pass"], "prints": res["receipt_lag_s"]["prints"]}


def _finish(a, family: str, label: str, sha: str, out: Path, res: dict) -> tuple[int, dict]:
    c17 = _c17()
    doc = {**res, "rules_sha256": {"pre": sha}}
    sup = getattr(a, "supersedes", None)
    if sup:
        sp = Path(sup)
        if not sp.exists() or sp.resolve() == out.resolve():
            raise c17.Refused(f"--supersedes {sup}: the earlier result must exist and differ from the new output path (it is kept, never overwritten)")
        doc["supersedes"] = {"path": str(sp), "sha256": c17.sha256_file(sp)}
    mismatch = family == "A" and not res["p1_reproduction"]["matches"]
    file_sha = c17.write_result_once(out, doc)
    status = f"{label}_p1_mismatch" if mismatch else f"{label}_complete"
    c17.log_descriptive(label, {"status": status, "result_sha256": file_sha, "path": str(out), **_summary(family, res)}, trials_path=_tp(a), role=c17.EVIDENCE_ROLE_HIST)
    # exit 2 on a P1 mismatch: failed (not done), investigated and never retried blindly; a rerun writes a NEW declared path with --supersedes (the earlier file is kept)
    return (REFUSED if mismatch else 0), {"status": status, "written": str(out), "sha256": file_sha, **_summary(family, res),
                                          **({"refused": "P1 mismatch: " + _pre_next_action()} if mismatch else {})}


def _pre_next_action() -> str:
    from astrolabe.research_lab import cb17_pre as pre  # noqa: PLC0415

    return pre.P1_NEXT_ACTION


@_guarded
def cmd_pre_census(a):
    c17, cen = _c17(), _census()
    sha, out = _prepare(a, cen.RESULT_NAMES[a.family])
    snaps = _dir(a, "snapshot_dir", c17.SNAPSHOT_DIR, ("snapshots",))
    if a.family == "A":
        trades = _dir(a, "trades_dir", c17.LIVE_TRADES_DIR, ("live_trades",))
        fills = Path(a.fills_dir) if getattr(a, "fills_dir", None) else c17.CB13_T_SCREEN_DIR
        res = cen.pre_census_A(fills, trades, snaps)
    elif a.family == "B":
        res = cen.pre_census_B(_dir(a, "sweep_dir", c17.SWEEP_DIR, ("book_sweeps",)), snaps)
    else:
        res = cen.pre_census_C(snaps)
    return _finish(a, a.family, f"pre_census_{a.family}", sha, out, res)


@_guarded
def cmd_cost_lag_map(a):
    c17, cen = _c17(), _census()
    sha, out = _prepare(a, cen.RESULT_NAMES["cost"])
    res = cen.cost_lag_map(_dir(a, "sweep_dir", c17.SWEEP_DIR, ("book_sweeps",)), _dir(a, "snapshot_dir", c17.SNAPSHOT_DIR, ("snapshots",)), _dir(a, "trades_dir", c17.LIVE_TRADES_DIR, ("live_trades",)))
    return _finish(a, "cost", "cost_lag_map", sha, out, res)


# ---- parser -------------------------------------------------------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    c17 = _c17()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(q: argparse.ArgumentParser) -> None:
        q.add_argument("--root", default=None, help="creative_batch17 root (default data-dumps/research_lab/creative_batch17)")
        q.add_argument("--out", default=None)
        q.add_argument("--snapshot-dir", default=None)
        q.add_argument("--sweep-dir", default=None)
        q.add_argument("--trades-dir", default=None)
        q.add_argument("--fills-dir", default=None, help="CB13-T SCREEN table directory (q0400 only; only creative_batch13/t_screen is accepted)")
        q.add_argument("--data-dumps", default=None, help="data-dumps root for the 40 GiB cap guard (default: the host's)")
        q.add_argument("--rules", default=None)
        q.add_argument("--part", default="pre")
        q.add_argument("--disk-cap-gb", type=float, default=DECLARED_DISK_CAP_GB)
        q.add_argument("--data-dumps-cap-gb", type=float, default=c17.DATA_DUMPS_CAP_GB)
        q.add_argument("--standalone", action="store_true", help="no collector yield (tests, off-host)")
        q.add_argument("--allow-uncommitted-rules", action="store_true", help="tests only")
        q.add_argument("--trials-path", default=None)
        q.add_argument("--supersedes", default=None, help="rerun after an investigated P1 mismatch: --out must be a NEW path; the earlier result file is kept and hashed into this one")

    q = sub.add_parser("rules")
    q.add_argument("--path", default=None)
    q.set_defaults(fn=cmd_rules)

    q = sub.add_parser("pre-census", help="q0400 (A), q0401 (B), q0402 (C)")
    common(q)
    q.add_argument("--family", required=True, choices=FAMILIES)
    q.set_defaults(fn=cmd_pre_census)

    q = sub.add_parser("cost-lag-map", help="q0403")
    common(q)
    q.set_defaults(fn=cmd_cost_lag_map)
    return ap


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
