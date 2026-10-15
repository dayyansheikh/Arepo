"""Expected-code caching never caches successful provenance/build verification."""
import builtins
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from astrolabe.feature_store import build_identity as source
from astrolabe.feature_store import source_parsers
from astrolabe.research_panel import frame
from astrolabe.research_panel.build_identity import verified_panel_build


def test_warm_verification_checks_loaded_code_without_recompiling(monkeypatch):
    source._COMPILED.clear()
    builds = []
    counts = []
    calls = []

    def observe(f, event, arg):
        if event == 'c_call' and arg is builtins.compile:
            calls.append(1)

    previous = sys.getprofile()
    sys.setprofile(observe)
    try:
        for _ in range(2):
            calls.clear()
            builds.append(verified_panel_build())
            counts.append(len(calls))
    finally:
        sys.setprofile(previous)
    assert counts[0] > 0 and counts[1] == 0
    assert builds[0] == builds[1]
    with monkeypatch.context() as m:
        m.setattr(source_parsers, 'clob_book', lambda *args: {})
        with pytest.raises(ValueError, match='loaded measurement code'):
            verified_panel_build()
    with monkeypatch.context() as m:
        m.setattr(frame, 'parse_page', lambda *args: {})
        with pytest.raises(ValueError, match='loaded panel code'):
            verified_panel_build()
    assert verified_panel_build() == builds[0]


@pytest.mark.parametrize('package', ['feature_store', 'research_panel'])
def test_warm_cache_still_reads_actual_source_bytes(monkeypatch, package):
    verified_panel_build()
    original = Path.read_bytes

    def changed(path):
        raw = original(path)
        if path.parent.name == package and path.name == 'build_identity.py':
            return raw + b'\n# changed despite unchanged path/stat\n'
        return raw

    monkeypatch.setattr(Path, 'read_bytes', changed)
    with pytest.raises(ValueError, match='build changed on disk'):
        verified_panel_build()


def test_cache_key_includes_bytes_filename_and_concurrent_expectations():
    a = source._compiled_codes(b'def value(): return 1\n', '/tmp/a.py')
    b = source._compiled_codes(b'def value(): return 2\n', '/tmp/a.py')
    c = source._compiled_codes(b'def value(): return 1\n', '/tmp/b.py')
    assert isinstance(a, tuple) and dict(a)['value'].co_consts != dict(b)['value'].co_consts
    assert dict(c)['value'].co_filename == '/tmp/b.py'
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: source._compiled_codes(
            b'def value(): return 1\n', '/tmp/a.py'), range(32)))
    assert all(result is a for result in results)


def test_cache_eviction_preserves_exact_expected_code(monkeypatch):
    source._COMPILED.clear()
    monkeypatch.setattr(source, '_COMPILED_LIMIT', 4)
    first = source._compiled_codes(b'def value(): return 1\n', '/tmp/first.py')
    for i in range(8):
        source._compiled_codes(b'def value(): return 1\n', f'/tmp/{i}.py')
    assert len(source._COMPILED) == 4
    assert source._compiled_codes(b'def value(): return 1\n', '/tmp/first.py') == first
    assert len(source._COMPILED) == 4
