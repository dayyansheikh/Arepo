"""Multi-signal pipeline development runner (arms M0, M1, M2, M3_eb, placebo, sweep-gap, SHAP).

Design: ``docs/research_lab/MULTI_SIGNAL_PIPELINE_DESIGN.md`` sections 4, 6 and the pre-declared
sweep-gap diagnostic. Everything here is DEVELOPMENT/post-hoc: no edge, calibration or
profitability claim is ever made.

Usage::

    python backend/scripts/run_ml_dev.py --dry-run   # panel + folds only; fits and logs nothing
    python backend/scripts/run_ml_dev.py             # real run: refused below the 40-snapshot gate

Targets (design "Targets" amendment): ``--target direction|dmid|absmove`` and ``--horizon 1|3|12``.
The default (direction, 1 snapshot, ~2h) is the only confirmatory target. Every other combination
runs as a separate EXPLORATORY run with its own manifest, report and ``trials.jsonl`` lines
(target name and horizon recorded); it never enters the confirmation family.

Families (``--families``): ``market_state`` (the confirmatory MC1 set, always on) plus the
exploratory ``flow`` and ``wallet`` families joined from each snapshot's trade sample
(``ml_panel.add_flow_wallet_columns``, origin-side trades only, NaN + ``ml_flow_sampled`` outside
the ~2,000-market sample). They are NOT in MC1 (adding them is a feature-set revision), so any run
selecting them is stamped ``exploratory_family``, runs through the separate EXPLORATORY path with
its own manifest and report, and never enters the confirmation family. ``--dry-run`` reports
coverage per family.

Evidence role: every trial line written here carries ``evidence_role`` (``exploratory_dev``;
``placebo`` for the placebo arms). ``provenance.append_trial`` rejects ml_* lines without one.

Gate (design section 6): at least 40 *consecutive* complete snapshots with the sidecar present,
consecutive meaning every start-to-start gap lies in [1.5, 3.0] h (the ``ml_panel`` pairing rule).
Snapshots are only read, never modified. The panel is built period by period by
``ml_panel_cache.build_panel_to_parquet`` (two snapshots and one sweep in memory at once; every
period frame is spilled to ``ml_cache/periods/<period key>.parquet`` and reused by any later panel
that gives the period the same inputs) and written as parquet under
``data-dumps/research_lab/ml_cache/<panel hash>/``. It is the same panel ``ml_panel.build_panel``
returns (after the parquet round trip every cached run already used).
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import hashlib
import json
import math
import os
import resource
import sys
import time
import warnings
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

DUMPS = ROOT / "data-dumps" / "research_lab"
SNAPSHOT_ROOT = DUMPS / "snapshots"
SWEEP_ROOT = DUMPS / "book_sweeps"
SAMPLE_ROOT = DUMPS / "trade_samples"
CACHE_ROOT = DUMPS / "ml_cache"
OUT_DIR = ROOT / "docs" / "research_lab" / "ml_dev"

MIN_SNAPSHOTS = 40
# Test code only: lowers the gate. Any use is stamped gate_overridden=true everywhere.
TEST_GATE_ENV = "AREPO_ML_DEV_TEST_ONLY_MIN_SNAPSHOTS"
CADENCE_H = 2.0
HASHED_MODULES = ("ml_panel", "ml_panel_cache", "panel", "features", "features_dev", "evaluate")
# columns the dry run reads back (panel_summary + fold plan); feature NaN rates are streamed
DRY_COLUMNS = ("period", "capture_i", "target_available", "y_class", "dmid", "t_i", "t0", "t_j",
               "event_id", "market_id", "dep_group", "dep_group_season", "dep_group_econ",
               "dep_group_category_driver", "dep_group_no_parent", "rep_sw_gap")
CORE_FAMILY = "market_state"
EVIDENCE_ROLE = "exploratory_dev"  # this runner never produces prospective_confirmation


def parse_families(spec: str) -> list[str]:
    """``--families`` value -> exploratory families beyond the always-on ``market_state``."""
    from astrolabe.research_lab import ml_panel

    names = [x.strip() for x in str(spec).split(",") if x.strip()] or [CORE_FAMILY]
    bad = [n for n in names if n != CORE_FAMILY and n not in ml_panel.EXPLORATORY_FAMILY_CHOICES]
    if bad:
        raise SystemExit(f"unknown --families {bad}; choose from "
                         f"{[CORE_FAMILY, *ml_panel.EXPLORATORY_FAMILY_CHOICES]}")
    return [n for n in dict.fromkeys(names) if n != CORE_FAMILY]


# ---------------------------------------------------------------------------------------------
# Discovery and the development gate
# ---------------------------------------------------------------------------------------------


def _start_epoch(cap: dict) -> float:
    return pd.Timestamp(cap["started_utc"]).timestamp()


MIN_EXT_VERSION = 3  # parent links (parentEventId) enter dep_group only from sidecar v3


def sidecar_version(snapshot_dir: Path) -> int | None:
    """Sidecar ``ext_version`` number (``snapshot-ext-v3`` -> 3) when the sidecar is complete."""
    from astrolabe.research_lab import forecast

    d = Path(snapshot_dir)
    mp = d / "ext_manifest.json"
    if mp.exists() and not (d / "rows_ext.csv.gz").exists():
        # manifest kept, sidecar rotated off by the host retention. Discovery only needs to know
        # the capture WAS complete: a manifest that shows a complete sidecar of a parseable
        # version counts (``require_local`` still guards every read of the sidecar, e.g.
        # ml_panel.load_snapshot_rows, so a period that is not cached and needs it fails loudly).
        # Any other manifest (unreadable, not complete, no version): fail closed, loud as before.
        try:
            m = json.loads(mp.read_text())
            if m.get("sidecar_status") == "complete":
                return int(str(m.get("ext_version", "")).rsplit("v", 1)[1])
        except (OSError, ValueError, IndexError):
            pass
        forecast.require_local(d / "rows_ext.csv.gz")
    if not (d / "rows_ext.csv.gz").exists() or not mp.exists():
        return None
    try:
        m = json.loads(mp.read_text())
        if m.get("sidecar_status") != "complete":
            return None
        return int(str(m.get("ext_version", "")).rsplit("v", 1)[1])
    except (OSError, ValueError, IndexError):
        return None


def has_complete_sidecar(snapshot_dir: Path) -> bool:
    """Counts toward the gate only with a complete sidecar of ext_version >= 3."""
    v = sidecar_version(snapshot_dir)
    return v is not None and v >= MIN_EXT_VERSION


def discover_captures(snapshot_root: Path) -> list[dict]:
    """Complete snapshots ordered by start. Reads manifests only."""
    caps = []
    for mp in Path(snapshot_root).glob("*/manifest.json"):
        man = json.loads(mp.read_text())
        if man.get("state") != "complete":
            continue
        caps.append({"capture_id": man["capture_id"], "started_utc": man["started_utc"],
                     "finished_utc": man.get("finished_utc"), "dir": str(mp.parent),
                     "sidecar": has_complete_sidecar(mp.parent),
                     "ext_version": sidecar_version(mp.parent)})
    return sorted(caps, key=_start_epoch)


def consecutive_runs(caps: list[dict]) -> list[list[dict]]:
    """Maximal runs of sidecar-complete snapshots with every start gap in [GAP_MIN_H, GAP_MAX_H]."""
    from astrolabe.research_lab import ml_panel

    runs: list[list[dict]] = []
    cur: list[dict] = []
    for c in caps:
        if not c["sidecar"]:
            if cur:
                runs.append(cur)
            cur = []
            continue
        if cur:
            gap_h = (_start_epoch(c) - _start_epoch(cur[-1])) / 3600.0
            if not (ml_panel.GAP_MIN_H <= gap_h <= ml_panel.GAP_MAX_H):
                runs.append(cur)
                cur = []
        cur.append(c)
    if cur:
        runs.append(cur)
    return runs


def gate_status(
    caps: list[dict], minimum: int = MIN_SNAPSHOTS, now: datetime | None = None
) -> dict:
    runs = consecutive_runs(caps)
    longest = max(runs, key=len) if runs else []
    trailing = runs[-1] if runs and caps and runs[-1][-1] is caps[-1] else []
    now = now or datetime.now(UTC)
    remaining = max(minimum - max(len(longest), len(trailing)), 0)
    anchor = datetime.fromtimestamp(_start_epoch(trailing[-1]), UTC) if trailing else now
    return {
        "minimum": minimum,
        "complete_snapshots": len(caps),
        "qualifying_with_sidecar": sum(c["sidecar"] for c in caps),
        "longest_consecutive_run": len(longest),
        "current_run": len(trailing),
        "met": len(longest) >= minimum,
        "remaining": remaining,
        "eta_utc": None if remaining == 0 else
        (anchor + timedelta(hours=CADENCE_H * remaining)).strftime("%Y-%m-%dT%H:%MZ"),
        "eta_assumption": f"{CADENCE_H:g}h cadence continuing from the latest qualifying snapshot",
        "run_capture_ids": [c["capture_id"] for c in longest],
    }


def usable_sweeps(sweep_root: Path, caps: list[dict]) -> tuple[dict, dict]:
    """Declared A sweeps (``ml_panel.pick_sweeps``) restricted to those ``build_period`` accepts:
    started at or after their snapshot's start and finished before the next snapshot starts."""
    from astrolabe.research_lab import ml_panel

    if not Path(sweep_root).exists():
        return {}, {"considered": 0, "used": 0}
    picked, report = ml_panel.pick_sweeps(sweep_root)
    out, dropped = {}, []
    for k, cap in enumerate(caps[:-1]):
        sw = picked.get(cap["capture_id"])
        if sw is None:
            continue
        if sw["started_epoch"] < _start_epoch(cap):
            dropped.append({"sweep_id": sw["sweep_id"], "reason": "started before its snapshot"})
        elif sw["receipt_epoch"] > _start_epoch(caps[k + 1]):
            dropped.append({"sweep_id": sw["sweep_id"], "reason": "finished after next snapshot"})
        else:
            out[cap["capture_id"]] = sw
    return out, {**report, "used": len(out), "dropped": dropped}


