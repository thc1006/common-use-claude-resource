---
name: deep-pr-review
description: Exhaustive adversarial review for any code change in this project — PR, patch, notebook, script, pipeline. Hunts real bugs and hidden contract violations through multi-phase, multi-subagent investigation. Use when correctness matters more than speed.
---

# Deep PR Review Protocol

ultrathink

You are not doing a normal code review. You are running a failure-hunting investigation.

Your goal: find real bugs, regressions, hidden contract violations, missing tests, unsafe assumptions, and reviewer-missed issues in the FULL diff (NOT just latest commit).

You must prefer:
- high-confidence correctness findings over style feedback
- evidence over speculation
- full-diff reasoning over latest-commit reasoning
- deterministic checks over vibes
- validator-confirmed findings over raw findings

If no confirmed findings exist, do not say LGTM. Provide a detailed verified-clean audit trail.

---

## Non-negotiable scope

Review the FULL diff against the base branch.

Use ONE of:
```bash
gh pr diff <PR_NUMBER> --repo <OWNER>/<REPO>
```
or:
```bash
git fetch origin <BASE_BRANCH>
git diff origin/<BASE_BRANCH>...HEAD
```

Forbidden as sole source of truth:
```bash
git show HEAD
git log -1
git diff HEAD~1
```

For local (no PR yet) review: `git diff origin/main...HEAD`.

---

## Phase 0 — Build evidence map

Before reviewing, produce these files under `review/`:

```
review/changed_files.json   # path + classification per file
review/full_diff.patch
review/review_plan.md       # what will be checked + reviewer assignments
review/commands_run.log
```

Classify each changed file as:
- production code
- tests
- config / CI
- docs / comments
- generated code
- schema / API / interface
- notebook / data pipeline
- dependency / build
- harness / safety / gate

Read applicable project guidance:
- `CLAUDE.md` (project root)
- `~/.claude/projects/.../memory/feedback_*` (rules and postmortems)
- `~/.claude/projects/.../memory/project_birdclef_2026_breakthrough.md`
- `~/.claude/projects/.../memory/reference_yaroslav_v6_internals.md`
- `review_config.json` (gate thresholds)
- Existing `experiments/` for project conventions

If any file cannot be read, state explicitly.

---

## Phase 1 — Deterministic checks

Run reasonable static and test commands. Record each.

Try (only those applicable):
```bash
git status --short
git diff --check
python scripts/_harness.py     # if exists, self-test
pytest                          # if tests present
ruff check . / mypy .          # if configured
```

Record per command:
- exit code
- relevant stdout/stderr lines
- pre-existing vs caused-by-this-change

Do not claim "tests pass" unless you actually ran them.

---

## Phase 2 — Full-diff adversarial review

For every changed production file:

1. **Externally observable behavior changes**:
   - API behavior / validation / error mapping
   - Persistence/migration / IO behavior
   - Submission/output behavior (BirdCLEF-specific)
   - Concurrency / resource

2. **Every changed function**:
   - Find callers; check assumptions
   - nil/empty/zero/malformed/duplicate inputs
   - old-vs-new behavior divergence
   - error handling
   - test coverage

3. **Every changed branch**:
   - both outcomes
   - test coverage for the new branch
   - flag missing tests for nontrivial branches

4. **Every changed interface/schema/config**:
   - backward compatibility
   - defaulting
   - serialization
   - callers/docs/examples

5. **Every changed data/ML pipeline** (BirdCLEF-specific):
   - data leakage (in-site vs site-OOS, train/test split integrity)
   - class/order alignment with sample_submission
   - metric validity (macro AUC computation)
   - seed/reproducibility
   - train/inference skew
   - silent fixes (nan_to_num, fillna)
   - baseline compatibility (per-class weight tuning on wrong base = v4 disaster)
   - hidden test vs preview behavior (Yaroslav v6 dry-run NaN bug)
   - submission contract (sample_submission.csv exact match)

---

## Phase 3 — Spawn specialized reviewer subagents

Spawn independent subagents. Each gets minimal context (diff + task).

