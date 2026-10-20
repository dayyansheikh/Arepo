# ruff: noqa: E501
"""Prospective public-data streams (docs/research_lab/NEW_STREAMS_2026-10-19.md).

Small, keyless, polite pollers for time-sensitive data that cannot be backfilled later: PredictIt and
Smarkets quotes (third / fourth crowds on the same political questions), ESPN-published sportsbook
lines, and the Polymarket rule text (Gamma serves only the current text). Data only: no statistic,
no outcome, no trading. Each stream writes change-only, receipt-timed JSONL under
``data-dumps/research_lab/stream_<name>/`` through ``common.ChangeLog``.
"""
