#!/usr/bin/env python3
"""PreToolUse hook — blocks `python <script>.py` invocations unless code_review.md exists for that script.

Reads tool input from stdin (Claude Code hook protocol).
Exit 0 = allow. Exit 2 = block with stderr message.

Only applies to Bash commands that look like running a .py file.
Exempts: -c oneliners, --version, -m module, scripts inside venvs / installed packages.
"""
from __future__ import annotations
import sys, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def parse_python_invocation(cmd: str) -> Path | None:
    """Return script path if cmd is `python <script>.py [args]`, else None."""
    # strip leading env / sudo
    cmd = cmd.strip()
    # match python/python3 invocations
    m = re.search(r"\bpython(?:3)?(?:\.exe)?\s+(.+)", cmd)
    if not m:
        return None
    rest = m.group(1).strip()
    # exempt -c, -m, --version, -h
    if rest.startswith("-c") or rest.startswith("-m") or rest.startswith("--") or rest.startswith("-h"):
        return None
    # exempt one-liner forms
    if '"' in rest[:3] or "'" in rest[:3]:
        return None
    # first token must be a .py file
    first = rest.split()[0].strip("\"'")
    if not first.endswith(".py"):
        return None
    p = Path(first)
    if not p.is_absolute():
        p = (Path.cwd() / p).resolve()
    return p


def find_review(script: Path) -> Path | None:
    """Look for code_review.md adjacent to script."""
    parent = script.parent
    base = script.stem
    candidates = [
        parent / f"{base}_code_review.md",
        parent / f"_{base}_code_review.md",
        parent / "code_review.md",
        parent / f"{base}.review.md",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def review_passes(review: Path) -> tuple[bool, str]:
    txt = review.read_text(encoding="utf-8", errors="ignore")
    if "**Status**: PASS" in txt or "Status: PASS" in txt or "Verdict: PASS" in txt:
        return True, "PASS marker found"
    if "**Status**: REJECTED" in txt or "Status: REJECTED" in txt:
        return False, "marked REJECTED"
    if "**Status**: NEEDS FIX" in txt or "Status: NEEDS FIX" in txt:
        return False, "marked NEEDS FIX"
    return False, "no PASS marker in review"


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        # If we can't parse hook payload, don't block (fail open on parser issue, not on review issue)
        return 0
    tool_name = payload.get("tool_name", "")
    if tool_name != "Bash":
        return 0
    tool_input = payload.get("tool_input", {})
    cmd = tool_input.get("command", "")
    script = parse_python_invocation(cmd)
    if script is None:
        return 0
    # Only enforce on scripts within this project
    try:
        rel = script.relative_to(ROOT)
    except ValueError:
        return 0  # outside project root, don't enforce
    # Skip if inside a venv / site-packages
    skip_parts = {"venv", ".venv", "site-packages", "node_modules", ".git", "__pycache__"}
    if any(p in skip_parts for p in rel.parts):
        return 0
    # Skip very short self-test commands
    if "_self_test" in cmd or "--help" in cmd:
        return 0
    review = find_review(script)
    if review is None:
        msg = (
            f"[SCRIPT-RUN BLOCK] {rel} has no code_review.md adjacent.\n"
            f"Per CLAUDE.md decision gating, invoke /deep-script-review on this file first.\n"
            f"Expected one of: {script.parent}/{script.stem}_code_review.md or _{script.stem}_code_review.md"
        )
        print(msg, file=sys.stderr)
        return 2
    ok, reason = review_passes(review)
    if not ok:
        msg = f"[SCRIPT-RUN BLOCK] {rel} review at {review.relative_to(ROOT)}: {reason}\nFix issues + re-review before running."
        print(msg, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
