#!/usr/bin/env bash
set -euo pipefail
TESTS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK_ROOT="$(cd "$TESTS_ROOT/.." && pwd)"
if [[ -d /workspace/environment/public_assets ]]; then TASK_ROOT=/workspace; fi
[[ "$TESTS_ROOT" == /tests && "$TASK_ROOT" == /workspace ]] || {
  echo 'Formal verifier must run inside the Harbor container at /tests' >&2
  exit 1
}

mkdir -p /logs/verifier
rm -f /logs/verifier/reward.txt /logs/verifier/reward.json
test "$(id -u)" -eq 0 || { echo 'Verifier must run as root for test isolation' >&2; exit 1; }
if [[ -d /logs/artifacts && -n "$(find /logs/artifacts -mindepth 1 -print -quit)" ]]; then
  echo 'Unexpected extra Agent artifact; only method.py is accepted' >&2
  exit 1
fi
test -f "$TESTS_ROOT/anchors.json" || { echo 'Missing measured anchors.json' >&2; exit 1; }
test -d "$TESTS_ROOT/benchmark_data" || { echo 'Missing benchmark data' >&2; exit 1; }
test -f "$TASK_ROOT/solution/method.py" && test ! -L "$TASK_ROOT/solution/method.py" || {
  echo 'Missing regular submitted method artifact' >&2
  exit 1
}

# The separate verifier container starts only after the agent container ends.
# Freeze the submitted artifact before any candidate process is launched.
chown root:root "$TASK_ROOT/solution" "$TASK_ROOT/solution/method.py"
chmod 0555 "$TASK_ROOT/solution"
chmod 0444 "$TASK_ROOT/solution/method.py"

chown -R root:root "$TESTS_ROOT"
chmod -R a-w "$TESTS_ROOT"
chmod 0700 "$TESTS_ROOT/benchmark_data"
find "$TESTS_ROOT/benchmark_data" -type f -exec chmod 0600 {} +
chmod 0600 "$TESTS_ROOT/anchors.json"
if runuser -u researcher -- head -c 1 "$TESTS_ROOT/benchmark_data/test_rcc8_k_2_b_1.csv" >/dev/null 2>&1; then
  echo 'Candidate user can read benchmark data' >&2
  exit 1
fi
if runuser -u researcher -- head -c 1 "$TESTS_ROOT/anchors.json" >/dev/null 2>&1; then
  echo 'Candidate user can read trusted anchors' >&2
  exit 1
fi
runuser -u researcher -- head -c 1 "$TASK_ROOT/environment/public_assets/data/train_rcc8.csv" >/dev/null

python -m unittest discover -s "$TESTS_ROOT" -p 'test_contract.py' -v
python "$TESTS_ROOT/grader.py" \
  --method "$TASK_ROOT/solution/method.py" \
  --data "$TASK_ROOT/environment/public_assets/data" \
  --test-data "$TESTS_ROOT/benchmark_data" \
  --anchors "$TESTS_ROOT/anchors.json" \
  --output "$TASK_ROOT/output/verifier_$(date +%s%N)" \
  --candidate-user researcher \
  --reward-file /logs/verifier/reward.txt
