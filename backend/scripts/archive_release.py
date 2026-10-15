#!/usr/bin/env python3
# ruff: noqa: E501, UP031  (runs on Python 3.6 collection hosts; long docstring/README lines)
"""Lossless zstd-tar release archiver for AREPO data: build, verify, restore-sample.

Scheme (same as the private `dayyansheikh/arepo-data` release `data-20261011`):
  * one PAX tar stream of the ORIGINAL file bytes (no re-encoding, no gzip normalisation), member names
    relative to --base (for example `data-dumps/research_lab/...`);
  * compressed by `zstd -<level> --long=<window>` and split into `<prefix>.tar.zst.part-aa`, `-ab`, ...;
  * `files.sha256`  = sha256 of every member, computed from the exact bytes written into the tar;
  * `MANIFEST.sha256` = sha256 of every part and of files.sha256;
  * `ARCHIVE_INFO.json`, `README.md`, and after a passing verify `VERIFY.json`.

Restore:  cat <prefix>.tar.zst.part-* | zstd -d --long=31 | tar xf -

Disk use is bounded by one part: each part is uploaded as soon as it is full, its upload size is checked, then the
local staging copy is removed. Verification streams every part back from GitHub (no disk), checks each part hash
against MANIFEST.sha256, decompresses, and re-hashes every tar member against files.sha256 (both directions).
The release is created as a draft and only published by `verify --publish` after a pass.

Requires Python >= 3.6, `zstd` and an authenticated `gh` on PATH. Never deletes anything outside its own
staging directory.
"""

import argparse
import datetime
import filecmp
import functools
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import tarfile
import threading
import time

CHUNK = 4 << 20
PIPE = subprocess.PIPE


def log(msg):
    sys.stderr.write("[{}] {}\n".format(datetime.datetime.utcnow().strftime("%H:%M:%SZ"), msg))
    sys.stderr.flush()


def run(cmd, check=True):
    p = subprocess.Popen(cmd, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    if check and p.returncode != 0:
        raise RuntimeError(
            "command failed (%d): %s\n%s" % (p.returncode, " ".join(cmd), err.decode()[-2000:])
        )
    return p.returncode, out.decode(), err.decode()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(CHUNK), b""):
            h.update(b)
    return h.hexdigest()


def part_suffixes():
    a = "abcdefghijklmnopqrstuvwxyz"
    for x in a:
        for y in a:
            yield x + y


def release_exists(repo, tag):
    return run(["gh", "release", "view", tag, "-R", repo, "--json", "tagName"], check=False)[0] == 0


def release_assets(repo, tag):
    out = run(["gh", "release", "view", tag, "-R", repo, "--json", "assets,isDraft"])[1]
    d = json.loads(out)
    return {a["name"]: a["size"] for a in d["assets"]}, d["isDraft"]


def upload(repo, tag, path, tries=10):
    name = os.path.basename(path)
    size = os.path.getsize(path)
    for i in range(tries):
        rc, _, err = run(
            ["gh", "release", "upload", tag, path, "-R", repo, "--clobber"], check=False
        )
        if rc == 0:
            assets, _ = release_assets(repo, tag)
            if assets.get(name) == size:
                return
            err = "remote size %r != local %d" % (assets.get(name), size)
        log("upload %s attempt %d failed: %s" % (name, i + 1, err.strip()[-300:]))
        time.sleep(min(30 * (i + 1), 300))  # rides out short network outages
    raise RuntimeError("upload failed: " + name)


class HashingReader:
    """Feeds exactly `size` bytes to tarfile; pads with zeros if the file shrank (flagged as changed)."""

    def __init__(self, fh, size):
        self.fh, self.left, self.h, self.short = fh, size, hashlib.sha256(), False

    def read(self, n=-1):
        if self.left <= 0:
            return b""
        n = self.left if n is None or n < 0 else min(n, self.left)
        b = self.fh.read(n)
        if len(b) < n:
            self.short = True
            b = b + b"\0" * (n - len(b))
        self.left -= len(b)
        self.h.update(b)
        return b


