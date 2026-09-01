#!/usr/bin/env bash
# Refresh optional base image digests in os-matrix.json (run before release rebuilds).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MATRIX="${SCRIPT_DIR}/os-matrix.json"
TMP="$(mktemp)"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required" >&2
  exit 1
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required" >&2
  exit 1
fi

echo "Refreshing base digests in ${MATRIX} ..."

jq -c '.[]' "$MATRIX" | while IFS= read -r row; do
  tag="$(echo "$row" | jq -r '.tag')"
  base="$(echo "$row" | jq -r '.base')"
  family="$(echo "$row" | jq -r '.family')"
  echo "  ${tag}: pulling ${base} ..."
  if ! docker pull "${base}" >/dev/null 2>&1; then
    echo "    WARN: pull failed; keeping empty digest for ${tag}" >&2
    echo "$row" | jq '.digest = ""'
    continue
  fi
  digest="$(docker inspect --format='{{index .RepoDigests 0}}' "${base}" 2>/dev/null | cut -d@ -f2 || true)"
  if [ -z "${digest}" ]; then
    digest="$(docker image inspect "${base}" --format='{{.Id}}' 2>/dev/null || true)"
  fi
  echo "$row" | jq --arg d "${digest}" '.digest = $d'
done | jq -s '.' > "$TMP"

mv "$TMP" "$MATRIX"
echo "Done. Review ${MATRIX} and commit digest updates when ready."
