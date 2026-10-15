# ruff: noqa: E501
"""CB1 history tests A (CH01), C (CH17), E (CH22): EXPLORATORY_HISTORICAL
(docs/research_lab/CREATIVE_BATCH_1.md; code in astrolabe/research_lab/cb1_history.py).

Subcommands (cwd = backend; paths default to <repo>/data-dumps/research_lab):

    declaration [--write]              print the declaration and E3 text-rule hashes; --write creates the spec file
                                       (the CB1 freeze file; never overwritten). Commit it before fetch-text.
    fetch-text   --run-id h2_main      Gamma question text + outcome labels (metadata only). Refuses unless the
                                       E3 text-rule hash is committed.
    census       --run-id h2_main      counts only (q0019); outcome columns are dropped by a guard; reads nothing from h5;
                                       logs no test. --fetch-text fetches the text first; --with-books adds C counts.
    dryrun       --run-id h2_main      whole pipeline on break-even random outcomes (no real outcome loaded); logs nothing.
    screen       --run-id h2_main      Stage-1 screen (q0020 A,E / q0021 C). Refuses unless the declaration spec is
                                       committed AND the committed h5 seal copy exists AND h5_cb1 verifies.
    replicate    --run-id h5_cb1       Stage-2 frozen replication of the tests that advanced (q0024 / q0026). Exits 0
                                       'nothing advanced' without reading h5. Verifies the seal, logs every h5 read.
    verify-seal  --run-id h5_cb1       seal check only.
    batch-holm   --results a.json b.json ...  binding batch Holm over all CB1 Stage-2 tests (history rep files, D rep,
                                       B R1 from run_cb1_structural). `replicate` only reports replicated_provisional_per_run.

Results are written OUTSIDE the run directories (default <root>/../creative_batch1/history/<run_id>/): an h5 run is sealed.

Results files are never overwritten. Nothing here is prospective, confirmatory, or an edge claim.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from astrolabe.research_lab import battery as B  # noqa: E402
from astrolabe.research_lab import cb1_history as cb  # noqa: E402
from astrolabe.research_lab import h5_seal  # noqa: E402
from astrolabe.research_lab import history_backfill as hb  # noqa: E402

HIST = ROOT / "data-dumps" / "research_lab" / "history"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def book_path(a, run_id: str) -> Path:
    if a.books:
        return Path(a.books)
    src = Path(a.root).parent / "history_sources"
    return src / ("book_features_h5_cb1" if run_id.startswith("h5") else "book_features") / "book_features.csv.gz"


def out_dir(a, run_id: str | None = None) -> Path:
    """Results directory: OUTSIDE the run directory (an h5 run is sealed; any file added under it breaks verify_seal).
    Default ``<root>/../creative_batch1/history/<run_id>`` (mirrors cb1_structural.OUT_ROOT)."""
    rid = run_id or a.run_id
    base = Path(a.out_root) if a.out_root else Path(a.root).parent / "creative_batch1" / "history"
    out = base / rid
    run = (Path(a.root) / rid).resolve()
    o = out.resolve()
    if o == run or run in o.parents:
        raise cb.Refused(f"results directory {out} is inside the run directory {run}; refused (sealed runs must stay untouched)")
    return out


def dump(obj) -> dict:
    return json.loads(json.dumps(B._clean(obj), default=cb._jsonable))


def cmd_declaration(a) -> int:
    log(f"declaration_sha256 {cb.declaration_sha256()}")
    log(f"e3_text_rule_sha256 {cb.e3_text_rule_sha256()}")
    if a.write:
        cb.write_spec()
        log(f"wrote {cb.SPEC_PATH}; review it, COMMIT it, then run fetch-text / census / screen")
    return 0


def cmd_fetch_text(a) -> int:
    res = cb.fetch_text(Path(a.root) / a.run_id, hb.httpx_transport(), rps=a.rps, live_check=hb.live_pass_or_lock)
    print(json.dumps(res))
    return 0


def cmd_census(a) -> int:
    books = cb.load_books(book_path(a, a.run_id)) if a.with_books else None
    res = cb.census(Path(a.root) / a.run_id, books=books)
    path = out_dir(a) / "census.json"
    cb.write_new(path, dump(res))
    print(json.dumps({"census_written": str(path), "census": dump(res["census"])}))
    return 0


def cmd_dryrun(a) -> int:
    fams = cb.parse_families(a.family)
    run_dir = Path(a.root) / a.run_id
    ctx = cb.make_ctx(run_dir)
    if ctx.is_h5:
        raise cb.Refused("dryrun runs on h2_main only")
    books = cb.load_books(book_path(a, a.run_id)) if "C" in fams else None
    out = {"note": "DRY RUN: break-even random outcomes, code check only, no trial logged", "families": fams, "tests": {}}
    for fam in fams:
        fr = cb.evaluate_family(run_dir, fam, ctx, stage=1, books=books, n_boot=min(a.n_boot, 200), n_placebo=min(a.n_placebo, 20),
                                max_markets=a.max_markets or 300, placebo_y=True)
        out["tests"].update({t: {k: r.get(k) for k in ("n", "n_event", "p", "mean", "testable", "advance")} for t, r in fr.tests.items()})
    od = out_dir(a)
    od.mkdir(parents=True, exist_ok=True)
    (od / "dryrun_results.json").write_text(json.dumps(dump(out), indent=1))
    log("dry run complete (code check only)")
    return 0


def cmd_screen(a) -> int:
    fams = cb.parse_families(a.family)
    path = out_dir(a) / cb.results_name(fams, False)
    if path.exists():
        raise cb.Refused(f"{path} exists (results are never overwritten)")
    books = cb.load_books(book_path(a, a.run_id)) if "C" in fams else None
    res = cb.screen(Path(a.root) / a.run_id, fams, books=books, n_boot=a.n_boot, n_placebo=a.n_placebo,
                    h5_run_dir=Path(a.root) / "h5_cb1")
    cb.write_results_and_log(dump(res), path, replication=False)
    if any("a1_sports_descriptive" in ex for ex in res["extras"].values()):
        cb.log_descriptive(path, "A1 sports descriptive (game-time end_at; not a test)", a.run_id)
    log(f"advanced: {res['advanced']}")
    print(json.dumps({"results": str(path), "advanced": res["advanced"]}))
    return 0


def cmd_replicate(a) -> int:
    fams = cb.parse_families(a.family)
    src = out_dir(a, a.src) / cb.results_name(fams, False)
    if not src.exists():
        log(f"screen results {src} not found")
        return 1
    path = out_dir(a) / cb.results_name(fams, True)
    if path.exists():
        raise cb.Refused(f"{path} exists (results are never overwritten)")
    books = cb.load_books(book_path(a, a.run_id)) if "C" in fams else None
    res = cb.replicate(Path(a.root) / a.run_id, json.loads(src.read_text()), fams, books=books, n_boot=a.n_boot,
                       n_placebo=a.n_placebo, job=a.job or f"run_cb1_history:replicate:{','.join(fams)}")
    if res is None:
        print(json.dumps({"status": "nothing advanced", "family": fams}))
        return 0
    cb.write_results_and_log(dump(res), path, replication=True)
    print(json.dumps({"results": str(path), "replicated_provisional_per_run": res["replicated_provisional_per_run"],
                      "note": "per-run Holm is provisional; the binding verdict is `batch-holm` over all CB1 Stage-2 tests"}))
    return 0


def cmd_batch_holm(a) -> int:
    if not a.results:
        raise cb.Refused("batch-holm needs --results <json> [<json> ...]")
    docs = [(str(Path(f)), json.loads(Path(f).read_text())) for f in a.results]
    res = cb.batch_holm(docs)
    res["inputs"] = [n for n, _ in docs]
    path = Path(a.out) if a.out else (Path(a.out_root) if a.out_root else Path(a.root).parent / "creative_batch1" / "history") / "batch_holm.json"
    cb.write_new(path, dump(res))
    print(json.dumps({"batch_holm": str(path), "m": res["m"], "replicated": res["replicated"]}))
    return 0


def cmd_verify(a) -> int:
    rc = 0
    for rid in [r for r in a.run_id.split(",") if r]:
        try:
            seal = cb.require_sealed(Path(a.root) / rid)
            print(json.dumps({"run_id": rid, "verified": True, "listing_sha256": seal["listing_sha256"]}))
        except (cb.Refused, h5_seal.SealError) as exc:
            print(json.dumps({"run_id": rid, "error": str(exc)}))
            rc = 1
    return rc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["declaration", "fetch-text", "census", "dryrun", "screen", "replicate", "verify-seal", "batch-holm"])
    ap.add_argument("--run-id", default="h2_main")
    ap.add_argument("--from", dest="src", default="h2_main", help="replicate: the screen run whose results select the tests")
    ap.add_argument("--family", default="A,E", help="A,E or C (comma separated)")
    ap.add_argument("--root", default=str(HIST))
    ap.add_argument("--out-root", default=None, help="results directory root (default <root>/../creative_batch1/history); never inside a run dir")
    ap.add_argument("--results", nargs="+", default=None, help="batch-holm: Stage-2 results files (history rep, D rep, B R1)")
    ap.add_argument("--out", default=None, help="batch-holm: output path")
    ap.add_argument("--books", default=None, help="pmxt book table (CB1-C); default per run")
    ap.add_argument("--with-books", action="store_true", help="census: include the C1/C2 order counts")
    ap.add_argument("--n-boot", type=int, default=cb.N_BOOT)
    ap.add_argument("--n-placebo", type=int, default=cb.PLACEBO_DRAWS)
    ap.add_argument("--max-markets", type=int, default=None, help="dryrun only")
    ap.add_argument("--rps", type=float, default=4.0)
    ap.add_argument("--fetch-text", action="store_true", help="census: fetch the h2 text first (needs the E3 hash committed)")
    ap.add_argument("--job", default=None, help="replicate: job id for the h5 access log")
    ap.add_argument("--write", action="store_true", help="declaration: write the spec file")
    a = ap.parse_args(argv)
    for rid in a.run_id.split(","):
        try:
            cb.forbid_run(rid)
        except cb.Refused as exc:
            print(json.dumps({"refused": str(exc)}))
            return 2
    try:
        if a.cmd == "census" and a.fetch_text and not (Path(a.root) / a.run_id / "cb1" / "text.csv.gz").exists():
            cmd_fetch_text(a)
        return {"declaration": cmd_declaration, "fetch-text": cmd_fetch_text, "census": cmd_census, "dryrun": cmd_dryrun,
                "screen": cmd_screen, "replicate": cmd_replicate, "verify-seal": cmd_verify, "batch-holm": cmd_batch_holm}[a.cmd](a)
    except (cb.Refused, h5_seal.SealError, FileExistsError) as exc:
        print(json.dumps({"refused": str(exc)[:400]}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
