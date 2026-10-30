#!/bin/bash
# Deploy committed code to the Oracle collection host and merge trials.jsonl both ways.
# Run on the Mac from anywhere:  scripts/oracle/deploy.sh [branch]   (default: current branch)
#  1. shallow clone of the COMMITTED branch tip (history since 2026-10-09, so the registration
#     commits that forecast/e003/e004/e006/e007 read with `git show` exist on the host);
#  2. union docs/research_lab/trials.jsonl Mac <-> host (append-only, nothing dropped);
#  3. rsync the clone over /home/opc/arepo (never touches .venv, run/, the data directory or the
#     host's trials.jsonl except by appending), under the collector lock so no pass is mid-write.
# Running monitors keep the code they started with; restart them for code changes:
#   ssh oracle '~/arepo/scripts/oracle/supervise.sh stop; rm ~/arepo/run/*.disabled; ~/arepo/scripts/oracle/supervise.sh'
set -euo pipefail
REPO=$(cd "$(dirname "$0")/../.." && pwd)
BRANCH=${1:-$(git -C "$REPO" rev-parse --abbrev-ref HEAD)}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
git clone -q --shallow-since=2026-10-09 --branch "$BRANCH" "file://$REPO" "$TMP/arepo"
echo "deploying $(git -C "$TMP/arepo" log --oneline -1)"
T=docs/research_lab/trials.jsonl
scp -q oracle:/home/opc/arepo/$T "$TMP/host_trials.jsonl" || touch "$TMP/host_trials.jsonl"
echo "trials rows pulled from host: $(python3 "$REPO/scripts/oracle/union_jsonl.py" "$REPO/$T" "$TMP/host_trials.jsonl")"
scp -q "$REPO/$T" oracle:/home/opc/arepo_trials_from_mac.jsonl
ssh -o BatchMode=yes oracle "flock /tmp/arepo_collector.lock true" # wait for a running pass
rsync -a --exclude .venv --exclude /run --exclude "/data-dumps" --exclude "/$T" "$TMP/arepo/" oracle:/home/opc/arepo/
ssh -o BatchMode=yes oracle "cd ~/arepo && echo trials rows pushed to host: \$(flock /tmp/arepo_collector.lock python3 scripts/oracle/union_jsonl.py $T ~/arepo_trials_from_mac.jsonl) && rm ~/arepo_trials_from_mac.jsonl && git log --oneline -1"
