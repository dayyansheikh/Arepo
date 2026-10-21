# ruff: noqa: E501
"""CB18 runner (docs/research_lab/CREATIVE_BATCH_18.md sections 3, 5, 6). Run from cwd=backend (queue worker). EXPLORATORY / METHODS DATA ONLY: no edge, calibration or profitability claim.

Part ``pre`` jobs (counts only, worn pre-window data named in seals/cb18_census_inputs.json; cpu lane, no network):

    python scripts/run_cb18.py rules                       # write docs/research_lab/seals/cb18_rules.json (part pre declared; common, S undeclared)
    python scripts/run_cb18.py seal-inputs --meta-dir DIR  # seals/cb18_census_inputs.json from the releases' MANIFEST.sha256 + files.sha256 (release metadata only; --download fetches them with gh)
    python scripts/run_cb18.py census-s    ...             # q0502 CB18-S (CH177): GS1-GS5, proxy SE (SE only), MDE_RS1 and MDE_RS2, route RS-0..RS-3
    python scripts/run_cb18.py census-p    ...             # q0503 CB18-P (CH172): GP1-GP6 (GP5 = max(formula, proxy)), route (LT5 member or dropped)
    python scripts/run_cb18.py map-race    ...             # q0504 CB18-R (CH179): the race map (descriptive; no gates, no route)
    python scripts/run_cb18.py census-f    ...             # q0505 CB18-F (CH176): rank churn at B in {10, 12, 20, 24, 50} (no price read)
    python scripts/run_cb18.py map-lastmid ...             # q0506 CB18-M (CH175): exits by folded last-mid band (no side, no comparison with earlier prices)
    python scripts/run_cb18.py routing --s S.json --p P.json --r R_map.json --f F.json --m M.json --out ../docs/research_lab/seals/cb18_routing.json   # orchestrator, after q0502-q0506

Window subcommands (smoke, keys, frame, census-window, screen, rep, stage2-final, size-check) belong to parts common / S and are not implemented here.

Exit codes: 0 ok; 1 error; 2 refusal (rules hash of part pre, refused root, unpinned or mismatched input, cut-off, result exists, declared argument exceeded); 75 (EX_TEMPFAIL) a
pinned input is missing ("restore byte for byte, hash-checked"), a collector pass is running, or the data-dumps / free-disk guard: "pending", no trials line.
"""

from __future__ import annotations

import argparse
import json
import resource
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

REFUSED, TEMPFAIL = 2, 75
FAMILY_OF = {"census-s": "S", "census-p": "P", "map-race": "R", "census-f": "F", "map-lastmid": "M"}


def _emit(obj: dict) -> None:
    print(json.dumps(obj, default=str, sort_keys=True))


def _mods():
    from astrolabe.research_lab import cb18_common as c  # noqa: PLC0415
    from astrolabe.research_lab import cb18_rules_pre as r  # noqa: PLC0415

    return r, c


def _peak_rss_mb() -> float:
    v = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return v / (1024.0 * 1024.0) if sys.platform == "darwin" else v / 1024.0


def _guarded(fn):
    def wrapper(a) -> int:
        r, _ = _mods()
        try:
            code, payload = fn(a)
        except r.NotNow as exc:
            _emit({"tempfail": str(exc), "science": "pending (no trials line)"})
            return TEMPFAIL
        except r.Refused as exc:
            _emit({"refused": str(exc)})
            return REFUSED
        except Exception as exc:  # noqa: BLE001
            _emit({"error": f"{type(exc).__name__}: {exc}"[:400]})
            return 1
        _emit(payload)
        return code

    wrapper.__name__ = fn.__name__
    return wrapper


def _data_dumps_of(out: Path) -> Path | None:
    for p in [out, *out.parents]:
        if p.name == "data-dumps":
            return p
    return None


def _prepare(a) -> tuple[str, Path]:
    """Declared arguments, rules part pre (committed), collector gap, write-once output path, disk guards (exit 75)."""
    r, _ = _mods()
    if a.part != "pre":
        raise r.Refused(f"part {a.part!r}: the CB18 pre-censuses bind on part 'pre' alone")
    if float(a.disk_cap_gb) > r.DISK_CAP_GB + 1e-9 or float(a.data_dumps_cap_gb) > r.DATA_DUMPS_CAP_GB + 1e-9:
        raise r.Refused(f"arguments exceed the declaration: disk_cap_gb={a.disk_cap_gb} (<= {r.DISK_CAP_GB}), data_dumps_cap_gb={a.data_dumps_cap_gb} (<= {r.DATA_DUMPS_CAP_GB})")
    sha = r.verify_rules(Path(a.rules), require_committed=not a.allow_uncommitted_rules, part="pre")
    if not a.standalone:
        from astrolabe.research_lab import cb16_common as c16  # noqa: PLC0415
        from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

        c16.collector_gap_ok(time.time(), hb.live_pass_or_lock)
    out = r.require_output_root(Path(a.out))
    if out.exists():
        raise r.Refused(f"{out} exists; a census is written once")
    from astrolabe.research_lab import cb16_common as c16  # noqa: PLC0415

    c16.require_disk(_data_dumps_of(out.resolve()), float(a.data_dumps_cap_gb), int(float(a.disk_cap_gb) * 1024**3), free_path=out.resolve().parent)
    return sha, out


