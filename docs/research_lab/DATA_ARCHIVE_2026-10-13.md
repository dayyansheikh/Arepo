# Data archive and Mac clean-up (2026-10-13)

You asked on 2026-10-13 to shrink AREPO's data and upload it to the private GitHub repo `dayyansheikh/arepo-data`, for both the
Mac and the Oracle server. This page says what is archived, how it was checked, and the single command you run to free the Mac's
disk. Claude did not delete anything on the Mac.

## What is in GitHub now (private repo `dayyansheikh/arepo-data`)
| Release | Contents | Files | Original size | Compressed | Verified |
|---|---|---|---|---|---|
| `data-20261011` | All of `data-dumps` as of 2026-10-11 ~01:00Z | 206,934 | 38.8 GB | 2.88 GB (2 parts) | PASS, re-verified 2026-10-13 |
| `data-20261013-fs2` | Phase 3 runs added after that (D118, D120, two captures) | 51,168 | 6.68 GB | 0.66 GB (1 part) | PASS |
| `data-20261013-research-lab` | `research_lab` files new or changed since 2026-10-11 | 47,991 | 6.51 GB | 4.79 GB (6 parts) | PASS, restore sample 60/60 |
| `data-20261014-research-lab-tail` | 57 `research_lab` files last written on the Mac before cutover | 57 | 0.33 GB | 0.21 GB | PASS, restore sample 57/57 |
| `retire-20261013` | Mac deletion manifests (tier 1a, tier 1b, tier 2) and summaries | | | | round-trip hash checked |

- **Format.** Each release is a tar of the original file bytes, compressed with zstd and split into parts (`*.tar.zst.part-aa`, ...).
  `files.sha256` lists every file's original hash, `MANIFEST.sha256` lists every part's hash, `README.md` has the restore command,
  and `VERIFY.json` holds the verification result. Nothing was re-encoded, so a restore gives back byte-identical files.
- **Verification.** Every part was streamed back from GitHub and checked against `MANIFEST.sha256`. The stream was then decompressed
  and every file inside was re-hashed against `files.sha256`, in both directions (nothing missing, nothing extra). The only extra
  member was one macOS `._.DS_Store` metadata entry in `data-20261011`, which is not data. A real restore was also run on a random
  sample of 60 files per release and compared byte for byte with the originals. All 60 were identical.
- **Not archived yet.** 48 files that were modified in the 3 hours before the run, from live collectors and snapshots in progress.
  They will be in a later release or on the Oracle host. (The deletion manifests were built later and skip only the one file whose
  hash had changed by then, `data-dumps/.DS_Store`.)

## Compression measured
| Data | Method | Ratio |
|---|---|---|
| 5 consecutive snapshot `rows.csv.gz` (135 MB) | original bytes, `zstd -19 --long=31` | 1.04x (the gzip files are already compressed) |
| same, decompressed CSV (477 MB) | `zstd -19 --long=31` across the 5 files | 11.8x on the CSV, so 3.3x smaller than the `.gz` originals |
| same, decompressed CSV | `zstd -19` without the long window | 4.3x (the long window adds most of the cross-snapshot gain) |
| Phase 3 capture JSON (6.68 GB) | `zstd -12 --long=27` | 10.1x |

The archive keeps the original `.gz` bytes, because re-creating a gzip file byte for byte from its CSV is not guaranteed. Storing the
CSV and re-gzipping on restore would cut the snapshot archive about 3x, but it would not be provably lossless, so it was not used.
The releases use `-12 --long=27`. On an 8 GB Mac, level 19 runs at about 3 MB/s and a 2 GB window is a memory risk, and the gain on
gzip originals is nil. Restore with `zstd -d --long=31`, which decodes any window up to 2 GB.

## Free the Mac's disk (you run this)
There are two manifests, each pinned by hash in the release `retire-20261013`. Every listed file is byte-identical to a file in a
verified release. Together they cover everything under `data-dumps/` outside `research_lab/`: 258,043 files.

| Manifest | What | Files | Frees on disk |
|---|---|---|---|
| **tier 1a** | Unprotected Phase 3 captures, panels and pilots (for example `fs2_capture_0da4…`, `eaec…`, `7e20…`, the window/screening pilots) | 98,530 | **about 14.5 GB** |
| **tier 1b** | The protected canonical Phase 3 roots: D082, D094, D097, D114, D116, D118, D120, the request-capacity captures, `fs2_capture_52eead5d` and `phase3_evidence_capsules` (list in `archive/PROTECTED_PREFIXES_2026-10-13.txt`) | 159,513 | **about 17.6 GB** |

**Tier 1b needs its own decision.** The retention policy says these roots "remain untouched". It was written for capsule-only clean-ups,
and here every byte is archived and verified, but deleting the local copies is still your explicit decision. Run tier 1a alone if
you prefer.

**Before you run anything.** GitHub becomes the **only** copy (one private repo, one account, no second backup). Deleting that repo, a
release asset or the account loses this data for good. Recommended: copy the archive parts to an external drive first:
```bash
mkdir -p /Volumes/<drive>/arepo-archive && cd /Volumes/<drive>/arepo-archive && for r in data-20261011 data-20261013-fs2; do gh release download $r -R dayyansheikh/arepo-data -D $r; done
```
That is 3.5 GB.

**Dry run first.** This deletes nothing and needs no session:
```bash
cd ~/Projects/astrolabe/backend && python3 scripts/retire_archived_local.py --manifest-name DELETION_MANIFEST_2026-10-13_tier1a.tsv.gz --manifest-sha256 db29b7361cf34a90ff65598a35feed9a4ef7c78b72c7c1b546866d4f3277d8a7
```

