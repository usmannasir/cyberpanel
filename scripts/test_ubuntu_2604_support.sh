#!/bin/bash

# Test script for Ubuntu 26.04 support in CyberPanel
# Verifies that CyberPanel detects Ubuntu 26.04 (Resolute Raccoon) and that the
# dependencies which differ from earlier Ubuntu releases resolve correctly.
#
# Ubuntu 26.04 differs from 24.04 in three ways that matter to CyberPanel:
#   - it ships Python 3.14, which Django 4.2 does not support (we install 3.12)
#   - MariaDB 10.11 publishes no resolute repo (we use 11.8 LTS)
#   - libpcre3 (PCRE1) was removed from the archive (we use pcre2)

echo "CyberPanel Ubuntu 26.04 Support Test"
echo "===================================="
echo ""

FAILED=0
pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; FAILED=1; }
info() { echo "  ..  $1"; }

if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo "Detected OS: $NAME $VERSION"
    if [[ "$NAME" == "Ubuntu" ]] && [[ "$VERSION_ID" == "26.04" ]]; then
        echo "Ubuntu 26.04 detected"
    else
        echo "NOTE: this test targets Ubuntu 26.04; running it elsewhere only"
        echo "      checks the detection logic, not the installed packages."
    fi
else
    echo "Cannot detect OS - /etc/os-release missing"
    exit 1
fi
echo ""

# Test 1: the installer's OS gate accepts 26.04
echo "Test 1: Version detection"
echo "-------------------------"
if grep -q -E "Ubuntu 26.04" /etc/os-release; then
    pass "Ubuntu 26.04 pattern matches /etc/os-release"
else
    info "not running on 26.04; skipping pattern match"
fi

# Server_OS_Version is derived with 'head -c2', so 26.04 must yield 26
PARSED=$(grep VERSION_ID /etc/os-release | awk -F[=,] '{print $2}' | tr -d \" | head -c2 | tr -d . )
if [[ "$VERSION_ID" == "26.04" ]]; then
    if [[ "$PARSED" == "26" ]]; then
        pass "Server_OS_Version parsed as 26"
    else
        fail "Server_OS_Version parsed as '$PARSED', expected 26"
    fi
fi
echo ""

# Test 2: codename mapping must be resolute, not noble
echo "Test 2: Codename mapping"
echo "------------------------"
if [[ "$VERSION_ID" == "26.04" ]]; then
    if [[ "$UBUNTU_CODENAME" == "resolute" ]]; then
        pass "codename is resolute"
    else
        fail "codename is '$UBUNTU_CODENAME', expected resolute"
    fi
fi
echo ""

# Test 3: Python runtime - Django 4.2 cannot run on 26.04's system Python 3.14
echo "Test 3: Python runtime"
echo "----------------------"
if [ -x /usr/local/CyberCP/bin/python ]; then
    VENV_PY=$(/usr/local/CyberCP/bin/python --version 2>&1 | awk '{print $2}')
    VENV_MINOR=$(echo "$VENV_PY" | cut -d. -f1,2)
    if [[ "$VENV_MINOR" == "3.12" ]]; then
        pass "CyberCP venv runs Python $VENV_PY"
    else
        fail "CyberCP venv runs Python $VENV_PY, expected 3.12.x (Django 4.2 supports <=3.12)"
    fi
    if /usr/local/CyberCP/bin/python -c "import django" 2>/dev/null; then
        pass "Django imports inside the venv"
    else
        fail "Django does not import inside the venv"
    fi
else
    info "CyberCP venv not present; skipping (run after install)"
fi
echo ""

# Test 4: PCRE - libpcre3 is gone from 26.04
echo "Test 4: PCRE libraries"
echo "----------------------"
if [[ "$VERSION_ID" == "26.04" ]]; then
    if apt-cache show libpcre3-dev >/dev/null 2>&1; then
        info "libpcre3-dev unexpectedly available; PCRE1 path still usable"
    else
        pass "libpcre3-dev absent as expected on 26.04"
        if apt-cache show libpcre2-dev >/dev/null 2>&1; then
            pass "libpcre2-dev available as the replacement"
        else
            fail "neither libpcre3-dev nor libpcre2-dev available"
        fi
    fi
fi

# lscpd is the panel daemon; if it wants PCRE1 and PCRE1 is gone, it will not start
if [ -f /usr/local/lscp/bin/lscpd ]; then
    if ldd /usr/local/lscp/bin/lscpd 2>/dev/null | grep -q 'libpcre\.so\.1'; then
        if [ -e /lib/x86_64-linux-gnu/libpcre.so.1 ]; then
            pass "lscpd needs libpcre.so.1 and it is present"
        else
            fail "lscpd needs libpcre.so.1 but it is missing - lscpd will not start"
        fi
    else
        pass "lscpd does not link against PCRE1"
    fi
else
    info "lscpd binary not found; skipping (run after install)"
fi
echo ""

# Test 5: MariaDB - 10.11 has no resolute repo, 11.8 does
echo "Test 5: MariaDB"
echo "---------------"
if command -v mysql >/dev/null 2>&1; then
    MDB=$(mysql --version)
    if echo "$MDB" | grep -qE '11\.8|1[2-9]\.'; then
        pass "MariaDB version acceptable: $MDB"
    else
        fail "unexpected MariaDB version on 26.04: $MDB"
    fi
else
    info "mysql client not found; skipping (run after install)"
fi
echo ""

# Test 6: services
echo "Test 6: Services"
echo "----------------"
for svc in lscpd lsws mariadb; do
    if systemctl list-unit-files 2>/dev/null | grep -q "^${svc}"; then
        if systemctl is-active --quiet "$svc"; then
            pass "$svc is active"
        else
            fail "$svc is installed but not active"
        fi
    else
        info "$svc not installed; skipping"
    fi
done
echo ""

echo "===================================="
if [ $FAILED -eq 0 ]; then
    echo "All executed checks passed."
    exit 0
else
    echo "One or more checks FAILED - see above."
    exit 1
fi