# ---------------------------------------------------------------------------------------------
# Panel (cached parquet keyed by panel hash)
# ---------------------------------------------------------------------------------------------


def load_link_fields(frame: Path | None) -> tuple[dict | None, str | None]:
    """Event titles and resolution-source domains from one fs2 frame, for the non-sports
    dependence links (``ml_panel.category_group_columns``). Static metadata used only to form
    clusters, never as a feature. Returns (link_fields, digest) or (None, None)."""
    if frame is None:
        return None, None
    from astrolabe.research_lab import ml_panel

    ev, src, _ = ml_panel._analysis().stream_frame(Path(frame))
    lf = {"event_titles": dict(zip(ev["event_id"], ev["event_title"], strict=True)),
          "sources": dict(zip(src["market_id"], src["source"], strict=True))}
    return lf, f"{Path(frame).name}:{len(lf['event_titles'])}:{len(lf['sources'])}"


def panel_hash(caps: list[dict], sweeps: dict, policy: dict, delta: float,
               with_leak: bool = False, link_digest: str | None = None) -> str:
    from astrolabe.research_lab import ml_panel, provenance

    here = Path(ml_panel.__file__).parent
    body = {
        "captures": [[c["capture_id"], c["started_utc"], bool(c["sidecar"])] for c in caps],
        "sweeps": {k: [v["sweep_id"], v["returned"], v["eligible"]]
                   for k, v in sorted(sweeps.items())},
        "policy": policy, "delta": delta, "with_leak": with_leak, "link_digest": link_digest,
        "features": ml_panel.extended_feature_versions(),
        "modules": {m: provenance.sha256_file(here / f"{m}.py") for m in HASHED_MODULES},
        "dep_underlying_date": ml_panel.DEP_GROUP_UNDERLYING,
    }
    blob = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


def _jsonable(o):
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (Path, datetime)):
        return str(o)
    raise TypeError(f"not serialisable: {type(o)}")


def _clean(o):
    """NaN/inf -> None so the output is strict JSON."""
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, np.ndarray):
        return _clean(o.tolist())
    if isinstance(o, np.generic):
        return _clean(o.item())
    if isinstance(o, float) and not math.isfinite(o):
        return None
    return o


def period_salt(delta: float, link_digest: str | None) -> str:
    """Everything a period frame depends on besides its captures and sweeps (period cache key)."""
    from astrolabe.research_lab import ml_panel, provenance

    here = Path(ml_panel.__file__).parent
    body = {"delta": delta, "link_digest": link_digest,
            "features": ml_panel.extended_feature_versions(),
            "modules": {m: provenance.sha256_file(here / f"{m}.py") for m in HASHED_MODULES},
            "dep_underlying_date": ml_panel.DEP_GROUP_UNDERLYING}
    blob = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


