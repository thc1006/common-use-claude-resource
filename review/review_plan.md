# Review plan

## Scope
- Full diff vs base commit 43ee075 (commit 697b3b9 changes)
- Files: .claude/agents/*.md, .claude/skills/**/SKILL.md, .claude/hooks/*.py, .claude/settings*.json

## Checks
- Validate hooks behavior (script_run_gate.py, stop_deep_review_gate.py) for correctness, safety, and false blocking/allowing.
- Validate skill and agent instructions for clarity, consistency, and alignment with official Claude Code best practices.
- Check for missing required project guidance (CLAUDE.md, review_config.json, memory files) and any contradictions.
- Assess whether commands/skills/subagents overlap or conflict in design.

## Reviewer assignments
- Primary reviewer: main agent (this review)
- Subagents: correctness-reviewer, test-coverage-reviewer, data-leakage-reviewer, submission-contract-reviewer, metric-validity-reviewer, domain-invariant-reviewer, missed-bug-hunter
