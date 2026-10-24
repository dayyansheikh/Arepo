"""Selected-market source contracts; streamed synthetic responses, no external calls."""

import base64
import copy
import json

import httpx
import pytest

from astrolabe.feature_store.capture import _digest, _json_bytes, verify_capture
from astrolabe.feature_store.source_parsers import gamma_market
from astrolabe.feature_store.source_run import (
    POLICY,
    TARGETED_POLICY,
    SourceRun,
    _pair,
    read_source_run,
)
from astrolabe.feature_store.sources import SOURCES
from astrolabe.research_panel.quote_computation import record_quote_computation
from astrolabe.research_panel.quote_inputs import QuoteInputPolicy, project_quote_inputs
from tests.unit.test_research_panel_input_read import rewrite, snapshot
from tests.unit.test_research_panel_quote_inputs import AT, book, gamma, row

SOURCE = SOURCES['gamma.market']


def market(**changes):
    value = json.loads(base64.b64decode(gamma()['raw_payload_inline']))[0]
    return {**value, 'id': '123', 'active': True, 'closed': False, 'archived': False,
            'acceptingOrders': True, **changes}


@pytest.mark.parametrize('target', [None, 1, True, '', '-1', '+1', '01', '1.0',
                                  '1/2', '../1', '1?x=y', '１２', '1\n', '9' * 79])
def test_reject_path_injection_and_noncanonical_or_unbounded_target(target):
    with pytest.raises(ValueError):
        SOURCE.request({'market_id': target})


def test_fixed_path_and_no_query_or_auth_with_legacy_contract_unchanged():
    request = SOURCE.request({'market_id': '123'})
    assert request == {'method': 'GET', 'url': 'https://gamma-api.polymarket.com/markets/123',
                       'params': {}, 'path_params': {'id': '123'}}
    assert SOURCE.market_request_id(request) == '123'
    assert SOURCE.market_request_id(SOURCE.request({'market_id': '0'})) == '0'
    for extra in ({'active': 'true'}, {'closed': 'false'}, {'include_tag': True},
                  {'url': 'https://example.com'}, {'auth': 'fixture'}):
        with pytest.raises(ValueError):
            SOURCE.request({'market_id': '123', **extra})
    for change in ({'url': 'https://example.com/markets/123'}, {'method': 'POST'},
                   {'params': {'id': '123'}}, {'path_params': {'id': '124'}},
                   {'path_params': None}, {'headers': {}}):
        with pytest.raises(ValueError):
            SOURCE.market_request_id({**request, **change})
    old = SOURCES['gamma.markets']
    values = {'limit': 1, 'active': 'true', 'closed': 'false'}
    assert old.request(values) == {'method': 'GET', 'url': old.endpoint, 'params': values}
    assert 'gamma.market' not in POLICY['sources']


@pytest.mark.parametrize('value', [market(id='124'), market(id=123), [market()],
                                  market(active='true'), market(closed=0)])
def test_wrong_target_or_malformed_lifecycle_never_yields_mapping(value):
    with pytest.raises(ValueError):
        gamma_market(value, expected_market='123')


def test_unknown_lifecycle_is_explicit_and_does_not_change_identity_mapping():
    known = gamma_market(market(), expected_market='123')
    missing = market()
    for key in ('active', 'closed', 'archived', 'acceptingOrders'):
        del missing[key]
    unknown = gamma_market(missing, expected_market='123')
    assert unknown['mapping_version'] == known['mapping_version']
    assert set(unknown['lifecycle'].values()) == {None}


async def run_source(tmp_path, *, value=None, status=200, late=False):
    requests = []

    class Stream(httpx.AsyncByteStream):
        def __init__(self, value):
            self.value = value

        async def __aiter__(self):
            yield _json_bytes(self.value)

    def handler(request):
        requests.append(str(request.url))
        target = request.url.path == '/markets/123'
        body = (market() if value is None else value) if target else json.loads(
            base64.b64decode(book()['raw_payload_inline']))
        return httpx.Response(status if target else 200, stream=Stream(body))

    root = tmp_path.resolve() / 'fs2_capture_targeted'
    run = SourceRun(root, policy_version=TARGETED_POLICY['version'],
                    transport=httpx.MockTransport(handler))
    calls = [('gamma.market', {'market_id': '123'}), ('clob.book', {'token_id': '1'})]
    for source, params in reversed(calls) if late else calls:
        await run.fetch(source, params)
    return root, run, requests


