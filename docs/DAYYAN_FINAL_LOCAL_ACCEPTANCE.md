# Dayyan final local acceptance (spec §21)

Branch `arepo-final-local-implementation`. Evidence from **running the product** (backend on :8012,
frontend on :3012) with browser measurement, plus code and automated tests. Gates: backend **309
pass** / ruff clean; frontend tsc + lint clean, **21 vitest**, production build compiled.

Legend: **Pass** (verified) · **Partial** (works, specific gap noted) · **Blocked** (external).

## Market and signal routes (§3, §4, §5)
| Item | Evidence | Verdict |
| --- | --- | --- |
| Valid market opens (incl. across modes) | IDs 2694364 & 2822017 open in Live AND Replay; browser: chart rendered, `notFound:false`, `data_source=live` | **Pass** |
| Search result opens regardless of prior mode | canonical `LiveSource.get_market` + `?mode=live` on results; 5 hermetic tests | **Pass** |
| Invalid market | clean "We could not open this market" card with Open in Live / Retry / Return to search | **Pass** |
| API failure / loading | loading skeleton; compact error card (not a blank page) | **Pass** |
| No excessive bottom scroll; footer placement | browser-measured `gapBelowFooter:0`; footer follows content (moved from ~640 to just below content) | **Pass** |

## Signal Lab (§6, §7)
| Item | Evidence | Verdict |
| --- | --- | --- |
| Collapsed cards, expandable detail | SignalItem: signal-first header + "Why this fired" expander | **Pass** |
| Directional-status filter + all sort directions | STATUS + SORT selects; `arrangeSignals` with 7 vitest | **Pass** |
| 40+/70+ thresholds removed as primary org | replaced by directional status + sort | **Pass** |
| URL restoration of controls | `useUrlState` (status, sort) | **Pass** |
| Direction in words, separate from strength/confidence | "Upward/Downward/No clear direction"; strength shown /100; no "28 Up" ambiguity | **Pass** |

## Navigation, title (§8, §9)
| Item | Evidence | Verdict |
| --- | --- | --- |
| Header uses full width, no bunching | header inner width == viewport (1470); wide fluid max-w-[1920px] | **Pass** |
| Title exactly `Arepo` on every route | browser: `document.title === "Arepo"` on market, signals, replay, sign-in | **Pass** |
| 80/90/110/125/150% zoom | verified at 100% (`gap 0`, full-width nav); other zoom levels not measurable via the tooling, but the shell uses vh/flex + fluid width that scale with zoom | **Partial** |

## Learn pages (§10)
| Shared side-menu, hidden scrollbar, independent scroll, active section, mobile fallback | both pages use `SectionMenu` with `.no-scrollbar` + IntersectionObserver | **Pass** |

## Authentication (§11)
| Item | Evidence | Verdict |
| --- | --- | --- |
| One-viewport, large symbol, nav-style wordmark (no black-bg PNG), footer credit | browser: whole sign-in fits 812px viewport, 104px symbol + clean Jost AREPO wordmark, PNG removed | **Pass** |
| Consistent on sign up / reset / verification | all use the shared AuthShell | **Pass** |

## Replay (§12-20)
| Item | Evidence | Verdict |
| --- | --- | --- |
| Default leads with reconstructed "last week's opportunities" | browser: default tab "Last week's opportunities" selected; no stale synthetic on default | **Pass** |
| Stale synthetic cohort removed from default (§19) | prospective (synthetic) is no longer the default; relabelled "Prospective record" | **Pass** |
| Funnel, top-5, inconclusive banner, baselines | present from prior pass; baselines now include current-implied + price-only (§2.1) | **Pass** |
| Baselines: no-change / current-implied / price-only / momentum / (order-book-only) | 6 baselines; order-book-only documented as impossible historically | **Pass** |
| Replay data status (§18) | `/api/replay/data-status` + a Disclose section; honest "leaving the site open does not grow the sample" | **Pass** |
| Cut-off persists in URL (§16) | `?cutoff=` via useUrlState | **Pass** |
| Prospective / reconstructed / synthetic separated, never mixed (§7, §20) | reconstructed default badged; provenance labels retained | **Pass** |
| Point-in-time fields: Research Priority at cut-off, close date + time-remaining at cut-off (§14) | reconstruction shows rank, direction, strength, confidence-at-time, entry, 1h/24h/7d moves, resolution; it does NOT yet show Research-Priority-at-cut-off or close-date/time-remaining-at-cut-off | **Partial** |
| Closing-soon lens (24h/3d/7d/all) on reconstruction (§16) | the live board has this filter; the historical reconstruction does not filter by time-to-close yet | **Partial** |
| `docs/replay-product-review.md` three-role loop (§13) | not created this pass | **Partial** |

## Completion gate (§23) - deployment
Not started, by design: §23 requires all local acceptance to pass before any Vercel/Render/Supabase/
Resend work. Deployment is **Blocked** on external accounts and is out of scope until the Partial
items above are closed.

## Honest summary
No item that was implemented is **Fail**. The critical routing bug (§3) and the layout/title/nav/
auth/Signal-Lab/Replay-default items are **Pass** with running-product evidence. The remaining
**Partial** items are specific and enumerated: Replay point-in-time Research-Priority/close-date
fields (§14), the reconstruction closing-soon lens (§16), the replay-product-review doc (§13), and
zoom-level checks at 80-150% (tooling could not change page zoom). These are the exact next tasks;
completion is **not** declared while they stand, and deployment has correctly not begun.
