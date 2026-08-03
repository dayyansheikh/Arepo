"""Idempotent command-line entry points for the weekly cohort workflow.

Run with ``python -m astrolabe.evaluation.cli <command>``. Every command is safe to run
repeatedly (that is what makes it scheduler-friendly) and none requires a browser:

    bootstrap            create/verify the evaluation tables and calculation version
    rank    [--mode]     update this week's provisional top ten from current signals
    freeze  [--at]       freeze the cohort for a week at the cut-off
    forward [--mode]     collect any due forward prices for frozen cohorts
    resolve [--mode]     record newly-available market resolutions
    evaluate             (re)compute the two evaluation views and portfolio values
    seed-synthetic       build the labelled synthetic demonstration cohort
    status               print the recorded cohort weeks

See docs/deployment.md for scheduler setup (e.g. GitHub Actions / provider cron).
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime

from ..service import MarketService
from ..storage.db import make_engine, make_sessionmaker
from .migrations import bootstrap
from .service import CohortReadService, CohortRunner


def _parse_at(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


async def _run(args: argparse.Namespace) -> int:
    engine = make_engine()
    await bootstrap(engine)
    sessionmaker = make_sessionmaker(engine)
    service = MarketService()

    async with sessionmaker() as session:
        if args.command == "bootstrap":
            print("Evaluation tables ready.")
        elif args.command == "rank":
            runner = CohortRunner(service, mode=args.mode)
            cohort = await runner.update_rankings(
                session, at=_parse_at(args.at), limit=args.limit
            )
            print(
                f"Ranked week {cohort.iso_year}-W{cohort.iso_week:02d}: "
                f"{cohort.actual_size} provisional entries "
                f"(frozen={cohort.frozen}, provenance={cohort.provenance_class})."
            )
        elif args.command == "freeze":
            cohort = await runner_freeze(service, session, args)
            if cohort is None:
                print("No cohort exists for that week.")
            else:
                print(
                    f"Froze week {cohort.iso_year}-W{cohort.iso_week:02d}: "
                    f"{cohort.actual_size} entries at {cohort.frozen_at}."
                )
        elif args.command == "forward":
            runner = CohortRunner(service, mode=args.mode)
            added = await runner.collect_forward(session)
            print(f"Recorded {added} new forward price observation(s).")
        elif args.command == "resolve":
            runner = CohortRunner(service, mode=args.mode)
            updated = await runner.check_resolutions(session)
            print(f"Recorded {updated} new resolution(s).")
        elif args.command == "evaluate":
            runner = CohortRunner(service, mode=args.mode)
            n = await runner.evaluate(session)
            print(f"Evaluated {n} entr(y/ies).")
        elif args.command == "seed-synthetic":
            from .seed import seed_synthetic_demo

            cohort_id = await seed_synthetic_demo(session, service)
            print(f"Seeded synthetic demonstration cohort (id={cohort_id}).")
        elif args.command == "status":
            weeks = await CohortReadService(session).available_weeks()
            if not weeks:
                print("No cohorts recorded yet.")
            for w in weeks:
                print(
                    f"{w.label}  frozen={w.frozen}  size={w.actual_size}/{w.target_size}  "
                    f"provenance={w.provenance_class}"
                )
    await service.aclose()
    return 0


async def runner_freeze(service, session, args):
    runner = CohortRunner(service, mode=args.mode)
    return await runner.freeze(session, at=_parse_at(args.at))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="astrolabe.evaluation.cli", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("bootstrap")
    for name in ("rank", "freeze", "forward", "resolve", "evaluate", "seed-synthetic", "status"):
        sp = sub.add_parser(name)
        sp.add_argument("--mode", default="live", choices=["live", "cached", "replay"])
        if name in ("rank", "freeze"):
            sp.add_argument("--at", default=None, help="ISO timestamp (defaults to now).")
        if name == "rank":
            sp.add_argument("--limit", type=int, default=None)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
