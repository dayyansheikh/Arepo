#!/usr/bin/env python3
"""PreToolUse guard for Bash. Best-effort, not a security boundary: it blocks obvious destructive commands that
target protected AREPO evidence or production refs. Set AREPO_RETIREMENT_SESSION=1 (explicit, user-approved
capsule-first retirement session only) to allow evidence-path operations. Exit 2 = block."""
import json, os, re, sys

PROTECTED_RUNS = [  # canonical + required captures; see docs/AREPO_V2_CHECKPOINT.md
    "fs2_selection_panel_owned_pilot_20261003_1", "fs2_capture_f1f8ed08",          # D082
    "fs2_selection_panel_observation_pilot_20261008_1", "fs2_capture_cb25bb8e",    # D094
    "fs2_selection_panel_temporal_pilot_20261008_1", "fs2_capture_82978cc9",       # D097
    "fs2_selection_panel_gzip_pilot_20261010_1", "fs2_capture_e9d035a8",           # D114
    "fs2_capture_3a4f80db", "fs2_capture_c63c72a0", "phase3_evidence_capsules",    # required by pilot script / capsules
]
DESTRUCTIVE = r"(\brm\b|\brmdir\b|\bmv\b|\bunlink\b|\bshred\b|find\b.*(-delete|-exec\s+rm)|\btruncate\b|>\s*\S*data-dumps|\brsync\b.*--delete|\bgit\s+clean\b)"

try:
    cmd = json.load(sys.stdin).get("tool_input", {}).get("command", "")
except Exception:
    sys.exit(0)

def block(msg):
    print(f"BLOCKED by .claude/hooks/protect_evidence.py: {msg}", file=sys.stderr)
    sys.exit(2)

if re.search(r"git\s+push\b.*(--force|-f\b|--force-with-lease|--delete|\s:)", cmd) or \
   re.search(r"git\s+push\b.*arepo-free-production-v1", cmd):
    block("force/delete pushes and any push to arepo-free-production-v1 are not allowed from Claude sessions.")
if re.search(r"(^|[;&|]\s*)(vercel|render|supabase)\s", cmd) and not re.search(r"--help|\bversion\b", cmd):
    block("deploy/infrastructure CLIs are protected; ask the user.")
if os.environ.get("AREPO_RETIREMENT_SESSION") != "1" and re.search(DESTRUCTIVE, cmd):
    if "data-dumps" in cmd or any(p in cmd for p in PROTECTED_RUNS) or re.search(r"EVIDENCE.*\.json", cmd):
        block("destructive operation on data-dumps/evidence needs an explicit retirement session (AREPO_RETIREMENT_SESSION=1).")
sys.exit(0)
