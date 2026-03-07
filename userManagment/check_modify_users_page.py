#!/usr/bin/env python3
"""
Check that the Modify User page renders with server-side user options and search.
Uses the real DB (no test database). Run from CyberPanel root:

  cd /usr/local/CyberCP
  ./bin/python manage.py shell < userManagment/check_modify_users_page.py

Or from repo:
  cd /home/cyberpanel-repo && python3 manage.py shell < userManagment/check_modify_users_page.py
"""
import os
import sys
import re

if 'django' not in sys.modules:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')
    import django
    django.setup()

from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from userManagment.views import modifyUsers
from loginSystem.models import Administrator

def main():
    rf = RequestFactory()
    req = rf.get('/users/modifyUsers')
    SessionMiddleware(lambda r: None).process_request(req)
    req.session.save()
    admin = Administrator.objects.first()
    if not admin:
        print('FAIL: No administrator in database')
        sys.exit(1)
    req.session['userID'] = admin.pk
    req.session.save()
    response = modifyUsers(req)
    html = response.content.decode('utf-8')
    errors = []
    if 'data-acct=' not in html:
        errors.append('missing data-acct in options')
    if 'modifyUserSearchInput' not in html:
        errors.append('missing modifyUserSearchInput')
    if 'modifyUserAccountSelect' not in html:
        errors.append('missing modifyUserAccountSelect')
    if not re.search(r'<option\s+value="[^"]+"\s+data-acct=', html):
        errors.append('no user option with value and data-acct')
    if errors:
        print('FAIL:', '; '.join(errors))
        sys.exit(1)
    print('OK: Modify User page renders user dropdown and search.')

if __name__ == '__main__':
    main()
else:
    # When run via: manage.py shell < userManagment/check_modify_users_page.py
    main()
