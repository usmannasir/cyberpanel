#!/usr/bin/env bash
# CyberPanel SSH login banner: /etc/profile.d/cyberpanel.sh (sourced on SSH login).
# Content is fetched from https://cyberpanel.sh/?banner (not stored in git).

Install_Cyberpanel_Ssh_Login_Banner() {
  local banner_url="${CYBERPANEL_SSH_BANNER_URL:-https://cyberpanel.sh/?banner}"
  local dest="/etc/profile.d/cyberpanel.sh"
  local tmp="${dest}.tmp.$$"

  rm -rf /etc/profile.d/cyberpanel* 2>/dev/null || true

  if ! curl --silent --fail --max-time 30 -o "$tmp" "$banner_url" 2>/dev/null; then
    echo "[CyberPanel] SSH login banner download failed (${banner_url})" >&2
    rm -f "$tmp" 2>/dev/null || true
    return 1
  fi

  if [[ ! -s "$tmp" ]] || ! head -1 "$tmp" | grep -q '#!/bin/bash'; then
    echo "[CyberPanel] SSH login banner response invalid" >&2
    rm -f "$tmp" 2>/dev/null || true
    return 1
  fi

  mv "$tmp" "$dest"
  chmod 644 "$dest" 2>/dev/null || true
  chown root:root "$dest" 2>/dev/null || true
  return 0
}
