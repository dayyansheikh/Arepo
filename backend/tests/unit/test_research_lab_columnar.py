import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import columnar as col

TOKEN = "7" * 77


def _rows():
    return pd.DataFrame(
        {
            "capture_id": ["c1", "c1", "c1"],
            "market_id": ["1", "2", "010"],
            "condition_id": ["0xaa", "0xbb", None],
            "clob_token_id_0": [TOKEN, TOKEN[:-1] + "8", np.nan],
            "best_bid": [0.1, np.nan, -0.0],
            "closed": [False, True, False],
            "binary": [1, 0, 1],
            "end_date": ["2027-01-01T00:00:00Z", None, "x"],
        }
    )


def test_roundtrip_exact(tmp_path):
    rows = _rows()
    m = col.IdMap()
    p = tmp_path / "a.parquet"
    col.write_parquet(col.to_columnar(rows, m), p)
    back = col.from_columnar(col.read_parquet(p), m)
    assert col.frames_identical(rows, back) == []
    assert back["clob_token_id_0"][0] == TOKEN and len(TOKEN) == 77
    assert back["market_id"][2] == "010"


def test_comparison_detects_difference():
    a = _rows()
    b = a.copy()
    b.loc[0, "best_bid"] = 0.1000000001
    assert col.frames_identical(a, b) == ["best_bid: values differ"]


def test_idmap_append_only_and_stable_across_sessions(tmp_path):
    path = tmp_path / "idmap.json"
    m = col.IdMap()
    k1 = m.encode("market_id", pd.Series(["b", "a", "b"]))
    assert k1.tolist() == [0, 1, 0]
    m.save(path)
    m2 = col.IdMap.load(path)
    k2 = m2.encode("market_id", pd.Series(["a", "c"]))
    assert k2.tolist() == [1, 2]
    m2.save(path)
    assert col.IdMap.load(path).decode("market_id", np.array([0, 1, 2])) == ["b", "a", "c"]
    # an old capture still decodes against the grown map
    assert m.content_sha256() != m2.content_sha256()


def test_idmap_refuses_to_alter_existing_keys(tmp_path):
    path = tmp_path / "idmap.json"
    m = col.IdMap()
    m.encode("market_id", pd.Series(["a", "b"]))
    m.save(path)
    other = col.IdMap()
    other.encode("market_id", pd.Series(["b", "a"]))
    with pytest.raises(col.IdMapError):
        other.save(path)
    shorter = col.IdMap()
    shorter.encode("market_id", pd.Series(["a"]))
    with pytest.raises(col.IdMapError):
        shorter.save(path)


def test_idmap_tamper_detected(tmp_path):
    path = tmp_path / "idmap.json"
    m = col.IdMap()
    m.encode("market_id", pd.Series(["a"]))
    m.save(path)
    path.write_text(path.read_text().replace('"a"', '"z"'))
    with pytest.raises(col.IdMapError):
        col.IdMap.load(path)


def test_schema_and_version_hash_recorded():
    m = col.IdMap()
    t = col.to_columnar(_rows(), m)
    meta = col.table_meta(t)
    assert meta["idmap_sha256"] == m.content_sha256()
    assert meta["schema_version"] == col.SCHEMA_VERSION
    assert meta["columns"] == list(_rows().columns)
    t2 = col.to_columnar(_rows().drop(columns=["binary"]), col.IdMap())
    assert col.table_meta(t2)["schema_sha256"] != meta["schema_sha256"]


def test_refuse_overwrite(tmp_path):
    t = col.to_columnar(_rows(), col.IdMap())
    p = tmp_path / "a.parquet"
    col.write_parquet(t, p)
    with pytest.raises(FileExistsError):
        col.write_parquet(t, p)


def test_non_string_id_rejected():
    with pytest.raises(TypeError):
        col.IdMap().encode("market_id", pd.Series([1, 2]))


def test_decimal_string_option_kept_verbatim():
    rows = pd.DataFrame({"market_id": ["1"], "best_bid": ["0.10"]})
    m = col.IdMap()
    t = col.to_columnar(rows, m, decimal_string_columns=("best_bid",))
    back = col.from_columnar(t, m)
    assert back["best_bid"][0] == "0.10"
