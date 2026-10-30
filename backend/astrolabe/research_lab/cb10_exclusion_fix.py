# ruff: noqa: E501
"""q0201: CB10 exclusion keys with composite-id normalisation and a reachable ``NOT_EXTRACTABLE`` label, without editing any rules-hashed function.

Why a new module. ``cb9_exclusion_fix`` (the q0182b run module, whose sha256 is recorded in the q0182b sidecar) is left byte-identical. It is not rules-hashed
(neither in cb9_rules_v4 nor in cb10_rules_v2), but editing it would change the provenance hash of an already finished run. This module reuses it unchanged.

What ``NOT_EXTRACTABLE`` means. A committed seal copy from which NO market id can be extracted: ``seal_ids_from_copy`` is empty AND the ``pred_prices/`` +
``pred_trades/`` file names give no ``<pred_market_id>__<pred_event_id>`` pair. Such a seal contributes nothing to the exclusion set, so disjointness against
it is NOT verified; that must be visible, never silent.

Why it was unreachable. ``cb8_books.seal_copy_ids_audited`` puts every committed seal copy with no market ids into ``skipped`` (reason ``no_market_ids``),
so ``used`` (the only input of ``build_seal_plan``) never contained one: (a) a seal with ONLY ``pred_*`` files lost its predecessor market ids and event ids
entirely, and (b) a seal with nothing extractable was only a line in ``seal_copies_skipped``, never labelled or counted.

Fix (run-scoped, restored on exit, applied BEFORE ``cb9_exclusion_fix.normalised_exclusion_ids`` so that it sees the amended call):
* ``seal_copy_ids_audited`` is wrapped: every ``no_market_ids`` copy is re-examined with ``cb8_exclusion_fix.pred_pairs_of_seal``. One with pred pairs moves from
  ``skipped`` to ``used`` (+ sha256 pin) and its pred market ids and event ids are handled by the unchanged ``build_seal_plan``. One with nothing moves to
  ``used`` as well (+ sha256 pin) and is labelled ``NOT_EXTRACTABLE`` by the unchanged ``build_seal_plan`` (``n_ids == 0 and n_pred_market_ids == 0``).
  Unparseable and not-committed copies stay in ``skipped`` with their original reason. The ids returned are unchanged.
* ``build_seal_plan`` is wrapped only to add ``n_not_extractable`` and ``not_extractable_seals`` to its counts (manifest ``params.exclusion_fix.counts``,
  the sidecar and the run report). A NOT_EXTRACTABLE seal does NOT refuse the run: the count is the disclosure. The 2% missing-metadata rule does NOT bound it (such a seal adds zero ids to numerator and denominator); the counts are carried into the D1/B1/B2 result records as 'not verified against'.
Known cosmetic residue, disclosed: the write-once sidecar note text of ``cb9_exclusion_fix`` still says "q0182 failed ... q0182b is the fix run".
"""
from __future__ import annotations

import contextlib
import hashlib
import json
from collections.abc import Iterator
from pathlib import Path

from . import cb6_tail as c6
from . import cb8_books as bk
from . import cb8_exclusion_fix as f8
from . import cb9_exclusion_fix as fix9
from . import h5_seal

NO_IDS_REASON = "no_market_ids"
NOT_EXTRACTABLE = f8.NOT_EXTRACTABLE
UNPARSEABLE_PREFIX = "unparseable"
NOT_VERIFIED_NOTE = ("not verified against by id or event key: these seal copies contributed no exclusion id, so the missing-metadata share (2% rule) does not bound "
                     "this risk; disclosure only, no gate (ruling 2026-10-30, MUST 2)")
N_CB8_IDS_NOTE = "n_cb8_ids counts the CB9 q0182b key-file ids in this run (the q0182b key file is CB9's), not CB8's"
MANIFEST_NAMES = ("manifest.json", "exclusion_run10/manifest.json")