class PartWriter(threading.Thread):
    def __init__(self, src, repo, tag, stage, prefix, part_size, on_error):
        threading.Thread.__init__(self)
        self.daemon = True
        self.src, self.repo, self.tag, self.stage = src, repo, tag, stage
        self.prefix, self.part_size, self.on_error = prefix, part_size, on_error
        self.parts, self.error = [], None

    def _flush(self, path, h, size):
        upload(self.repo, self.tag, path)
        self.parts.append({"name": os.path.basename(path), "size": size, "sha256": h.hexdigest()})
        os.remove(path)
        log(f"part {os.path.basename(path)} uploaded ({size / 1e6:.1f} MB), staging copy removed")

    def run(self):
        try:
            names = part_suffixes()
            cur = None
            while True:
                b = self.src.read(CHUNK)
                if not b:
                    break
                while b:
                    if cur is None:
                        path = os.path.join(self.stage, f"{self.prefix}.tar.zst.part-{next(names)}")
                        cur, h, size = open(path, "wb"), hashlib.sha256(), 0
                    take = b[: self.part_size - size]
                    b = b[len(take) :]
                    cur.write(take)
                    h.update(take)
                    size += len(take)
                    if size >= self.part_size:
                        cur.close()
                        self._flush(path, h, size)
                        cur = None
            if cur is not None:
                cur.close()
                self._flush(path, h, size)
        except BaseException as e:  # noqa: BLE001 - surfaced to the main thread
            self.error = e
            self.on_error()


def build(a):
    rels = [ln.rstrip("\n") for ln in open(a.list) if ln.strip()]
    if len(set(rels)) != len(rels):
        raise SystemExit("duplicate paths in list")
    reuse = False
    if release_exists(a.repo, a.tag):
        assets, draft = release_assets(a.repo, a.tag)
        if not draft or assets:
            raise SystemExit(f"release {a.tag} already exists; refusing to overwrite")
        reuse = True  # an empty draft left by an aborted build is reused
        log(f"reusing empty draft release {a.tag}")
    stage = os.path.join(a.workdir, a.tag)
    os.makedirs(stage, exist_ok=True)
    prefix = a.prefix or "arepo-" + a.tag
    notes = (
        a.notes
        or "Lossless zstd tar of original files. Draft until VERIFY.json passes. See README.md."
    )
    if not reuse:
        run(
            [
                "gh",
                "release",
                "create",
                a.tag,
                "-R",
                a.repo,
                "--draft",
                "--title",
                a.title or a.tag,
                "--notes",
                notes,
            ]
        )
    log("draft release %s created; %d files" % (a.tag, len(rels)))
    z = subprocess.Popen(
        ["zstd", "-%d" % a.level, "--long=%d" % a.long, "-T%d" % a.threads, "-q", "-c"],
        stdin=PIPE,
        stdout=PIPE,
    )
    w = PartWriter(z.stdout, a.repo, a.tag, stage, prefix, a.part_size, z.kill)
    w.start()
    files, changed, missing, total = {}, [], [], 0
    t0 = time.time()
    tar = tarfile.open(fileobj=z.stdin, mode="w|", format=tarfile.PAX_FORMAT)
    try:
        for i, rel in enumerate(rels):
            path = os.path.join(a.base, rel)
            try:
                st = os.stat(path)
                fh = open(path, "rb")
            except FileNotFoundError:
                missing.append(rel)
                continue
            with fh:
                ti = tar.gettarinfo(fileobj=fh, arcname=rel)
                r = HashingReader(fh, ti.size)
                tar.addfile(ti, r)
            st2 = os.stat(path)
            if r.short or st2.st_size != st.st_size or st2.st_mtime_ns != st.st_mtime_ns:
                changed.append(rel)
            files[rel] = (r.h.hexdigest(), ti.size)
            total += ti.size
            if (i + 1) % 5000 == 0:
                log(
                    "%d/%d files, %.2f GB in, %.0f s"
                    % (i + 1, len(rels), total / 1e9, time.time() - t0)
                )
        tar.close()
        z.stdin.close()
    except BaseException as e:
        z.kill()
        w.join()
        raise RuntimeError(f"build aborted: {e!r}; writer error: {w.error!r}") from e
    w.join()
    if z.wait() != 0 or w.error is not None:
        raise RuntimeError(f"zstd rc={z.returncode} writer error={w.error!r}")
    meta = os.path.join(stage, "meta")
    os.makedirs(meta, exist_ok=True)
    fs = os.path.join(meta, "files.sha256")
    with open(fs, "w") as o:
        for rel in sorted(files):
            o.write(f"{files[rel][0]}  {rel}\n")
    with open(os.path.join(meta, "MANIFEST.sha256"), "w") as o:
        for p in w.parts:
            o.write("{}  {}\n".format(p["sha256"], p["name"]))
        o.write(f"{sha256_file(fs)}  files.sha256\n")
    info = {
        "tag": a.tag,
        "repo": a.repo,
        "prefix": prefix,
        "created_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "host": os.uname()[1],
        "base": os.path.abspath(a.base),
        "zstd": "-%d --long=%d" % (a.level, a.long),
        "n_files": len(files),
        "logical_bytes": total,
        "compressed_bytes": sum(p["size"] for p in w.parts),
        "parts": w.parts,
        "changed_during_archive": changed,
        "missing_at_archive": missing,
        "seconds": round(time.time() - t0),
    }
    with open(os.path.join(meta, "ARCHIVE_INFO.json"), "w") as o:
        json.dump(info, o, indent=1)
    with open(os.path.join(meta, "README.md"), "w") as o:
        o.write(
            README.format(
                tag=a.tag,
                repo=a.repo,
                prefix=prefix,
                n=len(files),
                gb=total / 1e9,
                cgb=info["compressed_bytes"] / 1e9,
                z=info["zstd"],
            )
        )
    # per-file sizes for the data catalogue (not part of MANIFEST: the hashes in files.sha256 are the evidence)
    with open(os.path.join(meta, "files.bytes.json"), "w") as o:
        json.dump({rel: files[rel][1] for rel in sorted(files)}, o)
    for n in ("files.sha256", "MANIFEST.sha256", "ARCHIVE_INFO.json", "README.md", "files.bytes.json"):
        upload(a.repo, a.tag, os.path.join(meta, n))
    log(
        "built %s: %d files, %.2f GB -> %.2f GB in %d parts; changed=%d missing=%d"
        % (
            a.tag,
            len(files),
            total / 1e9,
            info["compressed_bytes"] / 1e9,
            len(w.parts),
            len(changed),
            len(missing),
        )
    )
    print(json.dumps({k: info[k] for k in ("tag", "n_files", "logical_bytes", "compressed_bytes")}))


