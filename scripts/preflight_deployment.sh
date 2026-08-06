#!/usr/bin/env bash
# Pre-deployment preflight (final pre-deployment §13). Run from the repo root. Verifies the repo is
# in a deployable state: clean tree, backend tests + ruff, migration is current, frontend builds,
# and no obvious secret is committed. Never prints secret VALUES. Exits non-zero on any failure.
set -euo pipefail
cd "$(dirname "$0")/.."
fail() { echo "PREFLIGHT FAIL: $1" >&2; exit 1; }

echo "== git clean =="
[ -z "$(git status --porcelain)" ] || fail "working tree is not clean; commit or stash first"

echo "== backend tests + ruff =="
cd backend
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pytest -q >/tmp/arepo_pytest.log 2>&1 || { tail -5 /tmp/arepo_pytest.log; fail "backend tests failed"; }
ruff check astrolabe >/dev/null || fail "ruff failed"
echo "== migration current (local DB) =="
python -m astrolabe.storage.migrate_cli check >/dev/null || fail "local schema is behind the ORM; run migrate_cli upgrade"
cd ..

echo "== frontend build =="
cd frontend
npx tsc --noEmit >/dev/null 2>&1 || fail "frontend tsc failed"
npx next build >/tmp/arepo_build.log 2>&1 || { tail -5 /tmp/arepo_build.log; fail "frontend build failed"; }
cd ..

echo "== no committed secrets (heuristic) =="
if git grep -nEI '(AUTH_SECRET|RESEND_API_KEY|DATABASE_URL)\s*[:=]\s*["'\''][A-Za-z0-9/_-]{16,}' -- ':!*.md' ':!render.yaml' ':!*.example' >/tmp/arepo_secrets.log 2>&1; then
  cat /tmp/arepo_secrets.log; fail "a possible committed secret was found"
fi

echo "PREFLIGHT OK"
