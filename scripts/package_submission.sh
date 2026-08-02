#!/usr/bin/env bash
# Build the clean submission ZIP for Astrolabe.
#   - stages a clean copy with all heavy/secret artefacts excluded
#   - validates the exclusions actually held
#   - creates the ZIP, prints its size, and FAILS if it exceeds 20 MB
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NAME="Dayyan-Sheikh-Prediction-Market-Project"
STAGING="$ROOT/staging"
ZIP="$ROOT/$NAME.zip"
MAX_BYTES=$((20 * 1024 * 1024))

echo "==> Cleaning previous staging/zip"
rm -rf "$STAGING" "$ZIP"
mkdir -p "$STAGING/$NAME"

echo "==> Staging a clean copy (excluding heavy/secret artefacts)"
rsync -a --prune-empty-dirs \
  --exclude '.git' \
  --exclude '.venv' --exclude 'venv' \
  --exclude 'node_modules' --exclude '.next' --exclude 'out' --exclude '.vercel' \
  --exclude '__pycache__' --exclude '*.pyc' --exclude '*.pyo' \
  --exclude '.pytest_cache' --exclude '.ruff_cache' --exclude '.mypy_cache' \
  --exclude '*.db' --exclude '*.sqlite' --exclude '*.sqlite3' \
  --exclude '.env' --exclude '*.env' --exclude 'frontend/.env.local' \
  --exclude 'staging' --exclude '*.zip' \
  --exclude '.DS_Store' --exclude 'coverage*' --exclude 'htmlcov' \
  --exclude '.coverage' --exclude 'data-dumps' \
  "$ROOT/" "$STAGING/$NAME/"

echo "==> Validating exclusions held"
VIOLATIONS="$(cd "$STAGING/$NAME" && find . \
  \( -name node_modules -o -name .venv -o -name venv -o -name .git \
     -o -name '*.db' -o -name '*.sqlite*' -o -name '.env' -o -name '.next' \) -print || true)"
if [ -n "$VIOLATIONS" ]; then
  echo "!! EXCLUSION VIOLATION — the following should not be in the package:"
  echo "$VIOLATIONS"
  exit 1
fi

echo "==> Scanning for obvious secrets"
# (exclude this script itself, whose grep pattern literals would self-match)
if grep -rIl --exclude='package_submission.sh' \
     -e 'BEGIN .*PRIVATE KEY' -e 'AWS_SECRET_ACCESS_KEY' -e 'aws_secret_access_key' \
     "$STAGING/$NAME" >/dev/null 2>&1; then
  echo "!! Possible secret material found in staging — aborting."
  exit 1
fi

echo "==> Verifying key deliverables are present"
for required in "README.md" "backend/astrolabe" "frontend/app" \
                "backend/astrolabe/replay/dataset/scenario.json"; do
  if [ ! -e "$STAGING/$NAME/$required" ]; then
    echo "   (warning) missing expected item: $required"
  fi
done
if [ ! -e "$STAGING/$NAME/docs/portfolio-report.pdf" ]; then
  echo "   (warning) docs/portfolio-report.pdf not found — run scripts/build_report_pdf.py first."
fi

echo "==> Creating ZIP"
(cd "$STAGING" && zip -rqX "$ZIP" "$NAME")

SIZE_BYTES="$(stat -f%z "$ZIP" 2>/dev/null || stat -c%s "$ZIP")"
SIZE_MB=$(awk "BEGIN {printf \"%.2f\", $SIZE_BYTES/1048576}")
echo "==> ZIP: $ZIP"
echo "==> Size: ${SIZE_MB} MB (${SIZE_BYTES} bytes)"

if [ "$SIZE_BYTES" -gt "$MAX_BYTES" ]; then
  echo "!! FAIL: package exceeds the 20 MB limit."
  exit 1
fi
echo "==> OK: package is under the 20 MB limit."

echo "==> Cleaning staging"
rm -rf "$STAGING"
echo "==> Done."
