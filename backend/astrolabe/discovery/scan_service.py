"""Complete-universe short-horizon scan service (prompt sections 2-8).

One scan: discover the COMPLETE active universe via real pagination, apply the 30-day public
eligibility gate, score every eligible market with the existing model, assign each to its
non-overlapping closing-time bucket, rank each bucket over ALL its eligible markets plus an overall
30-day ranking, and store the result append-only. The public top ten is a display subset flagged on
the stored rows; it never reduces the analysed, stored or ranked universe.

An incomplete pagination (offset cap, non-progression, retry exhaustion, emergency guard) is carried
through as ``pagination_complete=False`` with a reason, so a caller (a cohort freeze) can refuse or
degrade rather than treat a partial universe as complete (prompt sections 2, 20).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ..clients.gamma import GammaClient, PaginationReport
from ..domain.models import Market, utcnow
from ..evaluation.constants import CALCULATION_VERSION
from ..evaluation.research_constants import MODEL_VERSION, PUBLIC_SELECTION_SIZE
from ..evaluation.research_engine import ScoredScreen, score_screen
from ..ingest.normalize import normalize_market
from .eligibility import (
    PRIMARY_BUCKETS,
    DiscoveryFunnel,
    build_funnel,
)

PUBLIC_TOP_N = PUBLIC_SELECTION_SIZE  # 10 - a DISPLAY limit only


@dataclass
class AnalysedMarket:
    """One eligible market after scoring, ready to rank and store."""

    screen: ScoredScreen
    hours: float
    bucket: str
    rank_in_bucket: int | None = None
    overall_rank_30d: int | None = None
    public_top_ten: bool = False
    shadow_directional: bool = False


@dataclass
class ScanResult:
    scan_id: str
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    pagination: PaginationReport
    funnel: DiscoveryFunnel
    analysed: list[AnalysedMarket] = field(default_factory=list)
    scoring_excluded: list[dict] = field(default_factory=list)
    status: str = "ok"

    @property
    def directional(self) -> list[AnalysedMarket]:
        return [a for a in self.analysed if a.screen.direction in ("up", "down")]

    def bucket_counts(self) -> dict:
        out: dict[str, dict] = {}
        for b in PRIMARY_BUCKETS:
            members = [a for a in self.analysed if a.bucket == b]
            direc = [a for a in members if a.screen.direction in ("up", "down")]
            out[b] = {
                "eligible": len(members),
                "directional": len(direc),
                "public_top_ten": min(PUBLIC_TOP_N, len(direc)),
                "shadow_directional": max(0, len(direc) - PUBLIC_TOP_N),
            }
        return out


def _rank(members: list[AnalysedMarket]) -> None:
    """Assign 1-based ranks over ALL directional members by Research Priority desc (tie-break by
    strength desc, then market id), and flag the public top ten + shadow. Ranking is over the full
    set, never a pre-sliced ten (prompt section 5)."""
    directional = [a for a in members if a.screen.direction in ("up", "down")]
    directional.sort(
        key=lambda a: (-a.screen.research_priority, -a.screen.strength, a.screen.market_id)
    )
    for i, a in enumerate(directional):
        a.rank_in_bucket = i + 1
        a.public_top_ten = i < PUBLIC_TOP_N
        a.shadow_directional = i >= PUBLIC_TOP_N


class CompleteScanService:
    def __init__(self, market_service, data_api, *, gamma: GammaClient | None = None):
        self._market_service = market_service
        self._data_api = data_api
        self._gamma = gamma

    async def discover(self, *, max_pages: int = 1000) -> tuple[list[Market], PaginationReport]:
        """Complete paginated discovery of the active-open universe, normalised to Markets."""
        gamma = self._gamma or GammaClient()
        owns = self._gamma is None
        try:
            raw, report = await gamma.paginate_markets(
                active=True, closed=False, page_size=100, max_pages=max_pages
            )
        finally:
            if owns:
                await gamma.aclose()
        markets: list[Market] = []
        for r in raw:
            m = normalize_market(r)
            if m is not None:
                markets.append(m)
        return markets, report

    async def run_scan(
        self, *, now: datetime | None = None, max_pages: int = 1000
    ) -> ScanResult:
        started = now or utcnow()
        markets, report = await self.discover(max_pages=max_pages)

        funnel, eligible = build_funnel(markets, started)
        funnel.raw_records = report.raw_items
        funnel.duplicates_removed = report.duplicates_removed
        funnel.pagination_complete = report.complete
        funnel.pagination_reason = report.incomplete_reason

        # Score EVERY eligible market (not a top-N). Enrichment is bounded-concurrency inside the
        # market service.
        eligible_markets = [m for m, _e in eligible]
        elig_by_id = {m.id: e for m, e in eligible}
        pairs, _mode = await self._market_service.enrich_market_list(
            eligible_markets, requested_mode="live"
        )
        analysed: list[AnalysedMarket] = []
        scoring_excluded: list[dict] = []
        scored_ids: set[str] = set()
        for market, analytics in pairs:
            ss = await score_screen(market, analytics, self._data_api, live=True, now=started)
            e = elig_by_id.get(market.id)
            if ss is None or e is None or e.bucket is None:
                scoring_excluded.append(
                    {"market_id": market.id, "reason": "no usable point-in-time token data"}
                )
                continue
            scored_ids.add(market.id)
            analysed.append(AnalysedMarket(screen=ss, hours=e.hours, bucket=e.bucket))
        # Eligible markets that could not be enriched at all are honestly recorded as excluded.
        for m in eligible_markets:
            if m.id not in scored_ids and all(m.id != x["market_id"] for x in scoring_excluded):
                scoring_excluded.append(
                    {"market_id": m.id, "reason": "enrichment unavailable"}
                )

        # Per-bucket ranking over ALL directional members, plus an overall 30-day ranking.
        for b in PRIMARY_BUCKETS:
            _rank([a for a in analysed if a.bucket == b])
        overall = [a for a in analysed if a.screen.direction in ("up", "down")]
        overall.sort(
            key=lambda a: (-a.screen.research_priority, -a.screen.strength, a.screen.market_id)
        )
        for i, a in enumerate(overall):
            a.overall_rank_30d = i + 1

        finished = utcnow()
        status = "ok" if report.complete else ("incomplete" if report.offset_cap_reached
                                               or report.repeated_page_detected else "partial")
        scan_id = f"scan-{started.strftime('%Y%m%dT%H%M%S')}-{int(started.timestamp()) % 100000}"
        return ScanResult(
            scan_id=scan_id, started_at=started, finished_at=finished,
            duration_seconds=(finished - started).total_seconds(),
            pagination=report, funnel=funnel, analysed=analysed,
            scoring_excluded=scoring_excluded, status=status,
        )

    def result_summary(self, result: ScanResult) -> dict:
        f = result.funnel.as_dict()
        f["scoring_excluded"] = len(result.scoring_excluded)
        return {
            "scan_id": result.scan_id,
            "started_at": result.started_at.isoformat(),
            "finished_at": result.finished_at.isoformat(),
            "duration_seconds": round(result.duration_seconds, 2),
            "pagination": result.pagination.as_dict(),
            "funnel": f,
            "analysed": len(result.analysed),
            "directional": len(result.directional),
            "bucket_counts": result.bucket_counts(),
            "status": result.status,
            "model_version": MODEL_VERSION,
            "calculation_version": CALCULATION_VERSION,
        }
