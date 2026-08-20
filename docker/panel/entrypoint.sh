#!/usr/bin/env bash
set -euo pipefail

# Prepare cgroup mounts for systemd when the runtime does not provide them.
if [ -d /sys/fs/cgroup ] && [ ! -e /sys/fs/cgroup/systemd ]; then
  mkdir -p /sys/fs/cgroup/systemd
  mount -t cgroup -o none,name=systemd cgroup /sys/fs/cgroup/systemd 2>/dev/null || true
fi

export CYBERPANEL_CONTAINER=1

if [ -n "${CYBERPANEL_HOSTNAME:-}" ]; then
  hostname "${CYBERPANEL_HOSTNAME}" 2>/dev/null || true
  if command -v hostnamectl >/dev/null 2>&1; then
    hostnamectl set-hostname "${CYBERPANEL_HOSTNAME}" 2>/dev/null || true
  fi
fi

exec "$@"
