# Review Report

## Scope reviewed
- Commit 697b3b9 diff against parent 43ee075 (since origin/main == HEAD, the standard base diff was empty).
- Files in scope: .claude/agents/*.md, .claude/skills/deep-pr-review/SKILL.md, .claude/skills/deep-script-review/SKILL.md, .claude/hooks/script_run_gate.py, .claude/hooks/stop_deep_review_gate.py, .claude/settings (2).json.
- Additional context files read: README.md, .claude/settings.json, .claude/skills/adversarial-review/SKILL.md.

## Base branch
- origin/main (HEAD == 697b3b9); effective review base for the commit was parent 43ee075.

## Diff source
- `git diff origin/main...HEAD` (empty because origin/main == HEAD)
- `git diff 43ee075...HEAD` (full diff used for review)

## Files reviewed
- .claude/hooks/script_run_gate.py
- .claude/hooks/stop_deep_review_gate.py
- .claude/settings (2).json
- .claude/settings.json
- .claude/skills/deep-pr-review/SKILL.md
- .claude/skills/deep-script-review/SKILL.md
- .claude/skills/adversarial-review/SKILL.md
- .claude/agents/* (correctness-reviewer, test-coverage-reviewer, data-leakage-reviewer, submission-contract-reviewer, metric-validity-reviewer, domain-invariant-reviewer, missed-bug-hunter, false-positive-validator)
- README.md

## Commands run
See review/COMMANDS_RUN.md.

## Subagents used
- correctness-reviewer
- test-coverage-reviewer
- data-leakage-reviewer
- submission-contract-reviewer
- metric-validity-reviewer
- domain-invariant-reviewer
- missed-bug-hunter
- false-positive-validator (F002, F003, F004, F005, F001, X001)

## Guideline alignment (official Claude Code docs)
- Official docs emphasize using CLAUDE.md for persistent project instructions and keeping it concise, and using the .claude directory for project configuration and scoped rules/skills. These were used as the baseline standards for this review, but CLAUDE.md is missing in the repo and memory files referenced by skills are not present locally, limiting enforceability and portability. Source: Anthropic Claude Code docs on memory/CLAUDE.md and the .claude directory【3:1†source】【3:2†source】.
- Official guidance suggests keeping reusable workflows in the .claude structure; this repo uses skills but has no .claude/commands directory, and README only mentions /adversarial-review while new deep-* skills are undocumented, creating an onboarding/documentation gap.【3:2†source】

## Confirmed findings

### F002 (HIGH) — Script-run gate bypass via flags/versioned interpreter
- **File**: .claude/hooks/script_run_gate.py
- **Symptom**: Unreviewed scripts can run using `python -u script.py` or `python3.11 script.py`.
- **Trigger**: Any python invocation with flags before the script or python3.X executable.
- **Reasoning & Evidence**: Regex only matches python/python3; flags before the script cause the first token to be non-.py and the gate returns None.
- **Fix**: Parse with shlex, skip interpreter flags until first non-flag token, and accept python3.X executables.
- **Test gap**: No tests for flag-prefixed or python3.X invocations.
- **Validator**: confirmed, high.

### F003 (HIGH) — Recency/modified-since requirement not enforced
- **File**: .claude/hooks/script_run_gate.py
- **Symptom**: PASS reviews remain valid indefinitely even after script changes.
- **Trigger**: Script updated after review, or review older than 30 days.
- **Reasoning & Evidence**: deep-script-review SKILL requires review freshness; gate only checks PASS marker without mtime checks.
- **Fix**: Compare review mtime vs script mtime and enforce 30‑day freshness.
- **Test gap**: No tests for stale review enforcement.
- **Validator**: confirmed, high.

### F004 (HIGH) — Stop hook omits required REVIEW_REPORT sections
- **File**: .claude/hooks/stop_deep_review_gate.py
- **Symptom**: Reports missing Base branch / Files reviewed / Confirmed findings pass the stop gate.
- **Trigger**: REVIEW_REPORT.md missing those sections.
- **Reasoning & Evidence**: SKILL.md requires those sections, but REQUIRED_SECTIONS omits them.
- **Fix**: Add the missing sections to REQUIRED_SECTIONS.
- **Test gap**: No tests ensuring section list matches SKILL spec.
- **Validator**: confirmed, high.

### X001 (HIGH) — SubagentStop hook causes deep-pr-review deadlock
- **File**: .claude/settings (2).json, .claude/hooks/stop_deep_review_gate.py
- **Symptom**: Phase-3 subagents cannot stop once review/ exists and final artifacts are missing.
- **Trigger**: Deep-pr-review runs after Phase 0 creates review/ but before Phase 7 artifacts exist.
- **Reasoning & Evidence**: SubagentStop runs stop_deep_review_gate.py; that hook blocks if review/ exists but required artifacts missing; SKILL ordering requires subagents to stop before final artifacts.
- **Fix**: Remove SubagentStop hook or defer enforcement until finalization.
- **Test gap**: No tests for subagent stop behavior.
- **Validator**: confirmed, high.

## Verified-clean
- Agent/skill markdown files contain no executable logic; reviewed for conflicts—no direct behavioral conflicts found beyond documentation gaps noted below.
- No application/runtime code, tests, or data pipeline logic were modified; BirdCLEF leakage/metric/submission risks are not introduced in this diff.
- Existing adversarial-review skill remains intact; no changes to its behavior.

## Dropped candidate findings
- F001: Hook settings placed in .claude/settings (2).json may be ignored; validator confidence medium due to lack of direct loader verification.
- F005: Missing tests for new hooks; validator confidence medium (kept as a gap but not a confirmed high-confidence finding).

## Residual risk
- CLAUDE.md and review_config.json are missing; memory files referenced by skills under ~/.claude/projects/* are not available in this environment, so rule enforcement may vary by machine.
- Official Claude Code docs could not be fetched directly due to network restrictions; guidance relied on search-indexed official documentation pages.
- No automated tests exist for hook behavior, so regressions remain possible until tests are added.
