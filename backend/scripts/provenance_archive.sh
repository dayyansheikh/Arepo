#!/usr/bin/env bash
# Lossless cold archive of cohort-referenced discovery_signal_snapshots (infra 2026-10-11/12).
# Re-access / restore guide: docs/infra/PROVENANCE_ARCHIVE.md.
#
#   export  <dir>                      read-only: per scan, server-side count+md5, COPY to
#                                      <scan>.csv.gz; META.tsv records schema version, columns,
#                                      excluded live scans and the cohort->scan map
#   verify  <dir>                      reload every file into a TEMP table on $VERIFY_DATABASE_URL
#                                      (a SEPARATE scratch DB) and recompute count+md5
#   prune   <dir> --approved-by NAME   delete archived rows: per scan, in one locked transaction,
#                                      only if the live rows still match the manifest; refuses the
#                                      latest / latest-complete scan; then VACUUM FULL
#   restore <dir> [scan_id ...]        re-insert (idempotent, ON CONFLICT DO NOTHING) by the
#                                      archived column list, then re-verify count+md5 per scan
#
# Env: DATABASE_URL (plain postgresql://; never printed), VERIFY_DATABASE_URL (verify target),
#      SCAN_IDS (optional override of the export scan list; live scans are still refused by prune).
# Fingerprint: md5(string_agg(ROW(<archived columns>)::text, '\n' ORDER BY id)) with every session
# pinned to TimeZone=UTC, DateStyle=ISO and extra_float_digits=1, so text is reproducible.
set -euo pipefail

TABLE=discovery_signal_snapshots
SESSION_SETUP="SET TimeZone = 'UTC'; SET DateStyle = 'ISO, MDY'; SET extra_float_digits = 1;
SET IntervalStyle = 'postgres';"

die() { echo "ERROR: $*" >&2; exit 1; }
need_db() { [ -n "${DATABASE_URL:-}" ] || die "DATABASE_URL is not set"; }

q() {  # q URL [psql -v args...] <<< SQL   (session settings pinned, results unaligned)
  local url=$1; shift
  { echo "$SESSION_SETUP"; cat; } | psql -X -q -v ON_ERROR_STOP=1 -A -t "$url" "$@"
}

table_columns() {  # $1 url -> "c1,c2,..." (ordinal order, quoted)
  q "$1" <<SQL
SELECT string_agg(quote_ident(column_name), ',' ORDER BY ordinal_position)
FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = '$TABLE';
SQL
}

fp_sql() {  # $1 relation, $2 columns -> fingerprint SELECT (expects :'sid')
  local rowexpr
  rowexpr=$(sed 's/\([^,][^,]*\)/t.\1/g' <<<"$2")
  echo "SELECT count(*) || ' ' || md5(coalesce(string_agg(ROW($rowexpr)::text, E'\\n' ORDER BY t.id), ''))
        FROM $1 t WHERE t.scan_id = :'sid';"
}

live_scans() {  # latest scan + latest complete scan (never archived/pruned)
  q "$1" <<'SQL'
SELECT scan_id FROM (SELECT scan_id FROM discovery_scan_runs ORDER BY started_at DESC LIMIT 1) a
UNION
SELECT scan_id FROM (SELECT scan_id FROM discovery_scan_runs WHERE pagination_complete
                     ORDER BY started_at DESC LIMIT 1) b;
SQL
}

scan_ids() {
  if [ -n "${SCAN_IDS:-}" ]; then tr ' ' '\n' <<<"$SCAN_IDS" | grep -v '^$'; return; fi
  q "$DATABASE_URL" <<'SQL'
SELECT DISTINCT c.scan_id FROM research_cohorts c
WHERE c.scan_id IS NOT NULL
  AND c.scan_id NOT IN (
    SELECT scan_id FROM (SELECT scan_id FROM discovery_scan_runs ORDER BY started_at DESC LIMIT 1) a
    UNION
    SELECT scan_id FROM (SELECT scan_id FROM discovery_scan_runs WHERE pagination_complete
                         ORDER BY started_at DESC LIMIT 1) b)
ORDER BY 1;
SQL
}

cols_of_dir() { awk -F'\t' '$1=="columns"{print $2}' "$1/META.tsv"; }