README = """# {tag}

Lossless archive of {n} original AREPO data files ({gb:.2f} GB logical, {cgb:.2f} GB compressed, zstd {z}).
Every file is stored byte-for-byte as it was on disk; nothing was re-encoded.

## Restore everything

```bash
gh release download {tag} -R {repo} -p '{prefix}.tar.zst.part-*' -p 'MANIFEST.sha256' -p 'files.sha256'
shasum -a 256 -c MANIFEST.sha256          # every part and files.sha256
cat {prefix}.tar.zst.part-* | zstd -d --long=31 | tar xf -
shasum -a 256 -c files.sha256             # every restored file
```

Restore selected paths only: `cat {prefix}.tar.zst.part-* | zstd -d --long=31 | tar xf - <path> [<path> ...]`
(the parts form one zstd stream, so all parts are needed even for one file).

`ARCHIVE_INFO.json` records the host, base directory, part sizes and any file that changed while it was being
archived (such a file's hash in files.sha256 is the hash of the archived bytes). `VERIFY.json` records the
independent download-back verification. Tool: `backend/scripts/archive_release.py` in the AREPO repo.
"""


class PartFeeder(threading.Thread):
    """Streams each part from GitHub into `sink`, hashing it on the way."""

    def __init__(self, repo, tag, parts, sink):
        threading.Thread.__init__(self)
        self.daemon = True
        self.repo, self.tag, self.parts, self.sink = repo, tag, parts, sink
        self.result, self.error = [], None

    def run(self):
        try:
            for name, want in self.parts:
                p = subprocess.Popen(
                    ["gh", "release", "download", self.tag, "-R", self.repo, "-p", name, "-O", "-"],
                    stdout=PIPE,
                )
                h, n = hashlib.sha256(), 0
                for b in iter(functools.partial(p.stdout.read, CHUNK), b""):
                    h.update(b)
                    n += len(b)
                    self.sink.write(b)
                if p.wait() != 0:
                    raise RuntimeError("download failed: " + name)
                self.result.append(
                    {"name": name, "bytes": n, "sha256": h.hexdigest(), "ok": h.hexdigest() == want}
                )
                log(
                    "streamed {} ({:.1f} MB) hash {}".format(
                        name, n / 1e6, "OK" if h.hexdigest() == want else "MISMATCH"
                    )
                )
            self.sink.close()
        except BaseException as e:  # noqa: BLE001
            self.error = e
            try:
                self.sink.close()
            except Exception:  # noqa: BLE001
                pass


