#!/usr/bin/env bash
set -euo pipefail

# Harbor uploads the private solution folder only for Oracle runs. In a regular
# Agent container, this script runs the public R-GCN starter already present.
if [[ -f /solution/method.py && -d /workspace/solution ]]; then
  cp /solution/method.py /workspace/solution/method.py
fi

TASK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -d /workspace/environment/public_assets ]]; then TASK_ROOT=/workspace; fi
output="${1:-$TASK_ROOT/output/public_dev_42}"
[[ "$output" = /* ]] || output="$TASK_ROOT/$output"
seed="${2:-42}"
mode="${3:-public-dev}"
run_id="$(basename "$output")"
[[ "$output" == "$TASK_ROOT/output/$run_id" ]] || { echo 'Output must be a direct child of /workspace/output' >&2; exit 2; }
[[ "$run_id" =~ ^[a-zA-Z0-9_-]+$ && "$seed" == 42 ]] || exit 2
[[ "$mode" == public-dev || "$mode" == smoke ]] || exit 2
[[ ! -e "$output" ]] || { echo 'Local output already exists' >&2; exit 2; }
remote_root=/root/autodl-tmp/autore/harbor242-public
bash "$TASK_ROOT/tests/remote_client.sh" agent \
  "$remote_root/run.sh $mode $run_id $seed" < "$TASK_ROOT/solution/method.py"
mkdir -p "$output"
for name in result.json provenance.json epochs.jsonl; do
  bash "$TASK_ROOT/tests/remote_client.sh" agent \
    "cat $remote_root/output/$run_id/$name" > "$output/$name"
done
echo "Remote output: $remote_root/output/$run_id"