def read_panel_compact(pq_path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    """Value- and dtype-identical to ``pd.read_parquet(pq_path, columns=columns)`` with a far
    smaller peak: numeric columns convert column-by-column (no consolidated multi-GB block) while
    the Arrow buffers are released as they convert, and string columns become object arrays that
    share one Python str per distinct value (nulls stay ``None``)."""
    import numpy as np
    import pyarrow as pa
    import pyarrow.parquet as papq

    table = papq.read_table(pq_path, columns=columns)
    names = list(table.column_names)
    strs = {}
    for n in names:
        t = table.schema.field(n).type
        if pa.types.is_string(t) or pa.types.is_large_string(t):
            enc = table.column(n).combine_chunks().dictionary_encode()
            uniq = np.empty(len(enc.dictionary) + 1, dtype=object)
            uniq[: len(enc.dictionary)] = enc.dictionary.to_pylist()
            uniq[-1] = None
            strs[n] = uniq[enc.indices.fill_null(len(enc.dictionary)).to_numpy()]
            del enc
    table = table.drop_columns(list(strs))
    df = table.to_pandas(split_blocks=True, self_destruct=True)
    del table
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", pd.errors.PerformanceWarning)
        for i, n in enumerate(names):
            if n in strs:
                df.insert(i, n, strs.pop(n))
    return df


def slim_panel_summary(df: pd.DataFrame) -> dict:
    """``panel_summary(df)`` without copying the whole frame: in-frame NaN rates, then the summary
    on the (small) DRY_COLUMNS subset it actually reads."""
    from astrolabe.research_lab import ml_panel

    rates = ({c: float(df[c].isna().mean()) for c in ml_panel.EXTENDED_NAMES if c in df.columns}
             if len(df) else {})
    return panel_summary(df[[c for c in DRY_COLUMNS if c in df.columns]].copy(), rates)


def labelled_consuming(df: pd.DataFrame) -> pd.DataFrame:
    """Equal to ``ml_panel.labelled(df)`` but drops each column of ``df`` as soon as it is copied
    (``df`` is left empty), so the full and the labelled frame never coexist."""
    mask = df["target_available"].to_numpy(dtype=bool)
    cols = {}
    for c in list(df.columns):
        cols[c] = df[c].to_numpy()[mask]
        del df[c]
    out = pd.DataFrame(cols)
    out.attrs.update(df.attrs)
    return out


LEAK_PREFIX = "leak_"


def read_labelled_panel(pq_path: Path, columns: list[str] | None = None,
                        exclude_prefix: str | None = None,
                        mask: np.ndarray | None = None) -> pd.DataFrame:
    """Value-, dtype- and order-identical to ``labelled(read_panel_compact(pq_path))`` restricted
    to ``columns`` (default every column except those starting with ``exclude_prefix``), but the
    full frame never exists: one column is read, masked to ``target_available`` rows and kept,
    so the peak is the labelled frame plus one full column (~31 MB per 4M rows)."""
    import pyarrow.parquet as papq

    schema = papq.read_schema(pq_path)
    names = list(schema.names)
    if mask is None:
        mask = read_panel_compact(pq_path, ["target_available"])["target_available"].to_numpy(
            dtype=bool)
    want = set(columns) if columns is not None else {
        n for n in names if not (exclude_prefix and n.startswith(exclude_prefix))}
    names = [n for n in names if n in want]
    flt = [n for n in names if str(schema.field(n).type) == "double"]
    # float64 columns fill one column-major block (no later consolidation copy); the frame wraps
    # it without copying and the other columns are inserted at their original positions
    block = np.empty((int(mask.sum()), len(flt)), dtype=np.float64, order="F")
    for j, n in enumerate(flt):
        block[:, j] = read_panel_compact(pq_path, [n])[n].to_numpy()[mask]
    out = pd.DataFrame(block, columns=flt, copy=False)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", pd.errors.PerformanceWarning)
        for i, n in enumerate(names):
            if n not in out.columns or out.columns[i] != n:
                out.insert(i, n, read_panel_compact(pq_path, [n])[n].to_numpy()[mask])
    return out


def get_panel(caps, sweeps, policy, delta, cache_root: Path, rebuild: bool = False,
              with_leak: bool = False, link_frame: Path | None = None,
              columns: list[str] | tuple[str, ...] | None = None):
    """Returns (panel, counts, hash, cache_dir, from_cache). Snapshots are only read.

    The panel is always returned as read back from ``panel.parquet`` (``columns`` restricts the
    read; ``None`` = every column). ``rebuild`` also ignores the period cache."""
    from astrolabe.research_lab import ml_panel_cache

    link_fields, link_digest = load_link_fields(link_frame)
    h = panel_hash(caps, sweeps, policy, delta, with_leak, link_digest)
    cdir = Path(cache_root) / h
    pq, meta = cdir / "panel.parquet", cdir / "meta.json"
    cached = pq.exists() and meta.exists() and not rebuild
    if cached:
        m = json.loads(meta.read_text())
        counts, info = m["counts"], m["category_info"]
    else:
        cdir.mkdir(parents=True, exist_ok=True)
        counts, info, n = ml_panel_cache.build_panel_to_parquet(
            caps, pq, Path(cache_root) / "periods", period_salt(delta, link_digest),
            sweep_receipts=sweeps, delta=delta, policy=policy, with_leak=with_leak,
            link_fields=link_fields, rebuild=rebuild,
            log=lambda msg: print(f"[panel] {msg} (peak RSS {peak_rss_mb():.0f} MB)", flush=True))
        meta.write_text(json.dumps(_clean({"counts": counts, "category_info": info,
                                           "n_rows": n}), default=_jsonable))
    if columns is not None:
        import pyarrow.parquet as papq

        have = set(papq.read_schema(pq).names)
        columns = [c for c in columns if c in have]
    df = read_panel_compact(pq, None if columns is None else list(columns))
    df.attrs["category_info"] = info
    return df, counts, h, cdir, cached


def feature_nan_rates(pq_path: Path, names) -> dict:
    """``panel_summary`` NaN rates read one column at a time (a full panel never loads)."""
    import pyarrow.parquet as papq

    have = set(papq.read_schema(pq_path).names)
    return {c: float(pd.read_parquet(pq_path, columns=[c])[c].isna().mean())
            for c in names if c in have}


def code_sha() -> str:
    from astrolabe.research_lab import provenance

    g = provenance.git_state()
    return g["git_head"] + ("+dirty" if g["git_dirty"] else "")


def plan(df: pd.DataFrame, horizon: int = 1,
         extra_names: tuple[str, ...] = ()) -> tuple[dict | None, str | None]:
    """Fold manifest, or (manifest-or-None, reason) when the panel cannot support one.

    For ``horizon`` k > 1 the panel must carry ``add_horizon_targets`` columns; periods, label
    times and the embargo are those of the k-step target.
    """
    from astrolabe.research_lab import ml_panel

    if not len(df):
        return None, "empty panel"
    try:
        man = ml_panel.plan_folds(ml_panel.period_table(ml_panel.horizon_view(df, horizon)),
                                  horizon=horizon, code_sha=code_sha(),
                                  feature_vers={
                                      **ml_panel.extended_feature_versions(),
                                      **(ml_panel.flow_feature_versions(extra_names)
                                         if extra_names else {})},
                                  category_info=df.attrs.get("category_info"))
    except ValueError as e:
        return None, str(e)
    if not man["folds"]:
        need = man["min_train_periods"] + ml_panel.BLOCK_PERIODS
        return man, f"no full fold: {len(man['periods'])} periods, need at least {need}"
    return man, None


# ---------------------------------------------------------------------------------------------
# Panel summaries (used by the dry run and the report)
# ---------------------------------------------------------------------------------------------


def panel_summary(df: pd.DataFrame, nan_rates: dict | None = None) -> dict:
    """``nan_rates`` (from ``feature_nan_rates``) replaces the in-frame NaN rates when the frame
    was read without its feature columns."""
    from astrolabe.research_lab import ml_panel

    lab = ml_panel.labelled(df)
    per = []
    for p, g in df.groupby("period"):
        gl = g[g["target_available"]]
        per.append({"period": int(p), "capture_i": g["capture_i"].iloc[0], "n_rows": int(len(g)),
                    "n_labelled": int(len(gl)),
                    "class_shares": ml_panel.class_shares(gl["y_class"]) if len(gl) else None})
    feats = [c for c in ml_panel.EXTENDED_NAMES if c in df.columns]
    if nan_rates is None:
        nan_rates = {c: float(df[c].isna().mean()) for c in feats} if len(df) else {}
    ev = lab["event_id"].where(lab["event_id"].notna(), "mkt:" + lab["market_id"].astype(str))
    series = {"event": ev, "dep_group": lab["dep_group"],
              **{c: lab[c] for c in ("dep_group_season", "dep_group_econ",
                                     "dep_group_category_driver") if c in lab.columns}}
    return {
        "n_rows": int(len(df)), "n_labelled": int(len(lab)),
        "n_periods": int(df["period"].nunique()) if len(df) else 0,
        "rows_per_period": per,
        "class_shares_labelled": ml_panel.class_shares(lab["y_class"]) if len(lab) else None,
        "feature_nan_rates": nan_rates,
        "k_clusters_labelled": {k: int(s.nunique()) for k, s in series.items()},
        "largest_cluster_share_labelled": {
            k: float(s.value_counts(normalize=True).iloc[0]) if len(s) else None
            for k, s in series.items()},
        "dep_group_no_parent_share": float(lab["dep_group_no_parent"].astype(float).mean())
        if len(lab) else None,
        "sweep_gap_rows": int(df["rep_sw_gap"].notna().sum()) if "rep_sw_gap" in df else 0,
    }


SENSITIVITY_CLUSTERS = ("dep_group_season", "dep_group_econ", "dep_group_category_driver")


def add_sensitivity_clusters(clusters: dict, lab: pd.DataFrame) -> None:
    """S1 season, S4 economic driver, S5 category driver: reported next to the co-primary
    event and dep_group clusterings (which stay ``category_aware``), never combined into them."""
    for c in SENSITIVITY_CLUSTERS:
        if c in lab.columns:
            clusters[c] = lab[c].to_numpy()


def peak_rss_mb() -> float:
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r / 1e6 if sys.platform == "darwin" else r / 1e3


# ---------------------------------------------------------------------------------------------
# Dry run: builds the panel and folds; fits nothing, logs nothing
# ---------------------------------------------------------------------------------------------


def family_coverage(df: pd.DataFrame, extra: list[str], sample_root: Path,
                    nan_rates: dict | None = None) -> tuple[pd.DataFrame, dict]:
    """Per-family coverage. ``market_state`` = MC1 columns; flow/wallet join the trade samples."""
    from astrolabe.research_lab import ml_panel

    if nan_rates is not None:
        mc1 = [c for c in ml_panel.EXTENDED_NAMES if c in nan_rates]
        rates = [nan_rates[c] for c in mc1] if len(df) else []
    else:
        mc1 = [c for c in ml_panel.EXTENDED_NAMES if c in df.columns]
        rates = [float(df[c].isna().mean()) for c in mc1] if len(df) else []
    cov: dict = {CORE_FAMILY: {
        "n_features": len(mc1), "exploratory_family": False,
        "mean_nan_rate": float(np.mean(rates)) if rates else None}}
    if extra:
        df, rep = ml_panel.add_flow_wallet_columns(df, sample_root, extra)
        for f, c in rep["coverage"]["families"].items():
            cov[f] = {**c, "exploratory_family": True}
        cov["_join"] = {k: v for k, v in rep.items() if k != "coverage"}
        cov["_join"]["captures_in_panel"] = rep["coverage"]["captures_in_panel"]
        cov["_join"]["captures_with_sample"] = rep["coverage"]["captures_with_sample"]
    return df, cov


def dry_run(snapshot_root: Path, sweep_root: Path, cache_root: Path, policy: dict,
            delta: float, rebuild: bool = False, families: list[str] | None = None,
            sample_root: Path = SAMPLE_ROOT, link_frame: Path | None = None) -> dict:
    t0 = time.perf_counter()
    caps = discover_captures(snapshot_root)
    gate = gate_status(caps)
    gate_pub = {k: v for k, v in gate.items() if k != "run_capture_ids"}
    if len(caps) < 2:
        return {"mode": "dry-run", "gate": gate_pub, "error": "fewer than 2 complete snapshots"}
    sweeps, sweep_report = usable_sweeps(sweep_root, caps)
    # without flow/wallet families only the summary columns are read back; the feature NaN
    # rates are streamed column by column (the full panel never sits in memory)
    slim = not families
    df, counts, h, cdir, cached = get_panel(caps, sweeps, policy, delta, cache_root, rebuild,
                                            link_frame=link_frame,
                                            columns=DRY_COLUMNS if slim else None)
    from astrolabe.research_lab import ml_panel

    rates = feature_nan_rates(cdir / "panel.parquet", ml_panel.EXTENDED_NAMES) if slim else None
    df, fam_cov = family_coverage(df, families or [], sample_root, rates)
    extra_names = tuple(n for f in (families or [])
                        for n in ml_panel_family_names(f))
    man, why = plan(df, 1, extra_names)
    return {
        "mode": "dry-run (nothing fitted on real labels, nothing logged)",
        "families": fam_cov,
        "gate": gate_pub, "panel_hash": h, "cache_dir": str(cdir), "from_cache": cached,
        "n_snapshots_used": len(caps), "sweeps": sweep_report,
        "periods_skipped": [c for c in counts if c.get("skipped")],
        "panel": panel_summary(df, rates),
        "folds": {"n_folds": len(man["folds"]) if man else 0, "reason": why,
                  "manifest_sha256": man["manifest_sha256"] if man else None,
                  "periods": len(man["periods"]) if man else 0},
        "seconds": round(time.perf_counter() - t0, 1), "peak_rss_mb": round(peak_rss_mb(), 0),
    }


def ml_panel_family_names(family: str) -> tuple[str, ...]:
    from astrolabe.research_lab import ml_panel

    return ml_panel.family_features([family])[family]


def print_dry(out: dict) -> None:
    g, p = out["gate"], out.get("panel")
    state = "MET" if g["met"] else f"NOT MET, ETA {g['eta_utc']}"
    print(f"[dry-run] gate: {g['qualifying_with_sidecar']} sidecar snapshots of "
          f"{g['complete_snapshots']} complete; longest consecutive run "
          f"{g['longest_consecutive_run']}/{g['minimum']}; {state} ({g['eta_assumption']})")
    if p is None:
        print(out.get("error"))
        return
    src = "cache" if out["from_cache"] else "built"
    print(f"[dry-run] panel {out['panel_hash'][:12]} ({src}): "
          f"{p['n_rows']} rows, {p['n_labelled']} labelled, {p['n_periods']} periods")
    print(f"[dry-run] class shares: {p['class_shares_labelled']}")
    share = {k: None if v is None else round(v, 3)
             for k, v in p["largest_cluster_share_labelled"].items()}
    print(f"[dry-run] K (labelled): {p['k_clusters_labelled']}  largest share: {share}")
    print(f"[dry-run] dep_group_no_parent share: {p['dep_group_no_parent_share']}")
    print(f"[dry-run] folds: {out['folds']['n_folds']} ({out['folds']['reason']})")
    for f, c in out.get("families", {}).items():
        if f.startswith("_"):
            continue
        if c.get("exploratory_family"):
            nn = c["mean_non_nan_share_among_sampled"]
            print(f"[dry-run] family {f} (exploratory_family): {c['sampled_rows']} sampled rows "
                  f"({c['sampled_share']:.1%} of panel), {c['n_features']} features, "
                  f"mean non-NaN among sampled {'n/a' if nn is None else f'{nn:.2f}'}")
        else:
            print(f"[dry-run] family {f} (MC1): {c['n_features']} features, "
                  f"mean NaN rate {c['mean_nan_rate']}")
    j = out.get("families", {}).get("_join")
    if j:
        print(f"[dry-run] trade samples: {len(j['samples'])} joined over "
              f"{j['captures_with_sample']}/{j['captures_in_panel']} panel captures, "
              f"{len(j['skipped'])} skipped, origin mismatches {j['origin_mismatch_rows']}")
    hi = sorted(p["feature_nan_rates"].items(), key=lambda kv: -kv[1])[:8]
    print("[dry-run] highest NaN rates: " + ", ".join(f"{k}={v:.2f}" for k, v in hi))
    print(f"[dry-run] sweeps used {out['sweeps'].get('used')}, gap rows {p['sweep_gap_rows']}; "
          f"{out['seconds']}s, peak RSS {out['peak_rss_mb']:.0f} MB")


# ---------------------------------------------------------------------------------------------
# Probe arms (gap placebo and sweep-gap re-score): M0 logistic on declared column sets
# ---------------------------------------------------------------------------------------------


@contextlib.contextmanager
def _columns(attr: str, cols):
    """Run an ``ml_models`` fit on a different column set (``M0_FEATURES`` or ``M12_FEATURES``)."""
    from astrolabe.research_lab import ml_models as mm

    old = getattr(mm, attr)
    setattr(mm, attr, tuple(cols))
    try:
        yield
    finally:
        setattr(mm, attr, old)


def fit_probe(name: str, cols, lab, manifest, sink, fn=None, attr: str = "M0_FEATURES"):
    from astrolabe.research_lab import ml_models as mm

    mm.ARMS[name] = fn or mm.fit_m0
    try:
        with _columns(attr, cols or getattr(mm, attr)):
            return mm.run_arm(name, lab, manifest, sink=sink)
    finally:
        mm.ARMS.pop(name, None)


def run_gap_diagnostics(lab, manifest, results, sink) -> dict:
    """Gap placebo (M0 + gap, report-only), sweep-gap diagnostic and its re-score."""
    from astrolabe.research_lab import ml_models as mm
    from astrolabe.research_lab import ml_panel

    base = list(mm.M0_FEATURES)
    sw = list(ml_panel.SWEEP_NAMES)
    probes = {
        "M0_gap_placebo": [*base, "rep_sw_gap"],
        "M0_probe_sw": [*base, *sw],
        "M0_probe_sw_gap": [*base, *sw, "rep_sw_gap"],
    }
    fits = {n: fit_probe(n, c, lab, manifest, sink) for n, c in probes.items()}
    by_cols = {tuple(base): results["M0"], **{tuple(probes[n]): fits[n] for n in probes}}
    y = lab["y_class"].to_numpy(float)

    def score_fn(d: pd.DataFrame, cols: list[str]) -> float:
        r = by_cols[tuple(cols)]
        idx = d.index.to_numpy()
        idx = idx[r.test_mask[idx]]
        return float(mm.log_loss_rows(r.proba[idx], y[idx].astype(int)).mean())

    return {
        "status": "REPORT-ONLY, non-gating (gap placebo and sweep-gap diagnostic)",
        "correlations": ml_panel.sweep_gap_diagnostic(lab),
        "rescore": ml_panel.rescore_with_gap_control(lab, base, score_fn),
        "fits": fits,
    }


SHUFFLE_SEED = 116
LEAK_COLUMN = "dmid"  # the target-snapshot move itself (scorer sanity check)
SHUFFLE_BLOCKS = {"period": ["period"], "period_event": ["period", "event"]}


def _block_key(lab: pd.DataFrame, by: str) -> pd.Series:
    ev = lab["event_id"].where(lab["event_id"].notna(), "mkt:" + lab["market_id"].astype(str))
    parts = {"period": lab["period"].astype(str), "event": ev.astype(str)}
    key = parts[SHUFFLE_BLOCKS[by][0]]
    for c in SHUFFLE_BLOCKS[by][1:]:
        key = key + "|" + parts[c]
    return key


def singleton_share(lab: pd.DataFrame, by: str) -> float:
    """Share of rows alone in their shuffle block (their label cannot move)."""
    size = _block_key(lab, by).map(_block_key(lab, by).value_counts())
    return float((size == 1).mean()) if len(lab) else 0.0


def shuffle_labels(lab: pd.DataFrame, by: str = "period", seed: int = SHUFFLE_SEED) -> pd.DataFrame:
    """Seeded label permutation inside blocks: ``period`` is the global null; ``period_event``
    (design wording) is the secondary placebo. Features and timing columns are untouched, so the
    fold plan and purge are unchanged."""
    rng = np.random.default_rng(seed)
    out = lab.copy(deep=False)  # only y_class is replaced (assignment rebinds, never writes)
    y = out["y_class"].to_numpy(float).copy()
    for idx in out.groupby(_block_key(out, by), sort=True).indices.values():
        y[idx] = y[rng.permutation(idx)]
    out["y_class"] = y
    return out


def run_placebos(lab, manifest, results, clusters, sink, leak_loader=None) -> dict:
    """Report-only placebos, logged as placebo arms (never enter a verdict): shuffled labels
    (global within-period null, plus period x event), the leak positive control with EVERY
    feature shifted to the target snapshot (``leak_*`` panel columns) and the ``dmid`` scorer
    sanity check, and the quote-age-only model."""
    from astrolabe.research_lab import ml_models as mm

    sink = dataclasses.replace(sink, evidence_role="placebo")  # placebo arms carry their own role
    base = list(mm.M0_FEATURES)
    m0 = results["M0"]
    out: dict = {"status": "REPORT-ONLY placebos; never enter a verdict", "singleton_share": {
        by: singleton_share(lab, by) for by in SHUFFLE_BLOCKS}}
    for by in SHUFFLE_BLOCKS:
        shuf = shuffle_labels(lab, by)
        m0s = fit_probe(f"M0_placebo_shuffled_{by}", None, shuf, manifest, sink)
        m1s = fit_probe(f"M1_placebo_shuffled_{by}", None, shuf, manifest, sink, fn=mm.fit_m1)
        out[f"shuffled_labels_{by}"] = mm.score_arms(
            shuf, {"M0": m0s, f"M1_placebo_shuffled_{by}": m1s}, clusters, sink=sink,
            manifest=manifest)
    leak_cols = [f"leak_{n}" for n in mm.M12_FEATURES]
    leak_src = lab if all(c in lab.columns for c in leak_cols) else None
    if leak_src is None and leak_loader is not None:  # leak_* kept out of memory until now
        leak_src = leak_loader(leak_cols)
        if not all(c in leak_src.columns for c in leak_cols):
            leak_src = None
    if leak_src is not None:
        lk = lab.copy(deep=False)  # the shifted features are rebound, lab is not written
        for n in mm.M12_FEATURES:
            lk[n] = leak_src[f"leak_{n}"].to_numpy()
        del leak_src
        m1l = fit_probe("M1_placebo_leak_all_features", None, lk, manifest, sink, fn=mm.fit_m1)
        out["leak_all_features_positive_control"] = mm.score_arms(
            lab, {"M0": m0, "M1_placebo_leak_all_features": m1l}, clusters, sink=sink,
            manifest=manifest)
    else:
        out["leak_all_features_positive_control"] = {
            "status": "NOT RUN: leak_* columns absent (panel built without with_leak)"}
    dm = fit_probe("M0_placebo_leak_dmid", [*base, LEAK_COLUMN], lab, manifest, sink)
    out["leak_dmid_sanity_check"] = mm.score_arms(
        lab, {"M0": m0, "M0_placebo_leak_dmid": dm}, clusters, sink=sink, manifest=manifest)
    qa = fit_probe("M0_placebo_quote_age", [*base, "ml_quote_staleness_h"], lab, manifest, sink)
    out["quote_age_only"] = mm.score_arms(
        lab, {"M0": m0, "M0_placebo_quote_age": qa}, clusters, sink=sink, manifest=manifest)
    return out


def run_no_sweep_sensitivity(lab, manifest, results, clusters, sink) -> dict:
    """Report-only: M1 and M2 refitted on tier (a) minus the sweep (a11) features."""
    from astrolabe.research_lab import ml_models as mm

    fits = {
        "M1_noSweep": fit_probe("M1_noSweep", mm.M12_NO_SWEEP, lab, manifest, sink,
                                fn=mm.fit_m1, attr="M12_FEATURES"),
        "M2_noSweep": fit_probe("M2_noSweep", mm.M12_NO_SWEEP, lab, manifest, sink,
                                fn=mm.fit_m2, attr="M12_FEATURES"),
    }
    return {
        "status": "REPORT-ONLY sensitivity: tier (a) minus sweep (ml_sw_*) features",
        "features_removed": sorted(set(mm.M12_FEATURES) - set(mm.M12_NO_SWEEP)),
        "score": mm.score_arms(
            lab, {"M0": results["M0"], "M1": results["M1"], "M2": results["M2"], **fits},
            clusters, sink=sink, manifest=manifest),
    }


# ---------------------------------------------------------------------------------------------
# Real development run
# ---------------------------------------------------------------------------------------------


def _count_lines(path: Path) -> int:
    p = Path(path)
    if not p.exists():
        return 0
    with open(p, encoding="utf-8") as fh:
        return sum(1 for _ in fh)


def accounting(results: dict, probes: dict, trials_before: int, trials_path: Path) -> dict:
    n_fit = {a: len(r.folds) for a, r in {**results, **probes}.items()}
    configs = {a: sum(len(f.get("hyper_search", [])) for f in r.folds) for a, r in results.items()}
    after = _count_lines(trials_path)
    return {"fold_fits_per_arm": n_fit, "tuning_configs_evaluated_inside_folds": configs,
            "trial_lines_before": trials_before, "trial_lines_after": after,
            "trial_lines_written": after - trials_before}


def real_run(args, caps, gate, policy) -> dict:
    from astrolabe.research_lab import ml_models as mm
    from astrolabe.research_lab import ml_panel, provenance

    t0 = time.perf_counter()
    run_ids = set(gate["run_capture_ids"])
    run_caps = [c for c in caps if c["capture_id"] in run_ids]
    sweeps, sweep_report = usable_sweeps(args.sweep_root, run_caps)
    target, horizon = getattr(args, "target", "direction"), int(getattr(args, "horizon", 1))
    extra = list(getattr(args, "families_extra", []) or [])
    direct = not extra and target == "direction" and horizon == 1
    # direct path: only the slim columns (fold plan, summary) are read whole; the labelled frame
    # is then streamed column by column straight from the parquet (see read_labelled_panel)
    df, counts, h, cdir, cached = get_panel(run_caps, sweeps, policy, args.delta,
                                            args.cache_root, args.rebuild, with_leak=True,
                                            link_frame=getattr(args, "link_frame", None),
                                            columns=DRY_COLUMNS if direct else None)
    join_report = None
    if extra:  # exploratory flow/wallet families: joined after the cached MC1 panel
        df, join_report = ml_panel.add_flow_wallet_columns(
            df, getattr(args, "sample_root", SAMPLE_ROOT), extra)
    if extra or not (target == "direction" and horizon == 1):
        return exploratory_run(args, df, h, cdir, cached, gate, run_caps, sweeps, sweep_report,
                               target, horizon, t0, extra, join_report)
    man, why = plan(df)
    if man is None or why:
        raise SystemExit(f"cannot plan folds: {why}")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    stem = f"ml_dev_{stamp}_{man['manifest_sha256'][:8]}"
    # the manifest is written (and hashed) before any fit
    (out_dir / f"{stem}_fold_manifest.json").write_text(
        json.dumps(_clean(man), indent=1, default=_jsonable))
    # pure summary of the full panel, computed now so the full frame can be freed before the fits
    pq_path = cdir / "panel.parquet"
    panel_sum = panel_summary(df[[c for c in DRY_COLUMNS if c in df.columns]].copy(),
                              feature_nan_rates(pq_path, ml_panel.EXTENDED_NAMES))
    lab = read_labelled_panel(pq_path, exclude_prefix=LEAK_PREFIX)  # leak_* only for the placebo
    del df
    trials_path = Path(args.trials_path)
    before = _count_lines(trials_path)
    overridden = bool(gate.get("gate_overridden"))
    sink = mm.TrialSink(dataset=f"ml_dev panel {h[:12]}", path=trials_path,
                        extra={"gate_overridden": True} if overridden else {},
                        evidence_role=EVIDENCE_ROLE)
    # M1/M2 use the sweep (a11) features, so the sweep-gap diagnostic is mandatory
    sweep_used = bool(len(lab) and lab[list(ml_panel.SWEEP_NAMES)].notna().any().any()
                      and lab["rep_sw_gap"].notna().any())
    if not sweep_used:
        raise SystemExit("REFUSED: no sweep features / sweep-minus-Gamma gap in the labelled "
                         "panel, but the sweep-gap diagnostic is mandatory for M1/M2")

    results = mm.run_arms(lab, man, mm.ARM_NAMES, sink=sink, collect_shap=True)
    clusters = mm.cluster_vectors(lab, lab["dep_group"].to_numpy())
    add_sensitivity_clusters(clusters, lab)
    score = mm.score_arms(lab, results, clusters, sink=sink, manifest=man)
    shap = mm.summarize_shap(lab, results["M2"])

    diag = run_gap_diagnostics(lab, man, results, sink)
    probe_results = diag.pop("fits")
    diag["gap_placebo_vs_M0"] = mm.score_arms(
        lab, {"M0": results["M0"], "M0_gap_placebo": probe_results["M0_gap_placebo"]},
        clusters, sink=sink, manifest=man)
    no_sweep = run_no_sweep_sensitivity(lab, man, results, clusters, sink)
    placebos = run_placebos(
        lab, man, results, clusters, sink,
        leak_loader=lambda cols: read_labelled_panel(pq_path, columns=cols))
    report = {
        "placebos": placebos, "no_sweep_sensitivity": no_sweep,
        "gate_overridden": overridden,
        "status": ("GATE OVERRIDDEN (TEST ONLY). " if overridden else "")
        + "DEVELOPMENT/post-hoc. Exploratory. No edge, calibration or profitability claim.",
        "feature_lists": {"M0": list(mm.M0_FEATURES), "M1_M2": list(mm.M12_FEATURES),
                          "M3_eb": list(mm.BAYES_FEATURES),
                          "M1_M2_no_sweep": list(mm.M12_NO_SWEEP)},
        "utc": stamp, "panel_hash": h, "from_cache": cached, "cache_dir": str(cdir),
        "gate": {k: v for k, v in gate.items() if k != "run_capture_ids"},
        "capture_ids": [c["capture_id"] for c in run_caps], "sweeps": sweep_report,
        "manifest_sha256": man["manifest_sha256"], "n_folds": len(man["folds"]),
        "category_policy": man["category_policy"], "code_sha": man["code_sha"],
        "panel": panel_sum, "score": score, "shap": shap,
        "sweep_gap": diag, "sweep_gap_diagnostic_mandatory": True,
        "arms_use_sweep_features": True,
        "arm_fold_diagnostics": {a: r.folds for a, r in {**results, **probe_results}.items()},
        "accounting": accounting(results, probe_results, before, trials_path),
        "provenance": provenance.run_provenance(),
        "seconds": round(time.perf_counter() - t0, 1), "peak_rss_mb": round(peak_rss_mb(), 0),
    }
    report = _clean(report)
    jp, mp = out_dir / f"{stem}.json", out_dir / f"{stem}.md"
    jp.write_text(json.dumps(report, indent=1, default=_jsonable))
    mp.write_text(render_md(report))
    report["_paths"] = [str(jp), str(mp)]
    return report


def exploratory_run(args, df, h, cdir, cached, gate, run_caps, sweeps, sweep_report,
                    target, horizon, t0, extra_families=(), join_report=None) -> dict:
    """Separate EXPLORATORY run for a non-primary target / horizon.

    Own fold manifest (horizon-scaled purge and embargo), own report, own trial lines stamped with
    the target name and horizon. Not part of the confirmation family. The M0 / sweep-gap probes and
    placebos of the primary run are not repeated here: M1/M2 use the sweep features, so their
    results stay uninterpretable until the direction run's sweep-gap diagnostic is satisfied.
    """
    from astrolabe.research_lab import ml_models as mm
    from astrolabe.research_lab import ml_panel, provenance

    if horizon not in ml_panel.HORIZONS:
        raise SystemExit(f"horizon must be one of {ml_panel.HORIZONS}")
    if horizon > 1:
        df = ml_panel.add_horizon_targets(df, (horizon,), args.delta)
    extra_families = list(extra_families)
    extra_names = tuple(n for f in extra_families for n in ml_panel_family_names(f))
    man, why = plan(df, horizon, extra_names)
    if man is None or why:
        raise SystemExit(f"cannot plan folds: {why}")
    tname = mm.target_name(target, horizon)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    stem = f"ml_dev_{tname}_{stamp}_{man['manifest_sha256'][:8]}"
    (out_dir / f"{stem}_fold_manifest.json").write_text(
        json.dumps(_clean(man), indent=1, default=_jsonable))
    lab = ml_panel.labelled(ml_panel.horizon_view(df, horizon))
    trials_path = Path(args.trials_path)
    before = _count_lines(trials_path)
    overridden = bool(gate.get("gate_overridden"))
    extra = {"evidence_status_run": "EXPLORATORY", "target_name": tname}
    if extra_families:
        # not in MC1: adding a family is one feature-set revision (programme section 3)
        extra["exploratory_family"] = extra_families
        extra["families"] = [CORE_FAMILY, *extra_families]
    if overridden:
        extra["gate_overridden"] = True
    sink = mm.TrialSink(dataset=f"ml_dev panel {h[:12]} {tname}", path=trials_path, extra=extra,
                        evidence_role=EVIDENCE_ROLE)
    clusters = mm.cluster_vectors(lab, lab["dep_group"].to_numpy())
    add_sensitivity_clusters(clusters, lab)
    # M0 keeps the MC1 baseline; M1/M2 see MC1 plus the selected exploratory families
    cols_ctx = (_columns("M12_FEATURES", [*mm.M12_FEATURES, *extra_names]) if extra_names
                else contextlib.nullcontext())
    with cols_ctx:
        if target == "direction":
            results = mm.run_arms(lab, man, mm.ARM_NAMES, sink=sink, collect_shap=False)
            score = mm.score_arms(lab, results, clusters, sink=sink, manifest=man)
        else:
            results = mm.run_target_arms(target, lab, man, sink=sink)
            score = mm.score_target(lab, results, clusters, target, sink=sink, manifest=man)
    report = _clean({
        "target": tname, "target_family": target, "horizon_snapshots": horizon,
        "status": ("GATE OVERRIDDEN (TEST ONLY). " if overridden else "")
        + "EXPLORATORY (not in the confirmation family). DEVELOPMENT/post-hoc. "
        "No edge, calibration or profitability claim.",
        "sweep_gap_diagnostic": "NOT RUN for this target; M1/M2 use sweep features",
        "evidence_role": EVIDENCE_ROLE, "families": [CORE_FAMILY, *extra_families],
        "exploratory_family": extra_families or None,
        "family_join": join_report,
        "utc": stamp, "panel_hash": h, "from_cache": cached, "cache_dir": str(cdir),
        "gate": {k: v for k, v in gate.items() if k != "run_capture_ids"},
        "manifest_sha256": man["manifest_sha256"], "n_folds": len(man["folds"]),
        "embargo_s": man["embargo_s"], "code_sha": man["code_sha"],
        "n_labelled": int(len(lab)), "score": score,
        "arm_fold_diagnostics": {a: r.folds for a, r in results.items()},
        "accounting": {"trial_lines_written": _count_lines(trials_path) - before},
        "provenance": provenance.run_provenance(),
        "seconds": round(time.perf_counter() - t0, 1), "peak_rss_mb": round(peak_rss_mb(), 0),
    })
    jp = out_dir / f"{stem}.json"
    jp.write_text(json.dumps(report, indent=1, default=_jsonable))
    report["_paths"] = [str(jp)]
    return report


def render_md(r: dict) -> str:
    def f(x, nd=4):
        return "n/a" if x is None else f"{x:.{nd}f}"

    sc, pn = r["score"], r["panel"]
    L = [f"# ML development run {r['utc']}", "", f"**{r['status']}**", "",
         f"- dep_group_no_parent share: {r['panel']['dep_group_no_parent_share']}",
         f"- Panel `{r['panel_hash'][:12]}`: {pn['n_rows']} rows, {pn['n_labelled']} labelled, "
         f"{pn['n_periods']} periods, {r['n_folds']} folds; "
         f"manifest `{r['manifest_sha256'][:12]}`.",
         f"- Gate: longest consecutive sidecar run {r['gate']['longest_consecutive_run']} "
         f"(minimum {r['gate']['minimum']}).",
         f"- K (labelled rows): {pn['k_clusters_labelled']}; class shares "
         f"{pn['class_shares_labelled']}.",
         f"- Code `{r['code_sha']}`; {r['seconds']}s, peak RSS {r['peak_rss_mb']:.0f} MB.", ""]
    if sc["non_inferential"]:
        L += [f"**{sc['non_inferential_reason']}**", ""]
    L += ["## Out-of-fold scores", "", "| arm | log loss | Brier |", "|---|---|---|"]
    L += [f"| {a} | {f(v['log_loss'])} | {f(v['brier'])} |" for a, v in sc["arms"].items()]
    L += ["", "## Relative log-loss improvement vs M0 (95% clustered CI)", ""]
    names = {"event": "event (co-primary)",
             "dependence_group": "fixture-day dep_group (co-primary)",
             "dep_group_season": "season-level dep_group (sensitivity S1)",
             "dep_group_econ": "economic-driver dep_group (sensitivity S4)",
             "dep_group_category_driver": "category-driver dep_group (sensitivity S5, "
                                          "cluster-sensitive)"}
    for cname, blk in sc["bootstrap"].items():
        L += [f"### {names.get(cname, cname)}: K = {blk['n_clusters']}", "",
              "| arm | rel. improvement | CI95 |", "|---|---|---|"]
        for a, e in blk["log_loss"].items():
            ci = e["ci95"] or [None, None]
            L.append(f"| {a} | {f(e['rel_improvement'])} | [{f(ci[0])}, {f(ci[1])}] |")
        L.append("")
    L += ["A claim needs the CI to exclude 0 under BOTH co-primary clusterings; S1 is reported "
          "alongside. Development only.", "",
          "## Sweep-gap diagnostic and gap placebo (report-only, non-gating)", ""]
    sg = r["sweep_gap"]
    if "rescore" in sg:
        for tag, blk in sg["rescore"].items():
            L.append(f"- `{tag}`: sweep gain {f(blk['gain_sweep'], 5)}, with gap controlled "
                     f"{f(blk['gain_sweep_given_gap'], 5)} (log-loss units).")
        c = sg["correlations"]
        L.append(f"- share |gap| < 0.0025: {f(c['share_abs_gap_lt_0025'], 3)}; "
                 f"median |gap| {f(c['gap_abs_median'], 5)}.")
    else:
        L.append(sg["status"])
    pl = r["placebos"]
    L.append(f"- Singleton-block share of rows: {pl['singleton_share']}.")
    for tag, key, arm in (
            ("Shuffled labels, within period (global null; expect ~0)",
             "shuffled_labels_period", "M1_placebo_shuffled_period"),
            ("Shuffled labels, period x event (secondary)",
             "shuffled_labels_period_event", "M1_placebo_shuffled_period_event"),
            ("Leak control, ALL features shifted to target (must win)",
             "leak_all_features_positive_control", "M1_placebo_leak_all_features"),
            ("Leak sanity check, dmid added", "leak_dmid_sanity_check", "M0_placebo_leak_dmid"),
            ("Quote-age-only", "quote_age_only", "M0_placebo_quote_age")):
        if "bootstrap" not in pl[key]:
            L.append(f"- Placebo, {tag}: {pl[key].get('status')}")
            continue
        blk = pl[key]["bootstrap"]["event"]["log_loss"][arm]
        L.append(f"- Placebo, {tag}: rel. log-loss improvement vs M0 "
                 f"{f(blk['rel_improvement'])} (event-cluster CI {blk['ci95']}).")
    ns = r["no_sweep_sensitivity"]["score"]["bootstrap"]["event"]["log_loss"]
    L += ["", "## Tier (a) minus sweep sensitivity (report-only)", ""]
    L += [f"- {a}: rel. improvement vs M0 {f(e['rel_improvement'])}" for a, e in ns.items()]
    L += ["", f"M1/M2 use the sweep (a11) and sibling (a10) features "
          f"(`arms_use_sweep_features = {r['arms_use_sweep_features']}`); the sweep-gap "
          "diagnostic above is mandatory. M0 and M3_eb use their own declared features.",
          "", "## SHAP (M2, out-of-fold, exploratory)", "",
          "Never evidence of edge or mechanism. Mean |SHAP| by family (up minus down):", ""]
    fam = r["shap"]["margins"]["up_minus_down"]["mean_abs_by_family"]
    L += [f"- {k}: {f(v)}" for k, v in sorted(fam.items(), key=lambda kv: -kv[1])]
    a = r["accounting"]
    L += ["", "## Search accounting", "",
          f"- Fold fits per arm: {a['fold_fits_per_arm']}",
          f"- Tuning configs evaluated inside folds: {a['tuning_configs_evaluated_inside_folds']}",
          f"- Trial lines written to trials.jsonl: {a['trial_lines_written']}", ""]
    return "\n".join(L)


# ---------------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    from astrolabe.research_lab import ml_panel, provenance

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--snapshot-root", type=Path, default=SNAPSHOT_ROOT)
    ap.add_argument("--sweep-root", type=Path, default=SWEEP_ROOT)
    ap.add_argument("--cache-root", type=Path, default=CACHE_ROOT)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--trials-path", type=Path, default=provenance.TRIALS_PATH)
    ap.add_argument("--delta", type=float, default=ml_panel.DELTA_PRIMARY)
    ap.add_argument("--category-mode", choices=ml_panel.CATEGORY_MODES, default="all")
    ap.add_argument("--categories", default="", help="comma-separated fee categories")
    ap.add_argument("--target", choices=("direction", "dmid", "absmove"), default="direction",
                    help="direction (3-class, confirmatory at --horizon 1) | dmid (magnitude "
                    "regression) | absmove (|dmid| >= delta, binary); non-primary = EXPLORATORY")
    ap.add_argument("--horizon", type=int, choices=ml_panel.HORIZONS, default=1,
                    help="target snapshots ahead: 1 (~2h), 3 (~6h), 12 (~24h)")
    ap.add_argument("--families", default=CORE_FAMILY,
                    help="comma-separated: market_state (MC1, always on), flow, wallet. flow and "
                    "wallet are exploratory_family: not in MC1, separate EXPLORATORY run")
    ap.add_argument("--sample-root", type=Path, default=SAMPLE_ROOT,
                    help="trade_sample root holding plan.json + wallets.csv.gz per pass")
    ap.add_argument("--link-frame", type=Path, default=None,
                    help="fs2 frame dir giving event titles / resolution sources for the "
                    "non-sports dependence links (weather city x day, culture source, S4, S5); "
                    "without it dep_group equals fixture-day and dep_group_links_missing = 1")
    ap.add_argument("--rebuild", action="store_true", help="ignore the parquet cache")
    args = ap.parse_args(argv)
    args.families_extra = parse_families(args.families)
    policy = ml_panel.category_policy(
        args.category_mode, [c for c in args.categories.split(",") if c])

    if args.dry_run:
        out = dry_run(args.snapshot_root, args.sweep_root, args.cache_root, policy, args.delta,
                      args.rebuild, args.families_extra, args.sample_root, args.link_frame)
        print_dry(out)
        Path(args.cache_root).mkdir(parents=True, exist_ok=True)
        now = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        path = Path(args.cache_root) / f"dry_run_{now}.json"
        path.write_text(json.dumps(_clean(out), indent=1, default=_jsonable))
        print(f"[dry-run] summary: {path}")
        return 0

    caps = discover_captures(args.snapshot_root)
    minimum, overridden = MIN_SNAPSHOTS, False
    if os.environ.get(TEST_GATE_ENV):
        minimum, overridden = int(os.environ[TEST_GATE_ENV]), True
        if minimum != MIN_SNAPSHOTS:
            print(f"!!! WARNING: development gate OVERRIDDEN to {minimum} snapshots via "
                  f"{TEST_GATE_ENV}. TEST USE ONLY. Reports and trials are stamped "
                  "gate_overridden=true. !!!", file=sys.stderr)
        else:
            overridden = False
    gate = gate_status(caps, minimum)
    gate["gate_overridden"] = overridden
    if not gate["met"]:
        print(f"REFUSED: development gate not met. {gate['longest_consecutive_run']} consecutive "
              f"sidecar-complete snapshots exist ({gate['qualifying_with_sidecar']} with sidecar, "
              f"{gate['complete_snapshots']} complete); {gate['minimum']} required.")
        print(f"ETA: {gate['eta_utc']} ({gate['eta_assumption']}). Use --dry-run to inspect.")
        return 75  # EX_TEMPFAIL: the queue waits 30 min and retries, not counted
    rep = real_run(args, caps, gate, policy)
    kind = ("DEVELOPMENT RUN" if args.target == "direction" and args.horizon == 1
            else f"EXPLORATORY RUN ({args.target}, h{args.horizon})")
    print(f"{kind} (not evidence). Reports: " + ", ".join(rep["_paths"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
