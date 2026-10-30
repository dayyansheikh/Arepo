# LT8 challenger review R1 (science-reviewer, 2026-10-22 ~07:00Z)

Draft reviewed: `docs/research_lab/LIVE_TESTS_8.md` at 4552cec5 (sha256 4fa518c9…), branch `feat/live-tests-8`. Read-only
review; the record was saved and committed by the orchestrator (the reviewer session had no write tool). Context newer
than the draft's base (5ffe8229): LT6 closed with every test dropped at census (V, D, B, K); LT5 F, H, R dropped; E022
registered; LT7 text-frozen (840f4500…) and sealed (117e9b45…).

**Verdict: REVISE.**

## Must-fix
1. **LT6 has closed** (ledger "LT6 closed"). Remove the rule that drops CH203 if the freeze is not before `T_V`, in §0,
   the §1.1 table, §1.11, §8.3 and §12. Rewrite the §1.1 chain: LT7's window now depends on its own (a) and (c) rules,
   so the risk of sliding now comes from LT5 J/O. Note that the LT6-V entry in the `book0` token lapses (config.py:83).
   Disclose that the counts behind LT6's census deaths have been read, including V's within-correlation of 0.595. Rule:
   CH203's `VIF_w <= 2.0` gate stays exactly as drafted.
2. **LT7's census outputs will come before LT8's freeze.** LT7's censuses q0602-q0604 have not run yet; `seals/` has no
   CC7/CS7 output. They count the same sealed files and similar populations, so §1.6's "every threshold stated before"
   is false until the freeze. Declare now that the R1 response may only apply this review's items. Any other change to a
   gate, filter, planning count or expected fate after the LT7 census commit is labelled *informed (LT7 census)*.
3. **CH204's MDE does not follow from its own chain (§4).** About 1,955 hot units a day x 21 days x 0.8 gives `n_1` ≈
   32,800, not 38,600. Recomputed MDE: **0.57c low and 0.40c high, not 0.53c and 0.37c.** §6.1 item 9's claim that the
   cap loss is included is false for CH204. Update §0, §10 and the prior odds.
4. **CH202's "0.67c at the count floor" uses the wrong count (§3).** It treats 201,600 as all movers. The gate defines
   201,600 as held plus fresh units, and with 15% class shares that gives about 0.33c. Correct the text; leave the gate
   unchanged.
5. **Vendoring order contradicts itself.** §8.1 and §8.4 step 8 vendor LT7 functions only after LT7's pin, but the census
   code (steps 4-5) needs LT7's lag-slot loader and mid cache. Either vendor from the freeze-checked LT7 census-code
   commit with its hash, or make the censuses wait for LT7's pin.
6. **World 12 is not a null (Q9).** A real schedule that lasts one week satisfies the stated 7-day hypothesis. If world
   12 stays binding, a true effect can be labelled "SE check failed". Make it reported, and decide this now, before any
   size result exists.
7. **Worlds 3 and 5 give the control the exact true last-hour change.** The real `chg_1h` is computed by Gamma on an
   unpublished clock and basis. The binding worlds need a noisy, lagged (up to 60 min) last-trade proxy. Without that,
   "beyond the reversal" is not supported.
8. **CH203's fill confounder is overstated as "addressed" (§2).** Gamma omits `volume24hr` on 78% of rows
   (DESIGN_V1.md:345), so `dV_prev` is effectively absent for most units. World 8 must carry the census `vol_missing`
   share, or 0.78 if that is larger. The census should also print `vol_missing` against missing last-trade price.

## Should-fix
- **Daylight-saving time.** The census days (10-12..10-21) were on US and UK summer time; the window is on winter time. A
  US 8:30 ET release lands at 12:30Z, one minute before the 12:31 capture, during the census, but at 13:30Z,
  mid-interval, in the window. CH204's census gates are therefore not representative; disclose this.
- **The LT8 seal** must reproduce LT7's 159-entry `slots` map exactly, record the frozen LT8 design hash, and accept host
  copies that pass the hash check. Not confirmed: that the releases hold all 430 needed files.
- **Q14:** require at least 1.0 covered day in each sweep block. CH203 has 22 origins in block A and 19 in B; its F pairs
  split 13/10. Block A covers Thu-Sat and block B covers Tue-Wed.
- **CH204:** add a reported arm with slot x `fee_category` dummies; report the share of block-gate offsets that are
  multiples of 12, since those keep the slot alignment.
- Define "declared" in the gate rule `max(declared, design)`.

## Rulings on §11
- Q1: keep the target from k + 1 (`y_s`). Q2: accept sweep 1. Q3: placement OK; do not require the lag to be quiet
  (that would select on the price path after the target). Q4 and Q5: accept with item 8. Q6: keep the 0.8 correlation
  gate; item 7 applies. Q7: accept the 1c threshold and the 800-a-capture count gate; fix the text (item 4). Q8: accept
  the labels. Q9: item 6. Q10: partly; add the category arm. Q11: keep the cap; no cap for CH202. Q12: agree,
  conditional on the census. Q13: no drop rule for CH202. Q14: should-fix above. Q15: keep the dates. Q16: agree.
  Q17: agree; q0620-q0627 are unused in any ref.

## Checks that held
CH203's and CH202's MDE and F-MDE arithmetic; the seal origin counts 41 / 23 / 45 / 40; the LT7 hashes 840f4500 and
117e9b45; no seed collisions; every state comes before the origin.

## Not verified
Whether the data releases hold the needed files; E002/E004 status; LT7's last-input timing; host retention; what a
missing `volume24hr` actually means.