cmd_export() {
  local dir=$1; need_db; mkdir -p "$dir"
  [ -e "$dir/MANIFEST.tsv" ] && die "$dir/MANIFEST.tsv exists; use a fresh directory"
  local cols; cols=$(table_columns "$DATABASE_URL")
  [ -n "$cols" ] || die "could not read the $TABLE column list"
  {
    printf 'exported_at\t%s\n' "$(date -u +%FT%TZ)"
    printf 'table\t%s\n' "$TABLE"
    printf 'columns\t%s\n' "$cols"
    printf 'schema_version\t%s\n' "$(q "$DATABASE_URL" <<<'SELECT max(version) FROM schema_migrations;')"
    printf 'server_version\t%s\n' "$(q "$DATABASE_URL" <<<'SHOW server_version;')"
    printf 'session\t%s\n' "$(tr '\n' ' ' <<<"$SESSION_SETUP")"
    printf 'kept_live_scans\t%s\n' "$(live_scans "$DATABASE_URL" | tr '\n' ' ')"
  } >"$dir/META.tsv"
  q "$DATABASE_URL" <<'SQL' >"$dir/COHORT_SCAN_MAP.tsv"
SELECT id || E'\t' || cadence || E'\t' || cutoff_at || E'\t' || coalesce(scan_id, '')
FROM research_cohorts ORDER BY id;
SQL
  printf 'scan_id\trows\trow_md5\tfile_sha256\n' >"$dir/MANIFEST.tsv"
  local sid fp out n=0
  while read -r sid; do
    [ -n "$sid" ] || continue
    fp=$(fp_sql "$TABLE" "$cols" | q "$DATABASE_URL" -v sid="$sid")
    out="$dir/$sid.csv.gz"
    echo "COPY (SELECT $cols FROM $TABLE WHERE scan_id = :'sid' ORDER BY id) TO STDOUT WITH (FORMAT csv, HEADER true);" \
      | q "$DATABASE_URL" -v sid="$sid" | gzip -9 >"$out"
    gzip -t "$out"
    printf '%s\t%s\t%s\t%s\n' "$sid" "${fp%% *}" "${fp##* }" \
      "$(shasum -a 256 "$out" | cut -d' ' -f1)" >>"$dir/MANIFEST.tsv"
    n=$((n + 1)); echo "exported $sid rows=${fp%% *}"
  done < <(scan_ids)
  [ $n -gt 0 ] || die "no scans selected for export"
  echo "exported $n scans; manifest: $dir/MANIFEST.tsv"
}

load_temp_fp() {  # $1 url, $2 file, $3 columns -> count+md5 of a TEMP reload
  local sid; sid=$(basename "$2" .csv.gz)
  { echo "CREATE TEMP TABLE _arch AS SELECT $3 FROM $TABLE WITH NO DATA;"
    echo "\\copy _arch ($3) FROM STDIN WITH (FORMAT csv, HEADER true)"
    gunzip -c "$2"
    echo '\.'
    fp_sql _arch "$3"
  } | q "$1" -v sid="$sid" | tail -1
}