def _tree(a):
    r, c = _mods()
    seal_path = Path(a.seal)
    seal = c.load_seal(seal_path)
    tree = c.PinnedTree(seal, snapshot_root=Path(a.snapshot_root) if a.snapshot_root else None, sweep_root=Path(a.sweep_root) if a.sweep_root else None,
                        sample_root=Path(a.sample_root) if a.sample_root else None)
    return tree, c.sha256_file(seal_path)


def _summary(fam: str, doc: dict) -> dict:
    """What each census prints (counts, shares, SEs, gates, route); the full document is in the write-once file."""
    if fam == "S":
        return {"gate_inputs": doc.get("gate_inputs"), "gates": doc.get("gates"), "mde": doc.get("mde"), "route": doc.get("route", {}).get("route"),
                "frame": doc.get("frame"), "proxy_se_c": {k: v.get("se_c") for k, v in (doc.get("proxy_se") or {}).items()}, "burst": doc.get("burst"), "lookback": doc.get("lookback"),
                "silent_per_event": doc.get("silent_per_event"), "design_effect": doc.get("design_effect"), "census_to_spec": doc.get("census_to_spec")}
    if fam == "P":
        return {"counts": doc.get("counts"), "gates_non_sports": doc.get("gates_non_sports"), "gates_all": doc.get("gates_all"), "route": doc.get("route"),
                "non_sports": {k: (doc.get("non_sports") or {}).get(k) for k in ("units", "covered", "truncated", "states", "fades_per_day", "mde_formula_c", "mde_proxy_c", "m")},
                "census_to_spec": doc.get("census_to_spec")}
    if fam == "R":
        return {k: doc.get(k) for k in ("units", "counts", "raced_row_share", "ts_not_minute_share", "gap_hist_s", "label_same_ts", "fingerprint_identical_share_of_pairs", "same_side_share_of_pairs", "R_distribution")}
    if fam == "F":
        return {"counts": doc.get("counts"), "breakpoints": {b: {k: v.get(k) for k in ("churn_share", "entries_per_day", "exits_per_day", "crossings", "crossing_surge_share")} for b, v in (doc.get("breakpoints") or {}).items()}}
    if fam == "M":
        return {k: doc.get(k) for k in ("captures", "effective_days", "exits", "undetermined", "still_listed_at_end", "reappearances_after_exit", "negrisk_events_all_members_exit_within_24h")} | {
            "per_day_by_band": (doc.get("all") or {}).get("per_day_by_band"), "gap_adjacent": (doc.get("all") or {}).get("gap_adjacent")}
    return {}


