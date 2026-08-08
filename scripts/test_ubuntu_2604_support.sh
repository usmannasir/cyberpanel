#!/bin/bash

# Test script for Ubuntu 26.04 support in CyberPanel
# Verifies that CyberPanel detects Ubuntu 26.04 (Resolute Raccoon) and that the
# dependencies which differ from earlier Ubuntu releases resolve correctly.
#
# Ubuntu 26.04 differs from 24.04 in several ways that matter to CyberPanel:
#   - it ships Python 3.14, which Django 4.2 does not support (we install 3.12)
#   - MariaDB 10.11 publishes no resolute repo (we use 11.8 LTS)
#   - libpcre3 (PCRE1) was removed from the archive (we use pcre2)
#   - Dovecot 2.4 rejects the legacy 2.3 configuration syntax

echo "CyberPanel Ubuntu 26.04 Support Test"
echo "===================================="
echo ""

FAILED=0
pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; FAILED=1; }
info() { echo "  ..  $1"; }

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

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

    if [[ "$VERSION_ID" == "26.04" ]]; then
        if [[ "$(stat -c %a /usr/local/CyberCP/pyvenv.cfg 2>/dev/null)" == "644" ]]; then
            pass "CyberCP venv metadata is readable by lswsgi"
        else
            fail "CyberCP venv metadata permissions prevent lswsgi startup"
        fi

        if runuser -u cyberpanel -- test -r /usr/local/CyberCP/lib/python3.12/encodings/__init__.py; then
            pass "embedded Python 3.12 standard library is readable"
        else
            fail "embedded Python 3.12 standard library is missing or unreadable"
        fi
    fi
else
    info "CyberCP venv not present; skipping (run after install)"
fi

if grep -q 'cp -a /usr/lib/python3.12/. /usr/local/CyberCP/lib/python3.12/' "$REPO_ROOT/cyberpanel.sh" \
    && grep -q 'chmod 0644 /usr/local/CyberCP/pyvenv.cfg' "$REPO_ROOT/cyberpanel.sh"; then
    pass "Ubuntu 26 lswsgi runtime is provisioned"
else
    fail "Ubuntu 26 lswsgi runtime provisioning is incomplete"
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

# Test 6: Dovecot 2.4 configuration shipped by Ubuntu 26.04
echo "Test 6: Dovecot 2.4 configuration"
echo "--------------------------------"
DOVECOT_24_CONFIG="$REPO_ROOT/install/email-configs-one/dovecot-2.4.conf"
if [ -f "$DOVECOT_24_CONFIG" ]; then
    FIRST_SETTING=$(grep -m1 -v -E '^[[:space:]]*(#|$)' "$DOVECOT_24_CONFIG")
    if [[ "$FIRST_SETTING" == "dovecot_config_version = 2.4.0" ]]; then
        pass "Dovecot 2.4 config version is the first setting"
    else
        fail "Dovecot 2.4 config must begin with dovecot_config_version = 2.4.0"
    fi

    grep -q '^dovecot_storage_version = 2\.4\.0$' "$DOVECOT_24_CONFIG" \
        && pass "Dovecot 2.4 storage version is pinned" \
        || fail "Dovecot 2.4 storage version is missing"
    grep -q '^ssl_server_cert_file = ' "$DOVECOT_24_CONFIG" \
        && pass "Dovecot 2.4 SSL setting names are used" \
        || fail "Dovecot 2.4 SSL setting names are missing"
    grep -q '^namespace inbox {' "$DOVECOT_24_CONFIG" \
        && pass "Dovecot 2.4 namespace is named" \
        || fail "Dovecot 2.4 namespace must be named"

    if grep -q -E '^plugin \{|^passdb \{|^userdb \{|\$protocols|^ssl_(cert|key) = ' "$DOVECOT_24_CONFIG"; then
        fail "Dovecot 2.4 config contains legacy 2.3 syntax"
    else
        pass "Dovecot 2.4 config excludes legacy 2.3 syntax"
    fi
else
    fail "Dovecot 2.4 config template is missing"
fi

if grep -q 'dovecot-2.4.conf' "$REPO_ROOT/install/install.py"; then
    pass "installer selects the Dovecot 2.4 template"
else
    fail "installer does not select the Dovecot 2.4 template"
fi

if grep -q "dovecot_config_version = 2.4.0" "$REPO_ROOT/plogical/virtualHostUtilities.py" \
    && grep -q "ssl_server_cert_file" "$REPO_ROOT/plogical/virtualHostUtilities.py" \
    && grep -q "ssl_server_key_file" "$REPO_ROOT/plogical/virtualHostUtilities.py"; then
    pass "website SSL uses Dovecot 2.4 SNI setting names"
else
    fail "website SSL still writes legacy Dovecot SNI settings"
fi

if [ -f "$REPO_ROOT/install/email-configs-one/dovecot-sql-2.4.conf" ]; then
    pass "Dovecot 2.4 SQL authentication template is present"
else
    fail "Dovecot 2.4 SQL authentication template is missing"
fi

if [[ "$VERSION_ID" == "26.04" ]] && command -v doveconf >/dev/null 2>&1; then
    if doveconf -n >/dev/null 2>&1; then
        pass "installed Dovecot configuration parses successfully"
    else
        fail "installed Dovecot configuration does not parse"
    fi
