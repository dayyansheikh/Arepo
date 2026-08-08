# Final review — method note

The governing spec (§14) asked for 8 independent Sonnet review agents. Eight were launched in
parallel against the live staging instance + source, but all eight were terminated early by a
**session usage limit** before any wrote its report (`docs/final-review/` was empty on resume).

Rather than re-spawn eight heavy parallel agents (which is what tripped the limit and would likely
fail again), the **Opus lead conducted the eight-dimension scrutiny directly** via targeted code
inspection of the running staging system and source. These reports are therefore lead-authored, not
independently-agent-authored. That is a genuine reduction in independence and is stated plainly here
so no reader over-credits the reviews. Findings are grounded in `file:line` evidence and the reviews
are deliberately self-critical (the spec forbids vague praise / fabricated alpha).

Staging system reviewed: API `http://localhost:8000` (copy of the genuine DB — the real
`backend/astrolabe.db` was never touched), frontend `http://localhost:3000`, at commit `69425f1`.

Reports: 01 quant/research · 02 market-user · 03 beginner · 04 UI/design · 05 security ·
06 reliability/SRE · 07 data-integrity · 08 portfolio/hiring · FINAL_REVIEW_SYNTHESIS.
