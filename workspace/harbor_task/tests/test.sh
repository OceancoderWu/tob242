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
test "$(id -u)" -eq 0 || { echo 'Verifier must run as root' >&2; exit 1; }
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
# The local container holds the root SSH credential; the Agent never sees it.
chown root:root "$TASK_ROOT/solution" "$TASK_ROOT/solution/method.py"
chmod 0555 "$TASK_ROOT/solution"
chmod 0444 "$TASK_ROOT/solution/method.py"
python3 -m unittest discover -s "$TESTS_ROOT" -p 'test_contract.py' -v
temp="$(mktemp -d)"
trap 'rm -rf "$temp"' EXIT
cp "$TASK_ROOT/solution/method.py" "$temp/method.py"
cp "$TESTS_ROOT/anchors.json" "$temp/anchors.json"
tar -C "$temp" -cf - method.py anchors.json | \
  bash "$TESTS_ROOT/remote_client.sh" verifier \
    /root/autodl-tmp/autore/harbor242-private/verify.sh | tee "$temp/remote.log"
grep '^T242_REWARD=' "$temp/remote.log" | tail -n 1 | cut -d= -f2- > "$temp/reward.txt"
python3 - "$temp/reward.txt" <<'PY'
import math, pathlib, sys
raw = pathlib.Path(sys.argv[1]).read_text().strip()
if not raw or not math.isfinite(float(raw)):
    raise ValueError('Remote verifier returned no finite reward')
PY
reward_temp="$(mktemp /logs/verifier/.reward.XXXXXX)"
cp "$temp/reward.txt" "$reward_temp"
mv -f "$reward_temp" /logs/verifier/reward.txt
