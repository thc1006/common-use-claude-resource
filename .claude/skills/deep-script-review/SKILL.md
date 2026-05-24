---
name: deep-script-review
description: Exhaustive review of a SINGLE Python script BEFORE it is executed. Mandatory for any new or modified .py file in this project. Runs multi-subagent adversarial review and writes code_review.md adjacent to the script. Use BEFORE any `python <script>.py` invocation.
---

# Deep Script Review Protocol

ultrathink

You are reviewing ONE script (or a small set of related scripts) that is about to be executed. Goal: catch real bugs, hidden contract violations, silent failure modes, and project-rule violations BEFORE the script runs.

This is mandatory per `CLAUDE.md` decision gating. You may NOT run the script until review passes.

---

## When this skill triggers

- Any new `.py` file added under `scripts/` or `experiments/`
- Any modified `.py` file in those locations
- Any forked-and-adapted Kaggle notebook code (.py extracted from .ipynb)
- BEFORE any `python <script>.py` Bash command

Exemptions:
- Pure builtins: `python --version`, `python -c "<one liner>"`
- Re-running an unchanged script that already has a passing `code_review.md`
- Reading-only scripts (no file write, no network) — but still recommended to review

---

## Inputs you receive

- Path to script file
- Project context (CLAUDE.md, memory files, review_config.json)
- Existing tests / harness if applicable
- Sibling scripts in same directory (for consistency check)

---

## Output

A `code_review.md` written next to the script (e.g., `scripts/foo.py` → `scripts/foo_code_review.md` or `scripts/_foo_code_review.md`).

The file must contain:

```markdown
# Code Review — <path>

**Reviewed**: YYYY-MM-DD
**Reviewer**: Claude
**Status**: PASS | NEEDS FIX | REJECTED
**Verdict**: <one-line summary>

## What this script does
<2-4 sentence summary, in my own words after reading>

## Rules checked
- [ ] feedback_no_script_analysis: no hardcoded conclusions
- [ ] feedback_v4_disaster_postmortem #1: no nan_to_num near submission
- [ ] feedback_v4_disaster_postmortem #2: no per-class weight reuse across base mismatch
- [ ] feedback_v4_disaster_postmortem #4: no w=1.0 unvalidated
- [ ] feedback_kaggle_submission_discipline #5: baseline-consistency
- [ ] reference_yaroslav_v6_internals: Unnamed col + hidden_test handling

## Subagents spawned
- correctness-reviewer: <result summary>
- data-leakage-reviewer: <result summary>
- domain-invariant-reviewer: <result summary>
- (others as needed)

## Confirmed findings (validator-passed)
### F001: <claim>
- Severity: HIGH
- Evidence: line X, code
- Symptom: ...
- Fix sketch: ...
- Test gap: ...

(repeat for each finding)

## Verified-clean
For each function / section without a finding, what I checked and why it's clean.

## Residual risk
What I could NOT verify and why.

## Run gating decision
PASS — script may be executed
NEEDS FIX — fix the findings, re-review
REJECTED — fundamental design issue, do not run as-is
```

---

## Process (mandatory phases, no shortcuts)

### Phase 0 — Read and classify
- Read the full script
- Classify: experiment / harness / utility / notebook-extract / submission-generator
- Read its sibling code_review.md if exists (prior reviews)
- Read project rules: CLAUDE.md, all 4 memory files in CLAUDE.md mandate

### Phase 1 — Sanity checks (deterministic)
Run if applicable:
- `python -m py_compile <script>` — syntax
- `python <script> --help` if it accepts args
- `python <script>` self-test if it has `if __name__ == "__main__"` with self-test
- `ruff check <script>` if ruff present
- `mypy <script>` if mypy configured

Record each in code_review.md.

### Phase 2 — Adversarial walk
Read every function. For each:
- callers (search the codebase)
- inputs: nil/empty/NaN/inf/zero/extreme/duplicate
- outputs: does it match the function name's promise?
- error handling: silent vs loud
- side effects: files written, network calls

### Phase 3 — Spawn specialized subagents
Always spawn:
- `correctness-reviewer` — semantic bugs
- `false-positive-validator` for each finding produced

Spawn when the script is in scope:
- `test-coverage-reviewer` — if script is part of larger system
- `security-reviewer` — if script touches network, filesystem, secrets, shell

Spawn ONLY when a project marker indicates the relevant domain (see
"Project-specific things to check" below — do NOT spawn domain reviewers on
generic Claude Code resource repos):
- `domain-invariant-reviewer` — project rules from CLAUDE.md/postmortems
- `data-leakage-reviewer` — if script does CV/stacker/blend
- `submission-contract-reviewer` — if script writes submission.csv
- `metric-validity-reviewer` — if script computes AUC/blend math

### Phase 4 — Validator pass
Each candidate finding → fresh `false-positive-validator` subagent → confirm/reject/narrow.
Keep only `confirmed + high` confidence.

### Phase 5 — Missed-bug hunter
After all validators, spawn `missed-bug-hunter` with full script + dropped findings.
Adds ONE additional finding if it finds something serious.

### Phase 6 — Write code_review.md
Per template above. Status field decides whether script can run.

### Phase 7 — Apply fixes (if NEEDS FIX)
If status is NEEDS FIX:
1. Make the fixes in the script
2. Re-run Phase 0-6
3. Repeat until PASS

You may NOT mark PASS to skip fixes. The hook will check the code_review.md and block ending if there are HIGH-severity findings without "FIXED" annotation.

---

## Project-specific things to check (applied ONLY when the marker is present)

Generic Claude Code resource repos have no marker; skip this section entirely.

### BirdCLEF (marker: `birdclef-2026-data.json` in repo root, OR working in `~/.claude/projects/C--Users-thc1006*`)

From `~/.claude/projects/C--Users-thc1006/memory/`:

1. `feedback_v4_disaster_postmortem.md` — 6 rules
2. `feedback_kaggle_submission_discipline.md` — 6 gates
3. `feedback_no_script_analysis.md` — script can't write conclusions
4. `reference_yaroslav_v6_internals.md` — base notebook gotchas

Quick search patterns to grep for:
- `nan_to_num` → postmortem #1 violation, HIGH
- `fillna(0.5)` or `fillna(0)` near submission → postmortem #1, HIGH
- `w = 1.0` or `W_CLAP[...] = 1.0` → postmortem #4, HIGH
- `KFold(` without `groups=` → data leakage, HIGH
- `StratifiedKFold(` near stacker → site leakage, MEDIUM-HIGH
- `if delta < X: print("...is leaky")` → no_script_analysis, MEDIUM
- `if oof_macro > Y: print("ready to submit")` → no_script_analysis, MEDIUM
- `index=True` on `to_csv` near submission → Yaroslav Unnamed bug, MEDIUM
- `championship_w_per_class.json` direct reuse → postmortem #2, HIGH

---

## Run-gating contract

The PreToolUse hook (`.claude/hooks/script_run_gate.py`) blocks `python <script>.py` invocations unless:

1. `<script>_code_review.md` OR `_<basename>_code_review.md` exists next to script
2. The review has `**Status**: PASS` line
3. The review was written within the last 30 days (re-review if older or script modified since)

If you bypass this by, e.g., reading the script content via Read tool and running it via Python -c, the missed-bug-hunter will catch it in the next review and flag as a process violation.
