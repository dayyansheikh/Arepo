# Dependence clustering analysis, 2026-10-11 (design-time; no model performance used)

Question: is the giant dependence group a real dependence unit or a series-label artefact? Two uses depend on it:

- (a) the MC1 co-primary cluster (i) in `MULTI_SIGNAL_PIPELINE_DESIGN.md` section 4;
- (b) D120 group-disjointness (`fs2-dependence-groups-v2`).

Nothing here fits, scores or reads a model. The only outcome quantities are 2h Gamma mid changes, used as dependence
proxies. Reproduce with `cd backend && python scripts/dependence_clustering_analysis.py --out <report.json>`. The run takes
33 s with a peak RSS of 0.85 GB, and the script refuses to run while a collector process is active.

## 1. Data and method

- **Facts:** snapshot `20261011T123356Z_9cd3cdb9`, `rows.csv.gz` plus the `rows_ext.csv.gz` sidecar (needed columns only):
  event ids, series slugs, `neg_risk_market_id`, fee category and end date. It holds 249,719 markets and 22,128 events.
- **Parent links:** the sidecar has no `parentEventId` and no event slugs. Both come from the D118 frame
  (`fs2_capture_52eead5d...`), streamed one page at a time (183 MB). They cover 95.5% of markets. Events created after
  the frame (about 2h earlier) have no parent information.
- **Periods:** two consecutive complete 2h periods, `081844Z -> 103157Z -> 123356Z` (Sunday 08:18 to 12:33 UTC). Rows come
  from `panel.build_pair` (ML eligibility, Gamma mid): 91,544 market-period rows with facts, 319 rows dropped.
- **Proxies:** `dmid` (signed), `|dmid|` and `moved` = 1{|dmid| > 0.005}, the ML flat band. `moved` is an activity proxy
  close to the 3-class label.
- **Centring (residual proxy):** each proxy is centred within the cell period × fee category × time-to-end band × spread
  band × liquidity band × mid band. This removes what a price/time model would explain. Period × fee centring is shown
  as a secondary.
- **Design effect** `DE(C) = V_C / V_event`, with `V_C = sum over clusters of (sum of centred values)^2`. Clusters are pooled
  across both periods, as the MC1 bootstrap resamples them. A DE above 1 is covariance across the finer units that `C`
  captures.
- **Permutation null** (300 permutations, seed 116): within each fee category, the series label (or series × day label) is
  shuffled across base clusters, keeping the number of base clusters per label. The p-value floor is 0.0033.
- **Size-based effective clusters:** `G_eff = (sum n)^2 / sum n^2`.
- **Variance-estimator d.f.:** `nu = 3 (sum S^2)^2 / sum S^4`, which measures how many clusters actually drive the
  cluster-robust variance.
- **Definitions** (all built with `pairing.dependence_groups`):

| name | links |
|---|---|
| `event` | event id (MC1 co-primary (ii)) |
| `outcome` | event ∪ parentEventId ∪ negRiskMarketID ∪ underlying token (D120 table, series + event slugs, all dates) |
| `fixture_day` | `outcome` ∪ series slug × UTC end date |
| `fixture_day_sidecar` | event ∪ negRisk ∪ series × UTC end date ∪ underlying × UTC end date. Computable from today's sidecar |
| `season_series` | event ∪ negRisk ∪ series slug ∪ underlying × UTC end date. Today's `ml_panel.dep_group`, asserted identical |
| `d120_v2` | event ∪ parentEventId ∪ series slug ∪ negRisk ∪ underlying (all dates). The D120 rule |

## 2. Cause of the chaining: one league-season label, not transitive chaining

- **One link per market.** Every market carries at most one series slug and exactly one event id: 211,806 have one
  series and 37,913 have none.
- **No cross-links.** No `negRiskMarketID` spans two events, and no event spans two series.
- **Few multi-series groups.** Only 7 groups hold two or more series. All are crypto, joined through underlying × date.
- **What the 5,743 groups are:** 1,009 single-series groups, 7 crypto multi-series groups and 4,727 series-less groups,
  each of which is one event.
- **The giant group is the single slug `nfl-2026`:** 86 events and 15,972 markets in the universe. It is 6.4% of the
  universe and 6.4% of the 43,429 ML-eligible markets at 12:33, where it holds 2,789 markets in 46 events across 7 end
  days.
