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
  the sidecar and the run report). A NOT_EXTRACTABLE seal does NOT refuse the run: the count is the disclosure, and the unverified share is already bounded by
  the 2% missing-metadata rule on ids.
Known cosmetic residue, disclosed: the write-once sidecar note text of ``cb9_exclusion_fix`` still says "q0182 failed ... q0182b is the fix run".
"""
from __future__ import annotations

import contextlib
from collections.abc import Iterator
from pathlib import Path

from . import cb8_books as bk
from . import cb8_exclusion_fix as f8
from . import cb9_exclusion_fix as fix9
from . import h5_seal

NO_IDS_REASON = "no_market_ids"
NOT_EXTRACTABLE = f8.NOT_EXTRACTABLE


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
    orig_audited, orig_plan = bk.seal_copy_ids_audited, fix9.build_seal_plan

    def audited(seals_dir, *a, **kw):
        ids, used, skipped, shas = orig_audited(seals_dir, *a, **kw)
        used, skipped, shas = amend_seal_listing(Path(seals_dir), used, skipped, shas)
        return ids, used, skipped, shas

    def plan(seals_dir, used, ids):
        final, sp, pred_map = orig_plan(seals_dir, used, ids)
        names = sorted(n for n, r in sp["per_pin"].items() if r.get("label") == NOT_EXTRACTABLE)
        sp["counts"] = {**sp["counts"], "n_not_extractable": len(names), "not_extractable_seals": names}
        return final, sp, pred_map

    bk.seal_copy_ids_audited, fix9.build_seal_plan = audited, plan
    try:
        with fix9.normalised_exclusion_ids(extra_pins) as stats:
            yield stats
    finally:
        bk.seal_copy_ids_audited, fix9.build_seal_plan = orig_audited, orig_plan