def module_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def not_verified_disclosure(keys_path: Path) -> dict:
    """Disclosure-only record for the D1/B1/B2 results (no gate, no statistic touched): NOT_EXTRACTABLE seals and ``unparseable:*`` skipped copies of the q0201 run,
    read from the manifest written next to the CB10 key file. ``available`` is False if no manifest is found."""
    for rel in MANIFEST_NAMES:
        mp = Path(keys_path).parent / rel
        if not mp.exists():
            continue
        try:
            params = json.loads(mp.read_text()).get("params") or {}
        except (OSError, ValueError):
            break
        fx = params.get("exclusion_fix") or {}
        counts = fx.get("counts") or {}
        names = list(counts.get("not_extractable_seals") or [])
        unp = list(fx.get("unparseable_skipped") or [s for s in (params.get("seal_copies_skipped") or []) if str(s.get("reason", "")).startswith(UNPARSEABLE_PREFIX)])
        return {"available": True, "n_not_extractable": int(counts.get("n_not_extractable") or 0), "not_extractable_seals": names,
                "n_unparseable_skipped": len(unp), "unparseable_skipped": unp, "note": NOT_VERIFIED_NOTE}
    return {"available": False, "note": "q0201 manifest not found next to the key file; " + NOT_VERIFIED_NOTE}


def amend_seal_listing(seals_dir: Path, used: list[str], skipped: list[dict], shas: dict[str, str]) -> tuple[list[str], list[dict], dict[str, str]]:
    """Move every ``no_market_ids`` copy into ``used`` (sha256 pinned): pred-only seals contribute their pred ids, the rest are labelled NOT_EXTRACTABLE later."""
    used2, skipped2, shas2 = list(used), [], dict(shas)
    for row in skipped:
        if row.get("reason") != NO_IDS_REASON:
            skipped2.append(row)
            continue
        p = Path(seals_dir) / row["name"]
        used2.append(row["name"])
        shas2[row["name"]] = h5_seal.sha256_file(p)
    return sorted(used2), skipped2, shas2


@contextlib.contextmanager
def cb10_exclusion_ids(extra_pins: list[dict] | None = None) -> Iterator[dict]:
    """``cb9_exclusion_fix.normalised_exclusion_ids`` plus the reachable NOT_EXTRACTABLE handling. Yields the same ``stats`` dict."""
    orig_audited, orig_plan, orig_stage = bk.seal_copy_ids_audited, fix9.build_seal_plan, c6.exclusion_stage
    seen: dict = {"unparseable": []}

    def audited(seals_dir, *a, **kw):
        ids, used, skipped, shas = orig_audited(seals_dir, *a, **kw)
        used, skipped, shas = amend_seal_listing(Path(seals_dir), used, skipped, shas)
        seen["unparseable"] = [s for s in skipped if str(s.get("reason", "")).startswith(UNPARSEABLE_PREFIX)]
        return ids, used, skipped, shas

    def plan(seals_dir, used, ids):
        final, sp, pred_map = orig_plan(seals_dir, used, ids)
        names = sorted(n for n, r in sp["per_pin"].items() if r.get("label") == NOT_EXTRACTABLE)
        sp["counts"] = {**sp["counts"], "n_not_extractable": len(names), "not_extractable_seals": names}
        return final, sp, pred_map

    bk.seal_copy_ids_audited, fix9.build_seal_plan = audited, plan
    try:
        with fix9.normalised_exclusion_ids(extra_pins) as stats:
            inner_stage = c6.exclusion_stage  # fix9's wrapper: it sets fr.params["exclusion_fix"]; add the CB10 disclosure fields after it

            def stage(fr, ids, should_stop=None):
                out = inner_stage(fr, ids, should_stop)
                fx = fr.params.get("exclusion_fix")
                if isinstance(fx, dict):
                    fx["cb10_fix_module_sha256"] = module_sha256()
                    fx["unparseable_skipped"] = list(seen["unparseable"])
                    fx["counts"] = {**fx.get("counts", {}), "n_unparseable_skipped": len(seen["unparseable"])}
                    fx["notes"] = {"n_cb8_ids": N_CB8_IDS_NOTE, "not_extractable": NOT_VERIFIED_NOTE}
                stats["n_unparseable_skipped"] = len(seen["unparseable"])
                return out

            c6.exclusion_stage = stage
            try:
                yield stats
            finally:
                c6.exclusion_stage = inner_stage
    finally:
        bk.seal_copy_ids_audited, fix9.build_seal_plan = orig_audited, orig_plan
        c6.exclusion_stage = orig_stage
