# Dependence clustering analysis, 2026-10-11 (design-time; no model performance used)

Question: is the giant dependence group a real dependence unit or a series-label artefact? Two uses depend on it:

- (a) the MC1 co-primary cluster (i) in `MULTI_SIGNAL_PIPELINE_DESIGN.md` section 4;
- (b) D120 group-disjointness (`fs2-dependence-groups-v2`).

Nothing here fits, scores or reads a model. The only outcome quantities are 2h Gamma mid changes, used as dependence
proxies. Reproduce with `cd backend && python scripts/dependence_clustering_analysis.py --out <report.json>`. The run takes
about 4.5 minutes with a peak RSS below 0.9 GB, and the script refuses to run while a collector process is active.

## 1. Data and method

- **Facts:** snapshot `20261011T123356Z_9cd3cdb9`, `rows.csv.gz` plus the `rows_ext.csv.gz` sidecar (needed columns only):
  event ids, series slugs, `neg_risk_market_id`, fee category and end date. It holds 249,719 markets and 22,128 events.
- **Parent links and event titles:** the sidecar has no `parentEventId`, event slugs or titles. They come from the D118 frame
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
- **What the series link captures.** Polymarket splits one game into up to 4 events (main lines about 300 markets,
  player props about 200, first-TD scorer about 25, a 5-market neg-risk event). 43 of the 86 `nfl-2026` events carry
  `parentEventId` pointing to the main game event (e.g. `nfl-phi-jax-2026-10-11-first-td-scorer` has parent 941330,
  kickoff 13:30Z like its satellites). Across the universe, 8,258 of 22,128 events have a parent (59.6% of markets).
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

**The season-level groups are conservative, not meaningless** (largest cluster 6.4% of rows, G_eff 118 per period).
Their costs: no detectable dependence beyond the league-day for price moves (season over `fixture_day`: 0.97 and 1.01);
G_eff 118 against 171; one NFL or EPL cluster absorbs every game day of a multi-day window; and K saturates (a new game
day of an existing series adds no cluster), which stalls the `K ≥ K*` stopping rule.

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
     (K = 4,868). Implemented in `ml_panel` at `c2079dc` (`dep_group`; season kept as `dep_group_season`).
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
Over-clustering costs availability only (D120 population K 3,657 against 4,077 for `fixture_day`; largest group 9.7%
against 7.4%; one `nfl-2026` member per run), already priced into `D120_DESIGN_ESTIMATES.json` (3,677 groups, 127
drawable strata holding 96.1% of eligible members); it cannot produce a false PASS. Section 8 covers non-sports drivers.

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

## 8. Non-sports links (follow-up, same data and method)

The question here is whether shared drivers outside sports need grouping. The D120 economics pair is the motivating
case: ECB 2026 rate cut (`999108`) against Eurozone 2026 inflation 1.6-1.8% (`1124260`). These are separate events with
`economic_group_status: unresolved`.

**Link sources:**

- **Gamma tags: not captured anywhere.** They are not in the snapshot rows or the sidecar. In the `/markets/keyset`
  payload, none of 240,531 market objects (nor their events) carries `tags`. In this codebase tags come only from
  `/events/keyset`: `BoundedDiscovery` attaches them as `_arepo_event_tags` (`ingest/normalize.py`).
  - **Capturing them without new requests:** join, by event id and capture time, the event-keyset tags that the
    complete-universe scan already fetches.
  - **Store the link fields the markets payload already delivers but the sidecar drops:** `parentEventId`, event
    title/slug/ticker, `resolutionSource`, series `recurrence` and `eventMetadata` fixture ids and league.
  - Adding `/events/keyset` to the snapshot loop would mean new requests, about 1 per 100 events.
- **Entities** come from a deterministic dictionary plus regex on the **event title**, not on question text.
  - Each event gets one label, so events never chain.
  - The dictionary covers 13 economies or central banks, 16 crypto/finance assets, 11 AI/media organisations, 14
    people, 7 geopolitical theatres, weather city, a ticker in parentheses, and US elections (district, House, Senate,
    governor).
  - Coverage of markets: weather 83%, crypto 74%, finance 71%, politics 70%, geopolitics (fee `unknown`) 69%,
    economics 63%, culture 32%, tech 23%.
- **Further candidate links:** entity × UTC end day; the economy label alone ("economic driver"); resolution-source
  domain; and exact end timestamp. negRisk and parent links are already in `fixture_day`.

**Measurement.** Each link merges `fixture_day` clusters within one fee category. The baseline is the label-permutation
null: random groupings of the same sizes.

Only rows with an observed 2h dmid enter. Markets with no co-movement data are excluded, among them the Eurozone
inflation market, whose mid of 0.0065 is below the 0.02 floor. Its ECB counterpart has 2 rows.

Results use residual-proxy centring. Each cell is the ratio, then [null 95th percentile], then the p-value; labelled
cluster counts are in brackets.

