"""Scheduled digest runs must not touch the database while sending is disabled (infra fix)."""
import json

from astrolabe.digest import cli


async def test_disabled_digest_never_opens_the_database(monkeypatch, capsys):
    monkeypatch.setattr(cli, "digest_config", lambda: type("C", (), {"enabled": False})())

    def _boom(*a, **k):
        raise AssertionError("make_engine must not be called while digests are disabled")

    monkeypatch.setattr(cli, "make_engine", _boom)
    await cli._run(None)
    out = json.loads(capsys.readouterr().out)
    assert out == {"ran": False, "reason": "digest email is disabled", "processed": 0}


async def test_single_account_send_still_reaches_the_database(monkeypatch):
    monkeypatch.setattr(cli, "digest_config", lambda: type("C", (), {"enabled": False})())
    called = []

    def _engine(*a, **k):
        called.append(True)
        raise RuntimeError("stop here")

    monkeypatch.setattr(cli, "make_engine", _engine)
    try:
        await cli._run("x@example.com", single_account_send=True)
    except RuntimeError:
        pass
    assert called == [True]
