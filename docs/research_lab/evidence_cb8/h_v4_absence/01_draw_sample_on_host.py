import sys,random; sys.path.insert(0,"/home/opc/arepo/backend")
from pathlib import Path
from astrolabe.research_lab import cb8_holders as h, cb8_common as cm
cap=h.list_captures(Path(cm.c4.SNAPSHOT_ROOT))[-1]
base,_=h.holders_frame(h.read_capture(cap["dir"]))
cids=sorted({r["condition_id"] for r in base}); del base
random.seed(20261017); print("\n".join(random.sample(cids,600)))
