#!/usr/bin/env bash
set -euo pipefail

# Quality gate for TaskCompleted / TeammateIdle hook events.
# Exit 2 only when an applicable verifier exists AND it fails.
# Absence of a verifier is exit 0 with an informational warning,
# because exit 2 on TaskCompleted blocks the task from being marked done
# (per docs, "TaskCompleted: exit 2 prevents task from being marked completed").

INPUT="$(cat || true)"
HOOK_EVENT_NAME="$(printf '%s' "$INPUT" | jq -r '.hook_event_name // "unknown"' 2>/dev/null || echo "unknown")"
TASK_SUBJECT="$(printf '%s' "$INPUT" | jq -r '.task_subject // "unknown task"' 2>/dev/null || echo "unknown task")"
TEAMMATE_NAME="$(printf '%s' "$INPUT" | jq -r '.teammate_name // empty' 2>/dev/null || true)"
STOP_HOOK_ACTIVE="$(printf '%s' "$INPUT" | jq -r '.stop_hook_active // false' 2>/dev/null || echo "false")"

# Break potential forced-continuation loops driven by repeated blocks.
if [ "${STOP_HOOK_ACTIVE}" = "true" ]; then
  exit 0
fi

echo "Running quality gate for ${HOOK_EVENT_NAME}: ${TASK_SUBJECT}" >&2
if [ -n "${TEAMMATE_NAME}" ]; then
  echo "Triggered by teammate: ${TEAMMATE_NAME}" >&2
fi

run_cmd() {
  echo "+ $*" >&2
  "$@"
}

if [ -x "./verify.sh" ]; then
  run_cmd ./verify.sh

elif [ -x "./test.sh" ]; then
  run_cmd ./test.sh

elif [ -f "package.json" ]; then
  if command -v pnpm >/dev/null 2>&1; then
    if pnpm run | grep -qE '^  lint($|:)'; then
      run_cmd pnpm lint
    fi
    run_cmd pnpm test

  elif command -v npm >/dev/null 2>&1; then
    if npm run 2>/dev/null | grep -qE '^  lint($|:)'; then
      run_cmd npm run lint
    fi
    run_cmd npm test

  else
    echo "package.json exists but neither pnpm nor npm is available; skipping verifier." >&2
    exit 0
  fi

elif [ -f "pytest.ini" ] || { [ -f "pyproject.toml" ] && grep -qE '^\[tool\.pytest' pyproject.toml 2>/dev/null; } || [ -d "tests" ]; then
  if command -v pytest >/dev/null 2>&1; then
    run_cmd pytest
  else
    echo "Python test project detected, but pytest is not available; skipping verifier." >&2
    exit 0
  fi

elif [ -f "go.mod" ]; then
  run_cmd go test ./...

elif [ -f "Cargo.toml" ]; then
  run_cmd cargo test

elif [ -f "Makefile" ] && grep -qE '^test:' Makefile; then
  run_cmd make test

else
  # No verifier configured. Do NOT block the task — exit 2 here would deadlock
  # any task-tracking workflow in a config-only or docs-only repo.
  echo "No verifier configured for this repository. Skipping quality gate for ${TASK_SUBJECT}." >&2
  echo "(Add ./verify.sh, ./test.sh, package.json test script, pytest setup, go.mod, Cargo.toml, or Makefile 'test:' target to enable.)" >&2
  exit 0
fi

echo "Quality gate passed for ${TASK_SUBJECT}." >&2
exit 0
