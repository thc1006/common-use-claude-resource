---
name: parallel-dev
description: General-purpose parallel development workflow. Use after the user has described a coding, refactoring, testing, bug-fix, or implementation task and wants Claude Code to coordinate multiple specialized subagents or agent-team teammates with worktree isolation, tests, and adversarial review.
argument-hint: "[optional extra constraints, base branch, issue number, or PR number]"
disable-model-invocation: true
model: opus
effort: max
allowed-tools:
  - Read
  - Write
  - Edit
  - MultiEdit
  - Grep
  - Glob
  - Bash
  - TodoWrite
  - Task
---

# Parallel Development Orchestrator

ultrathink

You are the lead coordinator for a general-purpose parallel development workflow.

Do not ask the user to paste a task template.

Treat the task source as:
1. The latest explicit user request in the current Claude Code conversation.
2. Any additional arguments passed to `/parallel-dev`.
3. The current repository state.
4. The current branch name, git status, open issue/PR context, and existing TODOs.
5. Relevant project instructions from CLAUDE.md, AGENTS.md, .claude/rules, README, tests, and package scripts.

If no actionable development task can be inferred from the conversation or repository state, ask exactly one clarification question. Otherwise proceed.

## Goal

Coordinate multiple specialized Claude Code subagents or agent-team teammates to implement the requested change with maximum safe throughput.

Prefer concurrency. Use sequential execution only when:
- tasks have hard dependencies,
- file ownership overlaps,
- shared architecture decisions must be resolved first,
- the environment throttles,
- tests or build artifacts would conflict,
- or parallel execution would increase merge risk.

## Official Claude Code mechanisms to prefer

Use this order:

1. If the task can be split into independent implementation units, use `/batch`-style decomposition:
   - break the task into independent units,
   - assign each unit to a specialized worker,
   - use isolated git worktrees where edits are required,
   - require tests per unit,
   - require handoff notes per unit.

2. If workers need to coordinate with each other, challenge assumptions, or share a task list, use Agent Teams:
   - use 3–5 teammates,
   - keep the lead session as coordinator,
   - do not create nested teams,
   - keep each teammate’s ownership explicit.

3. If the task is smaller, use specialized subagents:
   - use worktree isolation for implementation agents,
   - use read-only agents for research/review,
   - keep high-volume exploration out of the main context.

## Mandatory planning phase

Before editing files:

1. Inspect repository state:
   - `git status --short`
   - `git branch --show-current`
   - detect base branch: PR base, `origin/main`, `origin/master`, or local default
   - inspect project scripts and test commands

2. Summarize:
   - inferred task
   - likely affected modules
   - proposed work units
   - file ownership plan
   - expected tests
   - known risks

3. Create a TODO plan with explicit phases:
   - discovery
   - decomposition
   - parallel implementation
   - integration
   - tests
   - adversarial review
   - final fix pass
   - final report

4. Ask for plan approval only if the requested change is risky, destructive, security-sensitive, or ambiguous. Otherwise proceed.

## Parallel execution policy

For each work unit:

- Assign the best-fit specialized agent.
- Prefer one worktree per implementation unit.
- Avoid same-file edits across agents.
- If two agents must touch the same file, create an explicit integration owner.
- Each agent must report:
  - files changed
  - behavior changed
  - tests run
  - failures encountered
  - assumptions made
  - remaining risks

Suggested worker roles:
- frontend-implementer
- backend-implementer
- api-contract-implementer
- test-engineer
- docs-maintainer
- integration-engineer
- migration-engineer
- performance-engineer
- security-reviewer
- adversarial-reviewer

Choose only the roles needed for this repository.

## Worktree policy

Use isolated worktrees for any agent that edits files.

If worktrees are unavailable, emulate isolation by:
- assigning non-overlapping files,
- committing or stashing safe checkpoints,
- serializing overlapping edits,
- and documenting the degraded isolation mode.

Each implementation agent must work against the same intended base branch unless the lead explicitly decides otherwise.

## Quality gates

Every implementation unit must run the narrowest relevant verification first.

Then the integrated branch must run the broad verification command, in this preference order:

1. `./verify.sh`
2. `./test.sh`
3. package-manager lint/test/build scripts
4. language-specific test commands:
   - `pytest`
   - `go test ./...`
   - `cargo test`
   - `npm test`
   - `pnpm test`
   - `make test`
5. project-specific CI-equivalent command discovered from docs or config

If no test command exists, create or recommend a minimal verification path before claiming completion.

## Mandatory adversarial review gate

After implementation and integration:

Run an ultrathink adversarial review against the full branch diff, not just the latest commit.

The review must check:
- correctness bugs
- API contract mismatch
- hidden coupling between parallel work units
- missing tests
- broken edge cases
- partial failure / rollback behavior
- concurrency bugs
- race conditions
- security vulnerabilities
- prompt/tool injection risks
- path traversal / SSRF / unsafe shell execution
- secret leakage
- performance regressions
- deployment and CI breakage

If an `/adversarial-review` skill exists, invoke it.

If no `/adversarial-review` skill exists, perform the review inline using this procedure:

1. Determine base branch.
2. Inspect:
   - `git diff --stat <base>...HEAD`
   - `git diff <base>...HEAD`
   - relevant tests and configs
3. Run tests.
4. Produce findings with:
   - severity
   - file path
   - code reference
   - failure scenario
   - suggested fix
   - test that should catch it
5. Fix all blocking findings.
6. Re-run relevant tests.
7. Re-run adversarial review once after fixes.

## Security-sensitive changes

If the task touches any of these, run an additional security review:
- authentication
- authorization
- user input
- filesystem access
- network access
- shell commands
- secrets
- database queries
- webhooks
- plugins
- MCP
- agent tools
- Skills
- CI/CD
- deployment scripts

## Merge policy

Do not mark the task complete until:
- implementation is integrated,
- relevant tests pass,
- adversarial review has run,
- blocking findings are fixed,
- final risks are documented.

Do not merge automatically unless the user explicitly asked for auto-merge.

## Final response format

Return:

# Parallel Development Result

## Inferred Task

State the task you inferred from the current conversation and repository.

## Execution Model Used

Say whether you used:
- batch-style parallel work,
- agent team,
- specialized subagents,
- or sequential fallback.

Explain why.

## Work Units

For each unit:
- owner / agent role
- files changed
- summary
- tests run
- status

## Integration Summary

Summarize how the branches/worktrees/changes were integrated.

## Test Results

List commands and outcomes.

## Adversarial Review Result

Include:
- verdict
- blocking findings
- fixes applied
- remaining non-blocking concerns

## Remaining Risks

List anything unresolved or not verifiable.

## Final Recommendation

Choose one:
- READY TO MERGE
- READY AFTER MANUAL REVIEW
- NEEDS MORE WORK
- BLOCKED
MD