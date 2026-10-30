# ruff: noqa: E501
"""M2-J2 (``MEASUREMENT_M2_CH264.md`` 9.3): the window-close unit manifest and the follow-up manifest, plus the state-chain audit (void case 11.2(a)).

* ``close_units`` (at or after ``END_UTC + 6 h``): ``manifest.json`` with the sha256 of every unit, no_favourite and status file, slot coverage over the
  window's 252 slots and the missing-capture list. Refuses unless every window slot is decided and the sha256 chain is unbroken. Write-once.
* ``close_followup`` (at or after ``READOUT_UTC``): ``followup_manifest.json`` with the sha256 of every follow-up file and slot coverage after the window,
  committed before the analysis reads any of them. It hashes bytes only and never opens a follow-up file as data; each file's hash is cross-checked
  against the sha256 recorded in the status of its capture. Refuses while a slot of the follow-up span is still undecided (its on-time set is not final
  before grid + 6 h). Write-once.
Research tooling; no network, no resolution read.
"""

from __future__ import annotations

import gzip
import json
import time
from collections import Counter
from pathlib import Path

from . import m2_spec as sp

SIDE_KINDS = ("late_capture_ignored", "duplicate_slot_capture_ignored", "off_grid_capture_ignored")


def _dumps(o) -> str:
    return json.dumps(o, sort_keys=True, separators=(",", ":"))


