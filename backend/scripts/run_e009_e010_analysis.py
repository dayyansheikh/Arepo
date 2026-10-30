"""E009/E010 one-shot analysis runner (queue wrapper). New file; the registered code is untouched.

It only chains the registered commands on frozen inputs and saves their stdout byte for byte. It
computes no statistic, and it never parses an evidence line (freeze copies bytes only).

  run_e009_e010_analysis.py freeze  --run-dir D --canonical-src C --copy-src V
      Byte copy of the 4 canonical files (C, the live folder the poller still appends to) and the 4
      validation-copy files (V) into D/inputs/{canonical,copy}/, each cut at its last newline (a
      partial line being written is dropped). Refuses before 2026-11-03T08:00Z, if D exists, or if
      the validation copy differs from its sha256 recorded on 2026-10-30. Writes
      D/inputs/FREEZE_MANIFEST.json (sha256, line counts, sizes; no values).
  run_e009_e010_analysis.py merge   --run-dir D
      Re-hashes the frozen inputs, then runs scripts/run_cross_venue_gapfill.py (rule gapfill-v2)
      into the new folder D/merged. D/MERGE_RUN.json records argv, HEAD and the dirty paths.
  run_e009_e010_analysis.py analyze --run-dir D --exp {e009,e010} --label {primary,sensitivity}
      Runs the registered `run_cross_venue_live.py --root R --analyze START END` (e009) or
      `--analyze-e010 START END` (e010) with the registered window. R = D/merged (primary) or
      D/inputs/canonical (sensitivity); its two input files must hash to the merge / freeze
      manifest. Saves stdout to D/results/<exp>_<label>.json (written once; refuses if present) and
      D/results/<exp>_<label>.run.json (provenance, child peak RSS). Refuses before the registered
      analysis time (E009 02:00Z, E010 08:00Z on 2026-11-03).
  run_e009_e010_analysis.py verdicts --run-dir D
      Runs scripts/live_verdicts.py on the four saved outputs; writes D/results/VERDICTS.json.

Every step refuses (exit 2) when tracked files other than ALLOWED_DIRTY are modified. The host's
docs/research_lab/trials.jsonl is routinely modified by queue jobs, so the gap-fill CLI then gets
`--allow-dirty` (manifest `tree_dirty: true`, rule gapfill-v2 R9) and MERGE_RUN.json names the
dirty path for the disclosure. A time refusal exits 75 (queue: "not now").
See docs/research_lab/E009_E010_ANALYSIS_RUNBOOK_2026-10-30.md.
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

FILES = ("predictions.jsonl", "outcomes.jsonl", "predictions_e010.jsonl", "outcomes_e010.jsonl")
# registered windows (EXPERIMENT_LEDGER.md E009 / E010; CROSS_VENUE_LIVE.md) and analysis times
EXPS = {
    "e009": {"flag": "--analyze", "start": "2026-10-13T00:00:00Z", "end": "2026-11-03T00:00:00Z",
             "not_before": "2026-11-03T02:00:00Z",
             "files": ("predictions.jsonl", "outcomes.jsonl")},
    "e010": {"flag": "--analyze-e010", "start": "2026-10-13T02:00:00Z",
             "end": "2026-11-03T00:00:00Z", "not_before": "2026-11-03T08:00:00Z",
             "files": ("predictions_e010.jsonl", "outcomes_e010.jsonl")},
}
# one freeze serves both analyses: after the last E010 6 h outcome is due (origin 23:00Z + 6 h)
FREEZE_NOT_BEFORE = "2026-11-03T08:00:00Z"
# /home/opc/arepo_val/data-dumps/research_lab/cross_venue_live, unchanged since 2026-10-14 11:28Z
# (sha256 read on the host 2026-10-30; release data-20261015-dsheikh-val)
COPY_SHA256 = {
    "predictions.jsonl": "ffa56c68d94cdccd070e0defdaf093a15136b71c3e2918000ed60f3bc35b662f",
    "outcomes.jsonl": "37b26a4590af71c64c6e038cac1110ba420b31f7cdfa0e24ebecf1f8c51dd052",
    "predictions_e010.jsonl": "dc47f94cbdaad8f404da3a47ee0cb6b7881710635083af0cbe7a86c5818a8848",
    "outcomes_e010.jsonl": "b612a4ea218e1c8342d681b1ffb39ea3cae3958042bc7c08286cc275cc683699",
}
ALLOWED_DIRTY = frozenset({"docs/research_lab/trials.jsonl"})
REGISTERED_CODE = (
    "backend/astrolabe/research_lab/cross_venue_live.py",
    "backend/astrolabe/research_lab/cross_venue_live_e010.py",
    "backend/scripts/run_cross_venue_live.py",
    "backend/astrolabe/research_lab/cross_venue_gapfill.py",
    "backend/scripts/run_cross_venue_gapfill.py",
    "backend/astrolabe/research_lab/live_verdicts.py",
    "backend/scripts/live_verdicts.py",
)


class Refusal(Exception):
    def __init__(self, msg: str, code: int = REFUSED):
        super().__init__(msg)
        self.code = code


def _ep(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def _utc(t: float | None = None) -> str:
    return datetime.fromtimestamp(time.time() if t is None else t, UTC).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def digest(path: Path) -> dict:
    h, n, size = hashlib.sha256(), 0, 0
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
            n += chunk.count(b"\n")
            size += len(chunk)
    return {"sha256": h.hexdigest(), "lines": n, "bytes": size}


def git_state(cwd: Path = BACKEND) -> tuple[str, list[str]]:
    """(HEAD, sorted repo-relative paths of modified tracked files)."""

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
    code = {p: digest(REPO / p)["sha256"] for p in REGISTERED_CODE if (REPO / p).exists()}
    return {"git_head": head, "dirty_tracked": dirty, "registered_code_sha256": code}


def _not_before(when: str, now: float | None) -> None:
    now = time.time() if now is None else now
    if now < _ep(when):
        raise Refusal(f"not before {when} (now {_utc(now)})", TEMPFAIL)


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
            buf = f.read(step)
            i = buf.rfind(b"\n")
            if i >= 0:
                cut = pos - step + i + 1
                break
            pos -= step
        f.truncate(cut)
    st = src.stat()
    return {"source_path": str(src.resolve()), "source_bytes_at_copy": size,
            "source_mtime_utc": _utc(st.st_mtime), "partial_tail_bytes_dropped": copied - cut}


def freeze(run_dir: Path, canonical_src: Path, copy_src: Path, *, now: float | None = None,
           expect_copy: dict | None = None, state: tuple[str, list[str]] | None = None) -> dict:
    _not_before(FREEZE_NOT_BEFORE, now)
    tree = check_tree(state or git_state())
    run_dir, canonical_src, copy_src = Path(run_dir), Path(canonical_src), Path(copy_src)
    if run_dir.exists():
        raise Refusal(f"{run_dir} exists; the run folder must be new")
    if _inside(run_dir, canonical_src) or _inside(run_dir, copy_src):
        raise Refusal("the run folder may not lie inside a source folder")
    for side, src in (("canonical", canonical_src), ("copy", copy_src)):
        missing = [f for f in FILES if not (src / f).is_file()]
        if missing:
            raise Refusal(f"{side} source {src} lacks {missing}")
    expect_copy = COPY_SHA256 if expect_copy is None else expect_copy
    for f in FILES:  # the validation copy is static: check it before writing anything
        got = digest(copy_src / f)["sha256"]
        if got != expect_copy[f]:
            raise Refusal(f"validation copy {f} sha256 {got} != recorded {expect_copy[f]}")
    files = {}
    for side, src in (("canonical", canonical_src), ("copy", copy_src)):
        (run_dir / "inputs" / side).mkdir(parents=True)
        for f in FILES:
            dst = run_dir / "inputs" / side / f
            info = _copy_complete_lines(src / f, dst)
            files[f"{side}/{f}"] = {**digest(dst), **info}
    man = {"step": "freeze", "frozen_utc": _utc(now), **tree, "files": files,
           "note": "byte copies cut at the last newline; no line was parsed"}
    (run_dir / "inputs" / "FREEZE_MANIFEST.json").write_text(json.dumps(man, indent=1))
    return man


def _verify(root: Path, expected: dict[str, str]) -> dict:
    got = {f: digest(root / f)["sha256"] for f in expected}
    bad = {f: (got[f], expected[f]) for f in expected if got[f] != expected[f]}
    if bad:
        raise Refusal(f"input files differ from their manifest: {bad}")
    return got


def _freeze_manifest(run_dir: Path) -> dict:
    p = Path(run_dir) / "inputs" / "FREEZE_MANIFEST.json"
    if not p.is_file():
        raise Refusal(f"{p} missing: run freeze first")
    return json.loads(p.read_text())


def merge(run_dir: Path, *, state: tuple[str, list[str]] | None = None) -> dict:
    run_dir = Path(run_dir)
    fm = _freeze_manifest(run_dir)
    for side in ("canonical", "copy"):
        _verify(run_dir / "inputs" / side,
                {f: fm["files"][f"{side}/{f}"]["sha256"] for f in FILES})
    tree = check_tree(state or git_state())
    out = run_dir / "merged"
    if out.exists() or (run_dir / "MERGE_RUN.json").exists():
        raise Refusal(f"{out} or MERGE_RUN.json exists; the merge runs once")
    argv = [sys.executable, str(BACKEND / "scripts" / "run_cross_venue_gapfill.py"),
            "--canonical", str(run_dir / "inputs" / "canonical"),
            "--copy", str(run_dir / "inputs" / "copy"), "--out", str(out)]
    if tree["dirty_tracked"]:
        argv.append("--allow-dirty")
    t0 = _utc()
    p = subprocess.run(argv, cwd=BACKEND, capture_output=True)
    rec = {"step": "merge", "argv": argv[1:], "started_utc": t0, "finished_utc": _utc(),
           "rc": p.returncode, **tree, "stderr_tail": p.stderr.decode(errors="replace")[-4000:],
           "merge_manifest": str(out / "MERGE_MANIFEST.json")}
    (run_dir / "MERGE_RUN.json").write_text(json.dumps(rec, indent=1))
    if p.returncode != 0:
        raise Refusal(f"gap-fill CLI exited {p.returncode}; see MERGE_RUN.json", p.returncode)
    return rec


def analyze(run_dir: Path, exp: str, label: str, *, now: float | None = None,
            state: tuple[str, list[str]] | None = None) -> dict:
    cfg = EXPS[exp]
    _not_before(cfg["not_before"], now)
    run_dir = Path(run_dir)
    if label == "primary":
        root = run_dir / "merged"
        mp = root / "MERGE_MANIFEST.json"
        if not mp.is_file():
            raise Refusal(f"{mp} missing: run merge first")
        mm = json.loads(mp.read_text())
        if mm.get("rule_id") != "gapfill-v2" or mm.get("inputs_unchanged_after_merge") is not True:
            raise Refusal("merge manifest is not a clean gapfill-v2 merge")
        expected = {f: mm["outputs"][f]["sha256"] for f in cfg["files"]}
    elif label == "sensitivity":
        root = run_dir / "inputs" / "canonical"
        fm = _freeze_manifest(run_dir)
        expected = {f: fm["files"][f"canonical/{f}"]["sha256"] for f in cfg["files"]}
    else:
        raise Refusal(f"unknown label {label}")
    res_dir = run_dir / "results"
    out, side = res_dir / f"{exp}_{label}.json", res_dir / f"{exp}_{label}.run.json"
    if out.exists() or side.exists():
        raise Refusal(f"{out} exists: each registered analysis runs once")
    tree = check_tree(state or git_state())
    inputs = _verify(root, expected)
    res_dir.mkdir(parents=True, exist_ok=True)
    argv = [sys.executable, "scripts/run_cross_venue_live.py", "--root", str(root),
            cfg["flag"], cfg["start"], cfg["end"]]
    t0 = _utc()
    p = subprocess.run(argv, cwd=BACKEND, capture_output=True)
    rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    rec = {"step": "analyze", "experiment": exp.upper(), "label": label, "root": str(root),
           "argv": argv[1:], "cwd": str(BACKEND), "started_utc": t0, "finished_utc": _utc(),
           "rc": p.returncode, **tree, "inputs_sha256": inputs,
           "child_peak_rss_mb": round(rss / (1 << 20 if sys.platform == "darwin" else 1 << 10)),
           "stderr_tail": p.stderr.decode(errors="replace")[-4000:]}
    ok = p.returncode == 0
    if ok:
        try:
            json.loads(p.stdout)
        except ValueError:
            ok = False
    if not ok:  # no saved output, so nothing was looked at: the job may be retried by hand
        (res_dir / f"{exp}_{label}.failed.json").write_text(json.dumps(rec, indent=1))
        raise Refusal(f"registered analyze failed (rc {p.returncode}); see the .failed.json",
                      p.returncode or 1)
    tmp = out.with_suffix(".json.tmp")
    tmp.write_bytes(p.stdout)
    os.replace(tmp, out)
    rec["output"] = {"path": str(out), **digest(out)}
    side.write_text(json.dumps(rec, indent=1))
    return rec


def verdicts(run_dir: Path, *, state: tuple[str, list[str]] | None = None) -> dict:
    res_dir = Path(run_dir) / "results"
    out = res_dir / "VERDICTS.json"
    if out.exists():
        raise Refusal(f"{out} exists")
    tree = check_tree(state or git_state())
    v: dict = {"step": "verdicts", "made_utc": _utc(), **tree, "primary": {}, "sensitivity": {}}
    for label in ("primary", "sensitivity"):
        for exp in EXPS:
            f = res_dir / f"{exp}_{label}.json"
            if not f.is_file():
                raise Refusal(f"{f} missing")
            p = subprocess.run([sys.executable, "scripts/live_verdicts.py", exp, str(f)],
                               cwd=BACKEND, capture_output=True)
            if p.returncode != 0:
                raise Refusal(f"live_verdicts.py {exp} {f.name} exited {p.returncode}: "
                              f"{p.stderr.decode(errors='replace')[-2000:]}", p.returncode)
            v[label][exp.upper()] = json.loads(p.stdout)
    out.write_text(json.dumps(v, indent=1, default=str))
    return v


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("freeze", "merge", "analyze", "verdicts"):
        s = sub.add_parser(name)
        s.add_argument("--run-dir", type=Path, required=True)
        if name == "freeze":
            s.add_argument("--canonical-src", type=Path, required=True)
            s.add_argument("--copy-src", type=Path, required=True)
        if name == "analyze":
            s.add_argument("--exp", choices=sorted(EXPS), required=True)
            s.add_argument("--label", choices=("primary", "sensitivity"), required=True)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "freeze":
            r = freeze(a.run_dir, a.canonical_src, a.copy_src)
        elif a.cmd == "merge":
            r = merge(a.run_dir)
        elif a.cmd == "analyze":
            r = analyze(a.run_dir, a.exp, a.label)
            r = {k: r[k] for k in ("experiment", "label", "output", "child_peak_rss_mb", "rc")}
        else:
            verdicts(a.run_dir)
            r = {"verdicts": str(Path(a.run_dir) / "results" / "VERDICTS.json")}
    except Refusal as e:
        print(f"refused: {e}", file=sys.stderr)
        return e.code
    print(json.dumps(r, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
