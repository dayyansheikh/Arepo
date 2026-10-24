#!/usr/bin/env python3
# ruff: noqa: E501, UP031, UP032, UP015, UP004, UP028  (Python 3.6-compatible style, shared with archive_rotate.py)
"""Restore selected files from the private data releases (dayyansheikh/arepo-data), byte for byte, and prove it.

Selection uses the data catalogue (docs/research_lab/data_catalogue/<tag>.jsonl, see its README):
  --tag T            release(s); repeatable. Default: every release in the catalogue.
  --experiment E     only files labelled with experiment id E (for example E011)
  --dir D            only files under research_lab dir D (repeatable), for example snapshots
  --since / --until  capture time (or day) bounds, ISO prefix such as 2026-10-14 or 2026-10-14T06:00:00Z
  --path-glob G      fnmatch on the archive path, repeatable (for example 'data-dumps/research_lab/snapshots/2026101*/rows.csv.gz')
With no selector the whole release is restored.

What it does, per release:
  1. downloads MANIFEST.sha256 and files.sha256; files.sha256 must match MANIFEST (else abort);
  2. streams the zstd tar parts from GitHub (the parts are ONE stream, so every part is read even for one file),
     checking each part's sha256 against MANIFEST.sha256;
  3. extracts ONLY the selected members into --dest (required; it never writes anywhere else);
  4. re-hashes every restored file against files.sha256 and, for file-level catalogue rows, against the catalogue
     sha256 as well; writes <dest>/RESTORE_REPORT_<tag>.json;
  5. optional --compare-with BASE: also compares each restored file with BASE/<path> byte for byte (filecmp).
Exit code is non-zero on any mismatch, missing member, part-hash failure, or tool failure.

Nothing in --dest is overwritten unless --overwrite is given. Requires zstd and (unless --parts-dir) an authenticated gh.
Tests/offline: --parts-dir DIR holds MANIFEST.sha256, files.sha256 and the part files of one release.
"""

import argparse
import filecmp
import fnmatch
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
_spec = importlib.util.spec_from_file_location(
    "data_catalogue", os.path.join(HERE, "..", "astrolabe", "research_lab", "data_catalogue.py")
)
dc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dc)

CHUNK = 4 << 20
DEFAULT_CAT = os.path.join(REPO_ROOT, "docs", "research_lab", "data_catalogue")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(CHUNK), b""):
            h.update(b)
    return h.hexdigest()


def read_hashes(path):
    out = {}
    for ln in open(path):
        if ln.strip():
            h, n = ln.rstrip("\n").split("  ", 1)
            out[n] = h
    return out


class LocalSource(object):
    """Release files from a local directory (tests, offline copies)."""

    def __init__(self, root):
        self.root = root

    def meta(self, tag, dest):
        return self.root

    def stream(self, tag, name):
        with open(os.path.join(self.root, name), "rb") as fh:
            for b in iter(lambda: fh.read(CHUNK), b""):
                yield b