def fetch_meta(repo, tag, dest):
    os.makedirs(dest, exist_ok=True)
    run(
        [
            "gh",
            "release",
            "download",
            tag,
            "-R",
            repo,
            "-D",
            dest,
            "--clobber",
            "-p",
            "MANIFEST.sha256",
            "-p",
            "files.sha256",
        ]
    )
    man = {}
    for ln in open(os.path.join(dest, "MANIFEST.sha256")):
        h, n = ln.rstrip("\n").split("  ", 1)
        man[n] = h
    if sha256_file(os.path.join(dest, "files.sha256")) != man.get("files.sha256"):
        raise RuntimeError("files.sha256 does not match MANIFEST.sha256")
    files = {}
    for ln in open(os.path.join(dest, "files.sha256")):
        h, p = ln.rstrip("\n").split("  ", 1)
        files[p] = h
    parts = sorted((n, h) for n, h in man.items() if ".tar.zst.part-" in n)
    return man, files, parts


def verify(a):
    dest = os.path.join(a.workdir, a.tag, "verify")
    man, files, parts = fetch_meta(a.repo, a.tag, dest)
    assets, draft = release_assets(a.repo, a.tag)
    size_problems = [n for n, _ in parts if n not in assets]
    z = subprocess.Popen(["zstd", "-d", "--long=31", "-q", "-c"], stdin=PIPE, stdout=PIPE)
    feeder = PartFeeder(a.repo, a.tag, parts, z.stdin)
    feeder.start()
    seen, bad, extra, appledouble, nonfile = set(), [], [], [], 0
    t0 = time.time()
    tar = tarfile.open(fileobj=z.stdout, mode="r|")
    for m in tar:
        if not m.isfile():
            nonfile += 1
            continue
        h = hashlib.sha256()
        f = tar.extractfile(m)
        for b in iter(functools.partial(f.read, CHUNK), b""):
            h.update(b)
        if m.name in seen:
            bad.append({"path": m.name, "why": "duplicate member"})
        seen.add(m.name)
        if m.name not in files:
            if os.path.basename(m.name).startswith("._"):
                appledouble.append(m.name)  # macOS bsdtar metadata member, not a data file
            else:
                extra.append(m.name)
        elif files[m.name] != h.hexdigest():
            bad.append({"path": m.name, "why": "hash mismatch"})
        if len(seen) % 20000 == 0:
            log("%d members verified" % len(seen))
    tar.close()
    feeder.join()
    zrc = z.wait()
    missing = sorted(set(files) - seen)
    ok = (
        feeder.error is None
        and zrc == 0
        and not bad
        and not extra
        and not missing
        and not size_problems
        and len(feeder.result) == len(parts)
        and all(r["ok"] for r in feeder.result)
    )
    rep = {
        "tag": a.tag,
        "verified_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "host": os.uname()[1],
        "method": "every part streamed back from GitHub, hashed against MANIFEST.sha256, decompressed with "
        "zstd -d --long=31, every tar member re-hashed against files.sha256 in both directions",
        "parts": feeder.result,
        "n_listed": len(files),
        "n_members_verified": len(seen),
        "hash_mismatches": bad,
        "missing_from_archive": missing[:50],
        "n_missing": len(missing),
        "unlisted_members": extra[:50],
        "unlisted_appledouble_metadata_members": appledouble,
        "nonfile_members": nonfile,
        "zstd_rc": zrc,
        "feeder_error": repr(feeder.error) if feeder.error else None,
        "files_sha256": man["files.sha256"],
        "passed": ok,
        "seconds": round(time.time() - t0),
    }
    out = os.path.join(dest, "VERIFY.json")
    with open(out, "w") as o:
        json.dump(rep, o, indent=1)
    log(
        "verify %s: %s (%d/%d members, %d parts)"
        % (a.tag, "PASS" if ok else "FAIL", len(seen), len(files), len(feeder.result))
    )
    if ok and a.upload_report:
        upload(a.repo, a.tag, out)
    if ok and a.publish and draft:
        run(["gh", "release", "edit", a.tag, "-R", a.repo, "--draft=false"])
        log(f"release {a.tag} published")
    print(
        json.dumps(
            {k: rep[k] for k in ("tag", "passed", "n_listed", "n_members_verified", "n_missing")}
        )
    )
    return 0 if ok else 1


