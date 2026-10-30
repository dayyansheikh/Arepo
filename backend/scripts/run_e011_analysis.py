"""E011 one-shot analysis runner (queue wrapper). New file; the registered code is untouched.

E011 (surprise-move detector) is analysed ONCE, after 2026-11-11T13:00:00Z, by the registered
``scripts/run_surprise_snapshot.py analyze`` (-> ``surprise_snapshot.analyze``). That function reads
exactly two append-only files, ``<root>/alerts.jsonl`` and ``<root>/outcomes.jsonl``, with ``root``
defaulting to the live surprise_live folder, which the collector keeps appending to. The CLI has no
root argument. This wrapper therefore:

  freeze   --run-dir D --src S
      Refuses (exit 75) before 2026-11-11T13:00Z. Enforces the sha256 pins of the 7 files named by
      the code-version ruling (exit 2 on any mismatch). Byte-copies
      S/{alerts,outcomes,passes}.jsonl, each cut at its last newline (a half-written tail is
      dropped), into D/inputs/ (built in a temp
      folder and renamed, so a failed freeze leaves no D/inputs). Writes D/inputs/PRE_RUN.json: the
      outcome-blind counts (line counts; passes.jsonl status breakdown and non-ok passes;
      window alert lines whose fee_category is "unknown", read from alert lines only) and
      FREEZE_MANIFEST.json
      (sha256, sizes, lines, source mtimes, last pass time). No outcome line is parsed.
  analyze  --run-dir D
      Refuses before 13:00Z, re-checks pins, re-hashes D/inputs against the manifest, then runs the
      registered ``run_surprise_snapshot.py analyze`` UNCHANGED with its registered default
      arguments (--start 2026-10-13T14:00:00Z --end 2026-11-10T00:00:00Z) inside a child
      interpreter in which
      ``surprise_snapshot.analyze`` is bound to ``root=D/inputs`` via functools.partial before the
      registered ``main()`` runs. The registered files are not edited; the only difference from the
      live CLI is the root of the two input files, which are byte copies cut at a recorded point.
      stdout is saved byte for byte to D/results/e011_analysis.json (written once). Secondaries
      (c), (e), (f), (g) are recorded as "not produced" and never filled.

Failure records are written once per attempt (never overwritten). A time refusal exits 75 (queue:
"not now"); declared refusals exit 2; a child's own 75 is mapped to 1.
See docs/research_lab/E011_ANALYSIS_RUNBOOK_2026-10-30.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
TEMPFAIL = 75
REFUSED = 2

# registered fixed window (surprise_snapshot.REGISTERED_UTC / END_UTC, ledger E011); analysis time
REGISTERED_UTC = "2026-10-13T14:00:00Z"
END_UTC = "2026-11-10T00:00:00Z"
NOT_BEFORE = "2026-11-11T13:00:00Z"
ROLE = "prospective_confirmation"
INPUT_FILES = ("alerts.jsonl", "outcomes.jsonl")  # the two files analyze() reads
RECORD_FILES = ("passes.jsonl",)  # frozen for the record only; analyze() does not read it
ALLOWED_DIRTY = frozenset({"docs/research_lab/trials.jsonl"})

# sha256 pins (reviews/E011_CODE_VERSION_RULING_2026-10-30.md, PIN_HEAD_WITH_DEVIATION_NOTE).
# Every step REFUSES (exit 2, never 75) on a mismatch or a missing file.
REGISTERED_PINS = {
    "backend/astrolabe/research_lab/surprise_snapshot.py":
        "413107af882152029da4db8c68bf011ca160382dc3298f55d5f44f3922dda4b1",
    "backend/scripts/run_surprise_snapshot.py":
        "6df4fb39af804a1f414ac5298d6d79458c005766b473bade635f7055115bcf9e",
    "backend/astrolabe/research_lab/detector_eval.py":
        "7cc2032706fed6a05d4f3edf00beabfeb5bc72eced9d8097d378aaa5e3880f24",
    "backend/astrolabe/research_lab/surprise_moves.py":
        "93183416a6bb3ab49ce1d653ac58a7f850deedf9dd2a7c4c459088c3da4d76ca",
    "backend/astrolabe/research_lab/detector_specs/FROZEN_SURPRISE_SNAPSHOT.json":
        "5c095deba482c3155e361484e7d13454644ad949556ff922d43ccd3376e0b6f2",
    "backend/astrolabe/research_lab/detector_specs/sm_learned_v2.json":
        "af9b9da2ad7e3644bf625a1b51edd4390cdddd34721ce169db99844ca718825d",
    "backend/astrolabe/research_lab/ml_explain.py":
        "ac00eac8739433036dab8e317199d5f6cc93cdedb53423fbf27617e24ae25399",
}
# imported by the registered path; recorded, not enforced (ruling (e): outcome-neutral changes)
IMPORTED_MODULES = (
    "backend/astrolabe/research_lab/forecast.py",
    "backend/astrolabe/research_lab/history_backfill.py",
    "backend/astrolabe/research_lab/compare.py",
    "backend/astrolabe/research_lab/provenance.py",
    "backend/astrolabe/research_lab/wallet_sidecar.py",
)
SECONDARIES_NOT_PRODUCED = {
    "c_2h_label_excess": "not produced",
    "e_sports_vs_non_sports_split": "not produced (analyze() outputs by_fee_category only)",
    "f_control_match_composition": "not produced",
    "g_passes_missed_and_request_timing_stats": "not produced (data exist in passes.jsonl; "
                                                "no statistic computed)",
    "note": "registered secondaries that analyze() does not output are reported 'not produced', "
            "never filled in (readiness 2026-10-19 S1; code-version ruling defect 4)",
}

# Child: run the REGISTERED CLI main() unchanged; only analyze()'s root keyword is bound.
CHILD_BOOT = """
import functools, importlib.util, sys
from pathlib import Path
backend, script, root = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, backend)
from astrolabe.research_lab import surprise_snapshot as ss
ss.analyze = functools.partial(ss.analyze, root=Path(root))
spec = importlib.util.spec_from_file_location("run_surprise_snapshot", script)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.main(["analyze"])
"""


class Refusal(Exception):
    def __init__(self, msg: str, code: int = REFUSED):
        super().__init__(msg)
        self.code = code


def _ep(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def _utc(t: float | None = None) -> str:
    return datetime.fromtimestamp(time.time() if t is None else t, UTC).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def _stamp(t: float | None = None) -> str:
    return datetime.fromtimestamp(time.time() if t is None else t, UTC).strftime("%Y%m%dT%H%M%SZ")


def digest(path: Path) -> dict:
    h, n, size = hashlib.sha256(), 0, 0
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
            n += chunk.count(b"\n")
            size += len(chunk)
    return {"sha256": h.hexdigest(), "lines": n, "bytes": size}


def git_state(cwd: Path = BACKEND) -> tuple[str, list[str]]:
    def run(*a):
        return subprocess.run(["git", *a], capture_output=True, text=True, cwd=cwd).stdout

    head = run("rev-parse", "HEAD").strip()
    dirty = sorted(ln[3:].strip() for ln in run("status", "--porcelain",
                                                 "--untracked-files=no").splitlines() if ln.strip())
    return head, dirty


def check_tree(state: tuple[str, list[str]]) -> dict:
    head, dirty = state
    if not head:
        raise Refusal("cannot read git HEAD (run from the repository)")
    extra = sorted(set(dirty) - ALLOWED_DIRTY)
    if extra:
        raise Refusal(f"tracked files modified beyond {sorted(ALLOWED_DIRTY)}: {extra}")
    code, bad = {}, {}
    for p, pin in REGISTERED_PINS.items():
        f = REPO / p
        got = digest(f)["sha256"] if f.is_file() else None
        code[p] = got
        if got != pin:
            bad[p] = {"found": got, "pinned": pin}
    if bad:
        raise Refusal(f"registered code differs from its pinned sha256: {bad}")
    mods = {p: digest(REPO / p)["sha256"] if (REPO / p).is_file() else None
            for p in IMPORTED_MODULES}
    return {"git_head": head, "dirty_tracked": dirty, "registered_code_sha256": code,
            "imported_modules_sha256": mods}


def _child_code(rc: int) -> int:
    """A child's exit 75 would be read by the queue as 'not now, retry': report it as 1."""
    return 1 if rc == TEMPFAIL else (rc or 1)


