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
            "tradeflow_direction, primary_category FROM research_entries"
        ))).one()
        assert row.market_id == "MKT" and row.direction == "up"
        assert row.momentum_direction is None
        assert row.orderbook_direction is None
        assert row.tradeflow_direction is None
        assert row.primary_category is None
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


async def test_existing_account_survives_additive_name_and_digest_upgrade(tmp_path):
    url = f"sqlite+aiosqlite:///{tmp_path/'legacy-account.db'}"
    eng = make_engine(url)
    async with eng.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE users (
                id VARCHAR PRIMARY KEY, email VARCHAR NOT NULL UNIQUE,
                hashed_password VARCHAR NOT NULL, is_active BOOLEAN NOT NULL,
                is_superuser BOOLEAN NOT NULL, is_verified BOOLEAN NOT NULL,
                consent_at DATETIME, auth_provider VARCHAR NOT NULL, created_at DATETIME NOT NULL
            )
        """))
        await conn.execute(text("""
            CREATE TABLE alert_preferences (
                user_id VARCHAR PRIMARY KEY, email_enabled BOOLEAN NOT NULL,
                immediate_exceptional BOOLEAN NOT NULL, daily_digest BOOLEAN NOT NULL,
                weekly_summary BOOLEAN NOT NULL, min_research_priority INTEGER NOT NULL,
                min_confidence FLOAT NOT NULL, categories VARCHAR NOT NULL,
                short_term_only BOOLEAN NOT NULL, max_hours_to_close INTEGER,
                paused BOOLEAN NOT NULL, unsubscribed BOOLEAN NOT NULL, updated_at DATETIME NOT NULL
            )
        """))
        await conn.execute(text(
            "INSERT INTO users VALUES "
            "('legacy','legacy@example.com','hash',1,0,1,NULL,'local',:now)"
        ), {"now": datetime.now(UTC).isoformat()})
        await conn.execute(text(
            "INSERT INTO alert_preferences VALUES "
            "('legacy',1,1,0,0,60,0.45,'Crypto',0,NULL,0,0,:now)"
        ), {"now": datetime.now(UTC).isoformat()})

    result = await upgrade(eng)
    assert {
        "users.first_name", "users.last_name", "alert_preferences.digest_frequency",
        "alert_preferences.digest_top_n", "alert_preferences.digest_unsubscribed",
        "alert_preferences.digest_categories",
    }.issubset(set(result["columns_added"]))
    async with eng.connect() as conn:
        user = (await conn.execute(text(
            "SELECT email, first_name, last_name FROM users WHERE id='legacy'"
        ))).one()
        pref = (await conn.execute(text(
            "SELECT categories, digest_categories, digest_frequency, digest_top_n, "
            "digest_unsubscribed "
            "FROM alert_preferences WHERE user_id='legacy'"
        ))).one()
    assert user.email == "legacy@example.com"
    assert user.first_name is None and user.last_name is None
    assert pref.categories == "Crypto"
    assert pref.digest_categories == ""
    assert pref.digest_frequency == "off" and pref.digest_top_n == 10
    assert pref.digest_unsubscribed in (False, 0)
    await eng.dispose()


async def test_web_tier_bootstrap_migrates_existing_schema(prior_db):
    # The web app startup path now goes through the migrator (DB review CRITICAL-1): bootstrap must
    # bring an existing behind-schema database current, not just create_all.
    await _build_prior(prior_db)
    from astrolabe.evaluation.migrations import bootstrap

    eng = make_engine(prior_db)
    await bootstrap(eng)
    status = await check(eng)
    assert status["current"] is True and status["missing_columns"] == []
    await eng.dispose()


async def test_concurrent_upgrade_does_not_crash(prior_db):
    # Two migrators racing an actual version bump must both succeed (one does the DDL, the other
    # tolerates the duplicate) rather than crashing (DB review CRITICAL-3).
    import asyncio

    await _build_prior(prior_db)
    eng_a = make_engine(prior_db)
    eng_b = make_engine(prior_db)
    results = await asyncio.gather(upgrade(eng_a), upgrade(eng_b), return_exceptions=True)
    assert all(not isinstance(r, BaseException) for r in results), results
    assert (await check(eng_a))["current"] is True
    await eng_a.dispose()
    await eng_b.dispose()


def test_callable_list_and_dict_defaults_are_rendered():
    # A callable list/dict default must render a constant DEFAULT so legacy rows read [] / {}, not
    # NULL under a NOT NULL column (DB review MAJOR-5). Time/uuid callables stay nullable.
    from sqlalchemy import create_engine

    from astrolabe.storage.migrate import _add_column_sql

    eng = create_engine("sqlite://")
    with eng.connect() as conn:
        # research_entries.evidence_families has default=list; component_availability default=dict.
        list_sql = _add_column_sql(conn, "research_entries", "evidence_families")
        dict_sql = _add_column_sql(conn, "research_entries", "component_availability")
        # created_at uses a callable time default -> must NOT be frozen into one literal.
        ts_sql = _add_column_sql(conn, "research_entries", "created_at")
    assert "DEFAULT '[]'" in list_sql
    assert "DEFAULT '{}'" in dict_sql
    assert "DEFAULT" not in ts_sql


def test_postgresql_ddl_compiles_for_research_and_digest_tables():
    # Portability: the ORM must emit valid PostgreSQL DDL for the research and digest tables (no
    # SQLite-only constructs). We compile rather than execute (no live Postgres in CI).
    ddl = "\n".join(ddl_preview("postgresql"))
    assert "CREATE TABLE research_entries" in ddl
    assert "CREATE TABLE digest_deliveries" in ddl
    assert "CREATE TABLE digest_entries" in ddl
    assert "momentum_direction" in ddl and "orderbook_direction" in ddl
    # A few Postgres-portable expectations and no SQLite-only AUTOINCREMENT keyword.
    assert "AUTOINCREMENT" not in ddl


def test_private_account_tables_are_marked_for_postgres_rls():
    from astrolabe.storage.migrate import _PRIVATE_ACCOUNT_TABLES

    assert {"users", "alert_preferences", "digest_deliveries", "digest_entries"}.issubset(
        set(_PRIVATE_ACCOUNT_TABLES)
    )