class GhSource(object):
    def __init__(self, repo):
        self.repo = repo

    def meta(self, tag, dest):
        os.makedirs(dest, exist_ok=True)
        p = subprocess.Popen(
            ["gh", "release", "download", tag, "-R", self.repo, "-D", dest, "--clobber",
             "-p", "MANIFEST.sha256", "-p", "files.sha256"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, err = p.communicate()
        if p.returncode != 0:
            raise SystemExit("cannot download metadata of %s: %s" % (tag, err.decode()[-500:]))
        return dest

    def stream(self, tag, name):
        p = subprocess.Popen(
            ["gh", "release", "download", tag, "-R", self.repo, "-p", name, "-O", "-"],
            stdout=subprocess.PIPE)
        for b in iter(lambda: p.stdout.read(CHUNK), b""):
            yield b
        if p.wait() != 0:
            raise RuntimeError("download failed: " + name)


class Feeder(threading.Thread):
    """Pushes every part into zstd's stdin, hashing each part on the way."""

    def __init__(self, source, tag, parts, sink):
        threading.Thread.__init__(self)
        self.daemon = True
        self.source, self.tag, self.parts, self.sink = source, tag, parts, sink
        self.result, self.error = [], None

    def run(self):
        try:
            for name, want in self.parts:
                h, n = hashlib.sha256(), 0
                for b in self.source.stream(self.tag, name):
                    h.update(b)
                    n += len(b)
                    self.sink.write(b)
                self.result.append({"name": name, "bytes": n, "sha256": h.hexdigest(), "ok": h.hexdigest() == want})
                sys.stderr.write("streamed %s (%.1f MB) %s\n" % (name, n / 1e6, "OK" if h.hexdigest() == want else "HASH MISMATCH"))
        except BaseException as e:  # noqa: BLE001
            self.error = e
        finally:
            try:
                self.sink.close()
            except Exception:  # noqa: BLE001
                pass


def select_paths(tag, files, cat_dir, a):
    """Expand catalogue selection into archive paths. Returns (paths, catalogue_sha) where catalogue_sha holds
    the catalogue's own hash for file-level rows."""
    cat_path = os.path.join(cat_dir, tag + ".jsonl")
    no_filter = not (a.experiment or a.dir or a.since or a.until or a.path_glob)
    if no_filter:
        return sorted(files), {}
    if not os.path.exists(cat_path):
        raise SystemExit("no catalogue for %s at %s (run archive_catalogue.py)" % (tag, cat_path))
    chosen, cat_sha = set(), {}
    for row in dc.load_jsonl(cat_path):
        if not dc.matches(row, a.experiment, a.dir, a.since, a.until, None if row.get("granularity") == "group" else a.path_glob):
            continue
        if row.get("granularity") == "group":
            pre = row["path_prefix"]
            for p in files:
                if p.startswith(pre):
                    if a.path_glob and not any(fnmatch.fnmatch(p, g) for g in a.path_glob):
                        continue
                    chosen.add(p)
        else:
            chosen.add(row["path"])
            cat_sha[row["path"]] = row["sha256"]
    return sorted(chosen), cat_sha


def restore_release(tag, source, cat_dir, a, workdir):
    meta = source.meta(tag, os.path.join(workdir, tag))
    man = read_hashes(os.path.join(meta, "MANIFEST.sha256"))
    fpath = os.path.join(meta, "files.sha256")
    if sha256_file(fpath) != man.get("files.sha256"):
        raise SystemExit("%s: files.sha256 does not match MANIFEST.sha256; aborting" % tag)
    files = read_hashes(fpath)
    paths, cat_sha = select_paths(tag, files, cat_dir, a)
    missing_listing = [p for p in paths if p not in files]
    if missing_listing:
        raise SystemExit("%s: catalogue lists %d paths not in files.sha256, e.g. %s" % (tag, len(missing_listing), missing_listing[0]))
    bad_cat = [p for p in paths if p in cat_sha and cat_sha[p] != files[p]]
    if bad_cat:
        raise SystemExit("%s: catalogue sha256 differs from files.sha256 for %d paths, e.g. %s" % (tag, len(bad_cat), bad_cat[0]))
    total = sum(1 for _ in paths)
    print("%s: %d of %d files selected" % (tag, total, len(files)))
    if a.list or not paths:
        for p in paths[:50]:
            print("  " + p)
        return {"tag": tag, "selected": total, "passed": True, "listed_only": True}
    clash = [p for p in paths if os.path.exists(os.path.join(a.dest, p))]
    if clash and not a.overwrite:
        raise SystemExit("%s: %d target files already exist in --dest (use --overwrite), e.g. %s" % (tag, len(clash), clash[0]))
    os.makedirs(a.dest, exist_ok=True)
    listf = os.path.join(workdir, "%s.members.txt" % tag)
    with open(listf, "w") as o:
        o.write("\n".join(paths) + "\n")
    parts = sorted((n, h) for n, h in man.items() if ".tar.zst.part-" in n)
    z = subprocess.Popen(["zstd", "-d", "--long=31", "-q", "-c"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    t = subprocess.Popen(["tar", "xf", "-", "-C", a.dest, "-T", listf], stdin=z.stdout)
    z.stdout.close()
    feeder = Feeder(source, tag, parts, z.stdin)
    feeder.start()
    feeder.join()
    zrc, trc = z.wait(), t.wait()
    parts_ok = feeder.error is None and len(feeder.result) == len(parts) and all(r["ok"] for r in feeder.result)
    bad, missing, same_live, diff_live, no_live, nbytes = [], [], 0, [], [], 0
    for p in paths:
        r = os.path.join(a.dest, p)
        if not os.path.isfile(r):
            missing.append(p)
            continue
        nbytes += os.path.getsize(r)
        if sha256_file(r) != files[p]:
            bad.append(p)
            continue
        if a.compare_with:
            live = os.path.join(a.compare_with, p)
            if not os.path.isfile(live):
                no_live.append(p)
            elif filecmp.cmp(r, live, shallow=False):
                same_live += 1
            else:
                diff_live.append(p)
    ok = parts_ok and zrc == 0 and trc == 0 and not bad and not missing and not diff_live
    rep = {
        "tag": tag, "selected": total, "restored_ok": total - len(bad) - len(missing), "bytes": nbytes,
        "hash_mismatch": bad[:50], "missing": missing[:50], "parts": feeder.result, "zstd_rc": zrc, "tar_rc": trc,
        "feeder_error": repr(feeder.error) if feeder.error else None,
        "selectors": {"experiment": a.experiment, "dir": a.dir, "since": a.since, "until": a.until, "path_glob": a.path_glob},
        "compare_with": a.compare_with, "identical_to_live": same_live, "differs_from_live": diff_live[:50],
        "live_copy_absent": len(no_live), "passed": ok,
    }
    with open(os.path.join(a.dest, "RESTORE_REPORT_%s.json" % tag), "w") as o:
        json.dump(rep, o, indent=1)
    print(json.dumps({k: rep[k] for k in ("tag", "selected", "restored_ok", "bytes", "identical_to_live", "passed")}))
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", action="append")
    ap.add_argument("--experiment")
    ap.add_argument("--dir", action="append")
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--path-glob", action="append")
    ap.add_argument("--dest", required=True, help="restore target directory (members keep their archive paths under it)")
    ap.add_argument("--catalogue", default=DEFAULT_CAT)
    ap.add_argument("--repo", default="dayyansheikh/arepo-data")
    ap.add_argument("--parts-dir", help="use a local release directory instead of GitHub (tests/offline); needs exactly one --tag")
    ap.add_argument("--workdir", default=os.path.expanduser("~/arepo_restore_work"))
    ap.add_argument("--compare-with", help="also compare each restored file byte for byte with BASE/<path>")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--list", action="store_true", help="only show what would be restored")
    a = ap.parse_args(argv)
    a.dest = os.path.abspath(os.path.expanduser(a.dest))
    tags = a.tag or sorted(f[:-6] for f in os.listdir(a.catalogue) if f.endswith(".jsonl"))
    if a.parts_dir and len(tags) != 1:
        raise SystemExit("--parts-dir needs exactly one --tag")
    source = LocalSource(a.parts_dir) if a.parts_dir else GhSource(a.repo)
    os.makedirs(a.workdir, exist_ok=True)
    rc = 0
    for tag in tags:
        rep = restore_release(tag, source, a.catalogue, a, a.workdir)
        if not rep.get("passed"):
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
