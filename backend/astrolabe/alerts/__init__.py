"""Opt-in research email alerts.

Honest, non-personalised research signals only: never buy/sell/stake, never a promise of
profit, never certainty. Provider-neutral with a console sink by default; external sending
stays disabled until explicitly enabled and configured via environment variables (never
hardcoded). Includes eligibility gating, deduplication, per-market cooldown, alert history,
retry handling, failure logging and a test mode.
"""
