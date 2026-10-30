import json, shutil, sys
from pathlib import Path
B = "/Users/DayyanSheikh/Projects/astrolabe/backend"
sys.path.insert(0, B); sys.path.insert(0, B + "/tests")
import m1_synth as ms
from astrolabe.research_lab import m1_extract as ex
SPEC = ms.make_spec()
root = Path(sys.argv[1]); snap, sw = ms.build_stores(root / "src"); k = ms.L + 2
store = root / "research_lab" / "m1_ch263"
ex.run_pass(store, snap, sw, SPEC, now=ms.after_end(SPEC))
A = snap / "A_dup"; shutil.copytree(snap / ms.cid(k), A)
m = json.loads((A / "manifest.json").read_text())
m.update(capture_id="A_dup", started_utc=ms.iso(ms.tcap(k) + ms.timedelta(minutes=-10)), finished_utc=ms.iso(ms.tcap(k) + ms.timedelta(minutes=180)))
(A / "manifest.json").write_text(json.dumps(m))
print(ex.run_pass(store, snap, sw, SPEC, now=ms.after_end(SPEC)))
for p in sorted((store / "status").glob("*")):
    if "dup" in p.name or "A_dup" in p.name or "late_" in p.name: print(p.name, p.read_text())
