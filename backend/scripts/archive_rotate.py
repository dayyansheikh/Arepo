#!/usr/bin/env python3
# ruff: noqa: E501, UP031  (runs on Python 3.6 collection hosts; long docstring lines)
"""Nightly rotation for the collection host: archive old captures to GitHub, then free the SERVER's local copies.

Intended for the Oracle collection host only (see docs/research_lab/COLLECTION_HOST.md, section
"Nightly archive rotation"). The user approved deleting the server's local copies of files that are verified
archived in a release; nothing else is ever deleted.

One run:
 1. Select regular files under --root/<--scan dirs> whose mtime is older than --older-than-days and that do
    not match --exclude. Files already recorded as verified-archived with the same sha256 are not re-archived.
 2. Build a draft release `data-YYYYMMDD-<host>` (suffix -2, -3 ... if taken) with archive_release.py
    (same scheme as data-20261011: zstd tar parts of the original bytes, files.sha256, MANIFEST.sha256).
 3. Verify by streaming every part back from GitHub and re-hashing every member; only a PASS publishes the
    release and appends it to the verified ledger (<state>/verified_releases.jsonl).
 4. With --delete: for every file listed in a verified release, re-check that the release's MANIFEST/files.sha256
    on GitHub still match the ledger, that the file is still older than the cut-off, and that its current sha256
    equals the archived sha256. Only then delete it and append {ts, path, sha256, bytes, tag} to
    <state>/deletions.jsonl. Anything else is kept and logged as `kept`.

It refuses to delete any file that is not in a verified release. Exit code is non-zero on any failure.
Python >= 3.6; needs `zstd` and an authenticated `gh` (token with access to the private data repo) on PATH.
Example cron (03:30 UTC):
  30 3 * * * cd ~/arepo/backend && python3 scripts/archive_rotate.py --root ~/arepo \
      --scan data-dumps/research_lab --older-than-days 7 --delete >> ~/.arepo/archive_rotate/cron.log 2>&1
"""

import argparse
import datetime
import fnmatch
import json
import os
import shutil
import socket
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import archive_release as ar  # noqa: E402

DEFAULT_EXCLUDES = ["*.lock", "*.pid", "*.tmp", "*.partial", "*/.DS_Store", "*state*.json"]


def now_iso():
    return datetime.datetime.utcnow().isoformat() + "Z"


def load_ledger(state):
    led = []
    p = os.path.join(state, "verified_releases.jsonl")
    if os.path.exists(p):
        for ln in open(p):
            if ln.strip():
                led.append(json.loads(ln))
    return led


def append_jsonl(path, obj):
    with open(path, "a") as o:
        o.write(json.dumps(obj, sort_keys=True) + "\n")
        o.flush()
        os.fsync(o.fileno())


def select(root, scans, cutoff, excludes):
    out = []
    for s in scans:
        top = os.path.join(root, s)
        for d, _, fs in os.walk(top):
            for f in fs:
                p = os.path.join(d, f)
                rel = os.path.relpath(p, root)
                if os.path.islink(p) or any(fnmatch.fnmatch(rel, e) for e in excludes):
                    continue
                if os.stat(p).st_mtime < cutoff:
                    out.append(rel)
    return sorted(out)


def free_tag(repo, base):
    tag, i = base, 1
    while ar.release_exists(repo, tag):
        i += 1
        tag = "%s-%d" % (base, i)
    return tag


def ns(**kw):
    return argparse.Namespace(**kw)


def archive_new(a, state, ledger):
    cutoff = time.time() - a.older_than_days * 86400
    cands = select(a.root, a.scan, cutoff, DEFAULT_EXCLUDES + a.exclude)
    archived = {}
    for e in ledger:
        for p, h in e["files"].items():
            archived[p] = h
    todo = [p for p in cands if archived.get(p) != ar.sha256_file(os.path.join(a.root, p))]
    print(
        json.dumps(
            {"event": "select", "ts": now_iso(), "candidates": len(cands), "to_archive": len(todo)}
        )
    )
    if not todo or a.no_archive:
        return None
    host = socket.gethostname().split(".")[0]
    tag = free_tag(a.repo, "data-{}-{}".format(datetime.datetime.utcnow().strftime("%Y%m%d"), host))
    listf = os.path.join(state, f"list_{tag}.txt")
    with open(listf, "w") as o:
        o.write("\n".join(todo) + "\n")
    ar.build(
        ns(
            repo=a.repo,
            workdir=a.workdir,
            tag=tag,
            base=a.root,
            list=listf,
            prefix=None,
            title="%s rotation (files older than %d days)" % (host, a.older_than_days),
            notes=None,
            part_size=a.part_size,
            level=a.level,
            long=a.long,
            threads=a.threads,
        )
    )
    rc = ar.verify(ns(repo=a.repo, workdir=a.workdir, tag=tag, upload_report=True, publish=True))
    if rc != 0:
        raise SystemExit(f"verification FAILED for {tag}; nothing recorded, nothing deleted")
    vdir = os.path.join(a.workdir, tag, "verify")
    man, files, _ = ar.fetch_meta(a.repo, tag, vdir)
    rep = json.load(open(os.path.join(vdir, "VERIFY.json")))
    entry = {
        "tag": tag,
        "repo": a.repo,
        "verified_utc": rep["verified_utc"],
        "files_sha256": man["files.sha256"],
        "manifest_sha256": ar.sha256_file(os.path.join(vdir, "MANIFEST.sha256")),
        "files": files,
    }
    append_jsonl(os.path.join(state, "verified_releases.jsonl"), entry)
    shutil.rmtree(os.path.join(a.workdir, tag), ignore_errors=True)
    print(json.dumps({"event": "archived", "ts": now_iso(), "tag": tag, "files": len(files)}))
    return entry


