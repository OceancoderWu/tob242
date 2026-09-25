#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
PYTHON="${PYTHON:-python}"
DATA="${DATA:-$PWD/workspace/harbor_task/environment/public_assets/data}"
TEST_DATA="${TEST_DATA:-$PWD/evaluation_assets/data}"
for seed in 42 43 44; do
  for method in baseline reference; do
    method_file=workspace/harbor_task/solution/method.py
    if [[ "$method" == reference ]]; then method_file=workspace/reference/method.py; fi
    out="optimization_evidence/${method}_runs/seed_${seed}"
    mkdir -p "$(dirname "$out")"
    "$PYTHON" workspace/harbor_task/tests/train_eval.py --method "$method_file" --seed "$seed" --data "$DATA" --test-data "$TEST_DATA" --output "$out" > "${out}.log" 2>&1
    "$PYTHON" workspace/harbor_task/tests/train_eval.py --method "$method_file" --seed "$seed" --data "$DATA" --test-data "$TEST_DATA" --output "${out}_reload" --reload "$out/best.pt" > "${out}_reload.log" 2>&1
  done
done
"$PYTHON" expert_evidence/summarize.py
