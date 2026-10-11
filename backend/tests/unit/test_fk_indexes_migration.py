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