| category | link | dmid | \|dmid\| | moved |
|---|---|---|---|---|
| politics (1,268) | entity (mostly US elections) | 0.27 [0.83] .61 | 6.76 [5.41] .003 | 10.0 [7.82] .003 |
| politics (1,827) | same end timestamp | 0.94 [1.57] .19 | 4.20 [1.42] .003 | 8.41 [1.41] .003 |
| economics (110) | entity | 0.76 [1.25] .82 | 0.88 [1.25] .66 | 0.93 [1.18] .45 |
| economics (67) | economic driver | 0.75 [1.11] .78 | 0.87 [1.30] .86 | 0.88 [1.16] .57 |
| economics (130) | resolution source | 1.11 [1.28] .17 | 1.19 [1.30] .11 | 1.04 [1.31] .29 |
| finance (240) | same end timestamp | 1.54 [1.55] .06 | 1.33 [1.52] .13 | 1.97 [1.53] .02 |
| crypto (198) | resolution source (cross-underlying) | 1.12 [1.42] .12 | 1.80 [1.71] .03 | 2.13 [1.56] .01 |
| crypto (44) | entity (adds bnb/hype/zec...) | 1.14 [1.87] .38 | 1.16 [1.49] .19 | 1.04 [1.38] .34 |
| weather (157) | city | 1.17 [1.23] .10 | 1.24 [1.16] .01 | 0.92 [1.23] .68 |
| weather (157) | city × day | 1.02 [1.08] .33 | 1.08 [1.06] .03 | 1.02 [1.09] .37 |
| culture (118) | resolution source | 1.33 [1.21] .02 | 2.19 [1.20] .003 | 1.51 [1.44] .03 |
| geopolitics (258) | entity | 0.50 [1.57] .98 | 0.45 [1.66] .93 | 0.68 [1.55] .64 |

Tech shows nothing on any link (p ≥ .08).

**Reading:**

1. **Directional co-movement across events is absent for every non-sports link except culture's shared source** (1.33).
   Economics and the economic-driver link show none (0.75 to 0.93). That is low power, not independence: these are two
   Sunday periods with no macro releases.
2. **Activity co-movement is strong for US elections**, whether linked by shared entity or by resolution time.
   It is moderate for crypto windows that share a resolution source across underlyings, and for culture's shared
   source. It is weak for weather city and finance end time.
3. **Only politics (activity) and culture (source) clearly beat the null.** About 100 tests were run, so about 5 false
   positives at p < 0.05 are expected; the remaining hits are marginal.
4. **Non-sports markets carry little of the panel variance.** Under `fixture_day`, politics holds 0.3% (dmid), 0.5%
   (`|dmid|`) and 7.2% (`moved`); every other non-sports category holds at most 1.1%.
   - So the small links change pooled variance by at most 0.4%. Within their categories they matter: culture's source
     link gives 1.33 / 2.19 / 1.51, weather city × day 1.02 / 1.08 / 1.02.
   - The exception is the politics block on activity: grouping by entity raises panel variance 1.62x for `moved`, and
     not at all for dmid or `|dmid|`.
5. **Giant non-sports groups cannot be measured with cell centring.** A cluster spanning whole cells has its sum removed
   by the centring: the crypto-wide ratio is 0.01. Their dependence must be measured on ΔLL, through S2.

**Groupings.** All add links over `fixture_day`; figures are ML-eligible at 12:33 and the D120 population.

| grouping | added links | ML-eligible K (largest, G_eff) | D120 pop. K (largest) | D120 econ pair grouped |
|---|---|---|---|---|
| `fixture_day` | none | 4,791 (5.4%, 171) | 4,077 (7.4%) | no |
| **`category_aware`** | weather city × UTC day; culture resolution source | **4,682 (5.4%, 170)** | 3,984 (7.4%) | no |
| `+ economic driver` | + economy / central-bank label, all categories | 4,602 (5.4%, 164) | 3,914 (7.4%) | **yes** |
| `category_driver` | + politics end time, crypto window, finance end time | 2,489 (12.6% politics, 31) | 1,890 (13.3%) | no |
| `entity_all` | + any non-sports entity label | 2,840 (10.3% politics, 59) | 2,212 (11.2%) | yes |

**Recommendation:**

- **Co-primary (i) becomes `category_aware`:** fixture-day everywhere, plus weather city × day and culture resolution
  source. These links are evidence-backed and local, and they cost nothing: K falls 2% and the largest cluster is
  unchanged.
- **Sensitivity S4 (economic driver).** The evidence is weak, so this is a conservative sensitivity. It costs K -1.7%,
  so the registration may fold it into (i).
- **Sensitivity S5 (category driver):** the politics election-time block, cross-underlying crypto windows and finance
  end time.
  - The politics block is the strongest non-sports dependence, but only in activity, and it forms a 12.6% cluster
    (G_eff 31).
  - Report S5 with the cluster-sensitive label. It is better modelled as the second dimension of S2, driver block ×
    period.
- **Per-category results**, for example politics-only rows, must use S5.

**D120's economics pair.** The two markets share nothing that `category_aware` uses:

| | `999108` (ECB) | `1124260` (Eurozone inflation) |
|---|---|---|
| resolution source | ecb.europa.eu | ec.europa.eu |
| end date | 2027-01-01 | 2027-01-19 |

They also share no event, parent, negRisk or series, so under `category_aware` they stay in separate groups. Under S4
both are `econ:EA` and are grouped.

For Phase 4 disjointness, adding the economy label is cheap: D120-population K goes from 3,984 to 3,914, and it resolves
`economic_group_status` deterministically. The same dictionary matches the event slugs `ecb-rate-cut-in-2026` and
`eurozone-2026-annual-inflation` (with hyphens read as spaces), so it stays within D120's slug-only rule.
