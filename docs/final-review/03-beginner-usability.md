# Agent 3 — Beginner usability

**Overall verdict: usable and mostly self-explanatory for a motivated novice; one persistent
misconception risk (Strength ≠ probability of being correct) to guard harder.**

## What worked (screenshots + copy)
- The one-line intro ("Arepo's public shortlist: the strongest directional signals across active markets
  closing within 30 days") + the grey disclaimer ("read-only research tool… not trading advice and does
  not predict outcomes. Read the methodology.") set expectations in ~10 seconds.
- YES/NO pricing is shown as "No · Closes 4d left" with direction (Down) — understandable.
- Progressive disclosure works: cards show a plain-English reason; "Details"/"Market detail" reveal more.
- **Confidence is framed honestly** ("Confidence 80%" chip, backed by `opportunity.ts`: a data-quality
  measure, not resolution probability). Good — low risk of the "Confidence = P(win)" trap.

## Confusion points
| Sev | Finding | Evidence | Fix |
|--|--|--|--|
| **Medium** | A novice may read **Strength 17/100** (or the red bar) as "17% chance the call is right." Nothing on the card explicitly says strength is *not* a probability. | Opportunities/Signal Lab cards | Add a one-line tooltip on the strength bar: "Strength is a signal-intensity score (0–100), **not** a probability of being correct." (metrics.ts already defines the term — surface it on hover.) |
| Medium | "Research Priority: High" — a beginner won't know what makes it High vs the strength number | card chip | One-line tooltip: "How strongly Arepo flags this for research attention (combines evidence breadth + strength)." |
| Low | Terms like "order-book pressure", "trade flow" appear before they're defined | chips | Link chips to the matching methodology anchor (metrics.ts links exist; ensure each chip is a help affordance) |
| Low | Replay's "moved as expected / against / no change" is clear, but "pending / unavailable = 50" may look like failure | Replay counts | Micro-copy: "Pending = outcome not due yet; Unavailable = no usable price at that time." |

## After 5 minutes, could I explain Arepo correctly?
Yes: "It scans prediction markets, flags ones with unusual directional pressure, ranks the strongest,
and keeps an honest scoreboard of whether its past flags moved as expected. It's research, not advice,
and doesn't predict who wins." The disclaimers make the "not a predictor" point land.

**Conclusion: ship-with-fixes** (the Strength-is-not-probability tooltip is the one that matters).
