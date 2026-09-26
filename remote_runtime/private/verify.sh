#!/usr/bin/env bash
set -euo pipefail
root=/root/autodl-tmp/autore/harbor242-private
[[ "$(id -u)" -eq 0 ]] || exit 2
exec 9>"$root/.verifier.lock"
flock -n 9 || { echo 'Another formal verifier is running' >&2; exit 1; }
exec 8</root/autodl-tmp/autore/harbor242-public/.gpu.lock
flock -x 8
[[ -d "$root/tests/benchmark_data" ]] || exit 1
input="$(mktemp -d "$root/input.XXXXXX")"
trap 'rm -rf "$input"' EXIT
tar -C "$input" -xf -
[[ -f "$input/method.py" && -f "$input/anchors.json" ]] || exit 2
[[ ! -L "$input/method.py" && ! -L "$input/anchors.json" ]] || exit 2
install -o root -g root -m 0444 "$input/method.py" "$root/solution/method.py"
install -o root -g root -m 0600 "$input/anchors.json" "$root/tests/anchors.json"
chmod 0555 "$root/solution"
chmod 0700 "$root/tests/benchmark_data"
find "$root/tests/benchmark_data" -type f -exec chmod 0600 {} +
output="$(mktemp -d "$root/output/formal.XXXXXX")"
rmdir "$output"
reward="$input/reward.txt"
/root/autodl-tmp/autore/envs/research/bin/python "$root/tests/grader.py" \
  --method "$root/solution/method.py" \
  --data "$root/environment/public_assets/data" \
  --test-data "$root/tests/benchmark_data" \
  --anchors "$root/tests/anchors.json" \
  --output "$output" --candidate-user researcher --reward-file "$reward"
[[ -s "$reward" ]] || exit 1
printf 'T242_REWARD='
cat "$reward"
