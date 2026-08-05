"""Schema migration tests (prompt section 3).

Reconstructs the EXACT prior SQLite schema (research_entries WITHOUT the per-family direction
columns), inserts representative data, runs the upgrade, and proves: prior rows survive, every
current ORM column is exposed, the migration is idempotent, the current-schema check passes, the
preflight fails on an outdated schema when auto-migrate is off, PostgreSQL DDL compiles, and no
historical value is fabricated for old rows.
"""
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from astrolabe.storage.db import make_engine, make_sessionmaker
from astrolabe.storage.migrate import (
    SCHEMA_VERSION,
    OutdatedSchemaError,
    check,
    ddl_preview,
    preflight,
    upgrade,
)

# The prior research_entries schema: the 34-column table that existed before momentum_direction /
# orderbook_direction / tradeflow_direction were added in code (the reproduced failure).
_PRIOR_RESEARCH_ENTRIES = """
CREATE TABLE research_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cohort_id INTEGER NOT NULL,
    role VARCHAR NOT NULL,
    rank INTEGER,
    walk_forward_partition VARCHAR NOT NULL,
    market_id VARCHAR NOT NULL,
    condition_id VARCHAR,
    event_id VARCHAR,
    token_id VARCHAR NOT NULL,
    market_question VARCHAR NOT NULL,
    outcome_name VARCHAR NOT NULL,
    direction VARCHAR,
    signal_classification VARCHAR NOT NULL,
    strength FLOAT NOT NULL,
    confidence FLOAT NOT NULL,
    research_priority INTEGER NOT NULL,
    n_families INTEGER NOT NULL,
    evidence_families JSON NOT NULL,
    component_scores JSON NOT NULL,
    component_availability JSON NOT NULL,
    data_quality VARCHAR NOT NULL,
    entry_price FLOAT,
    best_bid FLOAT,
    best_ask FLOAT,
    midpoint FLOAT,
    spread FLOAT,
    near_mid_depth FLOAT,
    liquidity FLOAT,
    volume FLOAT,
    data_age_seconds FLOAT,
    expected_close DATETIME,
    time_remaining_hours FLOAT,
    intended_horizons JSON NOT NULL,
    created_at DATETIME NOT NULL
)
"""

_PRIOR_COHORTS = """
CREATE TABLE research_cohorts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cadence VARCHAR NOT NULL,
    cutoff_at DATETIME NOT NULL,
    model_version VARCHAR NOT NULL,
    calculation_version VARCHAR NOT NULL,
    provenance_class VARCHAR NOT NULL,
    frozen BOOLEAN NOT NULL,
    frozen_at DATETIME,
    universe_size INTEGER NOT NULL,
    directional_count INTEGER NOT NULL,
    public_selection_count INTEGER NOT NULL,
    shadow_count INTEGER NOT NULL,
    observation_count INTEGER NOT NULL,
    abstention_count INTEGER NOT NULL,
    note VARCHAR,
    created_at DATETIME NOT NULL
)
"""


@pytest.fixture
def prior_db(tmp_path):
    return f"sqlite+aiosqlite:///{tmp_path/'prior.db'}"


async def _build_prior(url: str) -> None:
    eng = make_engine(url)
    async with eng.begin() as conn:
        await conn.execute(text(_PRIOR_COHORTS))
        await conn.execute(text(_PRIOR_RESEARCH_ENTRIES))
        now = datetime.now(UTC).isoformat()
        await conn.execute(text(
            "INSERT INTO research_cohorts (cadence,cutoff_at,model_version,calculation_version,"
            "provenance_class,frozen,universe_size,directional_count,public_selection_count,"
            "shadow_count,observation_count,abstention_count,created_at) VALUES "
            "('6h',:t,'m1','c1','prospective',1,2,1,1,0,0,1,:t)"
        ), {"t": now})
        await conn.execute(text(
            "INSERT INTO research_entries (cohort_id,role,walk_forward_partition,market_id,"
            "token_id,market_question,outcome_name,direction,signal_classification,strength,"
            "confidence,research_priority,n_families,evidence_families,component_scores,"
            "component_availability,data_quality,intended_horizons,created_at) VALUES "
            "(1,'public_selection','live','MKT','TOK','Q','Yes','up','Directional opportunity',"
            "0.5,0.6,90,2,'[]','[]','{}','good','[\"1h\"]',:t)"
        ), {"t": now})
    await eng.dispose()


async def test_upgrade_adds_missing_columns_and_preserves_rows(prior_db):
    await _build_prior(prior_db)
    eng = make_engine(prior_db)

    before = await check(eng)
    assert before["current"] is False
    assert "research_entries.momentum_direction" in before["missing_columns"]
    assert "research_entries.orderbook_direction" in before["missing_columns"]
    assert "research_entries.tradeflow_direction" in before["missing_columns"]

    result = await upgrade(eng)
    assert set(result["columns_added"]) >= {
        "research_entries.momentum_direction",
        "research_entries.orderbook_direction",
        "research_entries.tradeflow_direction",
    }

    after = await check(eng)
    assert after["current"] is True and after["missing_columns"] == []
    assert after["schema_version"] == SCHEMA_VERSION

    # Prior row preserved, and the new columns read NULL (never a fabricated value).
    sm = make_sessionmaker(eng)
    async with sm() as s:
        row = (await s.execute(text(
            "SELECT market_id, direction, momentum_direction, orderbook_direction, "
            "tradeflow_direction FROM research_entries"
        ))).one()
        assert row.market_id == "MKT" and row.direction == "up"
        assert row.momentum_direction is None
        assert row.orderbook_direction is None
        assert row.tradeflow_direction is None
        # The old cohort survived intact.
        n = (await s.execute(text("SELECT COUNT(*) FROM research_cohorts"))).scalar()
        assert n == 1
    await eng.dispose()


async def test_upgrade_is_idempotent(prior_db):
    await _build_prior(prior_db)
    eng = make_engine(prior_db)
    await upgrade(eng)
    second = await upgrade(eng)
    assert second["columns_added"] == []          # nothing left to add
    assert (await check(eng))["current"] is True
    await eng.dispose()


async def test_preflight_fails_on_outdated_schema_when_auto_migrate_off(prior_db):
    await _build_prior(prior_db)
    eng = make_engine(prior_db)
    with pytest.raises(OutdatedSchemaError) as exc:
        await preflight(eng, auto_migrate=False)
    assert "momentum_direction" in str(exc.value)
    # With auto-migrate on, the same preflight repairs it.
    status = await preflight(eng, auto_migrate=True)
    assert status["current"] is True
    await eng.dispose()


async def test_fresh_database_is_current_after_upgrade(prior_db):
    # A brand-new database (no prior tables) must end up fully current with no missing columns.
    eng = make_engine(prior_db)
    await upgrade(eng)
    status = await check(eng)
    assert status["current"] is True and status["missing_columns"] == []
    await eng.dispose()


def test_postgresql_ddl_compiles_for_research_tables():
    # Portability: the ORM must emit valid PostgreSQL DDL for the research tables (no SQLite-only
    # constructs). We compile rather than execute (no live Postgres in CI).
    ddl = "\n".join(ddl_preview("postgresql"))
    assert "CREATE TABLE research_entries" in ddl
    assert "momentum_direction" in ddl and "orderbook_direction" in ddl
    # A few Postgres-portable expectations and no SQLite-only AUTOINCREMENT keyword.
    assert "AUTOINCREMENT" not in ddl
