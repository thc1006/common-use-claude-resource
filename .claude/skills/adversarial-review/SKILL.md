---
name: adversarial-review
description: Run an ultrathink adversarial post-implementation review of the current branch, PR, or worktree diff. Use manually after multi-agent or worktree development is complete and before merging.
argument-hint: "[base-ref-or-pr] [optional focus]"
disable-model-invocation: true
context: fork
agent: adversarial-reviewer
model: opus
effort: max
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(git *)
  - Bash(gh pr view*)
  - Bash(gh pr diff*)
  - Bash(npm test*)
  - Bash(npm run test*)
  - Bash(npm run lint*)
  - Bash(pnpm test*)
  - Bash(pnpm lint*)
  - Bash(pytest *)
  - Bash(go test*)
  - Bash(cargo test*)
  - Bash(make test*)
  - Bash(./test.sh)
  - Bash(./verify.sh)
---

# Ultrathink Adversarial Review

ultrathink

## Target

Review target: `$ARGUMENTS`

If no argument is provided:
1. Detect the current branch.
2. Determine the base branch using this order:
   - PR base branch if `gh pr view` works.
   - `origin/main` if it exists.
   - `origin/master` if it exists.
   - otherwise ask the user for the base branch.
3. Review the full diff from base to current branch.

## Scope

You must review the FULL branch diff against the base branch, not only the latest commit.

Use commands like:

```bash
git status --short
git branch --show-current
git merge-base HEAD origin/main || true
git diff --stat <base>...HEAD
git diff <base>...HEAD
````

If this is a GitHub PR and `gh` is available, also inspect:

```bash
gh pr view --json number,title,baseRefName,headRefName,body,commits,files
gh pr diff
```

## Review procedure

Run this review in six passes:

### Pass 1 — Diff map

Summarize:

* changed files
* affected modules
* public API or data model changes
* test files changed or missing
* migration/config/deployment changes
* independently developed worktree changes that may conflict

### Pass 2 — Correctness and contracts

Look for:

* broken invariants
* wrong assumptions
* null/empty/error paths
* incompatible API contracts
* schema mismatch
* state-machine mistakes
* unhandled partial failure
* rollback problems

### Pass 3 — Tests and verification

Check whether tests cover:

* happy path
* edge cases
* failure paths
* integration boundaries
* concurrency
* regression cases from the changed behavior

Run the most relevant existing test/lint command. Prefer the project’s existing verification script if present:

* `./verify.sh`
* `./test.sh`
* `make test`
* package-manager test/lint commands
* language-specific test commands

Do not invent a heavy test matrix unless necessary. If tests cannot be run, explain why.

### Pass 4 — Security and abuse cases

Look for:

* injection
* unsafe shell execution
* unsafe deserialization
* auth/authz bypass
* secret leakage
* path traversal
* SSRF
* confused deputy
* insecure defaults
* prompt/tool injection risks if this code touches agents, tools, MCP, plugins, or Skills

### Pass 5 — Performance, reliability, operations

Look for:

* N+1 calls
* unbounded loops
* missing timeout/retry/backoff
* resource leaks
* file descriptor leaks
* memory growth
* logging/observability gaps
* poor error messages
* brittle CI/deploy assumptions

### Pass 6 — Falsification pass

For each potential finding:

1. Try to disprove it.
2. Check whether existing code or tests already handle it.
3. Keep only findings that remain plausible.
4. Downgrade speculative issues to non-blocking concerns.

## Output format

Return exactly this structure:

# Adversarial Review Result

## Verdict

Choose one:

* APPROVE
* APPROVE WITH NON-BLOCKING COMMENTS
* REQUEST CHANGES
* BLOCK MERGE

## Executive Summary

2–5 bullets.

## Blocking Findings

For each blocking finding:

### Finding N: <title>

* Severity:
* File(s):
* Code reference:
* Why this is a real bug:
* Reproduction / failure scenario:
* Suggested fix:
* Test that should catch it:

If none, write: `No blocking findings found.`

## Non-blocking Concerns

List maintainability, style, test-depth, or observability concerns that should not block merge.

## Test / Command Results

Include commands run and outcomes.

## Missing Evidence

List anything you could not verify because of missing dependencies, missing env vars, unavailable services, or permission limits.

## Final Merge Recommendation

One paragraph.