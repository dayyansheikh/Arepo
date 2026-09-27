"""Exact weather primitives and causal source-only measurement, with synthetic faults."""

import copy
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest

from astrolabe.feature_store.capture import _strict_json
from astrolabe.feature_store.source_bridge import source_parse_artifact
from astrolabe.feature_store.source_parsers import nws_observation
from astrolabe.feature_store.source_run import SourceRun, read_source_run
from astrolabe.feature_store.sources import SOURCES
from astrolabe.research_panel.nws_measurement import measure_nws
from astrolabe.research_panel.original_reader import read_original_input_read
from tests.unit.test_feature_store_capture import Stream
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_selection import snapshot

original_code = _original_code
BODY = b"""{"type":"Feature","properties":{
"@id":"https://api.weather.gov/stations/KNYC/observations/2026-09-01T10:00:00+00:00",
"station":"https://api.weather.gov/stations/KNYC","stationId":"KNYC",
"timestamp":"2026-09-01T10:00:00+00:00",
"temperature":{"value":-1.234567890123456789,"unitCode":"wmoUnit:degC","qualityControl":"V"},
"windSpeed":{"value":0,"unitCode":"wmoUnit:km_h-1","qualityControl":"Z"},
"maxTemperatureLast24Hours":{"value":null,"unitCode":"wmoUnit:degC"}}}"""


def parse(body=None):
    return nws_observation(
        _strict_json(BODY) if body is None else body,
        expected_station="KNYC",
        received_at=datetime(2026, 9, 1, 11, tzinfo=UTC),
    )


def test_exact_numbers_native_units_qc_and_distinct_missingness():
    result = parse()
    quantities = result["quantities"]
    assert quantities["temperature"]["value"] == Decimal("-1.234567890123456789")
    assert quantities["temperature"]["quality_control"] == "V"
    assert quantities["windSpeed"]["value"] == 0
    assert quantities["windSpeed"]["state"] == "reported"
    assert quantities["maxTemperatureLast24Hours"]["state"] == "source_null"
    assert quantities["dewpoint"] == {"state": "not_reported"}
    assert result["publication_clock"] is None and not result["first_release_known"]
    assert not result["market_relevance_admitted"] and not result["quality_control_interpreted"]
    body = _strict_json(BODY)
    body["properties"]["temperature"].update(minValue=Decimal("-2.10"), maxValue=Decimal("1.20"))
    assert parse(body)["quantities"]["temperature"]["bounds"]["minValue"] == Decimal("-2.10")


@pytest.mark.parametrize("value", [None, "bad", "2026-09-01T10:00:00", "2026-09-02T10:00:00Z"])
def test_observation_time_is_never_substituted_for_receipt_or_publication(value):
    body = _strict_json(BODY)
    body["properties"]["timestamp"] = value
    result = parse(body)
    assert result["publication_clock"] is None
    assert (
        result["observation_clock"]["missing_reason"] != "observed"
        or "future_source_clock" in result["observation_clock"]["quality_flags"]
    )


@pytest.mark.parametrize("change", ["station", "stationId", "@id", "quantity", "unit", "bool"])
def test_wrong_identity_and_invalid_quantities_refuse(change):
    body = _strict_json(BODY)
    props = body["properties"]
    if change in {"station", "stationId", "@id"}:
        props[change] = "wrong"
    elif change == "quantity":
        props["temperature"] = None
    elif change == "unit":
        props["temperature"]["unitCode"] = None
    else:
        props["temperature"]["value"] = True
    with pytest.raises(ValueError):
        parse(body)


@pytest.mark.parametrize("station", ["../KNYC", "KNYC?x=1", "knyc", "", None, "https://evil"])
def test_station_path_is_fixed_and_bounded(station):
    with pytest.raises(ValueError):
        SOURCES["nws.station.observation"].request({"station_id": station})


def transport(root, status=200, body=BODY):
    def handler(request):
        assert (root / "measurement_policy_ack.json").is_file()
        assert (root / "fs2_capture_nws" / "run_ack.json").is_file()
        assert str(request.url) == "https://api.weather.gov/stations/KNYC/observations/latest"
        assert request.headers["User-Agent"] == "Arepo-Research-Verification/2.0"
        assert request.headers["Accept"] == "application/geo+json"
        return httpx.Response(status, stream=Stream([body]))

    return httpx.MockTransport(handler)