**Tier 1a, real run** (you open the retirement session yourself):
```bash
cd ~/Projects/astrolabe/backend && AREPO_RETIREMENT_SESSION=1 python3 scripts/retire_archived_local.py --manifest-name DELETION_MANIFEST_2026-10-13_tier1a.tsv.gz --manifest-sha256 db29b7361cf34a90ff65598a35feed9a4ef7c78b72c7c1b546866d4f3277d8a7 --confirm
```

**Tier 1b, real run** (only if you decide to retire the protected roots' local copies):
```bash
cd ~/Projects/astrolabe/backend && AREPO_RETIREMENT_SESSION=1 python3 scripts/retire_archived_local.py --manifest-name DELETION_MANIFEST_2026-10-13_tier1b.tsv.gz --manifest-sha256 d4c5e4bc94ac039188db85e71bee54ddece55db82ba5f80c48fab540a72155ff --confirm
```

**What the script checks before deleting anything.** If any of these fails, it stops with nothing deleted.
- The manifest matches its pinned hash.
- Every path is under `data-dumps/`, is not in `research_lab/`, and has no `..`.
- For each release: `files.sha256` matches `MANIFEST.sha256`; `VERIFY.json` passed for that same `files.sha256`; the release is published;
  every part is present with the size that was verified; and every manifest row agrees with the release.

**Then, file by file.** It re-hashes each local file and deletes it only if the file is still byte-identical. Any other file is kept.
It removes only directories that it emptied.

**Logs.** Every decision goes to `~/arepo_retirement_logs/retirement_<time>.jsonl.gz`, and the measured space freed is in
`..._summary.json`. Copy the numbers into `archive/RETIREMENT_CAPSULE_2026-10-13.json` (`reclaimed_space`), or ask Claude to.

**What is kept.** All of `data-dumps/research_lab/`, every file in `docs/` (the frozen evidence JSONs and protocols), and anything
whose hash changed.

**What you give up.** Until you restore from GitHub, you lose:
- local replay or re-verification of the deleted Phase 3 frames;
- re-running E001's extraction (`run_research_e001.py` now refuses to run rather than overwrite its outputs);
- re-running the dependence-clustering analysis (tier 1b).

The local wrapper files `data-dumps/fs2_d116/d118/d120_*_evaluation.json` are also deleted, and they are archived. Outcomes and
statuses do not change.

### Tier 2: `data-dumps/research_lab` (approved 2026-10-14, after the Oracle cutover)
- **Scope.** The tier 2 manifest lists all 48,104 `research_lab` files, which frees **about 7.45 GB** on disk. Each file matches a verified
  release: `data-20261011`, `data-20261013-research-lab` or `data-20261014-research-lab-tail`.
- **Mac collection.** It has stopped: no `com.arepo` jobs are loaded and there have been no writes since about 11:28Z on 14 Oct.
- **Opt-in.** The script refuses `research_lab` rows unless you pass `--allow-research-lab`, and it keeps the `research_lab` folder
  itself.
- **What you give up.** Afterwards the Mac-only analysis data (`history`, `if_h2`, `ml_cache`, `large_trade_census`,
  `history_sources`, `dev_snapshots_v2`, ...) exists only on GitHub. Any local re-analysis, or a re-derivation of the E005/E007 dev
  fits, needs a restore first. The live experiments read the server, which holds byte-identical dev fits and append-only logs that
  extend the Mac's (checked 2026-10-14).

```bash
cd ~/Projects/astrolabe/backend && AREPO_RETIREMENT_SESSION=1 python3 scripts/retire_archived_local.py --manifest-name DELETION_MANIFEST_2026-10-14_tier2.tsv.gz --manifest-sha256 9f1a946eafe827bb4e641ebf5e62488207eadf9ab38f512bff06d7138bcce71d --allow-research-lab --confirm
```

## Restore
```bash
gh release download <release> -R dayyansheikh/arepo-data -p '*.tar.zst.part-*' -p MANIFEST.sha256 -p files.sha256
shasum -a 256 -c MANIFEST.sha256
cat *.tar.zst.part-* | zstd -d --long=31 | tar xf -        # run from the repo root; or name paths after "xf -"
shasum -a 256 -c files.sha256
```
A release's parts form one zstd stream, so restoring even one file needs every part of that release.

## research_lab before 2026-10-14
Tier 1 left `research_lab` alone while the Mac collectors were still running. After the Oracle cutover, tier 2 above covers it. The
deletion script only accepts its rows with `--allow-research-lab`. The rollback plan in `COLLECTION_HOST.md` copies host data back,
so it does not need the Mac copies.

## Oracle server
The server held only about 35 MB of fresh, actively written data at archive time, so nothing there was archived. The nightly rotation
script for the server is described in `COLLECTION_HOST.md`, in the section "Nightly archive rotation". It is not installed. It needs a
GitHub token on the server and a decision on which directories may rotate (see that section).

## Tools
- `backend/scripts/archive_release.py`: build, verify and restore-sample.
- `backend/scripts/build_deletion_manifest.py`: builds the deletion manifest.
- `backend/scripts/retire_archived_local.py`: the deletion script you run.
- `backend/scripts/archive_rotate.py`: the server rotation script.
- Capsule: `docs/research_lab/archive/RETIREMENT_CAPSULE_2026-10-13.json`.
