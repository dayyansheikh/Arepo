import json, shutil, sys
from pathlib import Path
B = "/Users/DayyanSheikh/Projects/astrolabe/backend"
sys.path.insert(0, B); sys.path.insert(0, B + "/tests")
import m1_synth as ms
from astrolabe.research_lab import m1_extract as ex
SPEC = ms.make_spec()
root = Path(sys.argv[1]); mode = sys.argv[2]
snap, sw = ms.build_stores(root / "src")
k = ms.L + 2
hold = root / "hold"
def mk(name, smin, fmin, src):
    A = snap / name; shutil.copytree(src, A)
    m = json.loads((A / "manifest.json").read_text())
    m.update(capture_id=name, started_utc=ms.iso(ms.tcap(k) + ms.timedelta(minutes=smin)), finished_utc=ms.iso(ms.tcap(k) + ms.timedelta(minutes=fmin)))
    (A / "manifest.json").write_text(json.dumps(m))
store = root / "research_lab" / "m1_ch263"
if mode == "missing":
    ms.move_capture(snap, hold, k)  # slot k has no capture when decided
    ex.run_pass(store, snap, sw, SPEC, now=ms.tcap(k).timestamp() + 6*3600 + 600)
    src = hold / ms.cid(k)
    mk("X1", 0, 100, src); mk("X2", 5, 120, src)  # two on-time captures delivered after missing recorded
    print(ex.run_pass(store, snap, sw, SPEC, now=ms.after_end(SPEC)))
else:  # tie: same start, smaller id, arrives after decision
    ex.run_pass(store, snap, sw, SPEC, now=ms.after_end(SPEC))
    mk("0_tie", 0, 100, snap / ms.cid(k))
    print(ex.run_pass(store, snap, sw, SPEC, now=ms.after_end(SPEC)))
    print("cid", ms.cid(k))
for p in sorted((store / "status").glob("*.json")):
    if p.name.startswith(("late_", "dup_")): print(p.name, p.read_text()[:200])
print("audit", {k2: v for k2, v in ex.audit_chain(store, SPEC).items() if k2 != "breaks"})
