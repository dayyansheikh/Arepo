"""Unit-test isolation: never touch the real ~/.arepo wallet hash key."""

import pytest


@pytest.fixture(autouse=True)
def _isolated_wallet_key(tmp_path_factory, monkeypatch):
    monkeypatch.setenv("AREPO_WALLET_HASH_KEY_PATH",
                       str(tmp_path_factory.mktemp("walletkey") / "wallet_hash_key"))
