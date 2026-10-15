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

## Blocked: unattended Claude sessions (needs a user decision)
On 2026-10-15 the Claude Code safety classifier (auto mode) refused to run even a dry test of `autopilot.py`. Its reason was "Create Unsafe Agents".
- The autopilot starts unattended Claude sessions with `--permission-mode bypassPermissions`.
- This was not worked around.

The user's options:
1. **Approve the Mac autopilot as built.** The user installs or tests it themselves, or adds an explicit permission rule. Every session is bounded to 3 hours, never overlaps another, sleeps through usage limits and refuses API-key auth.
   - Limitation: it runs only while the Mac is awake.
2. **A safer variant:** headless sessions with an `--allowedTools` allowlist instead of bypass. This means no `ssh` deploys, no pushes, and analysis plus queue specs only. That needs a new design pass.
3. **Server-only (current state):** the queue keeps computing unattended, and Claude work resumes when the user opens a session ("continue from checkpoint").

## Current state
Option 3 is live. The queue worker has been verified on the host, including a kill -9 interruption and recovery.
