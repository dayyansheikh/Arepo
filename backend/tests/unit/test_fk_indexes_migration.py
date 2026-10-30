"""The two previously-unindexed foreign keys gain covering indexes on upgrade (idempotent)."""
from sqlalchemy import inspect, text

from astrolabe.storage import migrate
from astrolabe.storage.db import make_engine


async def test_upgrade_adds_fk_indexes_to_an_existing_database_idempotently(tmp_path):
    engine = make_engine(f"sqlite+aiosqlite:///{tmp_path / 'old.db'}")
    await migrate.upgrade(engine)
    # Simulate a database created before the indexes existed.
    async with engine.begin() as conn:
        for name, _table, _col in migrate._FK_INDEXES:
            await conn.execute(text(f"DROP INDEX {name}"))
    await migrate.upgrade(engine)
    await migrate.upgrade(engine)  # second run is a no-op

    def _names(sync_conn):
        insp = inspect(sync_conn)
        return {t: {i["name"] for i in insp.get_indexes(t)}
                for t in ("signal_snapshots", "cohort_entries")}

    async with engine.connect() as conn:
        names = await conn.run_sync(_names)
    assert "ix_signal_snapshots_calculation_version" in names["signal_snapshots"]
    assert "ix_cohort_entries_snapshot_id" in names["cohort_entries"]
    async with engine.connect() as conn:
        assert (await conn.run_sync(migrate._check_sync))["current"] is True
    await engine.dispose()


async def test_postgres_builds_fk_indexes_concurrently_and_repairs_invalid(monkeypatch):
    """On Postgres the indexes are built CONCURRENTLY in AUTOCOMMIT after the DDL transaction; an
    INVALID leftover (interrupted build) is dropped and rebuilt; a valid one is left alone."""
    statements: list[str] = []

    class _Conn:
        def __init__(self, validity):
            self.validity = validity

        async def execution_options(self, **kw):
            assert kw == {"isolation_level": "AUTOCOMMIT"}
            return self

        async def scalar(self, stmt, params):
            return self.validity[params["name"]]

        async def execute(self, stmt):
            statements.append(str(stmt))

    class _Ctx:
        def __init__(self, conn):
            self.conn = conn

        async def __aenter__(self):
            return self.conn

        async def __aexit__(self, *a):
            return False

    class _Eng:
        def __init__(self, validity):
            self.validity = validity

        def connect(self):
            return _Ctx(_Conn(self.validity))

    names = [n for n, _t, _c in migrate._FK_INDEXES]
    built = await migrate._ensure_fk_indexes_concurrently(
        _Eng({names[0]: None, names[1]: False}))
    assert built == names
    assert statements[0].startswith(f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {names[0]}")
    assert statements[1] == f"DROP INDEX CONCURRENTLY IF EXISTS {names[1]}"
    assert statements[2].startswith(f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {names[1]}")
    statements.clear()
    assert await migrate._ensure_fk_indexes_concurrently(
        _Eng({names[0]: True, names[1]: True})) == []
    assert statements == []
