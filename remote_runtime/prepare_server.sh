#!/usr/bin/env bash
# One-time preparation only. This script never invokes the model or trainer.
set -euo pipefail
agent_key="${1:?agent public key required}"
verifier_key="${2:?verifier public key required}"
base=/root/autodl-tmp/autore
public="$base/harbor242-public"
private="$base/harbor242-private"
[[ "$(id -u)" -eq 0 ]] || exit 2
id researcher >/dev/null 2>&1 || useradd -m -s /bin/bash researcher
# Allow traversal to the existing Python environment without listing /root.
chmod 0711 /root
for name in data downloads experiment logs paper242 patches scripts src wheels; do
  [[ ! -d "$base/$name" ]] || chmod 0700 "$base/$name"
done
mkdir -p "$public" "$private"
tar -C "$public" -xzf "$base/tob242-public-prep.tgz"
tar -C "$private" -xzf "$base/tob242-private-prep.tgz"
install -o root -g root -m 0755 "$private/remote_runtime/agent_entry.sh" /usr/local/bin/tob242-agent-entry
install -o root -g root -m 0755 "$public/remote_runtime/public/run.sh" "$public/run.sh"
install -o root -g root -m 0755 "$private/remote_runtime/private/verify.sh" "$private/verify.sh"
mkdir -p "$public/solution" "$public/output" "$private/solution" "$private/output"
chown -R root:root "$public"
chown -R researcher:researcher "$public/solution" "$public/output"
if [[ ! -f "$public/solution/method.py" ]]; then
  install -o researcher -g researcher -m 0644 \
    "$public/environment/starter/method.py" "$public/solution/method.py"
fi
touch "$public/.gpu.lock"
chown root:root "$public/.gpu.lock"
chmod 0444 "$public/.gpu.lock"
chmod -R a-w "$public/tests" "$public/environment" "$public/run.sh"
chown -R root:root "$private"
find "$private" -type d -exec chmod 0755 {} +
chmod 0700 "$private/tests/benchmark_data"
find "$private/tests/benchmark_data" -type f -exec chmod 0600 {} +
chmod 0555 "$private/solution"
chmod 0600 "$private/tests/anchors.json" 2>/dev/null || true
mkdir -p /root/.ssh
chmod 0700 /root/.ssh
touch /root/.ssh/authorized_keys
chmod 0600 /root/.ssh/authorized_keys
agent_line="no-agent-forwarding,no-port-forwarding,no-X11-forwarding,command=\"/usr/local/bin/tob242-agent-entry\" $agent_key"
verifier_line="restrict $verifier_key"
grep -Fv "$agent_key" /root/.ssh/authorized_keys > /root/.ssh/authorized_keys.tmp || true
printf '%s\n' "$agent_line" >> /root/.ssh/authorized_keys.tmp
mv -f /root/.ssh/authorized_keys.tmp /root/.ssh/authorized_keys
chmod 0600 /root/.ssh/authorized_keys
grep -Fqx "$verifier_line" /root/.ssh/authorized_keys || printf '%s\n' "$verifier_line" >> /root/.ssh/authorized_keys
printf 'PREPARED public=%s private=%s\n' "$public" "$private"
