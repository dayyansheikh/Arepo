# M1 (CH263) challenger R1 (science-reviewer, 2026-10-30; read-only, saved by the experiments autopilot)

**Verdict: GO_WITH_CHANGES.** Draft sha256 `54fd5d49…c0d6` verified. Payoff and cost convention correct; nothing fatal, but
two look-ahead or validity holes and one open design branch must be closed in the text before J0 runs.

**Checked and correct:** payoff `E = c - r_eff` (win `c`, loss `c-1`, split `c-0.5`); one cost convention (ask-based `c`
plus fee plus capital, no half-spread); ruling conditions 1, 2, 3, 5, 6 written in, no banned word; decision clock (sidecar
from the same Gamma page bodies as the rows, gap about 0; `c` from a touch recorded before `t_d` is stale, not look-ahead:
disclose); parser `parse_outcome` (resolved before split; `y = 1` iff outcome 0 won, `calibration.py:78-96`); read-out END +
31 days.

## MUST
1. **Catch-up look-ahead in J1 (9.2, l. 270-274).** Require strictly chronological processing; the state file at k holds only
   captures before k; synthetic tests for both; a breach is a named void case under 11.2.
2. **E3 look-back of 24 h (l. 106).** Whether `uma_resolution_statuses` keeps history is unverified; a dispute reset and a new
   proposal days later would re-enter as a new unit. Extend the look-back to every retained pre-window capture (at least
   84). J0 counts the forms the status string takes (both tokens present; proposed -> empty transitions), counts only.
3. **`T_U` is not the bound it claims (7.2).** (a) Clopper-Pearson on each stratum's event rate bounds an event-weighted share;
   the unit-weighted worst case `sum n_e I_e / N_s` is larger if bigger events reverse more often. (b) Adding three 95% bounds
   is not a 95% bound. Fix: stratify on final-state units per event (1, 2-3, 4-9, 10+), state the within-stratum homogeneity
   assumption, use level `1 - 0.05/S` per stratum; print the 10 largest events' unit counts.
4. **Close J0 rule (c) (l. 265): no dedicated book fetch** (a new collector before 11-22, and its receipt would move `t_d` past
   the touch). Sweep coverage depends on price by construction (`bid > 0`, `ask < 1`, spread <= 0.10, mid in [0.02, 0.98],
   `end_date` > receipt + 3 h; `panel.py:14, 53-63`; `forecast.py:32`), so capacity is printed with the covered subset's
   S6/S7 composition, labelled not the population's.
5. **Population wording (13, l. 333; the ledger form).** Add: only units two-sided at k (readable 1,518 of 6,244 = 24%), and
   only proposals seen at a 2 h capture (lagged seen share 735 / 1,735 non-sports resolutions on 10-23). Restore CH263's
   survivorship line as a count-only read-out line. `theta_low` and `theta_W` in the same ledger line as `theta`.
6. **Ruling condition 4 not met at source.** `CREATIVE_HYPOTHESES_2026-11-02.md:820-822` counts "CH263 0.7" inside "about 1.8";
   add a ledger correction entry (about 0.9 without M1/M2, by that file's own figure).
7. **L2 cannot be computed as written.** `costs.taker_rate` returns 0 whenever `fees_enabled is False` (`costs.py:91-92`); the
   text must say L2 is called with `fees_enabled=None`.

## SHOULD
1. Rows columns are `best_bid` / `best_ask`, not `bid` / `ask` (3.1).
2. S6 cell `> 0.10` is empty by construction (mid >= 0.90 means `ask_f` >= 0.90); label it structural.
3. Among ladder members S3 equals S5; say so.
4. Restore CH263's declared world S47 (the proposal flag lagging the on-chain proposal by one capture, lowering `c`) as a
   disclosure.
5. J0 prints the unavailable classes by category (`no_k_minus_1_row` 1,552, `no_previous_capture` 1,576, scope unclear).
6. Cross-event dependence (same news day) is handled only by the day-block sensitivity; state it.

## Designer's questions
1. No dedicated fetch (MUST 4). 2. Rows' touch only; sweep `best_ask` a descriptor with an agreement table on the covered
subset (switching price source by coverage would select on price). 3. Accept the read-out's own fetch and pinned parser;
floor 0.95 of units and events fine. 4. L1 headline (the ruling's conservative fee); L2 feeds `theta_low`. 5. No (MUST 3).
6. 31 days + `theta_W` + the 2% coarse rule is enough. 7. 24 h not long enough (MUST 2). 8. Category from capture k's own
sidecar. 9. Accept thresholds; `T_U <= 0.30c` needs about 1,000 final-state events, so "coarse" is likely: disclose in advance.

## Feasibility
Streams exist (sidecar status field since 10-11; book sweep; 8-day retention). J0, J1 (host cron hook, apart from multi-GB
jobs), J2, J3 and A must be written, tested and deployed by 11-21: tight but feasible. Sweep coverage probably far below 50%
(median half-spread at k 0.0005 suggests most units at mid above 0.98).

**Could not verify:** host retention, disk, cron, pass health; UMA status history; Gamma best ask vs CLOB book; events per
unit; the 1,552 count's scope; `labels.fetch_resolutions` batch behaviour.
