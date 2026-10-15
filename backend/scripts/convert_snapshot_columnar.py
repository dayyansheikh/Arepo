"""Trial conversion of a research-lab snapshot (rows.csv.gz) to Parquet+zstd with an ID map.

Read-only on the snapshot. Writes only into a NEW --out directory (refuses to overwrite).
Runs an exact roundtrip equivalence check against the CSV as read by research_lab code.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

import pandas as pd

from astrolabe.research_lab import columnar
from astrolabe.research_lab.forecast import ID_DTYPES

ROOT = Path(__file__).resolve().parents[2]
TRIAL_ROOT = ROOT / "data-dumps" / "research_lab" / "columnar_trial"


def convert(snapshot: Path, out: Path, idmap_path: Path) -> dict:
    if out.exists():
        raise FileExistsError(f"refusing to overwrite existing {out}")
    csv_path = snapshot / "rows.csv.gz"
    rows = pd.read_csv(csv_path, dtype=ID_DTYPES)
    # Columns that are IDs but not in forecast.ID_DTYPES must also be read as str.
    extra = [c for c in columnar.ID_COLUMNS if c in rows.columns and rows[c].dtype != object]
    if extra:
        rows = pd.read_csv(csv_path, dtype={**ID_DTYPES, **dict.fromkeys(extra, str)})
    idmap = columnar.IdMap.load(idmap_path) if idmap_path.exists() else columnar.IdMap()
    before = idmap.sizes()
    table = columnar.to_columnar(rows, idmap)
    out.mkdir(parents=True)
    pq_path = out / "rows.parquet"
    pq_size = columnar.write_parquet(table, pq_path)
    idmap.save(idmap_path)
    back = columnar.from_columnar(columnar.read_parquet(pq_path), columnar.IdMap.load(idmap_path))
    problems = columnar.frames_identical(rows, back)
    csv_size = csv_path.stat().st_size
    idmap_gz = len(gzip.compress(idmap.to_json_bytes(), 9))
    marginal = idmap.new_keys_gz_bytes(before)
    report = {
        "snapshot": snapshot.name,
        "rows": len(rows),
        "equivalent": not problems,
        "problems": problems,
        "csv_gz_bytes": csv_size,
        "parquet_bytes": pq_size,
        "idmap_new_keys_gz_bytes": marginal,
        "idmap_full_gz_bytes": idmap_gz,
        "ratio_parquet_vs_csv": round(pq_size / csv_size, 4),
        "ratio_parquet_plus_marginal_idmap_vs_csv": round((pq_size + marginal) / csv_size, 4),
        "ratio_parquet_plus_full_idmap_vs_csv": round((pq_size + idmap_gz) / csv_size, 4),
        "idmap_sha256": idmap.content_sha256(),
        "schema_sha256": columnar.table_meta(table)["schema_sha256"],
    }
    (out / "report.json").write_text(json.dumps(report, indent=1))
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--snapshot", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--idmap", type=Path, default=None, help="default: <out parent>/idmap.json")
    a = ap.parse_args(argv)
    idmap_path = a.idmap or a.out.parent / "idmap.json"
    report = convert(a.snapshot, a.out, idmap_path)
    print(json.dumps(report, indent=1))
    return 0 if report["equivalent"] else 1


if __name__ == "__main__":
    sys.exit(main())
