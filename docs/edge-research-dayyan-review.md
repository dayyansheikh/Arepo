# Dayyan functional acceptance: edge-research (prompt section 16)

Acting as Dayyan, a non-technical owner, checking that the running product makes the research state
clear. Assessed against the live `/api/research/status` and the Replay "Edge-research status"
section (backend served the throwaway dry-run DB with three real frozen cohorts).

## The five questions the product must answer

1. **What is currently known?** The status shows real frozen cohorts by cadence (6h/daily/weekly),
   how many markets were frozen in total, how many are directional (public + shadow), how many are
   abstention controls, and how many outcomes are evaluable at each horizon. PASS.
2. **What is still unknown?** The edge banner states plainly: "Arepo has not yet accumulated enough
   prospective evidence to determine whether it has an edge. The system is collecting frozen
   predictions automatically." Calibration reads "Calibration unavailable...". PASS.
3. **How many real predictions exist?** Total frozen markets and directional signals are shown
   directly; the 24h "evaluable" count shows how many have a measured outcome yet (0 in the mid-
   period dry run, which is honest). PASS.
4. **Whether edge criteria are met?** A single unmissable banner: not supported. The 10 criteria are
   available via the API (`edge.criteria`), all honestly false except "frozen before outcome" and
   "thresholds unchanged". No positive claim is made. PASS.
5. **What data is being collected next?** The note explains the backend freeze and forward jobs grow
   the sample over days and weeks, and that leaving the site open does nothing. PASS.

## What a non-technical reader will correctly conclude

- Arepo is now recording real predictions before outcomes, at three cadences, across the whole
  screened universe (not just the visible top ten).
- It does not yet claim any edge, and it is explicit that it cannot until enough real outcomes exist.
- The system runs itself in the background once deployed.

## Honest limitations surfaced (acceptable)

- The current sample is empty of *evaluated* outcomes (the cohorts were just frozen); the product
  says so rather than showing a flattering number.
- Synthetic and reconstructed data are kept out of this surface entirely.

## Verdict

**Accept.** The running product makes the current state obvious and honest: what is known, what is
unknown, how many real predictions exist, that no edge is claimed, and what will be collected next.
It does not manufacture confidence from an empty sample.