def _write_unique(dirpath: Path, stem: str, text: str) -> Path:
    dirpath.mkdir(parents=True, exist_ok=True)
    base, n = f"{stem}-{_stamp()}", 0
    while True:
        p = dirpath / (f"{base}.json" if n == 0 else f"{base}-{n}.json")
        try:
            with p.open("x") as f:
                f.write(text)
            return p
        except FileExistsError:
            n += 1


def _not_before(now: float | None) -> None:
    now = time.time() if now is None else now
    if now < _ep(NOT_BEFORE):
        raise Refusal(f"not before {NOT_BEFORE} (now {_utc(now)})", TEMPFAIL)


def _inside(path: Path, root: Path) -> bool:
    path, root = path.resolve(), root.resolve()
    return path == root or root in path.parents


def _copy_complete_lines(src: Path, dst: Path) -> dict:
    """Copy the first st_size bytes of src, then cut dst after its last newline."""
    size = src.stat().st_size
    with src.open("rb") as fi, dst.open("wb") as fo:
        left = size
        while left > 0:
            chunk = fi.read(min(1 << 20, left))
            if not chunk:
                break
            fo.write(chunk)
            left -= len(chunk)
    copied = size - left
    with dst.open("r+b") as f:
        pos, cut = copied, 0
        while pos > 0:
            step = min(1 << 16, pos)
            f.seek(pos - step)
            i = f.read(step).rfind(b"\n")
            if i >= 0:
                cut = pos - step + i + 1
                break
            pos -= step
        f.truncate(cut)
    st = src.stat()
    return {"source_path": str(src.resolve()), "source_bytes_at_copy": size,
            "source_mtime_utc": _utc(st.st_mtime), "partial_tail_bytes_dropped": copied - cut}


