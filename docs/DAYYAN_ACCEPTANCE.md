# Dayyan acceptance review (spec §2, §18)

Reviewer acting as Dayyan (wrote the requirements, manually tested the product). Evidence is from
**running the product** (live Opportunity Board, `/api/opportunity/diagnostics`, live Replay
reconstruction, live confidence measurements) plus code inspection, not developer summaries.
Branch `arepo-final-gap-closure`. Gates at review time: backend **303 pass** / ruff clean /
idempotent bootstrap; frontend tsc + lint clean, **14 vitest**, production build compiled.

Legend: **Pass** (verified with evidence) · **Blocked** (genuine external dependency, exact steps
given) · **Fail** (not acceptable).

| # | Requirement | Route / feature | Evidence | Verdict |
|---|---|---|---|---|
| 3 | Broken "Full definition" removed | Tag popovers | `grep "Full definition"` = 0 refs; TagChip is a self-contained popover; the missing anchors (trade-flow, wallet-concentration, trade-timing) no longer linked; all 18 MetricHelp links resolve to real anchors | **Pass** |
| 4 | Directional views on a useful subset | Board, `/diagnostics` | Live: 28/60 screened (47%) receive a directional view; n_families 1→16, 2→25, 3→9 | **Pass** |
| 4 | Coverage disclosed | Board header | "Arepo screened N markets; M currently meet the requirements for a directional view" line; `/diagnostics` reports coverage | **Pass** |
| 4 | Abstentions only where justified | Market page, gate | `has_directional_view` requires a resolved direction AND (moderate strength OR price family); truly flat markets abstain | **Pass** |
| 10 | Filter state persists | Board, Explore | Filters URL-backed (`useUrlState`); `lib/url-state.ts` with 6 vitest cases (round-trip, default-removal, independence, shared-link, Back/Forward, clear-all). Full Playwright E2E not set up (noted) | **Pass** |
| 8 | Confidence not universally 100% | Board, `/diagnostics` | Live before→after: max 1.00→**0.80**, %==100% 10%→**0%**, %>90% 14%→0%, median 0.76→0.52. 100% now needs perfect data + ≥3 families + all components | **Pass** |
| 8 | Confidence is historical in Replay | Replay | Reconstructed entries show ~0.30 confidence, computed from cut-off information (price-only), not current confidence | **Pass** |
| 9 | Missing components wired or honestly removed | Board, Signal Lab, `/diagnostics` | Wired into the live enrich path (was 0/40; ~12/16 once a series accumulates); honest reasons instead of dashes; `docs/component-availability-audit.md` | **Pass** |
| 5 | Replay regression explained | doc | `docs/replay-regression-investigation.md`: both the ~50%/4 and 0%/3 samples are statistically inconclusive; kept the causal behaviour; regression tests lock invariants | **Pass** |
| 6 | Replay shows top-five | Replay | Live at -7d: 160 candidates → 6 eligible → **5 selected**; each shows entry, moves, direction, outcome | **Pass** |
| 6 | More historical cut-offs | Replay | Selector: 24h / 3 days / 7 days / 14 days / 30 days | **Pass** |
| 6 | Small sample not presented as proof | Replay | Inconclusive banner when below the meaningful minimum; `sample_verdict`; Wilson 95% intervals shown | **Pass** |
| 6 | Baselines shown | Replay | "Arepo vs baselines" table (no-change / momentum / always-up / always-down) with hit rate + CI; live: Arepo 3/5 = momentum 3/5 = always-down 3/5 → no edge, inconclusive | **Pass** |
| 7 | Replay modes explained | Replay | Prospective / Reconstructed / Synthetic badged and explained; never mixed in one metric | **Pass** |
| 11 | How It Works left menu | How It Works | Sticky `SectionMenu` with all 11 sections | **Pass** |
| 11 | Menus independently scroll | How It Works, Methodology | `overflow-y-auto` + `overscroll-contain`; both pages use the shared component | **Pass** |
| 11 | Menu text darker | menus | `text-arepo-ink2` (was muted); active item accent-highlighted via IntersectionObserver | **Pass** |
| 11 | Cards smaller | How It Works | Card padding p-6/p-7 → **p-5**, smaller headings, tighter spacing | **Pass** |
| 12 | Why Arepo moved to sign-in | How It Works, auth pages | Brand paragraph removed from How It Works; now on all auth pages | **Pass** |
| 12 | Large logo + supplied wordmark | Sign-in/up/reset | 72px grid symbol + the supplied `AREPO Typeface (word).png` (red mark under A), not a substitute font | **Pass** |
| 13 | Signal Lab / Market Detail / Replay consistent | Signal Lab, Market Detail | One shared gate (`lib/directional.ts`) used by both; Signal Lab shows "Qualifies for a directional view" vs "Observational only" + reason; Yes/No consolidated to one per market | **Pass** |
| 14 | Data-consistency checks | `/diagnostics`, tests | `analytics/consistency.py` + 7 tests; wired into diagnostics (`consistency_warnings`); invariant guard that the model can't emit 100% on one family | **Pass** |
| 16 | Production login works | deployed | Account system works locally end-to-end (register→verify→login→prefs→save→delete, prior smoke); **production** needs the hosts below | **Blocked** |
| 16 | Production emails work | deployed | Resend provider implemented; needs a Resend account + verified sender | **Blocked** |
| 16 | Production schedules work | deployed | 7 idempotent UTC crons in `render.yaml`; needs a Render account | **Blocked** |
| 16 | Vercel frontend live | deployed | `vercel.json` ready; needs a Vercel account | **Blocked** |
| 16 | Backend live | deployed | `render.yaml` ready; needs a Render account | **Blocked** |
| 16 | No localhost-only assumptions | build | API base is `NEXT_PUBLIC_API_BASE` (localhost only as a dev fallback); documented | **Pass** |

## Summary
No requirement is **Fail**. Everything achievable locally is **Pass** with running-product evidence.
The remaining items are **Blocked** solely on the user creating the external accounts (Vercel,
Render, Supabase, Resend) and setting secrets - the exact, unavoidable login/billing step. The
step-by-step external checklist is in `docs/deployment.md` §"Production deployment" and the final
report. Per §18, completion is not declared for the Blocked deployment items; all local work is
complete and verified.
