# ruff: noqa: E501
"""q0182b: make the CB9 exclusion-id set acceptable to Gamma without touching any rules-hashed function.

q0182 failed with ``ApiError: gamma markets lookup status 422``: the ``h7_cb4_series`` seal copy names its files ``<successor market_id>__<pred_event_id>``
(1,922 non-integer ids) and Gamma's ``id`` filter accepts integers only (the same cause as CB8 q0164). ``cb9_common.exclusion_keys`` / ``load_exclusion_keys``
and ``cb8_books.seal_copy_ids_audited`` are inside the CB9 rules hashes, so they are NOT edited. This module patches the call sites for one run only
(everything restored on exit) and applies the SAME mapping rule as the CB8 q0164b ruling (docs/research_lab/reviews/CB8_Q0164B_RULING_2026-10-22.md), by
reusing ``cb8_exclusion_fix.normalise_ids`` / ``pred_pairs_of_seal`` / ``ids_sha256``: (1) composite id -> numeric market part; (2) ``pred_prices/`` +
``pred_trades/`` files add their market ids and attach their pred_event_id to that market's event keys; (3) an id that cannot be resolved to an integer
market id REFUSES the run; (4) a write-once sidecar (pins, per-pin counts, sha256 of the final id set) makes a repeat run with a different set refuse,
because ``exclusion_stage`` saves batches by position in ``sorted(ids)``; (5) any failed manifest in the run directory is copied aside write-once.
Ids are normalised BEFORE the subtraction of the pinned CB8 key ids, so composite strings are never mistaken for "new" ids.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
from collections.abc import Iterator
from pathlib import Path

from . import cb6_tail as c6
from . import cb8_books as bk
from . import cb8_common as cm
from . import cb8_exclusion_fix as f8
from . import cb9_common as c9

MAPPING_RULE = (
    "composite id '<successor market_id>__<pred_event_id>' -> numeric market part (applied before subtracting the pinned CB8 key ids); pred_prices/ + "
    "pred_trades/ files '<pred_market_id>__<pred_event_id>' add their market ids and attach their pred_event_id to that market's event keys; unresolvable id "
    "-> refuse; first run saves pins + sha256 of the final id set, repeat runs with a different set refuse (same rule as cb8_exclusion_fix, q0164b ruling)"
)
SIDECAR = "exclusion_fix_provenance.json"
ASIDE = "manifest_q0182_failed.json"
ASIDE_SHA = "manifest_q0182_failed.json.sha256"
NOT_EXTRACTABLE = f8.NOT_EXTRACTABLE


def fix_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def build_seal_plan(seals_dir: Path, used: list[str], ids: set[str]) -> tuple[set[str], dict, dict[str, set[str]]]:
    """``(normalised seal ids incl. pred market ids, counts + per-seal rows, pred event map)`` for the seal copies ``used``. Refuses unresolvable ids."""
    w = bk.c4._cb2w()
    base, counts = f8.normalise_ids(ids)
    per_pin: dict[str, dict] = {}
    pred_map: dict[str, set[str]] = {}
    n_pred_bad = 0
    for name in used:
        path = Path(seals_dir) / name
        pairs, bad = f8.pred_pairs_of_seal(path)
        n_pred_bad += bad
        for mid, eid in pairs:
            pred_map.setdefault(mid, set()).add(eid)
        row = {"kind": "seal", "n_ids": len(w.seal_ids_from_copy(path)), "n_pred_market_ids": len({m for m, _ in pairs}), "n_pred_event_ids": len({e for _, e in pairs})}
        if row["n_ids"] == 0 and row["n_pred_market_ids"] == 0:
            row["label"] = NOT_EXTRACTABLE
        per_pin[name] = row
    final = base | set(pred_map)
    counts = {**counts, "n_unresolvable_dropped": counts["n_unresolvable_dropped"] + n_pred_bad, "n_pred_market_ids": len(pred_map),
              "n_pred_market_ids_new": len(set(pred_map) - base), "n_pred_event_ids": len({e for v in pred_map.values() for e in v}), "n_seal_ids_final": len(final)}
    if counts["n_unresolvable_dropped"] > 0:
        raise cm.Refused(f"{counts['n_unresolvable_dropped']} exclusion ids cannot be resolved to an integer market id; refusing (nothing was dropped silently)")
    return final, {"counts": counts, "per_pin": per_pin}, pred_map


def _sidecar_and_aside(fr, plan: dict) -> None:
    """Write-once copy of the failed manifest (only if one exists and no sidecar yet), then the write-once sidecar, or refuse a repeat run whose set differs."""
    rdir = Path(fr.rdir)
    side, mp = rdir / SIDECAR, rdir / "manifest.json"
    if side.exists():
        prior = json.loads(side.read_text())
        if prior.get("ids_sha256") != plan["ids_sha256"] or prior.get("pins") != plan["pins"]:
            raise cm.Refused("exclusion id set or pin list differs from the first run of this directory (batches are saved by position in sorted(ids)); refusing")
    else:
        aside, aside_sha = rdir / ASIDE, rdir / ASIDE_SHA
        if mp.exists():
            data = mp.read_bytes()
            if aside.exists():
                if aside.read_bytes() != data:
                    raise cm.Refused(f"{aside} already exists with different content; refusing to overwrite the failed-manifest copy")
            else:
                with aside.open("xb") as fh:
                    fh.write(data)
                with aside_sha.open("x") as fh:
                    fh.write(hashlib.sha256(data).hexdigest() + "\n")
        cm.write_once_json(side, {**plan, "note": "q0182 failed (gamma 422 on composite h7_cb4_series ids); q0182b is the fix run", "aside_manifest": ASIDE if mp.exists() else None})
    for f in (side, rdir / ASIDE, rdir / ASIDE_SHA):
        if f.exists():
            fr.record_file(f)


@contextlib.contextmanager
def normalised_exclusion_ids(extra_pins: list[dict] | None = None) -> Iterator[dict]:
    """While active: the seal-copy ids ``cb9_common.exclusion_keys`` reads are normalised (composite -> market part, plus pred market ids); the final new-id
    set handed to ``cb6_tail.exclusion_stage`` must be all-integer (else refuse), is hashed into a write-once sidecar and the manifest params, and
    ``cb6_tail.lookup_keys`` attaches pred_event_ids to the event keys of their markets. ``stats`` (yielded) is filled as the run proceeds."""
    orig_seal, orig_load, orig_stage, orig_lookup = bk.seal_copy_ids_audited, c9.load_exclusion_keys, c6.exclusion_stage, c6.lookup_keys
    stats: dict = {}
    state: dict = {}

    def wrapped_load(keys_path):
        out = orig_load(keys_path)
        state["n_cb8_ids"] = len(out[0])
        return out

    def wrapped_seal(seals_dir, *a, **kw):
        ids, used, skipped, shas = orig_seal(seals_dir, *a, **kw)
        final, sp, pred_map = build_seal_plan(Path(seals_dir), used, ids)
        state.update(seal_plan=sp, pred_map=pred_map, shas=dict(shas))
        stats.update(sp["counts"])
        stats["per_pin"] = sp["per_pin"]
        return final, used, skipped, shas

    def wrapped_stage(fr, ids, should_stop=None):
        bad = [i for i in ids if not str(i).isdigit()]
        if bad:
            raise cm.Refused(f"{len(bad)} exclusion ids are still not integer market ids after normalisation (e.g. {sorted(bad)[0]!r}); refusing")
        sp = state.get("seal_plan") or {"counts": {}, "per_pin": {}}
        plan = {"mapping_rule": MAPPING_RULE, "fix_module_sha256": fix_sha256(), "cb8_fix_module_sha256": f8.fix_sha256(),
                "counts": {**sp["counts"], "n_cb8_ids": state.get("n_cb8_ids"), "n_new_ids_final": len(ids)}, "per_pin": sp["per_pin"], "ids_sha256": f8.ids_sha256(set(ids)),
                "pins": [{"name": n, "kind": "seal", "sha256": s} for n, s in sorted(state.get("shas", {}).items())] + [{"name": p["name"], "kind": "ids", "sha256": p["sha256"]} for p in extra_pins or []],
                "pred_event_map_sha256": hashlib.sha256(json.dumps({k: sorted(v) for k, v in sorted((state.get("pred_map") or {}).items())}).encode()).hexdigest()}
        stats["n_new_ids_final"] = len(ids)
        fr.params["exclusion_fix"] = {k: plan[k] for k in ("mapping_rule", "fix_module_sha256", "cb8_fix_module_sha256", "counts", "ids_sha256", "pred_event_map_sha256")}
        _sidecar_and_aside(fr, plan)
        return orig_stage(fr, ids, should_stop)

    def wrapped_lookup(lim, ids, **kw):
        found, retried = orig_lookup(lim, ids, **kw)
        pred_map = state.get("pred_map") or {}
        for mid in ids:
            evs = pred_map.get(mid)
            if not evs:
                continue
            if mid not in found:
                stats["pred_markets_not_found_this_session"] = stats.get("pred_markets_not_found_this_session", 0) + 1
                continue
            have = [e for e in found[mid]["event_ids"].split(";") if e]
            new = [e for e in sorted(evs) if e not in have]
            if new:
                found[mid] = {**found[mid], "event_ids": ";".join(have + new)}
                stats["pred_event_ids_attached_new_this_session"] = stats.get("pred_event_ids_attached_new_this_session", 0) + len(new)
        return found, retried

    bk.seal_copy_ids_audited, c9.load_exclusion_keys, c6.exclusion_stage, c6.lookup_keys = wrapped_seal, wrapped_load, wrapped_stage, wrapped_lookup
    try:
        yield stats
    finally:
        bk.seal_copy_ids_audited, c9.load_exclusion_keys, c6.exclusion_stage, c6.lookup_keys = orig_seal, orig_load, orig_stage, orig_lookup
