#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python "$TASK_ROOT/tests/grader.py" --method "$TASK_ROOT/solution/method.py" --output "${1:?Pass a new output directory}" --anchors "${2:?Pass trusted anchors.json}"
