#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
PYTHON="${PYTHON:-python}"
DATA="${DATA:-$PWD/workspace/harbor_task/environment/public_assets/data}"
TEST_DATA="${TEST_DATA:-$PWD/evaluation_assets/data}"
for seed in 42; do
  for method in baseline reference; do
    method_file=workspace/harbor_task/environment/starter/method.py
    if [[ "$method" == reference ]]; then method_file=workspace/reference/method.py; fi
    out="optimization_evidence/${method}_runs/seed_${seed}"
    mkdir -p "$(dirname "$out")"
    if [[ -e "$out" || -e "${out}_reload" ]]; then
      echo "Run output already exists: $out (move it aside after auditing; never overwrite a seed)" >&2
      exit 1
    fi
    started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    exit_code=0
    timeout 7200s "$PYTHON" workspace/harbor_task/tests/train_eval.py --method "$method_file" --seed "$seed" --data "$DATA" --test-data "$TEST_DATA" --output "$out" > "${out}.run.log" 2>&1 || exit_code=$?
    if [[ "$exit_code" -eq 0 ]]; then
      timeout 7200s "$PYTHON" workspace/harbor_task/tests/train_eval.py --method "$method_file" --seed "$seed" --data "$DATA" --test-data "$TEST_DATA" --output "${out}_reload" --reload "$out/best.pt" > "${out}.reload.log" 2>&1 || exit_code=$?
    fi
    ended_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    "$PYTHON" expert_evidence/package_run.py --role "$method" --seed "$seed" --method "$method_file" \
      --run "$out" --reload "${out}_reload" --log "${out}.run.log" --reload-log "${out}.reload.log" \
      --started-at "$started_at" --ended-at "$ended_at" --exit-code "$exit_code"
    if [[ "$exit_code" -ne 0 ]]; then
      echo "Seed $seed $method failed; INVALID evidence preserved at $out" >&2
      exit "$exit_code"
    fi
  done
done
"$PYTHON" expert_evidence/summarize.py
