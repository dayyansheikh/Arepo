"""Idempotent CLI for the edge-research workflow (prompt sections 3, 5, 13, 17).

Run with ``python -m astrolabe.evaluation.research_cli <command>``. Every command is safe to run
repeatedly and none needs a browser:

    research-bootstrap                 create/verify the research tables
    research-freeze --cadence 6h       screen the live universe and freeze a 6h/daily/weekly cohort
    research-freeze --cadence daily
    research-freeze --cadence weekly
    research-forward                   collect any due 1h/6h/24h/7d forward observations
    research-resolve                   record newly-available market resolutions
    research-status [--horizon 24h]    print the real research status / edge verdict

See docs/deployment.md and the deployment handoff for the exact UTC schedules.
"""
from __future__ import annotations

import argparse
import asyncio
import json

from ..clients.data_api import DataApiClient
from ..domain.models import utcnow
from ..service import MarketService
from ..storage.db import make_engine, make_sessionmaker
from .constants import CALCULATION_VERSION
from .migrations import bootstrap
from .research_constants import CADENCES, MODEL_VERSION
from .research_engine import build_entry_inputs, cadence_cutoff, freeze_from_inputs, screen_universe
from .research_service import ResearchReadService
from .research_tracking import Quote, collect_due_forward


async def live_price_provider(service: MarketService):
    """Build a (market_id, token_id) -> Quote provider from live market detail."""
    async def price_of(market_id: str, token_id: str) -> Quote | None:
        try:
            detail = await service.market_detail(market_id, requested_mode="live")
        except Exception:  # noqa: BLE001
            return None
        if detail is None:
            return None
        for o in detail.market.outcomes:
            if o.token_id == token_id:
                return Quote(
                    midpoint=o.midpoint, best_bid=o.best_bid, best_ask=o.best_ask,
                    spread=o.spread, near_mid_depth=o.near_mid_depth, source_timestamp=utcnow(),
                )
        return None
    return price_of


async def _freeze(session, service, data_api, *, cadence: str) -> dict:
    now = utcnow()
    screens, mode = await screen_universe(service, data_api, now=now)
    inputs = build_entry_inputs(screens, now=now)
    cutoff = cadence_cutoff(cadence, now)
    return await freeze_from_inputs(
        session, cadence=cadence, cutoff_at=cutoff, inputs=inputs,
        model_version=MODEL_VERSION, calculation_version=CALCULATION_VERSION, frozen_at=now,
    )


async def _run(args: argparse.Namespace) -> int:
    engine = make_engine()
    await bootstrap(engine)
    sm = make_sessionmaker(engine)
    service = MarketService()
    data_api = DataApiClient()
    try:
        async with sm() as session:
            if args.command == "research-bootstrap":
                print("Research tables ready.")
            elif args.command == "research-freeze":
                summary = await _freeze(session, service, data_api, cadence=args.cadence)
                print(json.dumps(summary))
            elif args.command == "research-forward":
                provider = await live_price_provider(service)
                summary = await collect_due_forward(session, price_of=provider)
                print(json.dumps(summary))
            elif args.command == "research-resolve":
                from .service import CohortRunner  # reuse the resolution source
                updated = await CohortRunner(service, mode="live").check_resolutions(session)
                print(json.dumps({"resolutions_recorded": updated}))
            elif args.command == "research-status":
                svc = ResearchReadService(session)
                if getattr(args, "horizon", None):
                    print(json.dumps(await svc.horizon_analysis(args.horizon), indent=2))
                else:
                    print(json.dumps(await svc.status(), indent=2))
    finally:
        await service.aclose()
        try:
            await data_api.aclose()
        except Exception:  # noqa: BLE001
            pass
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="astrolabe.evaluation.research_cli", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("research-bootstrap")
    fr = sub.add_parser("research-freeze")
    fr.add_argument("--cadence", required=True, choices=list(CADENCES))
    sub.add_parser("research-forward")
    sub.add_parser("research-resolve")
    st = sub.add_parser("research-status")
    st.add_argument("--horizon", default=None, choices=["1h", "6h", "24h", "7d"])
    return p


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(_run(build_parser().parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
