# ruff: noqa: E501
"""AREPO signal engine v1: continuously improving, prospectively scored forecasts (champion / challengers).

Design: ``docs/research_lab/signal_engine/DESIGN_V1.md`` (North Star: ``NORTH_STAR.md`` in the same folder).

Research tooling only. The engine measures forecast quality (log loss, Brier, calibration, AUC) out of sample and
prospectively. It makes no edge, profitability or trading claim, and it never places trades. The confirmation
programme (E-tests) is separate and unchanged; this package never reads their outcome files.

Modules:

* ``config``    constants (paths, grid, targets, eligibility, versions);
* ``store``     write-once parquet/JSON, append-only day logs, capture index, locks, disk guard;
* ``features``  per-capture slim quotes + feature rows (families market_state, momentum, flow, book, xvenue, wallet);
* ``labels``    direction labels from later captures, resolution labels from Gamma (explicit pending/unavailable);
* ``specs``     frozen model specs (sha256), registry, champion history;
* ``learners``  design matrices, logistic regression and LightGBM fits, numpy prediction, artifacts;
* ``training``  memory-safe walk-forward training frames (rolling window, per-capture caps, float32);
* ``predict``   write-once prospective predictions per capture and model;
* ``scoring``   streaming scorer, leaderboard, clustered bootstrap CIs;
* ``promotion`` the pre-declared promotion rule;
* ``walkforward`` the development/historical bootstrap (never mixed with prospective scores);
* ``dashboard`` the compact summary the /lab snapshot embeds.
"""
