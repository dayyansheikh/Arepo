"""Robust idempotent production scheduler (master prompt §11).

A hosted runner (GitHub Actions) wakes roughly every five minutes and calls
``python -m astrolabe.scheduler.tick``. The APPLICATION decides what work is due and runs only that
work by reusing the existing collector functions/CLIs — no Arepo research logic lives in workflow
YAML. Every unit of work is idempotent and the tick is delay-tolerant, so a late, duplicate or
missed wake never fabricates data or double-writes.
"""