@pytest.mark.asyncio
@pytest.mark.parametrize('changes,status,expected', [
    ({}, 200, 'observed'), ({'closed': True}, 200, 'market_closed'),
    ({'active': False}, 200, 'market_not_accepting_orders'),
    ({'acceptingOrders': False}, 200, 'market_not_accepting_orders'),
    ({'archived': True}, 200, 'market_archived'),
    ({'active': None}, 200, 'market_lifecycle_unknown'),
    ({'id': '124'}, 200, 'identity_unresolved_at_receipt'),
    ({}, 404, 'identity_unresolved_at_receipt'), ({}, 429, 'identity_unresolved_at_receipt'),
])
async def test_targeted_source_read_and_durable_quote_chain(tmp_path, changes, status, expected):
    root, _, requests = await run_source(tmp_path, value=market(**changes), status=status)
    assert requests == ['https://gamma-api.polymarket.com/markets/123',
                        'https://clob.polymarket.com/book?token_id=1']
    frozen, _ = _pair(root, 'run')
    assert frozen['policy'] == TARGETED_POLICY
    before = snapshot(root)
    output = tmp_path.resolve() / 'fs2_quote_computation_targeted'
    result = record_quote_computation(root, output_root=output, policy=QuoteInputPolicy(60, 60))
    assert result['quote_states'] == {expected: 1}
    assert result['source_provenance_class'] == 'synthetic'
    assert result['source_observation_count'] == 2
    assert not result['origin_admitted'] and not result['feature_store_admitted']
    facts, _ = _pair(output, 'quote_facts')
    quote = facts['projection']['quotes'][0]
    assert quote['midpoint'] == ('0.500' if expected == 'observed' else None)
    assert snapshot(root) == before
    observations = [r for kind, r in read_source_run(root) if kind == 'source_observation']
    identity = next(r for r in observations if r['source_id'] == 'gamma.market')
    assert json.loads(base64.b64decode(identity['raw_payload_inline'])) == market(**changes)
    if status == 429:
        assert identity['missing_reason'] == 'rate_limited'
    elif status == 404 or changes.get('id') == '124':
        assert identity['missing_reason'] == 'invalid'


@pytest.mark.asyncio
async def test_late_targeted_identity_does_not_repair_prior_book(tmp_path):
    root, _, _ = await run_source(tmp_path, late=True)
    result = record_quote_computation(
        root, output_root=tmp_path.resolve() / 'fs2_quote_computation_late',
        policy=QuoteInputPolicy(60, 60))
    assert result['quote_states'] == {'identity_unresolved_at_receipt': 1}


@pytest.mark.asyncio
async def test_policy_is_explicit_exact_and_cannot_be_silently_expanded(tmp_path):
    root = tmp_path.resolve() / 'fs2_capture_default'
    transport = httpx.MockTransport(lambda r: pytest.fail('unexpected network'))
    run = SourceRun(root, transport=transport)
    before = snapshot(root)
    with pytest.raises(ValueError, match='outside predeclared'):
        await run.fetch('gamma.market', {'market_id': '123'})
    assert snapshot(root) == before
    with pytest.raises(ValueError, match='unknown source'):
        SourceRun(tmp_path.resolve() / 'fs2_capture_bad', policy_version='unknown')
    assert not (tmp_path / 'fs2_capture_bad').exists()
    root, run, _ = await run_source(tmp_path)
    with pytest.raises(ValueError, match='outside predeclared'):
        await run.fetch('gamma.markets', {'limit': 1, 'active': 'true', 'closed': 'false'})
    rewrite(root, 'run', lambda p: p['policy'].update(sources=POLICY['sources']))
    with pytest.raises(ValueError, match='integrity'):
        read_source_run(root)


@pytest.mark.asyncio
async def test_capture_reader_rejects_rehashed_target_request_corruption(tmp_path):
    root, _, _ = await run_source(tmp_path)
    folder = next(p for p in root.iterdir() if p.is_dir() and
                  json.loads((p / 'receipt.json').read_bytes())['source_id'] == 'gamma.market')
    path = folder / 'receipt.json'
    receipt = json.loads(path.read_bytes())
    receipt['request']['url'] = 'https://example.com/markets/123'
    path.write_bytes(_json_bytes(receipt))
    ack_path = folder / 'raw_ack.json'
    ack = json.loads(ack_path.read_bytes())
    ack['receipt_hash'] = _digest(path.read_bytes())
    ack_path.write_bytes(_json_bytes(ack))
    with pytest.raises(ValueError, match='pinned contract'):
        verify_capture(folder, raw_only=True)


def test_pure_projector_checks_target_binding_and_retains_lifecycle():
    request = SOURCE.request({'market_id': '123'})
    identity = row(1, 'gamma.market', market(), -40,
                   request_metadata={'request': request})
    quote = project_quote_inputs([identity, book()], policy=QuoteInputPolicy(60, 60), cutoff=AT)
    assert quote['quotes'][0]['mapping']['lifecycle']['active'] is True
    corrupt = copy.deepcopy(identity)
    corrupt['request_metadata']['request'] = SOURCE.request({'market_id': '124'})
    with pytest.raises(ValueError, match='requested market'):
        project_quote_inputs([corrupt, book()], policy=QuoteInputPolicy(60, 60), cutoff=AT)
