#!/bin/bash

set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEBSITE_FUNCTIONS="${BASE_DIR}/website-functions.sh"
HELPER="${BASE_DIR}/ols-apache-backend-setup.sh"

pass() { echo "[PASS] $1"; }
fail() { echo "[FAIL] $1"; exit 1; }

[[ -f "$WEBSITE_FUNCTIONS" ]] || fail "website-functions.sh missing"
[[ -f "$HELPER" ]] || fail "ols-apache-backend-setup.sh missing"
[[ -x "$HELPER" ]] || fail "helper is not executable"

bash -n "$WEBSITE_FUNCTIONS" || fail "website-functions.sh syntax invalid"
pass "website-functions syntax"

bash -n "$HELPER" || fail "helper syntax invalid"
pass "helper syntax"

if ! rg -q "Enable Additional Feature: OpenLiteSpeed \+ Apache backend" "$WEBSITE_FUNCTIONS"; then
    fail "create flow prompt for OLS+Apache backend missing"
fi
pass "create flow prompt exists"

if ! rg -q "setup_ols_apache_backend_if_enabled" "$WEBSITE_FUNCTIONS"; then
    fail "setup function wiring missing from website flow"
fi
pass "setup hook exists"

if ! rg -q "cyberpanel createChild" "$WEBSITE_FUNCTIONS"; then
    fail "child domain create function not wired"
fi
pass "child domain flow exists"

if ! rg -q "httpd -t" "$HELPER"; then
    fail "apache validation gate missing"
fi
pass "apache validation gate exists"

if ! rg -q "health_check_domain" "$HELPER"; then
    fail "domain health-check gate missing"
fi
pass "domain health-check gate exists"

echo "All OLS+Apache backend automation checks passed."
