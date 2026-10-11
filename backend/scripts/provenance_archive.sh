#!/usr/bin/env bash
# Lossless cold archive of cohort-referenced discovery_signal_snapshots (infra 2026-10-11).
#
# WHY: ~597 MB of the 951 MB production database is discovery_signal_snapshots, and essentially all
# of it is the scans that frozen research cohorts reference (permanent provenance, which the
# retention pass never prunes by design). The cohorts' own entries already carry copied values; the
# snapshots are the "what universe was it frozen from" provenance. This tool moves that provenance
# to verified, restorable files. It is DATA-DESTRUCTIVE only in the `prune` step, which requires an
# explicit approval flag, a verified manifest, and a re-check that the live rows still match it.
#
#   export  <dir>                 read-only: per scan, server-side count+md5, COPY to <scan>.csv.gz
#   verify  <dir>                 load every file into a TEMP table on $VERIFY_DATABASE_URL and
#                                 recompute count+md5 (must equal the server-side values)
#   prune   <dir> --approved-by NAME   delete archived rows (re-checks count+md5 first, per scan,
#                                 in one transaction each); then VACUUM FULL to return the space
#   restore <dir> [scan_id ...]   re-insert from files (idempotent: ON CONFLICT DO NOTHING), then
#                                 re-verify count+md5 against the manifest
#
# Env: DATABASE_URL (plain postgresql://..., session pooler for Supabase; never printed),
#      VERIFY_DATABASE_URL (a scratch Postgres for `verify`; defaults to DATABASE_URL, which only
#      creates a TEMP table), SCAN_IDS (optional space-separated override of the scan list).
# The fingerprint is md5(string_agg(row::text, '\n' ORDER BY id)): identical text => identical rows
# (all columns, types and NULLs), so a passing verify proves the archive is a lossless copy.
set -euo pipefail

TABLE=discovery_signal_snapshots
PSQL=(psql -X -q -v ON_ERROR_STOP=1 -A -t)
FP_SQL="SELECT count(*) || ' ' || md5(coalesce(string_agg(t::text, E'\\n' ORDER BY t.id), ''))"

die() { echo "ERROR: $*" >&2; exit 1; }
need_db() { [ -n "${DATABASE_URL:-}" ] || die "DATABASE_URL is not set"; }

scan_ids() {
  if [ -n "${SCAN_IDS:-}" ]; then
    tr ' ' '\n' <<<"$SCAN_IDS" | grep -v '^$'
  else
    "${PSQL[@]}" "$DATABASE_URL" -c \
      "SELECT DISTINCT scan_id FROM research_cohorts WHERE scan_id IS NOT NULL ORDER BY 1"
  fi
}

fingerprint() {  # $1 url, $2 relation, $3 scan_id  (stdin, so psql interpolates :'sid' safely)
  echo "$FP_SQL FROM $2 t WHERE t.scan_id = :'sid';" | "${PSQL[@]}" "$1" -v sid="$3"
}

cmd_export() {
  local dir=$1; need_db; mkdir -p "$dir"
  local manifest="$dir/MANIFEST.tsv"
  [ -e "$manifest" ] && die "$manifest exists; use a fresh directory"
  printf 'scan_id\trows\trow_md5\tfile_sha256\n' >"$manifest"
  "${PSQL[@]}" "$DATABASE_URL" -c "\\d+ $TABLE" >"$dir/TABLE_DEFINITION.txt" 2>/dev/null || true
  local sid fp out
  while read -r sid; do
    [ -n "$sid" ] || continue
    fp=$(fingerprint "$DATABASE_URL" "$TABLE" "$sid")
    out="$dir/$sid.csv.gz"
    echo "COPY (SELECT * FROM $TABLE WHERE scan_id = :'sid' ORDER BY id) TO STDOUT WITH (FORMAT csv, HEADER true);" \
      | "${PSQL[@]}" "$DATABASE_URL" -v sid="$sid" | gzip -9 >"$out"
    gzip -t "$out"
    printf '%s\t%s\t%s\t%s\n' "$sid" "${fp%% *}" "${fp##* }" \
      "$(shasum -a 256 "$out" | cut -d' ' -f1)" >>"$manifest"
    echo "exported $sid rows=${fp%% *}"
  done < <(scan_ids)
  echo "manifest: $manifest"
}

load_into_temp() {  # $1 url, $2 file -> prints count+md5 computed on a TEMP copy
  local url=$1 file=$2 sid
  sid=$(basename "$file" .csv.gz)
  { echo "CREATE TEMP TABLE _arch (LIKE $TABLE INCLUDING DEFAULTS);"
    echo "\\copy _arch FROM STDIN WITH (FORMAT csv, HEADER true)"
    gunzip -c "$file"
    echo '\.'
    echo "$FP_SQL FROM _arch t WHERE t.scan_id = :'sid';"
  } | "${PSQL[@]}" "$url" -v sid="$sid" | tail -1
}