- **Other league-season containers:** `fa-cup` (661 events), `cfb-2026` (221), and soccer leagues with 250 to 330 events
  each.
- **What the series link captures.** Polymarket splits one game into up to 4 events:
  - main lines, about 300 markets;
  - player props, about 200;
  - first-TD scorer, about 25;
  - a 5-market neg-risk event.

  43 of the 86 `nfl-2026` events carry `parentEventId` pointing to the main game event. For example,
  `nfl-phi-jax-2026-10-11-first-td-scorer` has parent 941330, whose kickoff is 13:30Z, the same as its satellites. Across
  the universe, 8,258 of 22,128 events have a parent, and 59.6% of markets sit in such an event.
- **Why the series is the only link today.** The ML sidecar has no `parentEventId`, so the season-level series slug is
  the only thing tying a game's events together. It does this by tying the whole season together.

## 3. Empirical dependence

**Design effect against `event`.** Residual-proxy centring first; period × fee centring in brackets.

| clustering | dmid | \|dmid\| | moved | nu (moved) |
|---|---|---|---|---|
| market | 0.12 (0.10) | 0.12 (0.10) | 0.33 (0.28) | |
| event | 1 | 1 | 1 | 576 (707) |
| event ∪ parentEventId | 1.03 (1.00) | 1.03 (1.02) | 1.27 (1.31) | 564 (516) |
| `outcome` | 1.03 (1.00) | 1.03 (1.02) | 1.27 (1.43) | 562 (290) |
| `fixture_day` | 1.47 (1.55) | 1.52 (1.77) | 1.68 (2.78) | 174 (38) |
| `fixture_day_sidecar` | 1.47 (1.55) | 1.52 (1.77) | 1.68 (2.69) | 174 (37) |
| `season_series` | 1.43 (1.62) | 1.54 (1.99) | 1.95 (3.11) | 133 (33) |

**Permutation tests of the series links** (residual-proxy centring). Each cell is the observed ratio, then [null mean,
null 95th percentile], then the p-value.

| link | slice | dmid | \|dmid\| | moved |
|---|---|---|---|---|
| season over `outcome` | sports (1,229 clusters) | 1.39 [1.00, 1.04] 0.003 | 1.50 [1.00, 1.05] 0.003 | 1.63 [0.98, 1.21] 0.003 |
| season over `outcome` | crypto | 0.84 [0.93, 1.57] 0.55 | 0.83 [0.92, 1.57] 0.52 | 1.00 [1.00, 1.38] 0.50 |
| season over `outcome` | all others | 0.99 [0.99, 1.05] 0.49 | 1.07 [1.01, 1.06] 0.03 | 1.03 [1.00, 1.03] 0.05 |
| series × day over `outcome` | sports | 1.42 [1.00, 1.03] 0.003 | 1.48 [1.00, 1.03] 0.003 | 1.37 [0.99, 1.14] 0.003 |
| season over `fixture_day` | all | 0.97 [1.00, 1.03] 0.84 | 1.01 [0.99, 1.06] 0.22 | 1.17 [0.99, 1.14] 0.04 |

**Between-game correlation within a series** (mean correlation of `outcome`-cluster sums, largest contributors):
`nfl-2026` 0.16 for `dmid` and 0.19 for `|dmid|` over 28 game clusters, carrying 68% and 51% of the excess; WTA 0.14 /
0.14 / 0.28 (`dmid` / `|dmid|` / `moved`); ITF 0.13 / 0.23; Premier League 0.40 (`dmid`); for `moved`, UEL 0.41, Brazil
Serie A 0.35, Argentina 0.36 and Bundesliga 0.57.

**Reading.**

1. **Within-event dependence is the dominant unit.** Market-level variance is only 0.12 of event-clustered for price
   moves (DE 8.5x) and 0.33 for activity (3x).
2. **Parent links add 27% for activity and about 3% for price moves.** The extra comes from game satellites.
3. **The season link captures real dependence in sports.** It sits at the **league-day** level: games of one league on
   one day co-move, at a correlation of about 0.13 to 0.57.
   - Series × day reproduces all of the season-level excess for `dmid` and `|dmid|` (sports: 1.42 and 1.48 against 1.39
     and 1.50), and about 60% of it for `moved` (1.37 against 1.63).
   - Beyond the league-day there is nothing for price moves, and 1.17x for activity (p = 0.04).
