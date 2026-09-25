#!/usr/bin/env bash
# Future full verifier; requires measured, trusted anchors and a CUDA runtime.
set -euo pipefail
mkdir -p /logs/verifier
rm -f /logs/verifier/reward.txt
python /workspace/tests/grader.py --output /workspace/output/evaluation --anchors /opt/benchmark/anchors.json
python - <<'PY'
import json,math
from pathlib import Path
s=json.loads(Path('/workspace/output/evaluation/metrics.json').read_text())['score']
assert math.isfinite(s)
Path('/logs/verifier/reward.txt').write_text(str(s)+'\n')
PY
