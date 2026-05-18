#!/usr/bin/env bash
set -euo pipefail

INPUT="$(cat || true)"
HOOK_EVENT_NAME="$(printf '%s' "$INPUT" | jq -r '.hook_event_name // "unknown"' 2>/dev/null || echo "unknown")"
TASK_SUBJECT="$(printf '%s' "$INPUT" | jq -r '.task_subject // "unknown task"' 2>/dev/null || echo "unknown task")"
TEAMMATE_NAME="$(printf '%s' "$INPUT" | jq -r '.teammate_name // empty' 2>/dev/null || true)"

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
    echo "package.json exists but neither pnpm nor npm is available." >&2
    echo "Install pnpm/npm or add ./verify.sh for this repository." >&2
    exit 2
  fi

elif [ -f "pytest.ini" ] || [ -f "pyproject.toml" ] || [ -d "tests" ]; then
  if command -v pytest >/dev/null 2>&1; then
    run_cmd pytest
  else
    echo "Python test project detected, but pytest is not available." >&2
    echo "Install pytest or add ./verify.sh for this repository." >&2
    exit 2
  fi

elif [ -f "go.mod" ]; then
  run_cmd go test ./...

elif [ -f "Cargo.toml" ]; then
  run_cmd cargo test

elif [ -f "Makefile" ] && grep -qE '^test:' Makefile; then
  run_cmd make test

else
  echo "No known verification command found." >&2
  echo "Add one of: ./verify.sh, ./test.sh, package.json test script, pytest tests, go.mod, Cargo.toml, or Makefile test target." >&2
  echo "Blocking task completion because this repository has no explicit quality gate." >&2
  exit 2
fi

echo "Quality gate passed for ${TASK_SUBJECT}." >&2
exit 0