4. **Outside sports the series adds at most 1.07x.** The crypto series adds nothing beyond the underlying.
5. **Crypto underlying rule (all dates against token × date) is inconclusive.** The ratio is 0.73 to 1.07 under
   residual centring. It is 1.17 to 2.43 under period × fee centring, where time-to-end mixing is not removed.
6. **The category × period component looks like fixed effects, not shocks.** Category deviations persist across both
   periods.
   - For `dmid`, every non-sports category sits at -0.002 to -0.006 in both periods and sports at +0.0015.
   - The period-to-period change has |z| ≤ 1.8, except `|dmid|` for crypto (+3.2) and weather (-3.4).
   - Two periods cannot identify category-wide shocks.
7. **Heavy tails limit every definition.** Price-move proxies give nu of only 24 to 53 under every definition, even
   `event`. Percentile intervals on heavy-tailed losses may under-cover whatever the clustering. This is separate from
   the chaining.

## 4. K and largest-cluster share

The ML-eligible columns are per period at 12:33. "Pooled" is the two periods together; "new" is the number of clusters
first seen in period 1. The D120 population is open markets with Gamma liquidity ≥ 1000 and a scheduled end after the
snapshot (or unknown).

| definition | universe K (largest) | ML-eligible K | largest | G_eff | pooled K / G_eff / new | D120 pop. K (largest) |
|---|---|---|---|---|---|---|
| `event` | 22,129 (612) | 10,543 | 0.5% | 2,009 | 11,039 / 2,157 / 454 | 9,753 (0.5%) |
| event ∪ parent | 15,719 (633) | 8,864 | 0.5% | 1,234 | 9,019 / 1,254 / 407 | 7,946 (0.7%) |
| `outcome` with underlying × date | 13,406 (633) | 6,796 | 1.1% | 913 | 6,948 / 989 / 210 | 5,798 (1.1%) |
| `outcome` | 13,301 (1,540) | 6,726 | 2.5% | 558 | 6,877 / 618 / 210 | 5,733 (2.8%) |
| `outcome` + crypto series | 12,021 (1,540) | 5,609 | 2.5% | 524 | 5,761 / 584 / 102 | 5,306 (2.8%) |
| **`fixture_day`** | 7,433 (9,422) | **4,791** | 5.4% | 171 | 4,878 / 170 / 49 | 4,077 (7.4%) |
| `fixture_day_sidecar` | 7,546 (9,422) | 4,868 | 5.4% | 194 | 4,955 / 189 / 49 | 4,150 (7.4%) |
| `season_series` (ML now) | **5,743 (15,972)** | 4,424 | 6.4% | 118 | 4,469 / 116 / 37 | 3,700 (9.7%) |
| `d120_v2` (D120) | 5,681 (15,972) | 4,378 | 6.4% | 115 | 4,422 / 114 / 37 | 3,657 (9.7%) |

Largest ML-eligible clusters: `fixture_day`, today's NFL games (28 events, 1 day); `season_series`, `nfl-2026` (46
events, 7 days); `outcome`, BTC + ETH up/down windows, merged by the two-token `eth-btc-hit-price-weekly` slug. The D120
rule reproduces the protocol's D118-frame figure closely: 3,657 here against 3,677.

## 5. Recommendation for ML inference (MC1 H1/H2)

**The season-level groups are conservative, not meaningless.** The largest cluster is 6.4% of rows, with G_eff 118 per
period. Their costs are:

- **no detectable dependence beyond the league-day for price moves** (season over `fixture_day`: 0.97 and 1.01);
- **fewer effective clusters:** G_eff is 118 against 171 per period;
- **growth across the window:** one NFL or EPL cluster absorbs every game day of a multi-day confirmation window;
- **K saturation:** a new game day of an existing series adds no cluster. This stalls the `K ≥ K*` stopping rule, which
  counts clusters, not information.

**Dropping series altogether under-clusters.**

- The candidate "event ∪ negRisk ∪ underlying × date, series only for shared underlyings" is the `outcome` row plus
  crypto series. It leaves the league-day dependence out. The variance is then understated by a factor of 1.39 to 1.63
  in sports and 1.38 to 1.53 overall, so the SE is understated by 17 to 28%.
- Series used only "when it implies a shared underlying" captures no extra dependence: the crypto series add 0.84 to
  1.00.

**Recommended:**

