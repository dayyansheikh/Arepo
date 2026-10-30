# ruff: noqa: E501
"""Owner messages from the Lab board to an autopilot instance's INBOX.md (Mac side).

The autopilot prompts tell each session to read `<home>/INBOX.md` first and then move it to
`INBOX.done-<UTC time>.md`. lab_mac appends every message fetched from the API to INBOX.md under a header carrying an
HTML-comment marker `<!-- lab-msg:<id> -->`, so writing is idempotent (a message already in INBOX.md or in any
INBOX.done-* file is never written twice) and the board can follow it: `delivered` once it is in INBOX.md, `read` once
INBOX.md no longer contains it (the session moved the file). Files are created owner-only (0600).
"""
from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from pathlib import Path

INBOX = "INBOX.md"
DONE_GLOBS = ("INBOX.done*", "*/INBOX.done*")
MAX_BODY = 4000
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def marker(msg_id: int) -> str:
    return f"<!-- lab-msg:{int(msg_id)} -->"


def clean_body(body) -> str:
    text = _CTRL.sub("", str(body or "")).replace("\r\n", "\n").replace("\r", "\n").strip()
    text = re.sub(r"lab-msg:\s*\d+", "lab-msg", text)  # a body can never forge another message's marker
    return text[:MAX_BODY]


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def done_files(home: Path) -> list[Path]:
    out: list[Path] = []
    for g in DONE_GLOBS:
        try:
            out.extend(p for p in Path(home).glob(g) if p.is_file())
        except OSError:
            continue
    return sorted(set(out))


def _fmt_time(iso: str | None) -> str:
    try:
        t = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if t.tzinfo is None:
            t = t.replace(tzinfo=UTC)
        return t.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return "unknown time"


def write_message(home: Path, msg_id: int, body, created_at: str | None) -> str:
    """Append one message to <home>/INBOX.md. Returns 'written' or 'already' (marker present in INBOX.md or a
    done file). Raises OSError when the inbox cannot be written."""
    home = Path(home)
    if not home.is_dir():
        raise FileNotFoundError(f"instance home {home.name} not found")
    mk = marker(msg_id)
    inbox = home / INBOX
    if mk in _read(inbox) or any(mk in _read(p) for p in done_files(home)):
        return "already"
    text = clean_body(body)
    block = (f"\n---\n\n## Message from the owner (sent {_fmt_time(created_at)} from the Lab board) {mk}\n\n"
             f"{text}\n")
    new = not inbox.exists()
    fd = os.open(inbox, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as fh:
        if new:
            fh.write("# Owner messages\n\nRead these first and treat them as the owner's instructions for this session; "
                     "then move this file to INBOX.done-<UTC time>.md.\n")
        fh.write(block)
    return "written"


def message_state(home: Path, msg_id: int) -> tuple[str, str | None]:
    """('pending', None) while INBOX.md holds the message; ('read', <iso>) once it is gone from INBOX.md (time = the
    done file's modification time when found there, else now)."""
    home = Path(home)
    mk = marker(msg_id)
    if mk in _read(home / INBOX):
        return "pending", None
    for p in done_files(home):
        if mk in _read(p):
            try:
                t = datetime.fromtimestamp(p.stat().st_mtime, UTC)
            except OSError:
                t = datetime.now(UTC)
            return "read", t.strftime("%Y-%m-%dT%H:%M:%SZ")
    return "read", None