def _lines(path: Path):
    with path.open(encoding="utf-8") as fh:
        yield from fh


def prerun_counts(inputs: Path) -> dict:
    """Outcome-blind counts from the frozen copies. outcomes.jsonl is only line-counted; alert
    lines are read for type / capture_t / evidence_role / fee_category only; passes.jsonl for
    status / written_utc only. No label, hit or move value is read."""
    t0, t1 = _ep(REGISTERED_UTC), _ep(END_UTC)
    status: dict[str, int] = {}
    bad_pass, last_pass = 0, None
    for ln in _lines(inputs / "passes.jsonl"):
        try:
            d = json.loads(ln)
        except ValueError:
            bad_pass += 1
            continue
        s = str(d.get("status"))
        status[s] = status.get(s, 0) + 1
        w = d.get("written_utc")
        if isinstance(w, str) and (last_pass is None or w > last_pass):
            last_pass = w
    n_alert = n_win = n_unknown = n_ctrl = bad_alert = 0
    for ln in _lines(inputs / "alerts.jsonl"):
        try:
            d = json.loads(ln)
        except ValueError:
            bad_alert += 1
            continue
        if d.get("type") == "control":
            n_ctrl += 1
        if d.get("type") != "alert":
            continue
        n_alert += 1
        ct = float(d.get("capture_t", d["t"]))
        if t0 <= ct < t1 and d.get("evidence_role") == ROLE:
            n_win += 1
            if d.get("fee_category") == "unknown":
                n_unknown += 1
    return {
        "passes": {"total": sum(status.values()), "by_status": status,
                   "non_ok": sum(v for k, v in status.items() if k != "ok"),
                   "unparsable_lines": bad_pass, "last_written_utc": last_pass},
        "alerts_jsonl": {"alert_lines": n_alert, "control_lines": n_ctrl,
                         "window_alert_lines": n_win,
                         "window_alert_lines_fee_category_unknown": n_unknown,
                         "unparsable_lines": bad_alert},
        "outcomes_jsonl": {"lines": digest(inputs / "outcomes.jsonl")["lines"],
                           "note": "newline count only; no outcome line parsed"},
        "window": [REGISTERED_UTC, END_UTC], "window_filter": "capture_t, role " + ROLE}


def freeze(run_dir: Path, src: Path, *, now: float | None = None,
           state: tuple[str, list[str]] | None = None) -> dict:
    _not_before(now)
    tree = check_tree(state or git_state())
    run_dir, src = Path(run_dir), Path(src)
    if _inside(run_dir, src):
        raise Refusal("the run folder may not lie inside the source folder")
    inputs = run_dir / "inputs"
    if inputs.exists():
        raise Refusal(f"{inputs} exists; the freeze runs once (move a failed one aside, never "
                      "remove it)")
    missing = [f for f in INPUT_FILES + RECORD_FILES if not (src / f).is_file()]
    if missing:
        raise Refusal(f"source {src} lacks {missing}")
    run_dir.mkdir(parents=True, exist_ok=True)
    tmp = run_dir / f"inputs.partial-{_stamp()}"
    tmp.mkdir()
    files = {}
    for f in INPUT_FILES + RECORD_FILES:  # alerts first, then outcomes, then passes
        info = _copy_complete_lines(src / f, tmp / f)
        files[f] = {**digest(tmp / f), **info}
    pre = prerun_counts(tmp)
    rec_text = json.dumps({"step": "pre_run_counts", "made_utc": _utc(now), **pre}, indent=1)
    (tmp / "PRE_RUN.json").write_text(rec_text)
    man = {"step": "freeze", "frozen_utc": _utc(now), **tree, "files": files,
           "pre_run_sha256": hashlib.sha256(rec_text.encode()).hexdigest(),
           "analyze_reads": list(INPUT_FILES),
           "note": "byte copies cut at the last newline; analyze() reads only alerts.jsonl and "
                   "outcomes.jsonl; passes.jsonl is frozen for the record"}
    (tmp / "FREEZE_MANIFEST.json").write_text(json.dumps(man, indent=1))
    tmp.rename(inputs)
    return man


