#!/usr/bin/env bash
set -euo pipefail

role="${1:?agent or verifier required}"
shift
case "$role" in
  agent)
    key_b64="${T242_AGENT_KEY_B64:?Host must provide T242_AGENT_KEY_B64}"
    # This root-owned SSH key has a forced command that drops to researcher.
    remote_user=root
    ;;
  verifier)
    key_b64="${T242_VERIFIER_KEY_B64:?Host must provide T242_VERIFIER_KEY_B64}"
    remote_user=root
    ;;
  *) echo 'Unknown SSH role' >&2; exit 2 ;;
esac
if [[ "$role" == verifier && "$#" -ne 1 ]] || [[ "$#" -gt 1 ]]; then
  echo 'Pass one remote command, or omit it for an interactive Agent shell' >&2
  exit 2
fi
ssh_mode=(-T)
if [[ "$role" == agent && "$#" -eq 0 ]]; then ssh_mode=(-tt); fi
temp_dir="$(mktemp -d)"
trap 'rm -rf "$temp_dir"' EXIT
umask 077
printf '%s' "$key_b64" | base64 -d > "$temp_dir/id_ed25519"
unset key_b64
chmod 0600 "$temp_dir/id_ed25519"
ssh "${ssh_mode[@]}" -i "$temp_dir/id_ed25519" \
  -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile=/workspace/environment/known_hosts \
  -o ConnectTimeout=20 -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
  -p 14755 "$remote_user@connect.bjb1.seetacloud.com" "$@"
