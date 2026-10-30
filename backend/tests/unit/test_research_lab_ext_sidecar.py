from __future__ import annotations

import csv
import gzip
import hashlib
import json
from datetime import UTC, datetime

from astrolabe.research_lab import collector, ext_sidecar
from astrolabe.research_panel.pairing import fee_category

LIMIT = collector.PARAMS["limit"]
PRE_ROWS = "178af7a56d43ae15fe83f5b13441deb42f2606cdc0c7f3ca713bcd7035526e66"
PRE_MANIFEST = "cdd884adac41b885809500b750b3e967dd8f8af715fe47c94172689cb78fcb1c"


def mk(i: int) -> dict:
    m = {
        "id": str(i), "conditionId": f"0x{i}", "closed": False, "active": True,
        "outcomes": '["Yes","No"]', "clobTokenIds": f'["t{i}a","t{i}b"]', "bestBid": "0.4",
        "bestAsk": 0.45, "spread": {"$decimal": "0.05"}, "lastTradePrice": "0.42",
        "oneHourPriceChange": -0.01, "liquidity": "1000.5", "volume24hr": 12,
        "endDate": "2027-01-01T00:00:00Z", "updatedAt": "2026-10-10T00:00:00Z",
        "events": [{"id": 77, "openInterest": 55.5, "commentCount": 3, "negRiskAugmented": True,
                    "createdAt": "2026-01-01T00:00:00Z"}],
    }
    if i % 2 == 0:
        m.update(feeType="crypto_fees", feesEnabled=True, takerBaseFee=1000,
                 orderPriceMinTickSize=0.01, orderMinSize=5, createdAt="2026-09-01T00:00:00Z",
                 startDate="2026-09-02T00:00:00Z", competitive=0.9, rewardsMinSize=50,
                 rewardsMaxSpread=3.5, clobRewards=[{"rewardsDailyRate": 2}],
                 acceptingOrders=False, umaResolutionStatuses="[]", volumeNum=99.0)
    return m


def page(ids, cursor=None) -> bytes:
    body: dict = {"markets": [mk(i) for i in ids]}
    if cursor is not None:
        body["next_cursor"] = cursor
    return json.dumps(body).encode()


class Fake:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls: list[dict] = []

    def __call__(self, params):
        self.calls.append(dict(params))
        return self.responses.pop(0)


def responses():
    return [(200, page(range(LIMIT), "c1"), {}), (200, page(range(LIMIT - 1, LIMIT + 20)), {})]


class FixedDT:
    @staticmethod
    def now(tz=None):
        return datetime(2026, 10, 11, 12, 0, 0, tzinfo=UTC)


def run(tmp_path, monkeypatch, **kw):
    monkeypatch.setattr(collector.uuid, "uuid4", lambda: type("U", (), {"hex": "0" * 32})())
    monkeypatch.setattr(collector, "datetime", FixedDT)
    clock = iter(f"2026-10-11T12:00:{i:02d}.000000Z" for i in range(60))
    fake = Fake(responses())
    m = collector.collect(tmp_path, transport=fake, sleep=lambda s: None, commit="abc",
                          now=lambda: next(clock), **kw)
    return m, fake, tmp_path / m["capture_id"]


def sha(path) -> str:
    raw = gzip.open(path).read() if path.suffix == ".gz" else path.read_bytes()
    return hashlib.sha256(raw).hexdigest()


def read_ext(d):
    with gzip.open(d / "rows_ext.csv.gz", "rt", newline="") as fh:
        return list(csv.DictReader(fh))


def test_main_decompressed_content_identical_with_and_without_sidecar(tmp_path, monkeypatch):
    class Off:
        def add_page(self, *a): pass
        def write(self, *a): pass
    a = tmp_path / "a"
    b = tmp_path / "b"
    _, _, da = run(a, monkeypatch)
    monkeypatch.setattr(collector, "SidecarBuilder", Off)
    _, _, db = run(b, monkeypatch)
    assert (da / "rows_ext.csv.gz").exists() and not (db / "rows_ext.csv.gz").exists()
    for f in ("rows.csv.gz", "manifest.json"):
        assert sha(da / f) == sha(db / f)
    # pinned hashes produced by the pre-change collector (git HEAD) on this fixture
    assert sha(da / "rows.csv.gz") == PRE_ROWS
    assert sha(da / "manifest.json") == PRE_MANIFEST