def analyze(run_dir: Path, *, now: float | None = None,
            state: tuple[str, list[str]] | None = None) -> dict:
    _not_before(now)
    run_dir = Path(run_dir)
    tree = check_tree(state or git_state())
    inputs = run_dir / "inputs"
    mp = inputs / "FREEZE_MANIFEST.json"
    if not mp.is_file() or not (inputs / "PRE_RUN.json").is_file():
        raise Refusal(f"{mp} or PRE_RUN.json missing: run freeze first")
    fm = json.loads(mp.read_text())
    got = {f: digest(inputs / f)["sha256"] for f in INPUT_FILES + RECORD_FILES}
    bad = {f: (got[f], fm["files"][f]["sha256"]) for f in got if got[f] != fm["files"][f]["sha256"]}
    if bad:
        raise Refusal(f"frozen inputs differ from their manifest: {bad}")
    res_dir = run_dir / "results"
    out, side = res_dir / "e011_analysis.json", res_dir / "e011_analysis.run.json"
    if out.exists() or side.exists():
        raise Refusal(f"{out} exists: the registered analysis runs once")
    res_dir.mkdir(parents=True, exist_ok=True)
    argv = [sys.executable, "-c", CHILD_BOOT, str(BACKEND),
            str(BACKEND / "scripts" / "run_surprise_snapshot.py"), str(inputs)]
    t0 = _utc()
    p = subprocess.run(argv, cwd=BACKEND, capture_output=True)
    rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    after = {f: digest(inputs / f)["sha256"] for f in INPUT_FILES + RECORD_FILES}
    rec = {"step": "analyze", "experiment": "E011",
           "registered_command": "scripts/run_surprise_snapshot.py analyze (default --start/--end: "
                                 f"{REGISTERED_UTC} {END_UTC}), unchanged",
           "analyze_root": str(inputs),
           "argv": ["-c", "<CHILD_BOOT>", *argv[3:]], "cwd": str(BACKEND), "started_utc": t0,
           "finished_utc": _utc(), "rc": p.returncode, **tree, "inputs_sha256": got,
           "inputs_unchanged_after": after == got,
           "child_peak_rss_mb": round(rss / (1 << 20 if sys.platform == "darwin" else 1 << 10)),
           "stderr_tail": p.stderr.decode(errors="replace")[-4000:]}
    ok = p.returncode == 0 and after == got
    if ok:
        try:
            json.loads(p.stdout)
        except ValueError:
            ok = False
    if not ok:  # nothing saved, nothing looked at: may be retried by hand after a ledger entry
        fp = _write_unique(res_dir, "e011_analysis.failed", json.dumps(rec, indent=1))
        raise Refusal(f"registered analyze failed (rc {p.returncode}); see {fp.name}",
                      _child_code(p.returncode))
    tmp = out.with_suffix(".json.tmp")
    tmp.write_bytes(p.stdout)
    os.replace(tmp, out)
    rec["output"] = {"path": str(out), **digest(out)}
    rec["secondaries_not_produced"] = SECONDARIES_NOT_PRODUCED
    (res_dir / "e011_secondaries_not_produced.json").write_text(
        json.dumps(SECONDARIES_NOT_PRODUCED, indent=1))
    side.write_text(json.dumps(rec, indent=1))
    return rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("freeze", "analyze"):
        s = sub.add_parser(name)
        s.add_argument("--run-dir", type=Path, required=True)
        if name == "freeze":
            s.add_argument("--src", type=Path, required=True)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "freeze":
            m = freeze(a.run_dir, a.src)
            r = {"frozen_utc": m["frozen_utc"],
                 "files": {k: v["sha256"] for k, v in m["files"].items()}}
        else:
            r = analyze(a.run_dir)
            r = {k: r[k] for k in ("experiment", "output", "child_peak_rss_mb", "rc")}
    except Refusal as e:
        print(f"refused: {e}", file=sys.stderr)
        return e.code
    print(json.dumps(r, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