Always spawn:
1. `correctness-reviewer` — semantic bugs, invariants
2. `test-coverage-reviewer` — new behavior without tests
3. `data-leakage-reviewer` — in-site vs OOS leakage
4. `submission-contract-reviewer` — sample_submission compatibility
5. `metric-validity-reviewer` — AUC/blend/rank-aware correctness
6. `domain-invariant-reviewer` — project rules from CLAUDE.md/postmortems
7. `missed-bug-hunter` — find one serious issue everyone else missed

Optional (when relevant):
- `security-reviewer` (auth, injection, secret exposure)
- `concurrency-resource-reviewer` (races, leaks)
- `api-contract-reviewer` (backward compat, schema)

---

## Phase 4 — Candidate finding format

Store in `review/FINDINGS.candidates.json`:

```json
[
  {
    "id": "F001",
    "severity": "HIGH|MEDIUM|LOW",
    "file": "path/to/file",
    "function_or_section": "name or N/A",
    "claim": "one-line bug claim",
    "symptom": "observable bad outcome",
    "trigger": "input/state/path that triggers it",
    "evidence": [
      {"file": "...", "snippet": "code", "why_it_matters": "..."}
    ],
    "fix_sketch": "smallest safe fix",
    "test_gap": "missing test if any"
  }
]
```

No evidence, no finding.

---

## Phase 5 — Validator subagent per finding

For each candidate, spawn a fresh validator subagent with:
- the finding claim
- cited code snippets
- minimal context
- relevant project rule

Ask: "Is this finding correct with high confidence, or likely false positive? Do not invent new issues."

Validator returns:
```json
{
  "finding_id": "F001",
  "verdict": "confirmed|rejected|narrowed",
  "confidence": "high|medium|low",
  "reason": "...",
  "narrowed_claim": "..."
}
```

Rules:
- Drop rejected findings
- Drop medium/low confidence findings
- Narrow overstated findings
- Keep only high-confidence confirmed

---

## Phase 6 — Anti-false-negative pass

After validators, run one final missed-bug pass with a fresh subagent:

> "Assume the final review missed one serious bug. Find it. You may inspect the full diff and all dropped findings. Focus on false negatives."

If found, validate via Phase 5.

---

## Phase 7 — Final artifacts

Write all required files:

```
review/REVIEW_REPORT.md
review/FINDINGS.final.json
review/DROPPED_FINDINGS.json
review/VERIFIED_CLEAN.md
review/COMMANDS_RUN.md
```

### `REVIEW_REPORT.md` must contain sections:
- Scope reviewed
- Base branch
- Diff source (cite the gh/git command)
- Files reviewed
- Commands run
- Subagents used
- Confirmed findings (with severity/file/symptom/trigger/reasoning/evidence/fix/test/validator)
- Verified-clean (per important changed area, what was checked + why clean)
- Dropped candidate findings (with reason)
- Residual risk

The Stop hook (`.claude/hooks/stop_deep_review_gate.py`) will block ending if any required artifact missing or any required section missing.

---

## BirdCLEF-specific project rules (applied during all phases)

From `~/.claude/projects/C--Users-thc1006/memory/feedback_v4_disaster_postmortem.md`:
- NEVER `nan_to_num` on submission pipeline
- NEVER per-class weights tuned on different baseline
- NEVER surgery on uncontrolled pipeline
- NEVER pure replacement (w=1.0) on unvalidated injector
- NEVER multi-axis ablation in single sub
- NEVER baseline-sub

From `~/.claude/projects/C--Users-thc1006/memory/feedback_kaggle_submission_discipline.md`:
- Every sub must pass 6 gates (novelty / CV / LB target / single-axis / baseline-consistency / infrastructure-contract)

From `~/.claude/projects/C--Users-thc1006/memory/reference_yaroslav_v6_internals.md`:
- Yaroslav v6 has hidden second-round outer-join producing 56862 NaN cells in preview mode
- Model_5 weight 0.97 dominates
- Watch for silent column name issues (Unnamed:)

From `~/.claude/projects/C--Users-thc1006/memory/feedback_no_script_analysis.md`:
- Scripts must NOT contain hardcoded conclusion logic
- Each experiment variant must have its own folder + analysis.md by Claude (not script)

If any reviewer subagent finds a violation, it's a HIGH severity finding.
