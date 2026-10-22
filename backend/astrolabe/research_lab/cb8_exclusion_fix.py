# ruff: noqa: E501
"""q0164b: make the CB8 exclusion-id set acceptable to Gamma without touching any rules-hashed function.

q0164 failed with ``gamma markets lookup status 422``: the h7_cb4_series seal copy names its files ``<successor market_id>__<pred_event_id>``
(cb4_data.py:2086; 1,922 such ids on 2026-10-22) and Gamma's ``id`` filter accepts integers only, so a single non-integer id rejects the whole 50-id
request. The functions that build and look up the id set (``cb8_updown.exclusion_ids_cb8`` / ``exclusion_keys`` / ``_ids_of_file`` and
``cb6_tail.lookup_keys`` / ``exclusion_stage``) are part of the pinned rules hash (``cb8_rules_v2.json``, 33decb52...), so they are NOT edited. This module
patches them for the duration of one run only (all restored on exit). Science-reviewer ruling: docs/research_lab/reviews/CB8_Q0164B_RULING_2026-10-22.md.

Mapping rule (``MAPPING_RULE``): (1) a composite id is replaced by its numeric market part; (2) the ``pred_prices/`` and ``pred_trades/`` files of a seal copy
(named ``<pred_market_id>__<pred_event_id>``, cb4_data.py:2096) add their market ids to the market set and their ``pred_event_id`` to the event keys of that
market's row; (3) any id that cannot be resolved to an integer market id REFUSES the run (never silently dropped). A provenance sidecar (pin list, sha256 of the
sorted id set, per-pin counts, this file's sha256) is written once in the run directory and listed in the manifest; a repeat run whose id set or pins differ
refuses, because ``exclusion_stage`` saves batches by position in ``sorted(ids)``. q0164's failed manifest is copied aside (write-once) before q0164b writes.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import re
from collections.abc import Iterator
from pathlib import Path

from . import cb6_tail as c6
from . import cb8_common as cm
from . import cb8_updown as u

MAPPING_RULE = (
    "composite id '<successor market_id>__<pred_event_id>' -> numeric market part; pred_prices/ + pred_trades/ files '<pred_market_id>__<pred_event_id>' add "
    "their market ids to the exclusion market set and their pred_event_id to the event keys of that market's row; unresolvable id -> refuse; "
    "first run saves pins + sha256 of sorted id set, repeat runs with a different set refuse"
)
SIDECAR = "exclusion_fix_provenance.json"
ASIDE = "manifest_q0164_failed.json"
ASIDE_SHA = "manifest_q0164_failed.json.sha256"
NOT_EXTRACTABLE = "ids not extractable from seal copy"
_PRED_RE = re.compile(r"^pred_(?:prices|trades)/([^/]+)\.csv\.gz$")


def normalise_ids(ids: set[str]) -> tuple[set[str], dict]:
    """``(ids with composite ids replaced by their numeric market part, counts)``. Plain numeric ids are unchanged."""
    out: set[str] = set()
    n_composite = n_unresolvable = 0
    for x in ids:
        s = str(x)
        if s.isdigit():
            out.add(s)
            continue
        base = s.split("__", 1)[0]
        if "__" in s and base.isdigit():
            n_composite += 1
            out.add(base)
        else:
            n_unresolvable += 1
    return out, {"n_ids_before": len(ids), "n_ids_after": len(out), "n_composite_replaced": n_composite, "n_unresolvable_dropped": n_unresolvable}


def pred_pairs_of_seal(path: Path) -> tuple[set[tuple[str, str]], int]:
    """``({(pred_market_id, pred_event_id)}, n_unparsable)`` from the ``pred_prices/`` / ``pred_trades/`` file names of a seal copy's file table (ids only)."""
    doc = json.loads(Path(path).read_text())
    files = doc.get("files")
    pairs: set[tuple[str, str]] = set()
    bad = 0
    for rel in files if isinstance(files, dict) else ():
        m = _PRED_RE.match(rel)
        if not m:
            continue
        mid, sep, eid = m.group(1).partition("__")
        if sep and mid.isdigit() and eid.isdigit():
            pairs.add((mid, eid))
        else:
            bad += 1
    return pairs, bad


def ids_sha256(ids: set[str]) -> str:
    return hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest()


