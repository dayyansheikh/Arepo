# Complete universe discovery, Signal Lab and short-horizon methodology

_Branch `arepo-complete-short-horizon-universe`. Companion to
`docs/complete-universe-discovery-audit.md` (which proves why the old cohort was 60). This documents
what the complete-universe pass built and the honest meaning of each number._

## How complete pagination is proved

`GammaClient.paginate_markets` follows every offset page of `/markets?active=true&closed=false` until
the upstream signals completion (an empty or short final page). It records the page count, raw item
count, unique count and offset progression, detects a non-progressing page (only already-seen
markets) and the upstream's documented offset cap (HTTP 422 "use keyset"), and enforces an emergency
`max_pages` loop guard. A `PaginationReport.complete` flag is the single source of truth: it is True
only on genuine exhaustion. An offset cap, non-progression, retry exhaustion or guard trip leaves it
False with a reason, so a caller fails loudly and never treats a partial universe as complete. Eleven
unit tests (`test_gamma_pagination.py`) cover one page, many pages, a full first page with more
remaining (the exact old bug), 500+ records, cross-page duplicates, a repeated page, the offset cap,
retry success/exhaustion, the emergency guard and deterministic deduplication.

On the live Gamma deployment the offset path caps at 2100 markets and the `/markets/keyset` cursor
does not advance, so a live scan honestly reports `pagination_complete=False` with the offset-cap
reason. This is surfaced, not hidden. See the audit for why the environment clock makes the within-30
day band sit beyond the offset cap.

## Why top ten is a display limit only

The complete-scan service discovers the full universe, applies the 30-day eligibility gate, scores
EVERY eligible market with the existing model, assigns each to its closing-time bucket, and ranks
each bucket over ALL its directional markets plus an overall 30-day ranking. The public top ten is a
flag on the stored rows (`public_top_ten`), and the rest are flagged `shadow_directional`. Nothing is
sliced away before analysis or ranking. Signal Lab shows the caption "Top 10 shown from N eligible
markets" so ten is never read as the number analysed. A real scan analysed 181 eligible markets and
83 directional signals; the public list shows ten per bucket while all 181 are stored and rankable.

## Why public analysis stops at 30 days

Eligibility (`discovery/eligibility.py`) is a backend rule applied before scoring: a market is
eligible only if it is active, not closed, has a valid close time, has more than zero and no more
than 30 days remaining, and has a resolvable tradable token. Markets closing more than 30 days out
never enter public Opportunities, Signal Lab, the public top ten or future public cohorts. This is
enforced server-side, not as a frontend filter.

## How short-horizon universes are constructed

Every eligible market is assigned to exactly one non-overlapping primary bucket from the close time
known at the scan timestamp: `closing_0_6h`, `closing_6_24h`, `closing_1_7d`, `closing_7_30d`, plus
the cumulative `all_0_30d`. Boundaries are inclusive at the upper edge (exactly 6h lands in the
0-6h bucket). Historical membership is never recomputed from the present time; the exact
`time_remaining_hours` and bucket are stored on each snapshot.

## How often signals refresh

The scheduled `arepo-signal-refresh` cron runs one complete scan every 5 minutes. A measured complete
scan took ~15-32 seconds for 181 eligible markets (book + trade enrichment for each), comfortably
inside 5 minutes, so 5 minutes was chosen with evidence rather than assumed. An advisory lease in
`discovery_scan_locks` prevents overlapping scans and recovers a crashed scan's stale lease. The
browser never scans; it only reads stored results.

## What strengthening and weakening mean; why strength is not probability

Trajectory (`discovery/trajectory.py`) is computed from stored snapshots. "Strengthening" means only
that the stored strength SCORE increased over the comparison period by more than the predeclared
stability threshold (0.02, i.e. 2 points on the 0-100 display scale, chosen from score precision and
jitter, not tuned to outcomes). It does NOT mean the outcome became more likely, that accuracy
increased, that expected profit rose, or that final resolution became more certain. Labels are New
signal, Strengthening, Weakening, Stable, Direction reversed, Temporarily unavailable and Stale. The
UI always shows the numeric change ("Strength 72, up 6 points over the last hour") and never
probability language.

## Why later signal changes cannot rewrite a frozen prediction

A later refresh only INSERTS new `discovery_signal_snapshots` rows (unique per scan+market+token); it
never updates or deletes an earlier snapshot or scan header. Trajectory and later-evolution views are
diagnostic layers over that immutable history. A frozen prediction's direction, strength and rank are
never rewritten by a later scan.

## How price outcomes, freeze-to-close, final resolution and executable performance differ

These are four separate questions and are never collapsed into one result: (A) short-term price
direction over 1h/6h/24h/7d; (B) freeze-to-close price direction to the last valid pre-close
observation; (C) final resolution (did the selected outcome actually resolve, shown only when a
genuine resolution is stored, "Closed, awaiting resolution" until then); (D) estimated executable
result after spread, fees, depth and slippage. A signal can be right for A and wrong for C, or right
for A but unprofitable for D. The prospective Replay product already separates short-term movement
from final resolution and reports executable performance separately.

## How repeated markets and related events affect denominators; why one cohort cannot establish edge

A market can appear in several scheduled cohorts and in many 5-minute snapshots. Repeated 5-minute
snapshots are history, not separate predictions, and must not be counted as independent evidence.
Replay denominators expose observation count, unique-market count and unique-event count so related
rows are never presented as fully independent. One cohort, on any horizon, is far below the
predeclared minimum sample and spans a single window and model version, so it cannot establish an
edge. Complete scanning and working Replay do not imply Arepo has an edge; they make the measurement
honest and complete.

## Server-side evaluation truth (API)

`/api/scan/status` (pagination completeness, discovery funnel, per-bucket counts), `/api/scan/signals`
(current signals by closing-time bucket and scope: public top ten, all directional, shadow, full
eligible universe, with server-computed trajectory), and `/api/scan/market/{id}/history` (snapshot
history + trajectory). Correctness, bucket membership, ranks, trajectory and completeness are computed
on the server; the frontend only renders them. Reads are deterministic and idempotent.

## Local manual commands

```
# one complete scan, appended immutably (overlaps refused, stale lease recovered)
python -m astrolabe.discovery.refresh_cli refresh
# latest stored scan status + funnel
python -m astrolabe.discovery.refresh_cli status
```

## Forward-looking (documented, not yet wired)

The complete-scan infrastructure (discovery, eligibility, buckets, full-universe ranking, append-only
snapshots, trajectory) is the foundation future prospective cohorts will freeze from. Wiring the
scheduled cohort freeze to consume the complete scan and store bucket membership on frozen entries,
plus freeze-to-close observation collection, is the remaining integration and is kept separate so the
existing historical 60-market cohort is never modified. The existing prospective Replay already
supports closing-window selection and separates short-term movement from final resolution.
