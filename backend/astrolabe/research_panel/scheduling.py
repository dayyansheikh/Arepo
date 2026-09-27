"""Wait for the actual UTC boundary; timer completion alone is not clock evidence."""

import asyncio
import time

from astrolabe.feature_store.capture import _clock
from astrolabe.feature_store.source_run import _time
from astrolabe.feature_store.types import utc_datetime


async def wait_until(boundary):
    boundary = utc_datetime(boundary)
    started = time.monotonic()
    initial = None
    while True:
        observed = _clock()
        remaining = (boundary - _time(observed)).total_seconds()
        if remaining <= 0:
            return observed
        if initial is None:
            if remaining > 86400:
                raise ValueError('scheduled boundary exceeds one-day wait limit')
            initial = remaining
        # A backward wall-clock step must not cause an unbounded wait. The one-second
        # allowance is a waiting budget, never permission to start before the boundary.
        if time.monotonic() - started > initial + 1:
            raise ValueError('UTC boundary not reached within bounded timer wait')
        await asyncio.sleep(max(0.001, min(remaining, initial + 1)))
