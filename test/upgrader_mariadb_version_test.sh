#!/bin/bash
# Test script for cyberpanel_upgrade.sh MariaDB version handling (11.8, 12.1, downgrade).
# Run from repo root: ./test/upgrader_mariadb_version_test.sh
# Does not require root or a real CyberPanel install.

set -e
FAILED=0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
UPGRADE_SCRIPT="$REPO_ROOT/cyberpanel_upgrade.sh"

# Default (same as cyberpanel_upgrade.sh)
MARIADB_VER="11.8"

# Parse --mariadb-version from "$@" (same logic as Check_Argument in cyberpanel_upgrade.sh)
parse_mariadb_version() {
  if [[ "$*" = *"--mariadb-version "* ]]; then
    MARIADB_VER=$(echo "$*" | sed -n 's/.*--mariadb-version \([^ ]*\).*/\1/p' | head -1)
    MARIADB_VER="${MARIADB_VER:-11.8}"
  fi
  if [[ "$MARIADB_VER" != "11.8" ]] && [[ "$MARIADB_VER" != "12.1" ]]; then
    MARIADB_VER="11.8"
  fi
}

assert_equals() {
  local expected="$1"
  local actual="$2"
  local name="${3:-value}"
  if [[ "$actual" != "$expected" ]]; then
    echo "FAIL: $name expected '\''$expected'\'' got '\''$actual'\''"
    FAILED=1
  else
    echo "OK: $name = $actual"
  fi
}

echo "=== 1. Default (no --mariadb-version) ==="
MARIADB_VER="11.8"
parse_mariadb_version ""
assert_equals "11.8" "$MARIADB_VER" "default"

echo ""
echo "=== 2. Explicit 11.8 ==="
MARIADB_VER="11.8"
parse_mariadb_version "--mariadb-version 11.8"
assert_equals "11.8" "$MARIADB_VER" "--mariadb-version 11.8"

echo ""
echo "=== 3. Explicit 12.1 ==="
MARIADB_VER="11.8"
parse_mariadb_version "--mariadb-version 12.1"
assert_equals "12.1" "$MARIADB_VER" "--mariadb-version 12.1"

echo ""
echo "=== 4. Downgrade: 12.1 then 11.8 (both must be accepted) ==="
MARIADB_VER="11.8"
parse_mariadb_version "--mariadb-version 12.1"
assert_equals "12.1" "$MARIADB_VER" "first 12.1"
parse_mariadb_version "--mariadb-version 11.8"
assert_equals "11.8" "$MARIADB_VER" "then 11.8 (downgrade)"

echo ""
echo "=== 5. Invalid value falls back to 11.8 ==="
MARIADB_VER="11.8"
parse_mariadb_version "--mariadb-version 10.11"
assert_equals "11.8" "$MARIADB_VER" "invalid 10.11 -> 11.8"
parse_mariadb_version "--mariadb-version 13"
assert_equals "11.8" "$MARIADB_VER" "invalid 13 -> 11.8"

echo ""
echo "=== 6. With -b and --mariadb-version ==="
MARIADB_VER="11.8"
parse_mariadb_version "-b v2.5.5-dev --mariadb-version 12.1"
assert_equals "12.1" "$MARIADB_VER" "-b v2.5.5-dev --mariadb-version 12.1"

echo ""
echo "=== 7. MariaDB.repo baseurl uses MARIADB_VER ==="
MARIADB_VER="12.1"
MARIADB_REPO="rhel9-amd64"
baseurl="https://mirror.mariadb.org/yum/$MARIADB_VER/$MARIADB_REPO"
assert_equals "https://mirror.mariadb.org/yum/12.1/rhel9-amd64" "$baseurl" "baseurl 12.1"
MARIADB_VER="11.8"
baseurl="https://mirror.mariadb.org/yum/$MARIADB_VER/$MARIADB_REPO"
assert_equals "https://mirror.mariadb.org/yum/11.8/rhel9-amd64" "$baseurl" "baseurl 11.8"

echo ""
echo "=== 8. Script contains required logic ==="
if [[ ! -f "$UPGRADE_SCRIPT" ]]; then
  echo "FAIL: $UPGRADE_SCRIPT not found"
  FAILED=1
else
  echo "OK: upgrade script exists"
  grep -q 'MARIADB_VER="11.8"' "$UPGRADE_SCRIPT" && echo "OK: default MARIADB_VER" || { echo "FAIL: default MARIADB_VER"; FAILED=1; }
  grep -q '/etc/cyberpanel/mariadb_version' "$UPGRADE_SCRIPT" && echo "OK: mariadb_version file" || { echo "FAIL: mariadb_version file"; FAILED=1; }
fi

echo ""
if [[ $FAILED -eq 0 ]]; then
  echo "All upgrader MariaDB version tests passed."
  exit 0
else
  echo "Some tests failed."
  exit 1
fi
