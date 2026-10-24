# Persistence mechanism: decision record (2026-10-15)

## What was required (mission §2)
- Keep research going through session ends and the 5-hour and weekly Claude usage limits.
- Recover from crashes.
- Never bill the API.
- Don't claim autonomy until it has been tested.

## Options checked (official Claude Code docs, 2026-10-15)
| Option | Verdict |
|---|---|
| **Server worker** (cron and a durable queue on `ssh oracle`) | **Built and verified.** Needs no Claude at all, so usage limits never stop it. See `../queue/README.md`. |
| **Headless `claude -p`** on the Mac via launchd, using the existing claude.ai Max login | Technically supported: `claude auth status` shows `authMethod: claude.ai`, `subscriptionType: max`, and no API key is set. Built as `scripts/autopilot/autopilot.py`. It is **not installed**; see "Blocked" below. |
| **`claude -p` on the server** | Needs Node or the native binary, plus a `claude setup-token` OAuth token that the user generates interactively (one-year token). It is a credential action, so it's the user's call. |
| **Cloud routines** (`/schedule`) | Minimum interval of 1 hour. They run in Anthropic's cloud and need a GitHub repo checkout. They cannot reach the Oracle host without placing an SSH key in the cloud, which is rejected for security. They draw on the same subscription usage. Not suitable as the main loop. |
| **`/loop` inside a session** | Dies with the session or at a usage limit. Not persistence. |

### How limits appear in `-p` mode
- The process exits non-zero and prints `You've hit your session limit · resets 3:45pm` or `... weekly limit · resets Mon 12:00am`.
- No reset field is documented in the JSON output. `autopilot.py` parses that text and sleeps until the reset, falling back to a 30-minute retry.

### One-time usage reset
- No redemption mechanism is documented anywhere in the Claude Code docs or support articles.
- The user was alerted by ntfy on 2026-10-15 to check claude.ai/settings/usage (or run `/usage`) before **Wed 21 Oct**.

## Decision and installed state (2026-10-15 ~19:05Z)
- **History.** The auto-mode classifier first refused to test the full-power autopilot ("Create Unsafe Agents"). It was not
  worked around.
- **User decision, 2026-10-15 ~20:00 UTC+1:** "I'll hand over the keys. I approve the full power autopilot ... You can just
  do that. Set it up."
- **Installed:** launchd `com.arepo.autopilot` (`scripts/autopilot/install.sh`; remove with `--uninstall`).
  - It ticks every 30 min, at login and after wake.
  - A session starts only when none is running, the queue is not paused, and no usage-limit reset is pending.
  - Each session lasts up to 5 h, runs under `caffeinate -i` so the Mac does not idle-sleep mid-session, and uses
    `--permission-mode bypassPermissions`. The mode is `AREPO_AUTOPILOT_MODE=full`; `restricted` switches to an allowlist
    with no push, no rm and the host reached only via `scripts/oracle/{deploy,queue_status}.sh`.
- **Verified** (test home `~/.arepo/autopilot_test`):
  1. A harmless real headless run returned `AUTOPILOT_OK`, rc 0, 5 s, on the claude.ai Max login.
  2. A controlled interruption: the session was killed with -9 mid-run, the next tick recorded `interrupted` and the
     following run was `ok`.
  3. The usage-limit parser read "resets 3:45pm" as the next 15:45 local + 2 min, "resets Mon 12:00am" as the next Monday
     00:00 local + 2 min, and with no time it falls back to retrying in 30 min.
  - A real usage-limit hit has not yet been observed. The first one will be checked in `runs.jsonl`.
- **Limits:**
  - It runs only while the Mac is awake. Lid-closed sleep stops it; launchd catches up after wake.
  - When the user chats interactively while an autopilot session is running, two sessions share the repo. Pause the
    autopilot first (below), or accept that both may commit, each committing only its own files.
- **Control:**
  - `/usr/bin/python3 scripts/autopilot/autopilot.py status|pause|resume|stop`;
  - logs and state in `~/.arepo/autopilot/` (`runs.jsonl`, `logs/`).
