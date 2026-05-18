# common-use-claude-resource

### 多代理並行（不衝突）

> 請先建立 To do list 然後請 claude code 建立 worktree 這樣才不用一直 checkout 或是 switch branch 進行開發，可以開多個 termianl 並行進行開發，但是前提是要有相同的例如進度檔案 可以是 CLAUDE.md 、 MEMORY.md 甚至是 自行宣告一份 to_do_list.md 通通都可以。

> 但就是要建立 一些機制來確保會自動寫入指定的 .md 檔案

未來針對特定功能的實現希望快速開發就可以：

我要幫這個 repo 加上 XXX 功能，需求是……
/parallel-dev

下面這個 prompt 也可以達成，但前提是要先有 sub-agents files
```
Coordinate multiple specialized anthropic official claude code sub-agents , delegating each isolated task to the best-fit agent and running them in parallel for maximum throughput. Assume adequate compute is available; prefer concurrency and only fall back to sequential execution if the environment throttles.
```

### 多代理對抗式 review

配合： ".claude\skills\adversarial-review\SKILL.md"

當你需要對抗式 review 你的 PR 的時候，或是例如希望使用 對抗式 review 就需要下 /adversarial-review 39

```
Coordinate the current development request using Claude Code’s official parallel-development mechanisms.

Use the latest explicit user request, current conversation context, current repo state, current branch, open issue/PR context, CLAUDE.md, AGENTS.md, README, tests, and package scripts as the task source. Do not ask me to paste a separate Task block.

ultrathink

Prefer maximum safe concurrency:
1. If the work can be decomposed into independent implementation units, use /batch-style decomposition with isolated worktrees.
2. If agents need to communicate, challenge each other, or coordinate integration risks, use Agent Teams with 3–5 teammates.
3. If the work is smaller, use specialized subagents with worktree isolation for file edits.
4. Fall back to sequential execution only when dependencies, file conflicts, environment throttling, or integration risk require it.

Before editing:
- infer the task,
- inspect git status and branch,
- identify the base branch,
- inspect project scripts,
- identify affected modules,
- create a file-ownership plan,
- create a test strategy,
- create TODOs for discovery, decomposition, implementation, integration, tests, adversarial review, and final fix pass.

Execution rules:
- The lead session coordinates all work.
- Do not delegate coordination to a worker.
- Use isolated worktrees for implementation agents whenever edits are required.
- Avoid assigning the same file to multiple agents.
- If file overlap is unavoidable, assign one integration owner.
- Each agent must report files changed, behavior changed, tests run, assumptions, failures, and residual risks.
- Prefer narrow tests per unit, then full repo verification after integration.

Quality gate:
- Run the most appropriate verification command, preferring ./verify.sh, then ./test.sh, then package-manager lint/test/build scripts, then language-specific test commands.
- If no test command exists, create or recommend a minimal verification path before claiming completion.

Adversarial review gate:
- After implementation and integration, run an ultrathink adversarial review of the full branch diff against the base branch, not only the latest commit.
- If /adversarial-review exists, invoke it.
- Otherwise perform the review inline.
- Review correctness, API contracts, hidden coupling between parallel changes, tests, edge cases, failure handling, rollback behavior, concurrency, security, prompt/tool injection, unsafe shell execution, path traversal, SSRF, secret leakage, performance, CI, and deployment risk.
- Fix all blocking findings.
- Re-run relevant tests.
- Re-run adversarial review once after fixes.

Do not merge automatically unless I explicitly ask.

Final output must include:
- inferred task,
- execution model used,
- work units,
- files changed,
- integration summary,
- tests run,
- adversarial review findings,
- fixes applied,
- remaining risks,
- final recommendation: READY TO MERGE, READY AFTER MANUAL REVIEW, NEEDS MORE WORK, or BLOCKED.
```