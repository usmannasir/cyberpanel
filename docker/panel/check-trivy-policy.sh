#!/usr/bin/env bash
# Enforce vulnerability thresholds after Trivy JSON scan.
set -euo pipefail

REPORT="${1:-}"
TAG="${2:-unknown}"
RECOMMENDED="almalinux10 ubuntu2404 debian13 openeuler2203"
HIGH_LIMIT=25

if [ -z "$REPORT" ] || [ ! -f "$REPORT" ]; then
  echo "Usage: $0 <trivy.json> [tag]" >&2
  exit 2
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required" >&2
  exit 2
fi

count_fixable() {
  local sev="$1"
  jq -r --arg s "$sev" '
    [.Results[]?.Vulnerabilities[]?
      | select(.Severity == $s)
      | select((.FixedVersion // "") != "")
    ] | length
  ' "$REPORT"
}

count_unfixed() {
  local sev="$1"
  jq -r --arg s "$sev" '
    [.Results[]?.Vulnerabilities[]?
      | select(.Severity == $s)
      | select((.FixedVersion // "") == "")
    ] | length
  ' "$REPORT"
}

CRIT="$(count_fixable CRITICAL)"
HIGH="$(count_fixable HIGH)"
CRIT_UNFIXED="$(count_unfixed CRITICAL)"
HIGH_UNFIXED="$(count_unfixed HIGH)"

echo "Trivy policy for ${TAG}: fixable critical=${CRIT} high=${HIGH}; unfixed critical=${CRIT_UNFIXED} high=${HIGH_UNFIXED}"

if [ "$CRIT" -gt 0 ]; then
  echo "FAIL: fixable critical vulnerabilities must be 0 (found ${CRIT})" >&2
  exit 1
fi

for rec in $RECOMMENDED; do
  if [ "$TAG" = "$rec" ] && [ "$HIGH" -gt "$HIGH_LIMIT" ]; then
    echo "FAIL: recommended tag ${TAG} fixable high count ${HIGH} exceeds limit ${HIGH_LIMIT}" >&2
    exit 1
  fi
done

if [ "$CRIT_UNFIXED" -gt 0 ] || [ "$HIGH_UNFIXED" -gt 0 ]; then
  echo "WARN: unfixed findings remain (critical=${CRIT_UNFIXED} high=${HIGH_UNFIXED}); rebuild weekly and track Scout" >&2
fi

echo "PASS: vulnerability policy satisfied for ${TAG}"