@pytest.mark.parametrize(
    "status,body,state",
    [(200, BODY, "observed"), (429, b"{}", "rate_limited"), (200, b"{}", "invalid")],
)
async def test_measurement_actual_reads_recovery_and_failed_source_states(
    tmp_path,
    original_code,
    status,
    body,
    state,
):
    root = tmp_path / "fs2_nws_measurement_test"
    report = await measure_nws(
        root,
        implementation_commit=original_code[1],
        repository=original_code[0],
        transport=transport(root, status, body),
    )
    assert report["state"] == state and report["provenance_class"] == "synthetic"
    assert not report["origin_admitted"] and not report["market_relevance_admitted"]
    source = root / "fs2_capture_nws"
    rows = read_source_run(source)
    observation = next(row for kind, row in rows if kind == "source_observation")
    assert observation["source_event_at"] is None and observation["first_available_at"] is None
    assert observation["first_received_at"] <= observation["available_to_model_at"]
    assert all(
        row["rights_state"] == "restricted" for kind, row in rows if kind == "source_registry"
    )
    if state == "observed":
        folder = next(p for p in source.iterdir() if p.is_dir())
        parsed = source_parse_artifact(folder, create=False)[1]["result"]["value"]
        assert parsed["quantities"]["temperature"]["value"] == {"$decimal": "-1.234567890123456789"}
    before = snapshot(root)
    with pytest.raises(FileExistsError):
        await measure_nws(
            root,
            implementation_commit=original_code[1],
            repository=original_code[0],
            transport=transport(root),
        )
    assert before == snapshot(root)
    with pytest.raises(ValueError, match="outside original source"):
        read_original_input_read(
            root / "fs2_input_read_nws",
            implementation_commit=original_code[1],
            repository=original_code[0],
            output_root=source / "fs2_input_read_read_bad",
        )
    if state == "observed":
        raw = next(source.glob("*/raw.bin"))
        raw.write_bytes(b"synthetic corruption")
        with pytest.raises(ValueError, match="original-build verification refused"):
            read_original_input_read(
                root / "fs2_input_read_nws",
                implementation_commit=original_code[1],
                repository=original_code[0],
                output_root=tmp_path / "fs2_input_read_read_corrupt",
            )


async def test_legacy_policy_stays_closed_and_changed_request_refused(tmp_path):
    run = SourceRun(tmp_path / "fs2_capture_default", transport=httpx.MockTransport(lambda r: None))
    with pytest.raises(ValueError, match="outside predeclared"):
        await run.fetch("nws.station.observation", {"station_id": "KNYC"})
    assert not any(p.is_dir() for p in run.journal.root.iterdir())
    contract = SOURCES["nws.station.observation"]
    request = contract.request({"station_id": "KNYC"})
    assert contract.station_request_id(request) == "KNYC"
    altered = copy.deepcopy(request)
    altered["url"] = "https://evil.example"
    with pytest.raises(ValueError):
        contract.station_request_id(altered)
    altered = copy.deepcopy(request)
    altered["headers"]["Accept"] = "application/json"
    with pytest.raises(ValueError):
        contract.station_request_id(altered)


async def test_revisions_preserved_and_resealed_parse_corruption_refused(tmp_path):
    import json

    from astrolabe.feature_store.capture import Budget, _digest, _json_bytes
    from astrolabe.feature_store.source_run import NWS_POLICY

    count = 0

    def handler(request):
        nonlocal count
        count += 1
        body = (
            BODY if count == 1 else BODY.replace(b"-1.234567890123456789", b"2.34567890123456789")
        )
        return httpx.Response(200, stream=Stream([body]))

    source = tmp_path / "fs2_capture_nws_revisions"
    run = SourceRun(
        source,
        budget=Budget(requests=2),
        transport=httpx.MockTransport(handler),
        policy_version=NWS_POLICY["version"],
        retained_bytes=1048576,
    )
    await run.fetch("nws.station.observation", {"station_id": "KNYC"})
    await run.fetch("nws.station.observation", {"station_id": "KNYC"})
    rows = [r for k, r in read_source_run(source) if k == "source_observation"]
    assert len(rows) == 2 and rows[0]["payload_hash"] != rows[1]["payload_hash"]
    parses = [
        source_parse_artifact(folder, create=False)[1]
        for folder in source.iterdir()
        if folder.is_dir()
    ]
    assert (
        parses[0]["result"]["value"]["observation_id"]
        == (parses[1]["result"]["value"]["observation_id"])
    )
    assert parses[0]["result"]["value"]["quantities"] != parses[1]["result"]["value"]["quantities"]
    file = next(source.glob("*/source_parse_*/source.json"))
    value = json.loads(file.read_bytes())
    value["result"]["value"]["quantities"]["temperature"]["value"] = {"$decimal": "999"}
    file.write_bytes(_json_bytes(value))
    ack_file = file.with_name("ack.json")
    ack = json.loads(ack_file.read_bytes())
    ack["payload_hash"] = _digest(file.read_bytes())
    ack_file.write_bytes(_json_bytes(ack))
    with pytest.raises(ValueError, match="exact raw replay"):
        read_source_run(source)


async def test_measurement_capacity_build_and_transport_refuse_before_requests(
    tmp_path,
    original_code,
    monkeypatch,
):
    from types import SimpleNamespace

    from astrolabe.research_panel import nws_measurement

    root = tmp_path / "fs2_nws_measurement_refused"
    with pytest.raises(ValueError, match="MockTransport"):
        await measure_nws(
            root,
            implementation_commit=original_code[1],
            repository=original_code[0],
            transport=object(),
        )
    with pytest.raises(ValueError, match="immutable Git"):
        await measure_nws(
            root,
            implementation_commit="HEAD",
            repository=original_code[0],
            transport=transport(root),
        )
    monkeypatch.setattr(nws_measurement.shutil, "disk_usage", lambda _: SimpleNamespace(free=0))
    with pytest.raises(ValueError, match="reservation"):
        await measure_nws(
            root,
            implementation_commit=original_code[1],
            repository=original_code[0],
            transport=transport(root),
        )
    assert not root.exists()
