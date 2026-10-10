"""Fixed public connector and explicit synthetic loopback seam; no collector or admission.

The future durable window driver must own subscription, receipt clocks, heartbeats, total
budgets and cleanup. Importing this module opens nothing. This connector alone creates no
prospective journal or model input and does not authenticate a caller's market identity.
"""

import asyncio
from dataclasses import dataclass

import websockets
from websockets.asyncio.client import connect

from astrolabe.feature_store.sources import SOURCES

VERSION = 'fs2-market-socket-connector-v1'
TESTED_LIBRARY = '17.0.1'
OPTIONS = {'proxy': None, 'compression': None, 'ping_interval': None, 'ping_timeout': None,
           'open_timeout': 5, 'close_timeout': 2, 'max_size': 262144, 'max_queue': 4,
           'write_limit': 32768, 'user_agent_header': 'Arepo-Research-Verification/2.0'}


class _NoRedirectConnect(connect):
    def process_redirect(self, exc):
        # Returning the original exception refuses even a same-origin redirect. No URL or
        # response text is copied into our own diagnostic records; the driver records class/code.
        return exc


@dataclass(frozen=True)
class MarketConnection:
    socket: object
    provenance_class: str
    endpoint: str

    async def close(self):
        """Bound cleanup even when a peer/library close handshake stalls; retain the error."""
        try:
            async with asyncio.timeout(OPTIONS['close_timeout']):
                await self.socket.close()
        except BaseException:
            try:
                self.socket.transport.abort()
            except Exception:
                pass  # preserve the original close/cancellation failure
            raise


def connector_contract():
    if websockets.__version__ != TESTED_LIBRARY:
        raise ValueError('socket library version unverified; review and test before use')
    return {'schema_version': VERSION, 'library_version': TESTED_LIBRARY,
            'source_contract_version': SOURCES['clob.market_stream'].version,
            'endpoint': SOURCES['clob.market_stream'].endpoint, 'options': dict(OPTIONS),
            'redirects': 'refused', 'retries': 0, 'reconnects': 0,
            'source_admitted': False, 'identity_verification_required': True,
            'durable_driver_required': True}


async def _open(endpoint, provenance):
    contract = connector_contract()
    # Await once; never use the library's reconnecting async iterator. No environment proxy,
    # caller headers, cookies, auth, custom DNS target or alternate URL enter this boundary.
    async with asyncio.timeout(contract['options']['open_timeout']):
        socket = await _NoRedirectConnect(endpoint, **contract['options'])
    return MarketConnection(socket, provenance, endpoint)


async def open_market_socket():
    """Only the future verified durable driver may use this fixed public diagnostic endpoint."""
    return await _open(SOURCES['clob.market_stream'].endpoint, 'prospective')


async def open_loopback_socket(port):
    """Actual local wire tests remain synthetic; no caller hostname or URI is accepted."""
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('explicit loopback TCP port required')
    return await _open(f'ws://127.0.0.1:{port}/ws/market', 'synthetic')
