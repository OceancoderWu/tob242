#!/usr/bin/env bash
set -euo pipefail

# Harbor uploads the private solution folder only for Oracle runs. In a regular
# Agent container, this script runs the public R-GCN starter already present.
if [[ -f /solution/method.py && -d /workspace/solution ]]; then
  cp /solution/method.py /workspace/solution/method.py
fi

TASK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -d /workspace/environment/public_assets ]]; then TASK_ROOT=/workspace; fi
exec python "$TASK_ROOT/tests/train_eval.py" \
  --method "$TASK_ROOT/solution/method.py" \
  --public-dev --seed "${2:-42}" --output "${1:-$TASK_ROOT/output/public_dev_42}"
