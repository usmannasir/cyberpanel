#!/usr/bin/env bash
# Live tests on v3.0.5-dev install (full tree, not v3.0.2 minimal patches)
set -uo pipefail
REPO="/home/Github/cyberPanel-repos/cyberpanel"
LIVE="/usr/local/CyberCP"
PLUGINS="/home/Github/cyberpanel-plugins"
PANEL="${PANEL_URL:-https://127.0.0.1:5003}"
LOG="$REPO/to-do/pr-live-tests/results-v3-$(date +%Y%m%d-%H%M%S).log"
FAIL=0
log(){ echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }
pass(){ log "PASS: $*"; }
fail(){ log "FAIL: $*"; FAIL=1; }
panel(){ local c; c=$(curl -sk -o /dev/null -w '%{http_code}' --connect-timeout 15 "$PANEL/" || echo 000); [[ "$c" =~ ^(200|302)$ ]] && pass "Panel $c" || fail "Panel $c"; return 0; }
restart(){ systemctl restart lscpd; sleep 8; }

log "=== LIVE v3.0.5-dev BASE CHECKS ==="
grep -q '"build":5' "$LIVE/version.txt" && pass "version build 5" || fail "version not build 5"
cd "$LIVE" && git rev-parse --abbrev-ref HEAD 2>/dev/null | grep -q "live/v305-dev-pr-integration" && pass "branch live/v305-dev-pr-integration" || fail "wrong live branch"
test -f "$LIVE/loginSystem/twoFactor.py" && pass "twoFactor present" || fail "twoFactor missing"
panel

log "=== REPO UNIT TESTS (integration branch) ==="
git -C "$REPO" checkout live/v305-dev-pr-integration >/dev/null 2>&1

python3 "$REPO/loginSystem/test_password_rehash.py" >>"$LOG" 2>&1 && pass "#1927 unit" || fail "#1927 unit"
python3 "$REPO/CyberCP/test_csp_insights.py" >>"$LOG" 2>&1 && pass "#1928 unit" || fail "#1928 unit"
python3 -c "import sys; sys.path.insert(0,'$LIVE'); import os; os.environ['DJANGO_SETTINGS_MODULE']='CyberCP.settings'; import django; django.setup(); from plogical.dnsUtilities import DNS; DNS.createCloudFlareClient('a@b.com','key','global_key'); DNS.createCloudFlareClient('','tok','api_token')" >>"$LOG" 2>&1 && pass "#1915 cf clients" || fail "#1915 cf clients"
cmp -s "$REPO/baseTemplate/static/baseTemplate/custom-js/system-status.js" "$REPO/static/baseTemplate/custom-js/system-status.js" && pass "#1909 identical copies" || fail "#1909 copies differ"
python3 "$REPO/baseTemplate/test_dashboard_polling.py" >>"$LOG" 2>&1 && pass "#1909 unit" || fail "#1909 unit"
grep -q autoBanSecurityAlerts "$REPO/firewall/firewallManager.py" && fail "#1908 autoBan present" || pass "#1908 no autoBan"
python3 -c "import sys; sys.path.insert(0,'$LIVE'); import os; os.environ['DJANGO_SETTINGS_MODULE']='CyberCP.settings'; import django; django.setup(); from firewall import ruleOrder; ruleOrder.next_sort_order()" >>"$LOG" 2>&1 && pass "#1908 ruleOrder" || fail "#1908 ruleOrder"

log "=== LIVE FEATURE CHECKS (deployed integration branch) ==="
grep -q needs_password_rehash "$LIVE/loginSystem/views.py" && pass "#1927 rehash in views" || fail "#1927 rehash missing"
grep -q static.cloudflareinsights.com "$LIVE/CyberCP/secMiddleware.py" && pass "#1928 CSP live" || fail "#1928 CSP missing"
curl -sk "$PANEL/" | grep -qE 'data-theme|cyberpanel-theme' && pass "#1931 dark HTML" || fail "#1931 dark HTML"
grep -q pollInFlight "$LIVE/baseTemplate/static/baseTemplate/custom-js/system-status.js" && pass "#1909 pollInFlight" || fail "#1909 pollInFlight"
python3 -m py_compile "$LIVE/plogical/dnsUtilities.py" "$LIVE/dns/dnsManager.py" && pass "#1915 dns py" || fail "#1915 dns py"
python3 -m py_compile "$LIVE/firewall/firewallManager.py" "$LIVE/firewall/ruleOrder.py" && pass "#1908 firewall py" || fail "#1908 firewall py"
panel

log "=== PLUGINS (cyberpanel-plugins) ==="
python3 -m py_compile "$PLUGINS/snappymailWebmail/utils.py" "$PLUGINS/roundcubeWebmail/utils.py" && pass "plugins syntax" || fail "plugins syntax"
if [[ -d "$LIVE/snappymailWebmail" ]]; then
  bash "$LIVE/snappymailWebmail/post_install" >>"$LOG" 2>&1 && pass "snappymail post_install" || fail "snappymail post_install"
else
  cp -a "$PLUGINS/snappymailWebmail" "$LIVE/"
  bash "$LIVE/snappymailWebmail/post_install" >>"$LOG" 2>&1 && pass "snappymail deploy+post_install" || fail "snappymail deploy"
fi
restart
sm=$(curl -sk -o /dev/null -w '%{http_code}' "$PANEL/snappymail/" || echo 000)
wm=$(curl -sk -o /dev/null -w '%{http_code}' "$PANEL/webmail/login" || echo 000)
[[ "$sm" =~ ^(200|302)$ ]] && pass "SnappyMail $sm" || fail "SnappyMail $sm"
[[ "$wm" =~ ^(200|302)$ ]] && pass "webmail/login $wm" || fail "webmail/login $wm"
panel

log "=== PLUGIN STORE ==="
cd "$LIVE" && python3 manage.py shell -c "
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from loginSystem.models import Administrator
from pluginHolder import views
adm = Administrator.objects.first()
if not adm:
    raise SystemExit('no admin')
rf = RequestFactory()
request = rf.get('/plugins/installed')
middleware = SessionMiddleware(lambda r: None)
middleware.process_request(request)
request.session.save()
request.session['userID'] = adm.pk
request.session.save()
response = views.installed(request)
if response.status_code != 200:
    raise SystemExit('plugins/installed status %s' % response.status_code)
print('plugins/installed OK')
" >>"$LOG" 2>&1 && pass "plugins/installed 200" || fail "plugins/installed"

log "=== PLUGIN STORE ==="
cd "$LIVE" && python3 manage.py shell -c "
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from loginSystem.models import Administrator
from pluginHolder import views
adm = Administrator.objects.first()
if not adm: raise SystemExit('no admin')
rf = RequestFactory()
def go(path, view):
    req = rf.get(path)
    m = SessionMiddleware(lambda r: None); m.process_request(req); req.session.save()
    req.session['userID'] = adm.pk; req.session.save()
    r = view(req)
    if r.status_code != 200: raise SystemExit('%s %s' % (path, r.status_code))
go('/plugins/installed', views.installed)
go('/plugins/help/', views.help_page)
go('/plugins/api/store/plugins/', views.fetch_plugin_store)
print('store OK')
" >>"$LOG" 2>&1 && pass "plugin store routes" || fail "plugin store routes"

cd "$LIVE" && python3 manage.py check >>"$LOG" 2>&1 && pass "manage.py check" || fail "manage.py check"
log "Log: $LOG"
exit $FAIL
