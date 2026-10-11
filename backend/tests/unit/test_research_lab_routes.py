"""Research-lab forecast surface: available, unavailable, malformed, size bound."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from astrolabe.api.app import create_app
from astrolabe.api.routes import research_lab as rl

HEADER = (
    "market_id,event_id,origin_receipt_utc,mid,spread,chg_1h,dmid_hat,model_id,"
    "prediction_created_utc"
)


def _write_forecast(root: Path, n: int = 150, manifest_patch: dict | None = None) -> Path:
    d = root / "forecasts" / "20261010T192208Z_abc"
    d.mkdir(parents=True)
    lines = [HEADER]
    for i in range(n):
        chg = (i - n / 2) / 100.0
        lines.append(
            f"{i},e{i},2026-10-10T19:22:{i % 60:02d}.000000Z,0.5,0.01,{chg},{-0.33161 * chg},"
            "e002_reversal_v1,2026-10-10T19:31:57Z"
        )
    csv = d / "e002_reversal_v1.csv.gz"
    with gzip.open(csv, "wt") as fh:
        fh.write("\n".join(lines) + "\n")
    man = {
        "model_id": "e002_reversal_v1",
        "snapshot_capture_id": "20261010T192208Z_abc",
        "prediction_created_utc": "2026-10-10T19:31:57Z",
        "n_forecasts": n,
        "forecast_csv_sha256": hashlib.sha256(csv.read_bytes()).hexdigest(),
    }
    man.update(manifest_patch or {})
    (d / "e002_reversal_v1.manifest.json").write_text(json.dumps(man))
    return d


@pytest.fixture
def client_for():
    rl._cache.clear()
    made = []

    def make(root: Path | None) -> TestClient:
        app = create_app()
        app.dependency_overrides[rl.get_research_lab_root] = lambda: root
        c = TestClient(app)
        made.append(c)
        return c

    yield make
    rl._cache.clear()


def test_available(tmp_path, client_for):
    _write_forecast(tmp_path)
    body = client_for(tmp_path).get("/api/research-lab/forecasts/latest?top=5").json()
    assert body["status"] == "available"
    assert body["model"]["experimental"] is True
    assert body["model"]["validation_status"] == "E002 prospective test pending"
    assert body["n_eligible"] == 150
    assert len(body["top"]) == 5
    mags = [abs(r["dmid_hat"]) for r in body["top"]]
    assert mags == sorted(mags, reverse=True)
    assert body["capture"]["capture_id"] == "20261010T192208Z_abc"
    for r in body["top"]:
        assert r["direction"] == ("up" if r["dmid_hat"] > 0 else "down")


def test_unavailable_missing_root(tmp_path, client_for):
    for root in (None, tmp_path / "nope", tmp_path):
        body = client_for(root).get("/api/research-lab/forecasts/latest").json()
        assert body["status"] == "unavailable" and body["reason"]
    scores = client_for(None).get("/api/research-lab/forecasts/scores").json()
    assert scores["status"] == "unavailable"


def test_malformed_manifest(tmp_path, client_for):
    d = _write_forecast(tmp_path)
    (d / "e002_reversal_v1.manifest.json").write_text("{not json")
    body = client_for(tmp_path).get("/api/research-lab/forecasts/latest").json()
    assert body["status"] == "unavailable" and "malformed" in body["reason"]


def test_hash_mismatch_and_row_count(tmp_path, client_for):
    _write_forecast(tmp_path, manifest_patch={"forecast_csv_sha256": "0" * 64})
    body = client_for(tmp_path).get("/api/research-lab/forecasts/latest").json()
    assert body["status"] == "unavailable" and "hash" in body["reason"]


def test_size_bound(tmp_path, client_for):
    _write_forecast(tmp_path, n=300)
    c = client_for(tmp_path)
    assert len(c.get("/api/research-lab/forecasts/latest?top=100").json()["top"]) == 100
    assert c.get("/api/research-lab/forecasts/latest?top=101").status_code == 422
    assert c.get("/api/research-lab/forecasts/latest?top=0").status_code == 422


def test_scores(tmp_path, client_for):
    c = client_for(tmp_path)
    assert c.get("/api/research-lab/forecasts/scores").json()["status"] == "unavailable"
    (tmp_path / "e002").mkdir()
    (tmp_path / "e002" / "results.json").write_text(json.dumps({"verdict": "x"}))
    body = c.get("/api/research-lab/forecasts/scores").json()
    assert body["status"] == "available" and body["results"] == {"verdict": "x"}
    (tmp_path / "e002" / "results.json").write_text("x" * (rl.MAX_RESULTS_BYTES + 1))
    assert c.get("/api/research-lab/forecasts/scores").json()["status"] == "unavailable"


def test_production_default_is_absent(monkeypatch):
    from astrolabe.config import Settings

    s = Settings(environment="production", research_lab_data_root="")
    monkeypatch.setattr(rl, "get_settings", lambda: s)
    assert rl.get_research_lab_root() is None


# --- experiments / trials ---

LEDGER = """# Ledger
| ID | Status | Question | Result summary |
|---|---|---|---|
| E001 | COMPLETE (exploratory) | Q one? | Did a | thing |
| E002 | REGISTERED (pre-outcome) | Q two? | pending |
| E00X | COMPLETE | bad id | x |
| E003 | COMPLETE (exploratory) | Q three? | inconclusive |
| E004 | weird | only three cells |
| Model | Pooled | a | b |
"""


def _lab_client(root, ledger=None, trials=None):
    app = create_app()
    app.dependency_overrides[rl.get_research_lab_root] = lambda: root
    if ledger is not None:
        app.dependency_overrides[rl.get_ledger_path] = lambda: ledger
    if trials is not None:
        app.dependency_overrides[rl.get_trials_path] = lambda: trials
    return TestClient(app)


def test_parse_ledger_malformed_rows():
    rows = rl.parse_ledger_table(LEDGER)
    ids = [r["id"] for r in rows]
    assert "E00X" not in ids and "E004" not in ids and "Model" not in ids
    assert ids == ["E002", "E003"]  # E001 has 5 cells (stray pipe) and is skipped, not mis-parsed
    assert rows[0]["status"] == "registered" and rows[1]["status"] == "complete"


def test_experiments_unavailable(tmp_path):
    c = _lab_client(tmp_path, ledger=tmp_path / "missing.md")
    assert c.get("/api/research-lab/experiments").json()["status"] == "unavailable"
    empty = tmp_path / "e.md"
    empty.write_text("no table here")
    r = _lab_client(tmp_path, ledger=empty).get("/api/research-lab/experiments")
    assert r.json()["status"] == "unavailable"
    big = tmp_path / "big.md"
    big.write_text("x" * (rl.MAX_LEDGER_BYTES + 1))
    r = _lab_client(tmp_path, ledger=big).get("/api/research-lab/experiments")
    assert r.json()["status"] == "unavailable"


def test_experiments_results_whitelisted(tmp_path):
    ledger = tmp_path / "l.md"
    ledger.write_text(LEDGER)
    (tmp_path / "e003").mkdir()
    (tmp_path / "e003" / "s2_results.json").write_text(json.dumps({
        "experiment": "E003", "scored_utc": "2026-10-10T00:00:00Z", "secret_raw": "LEAK" * 10,
        "rows": [1] * 5000,
        "primary_AB": {"n": 5, "a": {"r2_oos": 0.01, "ci": [-0.1, 0.2], "verdict": "inconclusive",
                                     "raw_dump": list(range(1000))}},
    }))
    (tmp_path / "e002").mkdir()
    (tmp_path / "e002" / "results.json").write_text("{bad")
    body = _lab_client(tmp_path, ledger=ledger).get("/api/research-lab/experiments").json()
    by = {e["id"]: e for e in body["experiments"]}
    r3 = by["E003"]["result"]
    assert r3["status"] == "available" and r3["fields"]["experiment"] == "E003"
    assert r3["metrics"][0]["ci"] == [-0.1, 0.2] and r3["metrics"][0]["name"] == "primary_AB.a"
    assert "LEAK" not in json.dumps(body) and "raw_dump" not in json.dumps(body)
    assert by["E002"]["result"]["status"] == "unavailable"
    nd = _lab_client(tmp_path / "none", ledger=ledger)
    nodata = nd.get("/api/research-lab/experiments").json()
    assert nodata["experiments"][0]["result"]["status"] == "unavailable"


def test_metrics_bounded():
    node = {f"k{i}": {"r2_oos": 0.1} for i in range(100)}
    assert len(rl.summarize_result(node)["metrics"]) == rl.MAX_METRICS


def test_trials(tmp_path):
    p = tmp_path / "t.jsonl"
    lines = [json.dumps({"trial_id": str(i), "utc": "u", "dataset": "e001", "kind": "comparison",
                         "summary": {"B0": {}}, "provenance": {"x": "SECRET"}}) for i in range(30)]
    p.write_text("\n".join(lines[:10] + ["{broken", "[1]"] + lines[10:]) + "\n")
    c = _lab_client(tmp_path, trials=p)
    body = c.get("/api/research-lab/trials?limit=5").json()
    assert body["total"] == 30 and body["malformed_lines"] == 2
    assert [t["trial_id"] for t in body["trials"]] == ["29", "28", "27", "26", "25"]
    assert "SECRET" not in json.dumps(body) and body["trials"][0]["n_models_summarised"] == 1
    assert c.get("/api/research-lab/trials?limit=201").status_code == 422
    r = _lab_client(tmp_path, trials=tmp_path / "no").get("/api/research-lab/trials")
    assert r.json()["status"] == "unavailable"
