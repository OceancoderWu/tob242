#!/usr/bin/env bash
set -euo pipefail
root=/root/autodl-tmp/autore/harbor242-public
mode="${1:?mode required}"
run_id="${2:?run id required}"
seed="${3:-42}"
[[ "$mode" == public-dev || "$mode" == smoke ]] || exit 2
[[ "$run_id" =~ ^[a-zA-Z0-9_-]+$ && "$seed" == 42 ]] || exit 2
[[ "$(id -un)" == researcher ]] || exit 2
exec 9<"$root/.gpu.lock"
flock -x 9
method="$root/solution/method.py"
output="$root/output/$run_id"
[[ ! -e "$output" ]] || { echo "Output already exists: $output" >&2; exit 2; }
temp="$(mktemp "$root/solution/.method.XXXXXX")"
trap 'rm -f "$temp"' EXIT
cat > "$temp"
[[ -s "$temp" && "$(wc -c < "$temp")" -le 262144 ]] || exit 2
chmod 0644 "$temp"
mv -f "$temp" "$method"
args=(--method "$method" --seed "$seed" --output "$output")
if [[ "$mode" == smoke ]]; then args+=(--smoke); else args+=(--public-dev); fi
exec /root/autodl-tmp/autore/envs/research/bin/python "$root/tests/train_eval.py" "${args[@]}"
