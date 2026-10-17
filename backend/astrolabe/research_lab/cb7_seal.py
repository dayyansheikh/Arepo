# ruff: noqa: E501
"""CB7 seals of ``h8_text`` (q0144) and ``h8_geo`` (q0145) (docs/research_lab/CREATIVE_BATCH_7.md section 1.3 "Drops at seal", CB7-F).

Only a complete fetch is sealed. The seal first RE-HASHES every fetched file against the fetch manifest (refuse on any
mismatch), waits for the drop sources to be terminal (exit 75 otherwise), and records drops (by id AND by event /
neg-risk / series key) as ``DROPPED_*`` blocks in ``drops.csv.gz`` -- fetched files are never edited. ``h8_text`` also drops
markets sharing an id or key with the FULL ``h8_geo`` frame as walked, before any filter or cap.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path

from . import cb6_tail as c6
from . import cb7_common as cm
from . import h5_seal
from . import history_backfill as hb

Refused, NotNow = cm.Refused, cm.NotNow
DROP_RUNS = ("h8_tail", "h7_cb4_era", "h7_cb4_series")
DROP_COLUMNS = ["market_id", "block", "reason"]


def verify_fetched_files(rdir: Path, manifest: dict) -> int:
    """Recompute the sha256 of every fetched file and compare with the manifest. Raises :class:`Refused` on any missing or
    changed file, or when the manifest has no hash table. Returns the number of files checked."""
    want = manifest.get("file_sha256")
    if not isinstance(want, dict) or not want:
        raise Refused(f"{rdir.name} manifest has no file_sha256; refusing to seal")
    for rel, sha in sorted(want.items()):
        fp = Path(rdir) / rel
        if not fp.is_file():
            raise Refused(f"fetched file missing at seal: {rel}")
        if h5_seal.sha256_file(fp) != sha:
            raise Refused(f"fetched file sha256 differs from the fetch manifest: {rel}")
    extra = sorted(set(h5_seal.list_files(Path(rdir))) - set(want) - {"manifest.json"})
    if extra:
        raise Refused(f"files not in the fetch manifest at seal: {extra[:5]}")
    return len(want)


def _add_keys(into: dict[str, set[str]], k: dict) -> None:
    into["event"].update(e for e in str(k.get("event_ids", "")).split(";") if e)
    if k.get("neg_risk_market_id"):
        into["neg_risk_market"].add(k["neg_risk_market_id"])
    into["series"].update(s for s in str(k.get("series_ids", "")).split(";") if s)


def geo_frame_state(root: Path) -> tuple[str, Path | None]:
    """``frame`` (the full walked tag frame exists), ``not_run`` (no geo frame will exist) or ``pending``."""
    gdir = Path(root) / cm.GEO_RUN_ID
    if (gdir / "frame_report.json").exists() and (gdir / "frame.csv.gz").exists():
        return "frame", gdir / "frame.csv.gz"
    if any((gdir / f).exists() for f in (cm.NOT_RUN_FILE, cm.UNVERIFIED_FILE)):
        return "not_run", None
    return "pending", None


def seal_cb7(root: Path, run_id: str, *, transport: hb.Transport | None = None, seals_dir: Path | None = None,
             trials_path: Path | None = None, rps: float = 2.0, sleep: Callable[[float], None] = time.sleep,
             live_check: Callable[[], bool] | None = None) -> dict:
    """q0144 / q0145. See the module docstring."""
    root, seals_dir = Path(root), Path(seals_dir or cm.SEALS_DIR)
    if run_id not in (cm.TEXT_RUN_ID, cm.GEO_RUN_ID):
        cm.refuse_run_id(run_id, cm.TEXT_RUN_ID)
    cm.refuse_path(root)
    is_text = run_id == cm.TEXT_RUN_ID
    rdir = root / run_id
    token = cm.TEXT_COMPLETE if is_text else cm.GEO_COMPLETE
    for fname, tok in ((cm.NOT_RUN_FILE, cm.NOT_RUN_TOKEN), (cm.UNVERIFIED_FILE, cm.UNVERIFIED_TOKEN),
                       (cm.SOURCE_UNVERIFIED_FILE, cm.SOURCE_UNVERIFIED_TOKEN)):
        if (rdir / fname).exists():
            raise Refused(f"{run_id} is {tok}; it is never sealed")
    mp = rdir / "manifest.json"
    man = json.loads(mp.read_text()) if mp.exists() else {}
    if not (man.get("complete") is True and not man.get("stopped") and man.get("status") == token):
        raise Refused(f"{run_id} is not {token}; refusing to seal")
    n_checked = verify_fetched_files(rdir, man)
    states = {h: c6.h7_state(h, seals_dir) for h in DROP_RUNS}
    pending = [h for h, (s, _) in states.items() if s == "pending"]
    geo_state, geo_frame = ("n/a", None)
    if is_text:
        geo_state, geo_frame = geo_frame_state(root)
        if geo_state == "pending":
            pending.append(cm.GEO_RUN_ID)
    if pending:
        raise NotNow(f"drop sources not terminal yet: {pending}")
    sample = list(cm.read_csv_gz(rdir / "sample.csv.gz"))
    ids: set[str] = set()
    for _, (s, p) in states.items():
        if s == "sealed" and p is not None:
            ids |= c6.h7_ids_from_copy(p)
    keys: dict[str, set[str]] = {"event": set(), "neg_risk_market": set(), "series": set()}
    missing_meta = 0
    if ids:
        if transport is None:
            raise Refused("drop seal copies exist but no transport was given for the key lookup")
        lim = hb.Limiter(transport, rps=min(rps, 2.0), sleep=sleep, live_check=live_check)
        found, _ = c6.lookup_keys(lim, sorted(ids))
        missing_meta = len(ids) - len(found)
        for k in found.values():
            _add_keys(keys, k)
    geo_ids: set[str] = set()
    geo_keys: dict[str, set[str]] = {"event": set(), "neg_risk_market": set(), "series": set()}
    if geo_frame is not None:
        for r in cm.read_csv_gz(geo_frame):
            geo_ids.add(r["market_id"])
            _add_keys(geo_keys, r)
    rows = []
    n = {"KEPT": 0, "DROPPED_SEALED_RUNS": 0, "DROPPED_GEO_FRAME": 0}
    for r in sample:
        why = (["id"] if r["market_id"] in ids else []) + cm.key_types_matched(r, keys)
        gwhy = (["id"] if r["market_id"] in geo_ids else []) + cm.key_types_matched(r, geo_keys)
        if why:
            n["DROPPED_SEALED_RUNS"] += 1
            rows.append([r["market_id"], "DROPPED_SEALED_RUNS", "+".join(why)])
        elif gwhy:
            n["DROPPED_GEO_FRAME"] += 1
            rows.append([r["market_id"], "DROPPED_GEO_FRAME", "+".join(gwhy)])
        else:
            n["KEPT"] += 1
    rows.sort()
    (rdir / "drops.csv.gz").write_bytes(hb._gz_csv_bytes(DROP_COLUMNS, rows))
    report = {"n_sample": len(sample), "counts": n, "sources": {h: s for h, (s, _) in states.items()}, "geo_frame": geo_state,
              "drop_ids_from_seal_copies": len(ids), "drop_ids_without_metadata": missing_meta, "geo_frame_ids": len(geo_ids),
              "fetched_files_rehashed": n_checked}
    (rdir / "drops_report.json").write_text(json.dumps(report, indent=1, sort_keys=True))
    decl = {"dataset_role": f"CB7 {run_id}: fresh fetch for the CB7 {'specificity (S)' if is_text else 'geopolitics longshot (G)'} screen; "
                            "exploratory_historical, not prospective, not an edge claim",
            "read_rules": "verify the listing hash first; append every read to ACCESS_LOG.jsonl; outcomes only from "
                          "outcomes_guarded.csv.gz and not before the CB7 freeze; DROPPED_* blocks of drops.csv.gz are never read",
            "information_end": "manifest request_clock_now (T_fetch) < T_seal of h4_seal"}
    extra = {"drops": report, "read_location": c6.read_location(root), "rules_sha256": man.get("rules_sha256"),
             "t_fetch": man.get("request_clock_now"), "exclusion_keys_sha256": man.get("exclusion_keys_sha256")}
    seal = h5_seal.seal_run(rdir, trials_path=trials_path, declaration_base=decl, extra=extra, source="creative_batch_7:cb7_f_seal")
    copy = h5_seal.write_committed_copy(rdir, seals_dir)
    return {"run_id": run_id, "sealed": True, "listing_sha256": seal["listing_sha256"], "committed_copy": str(copy),
            "drop_counts": n}


def verify_cb7(root: Path, run_id: str, seals_dir: Path | None = None) -> dict:
    return h5_seal.require_sealed(Path(root) / run_id, h5_seal.committed_seal_path(run_id, seals_dir))