1. **Co-primary (i) becomes `fixture_day`.** Its links are:
   - event ids and `parentEventId`;
   - `negRiskMarketID`;
   - series slug × UTC end date (a `sd:<slug>|<date>` node, injected as an event id, as `ml_panel` does for `ud:`);
   - the D120 underlying token table on series and event slugs, across all dates.

   It keeps all of the season-level excess for price moves and about 60% for activity, with K = 4,791 and the largest
   cluster at 5.4% per period.
   - **Implementable now:** the current sidecar gives `fixture_day_sidecar` with practically identical design effects
     (K = 4,868).
   - **Next sidecar version:** add `events[].parentEventId` and event slugs (ext v3), to match D120 and to link satellites
     that have no series.
2. **Keep co-primary (ii), the event (market fallback).** It is dominated and rarely binds, but it costs nothing.
3. **Count K and set K\* under (i).** The development dry run must measure K accrual per game day. Within one day,
   `fixture_day` adds +49 clusters per period and `season_series` +37.
4. **Keep the per-period sign gate.** It is the only guard against category × period shocks, which two periods cannot
   measure.

**Risk of under-clustering under `fixture_day`:**

| source | evidence here | handling |
|---|---|---|
| cross-day, same-series dependence | none for price moves; activity 1.17x, so the SE is understated by at most 8% | bounded by S1 and S3 |
| shared outcomes with no link | underlyings outside the token table (`bnb`, `hype`, `zec` up/down series); same team or candidate across series; the 4.5% of markets without parent information | not measurable |
| category-wide shocks | not identifiable from 2 periods | per-period gate, and S2 |

**Bounding the risk: pre-declared sensitivity analyses**, reported with every H1/H2 result:

- **S1:** the CI under `season_series` / `d120_v2`;
- **S2:** a two-way cluster-robust variance, clustering on (`fixture_day`, fee category × period), measured first in
  development on out-of-fold ΔLL;
- **S3:** `sqrt(V_season / V_fixture_day)` on the confirmation ΔLL, the SE inflation factor if season-level dependence
  were real. On these proxies it is 0.99 to 1.08.

If S1 or S2 includes 0 while (i) excludes it, the result is labelled **cluster-sensitive**. Whether that label blocks
"Supported" is a registration decision for `science-reviewer`. Making S1 gating reproduces today's conservative design.

## 6. Recommendation for D120 group-disjointness

**What a control needs** to be free of shared-outcome and interference links with the trigger and with every other
activated member, on this evidence:

- **a different event, `parentEventId` and `negRiskMarketID`:** mechanical or mutually exclusive outcomes, with
  within-event DE of 3 to 8.5x;
- **a different named underlying, on any date;**
- **a different series × UTC day:** games of one league on one day correlate at about 0.13 to 0.57.

**Residual shared shocks.** Run-level and category-wide shocks remain shared, for example the crypto factor across BTC
and ETH. The protocol already says group-disjoint is not independent. Phase 4 must cluster by run.

**v2 is a strict superset of this requirement.** A season series contains every series-day, so it can only be stricter.
Over-clustering costs availability only:

- D120 population K is 3,657 against 4,077 for `fixture_day`;
- the largest group is 9.7% against 7.4%;
- each run can screen one `nfl-2026` member, not one per game day.

These costs are already priced into `D120_DESIGN_ESTIMATES.json` (3,677 groups, 127 drawable strata holding 96.1% of
eligible members), and they cannot produce a false PASS.

**Verdict: D120 does not need to change before its freeze.**

Non-blocking notes for later registrations:

- Phase 4 effect studies should not reuse v2 as their inferential cluster across runs, because season groups accumulate
  across runs. They should declare `fixture_day` × run.
- The D120 disclosure could name cross-underlying crypto co-movement as a residual.

## 7. Limitations

- **Narrow window.** There are two periods from one Sunday morning, with no NFL game in play and little weekday or
  in-play data. Run the script on the development window (≥ 36 periods, `--facts` / `--periods`) before the MC1
  registration.
- **Proxies are not ΔLL.** Proxies are outcomes, and ΔLL can have a different sign structure. The binding evidence is the
  development `sd_c` and the S2/S3 ratios on out-of-fold ΔLL.
- **Older parent source.** Parent links come from a frame about 2h older than the facts. Facts from one snapshot are
  applied to all three; series and event membership are static.
- **Few large clusters.** Permutation p-values floor at 0.0033. The design effects are driven by a few large clusters:
  `nfl-2026` carries 51 to 68% of the excess for price moves.
