"""Columnar (Parquet+zstd) storage for research-lab snapshots with an append-only ID map.

Long string IDs (condition ids, 77-digit CLOB token ids) dominate snapshot size. Each ID
column gets its own append-only dictionary (string id -> int key); a capture stores only the
integer keys. The map never reassigns or deletes a key, so any older capture stays decodable
against any later version of the map.

Exactness: numeric columns are stored as float64, which is exactly what ``pd.read_csv``
produces from the collector's CSV. That is NOT exact-decimal storage; the collector's raw
decimal strings are not retained in the CSV. ``decimal_string_columns`` is a schema hook for
a later collector change that supplies raw decimal strings: such columns are stored and
returned verbatim as strings. Nothing here fabricates exactness.

Optional dependency: ``pip install '.[research]'`` (pyarrow).
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

SCHEMA_VERSION = 1
ID_COLUMNS = (
    "market_id",
    "condition_id",
    "event_id",
    "clob_token_id_0",
    "neg_risk_market_id",
    "token_id",
)
NULL_KEY = -1
_META = b"arepo_columnar"


class IdMapError(RuntimeError):
    pass


def _canonical(columns: dict[str, list[str]]) -> bytes:
    return json.dumps(columns, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


class IdMap:
    """Per-column append-only string -> int key map (key = position in the column list)."""

    def __init__(self, columns: dict[str, list[str]] | None = None):
        self._cols: dict[str, list[str]] = {c: list(v) for c, v in (columns or {}).items()}
        self._index: dict[str, dict[str, int]] = {
            c: {s: i for i, s in enumerate(v)} for c, v in self._cols.items()
        }
        for c, v in self._cols.items():
            if len(self._index[c]) != len(v):
                raise IdMapError(f"duplicate ids in column {c}")

    def size(self, column: str) -> int:
        return len(self._cols.get(column, []))

    def total(self) -> int:
        return sum(len(v) for v in self._cols.values())

    def content_sha256(self) -> str:
        return hashlib.sha256(_canonical(self._cols)).hexdigest()

    def encode(self, column: str, values: pd.Series) -> np.ndarray:
        """Keys for ``values`` (appending unseen ids in first-seen order); NaN/None -> -1."""
        cols = self._cols.setdefault(column, [])
        idx = self._index.setdefault(column, {})
        out = np.empty(len(values), dtype=np.int64)
        for i, v in enumerate(values.tolist()):
            if v is None or (isinstance(v, float) and v != v):
                out[i] = NULL_KEY
                continue
            if not isinstance(v, str):
                raise TypeError(f"{column}: ID values must be str, got {type(v).__name__}")
            k = idx.get(v)
            if k is None:
                k = len(cols)
                cols.append(v)
                idx[v] = k
            out[i] = k
        return out

    def decode(self, column: str, keys: np.ndarray) -> list:
        ids = self._cols.get(column, [])
        out: list = []
        for k in keys.tolist():
            if k == NULL_KEY:
                out.append(np.nan)
            elif 0 <= k < len(ids):
                out.append(ids[k])
            else:
                raise IdMapError(f"{column}: key {k} not in map (size {len(ids)})")
        return out

    def is_prefix_of(self, other: IdMap) -> bool:
        return all(
            other._cols.get(c, [])[: len(v)] == v for c, v in self._cols.items()
        )

    def to_json_bytes(self) -> bytes:
        body = {
            "schema_version": SCHEMA_VERSION,
            "content_sha256": self.content_sha256(),
            "columns": self._cols,
        }
        return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()

    def save(self, path: Path) -> None:
        """Persist; refuses to drop/reassign keys already stored at ``path``."""
        path = Path(path)
        if path.exists():
            existing = IdMap.load(path)
            if not existing.is_prefix_of(self):
                raise IdMapError("refusing to save: would alter or delete existing keys")
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(self.to_json_bytes())
        tmp.replace(path)

    @classmethod
    def load(cls, path: Path) -> IdMap:
        body = json.loads(Path(path).read_bytes())
        if body.get("schema_version") != SCHEMA_VERSION:
            raise IdMapError(f"unsupported idmap version {body.get('schema_version')}")
        m = cls(body["columns"])
        if m.content_sha256() != body["content_sha256"]:
            raise IdMapError("idmap content hash mismatch (file altered or corrupt)")
        return m

    def new_keys_gz_bytes(self, since: dict[str, int]) -> int:
        """Gzip size of the ids appended after ``since`` (column -> prior size)."""
        added = {c: v[since.get(c, 0):] for c, v in self._cols.items()}
        return len(gzip.compress(_canonical(added), 9))

    def sizes(self) -> dict[str, int]:
        return {c: len(v) for c, v in self._cols.items()}


def schema_hash(columns: list[str], dtypes: list[str], id_cols: list[str], dec: list[str]) -> str:
    spec = {"v": SCHEMA_VERSION, "cols": columns, "dtypes": dtypes, "ids": id_cols, "dec": dec}
    return hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()


def to_columnar(
    rows: pd.DataFrame,
    idmap: IdMap,
    id_columns: tuple[str, ...] = ID_COLUMNS,
    decimal_string_columns: tuple[str, ...] = (),
) -> pa.Table:
    """Arrow table: ID columns as int64 keys, everything else typed as in ``rows``.

    Metadata records the original column order and pandas dtypes, the idmap content hash
    and sizes at encode time, and a schema hash.
    """
    ids = [c for c in rows.columns if c in id_columns]
    dec = [c for c in rows.columns if c in decimal_string_columns]
    arrays, names = [], []
    for c in rows.columns:
        s = rows[c]
        if c in ids:
            arrays.append(pa.array(idmap.encode(c, s), type=pa.int64()))
        elif c in dec:
            arrays.append(pa.array(s.tolist(), type=pa.string(), from_pandas=True))
        elif s.dtype == object:
            vals = [None if (v is None or v != v) else v for v in s.tolist()]
            arrays.append(pa.array(vals, type=pa.string()))
        else:
            arrays.append(pa.array(s.to_numpy(), from_pandas=False))
        names.append(c)
    dtypes = [str(rows[c].dtype) for c in rows.columns]
    meta = {
        "schema_version": SCHEMA_VERSION,
        "columns": list(rows.columns),
        "dtypes": dtypes,
        "id_columns": ids,
        "decimal_string_columns": dec,
        "idmap_sha256": idmap.content_sha256(),
        "idmap_sizes": idmap.sizes(),
        "schema_sha256": schema_hash(list(rows.columns), dtypes, ids, dec),
    }
    table = pa.Table.from_arrays(arrays, names=names)
    return table.replace_schema_metadata({_META: json.dumps(meta).encode()})


def table_meta(table: pa.Table) -> dict:
    return json.loads((table.schema.metadata or {})[_META])


def from_columnar(table: pa.Table, idmap: IdMap) -> pd.DataFrame:
    """Rebuild the DataFrame; IDs are str (NaN when null), dtypes as recorded."""
    meta = table_meta(table)
    if meta["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"unsupported columnar schema {meta['schema_version']}")
    if meta["schema_sha256"] != schema_hash(
        meta["columns"], meta["dtypes"], meta["id_columns"], meta["decimal_string_columns"]
    ):
        raise ValueError("columnar schema hash mismatch")
    data = {}
    for c, dt in zip(meta["columns"], meta["dtypes"], strict=True):
        col = table.column(c)
        if c in meta["id_columns"]:
            data[c] = pd.Series(idmap.decode(c, col.to_numpy()), dtype=object)
        elif dt == "object" or c in meta["decimal_string_columns"]:
            data[c] = pd.Series(
                [np.nan if v is None else v for v in col.to_pylist()], dtype=object
            )
        else:
            data[c] = pd.Series(col.to_numpy(zero_copy_only=False)).astype(dt)
    return pd.DataFrame(data, columns=meta["columns"])


def write_parquet(table: pa.Table, path: Path, level: int = 19) -> int:
    """Write Parquet+zstd to a NEW path (refuses overwrite); returns file size."""
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    pq.write_table(table, path, compression="zstd", compression_level=level)
    return path.stat().st_size


def read_parquet(path: Path) -> pa.Table:
    return pq.read_table(path)


def parquet_bytes(table: pa.Table, level: int = 19) -> bytes:
    buf = io.BytesIO()
    pq.write_table(table, buf, compression="zstd", compression_level=level)
    return buf.getvalue()


def frames_identical(a: pd.DataFrame, b: pd.DataFrame) -> list[str]:
    """Exact comparison (values, NaN positions, dtypes, column order); returns problems."""
    problems = []
    if list(a.columns) != list(b.columns):
        return [f"column order differs: {list(a.columns)} vs {list(b.columns)}"]
    if len(a) != len(b):
        return [f"row count differs: {len(a)} vs {len(b)}"]
    for c in a.columns:
        if str(a[c].dtype) != str(b[c].dtype):
            problems.append(f"{c}: dtype {a[c].dtype} vs {b[c].dtype}")
            continue
        x, y = a[c], b[c]
        if x.dtype == object:
            same = (x.isna().to_numpy() == y.isna().to_numpy()).all() and (
                x.fillna("<NA>").to_numpy() == y.fillna("<NA>").to_numpy()
            ).all()
        elif x.dtype.kind == "f":
            same = np.array_equal(
                x.to_numpy().view(np.int64), y.to_numpy().view(np.int64)
            )  # bit-exact incl. NaN payload and -0.0
        else:
            same = np.array_equal(x.to_numpy(), y.to_numpy())
        if not same:
            problems.append(f"{c}: values differ")
    return problems