def restore_sample(a):
    """Real restore pipeline for a random sample of members, then byte-for-byte comparison with the originals."""
    dest = os.path.join(a.workdir, a.tag, "restore_meta")
    man, files, parts = fetch_meta(a.repo, a.tag, dest)
    cands = sorted(p for p in files if os.path.isfile(os.path.join(a.compare_base, p)))
    rnd = random.Random(a.seed)
    sample = sorted(rnd.sample(cands, min(a.n, len(cands))))
    out = os.path.join(a.workdir, a.tag, "restore_sample")
    os.makedirs(out, exist_ok=True)
    listf = os.path.join(dest, "sample.txt")
    with open(listf, "w") as o:
        o.write("\n".join(sample) + "\n")
    z = subprocess.Popen(["zstd", "-d", "--long=31", "-q", "-c"], stdin=PIPE, stdout=PIPE)
    t = subprocess.Popen(["tar", "xf", "-", "-C", out, "-T", listf], stdin=z.stdout)
    z.stdout.close()
    feeder = PartFeeder(a.repo, a.tag, parts, z.stdin)
    feeder.start()
    feeder.join()
    z.wait()
    t.wait()
    res = []
    for p in sample:
        r = os.path.join(out, p)
        same = os.path.isfile(r) and filecmp.cmp(r, os.path.join(a.compare_base, p), shallow=False)
        res.append(
            {
                "path": p,
                "identical": same,
                "bytes": os.path.getsize(r) if os.path.isfile(r) else None,
            }
        )
    ok = all(r["identical"] for r in res)
    rep = {
        "tag": a.tag,
        "n": len(res),
        "identical": sum(r["identical"] for r in res),
        "passed": ok,
        "seed": a.seed,
        "bytes": sum(r["bytes"] or 0 for r in res),
    }
    with open(os.path.join(dest, "RESTORE_SAMPLE.json"), "w") as o:
        json.dump(dict(rep, files=res), o, indent=1)
    shutil.rmtree(out)
    print(json.dumps(rep))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--repo", default="dayyansheikh/arepo-data")
    ap.add_argument("--workdir", default=os.path.expanduser("~/arepo_archive_tmp"))
    sub = ap.add_subparsers(dest="cmd")
    b = sub.add_parser("build")
    b.add_argument("--tag", required=True)
    b.add_argument("--base", required=True, help="directory the listed relative paths are under")
    b.add_argument("--list", required=True, help="file with one relative path per line")
    b.add_argument("--prefix")
    b.add_argument("--title")
    b.add_argument("--notes")
    b.add_argument("--part-size", type=int, default=900 * 1000 * 1000)
    b.add_argument("--level", type=int, default=12)
    b.add_argument("--long", type=int, default=27)
    b.add_argument("--threads", type=int, default=4)
    v = sub.add_parser("verify")
    v.add_argument("--tag", required=True)
    v.add_argument("--upload-report", action="store_true")
    v.add_argument("--publish", action="store_true")
    r = sub.add_parser("restore-sample")
    r.add_argument("--tag", required=True)
    r.add_argument("--compare-base", required=True)
    r.add_argument("--n", type=int, default=40)
    r.add_argument("--seed", type=int, default=20261013)
    a = ap.parse_args()
    if a.cmd == "build":
        build(a)
    elif a.cmd == "verify":
        sys.exit(verify(a))
    elif a.cmd == "restore-sample":
        sys.exit(restore_sample(a))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
