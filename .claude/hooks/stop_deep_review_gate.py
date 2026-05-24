#!/usr/bin/env python3
"""Stop hook — blocks Claude from ending if deep-pr-review didn't produce required artifacts.

Hook runs on Stop events. Exit code 2 = block (Claude must continue).

Safety rails (avoid the infinite-loop class of bug filed as anthropics/claude-code#55754):
1. If invoked for SubagentStop, exit 0 immediately. Phase-3 reviewer subagents
   stop BEFORE final artifacts exist by design; enforcing here would deadlock them.
   Enforcement happens on the top-level Stop event only.
2. If stop_hook_active is true, Claude is already in a forced-continuation state
   from a previous block — exit 0 to break the loop and surface the issue to the
   user instead of burning the session.

Only enforces when a deep-pr-review WAS started (review/ folder exists with at
least one artifact). Won't block normal coding tasks.
"""
from __future__ import annotations
import sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / "review"


def _read_payload() -> dict:
    try:
        return json.loads(sys.stdin.read() or "{}")
    except Exception:
        return {}


payload = _read_payload()

# Safety rail 1: never block subagent termination.
if payload.get("hook_event_name") == "SubagentStop":
    sys.exit(0)

# Safety rail 2: break forced-continuation loops.
if payload.get("stop_hook_active") is True:
    sys.exit(0)

# If no review folder OR empty, this is not a deep-review session — let it stop.
if not REVIEW.exists() or not any(REVIEW.iterdir()):
    sys.exit(0)

REQUIRED_FILES = [
    "changed_files.json",
    "full_diff.patch",
    "REVIEW_REPORT.md",
    "FINDINGS.final.json",
    "DROPPED_FINDINGS.json",
    "VERIFIED_CLEAN.md",
    "COMMANDS_RUN.md",
]

missing = []
for name in REQUIRED_FILES:
    path = REVIEW / name
    if not path.exists():
        missing.append(name)
    elif path.stat().st_size == 0:
        missing.append(f"{name} (empty)")

if missing:
    msg = "[DEEP REVIEW BLOCK] Missing required review artifacts:\n"
    msg += "\n".join(f"  - review/{m}" for m in missing)
    msg += "\nPer .claude/skills/deep-pr-review/SKILL.md, all artifacts must exist before stopping."
    print(msg, file=sys.stderr)
    sys.exit(2)

report = (REVIEW / "REVIEW_REPORT.md").read_text(encoding="utf-8")
REQUIRED_SECTIONS = [
    "Scope reviewed",
    "Base branch",
    "Diff source",
    "Files reviewed",
    "Commands run",
    "Subagents used",
    "Confirmed findings",
    "Verified-clean",
    "Dropped candidate findings",
    "Residual risk",
]
missing_sections = [s for s in REQUIRED_SECTIONS if s not in report]
if missing_sections:
    msg = "[DEEP REVIEW BLOCK] REVIEW_REPORT.md missing required sections:\n"
    msg += "\n".join(f"  - {s}" for s in missing_sections)
    print(msg, file=sys.stderr)
    sys.exit(2)

try:
    findings = json.loads((REVIEW / "FINDINGS.final.json").read_text(encoding="utf-8"))
except json.JSONDecodeError as e:
    print(f"[DEEP REVIEW BLOCK] FINDINGS.final.json invalid JSON: {e}", file=sys.stderr)
    sys.exit(2)

unconfirmed = [f for f in findings if f.get("validator_verdict") not in ("confirmed",) or f.get("validator_confidence") != "high"]
if unconfirmed:
    msg = f"[DEEP REVIEW BLOCK] {len(unconfirmed)} findings not validator-confirmed (high confidence):\n"
    for f in unconfirmed[:5]:
        msg += f"  - {f.get('id', '?')}: verdict={f.get('validator_verdict')} conf={f.get('validator_confidence')}\n"
    print(msg, file=sys.stderr)
    sys.exit(2)

verified_clean = (REVIEW / "VERIFIED_CLEAN.md").read_text(encoding="utf-8")
if "missed-bug-hunter" not in verified_clean.lower():
    print("[DEEP REVIEW BLOCK] VERIFIED_CLEAN.md does not mention missed-bug-hunter pass", file=sys.stderr)
    sys.exit(2)

print("[DEEP REVIEW PASS] All required artifacts present, sections present, findings validator-confirmed, missed-bug-hunter ran.")
sys.exit(0)
