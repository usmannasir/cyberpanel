#!/usr/local/CyberCP/bin/python
"""Quick checks for case-exact username resolution (run on server with Django)."""
import os
import sys

sys.path.insert(0, '/usr/local/CyberCP')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')

import django
django.setup()

from plogical.usernameUtils import resolve_administrator_by_login_name, validate_username_format


def main():
    ok, _ = validate_username_format('admin')
    assert ok
    admin, exact = resolve_administrator_by_login_name('admin')
    assert admin is not None
    assert exact is True
    _other, exact_wrong = resolve_administrator_by_login_name('ADMIN')
    if admin.userName == 'admin':
        assert exact_wrong is False
    print('username case tests OK')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
