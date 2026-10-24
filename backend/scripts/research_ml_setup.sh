#!/usr/bin/env bash
# Research-only: make the lightgbm wheel loadable on macOS arm64 without Homebrew.
# Homebrew here lives in /usr/local (Intel); an x86_64 libomp cannot load into the arm64 wheel, so
# we point lightgbm at the arm64 libomp vendored inside scikit-learn's wheel. Idempotent.
# Usage: cd backend && source .venv/bin/activate && pip install -r requirements-research.txt \
#          && bash scripts/research_ml_setup.sh
set -euo pipefail
SP=$(python -c "import site;print(site.getsitepackages()[0])")
LIB="$SP/lightgbm/lib/lib_lightgbm.dylib"
[ "$(uname -s)" = Darwin ] || { echo "not macOS: nothing to do"; exit 0; }
if python -c "import lightgbm" 2>/dev/null; then echo "lightgbm already loads"; exit 0; fi
install_name_tool -add_rpath "$SP/sklearn/.dylibs" "$LIB"
codesign --force -s - "$LIB"
python -c "import lightgbm; print('lightgbm', lightgbm.__version__, 'loads; libomp from', '$SP/sklearn/.dylibs')"