def fix_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def build_plan(files: dict, pins, orig) -> tuple[set[str], dict, dict[str, set[str]]]:
    """``(final ids, plan, pred event map)``. Raises :class:`cb8_common.Refused` when any id cannot be resolved."""
    raw = set(orig(files, pins))
    base, counts = normalise_ids(raw)
    per_pin: dict[str, dict] = {}
    pred_map: dict[str, set[str]] = {}
    n_pred_bad = 0
    for pin in pins:
        n_raw = len(orig({pin["name"]: files[pin["name"]]}, [pin]))
        row = {"kind": pin["kind"], "n_ids": n_raw, "n_pred_market_ids": 0, "n_pred_event_ids": 0}
        if pin["kind"] == "seal":
            pairs, bad = pred_pairs_of_seal(files[pin["name"]])
            n_pred_bad += bad
            for mid, eid in pairs:
                pred_map.setdefault(mid, set()).add(eid)
            row["n_pred_market_ids"] = len({m for m, _ in pairs})
            row["n_pred_event_ids"] = len({e for _, e in pairs})
        if pin["kind"] == "seal" and n_raw == 0 and row["n_pred_market_ids"] == 0:
            row["label"] = NOT_EXTRACTABLE  # not "covered" and not "disjoint": the seal copy gave no ids at all
        per_pin[pin["name"]] = row
    pred_markets = set(pred_map)
    final = base | pred_markets
    counts = {**counts, "n_unresolvable_dropped": counts["n_unresolvable_dropped"] + n_pred_bad,
              "n_pred_market_ids": len(pred_markets), "n_pred_market_ids_new": len(pred_markets - base),
              "n_pred_event_ids": len({e for v in pred_map.values() for e in v}), "n_ids_final": len(final)}
    plan = {"mapping_rule": MAPPING_RULE, "fix_module_sha256": fix_sha256(), "counts": counts, "per_pin": per_pin, "ids_sha256": ids_sha256(final),
            "pins": [{k: p[k] for k in ("name", "kind", "sha256")} for p in pins],
            "pred_event_map_sha256": hashlib.sha256(json.dumps({k: sorted(v) for k, v in sorted(pred_map.items())}).encode()).hexdigest()}
    if counts["n_unresolvable_dropped"] > 0:
        raise cm.Refused(f"{counts['n_unresolvable_dropped']} exclusion ids cannot be resolved to an integer market id; refusing (nothing was dropped silently)")
    return final, plan, pred_map


def _sidecar_and_aside(fr, plan: dict) -> None:
    """Write-once copy of q0164's failed manifest (first q0164b run only), then the write-once provenance sidecar, or refuse a repeat run whose set differs."""
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
                    raise cm.Refused(f"{aside} already exists with different content; refusing to overwrite q0164's failed-manifest copy")
            else:
                with aside.open("xb") as fh:
                    fh.write(data)
                with aside_sha.open("x") as fh:
                    fh.write(hashlib.sha256(data).hexdigest() + "\n")
        cm.write_once_json(side, {**plan, "note": "q0164 failed (gamma 422), exited 0 and was wrongly marked done; q0164b is the fix run", "aside_manifest": ASIDE if mp.exists() else None})
    for f in (side, rdir / ASIDE, rdir / ASIDE_SHA):
        if f.exists():
            fr.record_file(f)


@contextlib.contextmanager
def normalised_exclusion_ids() -> Iterator[dict]:
    """While active: ``exclusion_ids_cb8`` returns the resolved set (composite -> market part, plus pred_* market ids), ``cb8_common.open_run`` writes the
    provenance sidecar / failed-manifest copy and adds the plan to the manifest params, and ``cb6_tail.lookup_keys`` attaches the pred_event_ids to the event
    keys of their markets. ``stats`` (yielded) is filled as the run proceeds. All originals are restored on exit."""
    orig_ids, orig_open, orig_lookup = u.exclusion_ids_cb8, cm.open_run, c6.lookup_keys
    stats: dict = {}
    state: dict = {}

    def wrapped_ids(files, pins):
        final, plan, pred_map = build_plan(files, pins, orig_ids)
        state.update(plan=plan, pred_map=pred_map)
        stats.update(plan["counts"])
        stats["per_pin"] = plan["per_pin"]
        return final

    def wrapped_open(*a, **kw):
        plan = state.get("plan")
        if plan is not None:
            kw["params"] = {**kw["params"], "exclusion_fix": {k: plan[k] for k in ("mapping_rule", "fix_module_sha256", "counts", "ids_sha256", "pred_event_map_sha256")}}
        fr = orig_open(*a, **kw)
        if plan is not None:
            _sidecar_and_aside(fr, plan)
        return fr

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

    u.exclusion_ids_cb8, cm.open_run, c6.lookup_keys = wrapped_ids, wrapped_open, wrapped_lookup
    try:
        yield stats
    finally:
        u.exclusion_ids_cb8, cm.open_run, c6.lookup_keys = orig_ids, orig_open, orig_lookup