def _run_census(a, fam: str):
    r, c = _mods()
    sha, out = _prepare(a)
    tree, seal_sha = _tree(a)
    r.verify_pins()
    t0 = time.time()
    if fam == "S":
        from astrolabe.research_lab import cb18_pre as cp  # noqa: PLC0415

        doc = cp.census_s(tree)
    elif fam == "P":
        from astrolabe.research_lab import cb18_pre as cp  # noqa: PLC0415

        doc = cp.census_p(tree)
    elif fam == "F":
        from astrolabe.research_lab import cb18_pre as cp  # noqa: PLC0415

        doc = cp.census_f(tree)
    elif fam == "R":
        from astrolabe.research_lab import cb18_map as cm_  # noqa: PLC0415

        doc = cm_.map_race(tree)
    else:
        from astrolabe.research_lab import cb18_map as cm_  # noqa: PLC0415

        doc = cm_.map_lastmid(tree)
    head = {"evidence_role": r.EVIDENCE_ROLE_HIST, "kind": r.TRIAL_KIND, "n_tests": 0, "rules_version": r.RULES_VERSION, "rules_pre_sha256": sha, "census_inputs_seal_sha256": seal_sha,
            "code_sha256": c.code_sha256(), "pinned_imports_sha256": r.verify_pins(), "files_verified": len(tree.checked), "j4r_disclosure": r.J4R_DISCLOSURE,
            "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "seconds": round(time.time() - t0, 1), "peak_rss_mb": round(_peak_rss_mb(), 1)}
    doc = {**head, **doc}
    fsha = r.write_result_once(out, doc)
    summ = _summary(fam, doc)
    if not a.no_trials:
        c.log_descriptive(f"{fam}:pre_census", {"job": doc.get("job"), "file": out.name, "file_sha256": fsha, "rules_pre_sha256": sha}, trials_path=Path(a.trials_path) if a.trials_path else None)
    return 0, {"written": str(out), "sha256": fsha, "family": fam, "seconds": head["seconds"], "peak_rss_mb": head["peak_rss_mb"], "summary": summ}


@_guarded
def cmd_census(a):
    return _run_census(a, FAMILY_OF[a.cmd])


@_guarded
def cmd_rules(a):
    r, _ = _mods()
    out = r.write_rules(Path(a.path) if a.path else None)
    doc = r.rules_file_doc()
    return 0, {"written": str(out), "parts": {k: {"declared": v.get("part_declared") is not False, "rules_sha256": v.get("rules_sha256")} for k, v in doc["parts"].items()}}


@_guarded
def cmd_seal_inputs(a):
    r, c = _mods()
    meta = Path(a.meta_dir)
    drafts = Path(a.drafts_dir)
    if a.download:
        rest = c._restore_module()
        src = rest.GhSource(a.repo)
        for name in ("q0500_cb18_census_restore_captures.json", "q0501_cb18_census_restore_samples.json"):
            tags, _ = c.draft_selection(json.loads((drafts / name).read_text()))
            for tag in tags:
                src.meta(tag, str(meta / tag))
    doc = c.build_census_seal(meta, drafts, Path(a.c2_seal), Path(a.catalogue))
    out = Path(a.out)
    if out.exists():
        have = json.loads(out.read_text())
        if have != doc:
            raise r.Refused(f"{out} exists and differs; the census-input seal is never rewritten")
        return 0, {"unchanged": str(out), **c.check_completeness(doc)}
    out.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    return 0, {"written": str(out), **c.check_completeness(doc), "jobs": {k: {"files": v["files"], "per_tag": v["per_tag"]} for k, v in doc["jobs"].items()}}


@_guarded
def cmd_routing(a):
    r, c = _mods()
    from astrolabe.research_lab import cb18_pre as cp  # noqa: PLC0415

    sha = r.verify_rules(Path(a.rules), require_committed=not a.allow_uncommitted_rules, part="pre")
    out = Path(a.out)
    if out.name != "cb18_routing.json":
        raise r.Refused("the routing record is seals/cb18_routing.json")
    if out.exists():
        raise r.Refused(f"{out} exists; the routing record is written once")
    rec = cp.routing_record({"S": a.s and Path(a.s), "P": a.p and Path(a.p), "R": a.r and Path(a.r), "F": a.f and Path(a.f), "M": a.m and Path(a.m)}, sha)
    out.write_text(json.dumps(rec, indent=1, sort_keys=True, default=str) + "\n")
    return 0, {"written": str(out), "routes": rec["routes"]}


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    seals = ROOT / "docs" / "research_lab" / "seals"
    for name in FAMILY_OF:
        q = sub.add_parser(name)
        q.add_argument("--rules", default=str(seals / "cb18_rules.json"))
        q.add_argument("--part", default="pre")
        q.add_argument("--seal", default=str(seals / "cb18_census_inputs.json"))
        q.add_argument("--snapshot-root")
        q.add_argument("--sweep-root")
        q.add_argument("--sample-root")
        q.add_argument("--out", required=True)
        q.add_argument("--disk-cap-gb", type=float, required=True)
        q.add_argument("--data-dumps-cap-gb", type=float, required=True)
        q.add_argument("--trials-path")
        q.add_argument("--no-trials", action="store_true", help="test hook: no trials line")
        q.add_argument("--standalone", action="store_true", help="skip the collector-gap check (tests, off-host)")
        q.add_argument("--allow-uncommitted-rules", action="store_true", help="test hook: the rules file need not be committed")
        q.set_defaults(fn=cmd_census)
    q = sub.add_parser("rules")
    q.add_argument("--path")
    q.set_defaults(fn=cmd_rules)
    q = sub.add_parser("seal-inputs")
    q.add_argument("--meta-dir", required=True, help="directory holding <tag>/MANIFEST.sha256 and <tag>/files.sha256 for every tag of q0500 / q0501")
    q.add_argument("--download", action="store_true", help="fetch the two metadata files per tag with gh first (release metadata only)")
    q.add_argument("--repo", default="dayyansheikh/arepo-data")
    q.add_argument("--drafts-dir", default=str(ROOT / "docs" / "research_lab" / "queue" / "drafts"))
    q.add_argument("--c2-seal", default=str(seals / "lt3_census_inputs_C2.json"))
    q.add_argument("--catalogue", default=str(ROOT / "docs" / "research_lab" / "data_catalogue"))
    q.add_argument("--out", default=str(seals / "cb18_census_inputs.json"))
    q.set_defaults(fn=cmd_seal_inputs)
    q = sub.add_parser("routing")
    q.add_argument("--rules", default=str(seals / "cb18_rules.json"))
    for fam in ("s", "p", "r", "f", "m"):
        q.add_argument(f"--{fam}")
    q.add_argument("--out", default=str(seals / "cb18_routing.json"))
    q.add_argument("--allow-uncommitted-rules", action="store_true")
    q.set_defaults(fn=cmd_routing)
    return ap


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
