"""E009/E010 outage gap fill, rule ``gapfill-v1`` (docs/research_lab/E009_E010_GAPFILL_RULE.md).

Builds a NEW analysis root from the canonical live stream plus the validation copy, for the
documented 2026-10-14 outage only. Both sources are read-only; canonical lines are copied byte for
byte; lines taken from the copy carry ``"source": "validation_copy"``. Run once, at analysis time,
immediately before the registered ``--analyze`` / ``--analyze-e010`` (primary on the merged root,
sensitivity on the canonical root). No statistic is computed here; the manifest holds counts by
rule branch, sha256s and line counts only.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

RULE_ID = "gapfill-v1"
RULE_DOC = (Path(__file__).resolve().parents[3] / "docs" / "research_lab"
            / "E009_E010_GAPFILL_RULE.md")
SOURCE_TAG = "validation_copy"
# open interval: the canonical stream has cycles exactly at both endpoints
W_START_UTC = "2026-10-14T00:02:00Z"
W_END_UTC = "2026-10-14T10:44:00Z"

_E009_FIELDS = ("t", "pid", "ev", "role", "pm", "pb", "pa", "side", "trade", "fee", "cost", "f",
                "y0", "y1")
STREAMS = {
    "E009": {"pred": "predictions.jsonl", "out": "outcomes.jsonl", "horizons": (10, 20, 60),
             "grid": 600, "fields": _E009_FIELDS},
    "E010": {"pred": "predictions_e010.jsonl", "out": "outcomes_e010.jsonl",
             "horizons": (60, 360), "grid": 3600, "fields": (*_E009_FIELDS, "yg")},
}
REFUSALS = ("canonical_evaluated", "no_copy_outcome", "no_copy_prediction", "prediction_differs")


def _ep(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def _raw_lines(path: Path) -> Iterator[tuple[str, dict]]:
    """(raw line including newline, parsed) for every non-empty line; a missing file is empty."""
    if not path.exists():
        return
    with path.open() as f:
        for ln in f:
            if ln.strip():
                yield (ln if ln.endswith("\n") else ln + "\n"), json.loads(ln)


def file_digest(path: Path) -> dict:
    h, n = hashlib.sha256(), 0
    if not path.exists():
        return {"path": str(path), "exists": False}
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
            n += chunk.count(b"\n")
    return {"path": str(path), "exists": True, "sha256": h.hexdigest(), "lines": n}


def _inside(path: Path, root: Path) -> bool:
    path, root = path.resolve(), root.resolve()
    return path == root or root in path.parents


def merge_stream(canonical: Path, copy: Path, out: Path, stream: str,
                 w_start: float, w_end: float) -> dict:
    cfg = STREAMS[stream]
    hmax = max(cfg["horizons"]) * 60

    def in_w(x: float) -> bool:
        return w_start < x < w_end

    # copy: predictions in W or able to straddle into W, and their outcome lines (first kept)
    copy_pred: dict[str, dict] = {}
    for _, r in _raw_lines(copy / cfg["pred"]):
        if (in_w(r["t"]) or w_start - hmax < r["t"] <= w_start) and r["id"] not in copy_pred:
            copy_pred[r["id"]] = r
    copy_out: dict[tuple[str, int], dict] = {}
    for _, o in _raw_lines(copy / cfg["out"]):
        k = (o["id"], int(o["h"]))
        if (in_w(o["t0"]) or w_start - hmax < o["t0"] <= w_start) and k not in copy_out:
            copy_out[k] = o
    # canonical predictions: verbatim; remember ids in W and the straddling candidates
    canon_ids_w: set[str] = set()
    straddle: dict[str, dict] = {}
    n_pred_canon = 0
    with (out / cfg["pred"]).open("w") as fp:
        for raw, r in _raw_lines(canonical / cfg["pred"]):
            fp.write(raw)
            n_pred_canon += 1
            if in_w(r["t"]):
                canon_ids_w.add(r["id"])
            elif r["t"] <= w_start and r["t"] % cfg["grid"] == 0 and r["id"] not in straddle:
                if any(in_w(r["t"] + h * 60) for h in cfg["horizons"]):
                    straddle[r["id"]] = r
        # R2: copy predictions with origin in W and no canonical id
        added = sorted((r for i, r in copy_pred.items() if in_w(r["t"]) and i not in canon_ids_w),
                       key=lambda r: (r["t"], r["id"]))
        for r in added:
            fp.write(json.dumps({**r, "source": SOURCE_TAG}) + "\n")
    added_ids = {r["id"] for r in added}
    # canonical status of straddling records (first line, as analyze's dedup reads it)
    keys = {(i, h) for i, r in straddle.items() for h in cfg["horizons"] if in_w(r["t"] + h * 60)}
    canon_status: dict[tuple[str, int], str] = {}
    for _, o in _raw_lines(canonical / cfg["out"]):
        k = (o["id"], int(o["h"]))
        if k in keys and k not in canon_status:
            canon_status[k] = o.get("status")
    subst: dict[tuple[str, int], dict] = {}
    refused = {h: dict.fromkeys(REFUSALS, 0) for h in cfg["horizons"]}
    for k in sorted(keys):
        i, h = k
        if canon_status.get(k) == "evaluated":
            refused[h]["canonical_evaluated"] += 1
        elif k not in copy_out:
            refused[h]["no_copy_outcome"] += 1
        elif i not in copy_pred:
            refused[h]["no_copy_prediction"] += 1
        elif any(copy_pred[i].get(f) != straddle[i].get(f) for f in cfg["fields"]):
            refused[h]["prediction_differs"] += 1
        else:
            subst[k] = copy_out[k]
    # outcomes: canonical verbatim except records replaced under R4; then copy lines (R4, R3)
    dropped = 0
    with (out / cfg["out"]).open("w") as fo:
        for raw, o in _raw_lines(canonical / cfg["out"]):
            if (o["id"], int(o["h"])) in subst:
                dropped += 1
                continue
            fo.write(raw)
        r3 = sorted((k for k in copy_out if k[0] in added_ids),
                    key=lambda k: (copy_pred[k[0]]["t"], k[0], k[1]))
        for k in sorted(subst, key=lambda k: (straddle[k[0]]["t"], k[0], k[1])):
            fo.write(json.dumps({**subst[k], "source": SOURCE_TAG}) + "\n")
        for k in r3:
            fo.write(json.dumps({**copy_out[k], "source": SOURCE_TAG}) + "\n")
    hs = cfg["horizons"]
    return {
        "canonical_prediction_lines": n_pred_canon,
        "canonical_predictions_in_window": len(canon_ids_w),
        "r2_predictions_added": len(added),
        "r3_outcomes_added": {h: sum(1 for k in r3 if k[1] == h) for h in hs},
        "r4_candidates": {h: sum(1 for k in keys if k[1] == h) for h in hs},
        "r4_substituted": {h: sum(1 for k in subst if k[1] == h) for h in hs},
        "r4_refused": refused,
        "canonical_lines_dropped_r4": dropped,
    }


def merge(canonical: Path, copy: Path, out: Path, *, code_commit: str = "",
          w_start_utc: str = W_START_UTC, w_end_utc: str = W_END_UTC) -> dict:
    canonical, copy, out = Path(canonical), Path(copy), Path(out)
    if out.exists():
        raise FileExistsError(f"{out} exists; the merged root must be new")
    if _inside(out, canonical) or _inside(out, copy):
        raise ValueError("the merged root may not be, or lie inside, a source root")
    out.mkdir(parents=True)
    inputs = {f"{side}/{cfg[k]}": file_digest(root / cfg[k])
              for side, root in (("canonical", canonical), ("copy", copy))
              for cfg in STREAMS.values() for k in ("pred", "out")}
    counts = {s: merge_stream(canonical, copy, out, s, _ep(w_start_utc), _ep(w_end_utc))
              for s in STREAMS}
    # sources must be unchanged by the merge (read-only check)
    after = {f"{side}/{cfg[k]}": file_digest(root / cfg[k])
             for side, root in (("canonical", canonical), ("copy", copy))
             for cfg in STREAMS.values() for k in ("pred", "out")}
    unchanged = after == inputs
    manifest = {
        "rule_id": RULE_ID,
        "rule_doc_sha256": file_digest(RULE_DOC).get("sha256"),
        "code_commit": code_commit,
        "window_open_interval": [w_start_utc, w_end_utc],
        "merged_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": inputs,
        "inputs_unchanged_after_merge": unchanged,
        "outputs": {cfg[k]: file_digest(out / cfg[k]) for cfg in STREAMS.values()
                    for k in ("pred", "out")},
        "counts": counts,
    }
    (out / "MERGE_MANIFEST.json").write_text(json.dumps(manifest, indent=1, default=str))
    if not unchanged:
        raise RuntimeError("a source file changed during the merge; do not use this root")
    return manifest
