#!/usr/bin/env bash
# Live + unit tests for restore preview / confirmation PR
set -uo pipefail

REPO="/home/Github/cyberPanel-repos/cyberpanel"
LIVE="/usr/local/CyberCP"
PANEL="${PANEL_URL:-https://127.0.0.1:5003}"
LOG="$REPO/to-do/pr-live-tests/results-restore-preview-$(date +%Y%m%d-%H%M%S).log"
FAIL=0

log(){ echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }
pass(){ log "PASS: $*"; }
fail(){ log "FAIL: $*"; FAIL=1; }

log "=== RESTORE PREVIEW UNIT TESTS ==="
cd "$LIVE" && PYTHONPATH="$REPO:$LIVE" /usr/local/CyberCP/bin/python "$REPO/backup/test_restore_preview.py" >>"$LOG" 2>&1 && pass "restore preview unit tests" || fail "restore preview unit tests"

log "=== PYTHON SYNTAX ==="
python3 -m py_compile \
  "$LIVE/backup/backupManager.py" \
  "$LIVE/backup/views.py" \
  "$REPO/backup/test_restore_preview.py" >>"$LOG" 2>&1 \
  && pass "python syntax" || fail "python syntax"

log "=== LIVE STATIC + TEMPLATE CHECKS ==="
grep -q 'getBackupFileInfo' "$LIVE/static/backup/backup.js" && pass "live backup.js preview endpoint" || fail "live backup.js preview endpoint"
grep -q 'openRestoreConfirm' "$LIVE/static/backup/backup.js" && pass "live backup.js confirm modal" || fail "live backup.js confirm modal"
grep -q 'Review and Restore' "$LIVE/backup/templates/backup/restore.html" && pass "live restore template" || fail "live restore template"

log "=== LIVE API CHECKS (authenticated shell) ==="
cd "$LIVE" && python3 manage.py shell -c "
import json
import os
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from loginSystem.models import Administrator
from backup import views

adm = Administrator.objects.first()
if not adm:
    raise SystemExit('no admin user')

backup_dir = '/home/backup'
files = [f for f in os.listdir(backup_dir) if f.endswith('.tar.gz')]
if not files:
    raise SystemExit('no .tar.gz backups in /home/backup for live test')
sample = files[0]

def post(path, view, payload):
    rf = RequestFactory()
    req = rf.post(path, data=json.dumps(payload), content_type='application/json')
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(req)
    req.session.save()
    req.session['userID'] = adm.pk
    req.session.save()
    return view(req)

info_resp = post('/backup/getBackupFileInfo', views.getBackupFileInfo, {'backupFile': sample})
info = json.loads(info_resp.content)
if info.get('infoStatus') != 1:
    raise SystemExit('getBackupFileInfo failed: %s' % info)
if info.get('fileName') != sample:
    raise SystemExit('unexpected fileName: %s' % info.get('fileName'))

reject_resp = post('/backup/submitRestore', views.submitRestore, {'backupFile': sample})
reject = json.loads(reject_resp.content)
if reject.get('restoreStatus') != 0:
    raise SystemExit('submitRestore without confirm should fail')
if 'confirmation required' not in reject.get('error_message', '').lower():
    raise SystemExit('unexpected reject message: %s' % reject.get('error_message'))

print('live restore preview API OK (%s)' % sample)
" >>"$LOG" 2>&1 && pass "live restore preview API" || fail "live restore preview API"

panel_code=$(curl -sk -o /dev/null -w '%{http_code}' --connect-timeout 15 "$PANEL/backup/restoreSite" || echo 000)
[[ "$panel_code" =~ ^(200|302)$ ]] && pass "restoreSite route $panel_code" || fail "restoreSite route $panel_code"

log "Log: $LOG"
exit $FAIL
