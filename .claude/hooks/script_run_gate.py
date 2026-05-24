#!/usr/bin/env python3
"""PreToolUse hook — blocks `python <script>.py` invocations unless an up-to-date
code_review.md exists for that script.

Reads tool input from stdin (Claude Code hook protocol).
Exit 0 = allow. Exit 2 = block with stderr message.

Detects python invocations defensively:
- python, python3, python3.X, pythonw, py (+ optional .exe / path prefix)
- flag-prefixed invocations (python -u / -B / -O / -X faulthandler ... script.py)
- env-var prefix (FOO=bar python script.py) and `env [VAR=val] python ...`
- Common runners that ultimately exec a script: uv run, poetry run, pdm run,
  hatch run, pipx run (both `... run python script.py` and `... run script.py`)

Exempts: -c oneliners, --version/--help, -m module, scripts inside venvs / site-packages.

Recency policy (per .claude/skills/deep-script-review/SKILL.md):
- code_review.md must contain a PASS marker
- review must not be older than REVIEW_MAX_AGE_DAYS
- review mtime must be >= script mtime (script changed since review => stale)
"""
from __future__ import annotations
import sys, json, re, shlex, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVIEW_MAX_AGE_DAYS = 30

RUNNERS = {"uv", "poetry", "pdm", "hatch", "pipx", "rye"}
# Single-arg flags whose value is a separate token (so we must skip 2).
VALUE_TAKING_FLAGS = {"-W", "-X", "--check-hash-based-pycs"}


def _basename(token: str) -> str:
    name = re.split(r"[/\\]", token)[-1]
    if name.lower().endswith(".exe"):
        name = name[:-4]
    return name


def _is_python_interpreter(name: str) -> bool:
    """python / python3 / python3.X / pythonw / py (case-insensitive)."""
    n = name.lower()
    if n in ("py", "pythonw"):
        return True
    if not n.startswith("python"):
        return False
    rest = n[len("python"):]
    if rest == "" or rest == "3" or rest == "w":
        return True
    if rest.startswith("3."):
        tail = rest[2:].split(".", 1)[0]
        return tail.isdigit()
    return False


def _scan_for_script(tokens: list[str], start: int) -> Path | None:
    """Walk past interpreter flags, return the .py script path or None."""
    i = start
    while i < len(tokens):
        t = tokens[i]
        if t == "--":
            i += 1
            continue
        if t in ("-c", "-m"):
            return None  # running code/module, not a script file
        if t.startswith("--"):
            # --version, --help, --check-hash-based-pycs <mode>, etc.
            if t in VALUE_TAKING_FLAGS and i + 1 < len(tokens):
                i += 2
                continue
            i += 1
            continue
        if t.startswith("-"):
            if t in VALUE_TAKING_FLAGS and i + 1 < len(tokens):
                i += 2
                continue
            i += 1
            continue
        # First non-flag token is the candidate script.
        if t.endswith(".py"):
            p = Path(t)
            if not p.is_absolute():
                p = (Path.cwd() / p).resolve()
            return p
        return None
    return None


def parse_python_invocation(cmd: str) -> Path | None:
    """Return script path if cmd ultimately runs `python <script>.py`, else None."""
    try:
        tokens = shlex.split(cmd, posix=True)
    except ValueError:
        # Unbalanced quotes etc. — fail open (we'd rather not falsely block).
        return None
    if not tokens:
        return None

    i = 0
    # Strip leading env-var assignments (FOO=bar BAZ=qux python ...).
    while i < len(tokens) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[i]):
        i += 1
    # Strip `sudo` / `nice` / `time` / `exec` prefixes that don't change the parse.
    while i < len(tokens) and tokens[i] in ("sudo", "nice", "time", "exec"):
        i += 1

    while i < len(tokens):
        tok = tokens[i]
        base = _basename(tok)

        if _is_python_interpreter(base):
            return _scan_for_script(tokens, i + 1)

        # `env [VAR=val ...] python ...`
        if base == "env":
            j = i + 1
            while j < len(tokens) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[j]):
                j += 1
            i = j
            continue

        # Runner prefixes: `uv run [opts] (python|script.py)`, similar for poetry/pdm/hatch/pipx/rye.
        if base.lower() in RUNNERS and i + 1 < len(tokens) and tokens[i + 1] == "run":
            j = i + 2
            # Skip runner-level options. Conservatively, also skip their values.
            runner_value_flags = {"--python", "--with", "-p", "--project", "--directory"}
            while j < len(tokens) and tokens[j].startswith("-"):
                if tokens[j] in runner_value_flags and j + 1 < len(tokens):
                    j += 2
                else:
                    j += 1
            if j < len(tokens):
                nxt = tokens[j]
                nxt_base = _basename(nxt)
                if _is_python_interpreter(nxt_base):
                    return _scan_for_script(tokens, j + 1)
                if nxt.endswith(".py"):
                    p = Path(nxt)
                    if not p.is_absolute():
                        p = (Path.cwd() / p).resolve()
                    return p
            i = j
            continue

        i += 1

    return None


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


def review_is_fresh(review: Path, script: Path) -> tuple[bool, str]:
    """Per SKILL.md: review must be within REVIEW_MAX_AGE_DAYS and not older than the script."""
    now = time.time()
    review_mtime = review.stat().st_mtime
    age_days = (now - review_mtime) / 86400.0
    if age_days > REVIEW_MAX_AGE_DAYS:
        return False, f"review is {age_days:.0f} days old (>{REVIEW_MAX_AGE_DAYS}d limit)"
    try:
        script_mtime = script.stat().st_mtime
    except FileNotFoundError:
        return True, "script missing (cannot compare mtime)"
    if script_mtime > review_mtime:
        return False, "script modified after review — re-review required"
    return True, "review is fresh"


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        return 0
    if payload.get("tool_name", "") != "Bash":
        return 0
    cmd = payload.get("tool_input", {}).get("command", "")
    script = parse_python_invocation(cmd)
    if script is None:
        return 0
    try:
        rel = script.relative_to(ROOT)
    except ValueError:
        return 0
    # .claude is gating/infrastructure code (hooks, skill helpers); not a "user
    # script" subject to the review gate. Without this, the gate would refuse to
    # let its own files run during testing or hook execution.
    skip_parts = {"venv", ".venv", "site-packages", "node_modules", ".git", "__pycache__", ".claude"}
    if any(p in skip_parts for p in rel.parts):
        return 0
    if "_self_test" in cmd or "--help" in cmd:
        return 0
    review = find_review(script)
    if review is None:
        msg = (
            f"[SCRIPT-RUN BLOCK] {rel} has no code_review.md adjacent.\n"
            f"Per decision gating, invoke /deep-script-review on this file first.\n"
            f"Expected one of: {script.parent}/{script.stem}_code_review.md or _{script.stem}_code_review.md"
        )
        print(msg, file=sys.stderr)
        return 2
    ok, reason = review_passes(review)
    if not ok:
        print(f"[SCRIPT-RUN BLOCK] {rel} review at {review.relative_to(ROOT)}: {reason}\nFix issues + re-review before running.", file=sys.stderr)
        return 2
    fresh, freshness_reason = review_is_fresh(review, script)
    if not fresh:
        print(f"[SCRIPT-RUN BLOCK] {rel} review at {review.relative_to(ROOT)}: {freshness_reason}\nRe-run /deep-script-review.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
