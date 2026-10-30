import json
from datetime import UTC, datetime, timedelta

import pytest

from astrolabe.feature_store.identity_bridge import import_gamma_identities
from astrolabe.feature_store.identity_views import dependence_components, select_as_known
from astrolabe.feature_store.migrations import upgrade
from tests.unit.test_feature_store_source_bridge import captured


@pytest.mark.asyncio
async def test_linked_identity_projection_is_exact_unresolved_and_idempotent(tmp_path):
    payload = [{"id": "m1", "conditionId": "0x" + "a" * 64,
                "question": "Test question", "clobTokenIds": '["123456789012345678901", "2"]',
                "outcomes": '["Yes", "No"]', "description": "Resolution rules",
                "resolutionSource": "official", "endDate": "2027-01-01T00:00:00Z",
                "orderPriceMinTickSize": "0.00100", "active": True, "closed": False,
                "events": [{"id": "e1"}]}]
    capture = await captured(tmp_path, body=json.dumps(payload).encode(), source="gamma.markets",
                             params={"limit": 2, "active": "true", "closed": "false"})
    url = f"sqlite+aiosqlite:///{tmp_path / 'fs2_test_identities.sqlite'}"
    await upgrade(url)
    result = await import_gamma_identities(url, capture["folder"])
    assert await import_gamma_identities(url, capture["folder"]) == result
    rows = result["records"]
    condition = next(row for kind, row in rows if kind == "condition_identity")
    market = next(row for kind, row in rows if kind == "market_identity_version")
    tokens = [row for kind, row in rows if kind == "token_outcome_version"]
    groups = [row for kind, row in rows if kind == "event_group_membership"]
    assert condition["identity_status"] == "unresolved" and condition["chain_id"] is None
    assert market["condition_identity_id"] is None
    assert market["missing_fields"]["condition_identity_id"] == "identity_unresolved"
    assert market["information_event_at"] is None
    assert str(market["tick_size"]) == "0.00100"
    assert market["event_id"] == "e1" and market["rules_text"] == "Resolution rules"
    assert [t["outcome_label"] for t in tokens] == ["Yes", "No"]
    assert tokens[0]["token_id"] == "123456789012345678901"
    assert all(t["token_contract"] is None for t in tokens)
    assert all(row["mapping_evidence_ids"] == [result["observation_id"]] for _, row in rows)
    assert all(row["provenance_class"] == "synthetic" for _, row in rows)
    now = datetime.now(UTC)
    assert select_as_known([market], subject_fields=("market_id",), cutoff=now) == [market]
    assert select_as_known([market], subject_fields=("market_id",),
                           cutoff=market["observed_from_at"] - timedelta(seconds=1)) == []
    for view in ("as_known", "conservative_evaluation"):
        split = dependence_components([market["id"]], groups, view=view, cutoff=now)
        assert split["unresolved_market_ids"] == [market["id"]]
        assert not split["split_ready"] and not split["model_feature_eligible"]
