#!/usr/bin/env bash
set -euo pipefail
REF_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python "$REF_ROOT/../harbor_task/tests/grader.py" --method "$REF_ROOT/method.py" --output "${1:?Pass a new output directory}" --anchors "${2:?Pass trusted anchors.json}"