def test_sidecar_joins_and_parses(tmp_path, monkeypatch):
    m, fake, d = run(tmp_path, monkeypatch)
    assert len(fake.calls) == 2  # no extra requests
    with gzip.open(d / "rows.csv.gz", "rt", newline="") as fh:
        main = list(csv.DictReader(fh))
    ext = read_ext(d)
    assert [(r["market_id"], r["received_utc"], r["page_index"]) for r in main] == [
        (r["market_id"], r["received_utc"], r["page_index"]) for r in ext]
    assert all(r["capture_id"] == m["capture_id"] for r in ext)
    assert [r["clob_token_id_0"] for r in main] == [r["clob_token_id_0"] for r in ext]
    e0, e1 = ext[0], ext[1]  # id 0 (even), id 1 (odd, fields absent)
    assert e0["fee_type"] == "crypto_fees" and e0["fee_category"] == fee_category("crypto_fees")
    assert (e0["order_price_min_tick_size"], e0["rewards_max_spread"]) == ("0.01", "3.5")
    assert e0["clob_rewards"] == '[{"rewardsDailyRate":2}]' and e0["accepting_orders"] == "0"
    assert e0["clob_token_id_1"] == "t0b" and e0["event_open_interest"] == "55.5"
    assert e0["event_neg_risk_augmented"] == "1"
    for k in ("fee_type", "taker_base_fee", "created_at", "rewards_min_size", "volume_num",
              "open_interest", "clob_rewards", "fees_enabled"):
        assert e1[k] == ""  # missing stays missing, never 0
    assert e1["fee_category"] == fee_category(None)
    assert json.loads((d / "ext_manifest.json").read_text())["sidecar_status"] == "complete"


def test_incomplete_capture_has_partial_sidecar(tmp_path, monkeypatch):
    monkeypatch.setattr(collector.uuid, "uuid4", lambda: type("U", (), {"hex": "1" * 32})())
    fake = Fake([(200, page(range(LIMIT), "c1"), {}), (403, b"{}", {})])
    m = collector.collect(tmp_path, transport=fake, sleep=lambda s: None, commit="abc")
    d = tmp_path / m["capture_id"]
    em = json.loads((d / "ext_manifest.json").read_text())
    assert m["state"] != "complete" and em["sidecar_status"] == "partial_capture"
    assert len(read_ext(d)) == m["row_count"]


def test_sidecar_failure_does_not_break_snapshot(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("boom")
    monkeypatch.setattr(ext_sidecar, "ext_row", boom)
    _, _, d = run(tmp_path, monkeypatch)
    assert sha(d / "rows.csv.gz") == PRE_ROWS and sha(d / "manifest.json") == PRE_MANIFEST
    em = json.loads((d / "ext_manifest.json").read_text())
    assert em["sidecar_status"] == "missing" and not (d / "rows_ext.csv.gz").exists()


def test_sidecar_write_failure_marks_missing(tmp_path, monkeypatch):
    class NoCsv:
        @staticmethod
        def DictWriter(*a, **k):  # noqa: N802
            raise OSError("disk")
    monkeypatch.setattr(ext_sidecar, "csv", NoCsv)
    _, _, d = run(tmp_path, monkeypatch)
    assert json.loads((d / "ext_manifest.json").read_text())["sidecar_status"] == "missing"
    assert (d / "rows.csv.gz").exists()


def test_v2_fields_all_events_series_negrisk_feeschedule():
    m = mk(2)
    m.update(negRiskMarketID="nr1", feeSchedule='{"rate":0.07}')
    m["events"] = [{"id": 77, "series": [{"slug": "s-b"}, {"slug": "s-a"}]},
                   {"id": 5, "series": [{"slug": "s-a"}]}]
    r = ext_sidecar.ext_row(m, "c", "t", 0)
    assert r["fee_schedule"] == '{"rate":0.07}' and r["event_ids"] == '["5","77"]'
    assert r["series_slugs"] == '["s-a","s-b"]' and r["neg_risk_market_id"] == "nr1"
    bare = ext_sidecar.ext_row(mk(1), "c", "t", 0)
    assert bare["fee_schedule"] is None and bare["series_slugs"] is None
    assert bare["neg_risk_market_id"] is None and bare["event_ids"] == '["77"]'
    assert ext_sidecar.EXT_VERSION == "snapshot-ext-v3"
    assert r["parent_event_ids"] == "[null,null]" and bare["parent_event_ids"] == "[null]"
    m["events"][0]["parentEventId"] = 5000
    assert ext_sidecar.ext_row(m, "c", "t", 0)["parent_event_ids"] == '[null,"5000"]'
    m["events"] = []
    assert ext_sidecar.ext_row(m, "c", "t", 0)["parent_event_ids"] is None
