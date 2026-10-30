import json, shutil, sys
from pathlib import Path
B = "/Users/DayyanSheikh/Projects/astrolabe/backend"
sys.path.insert(0, B); sys.path.insert(0, B + "/tests")
import m1_synth as ms
from astrolabe.research_lab import m1_extract as ex
SPEC = ms.make_spec()
root = Path(sys.argv[1])
snap, sw = ms.build_stores(root / "src")
k = ms.L + 2
hold = root / "hold"
for kk in range(k + 1, ms.L + ms.W):
    if (snap / ms.cid(kk)).exists(): ms.move_capture(snap, hold, kk)
store = root / "research_lab" / "m1_ch263"
g = ms.tcap(k).timestamp()
print("pass1", ex.run_pass(store, snap, sw, SPEC, now=g + 6*3600 + 600))  # slot k decided with B
# A: started g-10 min, finished g+5h55 (on time) but its manifest became visible only now
A = snap / "A_dup"; shutil.copytree(snap / ms.cid(k), A)
m = json.loads((A / "manifest.json").read_text())
m.update(capture_id="A_dup", started_utc=ms.iso(ms.tcap(k) + ms.timedelta(minutes=-10)), finished_utc=ms.iso(ms.tcap(k) + ms.timedelta(minutes=355)))
(A / "manifest.json").write_text(json.dumps(m))
for kk in range(k + 1, ms.L + ms.W):
    if (hold / ms.cid(kk)).exists(): ms.move_capture(hold, snap, kk)
try:
    print("pass2", ex.run_pass(store, snap, sw, SPEC, now=ms.after_end(SPEC)))
except Exception as e:
    print("pass2 REFUSES:", type(e).__name__, e)
for p in sorted((store / "status").glob("dup_*.json")): print(p.name, p.read_text())