fi
echo ""

# Test 7: source-checkout-independent certificate generation
echo "Test 7: Certificate workspace"
echo "-----------------------------"
if grep -q '/root/cyberpanel/cert_conf' "$REPO_ROOT/cyberpanel.sh"; then
    fail "certificate generation assumes a /root/cyberpanel checkout"
else
    pass "certificate generation is independent of the source checkout path"
fi

if awk '
    /def installCustomOLSBinaries\(self\):/ { in_method=1 }
    in_method && /lswsctrl.*stop/ { stop_line=NR }
    in_method && /shutil\.move\(tmp_binary, OLS_BINARY_PATH\)/ {
        move_line=NR
        exit
    }
    END { exit !(stop_line && move_line && stop_line < move_line) }
' "$REPO_ROOT/install/installCyberPanel.py"; then
    pass "custom OpenLiteSpeed binary replacement stops the running server"
else
    fail "custom OpenLiteSpeed binary replacement can fail with a busy executable"
fi
echo ""

# Test 8: systemd-resolved and PowerDNS handoff
echo "Test 8: DNS service handoff"
echo "---------------------------"
if grep -q 'DNSStubListener=no' "$REPO_ROOT/cyberpanel.sh" \
    && grep -q 'chmod 0644 /etc/systemd/resolved.conf' "$REPO_ROOT/cyberpanel.sh" \
    && grep -q 'keep_resolved' "$REPO_ROOT/install/installCyberPanel.py"; then
    pass "installer keeps reliable DNS while reserving port 53 for PowerDNS"
else
    fail "installer is missing the Ubuntu 26 resolved and PowerDNS handoff"
fi

if grep -q 'Acquire::Retries' "$REPO_ROOT/cyberpanel.sh" \
    && grep -q 'APT::Update::Error-Mode=any' "$REPO_ROOT/cyberpanel.sh" \
    && grep -q 'APT::Update::Error-Mode=any' "$REPO_ROOT/install/install.py" \
    && grep -q 'os.chmod(key_file, 0o644)' "$REPO_ROOT/install/install.py"; then
    pass "Ubuntu 26 package indexes and LiteSpeed keys are APT 3 compatible"
else
    fail "Ubuntu 26 package repository refresh is not resilient"
fi

if [[ "$VERSION_ID" == "26.04" ]] && [ -d /usr/local/CyberCP ]; then
    if systemctl is-active --quiet systemd-resolved.service; then
        pass "systemd-resolved remains active for upstream DNS"
    else
        fail "systemd-resolved is not active"
    fi

    if [[ "$(stat -c %a /etc/systemd/resolved.conf 2>/dev/null)" == "644" ]]; then
        pass "systemd-resolved can read the CyberPanel configuration"
    else
        fail "systemd-resolved configuration permissions are incorrect"
    fi

    if runuser -u cyberpanel -- test -r /etc/cyberpanel/machineIP; then
        pass "CyberPanel can read the installed server address"
    else
        fail "CyberPanel cannot read the installed server address"
    fi

    if runuser -u cyberpanel -- /usr/local/CyberCP/bin/python -c \
        'import socket; s=socket.socket(socket.AF_UNIX); s.connect("/usr/local/lscpd/admin/comm.sock"); s.close()' \
        2>/dev/null; then
        pass "CyberPanel can reach the LSCPD command socket"
    else
        fail "CyberPanel cannot reach the LSCPD command socket"
    fi

    if ss -lntup 2>/dev/null | grep -E ':53[[:space:]]' | grep -q systemd-resolve; then
        fail "systemd-resolved still owns port 53"
    else
        pass "systemd-resolved leaves port 53 available to PowerDNS"
    fi

    if systemctl is-failed --quiet systemd-networkd-wait-online.service \
        || systemctl is-failed --quiet systemd-resolved-monitor.socket; then
        fail "resolved handoff left failed systemd units"
    else
        pass "resolved handoff left no failed systemd units"
    fi


    if dpkg-query -W -f='${Status}' quota 2>/dev/null | grep -q 'install ok installed'; then
        pass "quota package is installed"
    else
        fail "quota package is missing after installation"
    fi
fi
echo ""

# Test 9: services
echo "Test 9: Services"
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

if [[ "$VERSION_ID" == "26.04" ]] && [ -d /usr/local/CyberCP ]; then
    for svc in pdns postfix dovecot pure-ftpd-mysql firewalld; do
        if systemctl is-active --quiet "$svc"; then
            pass "$svc is active"
        else
            fail "$svc is not active after the Ubuntu 26.04 install"
        fi
    done

    PANEL_STATUS=$(curl -ksS -o /dev/null -w '%{http_code}' --max-time 15 https://127.0.0.1:8090/ || true)
    if [[ "$PANEL_STATUS" == "200" ]]; then
        pass "CyberPanel returns HTTP 200"
    else
        fail "CyberPanel returned HTTP $PANEL_STATUS"
    fi
fi
echo ""

echo "===================================="
if [ $FAILED -eq 0 ]; then
    echo "All executed checks passed."
    exit 0
else
    echo "One or more checks FAILED - see above."
    exit 1
fi