def write_once(path: Path, data: bytes) -> str:
    """Create ``path`` exclusively. An existing file with identical bytes is accepted (idempotent re-run); anything else is refused."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() == data:
            return "present_identical"
        raise sp.M2Refusal(f"refuses to overwrite {path}")
    with open(path, "xb") as fh:
        fh.write(data)
    return "written"


def load_statuses(store: Path) -> tuple[list[dict], dict]:
    """(chain statuses ordered by slot, {side kind: [records]}). Chain statuses are the ``processed`` and ``missing_capture`` kinds."""
    chain: list = []
    side: dict = {k: [] for k in SIDE_KINDS}
    for p in sorted((Path(store) / "status").glob("*.json")):
        d = json.loads(p.read_text())
        if d.get("kind") in side:
            side[d["kind"]].append(d)
        elif d.get("kind") in ("processed", "missing_capture"):
            chain.append(d)
    return sorted(chain, key=lambda d: d["slot"]), side


def audit_chain(store: Path, spec: dict = sp.SPEC) -> dict:
    """Void case 11.2(a): slots contiguous from the first chain status; each status's state sha before equal to the previous one's after (the first is
    ``none``); each status names the capture the chain folded before it."""
    chain, side = load_statuses(store)
    breaks: list = []
    prev_after = "none"
    prev_slot = None
    prev_id = None
    for d in chain:
        if prev_slot is not None and d["slot"] != prev_slot + 1:
            breaks.append(f"slot_gap_before_{d['slot']}")
        if d["state_sha256_before"] != prev_after:
            breaks.append(f"sha_break_at_{d['slot']}")
        if d.get("last_capture_id_before") != prev_id:
            breaks.append(f"last_capture_mismatch_at_{d['slot']}")
        prev_after, prev_slot = d["state_sha256_after"], d["slot"]
        prev_id = d["id"] if d["kind"] == "processed" else None
    return {"ok": not breaks, "breaks": breaks, "decided_slots": len(chain), "first_slot": chain[0]["slot"] if chain else None, "last_slot": prev_slot,
            "late_capture_ignored": len(side["late_capture_ignored"]), "duplicate_slot_capture_ignored": len(side["duplicate_slot_capture_ignored"]),
            "off_grid_capture_ignored": len(side["off_grid_capture_ignored"]),
            "missing_slots": [d["slot"] for d in chain if d["kind"] == "missing_capture"]}


def _hash_dir(store: Path, subs: tuple[str, ...]) -> dict:
    return {str(p.relative_to(store)): sp.sha256_file(p) for sub in subs for p in sorted((store / sub).glob("*")) if p.is_file()}


def close_units(store: Path, spec: dict = sp.SPEC, now: float | None = None, paths: dict | None = None, design: Path | None = None, pins: dict | None = None) -> dict:
    """J2 at ``END_UTC + 6 h``: the unit manifest. Write-once; the unit set is closed after it."""
    sp.check_pins(spec, paths, design)
    sp.check_run_pins(pins, spec)
    now = time.time() if now is None else now
    if now < sp.ts(spec, "end_utc") + spec["close_after_end_s"]:
        raise sp.M2Refusal("window close refuses before END_UTC + 6 h")
    store = Path(store)
    audit = audit_chain(store, spec)
    wslots = sp.window_slots(spec)
    decided = {d["slot"] for d in load_statuses(store)[0]}
    undecided = [s for s in wslots if s not in decided]
    if undecided or not audit["ok"]:
        raise sp.M2Refusal(f"window close refuses: {len(undecided)} of {len(wslots)} window slots undecided, chain ok {audit['ok']} {audit['breaks'][:3]}")
    files = _hash_dir(store, ("units", "nofav", "status"))
    n_units = n_nofav = 0
    for p in sorted((store / "units").glob("*.jsonl.gz")):
        with gzip.open(p, "rt") as fh:
            n_units += sum(1 for _ in fh)
    for p in sorted((store / "nofav").glob("*.jsonl.gz")):
        with gzip.open(p, "rt") as fh:
            n_nofav += sum(1 for _ in fh)
    missing_w = [s for s in audit["missing_slots"] if s in set(wslots)]
    man = {"kind": "M2-J2 window manifest", "spec_sha": sp.spec_sha(spec), "code_sha": sp.code_sha(), "role": sp.ROLE, "window_slots": len(wslots),
           "processed_slots": len(wslots) - len(missing_w), "slot_coverage": (len(wslots) - len(missing_w)) / len(wslots), "missing_slots": missing_w,
           "missing_slots_utc": [sp.iso(sp.slot_time(spec, s)) for s in missing_w], "missing_lookback_slots": sum(1 for s in audit["missing_slots"] if s < wslots[0]),
           "late_capture_ignored": audit["late_capture_ignored"], "duplicate_slot_capture_ignored": audit["duplicate_slot_capture_ignored"],
           "off_grid_capture_ignored": audit["off_grid_capture_ignored"], "units": n_units, "no_favourite_lines": n_nofav, "chain": audit, "files": files}
    p = store / "manifest.json"
    write_once(p, _dumps(man).encode())
    return man | {"manifest_sha256": sp.sha256_file(p)}


def close_followup(store: Path, spec: dict = sp.SPEC, now: float | None = None, paths: dict | None = None, design: Path | None = None, pins: dict | None = None) -> dict:
    """J2 at ``READOUT_UTC``: the follow-up manifest (sha256 of every follow-up file, slot coverage after the window). Needs the unit manifest. Write-once."""
    sp.check_pins(spec, paths, design)
    sp.check_run_pins(pins, spec)
    now = time.time() if now is None else now
    if now < sp.ts(spec, "readout_utc"):
        raise sp.M2Refusal("follow-up close refuses before READOUT_UTC")
    store = Path(store)
    if not (store / "manifest.json").exists():
        raise sp.M2Refusal("follow-up close refuses: no unit manifest (J2 window close has not run)")
    chain, _side = load_statuses(store)
    by_slot = {d["slot"]: d for d in chain}
    fslots = sp.followup_slots(spec)
    undecided = [s for s in fslots if s not in by_slot]
    if undecided:
        raise sp.M2Refusal(f"follow-up close refuses: {len(undecided)} of {len(fslots)} follow-up slots are undecided (first {sp.iso(sp.slot_time(spec, undecided[0]))}); run J1 again")
    audit = audit_chain(store, spec)
    if not audit["ok"]:
        raise sp.M2Refusal(f"follow-up close refuses: chain broken {audit['breaks'][:3]}")
    files = _hash_dir(store, ("followup",))
    recorded = {d["id"]: d.get("followup") for d in chain if d["kind"] == "processed" and d.get("followup")}
    mism = [n for n, h in files.items() if recorded.get(Path(n).name.removesuffix(".jsonl.gz")) is None or recorded[Path(n).name.removesuffix(".jsonl.gz")]["sha256"] != h]
    if mism:
        raise sp.M2Refusal(f"follow-up close refuses: follow-up files differ from the sha256 in their status files: {mism[:3]}")
    missing_f = [s for s in fslots if by_slot[s]["kind"] == "missing_capture"]
    counts = Counter(d["kind"] for d in chain)
    man = {"kind": "M2-J2 follow-up manifest", "spec_sha": sp.spec_sha(spec), "code_sha": sp.code_sha(), "role": sp.ROLE, "followup_slots": len(fslots),
           "processed_slots": len(fslots) - len(missing_f), "slot_coverage": (len(fslots) - len(missing_f)) / len(fslots) if fslots else None,
           "missing_slots": missing_f, "files": files, "status_kinds": dict(counts),
           "status_line_counts_recorded": {k: v["lines"] for k, v in sorted(recorded.items())}}
    p = store / "followup_manifest.json"
    write_once(p, _dumps(man).encode())
    return man | {"manifest_sha256": sp.sha256_file(p)}