def delete_verified(a, state, ledger):
    cutoff = time.time() - a.older_than_days * 86400
    dlog = os.path.join(state, "deletions.jsonl")
    n_del = n_keep = freed = 0
    for e in ledger:
        live = [p for p in e["files"] if os.path.exists(os.path.join(a.root, p))]
        if not live:
            continue
        chk = os.path.join(a.workdir, "recheck_" + e["tag"])
        man, files, _ = ar.fetch_meta(e["repo"], e["tag"], chk)
        if (
            ar.sha256_file(os.path.join(chk, "MANIFEST.sha256")) != e["manifest_sha256"]
            or files != e["files"]
        ):
            raise SystemExit(
                "release {} on GitHub no longer matches the verified ledger; refusing to delete".format(
                    e["tag"]
                )
            )
        _, draft = ar.release_assets(e["repo"], e["tag"])
        if draft:
            raise SystemExit("release {} is still a draft; refusing to delete".format(e["tag"]))
        shutil.rmtree(chk, ignore_errors=True)
        for rel in live:
            p = os.path.join(a.root, rel)
            st = os.stat(p)
            h = ar.sha256_file(p)
            rec = {"ts": now_iso(), "path": rel, "sha256": h, "bytes": st.st_size, "tag": e["tag"]}
            if h != files[rel] or st.st_mtime >= cutoff or os.path.islink(p):
                rec["action"] = "kept"
                rec["why"] = (
                    "hash differs from archive" if h != files[rel] else "too recent or link"
                )
                n_keep += 1
            elif a.dry_run:
                rec["action"] = "would_delete"
            else:
                os.remove(p)
                rec["action"] = "deleted"
                n_del += 1
                freed += st.st_size
            append_jsonl(dlog, rec)
    print(
        json.dumps(
            {
                "event": "delete",
                "ts": now_iso(),
                "deleted": n_del,
                "kept": n_keep,
                "freed_bytes": freed,
                "dry_run": a.dry_run,
            }
        )
    )


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--root", required=True, help="repo root on the host, e.g. ~/arepo")
    ap.add_argument(
        "--scan", action="append", required=True, help="dir under --root to rotate (repeatable)"
    )
    ap.add_argument("--older-than-days", type=float, default=7)
    ap.add_argument(
        "--exclude", action="append", default=[], help="fnmatch on the root-relative path"
    )
    ap.add_argument("--repo", default="dayyansheikh/arepo-data")
    ap.add_argument("--state", default=os.path.expanduser("~/.arepo/archive_rotate"))
    ap.add_argument("--workdir", default=os.path.expanduser("~/arepo_archive_tmp"))
    ap.add_argument("--part-size", type=int, default=1900 * 1000 * 1000)
    ap.add_argument("--level", type=int, default=12)
    ap.add_argument("--long", type=int, default=27)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument(
        "--delete", action="store_true", help="delete local copies of verified-archived files"
    )
    ap.add_argument("--dry-run", action="store_true", help="with --delete: log would_delete only")
    ap.add_argument(
        "--no-archive", action="store_true", help="skip archiving; only the deletion pass"
    )
    a = ap.parse_args()
    a.root = os.path.abspath(os.path.expanduser(a.root))
    if a.older_than_days < 1:
        raise SystemExit("--older-than-days must be >= 1")
    os.makedirs(a.state, exist_ok=True)
    os.makedirs(a.workdir, exist_ok=True)
    lockp = os.path.join(a.state, "rotate.lock")
    try:
        fd = os.open(lockp, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise SystemExit(f"another rotation holds {lockp}") from None
    try:
        os.write(fd, str(os.getpid()).encode())
        archive_new(a, a.state, load_ledger(a.state))
        if a.delete:
            delete_verified(a, a.state, load_ledger(a.state))
    finally:
        os.close(fd)
        os.remove(lockp)


if __name__ == "__main__":
    main()
