#!/usr/bin/env bash
set -euo pipefail
# SSH authenticates the key as root, then every Agent command runs as researcher.
cd /root/autodl-tmp/autore/harbor242-public
export PATH="/root/autodl-tmp/autore/envs/research/bin:/usr/local/bin:/usr/bin:/bin"
if [[ -n "${SSH_ORIGINAL_COMMAND:-}" ]]; then
  exec /usr/sbin/runuser -u researcher -- /bin/bash -c "$SSH_ORIGINAL_COMMAND"
fi
exec /usr/sbin/runuser -u researcher -- /bin/bash -i