cmd_verify() {
  local dir=$1 url=${VERIFY_DATABASE_URL:-${DATABASE_URL:-}}
  [ -n "$url" ] || die "VERIFY_DATABASE_URL or DATABASE_URL must be set"
  local bad=0 n=0 sid rows md5 sha got
  while IFS=$'\t' read -r sid rows md5 sha; do
    [ "$sid" = scan_id ] && continue
    n=$((n + 1))
    [ "$(shasum -a 256 "$dir/$sid.csv.gz" | cut -d' ' -f1)" = "$sha" ] \
      || { echo "FAIL $sid: file checksum"; bad=1; continue; }
    got=$(load_into_temp "$url" "$dir/$sid.csv.gz")
    if [ "$got" = "$rows $md5" ]; then echo "OK   $sid rows=$rows"; else
      echo "FAIL $sid: expected '$rows $md5' got '$got'"; bad=1; fi
  done <"$dir/MANIFEST.tsv"
  [ $n -gt 0 ] || die "manifest lists no scans"
  [ $bad -eq 0 ] || die "verification failed"
  touch "$dir/VERIFIED"
  echo "all archives verified"
}

cmd_prune() {
  local dir=$1 approver=${3:-}
  [ "${2:-}" = "--approved-by" ] && [ -n "$approver" ] || die "prune requires --approved-by NAME"
  [ -e "$dir/VERIFIED" ] || die "run verify first"
  need_db
  local sid rows md5 sha
  while IFS=$'\t' read -r sid rows md5 sha; do
    [ "$sid" = scan_id ] && continue
    # One transaction per scan: lock, re-fingerprint, delete only if unchanged since export.
    "${PSQL[@]}" "$DATABASE_URL" -v sid="$sid" -v exp="$rows $md5" <<SQL
BEGIN;
LOCK TABLE $TABLE IN SHARE ROW EXCLUSIVE MODE;
SELECT ($FP_SQL FROM $TABLE t WHERE t.scan_id = :'sid') = :'exp' AS ok \gset
\if :ok
  DELETE FROM $TABLE WHERE scan_id = :'sid';
  COMMIT;
\else
  ROLLBACK;
  \echo 'live rows changed since export; NOT deleted'
  SELECT 1/0 AS abort_prune;
\endif
SQL
    # Belt and braces: never report success unless the rows are really gone.
    [ "$(fingerprint "$DATABASE_URL" "$TABLE" "$sid" | cut -d' ' -f1)" = "0" ] \
      || die "$sid was NOT pruned"
    echo "pruned $sid ($rows rows) approved-by=$approver"
  done <"$dir/MANIFEST.tsv"
  printf '%s\tpruned\tapproved-by=%s\n' "$(date -u +%FT%TZ)" "$approver" >>"$dir/PRUNE_LOG.tsv"
  echo "Reclaim space (exclusive lock, brief for the now-small table): VACUUM FULL $TABLE;"
  "${PSQL[@]}" "$DATABASE_URL" -c "VACUUM (FULL, ANALYZE) $TABLE"
}

cmd_restore() {
  local dir=$1; shift; need_db
  local only=" $* " sid rows md5 sha got
  while IFS=$'\t' read -r sid rows md5 sha; do
    [ "$sid" = scan_id ] && continue
    [ "$only" = "  " ] || [[ "$only" == *" $sid "* ]] || continue
    { echo "BEGIN;"
      echo "CREATE TEMP TABLE _arch (LIKE $TABLE INCLUDING DEFAULTS) ON COMMIT DROP;"
      echo "\\copy _arch FROM STDIN WITH (FORMAT csv, HEADER true)"
      gunzip -c "$dir/$sid.csv.gz"
      echo '\.'
      echo "INSERT INTO $TABLE SELECT * FROM _arch ON CONFLICT DO NOTHING;"
      echo "COMMIT;"
    } | "${PSQL[@]}" "$DATABASE_URL" >/dev/null
    got=$(fingerprint "$DATABASE_URL" "$TABLE" "$sid")
    [ "$got" = "$rows $md5" ] || die "restore verify failed for $sid: got '$got'"
    echo "restored $sid rows=$rows (verified)"
  done <"$dir/MANIFEST.tsv"
  "${PSQL[@]}" "$DATABASE_URL" -c \
    "SELECT setval(pg_get_serial_sequence('$TABLE','id'), (SELECT max(id) FROM $TABLE))" >/dev/null
}

case "${1:-}" in
  export) cmd_export "${2:?dir}" ;;
  verify) cmd_verify "${2:?dir}" ;;
  prune) cmd_prune "${2:?dir}" "${3:-}" "${4:-}" ;;
  restore) d=${2:?dir}; shift 2; cmd_restore "$d" "$@" ;;
  *) sed -n '2,25p' "$0"; exit 2 ;;
esac
