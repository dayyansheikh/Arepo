#!/usr/bin/env python3
# ruff: noqa: E501, UP031
"""Build a Mac deletion manifest: local data-dumps files that are byte-identical to a member of a VERIFIED release.

Rows: sha256, bytes, release, parts, path. A file is listed only if (a) its path is under one of --include
prefixes and none of --exclude prefixes, (b) it is older than --min-age-hours, (c) a release's files.sha256 (checked
against MANIFEST.sha256, with a passing VERIFY.json for that files.sha256) lists the same path, and (d) its current
sha256 equals that entry. The output is a gzip TSV plus a per-root summary JSON. Nothing is deleted here.
"""
import argparse
import gzip
import hashlib
import json
import os
import sys
import time
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archive_release as ar  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--release", action="append", required=True)
    ap.add_argument("--include", action="append", required=True, help="root-relative path prefix")
    ap.add_argument("--exclude", action="append", default=[], help="root-relative path prefix")
    ap.add_argument("--exclude-file", help="file of exclude prefixes, one per line")
    ap.add_argument("--min-age-hours", type=float, default=3)
    ap.add_argument("--repo", default="dayyansheikh/arepo-data")
    ap.add_argument("--workdir", default=os.path.expanduser("~/arepo_archive_tmp/manifest"))
    ap.add_argument("--out", required=True, help="output .tsv.gz")
    a = ap.parse_args()
    if a.exclude_file:
        a.exclude += [x.strip() for x in open(a.exclude_file) if x.strip()]
    archived = {}
    for tag in a.release:
        dest = os.path.join(a.workdir, tag)
        man, files, parts = ar.fetch_meta(a.repo, tag, dest)
        ar.run(["gh", "release", "download", tag, "-R", a.repo, "-D", dest, "--clobber", "-p", "VERIFY.json"])
        v = json.load(open(os.path.join(dest, "VERIFY.json")))
        assert v["passed"] and v["files_sha256"] == man["files.sha256"], tag
        pr = "%s..%s" % (parts[0][0].rsplit("-", 1)[1], parts[-1][0].rsplit("-", 1)[1])
        for p, h in files.items():
            archived.setdefault(p, []).append((h, tag, pr))
    cut = time.time() - a.min_age_hours * 3600
    rows, summ = [], defaultdict(lambda: {"files": 0, "bytes": 0, "allocated_bytes": 0, "release": set()})
    skipped = defaultdict(int)
    tops = sorted({i.split("/")[0] for i in a.include})
    for top in tops:
        for d, _, fs in os.walk(os.path.join(a.base, top)):
            for f in fs:
                full = os.path.join(d, f)
                rel = os.path.relpath(full, a.base)
                if not any(rel.startswith(x) for x in a.include) or any(rel.startswith(x) for x in a.exclude):
                    continue
                if os.path.islink(full):
                    skipped["symlink"] += 1
                    continue
                st = os.stat(full)
                if st.st_mtime > cut:
                    skipped["too_recent"] += 1
                    continue
                if rel not in archived:
                    skipped["not_in_verified_release"] += 1
                    continue
                h = hashlib.sha256()
                with open(full, "rb") as fh:
                    for b in iter(lambda fh=fh: fh.read(1 << 20), b""):
                        h.update(b)
                match = [x for x in archived[rel] if x[0] == h.hexdigest()]
                if not match:
                    skipped["hash_differs_from_release"] += 1
                    continue
                want, tag, pr = match[-1]  # latest listed release holding these exact bytes
                rows.append((want, st.st_size, tag, pr, rel))
                root = "/".join(rel.split("/")[:2])
                s = summ[root]
                s["files"] += 1
                s["bytes"] += st.st_size
                s["allocated_bytes"] += st.st_blocks * 512
                s["release"].add(tag)
    rows.sort(key=lambda r: r[4])
    with gzip.open(a.out, "wt") as o:
        o.write("sha256\tbytes\trelease\tparts\tpath\n")
        for r in rows:
            o.write("%s\t%d\t%s\t%s\t%s\n" % r)
    summary = {
        "manifest": os.path.basename(a.out), "manifest_sha256": ar.sha256_file(a.out), "n_files": len(rows),
        "logical_bytes": sum(r[1] for r in rows), "allocated_bytes": sum(v["allocated_bytes"] for v in summ.values()), "releases": a.release, "include": a.include, "exclude": a.exclude,
        "skipped": dict(skipped),
        "roots": {k: {"files": v["files"], "bytes": v["bytes"], "allocated_bytes": v["allocated_bytes"], "release": sorted(v["release"])} for k, v in sorted(summ.items())},
    }
    with open(a.out.replace(".tsv.gz", "_summary.json"), "w") as o:
        json.dump(summary, o, indent=1)
    print(json.dumps({k: summary[k] for k in ("manifest_sha256", "n_files", "logical_bytes", "allocated_bytes", "skipped")}))


if __name__ == "__main__":
    main()
