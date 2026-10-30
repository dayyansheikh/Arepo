#!/usr/bin/env python3
"""Append-only union of two JSONL logs (used for docs/research_lab/trials.jsonl across hosts).

    union_jsonl.py BASE OTHER [OUT]

Writes BASE's lines in order, then OTHER's lines that are not already in BASE (exact line
match, OTHER's order), to OUT (default: BASE, extended by appending in place). Nothing is ever
dropped or reordered within a host, so running it in both directions converges on a superset. Stdlib
only
(runs under the server's system python3 too). Prints the number of lines added.
"""
import os
import sys


def read_lines(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [ln.rstrip("\n") for ln in f if ln.strip()]


def main(argv):
    if len(argv) not in (2, 3):
        print(__doc__)
        return 2
    base, other = read_lines(argv[0]), read_lines(argv[1])
    out = argv[2] if len(argv) == 3 else argv[0]
    seen = set(base)
    add = []
    for ln in other:
        if ln not in seen:
            seen.add(ln)
            add.append(ln)
    if out == argv[0]:  # in place: append only (never rewrite the inode an appender may hold)
        if add:
            needs_nl = False
            if os.path.exists(out) and os.path.getsize(out) > 0:
                with open(out, "rb") as f:
                    f.seek(-1, 2)
                    needs_nl = f.read(1) != b"\n"
            with open(out, "a", encoding="utf-8") as f:
                f.write(("\n" if needs_nl else "") + "".join(ln + "\n" for ln in add))
    else:
        tmp = out + ".union.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("".join(ln + "\n" for ln in base + add))
        os.replace(tmp, out)
    print(len(add))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