cmd_verify() {
  local dir=$1 url=${VERIFY_DATABASE_URL:-}
  [ -n "$url" ] || die "VERIFY_DATABASE_URL (a separate scratch database) must be set"
  local cols; cols=$(cols_of_dir "$dir"); [ -n "$cols" ] || die "META.tsv has no column list"
  local bad=0 n=0 sid rows md5 sha got
  while IFS=$'\t' read -r sid rows md5 sha; do
    [ "$sid" = scan_id ] && continue
    n=$((n + 1))
    [ "$(head -1 <(gunzip -c "$dir/$sid.csv.gz"))" = "$(tr -d '"' <<<"$cols")" ] \
      || { echo "FAIL $sid: CSV header != archived column list"; bad=1; continue; }
    [ "$(shasum -a 256 "$dir/$sid.csv.gz" | cut -d' ' -f1)" = "$sha" ] \
      || { echo "FAIL $sid: file checksum"; bad=1; continue; }
    got=$(load_temp_fp "$url" "$dir/$sid.csv.gz" "$cols")
    if [ "$got" = "$rows $md5" ]; then echo "OK   $sid rows=$rows"; else
      echo "FAIL $sid: expected '$rows $md5' got '$got'"; bad=1; fi
  done <"$dir/MANIFEST.tsv"
  [ $n -gt 0 ] || die "manifest lists no scans"
  [ $bad -eq 0 ] || die "verification failed"
  touch "$dir/VERIFIED"
  echo "all $n archives verified"
}

cmd_prune() {
  local dir=$1 approver=${3:-}
  [ "${2:-}" = "--approved-by" ] && [ -n "$approver" ] || die "prune requires --approved-by NAME"
  [ -e "$dir/VERIFIED" ] || die "run verify first"
  need_db
  local cols; cols=$(cols_of_dir "$dir"); [ -n "$cols" ] || die "META.tsv has no column list"
  [ "$(table_columns "$DATABASE_URL")" = "$cols" ] || die "live column list differs from archive"
  local live; live=" $(live_scans "$DATABASE_URL" | tr '\n' ' ') "
  local sid rows md5 sha fp
  while IFS=$'\t' read -r sid rows md5 sha; do
    [ "$sid" = scan_id ] && continue
    [[ "$live" == *" $sid "* ]] && die "$sid is the latest or latest-complete scan; refusing"
    fp=$(fp_sql "$TABLE" "$cols")
    # One transaction per scan: lock, re-fingerprint, delete only if unchanged since export.
    q "$DATABASE_URL" -v sid="$sid" -v exp="$rows $md5" <<SQL
BEGIN;
LOCK TABLE $TABLE IN SHARE ROW EXCLUSIVE MODE;
SELECT (${fp%;}) = :'exp' AS ok \gset
\if :ok
  DELETE FROM $TABLE WHERE scan_id = :'sid';
  COMMIT;
\else
  ROLLBACK;
  \echo 'live rows changed since export; NOT deleted'
  SELECT 1/0 AS abort_prune;
\endif
SQL
    [ "$(q "$DATABASE_URL" -v sid="$sid" <<<"SELECT count(*) FROM $TABLE WHERE scan_id = :'sid';")" = 0 ] \
      || die "$sid was NOT pruned"
    printf '%s\t%s\t%s\t%s\tapproved-by=%s\n' "$(date -u +%FT%TZ)" "$sid" "$rows" "$md5" \
      "$approver" >>"$dir/PRUNE_LOG.tsv"
    echo "pruned $sid ($rows rows) approved-by=$approver"
  done <"$dir/MANIFEST.tsv"
  echo "VACUUM FULL $TABLE (returns the space; brief exclusive lock on the now-small table)"
  psql -X -q -v ON_ERROR_STOP=1 "$DATABASE_URL" -c "VACUUM (FULL, ANALYZE) $TABLE"
}

cmd_restore() {
  local dir=$1; shift; need_db
  local cols; cols=$(cols_of_dir "$dir"); [ -n "$cols" ] || die "META.tsv has no column list"
  local only=" $* " sid rows md5 sha got
  while IFS=$'\t' read -r sid rows md5 sha; do
    [ "$sid" = scan_id ] && continue
    [ "$only" = "  " ] || [[ "$only" == *" $sid "* ]] || continue
    { echo "BEGIN;"
      echo "CREATE TEMP TABLE _arch ON COMMIT DROP AS SELECT $cols FROM $TABLE WITH NO DATA;"
      echo "\\copy _arch ($cols) FROM STDIN WITH (FORMAT csv, HEADER true)"
      gunzip -c "$dir/$sid.csv.gz"
      echo '\.'
      echo "INSERT INTO $TABLE ($cols) SELECT $cols FROM _arch ON CONFLICT DO NOTHING;"
      echo "COMMIT;"
    } | q "$DATABASE_URL" >/dev/null
    got=$(fp_sql "$TABLE" "$cols" | q "$DATABASE_URL" -v sid="$sid")
    [ "$got" = "$rows $md5" ] || die "restore verify failed for $sid: got '$got'"
    echo "restored $sid rows=$rows (verified)"
  done <"$dir/MANIFEST.tsv"
  q "$DATABASE_URL" >/dev/null <<SQL
SELECT setval(pg_get_serial_sequence('$TABLE', 'id'), (SELECT max(id) FROM $TABLE));
SQL
}

case "${1:-}" in
  export) cmd_export "${2:?dir}" ;;
  verify) cmd_verify "${2:?dir}" ;;
  prune) cmd_prune "${2:?dir}" "${3:-}" "${4:-}" ;;
  restore) d=${2:?dir}; shift 2; cmd_restore "$d" "$@" ;;
  *) sed -n '2,20p' "$0"; exit 2 ;;
esac
