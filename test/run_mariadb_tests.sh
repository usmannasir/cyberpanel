#!/bin/bash
# Run all MariaDB version tests (upgrader + upgrade.py logic).
# From repo root: ./test/run_mariadb_tests.sh
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"
echo "=== Upgrader MariaDB version tests ==="
./test/upgrader_mariadb_version_test.sh
echo ""
echo "=== Upgrade.py mariadb_version read tests ==="
python3 test/test_upgrade_mariadb_version.py
echo ""
echo "=== All MariaDB version tests passed (11.8, 12.1, downgrade). ==="
