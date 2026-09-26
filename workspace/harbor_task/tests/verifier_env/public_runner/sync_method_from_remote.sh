#!/usr/bin/env bash
set -euo pipefail
task_root=/workspace
remote_method=/root/autodl-tmp/autore/harbor242-public/solution/method.py
[[ -d "$task_root/solution" ]] || exit 2
temp="$(mktemp "$task_root/solution/.method.XXXXXX")"
trap 'rm -f "$temp"' EXIT
bash "$task_root/tests/remote_client.sh" agent "cat $remote_method" > "$temp"
python3 - "$temp" "$task_root/tests" <<'PY'
import pathlib, sys
sys.path.insert(0, sys.argv[2])
from security import check_method
path = pathlib.Path(sys.argv[1])
if not path.is_file() or not 0 < path.stat().st_size <= 262144:
    raise ValueError('Remote method is empty or too large')
check_method(path)
PY
chmod 0644 "$temp"
mv -f "$temp" "$task_root/solution/method.py"
echo 'Synced remote method to Harbor submission artifact.'
