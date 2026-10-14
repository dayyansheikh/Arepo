#!/usr/bin/env python3
# ruff: noqa: E501, UP031
"""User-run retirement of LOCAL copies of data-dumps files that are verified-archived on GitHub.

Only the user runs this, in a retirement session they open themselves (AREPO_RETIREMENT_SESSION=1), per
docs/implementation/PHASE_03_BOUNDED_RETENTION.md and docs/research_lab/DATA_ARCHIVE_2026-10-13.md.

Fails closed. Before deleting anything it:
  1. checks the deletion manifest's sha256 against the pinned --manifest-sha256;
  2. for every release named in the manifest, downloads MANIFEST.sha256, files.sha256 and VERIFY.json from
     GitHub, checks files.sha256 against MANIFEST.sha256, checks VERIFY.json passed for that same files.sha256,
     and checks the release is published (not a draft);
  3. checks every manifest row's sha256 equals that release's files.sha256 entry (any disagreement aborts).
Then, per file, it re-hashes the local copy and deletes it only if the hash still equals the archived hash;
anything else is kept. Every decision is logged (path, sha256, bytes, release, action). Directories left empty
by the deletions (and emptied parents below data-dumps/) are removed. Without --confirm it is a dry run.
"""

import argparse
import datetime
import gzip
import json
import os
import shutil
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archive_release as ar  # noqa: E402


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--manifest-release", default="retire-20261013", help="release holding the manifest"
    )
    ap.add_argument("--manifest-name", required=True, help="e.g. DELETION_MANIFEST_2026-10-13_tier1a.tsv.gz")
    ap.add_argument("--manifest-sha256", required=True, help="pinned sha256 of the manifest file")
    ap.add_argument(
        "--base", default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    )
    ap.add_argument("--repo", default="dayyansheikh/arepo-data")
    ap.add_argument("--workdir", default=os.path.expanduser("~/arepo_archive_tmp/retire"))
    ap.add_argument("--log-dir", default=os.path.expanduser("~/arepo_retirement_logs"))
    ap.add_argument("--confirm", action="store_true", help="actually delete (default is a dry run)")
    a = ap.parse_args()
    if a.confirm and os.environ.get("AREPO_RETIREMENT_SESSION") != "1":
        raise SystemExit(
            "refusing: set AREPO_RETIREMENT_SESSION=1 yourself to open a retirement session"
        )
    os.makedirs(a.workdir, exist_ok=True)
    os.makedirs(a.log_dir, exist_ok=True)

    ar.run(
        [
            "gh",
            "release",
            "download",
            a.manifest_release,
            "-R",
            a.repo,
            "-D",
            a.workdir,
            "--clobber",
            "-p",
            a.manifest_name,
        ]
    )
    mpath = os.path.join(a.workdir, a.manifest_name)
    if ar.sha256_file(mpath) != a.manifest_sha256:
        raise SystemExit("manifest sha256 does not match the pinned value; refusing")
    rows = []
    with gzip.open(mpath, "rt") as fh:
        header = fh.readline().rstrip("\n").split("\t")
        for ln in fh:
            rows.append(dict(zip(header, ln.rstrip("\n").split("\t"), strict=False)))
    for r in rows:
        q = r.get("path", "")
        if (
            not q.startswith("data-dumps/")
            or q.startswith("data-dumps/research_lab/")
            or ".." in q.split("/")
            or os.path.isabs(q)
        ):
            raise SystemExit(f"manifest row outside the allowed scope: {q!r}; refusing")
    by_rel = defaultdict(list)
    for r in rows:
        by_rel[r["release"]].append(r)

    for tag, rs in sorted(by_rel.items()):
        dest = os.path.join(a.workdir, tag)
        man, files, parts = ar.fetch_meta(a.repo, tag, dest)
        ar.run(
            [
                "gh",
                "release",
                "download",
                tag,
                "-R",
                a.repo,
                "-D",
                dest,
                "--clobber",
                "-p",
                "VERIFY.json",
            ]
        )
        v = json.load(open(os.path.join(dest, "VERIFY.json")))
        if not v.get("passed") or v.get("files_sha256") != man["files.sha256"]:
            raise SystemExit(
                f"release {tag}: VERIFY.json missing, failed, or for a different files.sha256"
            )
        assets, draft = ar.release_assets(a.repo, tag)
        if draft or not parts:
            raise SystemExit(f"release {tag} is a draft or has no parts")
        vsize = {x["name"]: x["bytes"] for x in v.get("parts", [])}
        for name, _h in parts:
            if name not in assets or assets[name] != vsize.get(name):
                raise SystemExit(
                    f"release {tag}: part {name} missing or size differs from VERIFY.json; refusing"
                )
        bad = [r["path"] for r in rs if files.get(r["path"]) != r["sha256"]]
        if bad:
            raise SystemExit(
                "release %s: %d manifest rows disagree with files.sha256 (e.g. %s); refusing"
                % (tag, len(bad), bad[0])
            )
        print(
            "release %s OK: %d parts, verified %s, %d manifest rows"
            % (tag, len(parts), v["verified_utc"], len(rs))
        )

    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    logp = os.path.join(
        a.log_dir, "retirement_{}{}.jsonl.gz".format(ts, "" if a.confirm else "_dryrun")
    )
    free0 = shutil.disk_usage(a.base).free
    acts, freed = Counter(), 0
    touched = set()
    with gzip.open(logp, "wt") as log:
        for r in rows:
            p = os.path.join(a.base, r["path"])
            rec = {"path": r["path"], "sha256": r["sha256"], "release": r["release"]}
            if not os.path.isfile(p) or os.path.islink(p):
                rec["action"] = "absent"
            elif ar.sha256_file(p) != r["sha256"]:
                rec["action"] = "kept_hash_changed"
            elif not a.confirm:
                rec["action"] = "would_delete"
                freed += os.path.getsize(p)
            else:
                rec["bytes"] = os.path.getsize(p)
                os.remove(p)
                rec["action"] = "deleted"
                freed += rec["bytes"]
                touched.add(os.path.dirname(p))
            acts[rec["action"]] += 1
            log.write(json.dumps(rec) + "\n")
    removed_dirs = 0
    stop = os.path.join(a.base, "data-dumps")
    # remove only directories that held a deleted file, and their emptied parents below data-dumps/
    for d in sorted(touched, key=lambda x: -len(x)):
        while d.startswith(stop + os.sep) and os.path.isdir(d) and not os.listdir(d):
            os.rmdir(d)
            removed_dirs += 1
            d = os.path.dirname(d)
    summary = {
        "utc": ts,
        "confirm": a.confirm,
        "manifest_sha256": a.manifest_sha256,
        "actions": dict(acts),
        "logical_bytes": freed,
        "disk_free_before": free0,
        "disk_free_after": shutil.disk_usage(a.base).free,
        "empty_dirs_removed": removed_dirs,
        "log": logp,
    }
    with open(logp.replace(".jsonl.gz", "_summary.json"), "w") as o:
        json.dump(summary, o, indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
